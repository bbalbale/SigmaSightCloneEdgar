# Detailed Merge Conflicts Analysis

**Created:** 2025-11-01
**Purpose:** Deep dive into each merge conflict with exact code comparisons and resolution instructions

---

## Overview

When you run `git merge origin/FrontendLocal-Onboarding`, Git will identify **5 files with conflicts**. This document explains each conflict in detail, shows you exactly what you'll see, and provides step-by-step resolution instructions.

---

## Conflict 1: backend/app/models/users.py 🔴 CRITICAL

### Severity: HIGH - This is the core schema conflict

### What Git Will Show You

When you open the file during conflict resolution, you'll see something like this:

```python
"""
User and Portfolio models
"""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
<<<<<<< HEAD (UIRefactor - Your current branch)
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index, Numeric, Boolean
=======
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index, Numeric
>>>>>>> origin/FrontendLocal-Onboarding
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.database import Base
```

### The User Class Conflict

```python
class User(Base):
    """User model - stores user account information"""
    __tablename__ = "users"

    # ... user fields (these are the same in both branches) ...

    # Relationships
<<<<<<< HEAD (UIRefactor)
    portfolios: Mapped[List["Portfolio"]] = relationship("Portfolio", back_populates="user", uselist=True)
=======
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="user", uselist=False)
>>>>>>> origin/FrontendLocal-Onboarding
    # Enhanced tag model (v2) - replaced the old tags relationship
    tags_v2: Mapped[List["TagV2"]] = relationship("TagV2", back_populates="user", foreign_keys="TagV2.user_id")
    modeling_sessions: Mapped[List["ModelingSessionSnapshot"]] = relationship("ModelingSessionSnapshot", back_populates="user")
```

**What This Means:**
- **UIRefactor (HEAD):** User has MANY portfolios (`portfolios` - plural, list)
- **Onboarding (incoming):** User has ONE portfolio (`portfolio` - singular)

### The Portfolio Class Conflict

```python
class Portfolio(Base):
<<<<<<< HEAD (UIRefactor)
    """Portfolio model - users can have multiple portfolios (accounts)"""
=======
    """Portfolio model - each user has exactly one portfolio"""
>>>>>>> origin/FrontendLocal-Onboarding
    __tablename__ = "portfolios"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
<<<<<<< HEAD (UIRefactor)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default='taxable')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
=======
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
>>>>>>> origin/FrontendLocal-Onboarding
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    # ... rest of fields are same ...

    # Relationships
<<<<<<< HEAD (UIRefactor)
    user: Mapped["User"] = relationship("User", back_populates="portfolios")
=======
    user: Mapped["User"] = relationship("User", back_populates="portfolio")
>>>>>>> origin/FrontendLocal-Onboarding
    positions: Mapped[List["Position"]] = relationship("Position", back_populates="portfolio")
    # ... rest of relationships are same ...

    __table_args__ = (
<<<<<<< HEAD (UIRefactor)
        Index('ix_portfolios_deleted_at', 'deleted_at'),
        Index('ix_portfolios_user_id', 'user_id'),  # Non-unique index for performance
=======
        UniqueConstraint('user_id', name='uq_portfolios_user_id'),
        Index('ix_portfolios_deleted_at', 'deleted_at'),
>>>>>>> origin/FrontendLocal-Onboarding
    )
```

### Key Differences Summary

| Aspect | UIRefactor (KEEP) | Onboarding (REJECT) |
|--------|-------------------|---------------------|
| Import | Includes `Boolean` | No `Boolean` |
| User relationship | `portfolios` (List) | `portfolio` (singular) |
| Portfolio comment | "multiple portfolios" | "exactly one portfolio" |
| user_id column | No `unique=True` | Has `unique=True` ❌ |
| account_name field | ✅ EXISTS | ❌ MISSING |
| account_type field | ✅ EXISTS | ❌ MISSING |
| is_active field | ✅ EXISTS | ❌ MISSING |
| Portfolio → User | `back_populates="portfolios"` | `back_populates="portfolio"` |
| Table constraints | Non-unique index | UniqueConstraint ❌ |

### Why This Conflict Exists

The onboarding branch was created **before** your multi-portfolio work. At that time, the system enforced one-to-one relationship. Your recent multi-portfolio migration (November 1) changed this to one-to-many.

### Resolution Strategy: KEEP UIRefactor, REJECT Onboarding

**Command:**
```bash
git checkout --ours backend/app/models/users.py
git add backend/app/models/users.py
```

