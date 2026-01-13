# Batch Processing Debug Analysis & Fix Plan

**Date**: January 7, 2026
**Issue**: Batch processing fails for new user "Testscotty" - factor analysis and stress testing not completing
**Error**: `Task was destroyed but it is pending! task: <Task pending name='Task-5' coro=<Connection._cancel()...>`

---

## Executive Summary

**Multiple issues identified** that affect batch processing reliability:

1. **PRIMARY ISSUE - Phase 1.5 Skipped**: The admin-triggered batch endpoint (`run_daily_batch_sequence`) skips Phase 1.5, which is responsible for adding new symbols to `symbol_universe`. This directly causes missing factor exposures for Testscotty.

2. **Fire-and-Forget Task Warning**: The "Task was destroyed" warning comes from `batch_history_service.py` using `asyncio.create_task()` without awaiting. This causes batch history rows to be dropped and should be fixed.

3. **Pool/Timeout Issues**: The original analysis of pool exhaustion and timeout issues remains valid and should be addressed for system stability.

---

## Issue #1: Phase 1.5 Skipped for Admin-Triggered Batches (PRIMARY)

### Evidence from Database

**Testscotty Portfolio Analysis:**
- Portfolio ID: `98518c7d-ea23-593b-aaed-9c0be7f3a66f`
- Created: 2026-01-07 20:56:52
- 13 positions (all PUBLIC equities)

**Symbol Universe Status:**
| Symbol | In symbol_universe? | Has Factor Exposures? |
|--------|--------------------|-----------------------|
| BIL    | YES                | YES (96 records)      |
| LQD    | YES                | YES (86 records)      |
| VTV    | YES                | YES (86 records)      |
| VUG    | YES                | YES (80 records)      |
| XLV    | YES                | YES (80 records)      |
| GGIPX  | **NO**             | NO                    |
| GINDX  | **NO**             | NO                    |
| GOVT   | **NO**             | NO                    |
| IAU    | **NO**             | NO                    |
| IEFA   | **NO**             | NO                    |
| MUB    | **NO**             | NO                    |
| NEAIX  | **NO**             | NO                    |
| VO     | **NO**             | NO                    |

**8 out of 13 symbols are missing from `symbol_universe`.**

### Code Path Analysis

**Two batch entry points:**

1. **`run_daily_batch_with_backfill`** (cron job via `railway_daily_batch.py`):
   - Runs Phase 1 (Market Data)
   - Runs **Phase 1.5** (Symbol Factors) → calls `ensure_symbols_in_universe()`
   - Runs Phase 1.75 (Symbol Metrics)
   - Then runs Phase 2-6

2. **`run_daily_batch_sequence`** (admin endpoint via `/api/v1/admin/batch/run`):
   - Calls `_run_sequence_with_session()`
   - Runs Phase 0, 1, 2, 2.5, 3, 4, 5, 6
   - **DOES NOT run Phase 1.5 or 1.75**

**Code Reference:**
- `batch_orchestrator.py:281-319` - Phase 1.5 only in `run_daily_batch_with_backfill`
- `batch_orchestrator.py:589-609` - `_run_sequence_with_session` runs Phase 1 but not 1.5

### Impact

When Testscotty was onboarded:
1. Admin triggered batch via `run_daily_batch_sequence`
2. Phase 1 collected market data → prices added to `market_data_cache` ✓
3. **Phase 1.5 never ran** → `ensure_symbols_in_universe()` never called ✗
4. 8 new symbols never added to `symbol_universe` ✗
5. Phase 6 factor analysis couldn't find symbols → no `position_factor_exposures` ✗

### Fix Required

**Baseline (Required):** Add defensive `ensure_symbols_in_universe` call at the start of Phase 6 analytics (`run_all_portfolios_analytics`). This is not optional - it's a safety net that ensures symbols are in the universe regardless of which batch path was used.

**Option A (Recommended):** Modify admin endpoint to call `run_daily_batch_with_backfill(start_date=calc_date, end_date=calc_date, portfolio_ids=...)` instead of `run_daily_batch_sequence`. This ensures admin triggers use the same complete code path as the cron job, including Phase 1.5 and 1.75.

**Option B (Backup):** Update `_run_sequence_with_session` to include Phase 1.5 (symbol factor calculation) and Phase 1.75 (symbol metrics) after Phase 1. This keeps the single-date path separate but adds the missing phases.

