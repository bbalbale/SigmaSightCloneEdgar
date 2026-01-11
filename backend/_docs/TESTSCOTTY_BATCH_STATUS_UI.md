# Batch Status UI - Design Document

**Document**: TESTSCOTTY_BATCH_STATUS_UI.md
**Created**: January 9, 2026
**Updated**: January 9, 2026 - All design decisions finalized
**Status**: Ready for Implementation
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
└─────────────────────────────────────────────────────────────────────┘
```

> **Note**: Download Log button intentionally NOT shown on progress screen.
> It only appears on completion and error screens.

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

### 4.4 Status Unavailable Screen (not_found mid-run)

When the status endpoint returns `not_found` during polling (server restart, network issue, etc.):

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   ⚠️ Status Unavailable                                             │
│                                                                     │
│   Unable to fetch status updates.                                   │
│   Your portfolio setup is still running in the background.          │
│                                                                     │
│   ══════════════════════════════════════════════════════════════    │
│                                                                     │
│              [ 🔄 Refresh Status ]    [ View Portfolio → ]          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Show after 3 consecutive `not_found` responses
- "Refresh Status" re-polls the endpoint
- "View Portfolio" navigates to portfolio dashboard to check if setup completed

### 4.5 Activity Log Filtering

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

## 9. Design Decisions (Resolved 2026-01-09)

All open questions have been resolved. Below are the finalized design decisions.

### 9.1 UI/UX Decisions

| Decision | Answer | Rationale |
|----------|--------|-----------|
| **Phase display** | Show all 9 phases | Granular progress visibility |
| **Activity log visibility** | Always visible | No toggle needed, users want to see activity |
| **Download log button on progress screen** | No | Only show on completion/error screens |
| **Page route** | `/onboarding/progress?portfolioId=xxx` | Query param approach |
| **Design system** | Use existing shadcn/ui + Tailwind | Consistency with rest of app |
| **Flow after upload** | Redirect to progress page | Separate from upload page |

### 9.2 Backend/Data Decisions

| Decision | Answer | Rationale |
|----------|--------|-----------|
| **Log persistence** | Hybrid (D+): In-memory during run, persist to DB after each phase | Balance of performance and durability |
| **Log retention** | Persisted in database | Survives restarts, queryable for support |
| **Authorization** | User + Admin override | Admins can view any user's status for support |
| **Build log download endpoint** | Yes, build now | Full feature ready at launch |

### 9.3 Retry & Error Handling

| Decision | Answer | Rationale |
|----------|--------|-----------|
| **Retry behavior** | Fresh run, keep previous attempt logs | New `attempt_number`, previous logs retained in DB for debugging |
| **Activity log filtering** | Follow doc spec: every 5th date + milestones (1, 50, 100, 150, 200, 250, last) | Balances visibility and noise |
| **`not_found` mid-run UX** | Show message + both options: [Refresh] [Check Portfolio] | Gives user choice when status unavailable |

### 9.4 Database Schema for Log Persistence

New table: `onboarding_logs`
```sql
CREATE TABLE onboarding_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    phase_id VARCHAR(20) NOT NULL,  -- "phase_1", "phase_1.5", etc.
    logs_json JSONB NOT NULL,       -- Array of log entries for this phase
    final_status VARCHAR(20),       -- "completed", "failed", NULL if in progress
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_onboarding_logs_portfolio_id ON onboarding_logs(portfolio_id);
CREATE INDEX ix_onboarding_logs_portfolio_attempt ON onboarding_logs(portfolio_id, attempt_number);
```

### 9.5 Additional UI Implementation Details (Resolved 2026-01-09)

| Decision | Answer | Rationale |
|----------|--------|-----------|
| **Phase 6 progress unit** | No progress bar, just spinner icon | No granular progress count available |
| **Elapsed time during running** | Yes, show for all phases | Gives user feedback something is happening |
| **Phase 1.5/1.75 display** | Show as separate phases | Aligns with backend reporting |
| **Activity log auto-scroll** | Smart scroll - auto only when at bottom, pause if user scrolls up | Best UX for reading earlier logs |
| **Timestamps** | UTC everywhere (UI and download) | Consistent format |
| **Polling control** | No UI control - automatic start/stop | Simpler UX |
| **Warning phase status** | Map from activity log - show ⚠️ if phase has warning-level entries | Minimal backend change |
| **Unavailable symbols on summary** | Show full list in expandable section | More visibility without downloading log |
| **Download button on running screen** | No (already decided) | Only on completion/error screens |
| **Progress header line** | Derive from backend response, fallback to generic message if unavailable | Accurate when possible, graceful degradation |

### 9.6 Concurrency Limitation (Known)

**Current architecture supports only ONE batch at a time.**

- `batch_run_tracker` has single `_current` field
- If 10 users onboard simultaneously, only the last one has status visibility
- This is a known limitation for MVP
- Future enhancement: Queue-based or per-portfolio tracking

---

## 10. References

- Phase 7 design in `TESTSCOTTY_PROGRESS.md`
- Phase 7.1 UX design in `TESTSCOTTY_PROGRESS.md`
- Existing endpoint: `backend/app/api/v1/onboarding_status.py`
- Batch tracker: `backend/app/batch/batch_run_tracker.py`
- Batch orchestrator: `backend/app/batch/batch_orchestrator.py`

---

## 11. Phase 7.4: Expose All 9 Processing Phases

**Created**: 2026-01-11
**Status**: Planned

### 11.1 Problem Statement

The current implementation only tracks 4 of the 9 batch processing phases via `start_phase()`/`complete_phase()`:
- `phase_1` - Market Data Collection ✅ Tracked
- `phase_1_5` - Factor Analysis ✅ Tracked
- `phase_1_75` - Symbol Metrics ✅ Tracked
- `phase_2_6` - Bundled (P&L + Snapshots + Market Values + Tags + Risk) ✅ Tracked

The frontend currently shows "Analyzing your portfolio with 1 processing phases" because `phases_total` is dynamically derived from registered phases.

### 11.2 Target State

Expose all 9 distinct processing phases with user-friendly names:

| Phase ID | Phase Name | Unit | Notes |
|----------|------------|------|-------|
| `phase_0` | Company Profile Sync | symbols | Sync company profiles for all symbols |
| `phase_1` | Market Data Collection | symbols | Fetch 1-year historical prices |
| `phase_1_5` | Factor Analysis | symbols | Calculate factor exposures |
| `phase_1_75` | Symbol Metrics | symbols | Calculate betas, volatility |
| `phase_2` | Fundamental Data Collection | symbols | Fetch fundamental data |
| `phase_3` | P&L Calculation & Snapshots | dates | Calculate P&L, create snapshots |
| `phase_4` | Position Market Value Updates | positions | Update current market values |
| `phase_5` | Sector Tag Restoration | positions | Restore sector tags |
| `phase_6` | Risk Analytics | items | Final risk calculations |

### 11.3 Backend Changes

**File**: `backend/app/batch/batch_orchestrator.py`

Add `start_phase()`/`complete_phase()` calls for each phase:

```python
# Phase 0: Company Profile Sync
batch_run_tracker.start_phase("phase_0", "Company Profile Sync", total=len(symbols), unit="symbols")
# ... existing sync logic ...
batch_run_tracker.complete_phase("phase_0", success=True, summary=f"Synced {count} profiles")

