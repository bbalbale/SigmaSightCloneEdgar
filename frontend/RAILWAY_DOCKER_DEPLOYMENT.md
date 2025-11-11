# Railway Docker Deployment Guide - SigmaSight Frontend

**Purpose**: Complete walkthrough for deploying the Dockerized Next.js frontend to Railway

**Last Updated**: 2025-11-11

---

## Overview

This guide walks you through deploying the SigmaSight frontend using the updated Docker configuration to Railway. The frontend will run as a containerized service alongside your existing backend deployment.

### What You'll Deploy

- **Frontend Service**: Next.js 16 application in Docker container
- **Port**: 3005 (internal), exposed via Railway's public URL
- **Build**: Multi-stage Docker build (~297MB optimized image)
- **Health Check**: `/api/health` endpoint for monitoring
- **Backend Integration**: Connects to your existing Railway backend

---

## Prerequisites

### 1. Railway CLI Installed

```bash
# Check if Railway CLI is installed
railway --version

# If not installed, install it:
# Windows (PowerShell)
iwr https://railway.app/install.ps1 | iex

# macOS/Linux
curl -fsSL https://railway.app/install.sh | sh
```

### 2. Railway Account & Login

```bash
# Login to Railway
railway login

# Verify you're logged in
railway whoami
```

### 3. Git Repository

```bash
# Ensure your changes are committed and pushed
cd C:\Users\BenBalbale\CascadeProjects\SigmaSight
git status

# Should show clean working tree
```

---

## Deployment Steps

### Step 1: Create New Railway Service

#### Option A: Via Railway Web Dashboard (Recommended)

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Select your **SigmaSight** project
3. Click **"New Service"** → **"GitHub Repo"**
4. Select your **SigmaSight** repository
5. Name the service: `sigmasight-frontend`
6. Railway will detect the Dockerfile automatically

#### Option B: Via Railway CLI

```bash
cd C:\Users\BenBalbale\CascadeProjects\SigmaSight

# Link to your existing Railway project
railway link

# Create new service from current directory
railway up
```

### Step 2: Configure Build Settings

Railway needs to know where to find the Dockerfile:

#### Via Web Dashboard

1. Go to your `sigmasight-frontend` service settings
2. Navigate to **"Build"** tab
3. Set **Root Directory**: `frontend`
4. Set **Dockerfile Path**: `frontend/Dockerfile`
5. Build Command: (leave empty - Docker handles this)

#### Via CLI

```bash
# Set the root directory for the service
railway variables set ROOT_DIR=frontend

# Railway will automatically detect Dockerfile in that directory
```

### Step 3: Configure Environment Variables

Railway needs these environment variables to build and run the frontend:

#### Required Build-Time Variables

```bash
# Via Railway CLI
railway variables set \
  NEXT_PUBLIC_BACKEND_API_URL=https://your-backend.up.railway.app/api/v1 \
  BACKEND_URL=https://your-backend.up.railway.app \
  OPENAI_API_KEY=your_openai_key_here \
  NODE_ENV=production
```

#### Via Web Dashboard

1. Go to service **"Variables"** tab
2. Add each variable:
   - `NEXT_PUBLIC_BACKEND_API_URL` = `https://sigmasight-be-production.up.railway.app/api/v1`
   - `BACKEND_URL` = `https://sigmasight-be-production.up.railway.app`
   - `OPENAI_API_KEY` = (your OpenAI API key)
   - `NODE_ENV` = `production`

#### Optional Configuration Variables

```bash
# Add these if you want to customize:
NEXT_PUBLIC_DEBUG=false
NEXT_PUBLIC_DEFAULT_PORTFOLIO_ID=your_default_portfolio_uuid
NEXT_PUBLIC_MARKET_DATA_REFRESH_INTERVAL=30000
NEXT_PUBLIC_ENABLE_REALTIME_DATA=true
NEXT_PUBLIC_ENABLE_HISTORICAL_CHARTS=true
```

### Step 4: Configure Networking

#### Set Port

Railway needs to know which port your app runs on:

```bash
# Via CLI
railway variables set PORT=3005

# Via Dashboard
# Add variable: PORT = 3005
```

#### Enable Public Domain

1. In Railway Dashboard, go to your frontend service
2. Click **"Settings"** → **"Networking"**
3. Click **"Generate Domain"**
4. Railway will provide a public URL like: `sigmasight-frontend-production.up.railway.app`

### Step 5: Create railway.json Config

