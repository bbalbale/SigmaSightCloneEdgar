# Auth & Billing Migration Progress

**Project**: Clerk Authentication & Billing Integration
**PRD Version**: 1.14
**Target**: 100 paying users for product validation
**Started**: 2026-01-04

---

## Current Status

| Phase | Status | Started | Completed |
|-------|--------|---------|-----------|
| Phase 1: Clerk Setup | ✅ COMPLETE | 2026-01-05 | 2026-01-05 |
| Phase 2: Backend Auth | ✅ COMPLETE | 2026-01-05 | 2026-01-05 |
| Phase 3: Frontend Auth | ✅ COMPLETE | 2026-01-05 | 2026-01-05 |
| Phase 4: Testing & Migration | 🔄 IN PROGRESS | 2026-01-05 | - |

**Active Phase**: Phase 4 - Testing & Migration (local testing complete, production deploy pending)

---

## Quick Links

- [PRD v1.14](./PRD_AUTH_BILLING_CLERK.md) - Full specification
- [Phase 1: Clerk Setup](./PHASES_AUTH_BILLING/PHASE_1_CLERK_SETUP.md)
- [Phase 2: Backend Auth](./PHASES_AUTH_BILLING/PHASE_2_BACKEND_AUTH.md)
- [Phase 3: Frontend Auth](./PHASES_AUTH_BILLING/PHASE_3_FRONTEND_AUTH.md)
- [Phase 4: Testing & Migration](./PHASES_AUTH_BILLING/PHASE_4_TESTING_MIGRATION.md)

---

## Completed Work

### Planning Phase (Complete)
- [x] PRD v1.8 initial draft
- [x] PRD v1.9 aligned with Clerk Billing (not direct Stripe)
- [x] PRD v1.10 stricter invite enforcement
- [x] PRD v1.11 invite code configuration (2026-FOUNDERS-BETA)
- [x] PRD v1.12 admin system separation documented
- [x] PRD v1.13 security/resilience fixes (JWKS, JIT, hooks, atomic SQL)
- [x] PRD v1.14 simplification pass (removed slowapi, atomic SQL, svix tracking)

---

## Blockers

None currently.

---

## Session Log

### 2026-01-05 - Phase 4 IN PROGRESS (Local Testing Complete)

**Migration scripts created and run successfully:**

#### 4.2 Dry-Run Migration ✅
- Created `backend/scripts/migrate_to_clerk_dryrun.py`
- Validates demo accounts exist, required columns present, Clerk API reachable

#### 4.3 Demo Account Migration ✅
- Created `backend/scripts/migrate_to_clerk.py`
- Successfully migrated 3 demo accounts to Clerk:
  - `demo_individual@sigmasight.com` → `user_37qyX3FtBwgylQeoq8Ag4YouNBk`
  - `demo_hnw@sigmasight.com` → `user_37qyX28BT2mgIsdHcykRxyfLJD2`
  - `demo_hedgefundstyle@sigmasight.com` → `user_37qyX63nRcwq3PieXSdhjP79a7D`
- Database updated with `clerk_user_id` values
- All accounts set `invite_validated=true`, `tier='free'`

#### 4.7.1 Demo Account Login ✅
- Password changed from "demo12345" to "SigmaSight!Demo2025" (Clerk rejected compromised password)
- Fixed Clerk Dashboard "Client Trust" setting that caused new device verification prompts
- All 3 demo accounts login successfully:
  - ✅ demo_individual login works
  - ✅ demo_hnw login works (verified via cookie:__session auth)
  - ✅ demo_hedgefundstyle login works (verified via bearer token auth)

#### Docker/Frontend Fixes
- Added Clerk build args to `frontend/Dockerfile` for Next.js static page generation
- Added Clerk build args to `frontend/docker-compose.yml`
- Fixed real CLERK_SECRET_KEY in `frontend/.env.local`

#### Code Cleanup
- Removed unused TradeFeed data provider (not using that service)
  - Moved `tradefeeds_client.py` to `backend/_archive/`
  - Cleaned up `factory.py`, `__init__.py`
- Fixed missing `CurrentUser` import in `insights.py`

**Committed to git**: `7d2619cf` on branch `AuthOnboarding`

**Backend logs confirm auth working:**
```
Clerk user authenticated: demo_hnw@sigmasight.com (method: cookie:__session)
Clerk user authenticated: demo_hedgefundstyle@sigmasight.com (method: bearer)
```

