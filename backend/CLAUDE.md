# Claude AI Agent Instructions - SigmaSight Backend

> ⚠️ **CRITICAL WARNING (2025-08-26)**: Many API endpoints return MOCK data or TODO stubs.
> See `backend/_docs/reference/API_REFERENCE_V1.4.6.md` for TRUE implementation status.
> Do NOT assume endpoints are functional based on other documentation.

**Purpose**: Complete instructions and reference guide for AI coding agents working on the SigmaSight backend codebase.

**Target**: Claude Code, Claude 3.5 Sonnet, Cursor, Windsurf, and other AI coding agents

**Last Updated**: 2025-10-04

---

# PART I: DEVELOPMENT GUIDELINES

## 🚨 CRITICAL: Autonomous Development Guidelines

### Things Requiring EXPLICIT User Help
**YOU MUST ASK THE USER TO:**
1. **Environment Setup**
   - Add/update API keys in `.env` file (OpenAI, Polygon, FMP, FRED)
   - Launch Docker Desktop application before running PostgreSQL
   - Verify Docker containers are running: `docker-compose up -d`
   - Install system dependencies (PostgreSQL client tools, etc.)

2. **External Services**
   - Obtain API keys from providers
   - Verify API key validity
   - Set up cloud services (AWS, GCP, monitoring)
   - Configure production deployments

### Things Requiring EXPLICIT Permission
**NEVER DO WITHOUT APPROVAL:**

1. **Database Schema Changes**
   - ❌ Modifying existing tables (users, portfolios, positions, etc.)
   - ❌ Changing column types, constraints, or relationships
   - ❌ Deleting or renaming existing columns
   - ❌ Creating ANY database changes without Alembic migrations
   - ✅ OK: Adding indexes to existing tables
   - ✅ OK: Creating new agent_* prefixed tables (Agent project only)

2. **API Contract Changes**
   - ❌ Changing existing endpoint paths or HTTP methods
   - ❌ Modifying existing Pydantic models in app/schemas/
   - ❌ Removing or renaming response fields
   - ❌ Breaking changes to authentication flow
   - ✅ OK: Adding optional query parameters with defaults
   - ✅ OK: Adding new endpoints that don't conflict

3. **Authentication & Security**
   - ❌ Modifying JWT token generation or validation logic
   - ❌ Changing password hashing algorithms
   - ❌ Altering CORS policies or security headers
   - ❌ Modifying rate limiting rules
   - ✅ OK: Using existing auth dependencies as documented

4. **Configuration & Environment**
   - ❌ Changing production configuration values
   - ❌ Modifying logging levels for production
   - ❌ Altering cache TTLs without load testing
   - ❌ Changing external API rate limits
   - ✅ OK: Adding new configuration with sensible defaults

5. **External Service Integration**
   - ❌ Adding new paid API dependencies
   - ❌ Changing market data providers
   - ❌ Modifying usage patterns that increase API costs
   - ✅ OK: Using already configured services

6. **Data Operations**
   - ❌ Deleting any user data or portfolios
   - ❌ Running destructive migrations
   - ❌ Modifying data retention policies
   - ❌ Changing backup/recovery procedures
   - ✅ OK: Reading data through existing patterns

7. **Performance-Critical Changes**
   - ❌ Modifying database connection pooling
   - ❌ Changing async/await patterns in hot paths
   - ❌ Altering caching strategies
   - ❌ Modifying batch processing orchestration
   - ✅ OK: Following existing async patterns

8. **Feature Flags**
   - ❌ Adding feature flags without explicit approval
   - **Note**: We prefer simple, correct implementations over complex toggles

---

## 🎯 Primary References

### **Essential Documentation**
1. **Part II of this file** ⭐ **CODEBASE REFERENCE**
   - Complete architecture and import patterns
   - Database models, relationships, query patterns
   - Common errors and diagnostic commands
   - **Read Part II before exploring the codebase**

