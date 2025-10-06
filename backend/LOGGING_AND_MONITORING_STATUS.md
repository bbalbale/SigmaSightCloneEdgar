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

## 🎯 Simplified Design Details

### Endpoint 1: Trigger Batch (Replaces /trigger/daily)

**Endpoint:** `POST /admin/batch/run`

**See implementation in Step 2 of the Simplified Implementation Plan above.**

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

### Simplified Implementation Plan (Option A - Minimal Real-Time Monitoring)

**Goal:** Remote trigger + real-time progress polling, minimal complexity

#### Step 1: Create Minimal In-Memory Tracker
**File:** `app/batch/batch_run_tracker.py`

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class CurrentBatchRun:
    """Minimal state for current batch run"""
    batch_run_id: str
    started_at: datetime
    triggered_by: str

    # Counts
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0

    # Current state
    current_job_name: Optional[str] = None
    current_portfolio_name: Optional[str] = None

class BatchRunTracker:
    """Simple singleton - only tracks CURRENT run"""
    def __init__(self):
        self._current: Optional[CurrentBatchRun] = None

    def start(self, run: CurrentBatchRun):
        self._current = run

    def get_current(self) -> Optional[CurrentBatchRun]:
        return self._current

    def complete(self):
        self._current = None

    def update(self, total_jobs: int = None, completed: int = None,
               failed: int = None, job_name: str = None,
               portfolio_name: str = None):
        if not self._current:
            return
        if total_jobs is not None:
            self._current.total_jobs = total_jobs  # Dynamic update
        if completed is not None:
            self._current.completed_jobs = completed
        if failed is not None:
            self._current.failed_jobs = failed
        if job_name:
            self._current.current_job_name = job_name
        if portfolio_name:
            self._current.current_portfolio_name = portfolio_name

# Singleton
batch_run_tracker = BatchRunTracker()
```

**~50 lines instead of 150+**

#### Step 2: Create 2 New Endpoints
**File:** `app/api/v1/endpoints/admin_batch.py`

Add these two endpoints (delete the old trigger/daily):

```python
from app.batch.batch_run_tracker import batch_run_tracker, CurrentBatchRun

@router.post("/run")
async def run_batch_processing(
    portfolio_id: Optional[str] = Query(None),
    force: bool = Query(False),
    background_tasks: BackgroundTasks,
    admin_user = Depends(require_admin)
):
    """Trigger batch with real-time tracking"""
    if batch_run_tracker.get_current() and not force:
        raise HTTPException(409, "Batch already running")

    run_id = str(uuid4())
    run = CurrentBatchRun(
        batch_run_id=run_id,
        started_at=utc_now(),
        triggered_by=admin_user.email
    )
    batch_run_tracker.start(run)

    background_tasks.add_task(_run_batch_with_tracking, run_id, portfolio_id)

    return {
        "status": "started",
        "batch_run_id": run_id,
        "poll_url": "/api/v1/admin/batch/run/current"
    }

@router.get("/run/current")
async def get_current_batch_status(admin_user = Depends(require_admin)):
    """Poll for real-time progress"""
    current = batch_run_tracker.get_current()

    if not current:
        return {"status": "idle", "message": "No batch running"}

    elapsed = (utc_now() - current.started_at).total_seconds()
    progress = (current.completed_jobs / current.total_jobs * 100) if current.total_jobs > 0 else 0

    return {
        "status": "running",
        "batch_run_id": current.batch_run_id,
        "started_at": current.started_at,
        "elapsed_seconds": elapsed,
        "jobs": {
            "total": current.total_jobs,
            "completed": current.completed_jobs,
            "failed": current.failed_jobs
        },
        "current_job": current.current_job_name,
        "current_portfolio": current.current_portfolio_name,
        "progress_percent": round(progress, 1)
    }
```

**~60 lines instead of 300+**

#### Step 3: Minimal Orchestrator Integration
**File:** `app/batch/batch_orchestrator_v2.py`

Add lightweight tracking calls (with dynamic job counting):

```python
async def _run_batch_with_tracking(batch_run_id: str, portfolio_id: Optional[str]):
    from app.batch.batch_run_tracker import batch_run_tracker

    try:
        # Get portfolios
        portfolios = await _get_portfolios(portfolio_id)

        # Initialize counters (don't pre-calculate total - jobs vary by portfolio)
        total_jobs = 0
        completed = 0
        failed = 0

        for portfolio in portfolios:
            batch_run_tracker.update(portfolio_name=portfolio.name)

            # Get actual jobs to run for this portfolio (Greeks may be disabled, etc.)
            jobs_to_run = _get_jobs_for_portfolio(portfolio)

            for job in jobs_to_run:
                total_jobs += 1  # Increment total as we discover jobs

                batch_run_tracker.update(
                    job_name=job,
                    total_jobs=total_jobs  # Update total dynamically
                )

                try:
                    await _execute_job(job, portfolio)
                    completed += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"Job {job} failed: {e}")

                batch_run_tracker.update(
                    completed=completed,
                    failed=failed
                )

        batch_run_tracker.complete()

    except Exception as e:
        logger.error(f"Batch failed: {e}")
        batch_run_tracker.complete()
