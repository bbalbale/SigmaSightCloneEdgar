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

### Decision: Keep Both Initially

**Approach**: Dual-write to both tables during validation phase:
1. Calculate symbol-level factors → store in `symbol_factor_exposures`
2. Continue writing position-level factors → store in `position_factor_exposures`
3. Run comparison script to validate consistency
4. Only deprecate position-level after high confidence in symbol-level accuracy

**Rationale**:
- Need to validate options delta handling works correctly
- Need to compare aggregated symbol-level vs direct position-level calculations
- Provides safety net during transition
- Enables A/B testing of calculation approaches

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

### New Table: `symbol_universe` (REQUIRED - supports Symbol Dashboard)
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

### New Table: `symbol_daily_metrics` (for Symbol Dashboard page)

This table consolidates all current-day metrics for fast dashboard queries. Updated daily by batch process.

```sql
CREATE TABLE symbol_daily_metrics (
    symbol VARCHAR(20) PRIMARY KEY REFERENCES symbol_universe(symbol),
    metrics_date DATE NOT NULL,

    -- Price & Returns (calculated from market_data)
    current_price DECIMAL(12, 4),
    return_1d DECIMAL(8, 6),        -- Daily return
    return_mtd DECIMAL(8, 6),       -- Month-to-date
    return_ytd DECIMAL(8, 6),       -- Year-to-date
    return_1m DECIMAL(8, 6),        -- Rolling 1 month
    return_3m DECIMAL(8, 6),        -- Rolling 3 months
    return_1y DECIMAL(8, 6),        -- Rolling 1 year

    -- Valuation (from company_profiles/fundamentals)
    market_cap DECIMAL(18, 2),
    enterprise_value DECIMAL(18, 2),
    pe_ratio DECIMAL(10, 4),
    ps_ratio DECIMAL(10, 4),
    pb_ratio DECIMAL(10, 4),

    -- Company Info (from company_profiles)
    sector VARCHAR(100),
    industry VARCHAR(100),
    company_name VARCHAR(255),

    -- Factor Exposures (denormalized from symbol_factor_exposures for fast reads)
    -- Ridge Factors
    factor_value DECIMAL(8, 6),
    factor_growth DECIMAL(8, 6),
    factor_momentum DECIMAL(8, 6),
    factor_quality DECIMAL(8, 6),
    factor_size DECIMAL(8, 6),
    factor_low_vol DECIMAL(8, 6),
    -- Spread Factors
    factor_growth_value_spread DECIMAL(8, 6),
    factor_momentum_spread DECIMAL(8, 6),
    factor_size_spread DECIMAL(8, 6),
    factor_quality_spread DECIMAL(8, 6),

    -- Metadata
    data_quality_score DECIMAL(4, 2),  -- 0-100, completeness indicator
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Index for sorting by any metric
    CONSTRAINT uq_symbol_metrics_date UNIQUE (symbol, metrics_date)
);

-- Indexes for common sort/filter operations
CREATE INDEX idx_metrics_sector ON symbol_daily_metrics(sector);
CREATE INDEX idx_metrics_market_cap ON symbol_daily_metrics(market_cap DESC);
CREATE INDEX idx_metrics_return_ytd ON symbol_daily_metrics(return_ytd DESC);
CREATE INDEX idx_metrics_pe ON symbol_daily_metrics(pe_ratio);
CREATE INDEX idx_metrics_factor_momentum ON symbol_daily_metrics(factor_momentum DESC);
```

**Why denormalize factors into this table?**
- Dashboard needs to sort/filter by factor exposure (e.g., "show me highest momentum stocks")
- Single query returns all columns - no joins needed
- ~100 symbols × 1 row each = tiny table, fast full scans
- Updated once per day during batch processing

**Data flow:**
```
Batch Processing:
├── market_data → calculate returns → symbol_daily_metrics.return_*
├── company_profiles → copy to → symbol_daily_metrics.sector, pe_ratio, etc.
└── symbol_factor_exposures → denormalize → symbol_daily_metrics.factor_*
```

---

## Symbol Returns as Single Source of Truth

**Key Insight**: Symbol returns should be calculated ONCE per symbol, then reused for:
1. Portfolio P&L calculation (position_weight × symbol_return)
2. Symbol Dashboard display
3. Factor regression inputs (if needed)

### Current Problem (Redundant Calculation)

