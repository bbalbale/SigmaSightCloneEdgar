# Fix Railway Cron Batch Processing Issues

**Created**: 2025-11-26
**Updated**: 2025-11-26
**Status**: RESOLVED
**Priority**: High

---

## ✅ ROOT CAUSE IDENTIFIED: Railway Running Wrong/Stale Code

### The Problem

The Railway cron service was **not connected to the GitHub repo**, causing it to run old/stale code while the main backend service had the latest fixes.

### Symptoms Observed

```
Correlated stress loss of $-648,999 exceeds 99% of portfolio. Clipping at $-529,731 (not scaling factors)
Correlated stress loss of $-4,383,345 exceeds 99% of portfolio. Clipping at $-1,328,034 (not scaling factors)
Direct stress loss of $-1,580,498 exceeds 99% of portfolio. Clipping at $-1,328,034 (not scaling factors)
```

Additionally:
- **Volatility analytics were missing** after daily cron runs
- Stress testing produced unrealistically large loss values
- Running `trigger_railway_fix.py` (HTTP API) fixed everything

### Why `trigger_railway_fix.py` Worked

| Method | Code Source | Result |
|--------|-------------|--------|
| `trigger_railway_fix.py` | HTTP API → Main backend (has latest code) | ✅ Works |
| Railway cron | Cron service (disconnected, stale code) | ❌ Broken |

The HTTP trigger worked because it calls the main backend service which **was** connected to the repo and had the latest code.

---

## ⚠️ CRITICAL: Railway Setup Requirements

### 1. Cron Service Must Be Connected to Repo

The Railway cron service **must be connected to the GitHub repo** to receive code updates.

**To verify**: Railway dashboard → Cron service → Settings → Ensure repo is connected.

**If disconnected:**
- Cron will run old/stale code
- Fixes deployed to main won't take effect
- Logs may show unexpected behavior (e.g., missing banner)

### 2. Correct Cron Script Path

The daily cron job must run:
```
cd backend && uv run python scripts/automation/railway_daily_batch.py
```

**Important distinctions:**
- `scripts/automation/railway_daily_batch.py` - **Automated daily cron** (this is what Railway should run)
- `scripts/railway/trigger_railway_fix.py` - **Manual fix trigger** (run locally to trigger HTTP API)

### 3. Verify Correct Script is Running

The cron script should log this banner at startup:
```
╔══════════════════════════════════════════════════════════════╗
║       SIGMASIGHT DAILY BATCH WORKFLOW - STARTING             ║
╚══════════════════════════════════════════════════════════════╝
```

If this banner doesn't appear but factor seeding logs do, Railway may be running the wrong script.

---

## Implementation Summary (5 Changes Applied)

### Change 1: Standardize "IR Beta" in seed_factors.py ✅

Changed factor name from `"Interest Rate"` to `"IR Beta"` to match analytics_runner and frontend.

### Change 2: Standardize "IR Beta" in stress_testing.py ✅

Updated `FACTOR_NAME_MAP` to map `Interest_Rate` → `"IR Beta"`.

### Change 3: Add Factor Seeding to Railway Cron ✅

Added `ensure_factor_definitions()` to `railway_daily_batch.py` to ensure factor definitions exist before batch runs.

### Change 4: Restructure Batch Orchestrator Cache Timing ✅

Changed execution order:
1. Run ALL Phase 1 (market data) for all dates FIRST
2. THEN load price cache (now includes today's data)
3. THEN run Phases 2-6 for all dates

This fixed the 20-minute runtime issue where cache was loaded before data existed.

### Change 5: Handle PRIVATE-only Portfolios Gracefully ✅

Updated `market_beta.py` and `market_risk.py` to return skip result instead of raising errors for portfolios with only PRIVATE positions.

### Change 6: Use print() for Railway Logging ✅

Changed critical log messages in `railway_daily_batch.py` from `logger.info()` to `print()` because Railway logs don't show logger output from this script.

---

## Debugging Notes

### The `<=` Query is CORRECT

The stress testing query uses `calculation_date <= calculation_date` with `ORDER BY calculation_date.desc()`:

```python
stmt = (
    select(FactorExposure, FactorDefinition)
    .where(FactorExposure.calculation_date <= calculation_date)
    .order_by(FactorExposure.calculation_date.desc())
)
```

This is a **defensive fallback pattern** - if today's data doesn't exist, it uses the most recent available data. This is correct behavior.

The extreme values were NOT caused by this query - they were caused by Railway running old code that had other bugs.

### Session Management

The equity balance "frozen" issue was fixed by ensuring database sessions are closed before calling the batch orchestrator:

```python
# Count portfolios (separate session, closed before batch runs)
async with get_async_session() as db:
    portfolio_count = await db.execute(select(func.count(Portfolio.id)))
    total_portfolios = portfolio_count.scalar()
# Session is now CLOSED before batch processing starts

# Batch orchestrator manages its own sessions
result = await batch_orchestrator.run_daily_batch_with_backfill()
```

---

## How to Fix If Issues Return

### Step 1: Verify Railway Setup

1. Check Railway dashboard → Cron service → Settings
2. Ensure repo is connected
3. Verify cron command is: `cd backend && uv run python scripts/automation/railway_daily_batch.py`

### Step 2: Run Manual Fix

```bash
cd backend
uv run python scripts/railway/trigger_railway_fix.py
```

### Step 3: For Backfill

```bash
cd backend
uv run python scripts/railway/trigger_railway_fix.py --start-date 2025-07-01 --end-date 2025-11-26
```

---

## Success Criteria ✅

- [x] Daily cron completes without extreme stress test clipping warnings
- [x] No "No exposure found for shocked factor: Interest_Rate" warnings
- [x] Volatility metrics appear correctly after daily cron
- [x] PRIVATE-only portfolios skip gracefully (info log, not error)
- [x] Cron banner appears in Railway logs (using print())
- [x] Completion summary appears in Railway logs

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/db/seed_factors.py` | `"Interest Rate"` → `"IR Beta"` |
| `backend/app/calculations/stress_testing.py` | Mapping to `"IR Beta"` |
| `backend/scripts/automation/railway_daily_batch.py` | Add factor seeding, use print() for logs |
| `backend/app/batch/batch_orchestrator.py` | Run all Phase 1s before cache load |
| `backend/app/calculations/market_beta.py` | Graceful skip for PRIVATE portfolios |
| `backend/app/calculations/market_risk.py` | Graceful skip for no positions |
| `backend/scripts/railway/RAILWAY_SCRIPTS_README.md` | Updated with correct instructions |
