# Database Migration Plan: Dual Fresh Database Architecture

**Created**: 2025-12-19
**Updated**: 2025-12-19
**Status**: Ready for Implementation
**Related**: [DATABASE_SEPARATION_ANALYSIS.md](./DATABASE_SEPARATION_ANALYSIS.md)

---

## Overview

This document provides a step-by-step migration plan to create two fresh PostgreSQL databases on Railway, separating AI/RAG vector workloads from core application data.

### Migration Approach: Two Fresh Databases

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Current DB        │     │   New Core DB       │     │   New AI DB         │
│   (to be retired)   │────▶│   sigmasight-core   │     │   sigmasight-ai     │
│                     │     │                     │     │                     │
│ • All tables        │     │ • users             │     │ • ai_kb_documents   │
│ • pgvector ext      │     │ • portfolios        │     │ • ai_memories       │
│ • Mixed workloads   │     │ • positions         │     │ • ai_feedback       │
│                     │     │ • calculations      │     │                     │
│                     │     │ • market_data       │     │ • pgvector ext      │
│                     │     │ • NO pgvector       │     │ • HNSW indexes      │
│                     │     │ • OLTP optimized    │     │ • Vector optimized  │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

### Why Two Fresh Databases?

| Benefit | Description |
|---------|-------------|
| **Clean separation** | Core DB never has pgvector extension |
| **Optimal tuning** | Configure each DB for its workload from start |
| **No cleanup** | No need to drop tables from old DB |
| **No legacy cruft** | Fresh schema, fresh indexes |
| **Simple cutover** | Update env vars, redeploy, done |

---

## Table Distribution

### Core Database (sigmasight-core) - 40+ tables

**User & Portfolio Data:**
- `users`
- `portfolios`
- `positions`
- `tags` / `tags_v2`
- `position_tags`
- `portfolio_target_prices`

**Calculation Results:**
- `position_greeks`
- `position_factor_exposures`
- `position_market_betas`
- `position_volatility`
- `position_interest_rate_betas`
- `correlation_calculations`
- `pairwise_correlations`
- `correlation_clusters`
- `correlation_cluster_positions`
- `factor_correlations`
- `factor_exposures`
- `factor_definitions`
- `portfolio_snapshots`
- `stress_test_scenarios`
- `stress_test_results`
- `market_risk_scenarios`

**Market Data:**
- `market_data_cache`
- `company_profiles`
- `benchmarks_sector_weights`
- `fund_holdings`

**System:**
- `batch_jobs`
- `batch_job_schedules`
- `batch_run_tracking`
- `export_history`
- `modeling_session_snapshots`
- `equity_changes`
- `position_realized_events`

**Fundamentals:**
- `income_statements`
- `balance_sheets`
- `cash_flows`

**Chat/Agent (non-vector):**
- `agent_conversations`
- `agent_messages`

### AI Database (sigmasight-ai) - 3 tables

- `ai_kb_documents` (with 1536-dim vector embeddings)
- `ai_memories`
- `ai_feedback`

---

## Phase 1: Preparation (1 hour)

### Step 1.1: Capture Baseline Metrics

```bash
# Run on Railway to capture current performance
cd backend
railway run python scripts/railway/pgvector_performance_diagnostic.py > baseline_metrics.txt

# Record batch calculation time
time railway run python scripts/run_batch_calculations.py
```

Document these metrics:
- [ ] Batch calculation time (full run): _____ seconds
- [ ] RAG query latency (p50): _____ ms
- [ ] Database memory usage: _____ MB
- [ ] Vector index scan count: _____

### Step 1.2: Get Current Database Credentials

```bash
# Get current Railway database connection info
railway variables

# Note the current DATABASE_URL
# Format: postgresql://user:pass@host:port/railway
```

### Step 1.3: Create Export Directory

```bash
mkdir -p db_migration_exports
cd db_migration_exports
```

---

## Phase 2: Create Two New Databases on Railway (20 min)

### Step 2.1: Create Core Database