```
AAPL in Portfolio A, B, C:
├── P&L Calculator: Fetch AAPL prices → calculate return (×3 redundant!)
├── Dashboard: Fetch AAPL prices → calculate return (×1 more!)
└── Total: 4 calculations of the same return
```

### New Approach (Calculate Once)

```
Phase 1.5: Symbol Returns
├── For each unique symbol in universe:
│   ├── Fetch prices from market_data
│   ├── Calculate return_1d, return_mtd, return_ytd, etc.
│   └── Store in symbol_daily_metrics
└── Done ONCE per symbol

Phase 2: Portfolio P&L (uses cached returns)
├── For each portfolio:
│   ├── Get positions with weights
│   ├── Lookup symbol returns from symbol_daily_metrics
│   ├── portfolio_pnl = Σ(position_weight × position_value × symbol_return_1d)
│   └── Update snapshots
└── No price fetching, just lookups!
```

### Impact on pnl_calculator.py

```python
# OLD: Calculate returns from prices for each position
async def calculate_position_pnl(position, calculation_date):
    prices = await get_prices(position.symbol, calculation_date)
    daily_return = (prices.close - prices.prev_close) / prices.prev_close
    return position.market_value * daily_return

# NEW: Lookup pre-calculated symbol returns
async def calculate_position_pnl(position, symbol_metrics: Dict[str, SymbolDailyMetrics]):
    symbol_return = symbol_metrics[position.symbol].return_1d
    return position.market_value * symbol_return
```

### Efficiency Gains

| Scenario | Old (per-position) | New (per-symbol) | Savings |
|----------|-------------------|------------------|---------|
| AAPL in 3 portfolios | 3 calculations | 1 calculation | 67% |
| 63 positions, 50 unique symbols | 63 calculations | 50 calculations | 21% |
| 120 days backfill | 63 × 120 = 7,560 | 50 × 120 = 6,000 | 21% |

### Dependency Change

```
OLD Order:
Phase 1: Market Data
Phase 2: P&L (calculates returns internally)
Phase 7: Dashboard (calculates returns again)

NEW Order:
Phase 1: Market Data (prices only)
Phase 1.5: Symbol Returns → symbol_daily_metrics  ← NEW, runs EARLY
Phase 2: P&L (lookups from symbol_daily_metrics)  ← MODIFIED
Phase 7: Dashboard (already populated)            ← SIMPLIFIED
```

### What Happens to `position_factor_exposures`?

**Decision: Dual-Write During Validation**

Both tables will be written during the transition period:

```
Batch Processing Flow (Dual-Write Mode):
├── Phase 0.5: Calculate symbol factors → symbol_factor_exposures
├── Phase 6: Calculate position factors → position_factor_exposures (existing)
└── Post-batch: Run comparison script → validate consistency
```

**Transition Timeline**:
1. **Dual-write mode** (Weeks 1-4): Write to both tables, run comparison daily
2. **Validation mode** (Weeks 3-4): Review comparison reports, investigate discrepancies
3. **Deprecation mode** (Week 5+): Stop writing to position_factor_exposures (only after 99.9%+ match rate)

**Key Validation Points**:
- Same symbol in different portfolios should have identical betas
- Options: `position_beta = delta × symbol_beta`
- Portfolio aggregation should match within tolerance

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

**Critical Change**: Symbol returns must be calculated BEFORE P&L calculation.

```
NEW Batch Phase Order:
Phase 0:   Company Profiles (existing)
Phase 0.5: Universe Factor Calculation → symbol_factor_exposures
Phase 1:   Market Data Fetch (prices only)
Phase 1.5: Symbol Returns & Metrics → symbol_daily_metrics  ← NEW, CRITICAL
Phase 2:   Portfolio P&L (uses symbol_daily_metrics.return_1d)  ← MODIFIED
Phase 2.5: Position Market Values (existing)
Phase 3-5: Snapshots, Greeks, Stress Tests (existing)
Phase 6:   Analytics (uses symbol_factor_exposures)  ← MODIFIED
```

