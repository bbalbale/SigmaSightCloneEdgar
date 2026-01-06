# Phase 2: Backend Auth Migration

**Estimated Duration**: 3-4 days
**Dependencies**: Phase 1 complete (Clerk account configured)
**PRD Reference**: Sections 5, 7, 9, 10, 15

---

## Entry Criteria

Before starting this phase, ensure:
- [x] Phase 1 complete (all exit criteria passed)
- [x] `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`, `CLERK_DOMAIN`, `CLERK_AUDIENCE` in `.env`
- [x] Local PostgreSQL running (`docker-compose up -d`)
- [x] Backend dependencies installed (`uv sync`)

---

## Tasks

### 2.1 Database Schema Changes ✅ COMPLETE

**File**: `migrations_core/versions/s5t6u7v8w9x0_add_clerk_auth_columns.py`

Created Alembic migration to add columns to `users` table:

```sql
ALTER TABLE users ADD COLUMN clerk_user_id VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN tier VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN invite_validated BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN ai_messages_used INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN ai_messages_reset_at TIMESTAMP DEFAULT NOW();

CREATE INDEX ix_users_clerk_user_id ON users(clerk_user_id);
```

- [x] Create Alembic migration file
- [x] Run migration locally: `uv run alembic -c alembic.ini upgrade s5t6u7v8w9x0`
- [x] Verify columns exist (verified via SQLAlchemy inspector)

### 2.2 Install Dependencies ✅ COMPLETE

**File**: `pyproject.toml`

```toml
dependencies = [
    # ... existing deps
    "python-jose[cryptography]>=3.3.0",  # JWT verification
    "cachetools>=6.2.4",                  # TTL cache for JWKS
]
```

- [x] Add `python-jose[cryptography]` to dependencies
- [x] Add `cachetools` to dependencies
- [x] Run `uv add` to install

### 2.3 Configuration Updates ✅ COMPLETE

**File**: `app/config.py`

Added Clerk settings to Settings class:

```python
# Clerk Authentication & Billing (Phase 2)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: str = Field(default="", env="NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
CLERK_SECRET_KEY: str = Field(default="", env="CLERK_SECRET_KEY")
CLERK_WEBHOOK_SECRET: str = Field(default="", env="CLERK_WEBHOOK_SECRET")
CLERK_DOMAIN: str = Field(default="", env="CLERK_DOMAIN")
CLERK_AUDIENCE: str = Field(default="sigmasight.io", env="CLERK_AUDIENCE")
```

- [x] Add Clerk settings to `app/config.py`
- [x] Invite code already configured (`BETA_INVITE_CODE`)
- [x] Verify settings load from `.env`
- [x] Removed unused TRADEFEEDS settings

### 2.4 Clerk Auth Module ✅ COMPLETE

**File**: `app/core/clerk_auth.py`

Implement (copy from PRD Section 5.3):
- `get_jwks()` - Async JWKS fetch with TTL cache
- `get_current_user()` - JWT verification + JIT provisioning
- `jit_provision_user()` - Create user from JWT claims if webhook hasn't arrived

- [x] Create `app/core/clerk_auth.py`
- [x] Implement `get_jwks()` with async httpx + TTLCache
- [x] Implement `get_current_user()` with RS256 verification
- [x] Implement `jit_provision_user()` for race condition handling
- [x] Add `get_user_by_clerk_id()` helper function

### 2.5 Consolidated Guard Dependency ✅ COMPLETE

**File**: `app/core/dependencies.py`

Add validated user dependency (PRD Section 9.5):

```python
async def get_validated_user(user: User = Depends(get_current_user)) -> User:
    """Combined dependency: Clerk auth + invite validation."""
    if not user.invite_validated:
        raise HTTPException(403, detail={"error": "invite_required", ...})
    return user

CurrentUser = Annotated[User, Depends(get_validated_user)]
```

- [x] Add `get_validated_user` to dependencies
- [x] Add `ValidatedUser` type alias (named ValidatedUser, not CurrentUser to avoid conflict)
- [x] Keep `get_current_user` for settings page (no invite required)

### 2.6 Tier Limits Configuration ✅ COMPLETE

**File**: `app/config.py`

