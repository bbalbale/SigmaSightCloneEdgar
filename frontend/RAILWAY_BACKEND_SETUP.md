# Connecting Frontend to Railway Backend

This guide explains how to configure your local frontend development environment to connect to the remote Railway backend instead of localhost.

## CORS Configuration

**Good news**: The Railway backend already allows `http://localhost:3005` in its CORS configuration!

The backend (`app/config.py`) has these allowed origins:
- `http://localhost:3000` (React dev)
- `http://localhost:3005` (Next.js dev) ✅ **Your local frontend**
- `http://localhost:5173` (Vite dev)
- `https://sigmasight-frontend.vercel.app` (Production)

**This means**:
- ✅ Local frontend (localhost:3005) → Railway backend: **Works immediately**
- ✅ No CORS configuration needed for development
- ⚠️ If deploying frontend to production, you'll need to add that URL to backend's ALLOWED_ORIGINS

---

## Quick Start

### Option 1: Environment Variable Override (Recommended)

**For npm development server**:
```bash
cd frontend
NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1 npm run dev
```

**For Docker**:
```bash
cd frontend
docker build --build-arg NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1 -t sigmasight-frontend .
docker run -d -p 3005:3005 --name frontend sigmasight-frontend
```

### Option 2: Edit .env File

1. **Get your Railway backend URL**:
   ```bash
   cd ../backend
   railway status
   # Or check Railway dashboard at https://railway.app
   ```

2. **Update frontend/.env**:
   ```bash
   # Change these lines:
   NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1
   BACKEND_API_URL=https://your-app.railway.app/api/v1
   ```

3. **Restart frontend**:
   ```bash
   # If using npm:
   npm run dev

   # If using Docker:
   docker stop frontend && docker rm frontend
   docker run -d -p 3005:3005 --name frontend sigmasight-frontend
   ```

---

## Detailed Configuration

### Step 1: Find Your Railway Backend URL

**Option A: Using Railway CLI**
```bash
cd backend
railway status

# Look for output like:
# Service: sigmasight-backend
# URL: https://sigmasight-backend-production.up.railway.app
```

**Option B: Railway Dashboard**
1. Visit https://railway.app
2. Navigate to your SigmaSight project
3. Click on the backend service
4. Find the "Domains" section - copy the URL

**Option C: Check Railway Environment**
```bash
cd backend
railway variables

# Look for RAILWAY_STATIC_URL or similar
```

### Step 2: Update Frontend Configuration

**Current .env Configuration (Local)**:
```env
# Backend Integration (localhost)
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
BACKEND_API_URL=http://localhost:8000/api/v1
```

**Updated .env Configuration (Railway)**:
```env
# Backend Integration (Railway)
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-backend-production.up.railway.app/api/v1
BACKEND_API_URL=https://sigmasight-backend-production.up.railway.app/api/v1
```

**Important Notes**:
- ✅ Use `https://` (not `http://`)
- ✅ Include `/api/v1` at the end
- ✅ No trailing slash
- ✅ Both variables must match (NEXT_PUBLIC_ prefix is for client-side, non-prefixed is for server-side)

### Step 3: Restart Your Frontend

**If using npm dev server**:
```bash
# Stop the current server (Ctrl+C)
npm run dev
```

**If using Docker**:
```bash
# Rebuild with new environment variable
docker stop frontend && docker rm frontend
docker build -t sigmasight-frontend .
docker run -d -p 3005:3005 --name frontend sigmasight-frontend
```

### Step 4: Verify Connection

**1. Check Browser DevTools**:
```bash
# Start frontend
npm run dev  # or Docker equivalent

# Open browser to http://localhost:3005
# Open DevTools (F12) → Network tab
# Login and watch API calls
# Verify they go to Railway URL (not localhost:8000)
```

**2. Test Authentication**:
```bash
# Login with demo credentials:
# Email: demo_hnw@sigmasight.com
# Password: demo12345

# Should see successful login and redirect to /portfolio
```

**3. Check Console for Errors**:
```javascript
// Should NOT see errors like:
// "Failed to fetch" or "CORS error" or "Network error"
```

---

## Environment Variable Reference

### All Backend-Related Variables

```env
# Backend API URLs
NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1
BACKEND_API_URL=https://your-app.railway.app/api/v1

# GPT Agent (if using separate deployment)
NEXT_PUBLIC_GPT_AGENT_URL=https://your-gpt-agent.railway.app
GPT_AGENT_URL=https://your-gpt-agent.railway.app
```