2. **[TODO3.md](TODO3.md)** - Current Phase 3.0 API development (active)
3. **[_archive/todos/TODO1.md](_archive/todos/TODO1.md)** - Phase 1 implementation (complete, archived)
4. **[_archive/todos/TODO2.md](_archive/todos/TODO2.md)** - Phase 2 implementation (complete, archived)
5. **[README.md](README.md)** - Setup instructions and environment
6. **[_docs/reference/API_REFERENCE_V1.4.6.md](_docs/reference/API_REFERENCE_V1.4.6.md)** - Complete API endpoint documentation

### **Specialized References**
- **Batch Processing Issues**: See `_archive/todos/TODO1.md` Section 1.6.14 for systematic issue resolution
- **Portfolio Reports**: See `_docs/requirements/PRD_PORTFOLIO_REPORT_SPEC.md` for specifications
- **Database Schema**: See Part II of this file for relationship maps and query patterns

---

## 🤖 Working Style & Preferences

### **Documentation Maintenance** 🔄 **IMPORTANT**
**Please update Part II of this file whenever you discover:**
- New import patterns or module locations
- Changes to database schema or relationships
- New batch processing issues or solutions
- Updated environment setup requirements
- New error patterns and their solutions

**Why**: This prevents future AI agents from re-discovering the same information and maintains institutional knowledge.

### **✅ DO:**
- Read Part II (Codebase Reference) first to understand the architecture
- Check TODO3.md for current work, `_archive/todos/TODO1.md` and `_archive/todos/TODO2.md` for completed phases
- Use existing demo data (3 portfolios, 63 positions) for testing
- Implement graceful degradation for missing calculation data
- Follow async patterns consistently (avoid sync/async mixing)
- Use the diagnostic commands from Part II
- Update completion status in TODO3.md as work progresses
- **ALWAYS use Alembic migrations** for database changes

### **❌ DON'T:**
- Explore file structure without consulting Part II reference
- Create new test data when demo data exists
- Assume tables exist without checking (see stress_test_results issue)
- Mix async/sync database operations (causes greenlet errors)
- Ignore batch processing issues documented in `_archive/todos/TODO1.md` Section 1.6.14
- **Add feature flags without explicit approval** - We prefer simple, correct implementations
- **Create or modify database tables without Alembic migrations**

### **Code Quality Standards**

**Database Operations:**
```python
# Always use async patterns
async with get_async_session() as db:
    result = await db.execute(select(Model).where(...))

# Handle UUID types properly
if isinstance(id, str):
    uuid_obj = UUID(id)
else:
    uuid_obj = id

# ALWAYS use Alembic for schema changes
# Never: db.execute("CREATE TABLE ...")
# Instead: uv run alembic revision --autogenerate -m "description"
```

**Error Handling:**
```python
# Implement graceful degradation
try:
    calculation_data = await get_calculation_data()
except Exception as e:
    logger.warning(f"Calculation data unavailable: {e}")
    calculation_data = None  # Proceed with limited data
```

### **Task Management**
- Use TODO tools frequently for complex tasks (3+ steps)
- Mark TODO items complete immediately after finishing
- Document any new issues discovered following the format in `_archive/todos/TODO1.md`
- Cross-reference related work in TODO files

---

## 📝 Communication Style

### **Progress Updates**
- Use clear completion markers: ✅ **COMPLETED**, ⚠️ **PARTIAL**, ❌ **FAILED**
- Include specific results: "Found 8 portfolios, 11 Greeks records"
- Document issues with references: "See `_archive/todos/TODO1.md` Section 1.6.14 for resolution plan"

### **Problem Reporting**
- Be specific about error messages and context
- Reference existing documentation when applicable
- Suggest systematic solutions rather than quick fixes
- Update documentation with new patterns discovered

---

## 🎯 Success Metrics

**Good AI Agent Session:**
- Minimal time spent on discovery (used Part II Codebase Reference)
- Clear progress tracking in TODO files
- Graceful handling of known issues
- Updated documentation for future agents
- Working code that follows established patterns

---

# PART II: CODEBASE REFERENCE

## 🏗️ Architecture Quick Reference