Create a `railway.json` file in the `frontend/` directory:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 300
  }
}
```

### Step 6: Deploy!

#### Automatic Deployment (Recommended)

Once configured, Railway will automatically deploy on every push to `main`:

```bash
# Push your changes
git add .
git commit -m "Configure Railway frontend deployment"
git push origin main

# Railway will automatically detect the push and deploy
```

#### Manual Deployment

```bash
cd frontend
railway up

# Or deploy specific service
railway up --service sigmasight-frontend
```

### Step 7: Monitor Deployment

#### View Build Logs

```bash
# Via CLI
railway logs

# Via Dashboard
# Go to service → "Deployments" tab → Click latest deployment
```

#### Expected Build Output

You should see:
```
#1 Building dependencies stage...
#2 Installing npm packages...
#3 Building Next.js application...
#4 Creating production runner...
#5 Deployment complete!
```

#### Check Health

Once deployed, verify the health endpoint:

```bash
# Replace with your Railway domain
curl https://sigmasight-frontend-production.up.railway.app/api/health

# Expected response:
# {"status":"ok","timestamp":"2025-11-11T..."}
```

---

## Environment Variable Reference

### Required Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `NEXT_PUBLIC_BACKEND_API_URL` | Backend API base URL (client-side) | `https://sigmasight-be-production.up.railway.app/api/v1` |
| `BACKEND_URL` | Backend URL (server-side proxy) | `https://sigmasight-be-production.up.railway.app` |
| `OPENAI_API_KEY` | OpenAI API key for chat features | `sk-proj-...` |
| `NODE_ENV` | Environment mode | `production` |
| `PORT` | Application port | `3005` |

### Optional Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `NEXT_PUBLIC_DEBUG` | Enable debug mode | `false` |
| `NEXT_PUBLIC_DEFAULT_PORTFOLIO_ID` | Default portfolio UUID | (none) |
| `NEXT_PUBLIC_MARKET_DATA_REFRESH_INTERVAL` | Data refresh interval (ms) | `30000` |
| `NEXT_PUBLIC_ENABLE_REALTIME_DATA` | Enable real-time data | `true` |
| `NEXT_PUBLIC_ENABLE_HISTORICAL_CHARTS` | Enable historical charts | `true` |

---

## Connecting Frontend to Backend

Your Railway setup should have two services:

1. **Backend Service**: `sigmasight-be-production` (already deployed)
2. **Frontend Service**: `sigmasight-frontend` (new)

### Get Backend URL

```bash
# Via CLI (from backend directory)
cd backend
railway domain

# Or via Dashboard
# Go to backend service → Settings → Networking → copy domain
```

### Update Frontend Environment

Use the backend URL in frontend environment variables:

```bash
# Example backend URL
BACKEND_URL=https://sigmasight-be-production.up.railway.app
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-production.up.railway.app/api/v1
```

---

## Verification Checklist

After deployment, verify everything works:

### 1. Health Check

```bash
curl https://your-frontend-domain.up.railway.app/api/health
```

Expected: `{"status":"ok",...}`

### 2. Homepage Loads

Visit: `https://your-frontend-domain.up.railway.app`

Expected: Landing page or redirect to `/landing`

### 3. Backend Connection

1. Visit `/login` page
2. Login with demo credentials: `demo_hnw@sigmasight.com` / `demo12345`
3. Should successfully authenticate and redirect to `/portfolio`

### 4. Check Logs

```bash
railway logs --service sigmasight-frontend
```

Look for:
- ✅ "Server listening on port 3005"
- ✅ No error messages
- ✅ Health check requests returning 200

### 5. Browser DevTools

1. Open browser DevTools (F12)
2. Go to Network tab
3. Visit a page in the app
4. Verify API calls go to correct backend URL
5. Check for any CORS errors (should be none)

---

## Troubleshooting

### Build Fails with Dependency Errors

**Problem**: `ERESOLVE could not resolve` during npm install

**Solution**: Ensure Dockerfile has `--legacy-peer-deps` flag
```dockerfile
RUN npm ci --prefer-offline --no-audit --legacy-peer-deps && \
    npm cache clean --force
```

### Environment Variables Not Working

**Problem**: Frontend can't connect to backend

**Solution**:
1. Verify variables are set in Railway Dashboard
2. Variables must be set BEFORE deployment
3. Redeploy after adding variables:
   ```bash
   railway up --service sigmasight-frontend
   ```

### Port Already in Use

**Problem**: Railway shows port conflict

**Solution**: Ensure `PORT=3005` is set in Railway variables

### Health Check Failing

**Problem**: Railway shows service as unhealthy

