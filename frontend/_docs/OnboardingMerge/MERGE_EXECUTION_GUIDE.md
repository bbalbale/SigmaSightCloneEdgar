# Merge Execution Guide: Step-by-Step for Coding Agents

**Created:** 2025-11-01
**Purpose:** Executable guide for AI coding agents to merge FrontendLocal-Onboarding into UIRefactor
**Designed for:** Multi-context-window execution with clear checkpoints

---

## 📚 Reference Documents

Before starting, ensure these documents are available:
- **`MERGE_ONBOARDING_PLAN.md`** - Overall strategy and rationale
- **`MERGE_CONFLICTS_DETAILED_ANALYSIS.md`** - Detailed conflict resolutions
- This document (`MERGE_EXECUTION_GUIDE.md`) - Execution checklist

---

## 🎯 Execution Overview

**Total Time:** 2-3 days (10-16 hours of work)
**Phases:** 6 phases with clear checkpoints
**Current Phase:** [MARK YOUR PROGRESS HERE]

### Phase Checklist
- [ ] **Phase 0:** Preparation & Backup (30 min)
- [ ] **Phase 1:** Execute Merge & Resolve Conflicts (2-3 hours)
- [ ] **Phase 2:** Adapt Onboarding Code for Multi-Portfolio (4-6 hours)
- [ ] **Phase 3:** Update Tests (2-3 hours)
- [ ] **Phase 4:** Integration Testing (2-4 hours)
- [ ] **Phase 5:** Commit & Documentation (1-2 hours)

---

## 🚦 Before Starting: Context Check

**AI Agent: Answer these questions before proceeding:**

1. What is the current branch? (Should be: `UIRefactor` or `test-merge/onboarding-multi-portfolio`)
2. What is the git status? (Should be: clean working tree)
3. Are there any uncommitted changes? (Should be: no)
4. Which phase are you resuming from? (Mark above)

**Command to check:**
```bash
git branch --show-current
git status
```

**Expected output:**
```
On branch UIRefactor
nothing to commit, working tree clean
```

---

## Phase 0: Preparation & Backup ✅

**Objective:** Ensure safety net exists before merge
**Time:** 30 minutes
**Checkpoint:** Phase0Complete

### Step 0.1: Verify Current State

**Command:**
```bash
cd C:\Users\BenBalbale\CascadeProjects\SigmaSight
git branch --show-current
git status
```

**Validation:**
- ✅ Current branch is `UIRefactor`
- ✅ Working tree is clean
- ✅ No untracked critical files

**If validation fails:** Stop and resolve issues first.

---

### Step 0.2: Check Current Database Migration

**Command:**
```bash
cd backend
.venv/Scripts/alembic.exe current
```

**Expected output:**
```
9b0768a49ad8 (head)
```

**Validation:**
- ✅ Current migration is `9b0768a49ad8` (multi-portfolio)
- ✅ This is the HEAD migration

**If different:** Document the actual migration ID - you'll need it for rollback.

**Record here:** Current migration: `_________________`

---

### Step 0.3: Create Safety Tag

**Command:**
```bash
git tag pre-onboarding-merge-$(date +%Y%m%d-%H%M%S)
git tag -l | tail -1
```

**Validation:**
- ✅ Tag created successfully
- ✅ Tag appears in `git tag -l` output

**Record here:** Safety tag: `_________________`

---

### Step 0.4: Create Test Merge Branch

**Command:**
```bash
git checkout -b test-merge/onboarding-multi-portfolio
git branch --show-current
```

**Expected output:**
```
Switched to a new branch 'test-merge/onboarding-multi-portfolio'
test-merge/onboarding-multi-portfolio
```

**Validation:**
- ✅ New branch created
- ✅ Currently on test merge branch
- ✅ UIRefactor branch still exists (run `git branch -a`)

---

### Step 0.5: Push Test Branch to Remote (Backup)

**Command:**
```bash
git push -u origin test-merge/onboarding-multi-portfolio
```

**Validation:**
- ✅ Branch pushed to remote successfully
- ✅ Branch visible on GitHub/remote

---

### Step 0.6: Document Starting Point

**Record the following:**
```
Date started: _________________
Time started: _________________
Current branch: test-merge/onboarding-multi-portfolio
Current commit: (run: git rev-parse HEAD): _________________
Safety tag: (from Step 0.3): _________________
Current migration: (from Step 0.2): _________________
```

---

### ✅ Phase 0 Checkpoint

**Before proceeding to Phase 1, confirm:**
- [ ] On test-merge/onboarding-multi-portfolio branch
- [ ] Working tree is clean
- [ ] Safety tag created
- [ ] Test branch pushed to remote
- [ ] Starting point documented

**If all confirmed:** Proceed to Phase 1
**If any failed:** Resolve issues before continuing

---

## Phase 1: Execute Merge & Resolve Conflicts 🔥

**Objective:** Merge branches and resolve all 5 conflicts
**Time:** 2-3 hours
**Checkpoint:** Phase1Complete

### Step 1.1: Fetch Latest from Onboarding Branch

**Command:**
```bash
git fetch origin FrontendLocal-Onboarding
```

**Validation:**
- ✅ Fetch completed without errors
- ✅ Remote branch is up to date

---

### Step 1.2: Attempt Merge (Will Have Conflicts - Expected!)

**Command:**
```bash
git merge origin/FrontendLocal-Onboarding --no-commit --no-ff
```

**Expected output:**
```
Auto-merging backend/app/models/users.py
CONFLICT (content): Merge conflict in backend/app/models/users.py
Auto-merging backend/app/api/v1/router.py
CONFLICT (content): Merge conflict in backend/app/api/v1/router.py
Auto-merging backend/app/main.py
CONFLICT (content): Merge conflict in backend/app/main.py
Auto-merging backend/app/config.py
CONFLICT (content): Merge conflict in backend/app/config.py
Auto-merging backend/CLAUDE.md
CONFLICT (content): Merge conflict in backend/CLAUDE.md
Automatic merge failed; fix conflicts and then commit the result.
```

