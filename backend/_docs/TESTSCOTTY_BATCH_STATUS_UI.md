# Batch Status UI - Design Document

**Document**: TESTSCOTTY_BATCH_STATUS_UI.md
**Created**: January 9, 2026
**Status**: Planning
**Related**: Phase 7, Phase 7.1 in TESTSCOTTY_PROGRESS.md

---

## 1. Overview

### Purpose
Provide real-time, transparent batch processing status during the portfolio onboarding flow. Users should see exactly what's happening during the ~15 minute setup process instead of a fake progress animation.

### Goals
1. Replace fake animation with real-time status updates
2. Show phase-by-phase progress with completion percentages
3. Display activity log with per-symbol/per-date granularity
4. Provide downloadable full log file for debugging/support
5. Handle errors gracefully with actionable messaging

### Scope
- **In Scope**: Onboarding flow batch processing status UI
- **Out of Scope**: Admin batch monitoring, cron job status, other pages

---

## 2. Existing Backend Infrastructure

### 2.1 Status API Endpoint (Implemented)

**Endpoint**: `GET /api/v1/onboarding/status/{portfolio_id}`

**File**: `backend/app/api/v1/onboarding_status.py`

**Authentication**: Clerk JWT (regular user, not admin-only)

**Response Schema**:
```typescript
interface OnboardingStatusResponse {
  portfolio_id: string;
  status: "running" | "completed" | "failed" | "not_found";
  started_at: string | null;  // ISO timestamp
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
    unit: string;  // "symbols", "dates", "positions"
  } | null;

  activity_log: Array<{
    timestamp: string;  // ISO timestamp
    message: string;
    level: "info" | "warning" | "error";
  }>;

  phases: Array<{
    phase_id: string;
    phase_name: string;
    status: "pending" | "running" | "completed" | "failed";
    current: number;
    total: number;
    unit: string;
    duration_seconds: number | null;
  }> | null;
}
```

**Polling Recommendation**: Every 2 seconds during active processing.

---

## 3. Batch Processing Phases

### 3.1 Complete Phase List

| Phase ID | User-Facing Name | Description | Progress Unit | Typical Duration |
|----------|------------------|-------------|---------------|------------------|
| phase_1 | Market Data Collection | Fetching 1 year of historical prices | symbols | 30-60s |
| phase_1.5 | Factor Analysis | Calculating Ridge/Spread factor exposures | symbols | 10-20s |
| phase_1.75 | Symbol Metrics | Computing returns and volatility metrics | symbols | 5-10s |
| phase_2 | Portfolio Snapshots | Creating daily portfolio valuations | dates | 5-8 min |
| phase_2.5 | Position Values | Updating current market values | positions | 10-30s |
| phase_3 | Position Betas | Calculating market and factor betas | positions | 30-60s |
| phase_4 | Factor Exposures | Computing portfolio factor exposures | positions | 20-40s |
| phase_5 | Volatility Analysis | Analyzing historical and implied volatility | positions | 20-40s |
| phase_6 | Correlations | Building position correlation matrix | N/A | 30-60s |

### 3.2 Phase Status States

