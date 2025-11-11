# Railway Daily Batch Automation

Automated daily workflow for market data synchronization and portfolio calculations.

## Overview

This automation runs **every weekday at 11:30 PM UTC** (6:30pm EST / 7:30pm EDT) via the batch orchestrator, which handles:

1. **Trading day detection** (NYSE calendar) with automatic adjustment
2. **Phase 0**: Company profile sync (beta values, sectors, industries) - on final date only
3. **Phase 1**: Market data collection (1-year lookback, YFinance/FMP/Polygon)
4. **Phase 2**: Fundamental data collection (earnings-driven smart fetch)
5. **Phase 3**: P&L calculation & snapshots (equity rollforward, trading days only)
6. **Phase 4**: Position market value updates (analytics accuracy)
7. **Phase 5**: Sector tag restoration (auto-tagging from company profiles)
8. **Phase 6**: Risk analytics (betas, factors, volatility, correlations, stress tests)

**Typical Duration**: 6-7 minutes total
**Trading Days Only**: Job automatically skips weekends/holidays and adjusts to previous trading day if run before 4:30 PM ET

**Key Change (Phase 11.1)**: The Railway script now directly calls `batch_orchestrator.run_daily_batch_with_backfill()` - no duplicate logic. Same code path as local batch processing.

## Files

- **`railway_daily_batch.py`** - Thin wrapper that calls batch orchestrator (114 lines, down from 376)
- **`trading_calendar.py`** - NYSE trading day detection utilities (used by batch orchestrator)
- **`../../railway.json`** - Railway cron service configuration

## Local Testing

```bash
# Run with automatic backfill detection
uv run python scripts/automation/railway_daily_batch.py

# Same as running the local batch script
uv run python scripts/batch_processing/run_batch.py
```

Both scripts now use the exact same batch orchestrator code path.

## Railway Deployment

### Deployment Methods

- **Dashboard Deployment** (Recommended): Follow the steps below for easiest setup
- **CLI Deployment**: See `RAILWAY_CLI_DEPLOYMENT.md` for command-line deployment
- **CLI Quickstart**: See `RAILWAY_CLI_QUICKSTART.md` if you already have backend deployed

### Prerequisites

1. **Environment Variables** (must be set for each service individually)
   - `DATABASE_URL` - PostgreSQL connection string (**Important**: Use `postgresql+asyncpg://` for async compatibility)
   - `POLYGON_API_KEY` - Market data API key
   - `FMP_API_KEY` - Financial Modeling Prep API key
   - `FRED_API_KEY` - Federal Reserve economic data API key
   - `SECRET_KEY` - JWT secret
   - `OPENAI_API_KEY` - OpenAI API key for chat

**Note**: Environment variables do NOT automatically inherit between services. You must configure them separately for the cron service.

### Dashboard Deployment Steps (Recommended)

#### Step 1: Create Railway Service

1. Go to Railway Project → **+ New Service**
2. Select **"GitHub Repo"** as source
3. Choose repository: `SigmaSight-BE`
4. Set **Root Directory**: `backend`
5. Name service: `sigmasight-backend-cron`

#### Step 2: Configure Service

1. Go to service **Settings**:
   - **Start Command**: `uv run python scripts/automation/railway_daily_batch.py`

     ⚠️ **CRITICAL**: You MUST set this custom start command in the Railway Dashboard Settings → Start Command field. The repository has a Dockerfile that starts the FastAPI web server (`CMD ["/app/start.sh"]`). Railway gives Dockerfile CMD priority over `railway.json` startCommand, so you must override it manually in the Dashboard.

     **Without this override**: The cron service will run the web server instead of the batch script!

   - **Cron Schedule**: Leave DISABLED initially (test manually first)

2. Configure environment variables in the **Variables** tab:

   **Option A: Use Variable References** (Recommended)

   Reference existing Postgres service and copy values from your web service:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (**Important**: Edit to use `postgresql+asyncpg://` instead of `postgresql://`)
   - `POLYGON_API_KEY` = Copy from web service
   - `FMP_API_KEY` = Copy from web service
   - `FRED_API_KEY` = Copy from web service
   - `SECRET_KEY` = Copy from web service
   - `OPENAI_API_KEY` = Copy from web service

   **Option B: Use Raw Values**

   Copy the actual connection string and API keys from your web service's Variables tab.

