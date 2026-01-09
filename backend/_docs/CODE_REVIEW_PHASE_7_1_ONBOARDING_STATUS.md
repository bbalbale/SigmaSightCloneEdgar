# Code Review Request: Phase 7.1 - Onboarding Status Endpoint

**Date**: 2026-01-09
**Author**: Claude (AI Assistant)
**Reviewer**: Elliott Ng
**Status**: ✅ Fixes Applied (Ready for Final Review)

---

## Post-Review Fixes Applied (2026-01-09)

Following code reviews from Gemini and a second reviewer, three issues were identified and fixed:

| Severity | Issue | Fix Applied |
|----------|-------|-------------|
| **Critical** | `UnboundLocalError` if first `collect_daily_market_data` raises | Initialized `phase1_result = None` before loop |
| **Medium** | Race condition - `portfolio_id` not set until async task starts | Set `portfolio_id` in `CurrentBatchRun` constructor immediately |
| **Medium** | Status endpoint never returns `completed`/`failed` | Added `_completed_runs` dict with 60s TTL retention |

### Fix Details

**Fix 1: `batch_orchestrator.py:360-361`**
```python
# Initialize before loop to prevent UnboundLocalError if first call raises
phase1_result = None
```

**Fix 2: `portfolios.py:576-580`**
```python
run = CurrentBatchRun(
    batch_run_id=batch_run_id,
    started_at=utc_now(),
    triggered_by=current_user.email,
    portfolio_id=str(portfolio_id)  # Set immediately for status endpoint
)
```

**Fix 3: `batch_run_tracker.py`**
- Added `CompletedRunStatus` dataclass
- Added `_completed_runs: Dict[str, CompletedRunStatus]` to tracker
- Modified `complete(success: bool)` to save terminal status before clearing
- Modified `get_onboarding_status()` to check completed runs first
- Added `_cleanup_old_completed()` for TTL enforcement (60 seconds)

### Verification (Round 1)

```
✅ All imports successful
✅ TTL configured: 60 seconds
✅ Running status works
✅ Complete with success flag works
✅ Completed status retained within TTL
✅ Wrong portfolio returns None
```

---

## Post-Review Fixes Round 2 (2026-01-09)

Following second round of code review, two additional issues were identified and fixed:

| Severity | Issue | Fix Applied |
|----------|-------|-------------|
| **Critical** | Force rerun ignores `portfolio_ids` and processes ALL portfolios | Restructured logic to ALWAYS prefer `portfolio_ids` when provided |
| **Medium** | Retry within 60s TTL shows stale completed/failed status | Clear `_completed_runs[portfolio_id]` in `start()` |

### Fix Details (Round 2)

**Fix 4: `batch_orchestrator.py:644-671` - Force rerun scope**
```python
# Before: force_rerun could process ALL portfolios even when portfolio_ids provided
# After: Always prefer portfolio_ids to respect caller's scope
if portfolio_ids:
    # Caller specified portfolios - use exactly those
    portfolios_to_process = portfolio_ids
elif not scoped_only:
    # force_rerun without specific portfolios: process all (admin use case)
    portfolios_to_process = all_active_portfolios
```

**Fix 5: `batch_run_tracker.py:90-96` - Clear stale status on retry**
```python
def start(self, run: CurrentBatchRun):
    # Clear any stale completed status for this portfolio
    if run.portfolio_id and run.portfolio_id in self._completed_runs:
        del self._completed_runs[run.portfolio_id]
    self._current = run
```

### Verification (Round 2)

```
✅ batch_orchestrator imports successfully
✅ Force rerun now respects caller's portfolio scope
✅ Stale status correctly cleared on retry
```

### Use Case Matrix (Final)

| Use Case | scoped_only | force_rerun | portfolio_ids | Result |
|----------|-------------|-------------|---------------|--------|
| Onboarding (single portfolio) | True | False | [uuid] | Process only that portfolio |
| Admin repair (specific) | False | True | [uuid] | Process only specified portfolio |
| Admin repair (all) | False | True | None | Process ALL active portfolios |
| Cron (normal) | False | False | None | Process portfolios missing snapshots |

---

## Summary

Implemented Phase 7.1: Real-time onboarding status endpoint that provides batch processing progress during the 15-20 minute portfolio setup process. Users can now see actual progress instead of a fake animation.

**Problem Solved**: Users experienced "authorization failed" errors when the frontend tried to poll admin endpoints for batch status. The new endpoint uses regular user authentication (portfolio owner) and provides real-time activity logs.

---

## Files Changed

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `app/batch/batch_run_tracker.py` | Modified | +180 lines |
| `app/batch/batch_orchestrator.py` | Modified | +45 lines |
| `app/api/v1/onboarding_status.py` | **New** | +215 lines |
| `app/api/v1/router.py` | Modified | +2 lines |

**Total**: ~440 lines added/modified

---

## Implementation Details

### 1. `batch_run_tracker.py` - Activity Log & Phase Tracking

**Added dataclasses:**
- `ActivityLogEntry`: Stores timestamp, message, and level (info/warning/error)
- `PhaseProgress`: Tracks phase status, progress counts, and duration

**Added methods to `BatchRunTracker`:**
- `add_activity(message, level)` - Add log entry (capped at 50 entries)
- `get_activity_log(limit)` - Get recent entries as dicts
- `set_portfolio_id(portfolio_id)` - Track which portfolio is processing
- `start_phase(phase_id, phase_name, total, unit)` - Begin phase tracking
- `update_phase_progress(phase_id, current, total)` - Update progress
- `complete_phase(phase_id, success, summary)` - Mark phase done
- `get_phase_progress()` - Get all phase progress for API
- `get_onboarding_status(portfolio_id)` - Full status for specific portfolio

