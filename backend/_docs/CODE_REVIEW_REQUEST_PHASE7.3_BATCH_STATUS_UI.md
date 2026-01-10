# Code Review Request: Phase 7.3 Batch Status UI

**Date**: January 10, 2026
**Author**: Claude Opus 4.5
**Branch**: `claude/OnboardingStatusUI-wTqsY`
**Related Design**: `TESTSCOTTY_BATCH_STATUS_UI.md`

---

## Summary

This PR implements the Batch Status UI for the onboarding flow. It replaces the fake progress animation with real-time status updates during the ~15 minute portfolio setup process.

### Changes Overview

**Backend (2 files)**:
- Extended `batch_run_tracker.py` with full log storage (5000 entries)
- Added log download endpoint to `onboarding_status.py`

**Frontend (12 files)**:
- New `useOnboardingStatus` hook for polling
- New onboarding components for status display
- New progress page at `/onboarding/progress`
- Updated `onboardingService.ts` with new methods and types

---

## Backend Changes

### 1. `backend/app/batch/batch_run_tracker.py`

**Changes**:
- Added `MAX_FULL_LOG_ENTRIES = 5000` constant
- Added `full_activity_log` field to `CurrentBatchRun` dataclass
- Modified `add_activity()` to also append to full log
- Added `get_full_activity_log()` method for download

**Rationale**: The existing condensed log (50 entries) is for real-time UI display. The full log (5000 entries) enables complete log download for debugging and support.

```python
# New field in CurrentBatchRun
full_activity_log: List[ActivityLogEntry] = field(default_factory=list)

# New method
def get_full_activity_log(self) -> List[Dict[str, Any]]:
    """Get complete activity log for download (up to 5000 entries)."""
```

### 2. `backend/app/api/v1/onboarding_status.py`

**Changes**:
- Added `GET /status/{portfolio_id}/logs` endpoint
- Added `_format_duration()` helper function
- Added `_build_txt_log()` helper for TXT format generation

**Endpoint Details**:
- **Path**: `GET /api/v1/onboarding/status/{portfolio_id}/logs`
- **Auth**: Clerk JWT (user must own portfolio)
- **Query Params**: `format` (txt|json, default: txt)
- **Response**: File download with `Content-Disposition` header

**Security**: Validates portfolio ownership before returning logs.

---

## Frontend Changes

### 1. `frontend/src/hooks/useOnboardingStatus.ts` (NEW)

Custom hook for polling the status endpoint:
- Polls every 2 seconds (configurable)
- Tracks consecutive `not_found` responses
- Auto-stops polling on `completed` or `failed`
- Returns `{ status, isLoading, error, refetch, notFoundCount }`

### 2. `frontend/src/services/onboardingService.ts`

Added types and methods:
- `ActivityLogEntry`, `PhaseDetail`, `OnboardingStatusResponse` types
- `getOnboardingStatus(portfolioId)` method
- `downloadLogs(portfolioId, format)` method

### 3. Component Files (8 NEW)

| Component | Purpose |
|-----------|---------|
| `PhaseListItem.tsx` | Single phase with status icon, progress bar, duration |
| `PhaseList.tsx` | List of all 9 phases with default fallback |
| `ActivityLogEntry.tsx` | Single log entry (timestamp, level, message) |
| `ActivityLog.tsx` | Scrollable log with smart auto-scroll |
| `DownloadLogButton.tsx` | Download button with loading state |
| `OnboardingProgress.tsx` | Main progress screen during batch |
| `OnboardingComplete.tsx` | Success screen with summary |
| `OnboardingError.tsx` | Failure screen with retry option |
| `OnboardingStatusUnavailable.tsx` | Recovery screen for lost status |

### 4. `frontend/app/onboarding/progress/page.tsx` (NEW)

Progress page that:
- Reads `portfolioId` from URL query param or store
- Uses `useOnboardingStatus` hook for polling
- Renders appropriate screen based on status

