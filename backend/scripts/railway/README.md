# Railway Deployment Scripts

Railway-specific scripts for database management, auditing, and operations. All scripts automatically handle Railway's `postgresql://` → `postgresql+asyncpg://` URL conversion.

## Directory Contents

### 🔧 Core Operations (Run in Railway SSH)

**Migration Management:**
- `railway_run_migration.py` - Run Alembic migrations
- `verify_railway_migration.py` - Verify migration status and table changes

**Database Management:**
- `railway_reset_database.py` - Complete database reset and reseed (DESTRUCTIVE)
- `railway_initial_seed.sh` - First-time database setup workflow

**Documentation:**
- `RAILWAY_SEEDING_README.md` - Comprehensive seeding guide

### 📊 Audit Scripts (Run from Local Machine)

**Data Auditing (API-Based):**
- `audit_railway_data.py` - Audit portfolio/position/tag data via API
- `audit_railway_market_data.py` - Audit market data with per-position historical coverage

**Calculation Auditing (Database-Direct):**
- `audit_railway_calculations_verbose.py` - Detailed calculation results (requires `railway run`)

---

## Core Operations

### 1. Run Migrations

**File:** `railway_run_migration.py`

**Purpose:** Run Alembic database migrations on Railway deployment.

**Usage:**
```bash
# In Railway SSH
railway shell
uv run python scripts/railway/railway_run_migration.py
```

**What it does:**
- Automatically converts DATABASE_URL for asyncpg driver
- Runs `alembic upgrade head`
- Shows success/failure status

**When to use:**
- After deploying code with new migrations
- After pulling database schema changes
- During initial Railway setup

**Output:**
```
✅ Converted DATABASE_URL to use asyncpg driver
🚀 Running Alembic migration...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade a1b2c3d4 -> e5f6g7h8
✅ Migration completed successfully!
```

---

### 2. Verify Migration

**File:** `verify_railway_migration.py`

**Purpose:** Verify migration status and check specific table/column changes.

**Usage:**
```bash
# In Railway SSH
railway shell
uv run python scripts/railway/verify_railway_migration.py
```

**What it does:**
- Shows current migration version
- Checks for specific tables (strategy tables removed, position_tags added)
- Verifies schema changes

**When to use:**
- After running migrations to confirm success
- Before reseeding database
- Troubleshooting migration issues

**Output:**
```
✅ Migration version: a766488d98ea
Strategy tables: ✅ REMOVED
positions.strategy_id column: ✅ REMOVED
position_tags table: ✅ EXISTS
```

---

### 3. Reset Database

**File:** `railway_reset_database.py`

**Purpose:** **DESTRUCTIVE** - Completely drop all tables, recreate schema, and reseed with demo data.

**Usage:**
```bash
# In Railway SSH - USE WITH CAUTION
railway shell
uv run python scripts/railway/railway_reset_database.py
```

**What it does:**
1. Converts DATABASE_URL for asyncpg
2. Calls `scripts/database/reset_and_seed.py reset --confirm`
3. Drops all tables
4. Recreates schema via Alembic
5. Seeds demo data:
   - 3 portfolios with 75 positions
   - 130 position-tag relationships
   - 8 factor definitions
   - 18 stress test scenarios

**When to use:**
- Breaking database migrations require full reset
- Corrupted database state
- Testing fresh deployment
- **NEVER on production with real user data**

**⚠️ WARNING:**
```
⚠️  WARNING: This will DROP ALL TABLES and reseed the database!
⚠️  All existing data will be PERMANENTLY DELETED!
```

**Output:**
```
✅ Converted DATABASE_URL to use asyncpg driver
🚀 Starting database reset and reseed...
✅ Database reset and reseed completed successfully!

📊 Demo data created:
  - 3 portfolios with 75 positions
  - 130 position-tag relationships
  - 8 factor definitions
  - 18 stress test scenarios

🔐 Demo accounts:
  - demo_individual@sigmasight.com
  - demo_hnw@sigmasight.com
  - demo_hedgefundstyle@sigmasight.com
  Password (all): demo12345
```

---

### 4. Initial Seed (First-Time Setup)

**File:** `railway_initial_seed.sh`

**Purpose:** Automated 6-step first-time database setup workflow.

**Usage:**
```bash
# From local machine (Railway CLI)
railway ssh bash scripts/railway/railway_initial_seed.sh
```