# Phase 2: Fundamental Data Collection (currently not tracked)
batch_run_tracker.start_phase("phase_2", "Fundamental Data Collection", total=len(symbols), unit="symbols")
# ... existing logic ...
batch_run_tracker.complete_phase("phase_2", success=True, summary=f"Collected {count} fundamentals")

# Phase 3: P&L Calculation & Snapshots (currently bundled in phase_2_6)
batch_run_tracker.start_phase("phase_3", "P&L Calculation & Snapshots", total=len(dates), unit="dates")
# ... existing logic ...
batch_run_tracker.complete_phase("phase_3", success=True, summary=f"Created {count} snapshots")

# Phase 4: Position Market Value Updates (currently bundled in phase_2_6)
batch_run_tracker.start_phase("phase_4", "Position Market Value Updates", total=len(positions), unit="positions")
# ... existing logic ...
batch_run_tracker.complete_phase("phase_4", success=True, summary=f"Updated {count} positions")

# Phase 5: Sector Tag Restoration (currently bundled in phase_2_6)
batch_run_tracker.start_phase("phase_5", "Sector Tag Restoration", total=len(positions), unit="positions")
# ... existing logic ...
batch_run_tracker.complete_phase("phase_5", success=True, summary=f"Restored {count} tags")

# Phase 6: Risk Analytics (currently bundled in phase_2_6)
batch_run_tracker.start_phase("phase_6", "Risk Analytics", total=0, unit="items")
# ... existing logic ...
batch_run_tracker.complete_phase("phase_6", success=True, summary="Risk analytics complete")
```

### 11.4 Frontend UI Changes

**File**: `frontend/src/components/onboarding/OnboardingProgress.tsx`

1. **Change header text** from dynamic to static:
   ```
   Before: "Analyzing your portfolio with {phases_total} processing phases."
   After:  "Analyzing your portfolio in 9 processing phases."
   ```

2. **Remove "This typically takes..." sentence** entirely

3. **Add phase list** below the header (visible during processing):
   ```
   1. Company Profile Sync
   2. Market Data Collection
   3. Factor Analysis
   4. Symbol Metrics
   5. Fundamental Data Collection
   6. P&L Calculation & Snapshots
   7. Position Market Value Updates
   8. Sector Tag Restoration
   9. Risk Analytics
   ```

4. **Phase list styling**:
   - Show checkmark ✓ for completed phases
   - Show spinner for running phase
   - Show dimmed/pending for future phases
   - Show X for failed phases

### 11.5 Implementation Order

1. **Backend first**: Add `start_phase()`/`complete_phase()` calls to batch_orchestrator.py
2. **Test backend**: Verify all 9 phases appear in `/api/v1/onboarding/status/{portfolio_id}` response
3. **Frontend second**: Update OnboardingProgress.tsx with static text and phase list
4. **E2E test**: Run full onboarding flow and verify all phases display correctly

### 11.6 Acceptance Criteria

- [ ] Backend: All 9 phases tracked via `batch_run_tracker`
- [ ] API: `/status/{portfolio_id}` returns `phases_total: 9`
- [ ] Frontend: Header shows "Analyzing your portfolio in 9 processing phases."
- [ ] Frontend: "This typically takes..." sentence removed
- [ ] Frontend: All 9 phases listed with appropriate status indicators
- [ ] Frontend: Phase status updates in real-time during polling

---

## 12. Phase 7.5: Market Data Collection Optimization

**Created**: 2026-01-11
**Status**: Planned
**Priority**: High (blocking onboarding performance)

### 12.1 Problem Statement

Current market data collection runs **date-by-date**, causing severe performance issues:

**Test Case**: `Tech-Focused-Professional.csv`
- 17 positions + 17 factor ETFs = 33 symbols
- Entry dates: June 30, 2025
- Processing dates: June 30, 2025 → Jan 11, 2026 = ~135 trading days

**Current Behavior**:
```
For EACH of 135 dates:
  1. Query DB for cache status (2 queries)
  2. Find 4 symbols "need data"
  3. YFinance API call → 4 succeed, SQ fails
  4. YahooQuery API call for SQ → fails
  5. Polygon API call for SQ → 10s rate limit wait → fails
  6. FMP API call for SQ → fails
  7. Store ~1004 records
  8. Repeat for next date...

