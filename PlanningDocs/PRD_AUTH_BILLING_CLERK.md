# PRD: Authentication & Billing Migration to Clerk

**Version**: 1.14
**Date**: January 4, 2026
**Status**: Draft
**Target Scale**: 100 paying users (product validation)

---

## 1. Executive Summary

Migrate SigmaSight's authentication system from the current custom JWT implementation to Clerk, enabling:
- Managed authentication with Email/Password + Google OAuth
- Integrated billing via Clerk Billing (backed by Stripe)
- Two-tier subscription model (Free / Paid)
- Foundation for future growth without over-engineering

**Key Constraint**: Minimal scope, minimal risk, minimal maintenance. Every feature has a clear rationale tied to validating product-market fit with 100 paying users.

---

## 2. Goals

| Goal | Success Metric |
|------|----------------|
| Enable paid subscriptions | Accept payments, track subscribers |
| Reduce auth maintenance | Zero custom auth code to maintain |
| Enforce tier-based limits | Portfolio limits work correctly |
| Preserve existing data | Demo accounts continue working |

## 3. Non-Goals (Explicit Exclusions)

| Excluded | Rationale |
|----------|-----------|
| MFA/2FA | Adds complexity, not needed at 100-user scale |
| Multiple paid tiers | One tier sufficient for validation |
| Annual billing/discounts | Adds billing complexity |
| **Trial period** | Deferred - simplifies state management |
| **Portfolio sharing** | Deferred to Phase 2 |
| **Admin impersonation UI** | Deferred - query DB directly for now |
| Full organization management | Not needed at this scale |
| Admin migration to Clerk | Keep existing separate admin system |
| Social logins beyond Google | Email + Google covers 95%+ of users |
| Custom billing UI | Clerk's hosted billing portal is sufficient |
| Usage-based billing | Fixed pricing is simpler to implement |

---

## 4. User Tiers & Limits

### 4.1 Free Tier
- **Portfolios**: 2 maximum
- **AI Messages**: 100/month (est. cost: $0.08/user)
- **Enforcement**: Hard block when limit reached

### 4.2 Paid Tier ($18/month)
- **Portfolios**: 10 maximum
- **AI Messages**: 1,000/month (est. cost: $0.80/user)
- **Payment**: Credit/debit card only
- **Enforcement**: Hard block when limit reached

### 4.3 Tier Transitions
```
NEW USER → FREE (no credit card required)
FREE → PAID (credit card via Stripe checkout)
PAID → FREE (subscription cancelled/expired)
```

### 4.4 Free Tier Onboarding Requirements
1. **Email verification** - Required (Clerk enforces before account active)
2. **Invite code** - Required (entered post-signup to unlock features)
3. **Credit card** - NOT required for Free tier

**No friction** - users can try the product immediately after email verification + invite code. Credit card only required when upgrading to Paid.

### 4.5 Downgrade Behavior (Over-Limit Handling)

**Scenario**: User has 8 portfolios on Paid tier, then cancels subscription → Free tier (limit 2).

**Approach: Read-Only Freeze (Soft Limit)**

Existing portfolios are NOT deleted. Instead:

1. **All existing portfolios remain accessible** (read-only)
2. **Creation of new portfolios blocked** until under limit
3. **Frontend shows clear messaging**:
   ```
   "You have 8 portfolios but your Free plan allows 2.
   To create new portfolios, please delete 6 portfolios or upgrade to Pro."
   ```

**Backend Implementation:**

```python
# app/api/v1/portfolios.py

@router.post("/")
async def create_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_validated_user),
    db: AsyncSession = Depends(get_db)
):
    """Create portfolio - blocked if over limit."""
    current_count = await get_portfolio_count(db, current_user.id)
    max_portfolios = get_tier_limit(current_user.tier, "max_portfolios")

    if current_count >= max_portfolios:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "portfolio_limit_reached",
                "message": f"You have {current_count} portfolios but your {current_user.tier} plan allows {max_portfolios}.",
                "current": current_count,
                "limit": max_portfolios,
                "action_required": "Delete portfolios or upgrade to create new ones.",
            }
        )
    # ... create portfolio
```

**AI Messages**: Same approach - existing usage preserved, new messages blocked at limit.

**Why NOT delete portfolios?**
- Data loss creates support burden
- Users may re-upgrade soon
- Read-only access maintains trust
- Simple to implement, no data migration needed

---

## 5. Authentication Specification

### 5.1 Auth Methods
- **Email/Password**: Primary method
- **Google OAuth**: Secondary method
- **Email Verification**: Required at signup (blocking)
- **Password Reset**: Clerk's default flow

### 5.2 Session Management
- Use Clerk's default session handling
- Frontend: Clerk React SDK
- Backend: JWKS-based JWT verification

### 5.3 Backend Integration Pattern

**CRITICAL**: Use async HTTP client with TTL cache. Sync `httpx.get()` with `@lru_cache` blocks the FastAPI event loop and causes timeouts under load.

```python
# app/core/clerk_auth.py

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt
from jose.backends import RSAKey
import httpx
import asyncio
from cachetools import TTLCache
from datetime import datetime

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer()

# TTL cache for JWKS - expires after 1 hour (Clerk rotates keys periodically)
_jwks_cache = TTLCache(maxsize=1, ttl=3600)
_jwks_lock = asyncio.Lock()

async def get_jwks():
    """Fetch and cache JWKS from Clerk with TTL and async."""
    async with _jwks_lock:
        if "jwks" not in _jwks_cache:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"https://{settings.CLERK_DOMAIN}/.well-known/jwks.json"
                    )
                    response.raise_for_status()
                    _jwks_cache["jwks"] = response.json()
                    logger.info("JWKS cache refreshed")
            except httpx.TimeoutException:
                logger.error("JWKS fetch timeout - Clerk may be unreachable")
                raise HTTPException(503, "Authentication service unavailable")
            except Exception as e:
                logger.error(f"JWKS fetch failed: {e}")
                raise HTTPException(503, "Authentication service unavailable")
        return _jwks_cache["jwks"]

async def get_current_user(token: str = Depends(security)):
    """Verify Clerk JWT and return user info with JIT provisioning."""
    try:
        jwks = await get_jwks()  # ← Now async
        unverified_header = jwt.get_unverified_header(token.credentials)

        rsa_key = None
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = RSAKey(key, algorithm="RS256")
                break

        if not rsa_key:
            # Key not found - might need to refresh cache (key rotation)
            _jwks_cache.clear()
            raise HTTPException(status_code=401, detail="Invalid token - key not found")

        payload = jwt.decode(
            token.credentials,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.CLERK_AUDIENCE,
            issuer=f"https://{settings.CLERK_DOMAIN}",  # ← Validate issuer
            options={"require": ["exp", "iat", "sub"]}   # ← Require claims
        )

        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await get_user_by_clerk_id(clerk_user_id)

        # JIT (Just-In-Time) Provisioning: Handle race between auth and webhook
        # User may have valid Clerk JWT but user.created webhook hasn't arrived yet
        if not user:
            user = await jit_provision_user(clerk_user_id, payload)
            if not user:
                raise HTTPException(status_code=401, detail="User provisioning failed")

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTClaimsError as e:
        raise HTTPException(status_code=401, detail=f"Invalid claims: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Auth error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


async def jit_provision_user(clerk_user_id: str, jwt_payload: dict) -> User | None:
    """
    Just-In-Time user provisioning for race condition handling.

    Timeline problem:
      T+0ms: User signs up in Clerk
      T+50ms: User hits our API with valid Clerk JWT
      T+200ms: user.created webhook arrives ← TOO LATE

    Solution: Create user record from JWT claims if webhook hasn't arrived.
    """
    from app.database import get_async_session
    from app.models.users import User

    logger.info(f"JIT provisioning user: {clerk_user_id}")

    async with get_async_session() as db:
        # Double-check user doesn't exist (webhook may have just arrived)
        existing = await get_user_by_clerk_id(clerk_user_id)
        if existing:
            return existing

        # Extract email from JWT (Clerk includes this in claims)
        email = jwt_payload.get("email") or jwt_payload.get("primary_email")
        if not email:
            logger.error(f"JIT provision failed - no email in JWT for {clerk_user_id}")
            return None

        # Create minimal user record - webhook will fill in details later
        user = User(
            email=email,
            clerk_user_id=clerk_user_id,
            tier="free",
            invite_validated=False,  # Must still validate invite
            full_name=jwt_payload.get("name", ""),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"JIT provisioned user: {email} ({clerk_user_id})")
        return user
```

