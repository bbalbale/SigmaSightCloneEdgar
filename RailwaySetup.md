# Railway Production Deployment - Step-by-Step Setup Guide

**Project**: SigmaSight (Monorepo with Backend + Frontend)
**Environment**: Railway Production
**Last Updated**: 2025-11-11

---

## Overview

This guide walks through deploying both backend and frontend services to Railway from a single monorepo. The backend uses a root-level Dockerfile, and the frontend has its own Dockerfile in the `frontend/` directory.

**Final Architecture:**
```
Railway Production Environment
├── Backend Service (Python/FastAPI)
│   └── Uses: /Dockerfile (root level)
├── Frontend Service (Next.js 16)
│   └── Uses: /frontend/Dockerfile
└── Postgres Database (shared)
```

---

## Prerequisites

- [x] Railway account created
- [x] Railway CLI installed: `railway --version`
- [x] Railway logged in: `railway login`
- [x] GitHub repo connected to Railway
- [x] All code committed and pushed to `main` branch

---

## Phase 1: Configure Backend Service

### Step 1.1: Access Railway Dashboard

1. Go to https://railway.app/dashboard
2. Select your **SigmaSight** project
3. Switch to **Production** environment (dropdown at top)

### Step 1.2: Locate Backend Service

Look for your existing backend service (likely named "SigmaSight-BE" or similar).

**Current URL:** `https://sigmasight-be-production.up.railway.app`

### Step 1.3: Configure Backend Build Settings

Click on Backend Service → **Settings** tab → **Build** section:

**IMPORTANT: Use these exact settings:**

```
Builder: DOCKERFILE
Root Directory: (leave blank or delete any value)
Dockerfile Path: Dockerfile
```

**Why?**
- Root-level `Dockerfile` already copies from `backend/` directory
- Setting root directory to `backend` would break the build
- The Dockerfile at `/Dockerfile` handles everything

### Step 1.4: Verify Backend Variables

Click on Backend Service → **Variables** tab.

**Check these exist:**
```
DATABASE_URL=postgresql://... (from Railway Postgres)
SECRET_KEY=your_jwt_secret
OPENAI_API_KEY=your_openai_key
POLYGON_API_KEY=your_polygon_key
FMP_API_KEY=your_fmp_key
FRED_API_KEY=your_fred_key
```

**Remove if exists:**
```
RAILWAY_DOCKERFILE_PATH (delete this variable)
```

### Step 1.5: Deploy Backend

After updating settings:
1. Backend should **auto-redeploy** (watch Deployments tab)
2. Build time: ~3-5 minutes
3. Verify deployment succeeds

**Health Check:**
```bash
curl https://sigmasight-be-production.up.railway.app/health
# Expected: {"status":"healthy"}
```

---

## Phase 2: Create Frontend Service

### Step 2.1: Create New Service

In Railway Dashboard (Production environment):

1. Click **"+ New"** button (top right)
2. Select **"GitHub Repo"**
3. Select your **SigmaSight** repository
4. Name: `SigmaSight-Frontend-Production`
5. Click **"Add Service"**

### Step 2.2: Configure Frontend Build Settings

Click on the new Frontend Service → **Settings** tab → **Build** section:

**IMPORTANT: Use these exact settings:**

```
Builder: DOCKERFILE
Root Directory: frontend
Dockerfile Path: Dockerfile
```

**Why?**
- Frontend has its own Dockerfile at `/frontend/Dockerfile`
- Root directory tells Railway to work from `frontend/` subdirectory
- Dockerfile path is relative to root directory

### Step 2.3: Configure Frontend Environment Variables

Click on Frontend Service → **Variables** tab.

Add these variables (click **"+ New Variable"** for each):

**Required Variables:**

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_BACKEND_API_URL` | `https://sigmasight-be-production.up.railway.app/api/v1` |
| `BACKEND_URL` | `https://sigmasight-be-production.up.railway.app` |
| `OPENAI_API_KEY` | (copy from backend service) |
| `NODE_ENV` | `production` |
| `PORT` | `3005` |