```python
# In batch_orchestrator.py

async def run_daily_batch_with_backfill(...):
    # Phase 0: Company Profiles (existing)
    ...

    # NEW: Phase 0.5 - Universe Factor Calculation
    logger.info(f"Phase 0.5: Calculating universe factor exposures")
    universe_result = await calculate_universe_factors(calculation_date)
    logger.info(f"[FACTORS] {universe_result['symbols_calculated']} symbols")

    # Phase 1: Market Data (existing - fetches prices)
    ...

    # NEW: Phase 1.5 - Symbol Returns & Metrics (BEFORE P&L!)
    logger.info(f"Phase 1.5: Calculating symbol returns")
    metrics_result = await calculate_symbol_metrics(calculation_date)
    logger.info(f"[METRICS] {metrics_result['symbols_updated']} symbols")

    # Phase 2: Portfolio P&L (MODIFIED - uses cached symbol returns)
    symbol_metrics = await load_symbol_metrics(calculation_date)  # Bulk load
    for portfolio in portfolios:
        await calculate_portfolio_pnl(portfolio, symbol_metrics)  # Lookups only

    # Phase 2.5-6: Existing phases...
```

### Phase 5: Symbol Metrics Service (2-3 hours)

Calculates returns and consolidates metrics for all symbols. **Runs EARLY in batch (Phase 1.5)**.

```python
# app/services/symbol_metrics_service.py

async def calculate_symbol_metrics(calculation_date: date) -> Dict:
    """
    Calculate returns and populate symbol_daily_metrics.

    MUST run before P&L calculation (Phase 1.5).
    P&L calculator will lookup returns from this table.
    """
    async with AsyncSessionLocal() as db:
        # Get all unique symbols from positions + universe
        symbols = await get_all_active_symbols(db)

        # Bulk fetch prices for all symbols (single query)
        prices = await bulk_fetch_prices(db, symbols, calculation_date)

        for symbol in symbols:
            symbol_prices = prices.get(symbol, {})

            # Calculate returns
            return_1d = calculate_daily_return(symbol_prices)
            return_mtd = calculate_mtd_return(symbol_prices, calculation_date)
            return_ytd = calculate_ytd_return(symbol_prices, calculation_date)

            # Get company profile data
            profile = await get_company_profile(db, symbol)

            # Upsert into symbol_daily_metrics
            await upsert_symbol_metrics(db, symbol, {
                'metrics_date': calculation_date,
                'current_price': symbol_prices.get('close'),
                'return_1d': return_1d,
                'return_mtd': return_mtd,
                'return_ytd': return_ytd,
                'market_cap': profile.market_cap if profile else None,
                'pe_ratio': profile.pe_ratio if profile else None,
                'sector': profile.sector if profile else None,
                # Factor exposures populated later in Phase 6
            })

        await db.commit()
        return {'symbols_updated': len(symbols)}
```

### Phase 6: Testing & Validation (2-3 hours)
1. Verify symbol betas match position betas (for same symbol)
2. Verify portfolio aggregation matches current calculation
3. Performance benchmarks: before vs after
4. Test parallelization under load

---

## Validation Script: Compare Position vs Symbol Factors

A critical component of the dual-write approach is a comparison script that validates consistency between the two calculation methods.

### Script Location
`backend/scripts/validation/compare_factor_exposures.py`

### What It Compares

For each position on each calculation date:

| Metric | Position-Level (Current) | Symbol-Level (New) |
|--------|--------------------------|-------------------|
| Factor beta | Direct from `position_factor_exposures` | Lookup from `symbol_factor_exposures` |
| Portfolio exposure | Sum of position betas × weights | Sum of symbol betas × weights |
| Options adjustment | Pre-computed with delta | Computed as delta × symbol_beta |

### Comparison Script Design

