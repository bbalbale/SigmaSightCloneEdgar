# 20: Critical Integration Gaps & Solutions

## Overview

This document addresses critical integration gaps identified during architecture review. Each section maps to specific existing code that must be updated or disabled for V2 to work correctly.

---

## Issue 1: Onboarding Status `not_found` Responses

### Current Behavior

**Frontend** (`frontend/src/hooks/useOnboardingStatus.ts:64-72`):
- Polls `/onboarding/status/{portfolio_id}` every 2 seconds
- Tracks consecutive `not_found` responses
- Shows "Status Unavailable" after 5 consecutive `not_found` AND 10s grace period
- Expects to see `running` → `completed` progression

**Backend** (`app/api/v1/onboarding/status.py`):
- Returns `not_found` when no batch is running
- Returns `running` with phase progress during batch
- Returns `completed`/`partial`/`failed` after batch

### Problem

V2 instant onboarding always returns `completed` immediately. Frontend will see:
1. First poll: `completed`
2. User sees flash of loading → instant redirect
3. UX is jarring (no progress animation)

### Solution: Coordinated Frontend + Backend Changes

**Option A: Skip Progress Page Entirely (Recommended)**

```typescript
// frontend/app/onboarding/upload/page.tsx
// After CSV upload completes successfully:

if (settings.batch_v2_enabled) {
  // V2: Snapshot already created, skip progress page
  router.push('/portfolio')
} else {
  // V1: Show progress page with polling
  router.push(`/onboarding/progress?portfolio_id=${portfolioId}`)
}
```

**Option B: Frontend Detects V2 Mode**

```typescript
// frontend/src/hooks/useOnboardingStatus.ts

export function useOnboardingStatus(options: UseOnboardingStatusOptions) {
  // ...existing code...

  const fetchStatus = useCallback(async () => {
    const response = await onboardingService.getOnboardingStatus(portfolioId)

    // V2 detection: If first response is "completed", we're in instant mode
    if (response.status === 'completed' && !hasSeenRunning && notFoundCount === 0) {
      // V2 instant onboarding - treat as immediate success
      setStatus(response)
      setIsV2InstantMode(true)  // New state
      return
    }
    // ...existing polling logic for V1...
  }, [...])

  return {
    ...existingReturn,
    isV2InstantMode,  // Frontend can use this to skip animations
  }
}
```

**Backend: Return V2 indicator**

```python
# backend/app/api/v1/onboarding/status.py

@router.get("/{portfolio_id}")
async def get_onboarding_status(portfolio_id: UUID, ...):
    if settings.batch_v2_enabled:
        # V2: Check if snapshot exists (instant completion)
        snapshot = await get_latest_snapshot(db, portfolio_id)
        if snapshot:
            return OnboardingStatusResponse(
                status="completed",
                progress=100,
                mode="v2_instant",  # NEW: Frontend can detect this
                message="Portfolio ready (instant mode)"
            )

    # V1: Existing batch status polling logic
    ...
```

---

## Issue 2: Coexisting Schedulers Will Double-Run

### Current Schedulers

**1. APScheduler** (`backend/app/batch/scheduler_config.py:57-153`):
- Runs at 4:00 PM ET: `_run_daily_batch` → `batch_orchestrator.run_daily_batch_with_backfill()`
- Runs at 6:00 PM ET: `_run_daily_correlations`
- Runs at 7:00 PM ET: `_sync_company_profiles`
- Runs at 7:30 PM ET: `_verify_market_data`
- Runs at 8:00 PM ET: `_run_feedback_learning`

**2. Railway Cron** (`scripts/automation/railway_daily_batch.py`):
- Currently runs `batch_orchestrator.run_daily_batch_with_backfill()`
- Scheduled via Railway dashboard

**V2 Proposes**:
- 9:00 PM ET: Symbol batch
- 9:30 PM ET: Portfolio refresh

### Problem

Without disabling old schedulers:
- 4 PM: APScheduler runs V1 batch
- 9 PM: V2 symbol batch runs
- 9:30 PM: V2 portfolio refresh runs
- **Result**: Duplicate snapshots, wasted API calls, data corruption

