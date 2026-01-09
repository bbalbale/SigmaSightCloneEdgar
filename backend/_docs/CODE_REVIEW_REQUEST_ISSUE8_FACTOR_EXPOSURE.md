# Code Review Request: Issue #8 - Factor Exposure Storage Bug Fix

**Date**: January 9, 2026
**Author**: Claude Opus 4.5
**Commit**: `4db1ad63`
**Priority**: High - Affects all portfolio stress testing

---

## Summary

Fixed a key name mismatch bug that was causing Ridge and Spread factor exposures to never be stored, resulting in stress tests showing $0 impact for style factors (Value, Growth, Momentum, Quality, Size, Low Volatility).

---

## Problem Statement

### Symptoms Observed
- Stress testing showed: `No exposure found for shocked factor: Value (mapped to Value)`
- Only 3 factors available instead of 12+ expected
- Railway telemetry showed: `"name":"Ridge Factors","success":true,"message":"Skipped: no_public_positions"`
- This message repeated for every calculation date - factors were never stored

### Root Cause Analysis

**The Bug**: Key name mismatch between two services

`analytics_runner.py` (line 572) looks for `total_symbols` in `data_quality`:
```python
data_quality = symbol_result.get('data_quality', {})
total_symbols = data_quality.get('total_symbols', 0)  # ← Looks for 'total_symbols'

if total_symbols == 0:  # ← Always TRUE because key doesn't exist!
    return {
        'success': True,
        'message': 'Skipped: no_public_positions'
    }
```

But `portfolio_factor_service.py` was putting symbol count in `metadata`, not `data_quality`:
```python
results = {
    'metadata': {
        'unique_symbols': len(symbols),  # ← Symbol count was HERE
    },
    'data_quality': {
        'symbols_with_ridge': 0,
        'symbols_with_spread': 0,
        'symbols_missing': 0
        # ← 'total_symbols' DID NOT EXIST HERE!
    }
}
```

**What happened**:
1. `get_portfolio_factor_exposures()` returned symbol count in `metadata.unique_symbols`
2. `analytics_runner.py` looked for `data_quality.total_symbols` which didn't exist
3. `data_quality.get('total_symbols', 0)` returned default value `0`
4. `if total_symbols == 0:` evaluated to TRUE even when portfolio had 13+ PUBLIC positions
5. Returned `"Skipped: no_public_positions"` and exited early
6. `store_portfolio_factor_exposures()` was never called
7. Ridge/Spread factors never stored to `FactorExposure` table
8. Stress testing found no factor exposures for style factors

---

## Changes Made

### File: `backend/app/services/portfolio_factor_service.py`

#### Change 1: Add `total_symbols` to main result (line 261)

**Before:**
```python
'data_quality': {
    'symbols_with_ridge': 0,
    'symbols_with_spread': 0,
    'symbols_missing': 0
}
```

**After:**
```python
'data_quality': {
    'total_symbols': len(symbols),  # ← ADDED
    'symbols_with_ridge': 0,
    'symbols_with_spread': 0,
    'symbols_missing': 0
}
```

**Location**: `get_portfolio_factor_exposures()` function, lines 260-265

#### Change 2: Add `total_symbols` to empty result (line 466)

**Before:**
```python
'data_quality': {
    'symbols_with_ridge': 0,
    'symbols_with_spread': 0,
    'symbols_missing': 0
}
```

**After:**
```python
'data_quality': {
    'total_symbols': 0,  # ← ADDED
    'symbols_with_ridge': 0,
    'symbols_with_spread': 0,
    'symbols_missing': 0
}
```

**Location**: `_build_empty_result()` function, lines 465-470

---

## Why This Approach

### Alternative Considered: Fix the reader instead

Could have changed `analytics_runner.py` to read from `metadata.unique_symbols`:
```python
# Alternative fix in analytics_runner.py
metadata = symbol_result.get('metadata', {})
total_symbols = metadata.get('unique_symbols', 0)
```

### Why We Chose to Fix the Writer

1. **Semantic correctness**: `total_symbols` logically belongs in `data_quality` - it's a data quality metric
2. **API contract**: `data_quality` dict should contain all quality-related counts
3. **Consistency**: Other quality fields (`symbols_with_ridge`, `symbols_with_spread`, `symbols_missing`) are in `data_quality`
4. **Single point of change**: Fixing the source ensures all consumers get correct data

---

## Impact Analysis

### Positive Impact
- Ridge factors (Value, Growth, Momentum, Quality, Size, Low Volatility) will now be stored
- Spread factors (Growth-Value, Momentum, Size, Quality spreads) will now be stored
- Stress test scenarios will show actual $ impact for style factors
- All portfolios benefit (not just new ones - requires re-run of batch)

### Risk Assessment
- **Low risk**: Additive change only - adds a key to existing dict
- **No breaking changes**: Existing consumers that don't use `total_symbols` are unaffected
- **Backwards compatible**: `_build_empty_result()` also updated for consistency

### Affected Code Paths
| Consumer | Location | Impact |
|----------|----------|--------|
| `_calculate_ridge_factors()` | analytics_runner.py:572 | ✅ Now works correctly |
| `_calculate_spread_factors()` | analytics_runner.py:620 | ✅ Now works correctly |
| Any future consumers | - | ✅ Will have access to `total_symbols` |

---

## Testing Verification