1. Railway Dashboard → **+ New** → **Database** → **PostgreSQL**
2. Name: `sigmasight-core-db`
3. Wait for provisioning (~1 min)
4. Copy connection credentials:
   - `CORE_DATABASE_URL` = `postgresql://...`

### Step 2.2: Create AI Database

1. Railway Dashboard → **+ New** → **Database** → **PostgreSQL**
2. Name: `sigmasight-ai-db`
3. Wait for provisioning (~1 min)
4. Copy connection credentials:
   - `AI_DATABASE_URL` = `postgresql://...`

### Step 2.3: Enable pgvector on AI Database Only

```bash
# Connect to AI database only
psql "$AI_DATABASE_URL"

# Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

# Verify
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
# Expected: vector | 0.7.0 (or similar)

\q
```

**Important**: Do NOT enable pgvector on the core database.

---

## Phase 3: Export All Data from Current Database (30 min)

### Step 3.1: Full Schema and Data Export

```bash
# Get current database URL (convert asyncpg to standard)
CURRENT_DB_URL=$(echo $DATABASE_URL | sed 's/postgresql+asyncpg/postgresql/')

# Export entire database (schema + data)
pg_dump "$CURRENT_DB_URL" \
  --no-owner \
  --no-acl \
  --format=plain \
  --file=full_database_backup.sql

# Export just schema (for reference)
pg_dump "$CURRENT_DB_URL" \
  --schema-only \
  --no-owner \
  --file=schema_only.sql
```

### Step 3.2: Export Tables by Category

Create `scripts/database/export_for_migration.sh`:

```bash
#!/bin/bash
# Export tables split by destination database
# Usage: ./export_for_migration.sh <current_db_url>

CURRENT_DB_URL=$1

if [ -z "$CURRENT_DB_URL" ]; then
    echo "Usage: $0 <database_url>"
    exit 1
fi

# Convert asyncpg URL to standard psql format
DB_URL=$(echo $CURRENT_DB_URL | sed 's/postgresql+asyncpg/postgresql/')

echo "=== Exporting Core Tables ==="

# Core tables (everything except AI tables)
CORE_TABLES=(
    "users"
    "portfolios"
    "positions"
    "tags"
    "tags_v2"
    "position_tags"
    "portfolio_target_prices"
    "position_greeks"
    "position_factor_exposures"
    "position_market_betas"
    "position_volatility"
    "position_interest_rate_betas"
    "correlation_calculations"
    "pairwise_correlations"
    "correlation_clusters"
    "correlation_cluster_positions"
    "factor_correlations"
    "factor_exposures"
    "factor_definitions"
    "portfolio_snapshots"
    "stress_test_scenarios"
    "stress_test_results"
    "market_risk_scenarios"
    "market_data_cache"
    "company_profiles"
    "benchmarks_sector_weights"
    "fund_holdings"
    "batch_jobs"
    "batch_job_schedules"
    "batch_run_tracking"
    "export_history"
    "modeling_session_snapshots"
    "equity_changes"
    "position_realized_events"
    "income_statements"
    "balance_sheets"
    "cash_flows"
    "agent_conversations"
    "agent_messages"
)

# Build table list for pg_dump
CORE_TABLE_ARGS=""
for table in "${CORE_TABLES[@]}"; do
    CORE_TABLE_ARGS="$CORE_TABLE_ARGS --table=$table"
done

pg_dump "$DB_URL" \
    --no-owner \
    --no-acl \
    --format=plain \
    --data-only \
    $CORE_TABLE_ARGS \
    --file=core_tables_data.sql

echo "Core tables exported to core_tables_data.sql"

echo "=== Exporting AI Tables ==="

# AI tables (with vector data)
pg_dump "$DB_URL" \
    --no-owner \
    --no-acl \
    --format=plain \
    --data-only \
    --table=ai_kb_documents \
    --table=ai_memories \
    --table=ai_feedback \
    --file=ai_tables_data.sql

echo "AI tables exported to ai_tables_data.sql"

echo "=== Export Complete ==="
ls -la *.sql
```

