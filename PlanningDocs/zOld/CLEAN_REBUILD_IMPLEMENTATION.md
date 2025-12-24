# Clean Rebuild Implementation Plan

**Created**: 2025-12-19
**Updated**: 2025-12-21
**Status**: Phases 1-10 Complete ✅ | Phase 11 Cleanup: December 28, 2025
**Architecture**: Modular Monolith (Single Repo, Dual Databases, Dual Migration Chains)

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chat history | Stays in Core DB | User data stays together, simpler auth joins |
| AI Feedback | Goes to AI DB | Logical UUID link to Core messages (no FK) |
| AI schema management | Alembic (not raw SQL) | Proper versioning, consistent tooling |
| Market data migration | Script copy from old DB | Faster than API, cleaner than pg_dump |

---

## Quick Reference Checklist

```
[x] Phase 1: Create temp repo (sigmasight-db-setup) - COMPLETE
[x] Phase 2: Create 2 new Railway PostgreSQL databases - COMPLETE
[x] Phase 3: Run Core migrations via temp repo - COMPLETE (38 tables)
[x] Phase 4: Run AI migrations via temp repo - COMPLETE (4 tables + HNSW)
[-] Phase 5: Backup current DB - SKIPPED (old DB is our backup)
[x] Phase 6-7.5: Data population - COMPLETE (via seeding + batch processing)
[x] Phase 8: Update main repo code - COMPLETE (commit 3be9a32b)
[x] Phase 9: Swap env vars + push main repo - COMPLETE (Railway on new DBs)
[x] Phase 10: Verify all features working - COMPLETE (2025-12-21)
[ ] Phase 11: Cleanup (after 1 week) - SCHEDULED: December 28, 2025
```

---

## Architecture Overview

### Target Repository Structure (Main Repo after Phase 8)

```
backend/
├── alembic.ini             # Config for Core DB
├── alembic_ai.ini          # Config for AI DB (NEW)
├── migrations_core/        # Was 'alembic/' - Core schema history
│   ├── env.py              # Targets Base.metadata
│   └── versions/
├── migrations_ai/          # Fresh start - AI schema history
│   ├── env.py              # Targets AiBase.metadata
│   └── versions/
├── app/
│   ├── models/
│   │   ├── ...             # Core models (Users, Portfolios, Market)
│   │   └── ai_models.py    # AI models with separate AiBase
│   ├── database.py         # Dual engines (core_engine, ai_engine)
│   └── config.py           # DATABASE_URL + AI_DATABASE_URL
```

### Database Separation

```
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│   CORE DATABASE                 │    │   AI DATABASE                   │
│   (sigmasight-core)             │    │   (sigmasight-ai)               │
│                                 │    │                                 │
│   37 tables:                    │    │   3 tables:                     │
│   - Users, Portfolios           │    │   - ai_kb_documents (pgvector)  │
│   - Positions, Market Data      │    │   - ai_memories                 │
│   - Calculations, Analytics     │    │   - ai_feedback                 │
│   - Tags, Snapshots             │    │                                 │
│   - Chat conversations/messages │    │   HNSW index for embeddings     │
│                                 │    │   No cross-DB foreign keys      │
│   Base.metadata                 │    │   AiBase.metadata               │
└─────────────────────────────────┘    └─────────────────────────────────┘
```

### Strategy Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ CURRENT STATE (remains untouched until Phase 9)                         │
│                                                                         │
│   Main Repo ────► Railway Backend ────► Current DB                      │
│   (unchanged)     (running)             (production, DO NOT TOUCH)      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ SETUP PHASE (Phases 1-7.5)                                              │
│                                                                         │
│   Temp Repo ─── alembic.ini ──────────► New Core DB (37 tables)         │
│   (sigmasight-db-setup)                                                 │
│              ─── alembic_ai.ini ──────► New AI DB (3 tables + HNSW)     │
│                                                                         │
│   Seed Script ────────────────────────► demo portfolios → New Core DB   │
│                                                                         │
│   Python Script ──► reads Old DB ─────► market data ───► New Core DB    │
│   (migrate_market_data.py)                                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ ATOMIC SWAP (Phase 9) - All at once                                     │
│                                                                         │
│   1. Update Railway env vars (DATABASE_URL, AI_DATABASE_URL)            │
│   2. git push main repo (dual-DB code)                                  │
│   3. Railway auto-redeploys with new code + new DBs                     │
│                                                                         │
│   Main Repo ────► Railway Backend ────┬──► New Core DB                  │
│   (updated)       (redeployed)        └──► New AI DB                    │
│                                                                         │
│   Old DB ────► Kept as backup (delete after 1 week)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Create Temporary Repository ✅ COMPLETE

