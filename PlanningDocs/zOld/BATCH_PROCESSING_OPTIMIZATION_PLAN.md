# Batch Processing Optimization Plan

**Created**: 2025-12-20
**Status**: Planning
**Estimated Impact**: 60-75% reduction in batch processing time

---

## Executive Summary

Current batch processing takes ~16-20 minutes for a full backfill (July 1 - Dec 19, 2025). The primary bottlenecks are sequential processing loops that can be parallelized without major architectural changes.

**Target**: Reduce batch processing time to ~5-7 minutes.

---

## Current Architecture

### Phase Sequence
```
Phase 0: Company Profile Sync (current date only)
    ↓
Phase 1: Market Data Collection (365-day lookback, YFinance primary)
    ↓
Phase 2: Fundamental Data Collection
    ↓
Phase 2.5: Snapshot Cleanup (idempotency)
    ↓
Phase 3: P&L Calculation & Snapshots
    ↓
Phase 4: Position Market Value Updates
    ↓
Phase 5: Sector Tag Restoration
    ↓
Phase 6: Risk Analytics (8 calculation engines)
```

### Key Files
| File | Lines | Purpose |
|------|-------|---------|
| `batch_orchestrator.py` | 1,419 | Main orchestration + backfill |
| `analytics_runner.py` | 995 | Phase 6 analytics |
| `market_data_collector.py` | 953 | Phase 1 data fetching |
| `pnl_calculator.py` | 591 | Phase 3 calculations |
| `fundamentals_collector.py` | 360 | Phase 2 |

---

## Identified Bottlenecks

### 1. Sequential Portfolio Processing (CRITICAL)
**Location**: `analytics_runner.py:130-153`
```python
for portfolio in portfolios:  # Sequential loop
    report = await self.run_portfolio_analytics(portfolio_id=portfolio.id, ...)
```
**Impact**: 3 portfolios = 3x slowdown (each blocks until complete)

### 2. Sequential Analytics Jobs per Portfolio (CRITICAL)
**Location**: `analytics_runner.py:214-222`
```python
for job_name, job_func in analytics_jobs:  # 9 jobs run sequentially
    raw_result = await job_func(db, portfolio_id, calculation_date)
```
**Impact**: 9 jobs × ~1-2s each = 9-18s per portfolio

### 3. Sequential Date Processing in Backfill (HIGH)
**Location**: `batch_orchestrator.py:191-206`
```python
for i, calc_date in enumerate(missing_dates, 1):  # Each date sequential
    phase1_result = await market_data_collector.collect_daily_market_data(...)
```
**Impact**: 20-day backfill = 20 sequential iterations

### 4. Single AsyncSession Constraint (ARCHITECTURAL)
**Location**: `analytics_runner.py:187`
```python
# Run analytics sequentially (single session can't handle concurrent ops)
```
**Impact**: Blocks parallel portfolio processing

---

## Implementation Plan

### Phase 1: Quick Wins (1-2 hours)
**Expected Improvement**: 5-15%

#### 1.1 Increase Batch Insert Size for Backfills
**File**: `app/batch/market_data_collector.py:797`

**Current**:
```python
batch_size = 1000
```

**Change to**:
```python
batch_size = 5000  # Larger batches for initial backfills
```

**Rationale**: Initial backfills have 100K+ records. Larger batches reduce transaction overhead.

#### 1.2 Batch Company Profile Fetches
**File**: `app/services/market_data_service.py:1293-1325`

**Current**:
```python
for symbol in symbols:
    profile = await self._fetch_company_profile_yfinance(symbol)
```

**Change to**:
```python
# Batch into groups of 10 (yfinance supports multiple tickers)
batch_size = 10
for i in range(0, len(symbols), batch_size):
    batch = symbols[i:i + batch_size]
    profiles = await self._fetch_company_profiles_batch_yfinance(batch)
```

---

### Phase 2: Parallelize Analytics Jobs (2-4 hours)
**Expected Improvement**: 60% reduction in Phase 6 time

#### 2.1 Dependency Analysis

| Job | Dependencies | Can Parallelize? |
|-----|-------------|------------------|
| Market Beta (90D) | Market data | Yes - Group A |
| Provider Beta (1Y) | Market data + profiles | Yes - Group A |
| IR Beta | Interest rates | Yes - Group A |
| Spread Factors | Market data | Yes - Group B |
| Ridge Factors | Market data | Yes - Group B |
| Volatility Analytics | Market data | Yes - Group C |
| Correlations | Market data | Yes - Group C |
| Sector Analysis | Company profiles | Yes - Group D |
| Stress Testing | Factor calculations | No - depends on Group B |

