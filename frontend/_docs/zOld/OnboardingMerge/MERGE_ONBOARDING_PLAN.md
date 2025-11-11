# Merge Planning Document: FrontendLocal-Onboarding → UIRefactor

**Created:** 2025-11-01
**Status:** Planning Phase - No Code Changes Yet
**Objective:** Merge onboarding feature into UIRefactor branch while preserving multi-portfolio architecture

---

## Executive Summary

### Why This Merge is Critical

**Problem:** Test users cannot sign up - onboarding code is on separate branch
**Urgency:** HIGH - Blocking user acquisition
**Complexity:** MEDIUM - 1 major schema conflict, several file conflicts
**Timeline:** 2-3 days of focused work
**Risk:** LOW-MEDIUM with proper testing

### Strategic Decision

✅ **Merge onboarding INTO UIRefactor BEFORE frontend work**

**Rationale:**
1. Backend multi-portfolio is complete and stable (3 days old)
2. Onboarding is mature and tested (~19k lines of code)
3. Test users are blocked without onboarding
4. Easier to adapt onboarding to multi-portfolio than vice versa
5. Frontend hasn't been built for either feature yet

---

## Branch Analysis

### Common Ancestor
**Commit:** `842b0fbc` (merged FrontendLocal into FrontendLocal-Onboarding)
**Date:** ~October 2025

### UIRefactor Branch (Target)
- **HEAD:** `8eb860fd` (61 commits ahead of ancestor)
- **Key Feature:** Multi-portfolio support (completed Nov 1, 2025)
- **Database Schema:** Users can have MULTIPLE portfolios
- **New Fields:** `account_name`, `account_type`, `is_active`
- **New Endpoints:** 10 endpoints (5 CRUD + 5 aggregate analytics)
- **Migration:** `9b0768a49ad8_add_multi_portfolio_support.py` (critical!)

### FrontendLocal-Onboarding Branch (Source)
- **HEAD:** `ef770184` (17 commits ahead of ancestor)
- **Key Feature:** User onboarding with CSV import
- **Database Schema:** Users have ONE portfolio (old model)
- **New Services:** 8 new service files
- **New Endpoints:** 4 onboarding endpoints
- **Tests:** 18 test files (e2e, integration, unit)

### File Changes Summary
- **Total Files Changed:** 219 files
- **Backend Files:** ~80 files
- **Frontend Files:** ~130 files
- **Documentation:** ~10 files

---

## Critical Conflicts (Must Resolve)

### 🔴 Conflict 1: Database Schema - models/users.py

**THE CORE ISSUE:** Fundamental incompatibility in User ↔ Portfolio relationship

#### UIRefactor (Current - KEEP THIS)
```python
class User(Base):
    # One-to-many relationship (MULTIPLE portfolios)
    portfolios: Mapped[List["Portfolio"]] = relationship(
        "Portfolio",
        back_populates="user",
        uselist=True
    )

class Portfolio(Base):
    # NO unique constraint on user_id (allows multiple portfolios per user)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
        # NO unique=True
    )

    # NEW fields from multi-portfolio
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default='taxable')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User", back_populates="portfolios")

    __table_args__ = (
        Index('ix_portfolios_deleted_at', 'deleted_at'),
        Index('ix_portfolios_user_id', 'user_id'),  # Non-unique index
    )
```

#### FrontendLocal-Onboarding (Incoming - ADAPT THIS)
```python
class User(Base):
    # One-to-one relationship (SINGLE portfolio)
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="user",
        uselist=False  # ❌ INCOMPATIBLE
    )

class Portfolio(Base):
    # UNIQUE constraint on user_id (only one portfolio per user)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        unique=True  # ❌ INCOMPATIBLE
    )

    # NO account_name, account_type, is_active fields ❌

    user: Mapped["User"] = relationship("User", back_populates="portfolio")

    __table_args__ = (
        UniqueConstraint('user_id', name='uq_portfolios_user_id'),  # ❌ INCOMPATIBLE
        Index('ix_portfolios_deleted_at', 'deleted_at'),
    )
```

#### Resolution Strategy
**KEEP:** UIRefactor schema (multi-portfolio)
**ADAPT:** Onboarding code to work with `user.portfolios[0]` instead of `user.portfolio`

**Files to Update After Merge:**
1. `app/services/onboarding_service.py` - Update portfolio creation
2. `app/api/v1/onboarding.py` - Update response schemas
3. All onboarding tests - Update assertions

---

### 🟡 Conflict 2: API Router Registration - api/v1/router.py

**Issue:** Both branches add new router imports

