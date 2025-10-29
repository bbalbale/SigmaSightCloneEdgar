# Admin Authentication - Implementation Guide

**Purpose**: Complete specification for superuser authentication system (missing from main design doc)

**Context**: SigmaSight currently has no admin/superuser concept. This document explains how to build it from scratch.

---

## 1. Database Setup

### 1.1 Add Superuser Column

```sql
-- Migration: Add is_superuser column
ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE NOT NULL;
CREATE INDEX idx_users_is_superuser ON users(is_superuser);
```

### 1.2 Bootstrap First Superuser

**Problem**: Chicken-and-egg - need superuser to create superusers, but no superusers exist!

**Solution**: Manual SQL script for initial setup

**File**: `scripts/admin/create_first_superuser.py`

```python
"""
Create the first superuser account.

This is a one-time bootstrap script. After the first superuser exists,
they can use admin endpoints to manage other superusers.

Usage:
    uv run python scripts/admin/create_first_superuser.py --email elliott@sigmasight.io
"""
import asyncio
import argparse
from sqlalchemy import select, update
from app.database import get_async_session
from app.models.users import User

async def create_first_superuser(email: str):
    """Promote existing user to superuser or create new superuser."""
    async with get_async_session() as db:
        # Check if user exists
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user:
            # Promote existing user
            await db.execute(
                update(User)
                .where(User.id == user.id)
                .values(is_superuser=True)
            )
            await db.commit()
            print(f"✅ Promoted {email} to superuser")
            print(f"   User ID: {user.id}")
        else:
            print(f"❌ User {email} not found")
            print(f"   Please create account first via registration, then run this script")
            return

        # Verify
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one()
        print(f"   is_superuser: {user.is_superuser}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Email of user to make superuser")
    args = parser.parse_args()

    asyncio.run(create_first_superuser(args.email))
```

**Usage:**
```bash
# Step 1: Register normally at /api/v1/onboarding/register
# (or use existing demo account)

# Step 2: Promote to superuser
uv run python scripts/admin/create_first_superuser.py --email elliott@sigmasight.io

# Output:
# ✅ Promoted elliott@sigmasight.io to superuser
#    User ID: a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d
#    is_superuser: True
```

---

## 2. Authentication Flow

### 2.1 Login (Same Endpoint for Everyone)

**Key Design Decision**: Superusers use the **same login endpoint** as regular users.

```
POST /api/v1/auth/login
```

**Why**: Simpler, no separate admin portal needed.

**Request** (same for all users):
```json
{
  "email": "elliott@sigmasight.io",
  "password": "your_password"
}
```

**Response** (JWT token includes superuser status):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    "email": "elliott@sigmasight.io",
    "full_name": "Elliott Ng",
    "is_superuser": true  // ⭐ This is the key difference
  }
}
```

### 2.2 JWT Token Payload

**Regular User Token:**
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "is_superuser": false,
  "exp": 1698768000
}
```

**Superuser Token:**
```json
{
  "sub": "superuser-uuid",
  "email": "elliott@sigmasight.io",
  "is_superuser": true,  // ⭐ Key claim
  "exp": 1698768000
}
```

---

## 3. Token Generation (Update Existing Auth)

### 3.1 Modify `app/core/auth.py`

**Current Code** (probably looks like this):
```python
def create_access_token(user: User) -> str:
    """Create JWT access token."""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
```

**Updated Code** (add is_superuser claim):
```python
def create_access_token(user: User) -> str:
    """Create JWT access token with superuser claim."""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "is_superuser": user.is_superuser,  // ⭐ Add this
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
```

### 3.2 Modify Login Response

**File**: `app/api/v1/auth.py`

**Current Response** (probably):
```python
@router.post("/login")
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_async_session)):
    # ... validation ...
    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer"
    }
```

**Updated Response** (include user info):
```python
@router.post("/login")
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_async_session)):
    # ... validation ...
    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {  // ⭐ Add user info
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_superuser": user.is_superuser
        }
    }
```

---

## 4. Admin Endpoint Authorization

### 4.1 Create Superuser Dependency

**File**: `app/core/dependencies.py`

```python
"""
FastAPI dependencies for authentication and authorization.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.config import settings
from app.database import get_async_session
from app.models.users import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_session)
) -> User:
    """
    Get current user from JWT token.

    Used by all authenticated endpoints.
    """
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = UUID(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify current user is a superuser.

    Used by admin endpoints only.

    Raises:
        HTTPException: 403 if user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized. This endpoint requires superuser access."
        )

    return current_user
```

### 4.2 Use in Admin Endpoints

**File**: `app/api/v1/admin.py`

```python
"""
Admin endpoints - require superuser authentication.
"""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_superuser
from app.models.users import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_superuser)  // ⭐ Requires superuser
):
    """List all users (superuser only)."""
    # current_user is guaranteed to be a superuser
    # ... implementation ...


@router.post("/impersonate")
async def impersonate_user(
    target_user_id: str,
    current_user: User = Depends(get_current_superuser)  // ⭐ Requires superuser
):
    """Impersonate another user (superuser only)."""
    # ... implementation ...
```

---

## 5. Frontend Integration

### 5.1 Login Response Handling

```typescript
// frontend/src/services/auth.ts

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    is_superuser: boolean;  // ⭐ Check this flag
  };
}

async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  const data: LoginResponse = await response.json();

  // Store token
  localStorage.setItem('access_token', data.access_token);

  // Store user info (including superuser status)
  localStorage.setItem('user', JSON.stringify(data.user));

  return data;
}

// Check if current user is superuser
function isSuperuser(): boolean {
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  return user.is_superuser === true;
}
```

