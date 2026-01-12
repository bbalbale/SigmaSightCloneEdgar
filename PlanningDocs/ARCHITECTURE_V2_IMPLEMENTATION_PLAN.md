# Architecture V2 Implementation Plan
## Decoupled Symbol-Portfolio Processing for 10,000+ Users

**Created**: 2026-01-10
**Author**: Claude Code Analysis
**Status**: Planning

---

## Executive Summary

This plan redesigns the batch processing architecture to decouple **symbol-level data maintenance** from **portfolio-level analytics**. The current architecture ties these together, causing a 10x slowdown (30 min vs 3 min) when portfolios are out of sync due to the "minimum watermark" strategy.

**Goal**: Symbol data updates run once daily regardless of user count. Portfolio analytics become fast aggregations of pre-computed data.

---

## Part 1: Current State Analysis

### 1.1 Current Factor Calculation Types

**OLS Regressions (2):**
| Factor | Window | ETF/Index | Location |
|--------|--------|-----------|----------|
| Market Beta | 90 days | SPY | `market_beta.py` |
| IR Beta | 90 days | TLT | `interest_rate_beta.py` |

**Ridge Regression Factors (6):**
| Factor | ETF | Constants File Reference |
|--------|-----|--------------------------|
| Value | VTV | `FACTOR_ETFS["Value"]` |
| Growth | VUG | `FACTOR_ETFS["Growth"]` |
| Momentum | MTUM | `FACTOR_ETFS["Momentum"]` |
| Quality | QUAL | `FACTOR_ETFS["Quality"]` |
| Size | IWM | `FACTOR_ETFS["Size"]` |
| Low Volatility | USMV | `FACTOR_ETFS["Low Volatility"]` |

Window: 90 days (`REGRESSION_WINDOW_DAYS`), Alpha: 1.0

**Spread Factors (4):**
| Factor | Long ETF | Short ETF | Interpretation |
|--------|----------|-----------|----------------|
| Growth-Value Spread | VUG | VTV | Growth tilt vs Value |
| Momentum Spread | MTUM | SPY | Momentum tilt vs Market |
| Size Spread | IWM | SPY | Small cap tilt vs Market |
| Quality Spread | QUAL | SPY | Quality tilt vs Market |

Window: 180 days (`SPREAD_REGRESSION_WINDOW_DAYS`)

### 1.2 Current Batch Phases

```
Phase 0:   Company Profile Sync (beta, sector, industry)
Phase 1:   Market Data Collection (1-year lookback)
Phase 1.5: Symbol Factor Calculation (ridge + spread) ← ALREADY EXISTS
Phase 1.75: Symbol Metrics Calculation (returns, valuations)
Phase 2:   Fundamental Data Collection
Phase 3:   P&L Calculation & Snapshots
Phase 4:   Position Market Value Updates
Phase 5:   Sector Tag Restoration
Phase 6:   Risk Analytics (portfolio aggregation)
```

### 1.3 Current Tables (Symbol-Level)

**Already implemented:**
- `symbol_universe` - Master symbol list
- `symbol_factor_exposures` - Per-symbol factor betas (ridge + spread)
- `symbol_daily_metrics` - Denormalized dashboard data

**Current architecture insight:**
Phase 1.5 (`symbol_factors.py`) already calculates at symbol level. The problem is **WHEN** it runs - it's triggered by portfolio watermarks, not independently.

### 1.4 Root Cause of Performance Issue

**Current watermark calculation** (in `_get_last_batch_run_date`):
```python
# MIN of per-portfolio MAX snapshot dates
subquery = select(
    PortfolioSnapshot.portfolio_id,
    func.max(PortfolioSnapshot.snapshot_date).label('max_date')
).group_by(PortfolioSnapshot.portfolio_id).subquery()
query = select(func.min(subquery.c.max_date))
```

This means: If ANY portfolio is behind (e.g., new user from Dec 15), the ENTIRE batch processes from that date, even for symbols already computed.

---

## Part 2: Target Architecture

### 2.1 Core Principle

**Symbol Processing**: Time-driven (daily cron)
**Portfolio Analytics**: Event-driven (on-demand with cache)

```
┌─────────────────────────────────────────────────────────────────┐
│               SYMBOL LAYER (Global, Time-Driven)                │
│                                                                  │
│   Daily Cron (9 PM ET) - Runs ONCE regardless of user count     │
│   ├── Update prices for ALL tracked symbols                     │
│   ├── Calculate Market Beta for ALL symbols                     │
│   ├── Calculate IR Beta for ALL symbols                         │
│   ├── Calculate Ridge factors for ALL symbols                   │
│   └── Calculate Spread factors for ALL symbols                  │
│                                                                  │
│   Tables: symbol_universe, symbol_prices_daily,                 │
│           symbol_factor_exposures, symbol_daily_metrics         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ READ ONLY
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│             PORTFOLIO LAYER (Per-User, Event-Driven)            │
│                                                                  │
│   On Portfolio Change (position add/remove/update):             │
│   └── Invalidate portfolio cache                                │
│                                                                  │
│   On Analytics Request:                                         │
│   ├── Check cache (keyed by positions hash)                     │
│   ├── If miss: Lookup symbol betas, aggregate by weight         │
│   └── Cache result                                               │
│                                                                  │
│   Tables: portfolios, positions, portfolio_analytics_cache      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 New Symbol Processing Pipeline

**Symbol Daily Batch** (completely independent of portfolios):

```
STEP 1: Get all symbols in symbol_universe WHERE is_active = true
        (~5,000-10,000 symbols)

STEP 2: Batch fetch today's prices from YFinance
        (bulk API call, ~2 min)

STEP 3: Update symbol_prices_daily table
        (batch insert, ~30 sec)

STEP 4: For each symbol (parallelized, 10 concurrent tasks*):
        a. Load 90 days of returns
        b. Calculate Market Beta (OLS vs SPY)
        c. Calculate IR Beta (OLS vs TLT)
        d. Calculate Ridge factors (6 factors)
        e. Load 180 days of returns
        f. Calculate Spread factors (4 factors)
        g. UPSERT into symbol_factor_exposures
        (~8-12 min total with Railway constraints)

STEP 5: Update symbol_daily_metrics (denormalized view)
        (~1 min)

TOTAL: ~12-15 minutes, FIXED regardless of user count

* See Part 12: Railway Deployment Constraints for concurrency limits
```

### 2.3 New Portfolio Analytics Flow

**On Portfolio Analytics Request:**

```python
async def get_portfolio_factor_exposures(portfolio_id, calculation_date):
    # STEP 1: Check cache
    cache_key = f"{portfolio_id}:{hash(positions)}"
    if cached := await cache.get(cache_key):
        return cached  # <100ms

    # STEP 2: Load positions with weights
    positions = await get_positions(portfolio_id)
    symbols = [p.symbol for p in positions]
    weights = {p.symbol: p.market_value / portfolio_equity}

    # STEP 3: Bulk lookup pre-computed symbol betas
    symbol_betas = await db.execute(
        select(SymbolFactorExposure)
        .where(
            SymbolFactorExposure.symbol.in_(symbols),
            SymbolFactorExposure.calculation_date == latest_date
        )
    )  # Single query, ~20ms

    # STEP 4: Aggregate by weight
    portfolio_betas = {}
    for factor in ALL_FACTORS:
        portfolio_betas[factor] = sum(
            weights[s] * symbol_betas[s][factor]
            for s in symbols if s in symbol_betas
        )

    # STEP 5: Cache and return
    await cache.set(cache_key, portfolio_betas, ttl=86400)
    return portfolio_betas  # Total: ~50-100ms
```

### 2.4 New Symbol Onboarding Flow

**When user adds position with unknown symbol:**

```python
async def handle_new_position(position):
    symbol = position.symbol

    # Check if symbol is tracked
    if not await symbol_exists_in_universe(symbol):
        # Queue async onboarding job
        await queue.enqueue(
            "onboard_symbol",
            symbol=symbol,
            priority="high"
        )
        # Return immediately - don't block user
        return {"status": "pending", "message": "Symbol data loading..."}

    # Symbol already tracked - immediate success
    return {"status": "ready"}
```

**Symbol Onboarding Job:**

```python
async def onboard_symbol(symbol: str):
    # STEP 1: Add to symbol_universe (status=pending)
    await add_to_universe(symbol, status="pending")

    # STEP 2: Fetch 1 year of historical prices
    prices = await yfinance.get_history(symbol, period="1y")
    await bulk_insert_prices(symbol, prices)

    # STEP 3: Calculate all factor betas
    await calculate_market_beta(symbol)
    await calculate_ir_beta(symbol)
    await calculate_ridge_factors(symbol)
    await calculate_spread_factors(symbol)

    # STEP 4: Update status
    await update_universe_status(symbol, status="active")

    # STEP 5: Invalidate any cached portfolio analytics
    await invalidate_caches_for_symbol(symbol)
```

---

## Part 3: Database Schema Changes

### 3.1 New Tables

**`symbol_prices_daily`** - Dedicated symbol price history:

```sql
CREATE TABLE symbol_prices_daily (
    symbol VARCHAR(20) NOT NULL,
    price_date DATE NOT NULL,
    open_price DECIMAL(12, 4),
    high_price DECIMAL(12, 4),
    low_price DECIMAL(12, 4),
    close_price DECIMAL(12, 4) NOT NULL,
    adj_close_price DECIMAL(12, 4),
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (symbol, price_date),
    FOREIGN KEY (symbol) REFERENCES symbol_universe(symbol)
);

CREATE INDEX idx_symbol_prices_date ON symbol_prices_daily(price_date);
CREATE INDEX idx_symbol_prices_symbol ON symbol_prices_daily(symbol);
```

**`portfolio_analytics_cache`** - Cached portfolio computations:

```sql
CREATE TABLE portfolio_analytics_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    cache_key VARCHAR(255) NOT NULL,  -- hash of positions
    cache_type VARCHAR(50) NOT NULL,  -- 'factor_exposures', 'stress_test', etc.
    cached_data JSONB NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (portfolio_id, cache_type, cache_key)
);

CREATE INDEX idx_cache_portfolio ON portfolio_analytics_cache(portfolio_id);
CREATE INDEX idx_cache_valid ON portfolio_analytics_cache(valid_until);
```

**`symbol_onboarding_queue`** - ~~Async job queue~~ **NOW IN-MEMORY** (no database table):

> **Updated Decision**: Symbol onboarding uses an in-memory queue instead of a database table because:
> - Jobs are transient (complete in seconds, then stale)
> - Single Railway instance (no multi-worker coordination needed)
> - If server restarts, user can simply retry (rare edge case)
> - Simpler implementation, no migration needed
>
> See `07-SYMBOL-ONBOARDING.md` for the in-memory `SymbolOnboardingQueue` class.

### 3.2 Schema Modifications

**`symbol_universe`** - ~~Add status tracking~~ **NO CHANGES NEEDED**:

> **Updated Decision**: Instead of adding columns, we query existing tables for freshness:
> - `last_price_date` → Query `market_data_cache` for max date per symbol
> - `last_factor_date` → Query `symbol_factor_exposures` for max calculation_date
>
> See `03-DATABASE-SCHEMA.md` for query patterns.

**`symbol_factor_exposures`** - Already exists, add Market Beta and IR Beta:

```sql
-- Ensure factor_definitions includes these factors:
INSERT INTO factor_definitions (name, description, factor_type, is_active) VALUES
('Symbol Market Beta', 'Symbol-level 90-day market beta vs SPY', 'style', true),
('Symbol IR Beta', 'Symbol-level 90-day interest rate beta vs TLT', 'macro', true)
ON CONFLICT (name) DO NOTHING;
```

---

## Part 4: Code Changes

### 4.1 New Files to Create

```
backend/app/batch/
├── symbol_batch_runner.py       # NEW: Symbol-only daily batch
├── symbol_onboarding_worker.py  # NEW: Async symbol onboarding
├── symbol_onboarding_tracker.py # NEW: Concurrent job tracking (see 4.1.1)
└── portfolio_analytics_cache.py # NEW: Cache management

