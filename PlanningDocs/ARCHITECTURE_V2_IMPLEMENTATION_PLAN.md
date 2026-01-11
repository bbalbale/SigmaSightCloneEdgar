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

---

## Appendix A: File Reference

### Current Files to Modify

| File | Changes |
|------|---------|
| `batch_orchestrator.py` | Remove symbol processing, add cache invalidation |
| `analytics_runner.py` | Add cache check, use pre-computed betas only |
| `portfolio_factor_service.py` | Minor - already uses symbol betas |
| `symbol_factors.py` | Minor - add Market/IR Beta support |

### New Files to Create

| File | Purpose |
|------|---------|
| `symbol_batch_runner.py` | Daily symbol-level batch |
| `symbol_onboarding_worker.py` | Async new symbol processing |
| `portfolio_cache_service.py` | Cache management |
| `symbol_price_service.py` | Price data management |

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
