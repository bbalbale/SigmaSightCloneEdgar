# Batch Processing Debug Analysis & Fix Plan

**Date**: January 7-8, 2026
**Issue**: Batch processing fails for new user "Testscotty" - factor analysis and stress testing not completing
**Error**: `Task was destroyed but it is pending! task: <Task pending name='Task-5' coro=<Connection._cancel()...>`
**Updated**: January 8, 2026 - Independent analysis by Claude Opus 4.5

---

## Executive Summary

**Three distinct bugs identified** that affect batch processing reliability:

| # | Bug | Severity | Impact |
|---|-----|----------|--------|
| 1 | **Phase 1.5 Skipped** | CRITICAL | New portfolios missing factor exposures |
| 2 | **Global Watermark Bug** | HIGH | Existing portfolios falling behind on snapshots |
| 3 | **Fire-and-Forget Tasks** | MEDIUM | Batch history records lost, misleading "running" status |

---

## Issue #1: Phase 1.5 Skipped for Admin/Onboarding Batches (CRITICAL)

### Root Cause

The admin dashboard and onboarding flow use `run_daily_batch_sequence()` which **does not run Phase 1.5 or 1.75**. Only the daily cron job uses `run_daily_batch_with_backfill()` which includes these phases.

### Code Path Comparison

| Entry Point | File:Line | Function Called | Phase 1.5? |
|-------------|-----------|-----------------|------------|
| **Onboarding Flow** | `portfolios.py:591-592` | `run_daily_batch_sequence()` | ❌ SKIPPED |
| **Admin Dashboard** | `admin_batch.py:85-86` | `run_daily_batch_sequence()` | ❌ SKIPPED |
| **Batch Trigger Service** | `batch_trigger_service.py:167-168` | `run_daily_batch_sequence()` | ❌ SKIPPED |
| **Daily Cron Job** | `scheduler_config.py:160-161` | `run_daily_batch_with_backfill()` | ✅ RUNS |

### Evidence from Railway Database (Jan 8, 2026)

**Testscotty Portfolio Analysis:**
- Portfolio ID: `98518c7d-ea23-593b-aaed-9c0be7f3a66f`
- Created: 2026-01-07 20:56:52
- 13 positions (all PUBLIC equities)
- Batch triggered by: **"admin"** (not cron)

**Symbol Universe Status:**
| Symbol | In symbol_universe? | Has symbol_factor_exposures? |
|--------|--------------------|-----------------------------|
| BIL    | ✅ YES             | ✅ YES (96 records)         |
| LQD    | ✅ YES             | ✅ YES (86 records)         |
| VTV    | ✅ YES             | ✅ YES (86 records)         |
| VUG    | ✅ YES             | ✅ YES (80 records)         |
| XLV    | ✅ YES             | ✅ YES (80 records)         |
| GGIPX  | ❌ **NO**          | ❌ NO                       |
| GINDX  | ❌ **NO**          | ❌ NO                       |
| GOVT   | ❌ **NO**          | ❌ NO                       |
| IAU    | ❌ **NO**          | ❌ NO                       |
| IEFA   | ❌ **NO**          | ❌ NO                       |
| MUB    | ❌ **NO**          | ❌ NO                       |
| NEAIX  | ❌ **NO**          | ❌ NO                       |
| VO     | ❌ **NO**          | ❌ NO                       |

**8 out of 13 symbols are missing from `symbol_universe`.**
**ALL 13 positions have 0 `position_factor_exposures`.**

### Impact

When a new portfolio is onboarded:
1. Admin/onboarding triggers batch via `run_daily_batch_sequence`
2. Phase 1 collects market data → prices added to `market_data_cache` ✓
3. **Phase 1.5 never runs** → `ensure_symbols_in_universe()` never called ✗
4. New symbols never added to `symbol_universe` ✗
5. Phase 6 factor analysis can't find symbols → no `position_factor_exposures` ✗
6. User sees broken analytics until next daily cron (up to 24h wait)

---

## Issue #2: Global Watermark Bug (HIGH)

### Root Cause

`_get_last_batch_run_date()` uses a **global MAX** query across all portfolios:

```python
# batch_orchestrator.py:1401-1403
query = select(PortfolioSnapshot.snapshot_date).order_by(
    desc(PortfolioSnapshot.snapshot_date)
).limit(1)  # Gets MAX across ALL portfolios, not per-portfolio
```

