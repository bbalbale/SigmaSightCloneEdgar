# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Last Updated**: 2025-10-29

## Project Overview

**SigmaSight** - A full-stack portfolio risk analytics platform combining a FastAPI backend with Next.js 14 frontend. The system provides real-time portfolio analytics, AI-powered chat interface, automated batch processing, and comprehensive financial risk calculations.

**Architecture**:
- **Backend**: FastAPI with 57 production endpoints, 8 calculation engines, batch processing framework
- **Frontend**: Next.js 14 multi-page application with 6 authenticated pages, AI chat integration
- **Database**: PostgreSQL with UUID primary keys, Alembic migrations
- **AI Integration**: OpenAI Responses API (NOT Chat Completions API) for analytical reasoning

> 🤖 **CRITICAL**: The AI agent system uses **OpenAI Responses API**, NOT Chat Completions API.

---

## Common Development Commands

### Quick Start - Full Stack
> **📖 Full Frontend Docker Guide**: See `frontend/DOCKER.md` for comprehensive Docker documentation

```bash
# Start frontend (Docker Compose - uses .env.local)
cd frontend && docker-compose up -d

# Start backend
cd backend && uv run python run.py

# Frontend is now at http://localhost:3005
# Backend API at http://localhost:8000
# API Docs at http://localhost:8000/docs
```

### Frontend (Docker Preferred)
```bash
# Using Docker Compose (Recommended - uses .env.local)
cd frontend
docker-compose up -d              # Build and start
docker-compose logs -f            # View logs
docker-compose down               # Stop and remove

# Using Docker directly with env file
docker build -t sigmasight-frontend .
docker run -d -p 3005:3005 --env-file .env.local --name sigmasight-frontend sigmasight-frontend

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
uv run python scripts/database/reset_and_seed.py seed  # Seed demo data (3 portfolios, 63 positions)
```

### Testing
```bash
# Backend tests
cd backend
uv run pytest                      # All tests
uv run pytest tests/test_market_data_service.py  # Single test file
uv run pytest -k "test_function_name"  # Single test function

# Frontend tests
cd frontend
npm run test                       # Run tests once
npm run test:watch                 # Run tests in watch mode
npm run type-check                 # TypeScript validation
```

### Code Quality
```bash
# Backend
cd backend
uv run black .                     # Format code
uv run isort .                     # Sort imports
uv run flake8 app/                 # Lint
uv run mypy app/                   # Type checking

# Frontend
cd frontend
npm run lint                       # ESLint
npm run type-check                 # TypeScript
npx prettier --write .             # Format
```

### Batch Processing & Reports
```bash
# Manual batch runs
cd backend
uv run python scripts/run_batch_calculations.py      # Run all calculations
uv run python scripts/generate_all_reports.py        # Generate portfolio reports

# Database reset
uv run python scripts/database/reset_and_seed.py reset  # Full reset and reseed
```

---

## High-Level Architecture

### Core Structure
The application follows a multi-layered architecture:

```
SigmaSight/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/v1/       # REST endpoints (57 implemented)
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── services/     # Business logic layer
│   │   ├── batch/        # Batch processing orchestration
│   │   ├── calculations/ # Financial calculation engines
│   │   ├── agent/        # AI agent system (OpenAI Responses API)
│   │   └── core/         # Shared utilities (auth, db, logging)
│   ├── scripts/          # Utility and verification scripts
│   ├── alembic/          # Database migrations
│   └── _docs/            # Backend documentation
│
├── frontend/             # Next.js 14 application
│   ├── app/              # Next.js App Router (6 pages)
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── containers/   # Page containers
│   │   ├── hooks/        # Custom React hooks
│   │   ├── services/     # API client services (11 total)
│   │   ├── stores/       # Zustand state management
│   │   └── lib/          # Utility libraries
│   └── _docs/            # Frontend documentation
│
└── docker-compose.yml    # PostgreSQL database
```

### Key Architectural Patterns

