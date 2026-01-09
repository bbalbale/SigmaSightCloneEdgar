# Code Review Request: ClerkAuth Branch

**Branch**: `ClerkAuth`
**Base**: `main`
**Reviewer**: AI Coding Agent
**Date**: 2026-01-06
**Author**: Claude Code

---

## 1. Executive Summary

This PR migrates SigmaSight's authentication system from a custom JWT implementation to **Clerk**, enabling:
- Managed authentication with Email/Password + Google OAuth
- Integrated billing via Clerk Billing (backed by Stripe)
- Two-tier subscription model (Free / Paid)
- AI message usage tracking and limits

**Scope**: 66 files changed, +7,689 lines, -452 lines

---

## 2. Commits to Review

| Commit | Description |
|--------|-------------|
| `518ea1e1` | docs: Add Clerk Auth & Billing PRD v1.14 with phase documentation |
| `c7033147` | feat: Clerk authentication migration (Phases 1-4) |
| `40bb94ef` | feat: Add Clerk auth columns migration (rebased on main) |

---

## 3. Architecture Changes

### 3.1 Authentication Flow (Before → After)

**Before (Custom JWT)**:
```
Login → Backend validates credentials → Backend issues JWT → Frontend stores in localStorage
```

**After (Clerk)**:
```
Login → Clerk handles auth → Clerk issues session token → Frontend gets token from Clerk
→ Backend validates via Clerk SDK or JWKS → Backend creates/updates local user record
```

### 3.2 New Database Schema

Migration `d5e6f7g8h9i0` adds to `users` table:
```sql
clerk_user_id     VARCHAR(255)  -- Unique, indexed
tier              VARCHAR(20)   -- 'free' | 'pro', default 'free'
invite_validated  BOOLEAN       -- default false
ai_messages_used  INTEGER       -- default 0
ai_messages_reset_at TIMESTAMP  -- default now()
```

### 3.3 Alembic Migration Chain

```
c4724714f341 (main's merge)
       ↓
d5e6f7g8h9i0 (Clerk auth columns) ← NEW
```

**Critical**: This migration was rebased from AuthOnboarding's `s5t6u7v8w9x0` which had an incorrect `down_revision`. Verify the chain is correct.

---

## 4. Files to Review (Priority Order)

### 4.1 🔴 Critical - Security & Auth (Review Thoroughly)

| File | Changes | Review Focus |
|------|---------|--------------|
| `backend/app/core/clerk_auth.py` | NEW | Clerk token validation, JWKS verification, user sync logic |
| `backend/app/core/dependencies.py` | Modified | `CurrentUserDep` implementation, auth dependency injection |
| `backend/app/api/v1/webhooks/clerk.py` | NEW | Webhook signature verification, event handling |
| `backend/app/api/v1/auth.py` | Modified | Login/logout flow changes, backward compatibility |
| `frontend/middleware.ts` | NEW | Route protection, Clerk middleware integration |
| `frontend/src/lib/clerkTokenStore.ts` | NEW | Token caching strategy, expiration handling |

**Security Review Checklist**:
- [ ] Webhook signature verification is cryptographically secure
- [ ] Token validation doesn't leak timing information
- [ ] No hardcoded secrets or API keys
- [ ] Proper error handling that doesn't expose internals
- [ ] CORS and CSP headers are appropriate
- [ ] Rate limiting considerations for auth endpoints

### 4.2 🟠 High Priority - Core Logic

| File | Changes | Review Focus |
|------|---------|--------------|
| `backend/app/models/users.py` | Modified | New columns, type annotations, defaults |
| `backend/app/services/usage_service.py` | NEW | AI message tracking, reset logic, tier limits |
| `backend/app/config.py` | Modified | New Clerk environment variables |
| `frontend/app/providers.tsx` | Modified | ClerkProvider integration, auth context |
| `frontend/src/hooks/useUserEntitlements.ts` | NEW | Tier-based feature gating logic |
| `frontend/src/services/apiClient.ts` | Modified | Token injection, error handling |

**Logic Review Checklist**:
- [ ] Usage tracking correctly resets monthly
- [ ] Tier limits are enforced server-side (not just client)
- [ ] Error states are handled gracefully
- [ ] No race conditions in usage increment

### 4.3 🟡 Medium Priority - API Endpoints

All 20+ API endpoint files were modified to use `CurrentUserDep`. Review for:
- [ ] Consistent auth dependency usage
- [ ] No endpoints accidentally left unprotected
- [ ] Proper error responses for unauthorized access

Key files:
- `backend/app/api/v1/portfolios.py`
- `backend/app/api/v1/chat/send.py`
- `backend/app/api/v1/analytics/*.py`

### 4.4 🟢 Lower Priority - UI Components

