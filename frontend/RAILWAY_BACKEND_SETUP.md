# Connecting Local Frontend to Railway Backend

This guide shows how to run your **local frontend** (npm dev server) against the **remote Railway backend** instead of localhost.

---

## CORS: Already Configured ✅

**Good news**: The Railway backend already allows `http://localhost:3005` in its CORS configuration!

**Allowed origins** (`backend/app/config.py`):
- `http://localhost:3005` ✅ **Your local frontend**
- `http://localhost:3000` (React dev)
- `http://localhost:5173` (Vite dev)
- `https://sigmasight-frontend.vercel.app` (Production)

**This means**:
- ✅ Local frontend → Railway backend: **Works immediately, no CORS changes needed**
- ⚠️ Production frontend: Add production URL to backend's `ALLOWED_ORIGINS` before deploying

---

## Quick Start (Two Methods)

### Method 1: Command-Line Override (Recommended)

Run dev server with Railway backend URL as environment variable:

```bash
cd frontend
NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1 npm run dev
```

**Pros**: One command, no file editing
**Cons**: Must type Railway URL each time

---

### Method 2: Edit .env File

**1. Get your Railway backend URL**:
```bash
cd backend
railway status
# Look for: URL: https://sigmasight-backend-production.up.railway.app
```

**2. Update `frontend/.env`**:
```env
# Change this line:
NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1
```

**3. Restart dev server**:
```bash
npm run dev
```

**Pros**: Set once, use many times
**Cons**: Must manually edit to switch back to local backend

---

## Environment Variable Reference

### Required Variable

**NEXT_PUBLIC_BACKEND_API_URL** - The only variable that matters:
```env
# Local backend (default):
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1

# Railway backend:
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-backend-production.up.railway.app/api/v1
```

**Important**:
- ✅ Use `https://` (not `http://`)
- ✅ Include `/api/v1` at the end
- ✅ No trailing slash
- ✅ `NEXT_PUBLIC_` prefix required (client-side access)

### Variables That Don't Need Changes