```python
"""
compare_factor_exposures.py

Validates that symbol-level factor calculations match position-level calculations.
Run after dual-write batch processing to ensure consistency before deprecation.
"""

import asyncio
from datetime import date, timedelta
from typing import Dict, List, Tuple
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.market_data import PositionFactorExposure
from app.models.symbol_factor_exposures import SymbolFactorExposure
from app.models.positions import Position

# Tolerance for floating point comparison
BETA_TOLERANCE = 0.0001  # 0.01% difference allowed
PORTFOLIO_TOLERANCE = 0.001  # 0.1% difference for aggregated values


async def compare_for_date(calculation_date: date) -> Dict:
    """Compare position-level vs symbol-level factors for a single date."""

    async with AsyncSessionLocal() as db:
        # Get all position factor exposures for this date
        position_factors = await db.execute(
            select(PositionFactorExposure)
            .where(PositionFactorExposure.calculation_date == calculation_date)
        )
        position_factors = position_factors.scalars().all()

        # Get corresponding symbol factors
        symbol_factors = await db.execute(
            select(SymbolFactorExposure)
            .where(SymbolFactorExposure.calculation_date == calculation_date)
        )
        symbol_factors = symbol_factors.scalars().all()

        # Build lookup: {symbol: {factor_name: beta}}
        symbol_betas = {}
        for sf in symbol_factors:
            if sf.symbol not in symbol_betas:
                symbol_betas[sf.symbol] = {}
            symbol_betas[sf.symbol][sf.factor_name] = sf.beta_value

        # Compare each position
        discrepancies = []
        matches = 0
        missing_symbols = set()

        for pf in position_factors:
            position = await db.get(Position, pf.position_id)
            symbol = position.symbol

            # Get symbol-level beta
            if symbol not in symbol_betas:
                missing_symbols.add(symbol)
                continue

            symbol_beta = symbol_betas.get(symbol, {}).get(pf.factor_name)
            if symbol_beta is None:
                missing_symbols.add(f"{symbol}:{pf.factor_name}")
                continue

            # For options, apply delta adjustment
            if position.is_option:
                expected_beta = position.delta * symbol_beta
            else:
                expected_beta = symbol_beta

            # Compare
            diff = abs(pf.beta_value - expected_beta)
            if diff > BETA_TOLERANCE:
                discrepancies.append({
                    'position_id': str(pf.position_id),
                    'symbol': symbol,
                    'factor': pf.factor_name,
                    'position_beta': float(pf.beta_value),
                    'symbol_beta': float(expected_beta),
                    'difference': float(diff),
                    'is_option': position.is_option
                })
            else:
                matches += 1

        return {
            'date': calculation_date.isoformat(),
            'total_comparisons': len(position_factors),
            'matches': matches,
            'discrepancies': discrepancies,
            'discrepancy_count': len(discrepancies),
            'missing_symbols': list(missing_symbols),
            'match_rate': matches / len(position_factors) if position_factors else 1.0
        }


async def compare_portfolio_aggregation(
    portfolio_id: str,
    calculation_date: date
) -> Dict:
    """
    Compare portfolio-level factor exposure calculated two ways:
    1. Sum of position_factor_exposures (current method)
    2. Sum of symbol_factor_exposures × position weights (new method)
    """

    async with AsyncSessionLocal() as db:
        # Method 1: Current approach (position-level)
        # ... aggregate from position_factor_exposures

        # Method 2: New approach (symbol-level)
        # ... aggregate from symbol_factor_exposures × weights

        # Compare
        pass  # Implementation details


async def run_full_comparison(
    start_date: date,
    end_date: date
) -> Dict:
    """Run comparison across date range and generate report."""

    results = []
    current = start_date

    while current <= end_date:
        result = await compare_for_date(current)
        results.append(result)
        current += timedelta(days=1)

    # Summary statistics
    total_comparisons = sum(r['total_comparisons'] for r in results)
    total_matches = sum(r['matches'] for r in results)
    total_discrepancies = sum(r['discrepancy_count'] for r in results)

    return {
        'date_range': f"{start_date} to {end_date}",
        'dates_analyzed': len(results),
        'total_comparisons': total_comparisons,
        'total_matches': total_matches,
        'total_discrepancies': total_discrepancies,
        'overall_match_rate': total_matches / total_comparisons if total_comparisons else 1.0,
        'daily_results': results,
        'recommendation': 'SAFE_TO_DEPRECATE' if total_discrepancies == 0 else 'INVESTIGATE_DISCREPANCIES'
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', required=True)
    parser.add_argument('--end-date', required=True)
    parser.add_argument('--output', default='factor_comparison_report.json')
    args = parser.parse_args()

    result = asyncio.run(run_full_comparison(
        date.fromisoformat(args.start_date),
        date.fromisoformat(args.end_date)
    ))

    # Write report
    import json
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Match rate: {result['overall_match_rate']:.2%}")
    print(f"Recommendation: {result['recommendation']}")
```

### Expected Discrepancy Sources

| Source | Cause | Expected? |
|--------|-------|-----------|
| Floating point | Minor rounding differences | Yes, within tolerance |
| Options delta | Delta × symbol_beta vs pre-computed | Should match exactly |
| Stale cache | Position calculated at different time | No, investigate |
| Missing symbol | Symbol not in universe | No, add to universe |
| Regression differences | Different data windows | No, align windows |

### Usage

