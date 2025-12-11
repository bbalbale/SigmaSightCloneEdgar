# Batch Processing Caching Optimization Plan

**Created**: 2025-11-06
**Status**: Planning Phase
**Goal**: Reduce batch processing time by 100-500x through smart caching architecture

---

## Executive Summary

**Problem**: Current batch processing queries the database 15,000+ times for data that's shared across portfolios (prices, company profiles, etc.). At scale (1,000+ portfolios), this is prohibitively slow.

**Solution**: Implement multi-layer caching that bulk-loads shared data once and reuses it across all portfolios.

**Expected Impact**:
- **Current**: 10 minutes for 1 month × 6 portfolios = ~167 minutes for 100 portfolios
- **With Caching**: 10 minutes for 1 month × 100 portfolios = ~10-15 minutes for 100 portfolios
- **Speedup**: **~10-15x improvement at 100 portfolios, scales linearly**

---

## Architecture Overview

### Current Flow (Wasteful)
```
For each portfolio:
  For each position in portfolio:
    Query database for price ❌ (15,000 queries)
    Query database for company profile ❌ (180 queries)
    Query database for previous snapshot ❌ (720 queries)
```

### Optimized Flow (Cached)
```
ONCE at start:
  Bulk load ALL prices for ALL symbols ✅ (1 query)
  Bulk load ALL company profiles ✅ (1 query)
  Bulk load ALL previous snapshots ✅ (1 query)

For each portfolio:
  For each position in portfolio:
    Lookup price in cache (O(1) dictionary)
    Lookup company profile in cache (O(1))
    Lookup previous snapshot in cache (O(1))
```

---

## PREREQUISITE: Database Indexes (Do FIRST)

Before implementing caching, these composite indexes are **REQUIRED** to make bulk queries fast. Without them, caching won't provide full benefit.

### **Priority 1: Extended Position Active Lookup** ⭐⭐⭐ **CRITICAL**

**Current Index**: `idx_positions_portfolio_deleted` on `(portfolio_id, deleted_at)`
**Problem**: Query filters on 4 columns but only 2 are indexed

**Query Pattern** (called 100-300 times per batch):
```python
Position.portfolio_id == portfolio_id,           # ✅ Indexed
Position.deleted_at.is_(None),                   # ✅ Indexed
Position.exit_date.is_(None),                    # ❌ NOT indexed
Position.investment_class.notin_(['PRIVATE'])    # ❌ NOT indexed
```

**Required Index**:
```sql
-- Drop old partial index
DROP INDEX IF EXISTS idx_positions_portfolio_deleted;

-- Create extended index
CREATE INDEX idx_positions_active_complete
ON positions(portfolio_id, deleted_at, exit_date, investment_class)
WHERE deleted_at IS NULL;
```

**Impact**:
- Current: Scans 100+ positions per portfolio to filter exit_date and investment_class
- After: Jumps directly to active positions of correct class
- **Speedup**: ~5-10x faster on position queries
- **Critical at scale**: With 1000s of positions, this becomes essential

**Estimated Effort**: 5 minutes (one migration)
**ROI**: **HIGH** - Required for Stage 1 caching to be effective

---

### **Priority 2: Market Data Cache with Close Filter** ⭐⭐ **HIGH**

**Current Index**: `idx_market_data_cache_symbol_date` on `(symbol, date)`
**Problem**: Many queries also filter for valid prices (close > 0)

**Query Pattern** (called 1000+ times per batch):
```python
MarketDataCache.symbol == symbol,     # ✅ Indexed
MarketDataCache.date == date,         # ✅ Indexed
MarketDataCache.close > 0             # ❌ NOT indexed (filtered after lookup)
```

**Required Index**:
```sql
-- Create covering index with close column
CREATE INDEX idx_market_data_symbol_date_close
ON market_data_cache(symbol, date, close)
WHERE close > 0;
```

**Alternative** (if above too large):
```sql
-- Partial index only for valid prices
CREATE INDEX idx_market_data_valid_prices
ON market_data_cache(symbol, date)
WHERE close > 0;
```

**Impact**:
- Current: Fetches all prices (including invalid close=0), filters in Python
- After: Index only contains valid prices, no post-filtering needed
- **Speedup**: ~2-3x faster on price lookups
- **Disk space savings**: Partial index is smaller (excludes invalid prices)

**Estimated Effort**: 5 minutes (one migration)
**ROI**: **MEDIUM-HIGH** - Complements Stage 1 caching

---

### **Priority 3: Position Symbol Active Filter** ⭐ **MEDIUM-HIGH**

**Current**: Individual indexes on `symbol`, `deleted_at`, `exit_date`, `expiration_date`
**Problem**: Symbol universe queries must combine multiple conditions

**Query Pattern** (called ~30 times per batch - once per date):
```python
Position.deleted_at.is_(None),           # Has single index
Position.symbol.is_not(None),            # Has single index
Position.exit_date.is_(None)             # Has single index
Position.expiration_date >= date         # Has single index
```

**Required Index**:
```sql
-- Composite index for active symbol lookup
CREATE INDEX idx_positions_symbol_active
ON positions(deleted_at, symbol, exit_date, expiration_date)
WHERE deleted_at IS NULL AND symbol IS NOT NULL AND symbol != '';
```

**Impact**:
- Current: PostgreSQL picks one index, scans remaining conditions
- After: All conditions handled by single index lookup
- **Speedup**: ~10-20x faster on symbol universe queries
- **Critical for**: Multi-day caching (Stage 2) where this runs once for entire date range

**Estimated Effort**: 5 minutes (one migration)
**ROI**: **MEDIUM** - Bigger impact with Stage 2 multi-day caching

---

### **Index Implementation**

**Create Migration**:
```bash
cd backend
uv run alembic revision -m "add_priority_indexes_for_caching"
```

