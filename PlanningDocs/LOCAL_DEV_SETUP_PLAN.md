# Local Development Setup Plan

**Purpose**: Set up local development environment for `BatchProcessUpdate` branch with production data from Railway.

**Created**: 2026-01-11

**Branch**: `BatchProcessUpdate`

**Status**: Planning

---

## Overview

Set up local PostgreSQL databases with production data imported from Railway, enabling full-stack local development while `main` branch runs in production on Railway.

### Architecture

```
Production (Railway)                    Local Development
┌─────────────────────┐                ┌─────────────────────┐
│  Core DB (gondola)  │  ──export──►   │  sigmasight_db      │
│  - users            │                │  - users            │
│  - portfolios       │                │  - portfolios       │
│  - positions        │                │  - positions        │
│  - market_data      │                │  - market_data      │
│  - conversations    │                │  - conversations    │
└─────────────────────┘                └─────────────────────┘

┌─────────────────────┐                ┌─────────────────────┐
│  AI DB (metro)      │  ──export──►   │  sigmasight_ai_db   │
│  - ai_feedback      │                │  - ai_feedback      │
│  - ai_memories      │                │  - ai_memories      │
│  - ai_kb_documents  │                │  - ai_kb_documents  │
└─────────────────────┘                └─────────────────────┘
```

---

## Prerequisites

### Required Software
- [ ] Docker Desktop installed and running
- [ ] Railway CLI installed (`npm install -g @railway/cli`)
- [ ] Access to Railway dashboard for database URLs
- [ ] `uv` package manager installed

### Required Credentials (from Railway Dashboard)
You need **DATABASE_PUBLIC_URL** (not DATABASE_URL) for both databases:

1. **Core DB (gondola)**:
   - Go to Railway project → PostgreSQL service (gondola)
   - Variables tab → Copy `DATABASE_PUBLIC_URL`
   - Format: `postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:PORT/railway`

2. **AI DB (metro)**:
   - Go to Railway project → PostgreSQL service (metro)
   - Variables tab → Copy `DATABASE_PUBLIC_URL`
   - Format: `postgresql://postgres:PASSWORD@metro.proxy.rlwy.net:PORT/railway`

---

## Phase 1: Local Infrastructure Setup

### 1.1 Start Docker Desktop
Ensure Docker Desktop is running before proceeding.

### 1.2 Start PostgreSQL Container
```bash
cd backend
docker-compose up -d
```

**Verify container is running:**
```bash
docker ps | grep postgres
```

Expected: `backend-postgres-1` running on port 5432

### 1.3 Create AI Database
The docker-compose only creates `sigmasight_db`. We need to create `sigmasight_ai_db` manually:

```bash
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "CREATE DATABASE sigmasight_ai_db OWNER sigmasight;"
```

**Verify both databases exist:**
```bash
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "\l"
```

Expected: Both `sigmasight_db` and `sigmasight_ai_db` listed

### 1.4 Enable pgvector Extension (for AI DB)
```bash
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_ai_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Phase 2: Schema Setup (Alembic Migrations)

### 2.1 Run Core DB Migrations
```bash
cd backend
uv run alembic -c alembic.ini upgrade head
```

**Verify:**
```bash
uv run alembic -c alembic.ini current
```

### 2.2 Run AI DB Migrations
```bash
uv run alembic -c alembic_ai.ini upgrade head
```

**Verify:**
```bash
uv run alembic -c alembic_ai.ini current
```

### 2.3 Verify Schema Created
```bash
# Core DB tables (should be ~42 tables)
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "\dt" | wc -l

# AI DB tables (should be ~3-5 tables)
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_ai_db -c "\dt"
```

---

## Phase 3: Data Import from Railway

### 3.1 Set Environment Variables

**In your terminal (PowerShell or bash):**

```bash
# Core DB - Replace with your actual Railway PUBLIC URL
export RAILWAY_CORE_URL="postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:PORT/railway"

# AI DB - Replace with your actual Railway PUBLIC URL
export RAILWAY_AI_URL="postgresql://postgres:PASSWORD@metro.proxy.rlwy.net:PORT/railway"
```

**For PowerShell:**
```powershell
$env:RAILWAY_CORE_URL = "postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:PORT/railway"
$env:RAILWAY_AI_URL = "postgresql://postgres:PASSWORD@metro.proxy.rlwy.net:PORT/railway"
```

### 3.2 Test Railway Connections
```bash
# Test Core DB connection
docker exec backend-postgres-1 psql "$RAILWAY_CORE_URL" -c "SELECT COUNT(*) FROM users;"

# Test AI DB connection
docker exec backend-postgres-1 psql "$RAILWAY_AI_URL" -c "SELECT COUNT(*) FROM ai_feedback;"
```

### 3.3 Import Core DB Data

**Clear existing data first:**
```bash
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "DROP DATABASE IF EXISTS sigmasight_db;"
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "CREATE DATABASE sigmasight_db OWNER sigmasight;"

# Re-run migrations
cd backend
uv run alembic -c alembic.ini upgrade head
```

**Import data from Railway:**
```bash
# For bash/Git Bash on Windows:
docker exec backend-postgres-1 pg_dump "$RAILWAY_CORE_URL" \
  --data-only \
  --no-owner \
  --no-privileges \
  --column-inserts | \
docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db \
  --set ON_ERROR_STOP=on
```

**For PowerShell (alternative approach):**
```powershell
# Export to file first
docker exec backend-postgres-1 pg_dump $env:RAILWAY_CORE_URL --data-only --no-owner --no-privileges --column-inserts > core_data.sql