**Validation:**
- ✅ Merge started
- ✅ 5 conflicts detected (models/users.py, router.py, main.py, config.py, CLAUDE.md)
- ✅ Git status shows "You have unmerged paths"

**Check status:**
```bash
git status
```

**If unexpected conflicts:** Document them and consult MERGE_CONFLICTS_DETAILED_ANALYSIS.md

---

### Step 1.3: Resolve Conflict 1 - models/users.py (CRITICAL) 🔴

**Reference:** See `MERGE_CONFLICTS_DETAILED_ANALYSIS.md` - Conflict 1

**Resolution Strategy:** Keep UIRefactor version entirely

**Command:**
```bash
git checkout --ours backend/app/models/users.py
git add backend/app/models/users.py
```

**Validation:**
```bash
git status
# Should show models/users.py under "Changes to be committed"
```

**Manual verification:**
```bash
# Check that multi-portfolio schema is preserved
grep "portfolios: Mapped\[List" backend/app/models/users.py
# Should output: portfolios: Mapped[List["Portfolio"]] = relationship(...)

grep "account_name" backend/app/models/users.py
# Should output: account_name: Mapped[str] = mapped_column(String(100), nullable=False)

grep "account_type" backend/app/models/users.py
# Should output: account_type: Mapped[str] = mapped_column(String(20), nullable=False, default='taxable')

grep "is_active" backend/app/models/users.py
# Should output: is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
```

**If validation fails:** STOP - models/users.py is critical. Review MERGE_CONFLICTS_DETAILED_ANALYSIS.md Conflict 1.

✅ **Checkpoint 1.3:** models/users.py resolved

---

### Step 1.4: Resolve Conflict 2 - api/v1/router.py (MANUAL) 🟡

**Reference:** See `MERGE_CONFLICTS_DETAILED_ANALYSIS.md` - Conflict 2

**Resolution Strategy:** Keep BOTH routers (portfolios + onboarding)

**Steps:**
1. Open `backend/app/api/v1/router.py` in editor
2. Find the import section
3. Manually merge to include ALL imports:

```python
from fastapi import APIRouter

from app.api.v1 import auth, data, portfolios  # ← Keep from UIRefactor
from app.api.v1.chat import router as chat_router
from app.api.v1.analytics.router import router as analytics_router
from app.api.v1.target_prices import router as target_prices_router
from app.api.v1.tags import router as tags_router
from app.api.v1.position_tags import router as position_tags_router
from app.api.v1.insights import router as insights_router
from app.api.v1.onboarding import router as onboarding_router  # ← ADD from Onboarding
from app.api.v1.endpoints import admin_batch
from app.api.v1.endpoints.fundamentals import router as fundamentals_router  # ← Keep from UIRefactor
```

4. Find the router registration section
5. Register BOTH routers:

```python
# Create the main v1 router
api_router = APIRouter(prefix="/v1")

# Include all endpoint routers
# Authentication (foundation)
api_router.include_router(auth.router)

# Onboarding APIs (/onboarding/) - user registration and portfolio creation
api_router.include_router(onboarding_router)  # ← ADD from Onboarding

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

# Target Prices APIs (/target-prices/) - portfolio-specific price targets
api_router.include_router(target_prices_router)

# Tag Management APIs (/tags/) - user-scoped organizational tags
api_router.include_router(tags_router)

# Position Tagging APIs (/positions/{id}/tags/)
api_router.include_router(position_tags_router, prefix="/positions")

# AI Insights APIs (/insights/)
api_router.include_router(insights_router)

# Admin Batch Processing APIs (/admin/batch/)
api_router.include_router(admin_batch.router)
```

6. Save and stage:

```bash
git add backend/app/api/v1/router.py
```

**Validation:**
```bash
# Check both routers are registered
grep "onboarding_router" backend/app/api/v1/router.py
# Should output: from app.api.v1.onboarding import router as onboarding_router
#                api_router.include_router(onboarding_router)

grep "portfolios.router" backend/app/api/v1/router.py
# Should output: from app.api.v1 import auth, data, portfolios
#                api_router.include_router(portfolios.router)

grep "fundamentals_router" backend/app/api/v1/router.py
# Should output: from app.api.v1.endpoints.fundamentals import router as fundamentals_router
#                api_router.include_router(fundamentals_router)
```

**If validation fails:** Check file manually, ensure both routers present.

✅ **Checkpoint 1.4:** router.py resolved

---

### Step 1.5: Resolve Conflict 3 - main.py (MANUAL) 🟡

**Reference:** See `MERGE_CONFLICTS_DETAILED_ANALYSIS.md` - Conflict 3

**Resolution Strategy:** Add onboarding features to UIRefactor base

**Steps:**
1. Open `backend/app/main.py` in editor

2. Update imports at top:

```python
"""
SigmaSight Backend - FastAPI Application
"""
from fastapi import FastAPI, Request  # ← Add Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse  # ← ADD this

from app.config import settings
from app.api.v1.router import api_router
from app.core.logging import setup_logging, api_logger
from app.core.onboarding_errors import OnboardingException, create_error_response  # ← ADD this
from app.core.startup_validation import validate_system_prerequisites, get_prerequisite_status  # ← ADD this
```

3. After CORS middleware setup, ADD exception handler:

```python
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers (ADD THIS BLOCK)
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

4. After existing /health endpoint, ADD prerequisites endpoint:

```python
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# ADD THIS ENDPOINT
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

5. Before /debug/routes endpoint, ADD startup validation:

```python
# ADD THIS EVENT HANDLER
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

@app.get("/debug/routes")
async def debug_routes():
    # ... existing code ...
```

6. Save and stage:

```bash
git add backend/app/main.py
```