---

## Issue #2: Fire-and-Forget Batch History Tasks

### Evidence

The "Task was destroyed but it is pending" warning originates from:
- `batch_history_service.py:44-53` and `124-135`
- Uses `asyncio.create_task()` without awaiting

```python
# batch_history_service.py:46
asyncio.create_task(
    cls._record_batch_start_async(...)
)  # Fire-and-forget - never awaited
```

When `railway_daily_batch.py` exits via `asyncio.run()`, the event loop closes while these tasks are still pending.

### Impact

- Batch history rows may be dropped (not persisted to database)
- Warning messages in logs cause confusion
- Several cron batches show as "running" forever in `batch_run_history`

### Fix Required

Either:
1. Await the batch history tasks properly
2. Use a different pattern for non-critical background writes
3. Add cleanup/await before script exit

---

## Issue #3: Database Pool/Timeout Configuration (Original Analysis)

The original analysis remains valid for system stability:

### 1.1 Error Signature

```
Task was destroyed but it is pending!
task: <Task pending name='Task-5' coro=<Connection._cancel() done,
defined at /app/.venv/lib/python3.11/site-packages/asyncpg/connection.py:1643>
wait_for=<Future pending cb=[BaseSelectorEventLoop._sock_write_done(...)]>>
```

**What this means**: An asyncpg database connection was being cancelled (`Connection._cancel()`) when the Python event loop was shut down or the task was destroyed. The cancellation didn't complete before the task was garbage collected.

### 1.2 Root Causes Identified

#### Issue #1: Database Pool Timeout Too Short

**Location**: `backend/app/database.py:21-30`

```python
core_engine = create_async_engine(
    settings.core_database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=20,        # 20 base connections
    max_overflow=20,     # 20 additional connections
    pool_timeout=30,     # <<<< ONLY 30 SECONDS!
    pool_recycle=1800,
)
```

**Problem**:
- Batch processing takes 2-5+ minutes total
- Stress testing alone can take 60+ seconds per portfolio
- If all 40 connections are busy, new operations wait 30 seconds then **timeout silently**
- Phase 6 analytics (factor analysis, stress testing) are the longest-running operations

**Impact**: When pool is exhausted, new database operations fail after 30 seconds, causing incomplete analytics.

---

#### Issue #2: BackgroundTasks + Session Lifecycle

**Location**: `backend/app/api/v1/endpoints/admin_batch.py:85-93`

```python
@router.post("/run")
async def run_batch_processing(
    background_tasks: BackgroundTasks,
    ...
):
    # ...
    background_tasks.add_task(
        batch_orchestrator.run_daily_batch_sequence,
        calculation_date,
        [portfolio_id] if portfolio_id else None,
        None,  # <<<< db is None - batch creates its own session
        None,
        None,
        False
    )
```

**Problem**:
- FastAPI's `BackgroundTasks` closes the request session before the background task runs
- Batch orchestrator creates a new session (line 487 in batch_orchestrator.py)
- If previous batch left connections in bad state, new session acquisition fails

**Flow**:
1. Admin triggers batch via `/api/v1/admin/batch/run`
2. Request returns immediately with batch_run_id
3. Background task starts, creates new `AsyncSessionLocal()` session
4. If pool is corrupted/exhausted from previous failed batch, this fails

---

#### Issue #3: Railway Container/Process Timeout

**Problem**:
- Railway has implicit timeouts for long-running processes
- When batch exceeds this limit (typically 5-10 minutes), the process is killed
- Python tasks are cancelled abruptly without cleanup
- Asyncpg connections left mid-query with pending `_cancel()` operations

**Evidence**: The error shows `Connection._cancel()` in pending state - this happens when a query is interrupted mid-execution.

---

#### Issue #4: No Cancellation Error Handling

**Location**: `backend/app/batch/batch_orchestrator.py:484-505`

```python
async def run_daily_batch_sequence(self, ...):
    try:
        if db is None:
            analytics_runner.reset_caches()
            self._sector_analysis_target_date = calculation_date
            async with AsyncSessionLocal() as session:
                result = await self._run_sequence_with_session(...)
                # <<<< If cancelled here, no cleanup happens
        # ...
    finally:
        batch_run_tracker.complete()
        # ...
```

**Problem**: No `except asyncio.CancelledError` handler to:
1. Explicitly rollback the session
2. Clean up any held resources
3. Log the cancellation for debugging

