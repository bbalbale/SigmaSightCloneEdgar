# Code Review Request: Batch Processing Phase 1 Fixes (v3)

**Date**: January 8, 2026
**Author**: Claude Opus 4.5
**Reviewer**: Human reviewer
**Status**: Ready for review

---

## Summary

This PR fixes **Issue #1 (CRITICAL): Phase 1.5 Skipped for Admin/Onboarding Batches** from the Testscotty batch processing bug analysis.

### Commits Included (local only, not pushed)

1. `1b022596` - fix: Add Phase 1.5 and 1.75 to `_run_sequence_with_session`
2. `ef8f76aa` - fix: Switch onboarding to use `run_daily_batch_with_backfill` (superseded)
3. `d4c32653` - fix: Create per-portfolio onboarding backfill (addresses code review v1)
4. `31686e14` - fix: Address code review v2 - batch_run_tracker cleanup and scoped symbols

---

## Problem Statement

When Testscotty was onboarded:
- Batch triggered by "admin" via `run_daily_batch_sequence()` which skips Phase 1.5
- 8 out of 13 symbols missing from `symbol_universe`
- ALL 13 positions have 0 `position_factor_exposures`
- New portfolios only get single-date snapshots (no historical data for P&L trends)

---

## Solution Overview

### Part A: Add Phase 1.5 and 1.75 to `_run_sequence_with_session()` (Commit 1)

**File**: `backend/app/batch/batch_orchestrator.py`

Added Phase 1.5 (Symbol Factors) and Phase 1.75 (Symbol Metrics) blocks to the core execution function so ALL batch paths include them.

### Part B: Create Per-Portfolio Onboarding Backfill (Commits 2-4)

**Files**:
- `backend/app/batch/batch_orchestrator.py` - New `run_portfolio_onboarding_backfill()` method
- `backend/app/api/v1/portfolios.py` - Updated trigger

Created a new dedicated method that:
1. Queries earliest position `entry_date` for THIS portfolio specifically
2. Calculates all trading days from that date to today
3. Runs full batch (Phase 1 → 2-6) for all dates
4. Bypasses global watermark entirely
5. **Adds portfolio's symbols to universe (scoped)** but does NOT run universe-wide factor calculations

---

## Code Review v1 and v2 Findings - All Addressed

### v1 Finding 1: Global watermark short-circuit (HIGH) - FIXED
- **Problem**: `run_daily_batch_with_backfill()` returns "already up to date" if cron ran today
- **Solution**: Created dedicated `run_portfolio_onboarding_backfill()` that bypasses global watermark

### v1 Finding 2: Global start date (HIGH) - FIXED
- **Problem**: Uses MAX snapshot across ALL portfolios, not per-portfolio
- **Solution**: New method queries earliest entry_date for specific portfolio

### v2 Finding 1: batch_run_tracker never cleared (HIGH) - FIXED
- **Problem**: `batch_run_tracker.start()` called but never `complete()`, causing 409 errors on next run
- **Solution**: Added try/finally block with `batch_run_tracker.complete()` in finally

### v2 Finding 2: Phase 1.5/1.75 corrupts global analytics (HIGH) - FIXED
- **Problem**: `calculate_universe_factors()` operates on ALL symbols but only portfolio's prices fetched
- **Solution**:
  - Removed `calculate_universe_factors()` call
  - Removed `calculate_symbol_metrics()` call
  - Now only calls `ensure_symbols_in_universe()` for portfolio's symbols
  - Daily cron calculates factors with full price cache

---

## Trade-offs Accepted

**New portfolios won't have factor exposures immediately.** This is acceptable because:
1. Factor analytics will show as "calculating" briefly (not broken/zero)
2. Daily cron (`run_daily_batch_with_backfill`) calculates factors with full price data
3. Data integrity preserved for ALL portfolios (not just the new one)
4. Cron runs daily at predictable time

---

## Key Code Changes

### 1. `run_portfolio_onboarding_backfill()` Method (lines 442-687)

```python
async def run_portfolio_onboarding_backfill(
    self,
    portfolio_id: str,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Run full backfill for a SINGLE newly onboarded portfolio.

    NOTE: This method does NOT run universe-level Phase 1.5/1.75 calculations
    because doing so would corrupt global analytics. The daily cron job
    (run_daily_batch_with_backfill) handles universe-wide factor calculations
    with complete market data.
    """
    # ... implementation with try/finally for batch_run_tracker ...
```

**Key features:**
- Scoped to single portfolio
- Queries earliest position entry_date
- try/finally ensures `batch_run_tracker.complete()` always called
- Adds symbols to universe but skips factor calculations

### 2. portfolios.py Onboarding Trigger (lines 590-601)

```python
# Execute batch processing in background using per-portfolio onboarding backfill
background_tasks.add_task(
    batch_orchestrator.run_portfolio_onboarding_backfill,
    str(portfolio_id),  # portfolio_id - the specific portfolio to backfill
    calculation_date    # end_date - process up to most recent trading day
)
```

### 3. Phase 1.5/1.75 in `_run_sequence_with_session()` (lines 625-697)

Added both phases to the core execution function that ALL batch entry points use.

---

## Verification After Deployment

```sql
-- Check symbols in universe after fix
SELECT symbol FROM symbol_universe
WHERE symbol IN ('GGIPX', 'GINDX', 'GOVT', 'IAU', 'IEFA', 'MUB', 'NEAIX', 'VO');
-- Expected: 8 rows

-- Check Testscotty portfolio factor exposures (after cron runs)
SELECT p.symbol, COUNT(pfe.id) as exposure_count
FROM positions p
LEFT JOIN position_factor_exposures pfe ON p.id = pfe.position_id
WHERE p.portfolio_id = '98518c7d-ea23-593b-aaed-9c0be7f3a66f'
GROUP BY p.symbol;
-- Expected: 13 rows with exposure_count > 0 (after daily cron)
```

---

## Files Modified

1. `backend/app/batch/batch_orchestrator.py`
   - Added `run_portfolio_onboarding_backfill()` method (lines 442-687)
   - Added Phase 1.5 and 1.75 to `_run_sequence_with_session()` (lines 625-697)

2. `backend/app/api/v1/portfolios.py`
   - Changed onboarding trigger from `run_daily_batch_sequence()` to `run_portfolio_onboarding_backfill()`

3. `backend/_docs/TESTSCOTTY_PROGRESS.md` - Updated with implementation details

4. `backend/_docs/TESTSCOTTY_BATCH_PROCESSING_DEBUG_AND_FIX_PLAN.md` - Updated plan

---

## Rollback Plan

```bash
# Revert all Phase 1 commits
git revert 31686e14 d4c32653 ef8f76aa 1b022596
git push origin main
```

---

## Questions for Reviewer

1. **Trade-off acceptable?** New portfolios won't have factor exposures until daily cron runs. Is this acceptable UX?

2. **Error handling**: Should we add more specific error handling in the try block, or is the current catch-all approach sufficient?

3. **Logging verbosity**: The new method has detailed logging. Should this be reduced for production?

---

## Approval Checklist

- [ ] Code changes reviewed
- [ ] Trade-offs acceptable
- [ ] No security concerns
- [ ] Ready to push to origin/main
