# SigmaSight Frontend - Railway Backend Migration Guide

**Created**: 2025-10-05
**Status**: 🟡 In Progress
**Confidence Level**: 85-90%

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Root Cause Analysis](#root-cause-analysis)
4. [Migration Plan](#migration-plan)
5. [Testing Checklist](#testing-checklist)
6. [Rollback Procedures](#rollback-procedures)
7. [Post-Migration Validation](#post-migration-validation)

---

## Executive Summary

### What Changed
- **Before**: Frontend (`localhost:3005`) → Backend (`localhost:8000`) - Same origin
- **After**: Frontend (`localhost:3005`) → Backend (`sigmasight-be-production.up.railway.app`) - **Cross-origin**

### Critical Impact
Cross-origin requests break HttpOnly cookie authentication, causing:
- ✅ Login succeeds (token stored in localStorage)
- ❌ Subsequent API calls fail (some missing Authorization header)
- ❌ userId/portfolioId lost after page refresh or navigation
- ❌ Authentication state becomes inconsistent

### Good News 🎉
**75% of your auth infrastructure already works with Railway!**
- ✅ `requestManager.ts` - Properly uses Bearer tokens
- ✅ `chatService.ts` - Properly uses Bearer tokens
- ✅ `chatAuthService.ts` - Has Bearer token support
- ✅ `authManager.ts` - Correctly manages localStorage tokens
- ✅ Backend CORS - Already configured for localhost:3005

### What Needs Fixing
- 🔴 **apiClient.ts** - Auth interceptor is disabled (lines 326-336)
- 🟡 **Token source** - Multiple services read localStorage directly (sync risk)
- 🟡 **cookies.txt** - Contains sensitive token, should be gitignored
- 🟡 **Cross-origin cookies** - Need to abandon or configure properly

---

## Current State Analysis

### Authentication Architecture

#### 1. Dual Authentication System
You have **two parallel auth systems** (potentially conflicting):

**System A: Bearer Token Auth** ✅ Works cross-origin
```typescript
// authManager.ts - Stores tokens in localStorage
localStorage.setItem('access_token', token)

// requestManager.ts - Uses Bearer tokens
headers: { 'Authorization': `Bearer ${token}` }

// chatService.ts - Uses Bearer tokens
'Authorization': `Bearer ${localStorage.getItem('access_token')}`
```

**System B: HttpOnly Cookie Auth** ❌ Broken cross-origin
```typescript
// chatAuthService.ts - Expects cookies
credentials: 'include'  // Won't work across origins

// cookies.txt - Cookie for localhost domain only
#HttpOnly_localhost ... auth_token eyJ...
```

#### 2. Current Service Inventory

| Service | Location | Auth Method | Railway Status |
|---------|----------|-------------|----------------|
| `apiClient` | `src/services/apiClient.ts` | ❌ Disabled | **BROKEN** |
| `requestManager` | `src/services/requestManager.ts` | ✅ Bearer Token | **WORKS** |
| `chatService` | `src/services/chatService.ts` | ✅ Bearer Token | **WORKS** |
| `chatAuthService` | `src/services/chatAuthService.ts` | ✅ Bearer Token | **WORKS** |
| `authManager` | `src/services/authManager.ts` | ✅ Token Storage | **WORKS** |
| `portfolioResolver` | `src/services/portfolioResolver.ts` | ✅ Uses requestManager | **WORKS** |
| `useFetchStreaming` | `src/hooks/useFetchStreaming.ts` | ✅ Uses chatAuthService | **WORKS** |

#### 3. Backend CORS Configuration ✅

**File**: `backend/app/config.py` (lines 103-108)
```python
ALLOWED_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:3005",  # ✅ Already configured!
    "http://localhost:5173",
    "https://sigmasight-frontend.vercel.app",
]
```

**File**: `backend/app/main.py` (lines 24-30)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,  # ✅ Allows Authorization header
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Status**: ✅ Backend is properly configured for Railway + localhost:3005

---

## Root Cause Analysis

### Primary Issue: Disabled apiClient Auth Interceptor

**File**: `src/services/apiClient.ts` (lines 326-336)

```typescript
// Add default request interceptor for auth (when needed)
apiClient.addRequestInterceptor(async (url, config) => {
  // Add auth headers here when authentication is implemented
  // const token = getAuthToken();
  // if (token) {
  //   config.headers = {
  //     ...config.headers,
  //     'Authorization': `Bearer ${token}`,
  //   };
  // }

  return { url, config };
});
```

**Impact**: Any API call using `apiClient` (instead of `requestManager` or `chatService`) fails authentication.

### Secondary Issues

#### 1. Cross-Origin Cookie Failure
**Problem**: HttpOnly cookies can't be shared between `localhost:3005` and `sigmasight-be-production.up.railway.app`

**Evidence**:
```
cookies.txt:
#HttpOnly_localhost  FALSE  /  FALSE  ...  auth_token  eyJ...
                     ^^^^^
                Domain mismatch - cookie is localhost-only
```

**Solution**: Switch fully to Bearer token auth, abandon cookie-based auth for Railway.

#### 2. Multiple Token Sources
**Problem**: Services read `localStorage` directly instead of using `authManager`

**Examples**:
```typescript
// chatService.ts:158
'Authorization': `Bearer ${localStorage.getItem('access_token')}`

// chatAuthService.ts:149, 289
localStorage.getItem('access_token')
```

**Risk**: If `authManager` updates the token, direct localStorage reads get stale data.

**Solution**: Centralize through `authManager.getAccessToken()`.

#### 3. Missing Token Validation
**Problem**: No checks if token is expired before making API calls

**Current Flow**:
1. User logs in → Token stored (expires in 30 min)
2. 31 minutes later → User makes API call → 401 error
3. App doesn't detect expired token → No auto-refresh or redirect

**Solution**: Add token expiration checks in request interceptors.

---

## Migration Plan

### Phase 1: Enable Bearer Token Authentication (CRITICAL) 🔴

#### Task 1.1: Fix apiClient Auth Interceptor
**File**: `src/services/apiClient.ts`

**Change**:
```typescript
// BEFORE (lines 326-336)
apiClient.addRequestInterceptor(async (url, config) => {
  // Add auth headers here when authentication is implemented
  // const token = getAuthToken();
  // if (token) {
  //   config.headers = {
  //     ...config.headers,
  //     'Authorization': `Bearer ${token}`,
  //   };
  // }

  return { url, config };
});

// AFTER
import { authManager } from './authManager';

apiClient.addRequestInterceptor(async (url, config) => {
  const token = authManager.getAccessToken();

  if (token) {
    config.headers = {
      ...config.headers,
      'Authorization': `Bearer ${token}`,
    };
  }

  return { url, config };
});
```

**Status**: ⬜ Not Started
**Priority**: P0 - Critical
**Risk**: Low
**Test**: Make API call using `apiClient.get()` and verify Authorization header is present

---

#### Task 1.2: Centralize Token Access in chatService
**File**: `src/services/chatService.ts`

**Change**: Replace direct `localStorage.getItem('access_token')` calls with `authManager.getAccessToken()`

**Locations to update**:
- Line 158: `createConversation()`
- Line 184: `listConversations()`
- Line 209: `deleteConversation()`
- Line 238: `sendMessage()`
- Line 281: `updateConversationMode()`

**Before**:
```typescript
'Authorization': `Bearer ${localStorage.getItem('access_token')}`
```

**After**:
```typescript
import { authManager } from './authManager';

'Authorization': `Bearer ${authManager.getAccessToken()}`
```

**Status**: ⬜ Not Started
**Priority**: P1 - High
**Risk**: Low (authManager already hydrates from localStorage)

---

#### Task 1.3: Centralize Token Access in chatAuthService
**File**: `src/services/chatAuthService.ts`

**Locations to update**:
- Line 149: `initializeConversation()`
- Line 289: `authenticatedFetch()`

**Change**: Same as Task 1.2

**Status**: ⬜ Not Started
**Priority**: P1 - High
**Risk**: Low

---

### Phase 2: Remove HttpOnly Cookie Dependency 🟡

#### Task 2.1: Update Proxy Route for Bearer Tokens
**File**: `app/api/proxy/[...path]/route.ts`

**Current**: Proxy forwards cookies and uses `credentials: 'include'`
**Railway**: Cookies won't work cross-origin, but Bearer tokens will

**Action**: No changes needed! The proxy already forwards Authorization headers correctly.

**Verification**:
```bash
# Test that Authorization header is forwarded
curl -H "Authorization: Bearer test123" http://localhost:3005/api/proxy/api/v1/auth/me
# Check Railway backend logs to verify header was received
```

**Status**: ⬜ Not Started
**Priority**: P2 - Medium
**Risk**: Low (informational check only)

---

#### Task 2.2: Remove cookies.txt from Version Control
**File**: `frontend/cookies.txt`

**Issue**: Contains sensitive JWT token, should not be in git

**Actions**:
1. Add to `.gitignore`:
   ```
   # Sensitive cookie data
   cookies.txt
   *.cookies
   ```
2. Remove from git:
   ```bash
   git rm --cached frontend/cookies.txt
   ```

**Status**: ⬜ Not Started
**Priority**: P2 - Medium (security)
**Risk**: None

---

### Phase 3: Add Token Validation & Expiration Handling 🟡

#### Task 3.1: Add Token Expiration Check
**File**: `src/services/authManager.ts`

**Add new method**:
```typescript
/**
 * Check if current token is expired
 */
isTokenExpired(): boolean {
  if (!this.session) {
    this.hydrateSession();
  }

  if (!this.session) {
    return true;
  }

  return Date.now() >= this.session.expiresAt;
}

/**
 * Get access token only if not expired
 */
getValidAccessToken(): string | null {
  if (this.isTokenExpired()) {
    this.clearSession();
    return null;
  }

  return this.getAccessToken();
}
```

**Status**: ⬜ Not Started
**Priority**: P2 - Medium
**Risk**: Low

---

#### Task 3.2: Update apiClient Interceptor with Expiration Check
**File**: `src/services/apiClient.ts`

**Enhanced interceptor**:
```typescript
apiClient.addRequestInterceptor(async (url, config) => {
  // Check if token is expired
  if (authManager.isTokenExpired()) {
    console.warn('Token expired, clearing session');
    authManager.clearSession();

    // Redirect to login if not already there
    if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
      window.location.href = '/login';
    }

    throw new Error('Authentication token expired');
  }

  const token = authManager.getAccessToken();

  if (token) {
    config.headers = {
      ...config.headers,
      'Authorization': `Bearer ${token}`,
    };
  }

  return { url, config };
});
```

**Status**: ⬜ Not Started
**Priority**: P2 - Medium
**Risk**: Medium (could cause unexpected redirects if buggy)

---

### Phase 4: Strengthen State Persistence 🟢

#### Task 4.1: Add Auth State Hydration on App Load
**File**: `src/app/layout.tsx` or `src/providers/AuthProvider.tsx`

**Add hydration check**:
```typescript
useEffect(() => {
  // Hydrate auth state from localStorage on app load
  const token = authManager.getAccessToken();
  const portfolioId = authManager.getPortfolioId();

  if (token && portfolioId) {
    // Verify token is still valid
    authManager.getCurrentUser().then(user => {
      if (!user) {
        // Token invalid, clear and redirect
        authManager.clearSession();
        window.location.href = '/login';
      }
    });
  }
}, []);
```

**Status**: ⬜ Not Started
**Priority**: P3 - Low
**Risk**: Low

---

#### Task 4.2: Add Portfolio Persistence Debug Logging
**File**: `src/services/portfolioResolver.ts`

**Add logging at key points**:
```typescript
async getUserPortfolioId(forceRefresh = false): Promise<string | null> {
  const token = authManager.getAccessToken();
  if (!token) {
    console.error('[PortfolioResolver] No authentication token found');
    return null;
  }

  // ... existing code ...

  if (Array.isArray(portfolios) && portfolios.length > 0) {
    const portfolio = portfolios[0];
    console.log('[PortfolioResolver] ✅ Portfolio discovered:', {
      id: portfolio.id,
      name: portfolio.name,
      cached: false,
      source: 'Railway backend'
    });
    // ... rest of code ...
  }
}
```

**Status**: ⬜ Not Started
**Priority**: P3 - Low
**Risk**: None (logging only)

---

## Testing Checklist

### Pre-Migration Tests
- [ ] **Backup current working state** - Create git branch `pre-railway-migration`
- [ ] **Document current behavior** - Record which features work/break currently
- [ ] **Export test credentials** - Note demo user emails and passwords

### Phase 1 Tests (Bearer Token Auth)
- [ ] **Test 1.1**: Login with `demo_individual@sigmasight.com`
  - [ ] Verify access_token in localStorage
  - [ ] Verify portfolioId in localStorage
  - [ ] Check browser console for errors

- [ ] **Test 1.2**: Make API call using apiClient
  ```typescript
  import { apiClient } from '@/services/apiClient';
  apiClient.get('/api/v1/data/portfolios').then(console.log);
  ```
  - [ ] Verify Authorization header in Network tab
  - [ ] Verify 200 response (not 401)

- [ ] **Test 1.3**: Navigate to different pages
  - [ ] Dashboard → Settings → Chat → Back to Dashboard
  - [ ] Verify portfolioId persists across navigation
  - [ ] Verify user name displayed correctly

- [ ] **Test 1.4**: Hard refresh (Ctrl+Shift+R)
  - [ ] Verify user stays logged in
  - [ ] Verify portfolioId persists
  - [ ] Verify no re-login required

### Phase 2 Tests (Cross-Origin Verification)
- [ ] **Test 2.1**: Verify Railway backend receives requests
  - [ ] Check Railway logs for incoming requests
  - [ ] Verify Authorization header present in logs
  - [ ] Verify CORS headers in response

- [ ] **Test 2.2**: Test SSE streaming (Chat feature)
  - [ ] Send chat message
  - [ ] Verify streaming works
  - [ ] Check Network tab for SSE connection
  - [ ] Verify Authorization header on SSE request

### Phase 3 Tests (Token Expiration)
- [ ] **Test 3.1**: Simulate expired token
  ```typescript
  // In browser console
  localStorage.setItem('token_expires_at', String(Date.now() - 1000));
  ```
  - [ ] Make API call
  - [ ] Verify redirect to login
  - [ ] Verify session cleared

- [ ] **Test 3.2**: Normal token expiration (wait 30 minutes)
  - [ ] Login
  - [ ] Wait 31 minutes
  - [ ] Try to use app
  - [ ] Verify graceful redirect to login

### Phase 4 Tests (State Persistence)
- [ ] **Test 4.1**: Multi-tab behavior
  - [ ] Open app in Tab A
  - [ ] Login
  - [ ] Open app in Tab B (same browser)
  - [ ] Verify Tab B shows logged-in state

- [ ] **Test 4.2**: Logout behavior
  - [ ] Logout
  - [ ] Verify localStorage cleared
  - [ ] Verify redirect to login
  - [ ] Verify can't access protected pages

### Regression Tests
- [ ] **Portfolio Features**
  - [ ] View portfolio overview
  - [ ] View positions list
  - [ ] View position details
  - [ ] Switch between portfolios (if applicable)

- [ ] **Chat Features**
  - [ ] Create conversation
  - [ ] Send message
  - [ ] Receive streaming response
  - [ ] View conversation history

- [ ] **Analytics Features**
  - [ ] View factor exposure
  - [ ] View Greeks
  - [ ] View correlations
  - [ ] Export reports

---

## Rollback Procedures

### If Migration Fails

#### Step 1: Revert Code Changes
```bash
# If you haven't committed yet
git checkout .

# If you committed to a branch
git checkout main
git branch -D railway-migration

# Restore pre-migration state
git checkout pre-railway-migration
```

#### Step 2: Revert Environment Variables
**File**: `frontend/.env`
```bash
# Change back to localhost
BACKEND_URL=http://localhost:8000
```

#### Step 3: Restart Frontend
```bash
cd frontend
npm run dev
```

#### Step 4: Clear Browser State
```javascript
// In browser console
localStorage.clear();
sessionStorage.clear();
location.reload();
```

### If Partial Migration Works
**Scenario**: Some features work, others don't

**Action**: Document what works/breaks, continue with remaining tasks. The migration is designed to be incremental.

---

## Post-Migration Validation

### Success Criteria ✅
- [ ] Login works and persists across page refreshes
- [ ] userId and portfolioId persist throughout session
- [ ] All API calls include Authorization header
- [ ] Portfolio data loads correctly from Railway backend
- [ ] Chat streaming works with Railway backend
- [ ] No CORS errors in browser console
- [ ] Token expiration handled gracefully
- [ ] Multi-tab behavior works correctly

### Performance Metrics
- [ ] **API Response Time**: < 500ms (Railway backend)
- [ ] **SSE First Token**: < 2s (Chat streaming)
- [ ] **Page Load Time**: < 3s (with Railway data)
- [ ] **Auth Check Time**: < 200ms

### Monitoring & Logging
Add these console logs temporarily for debugging:

```typescript
// In authManager.ts
console.log('[AuthManager] Token status:', {
  hasToken: !!this.getAccessToken(),
  isExpired: this.isTokenExpired(),
  portfolioId: this.getPortfolioId(),
  user: this.getCachedUser()?.email
});

// In apiClient.ts interceptor
console.log('[ApiClient] Request:', {
  url,
  hasAuth: !!config.headers?.['Authorization'],
  timestamp: new Date().toISOString()
});
```

Remove after successful migration.

---

## Risk Assessment

### High Risk Items 🔴
| Risk | Impact | Mitigation |
|------|--------|------------|
| Token expiration not handled | Users kicked out mid-session | Implement Task 3.1, 3.2 |
| CORS misconfiguration | All API calls fail | Already verified backend CORS ✅ |
| State sync issues | userId/portfolioId lost | Centralize through authManager |

### Medium Risk Items 🟡
| Risk | Impact | Mitigation |
|------|--------|------------|
| Multiple localStorage reads | Stale data | Centralize via authManager (Tasks 1.2, 1.3) |
| SSE auth failure | Chat doesn't work | Already uses Bearer tokens ✅ |
| Cookie dependency | Legacy code breaks | Fully migrate to Bearer tokens |

### Low Risk Items 🟢
| Risk | Impact | Mitigation |
|------|--------|------------|
| cookies.txt in git | Security concern | Remove from version control |
| Performance degradation | Slower API calls | Monitor Railway backend latency |
| Browser compatibility | Edge cases | Test in Chrome, Firefox, Safari |

---

## Architecture Decision Records (ADRs)

### ADR-001: Bearer Token Authentication over HttpOnly Cookies

**Date**: 2025-10-05
**Status**: ✅ Approved
**Context**: Moving from localhost backend to Railway (cross-origin)

**Decision**: Use Bearer token authentication (Authorization header) instead of HttpOnly cookies

**Rationale**:
- ✅ Works across different origins (localhost → Railway)
- ✅ Already implemented in 75% of services
- ✅ Simpler than CORS cookie configuration
- ✅ Industry standard for SPAs with separate backends
- ❌ Less secure than HttpOnly cookies (XSS vulnerability)

**Mitigation**:
- Store tokens in localStorage (standard practice)
- Implement short token lifetime (30 minutes)
- Add token expiration checks
- Future: Implement refresh token rotation

---

### ADR-002: Centralized Token Management via authManager

**Date**: 2025-10-05
**Status**: ✅ Approved
**Context**: Multiple services reading localStorage directly

**Decision**: All token access must go through `authManager.getAccessToken()`

**Rationale**:
- ✅ Single source of truth
- ✅ Enables token validation/refresh logic
- ✅ Easier debugging and logging
- ✅ Prevents stale token reads
- ❌ Slight performance overhead

**Migration Path**: Update all direct `localStorage.getItem('access_token')` calls

---

## Appendix

### A. File Reference

**Authentication Services**:
- `src/services/apiClient.ts` - Generic API client (needs auth fix)
- `src/services/requestManager.ts` - Retry/dedupe manager (✅ works)
- `src/services/chatService.ts` - Chat API service (✅ works)
- `src/services/chatAuthService.ts` - Chat auth (✅ works)
- `src/services/authManager.ts` - Token management (✅ works)
- `src/services/portfolioResolver.ts` - Portfolio discovery (✅ works)

**Auth Hooks**:
- `src/hooks/useFetchStreaming.ts` - SSE streaming (✅ works)

**State Management**:
- `src/stores/portfolioStore.ts` - Portfolio Zustand store

**Backend Config**:
- `backend/app/config.py` - CORS settings (lines 103-108)
- `backend/app/main.py` - CORS middleware (lines 24-30)

### B. Environment Variables

**Frontend** (`frontend/.env`):
```bash
# Backend Integration
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-production.up.railway.app/api/v1
BACKEND_API_URL=http://localhost:8000/api/v1  # Deprecated for Railway
BACKEND_URL=https://sigmasight-be-production.up.railway.app  # Proxy uses this
```

**Backend** (Railway environment):
```bash
ALLOWED_ORIGINS=http://localhost:3005,https://sigmasight-frontend.vercel.app
```

### C. Useful Commands

**Check localStorage state**:
```javascript
// In browser console
console.table({
  access_token: localStorage.getItem('access_token')?.substring(0, 20) + '...',
  user_email: localStorage.getItem('user_email'),
  portfolio_id: localStorage.getItem('portfolio_id'),
  token_expires_at: new Date(Number(localStorage.getItem('token_expires_at'))).toLocaleString()
});
```

**Test API call with token**:
```javascript
// In browser console
const token = localStorage.getItem('access_token');
fetch('https://sigmasight-be-production.up.railway.app/api/v1/auth/me', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(console.log);
```

**Check CORS from Railway backend**:
```bash
curl -I -X OPTIONS \
  -H "Origin: http://localhost:3005" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization" \
  https://sigmasight-be-production.up.railway.app/api/v1/auth/me
```

---

## Progress Tracking

**Last Updated**: 2025-10-05
**Completed**: 0/16 tasks
**In Progress**: Investigation complete
**Blocked**: None

**Next Steps**:
1. ✅ Investigation complete
2. ⬜ Start Phase 1: Task 1.1 (Fix apiClient interceptor)
3. ⬜ Test Phase 1
4. ⬜ Continue to Phase 2

---

## Questions & Answers

**Q: Will this break local development?**
A: No, the backend CORS already allows localhost:3005. Both local and Railway backends will work.

**Q: Do we need to change the backend?**
A: No, backend is already configured correctly for Railway + cross-origin requests.

**Q: What if Railway backend is down?**
A: Frontend will get network errors. Consider adding a fallback or status page.

**Q: Can we keep using cookies?**
A: Not recommended. Cross-origin cookies require complex SameSite/domain configuration. Bearer tokens are simpler and already 75% implemented.

**Q: Will this affect production deployment?**
A: This is for Railway backend. Production frontend (Vercel) will need similar Bearer token setup.

---

**Document Maintained By**: Claude Code
**Review Status**: 🟡 Pending User Approval
**Version**: 1.0
