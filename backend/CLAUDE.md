# Claude AI Agent Instructions - SigmaSight Backend

**Purpose**: Complete instructions and reference guide for AI coding agents working on the SigmaSight backend codebase.

**Target**: Claude Code, Claude 3.5 Sonnet, Cursor, Windsurf, and other AI coding agents

**Last Updated**: 2025-10-29

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
   - Set up cloud services (Railway, AWS, GCP, monitoring)
   - Configure production deployments

### Things Requiring EXPLICIT Permission
**NEVER DO WITHOUT APPROVAL:**

1. **Database Schema Changes**
   - ❌ Modifying existing tables (users, portfolios, positions, etc.)
   - ❌ Changing column types, constraints, or relationships
   - ❌ Deleting or renaming existing columns
   - ❌ Creating ANY database changes without Alembic migrations
   - ✅ OK: Adding indexes to existing tables
   - ✅ OK: Creating new tables via Alembic migrations with approval

2. **API Contract Changes**
   - ❌ Changing existing endpoint paths or HTTP methods
   - ❌ Modifying existing Pydantic models in app/schemas/
   - ❌ Removing or renaming response fields
   - ❌ Breaking changes to authentication flow
   - ✅ OK: Adding optional query parameters with defaults
   - ✅ OK: Adding new endpoints that don't conflict

3. **Batch Orchestrator Changes**
   - ❌ Modifying batch_orchestrator phase sequence
   - ❌ Changing calculation engine execution order
   - ❌ Altering graceful degradation logic
   - ❌ Modifying market data provider priority (YFinance-first)
   - ✅ OK: Adding logging or monitoring within existing flows

4. **Authentication & Security**
   - ❌ Modifying JWT token generation or validation logic
   - ❌ Changing password hashing algorithms
   - ❌ Altering CORS policies or security headers
   - ❌ Modifying rate limiting rules
   - ✅ OK: Using existing auth dependencies as documented

5. **Configuration & Environment**
   - ❌ Changing production configuration values
   - ❌ Modifying logging levels for production
   - ❌ Altering cache TTLs without load testing
   - ❌ Changing external API rate limits
   - ✅ OK: Adding new configuration with sensible defaults

6. **External Service Integration**
   - ❌ Adding new paid API dependencies
   - ❌ Changing market data providers (YFinance primary, FMP secondary)
   - ❌ Modifying usage patterns that increase API costs
   - ✅ OK: Using already configured services

7. **Data Operations**
   - ❌ Deleting any user data or portfolios
   - ❌ Running destructive migrations
   - ❌ Modifying data retention policies
   - ❌ Changing backup/recovery procedures
   - ✅ OK: Reading data through existing patterns

8. **Performance-Critical Changes**
   - ❌ Modifying database connection pooling
   - ❌ Changing async/await patterns in hot paths
   - ❌ Altering caching strategies
   - ❌ Modifying batch processing orchestration timing
   - ✅ OK: Following existing async patterns

9. **Feature Flags**
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

2. **[_docs/reference/API_REFERENCE_V1.4.6.md](_docs/reference/API_REFERENCE_V1.4.6.md)** - Complete API endpoint documentation (57 endpoints)
3. **[_archive/todos/](_archive/todos/)** - Historical TODO files (Phases 1-3 complete, archived)
4. **[README.md](README.md)** - Setup instructions and environment
5. **[_docs/requirements/](docs/requirements/)** - Product requirements and specifications

### **Specialized References**
- **Batch Processing**: See Part II Section on Batch Orchestrator v3
- **Position Tagging**: See Part II Section on Tagging System (October 2, 2025)
- **Railway Deployment**: See `scripts/railway/README.md` for audit scripts
- **Database Schema**: See Part II for relationship maps and query patterns

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
- Check `_docs/reference/API_REFERENCE_V1.4.6.md` for current API status
- Use existing demo data (3 portfolios, 63 positions) for testing
- Implement graceful degradation for missing calculation data
- Follow async patterns consistently (avoid sync/async mixing)
- Use the diagnostic commands from Part II
- **ALWAYS use Alembic migrations** for database changes
- Use `batch_orchestrator`, NOT v2
- Follow YFinance-first market data priority

### **❌ DON'T:**
- Explore file structure without consulting Part II reference
- Create new test data when demo data exists
- Mix async/sync database operations (causes greenlet errors)
- Reference strategy endpoints (removed October 2025)
- Use batch_orchestrator_v2 (deprecated, use v3)
- Assume FMP is primary market data provider (YFinance is primary)
- **Add feature flags without explicit approval**
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

