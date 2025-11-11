# Production Database Migration Guide

**Target**: Migrate Railway production database from `19c513d3bf90` to `792ffb1ab1ad`

**Status**: 23 migrations pending, critical schema elements missing

---

## Current State (from audit_production_schema.py)

### Missing Tables (7)
- `equity_changes` - Equity changes table
- `position_realized_events` - Position realized events
- `batch_run_tracking` - Batch run tracking
- `spread_factor_definitions` - Spread factors
- `position_volatility` - Position volatility
- `ai_insights` - AI insights
- `ai_insight_templates` - AI templates

### Missing Columns in portfolio_snapshots (5 groups)
- `beta_calculated_90d`, `beta_provider_1y` - Calculated/provider beta
- `realized_volatility_21d` - Volatility fields
- `hhi` - Concentration metrics
- `target_price_return_eoy` - Target price fields

---

## Migration Options

### Option 1: Railway CLI (RECOMMENDED)

**Requirements**:
- Railway CLI installed locally
- Railway project linked

**Steps**:
```bash
# 1. Link to Railway project (if not already)
railway link

# 2. Run migrations on Railway
railway run alembic upgrade head

# 3. Verify migration
railway run python scripts/check_production_db.py

# 4. Apply Short Interest fix
railway run python scripts/fix_short_interest_railway.py
```

**Advantages**:
- Alembic handles all schema changes automatically
- Safest approach with proper migration rollback
- Creates all missing tables and columns
- Handles dependencies and constraints correctly

---

### Option 2: Direct Stamping (NOT RECOMMENDED FOR THIS CASE)

**Why NOT recommended**:
- 7 tables completely missing
- 5 column groups missing
- Stamping without schema changes will cause application failures

**When stamping IS appropriate**:
- When all schema elements already exist
- When database was manually updated
- When consolidating migration history

**Current assessment**: Production database needs actual migrations, not just stamping.

---

### Option 3: Manual SQL Migration (ADVANCED)

**Requirements**:
- Export SQL from local database with full schema
- Apply manually to production

**Steps**:
```bash
# 1. Generate migration SQL locally
cd backend
alembic upgrade head --sql > production_migration.sql

# 2. Review SQL carefully
cat production_migration.sql

# 3. Apply to production (via Railway CLI or psql)
railway run psql < production_migration.sql

# 4. Stamp alembic version
railway run python scripts/migrate_production_db.py
```

**Advantages**:
- Full control over what gets executed
- Can review SQL before applying

**Disadvantages**:
- More error-prone
- Requires careful review
- May miss edge cases Alembic handles

---

## Pre-Migration Checklist

- [ ] Verify production database backup exists
- [ ] Test migrations on staging environment first
- [ ] Schedule maintenance window if needed
- [ ] Notify users of potential downtime
- [ ] Have rollback plan ready

---

## Post-Migration Steps

### 1. Verify Schema
```bash
railway run python scripts/audit_production_schema.py
```

**Expected**: All tables and columns should show `[EXISTS]`

### 2. Check Alembic Status
```bash
railway run python scripts/check_production_db.py
```

**Expected**: Revision `792ffb1ab1ad`

### 3. Apply Short Interest Fix
```bash
railway run python scripts/fix_short_interest_railway.py
```

**Expected**: Short Interest factor set to `is_active=FALSE`

### 4. Verify Factor Configuration
```bash
railway run python scripts/verify_railway_factors.py
```

**Expected**: 9 active style/macro factors

### 5. Test Application
- Login to production frontend
- Navigate to Risk Metrics page
- Verify market factors display correctly
- Check portfolio analytics work

---

## Rollback Plan

If migration fails:

```bash
# 1. Identify last known good revision
railway run python scripts/check_production_db.py

# 2. Rollback to previous revision
railway run alembic downgrade <previous_revision>

# 3. Verify application still works
```

---

## Scripts Reference

### Audit Scripts
- `check_production_db.py` - Check alembic revision and factor status
- `audit_production_schema.py` - Audit schema completeness

### Migration Scripts
- `migrate_production_db.py` - Stamp database (use only after schema is correct)
- `fix_short_interest_railway.py` - Fix Short Interest factor

### Verification Scripts
- `verify_railway_factors.py` - Verify 9 active factors

---

## Recommended Approach

**Based on audit results, we recommend Option 1 (Railway CLI):**

```bash
# Complete migration workflow
railway run alembic upgrade head
railway run python scripts/audit_production_schema.py
railway run python scripts/fix_short_interest_railway.py
railway run python scripts/verify_railway_factors.py
```

This ensures:
- All 7 missing tables are created
- All 5 missing column groups are added
- Proper constraints and indexes applied
- Alembic version correctly updated
- Short Interest factor fixed
- 9 active factors configured

---

## Questions?

- **Do you have Railway CLI installed?** → Use Option 1
- **Is there a staging environment?** → Test there first
- **Need to review SQL changes?** → Use Option 3
- **All schema already exists?** → Only then consider Option 2

---

**Last Updated**: 2025-11-11
**Production DB**: maglev.proxy.rlwy.net:27062
**Current Revision**: 19c513d3bf90
**Target Revision**: 792ffb1ab1ad