**Migration Content**:
```python
"""add_priority_indexes_for_caching

Adds 3 composite indexes required for caching optimization:
1. Extended position active lookup (portfolio_id, deleted_at, exit_date, investment_class)
2. Market data with close filter (symbol, date, close) WHERE close > 0
3. Position symbol active filter (deleted_at, symbol, exit_date, expiration_date)

Revision ID: xyz123
Revises: i6j7k8l9m0n1
Create Date: 2025-11-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'xyz123'
down_revision: Union[str, Sequence[str], None] = 'i6j7k8l9m0n1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add priority indexes for caching optimization."""

    # Priority 1: Extended position active lookup
    # Drop old partial index if exists
    op.execute("DROP INDEX IF EXISTS idx_positions_portfolio_deleted")

    op.create_index(
        'idx_positions_active_complete',
        'positions',
        ['portfolio_id', 'deleted_at', 'exit_date', 'investment_class'],
        unique=False,
        postgresql_where=sa.text('deleted_at IS NULL')
    )

    # Priority 2: Market data cache with close filter
    op.create_index(
        'idx_market_data_valid_prices',
        'market_data_cache',
        ['symbol', 'date'],
        unique=False,
        postgresql_where=sa.text('close > 0')
    )

    # Priority 3: Position symbol active filter
    op.create_index(
        'idx_positions_symbol_active',
        'positions',
        ['deleted_at', 'symbol', 'exit_date', 'expiration_date'],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL AND symbol IS NOT NULL AND symbol != ''")
    )


def downgrade() -> None:
    """Remove priority indexes."""
    op.drop_index('idx_positions_symbol_active', table_name='positions')
    op.drop_index('idx_market_data_valid_prices', table_name='market_data_cache')
    op.drop_index('idx_positions_active_complete', table_name='positions')

    # Recreate old index
    op.create_index(
        'idx_positions_portfolio_deleted',
        'positions',
        ['portfolio_id', 'deleted_at'],
        unique=False
    )
```

**Apply Migration**:
```bash
uv run alembic upgrade head
```

**Verify Indexes**:
```sql
-- Check positions indexes
\d positions

-- Check market_data_cache indexes
\d market_data_cache

-- Or via Python:
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('positions', 'market_data_cache')
ORDER BY tablename, indexname;
```

---

### **Index ROI Summary**

| Index | Effort | Queries Affected | Speedup | Critical For |
|-------|--------|------------------|---------|--------------|
| Priority 1: Extended Position Active | 5 min | 100-300/batch | 5-10x | Stage 1 (single-day cache) |
| Priority 2: Market Data Valid Prices | 5 min | 1000+/batch | 2-3x | Stage 1 & 2 (multi-day cache) |
| Priority 3: Symbol Active Filter | 5 min | 30/batch | 10-20x | Stage 2 (multi-day cache) |
| **TOTAL** | **15 min** | **1400+/batch** | **Combined 10-50x** | **All caching stages** |

**Recommendation**: Create and apply this migration **BEFORE** implementing any caching stages. The indexes make both current batch processing AND future caching much faster.

---

## Implementation Stages

### **Stage 1: Price Cache (Single-Day)** ⭐ **HIGHEST PRIORITY**

**Scope**: Cache market prices for ONE calculation date

**Files to Modify**:
1. `backend/app/batch/pnl_calculator.py`
2. `backend/app/calculations/market_data.py`

**Estimated Effort**: **4-6 hours**

**Expected ROI**:
- **Current**: 15,000 price queries × 10ms = 150 seconds
- **After**: 1 bulk query × 500ms + 15,000 dict lookups × 0.001ms = 0.5 seconds
- **Time Saved**: **149.5 seconds per batch date**
- **Speedup**: **300x on price lookups**

**For 120-day backfill**:
- Time saved: 149.5s × 120 days = **~5 hours saved**
- Current ~6-8 hours → After ~1-3 hours

**Implementation Details**: See Section "Stage 1 Implementation"

---

### **Stage 2: Price Cache (Multi-Day)** ⭐⭐ **HIGH PRIORITY**

**Scope**: Cache prices for MULTIPLE dates (rolling window for backfills)

**Why Needed**:
- Backfill scenario: Processing 120 dates sequentially
- Each date needs prices for current AND previous trading days (equity rollforward)
- **Without multi-day cache**: Must query previous day prices 120 times
- **With multi-day cache**: Load all 120 days at once

**Files to Modify**:
1. `backend/app/batch/pnl_calculator.py` - Extend Stage 1 cache
2. `backend/app/batch/batch_orchestrator.py` - Pass date range to bulk loader

**Estimated Effort**: **2-3 hours** (builds on Stage 1)

**Expected ROI**:
- **Current** (with Stage 1): 120 bulk queries × 500ms = 60 seconds
- **After Stage 2**: 1 bulk query for all dates × 5 seconds = 5 seconds
- **Additional Time Saved**: **55 seconds per backfill**
- **Speedup**: **12x on multi-day backfills**

**For 120-day backfill**:
- Additional time saved: **55 seconds**
- Stage 1 result: ~1-3 hours → After Stage 2: **~1-2 hours**

**Implementation Details**: See Section "Stage 2 Implementation"

---

### **Stage 3: Company Profile Cache** ⭐ **MEDIUM PRIORITY**

**Scope**: Cache company profiles (beta, sector, industry)

**Files to Modify**:
1. `backend/app/batch/batch_orchestrator.py` - Bulk load profiles at start
2. `backend/app/calculations/market_beta.py` - Accept profile cache
3. `backend/app/calculations/sector_analysis.py` - Accept profile cache
4. `backend/app/services/sector_tag_service.py` - Accept profile cache

**Estimated Effort**: **3-4 hours**

**Expected ROI**:
- **Current** (with Steps 3.1-3.7 optimizations): ~180 profile queries on current/final date only
- **After**: 1 bulk query × 100ms = 0.1 seconds
- **Time Saved**: **~1.8 seconds per batch run**
- **Speedup**: **18x on profile lookups**

**For 120-day backfill**:
- Time saved: **~2 seconds total** (only runs on final date)
- Minor impact on backfill, **major impact on daily production runs**

