# Phase 9: Railway Company Profile Integration

**Status**: Planning
**Created**: 2025-10-07
**Target**: Consolidate company profile sync into Railway cron automation

---

## Executive Summary

Integrate company profile synchronization (yfinance + yahooquery) into the existing Railway daily batch cron job (`scripts/automation/railway_daily_batch.py`), replacing the dormant APScheduler-based approach that was never activated in production.

**Goals**:
- Automate daily company profile updates on Railway
- Consolidate batch operations into single Railway cron service
- Remove unused APScheduler code and configuration
- Improve operational simplicity and monitoring

**Non-Goals**:
- Changing company profile data sources (stays yfinance + yahooquery)
- Modifying batch orchestrator (batch_orchestrator_v2)
- Adding new profile fields or schemas

---

## Current State Analysis

### What Works
✅ **Company Profile Fetcher** (`app/services/yahooquery_profile_fetcher.py`)
- Hybrid yfinance (basics) + yahooquery (estimates) approach
- 70+ fields: company name, sector, industry, revenue/earnings estimates
- Batch processing with rate limiting (10 symbols at a time)

✅ **Railway Cron Job** (`scripts/automation/railway_daily_batch.py`)
- Runs daily at 11:30 PM UTC (6:30 PM EST/7:30 PM EDT) on weekdays
- Successfully executes market data sync + batch calculations
- Proven reliable on Railway production environment

✅ **Manual Trigger API** (`/api/v1/admin/batch/trigger/company-profiles`)
- Admin endpoint works for on-demand profile sync
- Successfully used to populate Railway database (58.6% coverage for HNW portfolio)

### What's Broken
❌ **APScheduler Integration** (`app/batch/scheduler_config.py`)
- Defines company profile sync at 7:00 PM ET daily
- **Never integrated into FastAPI app lifecycle**
- No `lifespan` context manager in `app/main.py`
- Scheduler never starts, jobs never run
- Code is dormant since creation

❌ **Fragmented Scheduling**
- Railway cron handles market data + batch calc
- APScheduler (dormant) was intended for profiles, correlations, quality checks
- Two separate systems that should be one

### Current Railway Production Data
From audit (2025-10-07):
- **75 total positions** across 3 portfolios
- **Company name coverage**: 17/29 (58.6%) for HNW, 0% for Individual/Hedge Fund
- **Reason for gaps**: Profiles only populated for symbols explicitly processed
- **No automatic refresh**: Profiles become stale over time

---

## Proposed Solution

### Architecture Change

**Before**:
```
Railway Cron (11:30 PM UTC)          APScheduler (dormant)
├─ Market data sync                  ├─ 7:00 PM: Company profiles (never runs)
└─ Batch calculations                ├─ 7:30 PM: Quality check (never runs)
                                     └─ Weekly backfill (never runs)
```

**After**:
```
Railway Cron (11:30 PM UTC)
├─ Step 1: Market data sync
├─ Step 1.5: Company profile sync (NEW)
└─ Step 2: Batch calculations
```

### Why This Approach

**Benefits**:
1. **Actually works** - Railway cron proven reliable, APScheduler never ran
2. **Single monitoring point** - All logs in one Railway deployment
3. **Simpler deployment** - No need to fix APScheduler integration
4. **Consistent environment** - Same database connection, error handling
5. **Trading day logic** - Profiles only sync when markets traded (no wasted API calls)
6. **Resource efficient** - Railway ephemeral containers (vs always-on web server)

**Tradeoffs**:
1. Longer total cron duration (~6-7 min vs ~5 min) - acceptable
2. All-or-nothing execution - mitigated with try/except
3. Coupled scheduling - acceptable for daily operations

---

## Implementation Plan

### Phase 9.1: Railway Cron Integration

#### Task 1: Add Company Profile Sync Step
**File**: `scripts/automation/railway_daily_batch.py`

