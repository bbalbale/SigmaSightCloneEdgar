# Symbol-Level Factor Universe Architecture

**Created**: 2025-12-20
**Status**: Planning
**Goal**: Pre-compute factor exposures for all symbols in the universe, then aggregate to portfolios

---

## Open Discussion: Do We Need Position-Level Factor Storage?

### Current State
- `PositionFactorExposure` table stores factor betas per position
- Same symbol in different portfolios = duplicate records
- ~75,000+ records for 63 positions × 120 dates × 6-10 factors

### Proposed: Symbol-Level Only
- `SymbolFactorExposure` table stores factor betas per symbol
- Same symbol = one record regardless of portfolios
- ~6,000 records (90% reduction)

### Key Insight
We can always **reconstruct** position-level exposure from:
1. Symbol factor betas (from `symbol_factor_exposures`)
2. Position data (symbol, weight, delta for options)
3. Formula: `position_exposure = weight × delta × symbol_beta`

For any historical date:
- We have the positions that existed on that date
- We have the symbol factor exposures on that date
- We can recalculate position/portfolio exposure on demand

### Recommendation: Don't Store Position-Level
```python
# Portfolio aggregation (computed on demand, not stored)
for position in positions:
    if position.is_option:
        effective_beta = position.delta * symbol_betas[position.underlying_symbol]
    else:
        effective_beta = symbol_betas[position.symbol]

    portfolio_beta[factor] += position.weight * effective_beta
```

### Trade-offs

| Consideration | Symbol-Only | Keep Position-Level |
|--------------|-------------|---------------------|
| Storage | 90% less | Current size |
| Write speed | Faster | Slower |
| Read speed | Tiny compute | Direct lookup |
| Audit trail | Reconstruct on demand | Pre-computed |
| Schema simplicity | Simpler | More complex |
| Options handling | Compute delta×beta | Pre-computed |

### Decision: TBD
- Leaning toward symbol-only with on-demand position computation
- Need to validate options delta handling works correctly
- May keep PositionFactorExposure for transition period

---

## Factor Calculation Methods

This architecture applies to BOTH factor calculation methods:

### Ridge Factors (6 factors)
- **Method**: Ridge regression (L2 regularization)
- **Factors**: Value, Growth, Momentum, Quality, Size, Low Volatility
- **ETFs**: VTV, VUG, MTUM, QUAL, IWM, USMV
- **Window**: 365 days
- **Calculation**: Single multivariate regression per symbol

### Spread Factors (4 factors)
- **Method**: 4 separate univariate OLS regressions
- **Factors**: Growth-Value, Momentum, Size, Quality spreads
- **Spreads**: (VUG-VTV), (MTUM-SPY), (IWM-SPY), (QUAL-SPY)
- **Window**: 180 days
- **Calculation**: 4 independent regressions per symbol

### Why Symbol-Level Works for Both

Both methods calculate: **"How does this symbol's returns relate to factor returns?"**

This is intrinsic to the symbol, not the portfolio:
- AAPL's Growth-Value spread beta is the same in Portfolio A and Portfolio B
- AAPL's Ridge momentum factor is the same everywhere

The only position-specific adjustment is:
- **Weight**: What portion of the portfolio is this position?
- **Delta** (options only): What's the effective exposure to the underlying?

---

## Executive Summary

Current architecture calculates factor betas per-position, causing redundant calculations when the same ticker appears in multiple portfolios. This plan refactors to:

1. **Pre-compute** factor betas for ALL symbols in the database (universe-level)
2. **Cache** results in a new `symbol_factor_exposures` table
3. **Aggregate** to portfolio-level by looking up cached symbol betas and weighting

**Benefits:**
- Calculate each symbol ONCE per day (not once per position)
- Enable parallel processing with isolated sessions (avoids Railway errors)
- Support predictive "what-if" analysis for new portfolios
- Align with industry risk model architecture (Barra, Axioma, MSCI)

---

## Current vs Proposed Architecture

### Current (Position-First)
```
For each portfolio:
  For each position:
    1. Check if position has cached betas
    2. If not: fetch returns, run Ridge regression
    3. Save to PositionFactorExposure
  Aggregate position betas → portfolio betas
```
**Problem**: AAPL in 3 portfolios = 3 calculations (different position IDs)