backend/app/services/
├── symbol_price_service.py     # NEW: Price management
└── portfolio_cache_service.py  # NEW: Portfolio cache operations

backend/app/api/v1/
└── onboarding_status.py        # MODIFY: Add symbol status endpoint
```

#### 4.1.1 Symbol Onboarding Job Tracker

The current `batch_run_tracker` is a singleton that tracks ONE batch at a time. In the new
architecture, we may have:
- Daily symbol batch (cron) running
- Multiple symbol onboarding jobs (async) running concurrently

Add a separate tracker for async symbol onboarding jobs:

**`backend/app/batch/symbol_onboarding_tracker.py`:**

```python
"""
Symbol Onboarding Tracker - Track multiple concurrent symbol onboarding jobs.

Unlike batch_run_tracker (singleton for one batch), this tracks many
concurrent async jobs for new symbol processing.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from app.core.datetime_utils import utc_now


# How long to retain completed job status (seconds)
JOB_COMPLETED_TTL_SECONDS = 120


@dataclass
class SymbolOnboardingJob:
    """Status of a single symbol onboarding job."""
    symbol: str
    status: str  # "pending", "processing", "completed", "failed"
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    phases_completed: List[str] = field(default_factory=list)


class SymbolOnboardingTracker:
    """
    Track multiple concurrent symbol onboarding jobs.

    This is separate from batch_run_tracker to allow:
    - Daily symbol batch running (tracked by batch_run_tracker)
    - Multiple async symbol onboarding jobs running concurrently
    """

    def __init__(self):
        self._jobs: Dict[str, SymbolOnboardingJob] = {}

    def start_job(self, symbol: str) -> None:
        """Start tracking a new symbol onboarding job."""
        self._cleanup_old_completed()
        self._jobs[symbol] = SymbolOnboardingJob(
            symbol=symbol,
            status="processing",
            started_at=utc_now()
        )

    def update_job(self, symbol: str, phase_completed: str) -> None:
        """Mark a phase as completed for a job."""
        if symbol in self._jobs:
            self._jobs[symbol].phases_completed.append(phase_completed)

    def complete_job(self, symbol: str, success: bool, error: Optional[str] = None) -> None:
        """Mark a job as completed or failed."""
        if symbol in self._jobs:
            self._jobs[symbol].status = "completed" if success else "failed"
            self._jobs[symbol].completed_at = utc_now()
            if error:
                self._jobs[symbol].error_message = error

    def get_pending_symbols(self, symbols: List[str]) -> List[str]:
        """Get symbols from list that are still being processed."""
        return [
            s for s in symbols
            if s in self._jobs and self._jobs[s].status == "processing"
        ]

    def get_job_status(self, symbol: str) -> Optional[Dict]:
        """Get status of a specific job."""
        self._cleanup_old_completed()
        if symbol not in self._jobs:
            return None

        job = self._jobs[symbol]
        return {
            "symbol": job.symbol,
            "status": job.status,
            "started_at": job.started_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "phases_completed": job.phases_completed,
            "error_message": job.error_message
        }

    def _cleanup_old_completed(self) -> None:
        """Remove completed jobs older than TTL."""
        now = utc_now()
        expired = [
            symbol for symbol, job in self._jobs.items()
            if job.completed_at and
            (now - job.completed_at).total_seconds() > JOB_COMPLETED_TTL_SECONDS
        ]
        for symbol in expired:
            del self._jobs[symbol]


# Global singleton instance
symbol_onboarding_tracker = SymbolOnboardingTracker()
```

### 4.2 Key Code: Symbol Batch Runner

**`backend/app/batch/symbol_batch_runner.py`:**

```python
"""
Symbol Batch Runner - Daily symbol-level data maintenance.

This is COMPLETELY INDEPENDENT of portfolio processing.
Runs once daily, updates all symbols in the universe.

Time complexity: O(symbols) - fixed cost regardless of user count
"""

class SymbolBatchRunner:
    """
    Daily batch for symbol-level data.

    Does NOT use portfolio watermarks.
    Does NOT depend on any portfolio state.
    """

    async def run_daily_symbol_batch(
        self,
        target_date: date = None,
        symbols: Optional[List[str]] = None  # Override for testing
    ) -> Dict[str, Any]:
        """
        Main entry point for daily symbol batch.

        Args:
            target_date: Date to process (default: today)
            symbols: Optional symbol override (default: all active)
        """
        target_date = target_date or date.today()

        # STEP 1: Get all active symbols
        if symbols is None:
            symbols = await self._get_active_symbols()

        logger.info(f"Processing {len(symbols)} symbols for {target_date}")

        results = {
            'target_date': target_date.isoformat(),
            'symbols_total': len(symbols),
            'phases': {}
        }

        # STEP 2: Fetch and store prices (single day)
        price_result = await self._update_daily_prices(symbols, target_date)
        results['phases']['prices'] = price_result

        # STEP 3: Calculate Market Beta for all symbols
        market_beta_result = await self._calculate_symbol_market_betas(
            symbols, target_date
        )
        results['phases']['market_beta'] = market_beta_result

        # STEP 4: Calculate IR Beta for all symbols
        ir_beta_result = await self._calculate_symbol_ir_betas(
            symbols, target_date
        )
        results['phases']['ir_beta'] = ir_beta_result

        # STEP 5: Calculate Ridge factors (uses existing symbol_factors.py)
        ridge_result = await calculate_universe_factors(
            calculation_date=target_date,
            calculate_ridge=True,
            calculate_spread=False,
            symbols=symbols
        )
        results['phases']['ridge_factors'] = ridge_result

        # STEP 6: Calculate Spread factors
        spread_result = await calculate_universe_factors(
            calculation_date=target_date,
            calculate_ridge=False,
            calculate_spread=True,
            symbols=symbols
        )
        results['phases']['spread_factors'] = spread_result

        # STEP 7: Update symbol_daily_metrics
        metrics_result = await self._update_symbol_metrics(symbols, target_date)
        results['phases']['metrics'] = metrics_result

        # STEP 8: Invalidate all portfolio caches
        await self._invalidate_all_portfolio_caches()

        return results

    async def _calculate_symbol_market_betas(
        self,
        symbols: List[str],
        calculation_date: date
    ) -> Dict[str, Any]:
        """
        Calculate Market Beta for all symbols using OLS regression.

        Reuses logic from market_beta.py but at symbol level.
        """
        from app.calculations.market_beta import (
            calculate_single_symbol_market_beta
        )

        # Fetch SPY returns once
        spy_returns = await self._get_returns(['SPY'], calculation_date, window=90)

        success_count = 0
        fail_count = 0

        # Process in parallel batches (Railway limit: 10 concurrent)
        for batch in self._batch_symbols(symbols, batch_size=10):
            tasks = [
                self._calc_and_store_market_beta(
                    symbol, calculation_date, spy_returns
                )
                for symbol in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception) or not result.get('success'):
                    fail_count += 1
                else:
                    success_count += 1

        return {
            'success': success_count,
            'failed': fail_count,
            'total': len(symbols)
        }
```

#### 4.2.1 Phase Tracking Integration (Phase 7.x Compatibility)

The Phase 7.1-7.4 tracking infrastructure (`batch_run_tracker`) should be **reused** for
the new Symbol Batch Runner. This provides admin visibility into daily symbol processing.

**Update `symbol_batch_runner.py` to use existing tracking:**

```python
from app.batch.batch_run_tracker import batch_run_tracker, CurrentBatchRun
from app.core.datetime_utils import utc_now

class SymbolBatchRunner:

    async def run_daily_symbol_batch(self, target_date: date = None, ...):
        target_date = target_date or date.today()

        # Initialize batch tracking (reuse Phase 7.x infrastructure)
        batch_run_tracker.start(CurrentBatchRun(
            batch_run_id=f"symbol_batch_{target_date.isoformat()}",
            started_at=utc_now(),
            triggered_by="cron"
        ))

        try:
            symbols = await self._get_active_symbols()

            # Phase 1: Price Collection
            batch_run_tracker.start_phase(
                phase_id="prices",
                phase_name="Daily Price Collection",
                total=len(symbols),
                unit="symbols"
            )
            price_result = await self._update_daily_prices(symbols, target_date)
            batch_run_tracker.complete_phase(
                "prices",
                success=True,
                summary=f"{price_result['updated']} symbols updated"
            )

            # Phase 2: Market Beta
            batch_run_tracker.start_phase(
                phase_id="market_beta",
                phase_name="Market Beta Calculation",
                total=len(symbols),
                unit="symbols"
            )
            market_beta_result = await self._calculate_symbol_market_betas(symbols, target_date)
            batch_run_tracker.complete_phase(
                "market_beta",
                success=True,
                summary=f"{market_beta_result['success']}/{len(symbols)} calculated"
            )

            # Phase 3: IR Beta
            batch_run_tracker.start_phase(
                phase_id="ir_beta",
                phase_name="Interest Rate Beta Calculation",
                total=len(symbols),
                unit="symbols"
            )
            ir_beta_result = await self._calculate_symbol_ir_betas(symbols, target_date)
            batch_run_tracker.complete_phase("ir_beta", success=True, ...)

            # Phase 4: Ridge Factors
            batch_run_tracker.start_phase(
                phase_id="ridge_factors",
                phase_name="Ridge Factor Analysis",
                total=len(symbols),
                unit="symbols"
            )
            ridge_result = await calculate_universe_factors(...)
            batch_run_tracker.complete_phase("ridge_factors", success=True, ...)

            # Phase 5: Spread Factors
            batch_run_tracker.start_phase(
                phase_id="spread_factors",
                phase_name="Spread Factor Analysis",
                total=len(symbols),
                unit="symbols"
            )
            spread_result = await calculate_universe_factors(...)
            batch_run_tracker.complete_phase("spread_factors", success=True, ...)

            # Phase 6: Cache Invalidation
            batch_run_tracker.start_phase(
                phase_id="cache_invalidation",
                phase_name="Portfolio Cache Refresh",
                total=1,
                unit="operation"
            )
            await self._invalidate_all_portfolio_caches()
            batch_run_tracker.complete_phase("cache_invalidation", success=True)

            batch_run_tracker.complete(success=True)
            return results

        except Exception as e:
            batch_run_tracker.complete(success=False)
            raise
```

**Key Difference from Portfolio Batch:**
- Symbol batch uses **6 phases** (prices, market_beta, ir_beta, ridge, spread, cache)
- Portfolio batch used **9 phases** (phase_0, phase_1, phase_1_5, phase_1_75, etc.)
- Phase names are more descriptive ("Market Beta Calculation" vs "Phase 1.5")

### 4.3 Key Code: Portfolio Cache Service

**`backend/app/services/portfolio_cache_service.py`:**

```python
"""
Portfolio Analytics Cache Service

