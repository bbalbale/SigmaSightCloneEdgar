# Railway CLI Quick Start (Existing Project)

**For users who already have the backend deployed to Railway as a web service.**

Since your backend is already connected to Railway, you just need to create a **second service** (the cron service) in the **same project**.

---

## Prerequisites ✅ (You Already Have These)

- ✅ Railway CLI installed
- ✅ Backend directory linked to Railway project
- ✅ Existing web service running FastAPI

---

## Deployment Steps

### Step 1: Verify Project Link

```bash
cd backend
railway status
```

**Expected output**:
```
Project: SigmaSight (or your project name)
Environment: production
Service: sigmasight-backend-web (or your web service name)
```

If you see your project and web service, you're good! **Skip the `railway link` step** from the main guide.

### Step 2: Create Cron Service in Same Project

```bash
# Create new service (will be added to your existing project)
railway service create sigmasight-backend-cron
```

This creates a **second service** in your Railway project alongside your web service.

### Step 3: Verify Environment Variables

Since you're using **project-level shared variables**, check they're set:

```bash
railway variables --shared
```

**You should see**:
- `DATABASE_URL`
- `POLYGON_API_KEY`
- `FMP_API_KEY`
- `FRED_API_KEY`
- `SECRET_KEY`
- `OPENAI_API_KEY`

If these are already set for your web service, the cron service will **automatically inherit** them. No need to set them again!

### Step 4: Deploy to Cron Service

**Important**: Always use `--service` flag to target the cron service:

```bash
railway up --service sigmasight-backend-cron
```

Without the `--service` flag, it would deploy to your web service instead!

**Expected**: Service deploys successfully but exits immediately (no cron schedule yet).

### Step 5: Test Manually (REQUIRED)

```bash
railway run --service sigmasight-backend-cron uv run python scripts/automation/railway_daily_batch.py --force
```

**Watch logs** to verify success:
```bash
# In another terminal
railway logs --service sigmasight-backend-cron --follow
```

**Look for**:
- ✅ "FORCE MODE: Running batch job"
- ✅ "Market data sync complete"
- ✅ "Batch complete for {portfolio name}"
- ✅ "All operations completed successfully"

### Step 6: Enable Cron Schedule

**Option A: Update railway.json and redeploy**

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

**Option B: Use Railway Dashboard**

1. Go to Railway dashboard → Your project
2. Select `sigmasight-backend-cron` service
3. Settings → Cron Schedule
4. Add: `30 23 * * 1-5`
5. Click "Deploy"

### Step 7: Verify First Automated Run

```bash
# Wait until after 11:30 PM UTC on a weekday
railway logs --service sigmasight-backend-cron --follow
```

---

## Your Project Structure Now

```
Railway Project: SigmaSight
├── sigmasight-backend-web      (FastAPI - always running)
├── sigmasight-backend-cron     (Daily automation - cron schedule)
└── postgres                     (Database - always running)
```

Both services share:
- Same PostgreSQL database
- Same environment variables (via shared variables)
- Same codebase (same GitHub repo)

---

## Common Pitfalls to Avoid

### ❌ Wrong: Deploying to web service by accident
```bash
railway up
# This deploys to whatever service is "linked" (probably web service)
```

### ✅ Correct: Always specify the cron service
```bash
railway up --service sigmasight-backend-cron
railway logs --service sigmasight-backend-cron
railway run --service sigmasight-backend-cron <command>
```

### ❌ Wrong: Creating variables on cron service
```bash
railway variables --set DATABASE_URL="..." --service sigmasight-backend-cron
# Don't do this! Use shared variables instead
```

### ✅ Correct: Use project-level shared variables
```bash
railway variables --shared
# These are automatically available to ALL services
```

---

## Quick Reference

```bash
# View project status
railway status

# List all services in project
railway service list

# Switch between services (interactive)
railway service

# Deploy to cron service
railway up --service sigmasight-backend-cron

# View cron service logs
railway logs --service sigmasight-backend-cron --follow

# Run manual test
railway run --service sigmasight-backend-cron uv run python scripts/automation/railway_daily_batch.py --force

# Check shared variables
railway variables --shared
```

---

## Troubleshooting

### "Project is already linked to another service"
This is expected! You want to create a **second service** in the same project. Use:
```bash
railway service create sigmasight-backend-cron
```

### Deployed to wrong service
Check which service is currently active:
```bash
railway status
```

Always use `--service sigmasight-backend-cron` to be explicit.

### Variables not showing up
Verify they're set at project level (not service level):
```bash
railway variables --shared
```

If missing, set them as shared:
```bash
railway variables --set DATABASE_URL="..." --shared
```

---

## Next Steps After Deployment

1. ✅ Cron service created and deployed
2. ✅ Manual test successful
3. ✅ Cron schedule enabled
4. ⏭️ Wait for first automated run (11:30 PM UTC, weekday)
5. ⏭️ Monitor logs for success
6. ⏭️ Check Railway dashboard shows both services running

---

## Summary

**You already have**: Backend linked to Railway with web service running

**What you're adding**: Second service (cron) for daily automation

**Key difference**: Always use `--service sigmasight-backend-cron` to target the right service

**Same project, two services, shared variables** = Clean separation of web API and batch jobs!