### Step 3.3: Run Export

```bash
chmod +x scripts/database/export_for_migration.sh
./scripts/database/export_for_migration.sh "$DATABASE_URL"
```

### Step 3.4: Verify Exports

```bash
# Check file sizes
ls -lh *.sql

# Count records in exports
grep -c "^INSERT" core_tables_data.sql
grep -c "^INSERT" ai_tables_data.sql
```

---

## Phase 4: Create Schemas in New Databases (30 min)

### Step 4.1: Create Core Database Schema

**IMPORTANT**: We cannot run `alembic upgrade head` directly because it includes migrations that:
1. Create pgvector extension (not needed on core DB)
2. Create AI tables (should only be on AI DB)

**Solution**: Export schema from current DB, excluding AI components.

```bash
# Convert URL format for pg_dump
CURRENT_DB=$(echo $DATABASE_URL | sed 's/postgresql+asyncpg/postgresql/')
CORE_DB=$(echo $CORE_DATABASE_URL | sed 's/postgresql+asyncpg/postgresql/')

# Export schema excluding AI tables and pgvector extension
pg_dump "$CURRENT_DB" \
  --schema-only \
  --no-owner \
  --no-acl \
  --exclude-table=ai_kb_documents \
  --exclude-table=ai_memories \
  --exclude-table=ai_feedback \
  > full_schema.sql

# Remove pgvector-related lines from schema
grep -v -E "(CREATE EXTENSION.*vector|vector\(1536\)|USING (ivfflat|hnsw).*vector)" \
  full_schema.sql > core_schema_clean.sql

# Import clean schema to new core DB
psql "$CORE_DB" -f core_schema_clean.sql

# Verify tables created (should NOT include ai_* tables)
psql "$CORE_DB" -c "\dt"

# Verify pgvector is NOT installed
psql "$CORE_DB" -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
# Should return 0 rows
```

**Alternative: Manual Schema Cleanup Script**

If the grep approach misses something, create `scripts/database/clean_core_schema.py`:

```python
#!/usr/bin/env python
"""
Clean schema SQL file for core database.
Removes AI tables and pgvector references.
"""
import re
import sys

def clean_schema(input_file: str, output_file: str):
    with open(input_file, 'r') as f:
        content = f.read()

    # Patterns to remove
    patterns = [
        # pgvector extension
        r'CREATE EXTENSION IF NOT EXISTS vector;?\n?',
        # AI tables (full CREATE TABLE blocks)
        r'CREATE TABLE public\.ai_kb_documents[\s\S]*?;\n\n',
        r'CREATE TABLE public\.ai_memories[\s\S]*?;\n\n',
        r'CREATE TABLE public\.ai_feedback[\s\S]*?;\n\n',
        # AI indexes
        r'CREATE INDEX.*ai_kb_documents.*;\n',
        r'CREATE INDEX.*ai_memories.*;\n',
        r'CREATE INDEX.*ai_feedback.*;\n',
        # Vector column references
        r'.*vector\(1536\).*\n',
        # HNSW/IVFFlat indexes
        r'CREATE INDEX.*USING (hnsw|ivfflat).*vector.*;\n',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)

    with open(output_file, 'w') as f:
        f.write(content)

    print(f"Cleaned schema written to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python clean_core_schema.py <input.sql> <output.sql>")
        sys.exit(1)
    clean_schema(sys.argv[1], sys.argv[2])
```

Usage:
```bash
python scripts/database/clean_core_schema.py full_schema.sql core_schema_clean.sql
psql "$CORE_DB" -f core_schema_clean.sql
```

### Step 4.1b: Mark Alembic Migration State

After importing schema, we need to tell Alembic that migrations have been applied:

```bash
# Get the latest migration revision from current DB
LATEST_REV=$(psql "$CURRENT_DB" -t -c "SELECT version_num FROM alembic_version;")

# Create alembic_version table in new core DB with same revision
psql "$CORE_DB" -c "
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('$LATEST_REV');
"

# Verify
psql "$CORE_DB" -c "SELECT * FROM alembic_version;"
```