| Status | Icon | Color | Description |
|--------|------|-------|-------------|
| pending | ⏳ | Gray (#9CA3AF) | Phase not started yet |
| running | 🔄 | Blue (#3B82F6) | Currently executing (with spinner animation) |
| completed | ✅ | Green (#10B981) | Finished successfully |
| warning | ⚠️ | Yellow (#F59E0B) | Completed with non-critical issues |
| failed | ❌ | Red (#EF4444) | Phase failed (rare - usually recoverable) |

### 3.3 User-Friendly Messages Per Phase

| Phase | Running Message | Completed Summary |
|-------|-----------------|-------------------|
| phase_1 | "Fetching historical prices..." | "{n}/{total} symbols ({coverage}% coverage)" |
| phase_1.5 | "Calculating factor exposures..." | "Factor analysis complete" |
| phase_1.75 | "Computing symbol metrics..." | "Metrics computed" |
| phase_2 | "Creating daily snapshots..." | "{n} trading days processed" |
| phase_2.5 | "Updating position values..." | "Values updated" |
| phase_3 | "Calculating position betas..." | "Betas calculated" |
| phase_4 | "Computing factor exposures..." | "Exposures computed" |
| phase_5 | "Analyzing volatility..." | "Volatility analyzed" |
| phase_6 | "Building correlation matrix..." | "Correlations complete" |

---

## 4. Frontend UX Design

### 4.1 Main Status Screen Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   🚀 Setting Up Your Portfolio                                      │
│                                                                     │
│   Analyzing 254 trading days for 20 positions.                      │
│   This typically takes 15-20 minutes.                               │
│                                                                     │
│   ══════════════════════════════════════════════════════════════    │
│                                                                     │
│   PHASE PROGRESS                                                    │
│                                                                     │
│   ✅ Phase 1: Market Data Collection                        45s     │
│   ✅ Phase 2: Factor Analysis                               12s     │
│   🔄 Phase 3: Portfolio Snapshots                        3m 24s     │
│      ████████████████░░░░░░░░░░░░░░░░░░  142/254 dates              │
│   ⏳ Phase 4: Position Betas                                        │
│   ⏳ Phase 5: Volatility Analysis                                   │
│   ⏳ Phase 6: Correlations                                          │
│                                                                     │
│   ══════════════════════════════════════════════════════════════    │
│                                                                     │
│   📋 ACTIVITY LOG                                                   │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │ 12:04:05  Fetched AAPL: 254 days of history                 │   │
│   │ 12:04:06  Fetched MSFT: 254 days of history                 │   │
│   │ 12:04:07  ⚠️ HZNP: Symbol unavailable (delisted)            │   │
│   │ 12:04:08  Phase 1 complete: 18/20 symbols (90% coverage)    │   │
│   │ 12:04:20  Phase 2 complete: Factor analysis done            │   │
│   │ 12:04:21  Creating snapshot for 2024-01-02... (1/254)       │   │
│   │ 12:05:15  Creating snapshot for 2024-03-15... (50/254)      │   │
│   │ 12:06:42  Creating snapshot for 2024-06-15... (100/254)     │   │
│   │ 12:07:28  Creating snapshot for 2024-08-20... (142/254)     │   │
│   │                                           ▼ auto-scrolling  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│   ══════════════════════════════════════════════════════════════    │
│                                                                     │
│   ⏱️  Elapsed: 4m 21s                     📊 Overall: 45% complete  │
│                                                                     │
│                        [ 📥 Download Full Log ]                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Completion Screen

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   ✅ Portfolio Setup Complete!                                      │
│                                                                     │
│   Your portfolio "Growth Portfolio" is ready.                       │
│                                                                     │
│   ══════════════════════════════════════════════════════════════    │
│                                                                     │
│   📊 SUMMARY                                                        │
│                                                                     │
│   • 18 positions analyzed (2 unavailable symbols)                   │
│   • 254 trading days of history                                     │
│   • Risk metrics, factor exposures, and correlations ready          │
│                                                                     │
│   ⏱️  Total time: 14m 32s                                           │
│                                                                     │
│   ══════════════════════════════════════════════════════════════    │
│                                                                     │
│            [ 📥 Download Log ]    [ View Portfolio Dashboard → ]    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Error/Failure Screen

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   ⚠️ Setup Interrupted                                              │
│                                                                     │
│   We encountered an issue while setting up your portfolio.          │
│   Some features may have limited data.                              │
│                                                                     │
│   ══════════════════════════════════════════════════════════════    │
│                                                                     │
│   ✅ Completed: Phases 1-3 (Market Data, Factors, Snapshots)        │
│   ❌ Failed at: Phase 4 (Position Betas)                            │
│                                                                     │
│   Error: Database connection timeout                                │
│                                                                     │
│   Your portfolio is available with partial analytics.               │
│   Full analytics will be available after the next daily update.     │
│                                                                     │
│   ══════════════════════════════════════════════════════════════    │
│                                                                     │
│   [ 📥 Download Log ]  [ Retry Setup ]  [ View Portfolio Anyway → ] │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.4 Activity Log Filtering

**What to Show (filter IN)**:
| Entry Type | Example | When |
|------------|---------|------|
| Symbol fetch success | "Fetched AAPL: 254 days of history" | Phase 1 |
| Symbol unavailable | "⚠️ HZNP: Symbol unavailable (delisted)" | Phase 1 |
| Phase complete | "Phase 1 complete: 18/20 symbols (90%)" | End of each |
| Date milestone | "Creating snapshot for 2024-03-15... (50/254)" | Phase 2 |
| Calculation start | "Calculating betas for 18 positions..." | Phases 3-6 |
| Warnings | "⚠️ Limited data for PRIVATE positions" | Any phase |
| Errors | "❌ Failed to fetch options data" | Any phase |

**What to Hide (filter OUT)**:
- HTTP request logs
- Database session logs
- Authentication/token logs
- Duplicate consecutive messages
- Individual date processing (show every 5th + milestones: 50, 100, 150, 200, 250)

### 4.5 Component Specifications

**Phase List Item**:
```typescript
interface PhaseListItemProps {
  phaseId: string;
  phaseName: string;
  status: "pending" | "running" | "completed" | "warning" | "failed";
  current?: number;
  total?: number;
  unit?: string;
  durationSeconds?: number;
}
```

**Activity Log Entry**:
```typescript
interface ActivityLogEntryProps {
  timestamp: string;
  message: string;
  level: "info" | "warning" | "error";
}
```

**Progress Bar** (for running phase):
- Height: 8px
- Background: Gray (#E5E7EB)
- Fill: Blue (#3B82F6)
- Border radius: 4px
- Animation: Smooth transition on width change

---

## 5. Log Download Feature

### 5.1 Requirement

Add a "Download Full Log" button that exports the complete activity log as a .txt file. This is useful for:
- Debugging issues during onboarding
- Support tickets
- User peace of mind ("I can see everything that happened")

### 5.2 New API Endpoint Required

**Endpoint**: `GET /api/v1/onboarding/status/{portfolio_id}/logs`

**Authentication**: Clerk JWT (same as status endpoint)

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| format | string | "txt" | Output format: "txt" or "json" |
| include_debug | boolean | false | Include debug-level entries |

**Response** (format=txt):
```
Content-Type: text/plain
Content-Disposition: attachment; filename="portfolio_setup_log_<portfolio_id>_<timestamp>.txt"

================================================================================
SIGMASIGHT PORTFOLIO SETUP LOG
================================================================================
Portfolio ID: 52110fe1-ca52-42ff-abaa-c0c90e8e21be
Portfolio Name: Growth Portfolio
Started: 2026-01-09 12:00:00 UTC
Completed: 2026-01-09 12:14:32 UTC
Total Duration: 14m 32s
Final Status: completed

================================================================================
SUMMARY
================================================================================
Positions Analyzed: 18/20 (2 unavailable)
Trading Days Processed: 254
Phases Completed: 6/6

================================================================================
PHASE DETAILS
================================================================================
Phase 1 - Market Data Collection
  Status: completed
  Duration: 45s
  Symbols: 18/20 (90% coverage)

Phase 2 - Factor Analysis
  Status: completed
  Duration: 12s

Phase 3 - Portfolio Snapshots
  Status: completed
  Duration: 8m 15s
  Dates: 254/254

... (continued for all phases)

================================================================================
ACTIVITY LOG
================================================================================
2026-01-09 12:00:01 [INFO] Starting batch processing for portfolio 52110fe1...
2026-01-09 12:00:02 [INFO] Phase 1: Market Data Collection starting
2026-01-09 12:00:03 [INFO] Fetching AAPL: 254 days of history
2026-01-09 12:00:03 [INFO] Fetching MSFT: 254 days of history
2026-01-09 12:00:04 [INFO] Fetching GOOGL: 254 days of history
2026-01-09 12:00:05 [WARN] HZNP: Symbol unavailable (delisted)
2026-01-09 12:00:05 [WARN] SGEN: Symbol unavailable (delisted)
... (complete log)
2026-01-09 12:14:32 [INFO] Batch processing completed successfully

================================================================================
END OF LOG
================================================================================
```

**Response** (format=json):
```json
{
  "portfolio_id": "52110fe1-ca52-42ff-abaa-c0c90e8e21be",
  "portfolio_name": "Growth Portfolio",
  "started_at": "2026-01-09T12:00:00Z",
  "completed_at": "2026-01-09T12:14:32Z",
  "duration_seconds": 872,
  "final_status": "completed",
  "summary": {
    "positions_analyzed": 18,
    "positions_total": 20,
    "positions_unavailable": 2,
    "trading_days": 254,
    "phases_completed": 6,
    "phases_total": 6
  },
  "phases": [...],
  "activity_log": [...]
}
```

### 5.3 Backend Implementation

**File**: `backend/app/api/v1/onboarding_status.py` (extend existing)

**Changes Required**:
1. Add new route handler for `/status/{portfolio_id}/logs`
2. Extend `batch_run_tracker` to store full log history (not just last 50)
3. Add log formatting utilities for txt output
4. Return appropriate Content-Type and Content-Disposition headers

**Storage Consideration**:
- Store full logs in memory during batch run (capped at 5000 entries)
- After batch completes, optionally persist to database for later retrieval
- Clear from memory after 1 hour or when new batch starts

### 5.4 Frontend Implementation

**Download Button Component**:
```typescript
interface DownloadLogButtonProps {
  portfolioId: string;
  disabled?: boolean;  // Disabled while batch is running
  variant?: "primary" | "secondary";
}

function DownloadLogButton({ portfolioId, disabled, variant = "secondary" }: DownloadLogButtonProps) {
  const handleDownload = async () => {
    const response = await fetch(`/api/v1/onboarding/status/${portfolioId}/logs?format=txt`);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `portfolio_setup_log_${portfolioId}_${Date.now()}.txt`;
    a.click();
  };

  return (
    <Button onClick={handleDownload} disabled={disabled} variant={variant}>
      📥 Download Full Log
    </Button>
  );
}
```

---

## 6. Frontend Implementation Plan

### 6.1 New Components

| Component | Location | Description |
|-----------|----------|-------------|
| `OnboardingProgress.tsx` | `src/components/onboarding/` | Main progress container |
| `PhaseList.tsx` | `src/components/onboarding/` | Phase progress list |
| `PhaseListItem.tsx` | `src/components/onboarding/` | Single phase item |
| `ActivityLog.tsx` | `src/components/onboarding/` | Scrollable log display |
| `ActivityLogEntry.tsx` | `src/components/onboarding/` | Single log entry |
| `DownloadLogButton.tsx` | `src/components/onboarding/` | Log download button |
| `OnboardingComplete.tsx` | `src/components/onboarding/` | Completion screen |
| `OnboardingError.tsx` | `src/components/onboarding/` | Error/failure screen |

### 6.2 New Hook

```typescript
// src/hooks/useOnboardingStatus.ts

interface UseOnboardingStatusOptions {
  portfolioId: string;
  pollInterval?: number;  // Default: 2000ms
  enabled?: boolean;      // Enable/disable polling
}

interface UseOnboardingStatusReturn {
  status: OnboardingStatusResponse | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

function useOnboardingStatus(options: UseOnboardingStatusOptions): UseOnboardingStatusReturn {
  // Poll status endpoint every 2 seconds
  // Stop polling when status is "completed" or "failed"
  // Handle auth errors gracefully
}
```

### 6.3 Page Integration

**File**: `frontend/app/onboarding/progress/page.tsx`

```typescript
'use client'

import { useOnboardingStatus } from '@/hooks/useOnboardingStatus'
import { OnboardingProgress } from '@/components/onboarding/OnboardingProgress'
import { OnboardingComplete } from '@/components/onboarding/OnboardingComplete'
import { OnboardingError } from '@/components/onboarding/OnboardingError'

export default function OnboardingProgressPage() {
  const { portfolioId } = usePortfolioStore()
  const { status, isLoading, error } = useOnboardingStatus({
    portfolioId,
    pollInterval: 2000
  })

  if (status?.status === 'completed') {
    return <OnboardingComplete status={status} />
  }

  if (status?.status === 'failed') {
    return <OnboardingError status={status} />
  }

  return <OnboardingProgress status={status} isLoading={isLoading} />
}
```

---

## 7. Backend Changes Required

### 7.1 Extend batch_run_tracker.py

**Current**: Tracks basic running state and limited activity log (50 entries)

**Required Changes**:
```python
class BatchRunTracker:
    def __init__(self):
        # ... existing fields ...

        # NEW: Full log storage for download
        self._full_activity_log: List[Dict] = []  # Up to 5000 entries
        self._max_full_log_entries = 5000

    def add_activity(self, message: str, level: str = "info", phase: str = None):
        """Add activity log entry (both condensed and full)"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "level": level,
            "phase": phase
        }

        # Add to condensed log (for UI polling)
        self._activity_log.append(entry)
        if len(self._activity_log) > 50:
            self._activity_log.pop(0)

        # Add to full log (for download)
        self._full_activity_log.append(entry)
        if len(self._full_activity_log) > self._max_full_log_entries:
            self._full_activity_log.pop(0)

    def get_full_activity_log(self) -> List[Dict]:
        """Get complete activity log for download"""
        return self._full_activity_log.copy()

    def clear_logs(self):
        """Clear logs after batch completion (called after timeout)"""
        self._activity_log.clear()
        self._full_activity_log.clear()
```

### 7.2 Add Status Updates to batch_orchestrator.py

Add calls to `batch_run_tracker.add_activity()` at key points:
- Phase start/complete
- Symbol fetch success/failure
- Date processing milestones (every 5th + 50, 100, 150, 200, 250)
- Warnings and errors

### 7.3 New Endpoint for Log Download

Add to `onboarding_status.py`:
```python
@router.get("/status/{portfolio_id}/logs")
async def download_onboarding_logs(
    portfolio_id: str,
    format: str = "txt",  # "txt" or "json"
    include_debug: bool = False,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """Download complete activity log for portfolio setup."""
    # ... implementation
```

---

## 8. Implementation Checklist

### Backend Tasks
- [ ] Extend `batch_run_tracker.py` with full log storage
- [ ] Add activity logging calls to `batch_orchestrator.py` for all phases
- [ ] Implement log download endpoint in `onboarding_status.py`
- [ ] Add log formatting utilities (txt and json output)
- [ ] Test endpoint authentication and portfolio ownership

### Frontend Tasks
- [ ] Create `useOnboardingStatus` hook with polling
- [ ] Create `OnboardingProgress` component
- [ ] Create `PhaseList` and `PhaseListItem` components
- [ ] Create `ActivityLog` and `ActivityLogEntry` components
- [ ] Create `DownloadLogButton` component
- [ ] Create `OnboardingComplete` screen
- [ ] Create `OnboardingError` screen
- [ ] Integrate into onboarding flow page
- [ ] Test polling, auto-scroll, and download functionality

### Testing
- [ ] Test with real batch processing (multiple portfolios)
- [ ] Test error scenarios (batch failure, network issues)
- [ ] Test log download in all states (running, completed, failed)
- [ ] Test mobile responsiveness
- [ ] Performance test (polling doesn't cause memory leaks)

---

## 9. Open Questions

1. **Log Persistence**: Should we persist full logs to database after batch completion for later retrieval? Or only keep in memory during processing?

2. **Log Retention**: How long should logs be available for download after batch completes?

3. **Retry Behavior**: When user clicks "Retry Setup", should we clear previous logs or append to them?

4. **Admin Access**: Should admins be able to view any user's onboarding logs for support purposes?

---

## 10. References

- Phase 7 design in `TESTSCOTTY_PROGRESS.md`
- Phase 7.1 UX design in `TESTSCOTTY_PROGRESS.md`
- Existing endpoint: `backend/app/api/v1/onboarding_status.py`
- Batch tracker: `backend/app/batch/batch_run_tracker.py`
- Batch orchestrator: `backend/app/batch/batch_orchestrator.py`