**Explanation:**
- `git checkout --ours` = Keep UIRefactor version (multi-portfolio schema)
- This completely discards the onboarding version
- WHY: The multi-portfolio schema is your target architecture
- The onboarding code will be ADAPTED to work with this schema in Phase 2

### What You Get After Resolution

The final file will have:
```python
# Import includes Boolean
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index, Numeric, Boolean

class User(Base):
    # One-to-many relationship
    portfolios: Mapped[List["Portfolio"]] = relationship("Portfolio", back_populates="user", uselist=True)

class Portfolio(Base):
    """Portfolio model - users can have multiple portfolios (accounts)"""

    # NO unique constraint on user_id
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # NEW fields from multi-portfolio
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default='taxable')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')

    # Relationships back to User (plural)
    user: Mapped["User"] = relationship("User", back_populates="portfolios")

    __table_args__ = (
        Index('ix_portfolios_deleted_at', 'deleted_at'),
        Index('ix_portfolios_user_id', 'user_id'),  # Non-unique index
    )
```

### Impact on Onboarding Code

After resolving this conflict, you'll need to update these files in Phase 2:
- `app/services/onboarding_service.py` - Change `user.portfolio` to `user.portfolios[0]`
- `app/api/v1/onboarding.py` - Add `account_name`, `account_type` to responses
- All test files - Update assertions

---

## Conflict 2: backend/app/api/v1/router.py 🟡 MEDIUM

### Severity: MEDIUM - Simple router registration conflict

### What Git Will Show You

```python
"""
Main API v1 router that combines all endpoint routers
Updated for v1.4.4 namespace organization
"""
from fastapi import APIRouter

<<<<<<< HEAD (UIRefactor)
from app.api.v1 import auth, data, portfolios
=======
from app.api.v1 import auth, data
>>>>>>> origin/FrontendLocal-Onboarding
from app.api.v1.chat import router as chat_router
from app.api.v1.analytics.router import router as analytics_router
from app.api.v1.target_prices import router as target_prices_router
from app.api.v1.tags import router as tags_router
from app.api.v1.position_tags import router as position_tags_router
from app.api.v1.insights import router as insights_router
<<<<<<< HEAD (UIRefactor)
from app.api.v1.endpoints import admin_batch
from app.api.v1.endpoints.fundamentals import router as fundamentals_router
=======
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.endpoints import admin_batch
>>>>>>> origin/FrontendLocal-Onboarding

# Create the main v1 router
api_router = APIRouter(prefix="/v1")

# Include all endpoint routers
# Authentication (foundation)
api_router.include_router(auth.router)

<<<<<<< HEAD (UIRefactor)
# Portfolio Management APIs (/portfolios/) - multi-portfolio CRUD
api_router.include_router(portfolios.router)
=======
# Onboarding APIs (/onboarding/) - user registration and portfolio creation
api_router.include_router(onboarding_router)
>>>>>>> origin/FrontendLocal-Onboarding

# Chat API for Agent
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])

# ... rest is same in both branches ...
```

### Key Differences Summary

| Aspect | UIRefactor | Onboarding |
|--------|------------|------------|
| Import | Has `portfolios` | No `portfolios` |
| Import | Has `fundamentals_router` | No fundamentals |
| Import | No onboarding | Has `onboarding_router` ✅ |
| Router registration | `portfolios.router` | `onboarding_router` ✅ |

### Resolution Strategy: MANUAL MERGE (Keep Both)

**Why Manual?** Both branches add NEW functionality that doesn't overlap. We want BOTH the multi-portfolio endpoints AND the onboarding endpoints.

**Step-by-Step Resolution:**

1. **Open the file in your editor** (VS Code, etc.)

2. **Find the import section** and make it look like this:

```python
from fastapi import APIRouter

from app.api.v1 import auth, data, portfolios  # ← Keep from UIRefactor
from app.api.v1.chat import router as chat_router
from app.api.v1.analytics.router import router as analytics_router
from app.api.v1.target_prices import router as target_prices_router
from app.api.v1.tags import router as tags_router
from app.api.v1.position_tags import router as position_tags_router
from app.api.v1.insights import router as insights_router
from app.api.v1.onboarding import router as onboarding_router  # ← Add from Onboarding
from app.api.v1.endpoints import admin_batch
from app.api.v1.endpoints.fundamentals import router as fundamentals_router  # ← Keep from UIRefactor
```

3. **Find the router registration section** and make it look like this:

