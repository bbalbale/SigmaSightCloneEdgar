# SigmaSight Backend - AI Agent Reference Guide

**Purpose**: Comprehensive reference for AI coding agents to quickly understand codebase structure, avoid discovery overhead, and implement features efficiently.

**Target Audience**: AI agents (Claude, ChatGPT, etc.) working on SigmaSight backend development

**Last Updated**: 2025-08-26

---

## 🏗️ Codebase Architecture Quick Reference

### **Directory Structure & Purpose**
```
app/
├── models/           - Database models (SQLAlchemy ORM)
│   ├── users.py      - User, Portfolio models
│   ├── positions.py  - Position, Tag, PositionType enums
│   ├── market_data.py - PositionGreeks, PositionFactorExposure, StressTestResult
│   ├── correlations.py - CorrelationCalculation
│   ├── snapshots.py  - PortfolioSnapshot
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
└── test_*.py         - Testing scripts

_docs/requirements/   - Product requirements and specifications
├── PRD_PORTFOLIO_REPORT_SPEC.md - Portfolio report generator PRD
└── BATCH_TESTING_PRAGMATIC.md  - Batch testing procedures
```

### **Key Configuration Files**
```
docker-compose.yml    - PostgreSQL database (Redis removed)
pyproject.toml       - Dependencies (mibian, not py_vollib)
.env                 - Environment variables (no REDIS_URL)
alembic/             - Database migrations
TODO3.md             - Phase 3.0+ API development (CURRENT)
TODO1.md             - Phase 1 implementation (COMPLETE)
TODO2.md             - Phase 2 implementation (COMPLETE)
```

---

## 🔗 Critical Import Patterns

### **Database Models**
```python
# User and Portfolio models
from app.models.users import User, Portfolio

# Position models  
from app.models.positions import Position, PositionType, Tag, TagType

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

### **API Endpoints (Phase 3.0)**
```python
# Authentication endpoints (✅ COMPLETE)
POST /api/v1/auth/login       # JWT login
POST /api/v1/auth/logout      # Logout
POST /api/v1/auth/refresh     # Token refresh
GET  /api/v1/auth/me          # Current user info

# Raw Data APIs (✅ COMPLETE - optimized for LLM consumption)
GET /api/v1/data/portfolio/{id}/complete      # Full portfolio snapshot
GET /api/v1/data/portfolio/{id}/data-quality  # Data completeness assessment
GET /api/v1/data/positions/details            # Position details with P&L
GET /api/v1/data/prices/historical/{id}       # Historical prices
GET /api/v1/data/prices/quotes                # Real-time quotes
GET /api/v1/data/factors/etf-prices          # Factor ETF prices (mock)

# Analytics APIs (⏳ NOT IMPLEMENTED)
# Management APIs (⏳ NOT IMPLEMENTED)
# Export APIs (⏳ NOT IMPLEMENTED)
# System APIs (⏳ NOT IMPLEMENTED)

# Chat/Agent APIs (✅ COMPLETE - OpenAI Responses API)
POST /api/v1/chat/conversations    # Create conversation
POST /api/v1/chat/send             # SSE streaming chat (OpenAI Responses API)
GET  /api/v1/chat/conversations    # List conversations
```

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

**Configuration:**
```python
# OpenAI Responses API configuration (app/config.py)
MAX_COMPLETION_TOKENS: int = Field(default=4000, description="Max completion tokens for OpenAI Responses API")
OPENAI_API_TIMEOUT: float = Field(default=30.0, description="Timeout for OpenAI API requests")  
MAX_TOOLS_PER_CALL: int = Field(default=10, description="Maximum number of tools per Responses API call")
OPENAI_RATE_LIMIT: int = Field(default=50, description="Rate limit for OpenAI API calls")
```

---

## 🗄️ Database Schema Quick Reference

### **Core Relationships**
```
User (1) ─→ (N) Portfolio ─→ (N) Position
                │                │
                │                ├─→ (1) PositionGreeks
                │                ├─→ (N) PositionFactorExposure  
                │                └─→ (N) Tag (M:N relationship)
                │
                ├─→ (N) PortfolioSnapshot
                ├─→ (N) CorrelationCalculation
                └─→ (N) StressTestResult (⚠️ TABLE MISSING - see TODO1.md 1.6.14)
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