### 5.2 Conditional UI Rendering

```tsx
// frontend/src/components/Navigation.tsx

function Navigation() {
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  return (
    <nav>
      <Link to="/portfolio">Portfolio</Link>
      <Link to="/analytics">Analytics</Link>

      {/* Only show admin link if superuser */}
      {user.is_superuser && (
        <Link to="/admin">Admin</Link>
      )}
    </nav>
  );
}
```

### 5.3 Protected Admin Routes

```tsx
// frontend/src/App.tsx

function AdminRoute({ children }: { children: React.ReactNode }) {
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  if (!user.is_superuser) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

// In routes:
<Route path="/admin" element={
  <AdminRoute>
    <AdminDashboard />
  </AdminRoute>
} />
```

---

## 6. Testing the Admin System

### 6.1 Create Superuser

```bash
# 1. Start server
uv run python run.py

# 2. Register a user (or use existing demo account)
curl -X POST http://localhost:8000/api/v1/onboarding/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "elliott@sigmasight.io",
    "password": "SuperSecure123!",
    "full_name": "Elliott Ng",
    "invite_code": "SIGMA-BETA-2025"
  }'

# 3. Promote to superuser
uv run python scripts/admin/create_first_superuser.py --email elliott@sigmasight.io

# Output:
# ✅ Promoted elliott@sigmasight.io to superuser
```

### 6.2 Test Superuser Login

```bash
# Login as superuser
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "elliott@sigmasight.io",
    "password": "SuperSecure123!"
  }'

# Response includes is_superuser: true
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "email": "elliott@sigmasight.io",
    "full_name": "Elliott Ng",
    "is_superuser": true  // ⭐ Confirms superuser status
  }
}
```

### 6.3 Test Admin Endpoint Access

```bash
# Save token from login response
TOKEN="eyJ..."

# Test admin endpoint (should work for superuser)
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN"

# Should return list of users

# Test with regular user token (should fail)
curl -X GET http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $REGULAR_USER_TOKEN"

# Should return 403 Forbidden
{
  "detail": "Unauthorized. This endpoint requires superuser access."
}
```

---

## 7. Security Considerations

### 7.1 Superuser Creation

**Rule**: Only create superusers via:
1. Manual script (for first superuser)
2. Existing superuser promoting another user (future feature)

**Never**:
- Self-registration as superuser
- API endpoint to create superusers (too dangerous)
- Default superuser accounts

### 7.2 Audit Logging

**Log these events** (even though we simplified away structured audit logging):

```python
# In login endpoint
if user.is_superuser:
    logger.info(f"Superuser login: {user.email}")

# In admin endpoints
logger.info(f"Admin action: {current_user.email} accessed /admin/users")
logger.info(f"Impersonation started: {superuser.email} → {target_user.email}")
```

### 7.3 Token Expiration

**Recommendation**:
- Regular users: 30 days
- Superusers: **Same** (no difference for MVP)
- Impersonation tokens: 8 hours (shorter for security)

---

## 8. Implementation Checklist

**Database**:
- [ ] Add `is_superuser` column to `users` table
- [ ] Create index on `is_superuser`
- [ ] Run migration

**Scripts**:
- [ ] Create `scripts/admin/create_first_superuser.py`
- [ ] Test bootstrap process

**Backend**:
- [ ] Update `create_access_token()` to include `is_superuser` claim
- [ ] Update login endpoint to return user info
- [ ] Create `get_current_superuser()` dependency
- [ ] Add dependency to all admin endpoints

**Testing**:
- [ ] Create first superuser
- [ ] Login as superuser (verify token contains `is_superuser: true`)
- [ ] Access admin endpoint (verify it works)
- [ ] Login as regular user
- [ ] Try to access admin endpoint (verify 403 error)

**Frontend**:
- [ ] Store user info (including `is_superuser`) after login
- [ ] Show/hide admin navigation based on `is_superuser`
- [ ] Create protected admin routes
- [ ] Test with superuser account
- [ ] Test with regular user account

---

## 9. Future Enhancements (Post-MVP)

**Admin User Management Endpoint**:
```
POST /api/v1/admin/users/{user_id}/promote
POST /api/v1/admin/users/{user_id}/demote
```

Allow existing superusers to promote/demote other users (instead of manual script).

**Multi-Factor Authentication**:
Require MFA for superuser accounts only.

**Session Management**:
Track active superuser sessions, force logout, etc.

**Audit Trail**:
Structured audit logging for compliance.

---

## 10. Quick Reference

### First Time Setup
```bash
# 1. Apply migration
uv run alembic upgrade head

# 2. Register account
curl -X POST .../register (with invite code)

# 3. Promote to superuser
uv run python scripts/admin/create_first_superuser.py --email your@email.com

# 4. Login
curl -X POST .../login (get token with is_superuser: true)

# 5. Access admin endpoints
curl -X GET .../admin/users -H "Authorization: Bearer $TOKEN"
```

### File Changes Required

**New Files**:
- `scripts/admin/create_first_superuser.py` (bootstrap script)

**Modified Files**:
- `app/core/auth.py` (add `is_superuser` to token)
- `app/core/dependencies.py` (add `get_current_superuser`)
- `app/api/v1/auth.py` (return user info in login response)
- `app/api/v1/admin.py` (use `get_current_superuser` dependency)

**Database**:
- Migration: Add `users.is_superuser` column

---

**This supplement should be merged into Section 9.2 of the main design document.**