Manages caching for portfolio-level computations.
Cache invalidation triggers:
1. Daily symbol batch completes (global invalidation)
2. User modifies positions (per-portfolio invalidation)
3. TTL expiration (24 hours default)
"""

class PortfolioCacheService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.default_ttl = timedelta(hours=24)

    async def get_cached_factors(
        self,
        portfolio_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached factor exposures for portfolio.

        Returns None if cache miss or expired.
        """
        cache_key = await self._get_positions_hash(portfolio_id)

        result = await self.db.execute(
            select(PortfolioAnalyticsCache)
            .where(
                and_(
                    PortfolioAnalyticsCache.portfolio_id == portfolio_id,
                    PortfolioAnalyticsCache.cache_type == 'factor_exposures',
                    PortfolioAnalyticsCache.cache_key == cache_key,
                    PortfolioAnalyticsCache.valid_until > datetime.now(timezone.utc)
                )
            )
        )
        cached = result.scalar_one_or_none()

        if cached:
            logger.debug(f"Cache HIT for portfolio {portfolio_id}")
            return cached.cached_data

        logger.debug(f"Cache MISS for portfolio {portfolio_id}")
        return None

    async def cache_factors(
        self,
        portfolio_id: UUID,
        factor_data: Dict[str, Any],
        ttl: timedelta = None
    ) -> None:
        """
        Cache factor exposures for portfolio.
        """
        ttl = ttl or self.default_ttl
        cache_key = await self._get_positions_hash(portfolio_id)
        valid_until = datetime.now(timezone.utc) + ttl

        # Upsert pattern
        stmt = insert(PortfolioAnalyticsCache).values(
            portfolio_id=portfolio_id,
            cache_key=cache_key,
            cache_type='factor_exposures',
            cached_data=factor_data,
            valid_until=valid_until
        ).on_conflict_do_update(
            index_elements=['portfolio_id', 'cache_type', 'cache_key'],
            set_={'cached_data': factor_data, 'valid_until': valid_until}
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def invalidate_portfolio(self, portfolio_id: UUID) -> None:
        """
        Invalidate all caches for a portfolio.
        Called when positions change.
        """
        await self.db.execute(
            delete(PortfolioAnalyticsCache)
            .where(PortfolioAnalyticsCache.portfolio_id == portfolio_id)
        )
        await self.db.commit()
        logger.info(f"Invalidated cache for portfolio {portfolio_id}")

    async def invalidate_all(self) -> None:
        """
        Invalidate all portfolio caches.
        Called after daily symbol batch completes.
        """
        await self.db.execute(delete(PortfolioAnalyticsCache))
        await self.db.commit()
        logger.info("Invalidated all portfolio caches")

    async def _get_positions_hash(self, portfolio_id: UUID) -> str:
        """
        Generate hash of current positions for cache key.

        Hash includes: symbols, quantities, market_values
        Changes when positions are added/removed/modified.
        """
        positions = await self.db.execute(
            select(
                Position.symbol,
                Position.quantity,
                Position.market_value
            )
            .where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.exit_date.is_(None)
                )
            )
            .order_by(Position.symbol)
        )

        data = [(r.symbol, str(r.quantity), str(r.market_value))
                for r in positions.all()]
        return hashlib.sha256(str(data).encode()).hexdigest()[:16]