**Remaining Phase 4 tasks:**
- [ ] 4.1 Pre-Deployment Checklist (backup, prod env vars)
- [ ] 4.4 Deploy Backend to Railway
- [ ] 4.5 Configure Production Webhook
- [ ] 4.6 Deploy Frontend
- [ ] 4.7.2-4.7.5 Post-deployment verification (new signup, billing, AI chat, admin)
- [ ] 4.8 Monitor First 24 Hours

---

### 2026-01-05 - Phase 3 Code Review Fixes (All blocking issues resolved)

**Code review identified critical issues preventing API calls. All fixed:**

#### Fix #1: authManager not receiving Clerk tokens ✅
**Files**: `src/services/authManager.ts`
- **Issue**: Services like `tagsApi`, `portfolioService`, `chatService` all use `authManager.getAccessToken()` which returned `null` because nothing calls `authManager.setSession()` with Clerk auth.
- **Fix**: Updated `getAccessToken()` to check `clerkTokenStore` first (Clerk path), then fall back to localStorage (legacy path). All existing services now automatically work with Clerk tokens.

#### Fix #2: portfolioResolver failing ✅
**Files**: `src/services/portfolioResolver.ts` (no changes needed)
- **Issue**: `getUserPortfolioId()` called `authManager.getAccessToken()` which was returning `null`.
- **Fix**: Automatically fixed by Fix #1 - `authManager.getAccessToken()` now returns Clerk tokens.

#### Fix #3: useUserEntitlements wrong response shape ✅
**Files**: `src/hooks/useUserEntitlements.ts`
- **Issue**: Hook expected flat fields (`max_portfolios`, `ai_messages_used`) but backend returns nested `limits` object.
- **Fix**: Updated response mapping to use `response.limits.max_portfolios`, etc. Also added `portfolioId` field and removed non-existent `clerkUserId`.

#### Fix #4: providers.tsx redirect loop ✅
**Files**: `app/providers.tsx`
- **Issue**: Legacy `authManager.getAccessToken()` was called but never set, causing redirect loops.
- **Fix**: Rewrote to use Clerk hooks (`useClerkAuth`, `useUser`, `useClerk`). Auth state now driven by Clerk's `isSignedIn` and `clerkUser`.

#### Fix #5: Legacy registration page ✅
**Files**: `app/test-user-creation/page.tsx`
- **Issue**: Used legacy registration flow that won't work with Clerk auth.
- **Fix**: Now redirects to Clerk `/sign-up` page.

**Known Concerns for Phase 4 Testing:**
1. `authManager.setSession()` still called from legacy flows but not during Clerk sign-in. localStorage tokens not cleared on Clerk logout.
2. Initial render race: `getClerkToken()` returns null until `ClerkTokenSync` effect runs. May cause one 401 + retry.

**Phase 3 Exit Criteria**: All blocking issues resolved. Ready for Phase 4 testing.

---

### 2026-01-05 - Phase 3 COMPLETE (12/12 tasks)

**All frontend auth migration tasks completed:**

#### 3.1 Install Clerk SDK ✅
- Installed `@clerk/nextjs@6.36.5` and `@clerk/themes@2.4.46`
- Also installed `@radix-ui/react-progress` for usage UI

#### 3.2 Environment Variables ✅
- Added Clerk keys to `frontend/.env.local`
- Configured redirect URLs (`/sign-in`, `/sign-up`, `/settings`)
- Set Clerk domain for billing portal links

#### 3.3 ClerkProvider Setup ✅
- Wrapped `app/layout.tsx` with `ClerkProvider`
- ClerkProvider is outermost wrapper around entire app

#### 3.4 Middleware Configuration ✅
- Created `frontend/middleware.ts`
- Protects all routes except public paths
- Admin routes bypass Clerk (have own auth)
- API routes pass through for proxy

#### 3.5 Sign-In Page ✅
- Created `app/sign-in/[[...sign-in]]/page.tsx`
- Uses Clerk `<SignIn />` component with dark theme
- Styled to match app design

#### 3.6 Sign-Up Page ✅
- Created `app/sign-up/[[...sign-up]]/page.tsx`
- Uses Clerk `<SignUp />` component with dark theme
- Redirects to `/settings` after signup

#### 3.7 useApiClient Hook ✅
- Created `src/hooks/useApiClient.ts`
- Provides `authFetch`, `getAuthHeaders`, `getToken`
- For use in React components needing Clerk tokens

#### 3.8 Update Service Layer ✅
- Created `src/lib/clerkTokenStore.ts` for token sharing
- Updated `apiClient.ts` interceptor to use Clerk tokens
- Added `ClerkTokenSync` component to `providers.tsx`
- Token refreshes every 50 seconds automatically

