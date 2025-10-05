# Railway Backend - Organize Page Tag Issue Debug Guide

**Date**: 2025-10-05
**Issue**: Organize page tagging returns 401 Unauthorized when using Railway backend
**Status**: Investigation in progress

---

## Current Findings

### What's Working ✅
- Frontend successfully connects to Railway backend
- Portfolio data loads correctly
- Positions display properly
- User authentication is valid (token exists and works for other endpoints)

### What's Failing ❌
- `/api/v1/tags/` endpoint returns **401 Unauthorized**
- Tags cannot load on organize page
- Position tagging functionality broken

### Configuration Confirmed
**Frontend Backend URL**: `https://sigmasight-be-production.up.railway.app/api/v1`
- Set in `.env`: `NEXT_PUBLIC_BACKEND_API_URL`
- Set in `.env.local`: `NEXT_PUBLIC_BACKEND_API_URL`

**Railway Backend Has Tag Endpoints** (verified via OpenAPI spec):
- ✅ `/api/v1/tags/` (GET, POST)
- ✅ `/api/v1/tags/{tag_id}` (GET, PATCH)
- ✅ `/api/v1/tags/{tag_id}/archive` (POST)
- ✅ `/api/v1/tags/{tag_id}/restore` (POST)
- ✅ `/api/v1/positions/{position_id}/tags` (GET, POST, DELETE, PATCH)

---

## Root Cause Hypothesis

### Most Likely: Railway Database Missing Tag Tables

The tag system was added on **October 2, 2025** and requires new database tables:
- `tags_v2` table (user-scoped tags)
- `position_tags` table (many-to-many relationship between positions and tags)

**Theory**: Railway backend code is up-to-date (has endpoints), but Railway PostgreSQL database has not run the Alembic migrations to create these tables.

**Why 401 instead of 500?**
- Backend auth dependency might fail when database query fails
- Or auth is working but endpoint returns 401 due to missing data

---

## Quick Browser Console Tests

### Test 1: Try Railway Tag Endpoint Directly
```javascript
// Run this in browser console on organize page
const token = localStorage.getItem('access_token')

fetch('https://sigmasight-be-production.up.railway.app/api/v1/tags/', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => {
  console.log('Status:', r.status)
  return r.json()
})
.then(d => console.log('Response:', d))
.catch(e => console.error('Error:', e))
```

**Expected Outcomes**:
- 401 → Auth issue with Railway backend
- 500 → Database table missing (relation does not exist)
- 200 → Endpoint works (different issue)

### Test 2: Try Creating a Tag
```javascript
const token = localStorage.getItem('access_token')

fetch('https://sigmasight-be-production.up.railway.app/api/v1/tags/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Test Tag',
    color: '#4A90E2'
  })
})
.then(r => {
  console.log('Status:', r.status)
  return r.json()
})
.then(d => console.log('Create tag response:', d))
.catch(e => console.error('Error:', e))
```

### Test 3: Compare With Working Endpoint
```javascript
const token = localStorage.getItem('access_token')

// This SHOULD work (portfolio endpoint)
fetch('https://sigmasight-be-production.up.railway.app/api/v1/data/portfolios', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => {
  console.log('Portfolios status:', r.status)
  return r.json()
})
.then(d => console.log('Portfolios response:', d))
```

### Test 4: Check Token Format
```javascript
const token = localStorage.getItem('access_token')
console.log('Token exists:', !!token)
console.log('Token length:', token?.length)
console.log('Token preview:', token?.substring(0, 20) + '...')
```

---

## Debugging Steps

### Step 1: Check Railway Database Schema

**Access Railway Dashboard** → PostgreSQL database → Query tab