### Pre-Fix State (testscotty5 - January 9, 2026)
```
Railway logs:
telemetry {"name":"Ridge Factors","success":true,"message":"Skipped: no_public_positions"}
telemetry {"name":"Spread Factors","success":true,"message":"Skipped: no_public_positions"}
```
- Repeated for every calculation date
- Only 3 factors available (Market Beta, IR Beta, one other)
- Stress testing showed $0 impact for Value, Growth, Momentum, etc.

### Expected Post-Fix State
```
Railway logs:
telemetry {"name":"Ridge Factors","success":true,"factors_stored":6}
telemetry {"name":"Spread Factors","success":true,"factors_stored":4}
```
- 12+ factors should be stored
- Stress testing should show non-zero impacts for all style factors

### Verification Steps
1. Deploy fix to Railway (auto-deployed on push)
2. Re-run batch for testscotty5: `POST /api/v1/admin/batch/run?portfolio_id=<testscotty5_id>&force_rerun=true`
3. Check Railway logs for:
   - NO more `"Skipped: no_public_positions"` for Ridge/Spread Factors
   - Telemetry showing actual factor storage
4. Query `FactorExposure` table:
   ```sql
   SELECT factor_name, beta_value
   FROM factor_exposures
   WHERE portfolio_id = '<testscotty5_id>'
   ORDER BY factor_name;
   ```
   Expected: 12+ rows (not just 3)
5. Test stress testing endpoint:
   ```
   GET /api/v1/analytics/portfolio/<testscotty5_id>/stress-test
   ```
   Expected: Non-zero impacts for Value, Growth, Momentum, Quality, Size, Low Volatility

---

## Rollback Plan

If issues arise:
```bash
git revert 4db1ad63
git push origin main
```

This will remove the `total_symbols` key. The system will revert to the "skip" behavior, which is safe but means no style factor analytics.

---

## Checklist

- [x] Root cause identified and documented
- [x] Fix is minimal and focused (one key added in two locations)
- [x] Both code paths updated (`get_portfolio_factor_exposures` and `_build_empty_result`)
- [x] No breaking changes to existing API consumers
- [x] TESTSCOTTY_PROGRESS.md updated with fix status
- [x] Commit message explains the change clearly
- [x] Pushed to origin/main for Railway auto-deploy
- [ ] Railway verification pending (re-run batch, check logs, verify factors)

---

## Questions for Reviewer

1. **Naming consistency**: Should we also add `total_symbols` to other similar result dicts in the codebase for consistency?

2. **Logging enhancement**: Should we add a log line when factors are successfully stored (e.g., `logger.info(f"Stored {len(ridge_betas)} Ridge factors for portfolio {portfolio_id}")`)?

3. **Data backfill**: Should we proactively re-run batches for all portfolios to populate the missing factor data, or wait for daily cron to catch up?

---

## Addendum: Second Bug Found During Code Review (January 9, 2026)

### Code Review Results

**Gemini Review**: Verified & Approved
- Confirmed the fix aligns with project patterns
- Recommended logging enhancement (implemented)
- Recommended checking other `data_quality` blocks (checked - no others need changes)

**Codex Review**: Identified Second Bug
- Even after adding `total_symbols`, the `store_portfolio_factor_exposures()` call would fail
- The call used wrong kwargs: `ridge_betas=...` and `spread_betas=...`
- The function signature expects: `portfolio_betas=...` and `portfolio_equity=...`
- This would raise `TypeError: got an unexpected keyword argument 'ridge_betas'`
- The TypeError was swallowed by the `except Exception` block

### Second Bug Details

**The call in analytics_runner.py (BEFORE fix)**:
```python
await store_portfolio_factor_exposures(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=calculation_date,
    ridge_betas=ridge_betas,  # ← WRONG!
    spread_betas={}  # ← WRONG!
)
```

**The function signature**:
```python
async def store_portfolio_factor_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    portfolio_betas: Dict[str, float],  # ← Expected
    calculation_date: date,
    portfolio_equity: float  # ← Expected
)
```

### Additional Changes Made

**File: `backend/app/batch/analytics_runner.py`**

1. **Fixed Ridge factors call** (lines 595-600):
```python
await store_portfolio_factor_exposures(
    db=db,
    portfolio_id=portfolio_id,
    portfolio_betas=ridge_betas,  # ← FIXED
    calculation_date=calculation_date,
    portfolio_equity=portfolio_equity  # ← ADDED
)
```

2. **Fixed Spread factors call** (lines 674-679):
```python
await store_portfolio_factor_exposures(
    db=db,
    portfolio_id=portfolio_id,
    portfolio_betas=spread_betas,  # ← FIXED
    calculation_date=calculation_date,
    portfolio_equity=portfolio_equity  # ← ADDED
)
```

3. **Added logging enhancement** (lines 603, 681):
```python
logger.info(
    f"Stored {len(ridge_betas)} Ridge factors for portfolio {portfolio_id} "
    f"({symbols_with_ridge}/{total_symbols} symbols)"
)
```

### Updated Checklist

- [x] Bug #1 fixed: Added `total_symbols` to `data_quality` dict
- [x] Bug #2 fixed: Corrected function call signature in analytics_runner.py
- [x] Logging enhancement added (logger.debug → logger.info)
- [x] Both Ridge and Spread factor paths fixed
- [x] TESTSCOTTY_PROGRESS.md updated with complete fix
- [ ] Railway verification pending