---

#### Issue #5: Sequential Analytics Processing

**Location**: `backend/app/batch/analytics_runner.py:217-261`

```python
# Run analytics sequentially (single session for all jobs)
for job_name, job_func in analytics_jobs:
    try:
        raw_result = await job_func(db, portfolio_id, calculation_date)
        # ...
    except Exception as e:
        # Exception caught, job marked as failed
        logger.error(f"FAIL {job_name} error: {e}")

# Commit AFTER all analytics
await db.commit()  # <<<< If this fails, ALL results are rolled back
```

**Problem**:
- All analytics jobs share one session
- Stress testing (`analytics_runner.py:798-879`) can take 60+ seconds
- If one job times out or fails, commit at the end rolls back everything
- Connection held for entire duration, contributing to pool exhaustion

---

### 1.3 Why Testscotty Specifically Fails

**Timeline of batch execution**:

| Phase | Duration | Status | Notes |
|-------|----------|--------|-------|
| Phase 0: Company Profiles | ~10s | Success | Quick API calls |
| Phase 1: Market Data | ~30-60s | Success | YFinance data fetch |
| Phase 1.5: Symbol Factors | ~20s | Success | Factor pre-computation |
| Phase 2: Fundamentals | ~10s | Success | Current date only |
| Phase 2.5: Position Values | ~5s | Success | Market value updates |
| Phase 3: P&L & Snapshots | ~30s | Success | Snapshot creation |
| Phase 4: Position Updates | ~10s | Success | Quick updates |
| Phase 5: Sector Tags | ~5s | Success | Tag restoration |
| Phase 6: Analytics | **60-120s** | **FAILS** | Pool exhausted or timeout |

**Why Phase 6 fails**:
1. By the time Phase 6 starts, ~2 minutes have elapsed
2. Previous phases may have held connections without releasing promptly
3. Stress testing starts but:
   - Either pool is exhausted (30s timeout hit)
   - Or Railway timeout kills the process
4. Connection left in pending cancel state
5. Subsequent manual cron run tries to use corrupted pool

---

## 2. Implementation Plan

### 2.1 Priority 1: Increase Pool Timeout (Quick Fix)

**File**: `backend/app/database.py`

**Change**:
```python
# BEFORE
pool_timeout=30,

# AFTER
pool_timeout=120,  # 2 minutes for batch operations
```

**Rationale**: Gives long-running analytics operations time to acquire connections instead of failing after 30 seconds.

---

### 2.2 Priority 2: Add Cancellation Handling

**File**: `backend/app/batch/batch_orchestrator.py`

**Change** (around line 484):
```python
async def run_daily_batch_sequence(self, ...):
    start_time = asyncio.get_event_loop().time()
    result: Dict[str, Any] = {}

    try:
        if db is None:
            analytics_runner.reset_caches()
            self._sector_analysis_target_date = calculation_date
            async with AsyncSessionLocal() as session:
                try:
                    result = await self._run_sequence_with_session(
                        session,
                        calculation_date,
                        normalized_portfolio_ids,
                        bool(run_sector_analysis),
                        price_cache,
                        force_onboarding,
                    )
                except asyncio.CancelledError:
                    logger.warning(f"Batch cancelled, rolling back session")
                    await session.rollback()
                    raise  # Re-raise to propagate cancellation
        else:
            try:
                result = await self._run_sequence_with_session(...)
            except asyncio.CancelledError:
                logger.warning(f"Batch cancelled with external session")
                await db.rollback()
                raise
        return result
    finally:
        # ... existing cleanup code
```

**Rationale**: Ensures database connections are properly cleaned up when tasks are cancelled.

---

### 2.3 Priority 3: Add Timeout to Long-Running Analytics

**File**: `backend/app/batch/analytics_runner.py`

**Change** (around line 798):
```python
async def _calculate_stress_testing(
    self,
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """Run comprehensive stress test with timeout protection"""
    try:
        from app.calculations.stress_testing import (
            run_comprehensive_stress_test,
            save_stress_test_results
        )
        import asyncio

        logger.info(f"Starting stress test for portfolio {portfolio_id}")

        # Add timeout to prevent indefinite hanging
        try:
            stress_results = await asyncio.wait_for(
                run_comprehensive_stress_test(
                    db=db,
                    portfolio_id=portfolio_id,
                    calculation_date=calculation_date
                ),
                timeout=90.0  # 90 second timeout for stress testing
            )
        except asyncio.TimeoutError:
            logger.warning(f"Stress test timed out for portfolio {portfolio_id}")
            return {
                'success': False,
                'message': 'Stress testing timed out after 90 seconds',
            }

        # ... rest of existing code
```

