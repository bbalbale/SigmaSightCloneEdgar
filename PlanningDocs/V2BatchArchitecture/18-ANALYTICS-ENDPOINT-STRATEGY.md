# 18: Analytics Endpoint Strategy

## Overview

The current analytics stack treats analytics as **batch products** (computed during batch, stored in database). V2 changes some endpoints to **compute on-demand from cache**. This document clarifies the strategy for each endpoint.

---

## Endpoint Classification

| Endpoint | Current Source | V2 Source | Change Required? |
|----------|----------------|-----------|------------------|
| `/analytics/portfolio/{id}/overview` | Stored `portfolio_snapshots` | Stored (no change) | No |
| `/analytics/portfolio/{id}/correlation-matrix` | Computed from stored prices | Computed from cache | Yes |
| `/analytics/portfolio/{id}/diversification-score` | Computed | Computed from cache | Minor |
| `/analytics/portfolio/{id}/factor-exposures` | Stored `factor_exposures` | Computed from cache | Yes |
| `/analytics/portfolio/{id}/positions/factor-exposures` | Stored `position_factor_exposures` | Computed from cache | Yes |
| `/analytics/portfolio/{id}/stress-test` | Computed from stored factors | Computed from cache | Yes |
| `/analytics/portfolio/{id}/sector-exposure` | Computed from positions | No change | No |
| `/analytics/portfolio/{id}/concentration` | Computed from positions | No change | No |
| `/analytics/portfolio/{id}/volatility` | Computed from stored prices | Computed from cache | Yes |

---

## Endpoint Details

### 1. Portfolio Overview (`/overview`)

**Current**: Reads from `portfolio_snapshots` table (created during batch).

**V2**: No change. Snapshots are still created:
- During onboarding (instant snapshot)
- During nightly portfolio refresh batch

**Source**: Database (`portfolio_snapshots`)

```python
# No changes needed - reads from stored snapshot
async def get_portfolio_overview(portfolio_id: UUID) -> PortfolioOverview:
    snapshot = await get_latest_snapshot(portfolio_id)
    return PortfolioOverview(
        total_value=snapshot.total_value,
        total_cost=snapshot.total_cost,
        total_pnl=snapshot.total_pnl,
        pnl_percent=snapshot.pnl_percent,
        position_count=snapshot.position_count,
        snapshot_date=snapshot.snapshot_date
    )
```

---

### 2. Correlation Matrix (`/correlation-matrix`)

**Current**: Queries `market_data_cache` for 1-year price history, computes correlation matrix.

**V2**: Uses in-memory cache for price history (faster).

**Source**: In-memory cache (`symbol_cache.get_price_history()`)

```python
# V2 - Use cache instead of database query
async def get_correlation_matrix(portfolio_id: UUID) -> CorrelationMatrix:
    positions = await get_active_positions(portfolio_id)

    # Get price history from cache (not DB)
    price_histories = {}
    for pos in positions:
        history = symbol_cache.get_price_history(pos.symbol)
        if history:
            price_histories[pos.symbol] = [p.close for p in history]

    # Compute correlation matrix (same algorithm)
    returns = compute_returns(price_histories)
    correlation_matrix = np.corrcoef(returns)

    return CorrelationMatrix(
        symbols=list(price_histories.keys()),
        matrix=correlation_matrix.tolist()
    )
```

**Performance**: ~50-100ms (vs ~200-500ms with DB query)

---

### 3. Portfolio Factor Exposures (`/factor-exposures`)

**Current**: Reads from `factor_exposures` table (computed during batch).

**V2**: Computes on-demand from cached symbol factors.

**Source**: In-memory cache (`symbol_cache.get_factors()`)

**Rationale**: Symbol factors are already computed nightly. Portfolio factor exposures are just weighted averages - cheap to compute.