This assumes all portfolios are always in sync. When you run batch for a single portfolio, it advances the "global watermark" but leaves other portfolios behind.

### Evidence from Railway Database (Jan 8, 2026)

```
Portfolio                        Last Snapshot
──────────────────────────────────────────────
Demo Family Office Private Opp → 2026-01-05  ❌ Missing Jan 6, 7
Demo Family Office Public Grow → 2026-01-05  ❌ Missing Jan 6, 7
Demo Hedge Fund Style Investor → 2026-01-05  ❌ Missing Jan 6, 7
Demo High Net Worth Investor   → 2026-01-05  ❌ Missing Jan 6, 7
Demo Individual Investor       → 2026-01-05  ❌ Missing Jan 6, 7
Equity Balance Portfolio       → 2026-01-05  ❌ Missing Jan 6, 7
Futura Test Portfolio          → 2026-01-05  ❌ Missing Jan 6, 7
JP Morgan Bonds                → 2026-01-05  ❌ Missing Jan 6, 7
Robinhood Growth               → 2026-01-05  ❌ Missing Jan 6, 7
Robinhood Tech                 → 2026-01-05  ❌ Missing Jan 6, 7
Small Test Portfolio           → 2026-01-05  ❌ Missing Jan 6, 7
Tech Growth                    → 2026-01-06  ❌ Missing Jan 7
Test Scott Y Portfolio         → 2026-01-07  ✅ Current

Global MAX snapshot_date: 2026-01-07
```

**11 portfolios are stuck 2 days behind!**

### What Happened

1. **Jan 6**: Someone ran batch for "Tech Growth" only → created Jan 6 snapshot
2. **Jan 7**: Testscotty onboarded → created Jan 7 snapshot
3. **Cron jobs**: See global MAX = Jan 7 → think "all caught up" → skip processing
4. **Result**: 11 portfolios never get Jan 6 or Jan 7 snapshots

---

## Issue #3: Fire-and-Forget Batch History Tasks (MEDIUM)

### Root Cause

`batch_history_service.py` uses `asyncio.create_task()` without awaiting:

```python
# batch_history_service.py:44-53
asyncio.create_task(
    cls._record_batch_start_async(...)
)  # Fire-and-forget - never awaited
```

When the batch script exits, the event loop closes while these tasks are still pending.

### Evidence from Railway Database

Multiple cron-triggered batches show `status="running"` forever with no `completed_at`:
- Dec 23, 26, 29, 30, 31 (2025)
- Jan 2, 5 (2026)

These tasks were destroyed before they could update the database.

### Impact

- Batch history rows may be dropped (not persisted)
- "Task was destroyed but it is pending" warning in logs
- Admin dashboard shows batches as "running" indefinitely
- Misleading operational status

---

## 3-Phase Implementation Plan

We will fix these issues one at a time, verifying each on Railway before proceeding.

---

### PHASE 1: Fix Phase 1.5 Skipping (CRITICAL)

**Goal**: Ensure all batch entry points run Phase 1.5 (Symbol Factors) and Phase 1.75 (Symbol Metrics), AND ensure new portfolios get full historical snapshots for complete analytics.

**Approach (Two Parts)**:

**Part A**: Add Phase 1.5 and 1.75 to `_run_sequence_with_session()` so ALL batch paths include them.
- This ensures symbol factors are calculated regardless of which entry point triggers the batch.