Result: 135 dates × ~11 seconds = ~25 minutes for Phase 1 alone
```

**Root Causes**:
1. **Redundant API calls**: Same symbols fetched on each date iteration
2. **No failure memory**: SQ fails 135 times instead of once
3. **Overlapping date ranges**: 365-day lookback fetched repeatedly with 99% overlap
4. **Rate limit amplification**: Each SQ failure triggers 10s Polygon wait

### 12.2 Solution: Fetch Once, Verify Per-Date

Restructure Phase 1 into two sub-phases:

**Phase 1A: Bulk Historical Fetch (once)**
- Fetch ALL market data for the full date range in one pass
- Track which symbols are unavailable (delisted, etc.)
- One attempt per symbol, not 135

**Phase 1B: Per-Date Verification (DB only)**
- Quick cache verification for each calculation date
- No API calls - data already fetched
- Sub-second per date

### 12.3 Architecture Comparison

**Current (Inefficient)**:
```
┌────────────────────────────────────────────────────────┐
│ For EACH of 135 dates:                                 │
│   → Cache check queries (2 DB calls)                   │
│   → API calls for missing symbols (4 providers)        │
│   → Store fetched data                                 │
│   → 10s rate limit wait if any symbol fails            │
└────────────────────────────────────────────────────────┘
Time: ~25 minutes
API calls: Up to 540 (135 × 4 providers)
```

**Proposed (Optimized)**:
```
┌────────────────────────────────────────────────────────┐
│ Phase 1A: Bulk Fetch (ONCE)                            │
│   → Get per-symbol coverage from DB                    │
│   → Identify gaps per symbol                           │
│   → Single bulk fetch per symbol for missing ranges    │
│   → Track unavailable symbols (SQ, etc.)               │
└────────────────────────────────────────────────────────┘
Time: ~30-60 seconds

