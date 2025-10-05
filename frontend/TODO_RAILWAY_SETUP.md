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

**Option A: Use NEXT_PUBLIC_BACKEND_API_URL** (Recommended - Single variable):
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

**Option B: Require both variables** (Less user-friendly):
```typescript
// Keep as-is, but document that users must set BOTH variables
const BACKEND_URL = process.env.BACKEND_URL ||
  (process.env.DOCKER_ENV === 'true' ? 'http://host.docker.internal:8000' : 'http://localhost:8000')
```

**Recommendation**: Option A
- Users only need to set ONE variable: `NEXT_PUBLIC_BACKEND_API_URL`
- Consistent with documentation in RAILWAY_BACKEND_SETUP.md
- Less confusing for developers

---

### Change 2: Update RAILWAY_BACKEND_SETUP.md

**File**: `frontend/RAILWAY_BACKEND_SETUP.md`

**Current**: Only mentions `NEXT_PUBLIC_BACKEND_API_URL`

**If keeping Option B above** (two variables required):

Add to "Environment Variable Reference" section:

```markdown
### Required Variables (Both Needed)

**NEXT_PUBLIC_BACKEND_API_URL** - Client-side requests:
```env
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-production.up.railway.app/api/v1
```

**BACKEND_URL** - Server-side proxy route:
```env
BACKEND_URL=https://sigmasight-be-production.up.railway.app
```

**Important**:
- `NEXT_PUBLIC_BACKEND_API_URL` includes `/api/v1` suffix
- `BACKEND_URL` does NOT include `/api/v1` (proxy adds paths)
```

**If using Option A** (recommended):
- No documentation changes needed
- Current docs are correct

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
1. Make code changes (Option A recommended)
2. Restart frontend:
   ```bash
   NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-production.up.railway.app/api/v1 npm run dev
   ```
3. Test login at http://localhost:3005
4. Verify in DevTools Network tab that requests go to Railway URL
5. Document any additional issues below

---

## Additional Issues Found During Testing

### Issue 2: [To be filled during testing]

**Symptom**:

**Root Cause**:

**Required Change**:

---

### Issue 3: [To be filled during testing]

**Symptom**:

**Root Cause**:

**Required Change**:

---

## Final Checklist

Before reverting changes and handing off to FE team:

- [ ] All issues documented in this file
- [ ] All required changes clearly specified with code examples
- [ ] Testing verified all issues are resolved
- [ ] Git changes reverted: `git reset --hard HEAD`
- [ ] This TODO file committed for FE team reference
- [ ] FE team notified of required changes

---

## Implementation Notes for FE Team

### Recommended Approach

1. **Implement Option A** (single environment variable):
   - Update `frontend/app/api/proxy/[...path]/route.ts` with getBackendUrl() function
   - Keeps documentation simple (only NEXT_PUBLIC_BACKEND_API_URL needed)
   - More user-friendly

2. **Test locally**:
   ```bash
   NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-production.up.railway.app/api/v1 npm run dev
   ```

3. **Verify**:
   - Login works with demo credentials
   - Network tab shows requests to Railway URL
   - No console errors

4. **Update .env.example** if needed

### Alternative Approach (Option B)

If you prefer to keep two separate variables:

1. Document that BOTH variables are required in RAILWAY_BACKEND_SETUP.md
2. Add validation/warning when BACKEND_URL is not set
3. Update command-line examples to include both variables

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

1. Do you prefer Option A (single variable) or Option B (two variables)?
2. Are there any other services/routes that use BACKEND_URL?
3. Should we add runtime validation when BACKEND_URL/NEXT_PUBLIC_BACKEND_API_URL mismatch?

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