```python
# Create the main v1 router
api_router = APIRouter(prefix="/v1")

# Include all endpoint routers
# Authentication (foundation)
api_router.include_router(auth.router)

# Onboarding APIs (/onboarding/) - user registration and portfolio creation (NEW)
api_router.include_router(onboarding_router)  # ← Add from Onboarding

# Portfolio Management APIs (/portfolios/) - multi-portfolio CRUD
api_router.include_router(portfolios.router)  # ← Keep from UIRefactor

# Chat API for Agent
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])

# Raw Data APIs (/data/) - for LLM consumption
api_router.include_router(data.router)

# Analytics APIs (/analytics/) - calculated metrics
api_router.include_router(analytics_router)

# Fundamentals APIs (/fundamentals/) - financial statements and analyst data
api_router.include_router(fundamentals_router)  # ← Keep from UIRefactor

# ... rest stays the same ...
```

4. **Save the file**

5. **Stage the resolved file:**
```bash
git add backend/app/api/v1/router.py
```

### What You Get After Resolution

You'll have **ALL routers** registered:
- ✅ Onboarding router (`/api/v1/onboarding/*`)
- ✅ Portfolio router (`/api/v1/portfolios/*`)
- ✅ Fundamentals router (`/api/v1/fundamentals/*`)
- ✅ All other existing routers

This means both onboarding AND multi-portfolio endpoints will be available!

### Testing After Merge

After merge completes, verify both work:
```bash
# Start backend
.venv/Scripts/python.exe run.py

# Visit http://localhost:8000/docs

# You should see:
# - POST /api/v1/onboarding/register (from onboarding)
# - POST /api/v1/onboarding/create-portfolio (from onboarding)
# - POST /api/v1/portfolios (from multi-portfolio)
# - GET /api/v1/portfolios (from multi-portfolio)
# - GET /api/v1/analytics/aggregate/* (from multi-portfolio)
```

---

## Conflict 3: backend/app/main.py 🟡 MEDIUM

### Severity: MEDIUM - Exception handlers and startup validation

### What Git Will Show You

```python
"""
SigmaSight Backend - FastAPI Application
"""
<<<<<<< HEAD (UIRefactor)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
=======
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
>>>>>>> origin/FrontendLocal-Onboarding

from app.config import settings
from app.api.v1.router import api_router
from app.core.logging import setup_logging, api_logger
<<<<<<< HEAD (UIRefactor)
# UIRefactor has NO additional imports
=======
from app.core.onboarding_errors import OnboardingException, create_error_response
from app.core.startup_validation import validate_system_prerequisites, get_prerequisite_status
>>>>>>> origin/FrontendLocal-Onboarding

# ... CORS middleware setup (same in both) ...

<<<<<<< HEAD (UIRefactor)
# UIRefactor has NO exception handlers here
=======
# Exception handlers
@app.exception_handler(OnboardingException)
async def onboarding_exception_handler(request: Request, exc: OnboardingException):
    """Handle onboarding-specific exceptions"""
    api_logger.warning(
        f"Onboarding error: {exc.code} - {exc.message}",
        extra={"code": exc.code, "details": exc.details}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details
        )
    )
>>>>>>> origin/FrontendLocal-Onboarding

# Include API router
app.include_router(api_router, prefix="/api")

# ... /health endpoint (same in both) ...

<<<<<<< HEAD (UIRefactor)
# UIRefactor has NO additional health endpoints or startup events
=======
@app.get("/health/prerequisites")
async def health_prerequisites():
    """
    Health check for system prerequisites.
    """
    status = await get_prerequisite_status()
    return status

@app.on_event("startup")
async def startup_validation():
    """
    Validate system prerequisites on startup.
    """
    try:
        api_logger.info("Running startup validation...")
        result = await validate_system_prerequisites()
        # ... validation logic ...
    except Exception as e:
        api_logger.error(f"Startup validation failed: {e}")
        raise
>>>>>>> origin/FrontendLocal-Onboarding

# ... rest is same ...
```

### Key Differences Summary

| Feature | UIRefactor | Onboarding |
|---------|------------|------------|
| Request import | No | ✅ Has |
| JSONResponse import | No | ✅ Has |
| OnboardingException import | No | ✅ Has |
| startup_validation import | No | ✅ Has |
| Exception handler | No | ✅ Has |
| /health/prerequisites endpoint | No | ✅ Has |
| Startup event | No | ✅ Has |

### Resolution Strategy: MANUAL MERGE (Add Onboarding Features)

