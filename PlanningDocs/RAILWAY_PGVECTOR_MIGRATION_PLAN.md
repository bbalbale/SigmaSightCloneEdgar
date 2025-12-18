# Plan: Push FrontendLocal to FrontendRailway with pgvector Support

**Created**: 2025-12-16
**Updated**: 2025-12-16 (Revised approach: Local → Railway data push)
**Status**: Local testing complete, ready for Railway deployment

## Overview
Push FrontendLocal branch to FrontendRailway, enable pgvector on Railway PostgreSQL, and preserve all existing data.

## Current State
- **FrontendLocal**: Contains merged FrontendRailway changes + new AI features (Home page, web search, chat enhancements)
- **Migrations Required**:
  1. `l9m0n1o2p3q4_add_ai_learning_tables.py` - Creates 3 AI tables + pgvector extension
  2. `m9n0o1p2q3r4_switch_to_hnsw_index.py` - Switches vector index from IVFFlat to HNSW
- **Railway PostgreSQL**: Supports pgvector, but current instance doesn't have it enabled
- **Data Sources**:
  - Railway DB is more current (production data)
  - Local DB may have some recent changes from local development
- **Local Status**: ✅ Both migrations tested successfully on local database
- **Railway Backup**: ✅ Backed up via Railway dashboard

## ⚠️ CRITICAL: Deployment Sequencing

**DO NOT push code to FrontendRailway until pgvector is enabled!**

When code is pushed → Railway redeploys → runs `alembic upgrade head` → migration will FAIL or skip vector features if pgvector isn't enabled.

**Correct order:**
1. Enable pgvector on Railway FIRST
2. Set up schema (run migrations manually or via Railway CLI)
3. Import data
4. THEN push code

## HNSW vs IVFFlat Decision
We chose **HNSW** (Hierarchical Navigable Small World) over IVFFlat for better production quality:

| Aspect | IVFFlat (old) | HNSW (new) |
|--------|---------------|------------|
| Recall accuracy | ~95% | ~99% |
| Query speed | Good | Better |
| Memory usage | Lower | Higher |
| Build time | Fast | Slower |

**HNSW Parameters**: `m=16, ef_construction=64` (good defaults for <100k documents)

## Strategy (Revised)
1. **Compare** Railway vs Local data to understand differences
2. **Back up** Railway data locally (already done via Railway dashboard)
3. **Enable pgvector** on Railway (BEFORE any code push)
4. **Create schema** on Railway with migrations
5. **Push data** from Local → Railway (local has migrations applied)
6. **Push code** to FrontendRailway
7. **Verify** everything works

---

## Phase 1: Compare Railway vs Local Data (10 min)

### Step 1.1: Get Railway Data Counts
```bash
# Get Railway DATABASE_PUBLIC_URL from Railway dashboard
export RAILWAY_DB_URL="postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:PORT/railway"

# Query Railway counts
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT 'users' as tbl, COUNT(*) FROM users UNION ALL
SELECT 'portfolios', COUNT(*) FROM portfolios UNION ALL
SELECT 'positions', COUNT(*) FROM positions UNION ALL
SELECT 'market_data_cache', COUNT(*) FROM market_data_cache UNION ALL
SELECT 'company_profiles', COUNT(*) FROM company_profiles UNION ALL
SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots UNION ALL
SELECT 'position_factor_exposures', COUNT(*) FROM position_factor_exposures
ORDER BY tbl;
"
```

### Step 1.2: Get Local Data Counts
```bash
# Query local counts
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
SELECT 'users' as tbl, COUNT(*) FROM users UNION ALL
SELECT 'portfolios', COUNT(*) FROM portfolios UNION ALL
SELECT 'positions', COUNT(*) FROM positions UNION ALL
SELECT 'market_data_cache', COUNT(*) FROM market_data_cache UNION ALL
SELECT 'company_profiles', COUNT(*) FROM company_profiles UNION ALL
SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots UNION ALL
SELECT 'position_factor_exposures', COUNT(*) FROM position_factor_exposures
ORDER BY tbl;
"
```