```python
async def sync_company_profiles_step() -> Dict[str, Any]:
    """
    Sync company profiles from yfinance + yahooquery.

    Returns:
        Dict with sync results (successful, failed, total counts)

    Notes:
        Non-critical step - failures logged but don't stop batch calculations
    """
    from app.batch.market_data_sync import sync_company_profiles

    logger.info("=" * 60)
    logger.info("STEP 1.5: Company Profile Sync")
    logger.info("=" * 60)

    try:
        start_time = datetime.datetime.now()
        result = await sync_company_profiles()
        duration = (datetime.datetime.now() - start_time).total_seconds()

        logger.info(
            f"✅ Company profiles sync complete: "
            f"{result['successful']}/{result['total']} successful ({duration:.1f}s)"
        )

        return {
            "status": "success",
            "duration_seconds": duration,
            "successful": result['successful'],
            "failed": result['failed'],
            "total": result['total']
        }

    except Exception as e:
        logger.error(f"⚠️ Company profile sync failed: {e}")
        logger.exception(e)
        # Don't raise - this is non-critical enrichment data
        return {
            "status": "error",
            "error": str(e),
            "duration_seconds": 0
        }
```

**Error Handling Strategy**:
- **Non-blocking**: Profile sync failures don't prevent batch calculations
- **Logged**: All errors captured in Railway logs for debugging
- **Graceful degradation**: Partial failures (e.g., 5/10 symbols failed) still succeed
- **Exit code**: Don't count profile failures toward job exit code (only batch calc failures matter)

#### Task 2: Update Main Workflow
**File**: `scripts/automation/railway_daily_batch.py`

```python
async def main():
    # ... existing code ...

    try:
        # Step 0: Check trading day
        should_run = await check_trading_day(force=args.force)
        if not should_run:
            logger.info("Exiting: Not a trading day")
            sys.exit(0)

        # Step 1: Sync market data
        market_data_result = await sync_market_data_step()

        # Step 1.5: Sync company profiles (NEW - non-blocking)
        profile_result = await sync_company_profiles_step()

        # Step 2: Run batch calculations
        batch_results = await run_batch_calculations_step()

        # Step 3: Log completion summary
        await log_completion_summary(
            job_start,
            market_data_result,
            profile_result,  # NEW
            batch_results
        )
    # ... rest of exception handling ...
```

#### Task 3: Update Completion Summary
**File**: `scripts/automation/railway_daily_batch.py`

```python
async def log_completion_summary(
    start_time: datetime.datetime,
    market_data_result: Dict[str, Any],
    profile_result: Dict[str, Any],  # NEW parameter
    batch_results: List[Dict[str, Any]]
) -> None:
    """Log final completion summary including company profile sync."""

    # ... existing code ...

    logger.info(f"Market Data Sync:    {market_data_result['status']} ({market_data_result['duration_seconds']:.1f}s)")
    logger.info(f"Company Profiles:    {profile_result['status']} ({profile_result.get('successful', 0)}/{profile_result.get('total', 0)} symbols, {profile_result.get('duration_seconds', 0):.1f}s)")
    logger.info(f"Batch Calculations:  {success_count} portfolios succeeded, {fail_count} failed")
    logger.info("=" * 60)

    # Exit code based ONLY on batch calculations (not profiles)
    if fail_count > 0:
        logger.warning(f"⚠️ Job completed with {fail_count} portfolio failure(s)")
        sys.exit(1)
    else:
        logger.info("✅ All operations completed successfully")
        sys.exit(0)
```

---

### Phase 9.2: Documentation Updates

#### Task 4: Update Railway README
**File**: `scripts/automation/README.md`

Update workflow description:
```markdown
## Overview

This automation runs **every weekday at 11:30 PM UTC** (6:30pm EST / 7:30pm EDT) to:
1. Check if today is a trading day (NYSE calendar)
2. Sync latest market data for all portfolio positions
3. Sync company profiles (name, sector, industry, estimates) from yfinance + yahooquery  <!-- NEW -->
4. Run 8 calculation engines for all active portfolios
5. Log completion summary
```