### **Directory Structure & Purpose**
```
app/
├── models/           - Database models (SQLAlchemy ORM)
│   ├── users.py      - User, Portfolio models
│   ├── positions.py  - Position, Tag, PositionType enums
│   ├── market_data.py - PositionGreeks, PositionFactorExposure, StressTestResult
│   ├── correlations.py - CorrelationCalculation
│   ├── snapshots.py  - PortfolioSnapshot
│   ├── tags_v2.py    - TagV2 (tagging system - October 2, 2025)
│   └── history.py    - Historical data models
├── batch/            - Batch processing framework (8 calculation engines)
│   ├── batch_orchestrator_v2.py - Main orchestration (run_daily_batch_sequence)
│   └── scheduler_config.py   - APScheduler configuration
├── calculations/     - Core calculation engines
│   ├── greeks.py     - Options Greeks (mibian library)
│   ├── factors.py    - Factor exposure analysis
│   ├── correlations.py - Position correlations
│   └── market_risk.py - Market risk scenarios
├── api/v1/           - FastAPI REST endpoints
│   ├── auth.py       - Authentication (login, logout, JWT)
│   ├── data.py       - Raw Data APIs (/data/ namespace) ✅ COMPLETE
│   ├── analytics/    - Analytics endpoints (portfolio metrics)
│   ├── tags.py       - Tag management (October 2, 2025)
│   ├── position_tags.py - Position tagging (October 2, 2025)
│   ├── chat/         - Chat endpoints (SSE streaming with OpenAI Responses API)
│   └── router.py     - Main API router
├── agent/            - AI Agent system (OpenAI Responses API integration)
│   ├── services/     - OpenAI Responses API service and tool handlers
│   ├── models/       - Conversation and message models
│   └── schemas/      - Agent-specific Pydantic schemas
├── core/             - Core utilities (config, logging, auth)
├── db/               - Database utilities and seeding
│   └── seed_demo_portfolios.py - Demo data creation
└── database.py       - Database connection utilities

scripts/              - Utility scripts
├── reset_and_seed.py - Main seeding script (AUTHORITATIVE)
├── railway/          - Railway deployment & audit scripts (see scripts/railway/README.md)
│   ├── audit_railway_data.py - Portfolio/position audit via API
│   ├── audit_railway_market_data.py - Market data audit via API
│   ├── audit_railway_analytics.py - Analytics audit via API (client-friendly)
│   └── audit_railway_calculations_verbose.py - Calculation audit (requires SSH)
├── manual_tests/     - Manual testing scripts
├── verification/     - Verification and diagnostic scripts
└── monitoring/       - Monitoring scripts

_docs/                - Documentation
├── reference/        - API reference documentation
│   └── API_REFERENCE_V1.4.6.md - Complete API endpoint reference
└── requirements/     - Product requirements and specifications
```

### **Key Configuration Files**
```
docker-compose.yml    - PostgreSQL database (Redis removed)
pyproject.toml       - Dependencies (mibian, not py_vollib)
.env                 - Environment variables (no REDIS_URL)
alembic/             - Database migrations
TODO3.md             - Phase 3.0+ API development (CURRENT)
_archive/todos/TODO1.md - Phase 1 implementation (COMPLETE, archived)
_archive/todos/TODO2.md - Phase 2 implementation (COMPLETE, archived)
```

---

## 🔗 Critical Import Patterns

### **Database Models**
```python
# User and Portfolio models
from app.models.users import User, Portfolio

# Position models
from app.models.positions import Position, PositionType

# Tagging models (October 2, 2025)
from app.models.tags_v2 import TagV2
from app.models.position_tags import PositionTag

# Calculation result models
from app.models.market_data import PositionGreeks, PositionFactorExposure, StressTestResult
from app.models.correlations import CorrelationCalculation
from app.models.snapshots import PortfolioSnapshot

# Database utilities
from app.database import get_async_session, AsyncSessionLocal
```

### **Batch Processing**
```python
# Main batch orchestrator
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2

# Individual calculation engines
from app.calculations.greeks import calculate_position_greeks
from app.calculations.factors import calculate_factor_exposures
from app.calculations.portfolio import (
    calculate_portfolio_exposures,
    aggregate_portfolio_greeks,
    calculate_delta_adjusted_exposure,
)
```