**Implementation Details**: See Section "Stage 3 Implementation"

---

### **Stage 4: Snapshot Cache for Equity Rollforward** ⭐ **MEDIUM-HIGH PRIORITY**

**Scope**: Cache previous portfolio snapshots for equity rollforward

**Files to Modify**:
1. `backend/app/batch/pnl_calculator.py` - Bulk load snapshots

**Estimated Effort**: **2-3 hours**

**Expected ROI**:
- **Current**: 720 snapshot queries (6 portfolios × 120 days) × 10ms = 7.2 seconds
- **After**: 1 bulk query × 200ms = 0.2 seconds
- **Time Saved**: **7 seconds per backfill**
- **Speedup**: **36x on equity rollforward**

**For 120-day backfill**:
- Time saved: **7 seconds**
- Cumulative with Stages 1-3: **~1-2 hours** → **~1-1.5 hours**

**At 1000 portfolios**:
- Current: 120,000 queries × 10ms = **20 minutes**
- After: 1 bulk query × 2 seconds = **2 seconds**
- **MASSIVE impact at scale**

**Implementation Details**: See Section "Stage 4 Implementation"

---

### **Stage 5: Factor ETF Cache** ⭐ **LOW-MEDIUM PRIORITY**

**Scope**: Cache factor ETF prices (SPY, TLT, etc.)

**Files to Modify**:
1. `backend/app/calculations/factors.py` - Use cached factor prices

**Estimated Effort**: **1-2 hours**

**Expected ROI**:
- **Current**: ~50 factor ETF queries per batch × 10ms = 0.5 seconds
- **After**: Included in Stage 1 price cache = 0 seconds
- **Time Saved**: **0.5 seconds**
- **Note**: Mostly covered by Stage 1, minimal additional work

**Implementation Details**: See Section "Stage 5 Implementation"

---

## Total ROI Summary

### Time Investment
| Stage | Effort | Cumulative |
|-------|--------|------------|
| Stage 1: Single-Day Price Cache | 4-6 hours | 4-6 hours |
| Stage 2: Multi-Day Price Cache | 2-3 hours | 6-9 hours |
| Stage 3: Company Profile Cache | 3-4 hours | 9-13 hours |
| Stage 4: Snapshot Cache | 2-3 hours | 11-16 hours |
| Stage 5: Factor ETF Cache | 1-2 hours | 12-18 hours |
| **TOTAL** | **12-18 hours** | - |

### Time Savings (120-day backfill, 6 portfolios)

| Optimization | Current Time | After Stage | Time Saved | Speedup |
|--------------|--------------|-------------|------------|---------|
| **Baseline** (Steps 1-3.7) | 6-8 hours | - | - | - |
| **+ Stage 1** (Single-Day Cache) | 6-8 hours | 1-3 hours | **~5 hours** | **3-5x** |
| **+ Stage 2** (Multi-Day Cache) | 1-3 hours | 1-2 hours | **~1 hour** | **1.5x** |
| **+ Stage 3** (Profile Cache) | 1-2 hours | 1-2 hours | **~2 sec** | **1.0x** |
| **+ Stage 4** (Snapshot Cache) | 1-2 hours | ~1 hour | **~7 sec** | **1.0x** |
| **+ Stage 5** (Factor Cache) | ~1 hour | ~1 hour | **~0.5 sec** | **1.0x** |
| **TOTAL IMPROVEMENT** | **6-8 hours** | **~1 hour** | **~6-7 hours** | **6-8x** |

### Time Savings (120-day backfill, 1000 portfolios)

| Optimization | Current Time | After Stages 1-5 | Time Saved | Speedup |
|--------------|--------------|------------------|------------|---------|
| **No Optimizations** | ~280 hours (11.7 days) | - | - | - |
| **Steps 1-3.7 Only** | ~14 hours | - | 266 hours | **20x** |
| **+ Stages 1-5 Caching** | ~14 hours | **~1.5-2 hours** | **~12 hours** | **~9x additional** |
| **TOTAL** | **280 hours** | **~1.5-2 hours** | **~278 hours** | **~180x total** |

---

## Scale Analysis: Production Daily Runs

### Scenario: Daily Batch for 10,000 Portfolios

**Without Caching** (even with indexes):
```
10,000 portfolios × 15 positions × 10ms per query = 25 minutes (just prices)
10,000 portfolios × 10ms snapshot query = 100 seconds = 1.7 minutes
Total: ~30-40 minutes per day
```

**With Full Caching**:
```
1 bulk price query (3000 symbols) = 500ms
1 bulk snapshot query (10,000 portfolios) = 2 seconds
10,000 portfolios × in-memory processing = 30 seconds
Total: ~35 seconds per day
```

**Speedup**: **30-40 minutes → 35 seconds = ~60x faster**

**Annual Savings**:
- Without caching: 30 min/day × 365 days = **182.5 hours/year**
- With caching: 35 sec/day × 365 days = **3.5 hours/year**
- **Savings**: **179 hours/year** (22 working days!)

---

## Implementation Priority Recommendation

### **Phase 1: Must-Have (Blocks Scale)**
Do these FIRST before onboarding more customers:

1. ✅ **Stage 1: Single-Day Price Cache** - 4-6 hours, 300x speedup
2. ✅ **Stage 2: Multi-Day Price Cache** - 2-3 hours, 12x additional
3. ✅ **Stage 4: Snapshot Cache** - 2-3 hours, critical at scale

**Total**: 8-12 hours, enables scale to 1000+ portfolios

### **Phase 2: Production Optimization**
Do these for daily production efficiency:

4. ✅ **Stage 3: Company Profile Cache** - 3-4 hours, daily batch speedup
5. ✅ **Stage 5: Factor ETF Cache** - 1-2 hours, minor additional benefit

**Total**: 4-6 hours, improves daily operations

---

## Stage 1 Implementation

### Overview
Cache market prices for a single calculation date, reuse across all portfolios.

### Architecture