**Validation:**
```bash
# Check imports added
grep "from fastapi import FastAPI, Request" backend/app/main.py
grep "from fastapi.responses import JSONResponse" backend/app/main.py
grep "from app.core.onboarding_errors import" backend/app/main.py
grep "from app.core.startup_validation import" backend/app/main.py

# Check exception handler added
grep "@app.exception_handler(OnboardingException)" backend/app/main.py

# Check prerequisites endpoint added
grep "/health/prerequisites" backend/app/main.py

# Check startup validation added
grep '@app.on_event("startup")' backend/app/main.py
```

**If validation fails:** Review file manually, ensure all additions present.

✅ **Checkpoint 1.5:** main.py resolved

---

### Step 1.6: Resolve Conflict 4 - config.py (MANUAL) 🟢

**Reference:** See `MERGE_CONFLICTS_DETAILED_ANALYSIS.md` - Conflict 4

**Resolution Strategy:** Add onboarding settings after Anthropic settings

**Steps:**
1. Open `backend/app/config.py` in editor

2. Find the Anthropic settings section (around line 100)

3. After Anthropic settings, ADD onboarding settings:

```python
    # Anthropic settings for Analytical Reasoning Layer
    ANTHROPIC_API_KEY: str = Field(default="", env="ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL: str = Field(default="claude-sonnet-4-20250514", env="ANTHROPIC_MODEL")
    ANTHROPIC_MAX_TOKENS: int = Field(default=8000, env="ANTHROPIC_MAX_TOKENS")
    ANTHROPIC_TEMPERATURE: float = Field(default=0.7, env="ANTHROPIC_TEMPERATURE")
    ANTHROPIC_TIMEOUT_SECONDS: int = Field(default=120, env="ANTHROPIC_TIMEOUT_SECONDS")

    # Onboarding settings (ADD THIS BLOCK)
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
    # ... rest of config ...
```

4. Save and stage:

```bash
git add backend/app/config.py
```

**Validation:**
```bash
# Check settings added
grep "BETA_INVITE_CODE" backend/app/config.py
grep "DETERMINISTIC_UUIDS" backend/app/config.py
grep "PRESCOTT-LINNAEAN-COWPERTHWAITE" backend/app/config.py
```

**If validation fails:** Check file manually, ensure settings present between Anthropic and JWT sections.

✅ **Checkpoint 1.6:** config.py resolved

---

### Step 1.7: Resolve Conflict 5 - CLAUDE.md (SIMPLE) 🟢

**Reference:** See `MERGE_CONFLICTS_DETAILED_ANALYSIS.md` - Conflict 5

**Resolution Strategy:** Keep UIRefactor version (newer)

**Command:**
```bash
git checkout --ours backend/CLAUDE.md
git add backend/CLAUDE.md
```

**Validation:**
```bash
git status
# Should show CLAUDE.md under "Changes to be committed"

# Check date (should be Oct 29, 2025)
grep "Last Updated" backend/CLAUDE.md
# Should output: **Last Updated**: 2025-10-29
```

✅ **Checkpoint 1.7:** CLAUDE.md resolved

---

### Step 1.8: Verify All Conflicts Resolved

**Command:**
```bash
git status
```

**Expected output:**
```
On branch test-merge/onboarding-multi-portfolio
All conflicts fixed but you are still merging.
  (use "git commit" to conclude merge)

Changes to be committed:
    modified:   backend/app/api/v1/router.py
    modified:   backend/app/config.py
    modified:   backend/app/main.py
    modified:   backend/app/models/users.py
    modified:   backend/CLAUDE.md
    new file:   backend/app/api/v1/onboarding.py
    new file:   backend/app/core/onboarding_errors.py
    new file:   backend/app/core/startup_validation.py
    ... (many more new files)
```

**Validation:**
- ✅ "All conflicts fixed but you are still merging" message
- ✅ No "Unmerged paths" section
- ✅ 5 modified files (models/users.py, router.py, main.py, config.py, CLAUDE.md)
- ✅ Many new files listed

**If validation fails:** Run `git status -u` to see remaining conflicts, resolve them.

---

### Step 1.9: Review Staged Changes

**Command:**
```bash
git diff --cached --stat
```

**Expected output should show:**
- 5 modified files (resolved conflicts)
- 40+ new files (onboarding system)
- ~20k insertions (onboarding code)

**Manual spot check:**
```bash
# Verify critical resolutions
git diff --cached backend/app/models/users.py | grep "portfolios:"
# Should show: +    portfolios: Mapped[List["Portfolio"]] = relationship(...)

git diff --cached backend/app/api/v1/router.py | grep "onboarding_router"
# Should show: +from app.api.v1.onboarding import router as onboarding_router
#              +api_router.include_router(onboarding_router)
```

---

### ✅ Phase 1 Checkpoint

**Before proceeding to Phase 2, confirm:**
- [ ] All 5 conflicts resolved
- [ ] Git status shows "All conflicts fixed"
- [ ] models/users.py has multi-portfolio schema
- [ ] router.py has both routers
- [ ] main.py has exception handlers
- [ ] config.py has onboarding settings
- [ ] CLAUDE.md kept from UIRefactor
- [ ] Reviewed staged changes

**If all confirmed:** Proceed to Phase 2
**If any failed:** Review MERGE_CONFLICTS_DETAILED_ANALYSIS.md

**DO NOT COMMIT YET** - We need to adapt the code first (Phase 2)

---

## Phase 2: Adapt Onboarding Code for Multi-Portfolio 🔧

**Objective:** Update onboarding code to work with multi-portfolio schema
**Time:** 4-6 hours
**Checkpoint:** Phase2Complete

### Overview: Why This Phase is Needed

The onboarding code was written assuming **one-to-one** relationship (user.portfolio).
Your schema now has **one-to-many** relationship (user.portfolios).

