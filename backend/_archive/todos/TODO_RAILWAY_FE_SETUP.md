# TODO: Railway Backend Setup Issues & Required Changes

**Status**: Testing Phase
**Created**: 2025-10-05
**Purpose**: Document issues and required changes for connecting local frontend to Railway backend

---

## Problem Diagnosis

### Issue 1: Environment Variable Mismatch

**Symptom**: Login fails with "incorrect email or password" when connecting to Railway backend

**Root Cause**: The frontend proxy route uses a different environment variable than what's documented in RAILWAY_BACKEND_SETUP.md

**Current Behavior**:
```typescript
// frontend/app/api/proxy/[...path]/route.ts:4-5
const BACKEND_URL = process.env.BACKEND_URL ||
  (process.env.DOCKER_ENV === 'true' ? 'http://host.docker.internal:8000' : 'http://localhost:8000')
```

**What happens**:
1. User sets: `NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-production.up.railway.app/api/v1`
2. Proxy reads: `BACKEND_URL` (which is NOT set)
3. Proxy defaults to: `http://localhost:8000`
4. Result: All API calls go to local backend, not Railway

**Request Flow**:
```
Browser
  → /api/proxy/api/v1/auth/login (Next.js proxy route)
  → Proxy uses BACKEND_URL (not set, defaults to localhost:8000)
  → http://localhost:8000/api/v1/auth/login (WRONG - local backend!)

Expected:
  → https://sigmasight-be-production.up.railway.app/api/v1/auth/login (Railway backend)
```

**Verification**:
- Tested Railway backend directly with curl: ✅ Works, returns token
- Frontend login with env var set: ❌ Fails, uses localhost instead

---

## Required Changes

### Change 1: Update Proxy Route Environment Variable

**File**: `frontend/app/api/proxy/[...path]/route.ts`

**Current** (lines 4-5):
```typescript
const BACKEND_URL = process.env.BACKEND_URL ||
  (process.env.DOCKER_ENV === 'true' ? 'http://host.docker.internal:8000' : 'http://localhost:8000')
```

**Required Change** (Use NEXT_PUBLIC_BACKEND_API_URL):
```typescript
// Remove /api/v1 suffix if present since proxy adds the path
const getBackendUrl = () => {
  const publicUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL;
  if (publicUrl) {
    // Remove /api/v1 suffix if present
    return publicUrl.replace(/\/api\/v1\/?$/, '');
  }
  // Fallback to BACKEND_URL or localhost
  return process.env.BACKEND_URL ||
    (process.env.DOCKER_ENV === 'true' ? 'http://host.docker.internal:8000' : 'http://localhost:8000');
};

const BACKEND_URL = getBackendUrl();
```

**Why this approach**:
- Users only need to set ONE variable: `NEXT_PUBLIC_BACKEND_API_URL`
- Consistent with documentation in RAILWAY_BACKEND_SETUP.md
- Less confusing for developers
- Maintains backward compatibility with BACKEND_URL if already set

---

### Change 2: No Documentation Changes Needed

**File**: `frontend/RAILWAY_BACKEND_SETUP.md`

**Status**: Current documentation is correct
- Users only need to set `NEXT_PUBLIC_BACKEND_API_URL`
- Proxy code change handles the rest automatically

---

## Testing Plan

### Test 1: Verify Railway Backend is Available

```bash
# Get Railway URL
cd backend
railway domain
# Returns: sigmasight-be-production.up.railway.app

# Test auth endpoint
curl -X POST https://sigmasight-be-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}'

# Expected: {"access_token":"...","token_type":"bearer",...}
```

✅ **Result**: Railway backend works, returns token

---

### Test 2: Apply Frontend Changes Locally

**Steps**:
1. ✅ Made code changes (Option A - single variable approach)
2. ✅ Restarted frontend with Railway backend URL
3. ✅ Tested login at http://localhost:3005
4. ✅ Verified requests go to Railway URL in logs and Network tab
5. ✅ Documented results below

**Test Results** (2025-10-05):

