# Railway Database Schema Comparison Guide

**Created**: 2025-12-18
**Purpose**: Diagnose 20x performance degradation after pgvector migration
**Problem**: Batch calculations went from 3 seconds → 60 seconds per day

---

## Executive Summary

After migrating to Railway's pgvector-enabled PostgreSQL database, batch calculations became 20-30x slower. This guide provides tools to:

1. **Diagnose** what went wrong during the migration
2. **Identify** missing performance-critical indexes
3. **Fix** the performance issues

**Most Likely Cause**: Missing indexes after schema migration/restore

---

## Background

### Migration Timeline

1. **Nov 11, 2025**: Schema migrated from local to Railway using `pg_dump` + `pg_restore`
2. **Dec 16, 2025**: pgvector migration planned (HNSW indexes)
3. **Current**: Database running on Railway with pgvector support

### Key Migrations

Two critical performance migrations were added in November 2025:

1. **i6j7k8l9m0n1** - Composite indexes for batch processing
2. **j7k8l9m0n1o2** - Priority performance indexes (10x-100x speedup)

These migrations create **6 critical indexes** that are essential for fast batch calculations.

---

## Diagnostic Scripts

### 1. Performance Diagnostic (Recommended First)

**Script**: `diagnose_railway_performance.py`

**What it does**:
- Checks for 6 critical performance indexes
- Analyzes table sizes and row counts
- Verifies pgvector extension and indexes
- Provides actionable recommendations

**How to run**:
```bash
cd backend
uv run python scripts/database/diagnose_railway_performance.py
```

**Output**: Saves detailed report to `railway_performance_diagnostic_YYYYMMDD_HHMMSS.txt`

**What to look for**:
- "🚨 Critical indexes MISSING: X/6" - This is likely your problem
- Index status for `market_data_cache`, `positions`, `portfolio_snapshots`

---

### 2. Create Missing Indexes

**Script**: `create_missing_indexes.py`

**What it does**:
- Creates the 6 critical performance indexes
- Uses `CREATE INDEX CONCURRENTLY` (safe, no table locks)
- Supports dry-run mode

**How to run**:

```bash
# Dry run (see what would be created, no changes)
cd backend
uv run python scripts/database/create_missing_indexes.py

# Live mode (actually create indexes)
uv run python scripts/database/create_missing_indexes.py --live
```

**Expected outcome**:
- Batch calculation time: 60s → 3s per day
- Overall query performance: 20x faster

---

### 3. Full Schema Comparison (Advanced)

**Script**: `compare_schemas_simple.py`

**What it does**:
- Compares two PostgreSQL databases
- Checks tables, indexes, extensions, row counts
- Comprehensive schema analysis

**How to run**:
```bash
cd backend
uv run python scripts/database/compare_schemas_simple.py
```

**Note**: This script requires both local and Railway databases to be accessible. Since you're currently running directly against Railway, you may not have a local database to compare against.

---

## The 6 Critical Indexes

### From Migration i6j7k8l9m0n1

1. **idx_market_data_cache_symbol_date**
   - Table: `market_data_cache`
   - Columns: `(symbol, date)`
   - Purpose: Price lookups (378+ queries per batch run)
   - Impact: **Eliminates full table scans on 191k+ row table**

2. **idx_positions_portfolio_deleted**
   - Table: `positions`
   - Columns: `(portfolio_id, deleted_at)`
   - Purpose: Active position queries
   - Impact: Speeds up `WHERE portfolio_id = X AND deleted_at IS NULL`

3. **idx_snapshots_portfolio_date**
   - Table: `portfolio_snapshots`
   - Columns: `(portfolio_id, snapshot_date)`
   - Purpose: Equity rollforward (previous snapshot lookup)
   - Impact: Speeds up snapshot-based calculations

### From Migration j7k8l9m0n1o2

4. **idx_positions_active_complete**
   - Table: `positions`
   - Columns: `(portfolio_id, deleted_at, exit_date, investment_class)`
   - Partial: `WHERE deleted_at IS NULL`
   - Purpose: Get active PUBLIC positions for portfolio
   - Impact: **90%+ query speedup**

5. **idx_market_data_valid_prices**
   - Table: `market_data_cache`
   - Columns: `(symbol, date)`
   - Partial: `WHERE close > 0`
   - Purpose: Filter out null/zero prices
   - Impact: Eliminates invalid price lookups

6. **idx_positions_symbol_active**
   - Table: `positions`
   - Columns: `(deleted_at, symbol, exit_date, expiration_date)`
   - Partial: `WHERE deleted_at IS NULL AND symbol IS NOT NULL AND symbol != ''`
   - Purpose: Portfolio aggregations by symbol
   - Impact: Portfolio aggregation speedup

---

## Why Indexes Might Be Missing

### Scenario 1: Schema Dump/Restore Issue
- **What happened**: Schema was migrated using `pg_dump --schema-only` + `pg_restore`
- **Problem**: If migrations weren't run after restore, indexes weren't created
- **Evidence**: Alembic version shows `ec31ab63431d` but indexes don't exist

