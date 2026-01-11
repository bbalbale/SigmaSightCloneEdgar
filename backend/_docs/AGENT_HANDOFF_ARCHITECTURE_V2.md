# Agent Handoff: Architecture V2 Implementation

**Created**: 2026-01-11
**Purpose**: Provide context for the agent implementing Architecture V2 (decoupled symbol-portfolio processing)
**Related**: `PlanningDocs/ARCHITECTURE_V2_IMPLEMENTATION_PLAN.md` (on BatchProcessUpdate branch)

---

## 1. Executive Summary

This document captures the current state of the onboarding flow and batch processing system as of January 11, 2026. The Architecture V2 redesign should preserve certain user-facing requirements while fundamentally changing the backend processing model.

**Key Insight**: Architecture V2 will make the current complex onboarding progress UI largely obsolete because onboarding will complete in <5 seconds for known symbols. However, the Phase 7.x tracking infrastructure should be **preserved for the daily symbol batch** and admin operations.

---

## 2. Current State Summary (January 11, 2026)

### 2.1 Recent Deployments (Phase 7.x)

| Phase | Description | Status | Commit |
|-------|-------------|--------|--------|
| 7.4 | 9-phase individual tracking | Deployed | `961ae702` |
| 7.4.1 | `is_final_date` fix for phases 0,2,5 | Deployed | `64b9b41e` |
| 7.6 | Unified progress/completion screen | Deployed | `64b9b41e` |

### 2.2 Current Batch Processing Phases (9 Phases)

The current batch orchestrator (`batch_orchestrator.py`) runs these phases:

| Phase ID | Phase Name | Runs Per | Notes |
|----------|------------|----------|-------|
| `phase_0` | Company Profile Sync | Final date only | Syncs sector, industry, beta from FMP |
| `phase_1` | Market Data Collection | Each date | 1-year historical prices |
| `phase_1_5` | Factor Analysis | Once per batch | Ridge + spread factors |
| `phase_1_75` | Symbol Metrics | Once per batch | Returns, valuations |
| `phase_2` | Fundamental Data Collection | Final date only | Income, balance, cash flow |
| `phase_3` | P&L Calculation & Snapshots | Each date | Daily portfolio valuations |
| `phase_4` | Position Market Value Updates | Each date | Current market values |
| `phase_5` | Sector Tag Restoration | Final date only | Auto-tag positions by sector |
| `phase_6` | Risk Analytics | Each date | Betas, correlations, stress tests |

### 2.3 Current Onboarding Flow (15-30 minutes)

```
User uploads CSV → Create portfolio → Trigger batch →
Poll /api/v1/onboarding/status/{portfolio_id} every 2s →
See 9-phase progress UI → Completion screen (2-3 min typical, up to 30 min)
```

**Key files:**
- `app/api/v1/onboarding.py` - Portfolio creation
- `app/api/v1/onboarding_status.py` - Progress polling endpoint
- `app/batch/batch_orchestrator.py` - 9-phase processing
- `app/batch/batch_run_tracker.py` - Phase tracking infrastructure
- `frontend/src/components/onboarding/OnboardingProgress.tsx` - Unified UI

---

## 3. Requirements to Preserve

### 3.1 User Experience Requirements

1. **Real-time progress visibility**: Users must see what's happening during any wait >5 seconds
2. **Activity log**: Detailed logs for debugging/support (downloadable)
3. **Graceful error handling**: Show distinct states for completed, partial, failed
4. **Terminal state detection**: UI must know when to stop polling

### 3.2 Admin Requirements

1. **Batch monitoring**: Admin dashboard needs to see daily batch progress
2. **Manual triggers**: Admin can force batch runs for specific portfolios
3. **Data quality visibility**: Know what data is stale or missing

### 3.3 Technical Requirements

1. **No data loss during transition**: All calculation history preserved
2. **Backward compatibility**: Existing portfolios continue to work
3. **Graceful degradation**: Handle missing symbols, API failures

---

## 4. What Architecture V2 Deprecates (Onboarding Only)

Per the V2 plan (Part 10.9), these are deprecated **for onboarding only**:

| Component | Status | Notes |
|-----------|--------|-------|
| 9-phase progress UI for onboarding | Deprecated | Onboarding <5 sec |
| Activity log for onboarding | Deprecated | No long process to log |
| Phase progress tracking for onboarding | Deprecated | Simple ready/pending/error |
| `batch_trigger_service` for onboarding | Deprecated | No batch trigger needed |
| 60-second completed status TTL | Reduce to 10s | Faster onboarding completion |

---