**Rationale**: Prevents stress testing from hanging indefinitely and blocking other operations.

---

### 2.4 Priority 4: Check Railway Configuration

**Action**: Review Railway deployment settings for:

1. **Container timeout settings** - Increase if configurable
2. **Health check configuration** - Ensure long-running processes aren't killed
3. **Memory limits** - Ensure batch processing has adequate memory

**Railway Dashboard Check**:
- Go to Railway dashboard > SigmaSight Backend service
- Check "Settings" > "Deploy" section
- Look for timeout or health check settings

---

### 2.5 Priority 5: Add Connection Pool Health Monitoring

**New File**: `backend/app/core/db_health.py`

```python
"""Database connection pool health monitoring"""
from app.database import core_engine
from app.core.logging import get_logger

logger = get_logger(__name__)

async def log_pool_status():
    """Log current connection pool status for debugging"""
    pool = core_engine.pool
    logger.info(
        f"DB Pool Status: "
        f"size={pool.size()}, "
        f"checkedin={pool.checkedin()}, "
        f"checkedout={pool.checkedout()}, "
        f"overflow={pool.overflow()}"
    )

async def reset_pool_if_needed():
    """Reset connection pool if in bad state"""
    pool = core_engine.pool

    # If all connections are checked out and overflow is maxed, pool is likely stuck
    if pool.checkedout() >= pool.size() + pool.overflow():
        logger.warning("Connection pool appears exhausted, disposing engine")
        await core_engine.dispose()
        logger.info("Engine disposed, new connections will be created")
```

**Usage**: Call before manual batch runs to ensure clean pool state.

---

## 3. Testing Plan

### 3.1 After Implementing Fixes

1. **Deploy fixes to Railway**
2. **Reset connection pool**:
   ```bash
   railway run python -c "
   import asyncio
   from app.database import core_engine
   asyncio.run(core_engine.dispose())
   print('Pool reset')
   "
   ```
3. **Re-run batch for Testscotty**:
   - Via admin dashboard: `/api/v1/admin/batch/run?portfolio_id=<testscotty_portfolio_id>`
   - Monitor logs for Phase 6 completion
4. **Verify analytics data**:
   - Check factor exposures populated
   - Check stress test results saved
   - Check correlation matrix available

### 3.2 Success Criteria

- [ ] Batch completes all 7 phases without errors
- [ ] No "Task was destroyed" errors in logs
- [ ] Factor analysis data present in database
- [ ] Stress test results saved
- [ ] Correlation matrix available via API

---

## 4. Files to Modify

| File | Change | Priority |
|------|--------|----------|
| `backend/app/database.py` | Increase `pool_timeout` to 120s | P1 |
| `backend/app/batch/batch_orchestrator.py` | Add `asyncio.CancelledError` handling | P2 |
| `backend/app/batch/analytics_runner.py` | Add timeout to stress testing | P3 |
| Railway Dashboard | Check timeout settings | P4 |
| `backend/app/core/db_health.py` (new) | Pool health monitoring | P5 |

---

## 5. Rollback Plan

If fixes cause issues:

1. **Revert pool_timeout**: Change back to 30 if causing other issues
2. **Remove timeout wrapper**: If stress testing timeout causes false failures
3. **Railway settings**: Restore previous configuration

---

## 6. Long-Term Recommendations

1. **Consider connection pooling service**: PgBouncer for Railway deployment
2. **Implement batch job queue**: Redis-based queue with proper timeout handling
3. **Add telemetry**: Track Phase 6 duration and connection pool metrics
4. **Consider chunked analytics**: Run analytics per-portfolio with commits between

---

## Appendix: Key Code References

- **Database config**: `backend/app/database.py:21-30`
- **Admin batch endpoint**: `backend/app/api/v1/endpoints/admin_batch.py:45-102`
- **Batch orchestrator entry**: `backend/app/batch/batch_orchestrator.py:480-525`
- **Analytics runner**: `backend/app/batch/analytics_runner.py:798-879`
- **Stress testing calc**: `backend/app/calculations/stress_testing.py`