**Repo**: https://github.com/bbalbale/sigmasight-db-setup (private)

### Structure Created

```
sigmasight-db-setup/
├── alembic.ini              # Core DB config
├── alembic_ai.ini           # AI DB config
├── migrations_core/
│   ├── env.py               # Targets Base.metadata, excludes AI tables
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_core_schema.py
├── migrations_ai/
│   ├── env.py               # Targets AiBase.metadata
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_ai_schema.py  # Includes HNSW vector index
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py          # Base declarative
│   └── models/
│       ├── __init__.py      # Core models (37 tables)
│       ├── ai_models.py     # AI models with AiBase (3 tables)
│       └── ... (core model files)
├── pyproject.toml
├── railway.toml
└── README.md
```

### Key Implementation Details

**Separate Bases (no metadata collision):**
```python
# app/database.py
Base = declarative_base()  # For Core models

# app/models/ai_models.py
AiBase = declarative_base()  # For AI models
```

**Dual env.py files:**
- `migrations_core/env.py` → targets `Base.metadata`, excludes AI tables
- `migrations_ai/env.py` → targets `AiBase.metadata`, reads `AI_DATABASE_URL`

---

## Phase 2: Create New Databases on Railway ✅ COMPLETE

### 2.1 Databases Created

| Database | Railway Name | Host | Tables |
|----------|--------------|------|--------|
| Core | SigmaSight-Core-DB | gondola.proxy.rlwy.net:38391 | 38 |
| AI | SigmaSight-AI-DB | metro.proxy.rlwy.net:31246 | 4 |

### 2.2 Connection Strings (for reference)

```bash
# Core Database
CORE_DB="postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
CORE_DB_ASYNC="postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

# AI Database
AI_DB="postgresql://postgres:yaao16yhdsn4jad38lfnkfnbqmqmzysn@metro.proxy.rlwy.net:31246/railway"
AI_DB_ASYNC="postgresql+asyncpg://postgres:yaao16yhdsn4jad38lfnkfnbqmqmzysn@metro.proxy.rlwy.net:31246/railway"
```

### 2.3 Extensions

- **pgcrypto**: Not needed - PostgreSQL 13+ has `gen_random_uuid()` built-in
- **vector**: Created automatically by AI migration (line 29 of `0001_initial_ai_schema.py`)
- **pgvector version**: 0.8.1 (verified)

---

## Phase 3: Run Core Migrations ✅ COMPLETE

### 3.1 Command Used

```bash
cd C:\Users\BenBalbale\CascadeProjects\sigmasight-db-setup

DATABASE_URL="postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway" \
  alembic -c alembic.ini upgrade head
```

### 3.2 Result

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, Initial core database schema (excludes AI tables)
```

### 3.3 Verified

- **38 tables** created (37 core + alembic_version)
- First 10 tables: alembic_version, balance_sheets, batch_job_schedules, batch_jobs, batch_run_tracking, benchmarks_sector_weights, cash_flows, company_profiles, correlation_calculations, correlation_cluster_positions

---

## Phase 4: Run AI Migrations ✅ COMPLETE

**Key Change**: We use Alembic for AI schema (not raw SQL), consistent with Revised document.

### 4.1 Command Used

```bash
cd C:\Users\BenBalbale\CascadeProjects\sigmasight-db-setup

AI_DATABASE_URL="postgresql://postgres:yaao16yhdsn4jad38lfnkfnbqmqmzysn@metro.proxy.rlwy.net:31246/railway" \
DATABASE_URL="postgresql://postgres:yaao16yhdsn4jad38lfnkfnbqmqmzysn@metro.proxy.rlwy.net:31246/railway" \
  alembic -c alembic_ai.ini upgrade head
```

### 4.2 Result

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, Initial AI database schema with pgvector
```

### 4.3 Verified

- **4 tables**: ai_kb_documents, ai_memories, ai_feedback, alembic_version
- **pgvector**: v0.8.1 installed
- **HNSW index**: `ix_ai_kb_documents_embedding_hnsw` confirmed
- All other indexes: ix_ai_kb_documents_scope, ix_ai_kb_documents_created, ix_ai_memories_*, ix_ai_feedback_*

---

## Phase 5: Backup Current Database - SKIPPED

Old database remains untouched until Phase 11 cleanup. It serves as our backup.

---

## Phases 6-7.5: Data Population ✅ COMPLETE

**Approach Used**: Fresh seeding + batch processing (instead of migration script)

### What Was Done

Instead of migrating data from the old database, we:
1. Seeded fresh demo portfolios via `trigger_railway_fix.py`
2. Ran batch processing for July 1 - December 19, 2025

