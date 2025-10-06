# Logging and Monitoring Status - SigmaSight Backend

**Date:** 2025-10-06
**Context:** Remote deployment debugging challenges

---

## ✅ Current Logging Infrastructure

### 1. **Console & File Logging** (app/core/logging.py)

**Good News:**
- ✅ Structured logging configured with `get_logger(__name__)`
- ✅ Dual output: stdout (Railway can capture) + rotating file logs
- ✅ **JSON format in production** - machine parseable
- ✅ Human-readable format in development
- ✅ 10MB rotating logs with 5 backup files (50MB total)
- ✅ Module-scoped loggers (batch, market_data, api, auth, db)

**Configuration:**
```python
LOG_LEVEL=INFO  # Default (can be DEBUG, INFO, WARNING, ERROR)
ENVIRONMENT=production  # Triggers JSON logging format
```

**Log Output Locations:**
- Railway stdout/stderr (real-time via `railway logs`)
- Local file: `logs/sigmasight.log` (rotating)

---

### 2. **Batch Orchestrator Logging** (app/batch/batch_orchestrator_v2.py)

**What's Logged:**

```python
# High-level progress
logger.info(f"Starting sequential batch processing at {start_time}")
logger.info(f"Processing {len(portfolios)} portfolios sequentially")
logger.info(f"Processing portfolio {i}/{len(portfolios)}: {portfolio.name}")
logger.info(f"Sequential batch processing completed in {duration.total_seconds():.2f}s")

# Job-level execution
logger.info(f"Starting job: {job_name} (attempt {attempt + 1})")
logger.info(f"Job {job_name} completed in {duration:.2f}s")

# Errors with categorization
logger.error(f"Greenlet error in job {job_name} (attempt {attempt + 1}): {error_msg}")
logger.warning(f"Transient error in job {job_name} (attempt {attempt + 1}): {error_msg}")
logger.error(f"Job {job_name} failed (attempt {attempt + 1}): {error_msg}")
logger.error(f"Stack trace for {job_name}: {traceback.format_exc()}")  # On final attempt

# Warnings
logger.warning(f"No portfolios found to process")
logger.warning(f"Critical job {job_name} failed for {portfolio_name}, skipping remaining jobs")
```

**Strengths:**
- ✅ Start/end timestamps with duration
- ✅ Retry attempts tracked
- ✅ Error categorization (greenlet, transient, permanent)
- ✅ Stack traces on final failure
- ✅ Portfolio name context included

---

### 3. **Individual Calculation Engine Logging**

Each calculation module has logger calls:
- `app/calculations/factors.py` - Factor analysis progress
- `app/calculations/greeks.py` - Greeks calculation details
- `app/services/correlation_service.py` - Correlation matrix progress
- `app/batch/market_data_sync.py` - Market data fetch operations

**Example from factors.py:**
```python
logger.info(f"Calculating factor betas for portfolio {portfolio_id} as of {calculation_date}")
logger.warning(f"Insufficient data: {len(common_dates)} days (minimum: {MIN_REGRESSION_DAYS})")
```

**Example from batch_orchestrator_v2.py (Greeks job):**
```python
logger.info(f"Fetched market data for {len(market_data)} symbols for Greeks calculation")
```

---

## ❌ What's Missing (CRITICAL GAPS)

### 1. **No Database Persistence of Batch Job Logs** 🚨

**Problem:**
- `BatchJob` model exists but **NOT USED** in `batch_orchestrator_v2.py`
- Railway logs are ephemeral (lost on restart/redeploy)
- No historical audit trail of batch runs in database

**What should be stored:**
```python
class BatchJob:
    job_name: str           # "factor_analysis_portfolio_abc123"
    job_type: str          # "risk_metrics"
    status: str            # "success" | "failed" | "running"
    started_at: datetime
    completed_at: datetime
    duration_seconds: int
    records_processed: int
    error_message: str     # If failed
    job_metadata: JSON     # Results summary
```

**Impact:**
- Can't query "when was the last successful factor analysis run?"
- Can't see failure patterns over time
- Can't audit which portfolios were processed

---

### 2. **No Structured Batch Run Summary** 🚨

**Problem:**
- Results returned as list of dicts but not aggregated
- No "batch run ID" to tie all jobs together
- Can't easily see: "8 jobs run, 6 succeeded, 2 failed"

**What's needed:**
```python
{
    "batch_run_id": "uuid",
    "started_at": "2025-10-06T10:00:00",
    "portfolios_processed": 3,
    "total_jobs": 24,  # 3 portfolios × 8 jobs
    "successful_jobs": 20,
    "failed_jobs": 4,
    "total_duration": 127.5,
    "job_summary": [
        {"job": "market_data_update", "portfolios": 3, "success": 3, "failed": 0},
        {"job": "factor_analysis", "portfolios": 3, "success": 2, "failed": 1},
        ...
    ]
}
```

---

### 3. **Railway-Specific Challenges** 🚨