### Step 1.3: Decide Data Strategy
Compare the counts and decide:
- **If Railway has more data**: Export Railway → merge with local → push combined to Railway
- **If Local is sufficient**: Push local data directly to Railway
- **If both have unique data**: Manual merge required

---

## Phase 2: Export Local Data (10 min)

### Step 2.1: Export Local Database (Data Only)
```bash
# Export local data with column inserts (handles column order differences)
docker exec backend-postgres-1 pg_dump -U sigmasight -d sigmasight_db \
  --data-only \
  --no-owner \
  --no-privileges \
  --column-inserts \
  --disable-triggers \
  -f /tmp/local_data_export.sql

# Copy out of container
docker cp backend-postgres-1:/tmp/local_data_export.sql ./local_data_export.sql

# Verify file size
ls -lh local_data_export.sql
```

### Step 2.2: (Optional) Export Railway Data for Comparison/Backup
```bash
# If you need Railway data locally for comparison
docker exec backend-postgres-1 pg_dump "$RAILWAY_DB_URL" \
  --data-only \
  --no-owner \
  --no-privileges \
  --column-inserts \
  -f /tmp/railway_data_export.sql

docker cp backend-postgres-1:/tmp/railway_data_export.sql ./railway_data_export.sql
```

---

## Phase 3: Enable pgvector on Railway (10-15 min)

### ⚠️ DO THIS BEFORE PUSHING ANY CODE

### Step 3.1: Enable pgvector Extension
Railway supports pgvector. To enable it:

**Option A: Via Railway Dashboard (Preferred)**
1. Go to Railway Dashboard → PostgreSQL service → Settings
2. Look for "Extensions" or pgvector toggle
3. Enable pgvector extension
4. This may require a database restart

**Option B: Via SQL (if you have superuser access)**
```bash
# Connect to Railway and create extension
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Option C: Recreate PostgreSQL with pgvector Template**
If Options A/B don't work:
1. Note the current DATABASE_URL
2. Delete the PostgreSQL service in Railway
3. Re-add PostgreSQL and select pgvector template
4. Update DATABASE_URL in backend service if changed
5. Database will be empty - that's OK, we'll import data

### Step 3.2: Verify pgvector is Available
```bash
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT * FROM pg_available_extensions WHERE name = 'vector';
"
# Should show vector extension as available

# Or if already enabled:
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT * FROM pg_extension WHERE extname = 'vector';
"
```

---

## Phase 4: Prepare Railway Database Schema (10 min)

### Step 4.1: Clear Existing Data (if database exists)
```bash
# CAUTION: This deletes all data! Only do this after backup is confirmed
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
-- Disable foreign key checks temporarily
SET session_replication_role = replica;

-- Truncate all tables (preserves schema)
TRUNCATE TABLE alembic_version CASCADE;
-- Add other tables as needed if you want to preserve schema

SET session_replication_role = DEFAULT;
"
```

### Step 4.2: Apply Migrations to Create Schema
```bash
# Option A: Via Railway CLI (if available)
railway run "cd backend && uv run alembic upgrade head"

# Option B: Connect directly and run migrations
# First, temporarily point your local backend to Railway DB:
# Set DATABASE_URL in .env to Railway URL, then:
cd backend
uv run alembic upgrade head
# Then restore .env to local DATABASE_URL
```

### Step 4.3: Verify Schema Created
```bash
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "\dt"
# Should show all tables including ai_kb_documents, ai_memories, ai_feedback

docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT version_num FROM alembic_version;
"
# Should show: m9n0o1p2q3r4 (the HNSW migration)
```

---

## Phase 5: Import Data to Railway (15 min)

### Step 5.1: Import Local Data to Railway
```bash
# Import the exported local data
docker exec -i backend-postgres-1 psql "$RAILWAY_DB_URL" \
  --set ON_ERROR_STOP=on \
  < local_data_export.sql 2>&1 | tee import_log.txt