### Solution: Conditional Scheduler Initialization

```python
# backend/app/batch/scheduler_config.py

class BatchScheduler:
    def initialize_jobs(self):
        """Initialize scheduled batch jobs based on V2 flag."""
        from app.config import settings

        self.scheduler.remove_all_jobs()

        if settings.batch_v2_enabled:
            # V2 MODE: Only non-batch jobs run via APScheduler
            # Symbol batch and portfolio refresh run via Railway cron
            logger.info("V2 mode: Skipping batch jobs, using Railway cron")

            # Keep feedback learning (doesn't conflict)
            self.scheduler.add_job(
                func=self._run_feedback_learning,
                trigger='cron',
                hour=20, minute=0,
                id='feedback_learning',
                name='Daily Feedback Learning Analysis',
                replace_existing=True
            )

            # Keep admin metrics
            self.scheduler.add_job(
                func=self._run_admin_metrics_batch,
                trigger='cron',
                hour=20, minute=30,
                id='admin_metrics_batch',
                name='Daily Admin Metrics Aggregation',
                replace_existing=True
            )

        else:
            # V1 MODE: All existing jobs (unchanged)
            self._initialize_v1_jobs()

        logger.info(f"Batch jobs initialized (V2={settings.batch_v2_enabled})")


# scripts/automation/railway_daily_batch.py
async def main():
    """Railway cron entry point."""
    from app.config import settings

    if settings.batch_v2_enabled:
        # V2: This script should NOT run - use separate V2 scripts
        logger.error("BATCH_V2_ENABLED=true but railway_daily_batch.py was called!")
        logger.error("Railway should call run_symbol_batch.py and run_portfolio_refresh.py instead")
        sys.exit(1)

    # V1: Run legacy batch orchestrator
    await batch_orchestrator.run_daily_batch_with_backfill()
```

**Railway Cron Configuration**:

```json
{
  "crons": [
    {
      "name": "v1-daily-batch",
      "schedule": "0 21 * * 1-5",
      "command": "python scripts/automation/railway_daily_batch.py",
      "enabled": "{{ BATCH_V2_ENABLED != 'true' }}"
    },
    {
      "name": "v2-symbol-batch",
      "schedule": "0 2 * * 1-5",
      "command": "python scripts/batch_processing/run_symbol_batch.py",
      "enabled": "{{ BATCH_V2_ENABLED == 'true' }}"
    },
    {
      "name": "v2-portfolio-refresh",
      "schedule": "30 2 * * 1-5",
      "command": "python scripts/batch_processing/run_portfolio_refresh.py",
      "enabled": "{{ BATCH_V2_ENABLED == 'true' }}"
    }
  ]
}
```

**Note**: If Railway doesn't support conditional crons, use a wrapper script:

```python
# scripts/batch_processing/railway_batch_router.py
async def main():
    """Routes to V1 or V2 based on config."""
    from app.config import settings

    if settings.batch_v2_enabled:
        from app.batch.v2.symbol_batch_runner import run_symbol_batch
        await run_symbol_batch()
    else:
        await batch_orchestrator.run_daily_batch_with_backfill()
```

---

## Issue 3: Symbol Batch Must Support Backfill

### Current V1 Behavior

`batch_orchestrator.run_daily_batch_with_backfill()` (`batch_orchestrator.py:85-306`):
- Finds `last_run_date` via `_get_last_batch_run_date()` (min watermark)
- Gets all trading days between `last_run_date + 1` and `target_date`
- Processes ALL missing dates in sequence

### V2 Plan Gap

Document `04-SYMBOL-BATCH-RUNNER.md` only describes single-day runs:
```python
async def run_symbol_batch(target_date: date = None):
    target_date = target_date or get_effective_trading_date()
    # ... process single date ...
```

### Problem

If symbol batch fails Monday night:
- Tuesday: No symbol data for Monday
- Portfolio refresh Tuesday: Creates Tuesday snapshot, but Monday is missing
- **Permanent gap** in historical data

### Solution: Symbol Batch with Backfill