#### UIRefactor
```python
from app.api.v1 import auth, data, portfolios  # ← portfolios added
from app.api.v1.analytics.router import router as analytics_router

# Portfolio Management APIs (/portfolios/) - multi-portfolio CRUD
api_router.include_router(portfolios.router)  # ← NEW in UIRefactor
```

#### FrontendLocal-Onboarding
```python
from app.api.v1 import auth, data  # No portfolios
from app.api.v1.onboarding import router as onboarding_router  # ← NEW in onboarding

# Onboarding APIs (/onboarding/)
api_router.include_router(onboarding_router)  # ← NEW in onboarding
```

#### Resolution
**MERGE BOTH:** Include both routers

```python
from app.api.v1 import auth, data, portfolios
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.analytics.router import router as analytics_router

# Onboarding APIs (user registration + first portfolio)
api_router.include_router(onboarding_router)

# Portfolio Management APIs (additional portfolios)
api_router.include_router(portfolios.router)
```

---

### 🟡 Conflict 3: Application Startup - app/main.py

**Issue:** Onboarding adds exception handlers and startup validation

#### UIRefactor
```python
# Minimal main.py - just CORS and health check
app = FastAPI(title="SigmaSight API", version="1.4.6")
app.add_middleware(CORSMiddleware, ...)
app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

#### FrontendLocal-Onboarding
```python
# Adds exception handling and startup validation
from app.core.onboarding_errors import OnboardingException, create_error_response
from app.core.startup_validation import validate_system_prerequisites

@app.exception_handler(OnboardingException)
async def onboarding_exception_handler(request, exc):
    # Structured error responses for onboarding
    ...

@app.on_event("startup")
async def startup_validation():
    # Validate factor definitions and stress scenarios exist
    ...

@app.get("/health/prerequisites")
async def health_prerequisites():
    # Check system prerequisites
    ...