┌────────────────────────────────────────────────────────┐
│ Phase 1B: Verify Per-Date (DB only)                    │
│   → Quick count query per date                         │
│   → No API calls                                       │
│   → Exclude known unavailable symbols                  │
└────────────────────────────────────────────────────────┘
Time: ~15 seconds (135 × 0.1s)

Total: ~1-2 minutes (vs ~25 minutes)
```

### 12.4 Implementation Details

#### 12.4.1 New Method: `collect_market_data_bulk()`

**File**: `backend/app/batch/market_data_collector.py`

```python
async def collect_market_data_bulk(
    self,
    symbols: Set[str],
    start_date: date,
    end_date: date,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Phase 1A: Fetch ALL market data for date range in one pass.

    Args:
        symbols: All symbols needed (positions + factor ETFs)
        start_date: Earliest date needed (from position entry_dates)
        end_date: Latest date needed (today or target date)
        db: Database session

    Returns:
        Summary with cached/fetched/unavailable counts
    """
    logger.info(f"Phase 1A: Bulk market data fetch for {len(symbols)} symbols")
    logger.info(f"  Date range: {start_date} to {end_date}")

    # Step 1: Get per-symbol coverage
    symbol_coverage = await self._get_per_symbol_date_coverage(
        db, symbols, start_date, end_date
    )

    # Step 2: Categorize symbols
    fully_cached = set()
    needs_gap_fill = {}  # symbol -> list of (gap_start, gap_end)
    needs_full_fetch = set()

    trading_days_needed = self._count_trading_days(start_date, end_date)

    for symbol in symbols:
        coverage = symbol_coverage.get(symbol, {'count': 0, 'min_date': None, 'max_date': None})

        if coverage['count'] >= trading_days_needed * 0.95:  # 95% coverage
            fully_cached.add(symbol)
        elif coverage['count'] >= 50:
            # Has partial data - identify gaps
            gaps = await self._identify_date_gaps(
                db, symbol, start_date, end_date, coverage
            )
            if gaps:
                needs_gap_fill[symbol] = gaps
            else:
                fully_cached.add(symbol)
        else:
            needs_full_fetch.add(symbol)

    logger.info(f"  Fully cached: {len(fully_cached)} symbols")
    logger.info(f"  Need gap fill: {len(needs_gap_fill)} symbols")
    logger.info(f"  Need full fetch: {len(needs_full_fetch)} symbols")

    # Step 3: Fetch data for symbols that need it
    unavailable_symbols = set()
    fetched_count = 0

    # Full fetch for symbols with no/minimal data
    if needs_full_fetch:
        logger.info(f"  Fetching full history for {len(needs_full_fetch)} symbols...")
        fetched, failed = await self._fetch_symbols_bulk(
            list(needs_full_fetch), start_date, end_date, db
        )
        fetched_count += fetched
        unavailable_symbols.update(failed)

    # Gap fill for symbols with partial data
    if needs_gap_fill:
        logger.info(f"  Filling gaps for {len(needs_gap_fill)} symbols...")
        for symbol, gaps in needs_gap_fill.items():
            for gap_start, gap_end in gaps:
                fetched, failed = await self._fetch_symbols_bulk(
                    [symbol], gap_start, gap_end, db
                )
                fetched_count += fetched
                if failed:
                    unavailable_symbols.add(symbol)
                    break  # Don't try other gaps if symbol fails

    # Step 4: Store unavailable symbols for Phase 1B
    self._unavailable_symbols = unavailable_symbols

    logger.info(f"Phase 1A complete:")
    logger.info(f"  Symbols cached: {len(fully_cached)}")
    logger.info(f"  Symbols fetched: {fetched_count}")
    logger.info(f"  Symbols unavailable: {len(unavailable_symbols)} - {list(unavailable_symbols)}")

    return {
        'fully_cached': len(fully_cached),
        'fetched': fetched_count,
        'unavailable': list(unavailable_symbols),
        'unavailable_symbols': unavailable_symbols,  # Set for Phase 1B
    }
```

#### 12.4.2 New Method: `verify_date_coverage()`

```python
async def verify_date_coverage(
    self,
    calc_date: date,
    symbols: Set[str],
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Phase 1B: Quick DB verification - no API calls.

    Args:
        calc_date: Date to verify
        symbols: All symbols (will exclude unavailable)
        db: Database session

    Returns:
        Coverage report for this date
    """
    # Exclude known unavailable symbols
    check_symbols = symbols - getattr(self, '_unavailable_symbols', set())

    if not check_symbols:
        return {
            'date': calc_date,
            'coverage_pct': 100.0,
            'symbols_with_data': 0,
            'symbols_checked': 0,
        }

    # Single efficient query
    count_query = select(func.count(func.distinct(MarketDataCache.symbol))).where(
        and_(
            MarketDataCache.symbol.in_(list(check_symbols)),
            MarketDataCache.date == calc_date,
            MarketDataCache.close > 0
        )
    )

    result = await db.execute(count_query)
    symbols_with_data = result.scalar() or 0

    coverage_pct = (symbols_with_data / len(check_symbols) * 100) if check_symbols else 100.0

    return {
        'date': calc_date,
        'coverage_pct': coverage_pct,
        'symbols_with_data': symbols_with_data,
        'symbols_checked': len(check_symbols),
    }
```

#### 12.4.3 Updated Orchestrator Flow

**File**: `backend/app/batch/batch_orchestrator.py`

```python
# In _execute_batch_phases(), replace Phase 1 loop with:

# Phase 1A: Bulk fetch (ONCE)
logger.info(f"Phase 1A: Bulk market data collection")
batch_run_tracker.start_phase("phase_1a", "Market Data Collection", total=len(symbols), unit="symbols")

bulk_result = await market_data_collector.collect_market_data_bulk(
    symbols=all_symbols,
    start_date=missing_dates[0],
    end_date=missing_dates[-1],
    db=db,
)

batch_run_tracker.complete_phase(
    "phase_1a",
    success=True,
    summary=f"Fetched {bulk_result['fetched']} symbols, {len(bulk_result['unavailable'])} unavailable"
)

# Phase 1B: Verify per-date (DB only)
logger.info(f"Phase 1B: Verifying {len(missing_dates)} dates")
batch_run_tracker.start_phase("phase_1b", "Data Verification", total=len(missing_dates), unit="dates")

for i, calc_date in enumerate(missing_dates, 1):
    batch_run_tracker.update_phase_progress("phase_1b", i)

    coverage = await market_data_collector.verify_date_coverage(
        calc_date=calc_date,
        symbols=all_symbols,
        db=db,
    )

    if coverage['coverage_pct'] < 80:
        logger.warning(f"  {calc_date}: Low coverage {coverage['coverage_pct']:.1f}%")

batch_run_tracker.complete_phase("phase_1b", success=True, summary=f"Verified {len(missing_dates)} dates")
```

### 12.5 Helper Methods

```python
async def _get_per_symbol_date_coverage(
    self,
    db: AsyncSession,
    symbols: Set[str],
    start_date: date,
    end_date: date,
) -> Dict[str, Dict]:
    """Get date coverage statistics per symbol."""
    query = select(
        MarketDataCache.symbol,
        func.count(MarketDataCache.id).label('count'),
        func.min(MarketDataCache.date).label('min_date'),
        func.max(MarketDataCache.date).label('max_date'),
    ).where(
        and_(
            MarketDataCache.symbol.in_(list(symbols)),
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date,
            MarketDataCache.close > 0
        )
    ).group_by(MarketDataCache.symbol)

    result = await db.execute(query)

    return {
        row.symbol: {
            'count': row.count,
            'min_date': row.min_date,
            'max_date': row.max_date,
        }
        for row in result.fetchall()
    }


async def _fetch_symbols_bulk(
    self,
    symbols: List[str],
    start_date: date,
    end_date: date,
    db: AsyncSession,
) -> Tuple[int, Set[str]]:
    """
    Fetch data for symbols using provider priority chain.
    Returns (fetched_count, failed_symbols).
    """
    fetched_data, provider_counts = await self._fetch_with_priority_chain(
        symbols, start_date, end_date
    )

    if fetched_data:
        await self._store_in_cache(db, fetched_data)

    failed_symbols = set(symbols) - set(fetched_data.keys())

    return len(fetched_data), failed_symbols
```

### 12.6 Performance Impact

| Metric | Current | Optimized | Improvement |
|--------|---------|-----------|-------------|
| **Phase 1 time** | ~25 min | ~1-2 min | **12-25x faster** |
| **API calls** | ~540 | ~4-10 | **50-100x fewer** |
| **DB queries** | ~270 | ~140 | **2x fewer** |
| **Rate limit waits** | ~22 min | ~10 sec | **130x less** |
| **Total onboarding** | ~30-40 min | ~10-15 min | **2-3x faster** |

### 12.7 Implementation Order

1. **Add `_unavailable_symbols` instance variable** to `MarketDataCollector`
2. **Implement `_get_per_symbol_date_coverage()`** helper
3. **Implement `collect_market_data_bulk()`** (Phase 1A)
4. **Implement `verify_date_coverage()`** (Phase 1B)
5. **Update `batch_orchestrator._execute_batch_phases()`** to use new flow
6. **Update phase tracking** for 1A/1B split
7. **Test with Tech-Focused-Professional.csv** (June 2025 dates)
8. **Test with quick CSV** (Jan 2026 dates) for comparison

### 12.8 Acceptance Criteria

- [ ] Phase 1A fetches each symbol at most once per batch run
- [ ] Failed symbols (SQ, delisted, etc.) tracked and excluded from retries
- [ ] Phase 1B does NO API calls, only DB verification
- [ ] Total Phase 1 time < 5 minutes for 6-month backfill
- [ ] Total Phase 1 time < 1 minute for 2-week backfill
- [ ] Activity log shows clear 1A/1B separation
- [ ] Unavailable symbols logged once, not 135 times

### 12.9 Rollback Plan

If issues arise, the optimization can be disabled by:
1. Setting `USE_BULK_FETCH = False` in market_data_collector.py
2. Falling back to current date-by-date behavior
3. No database schema changes required