### **Known Batch Issues (see TODO1.md 1.6.14)**
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

# Test specific seeding
uv run python app/db/seed_demo_portfolios.py

# Check demo data status
uv run python -c "
from app.models.users import Portfolio
from app.database import get_async_session
import asyncio

async def check():
    async with get_async_session() as db:
        result = await db.execute(select(Portfolio))
        portfolios = result.scalars().all()
        print(f'Found {len(portfolios)} portfolios')
        
asyncio.run(check())
"
```

---

## 🚀 First 15 Minutes Runbook

### **Quick Start for New Engineers**
```bash
# 1. Start PostgreSQL database
docker-compose up -d

# 2. Apply database migrations
uv run alembic upgrade head

# 3. Seed demo data (3 portfolios, 63 positions)
python scripts/reset_and_seed.py seed

# 4. Run snapshot tests to verify fix
uv run pytest tests/test_snapshot_generation.py -q

# 5. Check database for snapshot records
uv run python -c "
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot

async def check():
    async with get_async_session() as db:
        count = await db.execute(select(func.count(PortfolioSnapshot.id)))
        print(f'PortfolioSnapshot records: {count.scalar()}')
        
asyncio.run(check())
"

# 6. Run batch calculations to populate all engines
uv run python scripts/run_batch_calculations.py

# 7. Verify complete system status
uv run python scripts/verify_demo_portfolios.py
```

### **Manual Snapshot Test**
```python
# Quick smoke test for snapshot generation
import asyncio
from datetime import date
from uuid import UUID
from app.database import get_async_session
from app.calculations.snapshots import create_portfolio_snapshot

async def test_snapshot():
    # Use demo portfolio ID
    portfolio_id = UUID("51134ffd-2f13-49bd-b1f5-0c327e801b69")  # Demo Individual
    
    async with get_async_session() as db:
        result = await create_portfolio_snapshot(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=date.today()
        )
        print(f"Snapshot result: {result}")
        
asyncio.run(test_snapshot())
```

---

## 🔧 Environment & Dependencies

### **Database Setup**
```bash
# Start PostgreSQL (Docker)
docker-compose up -d

# Apply migrations
uv run alembic upgrade head

# Check database connection
uv run python -c "from app.database import get_async_session; print('DB connection ready')"
```

### **Key Environment Variables (.env)**
```bash
# Database (required)
DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db

# Market Data APIs (required for batch processing)
POLYGON_API_KEY=your_polygon_key
FMP_API_KEY=your_fmp_key
TRADEFEEDS_API_KEY=your_tradefeeds_key
FRED_API_KEY=your_fred_key

# JWT (required)
SECRET_KEY=your_secret_key

# Note: REDIS_URL removed - not used in application
```

### **Dependencies Note**
- ✅ **mibian**: Used for Greeks calculations
- ❌ **py_vollib**: Removed due to `_testcapi` import issues
- ❌ **redis**: Removed - unused dependency
- ❌ **celery**: Removed - unused dependency

---

## 🚨 Known Issues & Workarounds

### **Current System Limitations**

**1. Batch Processing Issues** (TODO1.md Section 1.6.14)
- Async/sync architecture mixing → Use pure async patterns
- Missing database tables → Check `alembic upgrade head`
- Market data provider gaps → Implement graceful degradation

**2. Tag Relationships**
- Async relationship access has limitations for existing positions
- Workaround: Create tags during position creation, not after

**3. UUID Serialization**
- Batch jobs have UUID type handling workarounds
- Pattern: Always convert string to UUID when needed

### **Common Error Patterns & Solutions**

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

# Error: "Extra inputs are not permitted" (REDIS_URL)
# Solution: Remove REDIS_URL from .env file
```

