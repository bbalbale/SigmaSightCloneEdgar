# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Last Updated**: 2026-01-13

---

# MANDATORY RULES - READ BEFORE DOING ANYTHING

## Git Operations - NEVER VIOLATE

| Rule | Description |
|------|-------------|
| **NEVER push without permission** | Always ask user before `git push` to any branch |
| **NEVER commit without permission** | Always ask user before `git commit` |
| **NEVER assume branch syncing** | Only push to branches the user specifically requests |
| **Production runs on Railway** | Pushing to main triggers redeployment and kills running cron jobs |

**Before ANY git operation, ASK:**
> "Should I commit/push these changes to [branch]?"

## Platform - Windows Development, Railway Production

| Environment | Platform | Notes |
|-------------|----------|-------|
| Development | Windows | Use `Path` objects, not string paths with backslashes |
| Production | Railway (Linux) | Cron jobs run at 9 PM ET |

**ALL Python scripts using asyncpg MUST start with:**
```python
import sys
import asyncio

# REQUIRED for Windows + asyncpg compatibility
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

## Database - ALWAYS Verify Before Writing Code

**BEFORE writing ANY database-related code:**
1. **Read the actual model file first** - Never guess column names
2. **Use Alembic for ALL schema changes** - Never raw SQL for DDL
3. **Use correct database session** - Core vs AI database

```bash
# Check columns for any model
cd backend && uv run python -c "
from app.models.positions import Position
print([c.name for c in Position.__table__.columns])
"
```

| Model File | Contains |
|------------|----------|
| `backend/app/models/users.py` | User, Portfolio |
| `backend/app/models/positions.py` | Position, PositionType |
| `backend/app/models/market_data.py` | CompanyProfile, PositionGreeks |
| `backend/app/models/tags_v2.py` | TagV2 |
| `backend/app/models/position_tags.py` | PositionTag |

---

# Project Overview

**SigmaSight** - A full-stack portfolio risk analytics platform combining a FastAPI backend with Next.js 14 frontend. The system provides real-time portfolio analytics, AI-powered chat interface, automated batch processing, and comprehensive financial risk calculations.

**Architecture**:
- **Backend**: FastAPI with 129+ production endpoints, 8 calculation engines, batch processing framework
- **Frontend**: Next.js 14 multi-page application with 6 authenticated pages, AI chat integration
- **Database**: PostgreSQL with UUID primary keys, Alembic migrations
- **AI Integration**: OpenAI Responses API (NOT Chat Completions API) for analytical reasoning

---

# Quick Start Commands

### Full Stack
```bash
# Start frontend (Docker Compose - uses .env.local)
cd frontend && docker-compose up -d

# Start backend
cd backend && uv run python run.py

# Frontend is now at http://localhost:3005
# Backend API at http://localhost:8000
```

### Backend
```bash
cd backend
uv run python run.py              # Development server

# Database migrations (DUAL DATABASE)
uv run alembic -c alembic.ini upgrade head        # Core DB
uv run alembic -c alembic_ai.ini upgrade head     # AI DB

# Seed demo data
uv run python scripts/database/reset_and_seed.py seed
```

### Frontend
```bash
cd frontend
docker-compose up -d              # Docker (recommended)
npm run dev                       # Traditional npm
```

---

# Key Documentation

| Area | File | Purpose |
|------|------|---------|
| Backend | `backend/CLAUDE.md` | **READ FIRST** for backend work |
| Frontend | `frontend/CLAUDE.md` | **READ FIRST** for frontend work |
| API Reference | `backend/_docs/reference/API_REFERENCE_V1.4.6.md` | 59 endpoints documented |
| Requirements | `backend/_docs/requirements/` | Product specs |

---

# Architecture Quick Reference

## Database Architecture (Dual PostgreSQL)

**Core Database (gondola)** - Transactional data:
- Users, Portfolios, Positions, Market data, Snapshots
- Connection: `DATABASE_URL` / `get_db()` / `get_async_session()`

**AI Database (metro)** - Vector search and learning:
- `ai_kb_documents`, `ai_memories`, `ai_feedback`
- Connection: `AI_DATABASE_URL` / `get_ai_db()` / `get_ai_session()`

```python
# Core tables
from app.database import get_db, get_async_session

# AI tables
from app.database import get_ai_db, get_ai_session
```

## Batch Processing

- Use `batch_orchestrator` (NOT v2)
- Market data priority: YFinance → Polygon → FMP
- Nightly batch runs via Railway cron at 9 PM ET

## Key Patterns

| Pattern | Rule |
|---------|------|
| Async/Sync | Never mix - causes greenlet errors |
| UUID handling | Convert strings to UUID objects when needed |
| Strategy endpoints | **REMOVED** October 2025 - use tagging instead |
| Frontend | Client-side only - all pages use `'use client'` |
| API calls | Always use service layer, never direct `fetch()` |

---

# Demo Data

```python
# Demo credentials (password: demo12345)
DEMO_USERS = {
    "demo_individual@sigmasight.com": "Balanced Individual Investor (16 positions)",
    "demo_hnw@sigmasight.com": "High Net Worth (17 positions)",
    "demo_hedgefundstyle@sigmasight.com": "Hedge Fund Style (30 positions)"
}
```

---

# Common Gotchas

1. **Async/Sync Mixing**: Always use async patterns - mixing causes greenlet errors
2. **UUID Handling**: Convert string UUIDs to UUID objects when needed
3. **Batch Orchestrator**: Use `batch_orchestrator`, NOT v2
4. **Market Data**: YFinance-first, NOT FMP
5. **Strategy Endpoints**: Removed October 2025 - use tagging instead
6. **Dual Database**: Use `get_ai_session()` for AI tables, `get_async_session()` for Core
7. **Frontend**: All pages use `'use client'` directive, no SSR
8. **Service Layer**: Never make direct `fetch()` calls

---

**Remember**: Always consult `backend/CLAUDE.md` or `frontend/CLAUDE.md` for detailed guidance before starting work in either area.
