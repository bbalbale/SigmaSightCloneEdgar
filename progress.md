# SigmaSight Progress Log

## 2026-01-11: Phase 7.4 - Nine-Phase Batch Tracking

### Completed

**Backend Changes:**
- Replaced bundled `phase_2_6` tracking with individual tracking for all 9 phases
- Added `BatchActivityLogHandler` to capture INFO logs from calculation engines (`app.batch`, `app.calculations`, `app.services.market_data`, `app.services.company_profile`)
- Added `PHASE_ORDER` constant for consistent UI display ordering
- Fixed per-date phase tracking: phases 3, 4, 6 now track once per batch with aggregate stats
- Added duplicate handler prevention in `attach()` to handle leaked handlers from failed runs
- Added context manager support (`__enter__`/`__exit__`) for optional try/finally usage

**Frontend Changes:**
- Updated `PhaseList.tsx` with correct 9-phase IDs and names
- Updated `OnboardingProgress.tsx` with static "9 processing phases" header

**Files Modified:**
- `backend/app/batch/batch_orchestrator.py`
- `backend/app/batch/batch_run_tracker.py`
- `frontend/src/components/onboarding/PhaseList.tsx`
- `frontend/src/components/onboarding/OnboardingProgress.tsx`
- `backend/_docs/CODE_REVIEW_REQUEST_PHASE7.4_NINE_PHASE_TRACKING.md`

**Code Review:** 3 rounds completed, all issues resolved

**Deployment:** Deployed to Railway (commit 961ae702)

**Testing Results:**
- Onboarding flow tested with new portfolio "Tech 4"
- 9-phase progress UI displays correctly with real-time updates
- Verbose activity log captures calculation engine INFO messages
- Downloaded log file contains detailed debugging information
- Batch completed in 17 seconds for 5 dates, 16 positions

### Known Issues Found During Testing

**Bug: Phases 0, 2, 5 Never Run During Onboarding**
- **Symptom:** Only 6/9 phases appear in completion summary
- **Root Cause:** `is_historical = calculation_date < date.today()` marks ALL backfill dates as historical
- **Impact:** Company Profile Sync, Fundamental Data Collection, and Sector Tag Restoration never execute for new portfolios
- **Status:** Fix in progress (see Phase 7.4.1)

---

## 2026-01-11: Phase 7.4.1 - Fix Historical Date Logic (Implemented)

### Problem
For onboarding, the batch processes dates from portfolio entry_date to today. If today is 2026-01-11 and the batch processes 2026-01-05 to 2026-01-09, all dates are considered "historical" and phases 0, 2, 5 are skipped entirely.

### Solution
Run phases 0, 2, 5 on the **final date** of the batch, not just on today's date:
```python
# OLD:
is_historical = calculation_date < date.today()

# NEW:
is_final_date = (i == len(missing_dates))
is_historical = calculation_date < date.today() and not is_final_date
```

### Files Modified
- `backend/app/batch/batch_orchestrator.py` - Added `is_final_date` parameter

### Status
- [x] Implement fix
- [ ] Code review
- [ ] Deploy to Railway
- [ ] Verify phases 0, 2, 5 run during onboarding

---

## 2026-01-11: Phase 7.6 - Unified Progress/Completion Screen (Implemented)

### Problem
The current onboarding flow has two completely different screens:
1. **Progress Screen** - Shows rich information during processing (9 phases, activity log)
2. **Completion Screen** - Shows minimal summary (just checkmark and phase count)

When the batch completes, all the rich progress information is discarded. This is a jarring transition that removes useful context.

### Solution
Keep the same layout but change the **state** when batch completes. `OnboardingProgress` now handles all states: `running`, `completed`, `partial`, `failed`.

### Implementation

**OnboardingProgress.tsx Changes:**
- Added `getUIState()` helper to map backend status to UI state
- Added `isTerminal()` helper to determine when polling should stop
- Added `getUIConfig()` helper for state-based UI configuration
- Different icons: Rocket (running), CheckCircle (completed), AlertTriangle (partial), XCircle (failed)
- Different gradient backgrounds per state
- Different titles/subtitles per state
- Added button section for terminal states (Download Log + Dashboard)
- Respects `autoScroll` prop for ActivityLog
- Clears onboarding session on terminal state
- Caches portfolio name in local state before session clear (Code Review Fix)

**ActivityLog.tsx Changes:**
- Added `autoScroll` prop (defaults to true)
- Auto-scroll is disabled in terminal states to allow manual scrolling

**progress/page.tsx Changes:**
- Removed conditional routing to `OnboardingComplete`
- Removed conditional routing to `OnboardingError`
- Unified flow uses `OnboardingProgress` for all states

**useOnboardingStatus.ts Changes (Code Review Fix):**
- Added `partial` to terminal state stop condition (line 77)
- Updated JSDoc to document all terminal states

**onboardingService.ts Changes (Code Review Fix):**
- Added `partial` to `OnboardingStatusResponse.status` type union

**Deprecation:**
- `OnboardingComplete.tsx` - Added deprecation notice
- `OnboardingError.tsx` - Added deprecation notice
- Both components will be removed in a future release

### Files Modified
- `frontend/src/components/onboarding/OnboardingProgress.tsx`
- `frontend/src/components/onboarding/ActivityLog.tsx`
- `frontend/app/onboarding/progress/page.tsx`
- `frontend/src/components/onboarding/OnboardingComplete.tsx` (deprecation notice)
- `frontend/src/components/onboarding/OnboardingError.tsx` (deprecation notice)
- `frontend/app/onboarding/upload/page.tsx` (comment update)
- `frontend/src/hooks/useOnboardingStatus.ts` (Code Review Fix: add `partial` to terminal states)
- `frontend/src/services/onboardingService.ts` (add `partial` to status type)

### Design Document
See Section 13 in `backend/_docs/TESTSCOTTY_BATCH_STATUS_UI.md`

### Code Review Fixes (Round 1)
1. **Medium: Polling for partial status** - Added `partial` to terminal state condition in `useOnboardingStatus.ts` line 77. Updated status type in `onboardingService.ts` to include `partial`.
2. **Low: Portfolio name lost on session clear** - Added local state caching of portfolio name in `OnboardingProgress.tsx` before `clearOnboardingSession()` is called. Name is cached on mount and persists through session clear.

### Status
- [x] Implement unified progress/completion screen
- [x] Handle all terminal states (completed, partial, failed)
- [x] Add button section for terminal states
- [x] Disable auto-scroll in terminal states
- [x] Add deprecation notices to old components
- [x] TypeScript type check passes
- [x] Code review Round 1 - fixes applied
- [ ] Deploy to Railway
- [ ] Test all state transitions