### **Working Patterns**
```python
# Graceful degradation for missing data
try:
    result = await db.execute(select(SomeTable))
    data = result.scalars().all()
except Exception as e:
    logger.warning(f"Missing data: {e}")
    data = []  # Proceed with empty data

# Check table existence before querying
from sqlalchemy import inspect
inspector = inspect(db.bind)
if 'table_name' in inspector.get_table_names():
    # Query the table
else:
    # Handle missing table
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

### **Environment Validation**
```bash
# Check environment setup
uv run python -c "
from app.config import settings
print(f'Database: {settings.DATABASE_URL[:50]}...')
print(f'Polygon API: {'SET' if settings.POLYGON_API_KEY else 'MISSING'}')
print('✅ Environment configured')
"
```

---

## 🔌 Data Contracts & Common Patterns

### **Portfolio Aggregation Functions** ⚠️ **CRITICAL**
Functions in `app/calculations/portfolio.py` have strict input requirements:

**Input Contract:**
- **Expected**: `List[Dict]` - a flat list of position dictionaries
- **NOT**: The wrapper dict from `_prepare_position_data()` which returns `{"positions": [...], "warnings": [...]}`
- **Common Error**: Passing the wrapper dict causes pandas "All arrays must be of the same length" error

**Correct Usage:**
```python
# WRONG - causes array length error
position_data = await _prepare_position_data(db, positions, date)
aggregations = calculate_portfolio_exposures(position_data)  # ❌ Passes wrapper dict

# RIGHT - extract the list first
position_data = await _prepare_position_data(db, positions, date)
positions_list = position_data.get("positions", [])  # ✅ Extract list
aggregations = calculate_portfolio_exposures(positions_list)
```

**Required Fields per Position:**
- `exposure`: Decimal (signed: negative for shorts)
- `position_type`: String or Enum (will be normalized)
- `market_value`: Decimal (always positive)
- `greeks`: Dict or None (optional, for options only)

**Output Fields:**
- `gross_exposure`: Sum of absolute exposures (calculated from `exposure` field)
- `net_exposure`: Sum of signed exposures  
- `notional`: Sum of absolute market values (calculated from `market_value` field)
  - Note: Often equals gross_exposure when exposure == market_value, but computed separately
- Note: "notional_exposure" is NOT used in code, only "notional"

### **Position Type Handling** ⚠️ **IMPORTANT**
Position types come in two forms and MUST be normalized:

**The Problem:**
- Database models use `PositionType` enum (e.g., `PositionType.LONG`)
- Constants use string codes (e.g., `"LONG"`, `"SHORT"`)
- Pandas masks require strings, not enums

**The Solution:**
```python
# Always normalize to string before comparisons
position_type_str = getattr(position_type, 'value', position_type)
if position_type_str in OPTIONS_POSITION_TYPES:  # Now comparing strings
    # Handle options
