# Testscotty Batch Processing Fix - Progress Tracker

**Started**: January 8, 2026
**Goal**: Fix batch processing bugs identified during Testscotty onboarding
**Working Branch**: main
**Remote Push**: ✅ Pushed to origin/main (January 8, 2026)

---

## Current Status

| Phase | Description | Status | Verified on Railway |
|-------|-------------|--------|---------------------|
| 1 | Fix Phase 1.5 Skipping | ✅ IMPLEMENTED | Pending |
| 2 | Fix Global Watermark Bug (Hybrid) | ✅ IMPLEMENTED | Pending |
| 3 | Fix Fire-and-Forget Tasks | NOT STARTED | - |
| 4 | Add batch_run_tracker Timeout & Cleanup | ✅ DONE (earlier) | - |
| 5 | Unify Batch Functions (REFACTOR) | ✅ IMPLEMENTED | ✅ VERIFIED |
| 6 | Harden batch_run_history Error Handling | ✅ IMPLEMENTED | ✅ VERIFIED |
| 7 | Real-Time Onboarding Status Updates | NOT STARTED | - |

### Phase 5 Details (January 8, 2026)

**Commits (pushed to origin/main)**:
- `337e7d39` - docs: Add Phase 5 detailed implementation plan
- `3ae56503` - feat: Implement Phase 5 unified batch function with symbol scoping
- `ffb68fa1` - docs: Add code review request for Phase 5
- `a020f1ca` - fix: Address code review findings (tracker cleanup, history timing, source default)

**Key Changes**:
- Unified `run_daily_batch_with_backfill()` with `portfolio_id` and `source` params
- Added `scoped_only` mode for single-portfolio batches (~40x faster)
- `run_portfolio_onboarding_backfill()` now wraps unified function with try/finally
- Fixed: batch_run_tracker.complete() always called (prevents stuck UI)
- Fixed: record_batch_start() only after confirming work exists
- Fixed: source param defaults to None (preserves manual detection)

**Railway Verification (January 8, 2026 - testscotty4 "Scott Y 5M")**:
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Symbols processed | 1,193 | 27 | **44x fewer** |
| Runtime | 4+ hours | 894s (~15 min) | **~16x faster** |
| Dates processed | N/A | 254/254 | **100% success** |

**Key Log Evidence**:
- `Scoped mode: skipping cached universe (single-portfolio optimization)`
- `Symbol universe for portfolio: 27 symbols`
- `Backfill complete: 254/254 dates in 894s`

### Phase 6 Details (January 8, 2026)

**Commits (pushed to origin/main)**:
- `be0c7052` - docs: Add Phase 6 for batch_run_history error handling hardening
- `9963c9af` - feat: Implement Phase 6 try/except/finally implementation
- `f82496d7` - fix: Catch asyncio.CancelledError for deployment/restart handling
- `5749f64a` - fix: Track actual progress for accurate crash reporting
- `1357bd7b` - fix: Update progress tracker only after commit succeeds

**Problem Solved**:
The `batch_run_history` database table could have rows stuck in "running" status forever if:
- Server crashes (OOM, timeout, unhandled exception)
- Process killed during batch execution
- Any uncaught exception between `record_batch_start()` and `record_batch_complete()`

This is separate from the in-memory `batch_run_tracker` (fixed in Phase 5) - this is about the **persistent database record**.

**Solution**:
Wrapped all batch processing in `run_daily_batch_with_backfill()` with try/except:
1. Extracted processing logic into new `_execute_batch_phases()` method
2. On success: `record_batch_complete()` called with status="completed"
3. On exception: `record_batch_complete()` called with status="failed" before re-raising
4. Catches both `Exception` AND `asyncio.CancelledError` (inherits from BaseException)
5. Progress tracker accurately reports completed/failed dates even on crash

**Key Code** (batch_orchestrator.py lines 254-297):
```python
# Progress tracker: Mutable dict updated by _execute_batch_phases()
progress = {"completed": 0, "failed": 0}

try:
    return await self._execute_batch_phases(
        missing_dates=missing_dates,
        progress=progress,
        ...
    )
except (Exception, asyncio.CancelledError) as e:
    logger.error(f"Batch failed with exception: {e}")
    completed = progress["completed"]
    failed = len(missing_dates) - completed
    record_batch_complete(
        batch_run_id=batch_run_id,
        status="failed",
        completed_jobs=completed,
        failed_jobs=failed,
        error_summary={"exception": str(e), "type": type(e).__name__, "crashed_after_dates": completed},
    )
    raise  # Re-raise so caller knows batch failed
```

