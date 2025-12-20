# Clean Rebuild Implementation Plan

**Created**: 2025-12-19
**Status**: Ready for Implementation
**Approach**: Temp repo for safe DB setup, then atomic swap

---

## Quick Reference Checklist

```
[ ] Phase 1: Create temp repo (sigmasight-db-setup)
[ ] Phase 2: Create 2 new Railway PostgreSQL databases
[ ] Phase 3: Deploy temp repo → run migrations on new core DB
[ ] Phase 4: Create AI schema via SQL on new AI DB
[ ] Phase 5: Backup current DB (safety net only)
[ ] Phase 6: Import AI data (optional - only if valuable content exists)
[ ] Phase 7: Seed demo portfolios to new core DB
[ ] Phase 7.5: Copy market data from old DB (script-based, not pg_dump)
[ ] Phase 8: Update main repo code (commit, DO NOT PUSH)
[ ] Phase 9: Swap env vars + push main repo (atomic)
[ ] Phase 10: Verify all features working
[ ] Phase 11: Cleanup (after 1 week)
```

---

## Strategy Overview

**Problem**: Pushing Alembic changes to main repo would run migrations against production DB.

**Solution**: Use a temporary repo to create schemas on new databases, then swap.

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
│   Temp Repo ────► Temp Service ────► New Core DB (empty → schema)       │
│   (minimal)       (delete after)                                        │
│                                                                         │
│   SQL Script ───────────────────────► New AI DB (pgvector + schema)     │
│                                                                         │
│   Seed Script ─────────────────────► demo portfolios ────► New Core DB  │
│                                                                         │
│   Python Script ──► reads Old DB ──► writes to ──────────► New Core DB  │
│   (migrate_market_data.py)           market_data, profiles, fundamentals│
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ ATOMIC SWAP (Phase 9) - All at once                                     │
│                                                                         │
│   1. Update Railway env vars (DATABASE_URL → new core, add AI_DATABASE_URL)
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

## Phase 1: Create Temporary Repository (30 min)

### 1.1 Create Minimal Repo Structure

```bash
mkdir sigmasight-db-setup
cd sigmasight-db-setup
git init

mkdir -p alembic/versions
mkdir -p app/models
```

### 1.2 Files to Copy from Main Repo

Copy these files, modifying as noted:

| Source | Destination | Modifications |
|--------|-------------|---------------|
| `backend/alembic.ini` | `alembic.ini` | Update path |
| `backend/alembic/script.py.mako` | `alembic/script.py.mako` | None |
| `backend/alembic/versions/*.py` | `alembic/versions/` | **EXCLUDE** AI migrations (see below) |
| `backend/app/models/*.py` | `app/models/` | **EXCLUDE** `ai_learning.py` |

**DO NOT COPY these migration files:**
- `l9m0n1o2p3q4_add_ai_learning_tables.py`
- `m9n0o1p2q3r4_switch_to_hnsw_index.py`

### 1.3 Create Minimal Files

**`app/__init__.py`**
```python
# empty
```

**`app/config.py`**
```python
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    class Config:
        env_file = ".env"

settings = Settings()
```

**`app/database.py`**
```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

**`app/models/__init__.py`**
```python
# Import all models EXCEPT ai_learning
from app.models.users import *
from app.models.positions import *
from app.models.market_data import *
from app.models.correlations import *
from app.models.snapshots import *
from app.models.tags_v2 import *
from app.models.position_tags import *
from app.models.target_prices import *
from app.models.batch_tracking import *
from app.models.fundamentals import *
from app.models.history import *
from app.models.equity_changes import *
from app.models.position_realized_events import *
from app.models.modeling import *
# DO NOT import ai_learning, ai_insights
```

**`alembic/env.py`**
```python
from logging.config import fileConfig
from sqlalchemy import create_engine
from alembic import context

from app.database import Base
from app.config import settings
from app.models import *  # noqa - imports all models

config = context.config

# Use sync driver for alembic
db_url = settings.DATABASE_URL.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# CRITICAL: Exclude AI tables
AI_TABLES = {'ai_kb_documents', 'ai_memories', 'ai_feedback', 'ai_insights', 'ai_insight_templates'}