**Part B**: Change onboarding flow to use `run_daily_batch_with_backfill()` instead of `run_daily_batch_sequence()`.
- **Rationale**: New portfolios with new tickers need historical snapshots (not just today's) for full analytics (P&L trends, MTD/YTD returns, etc.). Single-date processing only creates one snapshot, leaving analytics incomplete.
- This ensures new portfolios get backfilled historical data immediately during onboarding.

**Files to Modify**:
- `backend/app/batch/batch_orchestrator.py` (Part A)
- `backend/app/api/v1/endpoints/portfolios.py` (Part B)

**Changes**:

*Part A (batch_orchestrator.py):*
1. Add Phase 1.5 call after Phase 1 in `_run_sequence_with_session()`
2. Add Phase 1.75 call after Phase 1.5 in `_run_sequence_with_session()`
3. Update result dict to include `phase_1_5` and `phase_1_75` keys

*Part B (batch_orchestrator.py + portfolios.py):*
1. Create new `run_portfolio_onboarding_backfill(portfolio_id)` method in batch_orchestrator.py
   - Queries earliest position entry_date for THIS portfolio specifically
   - Calculates all trading days from that date to today
   - Runs full batch (Phase 1 → 1.5 → 1.75 → 2-6) for all dates
   - Bypasses global watermark entirely
2. Change onboarding trigger in portfolios.py to call `run_portfolio_onboarding_backfill()`

**Why not use `run_daily_batch_with_backfill()`?** (Code review finding)
- Global backfill short-circuits when cron already ran ("already up to date")
- Global backfill uses system-wide MAX snapshot date, not per-portfolio
- New portfolios would get nothing if system is already "up to date"

**Verification Steps**:
1. Deploy to Railway
2. Re-run batch for Testscotty portfolio
3. Query database to confirm:
   - 8 missing symbols now in `symbol_universe`
   - All 13 positions have `symbol_factor_exposures`
   - All 13 positions have `position_factor_exposures`
   - Historical snapshots exist (not just single date)

**Rollback**: Revert the batch_orchestrator.py and portfolios.py changes if issues arise.

---

### PHASE 2: Fix Global Watermark Bug (HIGH)

**Goal**: Ensure cron job processes ALL portfolios that are behind, not just check global MAX.

**Status**: READY FOR IMPLEMENTATION (January 8, 2026)

---

#### Problem Statement

The current `_get_last_batch_run_date()` function returns the **global MAX** snapshot date:

```python
# Current (buggy) - batch_orchestrator.py:1707-1712
query = select(PortfolioSnapshot.snapshot_date).order_by(
    desc(PortfolioSnapshot.snapshot_date)
).limit(1)  # Gets MAX across ALL portfolios
```

**Impact**: If Portfolio A is up-to-date (Jan 8), but Portfolios B-L are stuck at Jan 5, the cron sees `last_run_date = Jan 8` and skips processing entirely.

**Evidence from Railway (Jan 8, 2026)**: 11 portfolios stuck at Jan 5, 1 at Jan 6, 1 at Jan 7. Global MAX = Jan 7, so cron thinks "all caught up."

---

#### Design Decision: Hybrid Approach

**Date**: January 8, 2026
**Decision**: Implement hybrid approach combining MIN of MAX watermark + per-date portfolio filtering.

**Options Considered**:

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| Option 1 | MIN of per-portfolio MAX dates | Simple (~15 lines) | Reprocesses already-current portfolios |
| Option 2 | Process each portfolio independently | Efficient | Complex, loses batch efficiency |
| Option 3 | Global MAX + per-date filtering | Efficient | Complex, unclear start date |
| **Hybrid** | MIN of MAX + per-date filtering | Efficient + Simple start date | Medium complexity |

**Chosen**: Hybrid approach (Option 1 + Option 3 filtering)

**Rationale**:
- MIN of MAX gives clear, simple date range calculation
- Per-date filtering avoids reprocessing already-current portfolios
- Processing time is already a concern (~15 min per onboarding) - efficiency matters
- Moderate complexity is acceptable given the processing time savings

---

#### Implementation Plan

**Step 1: Modify `_get_last_batch_run_date()` (MIN of MAX)**

```python
async def _get_last_batch_run_date(self, db: AsyncSession) -> Optional[date]:
    """
    Get the effective 'last run date' for the system.

    Strategy: "The Minimum Watermark"
    - Get MAX snapshot date for EACH portfolio
    - Return the MIN of those dates (the most behind portfolio)
    - This ensures we process dates that ANY portfolio is missing
    """
    # Subquery: Get MAX snapshot date for each portfolio
    subquery = (
        select(
            PortfolioSnapshot.portfolio_id,
            func.max(PortfolioSnapshot.snapshot_date).label('max_date')
        )
        .group_by(PortfolioSnapshot.portfolio_id)
        .subquery()
    )

    # Main query: Get the MIN of those max dates
    query = select(func.min(subquery.c.max_date))

    result = await db.execute(query)
    min_watermark = result.scalar()

    if min_watermark:
        logger.info(f"System watermark (most lagging portfolio): {min_watermark}")
        return min_watermark

    # Fallback: first run ever - get earliest position date
    return await self._get_earliest_position_date(db)
```

**Step 2: Add per-date portfolio filtering in `_execute_batch_phases()`**

Before processing each date, query which portfolios are missing that date's snapshot:

```python
# Inside the date processing loop
for i, calc_date in enumerate(missing_dates, 1):
    # Get portfolios that already have snapshot for this date
    portfolios_with_snapshot = await self._get_portfolios_with_snapshot(db, calc_date)

    # Filter to only portfolios needing this date
    if portfolio_ids:
        portfolios_to_process = [p for p in portfolio_ids if p not in portfolios_with_snapshot]
    else:
        # Get all active portfolios, filter out those with snapshots
        all_portfolios = await self._get_all_active_portfolio_ids(db)
        portfolios_to_process = [p for p in all_portfolios if p not in portfolios_with_snapshot]

    if not portfolios_to_process:
        logger.debug(f"Skipping {calc_date}: all portfolios already have snapshots")
        continue

    logger.info(f"Processing {calc_date}: {len(portfolios_to_process)} portfolios need updates")

    # Process only these portfolios for this date
    # ... existing phase 2-6 logic with portfolios_to_process ...
```

**Step 3: Add helper methods**

```python
async def _get_portfolios_with_snapshot(
    self, db: AsyncSession, snapshot_date: date
) -> Set[str]:
    """Get portfolio IDs that already have a snapshot for the given date."""
    query = select(PortfolioSnapshot.portfolio_id).where(
        PortfolioSnapshot.snapshot_date == snapshot_date
    )
    result = await db.execute(query)
    return {str(pid) for pid in result.scalars().all()}

async def _get_all_active_portfolio_ids(self, db: AsyncSession) -> List[str]:
    """Get all active (non-deleted) portfolio IDs."""
    query = select(Portfolio.id).where(Portfolio.deleted_at.is_(None))
    result = await db.execute(query)
    return [str(pid) for pid in result.scalars().all()]
```

---

#### Files to Modify

| File | Changes |
|------|---------|
| `backend/app/batch/batch_orchestrator.py` | Modify `_get_last_batch_run_date()` to use MIN of MAX |
| `backend/app/batch/batch_orchestrator.py` | Add `_get_portfolios_with_snapshot()` helper |
| `backend/app/batch/batch_orchestrator.py` | Add `_get_all_active_portfolio_ids()` helper |
| `backend/app/batch/batch_orchestrator.py` | Add per-date filtering in `_execute_batch_phases()` |

---

#### Example Scenario

**Before (Bug)**:
```
Portfolios: A (Jan 7), B (Jan 5), C (Jan 5)
Global MAX = Jan 7
Cron: "All caught up!" → Skips B and C
```

**After (Hybrid Fix)**:
```
Portfolios: A (Jan 7), B (Jan 5), C (Jan 5)
MIN of MAX = Jan 5
Date range: Jan 6, 7, 8

Jan 6: A already has it → Process B, C only
Jan 7: A already has it → Process B, C only
Jan 8: None have it → Process A, B, C
```

---

#### Verification Steps

1. Deploy to Railway
2. Wait for next cron job or trigger manual batch
3. Query database to confirm:
   - All portfolios now have snapshots for the same date
   - No portfolios are behind
4. Check logs for:
   - "System watermark (most lagging portfolio): YYYY-MM-DD"
   - "Skipping {date}: all portfolios already have snapshots"
   - "Processing {date}: N portfolios need updates"

**Verification Query**:
```sql
SELECT p.name, MAX(ps.snapshot_date) as last_snapshot
FROM portfolios p
LEFT JOIN portfolio_snapshots ps ON p.id = ps.portfolio_id
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name
ORDER BY last_snapshot;
-- Expected: All portfolios should have same date (or within 1 day)
```

---

#### Rollback Plan

If issues arise:
1. Revert `_get_last_batch_run_date()` to original global MAX query
2. Remove per-date filtering logic
3. Remove helper methods

The changes are isolated to batch_orchestrator.py and don't affect the data model.

---

### PHASE 3: Fix Fire-and-Forget Tasks (MEDIUM)

**Goal**: Ensure batch history records are properly persisted and no "Task was destroyed" warnings.

**Approach**: Make batch history recording synchronous or properly awaited.

**Files to Modify**:
- `backend/app/services/batch_history_service.py`

**Changes**:
Option A (Recommended): Make recording synchronous for critical operations
```python
# Change from fire-and-forget to awaited
async def record_batch_start(...):
    await cls._record_batch_start_async(...)  # Now awaited
```

Option B: Add cleanup before script exit
- In `railway_daily_batch.py`, gather and await pending tasks before exit

**Verification Steps**:
1. Deploy to Railway
2. Wait for next cron job or trigger manual batch
3. Check Railway logs for absence of "Task was destroyed" warning
4. Query `batch_run_history` to confirm:
   - New batches have `completed_at` timestamps
   - Status is "completed" not "running"

**Rollback**: Revert the batch_history_service.py changes if issues arise.

---

### PHASE 6: Harden batch_run_history Error Handling (LOW)

**Goal**: Ensure `batch_run_history` database rows don't get stuck in "running" status when batch crashes.

**Problem Statement**:

Currently, `run_daily_batch_with_backfill()` has this pattern:

```python
record_batch_start(batch_run_id, ...)  # Creates DB row: status="running"

# Phase 1, 1.5, 1.75, 2-6 processing...
# 💥 If crash/timeout/OOM here, DB row stays "running" forever

record_batch_complete(batch_run_id, status="completed")  # Never reached on crash
```

This is separate from `batch_run_tracker` (in-memory, for UI polling) which we fixed in Phase 5. This is about the **persistent database record** in `batch_run_history` table.

**Impact**:
- Admin dashboard shows phantom "running" batches
- Harder to debug - can't distinguish running vs crashed batches
- Not user-facing (UI uses batch_run_tracker which is fixed)

**Approach**: Wrap batch processing in try/except/finally to ensure `record_batch_complete()` is always called.

**Files to Modify**:
- `backend/app/batch/batch_orchestrator.py`

**Changes**:

```python
async def run_daily_batch_with_backfill(...):
    batch_run_id = None
    try:
        # ... date range calculation ...

        batch_run_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        record_batch_start(batch_run_id, triggered_by=triggered_by, total_jobs=len(missing_dates))

        # ... Phase 1, 1.5, 1.75, 2-6 ...

        record_batch_complete(batch_run_id, status="completed", ...)
        return result

    except Exception as e:
        logger.error(f"Batch failed: {e}")
        if batch_run_id:
            record_batch_complete(
                batch_run_id,
                status="failed",
                error_summary=str(e)
            )
        raise  # Re-raise so caller knows it failed
```

**Alternative Approach**: Use a context manager for batch lifecycle:

```python
@asynccontextmanager
async def batch_run_context(triggered_by: str, total_jobs: int):
    batch_run_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    record_batch_start(batch_run_id, triggered_by, total_jobs)
    try:
        yield batch_run_id
        record_batch_complete(batch_run_id, status="completed", ...)
    except Exception as e:
        record_batch_complete(batch_run_id, status="failed", error_summary=str(e))
        raise

# Usage:
async with batch_run_context("onboarding", len(missing_dates)) as batch_run_id:
    # ... all phases ...
```

**Verification Steps**:
1. Deploy to Railway
2. Simulate a crash (e.g., raise exception in Phase 3)
3. Query `batch_run_history` to confirm:
   - Crashed batch has `status='failed'`
   - `error_summary` contains the exception message
   - `completed_at` timestamp is set

**Priority**: LOW - This is an operational/admin visibility issue, not user-facing. The user-facing UI tracker was fixed in Phase 5.

**Rollback**: Revert the try/except changes if issues arise.

---

## Manual Catch-Up: DEFERRED

**Decision (Jan 8, 2026)**: Manual catch-up is deferred until after Phase 1 and Phase 2 are deployed.

**Rationale**:
- Phase 2 fix changes the watermark logic to use MIN of per-portfolio MAX dates
- Once deployed, the next cron job will automatically backfill all missing dates (Jan 6, 7, 8) for all 11 behind portfolios
- No manual intervention needed - the fix itself resolves the backlog

**Note**: A `scripts/manual_catchup_batch.py` script was created and deployed but encountered environment issues on Railway SSH. It remains available if needed in the future but is not required for this fix.

---

---

### PHASE 5: Unify Batch Functions (REFACTOR) - DETAILED IMPLEMENTATION PLAN

**Date**: January 8, 2026
**Author**: Claude Opus 4.5
**Status**: READY FOR IMPLEMENTATION

---

## Problem Statement

The current architecture has two separate batch functions:
1. `run_daily_batch_with_backfill()` - Used by cron jobs, processes ALL portfolios
2. `run_portfolio_onboarding_backfill()` - Used by onboarding/settings, processes ONE portfolio

### Issues Discovered During Testscotty3 Debugging

1. **Critical Bug Fixed**: ImportError on line 471 (`app.utils.trading_calendar` → `app.core.trading_calendar`) - Committed as `7d8b0e2a`

2. **Major Inefficiency**: When `run_portfolio_onboarding_backfill()` runs, it:
   - Calls `market_data_collector.collect_daily_market_data()` with `portfolio_ids=[portfolio_id]`
   - BUT `_get_symbol_universe()` adds ALL 1,163 cached symbols (lines 444-452)
   - Result: Processing 1,193 symbols instead of ~30 needed
   - Time: ~4 hours instead of ~10 minutes
   - Rate limiting: Polygon 429 errors

3. **Code Duplication**: Similar logic in both functions with subtle differences

4. **Debugging Complexity**: Bugs can exist in one path but not the other (as we discovered)

---

## Requirements

### Functional Requirements

**FR1: Unified Entry Point**
- Single function `run_daily_batch_with_backfill()` handles ALL use cases
- Parameters determine behavior (portfolio scope, source tracking, symbol scope)
- Deprecate `run_portfolio_onboarding_backfill()` (keep as wrapper initially)

**FR2: Symbol Scoping**
- When `portfolio_id` is provided:
  - Phase 1: Collect market data for portfolio symbols + factor ETFs ONLY
  - Phase 1.5: Calculate factors for portfolio symbols + factor ETFs ONLY
  - Phase 1.75: Calculate metrics for portfolio symbols + factor ETFs ONLY
- When `portfolio_id` is None:
  - Phase 1, 1.5, 1.75: Process entire universe (current cron behavior)

**FR3: Backfill Date Range**
- When `portfolio_id` is provided:
  - Use portfolio's earliest position entry_date as start
  - Backfill from that date to current trading day
- When `portfolio_id` is None:
  - Use global watermark (most recent snapshot date)
  - Backfill from that date to current trading day

**FR4: Analytics After Onboarding**
After onboarding completes, these analytics MUST be available:
- Volatility (historical, current, forward/HAR forecast)
- Portfolio beta
- Stress test results
- Factor exposures (5 factors)
- Correlation matrix (position + factor)
- Sector exposure analysis

**FR5: Graceful Symbol Handling**
- When a symbol doesn't exist in any data provider:
  1. Try YFinance → YahooQuery → Polygon → FMP in order
  2. If all fail, mark symbol as "unavailable" in logs
  3. Continue processing other symbols (don't fail entire batch)
  4. Report unavailable symbols in final summary

**FR6: Source Tracking**
- Track which entry point triggered the batch:
  - `source="cron"` - Daily cron job
  - `source="onboarding"` - New portfolio onboarding
  - `source="settings"` - User clicked "Recalculate Analytics"
  - `source="admin"` - Admin dashboard trigger
- Log source in batch_run_history for debugging

---

## Design

### Unified Function Signature

```python
async def run_daily_batch_with_backfill(
    self,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    portfolio_ids: Optional[List[str]] = None,
    # NEW PARAMETERS:
    portfolio_id: Optional[str] = None,  # Single portfolio mode
    source: str = "cron",                # Entry point tracking
) -> Dict[str, Any]:
    """
    Unified batch processing function for all entry points.

    Modes:
    1. Cron mode (portfolio_id=None): Process entire universe
    2. Single-portfolio mode (portfolio_id=X): Process only that portfolio's symbols

    Symbol scoping logic:
    - If portfolio_id is provided → only portfolio symbols + factor ETFs
    - If portfolio_id is None → entire cached universe + factor ETFs

    Backfill date range:
    - If portfolio_id is provided → from portfolio's earliest entry_date
    - If portfolio_id is None → from global watermark (most recent snapshot)
    """
```

### Key Implementation Changes

#### 1. `batch_orchestrator.py` - Unified Function

```python
# Line ~85-440: Modify run_daily_batch_with_backfill()

async def run_daily_batch_with_backfill(
    self,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    portfolio_ids: Optional[List[str]] = None,
    portfolio_id: Optional[str] = None,  # NEW: single portfolio mode
    source: str = "cron",                 # NEW: entry point tracking
) -> Dict[str, Any]:

    # Determine mode
    is_single_portfolio_mode = portfolio_id is not None

    if is_single_portfolio_mode:
        # Convert to list format for internal use
        portfolio_ids = [portfolio_id]

        # Get portfolio's earliest entry_date for backfill start
        async with AsyncSessionLocal() as db:
            earliest_query = select(Position.entry_date).where(
                and_(
                    Position.portfolio_id == UUID(portfolio_id),
                    Position.deleted_at.is_(None),
                    Position.entry_date.isnot(None)
                )
            ).order_by(Position.entry_date).limit(1)
            result = await db.execute(earliest_query)
            earliest_date = result.scalar_one_or_none()

            if earliest_date:
                start_date = earliest_date
                logger.info(f"Single-portfolio mode: backfill from {earliest_date}")

    # ... rest of function with scoped_only parameter passed to market_data_collector
```

#### 2. `market_data_collector.py` - Scoped Symbol Universe

```python
# Line ~407: Modify _get_symbol_universe()

async def _get_symbol_universe(
    self,
    db: AsyncSession,
    calculation_date: date,
    portfolio_ids: Optional[List[UUID]] = None,
    scoped_only: bool = False,  # NEW: if True, skip cached universe
) -> Set[str]:
    """
    Get all unique symbols from:
    1. Active positions (from portfolios)
    2. Factor ETFs (required for analytics)
    3. All symbols already in market_data_cache (ONLY if scoped_only=False)
    """
    # ... existing position symbols query ...

    # CHANGED: Only add cached universe if NOT in scoped mode
    if not scoped_only:
        # Get all symbols already in market_data_cache
        cached_symbols_query = select(MarketDataCache.symbol).distinct()
        cached_result = await db.execute(cached_symbols_query)
        cached_symbols = {
            normalize_symbol(symbol)
            for symbol in cached_result.scalars().all()
            if symbol
        }
        logger.info(f"  Cached universe symbols: {len(cached_symbols)}")
    else:
        cached_symbols = set()
        logger.info(f"  Scoped mode: skipping cached universe")

    # ... rest of function ...
```

#### 3. `market_data_collector.py` - Graceful Symbol Handling

```python
# Line ~706: Enhance _fetch_with_priority_chain()

async def _fetch_with_priority_chain(
    self,
    symbols: List[str],
    start_date: date,
    end_date: date
) -> Tuple[Dict[str, List[Dict]], Dict[str, int]]:
    """
    Enhanced with graceful handling for unavailable symbols.
    """
    all_data = {}
    provider_counts = {'yahooquery': 0, 'yfinance': 0, 'fmp': 0, 'polygon': 0}
    unavailable_symbols = []
    remaining_symbols = symbols.copy()

    # Try each provider in order...
    # (existing logic)

    # After all providers tried, log unavailable symbols gracefully
    if remaining_symbols:
        unavailable_symbols = remaining_symbols
        logger.warning(
            f"Unavailable symbols ({len(unavailable_symbols)}): {unavailable_symbols[:20]}"
            + (f"... and {len(unavailable_symbols) - 20} more" if len(unavailable_symbols) > 20 else "")
        )
        logger.info("These symbols will be skipped; batch continues for available symbols")

    return all_data, provider_counts, unavailable_symbols  # Return unavailable list
```

#### 4. `portfolios.py` - Update Calculate Endpoint

```python
# Line ~590: Update /calculate endpoint to use unified function

@router.post("/{portfolio_id}/calculate")
async def calculate_portfolio(portfolio_id: UUID, ...):
    # Call unified function with single-portfolio mode
    result = await batch_orchestrator.run_daily_batch_with_backfill(
        portfolio_id=str(portfolio_id),
        source="onboarding"  # or "settings" based on caller
    )
```

---

## Files to Modify

| File | Change | Lines (approx) |
|------|--------|----------------|
| `batch_orchestrator.py` | Add `portfolio_id` and `source` params to unified function | ~85-440 |
| `batch_orchestrator.py` | Deprecate `run_portfolio_onboarding_backfill()` (keep as wrapper) | ~442-687 |
| `market_data_collector.py` | Add `scoped_only` param to `_get_symbol_universe()` | ~407-505 |
| `market_data_collector.py` | Add `scoped_only` param to `collect_daily_market_data()` | ~95-405 |
| `market_data_collector.py` | Return unavailable symbols from `_fetch_with_priority_chain()` | ~706-774 |
| `portfolios.py` | Update `/calculate` to use unified function | ~590-617 |

---

## Implementation Steps

### Step 1: Update `market_data_collector.py`
1. Add `scoped_only` parameter to `collect_daily_market_data()`
2. Add `scoped_only` parameter to `_get_symbol_universe()`
3. When `scoped_only=True`, skip the cached universe (lines 444-452)
4. Return unavailable symbols from fetch chain

### Step 2: Update `batch_orchestrator.py`
1. Add `portfolio_id` and `source` parameters to `run_daily_batch_with_backfill()`
2. Detect single-portfolio mode when `portfolio_id` is provided
3. In single-portfolio mode:
   - Calculate backfill start from portfolio's earliest entry_date
   - Pass `scoped_only=True` to market_data_collector
   - Pass `scoped_only=True` to Phase 1.5 and 1.75
4. Convert `run_portfolio_onboarding_backfill()` to wrapper that calls unified function

### Step 3: Update `portfolios.py`
1. Change `/calculate` endpoint to use unified function with `portfolio_id` and `source`

### Step 4: Test & Verify
1. Test onboarding flow - should complete in ~5-10 minutes
2. Test settings "Recalculate Analytics" - same performance
3. Test cron job - still processes entire universe correctly
4. Verify analytics available: volatility, beta, stress test, factors, correlations

---

## Expected Performance Improvement

| Metric | Before (Inefficient) | After (Scoped) | Improvement |
|--------|---------------------|----------------|-------------|
| Symbols processed | 1,193 | ~30 | 40x fewer |
| Estimated runtime | 4+ hours | ~10 minutes | 24x faster |
| API calls | ~1,193 × days | ~30 × days | 40x fewer |
| Rate limit errors | Many 429s | None expected | Eliminated |

---

## Rollback Plan

If issues arise after deployment:
1. Revert `batch_orchestrator.py` changes
2. Revert `market_data_collector.py` changes
3. Revert `portfolios.py` changes
4. The `run_portfolio_onboarding_backfill()` wrapper preserves backward compatibility

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| Onboarding completes in <15 minutes | Time from trigger to completion |
| No 429 rate limit errors | Railway logs show no Polygon 429s |
| All analytics available | Check Testscotty3: vol, beta, stress, factors, correlations |
| Cron still works | Daily batch processes all portfolios correctly |
| Single code path | Both flows use same unified function |

---

## After All 5 Phases Complete

1. Verify next cron job catches up all portfolios (Phase 2 auto-backfill)
2. Re-run batch for Testscotty to verify Phase 1 fix (symbol factors)
3. Monitor logs for absence of "Task was destroyed" warnings (Phase 3)
4. Verify batch_run_tracker self-heals after timeout (Phase 4)
5. Verify single-portfolio batches complete in ~10 minutes (Phase 5)

---

## Success Criteria

| Phase | Criteria |
|-------|----------|
| Phase 1 | Testscotty's 8 missing symbols in `symbol_universe`, all 13 positions have factor exposures |
| Phase 2 | All portfolios have snapshots for the same dates (no stragglers) |
| Phase 3 | No "Task was destroyed" warnings, batch history shows "completed" status |

---

## Code References

| Component | File | Lines |
|-----------|------|-------|
| Global watermark query | `batch_orchestrator.py` | 1401-1410 |
| Phase 1.5 (backfill only) | `batch_orchestrator.py` | 280-319 |
| _run_sequence_with_session | `batch_orchestrator.py` | 526-800 |
| Admin batch endpoint | `admin_batch.py` | 45-102 |
| Onboarding batch trigger | `portfolios.py` | 521-606 |
| Fire-and-forget tasks | `batch_history_service.py` | 44-53, 124-135 |
| Symbol factor caching | `symbol_factors.py` | 145-171 |
| ensure_symbols_in_universe | `symbol_factors.py` | 174-218 |

---

## Appendix: Original Analysis (Jan 7, 2026)

The original analysis correctly identified the Phase 1.5 skipping issue and fire-and-forget task warnings. The pool timeout and cancellation handling recommendations remain valid for system stability but are lower priority than the three bugs identified above.

### Pool/Timeout Issues (Deferred)

The original analysis of pool exhaustion and timeout issues remains valid:
- `pool_timeout=30` in `database.py` may be too short for long batches
- No `asyncio.CancelledError` handling in batch orchestrator
- Stress testing can take 60+ seconds

These should be addressed after the three critical bugs are fixed.