```python
# backend/app/batch/v2/symbol_batch_runner.py

async def run_symbol_batch(
    target_date: date = None,
    backfill: bool = True  # NEW: Default to backfill mode
) -> Dict[str, Any]:
    """
    Run symbol batch with optional backfill for missed dates.

    Args:
        target_date: End date to process (defaults to today)
        backfill: If True, find and process all missed dates since last run
    """
    target_date = target_date or get_effective_trading_date()

    if backfill:
        # Find last successful symbol batch date
        last_run = await get_last_symbol_batch_date()

        if last_run:
            # Get all trading days between last_run + 1 and target_date
            missing_dates = get_trading_days_between(
                start_date=last_run + timedelta(days=1),
                end_date=target_date
            )
        else:
            # First run ever - just process target_date
            missing_dates = [target_date]

        logger.info(f"Symbol batch backfill: {len(missing_dates)} dates to process")

        # Process each missing date
        results = []
        for calc_date in missing_dates:
            result = await _run_symbol_batch_for_date(calc_date)
            results.append(result)

            # Record completion for this date
            await record_symbol_batch_completion(calc_date, result)

        return {
            "success": all(r.get("success") for r in results),
            "dates_processed": len(results),
            "results": results
        }

    else:
        # Single date mode (for manual runs)
        result = await _run_symbol_batch_for_date(target_date)
        await record_symbol_batch_completion(target_date, result)
        return result


async def get_last_symbol_batch_date() -> Optional[date]:
    """Get the most recent successful symbol batch date."""
    async with get_async_session() as db:
        result = await db.execute(
            select(func.max(BatchRunTracking.batch_date))
            .where(
                and_(
                    BatchRunTracking.batch_type == 'symbol_batch',
                    BatchRunTracking.status == 'completed'
                )
            )
        )
        return result.scalar()
```

---

## Issue 4: Analytics Services Read from DB

### Current Analytics Architecture

**FactorExposureService** (`backend/app/services/factor_exposure_service.py`):
- Reads from `FactorExposure` table (portfolio-level)
- Reads from `PositionFactorExposure` table (position-level)
- Uses `FactorDefinition` for factor metadata

**StressTestService** (`backend/app/services/stress_test_service.py`):
- Reads from `StressTestResult` table
- Uses factor exposures for scenario calculations

**CorrelationService** (`backend/app/services/correlation_service.py`):
- Reads from `CorrelationCalculation` table

### Problem

V2 proposes computing analytics on-demand from cache. But:
- All existing services query specific DB tables
- These tables are populated by `analytics_runner` in V1 batch
- Switching to cache breaks all services without rewrite

### Solution: Hybrid Approach - Cache Feeds DB

**Key Insight**: Don't rewrite analytics services. Instead, make symbol batch write to BOTH cache AND existing DB tables.

```python
# backend/app/batch/v2/symbol_batch_runner.py

async def _run_factor_phase(symbols: List[str], target_date: date):
    """Calculate and store factor exposures."""

    for symbol in symbols:
        factors = await calculate_symbol_factors(symbol, target_date)

        # 1. Write to cache (for fast reads)
        symbol_cache.set_factors(symbol, factors)

        # 2. Write to DB (for analytics services compatibility)
        await upsert_symbol_factor_exposure(
            db=db,
            symbol=symbol,
            calculation_date=target_date,
            market_beta=factors.market_beta,
            ir_beta=factors.ir_beta,
            momentum=factors.momentum,
            # ... other factors ...
        )


# backend/app/batch/v2/portfolio_refresh_runner.py

async def create_portfolio_snapshot(portfolio_id: UUID, target_date: date):
    """Create snapshot AND populate factor exposure tables."""

    # 1. Create snapshot (existing logic)
    snapshot = await _create_snapshot_from_cache(portfolio_id, target_date)

    # 2. Aggregate symbol factors to portfolio level
    portfolio_factors = await aggregate_portfolio_factors(portfolio_id, target_date)

    # 3. Write to FactorExposure table (for FactorExposureService compatibility)
    for factor_id, beta_value in portfolio_factors.items():
        await upsert_factor_exposure(
            db=db,
            portfolio_id=portfolio_id,
            factor_id=factor_id,
            calculation_date=target_date,
            beta=beta_value
        )

    # 4. Write to PositionFactorExposure table
    positions = await get_active_positions(db, portfolio_id)
    for pos in positions:
        symbol_factors = symbol_cache.get_factors(pos.symbol)
        if symbol_factors:
            await upsert_position_factor_exposure(
                db=db,
                position_id=pos.id,
                calculation_date=target_date,
                **symbol_factors.__dict__
            )
```

