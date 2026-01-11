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

STEP 4: For each symbol (parallelized, 50 workers):
        a. Load 90 days of returns
        b. Calculate Market Beta (OLS vs SPY)
        c. Calculate IR Beta (OLS vs TLT)
        d. Calculate Ridge factors (6 factors)
        e. Load 180 days of returns
        f. Calculate Spread factors (4 factors)
        g. UPSERT into symbol_factor_exposures
        (~5 min total with parallelization)

STEP 5: Update symbol_daily_metrics (denormalized view)
        (~1 min)

TOTAL: ~8-10 minutes, FIXED regardless of user count
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

**`symbol_onboarding_queue`** - Async job queue:

```sql
CREATE TABLE symbol_onboarding_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, processing, completed, failed
    requested_by UUID REFERENCES users(id),
    priority VARCHAR(10) DEFAULT 'normal',  -- high, normal, low
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_queue_status ON symbol_onboarding_queue(status, priority, created_at);
```

### 3.2 Schema Modifications

**`symbol_universe`** - Add status tracking:

```sql
ALTER TABLE symbol_universe ADD COLUMN status VARCHAR(20) DEFAULT 'active';
-- Values: 'pending', 'active', 'delisted', 'error'

ALTER TABLE symbol_universe ADD COLUMN last_price_date DATE;
ALTER TABLE symbol_universe ADD COLUMN last_factor_date DATE;
```

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
├── symbol_batch_runner.py      # NEW: Symbol-only daily batch
├── symbol_onboarding_worker.py # NEW: Async symbol onboarding
└── portfolio_analytics_cache.py # NEW: Cache management

backend/app/services/
├── symbol_price_service.py     # NEW: Price management
└── portfolio_cache_service.py  # NEW: Portfolio cache operations

backend/app/api/v1/
└── onboarding_status.py        # MODIFY: Add symbol status endpoint
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

        # Process in parallel batches
        for batch in self._batch_symbols(symbols, batch_size=50):
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

### 4.4 Modifications to Existing Code

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

### 5.1 Phase 1: Database Schema (Week 1)

1. Create migration for new tables:
   - `symbol_prices_daily`
   - `portfolio_analytics_cache`
   - `symbol_onboarding_queue`

2. Modify `symbol_universe` table:
   - Add `status`, `last_price_date`, `last_factor_date` columns

3. Add new factor definitions:
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

### 5.5 Phase 5: Onboarding Flow (Week 5)

1. Create `symbol_onboarding_worker.py`:
   - Background job processor
   - Symbol history fetch
   - Factor calculation for new symbols

2. Create API endpoint `/api/v1/symbols/{symbol}/status`:
   - Returns: `ready`, `pending`, `error`

3. Modify position creation:
   - Check symbol status
   - Queue onboarding if new
   - Return appropriate status to frontend

### 5.6 Phase 6: Cleanup (Week 6)

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

### 7.1 Symbol Batch (Daily)

| Step | Current | New | Notes |
|------|---------|-----|-------|
| Market Data | Variable (portfolio-driven) | 2 min | Batch YFinance call |
| Market Beta | Per-portfolio | 2 min | 5,000 symbols, parallel |
| IR Beta | Per-portfolio | 2 min | 5,000 symbols, parallel |
| Ridge Factors | Per-portfolio | 3 min | Already optimized |
| Spread Factors | Per-portfolio | 3 min | Already optimized |
| Metrics | Per-portfolio | 1 min | Denormalized update |
| **TOTAL** | 30+ min | ~8-10 min | **FIXED COST** |

### 7.2 Portfolio Analytics (Per Request)

| Scenario | Current | New |
|----------|---------|-----|
| Cache Hit | N/A | <10ms |
| Cache Miss (aggregation) | N/A | 50-100ms |
| Full calculation | 3-30 min | N/A (eliminated) |

### 7.3 Scaling

| Users | Current Time | New Time |
|-------|--------------|----------|
| 100 | 3-10 min | 8-10 min |
| 1,000 | 10-30 min | 8-10 min |
| 10,000 | Hours | 8-10 min |

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

### 10.7 Frontend Changes (Suggested)

**Current frontend (waiting state):**
```jsx
// Shows for 15-30 minutes
<div className="onboarding-progress">
  <h2>Processing your portfolio...</h2>
  <ProgressBar phases={9} current={currentPhase} />
  <ActivityLog entries={activityLog} />
  <p>Estimated time: 15-20 minutes</p>
</div>
```

**New frontend (instant):**
```jsx
// Case 1: Immediate success
<div className="onboarding-complete">
  <h2>✅ Your portfolio is ready!</h2>
  <Button onClick={() => navigate('/dashboard')}>
    View Analytics
  </Button>
</div>

// Case 2: Partial (rare)
<div className="onboarding-partial">
  <h2>📊 Analytics ready for most positions</h2>
  <p>Loading data for {pendingSymbols.length} new symbol(s)...</p>
  <ProgressBar indeterminate />
  <Button onClick={() => navigate('/dashboard')}>
    View Available Analytics
  </Button>
</div>
```

### 10.8 Files to Modify for Onboarding

| File | Change Type | Description |
|------|-------------|-------------|
| `app/api/v1/onboarding.py` | MAJOR | Add symbol check, remove batch trigger, compute analytics inline |
| `app/api/v1/onboarding_status.py` | SIMPLIFY | Remove 9-phase tracking, simple pending symbol status |
| `app/services/batch_trigger_service.py` | MINOR | Remove onboarding-specific batch logic |
| `app/services/onboarding_service.py` | MINOR | Add symbol check integration |
| `app/services/onboarding_helpers.py` | NEW | Helper functions for new flow |

### 10.9 Deprecations

The following will be deprecated/simplified:

1. **Phase 7.1 Progress Tracking** - No longer needed for onboarding
   - `batch_run_tracker.get_onboarding_status()` - simplified
   - Activity log for onboarding - removed
   - Phase progress UI - removed

2. **Batch Trigger for Onboarding**
   - `batch_trigger_service.trigger_batch(force_onboarding=True)` - removed
   - `run_daily_batch_sequence()` for single portfolio - removed

3. **Complex Status Polling**
   - 9-phase status response - simplified to ready/pending/error
   - 2-second polling for 15+ minutes - reduced to 5-second polling for <60 sec

---

## Appendix A: File Reference

### Current Files to Modify

| File | Changes |
|------|---------|
| `batch_orchestrator.py` | Remove symbol processing, add cache invalidation |
| `analytics_runner.py` | Add cache check, use pre-computed betas only |
| `portfolio_factor_service.py` | Minor - already uses symbol betas |
| `symbol_factors.py` | Minor - add Market/IR Beta support |
| `onboarding.py` | MAJOR - Add symbol check, compute analytics inline |
| `onboarding_status.py` | SIMPLIFY - Remove 9-phase tracking |
| `batch_trigger_service.py` | Remove onboarding-specific batch logic |
| `onboarding_service.py` | Add symbol check integration |

### New Files to Create

| File | Purpose |
|------|---------|
| `symbol_batch_runner.py` | Daily symbol-level batch |
| `symbol_onboarding_worker.py` | Async new symbol processing |
| `portfolio_cache_service.py` | Cache management |
| `symbol_price_service.py` | Price data management |
| `onboarding_helpers.py` | Symbol check and queue helpers |

### Database Migrations

| Migration | Description |
|-----------|-------------|
| `add_symbol_prices_daily.py` | New price history table |
| `add_portfolio_analytics_cache.py` | New cache table |
| `add_symbol_onboarding_queue.py` | New queue table |
| `modify_symbol_universe.py` | Add status columns |

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
