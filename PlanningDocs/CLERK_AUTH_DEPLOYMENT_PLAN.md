# ClerkAuth Branch Merge & Railway Deployment Plan

**Created**: 2026-01-06
**Status**: Ready for execution

## Overview

Merge the ClerkAuth branch into main and deploy to Railway production. This is a **breaking change** that replaces custom JWT authentication with Clerk authentication.

**Branch**: `ClerkAuth` → `main`
**Commits**: 5 (1 core feature, 1 migration, 2 fixes, 1 docs)
**Files Changed**: 76 files (+8,635 / -455 lines)

### Decisions Made
- **Clerk Project**: Use existing test project (`included-chimp-71.clerk.accounts.dev`)
- **Frontend Deployment**: Separate Railway service (needs its own env vars)
- **Execution**: Step-by-step together with Claude

---

## Phase 1: Pre-Merge Preparation

### 1.1 Clerk Credentials (Using Existing Test Project)

Using test project: `included-chimp-71.clerk.accounts.dev`

| Variable | Value Source |
|----------|-------------|
| `CLERK_SECRET_KEY` | Already in frontend/.env.local |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Already in frontend/.env.local |
| `CLERK_WEBHOOK_SECRET` | Clerk Dashboard → Webhooks → Create/edit webhook |
| `CLERK_DOMAIN` | `included-chimp-71.clerk.accounts.dev` |

### 1.2 Configure Clerk Webhook

In Clerk Dashboard → Webhooks:
1. Create new webhook endpoint: `https://sigmasight-be-production.up.railway.app/api/v1/webhooks/clerk`
2. Select events:
   - `user.created`
   - `user.deleted`
   - `subscription.created` (if using Clerk billing)
   - `subscription.cancelled` (if using Clerk billing)
3. Copy the signing secret → `CLERK_WEBHOOK_SECRET`

### 1.3 Add Environment Variables to Railway

**Backend Service** (sigmasight-be-production):
```
CLERK_DOMAIN=included-chimp-71.clerk.accounts.dev
CLERK_SECRET_KEY=sk_test_... (from frontend/.env.local)
CLERK_WEBHOOK_SECRET=whsec_... (from Clerk webhook config)
CLERK_AUDIENCE=  (leave empty)
```

**Frontend Service** (separate Railway service):
```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_... (from frontend/.env.local)
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/command-center
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/onboarding/upload
NEXT_PUBLIC_CLERK_DOMAIN=included-chimp-71.clerk.accounts.dev
CLERK_SECRET_KEY=sk_test_... (needed for middleware)
```

**Note**: Frontend needs CLERK_SECRET_KEY for Next.js middleware server-side auth checks.

---

## Phase 2: Merge & Deploy

### 2.1 Merge to Main

```bash
git checkout main
git pull origin main
git merge ClerkAuth
git push origin main
```

### 2.2 Railway Auto-Deploy

Railway will automatically:
1. Detect push to main
2. Build backend image
3. Deploy new version

### 2.3 Run Database Migration

After deployment completes:

```bash
# SSH into Railway or use Railway CLI
railway run alembic -c alembic.ini upgrade head
```

**Migration**: `d5e6f7g8h9i0_add_clerk_auth_columns`
- Adds 5 columns to `users` table:
  - `clerk_user_id` (String, unique index)
  - `tier` (String, default='free')
  - `invite_validated` (Boolean, default=False)
  - `ai_messages_used` (Integer, default=0)
  - `ai_messages_reset_at` (DateTime, default=now())

---

## Phase 3: Demo Account Migration

### 3.1 Dry Run Verification

```bash
railway run python scripts/migrate_to_clerk_dryrun.py
```

This verifies:
- CLERK_SECRET_KEY is set
- Demo accounts exist in database
- No users already have clerk_user_id

### 3.2 Execute Migration

```bash
railway run python scripts/migrate_to_clerk.py
```

This will:
1. Create Clerk users for each demo account
2. Update database with `clerk_user_id`
3. Set `invite_validated=true` for demo accounts

**Demo accounts to migrate**:
- `demo_individual@sigmasight.com`
- `demo_hnw@sigmasight.com`
- `demo_hedgefundstyle@sigmasight.com`

---

## Phase 4: Verification Test Plan

### 4.1 Backend API Tests

| Test | Endpoint | Expected Result |
|------|----------|-----------------|
| Health check | `GET /health` | 200 OK |
| Auth me (no token) | `GET /api/v1/auth/me` | 401 Unauthorized |
| Auth me (Clerk token) | `GET /api/v1/auth/me` | 200 with tier, limits |
| Webhook endpoint | `POST /api/v1/webhooks/clerk` | Accepts Clerk events |