**Result**:
- Analytics services continue reading from DB (no changes needed)
- Cache provides fast reads during onboarding
- Both paths use same underlying data

---

## Issue 5: P&L Calculation Complexity

### Current PnLCalculator

`backend/app/batch/pnl_calculator.py` handles:
- Equity rollforward from previous snapshot
- Mark-to-market P&L with proper sign handling
- Position-level multipliers (options: 100x)
- Exit dates (excluded from calculations)
- Cost basis tracking
- Snapshot idempotency (lock slot first)

### V2 Pseudocode Gap

Portfolio refresh pseudocode uses simple `price * quantity`:
```python
total_value = sum(position.quantity * get_cached_price(position.symbol))
```

### Problem

This ignores:
- Options contract multiplier (100 shares per contract)
- Positions with exit dates (should be excluded)
- Equity rollforward logic
- Cost basis for P&L calculation
- Snapshot slot locking (idempotency)

### Solution: Reuse PnLCalculator

```python
# backend/app/batch/v2/portfolio_refresh_runner.py

from app.batch.pnl_calculator import pnl_calculator

async def create_portfolio_snapshot(
    portfolio_id: UUID,
    target_date: date,
    price_cache: PriceCache
) -> PortfolioSnapshot:
    """
    Create snapshot using existing PnLCalculator.

    The PnLCalculator handles all complexity:
    - Equity rollforward
    - Options multipliers
    - Exit date exclusion
    - Snapshot idempotency

    We just pass our price cache to avoid live API calls.
    """
    # Use existing PnLCalculator with our cache
    result = await pnl_calculator.calculate_portfolio_pnl(
        portfolio_id=portfolio_id,
        calculation_date=target_date,
        db=db,
        price_cache=price_cache  # Pass V2 cache instead of live prices
    )

    return result
```

**Key Change**: PnLCalculator already accepts a `price_cache` parameter. V2 just needs to populate that cache from `market_data_cache` before calling.

---

## Issue 6: Batch Tracker Single-Run Limitation

### Current Behavior

`batch_run_tracker` (`backend/app/batch/batch_run_tracker.py`):
- Stores ONE `CurrentBatchRun` at a time
- `start()` replaces any existing run
- `get_current()` returns single run or None

`batch_trigger_service.check_batch_running()`:
- Returns True if ANY batch is running
- Used to prevent concurrent runs

### Problem

V2 can have running simultaneously:
1. Symbol batch (cron)
2. Portfolio refresh (cron, waiting for symbol batch)
3. Symbol onboarding (user-triggered, multiple users)

All would fight for the single tracker slot.

### Solution: Multi-Job Batch Tracker

