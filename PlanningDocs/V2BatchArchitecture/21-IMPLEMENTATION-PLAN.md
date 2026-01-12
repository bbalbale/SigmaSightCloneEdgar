# 21: Step-by-Step Implementation Plan

## Overview

This document provides a sequential implementation plan for V2 batch architecture. Each step has clear dependencies, files to modify, and acceptance criteria.

**Total Estimated Steps**: 12
**Critical Path**: Steps 1-4 must be completed in order before parallel work begins

---

## Pre-Implementation Checklist

Before starting, verify:

- [ ] `BatchProcessUpdate` branch is up to date with `main`
- [ ] Local development environment working (backend starts, tests pass)
- [ ] Railway staging environment available for testing
- [ ] Understand current batch flow by reading `01-CURRENT-STATE.md`

---

## Phase 1: Foundation (Steps 1-4)

These steps establish the V2 infrastructure without breaking V1 behavior.

**Key Principle**: Zero new database tables - V2 reuses existing tables.

### Step 1: Add V2 Feature Flag

**Goal**: Enable conditional V1/V2 code paths without changing behavior.

**Reference Docs**: `12-OPERATIONAL-TOGGLES.md`

**Files to Modify**:
```
backend/app/config.py                    # Add batch_v2_enabled setting
backend/.env.example                      # Document new env var
```

**Implementation**:
```python
# backend/app/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # V2 Batch Architecture
    batch_v2_enabled: bool = Field(
        default=False,
        env="BATCH_V2_ENABLED",
        description="Enable V2 batch architecture (two-cron, instant onboarding)"
    )
```

**Acceptance Criteria**:
- [ ] `settings.batch_v2_enabled` returns `False` by default
- [ ] Setting `BATCH_V2_ENABLED=true` in `.env` changes value to `True`
- [ ] No behavior change when flag is `False`

**Tests**:
```bash
# Verify default
uv run python -c "from app.config import settings; print(settings.batch_v2_enabled)"
# Should print: False
```

---

### Step 2: Multi-Job Batch Tracker

**Goal**: Replace single-job tracker with multi-job support.

**Reference Docs**: `20-CRITICAL-INTEGRATION-GAPS.md` Section 6

**Files to Modify**:
```
backend/app/batch/batch_run_tracker.py   # Rewrite for multi-job
backend/app/services/batch_trigger_service.py  # Update check_batch_running()
```

**Implementation**:

1. Add `BatchJobType` enum
2. Create `BatchJob` dataclass
3. Rewrite `BatchRunTracker` with `_jobs: Dict[BatchJobType, BatchJob]`
4. Add V1 compatibility wrappers (`start()`, `get_current()`)
5. Update `batch_trigger_service.check_batch_running()` to accept optional job type

**Acceptance Criteria**:
- [ ] Can start multiple jobs of different types concurrently
- [ ] Cannot start two jobs of same type
- [ ] V1 code using `batch_run_tracker.start()` still works
- [ ] V1 code using `batch_run_tracker.get_current()` still works
- [ ] Admin endpoint `/admin/batch/run/current` still works

**Tests**:
```bash
# Run existing batch tests
uv run pytest tests/batch/ -v

# Manual test: Start job, check status, complete job
uv run python -c "
from app.batch.batch_run_tracker import batch_run_tracker, BatchJobType, BatchJob
from datetime import datetime

job = BatchJob(
    job_id='test-123',
    job_type=BatchJobType.SYMBOL_BATCH,
    started_at=datetime.utcnow(),
    triggered_by='test'
)
print('Starting job:', batch_run_tracker.start_job(job))
print('Is running:', batch_run_tracker.is_running(BatchJobType.SYMBOL_BATCH))
print('Get job:', batch_run_tracker.get_job(BatchJobType.SYMBOL_BATCH))
"
```

---

### Step 3: V2 Guards in Existing Schedulers

**Goal**: Prevent V1 batch jobs from running when V2 is enabled.

