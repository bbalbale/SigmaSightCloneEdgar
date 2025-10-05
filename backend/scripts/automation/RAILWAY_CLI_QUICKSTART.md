# Railway CLI Quick Start (Existing Project)

**For users who already have the backend deployed to Railway as a web service.**

Since your backend is already connected to Railway, you just need to create a **second service** (the cron service) in the **same project**.

---

## ⚠️ Railway CLI Key Learnings

**Critical points that differ from typical documentation:**

1. **No standalone service create command**: Use `railway up --service <name>` to auto-create
2. **Variables do NOT auto-inherit**: Must manually copy environment variables between services
3. **Variable references don't work in CLI**: `${{...}}` syntax only works in Dashboard, use actual values
4. **Async driver required**: Use `postgresql+asyncpg://` not `postgresql://`
5. **Always use --service flag**: Prevents deploying to wrong service

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

### Step 2: Create Cron Service and Set Variables

**Important**: Railway CLI doesn't have a standalone service create command. Deploy to create the service:

```bash
# Deploy to new cron service (auto-creates it)
railway up --service sigmasight-backend-cron --detach
```

This creates a **second service** in your Railway project alongside your web service.

### Step 3: Copy Environment Variables

**CRITICAL**: Variables do NOT automatically inherit between services. You must copy them manually.

First, get variables from your web service:
```bash
railway variables --service SigmaSight-BE --kv
```

Then set them for the cron service:
```bash
# IMPORTANT: Use postgresql+asyncpg:// not postgresql://
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
- ⚠️ Use `postgresql+asyncpg://` NOT `postgresql://`
- ⚠️ Copy actual values, not Railway's `${{...}}` references
- ⚠️ Use `--skip-deploys` to set all variables before triggering redeploy

Verify:
```bash
railway variables --service sigmasight-backend-cron --kv
```

### Step 4: Test Manually (REQUIRED)

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

### Step 5: Enable Cron Schedule

**Recommended: Update railway.json and redeploy**

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

Then commit and redeploy:
```bash
git add railway.json
git commit -m "feat: enable cron schedule for daily automation"
railway up --service sigmasight-backend-cron --detach
```

**Alternative: Use Railway Dashboard**

1. Go to Railway dashboard → Your project
2. Select `sigmasight-backend-cron` service
3. Settings → Cron Schedule
4. Add: `30 23 * * 1-5`
5. Click "Deploy"

### Step 6: Verify First Automated Run

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

Both services:
- Connect to same PostgreSQL database (must set DATABASE_URL for each)
- Use same codebase (same GitHub repo)
- Require separate environment variable configuration (variables do NOT auto-inherit)

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

### ❌ Wrong: Using postgresql:// instead of postgresql+asyncpg://
```bash
railway variables --set DATABASE_URL="postgresql://..." --service sigmasight-backend-cron
# This will cause "asyncio extension requires an async driver" error
```

### ✅ Correct: Use postgresql+asyncpg:// for async compatibility
```bash
railway variables --set DATABASE_URL="postgresql+asyncpg://..." --service sigmasight-backend-cron
# Async driver required for SQLAlchemy async operations
```

### ❌ Wrong: Using Railway's variable reference syntax in CLI
```bash
railway variables --set DATABASE_URL='${{Postgres.DATABASE_URL}}' --service sigmasight-backend-cron
# The ${{...}} syntax only works in Railway Dashboard, not CLI
```

### ✅ Correct: Use actual values when setting via CLI
```bash
# Copy the actual connection string from your web service
railway variables --service SigmaSight-BE --kv  # Get actual values
railway variables --set DATABASE_URL="postgresql+asyncpg://actual-connection-string" --service sigmasight-backend-cron
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
This is expected! You want to create a **second service** in the same project. Deploy to create:
```bash
railway up --service sigmasight-backend-cron --detach
```

### Deployed to wrong service
Check which service is currently active:
```bash
railway status
```

Always use `--service sigmasight-backend-cron` to be explicit.

### Variables not showing up
Check what's set for the cron service:
```bash
railway variables --service sigmasight-backend-cron --kv
```

Copy from your web service:
```bash
railway variables --service SigmaSight-BE --kv
```

Then set them manually for the cron service (variables do NOT auto-inherit between services).

### "asyncio extension requires an async driver" error
Your DATABASE_URL is using `postgresql://` instead of `postgresql+asyncpg://`:
```bash
railway variables --service sigmasight-backend-cron \
  --set 'DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db' \
  --skip-deploys
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