#### 3.9 Settings Page Updates ✅
- Created `src/components/settings/AccountBillingSettings.tsx`
- Shows invite code form (if not validated)
- Shows billing portal link
- Displays usage stats (portfolios, AI messages)
- Created `src/hooks/useUserEntitlements.ts`

#### 3.10 Upgrade Prompts ✅
- Created `src/components/billing/UpgradePrompt.tsx`
- Reusable component for portfolio/AI limits
- Shows upgrade CTA when at limit

#### 3.11 Remove Old Auth Components ✅
- Updated `app/login/page.tsx` to redirect to `/sign-in`
- Legacy login page shows spinner then redirects

#### 3.12 UserButton in Navigation ✅
- Updated `src/components/navigation/UserDropdown.tsx`
- Uses Clerk `<UserButton />` with dark theme
- Shows Settings link in dropdown
- Shows Sign In button when signed out

**Type Check**: All TypeScript errors resolved

**Files Created (10 new files):**
1. `frontend/middleware.ts`
2. `frontend/app/sign-in/[[...sign-in]]/page.tsx`
3. `frontend/app/sign-up/[[...sign-up]]/page.tsx`
4. `frontend/src/hooks/useApiClient.ts`
5. `frontend/src/hooks/useUserEntitlements.ts`
6. `frontend/src/lib/clerkTokenStore.ts`
7. `frontend/src/components/settings/AccountBillingSettings.tsx`
8. `frontend/src/components/billing/UpgradePrompt.tsx`
9. `frontend/src/components/ui/progress.tsx`

**Files Modified (6 files):**
1. `frontend/.env.local` - Added Clerk variables
2. `frontend/app/layout.tsx` - Added ClerkProvider
3. `frontend/app/providers.tsx` - Added ClerkTokenSync
4. `frontend/app/login/page.tsx` - Redirect to sign-in
5. `frontend/src/services/apiClient.ts` - Clerk token support
6. `frontend/src/components/navigation/UserDropdown.tsx` - Clerk UserButton
7. `frontend/src/containers/SettingsContainer.tsx` - AccountBillingSettings

**Next:** Phase 4 - Testing & Migration
- Run end-to-end tests
- Verify all auth flows work
- Test with real Clerk credentials

---

### 2026-01-05 - Phase 2 Code Review Fixes (5/5 issues resolved)

**AI code review identified 5 critical issues. All fixed:**

#### Fix #1: Invite Validation Persistence Bug ✅
**File**: `app/api/v1/onboarding.py`
- **Issue**: `current_user` from `get_current_user_clerk` was detached from the db session, so `await db.commit()` wrote nothing
- **Fix**: Re-query user in the endpoint's session before updating `invite_validated`

#### Fix #2: Webhook Signature Verification Security ✅
**File**: `app/api/v1/webhooks/clerk.py`
- **Issue**: Homegrown HMAC verification lacked timestamp tolerance, vulnerable to replay attacks
- **Fix**: Replaced with official `svix` library using `Webhook.verify()` which validates signature AND timestamp freshness

#### Fix #3: SSE Cookie Names ✅
**Files**: `app/core/clerk_auth.py`, `app/core/dependencies.py`
- **Issue**: Code looked for `clerk_token` cookie but Clerk uses `__session` and `__client`
- **Fix**: Changed cookie aliases to `__session` (primary) and `__client` (fallback)

#### Fix #4: /auth/me Endpoint Auth Switch ✅
**File**: `app/api/v1/auth.py`
- **Issue**: `/me` endpoint still used legacy `get_current_user` instead of Clerk auth
- **Fix**: Switched to `Depends(get_current_user_clerk)` for proper Clerk JWT verification

#### Fix #5: Apply Validated User Guard to Protected Routes ✅
**Files**: `portfolios.py`, `chat/send.py`, `onboarding.py`
- **Issue**: Protected routes still used legacy auth, `get_validated_user` guard wasn't applied
- **Fix**: Updated all protected routes:
  - **portfolios.py**: Read operations use `get_current_user_clerk`, write operations use `get_validated_user`
  - **chat/send.py**: `/send` uses `get_validated_user` (AI feature requires invite)
  - **onboarding.py**: `/create-portfolio` uses `get_validated_user`

**Phase 2 Now Truly Complete**: All endpoints properly secured with Clerk auth + invite validation.

---

### 2026-01-05 - Additional Code Review Fixes (2/2 issues resolved)

**Second code review identified 2 more issues. Both fixed:**