#### Step 3: Manual Testing (REQUIRED before enabling cron)

1. Deploy the service (it will exit immediately since no cron schedule yet)
2. Go to service **Deployments** tab
3. Find latest deployment → Click **"View Logs"**
4. Manually trigger using Railway CLI (ensure you're targeting the cron service):
   ```bash
   railway run --service sigmasight-backend-cron uv run python scripts/automation/railway_daily_batch.py
   ```
   **Note**: The `--service` flag is critical - without it, Railway runs on the default web service.
5. Monitor logs for:
   - ✅ Batch orchestrator starting
   - ✅ Trading day detection (automatic adjustment if needed)
   - ✅ Phase 0: Company profile sync (on final date)
   - ✅ Phase 1: Market data collection
   - ✅ Phase 2: Fundamental data collection
   - ✅ Phase 3: P&L calculation & snapshots
   - ✅ Phase 4: Position market value updates
   - ✅ Phase 5: Sector tag restoration
   - ✅ Phase 6: Risk analytics
   - ✅ Completion summary showing success

#### Step 4: Enable Cron Schedule (after successful manual test)

1. Go to service **Settings** tab
2. Scroll down to **Cron Schedule** section
3. Click **"Add Cron Schedule"** or edit the existing field
4. Enter schedule: `30 23 * * 1-5`
   - This means: 11:30 PM UTC, Monday-Friday
   - **Standard Time (Nov-Mar)**: 11:30 PM UTC = 6:30 PM EST
   - **Daylight Time (Mar-Nov)**: 11:30 PM UTC = 7:30 PM EDT
5. Click **"Deploy"** to save changes
6. Verify cron is enabled by checking the Settings page shows the schedule

#### Step 5: Monitor First Automated Run

1. Wait for next scheduled run (11:30 PM UTC on a weekday)
2. Check **Deployments** → **View Logs**
3. Verify all 7 phases complete successfully
4. If failures occur, check Railway logs for error details

### Monitoring

**Railway Dashboard Logs** (Primary monitoring method):
- Check logs daily after 11:30 PM UTC
- Look for completion message: `✅ All operations completed successfully`
- If errors, check specific phase failure messages

**Manual Log Review**:
```bash
# Via Railway CLI
railway logs --service sigmasight-backend-cron

# Or via Railway Dashboard
Project → Services → sigmasight-backend-cron → Deployments → View Logs
```

### Troubleshooting

#### Cron Not Running
- Check cron schedule is set: `30 23 * * 1-5`
- Verify service is not paused
- Check Railway dashboard for deployment errors

#### Database Connection Errors
- Verify `DATABASE_URL` is set correctly for the cron service (check Variables tab)
- **Critical**: Ensure `DATABASE_URL` uses `postgresql+asyncpg://` not `postgresql://`
- Check PostgreSQL service is running
- Verify database credentials match your Postgres service

#### Cron Service Running Web Server Instead of Batch Script
**Symptom**: Deploy logs show `INFO: Uvicorn running on http://0.0.0.0:8080`

**Problem**: Railway is using the Dockerfile's `CMD ["/app/start.sh"]` which starts the FastAPI web server, ignoring the `railway.json` startCommand.

**Root Cause**: Railway's service detection priority:
1. Dockerfile CMD (if exists) ← Takes precedence
2. `railway.json` startCommand ← Ignored when Dockerfile exists
3. Nixpacks detection (fallback)

**Solution**: Override start command in Railway Dashboard Settings

1. Go to Railway Dashboard → Project → `sigmasight-backend-cron` service
2. Click **Settings** tab
3. Scroll to **Start Command** section
4. Enter: `uv run python scripts/automation/railway_daily_batch.py`
5. Click **Save**
6. Service will redeploy automatically

**Expected Behavior After Fix**:
- Service exits immediately (no cron schedule yet)
- Logs show batch script starting, not Uvicorn
- Once cron schedule is set, job runs at scheduled time

#### "asyncio extension requires an async driver" Error
This error means your `DATABASE_URL` is using the wrong driver.

**Problem**: `postgresql://user:pass@host:port/db`
**Solution**: Edit the variable to use `postgresql+asyncpg://user:pass@host:port/db`

In Railway Dashboard:
1. Go to cron service → Variables tab
2. Edit `DATABASE_URL`
3. Change `postgresql://` to `postgresql+asyncpg://` at the beginning
4. Save and redeploy

#### Trading Day Adjustment
**Symptom**: Logs show "Adjusted target date to previous trading day"

**Expected Behavior**: This is NORMAL. The batch orchestrator automatically:
- Detects non-trading days (weekends, holidays) and uses previous trading day
- Uses previous trading day if run before 4:30 PM ET (market hasn't closed yet)
- Uses current day if run after 4:30 PM ET on a trading day

**No action needed** - this is the orchestrator working correctly.

#### Phase Failures
The batch orchestrator isolates phases - failures in one phase don't stop later phases.

**Common Phase Issues**:
- **Phase 0 (Company Profiles)**: Non-blocking. Partial failures OK (synthetic symbols, options expected to fail)
- **Phase 1 (Market Data)**: Check API keys, provider status. Private positions intentionally skip.
- **Phase 2 (Fundamentals)**: "Data not available" warnings are normal (3+ day post-earnings requirement)
- **Phase 3 (P&L)**: Requires Phase 1 data. Check for market data gaps.
- **Phase 4 (Position Values)**: Depends on Phase 1. Check market data availability.
- **Phase 5 (Sector Tags)**: Depends on Phase 0. Check company profile sync.
- **Phase 6 (Analytics)**: Requires Phases 3-5. Check for calculation data issues.

**Manual Phase Re-run**:
```bash
# Re-run specific date
railway run --service sigmasight-backend-cron uv run python scripts/batch_processing/run_batch.py --start-date 2025-07-01 --end-date 2025-07-01
```

#### API Rate Limits (429 Errors)
- **Expected behavior** - script has fallback providers
- YFinance primary, FMP secondary fallback
- Private positions (real estate, PE) will fail gracefully - this is normal

### Batch Orchestrator Features

The Railway cron uses the **exact same batch orchestrator** as local development:

- ✅ **Automatic Backfill**: Detects missing trading days and fills gaps
- ✅ **Trading Day Detection**: NYSE calendar with automatic adjustment
- ✅ **Phase Isolation**: Failures don't cascade
- ✅ **Smart Optimization**: Company profiles/fundamentals only on final date
- ✅ **Graceful Degradation**: Missing data doesn't stop the batch

See `scripts/batch_processing/README.md` for detailed phase documentation.

### Cron Schedule Details

**Schedule**: `30 23 * * 1-5`
- **Minutes**: 30 (half past the hour)
- **Hour**: 23 (11 PM UTC)
- **Day of Month**: * (every day)
- **Month**: * (every month)
- **Day of Week**: 1-5 (Monday-Friday)

**Why 23:30 UTC?**
- Markets close at 4:00 PM ET
- **Standard Time**: 4:00 PM EST = 9:00 PM UTC → job runs at 11:30 PM UTC (2.5 hours later)
- **Daylight Time**: 4:00 PM EDT = 8:00 PM UTC → job runs at 11:30 PM UTC (3.5 hours later)
- Ensures market data providers have settled final prices
- Avoids midnight UTC rollover issues

**DST Handling**:
- No manual cron changes needed!
- Fixed 23:30 UTC time works year-round
- Job automatically runs 6:30 PM local time (EST/EDT)

### Exit Codes

The script uses standard Unix exit codes:
- `0` - Success (all operations completed)
- `1` - Failure (one or more issues occurred)
- `130` - Interrupted (Ctrl+C)

Railway will retry failed jobs based on `restartPolicyMaxRetries: 3` setting.

### Future Enhancements

Potential improvements documented but not implemented:
- Slack webhook notifications (see TODO4.md blocker #5 resolution)
- Email alerts via SendGrid/AWS SES
- Datadog metrics integration
- Railway webhook → Zapier → Email forwarding

For now, manual Railway dashboard log checking is sufficient.

---

## Phase 11.1 Changes (November 2025)

**Simplified Railway Script**:
- Removed duplicate trading day detection (orchestrator handles it)
- Removed duplicate company profile sync (now Phase 0 in orchestrator)
- Removed per-portfolio loop logic (orchestrator handles all portfolios)
- Removed custom result tracking (orchestrator provides summary)
- **Result**: 70% code reduction (376 → 114 lines)

**Benefits**:
- Single source of truth for batch processing
- Railway automatically gets all orchestrator improvements
- Easier to maintain (no duplicate code)
- Consistent behavior between Railway and local development