**What it does:**
1. ✅ Checks for existing data (warns if found)
2. ✅ Seeds demo accounts and portfolios (63 positions)
3. ✅ Validates database setup
4. ✅ Verifies deterministic portfolio IDs
5. ✅ Seeds target prices (105 records)
6. ✅ Shows next steps and API test commands

**When to use:**
- First-time Railway deployment
- Fresh database after `railway db` command
- Initial environment setup

**See also:** `RAILWAY_SEEDING_README.md` for complete documentation

**Output:**
```
============================================
SigmaSight Railway - Initial Database Setup
============================================

✓ DATABASE_URL transformed for asyncpg driver

[Step 1/6] Checking for existing data...
[Step 2/6] Seeding database with demo data...
✓ Demo data seeded successfully
[Step 3/6] Validating database setup...
✓ Database validation passed
[Step 4/6] Verifying deterministic portfolio IDs...
[Step 5/6] Seeding target prices...
✓ Target prices seeded successfully

============================================
✓ Railway Initial Setup Complete!
============================================
```

---

## Audit Scripts (Local Machine)

### 5. Audit Portfolio Data

**File:** `audit_railway_data.py`

**Purpose:** Comprehensive portfolio and position data audit via Railway API.

**Usage:**
```bash
# From local machine (NO SSH needed)
python scripts/railway/audit_railway_data.py
```

**What it does:**
- Logs in to all 3 demo accounts
- Fetches complete portfolio data via `/data/portfolio/{id}/complete` endpoint
- Analyzes position types, investment classes, tags
- Checks data coverage (company names, prices)
- Verifies data quality metrics
- Saves results to `railway_audit_results.json`

**When to use:**
- Verify Railway deployment has correct data
- Check portfolio/position integrity
- Analyze tag assignments
- Generate deployment report

**Requirements:**
- Python 3.11+ with `requests` library
- Railway backend must be running and accessible

**Output:**
```
🚀 Railway Database Audit
Backend: https://sigmasight-be-production.up.railway.app/api/v1
Users to audit: 3

################################################################################
👤 USER: Individual (demo_individual@sigmasight.com)
################################################################################
✅ Logged in successfully
✅ Found 1 portfolio(s)

================================================================================
📊 PORTFOLIO: Balanced Individual Investor Portfolio
================================================================================
ID: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
Position Count: 25
Total Value: $500,000.00

📦 Fetching complete portfolio data...
✅ Holdings: 25 positions

📈 Position Types:
   EQUITY: 20
   CALL: 3
   PUT: 2

💼 Investment Classes:
   US_EQUITY: 20
   OPTIONS: 5

🏢 Data Coverage:
   Company Names: 25/25 (100.0%)
   Last Prices: 25/25 (100.0%)

🏷️  Position Tags: 45 tag assignments
   Unique Tags: 8
   Tags: Growth, Large Cap, Technology, Value, ...

🔍 Checking data quality...
✅ Data Quality Report:
   Total Positions: 25
   With Greeks: 5
   With Factors: 25
   Completeness: 95.0%

================================================================================
📊 AUDIT SUMMARY
================================================================================
Total Portfolios: 3
Total Positions: 75
Total Value: $1,500,000.00

✅ Audit complete! Results saved to: railway_audit_results.json
```

---

### 6. Audit Market Data

**File:** `audit_railway_market_data.py`

**Purpose:** Detailed market data audit with per-position historical price coverage.

**Usage:**
```bash
# From local machine (NO SSH needed)
python scripts/railway/audit_railway_market_data.py
```

**What it does:**
- Logs in via Railway API
- Tests market quotes endpoint
- **Shows detailed per-symbol historical price coverage:**
  - Number of days of historical data
  - First date and last date of data
  - Data gaps identification
- Tests factor ETF prices
- Checks company profile coverage
- Generates summary statistics

**When to use:**
- Verify batch job populated market data
- Identify data gaps in historical prices
- Check market data coverage before running calculations
- Troubleshoot missing price data

**Requirements:**
- Python 3.11+ with `requests` library
- Railway backend must be running and accessible