#### 2.2 Implementation

**File**: `app/batch/analytics_runner.py:214-222`

**Current**:
```python
for job_name, job_func in analytics_jobs:
    raw_result = await job_func(db, portfolio_id, calculation_date)
```

**Change to**:
```python
import asyncio

# Group A: Beta calculations (independent)
beta_tasks = [
    self._calculate_market_beta(db, portfolio_id, calculation_date),
    self._calculate_provider_beta(db, portfolio_id, calculation_date),
    self._calculate_ir_beta(db, portfolio_id, calculation_date),
]
beta_results = await asyncio.gather(*beta_tasks, return_exceptions=True)
await db.commit()

# Group B: Factor calculations (independent)
factor_tasks = [
    self._calculate_spread_factors(db, portfolio_id, calculation_date),
    self._calculate_ridge_factors(db, portfolio_id, calculation_date),
]
factor_results = await asyncio.gather(*factor_tasks, return_exceptions=True)
await db.commit()

# Group C: Vol/Correlation (independent)
vol_corr_tasks = [
    self._calculate_volatility(db, portfolio_id, calculation_date),
    self._calculate_correlations(db, portfolio_id, calculation_date),
]
vol_corr_results = await asyncio.gather(*vol_corr_tasks, return_exceptions=True)
await db.commit()

# Group D: Sector analysis (independent)
sector_result = await self._calculate_sector_analysis(db, portfolio_id, calculation_date)
await db.commit()

# Group E: Stress testing (depends on Group B factors)
stress_result = await self._calculate_stress_testing(db, portfolio_id, calculation_date)
await db.commit()
```

**Time Impact**:
- Current: 9 jobs × 1.5s avg = 13.5s per portfolio
- After: max(Group A) + max(Group B) + max(Group C) + Group D + Group E ≈ 5-6s per portfolio

---

### Phase 3: Parallelize Portfolio Processing (3-5 hours)
**Expected Improvement**: 60-75% reduction in Phase 6 time

#### 3.1 Create Isolated Session per Portfolio

**File**: `app/batch/analytics_runner.py:130-153`

**Current**:
```python
async def run_all_portfolio_analytics(self, db: AsyncSession, ...):
    for portfolio in portfolios:
        report = await self.run_portfolio_analytics(portfolio_id=portfolio.id, db=db, ...)
```

**Change to**:
```python
async def run_all_portfolio_analytics(self, ...):
    async def _run_portfolio_isolated(portfolio_id: UUID, calculation_date: date):
        """Run analytics for single portfolio with isolated session."""
        async with AsyncSessionLocal() as isolated_db:
            try:
                return await self.run_portfolio_analytics(
                    portfolio_id=portfolio_id,
                    db=isolated_db,
                    calculation_date=calculation_date,
                    ...
                )
            except Exception as e:
                logger.error(f"Portfolio {portfolio_id} analytics failed: {e}")
                return None

    # Run all portfolios in parallel
    tasks = [
        _run_portfolio_isolated(portfolio.id, calculation_date)
        for portfolio in portfolios
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    successful = [r for r in results if r is not None and not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, Exception)]

    if failed:
        logger.warning(f"{len(failed)} portfolios failed analytics")
```

**Time Impact**:
- Current: 3 portfolios × 13.5s = 40.5s
- After Phase 2: 3 portfolios × 5.5s = 16.5s (sequential)
- After Phase 3: max(3 portfolios) × 5.5s = 5.5s (parallel)

---

### Phase 4: Parallelize Date Processing in Backfill (4-6 hours)
**Expected Improvement**: 50-70% reduction in backfill time

#### 4.1 Parallel Phase 1 (Market Data Collection)

**File**: `app/batch/batch_orchestrator.py:191-206`

**Current**:
```python
for i, calc_date in enumerate(missing_dates, 1):
    async with AsyncSessionLocal() as db:
        phase1_result = await market_data_collector.collect_daily_market_data(
            calc_date=calc_date, ...
        )
```