**Why Manual?** Onboarding adds NEW features that don't exist in UIRefactor. We want to ADD these features to the UIRefactor base.

**Step-by-Step Resolution:**

1. **Start with UIRefactor base, add onboarding imports:**

```python
"""
SigmaSight Backend - FastAPI Application
"""
from fastapi import FastAPI, Request  # ← Add Request from Onboarding
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse  # ← Add from Onboarding

from app.config import settings
from app.api.v1.router import api_router
from app.core.logging import setup_logging, api_logger
from app.core.onboarding_errors import OnboardingException, create_error_response  # ← Add from Onboarding
from app.core.startup_validation import validate_system_prerequisites, get_prerequisite_status  # ← Add from Onboarding
```

2. **Keep CORS middleware as-is** (same in both)

3. **ADD exception handler after CORS middleware:**

```python
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers (ADD THIS from Onboarding)
@app.exception_handler(OnboardingException)
async def onboarding_exception_handler(request: Request, exc: OnboardingException):
    """Handle onboarding-specific exceptions"""
    api_logger.warning(
        f"Onboarding error: {exc.code} - {exc.message}",
        extra={"code": exc.code, "details": exc.details}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details
        )
    )

# Include API router
app.include_router(api_router, prefix="/api")
```

4. **Keep existing /root and /health endpoints**

5. **ADD new health/prerequisites endpoint:**

```python
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# ADD THIS from Onboarding
@app.get("/health/prerequisites")
async def health_prerequisites():
    """
    Health check for system prerequisites.

    Returns current status of factor definitions and stress scenarios.
    Useful for deployment health checks and troubleshooting.
    """
    status = await get_prerequisite_status()
    return status
```

6. **ADD startup validation event:**

```python
# ADD THIS from Onboarding
@app.on_event("startup")
async def startup_validation():
    """
    Validate system prerequisites on startup.

    - Development: Logs warnings, doesn't block
    - Production: Blocks startup if prerequisites missing
    - Bypass: Set SKIP_STARTUP_VALIDATION=true
    """
    try:
        api_logger.info("Running startup validation...")
        result = await validate_system_prerequisites()

        if not result["valid"]:
            api_logger.warning("Startup validation completed with warnings")
            for warning in result["warnings"]:
                api_logger.warning(f"  - {warning}")
        else:
            api_logger.info("✅ Startup validation passed")

    except Exception as e:
        # In production, this will prevent startup
        api_logger.error(f"Startup validation failed: {e}")
        raise
```

7. **Keep /debug/routes endpoint**

8. **Stage the file:**
```bash
git add backend/app/main.py
```

### What You Get After Resolution

The final `main.py` will have:
- ✅ All UIRefactor functionality (base app, CORS)
- ✅ OnboardingException handler (structured error responses)
- ✅ /health/prerequisites endpoint (system health checks)
- ✅ Startup validation (ensures factor definitions exist)
- ✅ All existing endpoints (/root, /health, /debug/routes)

### Why These Additions Are Good

1. **OnboardingException handler:** Provides consistent error responses for onboarding flows (CSV validation errors, invite code errors, etc.)

2. **/health/prerequisites:** Useful for deployment health checks - ensures database has required reference data

3. **Startup validation:** Catches configuration issues early (missing factor definitions, stress scenarios) before they cause runtime errors

---

## Conflict 4: backend/app/config.py 🟢 LOW

### Severity: LOW - Simple settings addition

### What Git Will Show You

```python
# ... existing settings ...

# Anthropic API settings
ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514", env="ANTHROPIC_MODEL")
ANTHROPIC_MAX_TOKENS: int = Field(default=8000, env="ANTHROPIC_MAX_TOKENS")
ANTHROPIC_TEMPERATURE: float = Field(default=0.7, env="ANTHROPIC_TEMPERATURE")
ANTHROPIC_TIMEOUT_SECONDS: int = Field(default=120, env="ANTHROPIC_TIMEOUT_SECONDS")

<<<<<<< HEAD (UIRefactor)
# JWT settings (UIRefactor has no additional settings here)
=======
# Onboarding settings
BETA_INVITE_CODE: str = Field(
    default="PRESCOTT-LINNAEAN-COWPERTHWAITE",
    env="BETA_INVITE_CODE",
    description="Beta invite code for user registration. Can be overridden via environment variable for production."
)
DETERMINISTIC_UUIDS: bool = Field(
    default=True,
    env="DETERMINISTIC_UUIDS",
    description="Use deterministic UUIDs for testing/demo (True). Set False for production random UUIDs."
)

>>>>>>> origin/FrontendLocal-Onboarding
# JWT settings
SECRET_KEY: str = Field(..., env="SECRET_KEY")
ALGORITHM: str = "HS256"
```