This prevents Alembic from trying to re-run migrations on the new core DB.

### Step 4.2: Create AI Database Schema

Create `scripts/database/create_ai_schema.sql`:

```sql
-- AI Database Schema for SigmaSight
-- Run this on sigmasight-ai-db instance
-- pgvector extension should already be enabled

-- ai_kb_documents: RAG knowledge base with embeddings
CREATE TABLE IF NOT EXISTS ai_kb_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Indexes for ai_kb_documents
CREATE INDEX IF NOT EXISTS ix_ai_kb_documents_scope
ON ai_kb_documents(scope);

-- HNSW index for vector similarity (better than IVFFlat for our scale)
CREATE INDEX IF NOT EXISTS ix_ai_kb_documents_embedding_hnsw
ON ai_kb_documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ai_memories: Persistent rules and preferences
CREATE TABLE IF NOT EXISTS ai_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,  -- Soft reference to users table in core DB
    tenant_id UUID,
    scope VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_memories_scope ON ai_memories(scope);
CREATE INDEX IF NOT EXISTS ix_ai_memories_user_id ON ai_memories(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_memories_tenant_id ON ai_memories(tenant_id);

-- ai_feedback: User feedback on AI responses
CREATE TABLE IF NOT EXISTS ai_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL,  -- Soft reference to agent_messages in core DB
    rating VARCHAR(10) NOT NULL,
    edited_text TEXT,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_feedback_message_id ON ai_feedback(message_id);
CREATE INDEX IF NOT EXISTS ix_ai_feedback_rating ON ai_feedback(rating);

-- Verify setup
SELECT 'Schema created successfully' as status;
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

Run schema creation:

```bash
psql "$AI_DATABASE_URL" -f scripts/database/create_ai_schema.sql
```

---

## Phase 5: Import Data to New Databases (45 min)

### Step 5.1: Import Core Data

```bash
# Disable foreign key checks during import for speed
psql "$CORE_DATABASE_URL" -c "SET session_replication_role = 'replica';"

# Import core tables data
psql "$CORE_DATABASE_URL" -f core_tables_data.sql

# Re-enable foreign key checks
psql "$CORE_DATABASE_URL" -c "SET session_replication_role = 'origin';"

# Verify counts
psql "$CORE_DATABASE_URL" -c "
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots;
"
```

### Step 5.2: Import AI Data

```bash
# Import AI tables (includes vector data)
psql "$AI_DATABASE_URL" -f ai_tables_data.sql

# Verify counts
psql "$AI_DATABASE_URL" -c "
SELECT 'ai_kb_documents' as table_name, COUNT(*) as count FROM ai_kb_documents
UNION ALL SELECT 'ai_memories', COUNT(*) FROM ai_memories
UNION ALL SELECT 'ai_feedback', COUNT(*) FROM ai_feedback;
"