**Reference Docs**: `20-CRITICAL-INTEGRATION-GAPS.md` Section 2

**Files to Modify**:
```
backend/app/batch/scheduler_config.py         # Conditional job init
backend/scripts/automation/railway_daily_batch.py  # V2 mode guard
```

**Implementation**:

1. In `scheduler_config.py`:
   - Check `settings.batch_v2_enabled` in `initialize_jobs()`
   - If V2: Only schedule non-conflicting jobs (feedback_learning, admin_metrics)
   - If V1: Schedule all existing jobs (unchanged behavior)

2. In `railway_daily_batch.py`:
   - Add guard at start: if V2 enabled, log error and exit
   - This prevents Railway cron from running V1 batch in V2 mode

**Acceptance Criteria**:
- [ ] With `BATCH_V2_ENABLED=false`: All existing jobs scheduled (unchanged)
- [ ] With `BATCH_V2_ENABLED=true`: Only feedback_learning and admin_metrics scheduled
- [ ] Railway daily batch exits with error if V2 enabled
- [ ] Existing tests still pass

**Tests**:
```bash
# Check job count in V1 mode
BATCH_V2_ENABLED=false uv run python -c "
from app.batch.scheduler_config import batch_scheduler
batch_scheduler.initialize_jobs()
print('Jobs:', [j.id for j in batch_scheduler.scheduler.get_jobs()])
"

# Check job count in V2 mode
BATCH_V2_ENABLED=true uv run python -c "
from app.batch.scheduler_config import batch_scheduler
batch_scheduler.initialize_jobs()
print('Jobs:', [j.id for j in batch_scheduler.scheduler.get_jobs()])
"
```

---

### Step 4: Database Schema for V2 - ZERO NEW TABLES

**Goal**: Confirm V2 uses existing tables only. No migrations required.

**Reference Docs**: `03-DATABASE-SCHEMA.md`

**Key Principle**: V2 architecture reuses existing tables to avoid migration complexity.

**Existing Tables Used by V2**:

| Table | V2 Usage |
|-------|----------|
| `symbol_universe` | Track which symbols are in the system |
| `market_data_cache` | Store fetched prices (already exists) |
| `symbol_factor_exposures` | Store calculated factors (already exists) |
| `symbol_daily_metrics` | Store volatility/beta metrics (already exists) |
| `batch_run_history` | Track batch run completions (already exists) |

**Symbol Onboarding**: Uses **in-memory queue** (not database-backed)
- Jobs are short-lived (< 1 minute typically)
- If Railway restarts mid-onboarding, user can retry
- Simpler implementation, no migration needed
- `symbol_universe` tracks which symbols have been processed

**Files to Modify**: None

**Acceptance Criteria**:
- [ ] Confirm no new migrations needed
- [ ] Verify existing tables have required columns
- [ ] Document which existing tables V2 uses

**Verification**:
```bash
# Verify existing tables have required columns
uv run python -c "
from app.models import SymbolUniverse, SymbolFactorExposure, SymbolDailyMetrics, MarketDataCache
print('✅ All required V2 tables already exist')
"
```

---

## Phase 2: Symbol Batch Runner (Steps 5-7)

Can begin after Phase 1 is complete.

### Step 5: Symbol Batch Runner - Core

**Goal**: Create the main symbol batch runner with backfill support.

**Reference Docs**: `04-SYMBOL-BATCH-RUNNER.md`, `20-CRITICAL-INTEGRATION-GAPS.md` Sections 3, 8, 10

**Files to Create**:
```
backend/app/batch/v2/__init__.py
backend/app/batch/v2/symbol_batch_runner.py
backend/scripts/batch_processing/run_symbol_batch.py  # Cron entry point
```

**Implementation Order**:

1. Create `backend/app/batch/v2/` directory
2. Create symbol batch runner with:
   - `run_symbol_batch(target_date, backfill=True)` main function
   - `ensure_factor_definitions()` - seed factors before calculations
   - `get_last_symbol_batch_date()` - find last successful run
   - `_run_symbol_batch_for_date(date)` - process single date
   - `record_symbol_batch_completion(date, result)` - write to BatchRunTracking