**Key design decision**: Activity log capped at 50 entries to prevent memory growth during long batches.

### 2. `batch_orchestrator.py` - Emit Activity Log Entries

**Instrumented phases:**
- Phase 1 (Market Data): Start, progress every 5th date, completion summary
- Phase 1.5 (Factor Analysis): Start, completion
- Phase 1.75 (Symbol Metrics): Start, completion
- Phase 2-6 (Snapshots & Analytics): Start, progress every 5th date, completion

**Key design decision**: Show every 5th date to avoid log spam (254 dates → ~50 entries).

**Added `set_portfolio_id()` call** in `run_portfolio_onboarding_backfill()` to enable per-portfolio status queries.

### 3. `onboarding_status.py` - New API Endpoint

**Endpoint**: `GET /api/v1/onboarding/status/{portfolio_id}`

**Authentication**: Regular Clerk JWT (NOT admin-only)

**Authorization**: User must own the portfolio

**Response schema**:
```python
{
    "portfolio_id": "uuid",
    "status": "running" | "completed" | "failed" | "not_found",
    "started_at": "ISO timestamp",
    "elapsed_seconds": 123,
    "overall_progress": {
        "current_phase": "phase_2_6",
        "current_phase_name": "Portfolio Snapshots & Analytics",
        "phases_completed": 2,
        "phases_total": 4,
        "percent_complete": 45
    },
    "current_phase_progress": {
        "current": 120,
        "total": 254,
        "unit": "dates"
    },
    "activity_log": [
        {"timestamp": "...", "message": "...", "level": "info"},
        ...
    ],
    "phases": [
        {"phase_id": "phase_1", "phase_name": "Market Data Collection", "status": "completed", ...},
        ...
    ]
}
```

### 4. `router.py` - Register Endpoint

Added import and router registration with `/onboarding` prefix.

---

## Testing Recommendations

### Manual Testing

1. **Start a new portfolio onboarding** via the frontend
2. **Poll the status endpoint** during processing:
   ```bash
   curl -H "Authorization: Bearer $JWT" \
     "https://localhost:8000/api/v1/onboarding/status/{portfolio_id}"
   ```
3. **Verify**:
   - Activity log shows real-time entries
   - Phase progress updates
   - Percent complete increases
   - Status transitions from "running" to "not_found" after completion

### Edge Cases to Test

1. **Non-existent portfolio**: Should return 404
2. **Wrong user's portfolio**: Should return 404 (not 403, for security)
3. **No batch running**: Should return `status: "not_found"`
4. **Poll during Phase 1**: Should show market data fetching activity
5. **Poll during Phase 2-6**: Should show snapshot creation activity

### Automated Tests (Future)

Consider adding:
- Unit tests for `BatchRunTracker` methods
- Integration test for status endpoint with mock batch

---

## Frontend Integration Notes

### Polling Strategy

```typescript
const POLL_INTERVAL_MS = 2000;  // Poll every 2 seconds
const POLL_TIMEOUT_MS = 30 * 60000;  // Give up after 30 minutes

// Example polling hook
const pollStatus = async (portfolioId: string) => {
  const response = await fetch(`/api/v1/onboarding/status/${portfolioId}`, {
    headers: { Authorization: `Bearer ${clerkToken}` }
  });
  return response.json();
};
```

### UI Display

1. Show phases list with status icons (pending/running/completed)
2. Show progress bar for current phase
3. Show activity log (auto-scroll, last ~10 entries)
4. Show elapsed time and overall percent

### Status Handling

| Status | Action |
|--------|--------|
| `running` | Keep polling, show progress |
| `not_found` | Check if portfolio exists, maybe batch finished |
| `completed` | Redirect to portfolio dashboard |
| `failed` | Show error screen with retry option |

---

## Known Limitations

1. **In-memory only**: Status is lost if server restarts during batch. The batch will complete but frontend won't see progress.

2. **Single batch at a time**: Only tracks ONE batch. If two portfolios are onboarding simultaneously, only the last one's status is available.

3. **No persistence**: Activity log is not saved to database. This is intentional to keep it lightweight.

4. **No WebSocket/SSE**: Uses polling instead of push. SSE could be added later for real-time updates without polling.

---

## Security Considerations

1. **Portfolio ownership verified**: Users can only see status for their own portfolios

2. **No sensitive data in activity log**: Messages are user-friendly, no internal details exposed

3. **Rate limiting**: Standard API rate limits apply (frontend should not poll faster than 1/sec)

---

## Questions for Review

1. **Activity log retention**: 50 entries max - is this sufficient for 15-20 min batch?

2. **Polling interval**: 2 seconds recommended - should this be configurable?

3. **Phase naming**: Current names are user-friendly but could be more descriptive. Suggestions?

4. **Error handling**: Should failed symbols be shown in activity log, or just summarized at end?

---

## Related Documentation

- **Design doc**: `backend/_docs/TESTSCOTTY_PROGRESS.md` (Phase 7.1 section)
- **API reference**: To be added to `API_REFERENCE_V1.4.6.md`

---

## Deployment Notes

1. No database migrations required (in-memory tracking only)
2. No environment variables required
3. Backward compatible - existing batch processing unchanged
4. Frontend changes needed to use new endpoint

---

**Ready for review!**