```

**Position Type Constants:**
```python
from app.constants.portfolio import (
    OPTIONS_POSITION_TYPES,  # ["LC", "LP", "SC", "SP"]
    STOCK_POSITION_TYPES,    # ["LONG", "SHORT"]
)
```

### **Greeks Precision Policy** 📊
Different precision at different layers:

**Calculation Layer:**
- Greeks calculated to 4 decimal places (0.0000)
- Used internally for accuracy

**Database Layer:**
- `PortfolioSnapshot` stores as `Numeric(12,2)` - 2 decimal places
- Individual `PositionGreeks` stores as `Numeric(12,4)` - 4 decimal places
- **Rho**: Calculated but NOT stored in `PortfolioSnapshot` (no portfolio_rho field)

**API/Display Layer:**
- Apply final rounding as needed
- Current practice: Round at calculation layer to match DB constraints

**Quantization Points:**
```python
# In calculations (current practice)
delta = delta.quantize(Decimal("0.0000"))  # 4 dp for calculations
# When storing to PortfolioSnapshot
portfolio_delta = delta.quantize(Decimal("0.00"))  # 2 dp for storage
```

### **Field Naming Conventions** 📝
**Canonical Names (use these):**
- `notional` - Total notional exposure (NOT "notional_exposure")
- `gross_exposure` - Sum of absolute exposures
- `net_exposure` - Sum of signed exposures
- `market_value` - Always positive value
- `exposure` - Signed value (negative for shorts)

**Deprecated/Incorrect:**
- ~~`notional_exposure`~~ - Use `notional` instead
- ~~`portfolio_rho`~~ - Calculated but not stored in snapshots

### **Library Dependencies** 📚
**Current (as per pyproject.toml):**
- **mibian** - Used for Greeks calculations ✅
- ~~**py_vollib**~~ - REMOVED due to `_testcapi` import issues ❌

### **Cache Implementation** 🔄
**Status:** Implemented
- `timed_lru_cache` decorator with 60-second TTL in `app/calculations/portfolio.py`
- `clear_portfolio_cache()` function at lines 638-652 in `app/calculations/portfolio.py`
- Clears cache for all aggregation functions via `.cache_clear()` method
- Note: Currently no functions use `@timed_lru_cache` decorator - caching ready but not active

**Usage:**
```python
from app.calculations.portfolio import clear_portfolio_cache
# Clear all portfolio aggregation caches
clear_portfolio_cache()  # Logs: "Cleared all portfolio aggregation caches"
```

### **Market Data Storage** 📊
**Database Table:**
- Model: `app.models.market_data.MarketDataCache` (lines 14-45)
- Table: `market_data_cache` 
- Stores historical price data with symbol, date, OHLCV, sector/industry info
- Unique constraint on (symbol, date) pair

---

## 🚨 Common Issues & Solutions

### **Batch Processing Issues**

**1. Array Length Mismatch Errors**
```python
# Error: "All arrays must be of the same length"
# Cause: Aggregation functions receiving dict wrapper instead of list
# Solution:
positions_list = position_data.get("positions", [])  # Extract list from wrapper
aggregations = calculate_portfolio_exposures(positions_list)
```

**2. Missing calculation_date Parameter**
```python
# Error: Correlation calculations showing 0 records
# Solution: Add calculation_date parameter
await correlation_service.calculate_portfolio_correlations(
    portfolio_uuid,
    calculation_date=datetime.now()  # Add this parameter
)
```

**3. Greenlet/Async Errors**
```python
# Error: "greenlet_spawn has not been called"
# Solution: Use proper async context manager
async with get_async_session() as db:
    # All database operations here
```

### **Database Issues**

**1. Missing Tables**
```bash
# Error: "relation does not exist"
# Solution: Apply migrations
uv run alembic upgrade head
```

**2. UUID Type Handling**
```python
# Always convert string UUIDs when needed
from app.utils.uuid_utils import ensure_uuid
portfolio_uuid = ensure_uuid(portfolio_id)
```

**3. Duplicate Key Violations**
```python
# Use merge() for upsert operations
existing = await db.get(Model, primary_key)
if existing:
    for key, value in new_data.items():
        setattr(existing, key, value)
else:
    db.add(Model(**new_data))
```

### **Data Type Issues**

**1. Position Type Handling**
```python
# Convert enum to string for comparisons
position_type_str = getattr(position_type, 'value', position_type)
if position_type_str in OPTIONS_POSITION_TYPES:
    # Handle options
```

**2. Decimal Precision**
```python
# Apply correct precision for different fields
money_value = value.quantize(Decimal("0.00"))  # 2 decimal places
greek_value = value.quantize(Decimal("0.0000"))  # 4 decimal places
```

### **Import Issues**

**1. Circular Import Prevention**
```python
# Use late imports inside functions
def calculate_something():
    from app.models.market_data import MarketDataCache  # Import here
    # Use MarketDataCache