1. **Async-First Design**: All database operations use async/await with SQLAlchemy 2.0
2. **Batch Processing Framework**: 3-phase orchestration with 8 calculation engines
   - Phase 1: Market Data Collection (1-year lookback)
   - Phase 2: P&L Calculation & Snapshots
   - Phase 2.5: Position Market Value Updates (added Oct 29, 2025)
   - Phase 3: Risk Analytics (betas, factors, volatility, correlations)
3. **Multi-Provider Market Data**: YFinance (primary), Polygon (options), FMP (secondary), FRED (economic)
4. **Hybrid Calculation Engine**: Real calculations with graceful degradation when data unavailable
5. **AI-Powered Chat**: OpenAI Responses API with SSE streaming and tool integration
6. **Position Tagging System**: 3-tier tagging architecture (October 2, 2025)
   - **Strategy System Removed**: All `/api/v1/strategies/*` endpoints deprecated (October 2025)
   - Migration to position-level tagging only

### Database Architecture
- PostgreSQL with UUID primary keys
- Alembic for schema migrations
- Full audit trails with created_at/updated_at
- Relationships: User → Portfolio → Position → Calculations
- Position → Tags (M:N via position_tags junction table)

---

## Important Context

### Current Status
- **Phase**: Phases 1-11 complete, system in production refinement
- **APIs Ready**: 59 endpoints across 9 categories (see API Reference section)
- **Demo Data**: 3 portfolios with 63 positions ready for testing
- **Frontend**: Multi-page application with AI analytical reasoning
- **Features**: Target price tracking, sector tagging, risk metrics (sector exposure, concentration, volatility), company profiles

### Key Documentation

**Backend Documentation**:
- **`backend/CLAUDE.md`**: Comprehensive backend reference (READ FIRST for backend work)
- **`backend/_docs/reference/API_REFERENCE_V1.4.6.md`**: Complete API endpoint documentation
- **`backend/_docs/requirements/`**: Product requirements and specifications
- **`backend/_archive/todos/`**: Historical TODO files (Phase 1-3 complete, archived)

**Frontend Documentation**:
- **`frontend/CLAUDE.md`**: Complete frontend reference (READ FIRST for frontend work)
- **`frontend/_docs/requirements/README.md`**: Master implementation guide
- **`frontend/_docs/project-structure.md`**: Directory structure and patterns
- **`frontend/_docs/API_AND_DATABASE_SUMMARY.md`**: Backend API integration reference

### Environment Variables

**Backend `.env` file**:
```
# Database (required)
DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db

# Market Data APIs (required for batch processing)
POLYGON_API_KEY=your_polygon_key
FMP_API_KEY=your_fmp_key        # Secondary provider
FRED_API_KEY=your_fred_key

# JWT Authentication (required)
SECRET_KEY=your_jwt_secret

# OpenAI (required for AI chat)
OPENAI_API_KEY=your_openai_key
```

**Frontend `.env.local` file**:
```
# Backend API URL (switch between local/Railway)
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1

# Or for Railway backend:
# BACKEND_URL=https://sigmasight-be-sandbox-frontendrailway.up.railway.app
# NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-sandbox-frontendrailway.up.railway.app/api/v1
```

### Common Gotchas
1. **Async/Sync Mixing**: Always use async patterns - mixing causes greenlet errors
2. **UUID Handling**: Convert string UUIDs to UUID objects when needed
3. **Batch Orchestrator Version**: Use `batch_orchestrator_v3`, NOT v2 (updated Oct 2025)
4. **Market Data Priority**: YFinance-first, NOT FMP (changed Oct 2025)
5. **Strategy Endpoints**: All strategy endpoints removed (October 2025) - use tagging instead
6. **Demo Data**: Always test with existing demo portfolios first (password: demo12345)
7. **Frontend Client-Side**: All pages use `'use client'` directive, no SSR
8. **Service Layer**: Never make direct `fetch()` calls, always use service layer