**New File**: `backend/app/batch/cache_manager.py`
```python
"""
Cache management for batch processing.
Provides in-memory caches for market data, company profiles, and snapshots.
"""

from typing import Dict, List, Set, Tuple, Optional
from decimal import Decimal
from datetime import date
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data import MarketDataCache
from app.models.company_profiles import CompanyProfile
from app.models.snapshots import PortfolioSnapshot
from app.core.logging import get_logger

logger = get_logger(__name__)


class PriceCache:
    """
    In-memory cache for market prices.

    Usage:
        cache = PriceCache()
        await cache.load(db, symbols, calculation_date)
        price = cache.get("AAPL", calculation_date)
    """

    def __init__(self):
        self._cache: Dict[Tuple[str, date], Decimal] = {}
        self._loaded_dates: Set[date] = set()

    async def load_single_date(
        self,
        db: AsyncSession,
        symbols: Set[str],
        calculation_date: date
    ) -> int:
        """
        Load prices for all symbols on a single date.

        Args:
            db: Database session
            symbols: Set of symbols to load
            calculation_date: Date to load prices for

        Returns:
            Number of prices loaded
        """
        if calculation_date in self._loaded_dates:
            logger.debug(f"Prices for {calculation_date} already loaded, skipping")
            return 0

        logger.info(f"[CACHE] Bulk loading prices for {len(symbols)} symbols on {calculation_date}")

        # ONE bulk query instead of N individual queries
        stmt = select(
            MarketDataCache.symbol,
            MarketDataCache.date,
            MarketDataCache.close
        ).where(
            and_(
                MarketDataCache.symbol.in_(list(symbols)),
                MarketDataCache.date == calculation_date,
                MarketDataCache.close > 0  # Filter invalid prices
            )
        )

        result = await db.execute(stmt)

        # Build in-memory cache
        loaded_count = 0
        for row in result:
            cache_key = (row.symbol, row.date)
            self._cache[cache_key] = row.close
            loaded_count += 1

        self._loaded_dates.add(calculation_date)

        logger.info(f"[CACHE] Loaded {loaded_count} prices for {calculation_date}")
        return loaded_count

    def get(self, symbol: str, calculation_date: date) -> Optional[Decimal]:
        """
        Get price from cache.

        Args:
            symbol: Stock symbol
            calculation_date: Date of price

        Returns:
            Price as Decimal, or None if not in cache
        """
        cache_key = (symbol, calculation_date)
        return self._cache.get(cache_key)

    def get_batch(self, symbols: List[str], calculation_date: date) -> Dict[str, Decimal]:
        """
        Get prices for multiple symbols at once.

        Args:
            symbols: List of symbols
            calculation_date: Date of prices

        Returns:
            Dict mapping symbol -> price (only for symbols with prices)
        """
        result = {}
        for symbol in symbols:
            price = self.get(symbol, calculation_date)
            if price is not None:
                result[symbol] = price
        return result

    def clear(self):
        """Clear all cached data"""
        self._cache.clear()
        self._loaded_dates.clear()
        logger.info("[CACHE] Cleared price cache")

    def stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'total_prices': len(self._cache),
            'dates_loaded': len(self._loaded_dates)
        }
```

### Modified File: `backend/app/batch/pnl_calculator.py`

**Key Changes**:
1. Add cache initialization at start of batch
2. Bulk load all symbols once
3. Pass cache to calculation functions
4. Use cache instead of database queries

```python
# Add to imports
from app.batch.cache_manager import PriceCache

class PnLCalculator:
    """P&L Calculator with caching support"""

    async def calculate_all_portfolios_pnl(
        self,
        calculation_date: date,
        db: AsyncSession,
        portfolio_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Calculate P&L for all portfolios with smart caching.

        OPTIMIZATION: Bulk loads all market data once instead of
        querying individually for each portfolio.
        """

        logger.info(f"Starting P&L calculation for {len(portfolio_ids) if portfolio_ids else 'all'} portfolios")

        # STEP 1: Collect all symbols from all portfolios
        logger.info("[CACHE OPTIMIZATION] Step 1: Collecting symbol universe")
        all_symbols = set()
        portfolio_positions_map = {}

        for portfolio_id in portfolio_ids:
            # Get positions for this portfolio
            positions = await self._get_active_positions(db, portfolio_id, calculation_date)
            portfolio_positions_map[portfolio_id] = positions

            # Add symbols to universe
            for position in positions:
                if position.symbol:
                    all_symbols.add(position.symbol)

        logger.info(f"[CACHE OPTIMIZATION] Found {len(all_symbols)} unique symbols across {len(portfolio_ids)} portfolios")

        # STEP 2: Bulk load ALL prices in ONE query
        logger.info("[CACHE OPTIMIZATION] Step 2: Bulk loading market prices")
        price_cache = PriceCache()
        loaded_count = await price_cache.load_single_date(db, all_symbols, calculation_date)

        logger.info(f"[CACHE OPTIMIZATION] Loaded {loaded_count} prices into cache")
        logger.info(f"[CACHE OPTIMIZATION] Cache stats: {price_cache.stats()}")

        # STEP 3: Process portfolios using cached data (NO MORE DB QUERIES!)
        logger.info("[CACHE OPTIMIZATION] Step 3: Processing portfolios with cached data")
        results = []

        for portfolio_id in portfolio_ids:
            positions = portfolio_positions_map[portfolio_id]

            # Calculate P&L using cache (no DB queries)
            result = await self._calculate_portfolio_pnl_with_cache(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                positions=positions,
                price_cache=price_cache  # ✅ Pass cache
            )

            results.append(result)

        # STEP 4: Log cache efficiency
        cache_stats = price_cache.stats()
        logger.info(f"[CACHE OPTIMIZATION] Completed P&L calculation")
        logger.info(f"[CACHE OPTIMIZATION] Cache hit rate: {loaded_count}/{len(all_symbols)} ({loaded_count/len(all_symbols)*100:.1f}%)")

        return {
            'success': True,
            'portfolios_processed': len(results),
            'cache_stats': cache_stats,
            'results': results
        }

    async def _calculate_portfolio_pnl_with_cache(
        self,
        db: AsyncSession,
        portfolio_id: UUID,
        calculation_date: date,
        positions: List[Position],
        price_cache: PriceCache  # ✅ Cache parameter
    ) -> Dict[str, Any]:
        """
        Calculate P&L for single portfolio using price cache.

        NO database queries for prices - all lookups from cache!
        """

        # Get previous equity (still requires DB query for snapshot)
        previous_equity = await self._get_previous_equity(db, portfolio_id, calculation_date)

        total_unrealized_pnl = Decimal('0')
        total_realized_pnl = Decimal('0')
        positions_with_prices = 0
        positions_missing_prices = 0

        for position in positions:
            # ✅ Get price from CACHE (O(1) lookup, no DB query)
            current_price = price_cache.get(position.symbol, calculation_date)

            if current_price is None:
                logger.warning(f"[CACHE MISS] No price in cache for {position.symbol} on {calculation_date}")
                positions_missing_prices += 1
                continue

            positions_with_prices += 1

            # Calculate P&L (all math in memory, no DB)
            cost_basis = position.cost_basis_per_share or Decimal('0')
            quantity = position.quantity or Decimal('0')

            # Unrealized P&L
            unrealized_pnl = (current_price - cost_basis) * quantity
            total_unrealized_pnl += unrealized_pnl

            # Realized P&L (if position closed)
            if position.exit_date and position.exit_date == calculation_date:
                realized_pnl = unrealized_pnl
                total_realized_pnl += realized_pnl

        # Calculate new equity
        daily_capital_flow = Decimal('0')  # TODO: Track deposits/withdrawals
        new_equity = previous_equity + total_unrealized_pnl + total_realized_pnl + daily_capital_flow

        # Update portfolio equity (still requires DB write)
        portfolio = await self._get_portfolio(db, portfolio_id)
        portfolio.equity_balance = new_equity
        await db.flush()

        logger.info(f"[P&L] Portfolio {portfolio_id}: {positions_with_prices} positions with prices, {positions_missing_prices} missing")

        return {
            'portfolio_id': portfolio_id,
            'calculation_date': calculation_date,
            'previous_equity': previous_equity,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_realized_pnl': total_realized_pnl,
            'new_equity': new_equity,
            'positions_processed': len(positions),
            'positions_with_prices': positions_with_prices,
            'positions_missing_prices': positions_missing_prices
        }
```