✅ **Proxy Configuration**:
```
Proxy Backend URL: https://sigmasight-be-production.up.railway.app
NEXT_PUBLIC_BACKEND_API_URL: https://sigmasight-be-production.up.railway.app/api/v1
```
- /api/v1 suffix correctly stripped by getBackendUrl() function
- Environment variable correctly read from NEXT_PUBLIC_BACKEND_API_URL

✅ **Login Test**:
- Credentials: demo_hnw@sigmasight.com / demo12345
- Result: **Login successful**
- Redirected to /portfolio page
- JWT token stored in localStorage

✅ **API Requests**:
- POST /api/proxy/api/v1/auth/login → 200 OK
- GET /api/proxy/api/v1/data/portfolios → 200 OK
- POST /api/proxy/api/v1/chat/conversations → 201 Created
- GET /api/proxy/api/v1/auth/me → 200 OK
- GET /api/proxy/api/v1/analytics/portfolio/{id}/overview → 200 OK
- GET /api/proxy/api/v1/data/positions/details → 200 OK
- GET /api/proxy/api/v1/analytics/portfolio/{id}/factor-exposures → 200 OK

✅ **Portfolio Data**:
- 24 positions loaded successfully
- $2.9M equity balance displayed
- Portfolio metrics showing correctly
- Private investments (2) and long positions (22) rendered

✅ **Console Logs**:
- No authentication errors
- Portfolio ID correctly resolved
- Chat conversation initialized
- No CORS errors
- All API calls routed through Railway backend

**Screenshot**: `.playwright-mcp/railway-backend-success.png`

---

## Additional Issues Found During Testing

**Status**: ✅ **No additional issues found**

The fix works perfectly:
- Single environment variable (NEXT_PUBLIC_BACKEND_API_URL) is all users need to set
- Proxy correctly strips /api/v1 suffix before forwarding requests
- All API endpoints work correctly through Railway backend
- Authentication, portfolio data, and chat initialization all functional
- No changes needed to RAILWAY_BACKEND_SETUP.md documentation

---

## Final Checklist

Before reverting changes and handing off to FE team:

- [x] All issues documented in this file
- [x] All required changes clearly specified with code examples
- [x] Testing verified all issues are resolved
- [x] Proxy route changes implemented permanently (FE team approval)
- [x] This TODO file committed for FE team reference
- [x] FE team implemented changes (2025-10-05)

**Implementation Complete**:
1. ✅ Proxy route updated to use NEXT_PUBLIC_BACKEND_API_URL
2. ✅ Maintains backward compatibility with BACKEND_URL
3. ✅ Ready to commit both files to main branch

---

## Implementation Notes for FE Team

### Implementation Steps

1. **Update proxy route file**:
   - File: `frontend/app/api/proxy/[...path]/route.ts`
   - Replace lines 4-5 with getBackendUrl() function (see Change 1 above)
   - Maintains backward compatibility with BACKEND_URL

2. **Test locally**:
   ```bash
   NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-production.up.railway.app/api/v1 npm run dev
   ```

3. **Verify**:
   - Login works with demo credentials
   - Network tab shows requests to Railway URL (not localhost)
   - No console errors
   - Proxy logs show correct backend URL

4. **No documentation changes needed**:
   - RAILWAY_BACKEND_SETUP.md is already correct
   - .env.example already has NEXT_PUBLIC_BACKEND_API_URL

---

## Current Railway Backend

**URL**: `https://sigmasight-be-production.up.railway.app`

**Demo Credentials**:
- Email: `demo_hnw@sigmasight.com`
- Password: `demo12345`

**Health Check**:
```bash
curl https://sigmasight-be-production.up.railway.app/health
# Expected: {"status":"healthy"}
```

---

## Questions for FE Team

1. Are there any other services/routes that use BACKEND_URL?
2. Should we add console warning when NEXT_PUBLIC_BACKEND_API_URL is set but gets stripped?
3. Any concerns about the /api/v1 suffix stripping logic?

---

## Git Workflow

**Current branch**: `main`

**Planned workflow**:
1. Test changes locally (don't commit)
2. Document all issues in this file
3. Commit only this TODO file
4. Revert local changes: `git reset --hard HEAD~1` (keep only TODO commit)
5. FE team implements changes and tests
6. Delete this TODO file when complete