**Key changes needed:**
1. `user.portfolio` → `user.portfolios[0]`
2. Add `account_name`, `account_type`, `is_active` when creating portfolios
3. Update validation logic
4. Update response schemas

---

### Step 2.1: Update onboarding_service.py

**File:** `backend/app/services/onboarding_service.py`

**Reference:** See `MERGE_ONBOARDING_PLAN.md` - Phase 2, Priority 1

**Changes needed:** ~20 modifications

**Open file and make these changes:**

#### Change 1: Portfolio creation in register_user

**Find (around line 140):**
```python
# Create portfolio for user
portfolio = Portfolio(
    id=portfolio_id,
    user_id=user.id,
    name=portfolio_name,
    description=description,
    equity_balance=equity_balance,
    ...
)
```

**Replace with:**
```python
# Create FIRST portfolio for user (multi-portfolio support)
portfolio = Portfolio(
    id=portfolio_id,
    user_id=user.id,
    name=portfolio_name,
    account_name=f"{user.full_name}'s Main Account",  # ✅ NEW field
    account_type='taxable',  # ✅ NEW field - default to taxable
    is_active=True,  # ✅ NEW field
    description=description,
    equity_balance=equity_balance,
    ...
)
```

#### Change 2: Portfolio existence check

**Find (around line 85):**
```python
# Check if user already has portfolio
if user.portfolio:
    raise PortfolioExistsError("User already has a portfolio")
```

**Replace with:**
```python
# Check if user already has portfolio (multi-portfolio support)
if len(user.portfolios) > 0:
    raise PortfolioExistsError("User already has a portfolio")
```

#### Change 3: All other user.portfolio references

**Command to find all references:**
```bash
grep -n "user\.portfolio" backend/app/services/onboarding_service.py
```

**For each occurrence:**
- If accessing: `user.portfolio` → `user.portfolios[0]`
- If checking existence: `if user.portfolio:` → `if len(user.portfolios) > 0:`
- If creating: Add account_name, account_type, is_active fields

**Save changes:**
```bash
git add backend/app/services/onboarding_service.py
```

**Validation:**
```bash
# Should have no matches (all changed to portfolios)
grep "user\.portfolio[^s]" backend/app/services/onboarding_service.py

# Should have matches (uses portfolios)
grep "user\.portfolios" backend/app/services/onboarding_service.py

# Should have matches (new fields)
grep "account_name" backend/app/services/onboarding_service.py
grep "account_type" backend/app/services/onboarding_service.py
grep "is_active" backend/app/services/onboarding_service.py
```

✅ **Checkpoint 2.1:** onboarding_service.py updated

---

### Step 2.2: Update onboarding.py (API endpoints)

**File:** `backend/app/api/v1/onboarding.py`

**Changes needed:** ~10 modifications

**Open file and make these changes:**

#### Change 1: Update CreatePortfolioResponse schema

**Find (around line 50):**
```python
class CreatePortfolioResponse(BaseModel):
    portfolio_id: str
    portfolio_name: str
    equity_balance: float
    positions_imported: int
    positions_failed: int
    total_positions: int
    message: str
    next_step: dict
```

**Replace with:**
```python
class CreatePortfolioResponse(BaseModel):
    portfolio_id: str
    portfolio_name: str
    account_name: str  # ✅ NEW
    account_type: str  # ✅ NEW
    is_active: bool  # ✅ NEW
    equity_balance: float
    positions_imported: int
    positions_failed: int
    total_positions: int
    message: str
    next_step: dict
```

#### Change 2: Update create_portfolio endpoint response

**Find the return statement in create_portfolio endpoint:**
```python
return CreatePortfolioResponse(
    portfolio_id=str(portfolio.id),
    portfolio_name=portfolio.name,
    equity_balance=float(portfolio.equity_balance),
    ...
)
```

**Update to:**
```python
return CreatePortfolioResponse(
    portfolio_id=str(portfolio.id),
    portfolio_name=portfolio.name,
    account_name=portfolio.account_name,  # ✅ NEW
    account_type=portfolio.account_type,  # ✅ NEW
    is_active=portfolio.is_active,  # ✅ NEW
    equity_balance=float(portfolio.equity_balance),
    ...
)
```

**Save changes:**
```bash
git add backend/app/api/v1/onboarding.py
```

**Validation:**
```bash
# Check schema updated
grep "account_name: str" backend/app/api/v1/onboarding.py
grep "account_type: str" backend/app/api/v1/onboarding.py
grep "is_active: bool" backend/app/api/v1/onboarding.py

# Check response includes new fields
grep "account_name=portfolio.account_name" backend/app/api/v1/onboarding.py
```

✅ **Checkpoint 2.2:** onboarding.py updated

---

### Step 2.3: Test Import Compatibility

**Before updating tests, verify code changes compile:**

**Command:**
```bash
cd backend

# Test critical imports
.venv/Scripts/python.exe -c "from app.services.onboarding_service import onboarding_service; print('✅ Onboarding service imports')"

.venv/Scripts/python.exe -c "from app.api.v1.onboarding import router; print('✅ Onboarding router imports')"

.venv/Scripts/python.exe -c "from app.models.users import User, Portfolio; print('✅ Models import')"
```

**Expected output:**
```
✅ Onboarding service imports
✅ Onboarding router imports
✅ Models import
```

**If any import fails:**
- Review the file with error
- Check for syntax errors
- Verify all fields are defined
- Don't proceed until imports work

✅ **Checkpoint 2.3:** Imports working

---

### ✅ Phase 2 Checkpoint

**Before proceeding to Phase 3, confirm:**
- [ ] onboarding_service.py updated (~20 changes)
- [ ] onboarding.py updated (~10 changes)
- [ ] No `user.portfolio` references remain (only `user.portfolios`)
- [ ] Portfolio creation includes account_name, account_type, is_active
- [ ] Response schemas include new fields
- [ ] All critical imports working