### Resolution Strategy: MANUAL MERGE (Add Onboarding Settings)

**Simple!** Just add the two new settings from onboarding.

**Step-by-Step:**

1. **Open config.py**

2. **Find the Anthropic settings section**

3. **ADD the onboarding settings right after:**

```python
# Anthropic API settings
ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514", env="ANTHROPIC_MODEL")
ANTHROPIC_MAX_TOKENS: int = Field(default=8000, env="ANTHROPIC_MAX_TOKENS")
ANTHROPIC_TEMPERATURE: float = Field(default=0.7, env="ANTHROPIC_TEMPERATURE")
ANTHROPIC_TIMEOUT_SECONDS: int = Field(default=120, env="ANTHROPIC_TIMEOUT_SECONDS")

# Onboarding settings (ADD THIS)
BETA_INVITE_CODE: str = Field(
    default="PRESCOTT-LINNAEAN-COWPERTHWAITE",
    env="BETA_INVITE_CODE",
    description="Beta invite code for user registration. Can be overridden via environment variable for production."
)
DETERMINISTIC_UUIDS: bool = Field(
    default=True,
    env="DETERMINISTIC_UUIDS",
    description="Use deterministic UUIDs for testing/demo (True). Set False for production random UUIDs."
)

# JWT settings
SECRET_KEY: str = Field(..., env="SECRET_KEY")
ALGORITHM: str = "HS256"
```

4. **Stage the file:**
```bash
git add backend/app/config.py
```

### What These Settings Do

1. **BETA_INVITE_CODE:**
   - Default: `"PRESCOTT-LINNAEAN-COWPERTHWAITE"`
   - Purpose: Single invite code all beta users will use
   - Can override via environment variable for different deployments
   - Used by: `app/services/invite_code_service.py`

2. **DETERMINISTIC_UUIDS:**
   - Default: `True` (for testing/development)
   - Purpose: Generate deterministic UUIDs based on email (reproducible)
   - Set to `False` in production for random UUIDs
   - Used by: `app/core/uuid_strategy.py`

### Testing After Merge

```python
# Test that settings load correctly
from app.config import settings

print(settings.BETA_INVITE_CODE)  # Should print: PRESCOTT-LINNAEAN-COWPERTHWAITE
print(settings.DETERMINISTIC_UUIDS)  # Should print: True
```

---

## Conflict 5: backend/CLAUDE.md 🟢 LOW

### Severity: LOW - Documentation only

### What Git Will Show You

```markdown
# Claude AI Agent Instructions - SigmaSight Backend

<<<<<<< HEAD (UIRefactor)
**Purpose**: Complete instructions and reference guide...
**Last Updated**: 2025-10-29
=======
> ⚠️ **CRITICAL WARNING (2025-08-26)**: Many API endpoints return MOCK data...
**Last Updated**: 2025-10-04
>>>>>>> origin/FrontendLocal-Onboarding

# ... lots of documentation differences ...
```

### Resolution Strategy: KEEP UIRefactor (Newer Documentation)

**Why?** UIRefactor's CLAUDE.md is dated October 29, 2025 (newer) vs onboarding's October 4, 2025 (older).

**Command:**
```bash
git checkout --ours backend/CLAUDE.md
git add backend/CLAUDE.md
```

**What This Means:**
- We keep the UIRefactor version
- The onboarding-specific documentation will be added separately in Phase 5
- UIRefactor's docs reflect the current multi-portfolio architecture

### Follow-Up Action (Phase 5)

After merge completes, you can optionally add onboarding documentation:

1. Add a section to CLAUDE.md about onboarding endpoints
2. Reference the detailed onboarding docs that will be merged:
   - `_docs/requirements/USER_PORTFOLIO_ONBOARDING_DESIGN.md`
   - `_docs/ONBOARDING_GUIDE.md`

---

## Summary: Quick Resolution Checklist

When you execute the merge, resolve conflicts in this order:

### Step 1: models/users.py (CRITICAL)
```bash
git checkout --ours backend/app/models/users.py
git add backend/app/models/users.py
```
✅ **Result:** Multi-portfolio schema preserved