---

## 6. SSE/Chat Authentication

### 6.1 Current State
The AI chat uses SSE streaming with Bearer token authentication:
- Frontend stores JWT in localStorage via `authManager`
- `chatAuthService.ts` includes `Authorization: Bearer {token}` in SSE requests
- Backend validates token in `app/api/v1/chat/send.py`

### 6.2 Clerk Migration Approach

**CRITICAL**: React hooks (`useAuth()`) can only be called inside React components, not in utility functions. The pattern below will crash at runtime.

```typescript
// ❌ WRONG - Will crash: hooks can't be called outside components
export async function getAuthToken(): Promise<string | null> {
  const { getToken } = useAuth()  // ← CRASH
  return await getToken()
}
```

**Correct Pattern - Hook-based API Client:**

```typescript
// hooks/useApiClient.ts
import { useAuth } from '@clerk/nextjs'

export function useApiClient() {
  const { getToken } = useAuth()

  return {
    fetch: async (url: string, options?: RequestInit) => {
      const token = await getToken()
      return fetch(url, {
        ...options,
        headers: {
          ...options?.headers,
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    },

    // For SSE connections
    getAuthHeaders: async (): Promise<HeadersInit> => {
      const token = await getToken()
      return {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      }
    },
  }
}

// Usage in component
function ChatComponent() {
  const { getAuthHeaders } = useApiClient()

  const sendMessage = async (message: string) => {
    const headers = await getAuthHeaders()
    // Use headers for SSE connection...
  }
}
```

**Alternative - Server-side with `auth()`:**

```typescript
// For server components or API routes (not client components)
import { auth } from '@clerk/nextjs/server'

export async function getServerAuthHeaders() {
  const { getToken } = await auth()
  const token = await getToken()
  return { Authorization: `Bearer ${token}` }
}
```

### 6.3 SSE Token Expiration Handling

**Issue**: Clerk JWTs expire (default 60 seconds). Long AI chat responses could outlast the token.

**Solutions** (choose one):

1. **Extend token lifetime** (Recommended for MVP):
   - Clerk Dashboard → Sessions → Token lifetime → Set to 5-10 minutes
   - Simple, no code changes needed

2. **Validate once at connection start**:
   ```python
   # Backend: Validate token once when SSE connection opens
   # Don't re-validate per chunk - token was valid at connection time
   @router.post("/send")
   async def send_message(
       current_user: User = Depends(get_current_user),  # Validates here
       ...
   ):
       # Stream chunks without re-validating each one
       async for chunk in generate_response():
           yield chunk
   ```

3. **Token refresh mid-stream** (Complex, defer to Phase 2):
   - Requires bidirectional communication
   - Not worth the complexity for 100-user validation

### 6.4 Backend Compatibility
The backend SSE endpoint (`/api/v1/chat/send`) already uses `get_current_user` dependency:
```python
@router.post("/send")
async def send_message(
    request: MessageSend,
    current_user: User = Depends(get_current_user),  # ← This switches to Clerk auth
    db: AsyncSession = Depends(get_db)
):
```

**No changes needed to SSE endpoint** - swapping `get_current_user` handles it.

---

## 7. Onboarding Integration

### 7.1 Current Onboarding System
The app has an invite-code onboarding flow:
- `POST /api/v1/onboarding/register` - Registration with invite code
- `POST /api/v1/onboarding/create-portfolio` - CSV portfolio import
- `GET /api/v1/onboarding/csv-template` - Download template

### 7.2 Migration Decision: Keep Separate for Alpha

**Rationale**: Invite codes are still needed for controlled alpha access.

**Approach**:
1. Clerk handles authentication (email/password, Google)
2. After Clerk signup, user hits `/api/v1/onboarding/validate-invite` to unlock features
3. Invite code validation happens post-signup, not during signup

```python
# New endpoint: POST /api/v1/onboarding/validate-invite
@router.post("/validate-invite")
async def validate_invite_code(
    request: InviteCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """Validate invite code for existing Clerk user."""
    if current_user.invite_validated:
        return {"status": "already_validated"}

    if not await validate_code(request.invite_code):
        raise HTTPException(status_code=400, detail="Invalid invite code")

    await mark_user_invite_validated(current_user.id)
    return {"status": "validated"}
```

### 7.3 Invite Code Configuration

**Single shared invite code** - simplest for 100-user beta validation:

```python
# app/config.py
class Settings(BaseSettings):
    BETA_INVITE_CODE: str = "2026-FOUNDERS-BETA"
    INVITE_CODE_ENABLED: bool = True  # Kill switch - disable without redeploy

# In validate_invite endpoint
async def validate_code(code: str) -> bool:
    """Case-insensitive comparison with kill switch."""
    if not settings.INVITE_CODE_ENABLED:
        return True  # Bypass when disabled (emergency access)
    return code.upper().strip() == settings.BETA_INVITE_CODE.upper()
```

```bash
# .env
BETA_INVITE_CODE=2026-FOUNDERS-BETA
INVITE_CODE_ENABLED=true
```

**Why single code?**
- Easy to share (email, social, word-of-mouth)
- Easy to revoke (change env var, redeploy)
- Good enough for 100-user beta validation
- No database table needed for invite tracking

**To issue a new code**: Update `BETA_INVITE_CODE` in environment and redeploy. Existing validated users are unaffected (they already have `invite_validated = true`).

### 7.3.1 Abuse Detection (Logging-Based)

**Simple approach for MVP**: Log failed attempts, review manually if needed.

```python
# app/api/v1/onboarding.py

@router.post("/validate-invite")
async def validate_invite_code(
    request: Request,
    body: InviteCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate invite code with logging for abuse detection."""

    # Already validated - idempotent
    if current_user.invite_validated:
        return {"status": "already_validated"}

    # Validate code
    if not await validate_code(body.invite_code):
        # Log failed attempt - grep logs if abuse suspected
        logger.warning(
            f"EVENT: invite_failed | "
            f"user={current_user.email} | "
            f"ip={request.client.host}"
        )
        raise HTTPException(status_code=400, detail="Invalid invite code")

    # Success - mark validated
    current_user.invite_validated = True
    await db.commit()

    logger.info(f"EVENT: invite_validated | user={current_user.email}")
    return {"status": "validated"}
```

**If abuse detected** (grep logs for repeated failures):
- Change `BETA_INVITE_CODE` in environment and redeploy
- Or temporarily set `INVITE_CODE_ENABLED=false` to block all validations

**Why no rate limiting for MVP?**
- Adds slowapi dependency
- At 100 users, can spot abuse in logs manually
- Code rotation is the nuclear option if needed
- Can add rate limiting later if abuse becomes a pattern

### 7.4 CSV Import
Portfolio CSV import (`/api/v1/onboarding/create-portfolio`) continues to work unchanged - it already requires authentication.

---

## 8. Clerk Billing Setup

### 8.1 Understanding Clerk Billing

**IMPORTANT**: We're using **Clerk Billing**, NOT direct Stripe integration.

With Clerk Billing:
- Plans and pricing are managed **in the Clerk Dashboard**, not Stripe
- Clerk uses Stripe **only** for payment processing (credit card charges)
- Stripe products/prices are created automatically by Clerk - DO NOT create them manually
- All subscription management happens through Clerk's UI and APIs

### 8.2 Clerk Dashboard Setup

1. **Create Clerk account** at clerk.com
2. **Create application** for SigmaSight
3. **Enable Billing** in Clerk Dashboard → Billing
4. **Connect Stripe**:
   - Clerk Dashboard → Billing → Connect Stripe
   - Authorize Clerk to access your Stripe account
   - Stripe account can be existing or new

