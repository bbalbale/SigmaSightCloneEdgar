# Railway CLI Deployment Guide

Step-by-step guide to deploy the cron service using Railway CLI.

## Prerequisites

1. **Install Railway CLI**:
   ```bash
   npm i -g @railway/cli
   ```

2. **Login to Railway**:
   ```bash
   railway login
   ```

3. **Link to your project**:
   ```bash
   # Navigate to backend directory
   cd backend

   # Link to existing Railway project
   railway link
   # Select your SigmaSight project when prompted
   ```

## Step 1: Create Cron Service

```bash
# Create a new service in your Railway project
railway service create sigmasight-backend-cron
```

This creates a new service but doesn't deploy anything yet.

## Step 2: Link CLI to Cron Service

```bash
# Switch to the new cron service
railway service
# Select "sigmasight-backend-cron" from the list
```

Alternatively, specify the service directly:
```bash
export RAILWAY_SERVICE=sigmasight-backend-cron
```

## Step 3: Set Environment Variables

Since you're using **shared variables at project level**, the cron service should automatically inherit them. Verify:

```bash
# Check current environment variables for cron service
railway variables --service sigmasight-backend-cron
```

**Expected variables** (should auto-inherit from project-level shared variables):
- `DATABASE_URL`
- `POLYGON_API_KEY`
- `FMP_API_KEY`
- `FRED_API_KEY`
- `SECRET_KEY`
- `OPENAI_API_KEY`

If any are missing, set them at the **project level** (shared):
```bash
# Set shared variable (available to all services)
railway variables --set DATABASE_URL="postgresql+asyncpg://..." --shared
railway variables --set POLYGON_API_KEY="pk_..." --shared
railway variables --set FMP_API_KEY="..." --shared
railway variables --set FRED_API_KEY="..." --shared
railway variables --set SECRET_KEY="..." --shared
railway variables --set OPENAI_API_KEY="sk-..." --shared
```

Or verify they're already set:
```bash
# List all shared variables
railway variables --shared
```

## Step 4: Deploy the Service

The `railway.json` file in the backend directory already configures the start command and restart policy.

Deploy from the backend directory:
```bash
# Make sure you're in the backend directory
cd /path/to/SigmaSight-BE/backend

# Deploy to cron service
railway up --service sigmasight-backend-cron

# The deployment will exit immediately (no cron schedule set yet)
```

**Note**: The service will deploy but exit immediately since no cron schedule is set. This is expected.

## Step 5: Manual Testing (CRITICAL - Test Before Enabling Cron)

Test the script manually to ensure it works:

```bash
# Run the script manually on the cron service with --force flag
railway run --service sigmasight-backend-cron uv run python scripts/automation/railway_daily_batch.py --force
```

**Watch the logs** to verify:
- ✅ Trading day detection works
- ✅ Market data sync completes
- ✅ Batch calculations run for all portfolios
- ✅ Completion summary shows success

Monitor logs in another terminal:
```bash
railway logs --service sigmasight-backend-cron
```

## Step 6: Enable Cron Schedule (After Successful Test)

Unfortunately, **cron schedules cannot be set via Railway CLI** - you must use the dashboard for this.

**Via Railway Dashboard**:
1. Go to Railway dashboard → Your project
2. Select `sigmasight-backend-cron` service
3. Go to **Settings** tab
4. Scroll to **Cron Schedule** section
5. Click **"Add Cron Schedule"**
6. Enter: `30 23 * * 1-5`
7. Click **"Deploy"**

**Or update railway.json and redeploy**:

Edit `backend/railway.json` to add the cron schedule:
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "deploy": {
    "cronSchedule": "30 23 * * 1-5",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3,
    "startCommand": "uv run python scripts/automation/railway_daily_batch.py"
  }
}
```

Then redeploy:
```bash
railway up --service sigmasight-backend-cron
```

## Step 7: Verify Cron Schedule

Check that the cron schedule is active:

**Via CLI (check logs after next scheduled time)**:
```bash
# Wait until after 11:30 PM UTC on a weekday
railway logs --service sigmasight-backend-cron --follow
```

**Via Dashboard**:
- Go to service → Settings
- Verify "Cron Schedule" shows: `30 23 * * 1-5`
- Check Deployments tab for automated runs

## Quick Reference Commands

```bash
# Check which service you're linked to
railway status

# Switch services
railway service

# View logs (follow mode)
railway logs --service sigmasight-backend-cron --follow

# View logs (last 100 lines)
railway logs --service sigmasight-backend-cron --tail 100

# Redeploy after code changes
railway up --service sigmasight-backend-cron

# List all services in project
railway service list

# Check environment variables
railway variables --service sigmasight-backend-cron

# Run manual test
railway run --service sigmasight-backend-cron uv run python scripts/automation/railway_daily_batch.py --force
```

## Troubleshooting

### "Service not found"
Make sure you created the service first:
```bash
railway service create sigmasight-backend-cron
```

### "No environment found"
Link to the correct environment:
```bash
railway environment
# Select "production" or your target environment
```

### Variables not showing up
Check if they're set as shared at project level:
```bash
railway variables --shared
```

### Deployment fails
Check build logs:
```bash
railway logs --service sigmasight-backend-cron --deployment
```

### Wrong service targeted
Always specify the service explicitly:
```bash
railway logs --service sigmasight-backend-cron
railway up --service sigmasight-backend-cron
railway run --service sigmasight-backend-cron <command>
```

## Complete Deployment Checklist

- [ ] Railway CLI installed and logged in
- [ ] Project linked via `railway link`
- [ ] Cron service created: `railway service create sigmasight-backend-cron`
- [ ] Shared variables verified: `railway variables --shared`
- [ ] Service deployed: `railway up --service sigmasight-backend-cron`
- [ ] Manual test successful: `railway run --service sigmasight-backend-cron ...`
- [ ] Cron schedule enabled (via dashboard or railway.json update)
- [ ] First automated run verified via logs

## Next Steps After Deployment

1. Monitor logs after first scheduled run (11:30 PM UTC on a weekday)
2. Verify all portfolios processed successfully
3. Check for any API rate limit issues (expected, handled gracefully)
4. Document any issues or optimizations needed

## Reference

- Railway CLI Docs: https://docs.railway.app/develop/cli
- Cron Schedule Format: https://crontab.guru/#30_23_*_*_1-5
- Project README: `scripts/automation/README.md`