```python
# backend/app/batch/batch_run_tracker.py

from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class BatchJobType(Enum):
    SYMBOL_BATCH = "symbol_batch"
    PORTFOLIO_REFRESH = "portfolio_refresh"
    SYMBOL_ONBOARDING = "symbol_onboarding"
    LEGACY_BATCH = "legacy_batch"  # V1 compatibility


@dataclass
class BatchJob:
    job_id: str
    job_type: BatchJobType
    started_at: datetime
    triggered_by: str
    status: str = "running"
    phases: Dict = field(default_factory=dict)
    activity_log: List = field(default_factory=list)


class BatchRunTracker:
    """
    Multi-job batch tracker for V2.

    Supports concurrent jobs of different types while preventing
    duplicate jobs of the same type.
    """

    def __init__(self):
        self._jobs: Dict[BatchJobType, BatchJob] = {}
        self._lock = asyncio.Lock()

    async def start_job(self, job: BatchJob) -> bool:
        """
        Start a new job of given type.

        Returns False if job of same type is already running.
        """
        async with self._lock:
            existing = self._jobs.get(job.job_type)

            if existing and existing.status == "running":
                logger.warning(f"Job type {job.job_type} already running: {existing.job_id}")
                return False

            self._jobs[job.job_type] = job
            logger.info(f"Started job {job.job_id} ({job.job_type})")
            return True

    async def complete_job(self, job_type: BatchJobType, status: str = "completed"):
        """Mark job as complete."""
        async with self._lock:
            if job_type in self._jobs:
                self._jobs[job_type].status = status

    def get_job(self, job_type: BatchJobType) -> Optional[BatchJob]:
        """Get current job of given type."""
        return self._jobs.get(job_type)

    def is_running(self, job_type: BatchJobType) -> bool:
        """Check if job type is currently running."""
        job = self._jobs.get(job_type)
        return job is not None and job.status == "running"

    def get_all_running(self) -> List[BatchJob]:
        """Get all currently running jobs."""
        return [j for j in self._jobs.values() if j.status == "running"]

    # V1 Compatibility
    def start(self, run: CurrentBatchRun):
        """V1 compatibility - wraps as LEGACY_BATCH job."""
        job = BatchJob(
            job_id=run.batch_run_id,
            job_type=BatchJobType.LEGACY_BATCH,
            started_at=run.started_at,
            triggered_by=run.triggered_by
        )
        asyncio.create_task(self.start_job(job))

    def get_current(self) -> Optional[CurrentBatchRun]:
        """V1 compatibility - returns legacy job if running."""
        job = self._jobs.get(BatchJobType.LEGACY_BATCH)
        if job and job.status == "running":
            return CurrentBatchRun(
                batch_run_id=job.job_id,
                started_at=job.started_at,
                triggered_by=job.triggered_by
            )
        return None


# Update batch_trigger_service.py
class BatchTriggerService:
    @staticmethod
    async def check_batch_running(job_type: BatchJobType = None) -> bool:
        """
        Check if batch is running.

        Args:
            job_type: Specific job type to check. If None, checks any job.
        """
        if job_type:
            return batch_run_tracker.is_running(job_type)
        else:
            return len(batch_run_tracker.get_all_running()) > 0
```

---

## Issue 7: In-Memory Queue Lost on Restart

### Problem

Symbol onboarding uses in-memory queue (`07-SYMBOL-ONBOARDING.md`):
```python
class SymbolOnboardingQueue:
    def __init__(self):
        self._jobs: Dict[str, OnboardingJob] = {}  # In-memory!
```

Railway restarts (deploys, scaling) lose all pending jobs.

### Decision: Use In-Memory Queue (Accepted Risk)

After analysis, we choose **in-memory queue** over database-backed:

**Why In-Memory is Acceptable**:
1. Onboarding jobs are short-lived (< 1 minute typically)
2. If Railway restarts mid-job, user simply retries upload
3. `symbol_universe` table tracks which symbols have been processed
4. No new database migrations required (zero new tables principle)
5. Simpler implementation

**Mitigation**:
- `symbol_universe` serves as the "done" list - symbols won't be re-processed
- User can retry failed upload - new symbols will be re-queued
- Jobs complete quickly so restart window is small

### Solution: Simple In-Memory Queue with symbol_universe Tracking