5. **Create Plans in Clerk Dashboard**:

| Plan | Price | Features (display only) |
|------|-------|------------------------|
| Free | $0/month | 2 portfolios, 100 AI messages |
| Pro | $18/month | 10 portfolios, 1,000 AI messages |

**Note**: Feature limits are enforced by our backend code (Section 9), not by Clerk. The features listed in Clerk Dashboard are for display purposes in the billing portal.

### 8.3 Environment Variables

```bash
# .env (backend) - Clerk only, NO Stripe keys needed
CLERK_SECRET_KEY=sk_test_...
CLERK_WEBHOOK_SECRET=whsec_...    # From Clerk Dashboard → Webhooks
CLERK_DOMAIN=clerk.your-app.com
CLERK_AUDIENCE=your-clerk-audience

# Stripe keys NOT needed - Clerk handles payment processing
# DO NOT add: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID
```

### 8.4 What Happens in Stripe

Clerk automatically creates in your connected Stripe account:
- **Customer** for each Clerk user who subscribes
- **Product** for each plan defined in Clerk
- **Subscription** when user upgrades

You do NOT need to:
- Create Stripe products/prices manually
- Use Stripe CLI to configure billing
- Handle raw Stripe webhooks (Clerk normalizes these)

**Stripe Dashboard is read-only** for Clerk Billing - view transactions there but don't configure products.

---

## 9. Entitlement Management

### 9.1 Simple Config-Based Entitlements

**No database table needed.** Use a simple Python dict in config:

```python
# app/config.py

TIER_LIMITS = {
    "free": {
        "max_portfolios": 2,
        "max_ai_messages": 100,  # per month
    },
    "paid": {
        "max_portfolios": 10,
        "max_ai_messages": 1000,  # per month
    },
}

def get_tier_limit(tier: str, feature: str) -> int | None:
    """Get limit for a feature. Returns None for unlimited."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"]).get(feature)
```

### 9.2 User Tier Storage

**Clerk is the source of truth for billing**. We only store:
- `clerk_user_id` - Maps Clerk user to our internal UUID
- `tier` - Synced from Clerk metadata via webhooks
- `invite_validated` - Tracks alpha invite code validation
- `ai_messages_used` - Counter for current month (reset monthly)
- `ai_messages_reset_at` - When counter was last reset

```sql
-- Add minimal columns to users table (no Stripe IDs - Clerk is source of truth)
ALTER TABLE users ADD COLUMN clerk_user_id VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN tier VARCHAR(20) DEFAULT 'free';
ALTER TABLE users ADD COLUMN invite_validated BOOLEAN DEFAULT false;
ALTER TABLE users ADD COLUMN ai_messages_used INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN ai_messages_reset_at TIMESTAMP DEFAULT NOW();

-- Indexes
CREATE INDEX idx_users_clerk_id ON users(clerk_user_id);
```

### 9.2.1 AI Message Counter Logic

**Storage**: Counter lives on `users` table (not a separate usage table). Simple for 100 users.

**Simple Pattern** (acceptable for 100-user validation):

```python
# app/services/usage_service.py

from datetime import datetime
from app.config import get_tier_limit

async def check_and_increment_ai_messages(db: AsyncSession, user: User) -> bool:
    """
    Check limit and increment counter.
    Returns True if allowed, False if limit reached.

    Note: At 100 users, occasional race condition (user gets 101 messages)
    is acceptable. Simplicity > perfect enforcement for MVP.
    """
    limit = get_tier_limit(user.tier, "max_ai_messages")
    now = datetime.utcnow()

    # Check if we need to reset (new month)
    if (user.ai_messages_reset_at.month != now.month or
        user.ai_messages_reset_at.year != now.year):
        user.ai_messages_used = 0
        user.ai_messages_reset_at = now

    # Check limit
    if user.ai_messages_used >= limit:
        return False

    # Increment
    user.ai_messages_used += 1
    await db.commit()
    return True
```

**Usage in Chat Endpoint:**

```python
# app/api/v1/chat/send.py

from app.services.usage_service import check_and_increment_ai_messages

@router.post("/conversations/{conversation_id}/send")
async def send_message(
    conversation_id: UUID,
    request: MessageSend,
    current_user: User = Depends(get_validated_user),
    db: AsyncSession = Depends(get_db)
):
    # Check and increment counter BEFORE processing
    if not await check_and_increment_ai_messages(db, current_user):
        limit = get_tier_limit(current_user.tier, "max_ai_messages")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "ai_message_limit_reached",
                "message": f"You've reached your limit of {limit} AI messages this month.",
                "limit": limit,
            }
        )

    # Process message...
```

**Why simple increment?**
- Easy to understand and maintain
- At 100 users, race conditions are rare
- Occasional 101st message is harmless for validation phase
- Can add atomic SQL later if needed at scale

### 9.3 Invite Enforcement

**CRITICAL**: Users must have `invite_validated = true` before they can access the app.

**Allowed WITHOUT invite validation** (minimal access):
- `/settings` page (to enter invite code and manage billing)
- `/settings/billing` (to upgrade if desired)

**Blocked WITHOUT invite validation** (everything else):
- Dashboard (`/`)
- Portfolio pages (`/portfolio/*`)
- Chat (`/chat`)
- Any other authenticated pages

### 9.3.1 Frontend Route Guard (Simple Middleware)

```typescript
// middleware.ts - Add invite check after Clerk auth

import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)', '/landing(.*)'])
const isSettingsRoute = createRouteMatcher(['/settings(.*)', '/invite(.*)'])

export default clerkMiddleware(async (auth, req) => {
  if (isPublicRoute(req)) return

  // Require auth for all non-public routes
  const { userId } = auth()
  if (!userId) {
    return auth().protect()
  }

  // Allow settings page without invite (so they can enter code)
  if (isSettingsRoute(req)) return

  // For all other pages, check invite status
  // Fetch from /api/v1/auth/me (cached in session)
  const user = await fetchCurrentUser(userId)

  if (!user.invite_validated) {
    // Redirect to settings page to enter invite code
    return Response.redirect(new URL('/settings?invite_required=true', req.url))
  }
})
```

### 9.3.2 Backend API Guards

Even with frontend guards, backend must also enforce (defense in depth):

| Endpoint | Guard |
|----------|-------|
| `POST /api/v1/portfolios` | `require_invite_validated` |
| `POST /api/v1/onboarding/create-portfolio` | `require_invite_validated` |
| `POST /api/v1/chat/conversations/{id}/send` | `require_invite_validated` |
| `GET /api/v1/data/portfolio/*` | `require_invite_validated` |
| `GET /api/v1/analytics/*` | `require_invite_validated` |

```python
# app/core/guards.py

from fastapi import HTTPException

def require_invite_validated(user: User):
    """Guard function - call before any protected endpoint."""
    if not user.invite_validated:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "invite_required",
                "message": "Please enter your invite code to unlock this feature.",
                "redirect": "/settings"
            }
        )
```

### 9.4 Tier Enforcement in API Endpoints
```python
# app/api/v1/portfolios.py

from app.config import get_tier_limit
from app.core.guards import require_invite_validated

@router.post("/")
async def create_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new portfolio with invite + tier limit checks."""
    # STEP 1: Require validated invite
    require_invite_validated(current_user)

    # STEP 2: Check tier limit
    result = await db.execute(
        select(func.count(Portfolio.id)).where(Portfolio.user_id == current_user.id)
    )
    current_count = result.scalar()

    max_portfolios = get_tier_limit(current_user.tier, "max_portfolios")
    if max_portfolios and current_count >= max_portfolios:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "portfolio_limit_reached",
                "message": f"You've reached your limit of {max_portfolios} portfolios.",
                "current": current_count,
                "limit": max_portfolios,
            }
        )

    # Create portfolio...
```

**Also enforce on CSV import**:
```python
# app/api/v1/onboarding.py

@router.post("/create-portfolio")
async def create_portfolio_from_csv(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create portfolio from CSV - requires invite validation."""
    require_invite_validated(current_user)  # ← Guard here too
    # ... rest of CSV import logic
```