Add troubleshooting section:
```markdown
### Company Profile Sync Failures
- **Expected behavior** - yahooquery/yfinance have occasional API issues
- Partial failures (some symbols succeed, some fail) are normal
- Profile sync failures DO NOT stop batch calculations
- Review logs for specific symbols failing
- Check if Yahoo Finance is experiencing outages
```

#### Task 5: Update API Reference
**File**: `backend/_docs/reference/API_REFERENCE_V1.4.6.md`

Update admin batch endpoint documentation:
```markdown
#### POST /api/v1/admin/batch/trigger/company-profiles

**Status**: ⚠️ DEPRECATED - Now runs automatically via Railway cron daily

**Description**: Manually trigger company profile synchronization.

**Note**: As of Phase 9, company profiles sync automatically as part of daily Railway
cron job (11:30 PM UTC). This endpoint remains available for emergency manual syncs
or testing purposes only.
```

---

### Phase 9.3: Code Cleanup

#### Task 6: Remove APScheduler Code (Optional - Can Defer)
**Files to consider removing**:
- `app/batch/scheduler_config.py` - APScheduler configuration (never used)
- References to `batch_scheduler` in `admin_batch.py` endpoint

**Reasoning for deferral**:
- Code doesn't hurt anything (it's just not running)
- May want to keep for future weekly/monthly jobs
- Can clean up in Phase 10 after Railway cron proven reliable

**If removing**:
1. Delete `app/batch/scheduler_config.py`
2. Update `admin_batch.py` trigger endpoint to call `sync_company_profiles()` directly
3. Remove APScheduler from `pyproject.toml` dependencies
4. Update CLAUDE.md Part II reference architecture

---

## Critical Implementation Notes

**⚠️ READ BEFORE CODING**: These details prevent common bugs and ensure correct integration.

### 1. Exit Code Semantics (Railway Cron Script)

**Current Behavior** (`scripts/automation/railway_daily_batch.py`):
- Job exits 0 (success) if all portfolios succeed
- Job exits 1 (failure) if ANY portfolio fails
- Exit code determines Railway retry behavior

**Required for Phase 9**:
- **Company profile failures MUST NOT change exit code**
- Only batch calculation failures should trigger exit 1
- Profile sync is non-critical enrichment data

**Implementation**:
```python
async def log_completion_summary(..., profile_result, ...):
    # ... existing code ...

    # Exit code based ONLY on batch calculations (not profiles)
    if fail_count > 0:
        logger.warning(f"⚠️ Job completed with {fail_count} portfolio failure(s)")
        sys.exit(1)  # Only batch failures trigger retry
    else:
        logger.info("✅ All operations completed successfully")
        sys.exit(0)  # Profile failures don't affect exit code
```

---

### 2. Service Layer Return Value Mismatch

**Actual Service** (`app/batch/market_data_sync.py:390`):
```python
async def sync_company_profiles():
    return {
        'total': int,
        'successful': int,
        'failed': int,
        'duration': float  # NOT duration_seconds
    }
```

**Requirements Doc Example** (uses `duration_seconds`):
```python
return {
    'status': 'success',
    'duration_seconds': duration,  # Key mismatch!
    ...
}
```

**Solution**: Normalize in wrapper, don't change service
```python
async def sync_company_profiles_step() -> Dict[str, Any]:
    """Thin wrapper that normalizes sync_company_profiles() return value."""
    from app.batch.market_data_sync import sync_company_profiles

    try:
        start_time = datetime.datetime.now()
        result = await sync_company_profiles()

        # Normalize duration → duration_seconds
        return {
            "status": "success",
            "duration_seconds": result.get('duration', 0),  # Rename key
            "successful": result['successful'],
            "failed": result['failed'],
            "total": result['total']
        }
    except Exception as e:
        # Ensure status field always exists for summary formatter
        return {
            "status": "error",
            "error": str(e),
            "duration_seconds": 0,
            "successful": 0,
            "failed": 0,
            "total": 0
        }
```