def include_object(object, name, type_, reflected, compare_to):
    """Exclude AI tables from migrations."""
    if type_ == "table" and name in AI_TABLES:
        return False
    return True

def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = create_engine(config.get_main_option("sqlalchemy.url"))
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**`pyproject.toml`**
```toml
[project]
name = "sigmasight-db-setup"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "alembic>=1.13.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "pydantic-settings>=2.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**`railway.toml`**
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "alembic upgrade head"
```

### 1.4 Push Temp Repo

```bash
git add -A
git commit -m "Temp repo for core database schema setup"
git remote add origin https://github.com/YOUR_ORG/sigmasight-db-setup.git
git push -u origin main
```

---

## Phase 2: Create New Databases on Railway (15 min)

### 2.1 Create Core Database

1. Railway Dashboard → **+ New** → **Database** → **PostgreSQL**
2. Name: `sigmasight-core`
3. Wait for provisioning
4. Copy credentials:

```bash
# Save these for later
CORE_DB="postgresql://user:pass@host:port/railway"
CORE_DB_ASYNC="postgresql+asyncpg://user:pass@host:port/railway"
```

### 2.2 Create AI Database

1. Railway Dashboard → **+ New** → **Database** → **PostgreSQL**
2. Name: `sigmasight-ai`
3. Wait for provisioning
4. Copy credentials:

```bash
AI_DB="postgresql://user:pass@host:port/railway"
AI_DB_ASYNC="postgresql+asyncpg://user:pass@host:port/railway"
```

### 2.3 Enable pgvector on AI Database

**Railway PostgreSQL includes pgvector** - it's pre-installed, we just need to enable it:

```bash
psql "$AI_DB" << 'EOF'
-- Enable pgvector extension (included in Railway PostgreSQL)
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
EOF
```

Expected output: `vector | 0.7.x` or `0.8.x`

**Note**: This is all that's needed for pgvector. The extension provides the `vector` data type and operators (`<->`, `<#>`, `<=>`) used in Phase 4 for the AI tables. No separate "vector database" service required - it's just PostgreSQL with an extension.

### 2.4 Enable pgcrypto on BOTH databases (UUID generation)

`gen_random_uuid()` is used throughout the schemas. Ensure the extension exists on the new core and AI DBs before creating any tables:

```bash
# Core DB
psql "$CORE_DB" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# AI DB
psql "$AI_DB" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
```

---

## Phase 3: Run Migrations via Temp Repo (20 min)

### 3.1 Option A: Deploy Temp Service to Railway

1. Railway Dashboard → **+ New** → **GitHub Repo**
2. Select: `sigmasight-db-setup`
3. Name: `db-setup-temp`
4. Set environment variable:
   - `DATABASE_URL` = `$CORE_DB` (the NEW core database URL)
5. Railway deploys and runs `alembic upgrade head`

### 3.2 Option B: Run Locally

```bash
cd sigmasight-db-setup
export DATABASE_URL="$CORE_DB"
pip install -e .
alembic upgrade head
```

### 3.3 Verify Core Schema

```bash
# List all tables (should NOT include ai_* tables)
psql "$CORE_DB" -c "\dt"

# Verify NO pgvector extension
psql "$CORE_DB" -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
# Expected: 0 rows

# Check table count (should be ~35-40 tables)
psql "$CORE_DB" -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
```

### 3.4 Delete Temp Railway Service

If you used Option A:
1. Railway Dashboard → `db-setup-temp` → Settings → **Delete Service**

---

## Phase 4: Create AI Database Schema (10 min)

### Why SQL Script (Not a Temp Repo) for AI Database?

| Factor | Core Database | AI Database |
|--------|---------------|-------------|
| **Schema complexity** | 35+ tables with relationships | 3 simple tables |
| **Migration history** | 20+ Alembic migrations | None (fresh) |
| **Dependencies** | Complex FK relationships | Standalone tables |
| **Extension** | None | pgvector (installed via SQL) |
| **Approach** | Temp repo + Alembic | Direct SQL script |

The AI database doesn't need a temp repo because:
1. **No migration chain** - Fresh schema, no historical state to preserve
2. **Simple structure** - Only 3 tables with no foreign keys to core tables
3. **pgvector setup** - Extension installation is a single SQL command
4. **HNSW index** - Created via SQL, not Alembic migration