**Batch Orchestrator:**
```python
# Use v3, NOT v2
from app.batch.batch_orchestrator import batch_orchestrator

# Run batch processing
await batch_orchestrator.run_batch_sequence()
```

### **Task Management**
- Use TODO tools frequently for complex tasks (3+ steps)
- Mark TODO items complete immediately after finishing
- Document any new issues discovered
- Cross-reference related work

---

## 📝 Communication Style

### **Progress Updates**
- Use clear completion markers: ✅ **COMPLETED**, ⚠️ **PARTIAL**, ❌ **FAILED**
- Include specific results: "Found 8 portfolios, 11 Greeks records"
- Document issues with references: "See Part II Section X for resolution"

### **Problem Reporting**
- Be specific about error messages and context
- Reference existing documentation when applicable
- Suggest systematic solutions rather than quick fixes
- Update documentation with new patterns discovered

---

## 🎯 Success Metrics

**Good AI Agent Session:**
- Minimal time spent on discovery (used Part II Codebase Reference)
- Clear progress tracking
- Graceful handling of known issues
- Updated documentation for future agents
- Working code that follows established patterns
- Uses batch_orchestrator
- Respects YFinance-first market data priority

---

# PART II: CODEBASE REFERENCE

## 🏗️ Architecture Quick Reference

### **Directory Structure & Purpose**
```
backend/
├── app/
│   ├── models/           - Database models (SQLAlchemy ORM)
│   │   ├── users.py      - User, Portfolio models
│   │   ├── positions.py  - Position, PositionType enums
│   │   ├── market_data.py - PositionGreeks, PositionFactorExposure
│   │   ├── correlations.py - CorrelationCalculation
│   │   ├── snapshots.py  - PortfolioSnapshot
│   │   ├── tags_v2.py    - TagV2 (tagging system - October 2, 2025)
│   │   ├── position_tags.py - PositionTag (M:N junction - October 2, 2025)
│   │   ├── target_prices.py - TargetPrice (Phase 8)
│   │   └── history.py    - Historical data models
│   │
│   ├── batch/            - Batch processing framework
│   │   ├── batch_orchestrator.py - Main orchestration (3 phases + Phase 2.5) ⭐ USE THIS
│   │   ├── batch_orchestrator_v2.py - DEPRECATED, DO NOT USE
│   │   └── scheduler_config.py   - APScheduler configuration
│   │
│   ├── calculations/     - Core calculation engines (8 engines)
│   │   ├── greeks.py     - Options Greeks (mibian library)
│   │   ├── factors.py    - Factor exposure analysis
│   │   ├── correlations.py - Position correlations
│   │   ├── market_risk.py - Market risk scenarios
│   │   ├── portfolio.py  - Portfolio aggregations
│   │   └── volatility.py - Volatility calculations
│   │
│   ├── api/v1/           - FastAPI REST endpoints (57 total)
│   │   ├── auth.py       - Authentication (5 endpoints)
│   │   ├── data_endpoints/ - Data APIs (10 endpoints) ✅
│   │   ├── analytics/    - Analytics endpoints (7 endpoints) ✅
│   │   ├── tags.py       - Tag management (7 endpoints - Oct 2, 2025) ✅
│   │   ├── position_tags.py - Position tagging (5 endpoints - Oct 2, 2025) ✅
│   │   ├── target_prices.py - Target price management (10 endpoints - Phase 8) ✅
│   │   ├── chat/         - Chat endpoints (6 endpoints, SSE streaming) ✅
│   │   ├── admin_batch.py - Batch admin (7 endpoints - Oct 6, 2025) ✅
│   │   └── router.py     - Main API router
│   │
│   ├── agent/            - AI Agent system (OpenAI Responses API)
│   │   ├── services/     - OpenAI Responses API service and tool handlers
│   │   ├── models/       - Conversation and message models
│   │   └── schemas/      - Agent-specific Pydantic schemas
│   │
│   ├── services/         - Business logic services
│   │   ├── market_data_service.py - Market data fetching (YFinance primary)
│   │   ├── tagging_service.py - Tag operations
│   │   └── portfolio_service.py - Portfolio operations
│   │
│   ├── core/             - Core utilities
│   │   ├── config.py     - Settings and configuration
│   │   ├── logging.py    - Logging setup
│   │   ├── auth.py       - JWT authentication
│   │   └── dependencies.py - FastAPI dependencies
│   │
│   ├── db/               - Database utilities
│   │   └── seed_demo_portfolios.py - Demo data creation
│   │
│   └── database.py       - Database connection utilities
│
├── scripts/              - Utility scripts
│   ├── database/         - Database scripts
│   │   └── reset_and_seed.py - Main seeding script (AUTHORITATIVE)
│   ├── railway/          - Railway deployment & audit scripts
│   │   ├── audit_railway_data.py - Portfolio/position audit
│   │   ├── audit_railway_market_data.py - Market data audit
│   │   ├── audit_railway_analytics.py - Analytics audit (client-friendly)
│   │   └── README.md     - Audit script documentation
│   ├── verification/     - Verification and diagnostic scripts
│   └── monitoring/       - Monitoring scripts
│
├── _docs/                - Documentation
│   ├── reference/        - API reference documentation
│   │   └── API_REFERENCE_V1.4.6.md - Complete API endpoint reference (57 endpoints)
│   └── requirements/     - Product requirements and specifications
│
├── _archive/             - Archived files
│   └── todos/            - Historical TODO files (Phases 1-3 complete)
│
├── alembic/              - Database migrations
├── docker-compose.yml    - PostgreSQL database
├── pyproject.toml        - Dependencies (mibian, not py_vollib)
└── .env                  - Environment variables
```