**Output:**
```
🚀 Railway Market Data Audit
Backend: https://sigmasight-be-production.up.railway.app/api/v1

🔐 Logging in...
✅ Authenticated

📋 Fetching portfolio symbols...
✅ Found 17 unique symbols

   Symbols: AAPL, GOOGL, MSFT, TSLA, NVDA, META, AMZN, ...

🏢 Testing Company Profile Data
================================================================================
✅ Position Details: 200
   Total positions: 17
   With company name: 17 (100.0%)
   Missing company name: 0 (0.0%)

   Sample:
      AAPL: Apple Inc.

📊 Testing Market Quotes Endpoint
================================================================================
✅ Market Quotes: 200
   Requested: 5 symbols
   Received: 5 quotes

   Sample quote for AAPL:
      Price: $175.43
      Change: 1.25%
      Volume: 54,123,456

📈 Testing Historical Prices - Detailed Per-Position Coverage
================================================================================
✅ Historical Prices: 200

SYMBOL       STATUS  DAYS   FIRST DATE   LAST DATE
------------ ------ ------ ------------ ------------
AAPL         ✅      90     2024-07-07   2024-10-05
AMZN         ✅      89     2024-07-08   2024-10-05
BRK.B        ❌      0      N/A          N/A
GOOGL        ✅      90     2024-07-07   2024-10-05
GLD          ✅      88     2024-07-09   2024-10-05
HOME_EQUITY  ❌      0      N/A          N/A
META         ✅      90     2024-07-07   2024-10-05
MSFT         ✅      90     2024-07-07   2024-10-05
NVDA         ✅      87     2024-07-10   2024-10-05
QQQ          ✅      90     2024-07-07   2024-10-05
SPY          ✅      90     2024-07-07   2024-10-05
TSLA         ✅      85     2024-07-12   2024-10-05

================================================================================
HISTORICAL DATA SUMMARY:
   Total Symbols: 17
   With Data: 14 (82.4%)
   Missing Data: 3 (17.6%)
   Average Days per Symbol: 72.3

🏭 Testing Factor ETF Prices Endpoint
================================================================================
✅ Factor ETF Prices: 200
   Factor ETFs tracked: 8
      SPY: 90 data points
      QQQ: 90 data points
      IWM: 90 data points
      EFA: 90 data points

================================================================================
📊 MARKET DATA AUDIT SUMMARY
================================================================================
Company Profiles: 17/17 (100.0%)
Market Quotes: ✅ Working
Historical Prices: 14/17 symbols with data (72.3 avg days)
Factor ETFs: 8 tracked

✅ Market data audit complete!
```

---

### 7. Audit Analytics (Client-Friendly Reports)

**File:** `audit_railway_analytics.py`

**Purpose:** Comprehensive analytics audit across all 6 `/analytics/` endpoints with client-ready formatting.

**Usage:**
```bash
# From local machine (NO SSH needed)
python scripts/railway/audit_railway_analytics.py
```

**What it does:**
- Logs in to all 3 demo portfolios via Railway API
- Tests all 6 analytics endpoints for each portfolio:
  1. **Portfolio Summary** (`/analytics/portfolio/{id}/overview`)
     - Account value, P&L, market exposure breakdown
     - Leverage ratio, position counts
  2. **Risk Factor Analysis** (`/analytics/portfolio/{id}/factor-exposures`)
     - 7-factor model exposures with beta values
     - Dollar exposure per factor
  3. **Holdings Factor Breakdown** (`/analytics/portfolio/{id}/positions/factor-exposures`)
     - Position-level factor exposures
     - Sorted by market beta
  4. **Correlation Analysis** (`/analytics/portfolio/{id}/correlation-matrix`)
     - Position correlation matrix
     - Data quality metrics
  5. **Stress Testing** (`/analytics/portfolio/{id}/stress-test`)
     - Scenario analysis with P&L impacts
     - Best/worst case scenarios
  6. **Diversification Score** (`/analytics/portfolio/{id}/diversification-score`)
     - Diversification rating (0-100)
     - Actionable insights
- **Generates client-friendly reports** (not JSON dumps)
- Saves to `railway_analytics_audit_report.txt` (31KB, formatted)
- Saves JSON results to `railway_analytics_audit_results.json`

**When to use:**
- Verify all analytics endpoints are working
- Generate client-ready analytics reports
- Check calculation completeness across portfolios
- Present portfolio analytics to stakeholders
- Validate analytics API before frontend integration

**Requirements:**
- Python 3.11+ with `requests` library
- Railway backend must be running and accessible