```bash
psql "$AI_DB" << 'EOF'
-- Verify pgvector
SELECT extname FROM pg_extension WHERE extname = 'vector';

-- ai_kb_documents (RAG knowledge base)
CREATE TABLE ai_kb_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_ai_kb_documents_scope ON ai_kb_documents(scope);
CREATE INDEX ix_ai_kb_documents_created ON ai_kb_documents(created_at DESC);
CREATE INDEX ix_ai_kb_documents_embedding_hnsw
    ON ai_kb_documents USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ai_memories (user preferences/rules)
CREATE TABLE ai_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    tenant_id UUID,
    scope VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_ai_memories_scope ON ai_memories(scope);
CREATE INDEX ix_ai_memories_user_id ON ai_memories(user_id);
CREATE INDEX ix_ai_memories_tenant_id ON ai_memories(tenant_id);

-- ai_feedback (user ratings)
CREATE TABLE ai_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL,
    rating VARCHAR(10) NOT NULL,
    edited_text TEXT,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_ai_feedback_message_id ON ai_feedback(message_id);
CREATE INDEX ix_ai_feedback_rating ON ai_feedback(rating);

-- Verify
\dt
SELECT 'AI schema created successfully' as status;
EOF
```

### 4.1 Set a lightweight AI schema migration path

Even if AI tables are simple, store the above SQL as versioned scripts (e.g., `ai_migrations/V1__init.sql`, `V2__add_index.sql`) and record the latest applied version in a small table (`ai_schema_version`). This avoids drift when the AI schema evolves after go-live.

---

## Phase 5: Backup Current Database (5 min)

### 5.1 Full Backup (Safety Net)

Take a full logical backup in case anything is needed later:

```bash
# Get current DB URL
CURRENT_DB=$(railway variables --json | jq -r '.DATABASE_URL' | sed 's/postgresql+asyncpg/postgresql/')

# Full backup
pg_dump "$CURRENT_DB" -Fc -f full_backup_before_split.dump
```

### 5.2 Data Strategy: Script Copy vs pg_dump

| Data Type | Strategy | Rationale |
|-----------|----------|-----------|
| **Market Data** (`market_data_cache`) | ✅ Script copy from old DB | Data exists; faster than API; cleaner than pg_dump |
| **Company Profiles** | ✅ Script copy from old DB | Preserves existing data |
| **Fundamentals** (income, balance, cash flow) | ✅ Script copy from old DB | Historical data worth preserving |
| **Benchmarks** (`benchmarks_sector_weights`) | ✅ Script copy from old DB | Reference data |
| **AI Knowledge Base** (`ai_kb_documents`) | ⚠️ Decision needed | If curated content exists, export; otherwise start fresh |
| **AI Memories** (`ai_memories`) | ⚠️ Decision needed | User preferences; export if valuable |
| **AI Feedback** (`ai_feedback`) | 🔄 Start fresh | Low value; avoids orphan references |

### 5.3 Export AI Data (Optional - Only if Valuable Content Exists)

```bash
# Only run if you have curated RAG documents worth preserving
pg_dump "$CURRENT_DB" --data-only --no-owner \
    --table=ai_kb_documents \
    --table=ai_memories \
    -f ai_data.sql

ls -lh ai_data.sql
```

---

## Phase 6: Import AI Data (Optional) (10 min)

**Skip this phase if starting with fresh AI database.**

### 6.1 Import to AI Database (Only if Exported)

```bash
# Only if you ran 5.3
psql "$AI_DB" -f ai_data.sql

# Verify
psql "$AI_DB" -c "SELECT COUNT(*) as kb_docs FROM ai_kb_documents;"
psql "$AI_DB" -c "SELECT COUNT(*) as memories FROM ai_memories;"

# Optimize
psql "$AI_DB" -c "ANALYZE;"
```

### 6.2 If Starting Fresh

No import needed - AI tables are created empty in Phase 4. The RAG system will build knowledge over time through user interactions.

---

## Phase 7: Seed Demo Portfolios (30 min)

### 7.1 Run Seed Script

```bash
cd /path/to/sigmasight/backend

# Point to NEW core database (use asyncpg URL)
export DATABASE_URL="$CORE_DB_ASYNC"

# Seed demo data
uv run python scripts/database/reset_and_seed.py seed
```