### Testing Approach
- Use existing demo data (don't create new test data)
- Run diagnostic commands to verify imports
- Test with graceful degradation for missing data
- Frontend: Must login first at `/login` to establish authentication
- Check browser DevTools Network tab for API call verification

---

## API Endpoints Reference

### Current Implementation Status
**59 endpoints** implemented across 9 categories (~100% Phase 3 complete, production-ready)

### Authentication (5 endpoints) ✅
- `POST /api/v1/auth/login` - JWT token generation
- `POST /api/v1/auth/logout` - Session invalidation
- `POST /api/v1/auth/refresh` - Token refresh
- `GET /api/v1/auth/me` - Current user info
- `POST /api/v1/auth/register` - User registration

### Data (10 endpoints) ✅
- `GET /api/v1/data/portfolio/{id}/complete` - Full portfolio snapshot
- `GET /api/v1/data/portfolio/{id}/data-quality` - Data completeness metrics
- `GET /api/v1/data/positions/details` - Position details with P&L
- `GET /api/v1/data/prices/historical/{id}` - Historical price data
- `GET /api/v1/data/prices/quotes` - Real-time market quotes
- `GET /api/v1/data/factors/etf-prices` - Factor ETF prices
- `GET /api/v1/data/company-profile/{symbol}` - Company profile data (53 fields)
- `GET /api/v1/data/market-cap/{symbol}` - Market capitalization
- `GET /api/v1/data/beta/{symbol}` - Stock beta values
- `GET /api/v1/data/sector/{symbol}` - Sector classification

### Analytics (9 endpoints) ✅
- `GET /api/v1/analytics/portfolio/{id}/overview` - Portfolio metrics overview
- `GET /api/v1/analytics/portfolio/{id}/correlation-matrix` - Correlation matrix
- `GET /api/v1/analytics/portfolio/{id}/diversification-score` - Diversification metrics
- `GET /api/v1/analytics/portfolio/{id}/factor-exposures` - Portfolio factor betas
- `GET /api/v1/analytics/portfolio/{id}/positions/factor-exposures` - Position-level factors
- `GET /api/v1/analytics/portfolio/{id}/stress-test` - Stress test scenarios
- `GET /api/v1/analytics/portfolio/{id}/sector-exposure` - Sector exposure vs S&P 500 ✨ **NEW** (Oct 17, 2025)
- `GET /api/v1/analytics/portfolio/{id}/concentration` - Concentration metrics (HHI) ✨ **NEW** (Oct 17, 2025)
- `GET /api/v1/analytics/portfolio/{id}/volatility` - Volatility analytics with HAR forecasting ✨ **NEW** (Oct 17, 2025)

### Chat (6 endpoints) ✅
- `POST /api/v1/chat/conversations` - Create new conversation
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/{id}` - Get conversation
- `DELETE /api/v1/chat/conversations/{id}` - Delete conversation
- `POST /api/v1/chat/conversations/{id}/send` - Send message (SSE streaming)
- `GET /api/v1/chat/conversations/{id}/messages` - Get conversation messages

### Target Prices (10 endpoints) ✅
- `POST /api/v1/target-prices` - Create target price
- `GET /api/v1/target-prices` - List target prices (filter by portfolio/position)
- `GET /api/v1/target-prices/{id}` - Get target price
- `PUT /api/v1/target-prices/{id}` - Update target price
- `DELETE /api/v1/target-prices/{id}` - Delete target price
- `POST /api/v1/target-prices/bulk` - Bulk create target prices
- `PUT /api/v1/target-prices/bulk` - Bulk update target prices
- `DELETE /api/v1/target-prices/bulk` - Bulk delete target prices
- `POST /api/v1/target-prices/import-csv` - Import from CSV
- `GET /api/v1/target-prices/export-csv` - Export to CSV

### Position Tagging (12 endpoints) ✅

**Tag Management (7 endpoints)** - October 2, 2025:
- `POST /api/v1/tags` - Create tag
- `GET /api/v1/tags` - List all tags
- `GET /api/v1/tags/{id}` - Get tag
- `PUT /api/v1/tags/{id}` - Update tag
- `DELETE /api/v1/tags/{id}` - Delete tag
- `POST /api/v1/tags/bulk` - Bulk create tags
- `DELETE /api/v1/tags/bulk` - Bulk delete tags

**Position Tagging (5 endpoints)** - October 2, 2025 (PREFERRED):
- `POST /api/v1/position-tags` - Tag a position
- `GET /api/v1/position-tags` - List position tags (filter by position/tag)
- `DELETE /api/v1/position-tags/{id}` - Remove tag from position
- `POST /api/v1/position-tags/bulk` - Bulk tag positions
- `DELETE /api/v1/position-tags/bulk` - Bulk remove tags

### Admin Batch Processing (6 endpoints) ✅
- `POST /api/v1/admin/batch/run` - Trigger batch processing with real-time tracking
- `GET /api/v1/admin/batch/run/current` - Get current batch status (polling endpoint)
- `POST /api/v1/admin/batch/trigger/market-data` - Manually trigger market data update
- `POST /api/v1/admin/batch/trigger/correlations` - Manually trigger correlation calculations
- `GET /api/v1/admin/batch/data-quality` - Get data quality status and metrics
- `POST /api/v1/admin/batch/data-quality/refresh` - Refresh market data for quality improvement

### Company Profiles (1 endpoint) ✅
- `GET /api/v1/company-profile/sync/{symbol}` - Sync company profile data (automatic via Railway cron)

**Complete API Documentation**: See `frontend/_docs/1. API_AND_DATABASE_SUMMARY.md` (most current, updated Oct 7, 2025)

---

## Critical Import Paths

### Backend Imports
```python
# Database models
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.models.tags_v2 import TagV2
from app.models.position_tags import PositionTag
from app.models.market_data import PositionGreeks, PositionFactorExposure

# Database utilities
from app.database import get_async_session, AsyncSessionLocal

# Batch processing (USE V3, NOT V2)
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3

# Core utilities
from app.config import settings
from app.core.logging import get_logger
from app.core.auth import get_password_hash, verify_password
from app.core.dependencies import get_current_user
```

### Frontend Imports
```typescript
// Services (ALWAYS use these, never direct fetch)
import { apiClient } from '@/services/apiClient'
import { authManager } from '@/services/authManager'
import { portfolioResolver } from '@/services/portfolioResolver'
import strategiesApi from '@/services/strategiesApi'
import tagsApi from '@/services/tagsApi'

// State management
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useChatStore } from '@/stores/chatStore'

// Hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'

// Components
import { NavigationDropdown } from '@/components/navigation/NavigationDropdown'
import { Button } from '@/components/ui/button'
```

---

## Development Workflow

### Backend Development
1. **Before Starting**: Read `backend/CLAUDE.md` for comprehensive backend reference
2. **Check API Status**: Review `backend/_docs/reference/API_REFERENCE_V1.4.6.md`
3. **Test Imports**: Use diagnostic commands from backend documentation
4. **Implement**: Follow async patterns, use batch_orchestrator_v3
5. **Handle Errors**: Implement graceful degradation for missing data
6. **Migrations**: Always use Alembic for database changes

### Frontend Development
1. **Before Starting**: Read `frontend/CLAUDE.md` and `frontend/_docs/requirements/README.md`
2. **Check Services**: Review `frontend/_docs/requirements/07-Services-Reference.md`
3. **Authentication**: Must login at `/login` first
4. **Use Services**: Never make direct `fetch()` calls, always use service layer
5. **State Management**: Use Zustand for portfolio ID, React Context for auth
6. **Testing**: Test with browser DevTools Network tab

### Full-Stack Testing
1. Start backend: `cd backend && uv run python run.py`
2. Start frontend: `cd frontend && docker-compose up -d`
3. Login at `http://localhost:3005/login` (demo_hnw@sigmasight.com / demo12345)
4. Verify API calls in browser DevTools
5. Check backend logs for any errors