---

### 3. Event Loop Blocking (yahooquery/yfinance)

**Known Issue**: `yahooquery_profile_fetcher.py` uses synchronous HTTP calls
- `yfinance.Ticker()` and `yahooquery.Ticker()` block event loop
- Railway cron runs single asyncio process
- Profile sync will block during each API request (~1-2s per batch of 10)

**Impact**:
- Market data sync and batch calc can't progress during profile fetches
- Total job duration will be sum of all steps (not concurrent)
- Acceptable for daily cron, but worth noting

**Options**:

**Option A: Add TODO comment (recommended for Phase 9)**
```python
async def sync_company_profiles_step() -> Dict[str, Any]:
    """
    Sync company profiles from yfinance + yahooquery.

    TODO: yahooquery fetcher blocks event loop (synchronous HTTP).
    Consider wrapping in loop.run_in_executor() if this becomes
    a performance issue for large symbol counts.
    """
    # ... existing implementation ...
```

**Option B: Use run_in_executor (optional enhancement)**
```python
async def sync_company_profiles_step() -> Dict[str, Any]:
    from app.batch.market_data_sync import sync_company_profiles
    import asyncio

    try:
        start_time = datetime.datetime.now()
        loop = asyncio.get_event_loop()

        # Run blocking sync_company_profiles in thread pool
        result = await loop.run_in_executor(None, lambda: asyncio.run(sync_company_profiles()))

        # ... rest of implementation ...
```

**Recommendation**: Option A for Phase 9 (add TODO), defer Option B to Phase 10 unless profile sync duration exceeds 90 seconds.

---

### 4. Completion Summary Signature Mismatch

**Current Signature**:
```python
async def log_completion_summary(
    start_time: datetime.datetime,
    market_data_result: Dict[str, Any],
    batch_results: List[Dict[str, Any]]
) -> None:
```

**Required Signature** (after Phase 9):
```python
async def log_completion_summary(
    start_time: datetime.datetime,
    market_data_result: Dict[str, Any],
    profile_result: Dict[str, Any],  # NEW - add in correct position
    batch_results: List[Dict[str, Any]]
) -> None:
```

**Call Site Update Required**:
```python
# scripts/automation/railway_daily_batch.py main()

# Step 1: Sync market data
market_data_result = await sync_market_data_step()

# Step 1.5: Sync company profiles (NEW)
profile_result = await sync_company_profiles_step()

# Step 2: Run batch calculations
batch_results = await run_batch_calculations_step()

# Step 3: Log completion summary
await log_completion_summary(
    job_start,
    market_data_result,
    profile_result,      # NEW - must be in correct position
    batch_results
)
```

**Critical**: Pass arguments in correct order to avoid assigning `batch_results` to `profile_result` slot, which would crash the summary formatter.

---

### 5. Railway README Step Numbering

**Current README** (`scripts/automation/README.md:7-11`):
```markdown
## Overview

This automation runs **every weekday at 11:30 PM UTC** to:
1. Check if today is a trading day (NYSE calendar)
2. Sync latest market data for all portfolio positions
3. Run 8 calculation engines for all active portfolios
4. Log completion summary
```

**After Phase 9** (re-number steps):
```markdown
## Overview

This automation runs **every weekday at 11:30 PM UTC** to:
1. Check if today is a trading day (NYSE calendar)
2. Sync latest market data for all portfolio positions
3. Sync company profiles (name, sector, industry, estimates)  <!-- NEW -->
4. Run 8 calculation engines for all active portfolios
5. Log completion summary
```

**Also Update**: Add profile sync to troubleshooting section
```markdown
### Company Profile Sync Failures
- **Expected behavior**: yahooquery/yfinance have occasional API issues
- Partial failures (some symbols succeed, some fail) are normal
- Profile sync failures DO NOT stop batch calculations
- Review logs for specific symbols failing
- Check if Yahoo Finance is experiencing outages
```