```python
# V2 - Compute from cached symbol factors
async def get_portfolio_factor_exposures(portfolio_id: UUID) -> PortfolioFactorExposures:
    positions = await get_active_positions(portfolio_id)

    # Calculate total portfolio value
    total_value = Decimal('0')
    for pos in positions:
        price = symbol_cache.get_latest_price(pos.symbol)
        if price:
            total_value += pos.quantity * price

    # Weight-average the factor exposures
    portfolio_factors = defaultdict(Decimal)

    for pos in positions:
        price = symbol_cache.get_latest_price(pos.symbol)
        factors = symbol_cache.get_factors(pos.symbol)

        if price and factors and total_value > 0:
            weight = (pos.quantity * price) / total_value

            portfolio_factors['market_beta'] += weight * factors.market_beta
            portfolio_factors['ir_beta'] += weight * factors.ir_beta

            for name, value in factors.ridge_factors.items():
                portfolio_factors[name] += weight * value

            for name, value in factors.spread_factors.items():
                portfolio_factors[name] += weight * value

    return PortfolioFactorExposures(**portfolio_factors)
```

**Performance**: ~10-50ms

---

### 4. Position Factor Exposures (`/positions/factor-exposures`)

**Current**: Reads from `position_factor_exposures` or `symbol_factor_exposures` tables.

**V2**: Reads directly from cache.

**Source**: In-memory cache (`symbol_cache.get_factors()`)

```python
# V2 - Read from cache
async def get_position_factor_exposures(portfolio_id: UUID) -> List[PositionFactorExposures]:
    positions = await get_active_positions(portfolio_id)

    results = []
    for pos in positions:
        factors = symbol_cache.get_factors(pos.symbol)
        if factors:
            results.append(PositionFactorExposures(
                symbol=pos.symbol,
                market_beta=factors.market_beta,
                ir_beta=factors.ir_beta,
                factors=factors.ridge_factors | factors.spread_factors
            ))

    return results
```

**Performance**: ~5-20ms

---

### 5. Stress Test (`/stress-test`)

**Current**: Uses stored factor exposures to compute stressed P&L.

**V2**: Uses cached factor exposures.

**Source**: In-memory cache

```python
# V2 - Use cached factors for stress test
async def run_stress_test(portfolio_id: UUID, scenarios: List[Scenario]) -> StressTestResults:
    positions = await get_active_positions(portfolio_id)

    results = []
    for scenario in scenarios:
        portfolio_impact = Decimal('0')

        for pos in positions:
            price = symbol_cache.get_latest_price(pos.symbol)
            factors = symbol_cache.get_factors(pos.symbol)

            if price and factors:
                position_value = pos.quantity * price

                # Apply scenario shocks to factors
                position_impact = compute_position_stress(
                    position_value=position_value,
                    factors=factors,
                    scenario=scenario
                )
                portfolio_impact += position_impact

        results.append(ScenarioResult(
            scenario_name=scenario.name,
            portfolio_impact=portfolio_impact
        ))

    return StressTestResults(scenarios=results)
```

**Performance**: ~20-100ms depending on scenario count

---

### 6. Volatility (`/volatility`)

**Current**: Queries `market_data_cache` for price history, computes volatility.

**V2**: Uses cached price history.

**Source**: In-memory cache (`symbol_cache.get_price_history()`)

```python
# V2 - Use cached price history
async def get_portfolio_volatility(portfolio_id: UUID) -> VolatilityMetrics:
    positions = await get_active_positions(portfolio_id)

    # Get price histories from cache
    price_histories = {}
    weights = {}

    total_value = Decimal('0')
    for pos in positions:
        price = symbol_cache.get_latest_price(pos.symbol)
        if price:
            total_value += pos.quantity * price

    for pos in positions:
        history = symbol_cache.get_price_history(pos.symbol)
        price = symbol_cache.get_latest_price(pos.symbol)
        if history and price:
            price_histories[pos.symbol] = [p.close for p in history]
            weights[pos.symbol] = (pos.quantity * price) / total_value

    # Compute volatility (same algorithm as before)
    returns = compute_returns(price_histories)
    portfolio_returns = compute_weighted_returns(returns, weights)
    volatility = compute_volatility_metrics(portfolio_returns)

    return VolatilityMetrics(
        daily_vol=volatility.daily,
        annualized_vol=volatility.annualized,
        har_forecast=volatility.har_forecast
    )
```