These stay the same (they're for backend, not frontend):
```env
DATABASE_URL=...          # Backend only
POLYGON_API_KEY=...       # Backend only
FMP_API_KEY=...          # Backend only
OPENAI_API_KEY=...       # Backend only
```

---

## Switching Between Backends

### Quick Switch Commands

**Switch to Railway backend**:
```bash
# Update .env
sed -i '' 's|http://localhost:8000|https://your-app.railway.app|g' .env

# Restart dev server
npm run dev
```

**Switch back to local backend**:
```bash
# Update .env
sed -i '' 's|https://your-app.railway.app|http://localhost:8000|g' .env

# Restart dev server
npm run dev
```

### Verify Current Configuration

**Check .env file**:
```bash
grep NEXT_PUBLIC_BACKEND_API_URL .env
```

**Check browser console**:
```javascript
// Open DevTools → Console
console.log(process.env.NEXT_PUBLIC_BACKEND_API_URL)
```

---

## Verification Steps

### 1. Test Backend is Running

```bash
curl https://your-app.railway.app/api/v1/auth/login

# Should return: {"detail":"Method Not Allowed"}
# This confirms backend is up and routing works
```

### 2. Start Frontend

```bash
cd frontend
npm run dev
# or with Railway URL:
# NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1 npm run dev
```

### 3. Test Login

1. Open browser to `http://localhost:3005`
2. Login with demo credentials:
   - Email: `demo_hnw@sigmasight.com`
   - Password: `demo12345`
3. Should see successful login and redirect to `/portfolio`

### 4. Verify API Calls in DevTools

1. Open DevTools (F12) → Network tab
2. Login and navigate around
3. Verify API calls go to Railway URL (not `localhost:8000`)

---

## Troubleshooting

### Issue: API Calls Still Going to Localhost

**Symptom**: DevTools Network tab shows requests to `localhost:8000`

**Solutions**:
1. **Hard refresh browser** (clears cached config):
   ```
   Ctrl+Shift+R (Windows/Linux)
   Cmd+Shift+R (Mac)
   ```

2. **Verify .env file saved**:
   ```bash
   cat .env | grep NEXT_PUBLIC_BACKEND_API_URL
   ```

3. **Restart dev server**:
   ```bash
   # Stop with Ctrl+C, then:
   npm run dev
   ```

4. **Check browser console**:
   ```javascript
   console.log(process.env.NEXT_PUBLIC_BACKEND_API_URL)
   // Should show Railway URL
   ```

---

### Issue: CORS Errors

**Symptom**: `Access-Control-Allow-Origin` errors in console

**Important**: Railway backend already allows `http://localhost:3005`, so CORS should work.

**If you still see errors**:

1. **Verify requests go to Railway** (not localhost):
   - Open DevTools → Network tab
   - Check request URLs start with `https://your-app.railway.app`

2. **Hard refresh browser** (clears cached CORS preflight):
   ```
   Ctrl+Shift+R (Windows/Linux)
   Cmd+Shift+R (Mac)
   ```

3. **Check Railway backend logs**:
   ```bash
   railway logs --tail 100
   # Look for CORS-related errors
   ```

4. **Verify backend CORS config**:
   ```bash
   cd backend
   grep -A 5 "ALLOWED_ORIGINS" app/config.py
   # Should include: "http://localhost:3005"
   ```

---

### Issue: Authentication Fails

**Symptom**: Login returns 401 or errors

**Solutions**:

1. **Verify Railway backend is running**:
   ```bash
   curl https://your-app.railway.app/api/v1/auth/login
   # Should return 405 Method Not Allowed (expects POST)
   ```

2. **Check Railway has demo data**:
   ```bash
   railway ssh
   # Inside Railway shell:
   uv run python -c "from app.models.users import User; print('Backend ready')"
   ```

3. **Verify correct credentials**:
   - Email: `demo_hnw@sigmasight.com`
   - Password: `demo12345`

---

### Issue: 404 Errors on API Calls

**Symptom**: All API calls return 404

**Solution**: Verify URL includes `/api/v1`:

```env
# ✅ CORRECT
NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1

# ❌ WRONG (missing /api/v1)
NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app
```

---

### Issue: Slow API Responses

**Symptom**: API calls take 3-5 seconds

**Causes**:
- Railway cold starts (free tier)
- Backend hibernates after inactivity

**Solutions**:
1. First request may be slow (waking up backend)
2. Subsequent requests should be fast
3. Use Railway Pro for no cold starts (paid)
4. Set up uptime monitor to keep backend warm

---

### Issue: Environment Variable Not Updating

**Symptom**: Changed .env but still using old value

**Solutions**:

1. **Restart dev server** (required for .env changes):
   ```bash
   # Stop with Ctrl+C
   npm run dev
   ```

2. **Check for .env.local** (overrides .env):
   ```bash
   # Next.js loads in this order (highest priority first):
   # .env.local
   # .env.development
   # .env

   # If .env.local exists, it overrides .env
   ls -la .env*
   ```

3. **Clear browser cache**:
   ```
   Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   ```

---

## Advanced: Multiple Backend Configurations

### Option A: Multiple .env Files

**Setup**:
```bash
# Create separate env files
cp .env .env.local      # Local backend config
cp .env .env.railway    # Railway backend config

# Edit .env.railway:
# NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1

# Add to .gitignore:
echo ".env.railway" >> .gitignore
```

**Usage**:
```bash
# Use local backend
npm run dev

# Use Railway backend
cp .env.railway .env
npm run dev

# Switch back
cp .env.local .env
npm run dev
```

---

### Option B: npm Scripts

**Add to package.json**:
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

**Pros**: One command to switch, no file editing
**Cons**: Need to update script if Railway URL changes

---

## Production Frontend Deployment

If deploying frontend to production (not localhost):

### 1. Update Backend CORS

**Edit** `backend/app/config.py`:
```python
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3005",                    # Local dev
    "https://your-production-frontend.com",     # Add production URL
]
```

### 2. Redeploy Backend

```bash
cd backend
railway up
# Or: git push (if Railway watches git)
```

### 3. Set Frontend Environment Variables

In Railway/Vercel dashboard:
```
NEXT_PUBLIC_BACKEND_API_URL=https://your-backend.railway.app/api/v1
```

**Without backend CORS update, production frontend will get CORS errors!**

---

## Railway Backend Health Check

Before connecting frontend, verify backend is healthy:

```bash
# 1. Check backend is running
curl https://your-app.railway.app/api/v1/auth/login
# Expected: {"detail":"Method Not Allowed"}

# 2. Test authentication endpoint
curl -X POST https://your-app.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo_hnw@sigmasight.com","password":"demo12345"}'
# Expected: {"access_token":"...","token_type":"bearer"}

# 3. Check backend logs
railway logs --tail 100
```

---

## Summary

### To Connect to Railway Backend:

1. **Get Railway URL**: `railway status`
2. **Update .env**: `NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1`
3. **Restart frontend**: `npm run dev`
4. **Test login**: `demo_hnw@sigmasight.com` / `demo12345`
5. **Verify in DevTools**: API calls go to Railway URL

### Common Gotchas:

- ❌ Forgetting `https://` (not `http://`)
- ❌ Forgetting `/api/v1` at the end
- ❌ Not restarting dev server after .env changes
- ❌ Not hard-refreshing browser after changes
- ❌ Having .env.local that overrides .env

### Switch Back to Local:

```bash
# Update .env
sed -i '' 's|https://your-app.railway.app|http://localhost:8000|g' .env

# Restart
npm run dev
```

---

## Quick Reference Card

```bash
# Find Railway URL
railway status

# Start with Railway backend
NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1 npm run dev

# Check current config
grep NEXT_PUBLIC_BACKEND_API_URL .env

# Test backend health
curl https://your-app.railway.app/api/v1/auth/login

# Check Railway logs
railway logs --tail 50
```

**Demo Credentials**:
- Email: `demo_hnw@sigmasight.com`
- Password: `demo12345`

**CORS**: Already configured for localhost:3005 ✅
