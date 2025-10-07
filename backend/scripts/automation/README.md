# Railway Daily Batch Automation

Automated daily workflow for market data synchronization and portfolio calculations.

## Overview

This automation runs **every weekday at 11:30 PM UTC** (6:30pm EST / 7:30pm EDT) to:
1. Check if today is a trading day (NYSE calendar)
2. **Sync company profiles** for all position symbols (names, sectors, revenue estimates) - Phase 9.1
3. Sync latest market data for all portfolio positions
4. Run 8 calculation engines for all active portfolios
5. Log completion summary

**Typical Duration**: 6-7 minutes total (includes company profile sync + market data + calculations)
**Trading Days Only**: The job will automatically skip on weekends and holidays based on NYSE calendar

## Files

- **`railway_daily_batch.py`** - Main orchestration script
- **`trading_calendar.py`** - NYSE trading day detection utilities
- **`../../railway.json`** - Railway cron service configuration

## Local Testing

```bash
# Test on non-trading day (will skip)
uv run python scripts/automation/railway_daily_batch.py

# Force execution for testing
uv run python scripts/automation/railway_daily_batch.py --force
```

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
   railway run --service sigmasight-backend-cron uv run python scripts/automation/railway_daily_batch.py --force
   ```
   **Note**: The `--service` flag is critical - without it, Railway runs on the default web service.
5. Monitor logs for:
   - ✅ Trading day detection working
   - ✅ **Company profile sync completing** (Phase 9.1)
   - ✅ Market data sync completing
   - ✅ Batch calculations running for all portfolios
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
3. Verify all steps complete successfully
4. If failures occur, check Railway logs for error details

### Monitoring

**Railway Dashboard Logs** (Primary monitoring method):
- Check logs daily after 11:30 PM UTC
- Look for completion message: `✅ All operations completed successfully`
- If errors, check specific portfolio failure messages

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

#### API Rate Limits (429 Errors)
- **Expected behavior** - script has fallback providers
- Polygon API has rate limits, script falls back to FMP
- Private positions (real estate, PE) will fail gracefully - this is normal

#### Market Data Sync Failures
- Check API keys are valid and not expired
- Verify API keys are set in cron service's Variables tab
- Review logs for specific symbols failing

#### Batch Calculation Failures
- Check if specific portfolio is causing issue
- Review logs for detailed error messages
- Verify database schema is up to date (run migrations)

#### Company Profile Sync Failures (Phase 9.1)
**Symptom**: Logs show `❌ Company profile sync failed` or warnings about failed symbols

**Common Causes**:
- **Synthetic symbols** (RENTAL_CONDO, CRYPTO_BTC_ETH, etc.) - Expected failures, these are gracefully skipped
- **Options symbols** (e.g., AAPL250815P00200000) - May not have company profile data, this is normal
- **Rate limiting** - Yahoo Finance API may throttle requests during high traffic

**Expected Behavior**:
- Job continues even if profile sync fails (non-blocking)
- Partial failures are acceptable (e.g., 45/63 symbols synced successfully)
- Exit code still 0 if batch calculations succeed

**When to Investigate**:
- If **ALL** symbols fail to sync (0/63 successful) - check API connectivity
- If major stocks (AAPL, MSFT, etc.) fail consistently - check Yahoo Finance API status
- If profile sync takes >60 seconds - may indicate network issues

**Manual Recovery**:
```bash
# Manually trigger profile sync for testing
railway run --service sigmasight-backend-cron uv run python -c "
import asyncio
from app.batch.market_data_sync import sync_company_profiles
asyncio.run(sync_company_profiles(force_refresh=True))
"
```

**Note**: Company profiles update daily but are not critical for calculations. Missing profiles only affect display metadata (company names, sectors, etc.).

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
- `0` - Success (all portfolios processed)
- `1` - Failure (one or more portfolios failed or fatal error)
- `130` - Interrupted (Ctrl+C)

Railway will retry failed jobs based on `restartPolicyMaxRetries: 3` setting.

### Future Enhancements

Potential improvements documented but not implemented:
- Slack webhook notifications (see TODO4.md blocker #5 resolution)
- Email alerts via SendGrid/AWS SES
- Datadog metrics integration
- Railway webhook → Zapier → Email forwarding

For now, manual Railway dashboard log checking is sufficient.
