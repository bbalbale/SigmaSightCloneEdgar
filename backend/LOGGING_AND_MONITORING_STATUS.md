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
- `app/calculations/correlations.py` - Correlation matrix progress
- `app/batch/market_data_sync.py` - Market data fetch operations

**Example from factors.py:**
```python
logger.info(f"Calculating factor betas for portfolio {portfolio_id} as of {calculation_date}")
logger.warning(f"Insufficient data: {len(common_dates)} days (minimum: {MIN_REGRESSION_DAYS})")
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

### 5. **No Data Quality Logging** ⚠️

**Problem:**
- Hard to see WHY calculations might be incomplete
- Missing: "23/75 positions had insufficient data for factor analysis"
- Missing: "Factor ETF VTV has only 45 days of data (need 90)"

**What's needed:**
```python
logger.warning(f"Data quality issue: {insufficient_count}/{total_symbols} symbols have <90 days")
logger.info(f"Factor analysis quality: {quality_flag} - used {len(common_dates)} days")
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

**Add to batch orchestrator:**
```python
from app.models.snapshots import BatchJob

async def _execute_job_safely(self, job_name, job_func, args, portfolio_name):
    # Create BatchJob record
    batch_job = BatchJob(
        job_name=job_name,
        job_type=self._get_job_type(job_name),
        status="running",
        started_at=utc_now()
    )
    db.add(batch_job)
    await db.commit()

    try:
        # Execute job...
        result = await job_func(db, *args)

        # Update on success
        batch_job.status = "success"
        batch_job.completed_at = utc_now()
        batch_job.duration_seconds = (utc_now() - batch_job.started_at).total_seconds()
        batch_job.job_metadata = result

    except Exception as e:
        # Update on failure
        batch_job.status = "failed"
        batch_job.error_message = str(e)[:1000]

    await db.commit()
```

**Benefit:** Query batch history via database/API instead of parsing Railway logs

---

### Priority 2: Create Batch History API Endpoint

```python
@router.get("/batch/history")
async def get_batch_history(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100
):
    """Query batch job execution history"""
    # Query BatchJob table
    # Return structured results
```

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

### Priority 5: Data Quality Summary Logging

```python
# At start of each calculation
logger.info(f"Data availability check:")
logger.info(f"  - Positions with ≥90 days: {sufficient_count}/{total_count}")
logger.info(f"  - Positions with <90 days: {insufficient_count}/{total_count}")
logger.info(f"  - Factor ETFs data range: {min_date} to {max_date}")

# At end
logger.info(f"Calculation quality summary:")
logger.info(f"  - Full quality: {full_quality_count}")
logger.info(f"  - Limited quality: {limited_quality_count}")
logger.info(f"  - Failed: {failed_count}")
```

**Benefit:** Understand why calculations might be incomplete

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
| **Database Persistence** | ❌ Missing | Critical gap |
| **Batch History API** | ❌ Missing | Critical gap |
| **Progress Indicators** | ⚠️ Partial | Could be better |
| **Data Quality Logs** | ⚠️ Partial | Could be better |
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