**Performance**: ~50-100ms

---

### 7. Endpoints with No Change

These endpoints already compute from positions/prices and don't rely on batch-stored analytics:

| Endpoint | Current Behavior | V2 Behavior |
|----------|------------------|-------------|
| `/sector-exposure` | Queries positions + sector info | No change |
| `/concentration` | Computes HHI from positions | No change |
| `/diversification-score` | Computes from positions | Minor - use cache for prices |

---

## Compatibility Strategy

### API Response Contract

**No changes to response shapes.** Endpoints return the same data structure, just computed from cache instead of stored rows.

```typescript
// Response shape unchanged
interface PortfolioFactorExposures {
    market_beta: number;
    ir_beta: number;
    factor_value: number;
    factor_growth: number;
    factor_momentum: number;
    // ... same fields
}
```

### Fallback for Cache Miss

If symbol data is not in cache, fall back to database query:

```python
async def get_factors_with_fallback(symbol: str, db: AsyncSession) -> Optional[SymbolFactors]:
    # Try cache first
    cached = symbol_cache.get_factors(symbol)
    if cached:
        return cached

    # Fallback to database (slower but always works)
    logger.info(f"Cache miss for {symbol}, falling back to DB")
    return await db_get_symbol_factors(db, symbol)
```

### Cold Start Handling

When app restarts or scales, cache is empty. Analytics must still work.

**Strategy**: Cache initializes in background; analytics use DB fallback until ready.

```python
async def get_portfolio_factor_exposures(portfolio_id: UUID, db: AsyncSession):
    # Check if cache is ready
    use_cache = symbol_cache.is_ready()

    for pos in positions:
        if use_cache:
            # Fast path: cache hit
            factors = symbol_cache.get_factors(pos.symbol)
        else:
            # Slow path: DB query (cold start)
            factors = await db_get_symbol_factors(db, pos.symbol)
```

**Performance during cold start:**

| Scenario | Latency | Notes |
|----------|---------|-------|
| Cache ready | ~10-50ms | Normal operation |
| Cold start (cache empty) | ~200-500ms | Falls back to DB |
| Cache initializing | ~200-500ms | DB fallback while loading |

**Key**: Analytics always work. Cache is an optimization, not a requirement.

> **See also**: `06-PORTFOLIO-CACHE.md` for complete cold start implementation details.

---

## Migration Path

### Phase 1: Add Cache Layer (Non-Breaking)

1. Deploy cache infrastructure
2. Keep existing DB queries as fallback
3. Log cache hit/miss rates

### Phase 2: Switch to Cache-First

1. Change endpoints to read from cache first
2. Keep DB fallback for cache misses
3. Monitor performance improvements

### Phase 3: Cleanup (Optional)

1. Consider removing stored `factor_exposures` table (portfolio-level)
2. Keep `symbol_factor_exposures` (written by batch)
3. Simplify batch to only write symbol-level data

---

## Performance Comparison

| Endpoint | Current (DB) | V2 (Cache) | Improvement |
|----------|--------------|------------|-------------|
| `/overview` | ~20ms | ~20ms | Same (still DB) |
| `/correlation-matrix` | ~200-500ms | ~50-100ms | 4-5x faster |
| `/factor-exposures` | ~50-100ms | ~10-50ms | 2-5x faster |
| `/positions/factor-exposures` | ~30-80ms | ~5-20ms | 4-6x faster |
| `/stress-test` | ~100-300ms | ~20-100ms | 3-5x faster |
| `/volatility` | ~150-400ms | ~50-100ms | 3-4x faster |

---

## Summary

| Aspect | Current | V2 |
|--------|---------|-----|
| Data source | Batch-stored rows in DB | In-memory cache (refreshed nightly) |
| Computation timing | During batch (pre-computed) | On-demand (when requested) |
| Response shape | Same | Same (no API changes) |
| Performance | Good | Better (cache is faster than DB) |
| Freshness | As of last batch | As of last batch (same) |

**Key principle**: V2 changes HOW analytics are computed, not WHAT they return. API contract is preserved.