**Change to**:
```python
async def _collect_market_data_for_date(calc_date: date):
    async with AsyncSessionLocal() as db:
        return await market_data_collector.collect_daily_market_data(
            calc_date=calc_date, db=db, ...
        )

# Run Phase 1 for all dates in parallel (batched to avoid overwhelming API)
batch_size = 5  # Process 5 dates at a time
for i in range(0, len(missing_dates), batch_size):
    batch = missing_dates[i:i + batch_size]
    tasks = [_collect_market_data_for_date(d) for d in batch]
    await asyncio.gather(*tasks, return_exceptions=True)
```

#### 4.2 Parallel Phases 2-6

**File**: `app/batch/batch_orchestrator.py:252-277`

**Current**:
```python
for i, calc_date in enumerate(missing_dates, 1):
    async with AsyncSessionLocal() as db:
        result = await self._run_phases_2_through_6(calc_date=calc_date, db=db, ...)
```

**Change to**:
```python
# After Phase 1 completes for all dates, load price cache once
price_cache = PriceCache()
await price_cache.load_date_range(
    start_date=missing_dates[0],
    end_date=missing_dates[-1],
    symbols=all_symbols
)

async def _run_phases_2_6_for_date(calc_date: date):
    async with AsyncSessionLocal() as db:
        return await self._run_phases_2_through_6(
            calc_date=calc_date, db=db, price_cache=price_cache, ...
        )

# Run Phases 2-6 in parallel batches
batch_size = 5
for i in range(0, len(missing_dates), batch_size):
    batch = missing_dates[i:i + batch_size]
    tasks = [_run_phases_2_6_for_date(d) for d in batch]
    await asyncio.gather(*tasks, return_exceptions=True)
```

---

## Testing Strategy

### Unit Tests
1. Test parallel analytics jobs produce same results as sequential
2. Test isolated sessions don't create transaction conflicts
3. Test parallel date processing maintains data integrity

### Integration Tests
1. Run full backfill on demo portfolios
2. Compare calculation results before/after optimization
3. Verify no race conditions in database writes

### Performance Benchmarks
```bash
# Before optimization
time python scripts/railway/trigger_railway_fix.py --env sandbox --start-date 2025-07-01 --end-date 2025-12-19

# After each phase
# Record: total time, Phase 6 time, memory usage
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Race conditions in parallel writes | Use isolated sessions per portfolio/date |
| API rate limiting (yfinance) | Batch requests, add delays between batches |
| Memory pressure from parallel sessions | Limit concurrency (batch_size = 5) |
| Transaction deadlocks | Commit after each independent group |
| Partial failures in parallel execution | Use `return_exceptions=True`, log failures |

---

## Rollback Plan

If issues arise after deployment:

1. **Feature flag**: Add `PARALLEL_BATCH_ENABLED=false` env var
2. **Code path**: Keep sequential code path, switch via flag
3. **Monitoring**: Add timing logs to detect performance regressions

```python
if settings.PARALLEL_BATCH_ENABLED:
    results = await asyncio.gather(*tasks)
else:
    results = [await task for task in tasks]  # Sequential fallback
```

---

## Timeline

| Phase | Effort | Expected Improvement |
|-------|--------|---------------------|
| Phase 1: Quick Wins | 1-2 hours | 5-15% |
| Phase 2: Parallel Analytics Jobs | 2-4 hours | 60% of Phase 6 |
| Phase 3: Parallel Portfolios | 3-5 hours | 60-75% of Phase 6 |
| Phase 4: Parallel Dates | 4-6 hours | 50-70% of backfill |
| Testing & Validation | 2-3 hours | - |
| **Total** | **12-20 hours** | **60-75% overall** |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Full backfill (6 months) | ~16-20 min | ~5-7 min |
| Phase 6 (analytics) | ~40-50s | ~10-15s |
| Daily batch run | ~3-5 min | ~1-2 min |

---

## Appendix: Code Locations

| Component | File | Lines |
|-----------|------|-------|
| Main orchestrator | `app/batch/batch_orchestrator.py` | 1-1419 |
| Analytics runner | `app/batch/analytics_runner.py` | 1-995 |
| Market data collector | `app/batch/market_data_collector.py` | 1-953 |
| P&L calculator | `app/batch/pnl_calculator.py` | 1-591 |
| Price cache | `app/cache/price_cache.py` | (already optimized) |
| Company profiles | `app/services/market_data_service.py` | 1293-1325 |