3. Create cron entry point script

**Key Logic**:
```python
async def run_symbol_batch(target_date=None, backfill=True):
    target_date = target_date or get_effective_trading_date()

    # Seed factor definitions (critical!)
    await ensure_factor_definitions()

    if backfill:
        last_run = await get_last_symbol_batch_date()
        missing_dates = get_trading_days_between(last_run + 1, target_date)
    else:
        missing_dates = [target_date]

    for calc_date in missing_dates:
        await _run_symbol_batch_for_date(calc_date)
        await record_symbol_batch_completion(calc_date)
```

**Acceptance Criteria**:
- [ ] Can run for single date
- [ ] Backfill mode finds and processes missed dates
- [ ] Factor definitions seeded before calculations
- [ ] Completion recorded to BatchRunTracking table
- [ ] Logs use V2_BATCH_STEP format

**Tests**:
```bash
# Dry run for single date
BATCH_V2_ENABLED=true uv run python -c "
import asyncio
from app.batch.v2.symbol_batch_runner import run_symbol_batch
from datetime import date
result = asyncio.run(run_symbol_batch(date(2026, 1, 10), backfill=False))
print(result)
"
```

---

### Step 6: Symbol Batch - Market Data Phase

**Goal**: Implement price fetching phase of symbol batch.

**Reference Docs**: `04-SYMBOL-BATCH-RUNNER.md`

**Files to Modify**:
```
backend/app/batch/v2/symbol_batch_runner.py   # Add market data phase
```

**Implementation**:

1. Get symbols to process (from positions + universe + factor ETFs)
2. Separate equity symbols from options symbols
3. Fetch equity prices from YFinance (existing `market_data_collector`)
4. Fetch options prices from Polygon (existing provider)
5. Write to `market_data_cache` table
6. Include company profile sync (Phase 0)
7. Include fundamentals collection (Phase 2)

**Key Logic**:
```python
async def _run_symbol_batch_for_date(calc_date):
    symbols = await _get_symbols_to_process()

    # Phase 0: Company profiles (on final date only)
    await sync_company_profiles(calc_date)

    # Phase 1: Market data
    equity_symbols = [s for s in symbols if not is_options_symbol(s)]
    options_symbols = [s for s in symbols if is_options_symbol(s)]

    await fetch_equity_prices(equity_symbols, calc_date)  # YFinance
    await fetch_options_prices(options_symbols, calc_date)  # Polygon

    # Phase 2: Fundamentals (if due)
    await collect_fundamentals_if_due(calc_date)

    # Phase 3: Factors (next step)
    await calculate_all_factors(calc_date)
```

**Acceptance Criteria**:
- [ ] Equity prices fetched from YFinance
- [ ] Options prices fetched from Polygon
- [ ] Company profiles synced
- [ ] Fundamentals collected when earnings window
- [ ] PRIVATE positions excluded (no market prices)
- [ ] Prices written to market_data_cache

---

### Step 7: Symbol Batch - Factor Phase + DB Writes

**Goal**: Implement factor calculation with BOTH cache and DB writes.

**Reference Docs**: `04-SYMBOL-BATCH-RUNNER.md`, `20-CRITICAL-INTEGRATION-GAPS.md` Section 4

**Files to Modify**:
```
backend/app/batch/v2/symbol_batch_runner.py   # Add factor phase
```

**Implementation**:

1. Calculate factors for each equity symbol (skip options)
2. Write to in-memory cache (for fast reads)
3. **ALSO write to DB tables** (for analytics service compatibility):
   - `symbol_factor_exposures` table
   - This ensures `FactorExposureService` continues working

