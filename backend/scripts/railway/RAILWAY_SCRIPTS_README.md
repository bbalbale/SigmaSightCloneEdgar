# Railway Production Scripts

Scripts for managing Railway production deployment.

## ⚠️ CRITICAL: Railway Setup Requirements

### 1. Cron Service Must Be Connected to Repo

The Railway cron service **must be connected to the GitHub repo** to receive code updates. If disconnected:
- Cron will run old/stale code
- Fixes deployed to main won't take effect
- Logs may show unexpected behavior

**To verify**: Check Railway dashboard → Cron service → Settings → Ensure repo is connected.

### 2. Correct Cron Script Path

The daily cron job should run:
```
cd backend && uv run python scripts/automation/railway_daily_batch.py
```

**NOT** any script in `scripts/railway/` - those are for manual operations.

### 3. `railway run` Does NOT Work

The `railway run` command executes locally with Railway's DB connection, but this causes async driver conflicts.

**Instead use:**
- `trigger_railway_fix.py` (recommended - calls HTTP API)
- `railway ssh` + `uv run python` (for direct server execution)

---

## Quick Start - Trigger Data Fix

### HTTP Trigger (`trigger_railway_fix.py`) ⭐ **RECOMMENDED**

Calls the `/admin/fix/fix-all` HTTP endpoint on Railway. Runs locally, triggers fix remotely.

**Usage:**
```bash
cd backend
uv run python scripts/railway/trigger_railway_fix.py

# With date range for backfill:
uv run python scripts/railway/trigger_railway_fix.py --start-date 2025-07-01 --end-date 2025-11-20

# Against sandbox:
uv run python scripts/railway/trigger_railway_fix.py --base-url https://sigmasight-be-sandbox.up.railway.app/api/v1
```

**What it does (in order):**
1. Authenticates with demo credentials
2. Calls `/admin/fix/fix-all` endpoint
3. Polls for job completion
4. Reports results

**Use this when:**
- Daily cron produced errors
- Need to backfill historical data
- Stress tests showing extreme values
- Volatility analytics missing

---

## Script Reference

### Two Script Locations (Don't Confuse!)

| Location | Purpose | How to Run |
|----------|---------|------------|
| `scripts/automation/railway_daily_batch.py` | **Automated daily cron** | Railway cron scheduler |
| `scripts/railway/trigger_railway_fix.py` | **Manual fix trigger** | Local: `uv run python ...` |

### Daily Cron Script

**File:** `scripts/automation/railway_daily_batch.py`

This is what Railway's cron job runs automatically. It:
- Seeds factor definitions
- Runs batch orchestrator with backfill
- Handles all 6 phases (market data, P&L, analytics, etc.)

**You should NOT run this manually** - use `trigger_railway_fix.py` instead.

### Manual Fix Trigger

**File:** `scripts/railway/trigger_railway_fix.py`

This is for manual intervention when the cron fails or data needs fixing.

**Parameters:**
- `--base-url`: Backend URL (default: production)
- `--email`: Login email (default: demo_hnw@sigmasight.com)
- `--password`: Login password (default: demo12345)
- `--timeout`: Max wait time in seconds (default: 1800)
- `--start-date`: Optional backfill start date (YYYY-MM-DD)
- `--end-date`: Optional end date (YYYY-MM-DD)

---

## Direct Server Access (Advanced)

If HTTP trigger doesn't work, you can SSH into Railway:

```bash
# SSH into the backend service
railway ssh --service SigmaSight-BE

# Once connected, run commands directly:
cd /app/backend
uv run python scripts/automation/railway_daily_batch.py
```

---

## Troubleshooting

### "Stress test clipping" warnings in cron logs

**Symptom:**
```
Correlated stress loss of $-4,383,345 exceeds 99% of portfolio. Clipping at $-1,328,034
```

**Cause:** Usually means cron ran old code or factor exposures are stale.

**Fix:**
```bash
uv run python scripts/railway/trigger_railway_fix.py
```

### Cron banner not appearing in logs

**Symptom:** Factor seeding logs appear but no `╔════════════` banner.

**Cause:** Railway cron may be running wrong script or `logger.info()` not showing.

**Verify:** Check Railway dashboard for exact cron command configured.

### Missing volatility analytics after cron

**Cause:** Factor definitions may be missing or analytics failed silently.

**Fix:** Run trigger script to clear and recalculate:
```bash
uv run python scripts/railway/trigger_railway_fix.py
```

---

## Archived Scripts

The following scripts in `scripts/railway/` are **archived** and should not be used:

- `_archive_manual_batch_railway.py` - Old `railway run` approach (doesn't work)
- `clear_calculations_railway.py` - Use HTTP endpoint instead
- `seed_portfolios_railway.py` - Use HTTP endpoint instead
- `fix_railway_data.py` - Superseded by `trigger_railway_fix.py`

---

## See Also

- **Fix_Railway_Cron.md**: Detailed debugging notes for cron issues
- **Backend CLAUDE.md**: Complete backend architecture reference
- **API_REFERENCE_V1.4.6.md**: API endpoint documentation