```

**2. Missing Dependencies**
```python
# Check if library exists before using
import importlib.util
if importlib.util.find_spec("library_name"):
    import library_name
else:
    # Use fallback or raise clear error
```

---

## 📋 Common Development Tasks

### **Adding New Models**
1. Create model in appropriate `app/models/` file
2. Add to `alembic/env.py` if needed
3. Generate migration: `uv run alembic revision --autogenerate -m "description"`
4. Apply migration: `uv run alembic upgrade head`

### **Testing Batch Jobs**
1. Ensure demo data seeded: `python scripts/reset_and_seed.py seed`
2. Test individual functions before running full batch
3. Check TODO1.md Section 1.6.14 for known issues
4. Use graceful degradation for missing data

### **Working with Portfolio Reports** (Phase 2.0 ✅ COMPLETE)
1. Reference `_docs/requirements/PRD_PORTFOLIO_REPORT_SPEC.md`
2. Use existing calculation data (even if incomplete)
3. Implement graceful degradation for missing calculation engines
4. Target 3 demo portfolios initially

---

## 🧪 Testing Framework

### **Installation** ⚠️ **IMPORTANT**
Testing dependencies are in optional dev group:
```bash
# Install with dev dependencies
pip install -e ".[dev]"
# OR with uv
uv pip install -e ".[dev]"
```

### **Pytest Setup** ✅ **READY**
- **Framework**: pytest >= 7.4.0 with async support
- **Dependencies**: `pytest-asyncio>=0.21.0`, `pytest-cov>=4.1.0`
- **Test Location**: `tests/` directory with proper structure
- **Config**: See `pyproject.toml` for test configuration

### **Key Test Files**
```
tests/
├── test_snapshot_generation.py    - Portfolio snapshots
├── test_portfolio_aggregation.py  - Portfolio calculations  
├── test_greeks_calculations.py    - Options Greeks
├── test_market_data_service.py    - Market data integration
├── test_correlation_service.py    - Position correlations
└── fixtures/                      - Shared test fixtures
```

### **Running Tests**
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_snapshot_generation.py

# Run with coverage
uv run pytest --cov=app

# Run with verbose output
uv run pytest -v

# Run async tests specifically
uv run pytest -m asyncio
```

### **Test Gotchas**
- **Greeks Precision**: Tests should expect 2dp for snapshot Greeks (DB constraint)
- **Field Names**: Use `notional` not `notional_exposure` in assertions
  - **Compatibility Note**: If older tests expect `notional_exposure`, either:
    1. Update tests to use `notional` (preferred), or
    2. Add temporary alias: `result["notional_exposure"] = result["notional"]` in `calculate_portfolio_exposures()`
- **Position Types**: Test data may use enums - normalize to strings in tests
- **Async Tests**: Use `@pytest.mark.asyncio` decorator for async test functions

**Note**: Tests use async patterns (`pytest-asyncio`) and proper database mocking. Existing tests cover core calculation engines and batch processing workflows.

---

## 📐 Design Decisions & Policies

### **Input Validation Philosophy**
- **Current**: Permissive with logging - accept wrapper dicts and extract data
- **Rationale**: Resilience over strictness during development phase
- **Future**: May switch to fail-fast with clear exceptions in production

### **Precision & Rounding Policy**
- **Calculations**: Maintain full precision (4dp for Greeks)
- **Database Storage**: Round to match column constraints at write time
- **API Response**: Final rounding at serialization layer
- **Current Implementation**:
  - `calculate_portfolio_exposures()` rounds to 2dp (lines 180-188)
  - `aggregate_portfolio_greeks()` rounds to 4dp (lines 264-266)
  - This matches DB constraints: exposures use NUMERIC(16,2), Greeks use NUMERIC(12,4)
  - Note: May change to round only at DB/API layer in future