---

## Key Commands for Debugging

### Backend Diagnostics
```bash
cd backend

# Verify critical imports
uv run python -c "from app.models.users import User; print('✅ Models import successfully')"

# Check database content
uv run python scripts/verification/check_database_content.py

# Test batch processing v3
uv run python -c "from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3; print('✅ Batch v3 ready')"

# Verify demo portfolios
uv run python scripts/verification/verify_demo_portfolios.py
```

### Frontend Diagnostics
```bash
cd frontend

# TypeScript validation
npm run type-check

# Check build
npm run build

# Docker health check
curl http://localhost:3005/api/health

# View container logs
docker-compose logs -f
```

### Database Diagnostics
```bash
cd backend

# Check data counts
uv run python -c "
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position

async def check():
    async with get_async_session() as db:
        portfolios = await db.execute(select(func.count(Portfolio.id)))
        positions = await db.execute(select(func.count(Position.id)))
        print(f'Portfolios: {portfolios.scalar()}, Positions: {positions.scalar()}')

asyncio.run(check())
"
```

---

## Demo Data Reference

### Demo Users & Portfolios
```python
# Demo user credentials (all use same password: "demo12345")
DEMO_USERS = {
    "demo_individual@sigmasight.com": "Balanced Individual Investor Portfolio (16 positions)",
    "demo_hnw@sigmasight.com": "Sophisticated High Net Worth Portfolio (17 positions)",
    "demo_hedgefundstyle@sigmasight.com": "Long/Short Equity Hedge Fund Style Portfolio (30 positions)"
}

# Total positions: 63 across all 3 portfolios
```

### Investment Classes
- **PUBLIC**: Regular equities, ETFs (LONG/SHORT position types)
- **OPTIONS**: Options contracts (LC/LP/SC/SP position types)
- **PRIVATE**: Private/alternative investments

### Seeding Commands
```bash
# Full reset and reseed (AUTHORITATIVE script)
cd backend
python scripts/database/reset_and_seed.py reset

# Seed only (preserves existing data)
python scripts/database/reset_and_seed.py seed
```

---

## Railway Deployment

### Railway Audit Scripts
All audit scripts can be run from local machine against Railway deployment:

```bash
cd backend/scripts/railway

# Portfolio & Position Data Audit (no SSH required)
python audit_railway_data.py
# Output: railway_audit_results.json

# Market Data Audit (no SSH required)
python audit_railway_market_data.py
# Output: railway_market_data_audit_report.txt

# Analytics Audit - Client-Friendly (no SSH required)
python audit_railway_analytics.py
# Output: railway_analytics_audit_report.txt (31KB, formatted)

# Calculation Results Audit (requires Railway SSH)
railway run python audit_railway_calculations_verbose.py
# Output: railway_calculations_audit_report.txt
```

**Full Documentation**: See `backend/scripts/railway/README.md`

---

## Notes

- Main application code split between `backend/` and `frontend/` subdirectories
- Always work from appropriate subdirectory when running commands
- Backend uses batch_orchestrator_v3 (NOT v2) as of October 2025
- Market data priority is YFinance-first (NOT FMP) as of October 2025
- Strategy system removed October 2025 - use position tagging instead
- Frontend is client-side only - all pages use `'use client'` directive
- Position market value updates (Phase 2.5) added October 29, 2025
- System has 767+ commits since September 2025, significantly evolved from initial design
- Prefer simple, correct implementations over complex feature flags
- Update subdirectory CLAUDE.md files when discovering new patterns

---

**Remember**: This is a mature, production-ready system with comprehensive documentation. Always consult the subdirectory-specific CLAUDE.md files (`backend/CLAUDE.md`, `frontend/CLAUDE.md`) for detailed implementation guidance before starting work in either area.
