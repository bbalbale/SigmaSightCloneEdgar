# ClerkAuth Bug Fixes & Improvements

**Created**: 2026-01-06
**Status**: Tracking post-deployment issues

---

## Bug #1: BETA_INVITE_CODE Not Set in Railway

**Priority**: High
**Status**: Open

### Issue
The `BETA_INVITE_CODE` environment variable is not set in Railway backend, causing the system to use the default code from `config.py`.

### Evidence
```
2026-01-06 19:24:56 - WARNING - Invalid invite code attempt: user=elliott.ng+1testr001@gmail.com, code=2026***
```

User entered `2026-FOUNDERS-BETA` but Railway is using default `PRESCOTT-LINNAEAN-COWPERTHWAITE`.

### Root Cause
- `backend/app/config.py:181` has default: `PRESCOTT-LINNAEAN-COWPERTHWAITE`
- `BETA_INVITE_CODE` was not added to Railway environment variables during deployment

### Fix
Add to Railway backend env vars:
```bash
railway variables set BETA_INVITE_CODE=2026-FOUNDERS-BETA --service SigmaSight-BE
```

Or set via Railway dashboard for SigmaSight-BE service.

---

## Bug #2: Invite Code Error Message Not User-Friendly

**Priority**: Medium
**Status**: Open

### Issue
When a user enters an invalid invite code, the error message is generic and doesn't help them understand what went wrong.

### Current Behavior
Error returned:
```json
{
  "error": "invalid_invite_code",
  "message": "The invite code you entered is not valid. Please check and try again."
}
```

### Suggested Improvements
1. Add hint about where to get the invite code (e.g., "Contact support" or "Check your invite email")
2. Consider rate limiting with clearer messaging after multiple failed attempts
3. Frontend could show more helpful UI (e.g., link to request invite code)

### Files to Modify
- Backend: `backend/app/api/v1/endpoints/onboarding.py` (or wherever invite validation occurs)
- Frontend: Error handling in invite code form component

---

## Bug #4: Token Refresh May Not Work Reliably in Background

**Priority**: High
**Status**: ✅ FIXED (2026-01-06)

### Issue
The Clerk JWT token (60-second expiry) may expire while user is on Settings page, causing 401 errors when submitting the invite code.

### Solution Implemented
Created custom JWT template `sigmasight-session` in Clerk Dashboard with **1-hour lifetime** (3600 seconds).

Updated frontend to use the template:
- `frontend/app/providers.tsx` - ClerkTokenSync uses template, refreshes every 50 min
- `frontend/src/components/onboarding/InviteCodeForm.tsx` - Uses template
- `frontend/src/hooks/useApiClient.ts` - All getToken calls use template

**Commit**: `387c34d6` - feat: Use custom JWT template with 1-hour token lifetime

---

## Bug #3: (Potential) CLERK_SECRET_KEY May Be Using Test Key

**Priority**: Low
**Status**: To Verify

### Issue
During deployment, we used the existing test Clerk project (`included-chimp-71.clerk.accounts.dev`). When moving to production, ensure production Clerk keys are used.

### Verification Steps
1. Confirm if test keys are acceptable for beta launch
2. If production keys needed, create new Clerk project
3. Update Railway env vars with production keys:
   - `CLERK_SECRET_KEY`
   - `CLERK_DOMAIN`
   - Frontend: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`

---

## Deployment Checklist Updates

Based on this deployment, update `CLERK_AUTH_DEPLOYMENT_PLAN.md` Phase 1.3 to include:
- [ ] Add `BETA_INVITE_CODE` to Railway backend env vars

---

## Completed Items

- [x] Webhook endpoint configured: `whsec_E4GYCQVFhO0pXoy7VWj/9M4EGb5x7Cin`
- [x] Database migration applied: `d5e6f7g8h9i0_add_clerk_auth_columns`
- [x] Demo accounts synced with Clerk user IDs
- [x] Backend health check passing
- [x] Frontend sign-in page loading Clerk UI