```

#### Resolution
**MERGE BOTH:** Add onboarding handlers to UIRefactor's main.py

This is a clean merge - UIRefactor doesn't have these handlers, so we just add them.

---

### 🟢 Conflict 4: Configuration - app/config.py

**Issue:** Onboarding adds new config settings

#### Additions from Onboarding
```python
# Onboarding settings
BETA_INVITE_CODE: str = Field(
    default="PRESCOTT-LINNAEAN-COWPERTHWAITE",
    env="BETA_INVITE_CODE"
)
DETERMINISTIC_UUIDS: bool = Field(
    default=True,
    env="DETERMINISTIC_UUIDS"
)
```

#### Resolution
**MERGE:** Add these settings to UIRefactor's config.py

Clean merge - these are new settings, no overlap with existing config.

---

### 🟢 Conflict 5: Database Migration Files

**Issue:** UIRefactor has multi-portfolio migration that onboarding branch lacks

#### UIRefactor Migration (CRITICAL)
```
9b0768a49ad8_add_multi_portfolio_support.py
- Adds: account_name, account_type, is_active
- Removes: unique constraint on user_id
- Adds: non-unique index on user_id
```

#### Resolution
**KEEP:** UIRefactor's migration
**NO CONFLICT:** Onboarding branch has same earlier migrations, just missing this one

After merge, the migration chain will be:
```
initial_schema.py
→ [other migrations...]
→ 9b0768a49ad8_add_multi_portfolio_support.py (from UIRefactor)
```

---

## New Files from Onboarding (No Conflicts)

These files are NEW in onboarding branch and don't exist in UIRefactor. They will be added cleanly.

### Backend Services (8 files)
1. ✅ `app/services/onboarding_service.py` (345 lines) - Main orchestration
2. ✅ `app/services/csv_parser_service.py` (836 lines) - CSV parsing
3. ✅ `app/services/position_import_service.py` (269 lines) - Position creation
4. ✅ `app/services/invite_code_service.py` (91 lines) - Invite validation
5. ✅ `app/services/preprocessing_service.py` (266 lines) - Data preprocessing
6. ✅ `app/services/security_master_service.py` (164 lines) - Security lookup
7. ✅ `app/services/price_cache_service.py` (170 lines) - Price caching
8. ✅ `app/services/batch_trigger_service.py` (185 lines) - Batch triggers

### Backend Core (3 files)
1. ✅ `app/core/onboarding_errors.py` (383 lines) - Error framework
2. ✅ `app/core/startup_validation.py` (220 lines) - System validation
3. ✅ `app/core/uuid_strategy.py` (223 lines) - UUID generation

### API Endpoints (1 file)
1. ✅ `app/api/v1/onboarding.py` (236 lines) - 4 endpoints

### Tests (11 files)
1. ✅ `tests/e2e/test_onboarding_flow.py` (394 lines)
2. ✅ `tests/integration/test_onboarding_api.py` (447 lines)
3. ✅ `tests/integration/test_position_import.py` (314 lines)
4. ✅ `tests/unit/test_csv_parser_service.py` (408 lines)
5. ✅ `tests/unit/test_invite_code_service.py` (97 lines)
6. ✅ `tests/unit/test_position_import_service.py` (414 lines)
7. ✅ `tests/unit/test_uuid_strategy.py` (180 lines)
8. ✅ Updated `tests/conftest.py` (242 lines)
9. ✅ `tests/e2e/__init__.py`
10. ✅ Updated test fixtures
11. ✅ Updated test helpers

### Documentation (5 files)
1. ✅ `_docs/requirements/USER_PORTFOLIO_ONBOARDING_DESIGN.md` (2544 lines)
2. ✅ `_docs/requirements/ADMIN_AUTH_SUPPLEMENT.md` (624 lines)
3. ✅ `_docs/requirements/ONBOARDING_PIPELINE_COMPARISON.md` (600 lines)
4. ✅ `_docs/ONBOARDING_GUIDE.md` (493 lines)
5. ✅ Updated `_docs/requirements/DEMO_SEEDING_GUIDE.md`

### Frontend Components (10 files)
1. ✅ `frontend/src/components/onboarding/RegistrationForm.tsx` (224 lines)
2. ✅ `frontend/src/components/onboarding/PortfolioUploadForm.tsx` (295 lines)
3. ✅ `frontend/src/components/onboarding/UploadProcessing.tsx` (120 lines)
4. ✅ `frontend/src/components/onboarding/UploadSuccess.tsx` (157 lines)
5. ✅ `frontend/src/components/onboarding/ValidationErrors.tsx` (112 lines)
6. ✅ `frontend/src/hooks/useRegistration.ts` (103 lines)
7. ✅ `frontend/src/hooks/usePortfolioUpload.ts` (373 lines)
8. ✅ `frontend/src/services/onboardingService.ts` (126 lines)
9. ✅ `frontend/app/onboarding/upload/page.tsx` (62 lines)
10. ✅ `frontend/_docs/ONBOARDING_FLOW_PRD.md` (1863 lines)

---

## Files Modified in Both Branches (Potential Conflicts)

### Backend Files (Likely Conflicts)
1. 🟡 `backend/app/models/users.py` - **SCHEMA CONFLICT (critical)**
2. 🟡 `backend/app/api/v1/router.py` - **Router registration**
3. 🟡 `backend/app/main.py` - **Startup/error handlers**
4. 🟡 `backend/app/config.py` - **New settings**
5. 🟢 `backend/CLAUDE.md` - **Documentation (UIRefactor newer)**
6. 🟢 `backend/README.md` - **Documentation (merge both)**
7. 🟢 `backend/pyproject.toml` - **Dependencies (likely compatible)**

### Frontend Files (Minor Conflicts)
1. 🟢 `frontend/CLAUDE.md` - **Documentation updates**
2. 🟢 `frontend/src/services/apiClient.ts` - **Minor additions**
3. 🟢 `frontend/src/components/auth/LoginForm.tsx` - **UI updates**
4. 🟢 `frontend/src/components/portfolio/PortfolioError.tsx` - **Error handling**

### Other Files
1. 🟢 `CLAUDE.md` (root) - **Minor documentation**
2. 🟢 `.claude/settings.local.json` - **Tool settings**

---

## Post-Merge Code Adaptations Required

After merging, these files MUST be updated to work with multi-portfolio schema:

### Priority 1: Critical (Breaks Without Changes)

#### 1. `app/services/onboarding_service.py`
**Lines to Change:** ~20 modifications

**Current (onboarding branch):**
```python
async def register_user(...) -> User:
    # Creates user
    user = User(...)

    # Assumes one-to-one relationship
    if user.portfolio:  # ❌ Will break - `portfolio` doesn't exist
        raise PortfolioExistsError()
```

**Needs to Become:**
```python
async def register_user(...) -> User:
    # Creates user
    user = User(...)

    # Updated for one-to-many relationship
    if len(user.portfolios) > 0:  # ✅ Works with multi-portfolio
        raise PortfolioExistsError()
```

**Additional Changes:**
```python
# When creating first portfolio
portfolio = Portfolio(
    user_id=user.id,
    name=portfolio_name,
    account_name=f"{user.full_name}'s Main Account",  # ✅ NEW field
    account_type='taxable',  # ✅ NEW field (default)
    is_active=True,  # ✅ NEW field
    ...
)
```

#### 2. `app/api/v1/onboarding.py`
**Lines to Change:** ~10 modifications

**Update response schemas:**
```python
class RegisterResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    message: str
    next_step: dict
    # Add portfolio info if created during registration
    portfolio_id: Optional[str] = None  # ✅ NEW

