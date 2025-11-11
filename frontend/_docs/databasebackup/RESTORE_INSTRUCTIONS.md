# SigmaSight Railway Database Restore Instructions

**For AI Agents**: Complete guide to restore local database backups to Railway PostgreSQL.

---

## 📋 Overview

These backups were created from the **local Docker PostgreSQL database** and can be restored to the **Railway production database**.

**Backup Location**: `D:\SigmaSight_Backups\`

**Backup Types**:
- **Full**: Complete database dump (all tables, all data)
- **Critical**: Core tables only (users, portfolios, positions, position_tags, tags_v2)

---

## 🎯 When to Use This

### Use Full Backup When:
- Railway database needs complete reset to match local
- After breaking schema changes in Railway
- Restoring entire application state
- Fresh Railway deployment setup

### Use Critical Tables Backup When:
- Preserving user data after schema changes
- Migrating core data between databases with different schemas
- Selective table restoration
- Database structure changed but need user/portfolio data

---

## 🚀 Restore Methods

### Method 1: Railway CLI (Recommended)

**Prerequisites**:
- Railway CLI installed: `npm install -g @railway/cli`
- Logged in to Railway: `railway login`
- Linked to project: `railway link`

**Restore Full Backup**:
```bash
# Navigate to backup directory
cd D:\SigmaSight_Backups\full

# Find latest backup
dir /od

# Restore to Railway (replace with actual filename)
type backup_20251008_143000.sql | railway run psql $DATABASE_URL
```

**Restore Critical Tables Only**:
```bash
# Navigate to critical backups
cd D:\SigmaSight_Backups\critical

# Restore critical tables
type critical_20251008_143000.sql | railway run psql $DATABASE_URL
```

---

### Method 2: Direct psql (Requires Railway DATABASE_URL)

**Get Railway DATABASE_URL**:
```bash
railway variables --json
# Look for DATABASE_URL value
```

**Set Environment Variable**:
```bash
# PowerShell
$env:DATABASE_URL = "postgresql://postgres:password@host:port/railway"

# CMD
set DATABASE_URL=postgresql://postgres:password@host:port/railway
```

**Restore Backup**:
```bash
# Full backup
psql $DATABASE_URL < D:\SigmaSight_Backups\full\backup_20251008_143000.sql

# Critical tables
psql $DATABASE_URL < D:\SigmaSight_Backups\critical\critical_20251008_143000.sql
```

---

## 📂 Backup File Structure

### Full Backup Contents
```
backup_20251008_143000.sql
├── Schema (CREATE TABLE statements)
│   ├── users
│   ├── portfolios
│   ├── positions
│   ├── position_tags
│   ├── tags_v2
│   ├── company_profiles
│   ├── historical_prices
│   ├── portfolio_snapshots
│   ├── position_greeks
│   ├── position_factor_exposures
│   └── ... (all other tables)
├── Data (INSERT statements)
│   └── All data from all tables
└── Constraints & Indexes
```

### Critical Tables Backup Contents
```
critical_20251008_143000.sql
├── Schema (5 tables only)
│   ├── users
│   ├── portfolios
│   ├── positions
│   ├── position_tags
│   └── tags_v2
└── Data (Core user data only)
```

---

## ⚠️ Important Considerations

### Before Restoring

1. **Check Railway Database State**:
   ```bash
   # SSH into Railway
   railway shell

   # Count existing records
   uv run python -c "
   import asyncio
   from sqlalchemy import select, func
   from app.database import get_async_session
   from app.models.users import User, Portfolio
   from app.models.positions import Position

   async def check():
       async with get_async_session() as db:
           users = await db.execute(select(func.count(User.id)))
           portfolios = await db.execute(select(func.count(Portfolio.id)))
           positions = await db.execute(select(func.count(Position.id)))
           print(f'Users: {users.scalar()}')
           print(f'Portfolios: {portfolios.scalar()}')
           print(f'Positions: {positions.scalar()}')

   asyncio.run(check())
   "
   ```

2. **Backup Railway Database First** (if it has data you want to keep):
   ```bash
   # From local machine
   railway run pg_dump $DATABASE_URL > railway_backup_before_restore.sql
   ```

3. **Clear Target Tables** (if restoring to existing database):
   ```bash
   railway shell
   uv run python scripts/railway/railway_reset_database.py
   # This drops all tables and recreates schema
   ```

### UUID Conflicts

If restoring to a database that already has data with same UUIDs:

**Option A: Clear conflicting data first**
```sql
-- In Railway psql
DELETE FROM position_tags WHERE position_id IN (SELECT id FROM positions WHERE portfolio_id = 'conflicting-uuid');
DELETE FROM positions WHERE portfolio_id = 'conflicting-uuid';
DELETE FROM portfolios WHERE id = 'conflicting-uuid';
```

**Option B: Modify backup SQL file**
Open the .sql file in a text editor and use find/replace to change UUIDs before restoring.

---

## 🔍 Verification After Restore

### Check Data Counts
```bash
railway shell

uv run python -c "
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position

