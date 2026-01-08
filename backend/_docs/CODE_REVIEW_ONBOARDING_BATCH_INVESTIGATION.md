# Code Review: Onboarding Batch Investigation (UPDATED)

**Date**: January 8, 2026
**Investigator**: Claude Opus 4.5
**Issue**: Batch processing not completing during Testscotty3 onboarding
**Status**: ROOT CAUSE IDENTIFIED - Silent batch failure + inadequate error handling

---

## Executive Summary (CORRECTED)

**PREVIOUS FINDING (INCORRECT)**: Batch not triggered because frontend doesn't call `/calculate`.

**CORRECTED FINDING**: The frontend **DOES** call the `/calculate` endpoint. The batch is triggered but **fails silently**, and the status reporting doesn't surface the failure to the frontend.

**Root Cause**: The batch fails during execution (unknown reason - likely market data or database issue), but:
1. The `batch_run_tracker.complete()` is called in a `finally` block (always runs)
2. No snapshots are created (batch failed)
3. The `/batch-status` endpoint returns `"idle"` when no snapshots exist
4. The frontend only handles `"completed"` status, so it **polls forever** without error

---

## Complete Frontend Flow (Verified)

### Step 1: Portfolio Creation
**File**: `frontend/src/hooks/usePortfolioUpload.ts` (lines 140-161)
```typescript
// PHASE 2A: CSV Upload
const uploadResponse = await onboardingService.createPortfolio(formData)
// Returns portfolio_id
```

### Step 2: Batch Trigger (CONFIRMED - IT DOES CALL THIS)
**File**: `frontend/src/hooks/usePortfolioUpload.ts` (lines 180-184)
```typescript
// PHASE 2B: Batch Processing (30-60 seconds)
setUploadState('processing')

const calcResponse = await onboardingService.triggerCalculations(uploadResponse.portfolio_id)
setBatchStatus(calcResponse.status)
```

**File**: `frontend/src/services/onboardingService.ts` (lines 103-108)
```typescript
triggerCalculations: async (portfolioId: string): Promise<TriggerCalculationsResponse> => {
  const response = await apiClient.post<TriggerCalculationsResponse>(
    `/api/v1/portfolios/${portfolioId}/calculate`  // CALLS THE ENDPOINT!
  )
  return response
}
```

### Step 3: Status Polling
**File**: `frontend/src/hooks/usePortfolioUpload.ts` (lines 187-269)
```typescript
// Start polling for batch status
pollIntervalRef.current = setInterval(async () => {
  const status = await onboardingService.getBatchStatus(
    uploadResponse.portfolio_id,
    calcResponse.batch_run_id
  )

  // Check if complete - ONLY HANDLES "completed"!
  if (status.status === 'completed') {
    // Success handling...
  }
  // NOTE: No handling for "idle" or "failed" status!
}, 3000)
```

### Step 4: "Analyzing Your Portfolio" UI
**File**: `frontend/src/components/onboarding/UploadProcessing.tsx` (line 99)
```typescript
<CardTitle>
  {uploadState === 'processing'
    ? 'Analyzing Your Portfolio...'  // THIS IS THE PAGE USER SEES
    : 'Uploading Your Portfolio...'}
</CardTitle>
```

---

## Backend Flow (Verified)

### Calculate Endpoint
**File**: `backend/app/api/v1/portfolios.py` (lines 521-617)

1. **Line 573**: Creates new `batch_run_id = str(uuid4())`
2. **Line 580**: `batch_run_tracker.start(run)` - marks batch as "running"
3. **Lines 597-601**: Adds background task:
   ```python
   background_tasks.add_task(
       batch_orchestrator.run_portfolio_onboarding_backfill,
       str(portfolio_id),
       calculation_date
   )
   ```
4. Returns `TriggerCalculationsResponse` with `batch_run_id`

### Batch Execution
**File**: `backend/app/batch/batch_orchestrator.py` (lines 442-687)

1. **Line 474**: Logs "Portfolio Onboarding Backfill: Starting"
2. **Line 544-558**: Phase 1: Market data collection for all dates
3. **Line 594-617**: Phase 1.5: Add symbols to universe
4. **Line 630-646**: Phases 2-6: Analytics for each date
5. **Line 684-687**: FINALLY block - ALWAYS calls `batch_run_tracker.complete()`