### Proposed (Symbol-Universe-First)
```
PHASE A: Universe Factor Calculation (runs once per day)
  1. Get all unique symbols from positions table
  2. Check which symbols need calculation (not cached for today)
  3. Batch symbols into groups of 10-20
  4. Process batches in PARALLEL (each batch = isolated session)
  5. Store results in symbol_factor_exposures table

PHASE B: Portfolio Aggregation (runs per portfolio)
  1. Get positions for portfolio
  2. Look up symbol betas from cache (single query)
  3. Multiply by position weights
  4. Sum to get portfolio factor exposure
```
**Result**: AAPL calculated ONCE, used by all portfolios

---

## Database Schema Changes

### New Table: `symbol_factor_exposures`

Stores factor betas for both Ridge (6 factors) and Spread (4 factors) calculations.

```sql
CREATE TABLE symbol_factor_exposures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    factor_id UUID NOT NULL REFERENCES factor_definitions(id),
    calculation_date DATE NOT NULL,
    beta_value DECIMAL(10, 6) NOT NULL,
    r_squared DECIMAL(6, 4),
    observations INTEGER,
    quality_flag VARCHAR(20),
    calculation_method VARCHAR(50) NOT NULL,  -- 'ridge_regression', 'spread_regression'
    regularization_alpha DECIMAL(6, 4),       -- Only for ridge (NULL for spread)
    regression_window_days INTEGER,           -- 365 for ridge, 180 for spread
    created_at TIMESTAMP DEFAULT NOW(),

    -- Unique constraint for upsert pattern
    CONSTRAINT uq_symbol_factor_date UNIQUE (symbol, factor_id, calculation_date)
);

-- Index for fast lookups by symbol + date (most common query)
CREATE INDEX idx_symbol_factor_date ON symbol_factor_exposures(symbol, calculation_date);

-- Index for batch processing by method + date
CREATE INDEX idx_symbol_factor_method ON symbol_factor_exposures(calculation_method, calculation_date);
```

**Records per symbol per date:**
- Ridge factors: 6 records (Value, Growth, Momentum, Quality, Size, Low Volatility)
- Spread factors: 4 records (Growth-Value, Momentum, Size, Quality spreads)
- Total: 10 factor betas per symbol per date