**Problem:**
- Railway logs are time-limited (only recent logs visible)
- No easy way to grep/search Railway logs programmatically
- Logs intermixed with HTTP access logs (noise)
- Can't filter by portfolio or job type easily

**What's needed:**
- Database-backed audit trail
- Structured logging with consistent fields
- API endpoint to query batch history

---

### 4. **No Progress Indicators for Long-Running Jobs** ⚠️

**Problem:**
- Factor analysis on 3 portfolios with 75 positions could take minutes
- No indication of progress (e.g., "Processing position 15/75")
- Hard to tell if job is stuck or just slow

**What's needed:**
```python
logger.info(f"Factor analysis: Processing position {i}/{total_positions} ({symbol})")
logger.info(f"Factor analysis: {len(position_betas)}/{total_positions} positions completed")
```

---

### 5. **Limited Data Quality Roll-up Logging** ⚠️

**Current Status:**
- ✅ Individual calculation quality logging exists (`app/calculations/factors.py:86-92, 408-427`)
- ✅ Per-portfolio quality metadata captured
- ❌ Missing: Aggregate batch-level summaries

**What exists:**
```python
# app/calculations/factors.py lines 86-92
logger.info(f"Factor returns calculated: {total_days} days of data")
if missing_data.any():
    logger.warning(f"Missing data in factor returns: {missing_data[missing_data > 0].to_dict()}")

# lines 408-427
'data_quality': {
    'quality_flag': quality_flag,
    'regression_days': len(common_dates),
    'positions_processed': len(position_betas)
}
logger.info(f"Factor betas calculated: {len(position_betas)} positions, {quality_flag}")
```

**What's needed:**
```python
# Aggregate summaries across batch run
logger.info(f"Batch quality: {full_quality_count}/{total_portfolios} portfolios with full data")
logger.info(f"Cross-portfolio data availability: {avg_data_days:.0f} days average")
```

---

## 📊 Railway Logs Access

**Current Access Methods:**

1. **Railway Web Dashboard**
   ```
   https://railway.app → Project → Deployment → Logs tab
   ```
   - Real-time streaming
   - Search/filter by text
   - Download logs

2. **Railway CLI**
   ```bash
   railway logs --follow
   railway logs --tail 1000
   railway logs --since 1h
   ```

3. **Log Persistence**
   - Railway keeps logs for ~7 days
   - Older logs are automatically purged
   - NO permanent storage

---

## 🎯 Recommendations for Better Remote Debugging

### Priority 1: Enable Database Batch Job Logging

**Implementation Challenge:**
The current `_execute_job_safely()` method creates an isolated session for each job via `_get_isolated_session()`. BatchJob logging needs to happen either:
- **OUTSIDE** the isolated session (using a separate tracking session)
- **OR** passed into the session context as part of the job execution

**Proposed Pattern:**
```python
from app.models.snapshots import BatchJob

async def _execute_job_safely(self, job_name, job_func, args, portfolio_name):
    start_time = utc_now()

    # Option 1: Create separate session for BatchJob tracking
    async with self._get_isolated_session() as tracking_db:
        batch_job = BatchJob(
            job_name=job_name,
            job_type=job_name.split("_")[0],  # Extract type from job name
            status="running",
            started_at=start_time
        )
        tracking_db.add(batch_job)
        await tracking_db.commit()
        job_id = batch_job.id

    try:
        # Execute job in its own isolated session
        async with self._get_isolated_session() as db:
            result = await job_func(db, *args) if args else await job_func(db)

        # Update on success
        async with self._get_isolated_session() as tracking_db:
            batch_job = await tracking_db.get(BatchJob, job_id)
            batch_job.status = "success"
            batch_job.completed_at = utc_now()
            batch_job.duration_seconds = (utc_now() - start_time).total_seconds()
            batch_job.job_metadata = result
            await tracking_db.commit()

    except Exception as e:
        # Update on failure
        async with self._get_isolated_session() as tracking_db:
            batch_job = await tracking_db.get(BatchJob, job_id)
            batch_job.status = "failed"
            batch_job.error_message = str(e)[:1000]
            batch_job.completed_at = utc_now()
            batch_job.duration_seconds = (utc_now() - start_time).total_seconds()
            await tracking_db.commit()
```

**Benefit:** Query batch history via database/API instead of parsing Railway logs

**Note:** This requires careful integration with existing retry logic and error handling in batch_orchestrator_v2.py

---

### Priority 2: Fix Existing Batch History API Endpoints

**Status:** ✅ Endpoints EXIST but ❌ BROKEN and UNUSED

**Existing Endpoints:**
- `GET /api/v1/admin/batch/jobs/status` (`app/api/v1/endpoints/admin_batch.py:212`)
- `GET /api/v1/admin/batch/jobs/summary` (`app/api/v1/endpoints/admin_batch.py:258`)