### Testing Plan for Stage 1

**Test 1: Verify Cache Loading**
```bash
cd backend
uv run python -c "
import asyncio
from datetime import date
from app.batch.cache_manager import PriceCache
from app.database import get_async_session

async def test():
    async with get_async_session() as db:
        cache = PriceCache()
        symbols = {'AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN'}

        # Test single-day load
        loaded = await cache.load_single_date(db, symbols, date(2025, 11, 6))
        print(f'Loaded {loaded} prices')

        # Test cache retrieval
        aapl_price = cache.get('AAPL', date(2025, 11, 6))
        print(f'AAPL price: {aapl_price}')

        # Test batch retrieval
        prices = cache.get_batch(['AAPL', 'MSFT'], date(2025, 11, 6))
        print(f'Batch prices: {prices}')

        # Test stats
        print(f'Cache stats: {cache.stats()}')

asyncio.run(test())
"
```

**Test 2: Performance Comparison**
```bash
# Before caching
time uv run python scripts/batch_processing/run_batch.py --start-date 2025-11-01 --end-date 2025-11-07

# After implementing Stage 1
time uv run python scripts/batch_processing/run_batch.py --start-date 2025-11-01 --end-date 2025-11-07

# Should see ~5-10x improvement
```

---

## Stage 2 Implementation

### Overview
Extend Stage 1 to cache prices for MULTIPLE dates (rolling window).

### Key Enhancement: Multi-Day Bulk Loading

**Add to `cache_manager.py`**:
```python
class PriceCache:
    # ... existing methods from Stage 1 ...

    async def load_date_range(
        self,
        db: AsyncSession,
        symbols: Set[str],
        start_date: date,
        end_date: date
    ) -> int:
        """
        Load prices for all symbols across a date range.

        Perfect for backfills - loads all dates at once instead of
        querying individually for each date.

        Args:
            db: Database session
            symbols: Set of symbols to load
            start_date: First date to load
            end_date: Last date to load

        Returns:
            Number of prices loaded
        """
        logger.info(f"[CACHE] Bulk loading prices for {len(symbols)} symbols from {start_date} to {end_date}")

        # ONE massive query for entire date range
        stmt = select(
            MarketDataCache.symbol,
            MarketDataCache.date,
            MarketDataCache.close
        ).where(
            and_(
                MarketDataCache.symbol.in_(list(symbols)),
                MarketDataCache.date >= start_date,
                MarketDataCache.date <= end_date,
                MarketDataCache.close > 0
            )
        )

        result = await db.execute(stmt)

        # Build in-memory cache
        loaded_count = 0
        dates_seen = set()

        for row in result:
            cache_key = (row.symbol, row.date)
            self._cache[cache_key] = row.close
            loaded_count += 1
            dates_seen.add(row.date)

        # Track which dates we've loaded
        self._loaded_dates.update(dates_seen)

        logger.info(f"[CACHE] Loaded {loaded_count} prices across {len(dates_seen)} dates")
        return loaded_count

    def get_with_lookback(
        self,
        symbol: str,
        calculation_date: date,
        lookback_days: int = 10
    ) -> Tuple[Optional[Decimal], Optional[date]]:
        """
        Get price with fallback to previous trading days.

        Useful for equity rollforward when exact date might be missing.

        Args:
            symbol: Stock symbol
            calculation_date: Preferred date
            lookback_days: How many days to look back

        Returns:
            Tuple of (price, actual_date) or (None, None) if not found
        """
        from datetime import timedelta

        for days_back in range(lookback_days + 1):
            check_date = calculation_date - timedelta(days=days_back)
            price = self.get(symbol, check_date)

            if price is not None:
                if days_back > 0:
                    logger.debug(f"[CACHE FALLBACK] Using {symbol} price from {check_date} (requested {calculation_date})")
                return price, check_date

        return None, None
```