Run this SQL query:
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('tags_v2', 'position_tags', 'tags');
```

**Expected Results**:
- If `tags_v2` and `position_tags` exist → Tables are there (different issue)
- If missing → Need to run migrations

### Step 2: Check Alembic Migration History

Check which migrations have been applied:
```sql
SELECT * FROM alembic_version;
```

Compare with local migrations:
```bash
cd backend
alembic history
```

Look for migration that creates tag tables (likely around October 2, 2025).

### Step 3: Check Railway Backend Logs

In Railway dashboard:
1. Go to your backend service
2. Click "Deployments"
3. Click latest deployment
4. Check logs for errors like:
   - `relation "tags_v2" does not exist`
   - `table "position_tags" does not exist`
   - Authentication errors

---

## Solutions

### Solution A: Run Migrations on Railway Database ⭐ **MOST LIKELY FIX**

**Option 1: Via Railway CLI**
```bash
# Connect to Railway project
railway link

# Run migrations
railway run alembic upgrade head
```

**Option 2: Via Railway Dashboard**
1. Go to Railway project
2. Open database
3. Run migrations manually via SQL import

**Option 3: Trigger Redeploy with Migration**
1. Ensure `alembic upgrade head` runs in Railway deployment
2. Check Railway build settings
3. Redeploy backend service

### Solution B: Check Database User Permissions

Verify Railway PostgreSQL user has proper permissions:
```sql
-- Check current user permissions
SELECT * FROM information_schema.role_table_grants
WHERE grantee = current_user;
```

### Solution C: Verify Auth Configuration

Compare local vs Railway backend:
- JWT secret key (`SECRET_KEY` env var)
- Token expiration settings
- Auth dependency implementation

### Solution D: Temporarily Switch to Local Backend

**Quick workaround for testing**:

Edit `frontend/.env.local`:
```bash
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
```

Start local backend:
```bash
cd backend
uv run python run.py
```

Restart frontend:
```bash
cd frontend
npm run dev
```

---

## Success Criteria

When issue is resolved, you should see:
- ✅ No 401 errors on organize page
- ✅ Tags load successfully
- ✅ Tag creation works
- ✅ Drag-and-drop tagging functions
- ✅ Browser console shows no errors
- ✅ Network tab shows successful API calls to `/api/v1/tags/`

---

## Investigation Log

### 2025-10-05 - Initial Investigation
- **Confirmed**: Frontend using Railway backend URL
- **Confirmed**: Railway backend has tag endpoints in OpenAPI spec
- **Issue**: Tag endpoints return 401 while other endpoints work
- **Next**: Check Railway database for tag tables

### 2025-10-05 - Root Cause Found ✅
- **Test Result**: Direct fetch to Railway backend returned **200 OK** with 17 tags
- **Conclusion**: Railway backend works perfectly!
- **Real Issue**: Frontend `apiClient.ts` had Authorization header code **commented out** (lines 326-337)
- **Impact**: All apiClient requests missing auth token, causing 401 errors
- **Fix Applied**: Uncommented and implemented auth header attachment in request interceptor

### 2025-10-05 - Solution Implemented
**File**: `frontend/src/services/apiClient.ts` (lines 325-337)

**Changed from** (commented out):
```javascript
// const token = getAuthToken();
// if (token) {
//   config.headers = {
//     ...config.headers,
//     'Authorization': `Bearer ${token}`,
//   };
// }
```

**Changed to** (active):
```javascript
const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
if (token) {
  config.headers = {
    ...config.headers,
    'Authorization': `Bearer ${token}`,
  };
}
```

**Status**: ✅ **PARTIAL FIX** - Authorization header now attached, but still getting 401 on tags endpoint

---

### 2025-10-05 - Additional Fix: Trailing Slash Issue
**File**: `frontend/src/config/api.ts` (lines 96-97)

**Root Cause Found**: Trailing slashes in API endpoint URLs were causing **308 Permanent Redirect** responses, which **lose the Authorization header** during the redirect.

**Changed from**:
```typescript
TAGS: {
  LIST: '/api/v1/tags/',    // ❌ Trailing slash causes 308 redirect
  CREATE: '/api/v1/tags/',  // ❌ Authorization header lost
  ...
}
```

**Changed to**:
```typescript
TAGS: {
  LIST: '/api/v1/tags',     // ✅ No redirect
  CREATE: '/api/v1/tags',   // ✅ Authorization header preserved
  ...
}
```

**Network Request Flow (Before Fix)**:
1. `GET /api/proxy/api/v1/tags/?include_archived=false` → **308 Permanent Redirect**
2. Redirects to: `GET /api/proxy/api/v1/tags?include_archived=false` → **401 Unauthorized** (no auth header)

**Network Request Flow (After Fix)**:
1. `GET /api/proxy/api/v1/tags?include_archived=false` → **401 Unauthorized** (auth header present)

**Status**: ✅ **TRAILING SLASH FIXED** - No more 308 redirects, but **still getting 401**

---

### 2025-10-05 - Remaining Issue: 401 on Tags Endpoint (MYSTERY)

**Observation**: After both fixes AND fresh login with Railway-issued token, tags endpoint STILL returns 401:
- ✅ `/api/v1/auth/me` → **200 OK** (same token, same backend)
- ✅ `/api/v1/data/positions/details` → **200 OK**
- ✅ `/api/v1/analytics/portfolio/.../overview` → **200 OK**
- ❌ `/api/v1/tags?include_archived=false` → **401 Unauthorized**

**Evidence**:
- Fresh login with Railway backend (confirmed via proxy logs)
- JWT token issued by Railway backend
- Auth token properly attached to ALL requests (confirmed via browser test)
- Same token works for other Railway endpoints
- Both auth and tags endpoints use `Depends(get_current_user)` - IDENTICAL auth dependency

**What We Ruled Out**:
- ❌ Token mismatch (local vs Railway) - Token is Railway-issued
- ❌ Trailing slash redirect - Fixed, no more 308 redirects
- ❌ Missing Authorization header - Header is attached correctly
- ❌ Proxy not forwarding headers - `/auth/me` works with same proxy

**Most Likely Cause**: There's something SPECIFIC about the Railway backend's tags endpoint that rejects valid auth tokens, even though:
1. The token works for other endpoints
2. The endpoint code looks identical to working endpoints
3. User confirmed `tags_v2` table exists in Railway database

**Next Step**: Need to check Railway backend logs to see WHY the tags endpoint specifically is rejecting the valid token

---

## Related Files

### Frontend
- `frontend/src/containers/OrganizeContainer.tsx` - Main organize page logic
- `frontend/src/hooks/useTags.ts` - Tag fetching hook (line 39 - where 401 occurs)
- `frontend/src/services/tagsApi.ts` - Tag API service
- `frontend/src/config/api.ts` - API endpoint configuration
- `frontend/.env` - Backend URL configuration
- `frontend/.env.local` - Backend URL override

### Backend
- `backend/app/api/v1/tags.py` - Tag management endpoints
- `backend/app/api/v1/position_tags.py` - Position tagging endpoints
- `backend/app/models/tags_v2.py` - Tag database model
- `backend/app/models/position_tags.py` - Position-tag relationship model
- `backend/alembic/versions/` - Database migrations

---

## Quick Reference Commands

### Check Local Database Has Tag Tables
```bash
cd backend
uv run python -c "
import asyncio
from sqlalchemy import inspect
from app.database import get_async_session

async def check():
    async with get_async_session() as db:
        inspector = inspect(db.bind)
        tables = await inspector.get_table_names()
        tag_tables = [t for t in tables if 'tag' in t.lower()]
        print('Tag-related tables:', tag_tables)

asyncio.run(check())
"
```

### Test Tag Endpoint Locally
```bash
# Start local backend (if not running)
cd backend
uv run python run.py

# In another terminal, test endpoint
curl http://localhost:8000/api/v1/tags/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Next Steps

1. [ ] Run browser console Test 1 (check tag endpoint response)
2. [ ] Check Railway database for `tags_v2` table
3. [ ] Check Railway backend logs for errors
4. [ ] Run Alembic migrations on Railway database
5. [ ] Verify organize page works after fix
6. [ ] Document solution in this file
