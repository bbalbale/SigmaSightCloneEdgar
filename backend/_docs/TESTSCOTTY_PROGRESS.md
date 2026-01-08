# Testscotty Batch Processing Fix - Progress Tracker

**Started**: January 8, 2026
**Goal**: Fix 3 batch processing bugs identified during Testscotty onboarding
**Working Branch**: main
**Remote Push**: Pending code review

---

## Current Status

| Phase | Description | Status | Verified on Railway |
|-------|-------------|--------|---------------------|
| 1 | Fix Phase 1.5 Skipping | ✅ IMPLEMENTED | Pending |
| 2 | Fix Global Watermark Bug | NOT STARTED | - |
| 3 | Fix Fire-and-Forget Tasks | NOT STARTED | - |

---

## Manual Catch-Up: DEFERRED

**Decision**: Deferred until after Phase 1 and Phase 2 are deployed.

**Why**: Phase 2 fix will automatically backfill all 11 behind portfolios on the next cron run. No manual intervention needed.

**Script Status**: `scripts/manual_catchup_batch.py` was deployed (commit `6de057b2`) but encountered Railway SSH environment issues. Script remains available if needed later.

---

## Phase 1: Fix Phase 1.5 Skipping

### Objective
Ensure all batch entry points (admin, onboarding, cron) run Phase 1.5 (Symbol Factors) and Phase 1.75 (Symbol Metrics), AND ensure new portfolios get full historical snapshots for complete analytics.

### Pre-Fix State (Railway Production)
- Testscotty has 13 positions
- 8 symbols missing from `symbol_universe`: GGIPX, GINDX, GOVT, IAU, IEFA, MUB, NEAIX, VO
- 0 `position_factor_exposures` for all 13 positions
- Batch triggered by "admin" via `run_daily_batch_sequence()` which skips Phase 1.5
- New portfolios only get single-date snapshots (no historical data for P&L trends)

### Implementation - Part A (batch_orchestrator.py)

**File**: `backend/app/batch/batch_orchestrator.py`

**Status**: ✅ IMPLEMENTED (January 8, 2026)

**Changes Made**:
- [x] Updated docstring from "7-phase" to "9-phase" with full phase listing
- [x] Added `'phase_1_5': {}` and `'phase_1_75': {}` to result dict
- [x] Added Phase 1.5 (Symbol Factors) block after Phase 1, before Phase 2
  - Calls `calculate_universe_factors()` from `app.calculations.symbol_factors`
  - Ensures symbols in `symbol_universe` table
  - Calculates factor exposures (Ridge and Spread)
  - Non-blocking: continues to Phase 1.75 even on error
- [x] Added Phase 1.75 (Symbol Metrics) block after Phase 1.5
  - Calls `calculate_symbol_metrics()` from `app.services.symbol_metrics_service`
  - Pre-calculates returns for all symbols
  - Non-blocking: continues to Phase 2 even on error
- [x] Verified imports work correctly

**Key Code Locations**:
- Result dict: lines 559-572
- Phase 1.5: lines 625-661
- Phase 1.75: lines 663-697

### Implementation - Part B (portfolios.py + new orchestrator method)

**Files**:
- `backend/app/batch/batch_orchestrator.py` - New `run_portfolio_onboarding_backfill()` method
- `backend/app/api/v1/portfolios.py` - Updated to use new method

**Status**: ✅ IMPLEMENTED (January 8, 2026) - REVISED after code review

**Code Review Finding (Critical)**:
The initial implementation using `run_daily_batch_with_backfill()` had two issues:
1. **Global watermark short-circuit**: If cron already ran today, returns "already up to date" without processing the new portfolio
2. **Global start date**: Uses MAX snapshot across ALL portfolios, not per-portfolio earliest position

**Solution**: Created new dedicated method `run_portfolio_onboarding_backfill(portfolio_id)` that:
1. Queries earliest position `entry_date` for THIS portfolio specifically
2. Calculates all trading days from that date to today
3. Runs full batch (Phase 1 → 1.5 → 1.75 → 2-6) for all dates
4. Bypasses global watermark entirely

**Changes Made**:
- [x] Created `run_portfolio_onboarding_backfill(portfolio_id, end_date)` in batch_orchestrator.py (lines 442-671)
- [x] Changed portfolios.py to call `run_portfolio_onboarding_backfill()` instead of `run_daily_batch_with_backfill()`
- [x] Added detailed comments explaining why per-portfolio backfill is needed
- [x] Verified imports work correctly

**Key Code Locations**:
- New method: `batch_orchestrator.py` lines 442-671
- Trigger: `portfolios.py` lines 590-601

### Verification Queries

```sql
-- Check symbols in universe after fix
SELECT symbol FROM symbol_universe
WHERE symbol IN ('GGIPX', 'GINDX', 'GOVT', 'IAU', 'IEFA', 'MUB', 'NEAIX', 'VO');
-- Expected: 8 rows

-- Check symbol factor exposures after fix
SELECT symbol, COUNT(*) as factor_count
FROM symbol_factor_exposures
WHERE symbol IN ('GGIPX', 'GINDX', 'GOVT', 'IAU', 'IEFA', 'MUB', 'NEAIX', 'VO')
GROUP BY symbol;
-- Expected: 8 rows with factor_count > 0

-- Check position factor exposures for Testscotty
SELECT p.symbol, COUNT(pfe.id) as exposure_count
FROM positions p
LEFT JOIN position_factor_exposures pfe ON p.id = pfe.position_id
WHERE p.portfolio_id = '98518c7d-ea23-593b-aaed-9c0be7f3a66f'
GROUP BY p.symbol;
-- Expected: 13 rows with exposure_count > 0
```

