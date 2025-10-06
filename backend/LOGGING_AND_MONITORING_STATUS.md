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