**Key Logic**:
```python
async def calculate_all_factors(calc_date):
    equity_symbols = [s for s in symbols if not is_options_symbol(s)]

    for symbol in equity_symbols:
        factors = await calculate_symbol_factors(symbol, calc_date)

        # Write to cache (fast reads)
        symbol_cache.set_factors(symbol, factors)

        # Write to DB (analytics service compatibility)
        await upsert_symbol_factor_exposure(
            symbol=symbol,
            calculation_date=calc_date,
            market_beta=factors.market_beta,
            ir_beta=factors.ir_beta,
            # ... other factors
        )
```

**Acceptance Criteria**:
- [ ] Factors calculated for equity symbols only
- [ ] Options symbols skipped
- [ ] Factors written to cache
- [ ] Factors written to `symbol_factor_exposures` table
- [ ] Existing analytics endpoints still work

---

## Phase 3: Portfolio Refresh Runner (Steps 8-9)

Can begin after Step 7 is complete.

### Step 8: Portfolio Refresh Runner

**Goal**: Create portfolio refresh runner using existing PnLCalculator.

**Reference Docs**: `05-PORTFOLIO-REFRESH.md`, `20-CRITICAL-INTEGRATION-GAPS.md` Section 5

**Files to Create**:
```
backend/app/batch/v2/portfolio_refresh_runner.py
backend/scripts/batch_processing/run_portfolio_refresh.py  # Cron entry point
```

**Implementation**:

1. Wait for symbol batch completion (poll BatchRunTracking)
2. Wait for pending symbol onboarding (max 2 min)
3. Get portfolios needing snapshots
4. For each portfolio:
   - Check for symbols missing factors → calculate inline
   - **Use existing `PnLCalculator`** with price cache
   - Write factor exposures to DB tables

**Key Logic**:
```python
async def run_portfolio_refresh(target_date=None):
    target_date = target_date or get_effective_trading_date()

    # Wait for symbol batch
    if not await wait_for_symbol_batch(target_date, max_wait=60):
        return {"status": "aborted", "reason": "symbol_batch_timeout"}

    # Wait for pending onboarding
    await wait_for_onboarding_completion(max_wait=120)

    # Load price cache from market_data_cache
    price_cache = await load_price_cache(target_date)

    portfolios = await get_portfolios_needing_snapshots(target_date)

    for portfolio in portfolios:
        # Fill factor gaps
        missing = await get_symbols_missing_factors(portfolio.id)
        if missing:
            await calculate_factors_for_symbols(missing, target_date)

        # Use existing PnLCalculator
        await pnl_calculator.calculate_portfolio_pnl(
            portfolio_id=portfolio.id,
            calculation_date=target_date,
            db=db,
            price_cache=price_cache  # V2 cache!
        )

        # Write portfolio-level factors to DB
        await write_portfolio_factor_exposures(portfolio.id, target_date)
```

**Acceptance Criteria**:
- [ ] Waits for symbol batch completion
- [ ] Waits for pending onboarding jobs
- [ ] Uses existing PnLCalculator (not simplified pseudocode)
- [ ] Handles PRIVATE positions correctly (manual market_value)
- [ ] Writes to FactorExposure table
- [ ] Writes to PositionFactorExposure table
- [ ] Existing analytics endpoints still work

---

### Step 9: Symbol Onboarding Queue (In-Memory)

**Goal**: Implement in-memory symbol onboarding queue for instant processing.

**Reference Docs**: `07-SYMBOL-ONBOARDING.md`

**Files to Create**:
```
backend/app/batch/v2/symbol_onboarding.py
```

**Design Decision**: In-memory queue (not database-backed)
- Jobs are short-lived (< 1 minute typically)
- If Railway restarts mid-job, user simply retries upload
- `symbol_universe` table tracks which symbols have been processed
- Simpler implementation, no migration needed

**Implementation**:

1. `SymbolOnboardingQueue` class with:
   - `_pending: Dict[str, OnboardingJob]` - in-memory job storage
   - `enqueue(symbol, portfolio_id, user_id)` - add to queue
   - `get_pending()` - list pending jobs
   - `process_next()` - process one job
   - `is_symbol_known(symbol)` - check `symbol_universe` table