class CreatePortfolioResponse(BaseModel):
    portfolio_id: str
    portfolio_name: str
    account_name: str  # ✅ NEW
    account_type: str  # ✅ NEW
    equity_balance: float
    positions_imported: int
    ...
```

#### 3. `tests/integration/test_onboarding_api.py`
**Lines to Change:** ~30 modifications

**Update assertions:**
```python
# OLD
assert response.json()["user"]["portfolio_id"] is not None

# NEW
assert len(response.json()["user"]["portfolios"]) == 1
assert response.json()["user"]["portfolios"][0]["account_type"] == "taxable"
```

### Priority 2: Important (Tests Will Fail)

#### 4. `tests/e2e/test_onboarding_flow.py`
- Update all assertions to expect `portfolios` list
- Add checks for `account_name`, `account_type`, `is_active`

#### 5. `tests/unit/test_csv_parser_service.py`
- Update portfolio creation in test fixtures
- Add new fields to test data

#### 6. `tests/unit/test_position_import_service.py`
- Update portfolio models in tests
- Verify compatibility with multi-portfolio

#### 7. `tests/conftest.py`
- Update test fixtures to create portfolios with new fields
- Add multi-portfolio test scenarios

### Priority 3: Documentation

#### 8. `_docs/requirements/USER_PORTFOLIO_ONBOARDING_DESIGN.md`
- Add note about multi-portfolio compatibility
- Update schemas to show new fields
- Add section: "Creating Additional Portfolios"

#### 9. `_docs/ONBOARDING_GUIDE.md`
- Update examples to show `account_name`, `account_type`
- Add section: "After Onboarding - Adding More Accounts"

#### 10. `frontend/_docs/ONBOARDING_FLOW_PRD.md`
- Update API contracts
- Add note about progressive disclosure (1 vs multiple portfolios)

---

## Detailed Merge Process

### Phase 0: Preparation (30 minutes)

1. **Backup Everything**
   ```bash
   # Create database backup
   cd backend
   # Your database is already backed up (local_backup files exist)

   # Verify git status
   git status
   # Should be on UIRefactor branch, clean working tree

   # Create safety tag
   git tag pre-onboarding-merge
   git tag -l  # Verify tag created
   ```

2. **Document Current State**
   ```bash
   # Record current migration
   cd backend
   .venv/Scripts/alembic.exe current
   # Should show: 9b0768a49ad8 (multi-portfolio migration)

   # Record current endpoints
   # Visit http://localhost:8000/docs
   # Screenshot API docs showing 10 multi-portfolio endpoints
   ```

3. **Create Test Merge Branch**
   ```bash
   git checkout UIRefactor
   git checkout -b test-merge/onboarding-multi-portfolio
   git push origin test-merge/onboarding-multi-portfolio  # Backup to remote
   ```

### Phase 1: Execute Merge (2-3 hours)

1. **Attempt Merge**
   ```bash
   git merge origin/FrontendLocal-Onboarding --no-commit --no-ff
   ```

   **Expected Output:**
   ```
   Auto-merging backend/app/models/users.py
   CONFLICT (content): Merge conflict in backend/app/models/users.py
   Auto-merging backend/app/api/v1/router.py
   CONFLICT (content): Merge conflict in backend/app/api/v1/router.py
   Auto-merging backend/app/main.py
   CONFLICT (content): Merge conflict in backend/app/main.py
   Auto-merging backend/app/config.py
   Auto-merging backend/CLAUDE.md
   Automatic merge failed; fix conflicts and then commit the result.
   ```

2. **Resolve Conflict 1: models/users.py**

   **Strategy:** KEEP UIRefactor version entirely, REJECT onboarding version

   ```bash
   # Accept UIRefactor version (multi-portfolio schema)
   git checkout --ours backend/app/models/users.py
   git add backend/app/models/users.py
   ```

3. **Resolve Conflict 2: api/v1/router.py**

   **Strategy:** Manual merge - include BOTH routers

   ```python
   # Edit backend/app/api/v1/router.py
   # Keep UIRefactor's portfolios import
   # Add onboarding's router import
   # Include both routers

   from app.api.v1 import auth, data, portfolios
   from app.api.v1.onboarding import router as onboarding_router

   # ... other imports ...

   # Include both routers
   api_router.include_router(onboarding_router)
   api_router.include_router(portfolios.router)
   ```

   ```bash
   git add backend/app/api/v1/router.py
   ```

4. **Resolve Conflict 3: main.py**

   **Strategy:** Manual merge - add onboarding handlers to UIRefactor base

   ```python
   # Edit backend/app/main.py
   # Start with UIRefactor version
   # Add imports from onboarding
   from app.core.onboarding_errors import OnboardingException, create_error_response
   from app.core.startup_validation import validate_system_prerequisites

   # Add exception handler after CORS middleware
   @app.exception_handler(OnboardingException)
   async def onboarding_exception_handler(request, exc):
       # ... (copy from onboarding branch)

   # Add startup validation
   @app.on_event("startup")
   async def startup_validation():
       # ... (copy from onboarding branch)

   # Add prerequisites health check
   @app.get("/health/prerequisites")
   async def health_prerequisites():
       # ... (copy from onboarding branch)
   ```

   ```bash
   git add backend/app/main.py
   ```

5. **Resolve Conflict 4: config.py**

   **Strategy:** Add onboarding settings to UIRefactor config

   ```python
   # Edit backend/app/config.py
   # Add onboarding settings after Anthropic settings

   # Onboarding settings
   BETA_INVITE_CODE: str = Field(
       default="PRESCOTT-LINNAEAN-COWPERTHWAITE",
       env="BETA_INVITE_CODE"
   )
   DETERMINISTIC_UUIDS: bool = Field(
       default=True,
       env="DETERMINISTIC_UUIDS"
   )
   ```

   ```bash
   git add backend/app/config.py
   ```

6. **Resolve Documentation Conflicts**

   ```bash
   # CLAUDE.md - Keep UIRefactor version (newer)
   git checkout --ours backend/CLAUDE.md
   git add backend/CLAUDE.md

   # README.md - Merge manually if needed
   # Review and keep best parts of both
   ```

7. **Check for Remaining Conflicts**
   ```bash
   git status
   # Should show no unmerged files

   git diff --cached
   # Review all staged changes
   ```

8. **Complete Merge (Don't Commit Yet)**
   ```bash
   # Don't commit yet - we need to adapt the code first
   # The merge is staged but not committed
   ```

### Phase 2: Adapt Onboarding Code (4-6 hours)

**Critical:** Onboarding code assumes one-to-one relationship. Must update for one-to-many.

1. **Update onboarding_service.py**

   ```bash
   # Open backend/app/services/onboarding_service.py
   ```

   **Changes needed:**

   a. Update portfolio existence check:
   ```python
   # Line ~85: Update validation
   # OLD
   if user.portfolio:
       raise PortfolioExistsError()

   # NEW
   if len(user.portfolios) > 0:
       raise PortfolioExistsError("User already has a portfolio")
   ```

   b. Update portfolio creation:
   ```python
   # Line ~140: Add new fields
   portfolio = Portfolio(
       id=portfolio_id,
       user_id=user.id,
       name=portfolio_name,
       account_name=account_name or f"{user.full_name}'s Main Account",  # ✅ NEW
       account_type='taxable',  # ✅ NEW - default to taxable
       is_active=True,  # ✅ NEW
       description=description,
       equity_balance=equity_balance,
       ...
   )
   ```

   c. Update relationship access:
   ```python
   # Search for all `user.portfolio` references
   # Replace with `user.portfolios[0]` or appropriate list access
   ```

   ```bash
   git add backend/app/services/onboarding_service.py
   ```

2. **Update onboarding.py (API endpoints)**

   ```bash
   # Open backend/app/api/v1/onboarding.py
   ```

   **Changes needed:**

   a. Update CreatePortfolioResponse schema:
   ```python
   class CreatePortfolioResponse(BaseModel):
       portfolio_id: str
       portfolio_name: str
       account_name: str  # ✅ NEW
       account_type: str  # ✅ NEW
       equity_balance: float
       positions_imported: int
       ...
   ```

   b. Update endpoint to include new fields in response:
   ```python
   @router.post("/create-portfolio", ...)
   async def create_portfolio(...):
       # ... create portfolio ...

       return CreatePortfolioResponse(
           portfolio_id=str(portfolio.id),
           portfolio_name=portfolio.name,
           account_name=portfolio.account_name,  # ✅ NEW
           account_type=portfolio.account_type,  # ✅ NEW
           ...
       )
   ```

   ```bash
   git add backend/app/api/v1/onboarding.py
   ```

3. **Update Tests - Integration**

   ```bash
   # Open tests/integration/test_onboarding_api.py
   ```

   **Changes needed:** Update all assertions

   ```python
   # Example changes:

   # OLD
   assert "portfolio_id" in response.json()

   # NEW
   assert "portfolio_id" in response.json()
   assert response.json()["account_type"] == "taxable"
   assert response.json()["is_active"] is True
   ```

   ```bash
   git add tests/integration/test_onboarding_api.py
   ```

4. **Update Tests - E2E**

   ```bash
   # Open tests/e2e/test_onboarding_flow.py
   ```

   Similar assertion updates as integration tests.

   ```bash
   git add tests/e2e/test_onboarding_flow.py
   ```

5. **Update Tests - Unit**

   ```bash
   # Update all unit test files that create Portfolio objects
   # Add account_name, account_type, is_active to test fixtures

   git add tests/unit/test_csv_parser_service.py
   git add tests/unit/test_position_import_service.py
   # ... etc
   ```

6. **Update conftest.py**

   ```bash
   # Open tests/conftest.py
   # Update portfolio fixtures to include new fields

   @pytest.fixture
   async def sample_portfolio(db_session, sample_user):
       portfolio = Portfolio(
           id=uuid4(),
           user_id=sample_user.id,
           name="Test Portfolio",
           account_name="Test Account",  # ✅ NEW
           account_type="taxable",  # ✅ NEW
           is_active=True,  # ✅ NEW
           ...
       )
       db_session.add(portfolio)
       await db_session.commit()
       return portfolio
   ```

   ```bash
   git add tests/conftest.py
   ```

### Phase 3: Testing (2-4 hours)

1. **Verify Import Compatibility**

   ```bash
   cd backend

   # Test critical imports
   .venv/Scripts/python.exe -c "from app.services.onboarding_service import onboarding_service; print('✅ Onboarding service imports')"

   .venv/Scripts/python.exe -c "from app.api.v1.onboarding import router; print('✅ Onboarding router imports')"

   .venv/Scripts/python.exe -c "from app.core.onboarding_errors import OnboardingException; print('✅ Onboarding errors import')"
   ```

2. **Run Unit Tests**

   ```bash
   # Run onboarding unit tests
   .venv/Scripts/python.exe -m pytest tests/unit/test_csv_parser_service.py -v
   .venv/Scripts/python.exe -m pytest tests/unit/test_invite_code_service.py -v
   .venv/Scripts/python.exe -m pytest tests/unit/test_position_import_service.py -v
   .venv/Scripts/python.exe -m pytest tests/unit/test_uuid_strategy.py -v

   # Expected: All pass (or identify specific failures to fix)
   ```

3. **Run Integration Tests**

   ```bash
   # Start backend if not running
   .venv/Scripts/python.exe run.py &

   # Run integration tests
   .venv/Scripts/python.exe -m pytest tests/integration/test_onboarding_api.py -v
   .venv/Scripts/python.exe -m pytest tests/integration/test_position_import.py -v

   # Expected: All pass
   ```

4. **Run E2E Tests**

   ```bash
   .venv/Scripts/python.exe -m pytest tests/e2e/test_onboarding_flow.py -v

   # This tests the full user journey:
   # 1. Register user
   # 2. Upload CSV
   # 3. Create portfolio with positions
   # 4. Trigger calculations
   ```

5. **Test Multi-Portfolio Compatibility**

   ```bash
   # Create test script: test_onboarding_multi_portfolio.py
   ```

   ```python
   """
   Test that onboarding creates first portfolio,
   then user can create additional portfolios
   """
   import asyncio
   from app.services.onboarding_service import onboarding_service
   from app.database import AsyncSessionLocal

   async def test_onboarding_then_multi():
       async with AsyncSessionLocal() as db:
           # 1. Register user (creates first portfolio via onboarding)
           user = await onboarding_service.register_user(
               email="test@example.com",
               password="SecurePass123!",
               full_name="Test User",
               invite_code="PRESCOTT-LINNAEAN-COWPERTHWAITE",
               db=db
           )

           # 2. Verify user has 1 portfolio
           assert len(user.portfolios) == 1
           assert user.portfolios[0].account_type == "taxable"

           # 3. Create second portfolio using multi-portfolio endpoint
           # (This would use POST /api/v1/portfolios)

           print("✅ Onboarding creates first portfolio")
           print("✅ Multi-portfolio endpoint can add more")

   asyncio.run(test_onboarding_then_multi())
   ```

   ```bash
   .venv/Scripts/python.exe test_onboarding_multi_portfolio.py
   ```

6. **Manual API Testing**

   ```bash
   # Start backend
   .venv/Scripts/python.exe run.py

   # Visit http://localhost:8000/docs

   # Test sequence:
   # 1. POST /api/v1/onboarding/register
   # 2. POST /api/v1/auth/login
   # 3. POST /api/v1/onboarding/create-portfolio (with CSV)
   # 4. GET /api/v1/portfolios (should show 1 portfolio)
   # 5. POST /api/v1/portfolios (create 2nd portfolio)
   # 6. GET /api/v1/portfolios (should show 2 portfolios)
   # 7. GET /api/v1/analytics/aggregate/overview (aggregated metrics)
   ```

7. **Test Backward Compatibility**

   ```bash
   # Test with existing demo users
   # 1. Login as demo_hnw@sigmasight.com
   # 2. Verify portfolio data still loads
   # 3. Check that they have 1 portfolio
   # 4. Verify analytics still work
   ```

### Phase 4: Commit Merge (30 minutes)

1. **Review All Changes**

   ```bash
   git status
   # Review all staged files

   git diff --cached | less
   # Review all changes carefully
   ```

2. **Commit the Merge**

   ```bash
   git commit -m "Merge FrontendLocal-Onboarding into UIRefactor with multi-portfolio compatibility

   - Merged onboarding feature (~19k lines) into multi-portfolio architecture
   - Adapted onboarding_service.py to use user.portfolios (one-to-many)
   - Updated Portfolio creation to include account_name, account_type, is_active
   - Merged both routers (onboarding + portfolios) in api/v1/router.py
   - Added onboarding exception handlers and startup validation to main.py
   - Added BETA_INVITE_CODE and DETERMINISTIC_UUIDS to config.py
   - Updated all onboarding tests to expect multi-portfolio schema

   New Features:
   - User registration with invite code (POST /api/v1/onboarding/register)
   - Portfolio creation with CSV import (POST /api/v1/onboarding/create-portfolio)
   - CSV template download (GET /api/v1/onboarding/csv-template)
   - 8 new service files for onboarding pipeline
   - Comprehensive error handling framework
   - 11 test files (e2e, integration, unit)

   Compatibility:
   - Onboarding creates FIRST portfolio with account_type='taxable'
   - Users can add additional portfolios via POST /api/v1/portfolios
   - All multi-portfolio endpoints (aggregation) work with onboarded users
   - Backward compatible with existing demo users (1 portfolio = identity aggregation)

   Testing:
   - ✅ All onboarding unit tests passing
   - ✅ Integration tests updated for multi-portfolio
   - ✅ E2E flow tested (register → upload → create portfolio)
   - ✅ Multi-portfolio aggregation verified with onboarded users

   Documentation:
   - USER_PORTFOLIO_ONBOARDING_DESIGN.md (2544 lines)
   - ONBOARDING_GUIDE.md (493 lines)
   - Frontend onboarding PRD (1863 lines)

   Migration: Uses existing 9b0768a49ad8 (multi-portfolio) migration
   "
   ```

3. **Tag the Merge**

   ```bash
   git tag onboarding-merge-complete
   ```

4. **Push to Remote**

   ```bash
   # Push test merge branch
   git push origin test-merge/onboarding-multi-portfolio

   # Don't merge to UIRefactor yet - test first!
   ```

### Phase 5: Validation & Cleanup (1-2 hours)

1. **Fresh Install Test**

   ```bash
   # Simulate fresh setup
   cd backend

   # Drop and recreate database
   # (Use your Railway backup if needed)

   # Run migrations
   .venv/Scripts/alembic.exe upgrade head

   # Seed demo data
   .venv/Scripts/python.exe scripts/database/reset_and_seed.py seed

   # Start backend
   .venv/Scripts/python.exe run.py

   # Test onboarding flow manually
   ```

2. **Regression Testing**

   ```bash
   # Test all existing features still work
   # 1. Login as demo users
   # 2. View portfolios
   # 3. Check analytics
   # 4. Test AI chat
   # 5. Test target prices
   # 6. Test sector tagging
   # 7. Test batch processing
   ```

3. **Document Known Issues**

   Create `ONBOARDING_MERGE_NOTES.md`:
   ```markdown
   # Onboarding Merge Notes

   ## Issues Found During Testing
   - [ ] Issue 1: ...
   - [ ] Issue 2: ...

   ## Follow-Up Tasks
   - [ ] Update frontend to use onboarding flow
   - [ ] Add "Create Additional Account" button
   - [ ] Implement progressive disclosure
   ```

4. **If All Tests Pass: Merge to UIRefactor**

   ```bash
   # Switch to UIRefactor
   git checkout UIRefactor

   # Merge test branch
   git merge test-merge/onboarding-multi-portfolio --ff-only

   # Push to remote
   git push origin UIRefactor

   # Clean up test branch
   git branch -d test-merge/onboarding-multi-portfolio
   ```

---

## Risk Mitigation

### Rollback Plan

If merge fails catastrophically:

```bash
# Abort merge if not committed
git merge --abort