| File | Changes | Review Focus |
|------|---------|--------------|
| `frontend/src/components/billing/UpgradePrompt.tsx` | NEW | UX for upgrade flow |
| `frontend/src/components/settings/AccountBillingSettings.tsx` | NEW | Billing portal integration |
| `frontend/app/sign-in/[[...sign-in]]/page.tsx` | NEW | Clerk SignIn component styling |
| `frontend/app/sign-up/[[...sign-up]]/page.tsx` | NEW | Clerk SignUp component styling |

---

## 5. Specific Review Requests

### 5.1 Clerk Token Validation (`backend/app/core/clerk_auth.py`)

```python
# Review this validation logic:
async def validate_clerk_token(token: str) -> ClerkUser:
    # Is JWKS caching implemented correctly?
    # Is token expiration checked?
    # Are all required claims verified?
```

### 5.2 Webhook Security (`backend/app/api/v1/webhooks/clerk.py`)

```python
# Verify webhook signature validation:
def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    # Is this using constant-time comparison?
    # Is the signing secret properly secured?
```

### 5.3 Usage Service Reset Logic (`backend/app/services/usage_service.py`)

```python
# Review monthly reset logic:
async def check_and_reset_usage(user: User) -> None:
    # Does this handle timezone edge cases?
    # Is there a race condition if called concurrently?
```

### 5.4 Migration Script Safety (`backend/scripts/migrate_to_clerk.py`)

- [ ] Does dry-run mode accurately reflect what will happen?
- [ ] Is rollback possible if migration fails midway?
- [ ] Are existing users properly linked to Clerk accounts?

---

## 6. Testing Considerations

### 6.1 Manual Testing Required

1. **New User Registration Flow**
   - Sign up via email/password
   - Sign up via Google OAuth
   - Invite code validation (if required)

2. **Existing User Migration**
   - Run `migrate_to_clerk_dryrun.py` and verify output
   - Verify existing users can still log in after migration

3. **Tier Enforcement**
   - Free tier: Verify portfolio limit (1)
   - Free tier: Verify AI message limit (10/month)
   - Pro tier: Verify unlimited access

4. **Webhook Events**
   - `user.created` → User record created
   - `user.deleted` → User record handled
   - `checkout.session.completed` → Tier upgraded

### 6.2 Edge Cases to Test

- [ ] Token expiration during active session
- [ ] Concurrent requests with same user
- [ ] Webhook replay attacks (idempotency)
- [ ] Network failures during Clerk API calls
- [ ] Clock skew between servers

---

## 7. Environment Variables Required

```bash
# Backend (.env)
CLERK_SECRET_KEY=sk_live_xxx          # Clerk secret key
CLERK_PUBLISHABLE_KEY=pk_live_xxx     # Clerk publishable key
CLERK_WEBHOOK_SECRET=whsec_xxx        # Webhook signing secret
CLERK_JWKS_URL=https://xxx.clerk.accounts.dev/.well-known/jwks.json

# Frontend (.env.local)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_xxx
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/portfolio
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/portfolio
```

---

## 8. Known Limitations & Future Work

### Deferred (Per PRD v1.14)
- MFA/2FA support
- Multiple paid tiers
- Annual billing
- Trial periods
- Portfolio sharing
- Admin impersonation UI

### Technical Debt Introduced
- Legacy JWT auth code remains for backward compatibility during migration
- Some endpoints may have redundant auth checks

---

## 9. Review Response Format

Please provide feedback in the following structure:

```markdown
## Code Review: ClerkAuth Branch

### 🔴 Critical Issues (Must Fix)
- [File:Line] Issue description

### 🟠 Significant Concerns (Should Fix)
- [File:Line] Issue description

### 🟡 Minor Issues (Nice to Fix)
- [File:Line] Issue description

### ✅ Looks Good
- List of well-implemented aspects

### 💡 Suggestions
- Optional improvements

### ❓ Questions
- Clarifications needed
```

---

## 10. Reference Documentation

- **PRD**: `PlanningDocs/PRD_AUTH_BILLING_CLERK.md` (v1.14)
- **Phase Docs**: `PlanningDocs/PHASES_AUTH_BILLING/`
- **Progress**: `PlanningDocs/PROGRESS_AUTH_BILLING.md`
- **Clerk Docs**: https://clerk.com/docs
- **Backend CLAUDE.md**: `backend/CLAUDE.md`
- **Frontend CLAUDE.md**: `frontend/CLAUDE.md`

---

## 11. Commands for Review

```bash
# View all changes
git diff main..ClerkAuth

# View specific file
git diff main..ClerkAuth -- backend/app/core/clerk_auth.py

# View new files only
git diff --name-status main..ClerkAuth | grep "^A"

# Run backend tests (if applicable)
cd backend && uv run pytest

# Run frontend type check
cd frontend && npm run type-check

# Verify migration chain
cd backend && uv run python -c "
from alembic.config import Config
from alembic.script import ScriptDirectory
config = Config('alembic.ini')
scripts = ScriptDirectory.from_config(config)
print('Heads:', list(scripts.get_heads()))
"
```

---

**End of Code Review Request**