# Check for errors
grep -i error import_log.txt
```

### Step 5.2: Handle Import Errors (if any)
Common issues:
- **Duplicate key errors**: Data already exists, may need to truncate first
- **Foreign key errors**: Import order issue, may need to disable triggers
- **Type mismatch**: Schema differences between local and Railway

```bash
# If you need to disable triggers during import:
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "SET session_replication_role = replica;"
# Then run import
# Then re-enable:
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "SET session_replication_role = DEFAULT;"
```

### Step 5.3: Verify Data Imported
```bash
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT 'users' as tbl, COUNT(*) FROM users UNION ALL
SELECT 'portfolios', COUNT(*) FROM portfolios UNION ALL
SELECT 'positions', COUNT(*) FROM positions UNION ALL
SELECT 'market_data_cache', COUNT(*) FROM market_data_cache UNION ALL
SELECT 'company_profiles', COUNT(*) FROM company_profiles
ORDER BY tbl;
"
```

---

## Phase 6: Verify Railway Setup (10 min)

### Step 6.1: Verify pgvector Extension Active
```bash
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT * FROM pg_extension WHERE extname = 'vector';
"
```

### Step 6.2: Verify AI Tables and HNSW Index
```bash
# Check AI tables exist
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "\dt ai_*"

# Check HNSW index (not IVFFlat)
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_ai_kb_documents_embedding';
"
# Should show: USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64')
```

### Step 6.3: Test API Connectivity (if backend is running)
```bash
# Get Railway backend URL
curl -X POST https://your-railway-backend/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}'
```

---

## Phase 7: Push Code Changes (5 min)

### ⚠️ ONLY DO THIS AFTER PHASES 3-6 ARE COMPLETE

### Step 7.1: Commit Migration File (if not already committed)
```bash
cd /c/Users/BenBalbale/CascadeProjects/SigmaSight
git add backend/alembic/versions/m9n0o1p2q3r4_switch_to_hnsw_index.py
git commit -m "feat: Add HNSW index migration for better vector search recall"
```

### Step 7.2: Push FrontendLocal to FrontendRailway
```bash
git push origin FrontendLocal:FrontendRailway
```

### Step 7.3: Monitor Railway Deployment
- Check Railway dashboard for successful build
- Monitor deployment logs for errors
- Alembic should detect migrations are already applied (no-op)

---

## Phase 8: Final Verification (10 min)

### Step 8.1: Verify Railway Backend Running
```bash
# Check health endpoint
curl https://your-railway-backend/api/health

# Test authentication
curl -X POST https://your-railway-backend/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}'
```

### Step 8.2: Verify Frontend Connects
- Navigate to frontend URL
- Login with demo credentials
- Verify portfolio data loads
- Test AI chat functionality

---

## Rollback Plan

### If pgvector Enable Fails
- Railway has built-in backup restore
- Can restore from Railway dashboard backup point

### If Data Import Fails
- Re-import from railway_data_export.sql (Railway backup)
- Or restore via Railway dashboard

### If Code Push Breaks Things
```bash
# Revert to previous commit on FrontendRailway
git push origin FrontendRailway~1:FrontendRailway --force
```

---

## Critical Files
- `backend/alembic/versions/l9m0n1o2p3q4_add_ai_learning_tables.py` - AI tables + pgvector migration
- `backend/alembic/versions/m9n0o1p2q3r4_switch_to_hnsw_index.py` - HNSW index migration
- `backend/_docs/guides/RAILWAY_DATA_DOWNLOAD_GUIDE.md` - Detailed backup/restore guide
- `local_data_export.sql` - Exported local data (created in Phase 2)

## Expected Timeline
- Phase 1: 10 min (compare data)
- Phase 2: 10 min (export local data)
- Phase 3: 10-15 min (enable pgvector)
- Phase 4: 10 min (create schema)
- Phase 5: 15 min (import data)
- Phase 6: 10 min (verify setup)
- Phase 7: 5 min (push code)
- Phase 8: 10 min (final verification)
- **Total: 80-85 minutes**

## Success Criteria
1. pgvector extension installed and active on Railway
2. All tables created including AI tables
3. **HNSW index active** (not IVFFlat) on ai_kb_documents.embedding
4. Data counts match expected values
5. All API endpoints functional
6. Demo users can log in
7. Frontend connects to backend
8. AI chat works with vector search capability