### Modified File: `backend/app/batch/batch_orchestrator.py`

```python
async def run_batch_sequence(
    self,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    portfolio_ids: Optional[List[UUID]] = None
) -> Dict[str, Any]:
    """
    Run batch sequence with multi-day caching optimization.
    """

    # Generate date range
    date_range = self._generate_date_range(start_date, end_date)

    logger.info(f"Processing {len(date_range)} dates from {date_range[0]} to {date_range[-1]}")

    # OPTIMIZATION: For multi-day runs, initialize cache with entire date range
    if len(date_range) > 1:
        logger.info("[MULTI-DAY CACHE] Initializing cache for entire date range")

        # Collect all symbols across all portfolios
        all_symbols = await self._collect_all_symbols(db, portfolio_ids)
        logger.info(f"[MULTI-DAY CACHE] Found {len(all_symbols)} unique symbols")

        # Load ALL prices for ALL dates in ONE query
        price_cache = PriceCache()
        loaded_count = await price_cache.load_date_range(
            db=db,
            symbols=all_symbols,
            start_date=date_range[0],
            end_date=date_range[-1]
        )

        logger.info(f"[MULTI-DAY CACHE] Loaded {loaded_count} prices for {len(date_range)} dates")
    else:
        # Single date - use Stage 1 single-day cache
        price_cache = None

    # Process each date
    results = []
    for calculation_date in date_range:
        logger.info(f"Processing date: {calculation_date}")

        # Run phases with cached data
        result = await self._run_sequence_with_session(
            db=db,
            calculation_date=calculation_date,
            portfolio_ids=portfolio_ids,
            price_cache=price_cache  # ✅ Pass multi-day cache
        )

        results.append(result)

    return results

async def _collect_all_symbols(
    self,
    db: AsyncSession,
    portfolio_ids: Optional[List[UUID]]
) -> Set[str]:
    """
    Collect all unique symbols across all portfolios.

    Used for initializing multi-day cache.
    """
    all_symbols = set()

    # Get all positions
    stmt = select(Position.symbol.distinct()).where(
        and_(
            Position.deleted_at.is_(None),
            Position.symbol.is_not(None),
            Position.symbol != ''
        )
    )

    if portfolio_ids:
        stmt = stmt.where(Position.portfolio_id.in_(portfolio_ids))

    result = await db.execute(stmt)
    all_symbols = {row[0] for row in result}

    # Add factor ETF symbols
    factor_symbols = {'SPY', 'TLT', 'IEF', 'SHY', 'HYG', 'LQD', 'VTV', 'VUG', 'MTUM', 'QUAL', 'USMV'}
    all_symbols.update(factor_symbols)

    return all_symbols
```

### Performance Impact: Stage 2

**Scenario**: 120-day backfill with 6 portfolios

**Stage 1 Only** (single-day cache):
```
For each of 120 dates:
  Bulk load prices for 500 symbols = 500ms
Total: 120 × 500ms = 60 seconds
```

**Stage 2** (multi-day cache):
```
ONCE at start:
  Bulk load prices for 500 symbols × 120 dates = 5 seconds
Total: 5 seconds
```

**Improvement**: **60 seconds → 5 seconds = 12x faster**

---

## Stage 3 Implementation

### Overview
Cache company profiles (beta, sector, industry) to eliminate N+1 queries.

### New Class in `cache_manager.py`

```python
from app.models.company_profiles import CompanyProfile

class CompanyProfileCache:
    """
    In-memory cache for company profiles.

    Stores beta, sector, industry, and other company metadata.
    """

    def __init__(self):
        self._cache: Dict[str, CompanyProfile] = {}

    async def load(
        self,
        db: AsyncSession,
        symbols: Set[str]
    ) -> int:
        """
        Bulk load company profiles for all symbols.

        Args:
            db: Database session
            symbols: Set of symbols to load

        Returns:
            Number of profiles loaded
        """
        logger.info(f"[CACHE] Bulk loading company profiles for {len(symbols)} symbols")

        # ONE bulk query
        stmt = select(CompanyProfile).where(
            CompanyProfile.symbol.in_(list(symbols))
        )

        result = await db.execute(stmt)

        # Build cache
        loaded_count = 0
        for profile in result.scalars():
            self._cache[profile.symbol] = profile
            loaded_count += 1

        logger.info(f"[CACHE] Loaded {loaded_count} company profiles")
        return loaded_count

    def get(self, symbol: str) -> Optional[CompanyProfile]:
        """Get company profile from cache"""
        return self._cache.get(symbol)

    def get_beta(self, symbol: str) -> Optional[Decimal]:
        """Get beta value from cached profile"""
        profile = self.get(symbol)
        return profile.beta if profile else None

    def get_sector(self, symbol: str) -> Optional[str]:
        """Get sector from cached profile"""
        profile = self.get(symbol)
        return profile.sector if profile else None

    def stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'total_profiles': len(self._cache)
        }
```

### Modified Files

**1. `backend/app/calculations/market_beta.py`**