```bash
# Run comparison for recent batch
cd backend
uv run python scripts/validation/compare_factor_exposures.py \
    --start-date 2025-12-01 \
    --end-date 2025-12-19 \
    --output factor_comparison_report.json

# Review output
cat factor_comparison_report.json | jq '.overall_match_rate, .recommendation'
```

### Success Criteria for Deprecation

Before deprecating `position_factor_exposures`:
1. **Match rate > 99.9%** across 30+ days
2. **Zero unexplained discrepancies** (all within tolerance or documented)
3. **Options handling validated** for all option positions
4. **Performance improvement confirmed** (5x target met)

---

## Symbol Dashboard API

New endpoint to power the Symbol Universe dashboard page.

### Endpoint: `GET /api/v1/data/symbols`

Returns all symbols with current metrics, supporting sorting and filtering.

```python
# app/api/v1/data.py

@router.get("/symbols")
async def get_symbol_universe(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    # Sorting
    sort_by: str = Query("market_cap", regex="^(symbol|sector|market_cap|pe_ratio|ps_ratio|return_1d|return_ytd|factor_.*)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    # Filtering
    sector: Optional[str] = Query(None),
    min_market_cap: Optional[float] = Query(None),
    max_pe_ratio: Optional[float] = Query(None),
    # Pagination
    limit: int = Query(100, le=500),
    offset: int = Query(0),
) -> SymbolUniverseResponse:
    """
    Get all symbols with current metrics for dashboard display.

    Single query against symbol_daily_metrics table - no joins needed.
    Supports sorting by any column and filtering by sector/valuation.
    """
    stmt = select(SymbolDailyMetrics)

    # Apply filters
    if sector:
        stmt = stmt.where(SymbolDailyMetrics.sector == sector)
    if min_market_cap:
        stmt = stmt.where(SymbolDailyMetrics.market_cap >= min_market_cap)
    if max_pe_ratio:
        stmt = stmt.where(SymbolDailyMetrics.pe_ratio <= max_pe_ratio)

    # Apply sorting
    sort_column = getattr(SymbolDailyMetrics, sort_by)
    if sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc().nulls_last())
    else:
        stmt = stmt.order_by(sort_column.asc().nulls_last())

    # Pagination
    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    symbols = result.scalars().all()

    return SymbolUniverseResponse(
        symbols=[SymbolMetricsSchema.from_orm(s) for s in symbols],
        total_count=await get_total_count(db, sector, min_market_cap, max_pe_ratio),
        metrics_date=symbols[0].metrics_date if symbols else None
    )
```

### Response Schema

```python
class SymbolMetricsSchema(BaseModel):
    symbol: str
    company_name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]

    # Price & Returns
    current_price: Optional[float]
    return_1d: Optional[float]
    return_mtd: Optional[float]
    return_ytd: Optional[float]
    return_1y: Optional[float]

    # Valuation
    market_cap: Optional[float]
    enterprise_value: Optional[float]
    pe_ratio: Optional[float]
    ps_ratio: Optional[float]

    # Factor Exposures
    factor_value: Optional[float]
    factor_growth: Optional[float]
    factor_momentum: Optional[float]
    factor_quality: Optional[float]
    factor_size: Optional[float]
    factor_low_vol: Optional[float]

    data_quality_score: Optional[float]

class SymbolUniverseResponse(BaseModel):
    symbols: List[SymbolMetricsSchema]
    total_count: int
    metrics_date: Optional[date]
```

### Frontend Usage

```typescript
// services/symbolsApi.ts
export const symbolsApi = {
  getUniverse: async (params: {
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
    sector?: string;
    minMarketCap?: number;
  }) => {
    const response = await apiClient.get('/data/symbols', { params });
    return response.data;
  }
};

// Example: Sort by momentum factor, descending
const highMomentumStocks = await symbolsApi.getUniverse({
  sortBy: 'factor_momentum',
  sortOrder: 'desc',
  limit: 20
});
```

### Query Performance

| Operation | Expected Time |
|-----------|--------------|
| Full table scan (100 symbols) | <50ms |
| Filtered by sector | <20ms |
| Sorted by any column | <50ms (indexed) |

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

### Step 1: Deploy Schema & Comparison Script (Day 1)
- Run migration to create `symbol_factor_exposures` table
- Deploy `compare_factor_exposures.py` validation script
- No batch processing changes yet

### Step 2: Enable Dual-Write Mode (Day 2-3)
- Add Phase 0.5 to batch orchestrator (symbol-level calculation)
- Keep existing Phase 6 position-level calculation
- Both tables populated on each batch run