**Output (Client-Friendly Format):**
```
🚀 Railway Analytics Audit
Backend: https://sigmasight-be-production.up.railway.app/api/v1

========================================================================================================================
USER: Individual Investor (demo_individual@sigmasight.com)
========================================================================================================================

Portfolio: Demo Individual Investor Portfolio
Portfolio ID: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
Position Count: 16
Total Value: $1,021,834.72

   📊 PORTFOLIO SUMMARY
   ════════════════════════════════════════════════════════════════════════════

   ACCOUNT VALUE
   ----------------------------------------------------------------------------
   Total Equity:                      $     485,000.00
   Cash Balance:                      $     -51,834.72
   Leverage Ratio:                               1.11x

   PROFIT & LOSS
   ----------------------------------------------------------------------------
   Total P&L:                         $      51,974.72  (+10.72%)
   Unrealized P&L:                    $      51,974.72
   Realized P&L:                      $           0.00

   📈 RISK FACTOR ANALYSIS
   ════════════════════════════════════════════════════════════════════════════

   RISK FACTOR          BETA         DOLLAR EXPOSURE
   -------------------- ------------ --------------------
   Market Beta                0.535  $        259,617.82
   Momentum                   0.544  $        263,944.87
   Value                      0.484  $        234,935.60

   🎲 PORTFOLIO DIVERSIFICATION ANALYSIS
   ════════════════════════════════════════════════════════════════════════════

   Diversification Score:                       100.0/100  🌟
   Rating:                                       Excellent
   Average Correlation:                               0.00

✅ Analytics audit complete!
   - JSON results: railway_analytics_audit_results.json
   - Detailed report: railway_analytics_audit_report.txt
```

**Report File Format:**
The report file uses business-friendly formatting instead of JSON:
- Professional sections with headers and dividers
- Currency formatting with alignment
- Percentage changes with +/- signs
- Emoji indicators for ratings
- Interpretation guides for business users
- Factor analysis with beta explanations

---

## Common Workflows

### Initial Railway Deployment

```bash
# 1. Deploy to Railway
railway up --detach

# 2. Wait for deployment to complete
railway logs

# 3. Run initial seed
railway ssh bash scripts/railway/railway_initial_seed.sh

# 4. Verify deployment (from local machine)
python scripts/railway/audit_railway_data.py
python scripts/railway/audit_railway_market_data.py
```

---

### Applying Breaking Migration

```bash
# 1. Deploy code with migration
railway up --detach

# 2. SSH into Railway
railway shell

# 3. Run migration
uv run python scripts/railway/railway_run_migration.py

# 4. Verify migration
uv run python scripts/railway/verify_railway_migration.py

# 5. If migration requires reset (check migration notes):
uv run python scripts/railway/railway_reset_database.py

# 6. Exit SSH
exit

# 7. Verify results (from local machine)
python scripts/railway/audit_railway_data.py
```

---

### Daily Batch Processing

**Two Methods Available:**

#### Method 1: API-Based (Recommended - No SSH Required)

```bash
# From local machine - triggers batch via REST API with real-time monitoring
python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app --force

# Specific portfolio only
python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app --portfolio-id <uuid>

# Check status without triggering
python scripts/check_batch_results.py --url https://sigmasight-be-production.up.railway.app
```

**Features:**
- ✅ No SSH access needed
- ✅ Real-time progress monitoring with live updates
- ✅ Works from local machine or CI/CD
- ✅ Uses `/api/v1/admin/batch/run` and `/api/v1/admin/batch/run/current` endpoints

#### Method 2: SSH-Based (Direct Execution)

```bash
# 1. SSH into Railway
railway ssh

# 2. Run daily batch job directly (market data + calculations)
uv run python scripts/automation/railway_daily_batch.py --force

# 3. Verify results
uv run python scripts/verification/verify_batch_results.py
uv run python scripts/verification/verify_database_state.py

# 4. Exit SSH
exit

# 5. Audit market data coverage (from local machine)
python scripts/railway/audit_railway_market_data.py
```

**When to use SSH method:**
- Debugging batch issues
- Running verification scripts on Railway
- Direct access to logs

---

### Troubleshooting Data Issues

```bash
# 1. Check data quality (from local machine)
python scripts/railway/audit_railway_data.py
python scripts/railway/audit_railway_market_data.py
railway run python scripts/railway/audit_railway_calculations_verbose.py  # Detailed calculation results

# 2. Identify issues from audit output

# 3. If needed, reset database (requires SSH)
railway ssh
uv run python scripts/railway/railway_reset_database.py
exit

# 4. Re-run batch processing (use API method - easier)
python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app --force

# 5. Verify fix
python scripts/railway/audit_railway_market_data.py
railway run python scripts/railway/audit_railway_calculations_verbose.py
```

---

### 8. API Batch Monitoring (Recommended)