Add tier limits (PRD Section 9.1):

```python
TIER_LIMITS = {
    "free": {"max_portfolios": 2, "max_ai_messages": 100},
    "paid": {"max_portfolios": 10, "max_ai_messages": 1000},
}

def get_tier_limit(tier: str, feature: str) -> int:
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"]).get(feature)
```

- [x] Add `TIER_LIMITS` dict to config (lines 209-212)
- [x] Add `get_tier_limit()` helper function (lines 238-256)

### 2.7 AI Message Counter Service ✅ COMPLETE

**File**: `app/services/usage_service.py`

Implement simple counter (PRD Section 9.2.1):

```python
async def check_and_increment_ai_messages(db: AsyncSession, user: User) -> bool:
    """Check limit and increment. Returns False if limit reached."""
    # Reset if new month, check limit, increment
```

- [x] Create `app/services/usage_service.py` (121 lines)
- [x] Implement `check_and_increment_ai_messages()` - returns (allowed, remaining, limit) tuple
- [x] Added `get_ai_message_usage()` helper for status queries

### 2.8 Webhook Handler ✅ COMPLETE

**File**: `app/api/v1/webhooks/clerk.py`

Implement webhook endpoint (PRD Sections 10.3, 10.4):

- [x] Create `app/api/v1/webhooks/` directory
- [x] Create `clerk.py` with `verify_clerk_webhook()` function (317 lines total)
- [x] Implement `handle_clerk_webhook()` endpoint (POST /webhooks/clerk)
- [x] Implement `handle_user_created()` with IntegrityError idempotency
- [x] Implement `handle_user_deleted()` (soft delete via is_active=False)
- [x] Implement `handle_subscription_created()` (set tier='paid')
- [x] Implement `handle_subscription_cancelled()` (set tier='free')
- [x] Register router in `app/api/v1/router.py` (line 24, 86)

### 2.9 Invite Code Validation Endpoint ✅ COMPLETE

**File**: `app/api/v1/onboarding.py`

Add new endpoint (PRD Section 7.3):

```python
@router.post("/validate-invite")
async def validate_invite_code(...):
    """Validate invite code with logging."""
```

- [x] Add `validate_invite_code()` endpoint (lines 190-248)
- [x] Implement `validate_code()` helper (case-insensitive comparison, lines 176-187)
- [x] Add logging for failed attempts
- [x] Uses `get_current_user_clerk` dependency for Clerk JWT auth
- [x] Supports `INVITE_CODE_ENABLED` toggle for disabling enforcement

### 2.10 Update Existing Endpoints ✅ COMPLETE