### Step 3: Daily Comparison Runs (Days 4-30)
- Run comparison script after each batch:
  ```bash
  uv run python scripts/validation/compare_factor_exposures.py \
      --start-date $(date -d "yesterday" +%Y-%m-%d) \
      --end-date $(date +%Y-%m-%d)
  ```
- Review discrepancies, fix root causes
- Target: 99.9%+ match rate for 7+ consecutive days

### Step 4: Switch Read Path (Day 14+, after validation)
- Portfolio aggregation reads from `symbol_factor_exposures`
- Falls back to `position_factor_exposures` if missing
- Monitor for issues

### Step 5: Deprecate Position-Level (Day 30+)
- Only proceed after comparison script shows 99.9%+ match for 14+ days
- Stop writing to `position_factor_exposures` for factor betas
- Keep table for historical data reference
- Clean up old code paths

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

### New Files - Core Architecture
- `app/calculations/symbol_factors.py` - Core symbol-level calculation
- `app/services/portfolio_factor_service.py` - Portfolio aggregation
- `app/models/symbol_factor_exposures.py` - SQLAlchemy model for factor table
- `app/models/symbol_daily_metrics.py` - SQLAlchemy model for dashboard table
- `app/models/symbol_universe.py` - SQLAlchemy model for universe tracking
- `alembic/versions/xxx_add_symbol_tables.py` - Migration for all 3 new tables
- `scripts/validation/compare_factor_exposures.py` - Comparison script for dual-write validation

### New Files - Symbol Dashboard
- `app/services/symbol_metrics_service.py` - Consolidates metrics for dashboard
- `app/api/v1/schemas/symbols.py` - Pydantic schemas for API response
- `frontend/src/services/symbolsApi.ts` - Frontend API client

### Modified Files
- `app/batch/batch_orchestrator.py` - Add Phase 0.5 (factors), Phase 1.5 (returns)
- `app/batch/pnl_calculator.py` - **Use cached symbol returns instead of calculating**
- `app/batch/analytics_runner.py` - Use new aggregation service
- `app/calculations/factors_ridge.py` - Refactor to use symbol-level
- `app/api/v1/data.py` - Add `/symbols` endpoint

### Deprecated (Eventually, after validation passes)
- Position-level factor calculation in `factors_ridge.py`
- Position-level caching in `factor_utils.py`
- Writing to `position_factor_exposures` for factor betas
- Per-position return calculation in `pnl_calculator.py`

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Factor calculation time (100 symbols) | ~100s | ~20s |
| Redundant calculations (shared symbols) | Yes | None |
| Parallel batch errors | N/A | 0 |
| Portfolio aggregation time | ~10s | <1s |
| Symbol Dashboard API response | N/A | <100ms |
| Dashboard table size | N/A | ~100 rows |

---

## Performance Optimization: Caching & Indexing

### Predicted Calculation Time Impact

| Scenario | Current | With Symbol Architecture | Improvement |
|----------|---------|--------------------------|-------------|
| Daily batch (1 date, 63 positions) | ~45-60s | ~25-35s | **35-45%** |
| Backfill (120 dates) | ~90+ min | ~40-50 min | **45-55%** |
| Symbol Dashboard API | N/A (joins) | <50ms | **New capability** |

**Why daily improvement is modest:**
- `PriceCache` already bulk-loads prices (we have this)
- Factor regression (Ridge/Spread) dominates daily time
- Improvement comes from eliminating redundant return calculations

**Where big wins come from:**
- Backfills: Symbol-level caching across dates
- Dashboard: Single-table queries vs multi-table joins
- Parallel batches: Safe parallelization pattern

### Current Indexes (Already Have)

```sql
-- market_data_cache (prices) ✅
ix_market_data_cache_symbol
ix_market_data_cache_date
idx_market_data_cache_symbol_date (composite)
idx_market_data_valid_prices (partial - WHERE close > 0)

-- position_factor_exposures ✅
idx_pfe_factor_date
idx_pfe_position_date
idx_pfe_calculation_date
```

### New Indexes Needed for symbol_daily_metrics