```

### 4.4 In-Memory Analytics Cache (Replaces PriceCache)

**Background**: The current `PriceCache` class creates a fresh cache per batch run. For V2's instant analytics, we need a **persistent in-memory cache** that survives between requests and is refreshed after the daily batch.

**Rename**: `app/cache/price_cache.py` → `app/cache/analytics_cache.py`

**Memory Footprint**:
| Data | Size | Notes |
|------|------|-------|
| Symbol factor betas | ~370 KB | 5,000 symbols × 8 factors × 8 bytes |
| Factor ETF returns | ~16 KB | 8 ETFs × 252 days × 8 bytes |
| Correlation matrix | ~1 KB | 8×8 pre-computed |
| Historical prices | ~50 MB | 5,000 symbols × 252 days × ~40 bytes |
| **Total** | **~50 MB** | Acceptable for Railway |

**`backend/app/cache/analytics_cache.py`:**

```python
"""
Analytics Cache - Persistent In-Memory Cache for Instant Analytics

Extends the former PriceCache to include all data needed for instant analytics:
- Historical prices (1 year)
- Symbol factor betas (from symbol_factor_exposures)
- Factor ETF returns (for correlation matrix)
- Pre-computed correlation matrix

Lifecycle:
1. Loaded at application startup
2. Refreshed after daily batch completes
3. Used by all analytics requests (zero DB reads)

Memory: ~50 MB for 5,000 symbols
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import UUID
import numpy as np

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache, SymbolFactorExposure
from app.constants.factors import FACTOR_ETFS

logger = get_logger(__name__)

# Factor ETFs for correlation matrix (8 factors)
CORRELATION_FACTORS = list(FACTOR_ETFS.values())  # SPY, QQQ, IWM, TLT, etc.


@dataclass
class SymbolFactors:
    """Factor betas for a single symbol."""
    symbol: str
    market_beta: float          # SPY (90-day OLS)
    ir_beta: float              # TLT (90-day OLS)
    value_beta: float           # VTV (ridge)
    growth_beta: float          # VUG (ridge)
    momentum_beta: float        # MTUM (ridge)
    quality_beta: float         # QUAL (ridge)
    size_beta: float            # IWM (ridge)
    low_vol_beta: float         # USMV (ridge)
    growth_value_spread: float  # VUG-VTV (spread)
    momentum_spread: float      # MTUM-SPY (spread)
    size_spread: float          # IWM-SPY (spread)
    quality_spread: float       # QUAL-SPY (spread)
    calculation_date: date


@dataclass
class PriceRecord:
    """Single price record for a symbol/date."""
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None


class AnalyticsCache:
    """
    Persistent in-memory cache for all analytics data.

    Usage:
        # At startup
        await analytics_cache.load_all()

        # After daily batch
        await analytics_cache.refresh_after_batch()

        # During request
        betas = analytics_cache.get_symbol_betas("AAPL")
        corr = analytics_cache.get_correlation_matrix()
    """

    def __init__(self):
        # Price data: symbol -> date -> PriceRecord
        self._prices: Dict[str, Dict[date, PriceRecord]] = {}

        # Symbol factor betas: symbol -> SymbolFactors
        self._symbol_betas: Dict[str, SymbolFactors] = {}

        # Factor ETF returns: symbol -> list of daily returns (252 days)
        self._factor_returns: Dict[str, List[float]] = {}

        # Pre-computed correlation matrix: factor -> factor -> correlation
        self._correlation_matrix: Dict[str, Dict[str, float]] = {}

        # Metadata
        self._last_refresh: Optional[datetime] = None
        self._symbols_loaded: int = 0
        self._prices_loaded: int = 0
        self._is_loaded: bool = False

    # =========================================================================
    # LOADING METHODS
    # =========================================================================

    async def load_all(self, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Load all data needed for instant analytics.
        Called at startup and after daily batch.

        Returns:
            Summary of loaded data
        """
        logger.info("AnalyticsCache: Starting full load...")

        close_session = False
        if db is None:
            db = AsyncSessionLocal()
            close_session = True

        try:
            # Load in parallel where possible
            prices_result = await self._load_prices(db)
            betas_result = await self._load_symbol_betas(db)
            returns_result = await self._load_factor_returns(db)

            # Compute correlation matrix from returns
            self._compute_correlation_matrix()

            self._last_refresh = datetime.utcnow()
            self._is_loaded = True

            summary = {
                'success': True,
                'last_refresh': self._last_refresh.isoformat(),
                'symbols_with_prices': len(self._prices),
                'symbols_with_betas': len(self._symbol_betas),
                'factor_returns_loaded': len(self._factor_returns),
                'correlation_matrix_size': f"{len(self._correlation_matrix)}x{len(self._correlation_matrix)}",
                'total_prices': self._prices_loaded,
            }

            logger.info(
                f"AnalyticsCache: Loaded {len(self._symbol_betas)} symbol betas, "
                f"{self._prices_loaded} prices, {len(self._correlation_matrix)}x{len(self._correlation_matrix)} correlation matrix"
            )

            return summary

        finally:
            if close_session:
                await db.close()

    async def refresh_after_batch(self, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Refresh cache after daily batch completes.
        Called from batch_orchestrator at end of run_daily_batch_with_backfill().
        """
        logger.info("AnalyticsCache: Refreshing after daily batch...")
        return await self.load_all(db)

    async def _load_prices(self, db: AsyncSession) -> Dict[str, Any]:
        """Load 1 year of historical prices for all symbols."""
        from app.models.market_data import MarketDataCache

        end_date = date.today()
        start_date = end_date - timedelta(days=366)

        result = await db.execute(
            select(MarketDataCache)
            .where(MarketDataCache.date >= start_date)
            .order_by(MarketDataCache.symbol, MarketDataCache.date)
        )
        rows = result.scalars().all()

        self._prices.clear()
        self._prices_loaded = 0

        for row in rows:
            symbol = row.symbol.upper()
            if symbol not in self._prices:
                self._prices[symbol] = {}

            self._prices[symbol][row.date] = PriceRecord(
                open=float(row.open) if row.open else 0.0,
                high=float(row.high) if row.high else 0.0,
                low=float(row.low) if row.low else 0.0,
                close=float(row.close) if row.close else 0.0,
                volume=int(row.volume) if row.volume else 0,
                adjusted_close=float(row.adjusted_close) if row.adjusted_close else None,
            )
            self._prices_loaded += 1

        logger.debug(f"Loaded {self._prices_loaded} prices for {len(self._prices)} symbols")
        return {'prices_loaded': self._prices_loaded, 'symbols': len(self._prices)}

    async def _load_symbol_betas(self, db: AsyncSession) -> Dict[str, Any]:
        """Load all symbol factor betas from symbol_factor_exposures."""
        from app.models.market_data import SymbolFactorExposure

        # Get latest calculation date
        latest_date_result = await db.execute(
            select(SymbolFactorExposure.calculation_date)
            .order_by(SymbolFactorExposure.calculation_date.desc())
            .limit(1)
        )
        latest_date = latest_date_result.scalar_one_or_none()

        if not latest_date:
            logger.warning("No symbol factor exposures found in database")
            return {'symbols_loaded': 0}

        # Load all betas for latest date
        result = await db.execute(
            select(SymbolFactorExposure)
            .where(SymbolFactorExposure.calculation_date == latest_date)
        )
        rows = result.scalars().all()

        self._symbol_betas.clear()

        for row in rows:
            symbol = row.symbol.upper()

            # Extract betas from the row (adjust field names as needed)
            self._symbol_betas[symbol] = SymbolFactors(
                symbol=symbol,
                market_beta=float(row.market_beta or 0.0),
                ir_beta=float(row.ir_beta or 0.0),
                value_beta=float(row.value_beta or 0.0),
                growth_beta=float(row.growth_beta or 0.0),
                momentum_beta=float(row.momentum_beta or 0.0),
                quality_beta=float(row.quality_beta or 0.0),
                size_beta=float(row.size_beta or 0.0),
                low_vol_beta=float(row.low_vol_beta or 0.0),
                growth_value_spread=float(row.growth_value_spread or 0.0),
                momentum_spread=float(row.momentum_spread or 0.0),
                size_spread=float(row.size_spread or 0.0),
                quality_spread=float(row.quality_spread or 0.0),
                calculation_date=row.calculation_date,
            )

        self._symbols_loaded = len(self._symbol_betas)
        logger.debug(f"Loaded betas for {self._symbols_loaded} symbols (date={latest_date})")
        return {'symbols_loaded': self._symbols_loaded, 'calculation_date': latest_date}

    async def _load_factor_returns(self, db: AsyncSession) -> Dict[str, Any]:
        """Load 252 days of returns for factor ETFs (for correlation matrix)."""
        from app.models.market_data import MarketDataCache

        end_date = date.today()
        start_date = end_date - timedelta(days=300)  # Extra buffer for 252 trading days

        self._factor_returns.clear()

        for factor_symbol in CORRELATION_FACTORS:
            result = await db.execute(
                select(MarketDataCache.date, MarketDataCache.close)
                .where(
                    MarketDataCache.symbol == factor_symbol,
                    MarketDataCache.date >= start_date
                )
                .order_by(MarketDataCache.date)
            )
            rows = result.all()

            if len(rows) < 2:
                logger.warning(f"Insufficient data for factor {factor_symbol}")
                continue

            # Calculate daily returns
            prices = [float(row.close) for row in rows if row.close]
            returns = []
            for i in range(1, len(prices)):
                if prices[i-1] > 0:
                    daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                    returns.append(daily_return)

            # Keep last 252 trading days
            self._factor_returns[factor_symbol] = returns[-252:] if len(returns) > 252 else returns

        logger.debug(f"Loaded returns for {len(self._factor_returns)} factor ETFs")
        return {'factors_loaded': len(self._factor_returns)}

    def _compute_correlation_matrix(self) -> None:
        """Compute correlation matrix from factor returns."""
        import numpy as np

        self._correlation_matrix.clear()

        factors = list(self._factor_returns.keys())
        if len(factors) < 2:
            logger.warning("Insufficient factors for correlation matrix")
            return

        # Find minimum length across all factors
        min_len = min(len(self._factor_returns[f]) for f in factors)
        if min_len < 30:
            logger.warning(f"Insufficient data for correlation ({min_len} days)")
            return

        # Build correlation matrix
        for f1 in factors:
            self._correlation_matrix[f1] = {}
            returns1 = np.array(self._factor_returns[f1][-min_len:])

            for f2 in factors:
                if f1 == f2:
                    self._correlation_matrix[f1][f2] = 1.0
                else:
                    returns2 = np.array(self._factor_returns[f2][-min_len:])
                    corr = np.corrcoef(returns1, returns2)[0, 1]
                    # Bound correlation to [-0.95, 0.95] to avoid extreme values
                    corr = max(-0.95, min(0.95, corr))
                    self._correlation_matrix[f1][f2] = float(corr)

        logger.debug(f"Computed {len(factors)}x{len(factors)} correlation matrix")

    # =========================================================================
    # LOOKUP METHODS (Used by analytics at request time)
    # =========================================================================

    def get_symbol_betas(self, symbol: str) -> Optional[SymbolFactors]:
        """Get factor betas for a symbol. Returns None if not found."""
        return self._symbol_betas.get(symbol.upper())

    def get_all_symbol_betas(self) -> Dict[str, SymbolFactors]:
        """Get all cached symbol betas."""
        return self._symbol_betas

    def get_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """Get pre-computed factor correlation matrix."""
        return self._correlation_matrix

    def get_factor_returns(self, factor: str) -> List[float]:
        """Get daily returns for a factor ETF."""
        return self._factor_returns.get(factor, [])

    def get_price(self, symbol: str, price_date: date) -> Optional[PriceRecord]:
        """Get price for a symbol on a specific date."""
        symbol_prices = self._prices.get(symbol.upper())
        if symbol_prices:
            return symbol_prices.get(price_date)
        return None

    def get_prices_range(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, PriceRecord]:
        """Get prices for a symbol within a date range."""
        symbol_prices = self._prices.get(symbol.upper(), {})
        return {
            d: p for d, p in symbol_prices.items()
            if start_date <= d <= end_date
        }

    def get_returns(self, symbol: str, days: int = 90) -> List[float]:
        """Calculate daily returns for a symbol over N days."""
        symbol_prices = self._prices.get(symbol.upper(), {})
        if not symbol_prices:
            return []

        sorted_dates = sorted(symbol_prices.keys(), reverse=True)[:days+1]
        sorted_dates.reverse()

        returns = []
        for i in range(1, len(sorted_dates)):
            prev_price = symbol_prices[sorted_dates[i-1]].close
            curr_price = symbol_prices[sorted_dates[i]].close
            if prev_price > 0:
                returns.append((curr_price - prev_price) / prev_price)

        return returns

    # =========================================================================
    # STATUS METHODS
    # =========================================================================

    def is_loaded(self) -> bool:
        """Check if cache has been loaded."""
        return self._is_loaded

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'is_loaded': self._is_loaded,
            'last_refresh': self._last_refresh.isoformat() if self._last_refresh else None,
            'symbols_with_betas': len(self._symbol_betas),
            'symbols_with_prices': len(self._prices),
            'total_prices': self._prices_loaded,
            'factor_etfs_loaded': len(self._factor_returns),
            'correlation_matrix_size': len(self._correlation_matrix),
        }

    def has_symbol(self, symbol: str) -> bool:
        """Check if symbol has data in cache."""
        symbol_upper = symbol.upper()
        return symbol_upper in self._symbol_betas or symbol_upper in self._prices


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

# Global singleton - imported by other modules
analytics_cache = AnalyticsCache()
```

**Startup Integration** (`backend/app/main.py`):

```python
from contextlib import asynccontextmanager
from app.cache.analytics_cache import analytics_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load analytics cache
    logger.info("Loading analytics cache at startup...")
    try:
        result = await analytics_cache.load_all()
        logger.info(f"Analytics cache loaded: {result['symbols_with_betas']} symbols")
    except Exception as e:
        logger.error(f"Failed to load analytics cache: {e}")
        # Continue anyway - cache will be populated after first batch

    yield

    # Shutdown: Nothing to clean up (in-memory)
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)
```

**Batch Integration** (`backend/app/batch/batch_orchestrator.py`):

```python
from app.cache.analytics_cache import analytics_cache

async def run_daily_batch_with_backfill(...) -> Dict[str, Any]:
    # ... existing batch phases ...

    # At end of batch, refresh the persistent cache
    logger.info("Refreshing analytics cache after batch...")
    cache_result = await analytics_cache.refresh_after_batch()
    logger.info(f"Analytics cache refreshed: {cache_result}")

    return results
```

**Usage in Analytics** (`backend/app/calculations/stress_testing.py`):

```python
from app.cache.analytics_cache import analytics_cache

async def run_comprehensive_stress_test(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    ...
) -> Dict[str, Any]:
    # USE CACHED CORRELATION MATRIX (no DB query!)
    correlation_matrix = analytics_cache.get_correlation_matrix()

    if not correlation_matrix:
        # Fallback: compute from DB if cache not loaded
        correlation_data = await calculate_factor_correlation_matrix(db)
        correlation_matrix = correlation_data['correlation_matrix']

    # ... rest of stress test uses cached data ...
```

### 4.5 Modifications to Existing Code

**`batch_orchestrator.py`** - Use persistent AnalyticsCache:

```python
# BEFORE (current):
async def run_daily_batch_with_backfill(...):
    # Fresh cache created each run
    price_cache = PriceCache()
    await price_cache.load_date_range(db, symbols, start_date, end_date)
    # ... phases use price_cache ...
    # Cache discarded when function exits

# AFTER (new):
from app.cache.analytics_cache import analytics_cache

async def run_daily_batch_with_backfill(...):
    # Use persistent singleton (already loaded at startup)
    # Just refresh prices for this batch's date range
    await analytics_cache.load_prices(db, symbols, start_date, end_date)

    # ... phases use analytics_cache ...

    # At end: refresh all cached data (betas, returns, correlation)
    await analytics_cache.refresh_after_batch(db)
```

**`batch_orchestrator.py`** - Remove portfolio-driven symbol processing:

```python
# BEFORE (current):
async def run_daily_batch_with_backfill(...):
    # Watermark based on MIN of portfolio snapshot dates
    last_run_date = await self._get_last_batch_run_date(db, portfolio_ids)
    # Process all dates from watermark to today
    for calc_date in date_range:
        await self._run_phase_1_5(...)  # Symbol factors

# AFTER (new):
async def run_daily_batch_with_backfill(...):
    # Portfolio batch NO LONGER runs symbol calculations
    # It only aggregates pre-computed data
    for calc_date in date_range:
        # Phase 1.5 REMOVED - now in separate symbol_batch_runner
        await self._run_portfolio_analytics(...)
```

**`analytics_runner.py`** - Use cached symbol betas:

```python
# BEFORE (current):
async def _calculate_ridge_factors(...):
    # May trigger symbol-level calculations
    result = await get_portfolio_factor_exposures(...)

# AFTER (new):
async def _calculate_ridge_factors(...):
    # Check cache first
    cache_service = PortfolioCacheService(db)
    cached = await cache_service.get_cached_factors(portfolio_id)
    if cached:
        return {'success': True, 'method': 'cache', 'data': cached}

    # Lookup pre-computed symbol betas (no calculation)
    result = await get_portfolio_factor_exposures(...)

    # Cache for future requests
    await cache_service.cache_factors(portfolio_id, result)
    return result
```

---

## Part 5: Migration Strategy

### 5.1 Phase 1: Verify Schema (Week 1)

> **Updated**: V2 requires ZERO database migrations. All needed tables already exist.

1. ~~Create migration for new tables~~ **NOT NEEDED**:
   - ~~`symbol_prices_daily`~~ → Use existing `market_data_cache`
   - ~~`portfolio_analytics_cache`~~ → Use in-memory cache
   - ~~`symbol_onboarding_queue`~~ → Use in-memory queue

2. ~~Modify `symbol_universe` table~~ **NOT NEEDED**:
   - ~~Add columns~~ → Query existing tables instead

3. Add new factor definitions (if not present):
   - `Symbol Market Beta`
   - `Symbol IR Beta`

### 5.2 Phase 2: Symbol Batch Runner (Week 2)

1. Create `symbol_batch_runner.py` with:
   - `_update_daily_prices()` - Fetch and store daily prices
   - `_calculate_symbol_market_betas()` - OLS vs SPY
   - `_calculate_symbol_ir_betas()` - OLS vs TLT
   - Integrate existing `calculate_universe_factors()` for Ridge/Spread

2. Create Railway cron job for symbol batch:
   - Schedule: 9:00 PM ET daily (after market close)
   - Completely separate from portfolio batch

3. Test with subset of symbols

### 5.3 Phase 3: Portfolio Cache Service (Week 3)

1. Create `portfolio_cache_service.py`:
   - Cache lookup and storage
   - Position hash calculation
   - Invalidation methods

2. Modify position create/update/delete endpoints:
   - Call `invalidate_portfolio()` on changes

3. Test cache hit/miss scenarios

### 5.4 Phase 4: Integration (Week 4)

1. Modify `batch_orchestrator.py`:
   - Remove symbol calculation from portfolio batch
   - Portfolio batch now only handles: P&L, snapshots, analytics aggregation

2. Modify `analytics_runner.py`:
   - Add cache check before factor lookup
   - All factor calculations use pre-computed symbol data

3. Update API endpoints:
   - Factor endpoints read from cache or compute from symbol data
   - Stress test endpoints use cached factor exposures

### 5.5 Phase 5: Onboarding Flow - Backend (Week 5)

1. Create `symbol_onboarding_worker.py`:
   - Background job processor using in-memory queue
   - Symbol history fetch
   - Factor calculation for new symbols

2. Create in-memory `SymbolOnboardingQueue`:
   - Deduplication at queue time
   - Max queue depth (50)
   - Max concurrent processing (3)
   - No database table needed

3. Create API endpoint `/api/v1/symbols/{symbol}/status`:
   - Returns: `ready`, `pending`, `processing`, `error`
   - Reads from in-memory queue

4. Modify `onboarding.py` - `/create-portfolio` endpoint:
   - Check symbol universe
   - Create instant snapshot with known symbols
   - Queue unknown symbols (in-memory)
   - Return new response format: `{portfolio_id, status, pending_symbols, snapshot_date}`

5. Simplify `onboarding_status.py`:
   - Remove 9-phase tracking
   - Return simple `ready`/`partial` status

### 5.6 Phase 6: Onboarding Flow - Frontend (Week 5-6)

1. Update `usePortfolioUpload.ts`:
   - Remove `triggerCalculations()` call
   - Handle new response format with `status` field
   - Redirect directly to dashboard

2. Deprecate or repurpose `onboarding/progress/page.tsx`:
   - Option A: Remove entirely (all users go to dashboard)
   - Option B: Repurpose for symbol-only status (rare cases)

3. Replace `useOnboardingStatus.ts`:
   - Create new `useSymbolOnboardingStatus` hook
   - Simplified polling (5s interval)
   - Handle `ready`/`partial` status

4. Update `portfolioApi.ts`:
   - Update response types for `createPortfolio()`
   - Deprecate `triggerCalculations()` function

### 5.7 Phase 7: Cleanup (Week 6)

1. Remove deprecated code:
   - Portfolio-driven symbol processing
   - Old watermark calculation

2. Update documentation:
   - CLAUDE.md
   - API documentation
   - Batch processing docs

3. Performance testing:
   - Verify symbol batch <10 min
   - Verify portfolio analytics <100ms
   - Load test with simulated 10,000 users

---

## Part 6: Stress Testing Considerations

### 6.1 Current Stress Test Flow

Stress testing (`stress_testing.py`) requires:
1. Portfolio factor exposures (FactorExposure table)
2. Factor correlation matrix (computed from factor ETF returns)
3. Shocked factors applied with correlation propagation

### 6.2 Impact of New Architecture

**No changes needed to stress test logic** - it already reads from `FactorExposure` table.

What changes:
1. Factor exposures are populated faster (from cache or aggregation)
2. Stress tests can use cached portfolio betas

**Add to stress test flow:**
```python
async def run_comprehensive_stress_test(...):
    # Check if portfolio factors are cached
    cache_service = PortfolioCacheService(db)
    factors = await cache_service.get_cached_factors(portfolio_id)

    if not factors:
        # Compute factors (fast - symbol betas are pre-computed)
        factors = await get_portfolio_factor_exposures(...)
        await cache_service.cache_factors(portfolio_id, factors)

    # Run stress scenarios using cached factors
    ...
```

---

## Part 7: Performance Projections

### 7.1 Symbol Batch (Daily) - Railway Deployment

| Step | Current | New (Railway) | Notes |
|------|---------|---------------|-------|
| Market Data | Variable (portfolio-driven) | 2-3 min | Batch YFinance call |
| Market Beta | Per-portfolio | 3-4 min | 5,000 symbols, 10 concurrent |
| IR Beta | Per-portfolio | 3-4 min | 5,000 symbols, 10 concurrent |
| Ridge Factors | Per-portfolio | 3-4 min | Already optimized |
| Spread Factors | Per-portfolio | 3-4 min | Already optimized |
| Metrics | Per-portfolio | 1 min | Denormalized update |
| **TOTAL** | 30+ min | **~12-15 min** | **FIXED COST** |

**Note**: Performance projections adjusted for Railway constraints (10 concurrent tasks max).
See Part 12 for Railway-specific limits.

### 7.2 Portfolio Analytics (Per Request)

| Scenario | Current | New |
|----------|---------|-----|
| Cache Hit | N/A | <10ms |
| Cache Miss (aggregation) | N/A | 50-100ms |
| Full calculation | 3-30 min | N/A (eliminated) |

### 7.3 Scaling

| Users | Current Time | New Time (Railway) |
|-------|--------------|---------------------|
| 100 | 3-10 min | 12-15 min |
| 1,000 | 10-30 min | 12-15 min |
| 10,000 | Hours | 12-15 min |

**Key Insight**: Symbol batch time is now **O(symbols)** not **O(users × symbols)**.
With Railway constraints, batch takes slightly longer but scales infinitely with users.

---

## Part 8: Risk Assessment

### 8.1 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Symbol batch fails | Medium | High | Retry logic, alerting, fallback to previous day |
| Cache invalidation bug | Low | Medium | Position hash verification, TTL fallback |
| New symbol delay | Medium | Low | 30-60 sec acceptable, show "pending" status |
| Data inconsistency | Low | High | Transaction boundaries, audit logging |

### 8.2 Rollback Plan

1. Keep old batch orchestrator code (feature flagged)
2. Database migrations are additive (no destructive changes)
3. Can revert to portfolio-driven processing if needed

---

## Part 9: Success Criteria

1. **Symbol batch completes in <15 minutes** regardless of portfolio count
2. **Portfolio analytics respond in <100ms** (cache hit) or <500ms (cache miss)
3. **New symbol onboarding completes in <60 seconds**
4. **No regression in calculation accuracy** (validated against current system)
5. **System handles 10,000 concurrent portfolios** without degradation
6. **User onboarding completes in <5 seconds** (for known symbols)

---

## Part 10: User Onboarding Impact

This section details how the new architecture transforms the user onboarding experience from a 15-30 minute wait to near-instant portfolio analytics.

### 10.1 Current Onboarding Flow (SLOW)

**Current files involved:**
- `app/api/v1/onboarding.py` - Portfolio creation endpoint
- `app/api/v1/onboarding_status.py` - Progress polling (Phase 7.1)
- `app/services/batch_trigger_service.py` - Triggers full batch
- `app/batch/batch_orchestrator.py` - 9-phase processing

**Current flow:**
```
1. User uploads CSV via POST /api/v1/onboarding/create-portfolio
   ↓ (~2-3 sec)
2. Portfolio + positions created in database
   ↓
3. User triggers batch via POST /api/v1/portfolio/{id}/calculate
   ↓
4. batch_trigger_service calls batch_orchestrator.run_daily_batch_sequence()
   ↓
5. Watermark calculation determines start date (may go back weeks)
   ↓
6. FOR EACH DATE from watermark to today:
   - Phase 0: Company Profile Sync
   - Phase 1: Market Data Collection ← API calls for ALL symbols
   - Phase 1.5: Symbol Factor Calculation ← Regressions for ALL symbols
   - Phase 1.75: Symbol Metrics
   - Phase 2: Fundamentals
   - Phase 3: P&L/Snapshots
   - Phase 4: Position Market Values
   - Phase 5: Sector Tags
   - Phase 6: Risk Analytics
   ↓ (~15-30+ minutes)
7. User polls GET /api/v1/onboarding/status/{portfolio_id} every 2 sec
   ↓
8. Finally receives analytics
```

**Current user experience:**
- "Please wait 15-20 minutes while we process your portfolio..."
- Complex progress UI showing 9 phases
- High drop-off rate during wait

### 10.2 New Onboarding Flow (FAST)

**New flow:**
```
1. User uploads CSV via POST /api/v1/onboarding/create-portfolio
   ↓ (~2-3 sec)
2. Portfolio + positions created in database
   ↓ (<1 sec)
3. Check symbols against symbol_universe:
   ├── Known symbols (99% of cases): Already have factor betas ✓
   └── Unknown symbols: Queue async onboarding job
   ↓ (<1 sec)
4. Compute portfolio analytics IMMEDIATELY:
   - Lookup pre-computed symbol betas from symbol_factor_exposures
   - Aggregate by position weights
   - Cache result
   ↓ (<1 sec)
5. Return response with analytics ready
   ↓
   TOTAL: <5 seconds
```

**New user experience:**
- "Your portfolio is ready!" (immediate)
- Analytics displayed instantly
- Rare case (new symbols): "Loading data for NEWSTOCK... (30 sec)"

### 10.3 Onboarding Code Changes

#### 10.3.1 Modify `onboarding.py` - `/create-portfolio` endpoint

**Before (current):**
```python
@router.post("/create-portfolio", response_model=CreatePortfolioResponse)
async def create_portfolio(...):
    # Create portfolio with CSV import
    result = await onboarding_service.create_portfolio_with_csv(...)
    await db.commit()

    # Return - user must trigger batch separately
    return CreatePortfolioResponse(
        **result,
        message="Portfolio created! Use POST /api/v1/portfolio/{id}/calculate to run analytics.",
        next_step={
            "action": "calculate",
            "endpoint": f"/api/v1/portfolio/{result['portfolio_id']}/calculate"
        }
    )
```

**After (new):**
```python
@router.post("/create-portfolio", response_model=CreatePortfolioResponse)
async def create_portfolio(...):
    # Create portfolio with CSV import
    result = await onboarding_service.create_portfolio_with_csv(...)
    await db.commit()

    portfolio_id = UUID(result['portfolio_id'])

    # NEW: Check symbol readiness
    symbols = await get_portfolio_symbols(db, portfolio_id)
    pending_symbols = await check_symbols_pending(db, symbols)

    if pending_symbols:
        # Queue async jobs for unknown symbols
        for symbol in pending_symbols:
            await queue_symbol_onboarding(symbol, requested_by=current_user.id)

        # Compute partial analytics (known symbols only)
        await compute_and_cache_portfolio_analytics(db, portfolio_id, exclude=pending_symbols)

        return CreatePortfolioResponse(
            **result,
            status="partial",
            pending_symbols=pending_symbols,
            message=f"Portfolio created! Analytics ready for {len(symbols) - len(pending_symbols)}/{len(symbols)} positions. Loading {len(pending_symbols)} new symbols (30-60 sec)...",
            next_step={
                "action": "poll_status",
                "endpoint": f"/api/v1/onboarding/status/{result['portfolio_id']}"
            }
        )

    # All symbols ready - compute analytics immediately
    await compute_and_cache_portfolio_analytics(db, portfolio_id)

    return CreatePortfolioResponse(
        **result,
        status="ready",
        message="Portfolio created with full analytics!",
        next_step={
            "action": "view_dashboard",
            "endpoint": f"/dashboard/{result['portfolio_id']}"
        }
    )
```

#### 10.3.2 Simplify `onboarding_status.py`

**Before (current - Phase 7.1):**
- Tracks 9 batch phases with detailed progress
- Activity log for 15-30 min process
- Complex phase-by-phase status

**After (new):**
```python
class OnboardingStatusResponse(BaseModel):
    """Simplified onboarding status response"""
    portfolio_id: str
    status: str  # "ready", "pending", "error"
    analytics_available: bool
    pending_symbols: Optional[List[str]]
    estimated_seconds_remaining: Optional[int]
    message: str


@router.get("/status/{portfolio_id}")
async def get_onboarding_status(
    portfolio_id: str,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """
    Get portfolio onboarding status.

    In the new architecture, this is MUCH simpler:
    - Most portfolios: status="ready" immediately
    - Pending symbols: Simple countdown (30-60 sec max)

    No more 9-phase progress tracking needed.
    """
    # Verify ownership
    portfolio = await verify_portfolio_ownership(db, portfolio_id, current_user.id)

    # Check if any symbols are still pending
    pending = await get_pending_symbols_for_portfolio(db, portfolio_id)

    if not pending:
        return OnboardingStatusResponse(
            portfolio_id=portfolio_id,
            status="ready",
            analytics_available=True,
            pending_symbols=None,
            estimated_seconds_remaining=None,
            message="Your portfolio analytics are ready!"
        )

    # Calculate estimated time (30 sec per symbol)
    estimated_seconds = len(pending) * 30

    return OnboardingStatusResponse(
        portfolio_id=portfolio_id,
        status="pending",
        analytics_available=True,  # Partial analytics available
        pending_symbols=pending,
        estimated_seconds_remaining=estimated_seconds,
        message=f"Loading data for {len(pending)} new symbol(s)..."
    )
```

#### 10.3.3 Remove Batch Trigger from Onboarding

**Before (current) - `batch_trigger_service.py`:**
```python
# Called during onboarding to trigger full 9-phase batch
background_tasks.add_task(
    batch_orchestrator.run_daily_batch_sequence,
    calculation_date,
    [portfolio_id],
    db,
    None,  # run_sector_analysis
    None,  # price_cache
    force_onboarding
)
```

**After (new):**
```python
# NO BATCH TRIGGER NEEDED FOR ONBOARDING
# Symbol data is already current (from daily cron)
# Portfolio analytics are computed on-demand via cache service

# Only symbol onboarding jobs are queued (if needed)
if pending_symbols:
    for symbol in pending_symbols:
        await symbol_onboarding_queue.enqueue(symbol)
```

### 10.4 New Helper Functions

**`app/services/onboarding_helpers.py`:**

```python
"""
Onboarding helper functions for the new architecture.
"""

async def get_portfolio_symbols(db: AsyncSession, portfolio_id: UUID) -> List[str]:
    """Get all symbols in a portfolio."""
    result = await db.execute(
        select(Position.symbol)
        .where(
            Position.portfolio_id == portfolio_id,
            Position.exit_date.is_(None)
        )
        .distinct()
    )
    return [row[0] for row in result.all()]


async def check_symbols_pending(db: AsyncSession, symbols: List[str]) -> List[str]:
    """
    Check which symbols are not yet in the universe or still pending.

    Returns list of symbols that need onboarding.
    """
    result = await db.execute(
        select(SymbolUniverse.symbol)
        .where(
            SymbolUniverse.symbol.in_(symbols),
            SymbolUniverse.status == 'active'
        )
    )
    active_symbols = {row[0] for row in result.all()}

    return [s for s in symbols if s not in active_symbols]


async def queue_symbol_onboarding(
    symbol: str,
    requested_by: Optional[UUID] = None,
    priority: str = "high"
) -> None:
    """
    Queue a symbol for async onboarding.

    The symbol_onboarding_worker will:
    1. Fetch 1 year of historical prices
    2. Calculate all factor betas
    3. Add to symbol_universe as active
    """
    async with AsyncSessionLocal() as db:
        # Check if already queued
        existing = await db.execute(
            select(SymbolOnboardingQueue)
            .where(
                SymbolOnboardingQueue.symbol == symbol,
                SymbolOnboardingQueue.status.in_(['pending', 'processing'])
            )
        )
        if existing.scalar_one_or_none():
            return  # Already queued

        # Add to queue
        job = SymbolOnboardingQueue(
            symbol=symbol,
            status='pending',
            requested_by=requested_by,
            priority=priority
        )
        db.add(job)
        await db.commit()


async def get_pending_symbols_for_portfolio(
    db: AsyncSession,
    portfolio_id: str
) -> List[str]:
    """
    Get symbols in portfolio that are still pending onboarding.
    """
    portfolio_uuid = UUID(portfolio_id)

    # Get portfolio symbols
    symbols = await get_portfolio_symbols(db, portfolio_uuid)

    # Check which are pending
    return await check_symbols_pending(db, symbols)


async def compute_and_cache_portfolio_analytics(
    db: AsyncSession,
    portfolio_id: UUID,
    exclude: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Compute portfolio analytics from pre-computed symbol betas.

    This is FAST because symbol betas are already computed.
    Just lookup + aggregate + cache.

    Args:
        exclude: Symbols to exclude (still pending)
    """
    from app.services.portfolio_factor_service import get_portfolio_factor_exposures
    from app.services.portfolio_cache_service import PortfolioCacheService

    cache_service = PortfolioCacheService(db)

    # Get factor exposures (lookup + aggregate)
    result = await get_portfolio_factor_exposures(
        db=db,
        portfolio_id=portfolio_id,
        calculation_date=date.today(),
        use_delta_adjusted=False,
        include_ridge=True,
        include_spread=True
    )

    # Cache for future requests
    await cache_service.cache_factors(portfolio_id, result)

    return result
```

### 10.5 Timeline Comparison

| Step | Current | New |
|------|---------|-----|
| CSV upload + validation | 2-3 sec | 2-3 sec |
| Portfolio + positions created | 1-2 sec | 1-2 sec |
| **Symbol readiness check** | N/A | <1 sec |
| **Batch processing** | 15-30 min | **0 sec** (data already exists) |
| **Analytics computation** | Part of batch | <1 sec (aggregation) |
| **User sees results** | **15-30+ min** | **<5 sec** |

### 10.6 Edge Cases

#### Case 1: All Symbols Known (99% of users)
```
User uploads: AAPL, MSFT, GOOGL, SPY, QQQ
↓
All in symbol_universe with status='active'
↓
Analytics computed immediately (<1 sec)
↓
Response: { status: "ready", message: "Your portfolio is ready!" }
```

#### Case 2: One Unknown Symbol
```
User uploads: AAPL, MSFT, NEWSTOCK
↓
AAPL, MSFT in universe ✓
NEWSTOCK not in universe
↓
Queue NEWSTOCK for onboarding
Compute partial analytics (AAPL, MSFT)
↓
Response: {
  status: "partial",
  pending_symbols: ["NEWSTOCK"],
  message: "Analytics ready for 2/3 positions. Loading NEWSTOCK (30 sec)..."
}
↓
Background: symbol_onboarding_worker processes NEWSTOCK
↓
30-60 sec later: Full analytics available
```

#### Case 3: All Unknown Symbols (rare - new asset class)
```
User uploads: CRYPTO1, CRYPTO2, CRYPTO3
↓
None in symbol_universe
↓
Queue all 3 for onboarding
↓
Response: {
  status: "pending",
  pending_symbols: ["CRYPTO1", "CRYPTO2", "CRYPTO3"],
  message: "Loading data for 3 new symbols (1-2 min)..."
}
↓
Background: symbol_onboarding_worker processes all 3
↓
1-2 min later: Full analytics available
```

### 10.7 Frontend Changes (REQUIRED)

The frontend must be updated to handle instant onboarding. This is a **breaking change** from the current 15-20 minute batch flow.

#### 10.7.1 `frontend/src/hooks/usePortfolioUpload.ts`

**Current behavior**: Calls `createPortfolio()` then `triggerCalculations()` then redirects to progress page.

**Required changes**:
1. Remove call to `triggerCalculations()` - no longer needed
2. Handle new response format with `status` field
3. Redirect directly to dashboard instead of progress page

```typescript
// BEFORE (V1)
const handleUpload = async (file: File) => {
    const portfolio = await createPortfolio(file);
    await triggerCalculations(portfolio.id);  // DELETE THIS
    router.push(`/onboarding/progress?id=${portfolio.id}`);  // CHANGE THIS
};

// AFTER (V2)
const handleUpload = async (file: File) => {
    const response = await createPortfolio(file);

    if (response.status === 'ready') {
        router.push(`/portfolio/${response.portfolio_id}`);
    } else if (response.status === 'partial') {
        toast.info(`${response.pending_symbols.length} symbols loading...`);
        router.push(`/portfolio/${response.portfolio_id}`);
    }
};
```

#### 10.7.2 `frontend/app/onboarding/progress/page.tsx`

**Current behavior**: Shows batch phase progress (Phase 1, 2, 3...) with progress bars.

**Required changes**: Either deprecate entirely OR repurpose for symbol-only onboarding.

**Option A: Deprecate**
- Remove the page entirely
- All users go directly to dashboard

**Option B: Repurpose for symbol onboarding only** (Recommended)
- Only accessible when `response.status === 'partial'`
- Only track symbol onboarding progress (not full batch)
- Simplified UI: "Loading data for XYZ, ABC..." with checkmarks
- Allow user to proceed to dashboard at any time

```typescript
// Repurposed progress page
function OnboardingProgress() {
    const { pendingSymbols, isComplete } = useSymbolOnboardingStatus(portfolioId);

    if (isComplete) {
        router.push(`/portfolio/${portfolioId}`);
        return null;
    }

    return (
        <div>
            <h2>Loading market data...</h2>
            {pendingSymbols.map(symbol => (
                <SymbolStatusRow key={symbol} symbol={symbol} />
            ))}
            <p>You can start using your portfolio now.</p>
            <Button onClick={() => router.push(`/portfolio/${portfolioId}`)}>
                Go to Dashboard
            </Button>
        </div>
    );
}
```

#### 10.7.3 `frontend/src/hooks/useOnboardingStatus.ts`

**Current behavior**: Polls `/api/v1/onboarding/status/{id}` for batch phase progress.

**Required changes**:
1. Replace with symbol-specific status polling
2. Handle new simplified response format
3. Shorter polling interval (5s instead of 2s - symbols process faster)

```typescript
// BEFORE (V1) - Polls for batch phases
const { phase, progress, isComplete } = useOnboardingStatus(portfolioId);

// AFTER (V2) - Polls for symbol status only
export function useSymbolOnboardingStatus(portfolioId: string) {
    return useQuery({
        queryKey: ['symbolOnboarding', portfolioId],
        queryFn: () => fetchOnboardingStatus(portfolioId),
        refetchInterval: (data) => data?.status === 'ready' ? false : 5000,
    });
}
```

#### 10.7.4 `frontend/src/services/portfolioApi.ts` (or similar)

**Required changes**:
1. Update `createPortfolio()` return type to include new fields
2. Remove or deprecate `triggerCalculations()` function

```typescript
// Updated response type
interface CreatePortfolioResponse {
    portfolio_id: string;
    status: 'ready' | 'partial';
    pending_symbols?: string[];
    snapshot_date: string;
}

// Remove or deprecate
// async function triggerCalculations(portfolioId: string) { ... }
```

### 10.8 Files to Modify for Onboarding

**Backend Files:**

| File | Change Type | Description |
|------|-------------|-------------|
| `app/api/v1/onboarding.py` | MAJOR | Add symbol check, remove batch trigger, compute analytics inline |
| `app/api/v1/onboarding_status.py` | SIMPLIFY | Remove 9-phase tracking, simple pending symbol status |
| `app/services/batch_trigger_service.py` | MINOR | Remove onboarding-specific batch logic |
| `app/services/onboarding_service.py` | MINOR | Add symbol check integration |
| `app/services/onboarding_helpers.py` | NEW | Helper functions for new flow |

**Frontend Files:**

| File | Change Type | Description |
|------|-------------|-------------|
| `frontend/src/hooks/usePortfolioUpload.ts` | MAJOR | Skip triggerCalculations, handle new response, direct redirect |
| `frontend/app/onboarding/progress/page.tsx` | DEPRECATE/REPURPOSE | Remove batch UI, optionally repurpose for symbol status |
| `frontend/src/hooks/useOnboardingStatus.ts` | REPLACE | New hook for symbol-specific polling |
| `frontend/src/services/portfolioApi.ts` | MINOR | Update response types, deprecate triggerCalculations |

### 10.9 Deprecations

The following will be deprecated/simplified:

1. **Phase 7.1-7.4 Progress Tracking FOR ONBOARDING** - No longer needed
   - `batch_run_tracker.get_onboarding_status()` - simplified to simple status check
   - Activity log for onboarding - removed (onboarding is now <5 seconds)
   - Phase progress UI for onboarding - removed
   - 9-phase tracking in onboarding flow - removed
   - 60-second completed status TTL - reduce to 10 seconds for onboarding
   - **NOTE**: Phase 7.x tracking is PRESERVED for daily symbol batch (see Part 11)

2. **Batch Trigger for Onboarding**
   - `batch_trigger_service.trigger_batch(force_onboarding=True)` - removed
   - `run_daily_batch_sequence()` for single portfolio - removed
   - `run_portfolio_onboarding_backfill()` - removed (no longer triggers batch)

3. **Complex Status Polling**
   - 9-phase status response - simplified to ready/pending/error
   - 2-second polling for 15+ minutes - reduced to 5-second polling for <60 sec
   - `PhaseProgress` dataclass for onboarding - not used (still used for symbol batch)

4. **Onboarding-Specific Batch Code**
   - `is_single_portfolio_mode` logic in batch_orchestrator - removed
   - `source="onboarding"` tracking - removed
   - `scoped_only` mode for onboarding - removed (still used for admin operations)

---

## Part 11: Phase 7.x Compatibility Analysis

**Context**: 17 commits to main (January 9-10, 2026) implemented Phase 7.3 and 7.4
enhancements for batch tracking. This section analyzes compatibility with Architecture V2.

### 11.1 Phase 7.x Features Implemented

**Phase 7.1**: Activity Logging
- `ActivityLogEntry` dataclass for real-time status updates
- `add_activity()`, `get_activity_log()` methods
- Max 50 entries to prevent memory growth

**Phase 7.1 Fix**: Completed Run Status Retention
- `CompletedRunStatus` dataclass with 60-second TTL
- `_completed_runs` dictionary to retain terminal status
- Prevents frontend from seeing "not_found" after batch completes

**Phase 7.4**: 9-Phase Individual Tracking
- `PhaseProgress` dataclass with current/total/unit metrics
- `start_phase()`, `update_phase_progress()`, `complete_phase()` methods
- Phases: phase_1, phase_1_5, phase_1_75, phase_2_6 (combined)

### 11.2 Compatibility Matrix

| Phase 7.x Feature | Onboarding | Symbol Batch | Portfolio Batch |
|-------------------|------------|--------------|-----------------|
| Activity Log | ❌ DEPRECATED | ✅ REUSE | ✅ KEEP |
| Phase Progress | ❌ DEPRECATED | ✅ REUSE (6 phases) | ✅ KEEP |
| Completed Status TTL | ⚠️ REDUCE (10s) | ✅ KEEP (60s) | ✅ KEEP |
| 9-Phase Tracking | ❌ DEPRECATED | ⚠️ REPLACE (6 phases) | ✅ KEEP |
| `get_onboarding_status()` | ⚠️ SIMPLIFY | N/A | N/A |

### 11.3 What Gets Reused

**For Daily Symbol Batch** (REUSE Phase 7.x infrastructure):

```python
# batch_run_tracker can track the symbol batch with different phase names
batch_run_tracker.start_phase("prices", "Daily Price Collection", len(symbols), "symbols")
batch_run_tracker.start_phase("market_beta", "Market Beta Calculation", len(symbols), "symbols")
batch_run_tracker.start_phase("ir_beta", "IR Beta Calculation", len(symbols), "symbols")
batch_run_tracker.start_phase("ridge_factors", "Ridge Factor Analysis", len(symbols), "symbols")
batch_run_tracker.start_phase("spread_factors", "Spread Factor Analysis", len(symbols), "symbols")
batch_run_tracker.start_phase("cache_invalidation", "Portfolio Cache Refresh", 1, "operation")
```

**For Admin Dashboard** (KEEP existing features):
- Admin can monitor daily symbol batch progress
- Activity log shows what's happening
- Phase progress shows completion status

### 11.4 What Gets Deprecated (Onboarding Only)

**Current onboarding flow** (15-30 minutes):
```python
# Phase 7.x was designed for this long-running process
batch_run_tracker.set_portfolio_id(portfolio_id)
batch_run_tracker.start_phase("phase_1", "Market Data Collection", ...)
# ... 8 more phases over 15-30 minutes ...
batch_run_tracker.complete(success=True)
```

**New onboarding flow** (< 5 seconds):
```python
# No batch tracking needed - operation is instant
symbols = await get_portfolio_symbols(db, portfolio_id)
pending = await check_symbols_pending(db, symbols)

if not pending:
    # Instant success - no tracking needed
    await compute_and_cache_portfolio_analytics(db, portfolio_id)
    return {"status": "ready"}

# Only track pending symbols (rare case)
for symbol in pending:
    symbol_onboarding_tracker.start_job(symbol)  # Use NEW tracker
```

### 11.5 Concurrent Job Tracking

**Current limitation**: `batch_run_tracker` tracks ONE batch at a time.

**New requirement**: We may have running concurrently:
- Daily symbol batch (tracked by `batch_run_tracker`)
- Multiple symbol onboarding jobs (tracked by `symbol_onboarding_tracker`)

**Solution**: Add separate `symbol_onboarding_tracker` (see Section 4.1.1).

### 11.6 Migration Notes

1. **Preserve batch_run_tracker** - Don't modify the core tracking infrastructure
2. **Simplify onboarding_status.py** - Remove Phase 7.x complexity for onboarding
3. **Add symbol_onboarding_tracker.py** - New tracker for concurrent symbol jobs
4. **Update admin dashboard** - Show symbol batch phases instead of portfolio phases

### 11.7 Code Preservation Table

| File | Action | Notes |
|------|--------|-------|
| `batch_run_tracker.py` | KEEP AS-IS | Core infrastructure reused for symbol batch |
| `batch_orchestrator.py` | KEEP Phase 7.x code | Still used for admin-triggered portfolio batches |
| `onboarding.py` | REMOVE Phase 7.x calls | Onboarding no longer triggers batch |
| `onboarding_status.py` | SIMPLIFY | Remove 9-phase tracking, keep simple status |
| `symbol_batch_runner.py` | ADD Phase 7.x calls | Reuse existing tracking for symbol batch |

---

## Part 12: Railway Deployment Constraints

**Context**: SigmaSight runs on Railway with resource limits that affect concurrency design.

### 12.1 Railway Resource Limits

| Resource | Hobby Plan | Pro Plan | Our Limit |
|----------|------------|----------|-----------|
| vCPU | 8 | 32 | 8 (Hobby) |
| RAM | 8 GB | 32 GB | 8 GB |
| DB Connections | ~20-50 | ~100 | 20-30 |
| Dyno timeout | 30 min | 30 min | 30 min |

### 12.2 External API Rate Limits

| Service | Rate Limit | Practical Limit |
|---------|------------|-----------------|
| YFinance | ~2,000 req/hour | ~33 req/min |
| Polygon | 5 req/min (free) | Use sparingly |
| FMP | 250 req/day (free) | Backup only |

### 12.3 Concurrency Design

**CRITICAL**: Original plan specified 50 concurrent workers. This is **not feasible** on Railway.

**Recommended Limits**:

| Operation | Concurrent Tasks | Reason |
|-----------|------------------|--------|
| Symbol beta calculation | 10 | DB connection pool + memory |
| Price fetching | 5 | YFinance rate limits |
| Symbol onboarding | 3 | Rare, but may run during batch |

**Code Pattern**:

```python
# ✅ CORRECT - Railway-safe concurrency
RAILWAY_BATCH_SIZE = 10  # Conservative limit

for batch in self._batch_symbols(symbols, batch_size=RAILWAY_BATCH_SIZE):
    tasks = [self._calculate_beta(s) for s in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Rate limiting for YFinance
    await asyncio.sleep(0.5)  # 2 batches/sec max = 20 symbols/sec

# ❌ WRONG - Will exhaust resources
for batch in self._batch_symbols(symbols, batch_size=50):  # Too many!
    tasks = [self._calculate_beta(s) for s in batch]
```

### 12.4 Database Connection Pooling

**SQLAlchemy AsyncSession Configuration**:

```python
# app/database.py - Railway-optimized settings
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,           # Conservative pool
    max_overflow=5,         # Allow 15 total connections
    pool_timeout=30,        # Wait for connection
    pool_recycle=1800,      # Recycle every 30 min
)
```

**Connection Budget**:
- Pool size: 10
- Max overflow: 5
- Total max: 15 connections
- Reserve for API requests: 5
- **Available for batch: 10 concurrent**

### 12.5 Memory Considerations

| Component | Est. Memory | Notes |
|-----------|-------------|-------|
| FastAPI + workers | 500 MB | Base overhead |
| 10 concurrent calculations | 200 MB | ~20 MB each |
| Price data cache (90 days) | 500 MB | ~100 bytes × 5,000 symbols × 90 days |
| Symbol universe | 100 MB | Metadata for 10,000 symbols |
| **Total Estimated** | **1.3 GB** | Well under 8 GB limit |

### 12.6 Timeout Handling

Railway has a 30-minute request timeout. The symbol batch runs as a background task,
but we still need to handle timeouts gracefully:

```python
# Symbol batch with timeout handling
async def run_daily_symbol_batch(self, target_date: date):
    try:
        async with asyncio.timeout(1500):  # 25 min timeout (safety margin)
            return await self._run_batch_phases(target_date)
    except asyncio.TimeoutError:
        logger.error("Symbol batch timed out - will resume on next run")
        batch_run_tracker.complete(success=False)
        raise
```

### 12.7 Recommended Settings Summary

```python
# backend/app/core/railway_config.py (NEW FILE)

# Concurrency limits for Railway deployment
RAILWAY_BATCH_SIZE = 10                # Concurrent symbol calculations
RAILWAY_PRICE_FETCH_BATCH = 5          # Concurrent YFinance calls
RAILWAY_ONBOARDING_CONCURRENT = 3      # Concurrent new symbol jobs

# Rate limiting
YFINANCE_RATE_LIMIT_DELAY = 0.5        # Seconds between batches
BATCH_TIMEOUT_SECONDS = 1500           # 25 min safety margin

# Database pooling
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 5

# Cache settings
PORTFOLIO_CACHE_TTL_HOURS = 24
SYMBOL_DATA_RETENTION_DAYS = 400       # 1 year + buffer
```

### 12.8 Scaling Beyond Railway

If we outgrow Railway constraints, consider:

1. **Railway Pro Plan**: 32 vCPU, 32 GB RAM, ~100 DB connections
   - Increase batch_size to 30-40
   - Still use rate limiting for external APIs

2. **Dedicated Workers**: Separate Railway service for batch processing
   - Main service handles API requests
   - Worker service runs daily batch

3. **Redis Queue**: Add Redis for job queuing
   - Celery or RQ for distributed processing
   - Better failure recovery

4. **AWS/GCP Migration**: For 50,000+ users
   - ECS/GKE for auto-scaling
   - RDS/Cloud SQL for managed Postgres
   - True horizontal scaling

---

## Part 13: Railway Cron Refactoring

**Context**: The Railway cron job and scheduler configuration must be updated to use
the new symbol-driven architecture instead of the portfolio-driven approach.

### 13.1 Current Cron Architecture (Portfolio-Driven)

**File: `scripts/automation/railway_daily_batch.py`**
```python
# Current: Calls batch_orchestrator which processes per-portfolio
await batch_orchestrator.run_daily_batch_with_backfill()
```

**File: `app/batch/scheduler_config.py`**
```python
# Current schedule (all times ET):
# 4:00 PM - Daily batch (per-portfolio processing)
# 6:00 PM - Daily correlations (per-portfolio)
# 7:00 PM - Company profile sync
# 7:30 PM - Market data verification
# 8:00 PM - Feedback learning
# 8:30 PM - Admin metrics batch
```

**Problem**: Daily batch scales with O(portfolios × symbols) - 30+ minutes for 3 portfolios.

### 13.2 New Cron Architecture (Symbol-Driven)

**New Flow**:
```
Railway Cron (9:00 PM ET - after market close + settlement)
    ↓
railway_daily_batch.py (REFACTORED)
    ↓
symbol_batch_runner.run_daily_symbol_batch()
    ↓
Process ALL symbols ONCE:
  - Phase 1: Daily price collection (2-3 min)
  - Phase 2: Market Beta calculation (3-4 min)
  - Phase 3: IR Beta calculation (3-4 min)
  - Phase 4: Ridge factor analysis (3-4 min)
  - Phase 5: Spread factor analysis (3-4 min)
  - Phase 6: Portfolio cache invalidation (1 min)
    ↓
~12-15 minutes FIXED (regardless of user count)
```

**Key Change**: Portfolio analytics are NO LONGER scheduled. They're computed on-demand
with caching when users request them.

### 13.3 New Schedule Configuration

| Time (ET) | Job | Status | Notes |
|-----------|-----|--------|-------|
| 9:00 PM | Symbol batch | **NEW** | Replaces portfolio batch |
| ~~6:00 PM~~ | ~~Daily correlations~~ | **REMOVE** | Now part of symbol batch |
| 9:30 PM | Company profile sync | **KEEP** | Still needed |
| 10:00 PM | Market data verification | **KEEP** | Still needed |
| 10:30 PM | Feedback learning | **KEEP** | Still needed |
| 11:00 PM | Admin metrics batch | **KEEP** | Still needed |

**Why 9:00 PM?**
- Market closes at 4:00 PM ET
- After-hours trading ends ~8:00 PM ET
- 9:00 PM ensures all daily data is settled
- Completes by 9:15 PM, leaving time for other jobs

### 13.4 Refactored `railway_daily_batch.py`

```python
#!/usr/bin/env python3
"""
Railway Daily Symbol Batch - Architecture V2

Runs after market close to update ALL symbol data.
Portfolio analytics are computed on-demand (not scheduled).

Usage:
  uv run python scripts/automation/railway_daily_batch.py
"""

import os
import asyncio
import sys
import datetime

# Fix Railway DATABASE_URL format
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)