**Code Review Improvements**:
1. `asyncio.CancelledError` handling for SIGTERM/deployment restarts
2. Accurate progress tracking (not hardcoded to 0/total)
3. Progress updated AFTER `db.commit()` succeeds (not before)

**Impact**:
- Admin dashboard will never show phantom "running" batches
- Crashed batches now properly marked as "failed" with error details
- Better debugging: can distinguish running vs crashed batches
- Accurate crash reporting shows how many dates completed before failure

**Railway Verification (January 8, 2026)**:
- Batch completed successfully: 254/254 dates
- No stuck "running" status observed
- Phase 6 analytics executed for all dates

### Phase 7: Real-Time Onboarding Status Updates (January 8, 2026)

**Problem Statement**:
The current onboarding progress screen shows a fake animation through conceptual steps that don't reflect actual batch processing. With batch processing now taking ~15 minutes (down from 4+ hours after Phase 5), users still see a misleading progress UI. We want transparent, real-time status updates showing what's actually happening.

**Goals**:
1. Replace fake animation with real batch processing status
2. Two display modes: **User Mode** (friendly) and **Debug Mode** (technical)
3. Show actual phases and sub-phases as they execute
4. Per-symbol granularity for detailed progress tracking

**Scope**: Onboarding flow only (not admin batch triggers or cron jobs)

---

#### Design Decisions

**State Storage**: Extend `batch_run_tracker` (in-memory)
- Already tracks batch running state
- No database changes needed
- Fast reads/writes
- Status only relevant during processing (lost on restart is fine)

**Transport**: Polling (simplest)
- Frontend polls new endpoint periodically
- Already proven pattern with `/admin/batch/run/current`

**Endpoint**: New dedicated endpoint
- `GET /api/v1/onboarding/status/{portfolio_id}?debug=false`
- Tailored for onboarding UX (not mixed with admin concerns)
- RESTful (status is per-portfolio)

---

#### Two Display Modes

**User Mode** (default: `?debug=false`):
- Current phase name + friendly description
- Progress bar/percentage (e.g., "45% complete")
- Dates processed count (e.g., "120/254 dates")
- Elapsed time (e.g., "Running for 3m 42s")
- Estimated time remaining (based on current rate)
- All phases/steps printed and staying on screen (not just current)
- Technical details + timing per phase (e.g., "Phase 1: 45s")
- Error summaries if any occur

**Debug Mode** (`?debug=true`):
- Everything from User Mode, plus:
- Scrollable log window for verbose output
- Filtered log lines (remove Clerk auth, duplicates, noise)
- Per-symbol processing details
- Timing breakdowns per sub-phase
- Warning/error details that User Mode hides

**Mode Toggle**: Frontend button to switch between modes

---

#### Status Message Structure

```python
# In batch_run_tracker.py
@dataclass
class StatusMessage:
    timestamp: datetime
    phase: str              # "phase_1", "phase_1.5", "phase_2", etc.
    phase_name: str         # "Market Data Collection"
    message: str            # User-friendly: "Fetching historical prices..."
    detail: Optional[str]   # Debug: "AAPL: 254 days fetched in 0.3s"
    level: str              # "info", "warning", "error"
    progress: Optional[dict] # {"current": 15, "total": 27, "unit": "symbols"}

# Example status messages during processing:
{"phase": "phase_1", "phase_name": "Market Data Collection",
 "message": "Fetching historical prices...",
 "detail": "Processing AAPL (1/27)",
 "progress": {"current": 1, "total": 27, "unit": "symbols"}}

{"phase": "phase_1.5", "phase_name": "Symbol Factors",
 "message": "Calculating factor exposures...",
 "detail": "Ridge regression for 27 symbols",
 "progress": {"current": 0, "total": 27, "unit": "symbols"}}

{"phase": "phase_2", "phase_name": "Portfolio Snapshots",
 "message": "Creating daily snapshots...",
 "detail": "Processing 2025-03-15 (120/254)",
 "progress": {"current": 120, "total": 254, "unit": "dates"}}
```

---

#### API Response Schema

