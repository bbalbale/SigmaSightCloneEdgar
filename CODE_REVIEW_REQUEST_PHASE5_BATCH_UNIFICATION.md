# Code Review Request: Phase 5 Batch Function Unification

**Date**: January 8, 2026
**Author**: Claude Opus 4.5
**Reviewer**: Advanced AI Coding Agent
**Branch**: main (commits `337e7d39` and `3ae56503`)

---

## Summary

This PR implements Phase 5 of the Testscotty batch processing debug plan: **Unified Batch Function with Symbol Scoping**. The goal is to fix a critical performance issue where onboarding batches were processing **1,193 symbols** when only **~30** were needed, causing ~4 hour runtimes and API rate limiting.

## Problem Statement

When a user onboarded via CSV upload (Testscotty3 "Scott Y 5M"), the batch processing:
1. Called `run_portfolio_onboarding_backfill()`
2. Which called `market_data_collector.collect_daily_market_data()` with `portfolio_ids=[portfolio_id]`
3. BUT `_get_symbol_universe()` added ALL cached symbols (lines 444-452)
4. Result: **1,193 symbols** processed instead of **~30 needed**
5. Time: **~4 hours** instead of **~10 minutes**
6. Polygon API 429 rate limit errors

## Solution

### 1. Unified Function with Scoped Mode

Added `portfolio_id` and `source` parameters to `run_daily_batch_with_backfill()`:

```python
async def run_daily_batch_with_backfill(
    self,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    portfolio_ids: Optional[List[str]] = None,
    portfolio_id: Optional[str] = None,  # NEW: Single portfolio mode
    source: str = "cron",                 # NEW: Entry point tracking
) -> Dict[str, Any]:
```

When `portfolio_id` is provided:
- `scoped_only=True` is passed to downstream functions
- Only portfolio symbols + factor ETFs (~30) are processed
- Backfill starts from portfolio's earliest entry_date

### 2. Scoped Symbol Universe in market_data_collector.py

Added `scoped_only` parameter that skips the cached universe:

```python
if scoped_only:
    cached_symbols: Set[str] = set()
    logger.info(f"  Scoped mode: skipping cached universe (single-portfolio optimization)")
else:
    # Get ALL symbols from market_data_cache (full universe)
    ...
```

### 3. Scoped Phase 1.5 (Symbol Factors)

Added `symbols` parameter to `calculate_universe_factors()`:

```python
async def calculate_universe_factors(
    calculation_date: date,
    ...
    symbols: Optional[List[str]] = None,  # Override for scoped mode
) -> Dict[str, Any]:
```

### 4. Scoped Phase 1.75 (Symbol Metrics)

Added `symbols_override` parameter to `calculate_symbol_metrics()`:

```python
async def calculate_symbol_metrics(
    calculation_date: date,
    price_cache=None,
    symbols_override: Optional[List[str]] = None,
) -> Dict[str, Any]:
```

### 5. Wrapper for Backward Compatibility

`run_portfolio_onboarding_backfill()` is now a simple wrapper:

```python
async def run_portfolio_onboarding_backfill(self, portfolio_id: str, ...) -> Dict[str, Any]:
    """DEPRECATED: Wrapper for unified function"""
    return await self.run_daily_batch_with_backfill(
        end_date=end_date,
        portfolio_id=portfolio_id,
        source="onboarding",
    )
```

---

## Files Changed

| File | Changes |
|------|---------|
| `backend/app/batch/batch_orchestrator.py` | Added `portfolio_id`, `source` params; single-portfolio detection; scoped price cache loading; scoped Phase 1.5/1.75 calls; wrapper for deprecated function |
| `backend/app/batch/market_data_collector.py` | Added `scoped_only` param to `collect_daily_market_data()`, `_collect_with_session()`, and `_get_symbol_universe()` |
| `backend/app/calculations/symbol_factors.py` | Added `symbols` param to `calculate_universe_factors()` |
| `backend/app/services/symbol_metrics_service.py` | Added `symbols_override` param to `calculate_symbol_metrics()` |

---

## Key Review Points

### 1. Mode Detection Logic (batch_orchestrator.py lines ~157-170)