sys.path.insert(0, '/app')
sys.path.insert(0, '.')

from app.core.logging import get_logger
from app.batch.symbol_batch_runner import symbol_batch_runner  # NEW
from app.database import AsyncSessionLocal
from app.db.seed_factors import seed_factors

logger = get_logger(__name__)


async def ensure_factor_definitions():
    """Ensure factor definitions exist before running batch."""
    logger.info("Verifying factor definitions...")
    async with AsyncSessionLocal() as db:
        await seed_factors(db)
        await db.commit()
    logger.info("✅ Factor definitions verified/seeded")


async def main():
    """Main entry point for daily symbol batch job."""
    job_start = datetime.datetime.now()

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     SIGMASIGHT DAILY SYMBOL BATCH - ARCHITECTURE V2          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"Timestamp: {job_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        await ensure_factor_definitions()

        # NEW: Run symbol batch (decoupled from portfolios)
        # This updates ALL symbols in the universe, regardless of portfolios
        logger.info("Starting symbol batch runner...")
        results = await symbol_batch_runner.run_daily_symbol_batch()

        job_end = datetime.datetime.now()
        total_duration = (job_end - job_start).total_seconds()

        print("=" * 60)
        print("DAILY SYMBOL BATCH COMPLETE")
        print("=" * 60)
        print(f"Symbols Processed: {results.get('symbols_total', 0)}")
        print(f"Total Runtime: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        print(f"Phases: {list(results.get('phases', {}).keys())}")
        print("=" * 60)

        if results.get('success', True):
            print("✅ Symbol batch completed successfully")
            sys.exit(0)
        else:
            print(f"⚠️ Symbol batch completed with issues")
            sys.exit(1)

    except Exception as e:
        print(f"❌ FATAL ERROR: Symbol batch failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```

### 13.5 Refactored `scheduler_config.py`

**Key Changes**:

```python
class BatchScheduler:

    def initialize_jobs(self):
        """Initialize scheduled batch jobs - Architecture V2."""

        self.scheduler.remove_all_jobs()

        # NEW: Daily symbol batch - runs at 9:00 PM ET
        self.scheduler.add_job(
            func=self._run_daily_symbol_batch,  # NEW METHOD
            trigger='cron',
            hour=21,  # 9:00 PM ET
            minute=0,
            id='daily_symbol_batch',
            name='Daily Symbol Batch (Architecture V2)',
            replace_existing=True
        )

        # REMOVED: Daily correlations (now part of symbol batch)
        # self.scheduler.add_job(
        #     func=self._run_daily_correlations,  # DEPRECATED
        #     ...
        # )

        # KEEP: Company profile sync - moved to 9:30 PM
        self.scheduler.add_job(
            func=self._sync_company_profiles,
            trigger='cron',
            hour=21,
            minute=30,
            id='company_profile_sync',
            name='Daily Company Profile Sync',
            replace_existing=True
        )

        # KEEP: Market data verification - moved to 10:00 PM
        self.scheduler.add_job(
            func=self._verify_market_data,
            trigger='cron',
            hour=22,
            minute=0,
            id='market_data_verification',
            name='Daily Market Data Quality Check',
            replace_existing=True
        )

        # KEEP: Other jobs (feedback learning, admin metrics)...

    async def _run_daily_symbol_batch(self):
        """Execute the daily symbol batch (Architecture V2)."""
        from app.batch.symbol_batch_runner import symbol_batch_runner

        logger.info("Starting scheduled daily symbol batch")

        try:
            result = await symbol_batch_runner.run_daily_symbol_batch()

            logger.info(
                f"Symbol batch completed: {result.get('symbols_total', 0)} symbols, "
                f"phases: {list(result.get('phases', {}).keys())}"
            )

            if result.get('errors'):
                await self._send_batch_alert(
                    f"Symbol batch: {len(result['errors'])} errors",
                    result
                )

        except Exception as e:
            logger.error(f"Symbol batch failed: {str(e)}")
            await self._send_batch_alert(f"Symbol batch failed: {str(e)}", None)
            raise

    # DEPRECATED: Remove these methods
    # async def _run_daily_batch(self):  # Old portfolio-driven batch
    # async def _run_daily_correlations(self):  # Now in symbol batch
```

### 13.6 Backward Compatibility

**Admin Operations Still Use batch_orchestrator**:

The old `batch_orchestrator` is NOT deleted. It's still needed for:
- Admin-triggered portfolio recalculations
- Force rerun of specific portfolios
- Debugging and repair operations

```python
# Admin endpoint still works:
POST /api/v1/admin/batch/run
    ↓
batch_orchestrator.run_daily_batch_sequence(portfolio_ids=[...])
```

**New Admin Endpoint for Symbol Batch**:

```python
# NEW: Admin can trigger symbol batch manually
POST /api/v1/admin/symbol-batch/run
    ↓
symbol_batch_runner.run_daily_symbol_batch()
```

### 13.7 Migration Checklist

| Step | File | Action |
|------|------|--------|
| 1 | `symbol_batch_runner.py` | Create new file (see Part 4.2) |
| 2 | `railway_daily_batch.py` | Replace `batch_orchestrator` with `symbol_batch_runner` |
| 3 | `scheduler_config.py` | Update schedule, add `_run_daily_symbol_batch()` |
| 4 | `scheduler_config.py` | Remove `_run_daily_correlations()` |
| 5 | `admin_batch.py` | Add `/admin/symbol-batch/run` endpoint |
| 6 | Railway dashboard | Update cron schedule if needed |

### 13.8 Testing the New Cron

**Local Testing**:
```bash
# Test symbol batch directly
cd backend
uv run python -c "
import asyncio
from app.batch.symbol_batch_runner import symbol_batch_runner

async def test():
    result = await symbol_batch_runner.run_daily_symbol_batch(
        symbols=['AAPL', 'MSFT', 'GOOGL']  # Test subset
    )
    print(result)

asyncio.run(test())
"
```

**Railway Testing**:
```bash
# Trigger via Railway CLI
railway run python scripts/automation/railway_daily_batch.py
```

### 13.9 Rollback Plan

If issues arise, revert to portfolio-driven batch:

1. Update `railway_daily_batch.py` to call `batch_orchestrator` again
2. Revert `scheduler_config.py` to old schedule
3. No database changes needed (additive schema only)

---

## Appendix A: File Reference

### Current Files to Modify

| File | Changes |
|------|---------|
| `batch_orchestrator.py` | Remove symbol processing, add cache invalidation; KEEP Phase 7.x for admin ops |
| `batch_run_tracker.py` | KEEP AS-IS - Reused by symbol_batch_runner for Phase 7.x tracking |
| `analytics_runner.py` | Add cache check, use pre-computed betas only |
| `portfolio_factor_service.py` | Minor - already uses symbol betas |
| `symbol_factors.py` | Minor - add Market/IR Beta support |
| `onboarding.py` | MAJOR - Add symbol check, compute analytics inline, REMOVE Phase 7.x calls |
| `onboarding_status.py` | SIMPLIFY - Remove 9-phase tracking, use simple ready/pending/error status |
| `batch_trigger_service.py` | Remove onboarding-specific batch logic |
| `onboarding_service.py` | Add symbol check integration |
| `railway_daily_batch.py` | **MAJOR** - Replace batch_orchestrator with symbol_batch_runner (see Part 13) |
| `scheduler_config.py` | **MAJOR** - New schedule, add `_run_daily_symbol_batch()`, remove correlations job |
| `admin_batch.py` | Add `/admin/symbol-batch/run` endpoint for manual triggers |

### New Files to Create

| File | Purpose |
|------|---------|
| `symbol_batch_runner.py` | Daily symbol-level batch (reuses Phase 7.x tracking) |
| `symbol_onboarding_worker.py` | Async new symbol processing |
| `symbol_onboarding_tracker.py` | Concurrent job tracking for symbol onboarding (see 4.1.1) |
| `portfolio_cache_service.py` | Cache management |
| `symbol_price_service.py` | Price data management |
| `onboarding_helpers.py` | Symbol check and queue helpers |
| `railway_config.py` | Railway deployment constraints and limits (see Part 12) |

### Database Migrations

> **Updated**: V2 requires ZERO database migrations. All functionality uses existing tables + in-memory caches.

| ~~Migration~~ | ~~Description~~ | Status |
|---------------|-----------------|--------|
| ~~`add_symbol_prices_daily.py`~~ | ~~New price history table~~ | NOT NEEDED - use `market_data_cache` |
| ~~`add_portfolio_analytics_cache.py`~~ | ~~New cache table~~ | NOT NEEDED - use in-memory cache |
| ~~`add_symbol_onboarding_queue.py`~~ | ~~New queue table~~ | NOT NEEDED - use in-memory queue |
| ~~`modify_symbol_universe.py`~~ | ~~Add status columns~~ | NOT NEEDED - query existing tables |

---

## Appendix B: API Changes

### New Endpoints

```
GET  /api/v1/symbols/{symbol}/status
     Returns: { status: "ready" | "pending" | "error", factors_date: date }

POST /api/v1/admin/symbol-batch/run
     Triggers manual symbol batch run

GET  /api/v1/admin/symbol-batch/status
     Returns current/last symbol batch status
```

### Modified Endpoints

```
POST /api/v1/positions
     Now checks symbol status, may return { pending_symbols: [...] }

GET  /api/v1/analytics/portfolio/{id}/factor-exposures
     Now uses cache, much faster response
```

---

*End of Implementation Plan*