> Ensure the new core DB is a clean environment (no real user data) before seeding. If real data will exist pre-cutover, replace this step with targeted seed routines that avoid collisions.

### 7.2 Verify Demo Data

```bash
psql "$CORE_DB" << 'EOF'
SELECT u.email, p.name as portfolio, COUNT(pos.id) as positions
FROM users u
JOIN portfolios p ON p.user_id = u.id
JOIN positions pos ON pos.portfolio_id = p.id
GROUP BY u.email, p.name
ORDER BY u.email;
EOF
```

**Expected:**
```
demo_hedgefundstyle@sigmasight.com | Long/Short Equity Hedge Fund Style Portfolio | 30
demo_hnw@sigmasight.com            | Sophisticated High Net Worth Portfolio        | 17
demo_individual@sigmasight.com     | Balanced Individual Investor Portfolio        | 16
```

---

## Phase 7.5: Copy Market Data from Old DB (30 min)

**Why copy from old DB instead of re-fetching from APIs?**
- Data already exists - no need for API calls
- Faster than fetching from YFinance/FMP
- Avoids rate limits and API failures
- Cleaner than pg_dump (programmatic, can transform if needed)

### 7.5.1 Create Data Migration Script

Create `scripts/database/migrate_market_data.py`:

```python
"""
Copy market data from old database to new database.
Run with both DATABASE_URL (old) and NEW_DATABASE_URL (new) set.
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Connection URLs
OLD_DB_URL = os.environ["OLD_DATABASE_URL"]
NEW_DB_URL = os.environ["NEW_DATABASE_URL"]

# Tables to copy (market data only - user data comes from seed)
TABLES_TO_COPY = [
    "market_data_cache",
    "company_profiles",
    "income_statements",
    "balance_sheets",
    "cash_flows",
    "benchmarks_sector_weights",
]

async def copy_table(old_session: AsyncSession, new_session: AsyncSession, table: str):
    """Copy all rows from old DB table to new DB table."""
    print(f"Copying {table}...")

    # Get all rows from old DB
    result = await old_session.execute(text(f"SELECT * FROM {table}"))
    rows = result.fetchall()
    columns = result.keys()

    if not rows:
        print(f"  ⚠ {table}: no rows to copy")
        return 0

    # Build INSERT statement
    col_names = ", ".join(columns)
    placeholders = ", ".join([f":{col}" for col in columns])
    insert_sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    # Insert in batches
    batch_size = 1000
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        for row in batch:
            await new_session.execute(text(insert_sql), dict(zip(columns, row)))
        await new_session.commit()
        total += len(batch)
        print(f"  {table}: {total}/{len(rows)} rows")

    print(f"  ✓ {table}: {total} rows copied")
    return total

async def main():
    # Create engines
    old_engine = create_async_engine(OLD_DB_URL)
    new_engine = create_async_engine(NEW_DB_URL)

    OldSession = sessionmaker(old_engine, class_=AsyncSession, expire_on_commit=False)
    NewSession = sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)

    async with OldSession() as old_db, NewSession() as new_db:
        for table in TABLES_TO_COPY:
            try:
                await copy_table(old_db, new_db, table)
            except Exception as e:
                print(f"  ✗ {table}: {e}")

    # Cleanup
    await old_engine.dispose()
    await new_engine.dispose()
    print("\n✓ Migration complete!")

if __name__ == "__main__":
    asyncio.run(main())
```

### 7.5.2 Run the Migration Script

```bash
cd /path/to/sigmasight/backend

# Set both database URLs
export OLD_DATABASE_URL="postgresql+asyncpg://user:pass@OLD_HOST:port/railway"
export NEW_DATABASE_URL="$CORE_DB_ASYNC"

# Run the migration
uv run python scripts/database/migrate_market_data.py
```

### 7.5.3 Run Batch Calculations (to populate analytics)

After market data is copied, run batch to calculate derived data:

```bash
export DATABASE_URL="$CORE_DB_ASYNC"
uv run python scripts/run_batch_calculations.py
```

This will calculate betas, factors, volatility, correlations using the copied market data.

### 7.5.4 Verify Data Migration

