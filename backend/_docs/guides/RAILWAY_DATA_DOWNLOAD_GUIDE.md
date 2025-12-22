# Railway Production Database Download Guide

**Purpose**: Step-by-step instructions for AI agents to download and import production data from Railway to local PostgreSQL database.

**Last Updated**: 2025-11-12

**Difficulty**: Intermediate (requires careful attention to error handling)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Reference](#quick-reference)
3. [Step-by-Step Guide](#step-by-step-guide)
4. [Verification Steps](#verification-steps)
5. [Common Issues & Solutions](#common-issues--solutions)
6. [Rollback Procedure](#rollback-procedure)
7. [Important Gotchas](#important-gotchas)

---

## Prerequisites

### Required Tools
- Docker Desktop running
- PostgreSQL 17 container running locally (`backend-postgres-1`)
- Railway DATABASE_PUBLIC_URL (from Railway dashboard)
- Network access to Railway proxy (maglev.proxy.rlwy.net)

### Required Knowledge
- PostgreSQL version compatibility (15 vs 17 incompatibility)
- PostgreSQL `--column-inserts` flag purpose
- The critical importance of `--set ON_ERROR_STOP=on`

### Check Prerequisites
```bash
# 1. Verify Docker is running
docker ps | grep postgres

# 2. Verify local database is accessible
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "SELECT version();"

# 3. Test Railway connection (requires DATABASE_PUBLIC_URL)
docker exec backend-postgres-1 psql "postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:PORT/railway" -c "SELECT COUNT(*) FROM users;"
```

---

## Quick Reference

### Command Summary (Copy-Paste Ready)

```bash
# 1. Export Railway DATABASE_PUBLIC_URL
export RAILWAY_DB_URL="postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:PORT/railway"

# 2. Backup current local database (optional but recommended)
docker exec backend-postgres-1 pg_dump -U sigmasight -d sigmasight_db \
  --format=custom --file=/tmp/local_backup_$(date +%Y%m%d_%H%M%S).dump

# 3. Stop backend server to prevent connection conflicts
# (Kill the backend server if running)

# 4. Drop and recreate local database
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "DROP DATABASE IF EXISTS sigmasight_db;"
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "CREATE DATABASE sigmasight_db OWNER sigmasight;"

# 5. Run Alembic migrations to create schema (DUAL DATABASE)
cd backend
uv run alembic -c alembic.ini upgrade head        # Core DB migrations
uv run alembic -c alembic_ai.ini upgrade head     # AI DB migrations

# 6. Import data from Railway with PROPER ERROR HANDLING
bash -o pipefail -c "docker exec backend-postgres-1 pg_dump \"$RAILWAY_DB_URL\" \
  --data-only \
  --no-owner \
  --no-privileges \
  --column-inserts | \
docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db \
  --set ON_ERROR_STOP=on \
  2>&1 | tee import_log_\$(date +%Y%m%d_%H%M%S).txt"

# 7. Verify import success
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
SELECT
  'users' as table_name, COUNT(*) FROM users
UNION ALL SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'market_data_cache', COUNT(*) FROM market_data_cache
UNION ALL SELECT 'company_profiles', COUNT(*) FROM company_profiles;"
```

---

## Step-by-Step Guide

### Phase 1: Preparation (5 minutes)

#### 1.1 Get Railway DATABASE_PUBLIC_URL

**From Railway Dashboard:**
1. Navigate to your project
2. Click on "PostgreSQL" service
3. Go to "Variables" tab
4. Copy `DATABASE_PUBLIC_URL` (NOT `DATABASE_URL`)

**Why PUBLIC_URL?**
- `DATABASE_URL` uses private network (won't work from local machine)
- `DATABASE_PUBLIC_URL` uses public proxy (`maglev.proxy.rlwy.net`)

**Format:**
```
postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:PORT/railway
```

#### 1.2 Set Environment Variable

```bash
export RAILWAY_DB_URL="postgresql://postgres:YOUR_PASSWORD@maglev.proxy.rlwy.net:YOUR_PORT/railway"

# Verify connection
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "SELECT COUNT(*) FROM users;"
```

Expected output: Count of users (e.g., 6)

#### 1.3 Stop Backend Server

```bash
# Stop backend to prevent database connection conflicts
# If backend is running with "uv run python run.py", stop it

# Verify no active connections
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
SELECT COUNT(*) FROM pg_stat_activity
WHERE datname = 'sigmasight_db' AND pid <> pg_backend_pid();"
```

Expected: 0 active connections

---

### Phase 2: Database Reset (2 minutes)

#### 2.1 Backup Current Local Database (Optional)

**⚠️ IMPORTANT: Only if you have local data you care about**

```bash
# Create backup directory
mkdir -p backups

# Full backup (schema + data)
docker exec backend-postgres-1 pg_dump -U sigmasight -d sigmasight_db \
  --format=custom \
  --file=/tmp/local_backup_$(date +%Y%m%d_%H%M%S).dump

# Copy backup out of container
docker cp backend-postgres-1:/tmp/local_backup_*.dump ./backups/

# Verify backup
ls -lh backups/
```

#### 2.2 Drop and Recreate Database

```bash
# Drop existing database (connect to postgres DB to avoid "cannot drop active DB" error)
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "DROP DATABASE IF EXISTS sigmasight_db;"

# Recreate empty database
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "CREATE DATABASE sigmasight_db OWNER sigmasight;"

# Verify empty database
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "\dt"
```

Expected output: "Did not find any relations."

#### 2.3 Run Alembic Migrations

```bash
cd backend

# Apply all migrations to create schema (DUAL DATABASE)
uv run alembic -c alembic.ini upgrade head        # Core DB migrations
uv run alembic -c alembic_ai.ini upgrade head     # AI DB migrations

# Verify migration success
uv run alembic -c alembic.ini current             # Core DB
uv run alembic -c alembic_ai.ini current          # AI DB
```

Expected output: Shows current revision for each database (e.g., `n0o1p2q3r4s5 (head)` for Core)

**Verify schema created:**
```bash
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "\dt" | wc -l
```

Expected: ~42 tables created

---

### Phase 3: Data Import (5-10 minutes)

#### 3.1 Import Data from Railway

**🚨 CRITICAL: Use `--set ON_ERROR_STOP=on` to catch errors**

```bash
# Import with full error handling and logging
# Using bash -o pipefail ensures failures in pg_dump or psql are caught
bash -o pipefail -c "docker exec backend-postgres-1 pg_dump \"$RAILWAY_DB_URL\" \
  --data-only \
  --no-owner \
  --no-privileges \
  --column-inserts | \
docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db \
  --set ON_ERROR_STOP=on \
  2>&1 | tee import_log_\$(date +%Y%m%d_%H%M%S).txt"
```

**What this command does:**

1. **`pg_dump "$RAILWAY_DB_URL"`** - Dumps data from Railway
   - `--data-only` - Only data, no schema (schema already created by Alembic)
   - `--no-owner` - Don't include ownership information
   - `--no-privileges` - Don't include privileges
   - `--column-inserts` - Use column names in INSERT statements (handles column order differences)

2. **`psql -U sigmasight -d sigmasight_db`** - Imports to local database
   - `--set ON_ERROR_STOP=on` - **CRITICAL**: Stop on first error
   - `2>&1` - Capture both stdout and stderr
   - `tee import_log_*.txt` - Log all output to file

**Import will take 5-10 minutes**. Watch for:
- ✅ "INSERT 0 1" messages (successful inserts)
- ❌ "ERROR" messages (import will stop immediately)

#### 3.2 Handle Import Errors

**If import stops with error:**

```bash
# Check the error in log file
tail -100 import_log_*.txt

# Common error: Constraint violation
# Example: "ERROR:  duplicate key value violates unique constraint"
```

**Solutions:**

1. **UUID Primary Key Conflicts**
   ```bash
   # Clear specific table and retry
   docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db \
     -c "TRUNCATE TABLE table_name CASCADE;"

   # Re-import just that table
   docker exec backend-postgres-1 pg_dump "$RAILWAY_DB_URL" \
     --data-only --no-owner --no-privileges --column-inserts \
     -t table_name | \
   docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db \
     --set ON_ERROR_STOP=on
   ```

2. **Column Order Mismatch**
   - This is why we use `--column-inserts`
   - If you see "column X is of type Y but expression is of type Z"
   - Verify both databases are on same Alembic revision

---

### Phase 4: Verification (5 minutes)

#### 4.1 Row Count Verification

```bash
# Compare Railway vs Local row counts
echo "=== RAILWAY COUNTS ===" && \
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT
  'users' as table_name, COUNT(*) FROM users
UNION ALL SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'market_data_cache', COUNT(*) FROM market_data_cache
UNION ALL SELECT 'company_profiles', COUNT(*) FROM company_profiles
UNION ALL SELECT 'position_market_betas', COUNT(*) FROM position_market_betas
UNION ALL SELECT 'position_factor_exposures', COUNT(*) FROM position_factor_exposures
UNION ALL SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots;" && \
echo "" && echo "=== LOCAL COUNTS ===" && \
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
SELECT
  'users' as table_name, COUNT(*) FROM users
UNION ALL SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'market_data_cache', COUNT(*) FROM market_data_cache
UNION ALL SELECT 'company_profiles', COUNT(*) FROM company_profiles
UNION ALL SELECT 'position_market_betas', COUNT(*) FROM position_market_betas
UNION ALL SELECT 'position_factor_exposures', COUNT(*) FROM position_factor_exposures
UNION ALL SELECT 'portfolio_snapshots', COUNT(*) FROM portfolio_snapshots;"
```

**Expected Results (November 2025):**
| Table | Railway | Local | Status |
|-------|---------|-------|--------|
| users | 6 | 6 | ✅ Match |
| portfolios | 6 | 6 | ✅ Match |
| positions | 97 | 97 | ✅ Match |
| market_data_cache | ~193K | ~193K | ✅ Match |
| company_profiles | ~556 | ~556 | ✅ Match |
| position_market_betas | ~69 | ~69 | ✅ Match |
| position_factor_exposures | ~828 | ~828 | ✅ Match |
| portfolio_snapshots | ~12 | ~12 | ✅ Match |

**If counts don't match:**
- Check import log file for errors
- Verify `--set ON_ERROR_STOP=on` was used
- Check if import completed without stopping

#### 4.2 Data Quality Verification

**Check key symbols have complete data:**

```bash
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
SELECT symbol, COUNT(*) as days, MIN(date), MAX(date)
FROM market_data_cache
WHERE symbol IN ('AAPL', 'MSFT', 'SPY', 'GOOGL', 'AMZN')
GROUP BY symbol
ORDER BY symbol;"
```

**Expected (as of Nov 2025):**
- AAPL: ~363 days (2024-06-03 to 2025-11-11)
- MSFT: ~345 days
- SPY: ~468 days (2024-01-02 to 2025-11-11)
- GOOGL: ~363 days
- AMZN: ~348 days

**Check demo users exist:**

```bash
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
SELECT email, full_name FROM users ORDER BY email;"
```

Expected: 6 users including `demo_hnw@sigmasight.com`, `demo_individual@sigmasight.com`, etc.

#### 4.3 Schema Verification

```bash
# Verify both databases have same structure
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "\d market_data_cache" > /tmp/railway_schema.txt
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "\d market_data_cache" > /tmp/local_schema.txt

diff /tmp/railway_schema.txt /tmp/local_schema.txt
```

Expected: No differences (or only difference in ownership)

---

## Verification Steps

### Complete Verification Checklist

- [ ] Row counts match between Railway and local for all core tables
- [ ] Key symbols (AAPL, MSFT, SPY) have expected date ranges
- [ ] Demo users exist and can be queried
- [ ] No error messages in import log
- [ ] Alembic version matches between Railway and local
- [ ] Backend server can start successfully
- [ ] Test login with demo credentials works

### Test Backend Connection

```bash
# Start backend server
cd backend
uv run python run.py

# In another terminal, test API
curl http://localhost:8000/docs
```

Expected: Swagger UI loads successfully

### Test Demo Login

```bash
# Test authentication endpoint
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}'
```

Expected: JSON response with access_token

---

## Common Issues & Solutions

### Issue 1: Silent Data Loss (24% rows missing)

**Symptoms:**
- Import completes successfully
- Row counts 20-30% lower than Railway
- No obvious errors

**Root Cause:**
- Missing `--set ON_ERROR_STOP=on` flag
- PostgreSQL continues on constraint violations by default
- Each failed INSERT is silently skipped

**Solution:**
```bash
# ALWAYS use this flag:
psql --set ON_ERROR_STOP=on
```

**Verification:**
```bash
# Compare row counts for key tables (use COUNT(*), NOT pg_stat_user_tables)
# pg_stat_user_tables counters reset on ANALYZE/VACUUM and don't represent actual row counts
echo "=== RAILWAY COUNTS ===" && \
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "
SELECT 'users' as table_name, COUNT(*) FROM users
UNION ALL SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'market_data_cache', COUNT(*) FROM market_data_cache;" && \
echo "" && echo "=== LOCAL COUNTS ===" && \
docker exec backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
SELECT 'users' as table_name, COUNT(*) FROM users
UNION ALL SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL SELECT 'positions', COUNT(*) FROM positions
UNION ALL SELECT 'market_data_cache', COUNT(*) FROM market_data_cache;"
```

### Issue 2: Column Order Mismatch

**Symptoms:**
```
ERROR: column "created_at" is of type timestamp but expression is of type numeric
ERROR: invalid input syntax for type numeric: "PUBLIC"
```

**Root Cause:**
- Railway schema column order differs from local schema
- Using basic `--inserts` (position-dependent)

**Solution:**
```bash
# Use --column-inserts flag
pg_dump --column-inserts  # Explicit column names in INSERT
```

### Issue 3: UUID Primary Key Conflicts

**Symptoms:**
```
ERROR: duplicate key value violates unique constraint "pk_table_name"
DETAIL: Key (id)=(UUID) already exists.
```

**Root Cause:**
- Local database has existing data
- Railway dump includes explicit UUIDs that conflict

**Solution:**
```bash
# Clear database before import (connect to postgres DB to avoid "cannot drop active DB" error)
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "DROP DATABASE IF EXISTS sigmasight_db;"
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "CREATE DATABASE sigmasight_db OWNER sigmasight;"
uv run alembic -c alembic.ini upgrade head        # Recreate Core schema
uv run alembic -c alembic_ai.ini upgrade head     # Recreate AI schema
```

### Issue 4: PostgreSQL Version Incompatibility

**Symptoms:**
```
FATAL: database files are incompatible with server
The data directory was initialized by PostgreSQL version 15,
which is not compatible with this version 17
```

**Root Cause:**
- Trying to use PostgreSQL 15 data with PostgreSQL 17
- Data directory format changed

**Solution:**
```bash
# Remove old volume and start fresh
docker-compose down -v
docker-compose up -d
uv run python -m alembic upgrade head
# Then import data
```

### Issue 5: Connection Refused to Railway

**Symptoms:**
```
psql: error: connection to server at "maglev.proxy.rlwy.net" failed: Connection refused
```

**Root Cause:**
- Using DATABASE_URL instead of DATABASE_PUBLIC_URL
- Network/firewall blocking Railway proxy

**Solution:**
```bash
# Use DATABASE_PUBLIC_URL (public proxy)
export RAILWAY_DB_URL="postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:PORT/railway"

# Test connection
docker exec backend-postgres-1 psql "$RAILWAY_DB_URL" -c "SELECT 1;"
```

---

## Rollback Procedure

### If Import Fails Midway

```bash
# 1. Stop import (Ctrl+C if still running)

# 2. Drop corrupted database (connect to postgres DB to avoid "cannot drop active DB" error)
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "DROP DATABASE IF EXISTS sigmasight_db;"

# 3. Restore from backup (if you made one)
docker exec backend-postgres-1 psql -U sigmasight -d postgres -c "CREATE DATABASE sigmasight_db OWNER sigmasight;"
docker cp ./backups/local_backup_*.dump backend-postgres-1:/tmp/
docker exec backend-postgres-1 pg_restore -U sigmasight -d sigmasight_db /tmp/local_backup_*.dump

# OR start fresh with Alembic + seed data
uv run python -m alembic upgrade head
python scripts/database/reset_and_seed.py seed
```

---

## Important Gotchas

### 1. **ALWAYS use `--set ON_ERROR_STOP=on`**
Without this flag, PostgreSQL will silently skip failed INSERTs and continue. You'll end up with incomplete data and no obvious error.

### 2. **Use `--column-inserts` for Railway imports**
Railway schema may have different physical column ordering than local schema. Using `--column-inserts` ensures INSERT statements explicitly name columns.

### 3. **DATABASE_PUBLIC_URL vs DATABASE_URL**
- `DATABASE_URL` - Private network only (won't work from local machine)
- `DATABASE_PUBLIC_URL` - Public proxy (maglev.proxy.rlwy.net) - **USE THIS**

### 4. **Verify row counts match EXACTLY**
Don't assume import succeeded. Always compare row counts between Railway and local.

### 5. **Use `bash -o pipefail` for import pipelines**
Without `pipefail`, the exit status of `tee` (always 0) masks failures in `pg_dump` or `psql`. Wrap pipelines in:
```bash
bash -o pipefail -c "pg_dump ... | psql ... | tee import_log.txt"
```
This ensures failures in any part of the pipeline are caught and propagated.

### 6. **Log everything with `tee`**
Import logs are essential for debugging. Always use:
```bash
bash -o pipefail -c "psql ... 2>&1 | tee import_log.txt"
```

### 7. **Stop backend server before import**
Active connections can prevent database operations. Always stop the backend server first.

### 8. **Connect to `postgres` database for DROP/CREATE DATABASE**
Cannot drop or create a database while connected to it. Always use `-d postgres`:
```bash
psql -U sigmasight -d postgres -c "DROP DATABASE IF EXISTS sigmasight_db;"
```

### 9. **PostgreSQL version matters**
Cannot mix PostgreSQL 15 and 17 data directories. Must use `pg_dump`/`psql` approach, not volume copying.

### 10. **Alembic migrations first, data second**
Always run `alembic upgrade head` to create schema BEFORE importing data.

---

## Advanced: Selective Table Import

### Import Single Table

```bash
# Import just market_data_cache
docker exec backend-postgres-1 pg_dump "$RAILWAY_DB_URL" \
  --data-only --no-owner --no-privileges --column-inserts \
  -t market_data_cache | \
docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db \
  --set ON_ERROR_STOP=on
```

### Import Specific Tables Only

```bash
# Import just core tables
docker exec backend-postgres-1 pg_dump "$RAILWAY_DB_URL" \
  --data-only --no-owner --no-privileges --column-inserts \
  -t users -t portfolios -t positions -t market_data_cache | \
docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db \
  --set ON_ERROR_STOP=on
```

---

## Performance Considerations

### Large Dumps (~200K+ rows)

**Estimated times:**
- Dump from Railway: 2-3 minutes
- Import to local: 5-10 minutes
- Total: 7-13 minutes

**To speed up:**

1. **Use `--no-owner --no-privileges`** (already included)
2. **Disable triggers during import** (if safe):
   ```bash
   docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
   SET session_replication_role = replica;  -- Disable triggers
   "
   # Import data
   docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db -c "
   SET session_replication_role = DEFAULT;  -- Re-enable triggers
   "
   ```

3. **Consider using COPY instead of INSERT for huge tables:**
   ```bash
   # Remove --column-inserts, let pg_dump use COPY format
   docker exec backend-postgres-1 pg_dump "$RAILWAY_DB_URL" \
     --data-only --no-owner --no-privileges \
     -t market_data_cache | \
   docker exec -i backend-postgres-1 psql -U sigmasight -d sigmasight_db \
     --set ON_ERROR_STOP=on
   ```

---

## Troubleshooting Checklist

When import doesn't work as expected:

- [ ] Check import log file for errors
- [ ] Verify `--set ON_ERROR_STOP=on` was used
- [ ] Compare row counts Railway vs local for each table
- [ ] Check Alembic version matches: `alembic -c alembic.ini current` and `alembic -c alembic_ai.ini current`
- [ ] Verify DATABASE_PUBLIC_URL is correct (not DATABASE_URL)
- [ ] Test Railway connection: `psql "$RAILWAY_DB_URL" -c "SELECT 1;"`
- [ ] Check PostgreSQL versions match (both should be 17)
- [ ] Verify Docker container is running: `docker ps | grep postgres`
- [ ] Check disk space: `df -h`
- [ ] Look for constraint violations in logs
- [ ] Verify schema exists before import: `\dt`

---

## Summary: Critical Success Factors

1. ✅ Use `DATABASE_PUBLIC_URL` (not DATABASE_URL)
2. ✅ Use `--set ON_ERROR_STOP=on` (prevent silent failures)
3. ✅ Use `bash -o pipefail` (catch pipeline failures)
4. ✅ Use `--column-inserts` (handle column order differences)
5. ✅ Use `-d postgres` for DROP/CREATE DATABASE commands
6. ✅ Run Alembic migrations for BOTH databases BEFORE importing data
7. ✅ Stop backend server before import
8. ✅ Log everything with `tee` inside pipefail
9. ✅ Verify row counts match EXACTLY (use COUNT(*), not pg_stat)
10. ✅ Test with demo login after import

**Follow these steps exactly, and data import will succeed with 100% data parity.**

---

**Questions or Issues?**
- Check import log file first
- Verify all flags were used correctly
- Compare this guide's expected outputs vs actual
- When in doubt, start over with fresh database

**Last verified working**: 2025-11-12 with PostgreSQL 17, dual database Alembic setup (Core + AI)