2. Background worker that processes queue (asyncio task)

3. On symbol completion:
   - Add to `symbol_universe` table
   - Add prices to `market_data_cache`
   - Calculate and store factors in `symbol_factor_exposures`

**Key Logic**:
```python
@dataclass
class OnboardingJob:
    symbol: str
    portfolio_id: UUID
    user_id: UUID
    status: str = "pending"  # pending, processing, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)

class SymbolOnboardingQueue:
    _pending: Dict[str, OnboardingJob] = {}
    _processing: Dict[str, OnboardingJob] = {}

    async def enqueue(self, symbol: str, portfolio_id: UUID, user_id: UUID) -> bool:
        # Check if symbol already known (in symbol_universe)
        if await self.is_symbol_known(symbol):
            return False  # Already processed, skip

        # Check if already queued
        if symbol in self._pending or symbol in self._processing:
            return False  # Already queued

        self._pending[symbol] = OnboardingJob(symbol, portfolio_id, user_id)
        return True

    async def process_next(self) -> Optional[str]:
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
            raise
```

**Acceptance Criteria**:
- [ ] Queue processes jobs in order
- [ ] Duplicate symbols are deduplicated
- [ ] Known symbols (in symbol_universe) are skipped
- [ ] Completed symbols added to symbol_universe
- [ ] Factors calculated and stored in symbol_factor_exposures
- [ ] Prices stored in market_data_cache

---

## Phase 4: Cache & Health (Steps 10-11)

Can run in parallel with Phase 3.

### Step 10: Symbol Cache with Cold Start

**Goal**: Implement in-memory cache with health checks and DB fallback.

**Reference Docs**: `06-PORTFOLIO-CACHE.md`, `19-IMPLEMENTATION-FIXES.md` Section 1

**Files to Create**:
```
backend/app/cache/symbol_cache.py
```

**Files to Modify**:
```
backend/app/api/v1/health.py    # Add /health/ready endpoint
backend/app/main.py             # Background cache init in lifespan
```

**Implementation**:

1. `SymbolCacheService` with:
   - `_initialized`, `_initializing` state tracking
   - `is_ready()` method
   - `get_latest_price(symbol, db=None)` with DB fallback
   - `get_factors(symbol, db=None)` with DB fallback

2. Health endpoints:
   - `/health/live` - always 200 (liveness)
   - `/health/ready` - 503 until cache ready OR 30s timeout (readiness)

3. Background initialization in app lifespan