**If all confirmed:** Proceed to Phase 3 (Update Tests)
**If any failed:** Review changes, fix issues

---

## Phase 3: Update Tests 🧪

**Objective:** Update test files to expect multi-portfolio schema
**Time:** 2-3 hours
**Checkpoint:** Phase3Complete

### Overview

**Files to update:**
1. `tests/conftest.py` - Test fixtures
2. `tests/integration/test_onboarding_api.py` - API integration tests
3. `tests/e2e/test_onboarding_flow.py` - End-to-end tests
4. `tests/unit/test_csv_parser_service.py` - Unit tests
5. `tests/unit/test_position_import_service.py` - Unit tests

---

### Step 3.1: Update tests/conftest.py

**File:** `backend/tests/conftest.py`

**Changes needed:** Update portfolio fixtures to include new fields

**Find all Portfolio() instantiations:**
```bash
grep -n "Portfolio(" backend/tests/conftest.py
```

**For each Portfolio creation, add new fields:**

**Before:**
```python
portfolio = Portfolio(
    id=uuid4(),
    user_id=user.id,
    name="Test Portfolio",
    description="Test description",
    equity_balance=Decimal("100000"),
)
```

**After:**
```python
portfolio = Portfolio(
    id=uuid4(),
    user_id=user.id,
    name="Test Portfolio",
    account_name="Test Account",  # ✅ ADD
    account_type="taxable",  # ✅ ADD
    is_active=True,  # ✅ ADD
    description="Test description",
    equity_balance=Decimal("100000"),
)
```

**Save changes:**
```bash
git add backend/tests/conftest.py
```

✅ **Checkpoint 3.1:** conftest.py updated

---

### Step 3.2: Update tests/integration/test_onboarding_api.py

**File:** `backend/tests/integration/test_onboarding_api.py`

**Changes needed:** Update assertions to check new fields

**Find all assertions checking portfolio data:**
```bash
grep -n "assert.*portfolio" backend/tests/integration/test_onboarding_api.py
```

**Add assertions for new fields:**

**Example - After this:**
```python
assert response.status_code == 201
assert "portfolio_id" in response_data
```

**Add this:**
```python
assert "account_name" in response_data
assert "account_type" in response_data
assert response_data["account_type"] == "taxable"
assert response_data["is_active"] is True
```

**Save changes:**
```bash
git add backend/tests/integration/test_onboarding_api.py
```

✅ **Checkpoint 3.2:** integration tests updated

---

### Step 3.3: Update tests/e2e/test_onboarding_flow.py

**File:** `backend/tests/e2e/test_onboarding_flow.py`

**Similar changes as Step 3.2:**
- Add assertions for account_name, account_type, is_active
- Update any user.portfolio references to user.portfolios

**Save changes:**
```bash
git add backend/tests/e2e/test_onboarding_flow.py
```

✅ **Checkpoint 3.3:** e2e tests updated

---

### Step 3.4: Update unit tests

**Files:**
- `tests/unit/test_csv_parser_service.py`
- `tests/unit/test_position_import_service.py`

**For each file:**
1. Find Portfolio() instantiations
2. Add account_name, account_type, is_active
3. Update assertions if needed

**Save changes:**
```bash
git add backend/tests/unit/test_csv_parser_service.py
git add backend/tests/unit/test_position_import_service.py
```

✅ **Checkpoint 3.4:** unit tests updated

---

### Step 3.5: Run Unit Tests (Quick Check)

**Command:**
```bash
cd backend

# Run a quick unit test to verify syntax
.venv/Scripts/python.exe -m pytest tests/unit/test_invite_code_service.py -v
```

**Expected:**
- Tests run (pass or fail is OK for now)
- No import errors
- No syntax errors

**If import/syntax errors:** Fix them before proceeding.

✅ **Checkpoint 3.5:** Tests compile

---

### ✅ Phase 3 Checkpoint

**Before proceeding to Phase 4, confirm:**
- [ ] conftest.py updated (portfolio fixtures)
- [ ] integration tests updated (assertions)
- [ ] e2e tests updated (assertions)
- [ ] unit tests updated (fixtures)
- [ ] Tests compile without syntax errors

**If all confirmed:** Proceed to Phase 4 (Integration Testing)
**If any failed:** Review changes, fix issues

---

## Phase 4: Integration Testing 🧪

**Objective:** Verify merge works end-to-end
**Time:** 2-4 hours
**Checkpoint:** Phase4Complete

### Step 4.1: Run Import Tests

**Command:**
```bash
cd backend

# Test all critical imports
.venv/Scripts/python.exe -c "
from app.models.users import User, Portfolio
from app.services.onboarding_service import onboarding_service
from app.services.portfolio_aggregation_service import PortfolioAggregationService
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.portfolios import router as portfolios_router
print('✅ All critical imports successful')
"
```

**Expected:**
```
✅ All critical imports successful
```

**If fails:** Review the failing import, fix issues.

✅ **Checkpoint 4.1:** Imports working

---

### Step 4.2: Start Backend Server

**Command:**
```bash
cd backend
.venv/Scripts/python.exe run.py
```