### 9.5 Consolidated Guard Dependency (DRY Pattern)

Instead of calling `require_invite_validated(current_user)` in every endpoint, use a FastAPI dependency that handles all checks:

```python
# app/core/dependencies.py

from fastapi import Depends, HTTPException
from app.core.clerk_auth import get_current_user as get_clerk_user
from app.models.users import User

async def get_validated_user(user: User = Depends(get_clerk_user)) -> User:
    """
    Combined dependency: Clerk auth + invite validation.
    Use this for all protected endpoints that require invite code.
    """
    if not user.invite_validated:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "invite_required",
                "message": "Please enter your invite code to unlock this feature.",
                "redirect": "/settings"
            }
        )
    return user


# Usage type alias for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_validated_user)]
```

**Endpoint Usage (Clean Pattern):**

```python
# app/api/v1/portfolios.py

from app.core.dependencies import CurrentUser  # Import type alias

@router.post("/")
async def create_portfolio(
    data: PortfolioCreate,
    current_user: CurrentUser,  # ← Invite check built-in!
    db: AsyncSession = Depends(get_db)
):
    """Create portfolio - invite validation automatic via dependency."""
    # No need to call require_invite_validated() - already validated

    # Only need to check tier limits
    current_count = await get_portfolio_count(db, current_user.id)
    max_portfolios = get_tier_limit(current_user.tier, "max_portfolios")
    # ... rest of logic
```

**Three Dependency Levels:**

| Dependency | Use Case | Checks |
|------------|----------|--------|
| `get_current_user` | Settings page, invite code entry | Clerk JWT only |
| `get_validated_user` | All feature endpoints | Clerk JWT + invite |
| Custom tier check | Creation endpoints | + tier limits |

### 9.6 Frontend Entitlement Display

**No separate entitlements endpoint** - data comes from `/api/v1/auth/me`:

```typescript
// hooks/useEntitlements.ts

export function useEntitlements() {
  // Entitlements returned as part of /api/v1/auth/me response
  const { data } = useSWR<{
    id: string;
    email: string;
    tier: 'free' | 'paid';
    invite_validated: boolean;
    portfolio_count: number;
    portfolio_limit: number;
    ai_messages_used: number;
    ai_messages_limit: number;
  }>('/api/v1/auth/me');

  const canCreatePortfolio = data
    ? data.portfolio_count < data.portfolio_limit && data.invite_validated
    : false;

  const canSendAiMessage = data
    ? data.ai_messages_used < data.ai_messages_limit
    : false;

  return {
    tier: data?.tier ?? 'free',
    inviteValidated: data?.invite_validated ?? false,
    canCreatePortfolio,
    canSendAiMessage,
    portfolioUsage: data ? `${data.portfolio_count}/${data.portfolio_limit}` : '',
    aiMessageUsage: data ? `${data.ai_messages_used}/${data.ai_messages_limit}` : '',
    shouldShowUpgrade: data?.tier === 'free',
  };
}
```

---

## 10. Billing Flow & Webhooks

### 10.1 Checkout Flow (Free → Paid)
```
User clicks "Upgrade" on /settings
    ↓
Frontend opens Clerk Billing Portal (direct link, no backend endpoint)
    ↓
User enters payment info (Stripe Checkout)
    ↓
Stripe creates subscription
    ↓
Clerk receives Stripe webhook
    ↓
Clerk sends webhook to our backend
    ↓
Backend updates user.tier = 'paid'
```

**Frontend billing link** (no backend endpoint needed):
```typescript
// Direct link to Clerk billing portal
const billingUrl = `https://accounts.${CLERK_DOMAIN}/user/billing`

// In settings page
<a href={billingUrl} target="_blank">Manage Subscription</a>
```

### 10.2 Webhook Events to Handle (Clerk Billing)

**Note**: With Clerk Billing, all webhooks come from Clerk (not raw Stripe webhooks).

| Event | Source | Our Action |
|-------|--------|------------|
| `user.created` | Clerk Auth | Create internal user record with `tier='free'` |
| `user.deleted` | Clerk Auth | Soft-delete user, preserve data |
| `subscription.created` | Clerk Billing | Set `tier='paid'` |
| `subscription.cancelled` | Clerk Billing | Set `tier='free'` (at period end) |

**Clerk Billing subscription events** (different from raw Stripe events):
- `subscription.created` - User subscribed to a paid plan
- `subscription.cancelled` - User cancelled (still active until period end)
- `subscription.plan_changed` - User changed plans (future use)

### 10.3 Webhook Handler

```python
# app/api/v1/webhooks/clerk.py

from fastapi import APIRouter, Request, HTTPException
from app.config import settings
from app.core.logging import get_logger
from app.database import get_async_session
from datetime import datetime
import json
import hmac
import hashlib
import base64

logger = get_logger(__name__)
router = APIRouter()

MAX_WEBHOOK_AGE_SECONDS = 300  # 5 minutes - reject stale webhooks


def verify_clerk_webhook(payload: bytes, headers: dict) -> dict:
    """Verify Clerk webhook signature using svix headers."""
    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")

    if not all([svix_id, svix_timestamp, svix_signature]):
        raise ValueError("Missing svix headers")

    # Check timestamp freshness
    try:
        webhook_time = int(svix_timestamp)
        now = int(datetime.utcnow().timestamp())
        if abs(now - webhook_time) > MAX_WEBHOOK_AGE_SECONDS:
            raise ValueError(f"Webhook too old: {abs(now - webhook_time)}s")
    except (ValueError, TypeError):
        raise ValueError("Invalid svix-timestamp")

    # Verify signature
    signed_payload = f"{svix_id}.{svix_timestamp}.{payload.decode()}"
    secret = settings.CLERK_WEBHOOK_SECRET
    if secret.startswith("whsec_"):
        secret = secret[6:]

    secret_bytes = base64.b64decode(secret)
    expected_sig = hmac.new(secret_bytes, signed_payload.encode(), hashlib.sha256).digest()
    expected_sig_b64 = base64.b64encode(expected_sig).decode()

    signatures = svix_signature.split(" ")
    for sig in signatures:
        if "," in sig:
            _, sig_value = sig.split(",", 1)
            if hmac.compare_digest(sig_value, expected_sig_b64):
                return json.loads(payload)

    raise ValueError("Invalid webhook signature")