async def verify():
    async with get_async_session() as db:
        users = await db.execute(select(func.count(User.id)))
        portfolios = await db.execute(select(func.count(Portfolio.id)))
        positions = await db.execute(select(func.count(Position.id)))

        print('✅ Data restored successfully!')
        print(f'   Users: {users.scalar()}')
        print(f'   Portfolios: {portfolios.scalar()}')
        print(f'   Positions: {positions.scalar()}')

asyncio.run(verify())
"
```

### Test API Endpoints
```bash
# From local machine
python C:\Users\BenBalbale\CascadeProjects\SigmaSight\backend\scripts\railway\audit_railway_data.py
```

### Check Specific Portfolio
```bash
railway shell

uv run python -c "
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio

async def check_portfolio():
    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.portfolio_name.like('%Individual%'))
        )
        portfolio = result.scalar_one_or_none()
        if portfolio:
            print(f'✅ Found portfolio: {portfolio.portfolio_name}')
            print(f'   ID: {portfolio.id}')
        else:
            print('❌ Portfolio not found')

asyncio.run(check_portfolio())
"
```

---

## 🛠️ Troubleshooting

### Error: "relation already exists"

**Cause**: Trying to restore schema into database that already has tables.

**Solution**:
```bash
# Option 1: Drop all tables first
railway shell
uv run python scripts/railway/railway_reset_database.py

# Option 2: Use --data-only flag (PostgreSQL 12+)
# Modify the backup to only include data, not schema
```

### Error: "duplicate key value violates unique constraint"

**Cause**: UUID conflicts with existing data.

**Solution**: Clear existing data first or modify backup UUIDs.

### Error: "column does not exist"

**Cause**: Schema mismatch between backup and target database.

**Solution**:
1. Run Alembic migrations in Railway to match schema:
   ```bash
   railway shell
   uv run python scripts/railway/railway_run_migration.py
   ```
2. Or restore full backup (includes schema)

### Error: "psql: command not found"

**Cause**: PostgreSQL client tools not installed locally.

**Solution**: Use Railway CLI method instead (Method 1).

---

## 📝 Common Scenarios

### Scenario 1: Fresh Railway Deployment

**Steps**:
1. Deploy backend to Railway
2. Railway auto-provisions PostgreSQL
3. SSH into Railway and run migrations
4. Restore full backup from local
5. Verify with audit scripts

**Commands**:
```bash
# Step 1-2: Deploy
railway up --detach

# Step 3: Migrations
railway shell
uv run python scripts/railway/railway_run_migration.py
exit

# Step 4: Restore backup
cd D:\SigmaSight_Backups\full
type backup_20251008_143000.sql | railway run psql $DATABASE_URL

# Step 5: Verify
python C:\Users\BenBalbale\CascadeProjects\SigmaSight\backend\scripts\railway\audit_railway_data.py
```

---

### Scenario 2: Breaking Migration Requires Data Preservation

**Problem**: New Alembic migration drops columns you need.

**Steps**:
1. Backup local database before migration
2. Run migration locally and in Railway
3. Extract needed data from backup
4. Manually insert into new schema

**Commands**:
```bash
# Step 1: Backup BEFORE migration
D:\SigmaSight_Backups\backup_local_database.bat

# Step 2: Run migrations
cd C:\Users\BenBalbale\CascadeProjects\SigmaSight\backend
uv run alembic upgrade head

railway shell
uv run python scripts/railway/railway_run_migration.py
exit

# Step 3: Extract specific data from backup
# Open D:\SigmaSight_Backups\full\backup_TIMESTAMP.sql
# Search for table you need
# Copy INSERT statements

# Step 4: Create custom SQL script with modified INSERT statements
# Match new schema
# Run against Railway
```

---

### Scenario 3: Selective Table Restore

**Need**: Only restore users and portfolios, not positions.

**Steps**:
```bash
# Create custom backup from local
docker exec backend-postgres-1 pg_dump -U sigmasight -d sigmasight_db -t users -t portfolios > D:\SigmaSight_Backups\custom_user_portfolio_only.sql

# Restore to Railway
type D:\SigmaSight_Backups\custom_user_portfolio_only.sql | railway run psql $DATABASE_URL
```

---

## 🔐 Demo Account Credentials

After restore, these accounts should exist:

```
Email: demo_individual@sigmasight.com
Email: demo_hnw@sigmasight.com
Email: demo_hedgefundstyle@sigmasight.com
Password (all): demo12345
```

**Test Login**:
```bash
curl -X POST https://sigmasight-be-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_individual@sigmasight.com","password":"demo12345"}'
```

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Create backup | Run `D:\SigmaSight_Backups\backup_local_database.bat` |
| List backups | `dir D:\SigmaSight_Backups\full` |
| Restore to Railway | `type backup.sql \| railway run psql $DATABASE_URL` |
| Verify Railway data | `python scripts/railway/audit_railway_data.py` |
| Check Railway DB | `railway shell` then `uv run python -c "..."` |

---

## 🎯 Summary

**Backup Process**: Simple - run `backup_local_database.bat`

**Restore Process**:
1. Choose full or critical backup
2. Use Railway CLI (`railway run psql`)
3. Verify with audit scripts

**Critical Tables**: users, portfolios, positions, position_tags, tags_v2

**Always**: Backup Railway first if it has data you care about!

---

**Created**: 2025-10-08
**Location**: D:\SigmaSight_Backups\
**Project**: SigmaSight Backend