**Issues:**
1. **Code bugs:**
   - Line 234: References `BatchJob.portfolio_id` (field doesn't exist in model)
   - Line 254: Calls `job.to_dict()` (method doesn't exist in model)

2. **Data issue:**
   - BatchJob table is empty (orchestrator doesn't populate it)

**Required Fixes:**
1. Add `portfolio_id: Mapped[Optional[UUID]]` to BatchJob model (app/models/snapshots.py)
2. Add `to_dict()` method to BatchJob model OR remove references to it
3. Integrate BatchJob logging into batch_orchestrator_v2.py (see Priority 1)

**Benefit:** Can check batch status from anywhere (web UI, curl, monitoring)

---

### Priority 3: Enhanced Structured Logging

**Add correlation IDs:**
```python
batch_run_id = str(uuid4())
logger.info(f"[{batch_run_id}] Starting batch for portfolio {portfolio_id}")
logger.info(f"[{batch_run_id}] Job {job_name} completed")
```

**Benefit:** Group all logs from a single batch run together

---

### Priority 4: Add Progress Logging in Calculations

```python
# In factor analysis
logger.info(f"Factor analysis progress: {completed}/{total} positions ({completed/total*100:.1f}%)")

# In correlation analysis
logger.info(f"Correlation progress: Computed {pairs_done}/{total_pairs} pairwise correlations")
```

**Benefit:** Know if job is progressing or stuck

---

### Priority 5: Enhance Data Quality Roll-up Logging

**Current Status:** ✅ Individual calculation quality logging EXISTS

**Existing Quality Logging in `app/calculations/factors.py`:**
```python
# Lines 86-92: Per-calculation data quality
total_days = len(returns_df)
missing_data = returns_df.isnull().sum()

logger.info(f"Factor returns calculated: {total_days} days of data")
if missing_data.any():
    logger.warning(f"Missing data in factor returns: {missing_data[missing_data > 0].to_dict()}")

# Lines 408-427: Per-portfolio quality metadata
'data_quality': {
    'quality_flag': quality_flag,
    'regression_days': len(common_dates),
    'required_days': MIN_REGRESSION_DAYS,
    'positions_processed': len(position_betas),
    'factors_processed': len(factor_returns_aligned.columns)
}

logger.info(f"Factor betas calculated and stored successfully: {len(position_betas)} positions, {quality_flag}")
```

**What's Missing:** Aggregate summaries across batch runs
```python
# At batch completion - add roll-up summary
logger.info(f"Batch run data quality summary:")
logger.info(f"  - Portfolios with full quality: {full_quality_count}/{total_portfolios}")
logger.info(f"  - Portfolios with limited quality: {limited_quality_count}/{total_portfolios}")
logger.info(f"  - Portfolios failed: {failed_count}/{total_portfolios}")
logger.info(f"  - Aggregate positions processed: {total_positions_processed}")
logger.info(f"  - Cross-portfolio data availability: {avg_data_days:.0f} days average")
```

**Benefit:** Understand aggregate data quality across all portfolios in a batch run

---

## 🚀 Quick Wins for Immediate Improvement

1. **Set LOG_LEVEL=DEBUG on Railway** (temporarily)
   ```bash
   railway variables --set LOG_LEVEL=DEBUG
   ```

2. **Add batch run summary logging** (5 min change)
   ```python
   # At end of run_daily_batch_sequence()
   success = sum(1 for r in all_results if r['status'] == 'completed')
   failed = sum(1 for r in all_results if r['status'] == 'failed')
   logger.info(f"Batch run complete: {success} succeeded, {failed} failed")
   ```

3. **Create simple batch status endpoint** (10 min change)
   ```python
   @router.get("/batch/last-run")
   async def get_last_batch_run():
       # Check batch_jobs table for most recent run
       # Or read from file system timestamp
       return {"last_run": "2025-10-06T10:00:00", "status": "success"}
   ```

---

## 📝 Current Logging Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| **Console Logging** | ✅ Good | Captured by Railway |
| **Structured Format** | ✅ Good | JSON in production |
| **Log Rotation** | ✅ Good | 50MB total |
| **Error Context** | ✅ Good | Stack traces included |
| **Database Persistence** | ❌ Missing | Critical gap - needs implementation |
| **Batch History API** | ⚠️ Broken | Endpoints exist but broken (see Priority 2) |
| **Progress Indicators** | ⚠️ Partial | Could be better |
| **Data Quality Logs** | ⚠️ Partial | Individual logs exist, needs roll-up |
| **Correlation IDs** | ❌ Missing | Hard to trace |

---

## 🎯 Bottom Line

**Current State:**
- Decent console logging exists
- Railway captures logs but they're ephemeral
- Hard to debug remote issues without database audit trail

**Immediate Action Needed:**
1. Enable BatchJob database logging (Priority 1)
2. Add batch history API endpoint (Priority 2)
3. Increase log detail for long-running calculations (Priority 3)

**Long-term:**
- Consider structured logging service (DataDog, CloudWatch, Sentry)
- Add real-time monitoring dashboard
- Implement alerting for batch failures

---

# 🚀 Proposed: API-Based Batch Management

## Problem Statement

**Current SSH-Based Workflow is Onerous:**
- Requires `railway run` to SSH into Railway environment
- Hard to monitor batch progress in real-time
- Can't easily script batch execution and monitoring
- Railway logs are ephemeral and hard to search

**Desired Workflow:**
```bash
# Local script triggers batch on Railway via API
./scripts/run_railway_batch.sh

# Script polls status endpoint until complete
# Shows real-time progress without SSH
```

---

## Existing Admin Batch Endpoints (app/api/v1/endpoints/admin_batch.py)

### 🚨 CRITICAL FINDING: Admin Batch Endpoints Are NOT Registered

**Status:** The `admin_batch.py` router exists but is **completely orphaned** - it is NOT included in the FastAPI application.

**Evidence:**
- File exists: `app/api/v1/endpoints/admin_batch.py` (502 lines, 15 endpoints defined)
- Router created: `router = APIRouter(prefix="/admin/batch", tags=["Admin - Batch Processing"])`
- **NOT imported** in `app/api/v1/router.py`
- **NOT registered** in the main API router
- **NOT accessible** via HTTP requests

**Impact:**
- All 15 admin batch endpoints return 404 Not Found
- Frontend cannot call these endpoints
- Manual API testing would fail
- The endpoints exist as dead code only

**To Enable These Endpoints:**
```python
# In app/api/v1/router.py, add:
from app.api.v1.endpoints import admin_batch

api_router.include_router(
    admin_batch.router,
    tags=["Admin - Batch Processing"]
)
```

**Recommendation:** Since we're planning to delete 9 of these 15 endpoints anyway, we should:
1. Create the new `/admin/batch/run` endpoints with proper tracking
2. Fix the 2 broken endpoints (jobs/status, jobs/summary)
3. Register ONLY the new/fixed endpoints (6 total)
4. Never register the 9 endpoints marked for deletion

---

### ✅ Keep Unchanged (After Registration)

| Endpoint | Current Status | Reason |
|----------|---------------|---------|
| `POST /admin/batch/trigger/market-data` | ❌ Not Registered (code exists) | Useful standalone operation |
| `POST /admin/batch/trigger/correlations` | ❌ Not Registered (code exists) | Weekly job, special case |
| `GET /admin/batch/data-quality` | ❌ Not Registered (code exists) | Pre-flight validation |
| `POST /admin/batch/data-quality/refresh` | ❌ Not Registered (code exists) | Targeted data refresh |

### ⚠️ Fix Required (After Registration)

| Endpoint | Issue | Fix Needed |
|----------|-------|------------|
| `GET /admin/batch/jobs/status` | ❌ Not Registered<br>Line 234: `BatchJob.portfolio_id` doesn't exist<br>Line 254: `job.to_dict()` doesn't exist | Register endpoint<br>Add `portfolio_id` field to BatchJob model<br>Add `to_dict()` method or remove references |
| `GET /admin/batch/jobs/summary` | ❌ Not Registered<br>Line 254: `job.to_dict()` doesn't exist | Register endpoint<br>Same as above |

### ❌ Delete and Replace (Never Register These)

| Endpoint | Reason | Replacement |
|----------|--------|-------------|
| `POST /admin/batch/trigger/daily` | ❌ Not Registered<br>Lacks tracking, force flag, progress monitoring | **NEW:** `POST /admin/batch/run` |
| `POST /admin/batch/trigger/greeks` | ❌ Not Registered<br>Redundant | Use `/admin/batch/run?portfolio_id={id}` |
| `POST /admin/batch/trigger/factors` | ❌ Not Registered<br>Redundant | Use `/admin/batch/run?portfolio_id={id}` |
| `POST /admin/batch/trigger/stress-tests` | ❌ Not Registered<br>Redundant | Use `/admin/batch/run?portfolio_id={id}` |
| `POST /admin/batch/trigger/snapshot` | ❌ Not Registered<br>Redundant | Use `/admin/batch/run?portfolio_id={id}` |
| `DELETE /admin/batch/jobs/{job_id}/cancel` | ❌ Not Registered<br>Won't work without batch run tracking | **NEW:** `POST /admin/batch/run/current/cancel` |
| `GET /admin/batch/schedules` | ❌ Not Registered<br>**APScheduler not running** | Railway cron job (railway.json) |
| `POST /admin/batch/scheduler/pause` | ❌ Not Registered<br>**APScheduler not running** | Railway dashboard to disable cron |
| `POST /admin/batch/scheduler/resume` | ❌ Not Registered<br>**APScheduler not running** | Railway dashboard to enable cron |

**Rationale:** These individual calculation triggers are redundant when we have a comprehensive batch run endpoint. Since they're not registered anyway, simply don't include them when registering the admin batch router.

**APScheduler Investigation:** The APScheduler (`app/batch/scheduler_config.py`) is configured but **never started** in `app/main.py`. The application uses Railway's cron job system instead:
- **Railway Cron:** Runs at 11:30 PM UTC (6:30 PM ET) weekdays via `railway.json`
- **Script:** `scripts/automation/railway_daily_batch.py`
- **Workflow:** Checks trading day → Syncs market data → Runs batch calculations
- **Scheduler Endpoints:** Return misleading information since APScheduler isn't running

---

## 🎯 Proposed New Endpoints

### 1. New Batch Execution Endpoint (Replaces /trigger/daily)

**Delete:** `POST /admin/batch/trigger/daily`
**Create:** `POST /admin/batch/run`

```python
@router.post("/run")
async def run_batch_processing(
    portfolio_id: Optional[str] = Query(None, description="Specific portfolio or all"),
    force: bool = Query(False, description="Force run even if batch already running"),
    skip_market_data: bool = Query(False, description="Skip market data update"),
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """
    Trigger batch processing with real-time tracking.

    Returns batch_run_id for status polling.
    Prevents concurrent runs unless force=True.
    """
    # Check if batch already running
    if batch_run_tracker.is_running() and not force:
        current_run = batch_run_tracker.get_current()
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Batch already running",
                "current_batch_run_id": current_run.batch_run_id,
                "started_at": current_run.started_at,
                "progress": current_run.get_progress()
            }
        )

    # Create new batch run
    batch_run_id = str(uuid4())
    batch_run = BatchRun(
        batch_run_id=batch_run_id,
        portfolio_id=portfolio_id,
        started_at=utc_now(),
        triggered_by=admin_user.email,
        skip_market_data=skip_market_data
    )

    # Register with tracker
    batch_run_tracker.start(batch_run)

    # Execute in background
    background_tasks.add_task(
        _run_batch_with_tracking,
        batch_run_id,
        portfolio_id,
        skip_market_data
    )

    return {
        "status": "started",
        "batch_run_id": batch_run_id,
        "portfolio_id": portfolio_id or "all",
        "triggered_by": admin_user.email,
        "timestamp": utc_now(),
        "status_url": f"/api/v1/admin/batch/run/{batch_run_id}",
        "current_status_url": f"/api/v1/admin/batch/run/current"
    }
```

**Response Example:**
```json
{
  "status": "started",
  "batch_run_id": "550e8400-e29b-41d4-a716-446655440000",
  "portfolio_id": "all",
  "triggered_by": "admin@sigmasight.com",
  "timestamp": "2025-10-06T14:30:00Z",
  "status_url": "/api/v1/admin/batch/run/550e8400-e29b-41d4-a716-446655440000",
  "current_status_url": "/api/v1/admin/batch/run/current"
}
```

---

### 2. Current Batch Status Endpoint (Polling)

**New:** `GET /admin/batch/run/current`

```python
@router.get("/run/current")
async def get_current_batch_status(
    admin_user = Depends(require_admin)
):
    """
    Get status of currently running batch process.

    Returns null if no batch running.
    Designed for polling every 2-5 seconds.
    """
    current_run = batch_run_tracker.get_current()

    if not current_run:
        return {
            "status": "idle",
            "batch_run_id": None,
            "message": "No batch processing currently running"
        }

    return {
        "status": "running",
        "batch_run_id": current_run.batch_run_id,
        "started_at": current_run.started_at,
        "elapsed_seconds": (utc_now() - current_run.started_at).total_seconds(),
        "triggered_by": current_run.triggered_by,

        # Progress details
        "portfolios": {
            "total": current_run.total_portfolios,
            "completed": current_run.completed_portfolios,
            "current": current_run.current_portfolio_name
        },

        "jobs": {
            "total": current_run.total_jobs,
            "completed": current_run.completed_jobs,
            "running": current_run.running_jobs,
            "failed": current_run.failed_jobs,
            "pending": current_run.pending_jobs
        },

        "current_job": {
            "name": current_run.current_job_name,
            "portfolio": current_run.current_portfolio_name,
            "started_at": current_run.current_job_started_at
        },

        "progress_percent": round(
            (current_run.completed_jobs / current_run.total_jobs * 100)
            if current_run.total_jobs > 0 else 0,
            1
        )
    }
```

**Response Example (Running):**
```json
{
  "status": "running",
  "batch_run_id": "550e8400-e29b-41d4-a716-446655440000",
  "started_at": "2025-10-06T14:30:00Z",
  "elapsed_seconds": 127.5,
  "triggered_by": "admin@sigmasight.com",

  "portfolios": {
    "total": 3,
    "completed": 1,
    "current": "Sophisticated High Net Worth Portfolio"
  },

  "jobs": {
    "total": 24,
    "completed": 10,
    "running": 1,
    "failed": 1,
    "pending": 12
  },

  "current_job": {
    "name": "factor_analysis",
    "portfolio": "Sophisticated High Net Worth Portfolio",
    "started_at": "2025-10-06T14:32:15Z"
  },

  "progress_percent": 41.7
}
```

**Response Example (Idle):**
```json
{
  "status": "idle",
  "batch_run_id": null,
  "message": "No batch processing currently running"
}
```

---

### 3. Historical Batch Run Status

**New:** `GET /admin/batch/run/{batch_run_id}`

```python
@router.get("/run/{batch_run_id}")
async def get_batch_run_status(
    batch_run_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """
    Get status of specific batch run (current or completed).
    """
    # Check in-memory tracker first (for current/recent runs)
    run = batch_run_tracker.get(batch_run_id)

    if run:
        return run.to_dict()

    # Check database for historical runs (if we add BatchRun table)
    # For now, return 404
    raise HTTPException(
        status_code=404,
        detail=f"Batch run {batch_run_id} not found"
    )
```

---

### 4. Cancel Current Batch Run

**New:** `POST /admin/batch/run/current/cancel`

```python
@router.post("/run/current/cancel")
async def cancel_current_batch(
    admin_user = Depends(require_admin)
):
    """
    Cancel the currently running batch process.

    Marks current job as cancelled and prevents new jobs from starting.
    Jobs already running will complete.
    """
    current_run = batch_run_tracker.get_current()

    if not current_run:
        raise HTTPException(
            status_code=404,
            detail="No batch currently running"
        )

    # Mark as cancelled
    current_run.status = "cancelled"
    current_run.cancelled_by = admin_user.email
    current_run.cancelled_at = utc_now()

    logger.warning(
        f"Batch run {current_run.batch_run_id} cancelled by {admin_user.email}"
    )

    return {
        "status": "cancelled",
        "batch_run_id": current_run.batch_run_id,
        "cancelled_by": admin_user.email,
        "jobs_completed": current_run.completed_jobs,
        "jobs_pending": current_run.pending_jobs,
        "timestamp": utc_now()
    }
```

---

## 🔧 Implementation: Batch Run Tracker

### In-Memory State Tracker (MVP)

**Location:** `app/batch/batch_run_tracker.py`

```python
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
from uuid import UUID
from app.core.datetime_utils import utc_now

@dataclass
class BatchRun:
    """Tracks state of a batch processing run"""
    batch_run_id: str
    portfolio_id: Optional[str]
    started_at: datetime
    triggered_by: str
    skip_market_data: bool = False

    # Status
    status: str = "running"  # running, completed, failed, cancelled
    completed_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    cancelled_at: Optional[datetime] = None

    # Portfolio progress
    total_portfolios: int = 0
    completed_portfolios: int = 0
    current_portfolio_name: Optional[str] = None

    # Job progress
    total_jobs: int = 0
    completed_jobs: int = 0
    running_jobs: int = 0
    failed_jobs: int = 0
    pending_jobs: int = 0

    # Current job
    current_job_name: Optional[str] = None
    current_job_started_at: Optional[datetime] = None

    # Results
    job_results: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize to dict for API response"""
        return {
            "batch_run_id": self.batch_run_id,
            "portfolio_id": self.portfolio_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "triggered_by": self.triggered_by,
            "status": self.status,

            "portfolios": {
                "total": self.total_portfolios,
                "completed": self.completed_portfolios,
                "current": self.current_portfolio_name
            },

            "jobs": {
                "total": self.total_jobs,
                "completed": self.completed_jobs,
                "running": self.running_jobs,
                "failed": self.failed_jobs,
                "pending": self.pending_jobs
            },

            "progress_percent": round(
                (self.completed_jobs / self.total_jobs * 100)
                if self.total_jobs > 0 else 0,
                1
            ),

            "elapsed_seconds": (
                (self.completed_at or utc_now()) - self.started_at
            ).total_seconds(),

            "results": self.job_results
        }


class BatchRunTracker:
    """Singleton tracker for batch run state"""

    def __init__(self):
        self._current_run: Optional[BatchRun] = None
        self._recent_runs: Dict[str, BatchRun] = {}  # Last 10 runs
        self._max_recent = 10

    def start(self, batch_run: BatchRun):
        """Register new batch run as current"""
        self._current_run = batch_run
        self._recent_runs[batch_run.batch_run_id] = batch_run

        # Trim old runs
        if len(self._recent_runs) > self._max_recent:
            oldest_id = min(
                self._recent_runs.keys(),
                key=lambda k: self._recent_runs[k].started_at
            )
            del self._recent_runs[oldest_id]

    def complete(self, batch_run_id: str, status: str = "completed"):
        """Mark batch run as complete"""
        if self._current_run and self._current_run.batch_run_id == batch_run_id:
            self._current_run.status = status
            self._current_run.completed_at = utc_now()
            self._current_run = None  # No longer current

    def is_running(self) -> bool:
        """Check if any batch is currently running"""
        return self._current_run is not None

    def get_current(self) -> Optional[BatchRun]:
        """Get currently running batch"""
        return self._current_run

    def get(self, batch_run_id: str) -> Optional[BatchRun]:
        """Get batch run by ID (current or recent)"""
        if self._current_run and self._current_run.batch_run_id == batch_run_id:
            return self._current_run
        return self._recent_runs.get(batch_run_id)

    def update_progress(
        self,
        batch_run_id: str,
        completed_jobs: Optional[int] = None,
        failed_jobs: Optional[int] = None,
        current_job_name: Optional[str] = None,
        current_portfolio_name: Optional[str] = None
    ):
        """Update progress for current batch run"""
        run = self.get(batch_run_id)
        if not run:
            return

        if completed_jobs is not None:
            run.completed_jobs = completed_jobs
            run.pending_jobs = run.total_jobs - completed_jobs - failed_jobs

        if failed_jobs is not None:
            run.failed_jobs = failed_jobs

        if current_job_name:
            run.current_job_name = current_job_name
            run.current_job_started_at = utc_now()
            run.running_jobs = 1

        if current_portfolio_name:
            run.current_portfolio_name = current_portfolio_name


# Global singleton instance
batch_run_tracker = BatchRunTracker()
```

---

### Integration with Batch Orchestrator

**Modify:** `app/batch/batch_orchestrator_v2.py`

```python
async def _run_batch_with_tracking(
    batch_run_id: str,
    portfolio_id: Optional[str],
    skip_market_data: bool
):
    """
    Execute batch with real-time progress tracking.

    Updates batch_run_tracker as jobs complete.
    """
    from app.batch.batch_run_tracker import batch_run_tracker

    try:
        # Get portfolios to process
        async with get_async_session() as db:
            if portfolio_id:
                portfolio = await db.get(Portfolio, UUID(portfolio_id))
                portfolios = [portfolio] if portfolio else []
            else:
                result = await db.execute(select(Portfolio))
                portfolios = result.scalars().all()

        # Calculate total jobs
        jobs_per_portfolio = 8  # 8 calculation engines
        total_jobs = len(portfolios) * jobs_per_portfolio

        # Update tracker with totals
        run = batch_run_tracker.get(batch_run_id)
        run.total_portfolios = len(portfolios)
        run.total_jobs = total_jobs
        run.pending_jobs = total_jobs

        # Execute batch with progress updates
        completed_jobs = 0
        failed_jobs = 0

        for i, portfolio in enumerate(portfolios):
            batch_run_tracker.update_progress(
                batch_run_id,
                current_portfolio_name=portfolio.name
            )

            # Run each job for this portfolio
            for job_name in ["market_data", "positions", "greeks", ...]:
                # Update current job
                batch_run_tracker.update_progress(
                    batch_run_id,
                    current_job_name=job_name
                )

                try:
                    # Execute job
                    result = await self._execute_job(...)
                    completed_jobs += 1
                except Exception as e:
                    failed_jobs += 1
                    logger.error(f"Job {job_name} failed: {e}")

                # Update progress
                batch_run_tracker.update_progress(
                    batch_run_id,
                    completed_jobs=completed_jobs,
                    failed_jobs=failed_jobs
                )

        # Mark complete
        batch_run_tracker.complete(batch_run_id, "completed")

    except Exception as e:
        logger.error(f"Batch run {batch_run_id} failed: {e}")
        batch_run_tracker.complete(batch_run_id, "failed")
```

---

## 📝 Local Monitoring Script Example

**Create:** `scripts/railway_batch_monitor.sh`

```bash
#!/bin/bash

# Railway Batch Processing Monitor
# Triggers batch processing on Railway and monitors progress via API

RAILWAY_URL="https://sigmasight-backend.railway.app"
API_BASE="$RAILWAY_URL/api/v1"
ADMIN_EMAIL="admin@sigmasight.com"
ADMIN_PASSWORD="your_password"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🚀 Railway Batch Processing Monitor"
echo "===================================="

# Step 1: Login to get JWT token
echo -n "Logging in as $ADMIN_EMAIL... "
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ]; then
  echo -e "${RED}❌ Login failed${NC}"
  exit 1
fi
echo -e "${GREEN}✅${NC}"

# Step 2: Start batch processing
echo -n "Starting batch processing... "
START_RESPONSE=$(curl -s -X POST "$API_BASE/admin/batch/run?force=false" \
  -H "Authorization: Bearer $TOKEN")

BATCH_RUN_ID=$(echo $START_RESPONSE | jq -r '.batch_run_id')
STATUS=$(echo $START_RESPONSE | jq -r '.status')

if [ "$STATUS" != "started" ]; then
  echo -e "${RED}❌ Failed to start${NC}"
  echo $START_RESPONSE | jq '.'
  exit 1
fi

echo -e "${GREEN}✅${NC}"
echo "Batch Run ID: $BATCH_RUN_ID"
echo ""

# Step 3: Poll for status updates
echo "Monitoring batch progress..."
echo "----------------------------"

while true; do
  # Get current status
  STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/admin/batch/run/current" \
    -H "Authorization: Bearer $TOKEN")

  CURRENT_STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')

  # Check if batch completed
  if [ "$CURRENT_STATUS" = "idle" ]; then
    echo -e "\n${GREEN}✅ Batch processing completed!${NC}"
    break
  fi

  # Extract progress details
  PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress_percent')
  CURRENT_JOB=$(echo $STATUS_RESPONSE | jq -r '.current_job.name')
  CURRENT_PORTFOLIO=$(echo $STATUS_RESPONSE | jq -r '.portfolios.current')
  COMPLETED_JOBS=$(echo $STATUS_RESPONSE | jq -r '.jobs.completed')
  TOTAL_JOBS=$(echo $STATUS_RESPONSE | jq -r '.jobs.total')
  FAILED_JOBS=$(echo $STATUS_RESPONSE | jq -r '.jobs.failed')
  ELAPSED=$(echo $STATUS_RESPONSE | jq -r '.elapsed_seconds')

  # Display progress bar
  printf "\r[%-50s] %3.1f%% | %s | %s (%d/%d jobs, %d failed) | %ds" \
    $(printf '#%.0s' $(seq 1 $((${PROGRESS%.*}/2)))) \
    $PROGRESS \
    "$CURRENT_JOB" \
    "$CURRENT_PORTFOLIO" \
    $COMPLETED_JOBS \
    $TOTAL_JOBS \
    $FAILED_JOBS \
    ${ELAPSED%.*}

  # Wait before next poll
  sleep 3
done

# Step 4: Get final results
echo ""
echo "Fetching final results..."
FINAL_RESPONSE=$(curl -s -X GET "$API_BASE/admin/batch/run/$BATCH_RUN_ID" \
  -H "Authorization: Bearer $TOKEN")

echo $FINAL_RESPONSE | jq '.'
```

**Usage:**
```bash
chmod +x scripts/railway_batch_monitor.sh
./scripts/railway_batch_monitor.sh
```

**Expected Output:**
```
🚀 Railway Batch Processing Monitor
====================================
Logging in as admin@sigmasight.com... ✅
Starting batch processing... ✅
Batch Run ID: 550e8400-e29b-41d4-a716-446655440000

Monitoring batch progress...
----------------------------
[####################                              ] 41.7% | factor_analysis | Sophisticated High Net Worth Portfolio (10/24 jobs, 1 failed) | 127s
```

---

## 📊 API Endpoint Summary

### 🚨 Current State: All Admin Batch Endpoints Return 404
The `admin_batch.py` router is **NOT registered** in `app/api/v1/router.py`. All 15 existing endpoints are orphaned dead code.

### Proposed Implementation Plan

#### Create New (4 endpoints)
1. `POST /admin/batch/run` - Start batch with tracking and force option
2. `GET /admin/batch/run/current` - Poll current batch status (real-time)
3. `GET /admin/batch/run/{batch_run_id}` - Get specific batch run status
4. `POST /admin/batch/run/current/cancel` - Cancel current batch

#### Register + Fix Existing (2 endpoints)
1. `GET /admin/batch/jobs/status` - Fix portfolio_id and to_dict() issues
2. `GET /admin/batch/jobs/summary` - Fix to_dict() issue

#### Register Unchanged (4 endpoints)
1. `POST /admin/batch/trigger/market-data`
2. `POST /admin/batch/trigger/correlations`
3. `GET /admin/batch/data-quality`
4. `POST /admin/batch/data-quality/refresh`

#### Never Register (9 endpoints - just delete code)
1. `POST /admin/batch/trigger/daily` → Replaced by `/admin/batch/run`
2. `POST /admin/batch/trigger/greeks` → Redundant
3. `POST /admin/batch/trigger/factors` → Redundant
4. `POST /admin/batch/trigger/stress-tests` → Redundant
5. `POST /admin/batch/trigger/snapshot` → Redundant
6. `DELETE /admin/batch/jobs/{job_id}/cancel` → Replaced by `/run/current/cancel`
7. `GET /admin/batch/schedules` → APScheduler not running
8. `POST /admin/batch/scheduler/pause` → APScheduler not running
9. `POST /admin/batch/scheduler/resume` → APScheduler not running

**Final Result:** 10 working admin batch endpoints (4 new + 2 fixed + 4 existing) instead of 0 current

---

## ✅ Benefits

1. **No SSH Required:** Trigger and monitor batches via API from local machine
2. **Real-time Progress:** Poll `/run/current` to see live progress
3. **Concurrent Run Prevention:** Avoid conflicts with `force` flag override
4. **Better Monitoring:** Track progress percent, current job, elapsed time
5. **Scriptable:** Easy to automate with local scripts
6. **Simpler API:** Create 6 working endpoints instead of registering 15 (4 new + 2 fixed = 6 total)
7. **Audit Trail:** Track who triggered batches and when
8. **Remove Dead Code:** Never register 9 endpoints that are orphaned anyway
9. **First Working Admin Endpoints:** Current endpoints are NOT registered (all return 404)