```python
# GET /api/v1/onboarding/status/{portfolio_id}?debug=false
{
    "portfolio_id": "uuid",
    "status": "running" | "completed" | "failed" | "not_found",
    "started_at": "2026-01-08T12:00:00Z",
    "elapsed_seconds": 223,
    "estimated_remaining_seconds": 450,  # null if can't estimate

    # Overall progress
    "overall_progress": {
        "current_phase": "phase_2",
        "current_phase_name": "Portfolio Snapshots",
        "phases_completed": 2,
        "phases_total": 6,
        "percent_complete": 45
    },

    # Current phase detail
    "current_phase_progress": {
        "current": 120,
        "total": 254,
        "unit": "dates",
        "message": "Creating daily snapshots..."
    },

    # All status messages (User Mode: condensed, Debug Mode: full)
    "messages": [
        {
            "timestamp": "2026-01-08T12:00:05Z",
            "phase": "phase_1",
            "phase_name": "Market Data Collection",
            "message": "Fetching historical prices...",
            "detail": "Completed in 45s (27 symbols)",  # Only in debug mode
            "level": "info"
        },
        ...
    ],

    # Only in debug mode
    "debug_logs": [
        "2026-01-08 12:00:05 - Fetching AAPL: 254 days",
        "2026-01-08 12:00:05 - Fetching MSFT: 254 days",
        ...
    ]
}
```

---

#### Implementation Plan

**Backend Changes**:

1. **Extend `batch_run_tracker.py`**:
   - Add `status_messages: List[StatusMessage]` to tracker
   - Add `add_status(phase, message, detail, progress)` method
   - Add `get_status_for_portfolio(portfolio_id)` method
   - Cap messages at ~200 to prevent memory growth

2. **Add status calls to `batch_orchestrator.py`**:
   - Add status updates at start/end of each phase
   - Add per-symbol/per-date progress updates
   - Track timing per phase for estimates

3. **New endpoint `app/api/v1/onboarding_status.py`**:
   - `GET /api/v1/onboarding/status/{portfolio_id}`
   - Query param `?debug=true|false` (default: false)
   - Returns filtered messages based on mode
   - Include progress calculations and time estimates

**Frontend Changes**:

1. **Update onboarding progress component**:
   - Replace fake animation with polling-based real status
   - Poll every 2-3 seconds during processing
   - Show phase list with checkmarks for completed phases
   - Progress bar for current phase

2. **Add debug mode toggle**:
   - Button/switch in UI to toggle debug mode
   - Debug mode: scrollable log window with filtered output
   - Persist preference in localStorage

3. **Handle edge cases**:
   - Status not found (batch not started yet)
   - Batch completed (show success state)
   - Batch failed (show error details)

---

#### Batch Processing Phases to Report

| Phase | Name | User Message | Progress Unit |
|-------|------|--------------|---------------|
| phase_1 | Market Data Collection | "Fetching historical prices..." | symbols |
| phase_1.5 | Symbol Factors | "Calculating factor exposures..." | symbols |
| phase_1.75 | Symbol Metrics | "Computing symbol metrics..." | symbols |
| phase_2 | Portfolio Snapshots | "Creating daily snapshots..." | dates |
| phase_2.5 | Position Market Values | "Updating position values..." | positions |
| phase_3 | Betas | "Calculating position betas..." | positions |
| phase_4 | Factor Exposures | "Computing factor exposures..." | positions |
| phase_5 | Volatility | "Analyzing volatility..." | positions |
| phase_6 | Correlations | "Building correlation matrix..." | N/A |

---

#### Files to Modify

| File | Changes |
|------|---------|
| `backend/app/batch/batch_run_tracker.py` | Add StatusMessage dataclass, status_messages list, helper methods |
| `backend/app/batch/batch_orchestrator.py` | Add status update calls throughout processing |
| `backend/app/api/v1/onboarding_status.py` | NEW: Status endpoint for onboarding |
| `backend/app/api/v1/router.py` | Register new endpoint |
| `frontend/src/components/onboarding/...` | Update progress UI (TBD) |

---

#### Debug Mode Log Filtering

**Include** (in debug mode):
- Phase start/complete messages
- Per-symbol/date processing
- Timing information
- Warnings and errors
- API call summaries

**Exclude** (filter out):
- Clerk authentication logs
- Duplicate consecutive messages
- Low-level database session logs
- Health check logs
- Routine HTTP request logs

---

#### Success Criteria