```python
from app.batch.cache_manager import CompanyProfileCache

async def calculate_portfolio_provider_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    profile_cache: Optional[CompanyProfileCache] = None  # ✅ Cache parameter
) -> Dict[str, Any]:
    """Calculate portfolio beta using provider data"""

    positions = await get_active_positions(db, portfolio_id)

    total_market_value = Decimal('0')
    weighted_beta_sum = Decimal('0')
    positions_with_beta = 0

    for position in positions:
        # Get beta from CACHE or fallback to DB
        if profile_cache:
            # ✅ O(1) cache lookup
            beta = profile_cache.get_beta(position.symbol)
        else:
            # ❌ Fallback to DB query (for backward compatibility)
            stmt = select(CompanyProfile.beta).where(
                CompanyProfile.symbol == position.symbol
            )
            result = await db.execute(stmt)
            beta = result.scalar_one_or_none()

        if beta is None:
            continue

        # Calculate weighted beta
        market_value = position.quantity * position.current_price
        weighted_beta_sum += beta * market_value
        total_market_value += market_value
        positions_with_beta += 1

    # Portfolio beta = weighted average
    if total_market_value > 0:
        portfolio_beta = weighted_beta_sum / total_market_value
    else:
        portfolio_beta = Decimal('1.0')

    return {
        'portfolio_beta': portfolio_beta,
        'positions_with_beta': positions_with_beta,
        'total_positions': len(positions)
    }
```

**2. `backend/app/services/sector_tag_service.py`**

```python
from app.batch.cache_manager import CompanyProfileCache

async def restore_sector_tag_for_position(
    db: AsyncSession,
    user_id: UUID,
    position_id: UUID,
    profile_cache: Optional[CompanyProfileCache] = None  # ✅ Cache parameter
) -> Dict[str, Any]:
    """Restore sector tag using cached company profile"""

    position = await get_position(db, position_id)

    # Get sector from CACHE or fallback to DB
    if profile_cache:
        # ✅ O(1) cache lookup
        sector = profile_cache.get_sector(position.symbol)
    else:
        # ❌ Fallback to DB query
        stmt = select(CompanyProfile.sector).where(
            CompanyProfile.symbol == position.symbol
        )
        result = await db.execute(stmt)
        sector = result.scalar_one_or_none()

    # Rest of logic...
    return result
```

### Integration in Batch Orchestrator

```python
async def _run_sequence_with_session(
    self,
    db: AsyncSession,
    calculation_date: date,
    portfolio_ids: Optional[List[UUID]],
    price_cache: Optional[PriceCache] = None
) -> Dict[str, Any]:
    """Run phases with caching"""

    # Initialize company profile cache (do once per batch run)
    if not hasattr(self, '_profile_cache'):
        all_symbols = await self._collect_all_symbols(db, portfolio_ids)
        self._profile_cache = CompanyProfileCache()
        await self._profile_cache.load(db, all_symbols)
        logger.info(f"[CACHE] Loaded {self._profile_cache.stats()['total_profiles']} company profiles")

    # ... run phases, passing caches to calculation functions ...
```

---

## Stage 4 Implementation

### Overview
Cache previous portfolio snapshots to eliminate 720+ queries during equity rollforward.

### New Class in `cache_manager.py`

```python
class SnapshotCache:
    """
    In-memory cache for portfolio snapshots.

    Optimizes equity rollforward by eliminating repeated queries
    for previous snapshots.
    """

    def __init__(self):
        self._cache: Dict[Tuple[UUID, date], PortfolioSnapshot] = {}
        self._latest_cache: Dict[UUID, PortfolioSnapshot] = {}

    async def load_latest_snapshots(
        self,
        db: AsyncSession,
        portfolio_ids: List[UUID],
        before_date: date
    ) -> int:
        """
        Load the most recent snapshot for each portfolio before a date.

        Args:
            db: Database session
            portfolio_ids: List of portfolio IDs
            before_date: Get snapshots before this date

        Returns:
            Number of snapshots loaded
        """
        logger.info(f"[CACHE] Bulk loading latest snapshots for {len(portfolio_ids)} portfolios before {before_date}")

        loaded_count = 0

        # Use window function to get latest snapshot per portfolio
        # This is ONE query instead of N queries
        from sqlalchemy import func, and_

        # Subquery to get max date per portfolio
        subq = (
            select(
                PortfolioSnapshot.portfolio_id,
                func.max(PortfolioSnapshot.snapshot_date).label('max_date')
            )
            .where(
                and_(
                    PortfolioSnapshot.portfolio_id.in_(portfolio_ids),
                    PortfolioSnapshot.snapshot_date < before_date
                )
            )
            .group_by(PortfolioSnapshot.portfolio_id)
            .subquery()
        )

        # Join to get full snapshot records
        stmt = (
            select(PortfolioSnapshot)
            .join(
                subq,
                and_(
                    PortfolioSnapshot.portfolio_id == subq.c.portfolio_id,
                    PortfolioSnapshot.snapshot_date == subq.c.max_date
                )
            )
        )

        result = await db.execute(stmt)

        for snapshot in result.scalars():
            # Cache by portfolio_id AND date
            cache_key = (snapshot.portfolio_id, snapshot.snapshot_date)
            self._cache[cache_key] = snapshot

            # Also cache as "latest" for this portfolio
            self._latest_cache[snapshot.portfolio_id] = snapshot

            loaded_count += 1

        logger.info(f"[CACHE] Loaded {loaded_count} latest snapshots")
        return loaded_count

    def get_latest(self, portfolio_id: UUID) -> Optional[PortfolioSnapshot]:
        """Get most recent snapshot for portfolio"""
        return self._latest_cache.get(portfolio_id)

    def get_equity(self, portfolio_id: UUID) -> Decimal:
        """Get equity from latest snapshot, or 0 if not found"""
        snapshot = self.get_latest(portfolio_id)
        return snapshot.equity_balance if snapshot else Decimal('0')

    def stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'total_snapshots': len(self._cache),
            'portfolios_cached': len(self._latest_cache)
        }
```

### Modified File: `backend/app/batch/pnl_calculator.py`

```python
async def calculate_all_portfolios_pnl(
    self,
    calculation_date: date,
    db: AsyncSession,
    portfolio_ids: Optional[List[UUID]] = None,
    price_cache: Optional[PriceCache] = None,
    snapshot_cache: Optional[SnapshotCache] = None  # ✅ New parameter
) -> Dict[str, Any]:
    """Calculate P&L with snapshot caching"""

    # Initialize snapshot cache if not provided
    if snapshot_cache is None:
        snapshot_cache = SnapshotCache()
        await snapshot_cache.load_latest_snapshots(db, portfolio_ids, calculation_date)

    # ... rest of calculation ...

    for portfolio_id in portfolio_ids:
        # Get previous equity from CACHE instead of DB query
        previous_equity = snapshot_cache.get_equity(portfolio_id)

        # Calculate P&L...
```

