# Railway Daily Batch Automation

Automated daily workflow for market data synchronization and portfolio calculations.

## Overview

This automation runs **every weekday at 11:30 PM UTC** (6:30pm EST / 7:30pm EDT) to:
1. Check if today is a trading day (NYSE calendar)
2. Sync latest market data for all portfolio positions
3. Run 8 calculation engines for all active portfolios
4. Log completion summary

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

### Prerequisites

1. **Shared Environment Variables** (set at Project level in Railway)
   - `DATABASE_URL` - PostgreSQL connection string
   - `POLYGON_API_KEY` - Market data API key
   - `FMP_API_KEY` - Financial Modeling Prep API key
   - `FRED_API_KEY` - Federal Reserve economic data API key
   - `SECRET_KEY` - JWT secret
   - `OPENAI_API_KEY` - OpenAI API key for chat

### Deployment Steps

#### Step 1: Create Railway Service

1. Go to Railway Project → **+ New Service**
2. Select **"GitHub Repo"** as source
3. Choose repository: `SigmaSight-BE`
4. Set **Root Directory**: `backend`
5. Name service: `sigmasight-backend-cron`

#### Step 2: Configure Service

1. Go to service **Settings**:
   - **Start Command**: `uv run python scripts/automation/railway_daily_batch.py`
   - **Cron Schedule**: Leave DISABLED initially (test manually first)

2. Verify environment variables (should auto-inherit from shared):
   - Check **Variables** tab shows all required vars from project-level shared variables
   - If not visible, ensure they're set as `${{shared.VARIABLE_NAME}}` at project level

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
- Verify `DATABASE_URL` shared variable is set correctly
- Check PostgreSQL service is running
- Ensure cron service has access to shared variables

#### API Rate Limits (429 Errors)
- **Expected behavior** - script has fallback providers
- Polygon API has rate limits, script falls back to FMP
- Private positions (real estate, PE) will fail gracefully - this is normal

#### Market Data Sync Failures
- Check API keys are valid and not expired
- Verify API keys are set as shared variables
- Review logs for specific symbols failing

#### Batch Calculation Failures
- Check if specific portfolio is causing issue
- Review logs for detailed error messages
- Verify database schema is up to date (run migrations)

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