#### Fix #6: Remove `__client` Cookie Fallback ✅
**Files**: `app/core/clerk_auth.py`, `app/core/dependencies.py`
- **Issue**: `__client` cookie is NOT a JWT - it's a metadata blob containing settings, not a token. Code was trying to decode it as RS256, causing "JWT token missing 'kid'" warnings.
- **Fix**: Removed `__client` cookie as a fallback. Now only uses `__session` cookie (the actual Clerk JWT) or Bearer token.

#### Fix #7: Complete Auth Migration to Clerk ✅
**Files**: 18 router files updated
- **Issue**: Large parts of the API still expected legacy HS256 JWT tokens (`get_current_user`), not Clerk RS256 tokens.
- **Fix**: Updated ALL remaining routers to use Clerk auth:
  - **Read-only endpoints** → `get_current_user_clerk` (Clerk JWT, no invite check)
  - **Write/mutation endpoints** → `get_validated_user` (Clerk JWT + invite_validated check)

**Files Updated:**
1. `app/api/v1/agent_memories.py` → `get_validated_user`
2. `app/api/v1/tags.py` → `get_validated_user`
3. `app/api/v1/insights.py` → `get_validated_user`
4. `app/api/v1/position_tags.py` → `get_validated_user`
5. `app/api/v1/equity_changes.py` → `get_validated_user`
6. `app/api/v1/endpoints/fundamentals.py` → `get_current_user_clerk`
7. `app/api/v1/admin_fix.py` → `get_validated_user`
8. `app/api/v1/target_prices.py` → `get_validated_user`
9. `app/api/v1/auth.py` (refresh/logout) → `get_current_user_clerk`

**Verification**: Grep shows NO remaining `Depends(get_current_user)` calls in `/app/api/v1/`.

**Phase 2 Fully Complete**: Backend now 100% Clerk auth. Ready for Phase 3 frontend migration.

---

### 2026-01-05 - Phase 2 COMPLETE (11/11 tasks)
**Final tasks completed:**

- **2.10 Update Existing Endpoints** ✅ COMPLETE
  - Tier limit check in portfolio creation ✅
  - AI message limit check in chat/send.py ✅
  - Auth switch to Clerk: DEFERRED to Phase 3 (breaking change, needs frontend coordination)

- **2.11 Auth/Me Endpoint Update** ✅ COMPLETE
  - Created `UserMeResponse` schema in `app/schemas/auth.py`
  - Updated `/me` endpoint to return:
    - User info (id, email, full_name, is_active, created_at)
    - Clerk fields (tier, invite_validated)
    - Portfolio info (portfolio_id, portfolio_count)
    - Limits (max_portfolios, max_ai_messages, ai_messages_used, ai_messages_remaining)

**Phase 2 Exit Criteria:**
- All 11 tasks complete
- Backend ready for Clerk JWT authentication
- Webhook handler ready to receive Clerk events
- `/me` endpoint returns entitlements for frontend Settings page

**Next:** Phase 3 - Frontend Auth Migration

---

### 2026-01-05 - Phase 2 Progress Audit (9.5/11 tasks complete)
**Code analysis revealed significant progress not tracked in previous session:**

- **2.4 Clerk Auth Module** ✅ COMPLETE
  - Created `app/core/clerk_auth.py` (351 lines)
  - `get_jwks()` with async httpx + TTLCache
  - `get_current_user_clerk()` with RS256 verification
  - `jit_provision_user()` for webhook race conditions
  - `get_user_by_clerk_id()` helper

- **2.5 Consolidated Guard Dependency** ✅ COMPLETE
  - `get_validated_user()` in `app/core/dependencies.py`
  - `ValidatedUser` type alias
  - Returns 403 with invite_required if not validated

- **2.6 Tier Limits** ✅ COMPLETE (covered in 2.3)
  - `TIER_LIMITS` dict in config.py
  - `get_tier_limit()` helper function

- **2.7 AI Message Counter** ✅ COMPLETE
  - Created `app/services/usage_service.py` (121 lines)
  - `check_and_increment_ai_messages()` with monthly reset
  - Returns (allowed, remaining, limit) tuple

- **2.8 Webhook Handler** ✅ COMPLETE
  - Created `app/api/v1/webhooks/clerk.py` (317 lines)
  - `verify_clerk_webhook()` signature verification
  - Handlers: user.created, user.deleted, subscription.created/cancelled
  - Registered in router.py

- **2.9 Invite Validation** ✅ COMPLETE
  - POST `/validate-invite` in onboarding.py
  - `validate_code()` helper (case-insensitive)
  - Uses `get_current_user_clerk` dependency