```python
# backend/app/batch/v2/symbol_onboarding.py

@dataclass
class OnboardingJob:
    symbol: str
    portfolio_id: UUID
    user_id: UUID
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)


class SymbolOnboardingQueue:
    """
    In-memory symbol onboarding queue.

    Uses symbol_universe table to track completed symbols.
    If restart occurs, user can retry and only NEW symbols will be queued.
    """

    def __init__(self):
        self._pending: Dict[str, OnboardingJob] = {}
        self._processing: Dict[str, OnboardingJob] = {}

    async def enqueue(self, symbol: str, portfolio_id: UUID, user_id: UUID) -> bool:
        """Add symbol to onboarding queue if not already known."""
        symbol = symbol.upper()

        # Check if symbol already in symbol_universe (already processed)
        if await self._is_symbol_known(symbol):
            logger.debug(f"Symbol {symbol} already known, skipping")
            return False

        # Check if already queued
        if symbol in self._pending or symbol in self._processing:
            logger.debug(f"Symbol {symbol} already queued")
            return False

        self._pending[symbol] = OnboardingJob(symbol, portfolio_id, user_id)
        logger.info(f"Enqueued symbol {symbol} for onboarding")
        return True

    async def _is_symbol_known(self, symbol: str) -> bool:
        """Check if symbol exists in symbol_universe."""
        async with get_async_session() as db:
            result = await db.execute(
                select(SymbolUniverse.symbol)
                .where(SymbolUniverse.symbol == symbol)
            )
            return result.scalar_one_or_none() is not None

    async def process_next(self) -> Optional[str]:
        """Process next pending symbol."""
        if not self._pending:
            return None

        symbol, job = self._pending.popitem()
        job.status = "processing"
        self._processing[symbol] = job

        try:
            await self._process_symbol(symbol)
            job.status = "completed"
            del self._processing[symbol]
            return symbol
        except Exception as e:
            job.status = "failed"
            del self._processing[symbol]
            logger.error(f"Failed to onboard {symbol}: {e}")
            raise

    async def _process_symbol(self, symbol: str):
        """Fetch data and add to symbol_universe."""
        # 1. Fetch prices
        # 2. Calculate factors
        # 3. Add to symbol_universe (marks as "done")
        pass  # Implementation in Step 9
```

---

## Issue 8: Factor Definitions Must Be Seeded

### Current Behavior

`railway_daily_batch.py:58-70` calls `ensure_factor_definitions()` before batch:
```python
async def ensure_factor_definitions():
    """Ensure factor definitions exist before running batch."""
    async with AsyncSessionLocal() as db:
        await seed_factors(db)
        await db.commit()
```

### Problem

V2 symbol batch runner doesn't include this. Factor writes will fail if definitions don't exist.

### Solution: Add to V2 Symbol Batch

```python
# backend/app/batch/v2/symbol_batch_runner.py

from app.db.seed_factors import seed_factors

async def run_symbol_batch(target_date: date = None) -> Dict[str, Any]:
    """Run symbol batch with factor seeding."""

    # CRITICAL: Ensure factor definitions exist before writing exposures
    await ensure_factor_definitions()

    # ... rest of symbol batch ...


async def ensure_factor_definitions():
    """Ensure factor definitions exist (idempotent)."""
    from app.db.seed_factors import seed_factors

    logger.info("Verifying factor definitions...")
    async with get_async_session() as db:
        await seed_factors(db)
        await db.commit()
    logger.info("Factor definitions verified/seeded")
```

---

## Issue 9: Timing Conflicts with APScheduler

### Current APScheduler Jobs

| Time (ET) | Job | Action |
|-----------|-----|--------|
| 4:00 PM | daily_batch_sequence | Full V1 batch |
| 6:00 PM | daily_correlations | Correlation recalc |
| 7:00 PM | company_profile_sync | Company profile API calls |
| 7:30 PM | market_data_verification | Data quality check |
| 8:00 PM | feedback_learning | AI feedback processing |
| 8:30 PM | admin_metrics_batch | Metrics aggregation |

### V2 Proposed Schedule

| Time (ET) | Job | Action |
|-----------|-----|--------|
| 9:00 PM | symbol_batch | Prices + factors for all symbols |
| 9:30 PM | portfolio_refresh | Snapshots for all portfolios |

### Conflict Risks

1. **API Rate Limits**: If 4 PM job runs AND 9 PM job runs, YFinance/Polygon get hit twice
2. **Database Contention**: Both writing to same tables
3. **Resource Exhaustion**: 8 GB Railway limit with multiple jobs

### Solution: Disable V1 Jobs When V2 Enabled

See Issue 2 solution. Additionally:

```python
# backend/app/batch/scheduler_config.py

def initialize_jobs(self):
    """Initialize scheduled batch jobs."""
    from app.config import settings

    self.scheduler.remove_all_jobs()

    if settings.batch_v2_enabled:
        # V2: Only keep non-conflicting jobs
        # Market data, correlations, company profiles handled by V2 crons

        self.scheduler.add_job(
            func=self._run_feedback_learning,
            trigger='cron',
            hour=20, minute=0,
            id='feedback_learning',
            replace_existing=True
        )

        self.scheduler.add_job(
            func=self._run_admin_metrics_batch,
            trigger='cron',
            hour=20, minute=30,
            id='admin_metrics_batch',
            replace_existing=True
        )

        logger.info("V2 mode: Only feedback_learning and admin_metrics_batch scheduled")

    else:
        # V1: All existing jobs
        self._initialize_all_v1_jobs()
```

---

## Issue 10: Fundamentals & Company Profile Migration

### Current V1 Phases

- **Phase 0**: Company profile sync (sector, industry, beta from API)
- **Phase 2**: Fundamental data collection (earnings-driven)

These run BEFORE analytics in V1.

### V2 Gap

Documents don't specify how fundamentals/profiles fit into symbol batch.

### Solution: Include in Symbol Batch

```python
# backend/app/batch/v2/symbol_batch_runner.py

async def run_symbol_batch(target_date: date) -> Dict[str, Any]:
    """
    Complete symbol batch with all data phases.

    Phase order matches V1 for compatibility:
    1. Company profiles (sector, industry, beta from FMP)
    2. Market data (prices from YFinance)
    3. Fundamentals (earnings if due)
    4. Factor calculations
    """

    results = {}

    # Phase 0: Company profiles (only on final date of backfill)
    logger.info("Phase 0: Company profile sync")
    results['company_profiles'] = await sync_company_profiles(target_date)

    # Phase 1: Market data
    logger.info("Phase 1: Market data collection")
    results['market_data'] = await collect_market_data(target_date)

    # Phase 2: Fundamentals (if earnings window)
    logger.info("Phase 2: Fundamental data")
    results['fundamentals'] = await collect_fundamentals_if_due(target_date)

    # Phase 3: Factor calculations
    logger.info("Phase 3: Factor calculations")
    results['factors'] = await calculate_all_factors(target_date)

    # Record completion
    await record_symbol_batch_completion(target_date, results)

    return {
        "success": True,
        "target_date": target_date.isoformat(),
        "phases": results
    }


async def collect_fundamentals_if_due(target_date: date) -> Dict[str, Any]:
    """
    Collect fundamental data if within earnings window.

    Mirrors V1 Phase 2 logic from fundamentals_collector.
    """
    from app.batch.fundamentals_collector import fundamentals_collector

    # Use existing collector - it handles earnings-driven logic
    return await fundamentals_collector.collect_fundamentals(
        calculation_date=target_date,
        days_after_earnings=3  # Same as V1
    )
```

---

## Summary: Files Requiring Changes

| File | Changes Required |
|------|------------------|
| `scheduler_config.py` | V2-aware job initialization |
| `batch_run_tracker.py` | Multi-job support |
| `batch_trigger_service.py` | Job-type-aware checking |
| `railway_daily_batch.py` | V2 mode guard |
| `symbol_batch_runner.py` (NEW) | Backfill support, factor seeding, fundamentals |
| `portfolio_refresh_runner.py` (NEW) | Use PnLCalculator, write to DB tables |
| `symbol_onboarding.py` (NEW) | In-memory queue with symbol_universe tracking |
| `useOnboardingStatus.ts` | V2 instant mode detection |
| `onboarding/status.py` | V2 mode response |

**Note**: Zero new database tables required. V2 uses existing tables:
- `symbol_universe` - tracks known symbols
- `market_data_cache` - stores prices
- `symbol_factor_exposures` - stores factors
- `batch_run_history` - tracks batch completions

---

## Migration Order

1. **Week 1**: Add multi-job tracker, V2 guards in existing code
2. **Week 2**: Create V2 runners with backfill and DB writes
3. **Week 3**: Add in-memory onboarding queue
4. **Week 4**: Deploy with `BATCH_V2_ENABLED=false`, test V2 code paths
5. **Week 5**: Enable V2, monitor closely
6. **Week 6+**: Remove V1 code after stable