---

### 6. Admin Endpoint Documentation Update

**Current Documentation** (`_docs/reference/API_REFERENCE_V1.4.6.md`):
```markdown
#### POST /api/v1/admin/batch/trigger/company-profiles

**Status**: ✅ Fully Implemented

**Description**: Manually trigger company profile synchronization.
```

**After Phase 9** (mark deprecated but retain usage):
```markdown
#### POST /api/v1/admin/batch/trigger/company-profiles

**Status**: ⚠️ DEPRECATED - Now runs automatically via Railway cron daily

**Description**: Manually trigger company profile synchronization.

**Note**: As of Phase 9 (October 2025), company profiles sync automatically as part of
daily Railway cron job (11:30 PM UTC on weekdays). This endpoint remains available for:
- Emergency manual syncs outside scheduled window
- Testing and development purposes
- Re-drives after Yahoo Finance API outages

Operations teams should rely on automatic sync for normal operations. Manual triggers
only needed for exception handling.

**Request**: POST /api/v1/admin/batch/trigger/company-profiles
**Auth**: Requires admin role
**Response**:
```json
{
  "status": "started",
  "message": "Company profile sync started for all portfolio symbols",
  "triggered_by": "admin@example.com",
  "timestamp": "2025-10-07T19:30:00Z"
}
```
```

---

### 7. APScheduler Cleanup Verification

**Before Deleting** `app/batch/scheduler_config.py`:

1. **Check for imports**:
```bash
grep -r "from app.batch.scheduler_config import" backend/
grep -r "import.*scheduler_config" backend/
grep -r "batch_scheduler" backend/
```

2. **Verify app/main.py doesn't reference scheduler**:
```python
# app/main.py should NOT have:
from app.batch.scheduler_config import start_batch_scheduler
# or
@app.on_event("startup")
async def startup():
    await start_batch_scheduler()
```

3. **Check admin endpoints**:
```python
# app/api/v1/endpoints/admin_batch.py line ~194
# Currently imports batch_scheduler for manual trigger
from app.batch.scheduler_config import batch_scheduler

# After removal, call service directly:
from app.batch.market_data_sync import sync_company_profiles
background_tasks.add_task(sync_company_profiles)  # Direct call
```

**If Keeping APScheduler** (recommended for Phase 9):
- Add comment to `scheduler_config.py`:
  ```python
  """
  APScheduler Configuration for Batch Processing

  ⚠️ NOTE (2025-10-07): This scheduler is NOT currently integrated into
  the FastAPI application lifecycle. Railway cron handles all scheduled
  jobs. This code remains for potential future use (weekly jobs, monthly
  reports, etc.) but should be considered dormant technical debt.

  See Phase 9 decision in TODO4.md for rationale.
  """
  ```

---

### 8. profile_result Always Has status Field

**Critical for Summary Formatter**:
```python
# This will crash if profile_result doesn't have 'status':
logger.info(f"Company Profiles: {profile_result['status']} ...")

# Solution: ALWAYS include status in return dict
async def sync_company_profiles_step() -> Dict[str, Any]:
    try:
        # ... success path ...
        return {
            "status": "success",  # REQUIRED
            "duration_seconds": duration,
            "successful": result['successful'],
            "failed": result['failed'],
            "total": result['total']
        }
    except Exception as e:
        # Exception path MUST also include status
        return {
            "status": "error",  # REQUIRED
            "error": str(e),
            "duration_seconds": 0,
            "successful": 0,
            "failed": 0,
            "total": 0
        }
```

---

## Testing Strategy

### Local Testing

#### Test 1: Dry Run (Non-Trading Day)
```bash
# Should skip due to trading day check
uv run python scripts/automation/railway_daily_batch.py

# Expected: "Not a trading day - skipping batch job"
```