```python
is_single_portfolio_mode = portfolio_id is not None
scoped_only = is_single_portfolio_mode

if is_single_portfolio_mode:
    logger.info(f"Single-portfolio mode: processing portfolio {portfolio_id}")
    portfolio_ids = [portfolio_id]
```

**Question**: Is converting `portfolio_id` to `portfolio_ids` list the right approach for internal use?

### 2. Backfill Date Range Calculation (batch_orchestrator.py lines ~189-211)

When in single-portfolio mode, we query the portfolio's earliest entry_date:

```python
if is_single_portfolio_mode and not start_date:
    earliest_query = select(Position.entry_date).where(
        and_(
            Position.portfolio_id == UUID(portfolio_id) if isinstance(portfolio_id, str) else portfolio_id,
            Position.deleted_at.is_(None),
            Position.entry_date.isnot(None)
        )
    ).order_by(Position.entry_date).limit(1)
```

**Question**: Should we add an index on `(portfolio_id, entry_date)` for performance?

### 3. Scoped Symbol Universe (market_data_collector.py lines ~462-473)

```python
if scoped_only:
    cached_symbols: Set[str] = set()
    logger.info(f"  Scoped mode: skipping cached universe (single-portfolio optimization)")
else:
    # Original full universe fetch
    ...
```

**Question**: Is setting `cached_symbols = set()` the cleanest way to skip, or should we restructure the logic?

### 4. Optional symbols Parameter (symbol_factors.py lines ~576-580)

```python
if symbols:
    all_symbols = list(symbols)
    logger.info(f"Scoped mode: processing {len(all_symbols)} provided symbols")
else:
    all_symbols = await get_all_active_symbols(db)
```

**Question**: Should we validate that provided symbols actually exist in the database?

### 5. Phase 1.5/1.75 Calls Pass Symbols Only in Scoped Mode

```python
symbol_factor_result = await calculate_universe_factors(
    ...
    symbols=list(symbols) if scoped_only else None,
)
```

**Question**: Is `list(symbols)` necessary here since `symbols` is already a set? (Yes, because the API expects List[str])

---

## Testing Checklist

- [ ] Test onboarding flow: New portfolio should complete in ~10 minutes
- [ ] Test settings "Recalculate Analytics": Same performance as onboarding
- [ ] Test cron job: Should still process entire universe correctly
- [ ] Verify analytics available after onboarding: volatility, beta, stress test, factors, correlations
- [ ] Check Railway logs for no 429 rate limit errors
- [ ] Verify `source` field in batch_run_history for tracking

---

## Expected Performance Improvement

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Symbols processed | 1,193 | ~30 | 40x fewer |
| Estimated runtime | 4+ hours | ~10 minutes | 24x faster |
| API calls | ~1,193 × days | ~30 × days | 40x fewer |
| Rate limit errors | Many 429s | None expected | Eliminated |

---

## Rollback Plan

If issues arise:
1. The `run_portfolio_onboarding_backfill()` wrapper can be reverted to direct implementation
2. Remove `scoped_only` parameter usage (default to `False`)
3. Remove `portfolio_id` and `source` parameters (use only `portfolio_ids`)

---

## Related Documentation

- `backend/_docs/TESTSCOTTY_BATCH_PROCESSING_DEBUG_AND_FIX_PLAN.md` - Full Phase 5 plan
- `backend/_docs/SESSION_SUMMARY_BATCH_INVESTIGATION_JAN8.md` - Investigation summary
- `backend/_docs/TESTSCOTTY_PROGRESS.md` - Overall progress tracking

---

## Questions for Reviewer

1. **Naming**: Is `scoped_only` clear enough, or should we use `portfolio_scoped` or similar?

2. **Error Handling**: Should we add explicit error handling if a symbol can't be found in any provider during scoped mode?

3. **Logging**: Is the logging level appropriate? Should scoped mode info be DEBUG instead of INFO?

4. **Future-proofing**: Should we add a `scope` enum instead of `scoped_only: bool` for future scope types?

5. **Testing**: What additional unit tests should we add for the new scoped functionality?

---

## Commits

1. `337e7d39` - docs: Add Phase 5 detailed implementation plan for batch unification
2. `3ae56503` - feat: Implement Phase 5 unified batch function with symbol scoping

Please review and provide feedback on the implementation approach, code quality, and any edge cases that should be addressed.