```bash
psql "$CORE_DB" << 'EOF'
-- Check market data cache
SELECT COUNT(*) as total_rows,
       COUNT(DISTINCT symbol) as unique_symbols,
       MIN(date) as earliest_date,
       MAX(date) as latest_date
FROM market_data_cache;

-- Check company profiles
SELECT COUNT(*) as profiles FROM company_profiles;

-- Check fundamentals
SELECT
    (SELECT COUNT(*) FROM income_statements) as income,
    (SELECT COUNT(*) FROM balance_sheets) as balance,
    (SELECT COUNT(*) FROM cash_flows) as cashflow;

-- Check calculation results (populated by batch)
SELECT
    (SELECT COUNT(*) FROM position_greeks) as greeks,
    (SELECT COUNT(*) FROM position_factor_exposures) as factor_exposures,
    (SELECT COUNT(*) FROM position_market_betas) as betas;
EOF
```

---

## Phase 8: Update Main Repository (45 min)

**IMPORTANT: Commit changes but DO NOT PUSH until Phase 9**

### AI page / agent impact checklist (required before coding)

- Config: Add `AI_DATABASE_URL` (default to core only for dev), expose `core_database_url` and `ai_database_url` helpers.
- Database: Create dual async engines/sessions and FastAPI dependencies for core vs AI; apply the Railway-friendly pool/timeout settings to both engines.
- Alembic: Keep AI tables excluded via `include_object`; AI schema changes must live in versioned SQL (see Phase 4.1) to avoid drift.
- Services: Point RAG and memory services to `get_ai_session`; audit any other AI helpers to ensure they use AI DB, not core.
- Data placement: Decide where chat/conversation/message rows live; if `ai_feedback.message_id` references them, ensure those rows stay reachable (same DB or migrated together) to avoid orphaned feedback on the AI page.
- Health/observability: Add/verify a separate AI DB health check and log fields that distinguish core vs AI connection errors; ensure AI endpoints fail fast with clear errors if AI DB is unavailable.

### 8.1 Update `backend/app/config.py`

Add AI_DATABASE_URL:

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
        return self.AI_DATABASE_URL or self.DATABASE_URL