#### Test 2: Force Run with Company Profiles
```bash
# Force execution on any day
uv run python scripts/automation/railway_daily_batch.py --force

# Expected output:
# STEP 1: Market Data Sync
# ✅ Market data sync complete (30.2s)
# STEP 1.5: Company Profile Sync
# ✅ Company profiles sync complete: 75/75 successful (45.3s)
# STEP 2: Batch Calculations
# ✅ Batch complete for Demo Individual Investor Portfolio (89.1s)
# ✅ All operations completed successfully
```

#### Test 3: Profile Sync Failure Handling
```bash
# Temporarily break yahooquery (e.g., remove API import)
# Run with --force

# Expected:
# ⚠️ Company profile sync failed: [error details]
# STEP 2: Batch Calculations  # Should still run!
# ✅ All operations completed successfully  # Exit 0 despite profile failure
```

### Railway Testing (Pre-Production)

#### Test 4: Manual Railway Trigger
```bash
# Target cron service with modified code
railway ssh --service sigmasight-backend-cron "uv run python scripts/automation/railway_daily_batch.py --force"

# Monitor logs for:
# - Company profile step executes
# - Logs show symbol counts (75/75 successful)
# - Batch calculations still run afterward
# - Exit code 0
```

#### Test 5: Production Dry Run (Trading Day)
```bash
# Wait for next trading day
# Let Railway cron run automatically at 11:30 PM UTC
# Check Railway deployment logs

# Verify:
# - Trading day detected correctly
# - Company profiles sync (should see "STEP 1.5")
# - All portfolios processed
# - Job completes successfully
```

---

## Deployment Plan

### Pre-Deployment Checklist
- [ ] All code changes committed to feature branch
- [ ] Local testing completed (Tests 1-3 pass)
- [ ] Railway SSH manual test completed (Test 4 passes)
- [ ] Documentation updated (README, API reference)
- [ ] Code review completed

### Deployment Steps

#### 1. Deploy to Railway Cron Service
```bash
# Commit and push changes
git add scripts/automation/railway_daily_batch.py
git add scripts/automation/README.md
git add _docs/requirements/PHASE_9_RAILWAY_COMPANY_PROFILE_INTEGRATION.md
git commit -m "feat(phase9): integrate company profile sync into Railway cron

- Add Step 1.5 to railway_daily_batch.py for company profile sync
- Non-blocking: profile failures don't stop batch calculations
- Updates 75 symbols daily from yfinance + yahooquery
- Consolidates batch operations into single Railway cron job
- Replaces dormant APScheduler approach

Phase 9 Implementation - See _docs/requirements/PHASE_9_RAILWAY_COMPANY_PROFILE_INTEGRATION.md"

git push origin main
```

#### 2. Verify Railway Deployment
```bash
# Check Railway dashboard
# - Project → sigmasight-backend-cron service
# - Deployments tab → Latest deployment
# - Status should be "Success"
```

#### 3. Manual Test on Railway
```bash
# Trigger manual run with --force
railway ssh --service sigmasight-backend-cron "uv run python scripts/automation/railway_daily_batch.py --force"

# Expected: Company profile step runs, job succeeds
```

#### 4. Wait for Automated Run
```bash
# Next weekday at 11:30 PM UTC
# Check Railway logs the following morning

# Verify in logs:
# - Trading day detected
# - STEP 1.5: Company Profile Sync appears
# - Successful completion message
```

#### 5. Verify Data Population
```bash
# Run Railway audit script locally
uv run python scripts/railway/audit_railway_data.py

# Check company name coverage improved
# HNW portfolio should show >58.6% coverage
# Individual/Hedge Fund portfolios should have names populated
```

---

## Success Metrics

### Functional Metrics
- ✅ Company profile sync executes daily on trading days
- ✅ 100% of position symbols have profiles attempted
- ✅ >80% success rate for profile fetches (acceptable given API variability)
- ✅ Batch calculations still complete successfully after profile step
- ✅ Total cron job duration <10 minutes (currently ~5 min, expect ~6-7 min)

