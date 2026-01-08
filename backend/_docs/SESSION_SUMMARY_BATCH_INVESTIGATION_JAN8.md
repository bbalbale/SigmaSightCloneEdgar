# Session Summary: Testscotty Batch Processing Investigation

**Date**: January 8, 2026
**Last Active**: Investigating why batch processing fails for new onboarded portfolios
**Investigator**: Claude Opus 4.5

---

## The Problem

When users onboard via CSV upload (Testscotty2 "Yaphe 5M" and Testscotty3 "Scott Y 5M"), the batch processing that calculates portfolio analytics **fails silently**. Users see "Analyzing Your Portfolio..." indefinitely.

---

## Key Findings

### 1. Frontend DOES Call the Batch (Corrected Finding)
- `usePortfolioUpload.ts:183` calls `onboardingService.triggerCalculations()`
- This hits `POST /api/v1/portfolios/{id}/calculate`
- The batch IS triggered - it just fails silently

### 2. The Batch Fails Before Recording Start
- **No `onboarding_*` entries** in `batch_run_history` table
- This means the batch crashes BEFORE line 532 of `run_portfolio_onboarding_backfill()` which calls `record_batch_start()`

### 3. Root Cause: Likely Railway Timeout
- Testscotty3 has positions with `entry_date = 2025-01-06`
- Batch needs to process **~264 trading days** (Jan 6, 2025 → Jan 8, 2026)
- Railway likely kills long-running background tasks before completion

### 4. Status Reporting Bug (Secondary Issue)
- When batch fails, `batch_run_tracker.complete()` runs (in finally block)
- `/batch-status` endpoint returns `"idle"` when no snapshots exist
- Frontend only handles `"completed"` status → **polls forever**

### 5. Cron Batches Also Stuck
- Multiple cron batches stuck in "running" status (Jan 5, Jan 2, Dec 31, etc.)
- Demo portfolios stopped getting snapshots after Jan 5

---

## Database Evidence

### Testscotty3 Portfolio
- **Portfolio ID**: `21075bee-0f81-53be-bd95-facd2a40f8c5`
- **Portfolio Name**: "Scott Y 5M"
- **User Email**: elliott.ng+testscotty3@gmail.com

| Item | Status |
|------|--------|
| User created | ✅ 19:41:56 UTC Jan 8 |
| Portfolio "Scott Y 5M" | ✅ Created |
| 13 positions imported | ✅ All have entry_date 2025-01-06 |
| All 13 symbols in symbol_universe | ✅ |
| Market data in cache | ✅ 250-795 records per symbol |
| Snapshots | ❌ 0 |
| Factor exposures | ❌ 0 |
| batch_run_history entry | ❌ None for onboarding |

### Testscotty3 Positions (All PUBLIC class)
| Symbol | Entry Date | Entry Price | Quantity |
|--------|------------|-------------|----------|
| BIL | 2025-01-06 | $91.44 | 8,202 |
| GGIPX | 2025-01-06 | $22.40 | 11,160 |
| GINDX | 2025-01-06 | $33.45 | 31,928 |
| GOVT | 2025-01-06 | $23.09 | 14,381 |
| IAU | 2025-01-06 | $83.96 | 2,977 |
| IEFA | 2025-01-06 | $91.30 | 5,476 |
| LQD | 2025-01-06 | $110.62 | 1,355 |
| MUB | 2025-01-06 | $107.66 | 1,393 |
| NEAIX | 2025-01-06 | $64.32 | 777 |
| VO | 2025-01-06 | $295.86 | 168 |
| VTV | 2025-01-06 | $193.94 | 2,062 |
| VUG | 2025-01-06 | $492.16 | 2,031 |
| XLV | 2025-01-06 | $159.34 | 313 |

### Batch Run History (Recent)
Multiple batches stuck in "running" status:
- `batch_20260108_092147` - Jan 9 01:21 UTC - manual - running
- `batch_20260105_233025` - Jan 5 - cron - running
- `batch_20260102_233044` - Jan 2 - cron - running
- `batch_20251231_233052` - Dec 31 - cron - running

---

## Files Involved