### **Key Configuration Files**
```
docker-compose.yml    - PostgreSQL database (Redis removed)
pyproject.toml       - Dependencies (mibian, not py_vollib)
.env                 - Environment variables (no REDIS_URL)
alembic/             - Database migrations
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

# Target price models (Phase 8)
from app.models.target_prices import TargetPrice

# Calculation result models
from app.models.market_data import PositionGreeks, PositionFactorExposure
from app.models.correlations import CorrelationCalculation
from app.models.snapshots import PortfolioSnapshot

# Database utilities
from app.database import get_async_session, AsyncSessionLocal
```

### **Batch Processing**
```python
# Main batch orchestrator (USE V3, NOT V2)
from app.batch.batch_orchestrator import batch_orchestrator

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

### **Services**
```python
# Market data (YFinance primary, FMP secondary)
from app.services.market_data_service import get_market_data, get_historical_prices

# Tagging service
from app.services.tagging_service import create_tag, tag_position
```

---

## 📊 API Endpoints Overview

### **Implementation Status**
**59 endpoints** implemented across 9 categories (~100% Phase 3 complete, production-ready)

### **Endpoint Categories**
1. **Authentication** (5 endpoints) - JWT token management
2. **Data** (10 endpoints) - Raw data access (portfolio, positions, market data)
3. **Analytics** (9 endpoints) - Portfolio analytics and risk metrics (includes 3 NEW Risk Metrics endpoints - Oct 17, 2025)
4. **Chat** (6 endpoints) - AI chat with SSE streaming (OpenAI Responses API)
5. **Target Prices** (10 endpoints) - Target price management (Phase 8)
6. **Position Tagging** (12 endpoints) - Tag management + position tagging (October 2, 2025)
7. **Admin Batch** (6 endpoints) - Batch processing admin (October 6, 2025)
8. **Company Profiles** (1 endpoint) - Company profile sync (automatic via Railway cron)

**Complete Documentation**: See `frontend/_docs/1. API_AND_DATABASE_SUMMARY.md` (most current, updated Oct 7, 2025)

### **Breaking Changes**
- **Strategy Endpoints Removed** (October 2025): All `/api/v1/strategies/*` endpoints deprecated
- Migration to position-level tagging only via `/api/v1/tags` and `/api/v1/position-tags`

---

## 🤖 AI Agent Architecture (OpenAI Responses API)

### **Critical: OpenAI Responses API (NOT Chat Completions)**
The SigmaSight agent system uses **OpenAI Responses API** for all AI interactions, not the Chat Completions API.

**Key Implementation Files:**
- `app/agent/services/openai_service.py` - Main OpenAI Responses API integration
- `app/api/v1/chat/send.py` - SSE streaming endpoint using Responses API
- `app/config.py` - Responses API configuration (lines 52-61)

**Responses API Pattern:**
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
                │                ├─→ (N) TagV2 (M:N via position_tags - Oct 2, 2025)
                │                └─→ (N) TargetPrice (Phase 8)
                │
                ├─→ (N) PortfolioSnapshot
                └─→ (N) CorrelationCalculation
```

### **Common Query Patterns**
```python
# Get portfolios for user
portfolios = await db.execute(
    select(Portfolio).where(Portfolio.user_id == user_id)
)

# Get positions for portfolio with tags
positions = await db.execute(
    select(Position)
    .options(joinedload(Position.tags))
    .where(Position.portfolio_id == portfolio_id)
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

## ⚙️ Batch Processing System v3

### **Architecture Overview**
**batch_orchestrator** implements 3-phase processing with automatic backfill:

**Phase 1: Market Data Collection**
- 1-year historical price lookback
- YFinance primary, FMP secondary
- Options data from Polygon

**Phase 2: P&L Calculation & Snapshots**
- Portfolio snapshots (trading days only)
- Position P&L calculations
- Historical performance tracking

**Phase 2.5: Position Market Value Updates** (Added October 29, 2025)
- Updates position market values for current prices
- Critical for accurate analytics
- Runs after Phase 2, before Phase 3

**Phase 3: Risk Analytics**
- Portfolio and position betas
- Factor exposures (5 factors)
- Volatility calculations
- Correlation matrices (portfolio + factor)

### **8 Calculation Engines Status**
1. **Portfolio Aggregation** ✅ Working
2. **Position Greeks** ✅ Working (mibian library)
3. **Factor Analysis** ✅ Working (5 factors)
4. **Market Risk Scenarios** ⚠️ Partial (graceful degradation)
5. **Stress Testing** ⚠️ Partial (graceful degradation)
6. **Portfolio Snapshots** ✅ Working
7. **Position Correlations** ✅ Working
8. **Factor Correlations** ✅ Working

### **Batch Execution**
```python
# Main entry point (USE V3)
from app.batch.batch_orchestrator import batch_orchestrator

# Run all portfolios
await batch_orchestrator.run_batch_sequence()

# Individual portfolio
await batch_orchestrator.run_batch_sequence(portfolio_id="uuid-string")

# Manual trigger via API
POST /api/v1/admin/batch/trigger
```

### **Market Data Provider Priority** (Updated October 2025)
1. **YFinance** - Primary provider (historical prices, company data)
2. **FMP** - Secondary provider (backup for YFinance failures)
3. **Polygon** - Options data only
4. **FRED** - Economic data (treasury rates, macro indicators)

---

## 📊 Demo Data Reference

### **Demo Portfolios (3 Main)**
```python
# Demo user credentials (all use same password: "demo12345")
DEMO_USERS = {
    "demo_individual@sigmasight.com": {
        "portfolio": "Balanced Individual Investor Portfolio",
        "positions": 16,
        "classes": ["PUBLIC", "OPTIONS"]
    },
    "demo_hnw@sigmasight.com": {
        "portfolio": "Sophisticated High Net Worth Portfolio",
        "positions": 17,
        "classes": ["PUBLIC", "OPTIONS", "PRIVATE"]
    },
    "demo_hedgefundstyle@sigmasight.com": {
        "portfolio": "Long/Short Equity Hedge Fund Style Portfolio",
        "positions": 30,
        "classes": ["PUBLIC", "OPTIONS"]  # Includes short positions
    }
}

# Total expected positions: 63 across all 3 portfolios
```

### **Investment Classes**
- **PUBLIC**: Regular equities, ETFs (LONG/SHORT position types)
- **OPTIONS**: Options contracts (LC/LP/SC/SP position types)
- **PRIVATE**: Private/alternative investments

### **Demo Data Commands**
```bash
# Seed all demo data (AUTHORITATIVE script)
python scripts/database/reset_and_seed.py seed

# Full reset and reseed
python scripts/database/reset_and_seed.py reset

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
python scripts/database/reset_and_seed.py seed

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

# OpenAI (required for AI chat)
OPENAI_API_KEY=your_openai_key

# Note: REDIS_URL removed - not used in application
```

---

## 🔍 Quick Diagnostic Commands

### **Test Critical Imports**
```bash
# Test all key imports work (V3, not V2)
uv run python -c "
from app.models.users import Portfolio
from app.models.market_data import PositionGreeks
from app.batch.batch_orchestrator import batch_orchestrator
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
from app.models.positions import Position
from app.models.market_data import PositionGreeks

async def check():
    async with get_async_session() as db:
        portfolios = await db.execute(select(func.count(Portfolio.id)))
        positions = await db.execute(select(func.count(Position.id)))
        greeks = await db.execute(select(func.count(PositionGreeks.id)))
        print(f'Portfolios: {portfolios.scalar()}, Positions: {positions.scalar()}, Greeks: {greeks.scalar()}')

asyncio.run(check())
"
```

### **Test Batch Orchestrator v3**
```bash
# Verify batch orchestrator v3 imports
uv run python -c "
from app.batch.batch_orchestrator import batch_orchestrator
print('✅ Batch orchestrator v3 ready')
print(f'Phases: {batch_orchestrator.get_phase_count()}')
"
```

---

## 🔍 Railway Audit Scripts

### **API-Based Audits (No SSH Required)**

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

# 3. Analytics Audit (Client-Friendly Reports) ⭐
python scripts/railway/audit_railway_analytics.py
# - Tests all 7 /analytics/ endpoints
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
# - Audits snapshots, factor exposures, correlations
# - Shows actual beta values and scenario impacts
# - Saves: railway_calculations_audit_report.txt
```

**Full Documentation**: See `scripts/railway/README.md`

---

## 🚨 Common Issues & Solutions

### **Import Errors**
```python
# Error: "cannot import batch_orchestrator_v2"
# Solution: Use the current batch orchestrator module instead
from app.batch.batch_orchestrator import batch_orchestrator  # ✅ CORRECT
# from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2  # ❌ DEPRECATED

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

### **Market Data Provider Issues**
```python
# Always try YFinance first, then FMP
try:
    data = await yfinance_provider.get_data(symbol)
except Exception as e:
    logger.warning(f"YFinance failed: {e}, trying FMP")
    data = await fmp_provider.get_data(symbol)
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
- **Endpoints**: `/api/v1/tags` for tag management, `/api/v1/position-tags` for tagging

### **Batch Orchestrator Version**
- **Current**: batch_orchestrator (3 phases + Phase 2.5)
- **Deprecated**: batch_orchestrator_v2 (DO NOT USE)
- **Phase 2.5**: Position market value updates (added October 29, 2025)

### **Market Data Priority (Updated October 2025)**
1. **YFinance** - Primary (free, reliable)
2. **FMP** - Secondary (backup, paid)
3. **Polygon** - Options only (paid)
4. **FRED** - Economic data (free)

### **Trading Calendar Behavior**
- **Weekends**: All calculations run using most recent market data
- **Snapshots**: Only created on actual trading days
- **P&L**: Requires two snapshots to compare (skips weekends)

---

# PART III: CURRENT STATUS

## ✅ What's Working
- Database models and relationships (full schema)
- Demo data seeding (3 portfolios, 63 positions)
- 8 batch calculation engines with graceful degradation
- Async database operations with proper patterns
- Greeks calculations (mibian library)
- Factor analysis and correlations
- Position tagging system (October 2, 2025)
- Target price system (Phase 8)
- Admin batch monitoring (October 6, 2025)
- 59 production API endpoints

## 🎯 System Maturity
- **Phases 1-11**: Complete
- **API Development**: 59/59 endpoints implemented (100% Phase 3+, production-ready)
- **Batch Processing**: v3 with 3 phases + Phase 2.5
- **Frontend Integration**: Multi-page app with AI chat and risk metrics
- **Production Ready**: Railway deployment with audit scripts and automatic cron jobs

## 📊 Recent Major Updates
- **October 29, 2025**: Phase 2.5 position market value updates added
- **October 17, 2025**: Risk Metrics Phase 1-2 complete (3 new endpoints: sector-exposure, concentration, volatility with HAR forecasting)
- **October 7, 2025**: Railway cron hardening - removed 4x market data duplication, added critical/non-critical job failure detection
- **October 7, 2025**: Company profile sync integrated into Railway cron workflow (daily automatic sync at 11:30 PM UTC)
- **October 6, 2025**: Admin batch processing endpoints added (6 endpoints)
- **October 4, 2025**: Added company_profiles table with sector, industry, revenue/earnings estimates
- **October 2, 2025**: Position tagging system introduced (12 endpoints)
- **October 2025**: Strategy system removed (breaking change)
- **October 2025**: Market data priority changed to YFinance-first
- **October 2025**: Batch orchestrator migrated from v2 to v3

---

## 💡 Efficiency Tips for AI Agents

1. **Read Part II first** - saves 30-45 minutes of exploration
2. **Use batch_orchestrator** - v2 is deprecated
3. **Follow YFinance-first** - market data provider priority
4. **Check API_REFERENCE_V1.4.6.md** for current endpoint status
5. **Use existing demo data** rather than creating new test data
6. **Implement graceful degradation** for missing calculation data
7. **Use diagnostic commands** to verify environment quickly
8. **Update this file** when discovering new patterns
9. **Avoid strategy endpoints** - system removed October 2025
10. **Reference Railway audit scripts** for deployment verification

---

**Remember**: This is a mature, production-ready codebase with 59 endpoints, comprehensive batch processing, risk metrics, and full frontend integration. Your job is to build on the solid foundation, handle known issues gracefully, use batch_orchestrator, follow YFinance-first market data priority, and document new patterns for future AI agents. Part II is your roadmap - use it!