# Verify vector index is working
psql "$AI_DATABASE_URL" -c "
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'ai_kb_documents';
"
```

### Step 5.3: Verify Data Integrity

Create `scripts/database/verify_migration.py`:

```python
#!/usr/bin/env python
"""
Verify data integrity after migration to dual databases.

Usage:
    OLD_DATABASE_URL="..." \
    CORE_DATABASE_URL="..." \
    AI_DATABASE_URL="..." \
    python scripts/database/verify_migration.py
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def get_counts(db_url: str, tables: list[str]) -> dict:
    """Get row counts for specified tables."""
    # Convert to asyncpg format if needed
    if not db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url)
    async with AsyncSession(engine) as session:
        counts = {}
        for table in tables:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                counts[table] = result.scalar()
            except Exception as e:
                counts[table] = f"ERROR: {e}"
        return counts

async def main():
    old_url = os.environ.get("OLD_DATABASE_URL")
    core_url = os.environ.get("CORE_DATABASE_URL")
    ai_url = os.environ.get("AI_DATABASE_URL")

    if not all([old_url, core_url, ai_url]):
        print("ERROR: Set OLD_DATABASE_URL, CORE_DATABASE_URL, AI_DATABASE_URL")
        return

    core_tables = [
        "users", "portfolios", "positions", "portfolio_snapshots",
        "position_greeks", "company_profiles", "market_data_cache"
    ]
    ai_tables = ["ai_kb_documents", "ai_memories", "ai_feedback"]

    print("=== Verification Report ===\n")

    # Old database counts
    print("OLD DATABASE (source):")
    old_core = await get_counts(old_url, core_tables)
    old_ai = await get_counts(old_url, ai_tables)
    for t, c in {**old_core, **old_ai}.items():
        print(f"  {t}: {c}")

    print("\nNEW CORE DATABASE:")
    new_core = await get_counts(core_url, core_tables)
    for t, c in new_core.items():
        match = "✅" if c == old_core.get(t) else "❌"
        print(f"  {t}: {c} {match}")

    print("\nNEW AI DATABASE:")
    new_ai = await get_counts(ai_url, ai_tables)
    for t, c in new_ai.items():
        match = "✅" if c == old_ai.get(t) else "❌"
        print(f"  {t}: {c} {match}")

    # Summary
    core_ok = all(new_core.get(t) == old_core.get(t) for t in core_tables)
    ai_ok = all(new_ai.get(t) == old_ai.get(t) for t in ai_tables)

    print("\n=== Summary ===")
    print(f"Core tables: {'✅ ALL MATCH' if core_ok else '❌ MISMATCH'}")
    print(f"AI tables: {'✅ ALL MATCH' if ai_ok else '❌ MISMATCH'}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run verification:

```bash
OLD_DATABASE_URL="$DATABASE_URL" \
CORE_DATABASE_URL="$CORE_DATABASE_URL" \
AI_DATABASE_URL="$AI_DATABASE_URL" \
python scripts/database/verify_migration.py
```

---

## Phase 6: Update Application Code (2 hours)

### Step 6.1: Update Configuration

Edit `backend/app/config.py`:

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ... existing settings ...

    # Database URLs
    DATABASE_URL: str  # Will become core database
    AI_DATABASE_URL: Optional[str] = None  # Dedicated AI database

    @property
    def core_database_url(self) -> str:
        """Core database URL (portfolios, positions, calculations)."""
        return self.DATABASE_URL

    @property
    def ai_database_url(self) -> str:
        """AI database URL (RAG, memories, feedback). Falls back to core if not set."""
        return self.AI_DATABASE_URL or self.DATABASE_URL

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
```

### Step 6.2: Update Database Module

Edit `backend/app/database.py`:

```python
"""
Database connection utilities for SigmaSight.

Dual-database architecture:
- Core database: portfolios, positions, calculations, market data
- AI database: RAG knowledge base, memories, feedback (with pgvector)
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Create base class for models
Base = declarative_base()

# =============================================================================
# Core Database (portfolios, positions, calculations, market data)
# =============================================================================