## 5. What Architecture V2 Preserves

| Component | Status | Notes |
|-----------|--------|-------|
| `batch_run_tracker.py` | **PRESERVE** | Reused for daily symbol batch |
| `batch_orchestrator.py` | **PRESERVE** | Still used for admin operations |
| Phase 7.x tracking infrastructure | **PRESERVE** | Symbol batch uses 6 phases |
| Activity logging system | **PRESERVE** | For symbol batch monitoring |
| Completed status TTL | **PRESERVE** | For symbol batch status |

---

## 6. Key Files Reference

### 6.1 Backend - Batch Processing

| File | Purpose | V2 Action |
|------|---------|-----------|
| `batch_orchestrator.py` | Current 9-phase processing | Keep for admin, remove symbol processing |
| `batch_run_tracker.py` | Phase tracking singleton | **PRESERVE** - reuse for symbol batch |
| `analytics_runner.py` | Risk analytics | Add cache check |
| `symbol_factors.py` | Factor calculations | Already symbol-level |

### 6.2 Backend - Onboarding

| File | Purpose | V2 Action |
|------|---------|-----------|
| `onboarding.py` | Portfolio creation | Add symbol check, compute inline |
| `onboarding_status.py` | Progress polling | **SIMPLIFY** to ready/pending/error |
| `batch_trigger_service.py` | Triggers batch | Remove onboarding logic |

### 6.3 Frontend - Onboarding UI

| File | Purpose | V2 Action |
|------|---------|-----------|
| `OnboardingProgress.tsx` | Unified progress/completion | Keep for symbol onboarding edge case |
| `PhaseList.tsx` | 9-phase display | May simplify or remove |
| `ActivityLog.tsx` | Scrollable log | Keep for edge cases |
| `useOnboardingStatus.ts` | Polling hook | Simplify polling logic |

---

## 7. Phase 7.x Tracking Infrastructure

### 7.1 Core Classes (batch_run_tracker.py)

```python
@dataclass
class CurrentBatchRun:
    batch_run_id: str
    started_at: datetime
    triggered_by: str
    portfolio_ids: List[str]  # Optional for portfolio-scoped batch
    status: str  # "running", "completed", "failed", "partial"

@dataclass
class PhaseProgress:
    phase_id: str
    phase_name: str
    status: str  # "pending", "running", "completed", "failed"
    current: int
    total: int
    unit: str  # "symbols", "dates", "positions"
    duration_seconds: Optional[float]

@dataclass
class ActivityLogEntry:
    timestamp: datetime
    message: str
    level: str  # "info", "warning", "error"
```

### 7.2 Key Methods

```python
# Starting/completing batch
batch_run_tracker.start(CurrentBatchRun(...))
batch_run_tracker.complete(success: bool)

# Phase tracking
batch_run_tracker.start_phase(phase_id, phase_name, total, unit)
batch_run_tracker.update_phase_progress(phase_id, current)
batch_run_tracker.complete_phase(phase_id, success, summary)

# Activity logging
batch_run_tracker.add_activity(message, level)
batch_run_tracker.get_activity_log() -> List[ActivityLogEntry]

# Status retrieval
batch_run_tracker.get_onboarding_status(portfolio_id) -> OnboardingStatusResponse
```

### 7.3 Completed Run Retention

```python
# After batch completes, status is retained for 60 seconds
# This prevents frontend from seeing "not_found" immediately after completion
_completed_runs: Dict[str, CompletedRunStatus]  # TTL: 60 seconds
```

---

## 8. Frontend State Machine (OnboardingProgress.tsx)

### 8.1 UI States

```typescript
type UIState = 'running' | 'completed' | 'partial' | 'failed'

// Backend status → UI state mapping
function getUIState(status: string | undefined): UIState {
  switch (status) {
    case 'completed': return 'completed'
    case 'partial': return 'partial'
    case 'failed': return 'failed'
    default: return 'running'
  }
}
```

### 8.2 Terminal States

```typescript
// Polling stops for these states
function isTerminal(status: string | undefined): boolean {
  return ['completed', 'partial', 'failed'].includes(status ?? '')
}
```

### 8.3 State-Specific UI

| State | Icon | Background | Title |
|-------|------|------------|-------|
| running | Rocket | Blue gradient | "Setting Up Your Portfolio" |
| completed | CheckCircle | Green gradient | "Portfolio Setup Complete!" |
| partial | AlertTriangle | Yellow gradient | "Completed with Warnings" |
| failed | XCircle | Red gradient | "Setup Interrupted" |

---

## 9. API Contracts