### Variables That DON'T Need Changes

These should remain as-is (they're for backend, not frontend):
```env
# Database (backend only)
DATABASE_URL=postgresql+asyncpg://...

# API Keys (backend only)
POLYGON_API_KEY=...
FMP_API_KEY=...
OPENAI_API_KEY=...

# Auth (must match backend)
SECRET_KEY=...
```

---

## Common Patterns

### Pattern 1: Multiple .env Files (Recommended for Teams)

Create separate environment files:

**.env.local** (default - localhost):
```env
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
BACKEND_API_URL=http://localhost:8000/api/v1
```

**.env.railway** (Railway backend):
```env
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-backend-production.up.railway.app/api/v1
BACKEND_API_URL=https://sigmasight-backend-production.up.railway.app/api/v1
```

**Usage**:
```bash
# Use local backend
npm run dev

# Use Railway backend
cp .env.railway .env
npm run dev

# Or use env-cmd package:
npm install --save-dev env-cmd
npx env-cmd -f .env.railway npm run dev
```

### Pattern 2: npm Scripts (Add to package.json)

Add these to your `package.json`:
```json
{
  "scripts": {
    "dev": "next dev -p 3005",
    "dev:local": "NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1 next dev -p 3005",
    "dev:railway": "NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1 next dev -p 3005"
  }
}
```

**Usage**:
```bash
npm run dev:local     # Local backend
npm run dev:railway   # Railway backend
```

### Pattern 3: Docker Compose (For Full Stack)

Create `docker-compose.yml` in root:
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      args:
        NEXT_PUBLIC_BACKEND_API_URL: ${BACKEND_URL}
    ports:
      - "3005:3005"
    environment:
      - NEXT_PUBLIC_BACKEND_API_URL=${BACKEND_URL}
```

**Usage**:
```bash
# Local backend
BACKEND_URL=http://localhost:8000/api/v1 docker-compose up

# Railway backend
BACKEND_URL=https://your-app.railway.app/api/v1 docker-compose up
```

---

## Troubleshooting

### Issue: API Calls Still Going to Localhost

**Symptom**: Browser DevTools shows requests to `localhost:8000`

**Solutions**:
1. **Hard refresh** browser (Ctrl+Shift+R / Cmd+Shift+R)
2. **Clear browser cache**
3. **Restart dev server** after .env changes
4. **Check .env file** - verify changes saved
5. **Verify NEXT_PUBLIC_ prefix** - required for client-side access

```bash
# Debug: Print environment variable
console.log('Backend URL:', process.env.NEXT_PUBLIC_BACKEND_API_URL)
```

### Issue: CORS Errors

**Symptom**: `Access-Control-Allow-Origin` errors in console

**Important**: The Railway backend **already allows** `http://localhost:3005`, so CORS should work by default.

**If you still see CORS errors**:

1. **Verify the backend is actually on Railway**:
   ```bash
   # Check Network tab in DevTools - requests should go to Railway URL
   # NOT localhost:8000
   ```

2. **Hard refresh browser** (clear cached CORS preflight responses):
   ```
   Ctrl+Shift+R (Windows/Linux)
   Cmd+Shift+R (Mac)
   ```

3. **Check Railway backend logs** for CORS-related errors:
   ```bash
   railway logs --tail 100
   # Look for "CORS" or "Access-Control-Allow-Origin"
   ```

4. **Verify backend CORS config** (should already include localhost:3005):
   ```bash
   # In backend repo:
   grep -A 5 "ALLOWED_ORIGINS" app/config.py
   # Should show: "http://localhost:3005"
   ```

5. **If deploying frontend to production** (not localhost):
   - Add your production URL to `backend/app/config.py` ALLOWED_ORIGINS:
     ```python
     ALLOWED_ORIGINS: List[str] = [
         "http://localhost:3005",
         "https://your-frontend.railway.app",  # Add this
     ]
     ```
   - Redeploy backend to Railway

### Issue: Authentication Fails

**Symptom**: Login returns 401 or JWT errors

**Solutions**:
1. **Verify SECRET_KEY matches**:
   ```bash
   # frontend/.env and backend/.env must have same SECRET_KEY
   ```

2. **Check Railway backend is running**:
   ```bash
   curl https://your-app.railway.app/api/v1/auth/login
   # Should return 405 Method Not Allowed (expects POST)
   ```

3. **Verify backend has demo data**:
   ```bash
   railway ssh
   uv run python -c "from app.models.users import User; print('Backend ready')"
   ```

### Issue: 404 Errors on API Calls

**Symptom**: All API calls return 404

**Solutions**:
1. **Check URL includes /api/v1**:
   ```env
   # ✅ CORRECT
   NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1

   # ❌ WRONG (missing /api/v1)
   NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app
   ```

2. **Verify Railway deployment**:
   ```bash
   railway status
   railway logs --tail 50
   ```

### Issue: Slow API Responses

**Symptom**: API calls take 3-5 seconds

**Causes**:
- Railway cold starts (free tier)
- Backend not optimized for production
- Database connection issues

**Solutions**:
1. **Keep backend warm** with uptime monitor
2. **Check Railway logs** for performance issues
3. **Use Railway Pro** (paid tier, no cold starts)

### Issue: Environment Variable Not Updating

**Symptom**: Changed .env but still using old value

**Solutions**:
1. **Restart dev server** (npm run dev)
2. **Rebuild Docker image**:
   ```bash
   docker stop frontend && docker rm frontend
   docker build --no-cache -t sigmasight-frontend .
   docker run -d -p 3005:3005 --name frontend sigmasight-frontend
   ```

3. **Check .env.local** (overrides .env):
   ```bash
   # Next.js loads in this order:
   # .env.local (highest priority)
   # .env.development
   # .env
   ```

---

## Quick Reference

### Switch to Railway Backend
```bash
# 1. Update .env
sed -i '' 's|http://localhost:8000|https://your-app.railway.app|g' .env

# 2. Restart frontend
npm run dev
```

### Switch Back to Local Backend
```bash
# 1. Update .env
sed -i '' 's|https://your-app.railway.app|http://localhost:8000|g' .env

# 2. Restart frontend
npm run dev
```

### Verify Current Configuration
```bash
# Check .env file
grep BACKEND_API_URL .env

# Check browser console
# Open DevTools → Console
console.log(process.env.NEXT_PUBLIC_BACKEND_API_URL)
```

---

## Best Practices

### For Development
- ✅ Use **local backend** by default (faster, easier debugging)
- ✅ Use **Railway backend** when testing production deployment
- ✅ Keep `.env.example` updated with Railway URL format
- ✅ Document Railway URL in team wiki/notes

### For Teams
- ✅ Create `.env.local` and `.env.railway` files
- ✅ Add `.env.local` to `.gitignore` (already done)
- ✅ Share Railway URL in team documentation
- ✅ Use npm scripts (`dev:local`, `dev:railway`)

### For Production Frontend Deployment
- ✅ Set environment variables in Railway/Vercel dashboard
- ✅ Never commit Railway URLs to git (use env vars)
- ✅ Use Railway private networking if both frontend/backend on Railway
- ✅ **CRITICAL**: Add production frontend URL to backend CORS:
  ```python
  # backend/app/config.py
  ALLOWED_ORIGINS: List[str] = [
      "http://localhost:3005",  # Local dev
      "https://your-production-frontend.com",  # Add this!
  ]
  ```
  - Then redeploy backend to Railway
  - Without this, production frontend will get CORS errors

---

## Railway Backend Health Check

Before connecting frontend, verify backend is working:

```bash
# 1. Check backend is running
curl https://your-app.railway.app/api/v1/auth/login

# Should return: {"detail":"Method Not Allowed"}
# This confirms backend is up and routing works

# 2. Test authentication endpoint
curl -X POST https://your-app.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo_hnw@sigmasight.com","password":"demo12345"}'

# Should return: {"access_token":"...","token_type":"bearer"}

# 3. Check backend logs
railway logs --tail 100
```

---

## Summary

**To connect to Railway backend**:

1. Get Railway URL: `railway status`
2. Update `.env`: `NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1`
3. Restart frontend: `npm run dev`
4. Test login: `demo_hnw@sigmasight.com` / `demo12345`
5. Verify in DevTools: API calls go to Railway URL

**Common gotchas**:
- Don't forget `https://` (not `http://`)
- Don't forget `/api/v1` at the end
- Update BOTH variables (NEXT_PUBLIC_BACKEND_API_URL and BACKEND_API_URL)
- Hard refresh browser after changes

**Switch back to local**:
- Change URLs back to `http://localhost:8000/api/v1`
- Restart frontend