**Portfolio Creation** (`app/api/v1/portfolios.py`):
- [x] Add tier limit check before creating portfolio (lines 72-97)
- [x] Auth switch complete (Code Review Fix #5):
  - Read operations (list, get, batch-status) → `get_current_user_clerk`
  - Write operations (create, update, delete, calculate) → `get_validated_user`

**CSV Import** (`app/api/v1/onboarding.py`):
- [x] Auth switch to `get_validated_user` (Code Review Fix #5)

**Chat Send** (`app/api/v1/chat/send.py`):
- [x] Call `check_and_increment_ai_messages()` before processing (lines 740-758)
- [x] Auth switch to `get_validated_user` (Code Review Fix #5)

### 2.11 Auth/Me Endpoint Update ✅ COMPLETE

**File**: `app/api/v1/auth.py`

Update response to include entitlements (PRD Section 15.1.1):

- [x] Create `UserMeResponse` schema with all fields:
  - id, email, full_name
  - tier, invite_validated
  - portfolio_id, portfolio_count
  - limits dict with max_portfolios, max_ai_messages, ai_messages_used, ai_messages_remaining
- [x] Update `/me` endpoint to return new schema with portfolio_count, limits, etc.

**Implementation**: `UserMeResponse` in `app/schemas/auth.py` (lines 67-118), `/me` endpoint updated (lines 218-300)

---

## Exit Criteria (Definition of Done)

### Database
- [ ] All new columns exist on `users` table
- [ ] Index exists on `clerk_user_id`

### Unit Tests
```bash
# Test JWKS fetch (mock)
uv run pytest tests/test_clerk_auth.py -v

# Test webhook signature verification
uv run pytest tests/test_webhooks.py -v
```
- [ ] JWKS fetch test passes
- [ ] Webhook signature verification test passes

### Integration Tests (Local)

**Test 1: Webhook creates user**
```bash
# Simulate user.created webhook (use Clerk Dashboard → Webhooks → Send test)
# Verify user appears in database with tier='free', invite_validated=false
```
- [ ] Webhook creates user in database

**Test 2: Auth rejects without valid JWT**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer invalid_token"
# Expected: 401 Unauthorized
```
- [ ] Invalid token returns 401

**Test 3: Invite validation works**
```bash
# Login via Clerk, get JWT, then:
curl -X POST http://localhost:8000/api/v1/onboarding/validate-invite \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"invite_code": "2026-FOUNDERS-BETA"}'
# Expected: {"status": "validated"}
```
- [ ] Valid invite code sets `invite_validated=true`
- [ ] Invalid invite code returns 400

**Test 4: Protected endpoints require invite**
```bash
# With user who has invite_validated=false:
curl -X POST http://localhost:8000/api/v1/portfolios \
  -H "Authorization: Bearer $JWT" \
  -d '...'
# Expected: 403 {"error": "invite_required"}
```
- [ ] Portfolio creation blocked without invite

---

## Rollback Plan

If issues arise:
1. Revert migration: `uv run alembic -c alembic.ini downgrade -1`
2. Remove new files: `clerk_auth.py`, `usage_service.py`, `webhooks/clerk.py`
3. Restore original `get_current_user` in dependencies

---

## Notes

- Keep original auth endpoints (`/api/v1/auth/login`, etc.) working during development
- Test with Clerk Development instance, not production
- Use `ngrok` to expose local webhook endpoint to Clerk

---

## Code Review Fixes (2026-01-05)

AI code review identified 5 critical issues after initial Phase 2 completion. All resolved:

### Fix #1: Invite Validation Persistence Bug
**File**: `app/api/v1/onboarding.py`
- **Issue**: `current_user` from `get_current_user_clerk` was detached from the db session
- **Root Cause**: SQLAlchemy objects are bound to the session that created them
- **Fix**: Re-query user with `select(User).where(User.id == current_user.id)` before updating

### Fix #2: Webhook Signature Verification Security
**File**: `app/api/v1/webhooks/clerk.py`
- **Issue**: Homegrown HMAC verification lacked timestamp tolerance
- **Security Risk**: Vulnerable to replay attacks
- **Fix**: Replaced with official `svix` library using `Webhook.verify()` which validates both signature AND timestamp freshness
- **Dependency Added**: `svix>=1.40.0` to pyproject.toml

### Fix #3: SSE Cookie Names
**Files**: `app/core/clerk_auth.py`, `app/core/dependencies.py`
- **Issue**: Code looked for `clerk_token` cookie but Clerk uses `__session`
- **Fix**: Changed cookie aliases to:
  - Primary: `__session` (Clerk's session JWT)
  - Fallback: `__client` (alternative token source)

### Fix #4: /auth/me Auth Switch
**File**: `app/api/v1/auth.py`
- **Issue**: `/me` endpoint still used legacy `get_current_user`
- **Fix**: Switched to `Depends(get_current_user_clerk)` for Clerk JWT verification

### Fix #5: Protected Routes Guard
**Files**: `portfolios.py`, `chat/send.py`, `onboarding.py`
- **Issue**: `get_validated_user` guard wasn't applied to protected routes
- **Fix**: Applied proper auth dependencies:
  - **Read operations**: `get_current_user_clerk` (auth only)
  - **Write operations**: `get_validated_user` (auth + invite validation)

### Fix #6: Remove `__client` Cookie Fallback
**Files**: `app/core/clerk_auth.py`, `app/core/dependencies.py`
- **Issue**: `__client` cookie is NOT a JWT - it's a metadata blob containing settings, not a token. Code was trying to decode it as RS256, causing "JWT token missing 'kid'" warnings.
- **Fix**: Removed `__client` cookie as a fallback. Now only uses `__session` cookie (the actual Clerk JWT) or Bearer token.

### Fix #7: Complete Auth Migration to Clerk
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