### Backend
- `backend/app/api/v1/portfolios.py` - `/calculate` endpoint (lines 521-617), `/batch-status` endpoint (lines 620-722)
- `backend/app/batch/batch_orchestrator.py` - `run_portfolio_onboarding_backfill()` (lines 442-687)

### Frontend
- `frontend/src/hooks/usePortfolioUpload.ts` - Main upload hook with polling logic
- `frontend/src/services/onboardingService.ts` - API calls
- `frontend/src/components/onboarding/UploadProcessing.tsx` - "Analyzing Your Portfolio..." UI

### Documentation
- `backend/_docs/CODE_REVIEW_ONBOARDING_BATCH_INVESTIGATION.md` - Full investigation with findings and recommended fixes

---

## Architecture Flow (What Should Happen)

```
Frontend                                    Backend
────────                                    ───────
1. POST /onboarding/create-portfolio  ────► Creates portfolio, imports positions
   ◄──── Returns portfolio_id

2. POST /portfolios/{id}/calculate    ────► batch_run_tracker.start()
   ◄──── Returns batch_run_id              Starts background task:
                                           run_portfolio_onboarding_backfill()
                                              │
3. GET /batch-status/{batch_run_id}   ────► │ Phase 1: Market data (264 days)
   (polling every 3s)                       │ Phase 1.5: Symbol factors
   ◄──── "running" / "completed"            │ Phase 2-6: P&L, snapshots, analytics
                                            │
                                            ▼ FAILS HERE (timeout?)
                                           batch_run_tracker.complete()

4. Frontend receives "idle" status
   (no snapshot exists)
   Keeps polling forever ❌
```

---

## Next Steps (When Session Resumes)

### 1. Get Railway Logs
- **Service**: SigmaSight-BE
- **Time**: January 8, 2026, **19:40 - 19:55 UTC**
- **Look for**:
  - `ERROR`, `Exception`
  - `Portfolio Onboarding Backfill`
  - `21075bee` (portfolio ID prefix)
  - `Phase 1`, `Phase 2`, `Phase 3`
  - `Killed`, `Timeout`, `OOM`

### 2. Potential Fixes to Implement

**Fix 1: Chunked Backfill (HIGH PRIORITY)**
Don't process 264 days in one background task. Options:
- Process in chunks (30 days at a time)
- Use job queue (Celery, RQ)
- Run as separate worker process

**Fix 2: Backend - Add "failed" Status**
File: `backend/app/api/v1/portfolios.py`
```python
# In batch-status endpoint, check for failed batch
if no_snapshot and no_running_batch:
    return BatchStatusResponse(status="failed", ...)
```

**Fix 3: Frontend - Handle Non-Completed Statuses**
File: `frontend/src/hooks/usePortfolioUpload.ts`
```typescript
if (status.status === 'failed' || status.status === 'idle') {
  clearInterval(pollIntervalRef.current)
  setUploadState('error')
  setError('Processing failed. Please try again.')
}
```

**Fix 4: Polling Timeout (MEDIUM PRIORITY)**
Add 5-minute timeout as safety net in frontend polling.

### 3. Manual Test
Once fixes are understood, manually trigger batch for Testscotty3 to verify.

---

## Git Status at Session End

**Branch**: main

**Uncommitted files**:
- `CODE_REVIEW_REQUEST_CLERKAUTH.md`
- `backend/_docs/CODE_REVIEW_ONBOARDING_BATCH_INVESTIGATION.md`
- Various backup/test files

**Recent commits on main**:
- `387c34d6` - feat: Use custom JWT template with 1-hour token lifetime
- `9b7f1cb7` - fix: Remove localStorage auth patterns blocking Clerk users
- `3004cd6b` - fix: Address code review findings - JWT audience and routing
- `27092bc6` - feat: Add Clerk auth columns migration (rebased on main)

---

## Summary One-Liner

**The onboarding batch IS triggered but crashes before recording anything because processing ~264 trading days exceeds Railway's background task timeout. Need Railway logs from Jan 8 19:40-19:55 UTC to confirm.**

---

## To Resume This Session

Share this file with Claude and say:
> "Continue investigating the batch processing failure for Testscotty3. Here's the session summary from last time. I have Railway logs to share."

Then paste the Railway logs.