### Batch Status Endpoint
**File**: `backend/app/api/v1/portfolios.py` (lines 620-722)

1. **Lines 664-678**: If `batch_run_tracker.get_current().batch_run_id` matches → return `"running"`
2. **Lines 684-703**: If tracker cleared AND snapshot exists → return `"completed"`
3. **Lines 705-713**: If tracker cleared AND NO snapshot → return `"idle"` **← BUG!**

---

## THE BUG

### Status Reporting Gap

When the batch **fails silently** (exception during Phase 1 or 2-6):
1. The exception is caught/logged but the batch completes
2. `batch_run_tracker.complete()` runs in finally block (tracker cleared)
3. No snapshots were created (batch failed during processing)
4. Status endpoint returns `"idle"` (no tracker, no snapshot)
5. **Frontend polls forever** because it only handles `"completed"`

### Missing Error Propagation

The frontend error handling (lines 254-267) only triggers on **API errors**, not on silent batch failures:
```typescript
} catch (error) {
  // Only handles network/API errors, not batch failures
  setUploadState('error')
}
```

---

## Architecture Diagram (Corrected)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND FLOW                                    │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 1: POST /onboarding/create-portfolio                               │
│  - Creates user, portfolio, imports positions                           │
│  - Returns portfolio_id                                                  │
│  ✅ WORKING                                                              │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 2: POST /portfolios/{id}/calculate                                │
│  - batch_run_tracker.start() marks as "running"                         │
│  - Starts background task: run_portfolio_onboarding_backfill()          │
│  - Returns batch_run_id for polling                                     │
│  ✅ WORKING                                                              │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 3: run_portfolio_onboarding_backfill() (Background)               │
│  - Phase 1: Market data collection                                      │
│  - Phase 1.5: Symbol universe                                           │
│  - Phase 2-6: Analytics and snapshots                                   │
│  - Finally: batch_run_tracker.complete()                                │
│  ❓ LIKELY FAILING HERE (silent exception)                              │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 4: GET /portfolios/{id}/batch-status/{batch_run_id} (Polling)     │
│  - If tracker has batch_run_id → "running"                              │
│  - If tracker cleared + snapshot → "completed"                          │
│  - If tracker cleared + NO snapshot → "idle" ← RETURNS THIS!            │
│  ❌ BUG: "idle" not handled by frontend                                 │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Frontend receives "idle" status                                        │
│  - Only checks for "completed"                                          │
│  - Keeps polling every 3 seconds forever                                │
│  - User sees "Analyzing Your Portfolio..." indefinitely                 │
│  ❌ BUG: No timeout or error handling for "idle"                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Evidence (Testscotty3)

| Check | Result | Implication |
|-------|--------|-------------|
| User created | ✅ 19:41:56 UTC | Onboarding Step 1 worked |
| Portfolio created | ✅ "Scott Y 5M" | Onboarding Step 1 worked |
| Positions imported | ✅ 13 positions | CSV parsing worked |
| All 13 symbols in universe | ✅ | Phase 1.5 ran successfully |
| Snapshots | ❌ 0 | Batch failed during Phase 2-6 |
| Factor exposures | ❌ 0 | Batch failed during Phase 2-6 |
| batch_run_history | ❌ No new entries | Need Railway logs to confirm |

---

## Why Batch Might Be Failing

### Hypothesis 1: Position Entry Dates Missing
If positions have no `entry_date`, the batch returns early (line 503-510):
```python
if not earliest_position_date:
    logger.warning(f"Portfolio {portfolio_id} has no positions with entry dates")
    return {'success': True, 'dates_processed': 0, ...}
```
**But**: This would still be "success" with 0 dates, not a failure.

### Hypothesis 2: Market Data Collection Failure (MOST LIKELY)
Phase 1 market data collection (lines 544-558) might be failing for some symbols:
- API rate limits
- Invalid symbols
- Network timeouts

### Hypothesis 3: Database Connection Exhaustion
Railway might be hitting connection limits during heavy batch processing.

### Hypothesis 4: Exception in Phase 2-6
`_run_phases_2_through_6()` might be throwing an exception that's caught but leaves no snapshots.