# Or reset to pre-merge state
git reset --hard pre-onboarding-merge

# Restore database from backup
# (You have local_backup files)
```

### Safety Checks

Before declaring merge successful:

- [ ] Backend starts without errors
- [ ] All migrations run successfully
- [ ] Demo users can login
- [ ] Onboarding flow completes end-to-end
- [ ] Multi-portfolio aggregation works
- [ ] Existing features not broken
- [ ] Tests passing (at least core tests)

---

## Success Metrics

✅ **Merge is successful when:**

1. Backend starts and serves requests
2. User can register with invite code
3. User can upload CSV and create portfolio
4. Created portfolio has `account_name`, `account_type`, `is_active`
5. User can create 2nd portfolio via `/api/v1/portfolios`
6. Aggregate analytics work across both portfolios
7. Existing demo users still function
8. All critical tests passing
9. No database errors
10. Documentation updated

---

## Timeline Estimate

| Phase | Time | Complexity |
|-------|------|------------|
| **Phase 0:** Preparation | 30 min | Low |
| **Phase 1:** Execute Merge | 2-3 hours | Medium |
| **Phase 2:** Adapt Code | 4-6 hours | Medium-High |
| **Phase 3:** Testing | 2-4 hours | Medium |
| **Phase 4:** Commit | 30 min | Low |
| **Phase 5:** Validation | 1-2 hours | Low-Medium |
| **TOTAL** | **10-16 hours** | **Medium** |

**Calendar Time:** 2-3 days (with breaks, context switching)

---

## Next Steps

### Immediate (Before Merge)

1. ✅ Review this plan
2. ✅ Ask questions about anything unclear
3. ✅ Decide on merge timing (now vs later)
4. ✅ Ensure you have time blocked (2-3 days)

### During Merge

1. Follow phases sequentially
2. Document issues as you encounter them
3. Don't skip testing phases
4. Ask for help if stuck

### After Merge

1. Update project README with onboarding instructions
2. Create user-facing documentation
3. Test with real test user
4. Plan frontend implementation
5. Consider creating video demo

---

## Questions to Answer Before Starting

1. **Database:** Are you comfortable with your current database state? Any concerns about data loss?

2. **Timing:** Do you have 2-3 focused days to dedicate to this?

3. **Testing:** Can you allocate time for thorough testing, or do you want to move fast?

4. **Rollback:** Are you comfortable with the rollback plan if things go wrong?

5. **Help:** Do you want me to guide you through each conflict as they happen, or do you prefer to try solo first?

---

## Appendix A: Conflict Resolution Reference

### Quick Resolution Guide

```bash
# Accept UIRefactor version
git checkout --ours <file>