### Scenario 2: Migration Failure During pgvector Setup
- **What happened**: pgvector migration interrupted or failed
- **Problem**: Alembic marked migration as complete but indexes weren't created
- **Evidence**: `alembic_version` shows latest, but indexes missing

### Scenario 3: CREATE INDEX CONCURRENTLY Failure
- **What happened**: Index creation started but was cancelled/failed
- **Problem**: Partial index exists in invalid state
- **Evidence**: Index exists but is marked as invalid in `pg_indexes`

---

## Recommended Workflow

### Step 1: Diagnose
```bash
cd backend
uv run python scripts/database/diagnose_railway_performance.py
```

Review the report. Look for:
- Number of missing critical indexes
- Table sizes (especially `market_data_cache`)
- Row counts

### Step 2: Create Missing Indexes (if needed)
```bash
# Dry run first to see what will be created
uv run python scripts/database/create_missing_indexes.py

# If output looks good, run for real
uv run python scripts/database/create_missing_indexes.py --live
```

### Step 3: Update Table Statistics
```bash
# This helps PostgreSQL choose optimal query plans
railway run 'psql -c "ANALYZE;"'
```

### Step 4: Test Performance
```bash
cd backend
uv run python scripts/run_batch_calculations.py
```

Expected: 3 seconds per day (was 60 seconds)

### Step 5: Verify in Production
- Run batch calculations on Railway
- Monitor execution time
- Check logs for any errors

---

## If Indexes Are Already Present

If the diagnostic shows all 6 indexes exist but performance is still slow, investigate:

### 1. Network Latency
Railway's database is in the cloud - network round-trips add up.

**Test**:
```bash
# From local machine to Railway
time railway run 'psql -c "SELECT 1;"'
```

If latency is >100ms, this could explain 10-20x slower batch operations.

### 2. Database Resource Limits
Railway may have CPU/memory limits on the PostgreSQL instance.

**Check**: Railway dashboard → PostgreSQL service → Metrics

### 3. Missing Table Statistics
PostgreSQL query planner needs current statistics.

**Fix**:
```bash
railway run 'psql -c "ANALYZE VERBOSE;"'
```

### 4. Invalid Indexes
Indexes may exist but be marked invalid.

**Check**:
```sql
SELECT
    schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname IN (
    'idx_market_data_cache_symbol_date',
    'idx_positions_portfolio_deleted',
    'idx_snapshots_portfolio_date',
    'idx_positions_active_complete',
    'idx_market_data_valid_prices',
    'idx_positions_symbol_active'
);
```

---

## Database Connection Details

### Current Setup (from .env)
```
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@pgvector.railway.internal:5432/railway
```

This is Railway's **internal** URL (only works from within Railway).

### For External Access
Use the **public** URL:
```
postgresql://postgres:PASSWORD@junction.proxy.rlwy.net:47057/railway
```

Get this from: Railway Dashboard → PostgreSQL → Variables → `DATABASE_PUBLIC_URL`

---

## Files Created

1. **diagnose_railway_performance.py** - Main diagnostic script
2. **create_missing_indexes.py** - Index creation script
3. **compare_schemas_simple.py** - Full schema comparison
4. **check_railway_indexes.py** - Alternative index checker
5. **SCHEMA_COMPARISON_GUIDE.md** - This guide

---

## Expected Outcomes

### Before Fix
- Batch calculation: **60 seconds per day**
- Full batch run (1 year): **6+ hours**
- Database load: High (full table scans)

### After Fix
- Batch calculation: **3 seconds per day**
- Full batch run (1 year): **~18 minutes**
- Database load: Low (index scans)

### Performance Improvement
- **20x faster** batch calculations
- **95% reduction** in database I/O
- **90%+ speedup** on position queries

---

## Troubleshooting

### "Connection refused"
- Check Railway database is running
- Verify you're using `DATABASE_PUBLIC_URL` for external access
- Check firewall/network settings

### "Permission denied"
- Verify database password is correct
- Check user has `CREATE` permission on schema
- May need superuser for `CREATE EXTENSION`

### "Index already exists"
- This is good! Index is present
- Move on to checking other indexes
- If all exist, investigate other performance factors

### "Cannot create index CONCURRENTLY in transaction"
- Make sure you're not in an explicit transaction
- The script uses direct connection (not in transaction)
- If using `psql`, don't use `BEGIN/COMMIT`

---

## Next Steps

1. **Run the diagnostic** to identify missing indexes
2. **Create missing indexes** using the provided script
3. **Update statistics** with `ANALYZE`
4. **Test performance** with batch calculations
5. **Monitor** Railway metrics to verify improvement

---

## Support Files

- **Migration files**:
  - `alembic/versions/i6j7k8l9m0n1_add_composite_indexes_for_performance.py`
  - `alembic/versions/j7k8l9m0n1o2_add_priority_performance_indexes.py`

- **Documentation**:
  - `_docs/guides/RAILWAY_DATA_DOWNLOAD_GUIDE.md`
  - `scripts/railway/RAILWAY_MIGRATION_FIX.md`
  - `PlanningDocs/RAILWAY_PGVECTOR_MIGRATION_PLAN.md`

---

**Last Updated**: 2025-12-18
**Author**: AI Analysis of Railway Performance Issues