**Acceptance Criteria**:
- [ ] Cache initializes in background
- [ ] App starts immediately (doesn't block on cache)
- [ ] `/health/live` returns 200 immediately
- [ ] `/health/ready` returns 503 during init, 200 after
- [ ] Analytics work with DB fallback during init
- [ ] Cache methods fall back to DB on miss

---

### Step 11: Frontend V2 Mode Detection

**Goal**: Handle instant onboarding UX in frontend.

**Reference Docs**: `20-CRITICAL-INTEGRATION-GAPS.md` Section 1

**Files to Modify**:
```
backend/app/api/v1/onboarding/status.py           # Add mode field
frontend/src/hooks/useOnboardingStatus.ts         # Detect V2 mode
frontend/app/onboarding/upload/page.tsx           # Skip progress page
```

**Implementation**:

1. Backend: Return `mode: "v2_instant"` when V2 enabled
2. Frontend: Detect V2 mode from first response
3. Frontend: Skip progress page, redirect directly to `/portfolio`

**Acceptance Criteria**:
- [ ] Backend returns `mode` field in onboarding status
- [ ] Frontend detects V2 instant mode
- [ ] V2: Upload → redirect to /portfolio (no progress page)
- [ ] V1: Upload → progress page → redirect (unchanged)

---

## Phase 5: Testing & Deployment (Step 12)

### Step 12: Integration Testing & Rollout

**Goal**: Test V2 end-to-end and deploy.

**Files to Create**:
```
backend/tests/batch/test_v2_symbol_batch.py
backend/tests/batch/test_v2_portfolio_refresh.py
backend/tests/batch/test_v2_integration.py
```

**Testing Checklist**:

1. **Unit Tests**:
   - [ ] Symbol batch runner tests
   - [ ] Portfolio refresh runner tests
   - [ ] Symbol onboarding queue tests
   - [ ] Multi-job tracker tests

2. **Integration Tests** (local):
   - [ ] V1 mode: Full batch still works
   - [ ] V2 mode: Symbol batch → portfolio refresh works
   - [ ] V2 mode: Instant onboarding creates snapshot
   - [ ] Analytics endpoints return correct data

3. **Railway Staging**:
   - [ ] Deploy with `BATCH_V2_ENABLED=false`
   - [ ] Verify V1 behavior unchanged
   - [ ] Set `BATCH_V2_ENABLED=true`
   - [ ] Manually trigger symbol batch
   - [ ] Manually trigger portfolio refresh
   - [ ] Verify analytics endpoints

4. **Production Rollout**:
   - [ ] Deploy code with `BATCH_V2_ENABLED=false`
   - [ ] Monitor for 24h
   - [ ] Set `BATCH_V2_ENABLED=true`
   - [ ] Monitor first nightly run
   - [ ] Monitor for 1 week
   - [ ] Remove V1 code (optional, after stable)

---

## Implementation Order Summary

```
Week 1: Foundation
├── Step 1: V2 Feature Flag .............. [Day 1] ✅
├── Step 2: Multi-Job Batch Tracker ...... [Day 1-2] ✅
├── Step 3: V2 Guards in Schedulers ...... [Day 2] ✅
└── Step 4: Zero New Tables .............. [SKIPPED - uses existing tables] ✅

Week 2: Symbol Batch
├── Step 5: Symbol Batch Core ............ [Day 1-2]
├── Step 6: Market Data Phase ............ [Day 2-3]
└── Step 7: Factor Phase + DB Writes ..... [Day 3-4]

Week 3: Portfolio & Cache (Parallel)
├── Step 8: Portfolio Refresh Runner ..... [Day 1-3]
├── Step 9: Symbol Onboarding (In-Memory). [Day 2-3]
├── Step 10: Symbol Cache + Health ....... [Day 1-2]
└── Step 11: Frontend V2 Mode ............ [Day 3]

Week 4: Testing & Rollout
└── Step 12: Integration Testing ......... [Day 1-5]

Week 5+: Production
├── Deploy with V2=false
├── Enable V2
└── Monitor & iterate
```

---

## Quick Reference: Files by Step

| Step | New Files | Modified Files |
|------|-----------|----------------|
| 1 | - | `config.py`, `.env.example` |
| 2 | - | `batch_run_tracker.py`, `batch_trigger_service.py` |
| 3 | - | `scheduler_config.py`, `railway_daily_batch.py` |
| 4 | - (zero new tables) | - |
| 5 | `batch/v2/__init__.py`, `symbol_batch_runner.py`, `run_symbol_batch.py` | - |
| 6 | - | `symbol_batch_runner.py` |
| 7 | - | `symbol_batch_runner.py` |
| 8 | `portfolio_refresh_runner.py`, `run_portfolio_refresh.py` | - |
| 9 | `batch/v2/symbol_onboarding.py` (in-memory queue) | - |
| 10 | `cache/symbol_cache.py` | `health.py`, `main.py` |
| 11 | - | `onboarding/status.py`, `useOnboardingStatus.ts`, `upload/page.tsx` |
| 12 | `tests/batch/test_v2_*.py` | - |

---

## Rollback Plan

If V2 causes issues in production:

1. Set `BATCH_V2_ENABLED=false` in Railway dashboard
2. Redeploy (automatic on env change)
3. V1 batch resumes on next scheduled run
4. Investigate and fix V2 issues
5. Re-enable when fixed

**Rollback time**: ~3 minutes