```

### 8.2 Update `backend/app/database.py`

```python
"""
Dual database architecture:
- Core: portfolios, positions, calculations, market data
- AI: RAG, memories, feedback (with pgvector)
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

# Core database
core_engine = create_async_engine(
    settings.core_database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
CoreSessionLocal = sessionmaker(core_engine, class_=AsyncSession, expire_on_commit=False)

# AI database
ai_engine = create_async_engine(
    settings.ai_database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
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

### 8.3 Update `backend/alembic/env.py`

Add AI table exclusion:

```python
# Near top of file
AI_TABLES = {'ai_kb_documents', 'ai_memories', 'ai_feedback', 'ai_insights', 'ai_insight_templates'}

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in AI_TABLES:
        return False
    return True

# In run_migrations_online(), add to context.configure():
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_object=include_object,  # ADD THIS LINE
    # ... rest of config
)
```

### 8.4 Update RAG Service

Edit `backend/app/agent/services/rag_service.py`:

```python
# Change import at top
from app.database import get_ai_session  # was: get_async_session
```

### 8.5 Update Memory Service

Edit `backend/app/agent/services/memory_service.py`:

```python
# Change import at top
from app.database import get_ai_session  # was: get_async_session
```

### 8.6 Commit (DO NOT PUSH)

```bash
git add -A
git commit -m "feat: Dual database architecture (core + AI separation)

- Add AI_DATABASE_URL configuration
- Separate database engines for core and AI
- Update alembic to exclude AI tables
- Update RAG/memory services to use AI database"

# DO NOT PUSH YET - wait for Phase 9
```

### 8.7 Connection settings tuned for Railway

Set conservative pool and timeout values to match Railway limits and avoid idle locks (adjust if you measure different needs):

```
SQLALCHEMY_POOL_SIZE=10
SQLALCHEMY_MAX_OVERFLOW=5
SQLALCHEMY_POOL_RECYCLE=1800
SQLALCHEMY_POOL_PRE_PING=true
STATEMENT_TIMEOUT_MS=20000
IDLE_IN_TRANSACTION_TIMEOUT_MS=10000
```

Apply these to both engines (core + AI) when configuring `create_async_engine`.

---

## Phase 9: Atomic Swap (15 min)

**Do these steps in quick succession:**

### 9.0 Rehearsal (strongly recommended)

Spin up a throwaway Railway backend service that points to the new core/AI URLs and the dual-DB code branch. Deploy once, run health checks, and validate chat + analytics before touching the main service.

### 9.1 Update Railway Environment Variables

Railway Dashboard → Main Backend Service → Variables:

1. **Update** `DATABASE_URL`:
   ```
   postgresql+asyncpg://user:pass@NEW_CORE_HOST:port/railway
   ```

2. **Add** `AI_DATABASE_URL`:
   ```
   postgresql+asyncpg://user:pass@NEW_AI_HOST:port/railway
   ```

### 9.2 Push Main Repo

```bash
git push origin main
```

Railway will automatically redeploy with new code pointing to new databases.

### 9.3 Run Batch Calculations

After deployment completes (~2-3 min):

```bash
# Option A: Railway CLI
railway run python scripts/run_batch_calculations.py

# Option B: API
curl -X POST https://your-api.railway.app/api/v1/admin/batch/run \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Phase 10: Verify (30 min)

### 10.1 Health Check

```bash
curl https://your-api.railway.app/api/v1/health
```

### 10.2 Authentication

```bash
curl -X POST https://your-api.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_hnw@sigmasight.com", "password": "demo12345"}'
```

### 10.3 Portfolio Data

```bash
# Get token from login response, then:
curl https://your-api.railway.app/api/v1/data/portfolio/{portfolio_id}/complete \
  -H "Authorization: Bearer $TOKEN"
```

### 10.4 AI Chat (Tests AI Database)

```bash
# Create conversation
CONV=$(curl -s -X POST https://your-api.railway.app/api/v1/chat/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test"}')

# Send message (tests RAG retrieval from AI DB)
curl -X POST "https://your-api.railway.app/api/v1/chat/conversations/{conv_id}/send" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "What is my portfolio risk?"}'
```

### 10.4.1 AI DB health and integrity

- Hit a lightweight AI DB health endpoint (or add one) that checks `AI_DATABASE_URL` connectivity and a simple `SELECT 1`.
- Confirm row counts match pre-migration for `ai_kb_documents`, `ai_memories`, `ai_feedback`; spot-check a few records for expected metadata.
- If feedback references chat messages, verify referenced message rows exist in the chosen database.

### 10.5 Check Logs

```bash
railway logs --service sigmasight-be | head -100
# Look for any database connection errors
```

---

## Phase 11: Cleanup (After 1 Week)

### Verification Checklist

Wait 1 week with all boxes checked:

- [ ] All 3 demo users can log in
- [ ] Portfolio data displays correctly
- [ ] Analytics endpoints working
- [ ] AI chat working with RAG retrieval
- [ ] Daily batch calculations succeeding
- [ ] No database errors in logs

### Delete Old Resources

1. **Old Railway Database**: Dashboard → Old DB → Settings → Delete
2. **Temp GitHub Repo**: Delete `sigmasight-db-setup`
3. **Backup Files**: `rm *.sql`

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

| Phase | Duration | Description |
|-------|----------|-------------|
| 1 | 30 min | Create temp repo |
| 2 | 15 min | Create 2 new Railway DBs |
| 3 | 20 min | Run migrations (temp repo) |
| 4 | 10 min | Create AI schema (SQL) |
| 5 | 5 min | Backup current DB (safety net) |
| 6 | 10 min | Import AI data (optional) |
| 7 | 30 min | Seed demo portfolios |
| 7.5 | 30 min | Copy market data from old DB |
| 8 | 45 min | Update main repo code |
| 9 | 15 min | Swap (env vars + push) |
| 10 | 30 min | Verify everything |
| **Total** | **~4 hours** | Plus 1 week before cleanup |

---

## Key Files Changed in Main Repo

| File | Change |
|------|--------|
| `app/config.py` | Add `AI_DATABASE_URL` property |
| `app/database.py` | Dual engine setup |
| `alembic/env.py` | Add `include_object` filter |
| `app/agent/services/rag_service.py` | Use `get_ai_session` |
| `app/agent/services/memory_service.py` | Use `get_ai_session` |