### New Table: `symbol_universe` (optional, for tracking)
```sql
CREATE TABLE symbol_universe (
    symbol VARCHAR(20) PRIMARY KEY,
    asset_type VARCHAR(20),  -- 'equity', 'etf', 'option_underlying'
    sector VARCHAR(100),
    first_seen_date DATE,
    last_seen_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### What Happens to `position_factor_exposures`?

**Option A: Deprecate entirely**
- Stop writing to it
- Portfolio aggregation uses `symbol_factor_exposures` + position weights
- Eventually drop the table

**Option B: Keep for transition**
- Dual-write during validation period
- Compare results to ensure correctness
- Deprecate after confidence is high

**Recommendation**: Option B initially, then Option A after validation.

---

## Parallelization Strategy (Avoiding Railway Errors)

### Root Cause of Previous Errors
```
Error: "This session is provisioning a new connection; concurrent operations are not permitted"
Error: "Usage of the 'Session.add()' operation is not currently supported within flush"
```

**Cause**: Multiple coroutines using the same SQLAlchemy AsyncSession concurrently.

### Solution: Batch-Level Session Isolation

```python
async def calculate_universe_factors(calculation_date: date) -> Dict[str, Any]:
    """
    Calculate factor betas for all symbols in universe using parallel batches.

    Key: Each BATCH gets its own isolated session, avoiding concurrent session access.
    """

    # Step 1: Get symbols needing calculation (single query)
    async with AsyncSessionLocal() as db:
        symbols_needing_calc = await get_uncached_symbols(db, calculation_date)

    # Step 2: Batch symbols (10-20 per batch to balance parallelism vs overhead)
    batch_size = 15
    batches = [
        symbols_needing_calc[i:i + batch_size]
        for i in range(0, len(symbols_needing_calc), batch_size)
    ]

    # Step 3: Fetch factor ETF returns ONCE (shared across all batches)
    async with AsyncSessionLocal() as db:
        factor_returns = await get_factor_etf_returns(db, calculation_date)

    # Step 4: Process batches in parallel (each batch = isolated session)
    async def process_batch(batch_symbols: List[str]) -> Dict[str, Any]:
        """Process a batch of symbols with its own database session."""
        async with AsyncSessionLocal() as batch_db:
            results = []
            for symbol in batch_symbols:
                try:
                    result = await calculate_symbol_factors(
                        db=batch_db,
                        symbol=symbol,
                        factor_returns=factor_returns,  # Shared, read-only
                        calculation_date=calculation_date
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to calculate factors for {symbol}: {e}")
                    results.append({'symbol': symbol, 'success': False, 'error': str(e)})

            # Commit all symbols in this batch at once
            await batch_db.commit()
            return {'batch_size': len(batch_symbols), 'results': results}

    # Step 5: Run batches in parallel
    batch_tasks = [process_batch(batch) for batch in batches]
    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

    return aggregate_batch_results(batch_results)
```

### Why This Works
| Aspect | Before (Broken) | After (Safe) |
|--------|-----------------|--------------|
| Session scope | Shared across parallel coroutines | Isolated per batch |
| Parallel unit | Individual symbols | Batches of 15 symbols |
| Commit pattern | After each symbol | After each batch |
| Error isolation | One failure affects all | One batch failure isolated |

### Parallelization Parameters
```python
# Tunable parameters
BATCH_SIZE = 15          # Symbols per batch (balance parallelism vs session overhead)
MAX_CONCURRENT_BATCHES = 5  # Limit concurrent DB connections
FACTOR_ETF_CACHE_TTL = 3600  # Cache factor returns for 1 hour
```

---

## Implementation Phases

### Phase 1: Database Schema (1-2 hours)
1. Create Alembic migration for `symbol_factor_exposures` table
2. Create Alembic migration for `symbol_universe` table (optional)
3. Add indexes for performance
4. Test migration on local/sandbox

### Phase 2: Symbol Factor Calculator (3-4 hours)
1. Create `app/calculations/symbol_factors.py`
   - `calculate_symbol_factors()` - single symbol calculation
   - `calculate_universe_factors()` - parallel batch orchestration
   - `get_uncached_symbols()` - find symbols needing calculation
   - `persist_symbol_factors()` - save to new table

2. Key functions:
```python
async def calculate_symbol_factors(
    db: AsyncSession,
    symbol: str,
    factor_returns: pd.DataFrame,
    calculation_date: date,
    regularization_alpha: float = 1.0
) -> Dict[str, Any]:
    """Calculate Ridge factor betas for a single symbol."""

    # Get symbol returns
    symbol_returns = await get_symbol_returns(db, symbol, calculation_date)

    # Run Ridge regression
    result = run_ridge_regression(symbol_returns, factor_returns, regularization_alpha)

    # Persist to symbol_factor_exposures
    await persist_symbol_factors(db, symbol, result, calculation_date)

    return result
```

### Phase 3: Portfolio Aggregation Service (2-3 hours)
1. Create `app/services/portfolio_factor_service.py`
   - `get_portfolio_factor_exposures()` - main entry point
   - `load_symbol_betas_for_portfolio()` - bulk lookup from cache
   - `aggregate_to_portfolio()` - weight and sum

2. Key function:
```python
async def get_portfolio_factor_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, float]:
    """
    Get portfolio factor exposures by aggregating symbol-level betas.

    This is a LOOKUP operation, not a calculation.
    Assumes symbol betas were pre-computed by universe job.
    """

    # Get positions with weights
    positions = await get_portfolio_positions_with_weights(db, portfolio_id)

    # Get symbols
    symbols = [p.symbol for p in positions]

    # Bulk lookup symbol betas (single query)
    symbol_betas = await load_symbol_betas(db, symbols, calculation_date)

    # Aggregate: portfolio_beta[factor] = sum(position_weight * symbol_beta[factor])
    portfolio_betas = {}
    for factor_name in FACTOR_NAMES:
        portfolio_betas[factor_name] = sum(
            p.weight * symbol_betas.get(p.symbol, {}).get(factor_name, 0)
            for p in positions
        )

    return portfolio_betas
```

### Phase 4: Batch Orchestrator Integration (2-3 hours)
1. Add new Phase 0.5: Universe Factor Calculation (runs BEFORE portfolio processing)
2. Modify Phase 6 analytics to use new aggregation service
3. Keep backward compatibility with existing PositionFactorExposure table

```python
# In batch_orchestrator.py

async def run_daily_batch_with_backfill(...):
    # ...existing Phase 0 (Company Profiles)...

    # NEW: Phase 0.5 - Universe Factor Calculation
    logger.info(f"Phase 0.5: Calculating universe factor exposures")
    universe_result = await calculate_universe_factors(calculation_date)
    logger.info(f"[FACTORS] {universe_result['symbols_calculated']} symbols in {universe_result['duration']}s")

    # ...existing Phase 1 (Market Data)...
    # ...existing Phase 2-6...