### Batch Processing Results (December 21, 2025)

```
Duration: ~43 minutes (121 trading days)
Portfolios: 11
Positions: 144

Data populated:
- position_factor_exposures: 140,360 rows
- correlation_calculations: 1,067 rows
- portfolio_snapshots: 1,331 rows
- pairwise_correlations: 169,996 rows
- symbol_factor_exposures: 730 rows
- symbol_daily_metrics: 73 rows
```

### Command Used

```bash
cd C:\Users\BenBalbale\CascadeProjects\SigmaSight\backend
python scripts/railway/trigger_railway_fix.py
# Selected date range: July 1, 2025 - December 19, 2025
```

### Note on Migration Script

The original migration script (`migrate_to_new_dbs.py`) was not used. Fresh data was preferred to ensure clean state without legacy issues.

---

## Phase 8: Update Main Repository ✅ COMPLETE

**Commit**: `3be9a32b feat: Dual database architecture (Core + AI separation)`

### 8.1 Rename Migration Folder

```bash
cd /path/to/sigmasight/backend
git mv alembic migrations_core
```

### 8.2 Copy AI Migration Structure from Temp Repo

```bash
# Copy from temp repo
cp -r /path/to/sigmasight-db-setup/migrations_ai .
cp /path/to/sigmasight-db-setup/alembic_ai.ini .
cp /path/to/sigmasight-db-setup/app/models/ai_models.py app/models/
```

### 8.3 Update `alembic.ini`

```ini
[alembic]
script_location = migrations_core
# ... rest unchanged
```

### 8.4 Update `app/config.py`

```python
from typing import Optional

class Settings(BaseSettings):
    # ... existing settings ...

    DATABASE_URL: str
    AI_DATABASE_URL: Optional[str] = None

    @property
    def core_database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def ai_database_url(self) -> str:
        # Fallback for local dev: use same DB if AI_URL not set
        return self.AI_DATABASE_URL or self.DATABASE_URL
```

### 8.5 Update `app/database.py`

```python
"""
Dual database architecture:
- Core: portfolios, positions, calculations, market data, chat
- AI: RAG, memories, feedback (with pgvector)
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

# Core database (high throughput)
core_engine = create_async_engine(
    settings.core_database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=1800
)
CoreSessionLocal = sessionmaker(core_engine, class_=AsyncSession, expire_on_commit=False)

# AI database (heavy/slow queries)
ai_engine = create_async_engine(
    settings.ai_database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800
)
AISessionLocal = sessionmaker(ai_engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def get_core_session() -> AsyncGenerator[AsyncSession, None]:
    async with CoreSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

@asynccontextmanager
async def get_ai_session() -> AsyncGenerator[AsyncSession, None]:
    async with AISessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

# FastAPI dependencies
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_core_session() as session:
        yield session

async def get_ai_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_ai_session() as session:
        yield session

# Backwards compatibility
get_async_session = get_core_session
AsyncSessionLocal = CoreSessionLocal
```

### 8.6 Update `migrations_core/env.py`

Add AI table exclusion (if not already):

```python
AI_TABLES = {'ai_kb_documents', 'ai_memories', 'ai_feedback', 'ai_insights', 'ai_insight_templates'}

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in AI_TABLES:
        return False
    return True
```

### 8.7 Update Services

**RAG Service** (`app/agent/services/rag_service.py`):
```python
from app.database import get_ai_session  # was: get_async_session
```

**Memory Service** (`app/agent/services/memory_service.py`):
```python
from app.database import get_ai_session  # was: get_async_session
```

**Feedback Service** (if exists):
```python
from app.database import get_ai_session

async def create_feedback(message_id: UUID, rating: str):
    # message_id is logical reference to Core DB - no FK
    async with get_ai_session() as session:
        feedback = AIFeedback(message_id=message_id, rating=rating)
        session.add(feedback)
        await session.commit()
```

### 8.8 Update `railway.toml` (Start Command)

```toml
[deploy]
startCommand = "alembic -c alembic.ini upgrade head && alembic -c alembic_ai.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

### 8.9 Commit (DO NOT PUSH)

```bash
git add -A
git commit -m "feat: Dual database architecture (core + AI separation)

- Rename alembic/ to migrations_core/
- Add migrations_ai/ for AI schema (pgvector + HNSW)
- Add alembic_ai.ini for AI database
- Add AI_DATABASE_URL configuration
- Separate database engines for core and AI
- Update RAG/memory services to use AI database
- Add ai_models.py with separate AiBase"