**Optional Variables:**

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_DEBUG` | `false` |
| `NEXT_PUBLIC_ENABLE_REALTIME_DATA` | `true` |
| `NEXT_PUBLIC_ENABLE_HISTORICAL_CHARTS` | `true` |

### Step 2.4: Generate Public Domain

1. Frontend Service → **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Railway creates URL: `sigmasight-frontend-production.up.railway.app`
4. **Copy this URL** - you'll need it!

### Step 2.5: Deploy Frontend

1. After setting variables, go to **Deployments** tab
2. Railway should auto-deploy
3. If not, click **"Deploy"** button
4. Build time: ~3-5 minutes (first build)

**Health Check:**
```bash
curl https://sigmasight-frontend-production.up.railway.app/api/health
# Expected: {"status":"ok","timestamp":"..."}
```

---

## Phase 3: Verify CORS Configuration

### Step 3.1: Check Backend CORS Settings

The backend CORS configuration should already include the Railway frontend URL (we committed this).

**File:** `backend/app/config.py` (lines 122-128)

Should contain:
```python
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3005",  # Local dev
    "https://sigmasight-frontend-production.up.railway.app",  # Railway
]
```

✅ **Already done** - This was committed in the last push.

### Step 3.2: Verify Backend Redeployed

Backend must redeploy to pick up CORS changes:
1. Check backend **Deployments** tab
2. Latest deployment should be after the git push
3. If not, manually trigger redeploy

---

## Phase 4: End-to-End Verification

### Step 4.1: Test Backend

```bash
# Health check
curl https://sigmasight-be-production.up.railway.app/health

# API docs (should load in browser)
https://sigmasight-be-production.up.railway.app/docs

# Test auth endpoint
curl -X POST https://sigmasight-be-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}'

# Should return JWT token
```

### Step 4.2: Test Frontend

**Browser Tests:**

1. Visit: `https://sigmasight-frontend-production.up.railway.app`
   - ✅ Should see landing page or redirect to `/landing`

2. Go to `/login`
   - ✅ Login form should load

3. Login with demo credentials:
   - Email: `demo_hnw@sigmasight.com`
   - Password: `demo12345`
   - ✅ Should redirect to `/portfolio`

4. Test navigation:
   - ✅ Click navigation dropdown (top right)
   - ✅ All 6 pages accessible:
     - Portfolio Dashboard
     - Public Positions
     - Private Positions
     - Organize
     - AI Chat
     - Settings

5. Test backend integration:
   - ✅ Portfolio page shows real data
   - ✅ No CORS errors in browser console (F12)
   - ✅ API calls succeed (check Network tab)

6. Test AI chat:
   - ✅ Go to `/ai-chat` or `/sigmasight-ai`
   - ✅ Send a test message
   - ✅ Response streams in real-time

### Step 4.3: Check Logs

**Backend Logs:**
```bash
railway logs --service sigmasight-be-production
```

**Frontend Logs:**
```bash
railway logs --service sigmasight-frontend-production
```

Look for:
- ✅ No error messages
- ✅ Successful API requests
- ✅ Health checks returning 200

---

## Phase 5: Post-Deployment Configuration

### Step 5.1: Set Up Monitoring

In Railway Dashboard for each service:

1. Go to **Metrics** tab
2. Monitor:
   - CPU usage
   - Memory usage
   - Network traffic
   - Request count

### Step 5.2: Configure Alerts (Optional)

Railway Dashboard → Service → **Settings** → **Alerts**:

Set up alerts for:
- Deployment failures
- High memory usage (>80%)
- Service crashes
- Health check failures

### Step 5.3: Custom Domain (Optional)

If you want a custom domain:

**Frontend:**
1. Settings → Networking → **Custom Domain**
2. Add domain: `app.yourdomain.com`
3. Configure DNS: `CNAME` to Railway domain
4. SSL auto-provisioned