**File:** `scripts/api_batch_monitor.py`

**Purpose:** Trigger and monitor batch processing via REST API without SSH access.

**Usage:**
```bash
# Railway production (recommended)
python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app --force

# Local development
python scripts/api_batch_monitor.py

# Specific portfolio
python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app --portfolio-id <uuid>

# Custom polling interval
python scripts/api_batch_monitor.py --url https://sigmasight-be-production.up.railway.app --poll-interval 5
```

**What it does:**
- Authenticates via `/auth/login` endpoint
- Triggers batch via `POST /admin/batch/run` with optional `--force` flag
- Monitors progress via `GET /admin/batch/run/current`
- Shows real-time progress bar with job counts and status
- Automatically polls every N seconds (default: 3)
- Exits when batch completes (status: idle)

**When to use:**
- **Primary method** for triggering batch processing
- CI/CD pipelines
- Scheduled batch jobs
- Remote batch triggering without Railway CLI
- Real-time monitoring needed

**Output:**
```
🔐 Authenticating as demo_individual@sigmasight.com...
✅ Authentication successful

🚀 Triggering batch run for all portfolios...
✅ Batch started: fdd4b9f0-be3c-4ff4-9299-eae22d1972cc
📊 Poll URL: /api/v1/admin/batch/run/current

📡 Monitoring progress (polling every 3s)...
================================================================================
[22:03:55] [████████████████░░░░░░░░░░░░░░░░░░░░░░░] 41.7% | 3m 12s | 10/24 jobs | factor_analysis...
```

**Related Scripts:**
- `scripts/test_railway_batch.py` - Simple batch trigger + verification
- `scripts/check_batch_results.py` - Check batch status without triggering

---

### 9. Audit Calculation Results (Verbose)

**File:** `scripts/railway/audit_railway_calculations_verbose.py`

**Purpose:** Detailed audit of batch calculation results with sample data from each engine.

**Usage:**
```bash
# From local machine (requires Railway CLI to inject DATABASE_URL)
railway run python scripts/railway/audit_railway_calculations_verbose.py

# Alternative: Set DATABASE_URL manually then run
export DATABASE_URL="postgresql://user:pass@host:port/db"
python scripts/railway/audit_railway_calculations_verbose.py
```

**What it does:**
- Audits all 3 portfolios for calculation data
- Shows detailed results from each calculation engine:
  - **Snapshots**: Latest snapshot with full metrics
  - **Factor Exposures**: Actual beta values per position (Market, Value, Growth, etc.)
  - **Correlations**: Top 20 pairwise correlations with correlation values
  - **Stress Tests**: All scenarios with P&L impacts (direct and correlated)
  - **Greeks**: Options Greeks if any exist
- Saves results to `railway_calculations_audit_report.txt` (detailed)
- Saves summary to `railway_calculations_audit_results.json`

**When to use:**
- Verify batch calculations ran for all portfolios
- Debug missing calculation data
- Generate detailed calculation reports
- Check which portfolios have data vs "No data"

**Output:**
```
================================================================================
📊 PORTFOLIO SNAPSHOTS: Demo Individual Investor Portfolio
================================================================================
Total snapshots found: 1

Latest Snapshot (2025-10-06):
  Position Count: 16
  Total Market Value: $484,860.00
  Long Value: $484,860.00
  Portfolio Delta: 1.23

================================================================================
📈 FACTOR EXPOSURES: Demo Individual Investor Portfolio
================================================================================
Total exposure records: 112

Factor Exposures by Position (sample, latest calculation):

SYMBOL       FACTORS                                                      DATE
----------------------------------------------------------------------------------------
AAPL         Gro: 0.89, Low: 0.41, Mar: 1.14, Mom: 0.18, Qua: 0.97...   2025-10-06
TSLA         Gro: 1.47, Low: 0.49, Mar: 2.08, Mom: 1.24, Qua: 1.57...   2025-10-06
```

---

## Important Notes

### DATABASE_URL Auto-Conversion

All Railway scripts automatically convert DATABASE_URL:
```python
# Railway provides: postgresql://user:pass@host/db
# Scripts convert to: postgresql+asyncpg://user:pass@host/db
```

This is required for SQLAlchemy async operations. **No manual configuration needed.**

### Audit Scripts Run Locally

Most `audit_*.py` scripts **do NOT need Railway SSH**:
- Run from your local machine
- Hit Railway API endpoints directly (except `audit_railway_calculations_verbose.py`)
- Require `requests` library only
- Faster than SSH for quick checks