# Accept Onboarding version
git checkout --theirs <file>

# Manual merge (open in editor)
# Look for <<<<<<< ======= >>>>>>>
# Decide which to keep or merge both
```

### Critical Files - Resolution Strategy

| File | Strategy | Reason |
|------|----------|--------|
| `models/users.py` | Keep UIRefactor (--ours) | Multi-portfolio schema is target |
| `api/v1/router.py` | Manual merge (both routers) | Need both endpoints |
| `main.py` | Manual merge (add handlers) | Onboarding adds to base |
| `config.py` | Manual merge (add settings) | Onboarding adds to base |
| `CLAUDE.md` | Keep UIRefactor (--ours) | Newer documentation |

---

## Appendix B: File Modification Checklist

After merge, verify these files are updated:

### Backend Services
- [ ] `app/services/onboarding_service.py` - Updated for multi-portfolio
- [ ] `app/api/v1/onboarding.py` - Updated response schemas

### Backend Core
- [ ] `app/models/users.py` - Multi-portfolio schema (from UIRefactor)
- [ ] `app/api/v1/router.py` - Both routers registered
- [ ] `app/main.py` - Exception handlers added
- [ ] `app/config.py` - Onboarding settings added

### Tests
- [ ] `tests/integration/test_onboarding_api.py` - Assertions updated
- [ ] `tests/e2e/test_onboarding_flow.py` - Assertions updated
- [ ] `tests/unit/test_csv_parser_service.py` - Fixtures updated
- [ ] `tests/unit/test_position_import_service.py` - Fixtures updated
- [ ] `tests/conftest.py` - Portfolio fixtures updated

### Documentation
- [ ] `_docs/requirements/USER_PORTFOLIO_ONBOARDING_DESIGN.md` - Multi-portfolio notes added
- [ ] `_docs/ONBOARDING_GUIDE.md` - Examples updated
- [ ] `frontend/_docs/ONBOARDING_FLOW_PRD.md` - API contracts updated

---

**Document Version:** 1.0
**Created:** 2025-11-01
**Status:** Planning - Ready for Review
**Next Action:** Review plan, ask questions, get approval to proceed