### Post-Fix Verification
- [ ] Deployed to Railway
- [ ] Re-ran batch for Testscotty portfolio
- [ ] Verified 8 missing symbols now in `symbol_universe`
- [ ] Verified all 13 positions have `symbol_factor_exposures`
- [ ] Verified all 13 positions have `position_factor_exposures`

### Notes
- **Design Decision (Part A)**: Phase 1.5 and 1.75 are non-blocking - they continue to subsequent phases even if they fail. This is consistent with the pattern used in `run_daily_batch_with_backfill()`.
- **Design Decision (Part B - Revised)**: After code review, switched from `run_daily_batch_with_backfill()` to new dedicated `run_portfolio_onboarding_backfill()` method because:
  1. Global backfill short-circuits when cron already ran (returns "already up to date")
  2. Global backfill uses system-wide watermark, not per-portfolio dates
  3. New method guarantees processing regardless of global system state
- **Key Benefit**: Now ALL batch entry points run Phase 1.5 and 1.75, and onboarding specifically gets full per-portfolio backfill from earliest position date.
- **Performance Note**: The new onboarding method recalculates symbol factors for the portfolio's symbols. This is intentional to ensure new/uncommon symbols get factor exposures.
- **Testing Note**: Imports verified locally. Ready for Railway deployment and verification.

---

## Phase 2: Fix Global Watermark Bug

### Objective
Ensure cron job processes ALL portfolios that are behind, not just check global MAX snapshot date.

### Pre-Fix State (Railway Production)
- 11 portfolios stuck at Jan 5 snapshots
- 1 portfolio (Tech Growth) at Jan 6
- 1 portfolio (Testscotty) at Jan 7
- Global MAX = Jan 7, so cron thinks "all caught up"

### Implementation

**File**: `backend/app/batch/batch_orchestrator.py`

**Status**: NOT STARTED

**Changes Made**:
- [ ] TBD

### Verification Queries

```sql
-- Check snapshot dates per portfolio after fix
SELECT p.name, MAX(ps.snapshot_date) as last_snapshot
FROM portfolios p
LEFT JOIN portfolio_snapshots ps ON p.id = ps.portfolio_id
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name
ORDER BY last_snapshot;
-- Expected: All portfolios should have same date (or within 1 day)
```

### Post-Fix Verification
- [ ] Deployed to Railway
- [ ] Ran `run_daily_batch_with_backfill()`
- [ ] Verified all portfolios have snapshots for current date
- [ ] Verified no portfolios are more than 1 day behind

### Notes
(Add any observations, issues, or decisions during implementation)

---

## Phase 3: Fix Fire-and-Forget Tasks

### Objective
Ensure batch history records are properly persisted and no "Task was destroyed" warnings in logs.

### Pre-Fix State (Railway Production)
- Multiple cron batches show `status="running"` forever
- "Task was destroyed but it is pending" warnings in logs
- `batch_history_service.py` uses `asyncio.create_task()` without awaiting

### Implementation

**File**: `backend/app/services/batch_history_service.py`

**Status**: NOT STARTED

**Changes Made**:
- [ ] TBD

### Verification Queries

```sql
-- Check batch history status after fix
SELECT batch_run_id, triggered_by, status, started_at, completed_at
FROM batch_run_history
ORDER BY started_at DESC
LIMIT 10;
-- Expected: Recent batches have status="completed" and completed_at set
```

### Post-Fix Verification
- [ ] Deployed to Railway
- [ ] Triggered or waited for a batch run
- [ ] Verified no "Task was destroyed" warnings in Railway logs
- [ ] Verified new batches have `completed_at` timestamps
- [ ] Verified status is "completed" not "running"

### Notes
(Add any observations, issues, or decisions during implementation)

---

## Timeline

| Date | Action | Result |
|------|--------|--------|
| 2026-01-08 | Initial analysis and plan created | 3 bugs identified |
| 2026-01-08 | Phase 1 Part A implemented | Added Phase 1.5 and 1.75 to `_run_sequence_with_session()` |
| 2026-01-08 | Phase 1 Part B implemented (v1) | Changed onboarding to use `run_daily_batch_with_backfill()` |
| 2026-01-08 | Code review identified issues | Global watermark problems with Part B v1 |
| 2026-01-08 | Phase 1 Part B revised (v2) | Created `run_portfolio_onboarding_backfill()` method |
| | | |

---

## Code Review Checklist

Before pushing to remote:
- [x] Phase 1 changes reviewed by AI agent (Claude Opus 4.5)
- [ ] Phase 2 changes reviewed by AI agent
- [ ] Phase 3 changes reviewed by AI agent
- [ ] All verification queries pass on Railway
- [ ] No regressions in existing functionality

---

## Rollback Plan

If issues arise after deployment:

**Phase 1 Rollback**:
```bash
git revert <phase1-commit-hash>
git push origin main
```

**Phase 2 Rollback**:
```bash
git revert <phase2-commit-hash>
git push origin main
```

**Phase 3 Rollback**:
```bash
git revert <phase3-commit-hash>
git push origin main
```