---

## Stage 5 Implementation

### Overview
Factor ETF prices are already covered by Stage 1 price cache - minimal additional work.

### Integration

Simply ensure factor symbols are included in the symbol universe:

```python
# In _collect_all_symbols() method
FACTOR_SYMBOLS = {
    'SPY',   # S&P 500
    'TLT',   # Long-term Treasury
    'IEF',   # Intermediate Treasury
    'SHY',   # Short-term Treasury
    'HYG',   # High Yield
    'LQD',   # Investment Grade
    'VTV',   # Value
    'VUG',   # Growth
    'MTUM',  # Momentum
    'QUAL',  # Quality
    'USMV',  # Low Volatility
}

all_symbols.update(FACTOR_SYMBOLS)
```

No additional cache needed - these symbols are automatically included in the price cache!

---

## Migration & Rollout Plan

### Week 1: Stage 1 Implementation
**Days 1-2**: Build `cache_manager.py` with `PriceCache` class
**Days 3-4**: Modify `pnl_calculator.py` to use cache
**Day 5**: Testing and validation

### Week 2: Stage 2 + Stage 4 Implementation
**Days 1-2**: Add multi-day price caching to `PriceCache`
**Days 3-4**: Build `SnapshotCache` class
**Day 5**: Integration and testing

### Week 3: Stage 3 Implementation + Production Testing
**Days 1-2**: Build `CompanyProfileCache` class
**Days 3-4**: Modify calculation functions to accept cache
**Day 5**: Full integration testing

### Week 4: Production Deployment & Monitoring
**Days 1-2**: Deploy to staging environment
**Days 3-4**: Run full 120-day backfill test
**Day 5**: Production deployment

---

## Monitoring & Validation

### Cache Hit Rate Metrics

Add logging to track cache effectiveness:

```python
# Log cache stats after each batch run
logger.info(f"[CACHE STATS] Price cache: {price_cache.stats()}")
logger.info(f"[CACHE STATS] Profile cache: {profile_cache.stats()}")
logger.info(f"[CACHE STATS] Snapshot cache: {snapshot_cache.stats()}")

# Calculate hit rates
total_lookups = positions_with_prices + positions_missing_prices
hit_rate = (positions_with_prices / total_lookups * 100) if total_lookups > 0 else 0
logger.info(f"[CACHE EFFICIENCY] Hit rate: {hit_rate:.1f}%")
```

### Performance Benchmarks

Track time spent in each phase:

```python
import time

start_time = time.time()

# ... bulk load cache ...
cache_load_time = time.time() - start_time
logger.info(f"[PERFORMANCE] Cache loading took {cache_load_time:.2f}s")

# ... process portfolios ...
processing_time = time.time() - start_time - cache_load_time
logger.info(f"[PERFORMANCE] Portfolio processing took {processing_time:.2f}s")

total_time = time.time() - start_time
logger.info(f"[PERFORMANCE] Total batch time: {total_time:.2f}s")
logger.info(f"[PERFORMANCE] Cache overhead: {(cache_load_time/total_time)*100:.1f}%")
```

---

## Risks & Mitigations

### Risk 1: Memory Overhead

**Risk**: Loading all prices into memory could consume significant RAM

**Calculation**:
- 3,000 symbols × 120 days × 8 bytes per Decimal = ~2.8 MB
- 10,000 portfolios × 1 snapshot × 500 bytes = ~5 MB
- **Total**: < 10 MB (negligible)

**Mitigation**: Not a concern for current scale. At 100K+ symbols, implement LRU cache eviction.

---

### Risk 2: Stale Cache Data

**Risk**: Cache might contain stale data if database is updated during batch run

**Mitigation**:
- Batch processing is read-heavy, writes only happen at end
- Clear caches between batch runs
- Add cache TTL if needed for long-running batches

---

### Risk 3: Cache Miss Handling

**Risk**: What if cached data is missing?

**Mitigation**:
- Always provide fallback to database query
- Log cache misses for monitoring
- Pre-validate cache completeness before processing

---

## Success Criteria

### Stage 1 Success Metrics
- ✅ Single-day batch time reduced by 50%+
- ✅ Database query count reduced by 90%+
- ✅ Cache hit rate > 95%

### Stage 2 Success Metrics
- ✅ Multi-day backfill time reduced by 5x+
- ✅ No degradation in data quality
- ✅ Memory usage < 50 MB for 120-day cache

### Overall Success
- ✅ 120-day backfill for 6 portfolios: < 1 hour (from 6-8 hours)
- ✅ Daily production batch for 1000 portfolios: < 5 minutes (from 30-40 minutes)
- ✅ System scales to 10,000 portfolios without architectural changes

---

## Next Steps

1. **Review this plan** and approve implementation approach
2. **Test current batch** to establish baseline metrics
3. **Implement Stage 1** (single-day price cache) - highest ROI
4. **Measure improvement** and validate cache hit rates
5. **Implement Stages 2-4** based on production needs
6. **Document learnings** and update this plan

---

## Appendix: Alternative Approaches Considered

### Option A: Redis External Cache
**Pros**: Shared across multiple workers, persistent
**Cons**: Network latency, added complexity, requires Redis infrastructure
**Decision**: In-memory cache is simpler and faster for batch processing

### Option B: Database Materialized Views
**Pros**: Database-native, automatically updated
**Cons**: Slower than in-memory, doesn't eliminate queries
**Decision**: In-memory cache provides better performance

### Option C: Pre-computed Daily Snapshots
**Pros**: Zero computation during batch
**Cons**: Requires background job to maintain, storage overhead
**Decision**: May implement later for API endpoints, not batch processing

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Next Review**: After Stage 1 implementation