core_engine = create_async_engine(
    settings.core_database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

CoreSessionLocal = sessionmaker(
    core_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# =============================================================================
# AI Database (RAG, memories, feedback - with pgvector)
# =============================================================================

ai_engine = create_async_engine(
    settings.ai_database_url,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
    echo=False,
)

AISessionLocal = sessionmaker(
    ai_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# =============================================================================
# Session Context Managers
# =============================================================================

@asynccontextmanager
async def get_core_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session for core database."""
    async with CoreSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_ai_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async session for AI database (RAG, memories, feedback)."""
    async with AISessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# FastAPI Dependencies
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for core database session."""
    async with get_core_session() as session:
        yield session


async def get_ai_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for AI database session."""
    async with get_ai_session() as session:
        yield session


# =============================================================================
# Backwards Compatibility
# =============================================================================

# Existing code uses these names - alias to core database
get_async_session = get_core_session
AsyncSessionLocal = CoreSessionLocal
```

### Step 6.3: Update RAG Service

Edit `backend/app/agent/services/rag_service.py`:

```python
# Change this import at the top
from app.database import get_ai_session  # Changed from get_async_session

# All functions now use AI database session
# No other changes needed - the session is passed in
```

### Step 6.4: Update Memory Service

Edit `backend/app/agent/services/memory_service.py`:

```python
# Change this import at the top
from app.database import get_ai_session  # Changed from get_async_session

# Update any direct session usage to use get_ai_session
```

### Step 6.5: Update Chat Endpoints (if needed)

Check `backend/app/api/v1/chat/` for any endpoints that directly access AI tables:

```python
# If any endpoint directly queries ai_feedback, ai_memories, etc.
from app.database import get_ai_db

@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_ai_db),  # Use AI database
):
    # ...
```

---

## Phase 7: Deploy and Cutover (30 min)

### Step 7.1: Update Railway Environment Variables

1. Go to Railway Dashboard → SigmaSight Backend Service → Variables

2. **Update** existing variable:
   - `DATABASE_URL` → Set to new core database URL
   - Format: `postgresql+asyncpg://user:pass@host:port/railway`

3. **Add** new variable:
   - `AI_DATABASE_URL` → Set to new AI database URL
   - Format: `postgresql+asyncpg://user:pass@host:port/railway`

### Step 7.2: Deploy

```bash
# Trigger deployment
railway up

# Or via dashboard: Deploy → Deploy Now
```

### Step 7.3: Verify Deployment

```bash
# Check logs for any connection errors
railway logs --service sigmasight-be

# Test API endpoints
curl https://your-api.railway.app/api/v1/health

# Test AI chat (uses AI database)
curl -X POST https://your-api.railway.app/api/v1/chat/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test"}'
```

### Step 7.4: Run Post-Migration Performance Test

```bash
# Run batch calculations
railway run python scripts/run_batch_calculations.py

# Compare to baseline
railway run python scripts/railway/pgvector_performance_diagnostic.py > post_migration_metrics.txt

# Expected: Batch calculations 30-50% faster
```

---

## Phase 8: Cleanup Old Database (After 1 Week)

### Step 8.1: Verification Checklist

Wait **at least 1 week** and verify:

- [ ] All API endpoints working correctly
- [ ] AI chat functioning (RAG retrieval working)
- [ ] Batch calculations running successfully
- [ ] No errors in production logs
- [ ] Performance improvement confirmed
- [ ] All three demo users can log in and view portfolios

### Step 8.2: Delete Old Database

1. Railway Dashboard → Old PostgreSQL instance
2. Settings → Danger Zone → Delete Service
3. Confirm deletion

### Step 8.3: Update Documentation

- [ ] Update `backend/CLAUDE.md` with new database architecture
- [ ] Update `.env.example` with both database URLs
- [ ] Update deployment documentation

---

## Rollback Plan

### Quick Rollback (< 5 min)

If issues occur immediately after cutover:

1. Railway Dashboard → Backend Service → Variables
2. Change `DATABASE_URL` back to old database URL
3. Remove `AI_DATABASE_URL`
4. Redeploy

Old database still has all data (we haven't deleted it yet).

### Full Rollback (if old DB deleted)

1. Create new PostgreSQL instance on Railway
2. Restore from `full_database_backup.sql`
3. Update `DATABASE_URL` to new instance
4. Remove `AI_DATABASE_URL`
5. Redeploy

---

## Files Changed Summary

| File | Change |
|------|--------|
| `app/config.py` | Add `AI_DATABASE_URL`, properties for both URLs |
| `app/database.py` | Dual engine setup, `get_ai_session()`, `get_ai_db()` |
| `app/agent/services/rag_service.py` | Import `get_ai_session` |
| `app/agent/services/memory_service.py` | Import `get_ai_session` |
| Railway Environment | Update `DATABASE_URL`, add `AI_DATABASE_URL` |

---

## Scripts Created

| Script | Purpose |
|--------|---------|
| `scripts/database/export_for_migration.sh` | Export tables split by destination |
| `scripts/database/create_ai_schema.sql` | Create AI database schema |
| `scripts/database/verify_migration.py` | Verify data integrity |

---

## Timeline Summary

| Phase | Duration | Description |
|-------|----------|-------------|
| 1. Preparation | 1 hour | Baseline metrics, export setup |
| 2. Create DBs | 20 min | Two new Railway PostgreSQL instances |
| 3. Export Data | 30 min | pg_dump from current database |
| 4. Create Schemas | 30 min | Alembic + AI schema SQL |
| 5. Import Data | 45 min | pg_restore, verify counts |
| 6. Update Code | 2 hours | config, database.py, services |
| 7. Deploy | 30 min | Railway env vars, cutover |
| 8. Cleanup | 15 min | After 1 week verification |
| **Total** | **~6 hours** | Plus 1 week monitoring |

---

## Success Criteria

- [ ] All data migrated (record counts match)
- [ ] Zero data loss verified
- [ ] AI features work identically
- [ ] Batch calculations **>30% faster**
- [ ] No increase in RAG query latency
- [ ] No errors in production for 1 week
- [ ] Old database successfully decommissioned

---

## Future Alembic Migrations (Important!)

After the migration, you'll have two databases but Alembic only knows about one. Here's how to handle future schema changes:

### Core Database Changes (Normal Workflow)

For changes to core tables (users, portfolios, positions, etc.):

```bash
# Works normally - Alembic manages core DB
cd backend
uv run alembic revision --autogenerate -m "add new column to positions"
uv run alembic upgrade head
```

### AI Database Changes (Manual SQL)

For changes to AI tables, you have two options:

**Option A: Manual SQL Scripts** (Simple, recommended for now)

```bash
# Create migration script manually
cat > scripts/database/ai_migrations/002_add_embedding_index.sql << 'EOF'
-- AI Database Migration: Add new index
-- Date: 2025-XX-XX
-- Description: Add partial index for scope filtering

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ai_kb_documents_scope_global
ON ai_kb_documents(scope) WHERE scope = 'global';
EOF

# Apply to AI database
psql "$AI_DATABASE_URL" -f scripts/database/ai_migrations/002_add_embedding_index.sql
```

**Option B: Separate Alembic Config** (For complex AI schema needs)

Create `alembic_ai.ini` and `alembic_ai/` directory for AI-specific migrations:

```ini
# alembic_ai.ini
[alembic]
script_location = alembic_ai
sqlalchemy.url = %(AI_DATABASE_URL)s
```

```bash
# Run AI-specific migrations
AI_DATABASE_URL="$AI_DATABASE_URL" uv run alembic -c alembic_ai.ini upgrade head
```

### Long-term: Modify Existing Alembic to Skip AI Tables

Update `alembic/env.py` to conditionally skip AI tables on core DB:

```python
# alembic/env.py - add near the top
import os

def include_object(object, name, type_, reflected, compare_to):
    """Filter objects for migrations based on database target."""
    # AI tables should only be in AI database
    ai_tables = {'ai_kb_documents', 'ai_memories', 'ai_feedback'}

    if type_ == "table" and name in ai_tables:
        # Skip AI tables when running on core DB
        if os.environ.get("AI_DATABASE_URL"):
            return False
    return True

# In run_migrations_online():
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_object=include_object,  # Add this line
    # ... other config
)
```

---

## Post-Migration Database Tuning (Optional)

After migration is stable, apply workload-specific tuning:

### Core Database (OLTP optimized)

```sql
-- Connect to core database
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET effective_cache_size = '768MB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
SELECT pg_reload_conf();
```

### AI Database (Vector optimized)

```sql
-- Connect to AI database
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
-- pgvector specific
SET hnsw.ef_search = 100;
SELECT pg_reload_conf();
```