### **Core Utilities**
```python
# Configuration
from app.config import settings

# Logging
from app.core.logging import get_logger

# Authentication
from app.core.auth import get_password_hash, verify_password, create_token_response
from app.core.dependencies import get_current_user
```

### **API Endpoints Overview**
See `_docs/reference/API_REFERENCE_V1.4.6.md` for complete endpoint documentation with:
- 5 Authentication endpoints
- 10 Data endpoints
- 7 Analytics endpoints (including diversification-score)
- 6 Chat endpoints (SSE streaming)
- 10 Target Price endpoints
- 10 Tag Management endpoints (October 2, 2025)
- 5 Position Tagging endpoints (October 2, 2025 - PREFERRED)

---

## 🤖 AI Agent Architecture (OpenAI Responses API)

### **Critical: OpenAI Responses API (NOT Chat Completions)**
The SigmaSight agent system uses **OpenAI Responses API** for all AI interactions, not the Chat Completions API. This is a critical architectural distinction.

**Key Implementation Files:**
- `app/agent/services/openai_service.py` - Main OpenAI Responses API integration
- `app/api/v1/chat/send.py` - SSE streaming endpoint using Responses API
- `app/config.py` - Responses API configuration (lines 52-61)

**Responses API vs Chat Completions:**
```python
# ✅ CORRECT - What we use (Responses API)
stream = await self.client.responses.create(
    model=settings.MODEL_DEFAULT,
    messages=messages,
    tools=tools,
    stream=True
)

# ❌ WRONG - Chat Completions API (we do NOT use this)
# stream = await self.client.chat.completions.create(...)
```

---

## 🗄️ Database Schema Quick Reference

### **Core Relationships**
```
User (1) ─→ (N) Portfolio ─→ (N) Position
                │                │
                │                ├─→ (1) PositionGreeks
                │                ├─→ (N) PositionFactorExposure
                │                └─→ (N) TagV2 (M:N via position_tags - Oct 2, 2025)
                │
                ├─→ (N) PortfolioSnapshot
                ├─→ (N) CorrelationCalculation
                └─→ (N) StressTestResult (⚠️ TABLE MISSING - see `_archive/todos/TODO1.md` Section 1.6.14)
```

### **Common Query Patterns**
```python
# Get portfolios for user
portfolios = await db.execute(
    select(Portfolio).where(Portfolio.user_id == user_id)
)

# Get positions for portfolio
positions = await db.execute(
    select(Position).where(Position.portfolio_id == portfolio_id)
)

# Get latest portfolio snapshot
snapshot = await db.execute(
    select(PortfolioSnapshot)
    .where(PortfolioSnapshot.portfolio_id == portfolio_id)
    .order_by(PortfolioSnapshot.calculation_date.desc())
    .limit(1)
)

# Count records for data verification
count = await db.execute(select(func.count(PositionGreeks.id)))
```

### **UUID Handling Pattern**
```python
# Always convert string UUIDs to UUID objects when needed
from uuid import UUID

if isinstance(portfolio_id, str):
    portfolio_uuid = UUID(portfolio_id)
else:
    portfolio_uuid = portfolio_id  # Already UUID object
```

---

## ⚙️ Batch Processing System

### **8 Calculation Engines Status**
1. **Portfolio Aggregation** ✅ Working
2. **Position Greeks** ✅ Working (mibian library)
3. **Factor Analysis** ⚠️ Partial (missing factor ETF data)
4. **Market Risk Scenarios** ⚠️ Partial (async/sync issues)
5. **Stress Testing** ❌ Failed (missing stress_test_results table)
6. **Portfolio Snapshots** ✅ Working
7. **Position Correlations** ✅ Working
8. **Factor Correlations** ✅ Working

### **Batch Execution**
```python
# Main entry point
await batch_orchestrator_v2.run_daily_batch_sequence()  # Runs all 8 engines

# Individual portfolio
await batch_orchestrator_v2.run_daily_batch_sequence(portfolio_id="uuid-string")

# Check if batch orchestrator imports correctly
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
print("Batch orchestrator ready!")
```