- **2.10 Update Existing Endpoints** ⚠️ PARTIAL
  - ✅ Tier limit check added to portfolio creation
  - ✅ AI message limit check added to chat/send.py
  - ❌ Endpoints still use `get_current_user` (legacy), not `get_validated_user`
  - Note: Full switch to Clerk auth happens with Phase 3 frontend

- **2.11 Auth/me Endpoint** ❌ NOT STARTED
  - Current `/me` returns basic CurrentUser schema
  - Needs UserMeResponse with portfolio_count, limits, tier, etc.

**Next session:**
- Complete 2.11: Update `/me` endpoint with UserMeResponse schema
- Then: Decide if 2.10 endpoint auth switch is needed before Phase 3

---

### 2026-01-05 - Phase 2 Started (3/11 tasks complete)
**What was done:**
- **2.1 Database Schema** ✅
  - Created migration `s5t6u7v8w9x0_add_clerk_auth_columns.py`
  - Added 5 columns: `clerk_user_id`, `tier`, `invite_validated`, `ai_messages_used`, `ai_messages_reset_at`
  - Added unique index on `clerk_user_id`
  - Updated User model in `app/models/users.py`
- **2.2 Dependencies** ✅
  - Added `python-jose[cryptography]>=3.3.0` via `uv add`
  - Added `cachetools>=6.2.4` via `uv add`
- **2.3 Configuration** ✅
  - Added Clerk settings to `app/config.py`
  - Removed unused TRADEFEEDS settings from config
  - Updated `.env.example` with complete env var structure

**Next session:**
- Continue Phase 2: task 2.4 (create `app/core/clerk_auth.py`)
- See [PHASE_2_BACKEND_AUTH.md](./PHASES_AUTH_BILLING/PHASE_2_BACKEND_AUTH.md) for remaining tasks

---

### 2026-01-05 - Phase 1 Complete
**What was done:**
- Created Clerk account and SigmaSight application
- Configured authentication methods:
  - Email/password with verification codes
  - Google OAuth enabled
  - Email subaddresses blocked
- Enabled Clerk Billing with Stripe connection
- Created subscription plans:
  - Free ($0): key = `free_user`
  - Pro ($18/mo): key = `pro_user`
  - 30-day free trial enabled for Pro
- Configured webhook endpoint (pointing to Railway backend)
- Collected all environment variables:
  - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
  - `CLERK_SECRET_KEY`
  - `CLERK_WEBHOOK_SECRET`
  - `CLERK_DOMAIN` = `included-chimp-71.clerk.accounts.dev`
- Updated `backend/.env.example` with Clerk variables template

**Next session:**
- Begin Phase 2: Backend Auth Migration
- See [PHASE_2_BACKEND_AUTH.md](./PHASES_AUTH_BILLING/PHASE_2_BACKEND_AUTH.md) for detailed checklist
- First task: Create Alembic migration for users table columns

---

### 2026-01-04 - Planning Complete
**What was done:**
- Finalized PRD v1.14 with simplification pass
- Removed unnecessary complexity (slowapi, atomic SQL, in-memory webhook tracking)
- Created phase breakdown with entry/exit criteria
- Set up progress tracking structure

**Next session:**
- Begin Phase 1: Create Clerk account and application
- See [PHASE_1_CLERK_SETUP.md](./PHASES_AUTH_BILLING/PHASE_1_CLERK_SETUP.md) for detailed checklist

---

## Key Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-05 | Plan keys: `free_user` → `free`, `pro_user` → `paid` | Clerk plan keys map to tier values in database |
| 2026-01-05 | 30-day Pro trial enabled | User acquisition incentive, no charge first month |
| 2026-01-05 | Block email subaddresses | Prevents `user+test@email.com` workarounds |
| 2026-01-04 | Use Clerk Billing, not direct Stripe | Simpler integration, Clerk handles webhook normalization |
| 2026-01-04 | Single invite code (2026-FOUNDERS-BETA) | Good enough for 100 users, easy to rotate |
| 2026-01-04 | Keep admin system separate | Admins aren't customers, different auth needs |
| 2026-01-04 | Simple AI counter (not atomic SQL) | Occasional 101st message acceptable for MVP |
| 2026-01-04 | Log-based invite abuse detection | No slowapi dependency, grep logs if needed |
| 2026-01-04 | IntegrityError for webhook idempotency | Database constraint simpler than tracking svix-ids |

---

## How to Use This File

1. **Starting a session**: Read "Current Status" and "Next session" from the latest session log
2. **During work**: Update the phase status table as you progress
3. **Ending a session**: Add a new session log entry with what was done and what's next
4. **Between phases**: Run `/clear` to reset context, then reference the next phase file