**Exception:** `audit_railway_calculations_verbose.py` requires direct database access:
- Use `railway run` to inject DATABASE_URL
- OR set DATABASE_URL environment variable manually

### SSH vs Local Execution

**In Railway SSH:**
- Migration operations (`railway_run_migration.py`, `verify_railway_migration.py`)
- Database operations (`railway_reset_database.py`, `railway_initial_seed.sh`)
- Batch processing (`automation/railway_daily_batch.py`)

**From Local Machine:**
- Auditing (`audit_railway_data.py`, `audit_railway_market_data.py`)
- Quick health checks
- Report generation

### Demo Credentials

All demo accounts use the same password:
```
Email: demo_individual@sigmasight.com
Email: demo_hnw@sigmasight.com
Email: demo_hedgefundstyle@sigmasight.com
Password: demo12345
```

### Deterministic Portfolio IDs

Portfolio IDs are deterministic for testing:
```
Individual: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
HNW:        e23ab931-a033-edfe-ed4f-9d02474780b4
Hedge Fund: fcd71196-e93e-f000-5a74-31a9eead3118
```

---

## Troubleshooting

### "command not found" in Railway SSH

**Problem:** `bash: uv: command not found`

**Solution:** Use full `uv run python` prefix:
```bash
uv run python scripts/railway/railway_run_migration.py
```

### "asyncio extension requires async driver"

**Problem:** Script fails with async driver error

**Solution:** Already fixed in all scripts via DATABASE_URL conversion. If seeing this error:
1. Check you're using the Railway scripts (not local dev scripts)
2. Verify DATABASE_URL is set: `echo $DATABASE_URL`
3. Restart Railway shell session

### Audit scripts fail with connection error

**Problem:** `audit_railway_*.py` can't connect to Railway

**Solution:**
1. Check Railway deployment is running: `railway status`
2. Verify backend URL in script: `RAILWAY_URL = "https://sigmasight-be-production.up.railway.app/api/v1"`
3. Test Railway API health: `curl https://sigmasight-be-production.up.railway.app/health`

### Migration verification shows wrong version

**Problem:** `verify_railway_migration.py` shows old migration version

**Solution:**
1. Check if migration actually ran: `railway logs --lines 100`
2. Re-run migration: `uv run python scripts/railway/railway_run_migration.py`
3. Check for migration errors in Railway logs

---

## Related Documentation

- **Main README**: `backend/README.md` - Railway operations overview
- **Scripts README**: `scripts/README.md` - All backend scripts
- **Seeding Guide**: `RAILWAY_SEEDING_README.md` - Detailed seeding documentation
- **Daily Batch**: `scripts/automation/railway_daily_batch.py` - Daily processing script
- **Verification**: `scripts/verification/` - Database verification scripts

---

## Summary

**Railway Scripts Overview:**

### SSH-Based (Require Railway CLI)
1. ✅ `railway_run_migration.py` - Run Alembic migrations
2. ✅ `verify_railway_migration.py` - Verify migration status
3. ✅ `railway_reset_database.py` - Reset database (DESTRUCTIVE)
4. ✅ `railway_initial_seed.sh` - First-time setup workflow

### API-Based (No SSH Required) - **Recommended**
5. ✅ `scripts/api_batch_monitor.py` - Trigger & monitor batch processing via API
6. ✅ `audit_railway_data.py` - Audit portfolio/position data
7. ✅ `audit_railway_market_data.py` - Audit market data with per-position coverage
8. ✅ `audit_railway_analytics.py` - Audit analytics endpoints with client-friendly reports
9. ✅ `scripts/test_railway_batch.py` - Simple batch trigger + verification
10. ✅ `scripts/check_batch_results.py` - Check batch status

### Database-Direct (Requires DATABASE_URL)
11. ✅ `audit_railway_calculations_verbose.py` - Detailed calculation results audit (use `railway run`)

### Batch Processing Methods
- **API Method (Recommended)**: `python scripts/api_batch_monitor.py --url <railway-url> --force`
  - No SSH needed, real-time monitoring, works from anywhere
- **SSH Method**: `railway ssh` then `uv run python scripts/automation/railway_daily_batch.py --force`
  - Direct execution, useful for debugging

**Clean, focused, documented.** Each script has a specific purpose.

---

**Last Updated**: October 8, 2025
**Scripts Version**: 3.1 (Added client-friendly analytics audit)