```

**Key Fix:** Dynamic job counting instead of hard-coded `len(portfolios) * 8`
- Greeks disabled? Total doesn't include it
- Stress tests skip? Total adjusts automatically
- Progress % stays accurate

**~50 lines of integration instead of complex session management**

#### Step 4: Delete Unwanted Endpoints (9 endpoints)
**File:** `app/api/v1/endpoints/admin_batch.py`

Delete these functions entirely:
1. `trigger_daily` → Replaced by `/run`
2. `trigger_greeks`, `trigger_factors`, `trigger_stress_tests`, `trigger_snapshot` → Redundant
3. `cancel_batch_job` → Not needed for MVP
4. `get_batch_schedules`, `pause_scheduler`, `resume_scheduler` → APScheduler not running

#### Step 5: Register Router ⭐ **CRITICAL**
**File:** `app/api/v1/router.py`

```python
from app.api.v1.endpoints import admin_batch

api_router.include_router(
    admin_batch.router,
    tags=["Admin - Batch Processing"]
)
```

#### Keep Unchanged (4 endpoints)
Already in admin_batch.py, just register them:
1. `POST /admin/batch/trigger/market-data`
2. `POST /admin/batch/trigger/correlations`
3. `GET /admin/batch/data-quality`
4. `POST /admin/batch/data-quality/refresh`

---

### What We're NOT Doing (Complexity Cuts)

❌ No per-job BatchJob DB persistence
❌ No historical batch run lookups
❌ No cancel endpoint
❌ No fixing broken /jobs/status and /jobs/summary
❌ No data quality roll-ups
❌ No verbose progress logging
❌ No job results storage

### What We Get

✅ Remote batch trigger (no SSH)
✅ Real-time progress monitoring (poll every 3 seconds)
✅ Force flag to override concurrent runs
✅ Progress bar in local script
✅ Know which job/portfolio is running
✅ See completion % and elapsed time

**Total Implementation:** ~150 lines of new code instead of 800+
**Final Endpoint Count:** 6 working endpoints (2 new + 4 existing)

---

## 📋 Agent Feedback & Decisions

**Feedback Received:** Another agent suggested going even simpler - just register existing router, add summary log line, no real-time monitoring.

**Our Decision:** Stick with current plan for real-time monitoring

**Why:**
1. **User requirement explicit:** "status endpoint that can be hit repeatedly to get the latest status of the currently running batch process"
2. **Existing endpoints don't work:** `/jobs/status` and `/jobs/summary` query empty BatchJob table, don't show real-time progress
3. **Real-time monitoring is the goal:** Summary logs only show results after completion, not during execution
4. **Acceptable complexity:** ~150 lines is manageable vs. 800+ lines of full proposal

**Feedback Incorporated:**
- ✅ Fixed hard-coded "8 jobs per portfolio" bug - now uses dynamic job counting
- ✅ Avoided DB persistence complexity (in-memory only)
- ✅ Cut unnecessary features (cancel, history, data quality roll-ups)
- ✅ Kept code minimal (~150 lines)

**Risks Accepted:**
- ⚠️ Server restart = lost tracking state (acceptable for MVP)
- ⚠️ Railway cron + API trigger could conflict (mitigated by timing/manual coordination)
- ⚠️ Background tasks die on server shutdown (acceptable - Railway cron is durable fallback)
- ⚠️ No audit trail (Railway logs sufficient for now)

---

## ✅ Benefits of Simplified Approach

1. **No SSH Required:** Trigger and monitor batches via API from local machine
2. **Real-time Progress:** Poll `/run/current` every 3 seconds to see live progress
3. **Concurrent Run Prevention:** Avoid conflicts with `force` flag override
4. **Progress Monitoring:** Track completion %, current job, elapsed time
5. **Scriptable:** Easy to automate with local bash/python scripts
6. **Minimal Code:** ~150 lines of new code instead of 800+
7. **No DB Complexity:** In-memory tracking, no session management headaches
8. **Clean API:** 6 working endpoints (2 new + 4 existing) instead of 0
9. **No Dead Code:** Delete 9 unused endpoints entirely
10. **Fast to Ship:** Can implement in a few hours instead of days