**Expected output:**
```
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Running startup validation...
INFO:     ✅ Startup validation passed
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Validation:**
- ✅ Server starts without errors
- ✅ Startup validation passes (or logs warnings)
- ✅ No import errors

**If server fails to start:**
- Review error messages
- Check imports
- Verify config.py settings
- Don't proceed until server starts

✅ **Checkpoint 4.2:** Backend server running

---

### Step 4.3: Verify API Endpoints (Browser Test)

**Open browser:** http://localhost:8000/docs

**Verify endpoints present:**

**Onboarding endpoints (4 expected):**
- [ ] POST /api/v1/onboarding/register
- [ ] POST /api/v1/onboarding/create-portfolio
- [ ] GET /api/v1/onboarding/csv-template
- [ ] (possibly one more endpoint)

**Multi-portfolio endpoints (10 expected):**
- [ ] POST /api/v1/portfolios
- [ ] GET /api/v1/portfolios
- [ ] GET /api/v1/portfolios/{id}
- [ ] PUT /api/v1/portfolios/{id}
- [ ] DELETE /api/v1/portfolios/{id}
- [ ] GET /api/v1/analytics/aggregate/overview
- [ ] GET /api/v1/analytics/aggregate/breakdown
- [ ] GET /api/v1/analytics/aggregate/beta
- [ ] GET /api/v1/analytics/aggregate/volatility
- [ ] GET /api/v1/analytics/aggregate/factor-exposures

**If endpoints missing:**
- Check router.py includes both routers
- Check main.py imports router correctly
- Restart server

✅ **Checkpoint 4.3:** All endpoints present

---

### Step 4.4: Test Onboarding Flow (Manual)

**Using Swagger UI at http://localhost:8000/docs:**

#### Test 1: User Registration

**Endpoint:** POST /api/v1/onboarding/register

**Request body:**
```json
{
  "email": "test@example.com",
  "password": "TestPass123!",
  "full_name": "Test User",
  "invite_code": "PRESCOTT-LINNAEAN-COWPERTHWAITE"
}
```

**Expected response:** 201 Created
```json
{
  "user_id": "...",
  "email": "test@example.com",
  "full_name": "Test User",
  "message": "Account created successfully"
}
```

**If fails:**
- Check error message
- Verify invite code matches config
- Check database is accessible

#### Test 2: Login

**Endpoint:** POST /api/v1/auth/login

**Request body:**
```json
{
  "email": "test@example.com",
  "password": "TestPass123!"
}
```

**Expected:** 200 OK with access_token

**Copy the access_token** - you'll need it for next test.

#### Test 3: Check User Has Zero Portfolios (Before Upload)

**Endpoint:** GET /api/v1/portfolios

**Headers:** Authorization: Bearer {access_token}

**Expected:** Empty array `[]`

#### Test 4: Create Portfolio with CSV (Skip for now - would need actual CSV)

**Note:** Full CSV upload test requires a real CSV file. Skip this for now.

✅ **Checkpoint 4.4:** Manual API tests working

---

### Step 4.5: Test Multi-Portfolio Endpoints

**Using the same access_token from Step 4.4:**

#### Test 1: Create Second Portfolio (Multi-Portfolio Endpoint)

**Endpoint:** POST /api/v1/portfolios

**Headers:** Authorization: Bearer {access_token}

**Request body:**
```json
{
  "account_name": "Test Second Account",
  "account_type": "ira",
  "description": "Test IRA account"
}
```

**Expected:** 201 Created with portfolio details

#### Test 2: List All Portfolios

**Endpoint:** GET /api/v1/portfolios

**Headers:** Authorization: Bearer {access_token}

**Expected:** Array with portfolios (could be 1 or more)

#### Test 3: Get Aggregate Analytics

**Endpoint:** GET /api/v1/analytics/aggregate/overview

**Headers:** Authorization: Bearer {access_token}

**Expected:** Aggregate metrics (might be empty if no positions)

✅ **Checkpoint 4.5:** Multi-portfolio endpoints working

---

### Step 4.6: Run Unit Tests

**Command:**
```bash
cd backend

# Run onboarding unit tests
.venv/Scripts/python.exe -m pytest tests/unit/test_invite_code_service.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_csv_parser_service.py -v
.venv/Scripts/python.exe -m pytest tests/unit/test_uuid_strategy.py -v
```

**Expected:**
- Most tests pass
- Some failures are OK (need data that doesn't exist yet)
- No import errors
- No syntax errors

**Document results:**
```
test_invite_code_service.py: _____ passed, _____ failed
test_csv_parser_service.py: _____ passed, _____ failed
test_uuid_strategy.py: _____ passed, _____ failed
```

✅ **Checkpoint 4.6:** Unit tests run

---

### Step 4.7: Test Backward Compatibility (Existing Demo Users)

**Verify existing demo users still work:**

#### Test 1: Login as Demo User

**Endpoint:** POST /api/v1/auth/login

**Request:**
```json
{
  "email": "demo_hnw@sigmasight.com",
  "password": "demo12345"
}
```

**Expected:** 200 OK with access_token

#### Test 2: Get Demo User Portfolios

**Endpoint:** GET /api/v1/portfolios

**Headers:** Authorization: Bearer {demo_access_token}

**Expected:** Array with 1 portfolio (demo user's portfolio)

**Check response:**
```json
[
  {
    "id": "...",
    "name": "...",
    "account_name": "...",  // ← Should exist (from migration)
    "account_type": "taxable",  // ← Should exist
    "is_active": true  // ← Should exist
  }
]
```

**If demo user broken:** STOP - backward compatibility critical. Review migration.

✅ **Checkpoint 4.7:** Backward compatibility verified

---

### ✅ Phase 4 Checkpoint

**Before proceeding to Phase 5, confirm:**
- [ ] All imports working
- [ ] Backend server starts successfully
- [ ] Startup validation passes
- [ ] Both endpoint groups visible in /docs
- [ ] Onboarding registration works
- [ ] Multi-portfolio creation works
- [ ] Unit tests run (most passing)
- [ ] Existing demo users still work

**If all confirmed:** Proceed to Phase 5 (Commit & Documentation)
**If critical issues:** STOP and fix before committing

---

## Phase 5: Commit & Documentation 📝

**Objective:** Commit the merge and update documentation
**Time:** 1-2 hours
**Checkpoint:** Phase5Complete

### Step 5.1: Review All Changes

**Command:**
```bash
git status
```

**Expected:**
- Still in "merging" state
- Many files to be committed
- No untracked critical files

**Review diff:**
```bash
git diff --cached --stat
```

**Expected:** ~20k lines added (onboarding system)

---

### Step 5.2: Commit the Merge

**Command:**
```bash
git commit -m "Merge FrontendLocal-Onboarding into UIRefactor with multi-portfolio compatibility