- [ ] User sees real phase names during onboarding
- [ ] Progress bar reflects actual completion percentage
- [ ] Per-symbol updates visible in debug mode
- [ ] Elapsed time and estimate displayed
- [ ] Debug mode shows filtered technical logs
- [ ] Status endpoint returns accurate data
- [ ] Frontend polls and updates smoothly (no flicker)
- [ ] Completed state shows success with summary

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
- **Design Decision (Part B - Revised v2)**: After code review v1, switched from `run_daily_batch_with_backfill()` to new dedicated `run_portfolio_onboarding_backfill()` method because:
  1. Global backfill short-circuits when cron already ran (returns "already up to date")
  2. Global backfill uses system-wide watermark, not per-portfolio dates
  3. New method guarantees processing regardless of global system state
- **Design Decision (Part B - Revised v3)**: After code review v2:
  1. Added try/finally to ensure `batch_run_tracker.complete()` always called (prevents 409 errors)
  2. **REMOVED** universe-wide `calculate_universe_factors()` call - was corrupting global analytics
  3. **REMOVED** universe-wide `calculate_symbol_metrics()` call - same issue
  4. Now only calls `ensure_symbols_in_universe()` for portfolio's specific symbols
  5. Daily cron will calculate factors with complete price cache
- **Trade-off Accepted**: New portfolios won't have factor exposures immediately. Daily cron calculates them with full data. This is acceptable because data integrity is preserved for all portfolios.
- **Key Benefit**: Now ALL batch entry points run Phase 1.5 and 1.75, and onboarding specifically gets full per-portfolio backfill from earliest position date.
- **Testing Note**: Imports verified locally. Ready for Railway deployment and verification.

---

## Testscotty2 Verification Test (January 8, 2026)

### Test Setup
- **User**: Testscotty2 (elliott.ng+testscotty2@gmail.com)
- **Portfolio**: Yaphe 5M
- **Portfolio ID**: `2ecdbdaf-468d-5484-98a1-26943635c829`
- **Created**: 2026-01-08 19:15:38 UTC
- **Positions**: 13 (same symbols as original Testscotty)

### Test Results

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| User created in DB | ✅ | ✅ Created 19:14:43 UTC | ✅ PASS |
| Portfolio created | ✅ | ✅ Created 19:15:38 UTC | ✅ PASS |
| Positions imported | 13 | 13 | ✅ PASS |
| Symbols in `symbol_universe` | 8 new | 8 found | ✅ PASS |
| Portfolio snapshots | >0 | **0** | ❌ FAIL |
| Position factor exposures | >0 | **0** | ❌ FAIL |
| Batch triggered on onboarding | Yes | **No batch record** | ❌ FAIL |

### Root Cause Analysis

**Finding: Stuck batch blocking onboarding**

The `batch_run_tracker` is an **in-memory singleton** that prevents concurrent batch runs:

1. When a batch starts → calls `batch_run_tracker.start()` → sets "running" flag
2. If another batch tries to start while flag is set → **blocked** (409 conflict)
3. When batch completes → should call `batch_run_tracker.complete()` → clears flag

**The problem**: A previous batch crashed/hung WITHOUT calling `complete()`, leaving the flag stuck. This blocked the onboarding batch from starting.

**Evidence from Railway DB**:
```
=== Batch Run History (since Jan 7) ===
2026-01-09 01:21:47 | manual | running | completed: None  ← STUCK
2026-01-07 20:56:52 | admin  | completed | completed: 2026-01-07 21:01:11
```

**Timeline**:
| Time (UTC) | Event |
|------------|-------|
| 2026-01-07 21:01:11 | Last successful batch completed (original Testscotty) |
| 2026-01-08 19:15:38 | Yaphe 5M portfolio created |
| 2026-01-08 19:15:38 | Onboarding batch should have triggered → **BLOCKED or FAILED** |
| 2026-01-09 01:21:47 | Manual batch triggered → now **STUCK** |

**Why symbols are in universe**: The `ensure_symbols_in_universe()` call may have succeeded before the batch crashed, or there's a separate code path that adds symbols.

### Implications

