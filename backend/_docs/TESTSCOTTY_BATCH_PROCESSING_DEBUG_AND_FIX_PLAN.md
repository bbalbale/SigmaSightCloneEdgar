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

**Approach**: Change `_get_last_batch_run_date()` to use MIN of per-portfolio MAX dates instead of global MAX.

**Files to Modify**:
- `backend/app/batch/batch_orchestrator.py`

**Changes**:
1. Modify `_get_last_batch_run_date()` to:
   - Get the MAX snapshot_date for EACH portfolio
   - Return the MIN of those dates (the most behind portfolio)
   - This ensures we process dates that ANY portfolio is missing

**Alternative Approach** (simpler):
1. Instead of changing watermark logic, modify `_run_phases_2_through_6()` to check each portfolio individually
2. For each date, only process portfolios that don't have a snapshot for that date

**Verification Steps**:
1. Deploy to Railway
2. Run `run_daily_batch_with_backfill()` (via cron trigger or manual)
3. Query database to confirm:
   - All 12 portfolios now have snapshots for Jan 6 and Jan 7
   - No portfolios are behind

**Rollback**: Revert the batch_orchestrator.py changes if issues arise.

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

## Manual Catch-Up: DEFERRED

**Decision (Jan 8, 2026)**: Manual catch-up is deferred until after Phase 1 and Phase 2 are deployed.

**Rationale**:
- Phase 2 fix changes the watermark logic to use MIN of per-portfolio MAX dates
- Once deployed, the next cron job will automatically backfill all missing dates (Jan 6, 7, 8) for all 11 behind portfolios
- No manual intervention needed - the fix itself resolves the backlog

**Note**: A `scripts/manual_catchup_batch.py` script was created and deployed but encountered environment issues on Railway SSH. It remains available if needed in the future but is not required for this fix.

---

## After All 3 Phases Complete

1. Verify next cron job catches up all portfolios (Phase 2 auto-backfill)
2. Re-run batch for Testscotty to verify Phase 1 fix (symbol factors)
3. Monitor logs for absence of "Task was destroyed" warnings (Phase 3)

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