BREAKING CHANGES:
- Onboarding system now creates portfolios with multi-portfolio schema
- Portfolio model includes account_name, account_type, is_active fields
- User → Portfolio relationship is now one-to-many (user.portfolios)

NEW FEATURES:
- User registration with invite code (POST /api/v1/onboarding/register)
- Portfolio creation with CSV import (POST /api/v1/onboarding/create-portfolio)
- CSV template download (GET /api/v1/onboarding/csv-template)
- 8 new service modules for onboarding pipeline
- Comprehensive error handling framework (OnboardingException)
- Startup validation for system prerequisites
- 11 test files (e2e, integration, unit)

CODE ADAPTATIONS:
- Updated onboarding_service.py: user.portfolio → user.portfolios[0]
- Updated Portfolio creation to include account_name, account_type, is_active
- Added OnboardingException handler to main.py
- Added /health/prerequisites endpoint
- Added startup validation event
- Added BETA_INVITE_CODE and DETERMINISTIC_UUIDS to config.py
- Updated all test fixtures and assertions

COMPATIBILITY:
- Multi-portfolio endpoints preserved (POST/GET /api/v1/portfolios)
- Aggregate analytics endpoints working (GET /api/v1/analytics/aggregate/*)
- Backward compatible with existing demo users (1 portfolio = identity)
- Onboarding creates FIRST portfolio with account_type='taxable'
- Users can add additional portfolios via POST /api/v1/portfolios

TESTING:
- All critical imports working
- Backend server starts successfully
- Onboarding registration tested manually
- Multi-portfolio creation tested manually
- Existing demo users verified working
- Unit tests updated for multi-portfolio schema

MIGRATION:
- Uses existing 9b0768a49ad8 multi-portfolio migration
- No new migrations required

FILES CHANGED:
- Modified: backend/app/models/users.py (kept multi-portfolio schema)
- Modified: backend/app/api/v1/router.py (registered both routers)
- Modified: backend/app/main.py (added exception handlers, startup validation)
- Modified: backend/app/config.py (added onboarding settings)
- Modified: backend/CLAUDE.md (kept UIRefactor version)
- New: 40+ files (services, APIs, tests, docs)
- Updated: All test files for multi-portfolio assertions

DOCUMENTATION:
- backend/_docs/requirements/USER_PORTFOLIO_ONBOARDING_DESIGN.md (2544 lines)
- backend/_docs/ONBOARDING_GUIDE.md (493 lines)
- frontend/_docs/ONBOARDING_FLOW_PRD.md (1863 lines)
- MERGE_ONBOARDING_PLAN.md (16000 lines)
- MERGE_CONFLICTS_DETAILED_ANALYSIS.md (8000 lines)
- MERGE_EXECUTION_GUIDE.md (this document)

Co-authored-by: Claude (AI Assistant) <noreply@anthropic.com>
"
```

**Validation:**
```bash
git log -1 --stat
# Should show the merge commit with all changes
```

✅ **Checkpoint 5.1:** Merge committed

---

### Step 5.3: Tag the Merge

**Command:**
```bash
git tag onboarding-merge-complete-$(date +%Y%m%d-%H%M%S)
git tag -l | tail -1
```

**Record tag:** _________________

✅ **Checkpoint 5.2:** Merge tagged

---

### Step 5.4: Push to Remote

**Command:**
```bash
git push origin test-merge/onboarding-multi-portfolio
git push origin --tags
```

**Validation:**
- ✅ Branch pushed successfully
- ✅ Tags pushed successfully
- ✅ Visible on GitHub/remote

✅ **Checkpoint 5.3:** Changes backed up to remote

---

### Step 5.5: Create Merge Summary Document

**Create:** `ONBOARDING_MERGE_SUMMARY.md`

**Content:**
```markdown
# Onboarding Merge Summary

**Date:** [DATE]
**Branches:** FrontendLocal-Onboarding → test-merge/onboarding-multi-portfolio
**Status:** ✅ Complete
**Merge Commit:** [git rev-parse HEAD]
**Tag:** [from Step 5.2]

## Summary

Successfully merged onboarding system into multi-portfolio architecture.

## Changes

- 5 conflicts resolved
- 40+ new files added
- ~20k lines of code
- 10 files adapted for multi-portfolio

## Testing Results

- [ ] All imports working
- [ ] Backend server starts
- [ ] Onboarding endpoints present
- [ ] Multi-portfolio endpoints present
- [ ] Manual registration test: PASS/FAIL
- [ ] Demo user compatibility: PASS/FAIL
- [ ] Unit tests: _____ passed, _____ failed

## Known Issues

[Document any issues found during testing]

## Next Steps

1. Merge test branch to UIRefactor (if testing passed)
2. Build frontend for onboarding
3. Test with real users
4. Deploy to production

## Rollback Plan

If issues found:
```bash
git checkout UIRefactor
git reset --hard [pre-merge commit]
# Or: git revert [merge commit]
```

Safety tag: [from Phase 0]
```

**Save document:**
```bash
git add ONBOARDING_MERGE_SUMMARY.md
git commit -m "docs: Add onboarding merge summary"
git push origin test-merge/onboarding-multi-portfolio
```

✅ **Checkpoint 5.4:** Documentation complete

---

### ✅ Phase 5 Checkpoint

**Before declaring merge complete, confirm:**
- [ ] Merge committed with comprehensive message
- [ ] Merge tagged
- [ ] Changes pushed to remote
- [ ] Summary document created

**If all confirmed:** Merge is COMPLETE on test branch!

---

## Phase 6: Merge to UIRefactor (Final) 🎉

**Objective:** Merge test branch back to UIRefactor
**Time:** 30 minutes
**Checkpoint:** Phase6Complete

**⚠️ ONLY DO THIS IF Phase 4 testing was successful!**

### Step 6.1: Review Test Results

**Before merging to UIRefactor, ensure:**
- [ ] All critical functionality working
- [ ] No blocking bugs found
- [ ] Existing demo users work
- [ ] New onboarding flow works
- [ ] Multi-portfolio endpoints work

**If ANY issues:** Document them, fix them, don't merge yet.

---

### Step 6.2: Switch to UIRefactor

**Command:**
```bash
git checkout UIRefactor
git log -1 --oneline
```

**Validation:**
- ✅ On UIRefactor branch
- ✅ At the commit before merge started

---

### Step 6.3: Merge Test Branch (Fast-Forward)

**Command:**
```bash
git merge test-merge/onboarding-multi-portfolio --ff-only
```

**Expected:**
```
Updating [old_commit]..[new_commit]
Fast-forward
 [list of files changed]
```

**Validation:**
- ✅ Fast-forward merge (no new merge commit)
- ✅ UIRefactor now has all onboarding changes

---

### Step 6.4: Verify UIRefactor State

**Commands:**
```bash
git log -1 --stat
git diff origin/UIRefactor --stat
```

**Validation:**
- ✅ UIRefactor has merge commit
- ✅ All changes present

---

### Step 6.5: Push UIRefactor to Remote

**Command:**
```bash
git push origin UIRefactor
```

**Validation:**
- ✅ Pushed successfully
- ✅ Visible on GitHub

---

### Step 6.6: Clean Up Test Branch (Optional)

**Command:**
```bash
# Delete local test branch
git branch -d test-merge/onboarding-multi-portfolio

# Delete remote test branch (optional - you might want to keep it)
# git push origin --delete test-merge/onboarding-multi-portfolio
```

---

### ✅ Phase 6 Complete!

**Merge is now on UIRefactor branch! 🎉**

**Final validation:**
```bash
git checkout UIRefactor
git log --oneline -10
# Should show merge commit at top

git branch -a
# UIRefactor should be up to date
```

---

## 🎯 Success Criteria Summary

### ✅ All Phases Complete When:

- [x] Phase 0: Preparation complete (safety tag created, test branch exists)
- [x] Phase 1: All 5 conflicts resolved
- [x] Phase 2: Onboarding code adapted for multi-portfolio
- [x] Phase 3: Tests updated
- [x] Phase 4: Integration testing passed
- [x] Phase 5: Merge committed and documented
- [x] Phase 6: Merged to UIRefactor (if testing successful)

### ✅ System Working When:

- [ ] Backend starts without errors
- [ ] User can register with invite code
- [ ] User can create portfolio with CSV
- [ ] User can create additional portfolios
- [ ] Aggregate analytics work
- [ ] Existing demo users still work
- [ ] No import errors
- [ ] No syntax errors

---

## 🚨 Rollback Instructions

### If Issues Found During Phase 1-4 (Before Final Commit)

**Command:**
```bash
# Abort merge
git merge --abort

# Return to starting point
git checkout UIRefactor
```

---

### If Issues Found After Phase 5 (After Commit, Before UIRefactor Merge)

**Command:**
```bash
# On test branch
git reset --hard pre-onboarding-merge-[timestamp]

# Or reset to specific commit
git log --oneline
git reset --hard [commit_before_merge]
```

---

### If Issues Found After Phase 6 (After Merged to UIRefactor)

**Option 1: Revert the merge commit**
```bash
git checkout UIRefactor
git log --oneline -5
# Find the merge commit
git revert -m 1 [merge_commit_hash]
git push origin UIRefactor
```

**Option 2: Reset to before merge (if no one else pulled)**
```bash
git checkout UIRefactor
git reset --hard [commit_before_merge]
git push origin UIRefactor --force  # ⚠️ DANGEROUS - only if no one pulled
```

---

## 📋 Quick Reference Checklist

**Use this for quick status checks:**

### Pre-Merge Status
- [ ] On test-merge/onboarding-multi-portfolio branch
- [ ] Safety tag created: __________
- [ ] Test branch pushed to remote

### Conflict Resolution Status
- [ ] models/users.py resolved (UIRefactor version)
- [ ] router.py resolved (both routers)
- [ ] main.py resolved (added handlers)
- [ ] config.py resolved (added settings)
- [ ] CLAUDE.md resolved (UIRefactor version)

### Code Adaptation Status
- [ ] onboarding_service.py updated (user.portfolios)
- [ ] onboarding.py updated (response schemas)
- [ ] conftest.py updated (fixtures)
- [ ] integration tests updated (assertions)
- [ ] e2e tests updated (assertions)
- [ ] unit tests updated (fixtures)

### Testing Status
- [ ] Imports working
- [ ] Backend starts
- [ ] /docs shows all endpoints
- [ ] Onboarding registration works
- [ ] Multi-portfolio creation works
- [ ] Demo users work
- [ ] Unit tests run

### Commit Status
- [ ] Merge committed
- [ ] Merge tagged: __________
- [ ] Changes pushed to remote
- [ ] Summary doc created

### Final Merge Status
- [ ] Test results reviewed
- [ ] UIRefactor updated
- [ ] UIRefactor pushed

---

## 📞 Getting Help

**If stuck at any checkpoint:**

1. **Review the detailed docs:**
   - `MERGE_CONFLICTS_DETAILED_ANALYSIS.md` for conflict resolution
   - `MERGE_ONBOARDING_PLAN.md` for overall strategy

2. **Check validation steps:**
   - Each step has validation commands
   - Run them to diagnose issues

3. **Document the issue:**
   - What phase/step?
   - What command failed?
   - What error message?
   - What validation failed?

4. **Ask for help:**
   - Provide checkpoint you're at
   - Provide error details
   - Provide relevant command output

---

**Document Version:** 1.0
**Created:** 2025-11-01
**Last Updated:** 2025-11-01
**Status:** Ready for execution