---

## Recommended Fixes

### Fix 1: Add "failed" Status to Batch Status Endpoint (HIGH PRIORITY)
**File**: `backend/app/api/v1/portfolios.py`

```python
# After checking for snapshot, check for recent batch_run_history failure
from app.models.batch_tracking import BatchRunHistory

result = await db.execute(
    select(BatchRunHistory)
    .where(
        BatchRunHistory.portfolio_id == portfolio_id,
        BatchRunHistory.status == 'failed'
    )
    .order_by(BatchRunHistory.started_at.desc())
    .limit(1)
)
failed_batch = result.scalar_one_or_none()

if failed_batch:
    return BatchStatusResponse(
        status="failed",  # NEW STATUS
        batch_run_id=batch_run_id,
        portfolio_id=str(portfolio_id),
        started_at=failed_batch.started_at.isoformat(),
        triggered_by=failed_batch.triggered_by,
        elapsed_seconds=0,
        error_message=failed_batch.error_message  # NEW FIELD
    )
```

### Fix 2: Frontend Handle "failed" and "idle" Status (HIGH PRIORITY)
**File**: `frontend/src/hooks/usePortfolioUpload.ts`

```typescript
// In polling callback:
if (status.status === 'completed') {
  // ... existing success handling
} else if (status.status === 'failed' || status.status === 'idle') {
  // NEW: Handle batch failure
  if (pollIntervalRef.current) {
    clearInterval(pollIntervalRef.current)
  }
  setUploadState('error')
  setError(status.error_message || 'Batch processing failed. Please try again.')
}
```

### Fix 3: Add Polling Timeout (MEDIUM PRIORITY)
```typescript
const MAX_POLLING_TIME_MS = 5 * 60 * 1000  // 5 minutes

const pollingStartTime = Date.now()
if (Date.now() - pollingStartTime > MAX_POLLING_TIME_MS) {
  clearInterval(pollIntervalRef.current)
  setUploadState('error')
  setError('Processing took too long. Please contact support.')
}
```

### Fix 4: Better Batch Error Recording (MEDIUM PRIORITY)
**File**: `backend/app/batch/batch_orchestrator.py`

In `run_portfolio_onboarding_backfill()`, wrap more specific error recording:
```python
except Exception as e:
    logger.error(f"Onboarding batch failed: {e}", exc_info=True)
    record_batch_complete(
        batch_run_id=batch_run_id,
        status="failed",
        error_summary=str(e)
    )
    raise  # Re-raise to ensure failure is visible
```

---

## Immediate Action Items

1. **Check Railway Logs** - Look for errors during Testscotty3's batch processing
2. **Check Position Entry Dates** - Verify Testscotty3's 13 positions have valid entry_dates
3. **Implement Fix 1** - Add "failed" status to batch-status endpoint
4. **Implement Fix 2** - Frontend handle non-completed statuses
5. **Manual Test** - Trigger batch manually for Testscotty3 to verify Phase 1 fix

---

## Files Reviewed

### Frontend
1. `frontend/src/hooks/usePortfolioUpload.ts` - Main upload hook (492 lines)
2. `frontend/src/services/onboardingService.ts` - API service (135 lines)
3. `frontend/src/components/onboarding/UploadProcessing.tsx` - Processing UI (164 lines)

### Backend
1. `backend/app/api/v1/portfolios.py` - Calculate and batch-status endpoints (lines 521-722)
2. `backend/app/batch/batch_orchestrator.py` - run_portfolio_onboarding_backfill (lines 442-687)
3. `backend/app/api/v1/onboarding.py` - Create portfolio endpoint

---

## Conclusion

The frontend and backend are **correctly wired together**. The batch IS triggered. The problem is:

1. **The batch is failing silently** during execution (need Railway logs to confirm where)
2. **The status endpoint returns "idle"** instead of "failed" when no snapshots exist
3. **The frontend has no handling** for non-"completed" statuses, so it polls forever

The user sees "Analyzing Your Portfolio..." indefinitely because the batch failed but nobody told the frontend.

**Priority fixes**:
1. Add "failed" status to backend batch-status endpoint
2. Frontend handle "failed"/"idle" statuses with error UI
3. Add polling timeout as safety net