### 4.2 Authentication Flow Tests

| Test | Steps | Expected Result |
|------|-------|-----------------|
| Sign up flow | Visit /sign-up → Create account | Redirects to /onboarding/upload |
| Sign in flow | Visit /sign-in → Enter credentials | Redirects to /command-center |
| Demo login | Sign in as demo_hnw@sigmasight.com | Access to all features |
| Token refresh | Wait 60+ seconds on page | No auth errors (auto-refresh) |
| Sign out | Click sign out | Redirects to /sign-in |

### 4.3 Feature Tests

| Feature | Test | Expected Result |
|---------|------|-----------------|
| Portfolio loading | Visit /command-center | Portfolio data loads |
| AI Chat | Send message | SSE stream works, response received |
| Analytics | Visit /risk-analysis | Factor exposures, correlations load |
| Tags | Visit /organize | Tags load and can be created |
| Position details | Click position | Risk metrics load |

### 4.4 Tier Limit Tests (if applicable)

| Test | Steps | Expected Result |
|------|-------|-----------------|
| Portfolio limit | Create portfolios up to limit | Shows upgrade prompt |
| AI message limit | Send messages up to limit | Shows limit warning |
| Upgrade flow | Click upgrade | Redirects to Clerk billing |

### 4.5 Webhook Tests

Verify in Clerk Dashboard → Webhooks → Recent deliveries:
- Events are being received
- Signature verification passing
- 200 responses from backend

---

## Phase 5: Rollback Plan

### If Issues Occur

**Option A: Revert Merge (if caught quickly)**
```bash
git checkout main
git revert HEAD
git push origin main
```

**Option B: Restore from Previous Deployment**
- Railway dashboard → Deployments → Select previous → Rollback

**Option C: Database Rollback**
```bash
railway run alembic -c alembic.ini downgrade -1
```

### Critical Rollback Considerations

1. **Users created via Clerk** will have `clerk_user_id` set
2. **Demo accounts** may need re-migration if rolled back then re-deployed
3. **Clerk webhooks** should be paused in Clerk dashboard during rollback

---

## Deployment Checklist

### Pre-Merge
- [ ] Clerk production project created (or using test)
- [ ] All 4 backend env vars added to Railway
- [ ] All 6 frontend env vars added (if separate service)
- [ ] Webhook endpoint configured in Clerk dashboard
- [ ] Webhook events selected: user.created, user.deleted

### Merge & Deploy
- [ ] Merged ClerkAuth to main
- [ ] Railway deployment completed successfully
- [ ] Database migration ran: `alembic upgrade head`
- [ ] Migration output shows 5 columns added

### Demo Account Migration
- [ ] Dry run passed: `migrate_to_clerk_dryrun.py`
- [ ] Migration executed: `migrate_to_clerk.py`
- [ ] All 3 demo accounts have clerk_user_id

### Verification
- [ ] Backend health check passes
- [ ] Demo user can sign in via Clerk
- [ ] /api/v1/auth/me returns tier and limits
- [ ] Portfolio data loads correctly
- [ ] AI chat works (SSE streaming)
- [ ] Analytics endpoints return data
- [ ] Tags/positions load correctly
- [ ] Clerk webhook events showing in dashboard
- [ ] No errors in Railway logs

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Clerk credentials misconfigured | Medium | High | Test in staging first |
| Database migration fails | Low | High | Test migration locally first |
| Demo account migration fails | Low | Medium | Dry run validates first |
| Token refresh issues | Low | Medium | 50-second refresh prevents expiry |
| Webhook signature fails | Medium | Medium | Verify CLERK_WEBHOOK_SECRET |

---

## Files Modified (Key Files)

**Backend**:
- `backend/app/core/clerk_auth.py` (new - JWT verification)
- `backend/app/api/v1/webhooks/clerk.py` (new - webhook handler)
- `backend/app/services/usage_service.py` (new - tier limits)
- `backend/migrations_core/versions/d5e6f7g8h9i0_add_clerk_auth_columns.py`

**Frontend**:
- `frontend/app/providers.tsx` (ClerkProvider, token sync)
- `frontend/middleware.ts` (route protection)
- `frontend/src/lib/clerkTokenStore.ts` (token management)
- `frontend/src/services/apiClient.ts` (Clerk token injection)