**Backend:**
1. Settings → Networking → **Custom Domain**
2. Add domain: `api.yourdomain.com`
3. Configure DNS: `CNAME` to Railway domain
4. Update frontend `NEXT_PUBLIC_BACKEND_API_URL` variable

---

## Configuration Summary

### Backend Service Configuration

| Setting | Value |
|---------|-------|
| **Service Name** | SigmaSight-BE-Production |
| **Builder** | DOCKERFILE |
| **Root Directory** | (blank/empty) |
| **Dockerfile Path** | Dockerfile |
| **Domain** | sigmasight-be-production.up.railway.app |
| **Port** | 8000 |
| **Health Endpoint** | /health |

### Frontend Service Configuration

| Setting | Value |
|---------|-------|
| **Service Name** | SigmaSight-Frontend-Production |
| **Builder** | DOCKERFILE |
| **Root Directory** | frontend |
| **Dockerfile Path** | Dockerfile |
| **Domain** | sigmasight-frontend-production.up.railway.app |
| **Port** | 3005 |
| **Health Endpoint** | /api/health |

---

## Troubleshooting

### Backend Build Fails

**Issue:** Build fails with "cannot find Dockerfile"

**Fix:**
```
Backend Service → Settings → Build:
- Root Directory: (blank/empty) ← IMPORTANT
- Dockerfile Path: Dockerfile
```

### Frontend Build Fails with npm Error

**Issue:** ERESOLVE dependency conflict

**Fix:** Already handled! `frontend/Dockerfile` has `--legacy-peer-deps` flag.

If still fails, check:
```
frontend/Dockerfile line 14:
RUN npm ci --prefer-offline --no-audit --legacy-peer-deps
```

### Frontend Can't Connect to Backend

**Issue:** CORS errors in browser console

**Fix:**
1. Check `backend/app/config.py` line 127 includes Railway frontend URL
2. Redeploy backend to pick up CORS changes
3. Verify frontend URL in `ALLOWED_ORIGINS` matches actual Railway domain

### Environment Variables Not Working

**Issue:** Frontend shows undefined variables

**Fix:**
1. Variables must be set BEFORE deployment
2. After adding variables, redeploy:
   - Deployments tab → Click "Redeploy"
3. Check variables in Railway Dashboard match exactly

### Health Check Failing

**Issue:** Railway shows service as unhealthy

**Backend Fix:**
```bash
# Verify endpoint works
curl https://sigmasight-be-production.up.railway.app/health
```

**Frontend Fix:**
```bash
# Verify endpoint works
curl https://sigmasight-frontend-production.up.railway.app/api/health
```

Check `railway.json` files have correct health check paths.

---

## Rollback Procedure

If deployment fails or has critical issues:

### Via Dashboard

1. Service → **Deployments** tab
2. Find last successful deployment (green checkmark)
3. Click **"Redeploy"**

### Via CLI

```bash
# View deployment history
railway deployments

# Rollback to specific deployment
railway rollback <deployment-id>
```

---

## Maintenance & Updates

### Deploying Code Changes

Railway **auto-deploys** on every push to `main`:

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main