### **Field Naming Standards**
- **Canonical**: Use `notional` (not `notional_exposure`)
- **Backward Compatibility**: Not required for internal APIs
- **Documentation**: Update all references to canonical names

### **Rho Handling**
- **Policy**: Calculate rho but do NOT store in PortfolioSnapshot
- **Rationale**: Rarely used metric, saves storage
- **Details**: 
  - `aggregate_portfolio_greeks()` returns rho in its output (line 240)
  - `PortfolioSnapshot` model has no `portfolio_rho` field (`app/models/snapshots.py` lines 14-57)
  - Snapshot write path ignores rho when storing aggregated Greeks
- **Access**: Available in PositionGreeks table, can aggregate if needed

### **Trading Calendar Gating & Weekend Behavior** 📅 **IMPORTANT**
**Verified 2025-08-09**: Batch framework behavior on weekends/non-market days:

**What RUNS on weekends:**
- ✅ All calculation engines (Greeks, Factors, Correlations, Stress Tests, etc.)
- ✅ Report generation (MD, JSON, CSV)
- ✅ Market data sync (uses most recent available data)
- ✅ All batch jobs via `scripts/run_batch_with_reports.py`

**What SKIPS weekends:**
- ❌ Portfolio snapshots - Message: "2025-08-09 is not a trading day, skipping snapshot"
- ❌ Daily P&L calculation (requires two snapshots to compare)

**P&L Behavior:**
- First snapshot: P&L = $0.00 (no previous snapshot for comparison)
- Weekends: P&L remains $0.00 (no new snapshot created)
- Next trading day: P&L will show actual change from last trading day

**Key Insight:** The batch framework has NO market day restrictions except for snapshot creation. This is intentional - calculations can run anytime using the most recent market data, but snapshots only capture end-of-day values on actual trading days.

### **Aggregation Function Status**
All functions in `app/calculations/portfolio.py`:
- ✅ `calculate_portfolio_exposures` (lines 68-197) - Fully implemented
- ✅ `aggregate_portfolio_greeks` (lines 200-284) - Fully implemented  
- ✅ `calculate_delta_adjusted_exposure` (lines 287-370) - Fully implemented
- ✅ `aggregate_by_tags` (lines 373-502) - Fully implemented
- ✅ `aggregate_by_underlying` (lines 505-634) - Fully implemented

---

## 🎯 Phase-Specific Context

### **Phase 1: COMPLETED** ✅
- All 8 batch calculation engines implemented
- Demo data seeding production-ready
- Database schema complete (except stress_test_results)
- Basic infrastructure solid

### **Phase 3.0: API Development** ⏳ **CURRENT**
- Raw Data APIs (/data/) ✅ COMPLETE (6/6 endpoints)
- Analytics APIs (/analytics/) - 0% complete
- Management APIs (/management/) - 0% complete
- Overall: 30% complete (12/39 endpoints)
- Use existing calculation data with graceful degradation
- Target: 3 demo portfolios
- Known issues documented in TODO1.md 1.6.14

### **Phase 3.0: Developer Experience** 📋 **PLANNED**
- Streamlined onboarding (enhanced from Redis removal)
- Automated setup scripts
- Better documentation

---

## 💡 AI Agent Efficiency Tips

1. **Always check TODO3.md first** for current work, TODO1.md and TODO2.md for historical reference
2. **Use existing demo data** rather than creating new test data
3. **Implement graceful degradation** for missing calculation data
4. **Reference this guide** instead of exploring file structure
5. **Check completion status** in TODO files before implementing features
6. **Use the diagnostic commands** to verify environment quickly

---

**Remember**: This codebase has 8 working calculation engines with some data gaps. Use graceful degradation patterns and reference the systematic issue resolution plan in TODO1.md Section 1.6.14 for any batch processing problems.