**Solution**:
1. Check `/api/health` route exists in `app/api/health/route.ts`
2. Verify health check path in `railway.json`: `"healthcheckPath": "/api/health"`
3. Increase timeout: `"healthcheckTimeout": 300`

### CORS Errors

**Problem**: Browser shows CORS errors when calling backend

**Solution**: Backend must have CORS configured to allow frontend domain
```python
# In backend app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-domain.up.railway.app",
        "http://localhost:3005"  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Build Takes Too Long

**Problem**: Docker build exceeds Railway timeout

**Solution**:
1. Ensure `.dockerignore` is properly configured
2. Check that `node_modules` and `.next` are in `.dockerignore`
3. Verify multi-stage build is working (should use layer caching)

---

## Updating Deployment

### Code Changes

```bash
# Make your changes
git add .
git commit -m "Update frontend feature"
git push origin main

# Railway will automatically redeploy
```

### Environment Variable Changes

```bash
# Via CLI
railway variables set VARIABLE_NAME=new_value

# Via Dashboard
# Go to service → Variables → Edit → Save
# Then redeploy:
railway up
```

### Force Rebuild

```bash
# Force a full rebuild (clears cache)
railway up --service sigmasight-frontend
```

---

## Cost Optimization

Railway bills based on usage. Optimize costs:

### 1. Use Efficient Docker Build

- ✅ Multi-stage build (already configured)
- ✅ Minimal base image (node:20-alpine)
- ✅ Proper layer caching

### 2. Set Resource Limits

In Railway Dashboard → Settings → Resources:
- Memory: 512MB-1GB (sufficient for Next.js)
- CPU: Shared (default)

### 3. Enable Sleep on Idle (Hobby Plan)

Railway can sleep services on inactivity:
- Settings → Enable "Sleep on Idle"
- Service wakes on first request

---

## Production Checklist

Before going live with users:

- [ ] Environment variables set correctly
- [ ] Backend URL points to production backend
- [ ] OPENAI_API_KEY is production key (not dev)
- [ ] NODE_ENV=production
- [ ] Health check endpoint working
- [ ] Custom domain configured (optional)
- [ ] CORS configured on backend for frontend domain
- [ ] Monitoring/logging configured
- [ ] Test authentication flow end-to-end
- [ ] Verify all 6 pages load correctly
- [ ] Test AI chat functionality
- [ ] Check mobile responsiveness

---

## Monitoring & Maintenance

### View Logs

```bash
# Real-time logs
railway logs --service sigmasight-frontend

# Last 100 lines
railway logs --service sigmasight-frontend --lines 100
```

### Metrics

Railway Dashboard → Service → Metrics shows:
- CPU usage
- Memory usage
- Network traffic
- Request count

### Alerts

Set up alerts in Railway Dashboard:
- Deployment failures
- Health check failures
- Resource usage spikes

---

## Rollback

If deployment fails or has issues:

### Via Dashboard

1. Go to service → Deployments
2. Click on previous successful deployment
3. Click "Redeploy"

### Via CLI

```bash
# View deployment history
railway deployments

# Rollback to specific deployment
railway rollback <deployment-id>
```

---

## Next Steps

After successful deployment:

1. **Custom Domain** (Optional)
   - Add your own domain in Railway Settings → Networking
   - Configure DNS: `CNAME` to Railway domain

2. **Analytics** (Optional)
   - Add analytics service (Google Analytics, Plausible, etc.)
   - Set `NEXT_PUBLIC_ANALYTICS_ID` environment variable

3. **Error Tracking** (Optional)
   - Set up Sentry for error monitoring
   - Add `NEXT_PUBLIC_SENTRY_DSN` environment variable

4. **CI/CD** (Already configured!)
   - Railway automatically deploys on `git push`
   - Configure branch-specific deployments if needed

---

## Support Resources

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Railway Status**: https://status.railway.app
- **SigmaSight Docs**: See `frontend/DOCKER.md` for Docker-specific details

---

## Summary

Your Dockerized frontend is now deployed to Railway! 🚀

**What You Have:**
- ✅ Containerized Next.js 16 application
- ✅ Automatic deployments on git push
- ✅ Health monitoring
- ✅ Connected to production backend
- ✅ Public HTTPS domain
- ✅ Production-ready configuration

**Access Your App:**
- Frontend: `https://your-frontend-domain.up.railway.app`
- Backend API: `https://sigmasight-be-production.up.railway.app/api/v1`

**Maintenance:**
- Push to `main` → Auto-deploy
- Update env vars → Redeploy
- Monitor via Railway Dashboard

Enjoy your production SigmaSight platform! 🎉