# Import from file
Get-Content core_data.sql | docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db --set ON_ERROR_STOP=on
```

### 3.4 Import AI DB Data

**Clear existing data first:**
```bash
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "DROP DATABASE IF EXISTS sigmasight_ai_db;"
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "CREATE DATABASE sigmasight_ai_db OWNER sigmasight;"

# Enable pgvector
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_ai_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Re-run AI migrations
uv run alembic -c alembic_ai.ini upgrade head
```

**Import data from Railway:**
```bash
docker exec backend-postgres-1 pg_dump "$RAILWAY_AI_URL" \
  --data-only \
  --no-owner \
  --no-privileges \
  --column-inserts | \
docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_ai_db \
  --set ON_ERROR_STOP=on
```

---

## Phase 4: Update Local Configuration

### 4.1 Update backend/.env

Change the database URLs from Railway internal to local:

**Before (Railway internal - won't work locally):**
```
DATABASE_URL=postgresql+asyncpg://postgres:...@pgvector.railway.internal:5432/railway
```

**After (local PostgreSQL):**
```
DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_db
AI_DATABASE_URL=postgresql+asyncpg://sigmasight:sigmasight_dev@localhost:5432/sigmasight_ai_db
```

### 4.2 Keep Other Variables
All API keys (Polygon, FMP, FRED, OpenAI, Anthropic) can stay the same - they work from any location.

---

## Phase 5: Verification

### 5.1 Verify Data Counts

```bash
# Check Core DB
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
SELECT 'users' as table_name, COUNT(*) FROM users
UNION ALL SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'market_data_cache', COUNT(*) FROM market_data_cache
UNION ALL SELECT 'company_profiles', COUNT(*) FROM company_profiles;"
```

**Expected counts (approximate):**
| Table | Expected |
|-------|----------|
| users | 6 |
| portfolios | 6 |
| positions | 97 |
| market_data_cache | ~193K |
| company_profiles | ~556 |

```bash
# Check AI DB
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_ai_db -c "
SELECT 'ai_feedback' as table_name, COUNT(*) FROM ai_feedback
UNION ALL SELECT 'ai_memories', COUNT(*) FROM ai_memories
UNION ALL SELECT 'ai_kb_documents', COUNT(*) FROM ai_kb_documents;"
```

### 5.2 Test Backend Server

```bash
cd backend
uv run python run.py
```

Expected: Server starts on http://localhost:8000

### 5.3 Test API Endpoints

```bash
# Health check
curl http://localhost:8000/docs

# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}'
```

Expected: Returns JWT access_token

### 5.4 Test Frontend (Optional)

```bash
cd frontend
docker-compose up -d

# Or with npm
npm run dev
```

Navigate to http://localhost:3005 and login with demo credentials.

---

## Troubleshooting

### Issue: "Connection refused" to Railway
- **Cause**: Using DATABASE_URL instead of DATABASE_PUBLIC_URL
- **Solution**: Get the PUBLIC URL from Railway dashboard (uses maglev.proxy.rlwy.net)

### Issue: "relation does not exist"
- **Cause**: Migrations not run before import
- **Solution**: Run `alembic upgrade head` for both databases before importing

### Issue: "duplicate key" errors
- **Cause**: Local database has existing data
- **Solution**: Drop and recreate database before import

### Issue: Silent data loss (counts don't match)
- **Cause**: Missing `--set ON_ERROR_STOP=on` flag
- **Solution**: Always use this flag to stop on first error

### Issue: PowerShell variable expansion
- **Cause**: PowerShell handles environment variables differently
- **Solution**: Use `$env:VARIABLE_NAME` syntax or export to file first

---

## Quick Reference Commands

```bash
# Start local PostgreSQL
cd backend && docker-compose up -d

# Check container status
docker ps | grep postgres

# Connect to local Core DB
docker exec -it backend-postgres-1 psql -U sigmasight -d sigmasight_db

# Connect to local AI DB
docker exec -it backend-postgres-1 psql -U sigmasight -d sigmasight_ai_db

# Start backend
cd backend && uv run python run.py

# Start frontend
cd frontend && docker-compose up -d
```

---

## Checklist

### Phase 1: Infrastructure
- [ ] Docker Desktop running
- [ ] PostgreSQL container started
- [ ] AI database created
- [ ] pgvector extension enabled

### Phase 2: Schema
- [ ] Core DB migrations applied
- [ ] AI DB migrations applied
- [ ] Tables verified

### Phase 3: Data Import
- [ ] Railway PUBLIC URLs obtained (both databases)
- [ ] Core DB data imported
- [ ] AI DB data imported
- [ ] Row counts verified

### Phase 4: Configuration
- [ ] backend/.env updated with local URLs
- [ ] AI_DATABASE_URL added

### Phase 5: Verification
- [ ] Backend server starts
- [ ] Demo login works
- [ ] Frontend connects (optional)

---

## Notes

- **Branch**: Working on `BatchProcessUpdate`, production runs `main` on Railway
- **Data Isolation**: Local databases are completely separate from production
- **API Keys**: Same keys work for both local and production
- **Import Time**: Core DB import takes 5-10 minutes due to ~193K market_data_cache rows

---

**Next Steps After Setup:**
1. Start developing on `BatchProcessUpdate` branch
2. Test changes locally before pushing
3. When ready, merge to `main` for Railway deployment