### **Known Batch Issues (see `_archive/todos/TODO1.md` Section 1.6.14)**
- **CRITICAL**: Async/sync mixing causes greenlet errors
- **CRITICAL**: Missing stress_test_results table in database
- **HIGH**: Market data gaps (SPY/QQQ options, factor ETFs, BRK.B)
- **HIGH**: Treasury rate data insufficient for IR beta calculations

---

## 📊 Demo Data Reference

### **Demo Portfolios (3 Main)**
```python
# Demo user credentials (all use same password)
DEMO_USERS = [
    "demo_individual@sigmasight.com",     # Balanced Individual Investor
    "demo_hnw@sigmasight.com",           # High Net Worth Investor
    "demo_hedgefundstyle@sigmasight.com" # Hedge Fund Style Investor
]
# Password for all demo users: "demo12345"

# Portfolio names
"Balanced Individual Investor Portfolio"      # 16 positions
"Sophisticated High Net Worth Portfolio"      # 17 positions
"Long/Short Equity Hedge Fund Style Portfolio" # 30 positions (includes options)

# Total expected positions: 63 across all 3 portfolios
```

### **Demo Data Commands**
```bash
# Seed all demo data (AUTHORITATIVE script)
python scripts/reset_and_seed.py seed

# Check demo data status
uv run python -c "
from app.models.users import Portfolio
from app.database import get_async_session
import asyncio
from sqlalchemy import select

async def check():
    async with get_async_session() as db:
        result = await db.execute(select(Portfolio))
        portfolios = result.scalars().all()
        print(f'Found {len(portfolios)} portfolios')

asyncio.run(check())
"
```

---

## 🚀 Quick Start Commands

### **Environment Setup**
```bash
# 1. Start PostgreSQL database
docker-compose up -d

# 2. Apply database migrations
uv run alembic upgrade head

# 3. Seed demo data (3 portfolios, 63 positions)
python scripts/reset_and_seed.py seed

# 4. Verify setup
uv run python scripts/verification/verify_setup.py

# 5. Start backend server
uv run python run.py
```

### **Key Environment Variables (.env)**
```bash
# Database (required)
DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db

# Market Data APIs (required for batch processing)
POLYGON_API_KEY=your_polygon_key
FMP_API_KEY=your_fmp_key
FRED_API_KEY=your_fred_key

# JWT (required)
SECRET_KEY=your_secret_key

# Note: REDIS_URL removed - not used in application
```

---

## 🔍 Quick Diagnostic Commands

### **Test Critical Imports**
```bash
# Test all key imports work
uv run python -c "
from app.models.users import Portfolio
from app.models.market_data import PositionGreeks
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
from app.database import get_async_session
print('✅ All critical imports working')
"
```

### **Check Data Status**
```bash
# Quick data verification
uv run python -c "
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.market_data import PositionGreeks

async def check():
    async with get_async_session() as db:
        portfolios = await db.execute(select(func.count(Portfolio.id)))
        greeks = await db.execute(select(func.count(PositionGreeks.id)))
        print(f'Portfolios: {portfolios.scalar()}, Greeks: {greeks.scalar()}')

asyncio.run(check())
"
```

---

## 🔍 Railway Audit Scripts

### **API-Based Audits (No SSH Required)**

All audit scripts can be run from your local machine against the Railway deployment:

```bash
# 1. Portfolio & Position Data Audit
python scripts/railway/audit_railway_data.py
# - Tests 3 demo portfolios
# - Verifies position data, tags, investment classes
# - Checks data quality metrics
# - Saves: railway_audit_results.json

# 2. Market Data Audit
python scripts/railway/audit_railway_market_data.py
# - Tests company profile data (all 53 fields)
# - Historical price coverage per symbol
# - Market quotes functionality
# - Factor ETF prices
# - Saves: railway_market_data_audit_report.txt

# 3. Analytics Audit (Client-Friendly Reports) ⭐ NEW
python scripts/railway/audit_railway_analytics.py
# - Tests all 6 /analytics/ endpoints
# - Portfolio summary, risk factors, holdings breakdown
# - Correlation matrix, stress testing, diversification
# - Business-friendly formatting (not JSON)
# - Saves: railway_analytics_audit_report.txt (31KB, formatted)
```