# Railway automatically:
# 1. Detects push
# 2. Rebuilds affected services
# 3. Deploys new version
```

### Updating Environment Variables

**Via Dashboard:**
1. Service → Variables
2. Edit variable value
3. Redeploy service

**Via CLI:**
```bash
railway variables set VARIABLE_NAME=new_value
railway up
```

### Manual Redeploy

Force a rebuild without code changes:

**Via Dashboard:**
- Deployments → Latest deployment → **Redeploy**

**Via CLI:**
```bash
railway up --service sigmasight-frontend-production
```

---

## Resource Optimization

### Recommended Resource Limits

**Backend Service:**
- Memory: 1GB
- CPU: Shared (default)
- Reason: FastAPI + calculations need memory

**Frontend Service:**
- Memory: 512MB - 1GB
- CPU: Shared (default)
- Reason: Next.js is lightweight

**Set in:** Settings → Resources

### Cost Optimization

1. **Enable Sleep on Idle** (Hobby Plan):
   - Settings → Enable "Sleep on Idle"
   - Services wake on first request
   - Saves money during low traffic

2. **Monitor Usage:**
   - Dashboard → Usage tab
   - Track execution time
   - Optimize expensive operations

---

## Security Checklist

- [ ] Environment variables contain no secrets in git
- [ ] CORS only allows specific domains (not wildcard)
- [ ] JWT secret is strong and unique
- [ ] API keys are production keys (not dev/sandbox)
- [ ] Database uses secure password
- [ ] Services run as non-root user (Dockerfiles handle this)
- [ ] HTTPS enforced (Railway handles this)

---

## Production Checklist

Before going live with users:

**Backend:**
- [ ] Health endpoint responds
- [ ] API docs accessible at /docs
- [ ] Database migrations applied
- [ ] Demo data seeded (3 portfolios)
- [ ] Batch processing scheduled
- [ ] Logs show no errors

**Frontend:**
- [ ] Landing page loads
- [ ] Login flow works end-to-end
- [ ] All 6 pages accessible
- [ ] AI chat functional
- [ ] Real-time data updating
- [ ] Mobile responsive
- [ ] No console errors

**Integration:**
- [ ] Frontend connects to backend
- [ ] No CORS errors
- [ ] Authentication working
- [ ] API calls succeed
- [ ] WebSocket/SSE streaming works

**Monitoring:**
- [ ] Health checks configured
- [ ] Alerts set up
- [ ] Logging enabled
- [ ] Metrics dashboard reviewed

---

## Support & Resources

**Railway:**
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app

**SigmaSight:**
- Backend Docs: `backend/CLAUDE.md`
- Frontend Docs: `frontend/CLAUDE.md`
- Docker Guide: `frontend/DOCKER.md`
- Full Deployment Guide: `frontend/RAILWAY_DOCKER_DEPLOYMENT.md`

**Railway CLI:**
```bash
railway help              # Show all commands
railway logs              # View logs
railway status            # Check service status
railway variables         # List variables
railway link              # Link to project
```

---

## Quick Reference Commands

```bash
# View backend logs
railway logs --service sigmasight-be-production

# View frontend logs
railway logs --service sigmasight-frontend-production

# Check deployment status
railway status

# Redeploy service
railway up --service <service-name>

# View variables
railway variables

# Set variable
railway variables set KEY=value
```

---

## Success Criteria

✅ **Deployment Complete When:**

1. Backend service healthy at: `https://sigmasight-be-production.up.railway.app`
2. Frontend service healthy at: `https://sigmasight-frontend-production.up.railway.app`
3. Login works with demo credentials
4. All 6 pages accessible and functional
5. No CORS errors in browser console
6. API calls succeed in Network tab
7. AI chat streams responses
8. Health checks passing
9. No errors in Railway logs

---

## Timeline

**Expected total setup time: ~30-45 minutes**

- Phase 1 (Backend): 10 minutes
- Phase 2 (Frontend): 15 minutes
- Phase 3 (CORS): 5 minutes
- Phase 4 (Verification): 10 minutes
- Phase 5 (Post-config): 5 minutes

---

## Next Steps After Deployment

1. **Share Access:**
   - Send frontend URL to users
   - Provide demo credentials if needed

2. **Monitor Performance:**
   - Watch Railway metrics for first 24 hours
   - Check for memory/CPU spikes
   - Review error logs

3. **Optimize:**
   - Adjust resource limits based on usage
   - Enable caching if needed
   - Review slow API endpoints

4. **Scale:**
   - Monitor request volume
   - Upgrade Railway plan if needed
   - Add horizontal scaling if necessary

---

**Deployment Guide Complete!** 🚀

Follow these steps in order and both services will be running on Railway Production.

For detailed troubleshooting, see `frontend/RAILWAY_DOCKER_DEPLOYMENT.md`.