### Operational Metrics
- ✅ Single Railway cron service handles all daily batch operations
- ✅ All logs consolidated in one Railway deployment stream
- ✅ No manual intervention required for profile updates
- ✅ Company name coverage improves from 58.6% to >80% after first run

### Data Quality Metrics
From `GET /api/v1/data/positions/details`:
```json
{
  "symbol": "AAPL",
  "company_name": "Apple Inc.",  // Previously missing for many symbols
  ...
}
```

Check via audit script:
- Individual portfolio: 0% → >80% company names
- HNW portfolio: 58.6% → >90% company names
- Hedge Fund portfolio: 0% → >80% company names

---

## Rollback Strategy

### If Company Profile Step Breaks Cron Job

#### Option 1: Quick Disable (Comment Out)
```python
# scripts/automation/railway_daily_batch.py

async def main():
    # ...

    # Step 1: Sync market data
    market_data_result = await sync_market_data_step()

    # Step 1.5: Sync company profiles
    # DISABLED 2025-10-XX: Causing cron failures, needs investigation
    # profile_result = await sync_company_profiles_step()
    profile_result = {"status": "skipped", "duration_seconds": 0}

    # Step 2: Run batch calculations
    batch_results = await run_batch_calculations_step()

    # ...
```

Commit, push, verify next cron run succeeds without profiles.

#### Option 2: Git Revert
```bash
# Revert to previous working commit
git revert HEAD
git push origin main

# Railway auto-deploys previous version
# Verify cron job runs successfully
```

#### Option 3: Railway Rollback
```bash
# Via Railway Dashboard
# Project → sigmasight-backend-cron → Deployments
# Find previous working deployment
# Click "Redeploy"
```

### If Partial Failures Acceptable
Company profile sync is designed to be non-blocking:
- Partial failures (e.g., 60/75 symbols succeed) still mark step as "success"
- Only complete catastrophic failure (all symbols fail) marks step as "error"
- Even in error state, batch calculations still proceed
- No rollback needed unless profiles cause actual cron job crashes

---

## Future Enhancements (Out of Scope for Phase 9)

### Weekly Deep Sync
Run comprehensive profile refresh weekly (not daily):
- Create separate Railway cron service: `sigmasight-backend-weekly`
- Schedule: `0 3 * * 0` (Sunday 3 AM UTC)
- Fetch additional data: historical financials, news, analyst upgrades
- Longer timeout, more API calls allowed

### Intelligent Refresh Logic
Only fetch profiles that are stale:
- Track `last_updated` timestamp in `company_profiles` table
- Skip symbols updated within last 7 days
- Prioritize symbols with NULL company_name
- Reduces API calls, improves efficiency

### Profile Data API Endpoint
Expose full company profiles via API:
```
GET /api/v1/data/company-profiles/{symbol}
```
Returns full 70+ field profile for frontend display.

### Alerting on High Failure Rates
Add Slack/email alerts when >20% of symbols fail:
- Already has logging in place
- Add webhook call to `_send_batch_alert()` equivalent
- See TODO4.md blocker #5 for implementation approach

---

## Related Documentation

- **Current Cron System**: `scripts/automation/README.md`
- **Company Profile Architecture**: See previous analysis in this conversation
- **Batch Orchestrator**: `app/batch/batch_orchestrator_v2.py`
- **APScheduler (Dormant)**: `app/batch/scheduler_config.py`
- **Market Data Sync**: `app/batch/market_data_sync.py`
- **Profile Fetcher**: `app/services/yahooquery_profile_fetcher.py`

---

## Approval & Sign-Off

**Prepared By**: Claude (AI Agent)
**Date**: 2025-10-07
**Status**: Awaiting approval

**Approved By**: _________________
**Date**: _________________

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-10-07 | 1.0 | Claude | Initial plan created |