# DO NOT PUSH YET - wait for Phase 9
```

---

## Phase 9: Atomic Swap ✅ COMPLETE

### 9.1 Railway Environment Variables Updated

Railway Dashboard → Main Backend Service → Variables:

1. **DATABASE_URL**: Updated to gondola (Core DB)
   ```
   postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway
   ```

2. **AI_DATABASE_URL**: Added for metro (AI DB)
   ```
   postgresql+asyncpg://postgres:yaao16yhdsn4jad38lfnkfnbqmqmzysn@metro.proxy.rlwy.net:31246/railway
   ```

### 9.2 Main Repo Pushed

Railway auto-redeployed with dual-DB code.

### 9.3 Batch Calculations Executed

Ran via `trigger_railway_fix.py` - see Phase 6-7.5 results.

---

## Phase 10: Verify ✅ COMPLETE (December 21, 2025)

### 10.1 Demo User Login ✅

All 3 demo users verified working:
- `demo_individual@sigmasight.com`
- `demo_hnw@sigmasight.com`
- `demo_hedgefundstyle@sigmasight.com`

### 10.2 Portfolio Data ✅

Portfolio data displays correctly via `/api/v1/data/portfolio/{id}/complete`

### 10.3 Analytics Endpoints ✅

Analytics endpoints returning data with populated calculations.

### 10.4 AI Chat with RAG Retrieval ✅

Tested via `/api/v1/chat/send`:
- Created test conversation
- Sent message "What are my top holdings?"
- Received 6,730 character AI response via SSE streaming
- Tool calls executed: `list_user_portfolios`, `get_portfolio_complete`

### 10.5 Batch Calculations ✅

Successfully processed 121 trading days (July 1 - Dec 19, 2025):
- 140,360 factor exposures calculated
- 1,331 portfolio snapshots created
- No parallelization errors

### 10.6 Railway Logs ✅

No database connection errors found:
- Some 401 auth errors (expired JWT tokens from testing) - expected
- Recent logs show healthy operation
- Tool calls completing successfully (28ms, 387ms)
- OpenAI API calls succeeding

---

## Phase 11: Cleanup - SCHEDULED December 28, 2025

### Verification Checklist (All Passed December 21, 2025)

- [x] All 3 demo users can log in
- [x] Portfolio data displays correctly
- [x] Analytics endpoints working
- [x] AI chat working with RAG retrieval
- [x] Daily batch calculations succeeding
- [x] No database errors in logs

### Delete Old Resources (After December 28, 2025)

1. **Old Railway Database**: Dashboard → Old DB → Settings → Delete
2. **Temp GitHub Repo**: Delete `sigmasight-db-setup`
3. **Backup Files**: `rm *.sql *.dump`

---

## Rollback Plan

If anything breaks after Phase 9:

```bash
# 1. Railway Dashboard → Backend Service → Variables
# 2. Change DATABASE_URL back to OLD database URL
# 3. Remove AI_DATABASE_URL
# 4. Redeploy (or it auto-redeploys)
```

Old database is completely untouched and ready to use.

---

## Timeline

| Phase | Duration | Description | Status |
|-------|----------|-------------|--------|
| 1 | 30 min | Create temp repo | ✅ COMPLETE |
| 2 | 15 min | Create 2 new Railway DBs | ✅ COMPLETE |
| 3 | 20 min | Run Core migrations | ✅ COMPLETE |
| 4 | 15 min | Run AI migrations (Alembic) | ✅ COMPLETE |
| 5 | - | Backup current DB | ⏭️ SKIPPED |
| 6-7.5 | 43 min | Data population (seeding + batch) | ✅ COMPLETE |
| 8 | 45 min | Update main repo code | ✅ COMPLETE |
| 9 | 15 min | Swap (env vars + push) | ✅ COMPLETE |
| 10 | 30 min | Verify everything | ✅ COMPLETE |
| 11 | - | Cleanup | 📅 Dec 28, 2025 |
| **Total** | **~4 hours** | All phases complete except cleanup |

---

## Key Files Changed in Main Repo (Phase 8)

| File | Change |
|------|--------|
| `alembic.ini` | Point to `migrations_core` |
| `alembic_ai.ini` | NEW - AI database config |
| `migrations_core/` | Renamed from `alembic/` |
| `migrations_ai/` | NEW - AI migrations |
| `app/config.py` | Add `AI_DATABASE_URL` |
| `app/database.py` | Dual engine setup |
| `app/models/ai_models.py` | NEW - AiBase models |
| `app/agent/services/rag_service.py` | Use `get_ai_session` |
| `app/agent/services/memory_service.py` | Use `get_ai_session` |
| `railway.toml` | Dual migration start command |