### **Database-Direct Audit (Requires Railway SSH)**

```bash
# Calculation Results Audit (verbose with samples)
railway run python scripts/railway/audit_railway_calculations_verbose.py
# - Requires DATABASE_URL from Railway
# - Audits snapshots, factor exposures, correlations, stress tests
# - Shows actual beta values and scenario impacts
# - Saves: railway_calculations_audit_report.txt
```

### **When to Run Audits**

- **After deployment**: Verify all endpoints working
- **After batch processing**: Check calculation completeness
- **Before demo**: Generate client-ready analytics reports
- **During development**: Validate API changes across all portfolios

**Full Documentation**: See `scripts/railway/README.md` for complete audit script reference.

---

## 🚨 Common Issues & Solutions

### **Import Errors**
```python
# Error: "cannot import name X from Y"
# Solution: Check actual model locations in app/models/

# Error: "greenlet_spawn has not been called"
# Solution: Ensure using async session properly
async with get_async_session() as db:
    # All database operations here

# Error: "relation does not exist"
# Solution: Apply migrations
# uv run alembic upgrade head
```

### **UUID Type Handling**
```python
# Always convert string UUIDs when needed
from uuid import UUID
portfolio_uuid = UUID(portfolio_id) if isinstance(portfolio_id, str) else portfolio_id
```

### **Graceful Degradation Pattern**
```python
# Handle missing data gracefully
try:
    result = await db.execute(select(SomeTable))
    data = result.scalars().all()
except Exception as e:
    logger.warning(f"Missing data: {e}")
    data = []  # Proceed with empty data
```

---

## 📐 Design Decisions & Policies

### **Precision & Rounding**
- **Calculations**: Maintain full precision (4dp for Greeks)
- **Database Storage**: Round to match column constraints
- **API Response**: Final rounding at serialization layer

### **Position Tagging System (October 2, 2025)**
- **Preferred**: Direct position-to-tag relationships via `position_tags` junction table
- **Removed (Oct 2025)**: Strategy-based tagging (strategy models/tables dropped)
- **Architecture**: 3-tier separation (position_tags.py, tags.py, tags_v2.py)

### **Trading Calendar Behavior**
- **Weekends**: All calculations run using most recent market data
- **Snapshots**: Only created on actual trading days
- **P&L**: Requires two snapshots to compare (skips weekends)

---

# PART III: CURRENT STATUS

## ✅ What's Working
- Database models and relationships (except stress_test_results table)
- Demo data seeding (3 portfolios, 63 positions)
- 7/8 batch calculation engines (partial data available)
- Async database operations with proper patterns
- Greeks calculations (mibian library)
- Factor analysis and correlations
- Position tagging system (October 2, 2025)

## ⚠️ Known Issues (see `_archive/todos/TODO1.md` Section 1.6.14)
- Batch processing has async/sync mixing issues
- Missing stress_test_results database table
- Market data gaps for certain symbols
- Treasury rate integration problems

## 🎯 Current Focus: Phase 3.0 API Development
- **Status**: 30% complete (12/39 endpoints originally planned)
- **Complete**: Authentication (5), Raw Data (10), Chat (6), Target Prices (10), Tags (10), Position Tagging (5)
- **Analytics**: 7 endpoints complete including diversification-score
- **See**: `TODO3.md` for current work, `_docs/reference/API_REFERENCE_V1.4.6.md` for complete endpoint list

---

## 💡 Efficiency Tips for AI Agents

1. **Read Part II first** - saves 30-45 minutes of exploration
2. **Check `TODO3.md`** for current work and status
3. **Reference `_archive/todos/`** for historical context (TODO1.md, TODO2.md)
4. **Use existing demo data** rather than creating new test data
5. **Implement graceful degradation** for missing calculation data
6. **Use diagnostic commands** to verify environment quickly
7. **Update this file** when discovering new patterns

---

**Remember**: This codebase has substantial infrastructure already built. Your job is to build on the solid foundation, handle known issues gracefully, and document new patterns for future AI agents. Part II is your roadmap - use it!