### 9.1 Onboarding Status Response

```typescript
interface OnboardingStatusResponse {
  portfolio_id: string;
  status: 'running' | 'completed' | 'partial' | 'failed' | 'not_found';
  started_at: string | null;
  elapsed_seconds: number;

  overall_progress: {
    current_phase: string | null;
    current_phase_name: string | null;
    phases_completed: number;
    phases_total: number;
    percent_complete: number;
  } | null;

  current_phase_progress: {
    current: number;
    total: number;
    unit: string;
  } | null;

  activity_log: Array<{
    timestamp: string;
    message: string;
    level: 'info' | 'warning' | 'error';
  }>;

  phases: Array<{
    phase_id: string;
    phase_name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    current: number;
    total: number;
    unit: string;
    duration_seconds: number | null;
  }> | null;
}
```

### 9.2 V2 Simplified Response (for onboarding)

```typescript
// Per V2 plan Part 10.3.2
interface OnboardingStatusResponseV2 {
  portfolio_id: string;
  status: 'ready' | 'pending' | 'error';
  analytics_available: boolean;
  pending_symbols: string[] | null;
  estimated_seconds_remaining: number | null;
  message: string;
}
```

---

## 10. Testing Verification

### 10.1 Verified Working (2026-01-11)

- [x] 9-phase progress UI displays correctly
- [x] Phase 7.4.1: Phases 0, 2, 5 run on final date
- [x] Phase 7.6: Unified screen shows completion state
- [x] Download Log button works in terminal states
- [x] Auto-scroll disabled in terminal states
- [x] Polling stops for completed/partial/failed

### 10.2 Not Yet Tested

- [ ] `partial` status UI (need to trigger partial completion)
- [ ] `failed` status UI (need to trigger failure)
- [ ] Retry button functionality

---

## 11. Implementation Notes for V2

### 11.1 Symbol Batch Runner

The V2 plan (Part 4.2) shows how `symbol_batch_runner.py` should reuse `batch_run_tracker`:

```python
from app.batch.batch_run_tracker import batch_run_tracker

class SymbolBatchRunner:
    async def run_daily_symbol_batch(self, target_date):
        batch_run_tracker.start(CurrentBatchRun(
            batch_run_id=f"symbol_batch_{target_date.isoformat()}",
            started_at=utc_now(),
            triggered_by="cron"
        ))

        # Phase 1: Daily Price Collection
        batch_run_tracker.start_phase("prices", "Daily Price Collection", len(symbols), "symbols")
        # ... processing ...
        batch_run_tracker.complete_phase("prices", success=True)

        # Continue for all 6 phases...
        batch_run_tracker.complete(success=True)
```

### 11.2 Onboarding Simplification

The V2 plan (Part 10.3.2) shows simplified onboarding status:

```python
@router.get("/status/{portfolio_id}")
async def get_onboarding_status_v2(...):
    pending = await get_pending_symbols_for_portfolio(db, portfolio_id)

    if not pending:
        return OnboardingStatusResponseV2(
            status="ready",
            analytics_available=True,
            message="Your portfolio analytics are ready!"
        )

    return OnboardingStatusResponseV2(
        status="pending",
        pending_symbols=pending,
        estimated_seconds_remaining=len(pending) * 30,
        message=f"Loading data for {len(pending)} new symbol(s)..."
    )
```

### 11.3 Admin Endpoint Preservation

Keep existing admin batch functionality:

```python
# Still works in V2:
POST /api/v1/admin/batch/run
# Uses batch_orchestrator for force-recalculation of specific portfolios

# New in V2:
POST /api/v1/admin/symbol-batch/run
# Uses symbol_batch_runner for manual symbol batch trigger
```

---

## 12. Documentation References

| Document | Location | Purpose |
|----------|----------|---------|
| Architecture V2 Plan | `PlanningDocs/ARCHITECTURE_V2_IMPLEMENTATION_PLAN.md` (BatchProcessUpdate branch) | Full implementation plan |
| Batch Status UI Design | `backend/_docs/TESTSCOTTY_BATCH_STATUS_UI.md` | Phase 7.x design decisions |
| Progress Log | `progress.md` | Implementation history |
| Backend CLAUDE.md | `backend/CLAUDE.md` | Backend development guide |
| Frontend CLAUDE.md | `frontend/CLAUDE.md` | Frontend development guide |

---

## 13. Contact Points

If questions arise during V2 implementation:

1. **Phase 7.x tracking**: See `batch_run_tracker.py` and `TESTSCOTTY_BATCH_STATUS_UI.md`
2. **Onboarding UI**: See `OnboardingProgress.tsx` and `useOnboardingStatus.ts`
3. **Current batch phases**: See `batch_orchestrator.py` lines 200-400
4. **API contracts**: See `onboarding_status.py` response models

---

## Appendix A: Critical Constants (batch_run_tracker.py)

```python
# Maximum activity log entries for UI (prevents memory growth)
MAX_ACTIVITY_LOG_ENTRIES = 50

# Maximum full log entries for download
MAX_FULL_LOG_ENTRIES = 5000

# Completed run status retention (2 hours)
COMPLETED_RUN_TTL_SECONDS = 7200

# Logger prefixes captured for activity log
CAPTURED_LOGGER_PREFIXES = (
    'app.batch',
    'app.calculations',
    'app.services.market_data',
    'app.services.company_profile',
)

# Fixed phase ordering for consistent UI display
PHASE_ORDER = [
    'phase_1',      # Market Data Collection
    'phase_1_5',    # Factor Analysis
    'phase_1_75',   # Symbol Metrics
    'phase_0',      # Company Profile Sync (final date only)
    'phase_2',      # Fundamental Data Collection (final date only)
    'phase_3',      # P&L Calculation & Snapshots
    'phase_4',      # Position Market Value Updates
    'phase_5',      # Sector Tag Restoration (final date only)
    'phase_6',      # Risk Analytics
]
```

---

## Appendix A9: Historical Date Logic Fix (Phase 7.4.1)

**Problem**: Onboarding batch processes dates from portfolio entry_date to today. If all dates are historical, phases 0, 2, 5 were skipped entirely.

**Fix in batch_orchestrator.py**:
```python
# OLD (broken):
is_historical = calculation_date < date.today()

# NEW (fixed):
is_final_date = (i == len(missing_dates))
is_historical = calculation_date < date.today() and not is_final_date
```

This ensures phases 0, 2, 5 run on the **final date** of any backfill batch.

---

## Appendix A10: Frontend Terminal State Handling

The unified `OnboardingProgress.tsx` handles four states:

```typescript
// State-specific configuration
function getUIConfig(uiState: UIState, portfolioName: string) {
  switch (uiState) {
    case 'completed':
      return {
        icon: CheckCircle,
        iconColor: 'text-green-600',
        gradient: 'from-green-50 to-emerald-50',
        title: 'Portfolio Setup Complete!',
        subtitle: `Your portfolio "${portfolioName}" is ready.`,
      }
    case 'partial':
      return {
        icon: AlertTriangle,
        iconColor: 'text-yellow-600',
        gradient: 'from-yellow-50 to-amber-50',
        title: 'Portfolio Setup Completed with Warnings',
        subtitle: 'Your portfolio is ready, but some data may be incomplete.',
      }
    case 'failed':
      return {
        icon: XCircle,
        iconColor: 'text-red-600',
        gradient: 'from-red-50 to-rose-50',
        title: 'Setup Interrupted',
        subtitle: 'We encountered an issue. Some features may have limited data.',
      }
    default: // running
      return {
        icon: Rocket,
        iconColor: 'text-blue-600',
        gradient: 'from-blue-50 to-indigo-50',
        title: 'Setting Up Your Portfolio',
        subtitle: 'Analyzing your portfolio in 9 processing phases.',
      }
  }
}
```

---

## Appendix A11: Polling Behavior

**useOnboardingStatus.ts**:
```typescript
// Terminal states stop polling
if (response.status === 'completed' ||
    response.status === 'partial' ||
    response.status === 'failed') {
  clearInterval(pollIntervalRef.current)
}

// Grace period for "not_found" status
const UNAVAILABLE_GRACE_PERIOD_MS = 10000  // 10 seconds
const MIN_NOT_FOUND_COUNT = 5  // 5 consecutive not_found responses
```

---

## Appendix A12: Activity Log Handler

**BatchActivityLogHandler** captures logs from calculation engines:

```python
class BatchActivityLogHandler(logging.Handler):
    """Forwards calculation engine logs to activity log."""

    def attach(self) -> None:
        """Attach to root logger to capture all relevant logs."""
        # Prevents duplicate handlers from leaked previous runs
        existing = [h for h in logging.root.handlers
                   if isinstance(h, BatchActivityLogHandler)]
        for h in existing:
            logging.root.removeHandler(h)
        logging.root.addHandler(self)
        self._attached = True

    def detach(self) -> None:
        """Detach from root logger."""
        if self._attached:
            logging.root.removeHandler(self)
            self._attached = False
```

---

*End of Handoff Document*