1. **Phase 1 fix is correct** - the try/finally ensures `batch_run_tracker.complete()` is always called
2. **But old code was running** - the deployment happened AFTER the portfolio was created, so the old (unfixed) code ran
3. **Need to clear stuck batch** - before testing again, need to:
   - Restart Railway service (clears in-memory tracker), OR
   - Wait for the stuck batch to timeout (if there's a timeout)

### Next Steps

1. [ ] Restart Railway service to clear stuck `batch_run_tracker`
2. [ ] Manually trigger batch for Yaphe 5M portfolio
3. [ ] Verify snapshots and factor exposures are created
4. [ ] Test with a NEW account created AFTER the deployment

---

## Phase 2: Fix Global Watermark Bug

### Objective
Ensure cron job processes ALL portfolios that are behind, not just check global MAX snapshot date.

### Pre-Fix State (Railway Production)
- 11 portfolios stuck at Jan 5 snapshots
- 1 portfolio (Tech Growth) at Jan 6
- 1 portfolio (Testscotty) at Jan 7
- Global MAX = Jan 7, so cron thinks "all caught up"

### Design Decision (January 8, 2026)

**Chosen Approach**: Hybrid (MIN of MAX + per-date portfolio filtering)

**Options Considered**:
| Option | Description | Verdict |
|--------|-------------|---------|
| Option 1 | MIN of per-portfolio MAX dates | Simple but reprocesses already-current portfolios |
| Option 2 | Process each portfolio independently | Efficient but complex, loses batch efficiency |
| Option 3 | Global MAX + per-date filtering | Efficient but unclear start date |
| **Hybrid** | MIN of MAX + per-date filtering | **CHOSEN** - Best of both |

**Rationale**:
- MIN of MAX gives clear, simple date range calculation
- Per-date filtering avoids reprocessing already-current portfolios
- Processing time is already a concern (~15 min per onboarding) - efficiency matters

### Implementation

**File**: `backend/app/batch/batch_orchestrator.py`

**Status**: ✅ IMPLEMENTED (January 8, 2026)

**Changes Made**:
- [x] Modify `_get_last_batch_run_date()` to use MIN of per-portfolio MAX dates
- [x] Add `_get_portfolios_with_snapshot(db, date)` helper method
- [x] Add `_get_all_active_portfolio_ids(db)` helper method
- [x] Add per-date portfolio filtering in `_execute_batch_phases()`

**Code Review**: See `CODE_REVIEW_REQUEST_PHASE2_GLOBAL_WATERMARK.md`

**Key Code Changes**:

1. **`_get_last_batch_run_date()`** - MIN of MAX watermark:
```python
# Subquery: Get MAX snapshot date for each portfolio
subquery = (
    select(
        PortfolioSnapshot.portfolio_id,
        func.max(PortfolioSnapshot.snapshot_date).label('max_date')
    )
    .group_by(PortfolioSnapshot.portfolio_id)
    .subquery()
)
# Main query: Get the MIN of those max dates
query = select(func.min(subquery.c.max_date))
```

2. **Per-date filtering** in processing loop:
```python
for calc_date in missing_dates:
    portfolios_with_snapshot = await self._get_portfolios_with_snapshot(db, calc_date)
    portfolios_to_process = [p for p in all_portfolios if p not in portfolios_with_snapshot]
    if not portfolios_to_process:
        logger.debug(f"Skipping {calc_date}: all portfolios already have snapshots")
        continue
    # Process only portfolios_to_process for this date
```

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
- [ ] Verified logs show "System watermark (most lagging portfolio): YYYY-MM-DD"
- [ ] Verified logs show "Skipping {date}: all portfolios already have snapshots" for caught-up dates

### Notes
- Full implementation plan in `TESTSCOTTY_BATCH_PROCESSING_DEBUG_AND_FIX_PLAN.md` Phase 2 section
- This fix applies to cron job path only (onboarding uses scoped mode from Phase 5)

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

## Phase 4: Add batch_run_tracker Timeout & Cleanup

### Objective
Make the batch system self-healing when batches crash or hang, eliminating the need for manual Railway restarts.

### Problem Statement
The `batch_run_tracker` is an in-memory singleton that prevents concurrent batch runs. If a batch crashes without calling `complete()`, the flag stays stuck until server restart, blocking ALL subsequent batches.

**Discovered during**: Testscotty2 verification test (Jan 8, 2026)

### Pre-Fix State
- `batch_run_tracker` has no timeout mechanism
- Crashed batches leave tracker stuck indefinitely
- Only fix is manual Railway restart
- No automatic cleanup on server startup

### Implementation

**Files to Modify**:
- `backend/app/batch/batch_run_tracker.py` - Add timeout logic
- `backend/app/main.py` - Add startup cleanup

**Status**: NOT STARTED

**Changes Required**:

#### Part A: Add Timeout to In-Memory Tracker

```python
# batch_run_tracker.py
class BatchRunTracker:
    def __init__(self, timeout_minutes=30):
        self._running = False
        self._started_at = None
        self._timeout = timedelta(minutes=timeout_minutes)

    def is_running(self) -> bool:
        if self._running and self._started_at:
            # Auto-expire if running too long
            if datetime.utcnow() - self._started_at > self._timeout:
                logger.warning(f"Batch auto-expired after {self._timeout}")
                self._running = False
                return False
        return self._running

    def start(self):
        if self.is_running():  # Uses timeout check
            raise BatchAlreadyRunningError()
        self._running = True
        self._started_at = datetime.utcnow()

    def complete(self):
        self._running = False
        self._started_at = None
```

#### Part B: Add Startup Cleanup for Database Records

```python
# In app startup (main.py or lifespan)
async def cleanup_stale_batches():
    """Mark any batch 'running' for >30 min as 'failed'"""
    async with get_async_session() as db:
        await db.execute(text("""
            UPDATE batch_run_history
            SET status = 'failed',
                completed_at = NOW(),
                notes = 'Auto-failed: exceeded 30 minute timeout'
            WHERE status = 'running'
            AND started_at < NOW() - INTERVAL '30 minutes'
        """))
        await db.commit()
```

### Design Decisions

1. **Timeout value**: 30 minutes
   - Longest normal batch run is ~15-20 minutes
   - 30 minutes gives buffer for slow runs
   - Can be made configurable via environment variable

2. **Dual approach**:
   - In-memory timeout: Self-heals during runtime
   - Startup cleanup: Handles restart scenarios and keeps DB accurate

3. **Logging**: Log when auto-expiring so we can track crash frequency

### Verification Steps

1. [ ] Unit test: Verify tracker auto-expires after timeout
2. [ ] Integration test: Start batch, kill process, verify new batch can start after timeout
3. [ ] Startup test: Create stale "running" record, restart server, verify it's marked "failed"

### Post-Fix Verification
- [ ] Deployed to Railway
- [ ] Simulated stuck batch (or waited for natural occurrence)
- [ ] Verified system auto-recovered without restart
- [ ] Verified stale DB records cleaned up on startup

### Notes
- This is a **preventive fix** - makes the system resilient to future crashes
- Combined with Phase 1's try/finally, crashes should be rare
- But when they do happen, system will self-heal

---

## Phase 5: Unify Batch Functions (REFACTOR)

### Objective
Consolidate `run_portfolio_onboarding_backfill()` and `run_daily_batch_with_backfill()` into a single unified function with parameters for different entry points.

### Problem Discovered (January 8, 2026)

During Testscotty3 debugging, we found the batch was processing **ALL 1,193 symbols** in the symbol universe when it only needed **~30 symbols** (13 positions + 17 factor ETFs). This caused:
- Excessive runtime (~4+ hours estimated vs ~10 minutes expected)
- Polygon API rate limiting (429 errors)
- Unnecessary database writes

### Root Cause

When we created `run_portfolio_onboarding_backfill()` as a separate function from `run_daily_batch_with_backfill()`, we:
1. Created code duplication (two similar functions to maintain)
2. Did NOT scope the symbol collection to just the portfolio's symbols
3. Made debugging harder (bugs can exist in one path but not the other)

### Proposed Solution

Create ONE unified `run_batch()` function with parameters:

```python
async def run_batch(
    portfolio_id: Optional[str] = None,  # If None, process all portfolios
    source: str = "cron",                # "cron" | "onboarding" | "settings" | "admin"
    backfill_mode: bool = True,          # True = historical, False = today only
    symbols_scope: str = "auto"          # "auto" | "portfolio" | "universe"
) -> Dict[str, Any]:
```

**Key behavior**:
- When `portfolio_id` is provided → only fetch portfolio's symbols + factor ETFs (~30 symbols)
- When `portfolio_id` is None → fetch entire universe (cron job behavior)

### Implementation Status

**Status**: NOT STARTED - **NEXT PRIORITY**

**Files to Modify**:
- [ ] `backend/app/batch/batch_orchestrator.py` - Unify functions
- [ ] `backend/app/api/v1/portfolios.py` - Update to use unified function
- [ ] `backend/app/api/v1/endpoints/admin_batch.py` - Update to use unified function
- [ ] `backend/app/batch/scheduler_config.py` - Update cron to use unified function

### Expected Benefits
1. Single code path = easier debugging
2. **~40x faster** for single-portfolio batches (30 vs 1,193 symbols)
3. Consistent behavior across all entry points
4. Reduced API rate limiting issues

### Import Fix (January 8, 2026)

While debugging, we also fixed a blocking bug:
- **Bug**: `ImportError: cannot import name 'get_most_recent_trading_day' from 'app.utils.trading_calendar'`
- **Fix**: Changed import to `from app.core.trading_calendar import get_most_recent_trading_day`
- **Commit**: `7d8b0e2a` - "fix: Correct import path for get_most_recent_trading_day"

This fix allows the batch to START, but it still runs inefficiently until Phase 5 is implemented.

---

## Timeline

| Date | Action | Result |
|------|--------|--------|
| 2026-01-08 | Initial analysis and plan created | 3 bugs identified |
| 2026-01-08 | Phase 1 Part A implemented | Added Phase 1.5 and 1.75 to `_run_sequence_with_session()` |
| 2026-01-08 | Phase 1 Part B implemented (v1) | Changed onboarding to use `run_daily_batch_with_backfill()` |
| 2026-01-08 | Code review identified issues | Global watermark problems with Part B v1 |
| 2026-01-08 | Phase 1 Part B revised (v2) | Created `run_portfolio_onboarding_backfill()` method |
| 2026-01-08 | Code review v2 identified issues | batch_run_tracker cleanup, Phase 1.5 corruption |
| 2026-01-08 | Phase 1 Part B revised (v3) | Added try/finally, scoped symbol processing |
| 2026-01-08 | Code review request v3 written | `CODE_REVIEW_REQUEST_BATCH.md` |
| 2026-01-08 | Pushed to origin/main | Railway deployment triggered |
| 2026-01-08 | Testscotty2 verification test | Onboarding batch blocked by stuck batch_run_tracker |
| 2026-01-08 | Phase 4 added to plan | batch_run_tracker timeout & cleanup |
| 2026-01-08 | Testscotty3 debugging session | Found ImportError blocking batch start |
| 2026-01-08 | Import fix deployed | `7d8b0e2a` - Fixed `get_most_recent_trading_day` import path |
| 2026-01-08 | Batch now runs but inefficient | Processing 1,193 symbols instead of ~30 |
| 2026-01-08 | Phase 5 added to plan | Unify batch functions for efficiency |
| 2026-01-08 | Phase 5 & 6 implemented | Unified batch function + error handling hardening |
| 2026-01-08 | Code review iterations (3 rounds) | asyncio.CancelledError, progress tracking, commit ordering |
| 2026-01-08 | Pushed 9 commits to origin/main | Railway auto-deployed |
| 2026-01-08 | Railway verification (testscotty4) | ✅ 254/254 dates in 894s (~15 min), 27 symbols |
| 2026-01-08 | Phase 7 planned | Real-time onboarding status updates with User/Debug modes |
| 2026-01-08 | Phase 2 implemented | Hybrid approach: MIN of MAX + per-date filtering |
| | | |

---

## Code Review Checklist

Before pushing to remote:
- [x] Phase 1 changes reviewed by AI agent (Claude Opus 4.5)
- [ ] Phase 2 changes reviewed by AI agent
- [ ] Phase 3 changes reviewed by AI agent
- [ ] Phase 4 changes reviewed by AI agent
- [x] Phase 5 changes reviewed by AI agent (3 iterations)
- [x] Phase 6 changes reviewed by AI agent (3 iterations)
- [x] Phase 5 & 6 verified on Railway (testscotty4)
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

**Phase 4 Rollback**:
```bash
git revert <phase4-commit-hash>
git push origin main
```

**Phase 5 Rollback**:
```bash
# Revert all Phase 5 commits in reverse order
git revert a020f1ca  # fix: Address code review findings
git revert ffb68fa1  # docs: Add code review request
git revert 3ae56503  # feat: Implement Phase 5 unified batch
git revert 337e7d39  # docs: Add Phase 5 plan
git push origin main
```

**Phase 6 Rollback**:
```bash
# Revert all Phase 6 commits in reverse order
git revert 1357bd7b  # fix: Update progress tracker only after commit
git revert 5749f64a  # fix: Track actual progress for crash reporting
git revert f82496d7  # fix: Catch asyncio.CancelledError
git revert 9963c9af  # feat: Implement Phase 6 try/except/finally
git revert be0c7052  # docs: Add Phase 6 plan
git push origin main
```
