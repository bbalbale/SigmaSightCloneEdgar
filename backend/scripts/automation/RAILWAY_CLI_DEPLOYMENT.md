# Railway CLI Deployment Guide

Step-by-step guide to deploy the cron service using Railway CLI.

## ⚠️ Railway CLI Key Learnings

**Critical points discovered during actual deployment that differ from typical documentation:**

1. **No standalone service create command**: Use `railway up --service <name>` to auto-create services
2. **Variables do NOT auto-inherit**: Must manually copy environment variables between services
3. **Variable references don't work in CLI**: `${{Postgres.DATABASE_URL}}` syntax only works in Dashboard
4. **Async driver requirement**: Must use `postgresql+asyncpg://` not `postgresql://` for SQLAlchemy async
5. **Services and Environments are siblings**: Both belong to Project, not parent-child relationship

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

## Step 1: Create and Deploy Cron Service

**Note**: Railway CLI doesn't have a standalone `service create` command. The service is created automatically when you first deploy to it.

```bash
# Navigate to backend directory
cd backend

# Deploy to new cron service (auto-creates the service)
railway up --service sigmasight-backend-cron --detach
```

This will:
- Create the `sigmasight-backend-cron` service in your project
- Upload and build the code
- Deploy (will exit immediately since no cron schedule is set yet)

## Step 2: Set Environment Variables

**CRITICAL**: Environment variables do NOT automatically inherit between services. You must manually copy them from your web service to the cron service.

First, check what variables your web service has:
```bash
railway variables --service SigmaSight-BE --kv
```

Then set all required variables for the cron service:

```bash
# IMPORTANT: DATABASE_URL must use postgresql+asyncpg:// for async compatibility
railway variables --service sigmasight-backend-cron \
  --set 'DATABASE_URL=postgresql+asyncpg://user:pass@postgres.railway.internal:5432/railway' \
  --set 'POLYGON_API_KEY=your_key' \
  --set 'FMP_API_KEY=your_key' \
  --set 'FRED_API_KEY=your_key' \
  --set 'SECRET_KEY=your_key' \
  --set 'OPENAI_API_KEY=your_key' \
  --skip-deploys
```

**Key Points**:
- ⚠️ Use `postgresql+asyncpg://` NOT `postgresql://` (async driver requirement)
- ⚠️ Railway's `${{Postgres.DATABASE_URL}}` reference syntax doesn't work in CLI
- ⚠️ Copy the actual connection string from your web service
- ⚠️ Use `--skip-deploys` to set all variables before triggering a redeploy

Verify variables were set:
```bash
railway variables --service sigmasight-backend-cron --kv
```

## Step 3: Verify Initial Deployment

Check deployment status:
```bash
# View recent logs
railway logs --service sigmasight-backend-cron --tail 50
```

The service will exit immediately since no cron schedule is set yet. This is expected.

## Step 4: Manual Testing (CRITICAL - Test Before Enabling Cron)

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

## Step 5: Enable Cron Schedule (After Successful Test)

**Recommended Method**: Update `railway.json` and redeploy via CLI.

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

Commit and redeploy:
```bash
git add railway.json
git commit -m "feat: enable cron schedule for daily automation"
railway up --service sigmasight-backend-cron --detach
```

**Alternative**: Via Railway Dashboard:
1. Go to Railway dashboard → Your project
2. Select `sigmasight-backend-cron` service
3. Go to **Settings** tab
4. Scroll to **Cron Schedule** section
5. Click **"Add Cron Schedule"**
6. Enter: `30 23 * * 1-5`
7. Click **"Deploy"**

## Step 6: Verify Cron Schedule

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
The service is created automatically on first deploy. Use:
```bash
railway up --service sigmasight-backend-cron --detach
```

### "No environment found"
Link to the correct environment:
```bash
railway environment
# Select "production" or your target environment
```

### Variables not showing up
Environment variables must be set per-service. Check:
```bash
railway variables --service sigmasight-backend-cron --kv
```

Copy from your web service:
```bash
railway variables --service SigmaSight-BE --kv
```

### "asyncio extension requires an async driver"
Your `DATABASE_URL` is using `postgresql://` instead of `postgresql+asyncpg://`. Fix:
```bash
railway variables --service sigmasight-backend-cron \
  --set 'DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db' \
  --skip-deploys
```

### Deployment fails
Check build logs:
```bash
railway logs --service sigmasight-backend-cron --tail 100
```

### Wrong service targeted
Always specify the service explicitly with `--service`:
```bash
railway logs --service sigmasight-backend-cron
railway up --service sigmasight-backend-cron
railway run --service sigmasight-backend-cron <command>
```

### Railway variable references like ${{Postgres.DATABASE_URL}} don't work
Railway's variable reference syntax (`${{...}}`) only works in the Railway Dashboard, not in CLI. You must use the actual values when setting variables via CLI.

## Complete Deployment Checklist

- [ ] Railway CLI installed and logged in
- [ ] Project linked via `railway link`
- [ ] Cron service created via first deploy: `railway up --service sigmasight-backend-cron --detach`
- [ ] Environment variables copied from web service and set with `postgresql+asyncpg://` driver
- [ ] Variables verified: `railway variables --service sigmasight-backend-cron --kv`
- [ ] Manual test successful: `railway run --service sigmasight-backend-cron uv run python scripts/automation/railway_daily_batch.py --force`
- [ ] Cron schedule enabled via `railway.json` update and redeploy
- [ ] First automated run verified via logs: `railway logs --service sigmasight-backend-cron --follow`

## Next Steps After Deployment

1. Monitor logs after first scheduled run (11:30 PM UTC on a weekday)
2. Verify all portfolios processed successfully
3. Check for any API rate limit issues (expected, handled gracefully)
4. Document any issues or optimizations needed

## Reference

- Railway CLI Docs: https://docs.railway.app/develop/cli
- Cron Schedule Format: https://crontab.guru/#30_23_*_*_1-5
- Project README: `scripts/automation/README.md`