@router.post("/clerk")
async def handle_clerk_webhook(request: Request):
    """Handle incoming Clerk webhooks."""
    payload = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Verify signature
    try:
        event = verify_clerk_webhook(payload, headers)
    except ValueError as e:
        logger.warning(f"Webhook rejected: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    event_type = event.get("type")
    data = event.get("data", {})

    logger.info(f"Processing webhook: {event_type}")

    # Route to handler (each handler is idempotent)
    if event_type == "user.created":
        await handle_user_created(data)
    elif event_type == "user.deleted":
        await handle_user_deleted(data)
    elif event_type == "subscription.created":
        await handle_subscription_created(data)
    elif event_type == "subscription.cancelled":
        await handle_subscription_cancelled(data)
    else:
        logger.info(f"Unhandled webhook type: {event_type}")

    return {"status": "ok"}
```

### 10.4 Event Handlers (Idempotent via Database Constraints)

**Simple idempotency**: Use database constraints and conditional updates. No in-memory tracking needed.

```python
# app/api/v1/webhooks/clerk.py

from sqlalchemy.exc import IntegrityError

async def handle_user_created(data):
    """
    Handle user.created - idempotent via unique constraint on clerk_user_id.
    """
    clerk_user_id = data.get("id")
    email = data.get("email_addresses", [{}])[0].get("email_address")

    async with get_async_session() as db:
        try:
            user = User(
                email=email,
                clerk_user_id=clerk_user_id,
                tier="free",
                invite_validated=False,
                full_name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            )
            db.add(user)
            await db.commit()
            logger.info(f"EVENT: user_signup | email={email}")
        except IntegrityError:
            # User already exists (JIT provision or previous webhook) - that's fine
            await db.rollback()
            logger.info(f"EVENT: user_signup_idempotent | email={email}")


async def handle_user_deleted(data):
    """Handle user.deleted - soft delete, preserve data."""
    clerk_user_id = data.get("id")

    async with get_async_session() as db:
        user = await get_user_by_clerk_id(clerk_user_id)
        if not user:
            return  # Already deleted or never existed

        user.is_active = False
        user.deleted_at = datetime.utcnow()
        await db.commit()
        logger.info(f"EVENT: user_deleted | email={user.email}")


async def handle_subscription_created(data):
    """Handle subscription.created - idempotent (only updates if not already paid)."""
    clerk_user_id = data.get("user_id")

    async with get_async_session() as db:
        user = await get_user_by_clerk_id(clerk_user_id)
        if not user or user.tier == "paid":
            return  # Already paid or user not found

        user.tier = "paid"
        await db.commit()
        logger.info(f"EVENT: upgrade | email={user.email}")


async def handle_subscription_cancelled(data):
    """Handle subscription.cancelled - idempotent (only updates if currently paid)."""
    clerk_user_id = data.get("user_id")

    async with get_async_session() as db:
        user = await get_user_by_clerk_id(clerk_user_id)
        if not user or user.tier == "free":
            return  # Already free or user not found

        user.tier = "free"
        await db.commit()
        logger.info(f"EVENT: downgrade | email={user.email}")
```

**Why no in-memory webhook tracking?**
- Database unique constraint on `clerk_user_id` already prevents duplicates
- `IntegrityError` catch is simpler than tracking svix-ids
- No memory growth concerns
- Works across multiple server instances

### 10.5 Instrumentation & Alerts

**Log limit hits**:
```python
# In create_portfolio endpoint
if max_portfolios and current_count >= max_portfolios:
    logger.info(f"EVENT: portfolio_limit_hit | user={current_user.email} | tier={current_user.tier}")
    raise HTTPException(...)

# In chat send endpoint
if current_user.ai_messages_used >= get_tier_limit(current_user.tier, "max_ai_messages"):
    logger.info(f"EVENT: ai_message_limit_hit | user={current_user.email} | tier={current_user.tier}")
    raise HTTPException(403, "ai_message_limit_reached")
```

**Slack Alerts (Optional but Recommended)**:
Set up a simple Slack webhook for critical events:
```python
# app/core/alerts.py
import httpx

SLACK_WEBHOOK_URL = settings.SLACK_WEBHOOK_URL  # Optional env var

async def send_alert(message: str):
    """Send alert to Slack (if configured)."""
    if not SLACK_WEBHOOK_URL:
        return
    try:
        await httpx.post(SLACK_WEBHOOK_URL, json={"text": f"🚨 {message}"})
    except Exception:
        pass  # Don't fail if Slack is down
```

**Alert Triggers**:
- Webhook signature verification failures
- Subscription webhook processing errors
- Invite code validation failures (potential abuse)

### 10.5 Recovery Playbook for Clerk/Stripe Sync

**Problem**: If Clerk is down or webhook backlog appears, user tier state may drift.

**Operational Checklist**:

| Cadence | Task | Owner |
|---------|------|-------|
| Weekly | Review Clerk Dashboard → Webhooks for failed deliveries | Dev lead |
| Weekly | Spot-check: Compare 5 random paid users in DB vs Clerk Dashboard | Dev lead |
| As needed | Manual tier fix via DB if customer complains | Dev lead |

**If Clerk Dashboard Shows Failed Webhooks**:
1. Click "Retry" in Clerk Dashboard for failed events
2. If retry fails, manually update user tier in database:
   ```sql
   UPDATE users SET tier = 'paid' WHERE email = 'customer@example.com';
   ```
3. Notify customer their access has been restored

**If Customer Reports Wrong Tier**:
1. Check Clerk Dashboard → Users → Find user → Billing tab
2. Verify subscription status in Clerk
3. If Clerk shows active subscription but DB shows `tier='free'`:
   ```sql
   UPDATE users SET tier = 'paid' WHERE clerk_user_id = 'user_xxx';
   ```
4. Log incident for pattern analysis

**If Clerk is Completely Down**:
- Users can still access app if they have valid JWT (sessions persist)
- New signups/logins will fail - communicate via status page
- No action needed on billing - Stripe still processes payments
- Webhooks will queue and process when Clerk recovers

---

## 11. Local Development & Testing

### 11.1 Clerk Test Environment
1. Create Clerk "Development" instance (separate from production)
2. Use Clerk test API keys (`sk_test_...`, `pk_test_...`)
3. Test users created in dev instance don't affect production
4. Enable Billing in development instance with Stripe test mode

### 11.2 Stripe Test Mode (via Clerk Billing)

When testing billing through Clerk:
1. Clerk automatically uses Stripe test mode when your Clerk instance is in development
2. Test card numbers (entered in Clerk's checkout):
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`
3. **No Stripe CLI needed** - Clerk handles webhook routing

### 11.3 Local Webhook Testing
```bash
# Terminal 1: Start backend
cd backend && uv run python run.py

# Terminal 2: Expose local server for Clerk webhooks
ngrok http 8000

# Then configure in Clerk Dashboard:
# 1. Go to Webhooks
# 2. Add endpoint: https://your-ngrok-url.ngrok.io/api/v1/webhooks/clerk
# 3. Select events: user.created, user.deleted, subscription.created, subscription.cancelled
# 4. Copy the signing secret to CLERK_WEBHOOK_SECRET
```

**No Stripe CLI needed** - Clerk Billing sends all subscription events through Clerk webhooks.

### 11.4 Test Environment Variables
```bash
# .env.test - Clerk only
CLERK_SECRET_KEY=sk_test_...
CLERK_DOMAIN=your-dev-instance.clerk.accounts.dev
CLERK_AUDIENCE=your-dev-audience
CLERK_WEBHOOK_SECRET=whsec_...  # From Clerk Dashboard → Webhooks

# NO Stripe keys needed for Clerk Billing
```

---

## 12. User Migration Strategy

### 12.1 Migration Checklist

**Pre-Migration (Day -1)**:
- [ ] Note the current commit hash (rollback point): `git rev-parse HEAD`
- [ ] Backup database
- [ ] Run database migration to add new columns (`clerk_user_id`, `tier`, etc.)

**Migration Day (Day 0)**:
- [ ] Run `scripts/migrate_to_clerk.py` to create demo accounts in Clerk
- [ ] Deploy backend with Clerk auth (replaces old auth entirely)
- [ ] Deploy frontend with Clerk components
- [ ] Verify demo accounts can login via Clerk
- [ ] Test that demo accounts see their existing portfolios
- [ ] Test end-to-end auth flow

**Post-Migration (Day +1)**:
- [ ] Monitor for auth errors
- [ ] If critical issues: execute rollback (see Section 17)
- [ ] Communicate login change to beta tester (if any beyond demo accounts)

### 12.2 Demo Account Migration
```python
# scripts/migrate_to_clerk.py

async def migrate_demo_accounts():
    """Create demo accounts in Clerk and map to existing users."""
    demo_accounts = [
        {"email": "demo_individual@sigmasight.com", "password": "demo12345", "name": "Individual Investor"},
        {"email": "demo_hnw@sigmasight.com", "password": "demo12345", "name": "HNW Investor"},
        {"email": "demo_hedgefundstyle@sigmasight.com", "password": "demo12345", "name": "Hedge Fund Style"},
    ]

    for account in demo_accounts:
        try:
            clerk_user = clerk.users.create(
                email_address=[account["email"]],
                password=account["password"],
                first_name=account["name"],
                skip_password_checks=True
            )
            print(f"Created Clerk user: {account['email']} -> {clerk_user.id}")

            # Directly update database (webhook may not fire for API-created users)
            await update_user_by_email(
                email=account["email"],
                clerk_user_id=clerk_user.id
            )

        except Exception as e:
            print(f"Error creating {account['email']}: {e}")
```

### 12.3 Handling Existing External Alpha Testers

If there are alpha testers beyond demo accounts (real users with real portfolios):

**Pre-Migration Communication** (send 1 week before):
```
Subject: SigmaSight Login Change - Action Required

We're upgrading our login system on [DATE]. You'll need to:
1. Create a new account at sigmasight.com (same email recommended)
2. Enter your invite code: [CODE]
3. Re-import your portfolio CSV

Your old data will not carry over automatically. If you need help
migrating, reply to this email and we'll assist personally.
```

**Migration Options**:
| Option | Effort | When to use |
|--------|--------|-------------|
| **A: User re-registers** | Low | Default - user re-imports CSV |
| **B: Manual migration** | Medium | VIP early adopters - we create Clerk account + link existing data |
| **C: Script migration** | High | Only if >10 external testers (not expected) |

**For Option B (manual VIP migration)**:

```bash
# Step 1: Get test user's email from our database
psql $DATABASE_URL -c "SELECT id, email, full_name FROM users WHERE email NOT LIKE '%@sigmasight.com';"
# Example output: test_user@gmail.com
```

```python
# Step 2: Create Clerk user via API (run in Python shell or script)
# scripts/migrate_vip_user.py

import clerk
from clerk.client import Clerk

clerk_client = Clerk(api_key="sk_live_...")

# Create user in Clerk with their existing email
# They'll need to set a new password via "Forgot Password" flow
vip_user = clerk_client.users.create(
    email_address=["test_user@gmail.com"],
    first_name="Test",
    last_name="User",
    skip_password_requirement=True,  # They'll reset via email
)

print(f"Created Clerk user: {vip_user.id}")
# Output: user_2abc123...
```

```sql
-- Step 3: Link Clerk user to existing data in our database
UPDATE users
SET clerk_user_id = 'user_2abc123...',
    tier = 'free',
    invite_validated = true  -- They're already validated
WHERE email = 'test_user@gmail.com';

-- Verify the link
SELECT id, email, clerk_user_id, tier, invite_validated
FROM users
WHERE email = 'test_user@gmail.com';
```

```
# Step 4: Send email to test user

Subject: SigmaSight Login Update - Your Data is Preserved

Hi [Name],

We've upgraded our login system. Your portfolios and data are fully preserved.

To access your account:
1. Go to sigmasight.com
2. Click "Forgot Password"
3. Enter your email: test_user@gmail.com
4. Set a new password via the email link
5. Log in - you'll see all your existing portfolios

If you have any issues, reply to this email and we'll help immediately.

Thanks for being an early supporter!
```

At 100-user validation scale with mostly demo accounts, Option A is the default. Reserve Option B for your earliest evangelists who provided valuable feedback.

---

## 13. Admin System

### 13.1 Approach: Keep Existing Separate Admin System
The current admin system remains unchanged:
- Separate `admin_users` table
- Separate JWT tokens with `type: "admin"` claim
- Admin dashboard at `/admin/*`
- No migration to Clerk (admins are not customers)

### 13.2 Frontend Middleware Coexistence

**CRITICAL**: The Clerk middleware must exclude admin routes, otherwise admin authentication will break.

```typescript
// middleware.ts

import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isAdminRoute = createRouteMatcher(['/admin(.*)'])
const isPublicRoute = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)', '/landing(.*)'])
const isSettingsRoute = createRouteMatcher(['/settings(.*)', '/invite(.*)'])

export default clerkMiddleware(async (auth, req) => {
  // ✅ Admin routes bypass Clerk entirely - admin layout handles its own auth
  if (isAdminRoute(req)) {
    return  // Let adminAuthService handle authentication
  }

  // Public routes don't require auth
  if (isPublicRoute(req)) return

  // Require Clerk auth for all other routes
  const { userId } = auth()
  if (!userId) {
    return auth().protect()
  }

  // Allow settings page without invite (so they can enter code)
  if (isSettingsRoute(req)) return

  // For all other pages, check invite status
  const user = await fetchCurrentUser(userId)
  if (!user.invite_validated) {
    return Response.redirect(new URL('/settings?invite_required=true', req.url))
  }
})
```

### 13.3 Backend Auth System Separation

Two completely independent JWT systems coexist:

| System | JWT Claim | Signing | Algorithm | Validation | Dependency |
|--------|-----------|---------|-----------|------------|------------|
| **Admin** | `type: "admin"` | `SECRET_KEY` | HS256 | `verify_admin_token()` | `get_current_admin` |
| **User (Clerk)** | `sub: clerk_user_id` | Clerk JWKS | RS256 | JWKS fetch | `get_current_user` |

**These systems are completely independent:**
- Different signing keys (our SECRET_KEY vs Clerk's private key)
- Different token structures
- Different validation logic
- No shared state

```python
# app/core/dependencies.py - AFTER MIGRATION

# Admin auth (UNCHANGED - uses internal JWT with SECRET_KEY)
from app.core.admin_dependencies import get_current_admin

# User auth (NEW - uses Clerk JWT validated via JWKS)
from app.core.clerk_auth import get_current_user
```

**Route Protection Examples:**
```python
# Admin routes - unchanged, uses admin JWT
@router.get("/admin/batch/status")
async def get_batch_status(admin: CurrentAdmin = Depends(get_current_admin)):
    ...

# User routes - now uses Clerk JWT
@router.get("/api/v1/portfolios")
async def get_portfolios(user: User = Depends(get_current_user)):
    ...
```

### 13.4 Frontend Token Storage

Admin and Clerk use different localStorage keys - no conflict:

| System | localStorage Key | Cookie |
|--------|------------------|--------|
| Admin | `admin_auth_token` | `admin_auth_cookie` |
| Clerk | `__clerk_*` | `__clerk_db_jwt` |

**Note**: If someone logs in as both admin and user in different tabs, the auth states are independent and won't conflict.

### 13.5 Admin Dashboard Queries

After migration, admins can query user data with these columns:

```sql
-- User list with Clerk billing status
SELECT
    id,
    email,
    clerk_user_id,
    tier,
    invite_validated,
    ai_messages_used,
    ai_messages_reset_at,
    created_at,
    (SELECT COUNT(*) FROM portfolios WHERE user_id = u.id) as portfolio_count
FROM users u
ORDER BY created_at DESC;

-- Recent signups (last 7 days)
SELECT email, created_at, invite_validated, tier
FROM users
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;

-- Users approaching AI message limits
SELECT email, tier, ai_messages_used,
    CASE tier
        WHEN 'free' THEN 100
        WHEN 'paid' THEN 1000
    END as ai_messages_limit
FROM users
WHERE ai_messages_used >= CASE tier WHEN 'free' THEN 90 ELSE 900 END
ORDER BY ai_messages_used DESC;

-- Paid subscribers
SELECT email, clerk_user_id, created_at
FROM users
WHERE tier = 'paid'
ORDER BY created_at DESC;
```

**No admin UI changes required** for initial launch - direct SQL queries are sufficient at 100-user scale.

### 13.6 Deferred: Admin Impersonation Architecture

When implemented (Phase 2), admin impersonation will:

1. **NOT** generate fake Clerk tokens (security risk)
2. Instead: Admin makes API calls with header `X-Impersonate-User: {clerk_user_id}`
3. Backend recognizes admin token + impersonate header
4. All impersonated actions logged for audit

```python
# Future implementation sketch
async def get_effective_user(
    admin: CurrentAdmin = Depends(get_current_admin),
    impersonate_id: str = Header(None, alias="X-Impersonate-User")
):
    if impersonate_id:
        logger.info(f"IMPERSONATE: admin={admin.email} as user={impersonate_id}")
        return await get_user_by_clerk_id(impersonate_id)
    raise HTTPException(400, "Admin endpoints require impersonation header")
```

This avoids breaking Clerk's security model while allowing admin debugging.

---

## 14. Frontend Changes

### 14.1 New Dependencies
```json
{
  "@clerk/nextjs": "^5.x",
  "@clerk/themes": "^2.x"
}
```

### 14.2 Auth Integration
```typescript
// app/layout.tsx
import { ClerkProvider } from '@clerk/nextjs'

export default function RootLayout({ children }) {
  return (
    <ClerkProvider>
      <html>
        <body>{children}</body>
      </html>
    </ClerkProvider>
  )
}

// middleware.ts
import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

const isPublicRoute = createRouteMatcher(['/sign-in(.*)', '/sign-up(.*)', '/landing(.*)'])

export default clerkMiddleware((auth, req) => {
  if (!isPublicRoute(req)) {
    auth().protect()
  }
})
```

### 14.3 Pages to Update
| Page | Change |
|------|--------|
| `/login` | Replace with Clerk's `<SignIn />` |
| `/signup` | Replace with Clerk's `<SignUp />` |
| `/settings` | Add billing link (direct to Clerk portal) |
| `/portfolios` | Show upgrade prompt when at limit |

### 14.4 API Client Update

**CRITICAL**: See Section 6.2 for the correct pattern. React hooks cannot be called in utility functions.

```typescript
// hooks/useApiClient.ts - Correct pattern (hook-based)
import { useAuth } from '@clerk/nextjs'

export function useApiClient() {
  const { getToken } = useAuth()

  const authFetch = async (url: string, options?: RequestInit) => {
    const token = await getToken()
    return fetch(url, {
      ...options,
      headers: {
        ...options?.headers,
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
  }

  return { authFetch, getToken }
}

// Usage in components
function MyComponent() {
  const { authFetch } = useApiClient()

  const loadData = async () => {
    const response = await authFetch('/api/v1/portfolios')
    return response.json()
  }
}
```

**For existing service layer**: Refactor to accept token as parameter:

```typescript
// services/portfolioService.ts
export async function getPortfolios(token: string) {
  return fetch('/api/v1/portfolios', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

// Component passes token from hook
function PortfolioPage() {
  const { getToken } = useAuth()

  useEffect(() => {
    const load = async () => {
      const token = await getToken()
      const data = await getPortfolios(token)
    }
    load()
  }, [])
}
```

---

## 15. API Changes Summary

### 15.1 Modified Endpoints
| Endpoint | Change |
|----------|--------|
| All authenticated endpoints | Use Clerk JWT via `get_current_user` |
| `GET /api/v1/auth/me` | Add `tier`, `invite_validated`, `portfolio_count`, `portfolio_limit` to response |
| `POST /api/v1/portfolios` | Add invite check + tier limit check |
| `POST /api/v1/onboarding/create-portfolio` | Add invite check (CSV import) |

### 15.1.1 `/api/v1/auth/me` Response Schema

**Full Response Model:**

```python
# app/schemas/auth.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserMeResponse(BaseModel):
    """Complete response for GET /api/v1/auth/me"""

    # Identity
    id: str                           # Internal UUID
    email: str
    full_name: Optional[str]
    clerk_user_id: str                # Clerk's user ID

    # Account Status
    is_active: bool
    invite_validated: bool            # Has entered valid invite code
    created_at: datetime

    # Subscription
    tier: str                         # "free" or "paid"

    # Portfolio Limits
    portfolio_count: int              # Current number of portfolios
    portfolio_limit: int              # Max allowed for tier

    # AI Message Limits
    ai_messages_used: int             # Messages used this month
    ai_messages_limit: int            # Max allowed for tier
    ai_messages_reset_at: datetime    # When counter resets

    class Config:
        from_attributes = True


# Example response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "email": "user@example.com",
#   "full_name": "John Doe",
#   "clerk_user_id": "user_2abc123...",
#   "is_active": true,
#   "invite_validated": true,
#   "created_at": "2026-01-01T00:00:00Z",
#   "tier": "free",
#   "portfolio_count": 1,
#   "portfolio_limit": 2,
#   "ai_messages_used": 45,
#   "ai_messages_limit": 100,
#   "ai_messages_reset_at": "2026-01-01T00:00:00Z"
# }
```

**Backend Implementation:**

```python
# app/api/v1/auth.py

@router.get("/me", response_model=UserMeResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),  # Note: NOT get_validated_user
    db: AsyncSession = Depends(get_db)
):
    """Get current user info with entitlements."""
    # Count portfolios
    result = await db.execute(
        select(func.count(Portfolio.id)).where(Portfolio.user_id == current_user.id)
    )
    portfolio_count = result.scalar()

    return UserMeResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        clerk_user_id=current_user.clerk_user_id,
        is_active=current_user.is_active,
        invite_validated=current_user.invite_validated,
        created_at=current_user.created_at,
        tier=current_user.tier,
        portfolio_count=portfolio_count,
        portfolio_limit=get_tier_limit(current_user.tier, "max_portfolios"),
        ai_messages_used=current_user.ai_messages_used,
        ai_messages_limit=get_tier_limit(current_user.tier, "max_ai_messages"),
        ai_messages_reset_at=current_user.ai_messages_reset_at,
    )
```

### 15.2 New Endpoints
| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/webhooks/clerk` | Handle Clerk/Stripe webhooks |
| `POST /api/v1/onboarding/validate-invite` | Validate invite code post-signup |

**Removed**: `GET /api/v1/users/me/entitlements` - data merged into `/api/v1/auth/me`

### 15.3 Deprecated Endpoints
| Endpoint | Replacement |
|----------|-------------|
| `POST /api/v1/auth/login` | Clerk `<SignIn />` |
| `POST /api/v1/auth/logout` | Clerk handles |
| `POST /api/v1/auth/register` | Clerk `<SignUp />` |
| `POST /api/v1/onboarding/register` | Clerk `<SignUp />` + `/validate-invite` |

### 15.4 Removed Endpoints (from original PRD)
| Endpoint | Reason |
|----------|--------|
| `GET /api/v1/billing/portal-url` | Not needed - link directly to Clerk portal |

---

## 16. Implementation Phases

**Total Estimated Time**: 8-12 days

**Detailed Checklists**: See `PHASES_AUTH_BILLING/` directory for comprehensive task lists with entry/exit criteria.

| Phase | Duration | Detailed Checklist |
|-------|----------|-------------------|
| **Phase 1: Clerk Setup** | 1-2 days | [PHASE_1_CLERK_SETUP.md](./PHASES_AUTH_BILLING/PHASE_1_CLERK_SETUP.md) |
| **Phase 2: Backend Auth** | 3-4 days | [PHASE_2_BACKEND_AUTH.md](./PHASES_AUTH_BILLING/PHASE_2_BACKEND_AUTH.md) |
| **Phase 3: Frontend Auth** | 2-3 days | [PHASE_3_FRONTEND_AUTH.md](./PHASES_AUTH_BILLING/PHASE_3_FRONTEND_AUTH.md) |
| **Phase 4: Testing & Migration** | 2 days | [PHASE_4_TESTING_MIGRATION.md](./PHASES_AUTH_BILLING/PHASE_4_TESTING_MIGRATION.md) |

**Progress Tracking**: See [PROGRESS_AUTH_BILLING.md](./PROGRESS_AUTH_BILLING.md) for current status and session logs.

### Phase Summary

**Phase 1: Clerk Setup**
- Create Clerk account and application
- Enable Billing, create Free/Pro plans
- Connect Stripe, configure webhook endpoint
- Collect environment variables

**Phase 2: Backend Auth**
- Add database columns via Alembic migration
- Implement JWKS-based JWT verification
- Create webhook handler with idempotency
- Add invite validation and tier limit enforcement
- Update `/api/v1/auth/me` with entitlements

**Phase 3: Frontend Auth**
- Install Clerk Next.js SDK
- Replace login/signup with Clerk components
- Update middleware for route protection
- Create `useApiClient` hook for authenticated requests
- Add invite code form and billing link to settings

**Phase 4: Testing & Migration**
- Run migration dry-run script
- Migrate demo accounts to Clerk
- Deploy backend and frontend
- Verify all auth flows work
- Monitor first 24 hours for issues

---

## 17. Rollback Plan

**Simple git revert** - no feature flags, no dual code paths:

```bash
# If Clerk auth has critical issues:

# 1. Revert to pre-Clerk commit (noted in Day -1)
git revert --no-commit HEAD~N..HEAD  # or specific commit range
git commit -m "Rollback: Revert Clerk auth migration"
git push

# 2. Railway/Vercel auto-deploys (~3-5 minutes)

# 3. Users can login with old auth immediately
```

**Rollback Time**: ~5 minutes (deploy time)

**Data Safety**:
- `clerk_user_id` column remains but is ignored by old auth
- All portfolio data uses internal UUIDs (unaffected)
- Database columns are additive, no data loss

**Why No Feature Flag**:
- Only 1 test user currently - minimal blast radius
- Simpler codebase without dual auth paths
- Faster to debug single implementation
- Git history preserves old auth code if needed

---

## 18. Success Criteria

| Metric | Target |
|--------|--------|
| Demo accounts work | 3/3 login and see existing data |
| New user signup | Complete in <60 seconds |
| Invite validation | Blocks portfolio/CSV until validated |
| First payment | $18 processed successfully |
| Portfolio limit (Free) | Hard block at 2 |
| Portfolio limit (Paid) | Hard block at 10 |
| AI message limit (Free) | Hard block at 100/month |
| AI message limit (Paid) | Hard block at 1,000/month |
| Upgrade flow | Immediate access to higher limits |
| SSE chat | Works with Clerk token |
| Logging | All key events (signup, upgrade, limit hits) appear in logs |

---

## 19. Deferred to Phase 2

| Feature | Rationale |
|---------|-----------|
| Portfolio Sharing | Standalone, not needed for billing validation |
| Trial Period | Adds state complexity |
| Admin Impersonation UI | Query DB directly |
| Automated Billing Sync | Manual recovery playbook sufficient at this scale (see Section 10.5) |

---

## 20. Appendix: Cost Analysis

### Auth Costs (Clerk)
- Free: 10,000 MAU
- At 100 users: $0/month

### Billing Costs
| Component | Fee |
|-----------|-----|
| Stripe processing | ~2.9% + $0.30 |
| Clerk Billing | 0.7% |
| **Per $18 transaction** | ~$0.95 (5.3%) |

### AI Message Costs (GPT-4o-mini)
| Tier | Messages/month | Cost/user |
|------|----------------|-----------|
| Free | 100 | $0.08 |
| Paid | 1,000 | $0.80 |

### Total Monthly Costs (100 users, 50% paid)
| Item | Cost |
|------|------|
| Clerk Auth | $0 |
| AI (50 free × $0.08) | $4 |
| AI (50 paid × $0.80) | $40 |
| Railway DB | ~$20 |
| **Total** | ~$64/month |

### Monthly Revenue (50 paid)
- 50 × $18 = $900
- After fees: ~$852
- **Net**: ~$788/month

---

## 21. Quick Wins & Operational Improvements

### 21.1 Health Check Endpoint

Add a health check that verifies Clerk connectivity:

```python
# app/api/v1/health.py

from fastapi import APIRouter
from app.core.clerk_auth import get_jwks
from app.database import get_async_session

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check with Clerk connectivity test."""
    checks = {
        "database": False,
        "clerk": False,
    }

    # Database check
    try:
        async with get_async_session() as db:
            await db.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)

    # Clerk JWKS check (uses cached value if available)
    try:
        await get_jwks()
        checks["clerk"] = True
    except Exception as e:
        checks["clerk_error"] = str(e)

    status = "healthy" if all([checks["database"], checks["clerk"]]) else "degraded"

    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### 21.2 Retry-After Headers (Optional)

**Pattern for future use** if rate limiting is added later:

```python
# For rate limits (short wait)
raise HTTPException(
    status_code=429,
    detail="Too many requests",
    headers={"Retry-After": "60"}  # 60 seconds
)

# For monthly limits (long wait)
raise HTTPException(
    status_code=429,
    detail="Monthly limit reached",
    headers={"Retry-After": "2592000"}  # 30 days
)
```

**Note**: Currently not used - we rely on simple 403/429 responses without Retry-After headers for MVP simplicity.

### 21.3 Webhook Delivery Monitoring

**Clerk Dashboard Alert Setup:**

1. Go to Clerk Dashboard → Webhooks → Your endpoint
2. Enable "Failed delivery notifications"
3. Set email alert for: 3+ failures in 1 hour

**Manual Check (Weekly):**

```sql
-- Check for users with tier/subscription mismatches
-- Run this weekly to catch any webhook failures

SELECT
    u.email,
    u.tier as db_tier,
    u.clerk_user_id,
    u.created_at
FROM users u
WHERE u.clerk_user_id IS NOT NULL
ORDER BY u.created_at DESC
LIMIT 20;

-- Then cross-reference with Clerk Dashboard → Users → Billing tab
```

### 21.4 Migration Dry-Run Script

Before running actual migration, test with dry-run:

```python
# scripts/migrate_to_clerk_dryrun.py

"""
Dry-run migration script - validates without making changes.

Usage:
    python scripts/migrate_to_clerk_dryrun.py

Checks:
1. All demo accounts exist in our database
2. Clerk API is reachable
3. No duplicate clerk_user_ids would be created
4. All required columns exist
"""

import asyncio
from app.database import get_async_session
from app.models.users import User
from sqlalchemy import select

DEMO_ACCOUNTS = [
    "demo_individual@sigmasight.com",
    "demo_hnw@sigmasight.com",
    "demo_hedgefundstyle@sigmasight.com",
]


async def main():
    print("=" * 60)
    print("MIGRATION DRY-RUN")
    print("=" * 60)

    errors = []

    # Check 1: Demo accounts exist
    print("\n1. Checking demo accounts in database...")
    async with get_async_session() as db:
        for email in DEMO_ACCOUNTS:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user:
                print(f"   ✅ {email} (id={user.id})")
            else:
                print(f"   ❌ {email} NOT FOUND")
                errors.append(f"Missing user: {email}")

    # Check 2: Required columns exist
    print("\n2. Checking required columns...")
    required_columns = ["clerk_user_id", "tier", "invite_validated", "ai_messages_used"]
    async with get_async_session() as db:
        for col in required_columns:
            try:
                await db.execute(text(f"SELECT {col} FROM users LIMIT 1"))
                print(f"   ✅ users.{col}")
            except Exception as e:
                print(f"   ❌ users.{col} - {e}")
                errors.append(f"Missing column: {col}")

    # Check 3: Clerk API reachable
    print("\n3. Checking Clerk API...")
    try:
        import httpx
        from app.config import settings
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://{settings.CLERK_DOMAIN}/.well-known/jwks.json"
            )
            if response.status_code == 200:
                print(f"   ✅ Clerk JWKS endpoint reachable")
            else:
                print(f"   ❌ Clerk returned {response.status_code}")
                errors.append("Clerk API not reachable")
    except Exception as e:
        print(f"   ❌ Clerk connection failed: {e}")
        errors.append(f"Clerk connection failed: {e}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ DRY-RUN FAILED - {len(errors)} errors:")
        for error in errors:
            print(f"   - {error}")
        print("\nFix these issues before running actual migration.")
    else:
        print("✅ DRY-RUN PASSED - Ready for migration")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

---

*PRD v1.14 - Simplification pass for 100-user MVP:*

**Simplified (removed complexity):**
- *Section 9.2.1: Simple AI counter increment (removed atomic SQL - occasional 101st message is acceptable)*
- *Section 7.3.1: Logging-based abuse detection (removed slowapi dependency - grep logs if abuse suspected)*
- *Section 10.3-10.4: Database-constraint idempotency (removed in-memory svix-id tracking - IntegrityError is simpler)*

**Kept from v1.13:**
- *Section 5.3: Async JWKS fetch + TTL cache (essential - blocking fetch causes timeouts)*
- *Section 5.3: JIT user provisioning (essential - prevents 401s for new users)*
- *Section 6.2, 14.4: React hooks pattern (essential - wrong pattern crashes at runtime)*
- *Section 9.5: Consolidated guards (reduces complexity)*
- *Section 4.5: Downgrade behavior (just policy documentation)*
- *Section 15.1.1: Auth/me response schema (helpful documentation)*
- *Section 21: Quick wins (health check, dry-run script)*

**Philosophy**: Ship billing and gating for 100 users. Add complexity later only if problems emerge.
