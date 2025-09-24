# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> ⚠️ **CRITICAL WARNING (2025-08-26)**: API implementation significantly incomplete.
> - Many endpoints return MOCK/random data
> - Legacy endpoints are TODO stubs
> - See `backend/API_IMPLEMENTATION_STATUS.md` for TRUE status
> - Do NOT rely on other documentation claiming "100% complete"

## Project Overview

SigmaSight Backend - A FastAPI-based portfolio risk analytics platform with 8 calculation engines, automated batch processing, comprehensive financial analytics, and AI-powered chat interface using OpenAI Responses API. The project is structured with the main application code in the `backend/` subdirectory.

> 🤖 **CRITICAL**: The AI agent system uses **OpenAI Responses API**, NOT Chat Completions API.

## Common Development Commands

### Quick Start - Full Stack
```bash
# Start frontend (Docker)
cd frontend && docker build -t sigmasight-frontend . && docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Start backend
cd backend && uv run python run.py

# Frontend is now at http://localhost:3005
# Backend API at http://localhost:8000
```

### Frontend (Docker Preferred)
```bash
# Build and run frontend
cd frontend
docker build -t sigmasight-frontend .
docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Quick restart (if image exists)
docker stop frontend && docker rm frontend
docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Check health
curl http://localhost:3005/api/health

# Traditional npm (fallback)
cd frontend && npm run dev
```

### Backend & Database
```bash
# Start development server
cd backend
uv run python run.py              # Main development server
uvicorn app.main:app --reload     # Alternative with auto-reload

# Database setup
docker-compose up -d               # Start PostgreSQL
uv run alembic upgrade head        # Run migrations
uv run python scripts/seed_database.py  # Seed demo data (3 portfolios, 63 positions)
```

### Testing
```bash
# Run test suite
uv run pytest                      # All tests
uv run pytest tests/test_market_data_service.py  # Single test file
uv run pytest -k "test_function_name"  # Single test function

# Verification scripts
uv run python scripts/verify_setup.py    # Verify installation
./scripts/test_api_endpoints.sh          # Test API endpoints
```

### Code Quality
```bash
# Format and lint
uv run black .                     # Format code
uv run isort .                     # Sort imports
uv run flake8 app/                 # Lint
uv run mypy app/                   # Type checking
```

### Batch Processing & Reports
```bash
# Manual batch runs
uv run python scripts/run_batch_calculations.py      # Run all calculations
uv run python scripts/generate_all_reports.py        # Generate portfolio reports

# Database reset
uv run python scripts/reset_and_seed.py              # Full reset and reseed
```

## High-Level Architecture

### Core Structure
The application follows a multi-layered architecture within `backend/`:

```
app/
├── api/v1/               # FastAPI REST endpoints (auth, data, router)
├── models/               # SQLAlchemy ORM models
├── services/             # Business logic layer
├── batch/                # Batch processing orchestration
├── calculations/         # Financial calculation engines
├── core/                 # Shared utilities (auth, db, logging)
└── database.py           # Database connection management
```

### Key Architectural Patterns

1. **Async-First Design**: All database operations use async/await with SQLAlchemy 2.0
2. **Batch Processing Framework**: 8 sequential calculation engines with graceful degradation
3. **Multi-Provider Market Data**: FMP (primary), Polygon (options), FRED (economic)
4. **Hybrid Calculation Engine**: Real calculations with mock fallbacks when data unavailable

### Database Architecture
- PostgreSQL with UUID primary keys
- Alembic for schema migrations
- Full audit trails with created_at/updated_at
- Relationships: User → Portfolio → Position → Calculations

### Critical Import Paths
```python
# Database models
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.models.market_data import PositionGreeks, PositionFactorExposure

# Database utilities
from app.database import get_async_session, AsyncSessionLocal

# Batch processing
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2

# Core utilities
from app.config import settings
from app.core.logging import get_logger
```

## Important Context

### Current Status
- **Phase**: 3.0 - API Development (30% complete, Raw Data APIs done)
- **APIs Ready**: Authentication + Raw Data endpoints (12/39 endpoints)
- **Demo Data**: 3 portfolios with 63 positions ready for testing
- **Ready for**: Frontend and LLM agent development

### Key Documentation
- **`backend/AI_AGENT_REFERENCE.md`**: Comprehensive codebase reference (READ FIRST)
- **`backend/TODO3.md`**: Current Phase 3.0 API development (ACTIVE)
- **`backend/TODO1.md`**: Phase 1 complete (reference only)
- **`backend/TODO2.md`**: Phase 2 complete (reference only)
- **`backend/_docs/requirements/`**: Product requirements and specifications

### Environment Variables
Required in `.env` file:
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/sigmasight
POLYGON_API_KEY=your_key_here
SECRET_KEY=your_jwt_secret
FMP_API_KEY=your_fmp_key  # Optional but recommended
FRED_API_KEY=your_fred_key  # Optional
```

### Common Gotchas
1. **Async/Sync Mixing**: Always use async patterns - mixing causes greenlet errors
2. **UUID Handling**: Convert string UUIDs to UUID objects when needed
3. **Missing Tables**: stress_test_results table doesn't exist (known issue)
4. **Import Errors**: Use diagnostic commands from AI_AGENT_REFERENCE.md
5. **Demo Data**: Always test with existing demo portfolios first (password: demo12345)

### Testing Approach
- Use existing demo data (don't create new test data)
- Run diagnostic commands to verify imports
- Test with graceful degradation for missing data
- Update TODO3.md with completion status

## Development Workflow

1. **Before Starting**: Read `backend/AI_AGENT_REFERENCE.md`
2. **Check Status**: Review TODO3.md for current work, TODO1/TODO2 for history
3. **Test Imports**: Use diagnostic commands to verify setup
4. **Implement**: Follow async patterns, handle errors gracefully
5. **Update Docs**: Document new patterns in AI_AGENT_REFERENCE.md
6. **Mark Complete**: Update TODO3.md status with detailed results

## Key Commands for Debugging

```bash
# Verify critical imports
cd backend && uv run python -c "from app.models.users import User; print('✅ Models import successfully')"

# Check database content
uv run python scripts/check_database_content.py

# Test batch processing
uv run python scripts/test_batch_with_reports.py

# Verify demo portfolios
uv run python scripts/verify_demo_portfolios.py
```

## API Endpoints Ready for Use

### Authentication (✅ Complete)
- `POST /api/v1/auth/login` - JWT token generation
- `POST /api/v1/auth/logout` - Session invalidation  
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /api/v1/auth/me` - Current user info

### Raw Data APIs (✅ Complete)
- `GET /api/v1/data/portfolio/{id}/complete` - Full portfolio snapshot
- `GET /api/v1/data/portfolio/{id}/data-quality` - Data completeness
- `GET /api/v1/data/positions/details` - Position details with P&L
- `GET /api/v1/data/prices/historical/{id}` - Historical prices
- `GET /api/v1/data/prices/quotes` - Real-time market quotes
- `GET /api/v1/data/factors/etf-prices` - Factor ETF prices

## Notes
- Main application code is in `backend/` subdirectory
- Always work from the `backend/` directory when running commands
- Update `backend/AI_AGENT_REFERENCE.md` when discovering new patterns
- Prefer simple, correct implementations over complex feature flags
- Backend is ready for frontend/agent development - no additional APIs needed for MVP