### Step 2: api/v1/router.py (MANUAL)
- [ ] Open in editor
- [ ] Add `portfolios` to imports
- [ ] Add `onboarding_router` to imports
- [ ] Add `fundamentals_router` to imports
- [ ] Register BOTH `onboarding_router` and `portfolios.router`
```bash
git add backend/app/api/v1/router.py
```
✅ **Result:** Both routers registered

### Step 3: main.py (MANUAL)
- [ ] Add `Request`, `JSONResponse` to imports
- [ ] Add onboarding error imports
- [ ] Add `OnboardingException` handler after CORS
- [ ] Add `/health/prerequisites` endpoint
- [ ] Add `startup_validation` event
```bash
git add backend/app/main.py
```
✅ **Result:** Exception handling + startup validation added

### Step 4: config.py (MANUAL)
- [ ] Add `BETA_INVITE_CODE` setting after Anthropic settings
- [ ] Add `DETERMINISTIC_UUIDS` setting
```bash
git add backend/app/config.py
```
✅ **Result:** Onboarding configuration added

### Step 5: CLAUDE.md (SIMPLE)
```bash
git checkout --ours backend/CLAUDE.md
git add backend/CLAUDE.md
```
✅ **Result:** Newer documentation kept

### Final Check
```bash
git status
# Should show: "All conflicts fixed but you are still merging"

git diff --cached
# Review all staged changes

git commit
# Complete the merge
```

---

## Visual Conflict Resolution Map

```
Conflict 1: models/users.py
├─ Import conflict: Boolean type
│  └─ Resolution: Keep UIRefactor (needs Boolean for is_active)
├─ User.portfolio vs User.portfolios
│  └─ Resolution: Keep UIRefactor (portfolios - plural, list)
├─ Portfolio fields: account_name, account_type, is_active
│  └─ Resolution: Keep UIRefactor (has these fields)
└─ Portfolio.user_id unique constraint
   └─ Resolution: Keep UIRefactor (no unique, allows multiple)

Conflict 2: api/v1/router.py
├─ portfolios import
│  └─ Resolution: Keep UIRefactor (need multi-portfolio endpoints)
├─ fundamentals import
│  └─ Resolution: Keep UIRefactor (keep fundamentals)
├─ onboarding_router import
│  └─ Resolution: Add from Onboarding (need onboarding endpoints)
└─ Router registration
   └─ Resolution: Register BOTH portfolios and onboarding

Conflict 3: main.py
├─ Request, JSONResponse imports
│  └─ Resolution: Add from Onboarding
├─ OnboardingException handler
│  └─ Resolution: Add from Onboarding
├─ /health/prerequisites
│  └─ Resolution: Add from Onboarding
└─ Startup validation
   └─ Resolution: Add from Onboarding

Conflict 4: config.py
├─ BETA_INVITE_CODE
│  └─ Resolution: Add from Onboarding
└─ DETERMINISTIC_UUIDS
   └─ Resolution: Add from Onboarding

Conflict 5: CLAUDE.md
└─ Documentation updates
   └─ Resolution: Keep UIRefactor (newer)
```

---

## Expected Outcome After All Conflicts Resolved

### Files Changed
- ✅ `backend/app/models/users.py` - Multi-portfolio schema
- ✅ `backend/app/api/v1/router.py` - Both routers registered
- ✅ `backend/app/main.py` - Enhanced with onboarding handlers
- ✅ `backend/app/config.py` - Onboarding settings added
- ✅ `backend/CLAUDE.md` - UIRefactor docs kept

### New Files Added (No Conflicts)
- ✅ 40+ new files from onboarding branch
- ✅ 8 service files
- ✅ 4 API endpoints
- ✅ 11 test files
- ✅ 5 documentation files
- ✅ 10 frontend components

### Endpoints Available
- ✅ POST /api/v1/onboarding/register
- ✅ POST /api/v1/onboarding/create-portfolio
- ✅ GET /api/v1/onboarding/csv-template
- ✅ POST /api/v1/portfolios (multi-portfolio)
- ✅ GET /api/v1/portfolios (list all)
- ✅ GET /api/v1/analytics/aggregate/* (5 endpoints)

### What Still Needs Work (Phase 2)
- ⚠️ `app/services/onboarding_service.py` - Update for multi-portfolio
- ⚠️ `app/api/v1/onboarding.py` - Add account fields to responses
- ⚠️ All test files - Update assertions

---

**Document Version:** 1.0
**Created:** 2025-11-01
**Status:** Complete - Ready for merge execution