```sql
-- Primary lookup (dashboard default sort)
CREATE INDEX idx_metrics_date ON symbol_daily_metrics(metrics_date);

-- Sort/filter by key columns
CREATE INDEX idx_metrics_sector ON symbol_daily_metrics(sector);
CREATE INDEX idx_metrics_market_cap ON symbol_daily_metrics(market_cap DESC NULLS LAST);
CREATE INDEX idx_metrics_return_ytd ON symbol_daily_metrics(return_ytd DESC NULLS LAST);
CREATE INDEX idx_metrics_pe ON symbol_daily_metrics(pe_ratio NULLS LAST);

-- Factor exposure sorts (dashboard "sort by momentum")
CREATE INDEX idx_metrics_factor_momentum ON symbol_daily_metrics(factor_momentum DESC NULLS LAST);
CREATE INDEX idx_metrics_factor_value ON symbol_daily_metrics(factor_value DESC NULLS LAST);

-- Composite for common query pattern
CREATE INDEX idx_metrics_sector_cap ON symbol_daily_metrics(sector, market_cap DESC NULLS LAST);
```

### New Indexes Needed for symbol_factor_exposures

```sql
-- Primary lookup pattern (symbol + date)
CREATE INDEX idx_symbol_factor_lookup ON symbol_factor_exposures(symbol, calculation_date);

-- Batch processing (find uncached symbols)
CREATE INDEX idx_symbol_factor_date ON symbol_factor_exposures(calculation_date);

-- Factor type filtering
CREATE INDEX idx_symbol_factor_method ON symbol_factor_exposures(calculation_method, calculation_date);
```

### Caching Strategy

**What we already have:**
- `PriceCache` class for bulk price loading (300x speedup claimed)

**What we'll add:**

```python
# 1. Symbol Returns Cache (new in Phase 1.5)
class SymbolReturnsCache:
    """
    Cache symbol returns for the batch run.
    Loaded once in Phase 1.5, used by P&L and analytics.
    """
    _returns: Dict[Tuple[str, date], SymbolReturns] = {}

    async def load_for_date(self, db: AsyncSession, calc_date: date):
        # Bulk load from symbol_daily_metrics
        stmt = select(SymbolDailyMetrics).where(
            SymbolDailyMetrics.metrics_date == calc_date
        )
        result = await db.execute(stmt)
        for row in result.scalars():
            self._returns[(row.symbol, calc_date)] = row

    def get_return(self, symbol: str, calc_date: date) -> Optional[float]:
        return self._returns.get((symbol, calc_date))


# 2. Symbol Factors Cache (new in Phase 0.5)
class SymbolFactorsCache:
    """
    Cache symbol factor betas for portfolio aggregation.
    Loaded after Phase 0.5, used by Phase 6 analytics.
    """
    _factors: Dict[Tuple[str, date], Dict[str, float]] = {}

    async def load_for_symbols(
        self,
        db: AsyncSession,
        symbols: List[str],
        calc_date: date
    ):
        # Bulk load from symbol_factor_exposures
        stmt = select(SymbolFactorExposure).where(
            and_(
                SymbolFactorExposure.symbol.in_(symbols),
                SymbolFactorExposure.calculation_date == calc_date
            )
        )
        # ... build cache
```

### Cache Lifecycle in Batch

```
Batch Run for Date D:
├── Phase 0.5: Calculate symbol factors → symbol_factor_exposures
│   └── SymbolFactorsCache.load_for_symbols() after calculation
├── Phase 1: Fetch market data → market_data_cache
│   └── PriceCache.load_single_date() (existing)
├── Phase 1.5: Calculate symbol returns → symbol_daily_metrics
│   └── SymbolReturnsCache.load_for_date() after calculation
├── Phase 2: Portfolio P&L
│   └── Uses SymbolReturnsCache.get_return() (no DB queries!)
├── Phase 6: Analytics
│   └── Uses SymbolFactorsCache.get_factor() (no DB queries!)
└── End of date: Clear all caches for next date
```

### Are We Using Existing Indexes?

**Yes, but could be better:**

```python
# Current query pattern (uses ix_market_data_cache_symbol)
SELECT * FROM market_data_cache WHERE symbol = 'AAPL' AND date = '2025-12-19'

# Better query pattern (uses idx_market_data_cache_symbol_date composite)
SELECT symbol, date, close FROM market_data_cache
WHERE symbol IN ('AAPL', 'MSFT', ...) AND date = '2025-12-19'
```

The `PriceCache` class already does bulk loading, which uses the composite index efficiently.

**Key insight**: The new `symbol_daily_metrics` table will be tiny (~100 rows), so even without indexes, full table scans are fast. Indexes mainly help with sorting.

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