---

## Design Decisions

### 1. In-Memory Log Storage (Not DB)

Per design doc Section 9.2, logs are stored in memory during batch processing. This is acceptable for MVP because:
- Logs only matter during/after batch processing
- Simpler implementation, no DB migration needed
- Can add DB persistence later if needed

### 2. Polling (Not SSE)

Using 2-second polling interval instead of SSE because:
- Simpler to implement and debug
- Proven pattern for progress updates
- Design doc explicitly chose polling (Section 9 decisions)

### 3. Download Button Only on Terminal Screens

Download button is intentionally hidden during progress:
- Reduces UI clutter
- Log is incomplete during processing
- Matches design doc spec

### 4. Smart Auto-Scroll

Activity log auto-scrolls to bottom unless user scrolls up:
- Allows reading earlier entries without fighting auto-scroll
- Shows "auto-scrolling" indicator when paused

---

## Testing Checklist

### Backend
- [ ] `GET /status/{portfolio_id}/logs` returns 404 when no logs available
- [ ] `GET /status/{portfolio_id}/logs?format=txt` returns properly formatted text file
- [ ] `GET /status/{portfolio_id}/logs?format=json` returns valid JSON
- [ ] Portfolio ownership is validated (403 for other users' portfolios)

### Frontend
- [ ] Progress page loads and starts polling
- [ ] Phase list shows correct status icons (pending/running/completed)
- [ ] Progress bar animates smoothly for running phase
- [ ] Activity log auto-scrolls and shows entries
- [ ] Completion screen shows summary and download button
- [ ] Error screen shows failed phase and options
- [ ] StatusUnavailable screen shows after 3 not_found responses
- [ ] Download button triggers file download

---

## Files Changed Summary

| Path | Status | Lines |
|------|--------|-------|
| `backend/app/batch/batch_run_tracker.py` | Modified | +30 |
| `backend/app/api/v1/onboarding_status.py` | Modified | +160 |
| `frontend/src/hooks/useOnboardingStatus.ts` | New | 100 |
| `frontend/src/services/onboardingService.ts` | Modified | +90 |
| `frontend/src/components/onboarding/PhaseListItem.tsx` | New | 115 |
| `frontend/src/components/onboarding/PhaseList.tsx` | New | 70 |
| `frontend/src/components/onboarding/ActivityLogEntry.tsx` | New | 55 |
| `frontend/src/components/onboarding/ActivityLog.tsx` | New | 90 |
| `frontend/src/components/onboarding/DownloadLogButton.tsx` | New | 60 |
| `frontend/src/components/onboarding/OnboardingProgress.tsx` | New | 100 |
| `frontend/src/components/onboarding/OnboardingComplete.tsx` | New | 100 |
| `frontend/src/components/onboarding/OnboardingError.tsx` | New | 110 |
| `frontend/src/components/onboarding/OnboardingStatusUnavailable.tsx` | New | 50 |
| `frontend/app/onboarding/progress/page.tsx` | New | 100 |
| `backend/_docs/TESTSCOTTY_PROGRESS.md` | Modified | +60 |

---

## Review Focus Areas

1. **Security**: Is portfolio ownership properly validated in the logs endpoint?
2. **Memory**: Is 5000-entry log cap appropriate? Should it be configurable?
3. **Error Handling**: Are all error cases covered in the frontend?
4. **UX**: Does the auto-scroll behavior make sense?
5. **Types**: Are TypeScript types complete and accurate?

---

## Deployment Notes

- No database migrations required
- No environment variables needed
- Backend changes are additive (new endpoint, extended existing functionality)
- Frontend changes create new route `/onboarding/progress`

---

## Related Issues

- Phase 7.1: Backend status endpoint (already deployed)
- Phase 7.2: Invite code gate (already deployed)
- Design doc: `TESTSCOTTY_BATCH_STATUS_UI.md`