```

### Phase 5: Testing & Validation (2-3 hours)
1. Verify symbol betas match position betas (for same symbol)
2. Verify portfolio aggregation matches current calculation
3. Performance benchmarks: before vs after
4. Test parallelization under load

---

## Performance Expectations

### Current Performance (100 symbols across 3 portfolios)
- 100 symbols × ~1s each = ~100s sequential
- With position caching: ~60s (some positions cached within same run)

### Expected Performance (Same scenario)
- Phase 0.5: 100 unique symbols ÷ 15 per batch = 7 batches
- 7 batches in parallel × ~15s per batch = ~15s total
- Portfolio aggregation: ~0.5s per portfolio (just lookups)
- **Total: ~20s vs ~100s = 5x improvement**

### For Large Backfills (120 dates)
- Current: 120 dates × 100s = 3.3 hours
- New: 120 dates × 20s = 40 minutes
- **83% reduction in processing time**

---

## Rollout Strategy

### Step 1: Deploy Schema (Day 1)
- Run migration to create new tables
- No code changes yet

### Step 2: Dual-Write Mode (Day 2-3)
- Calculate factors using new symbol-level approach
- ALSO write to existing PositionFactorExposure (backward compatibility)
- Compare results to validate

### Step 3: Switch Read Path (Day 4-5)
- Portfolio aggregation reads from symbol_factor_exposures
- Falls back to PositionFactorExposure if missing
- Monitor for issues

### Step 4: Deprecate Position-Level (Day 7+)
- Stop writing to PositionFactorExposure for factor betas
- Keep table for other position-specific metrics
- Clean up old code

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| New table migration fails | Test on sandbox first, have rollback ready |
| Parallel batches overload DB | MAX_CONCURRENT_BATCHES limit, connection pooling |
| Symbol not in universe | Fallback to on-demand calculation |
| Incorrect aggregation | Dual-write mode validates against old approach |
| Railway rate limits on logs | Reduced logging already implemented |

---

## File Changes Summary

### New Files
- `app/calculations/symbol_factors.py` - Core symbol-level calculation
- `app/services/portfolio_factor_service.py` - Portfolio aggregation
- `alembic/versions/xxx_add_symbol_factor_exposures.py` - Migration

### Modified Files
- `app/batch/batch_orchestrator.py` - Add Phase 0.5
- `app/batch/analytics_runner.py` - Use new aggregation service
- `app/calculations/factors_ridge.py` - Refactor to use symbol-level

### Deprecated (Eventually)
- Position-level factor calculation in `factors_ridge.py`
- Position-level caching in `factor_utils.py`

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Factor calculation time (100 symbols) | ~100s | ~20s |
| Redundant calculations (shared symbols) | Yes | None |
| Parallel batch errors | N/A | 0 |
| Portfolio aggregation time | ~10s | <1s |

---

## Appendix: Key Code Patterns

### Safe Parallel Batch Pattern
```python
async def safe_parallel_batches(items: List[T], batch_size: int, process_fn) -> List:
    """
    Process items in parallel batches with isolated sessions.

    This pattern avoids SQLAlchemy session conflicts by:
    1. Batching items (not individual parallel processing)
    2. Each batch gets its own session
    3. Sequential processing within each batch
    4. Parallel processing across batches
    """
    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

    async def process_batch(batch: List[T]) -> List:
        async with AsyncSessionLocal() as db:
            results = []
            for item in batch:
                result = await process_fn(db, item)
                results.append(result)
            await db.commit()
            return results

    batch_results = await asyncio.gather(
        *[process_batch(b) for b in batches],
        return_exceptions=True
    )

    # Flatten results
    return [r for batch in batch_results if not isinstance(batch, Exception) for r in batch]
```

### Bulk Symbol Beta Lookup
```python
async def load_symbol_betas(
    db: AsyncSession,
    symbols: List[str],
    calculation_date: date
) -> Dict[str, Dict[str, float]]:
    """
    Bulk load symbol betas in a single query.

    Returns: {symbol: {factor_name: beta_value}}
    """
    stmt = (
        select(
            SymbolFactorExposure.symbol,
            FactorDefinition.name,
            SymbolFactorExposure.beta_value
        )
        .join(FactorDefinition, SymbolFactorExposure.factor_id == FactorDefinition.id)
        .where(
            and_(
                SymbolFactorExposure.symbol.in_(symbols),
                SymbolFactorExposure.calculation_date == calculation_date
            )
        )
    )

    result = await db.execute(stmt)
    rows = result.fetchall()

    # Build nested dict
    betas = {}
    for symbol, factor_name, beta_value in rows:
        if symbol not in betas:
            betas[symbol] = {}
        betas[symbol][factor_name] = float(beta_value)

    return betas
```
