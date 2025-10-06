# Scripts Directory Organization

This directory contains all utility scripts for the SigmaSight backend, organized by functionality.

> **📚 For complete workflow guides, see:**
> - Initial Setup: [`_guides/BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md`](../_guides/BACKEND_INITIAL_COMPLETE_WORKFLOW_GUIDE.md)
> - Daily Operations: [`_guides/BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md`](../_guides/BACKEND_DAILY_COMPLETE_WORKFLOW_GUIDE.md)
> - Client Onboarding: [`_guides/ONBOARDING_NEW_ACCOUNT_PORTFOLIO.md`](../_guides/ONBOARDING_NEW_ACCOUNT_PORTFOLIO.md)

---

## 🚀 Critical Scripts Quick Reference

### ⚙️ Initial Setup (Run Once - In Order)

1. **Apply Database Migrations** ⚠️ **ALWAYS FIRST**
   ```bash
   # Check current migration status
   uv run alembic current

   # Apply all pending migrations
   uv run alembic upgrade head

   # Verify migrations applied
   uv run alembic history --verbose | head -10
   ```
   > **Critical**: Recent migration `add_equity_balance_to_portfolio` is required for API endpoints to work!

2. **Setup Database Schema** (Choose one method)
   ```bash
   # Method A: Manual Alembic (recommended)
   uv run alembic upgrade head

   # Method B: Automated setup script (alternative)
   uv run python scripts/database/setup_dev_database_alembic.py
   ```

3. **Seed Demo Data** (3 portfolios, 63 positions)
   ```bash
   # Check if data already exists first (IMPORTANT!)
   uv run python scripts/database/check_database_content.py

   # If no data exists, seed it:
   uv run python scripts/database/seed_database.py

   # OR full reset (DESTRUCTIVE - deletes all data):
   uv run python scripts/database/reset_and_seed.py reset --confirm
   ```

4. **Validate Setup** ✅ **CRITICAL**
   ```bash
   # Run comprehensive validation (8/8 checks)
   uv run python scripts/validation/validate_setup.py

   # Alternative verification
   uv run python scripts/verification/verify_setup.py
   ```
   > Expected: `📊 Validation Summary: 8/8 checks passed`

5. **Populate Target Prices** (Optional but recommended)
   ```bash
   # Preview import (dry run)
   uv run python scripts/data_operations/populate_target_prices_via_service.py \
     --csv-file data/target_prices_import.csv --dry-run

   # Execute import (105 records)
   uv run python scripts/data_operations/populate_target_prices_via_service.py \
     --csv-file data/target_prices_import.csv --execute
   ```

6. **Initial Batch Processing** (First run only)
   ```bash
   # Process all portfolios (30-60 seconds per portfolio)
   uv run python scripts/batch_processing/run_batch.py
   ```

---

### 🔄 Daily Operations (Regular Tasks)

#### **1. Database Migrations** ⚠️ **Run After Every Git Pull**
```bash
# ALWAYS run this after pulling code changes
uv run alembic upgrade head
```

#### **2. Market Data Updates** ⭐ **Daily Required**

**Important**: Private positions (real estate, private equity, collectibles) are automatically excluded from price fetching.

```bash
# Sync latest market prices (last 5 trading days)
# Preserves existing historical data, won't overwrite
uv run python -c "
import asyncio
from app.batch.market_data_sync import sync_market_data
asyncio.run(sync_market_data())
"

# Backfill missing historical data (90 days)
# Checks per-symbol coverage with 80% threshold
uv run python -c "
import asyncio
from app.batch.market_data_sync import fetch_missing_historical_data
asyncio.run(fetch_missing_historical_data(days_back=90))
"

# Ensure factor analysis data (252 days) - only if doing factor analysis
uv run python -c "
import asyncio
from app.batch.market_data_sync import validate_and_ensure_factor_analysis_data
from app.database import AsyncSessionLocal

async def validate():
    async with AsyncSessionLocal() as db:
        result = await validate_and_ensure_factor_analysis_data(db)
        print(f'Status: {result.get(\"status\")}')
        print(f'Sufficient data: {len(result.get(\"symbols_with_sufficient_data\", []))} symbols')

asyncio.run(validate())
"
```

#### **3. Batch Calculations** ⭐ **Main Operations Script**
```bash
# Run all 8 calculation engines (WITHOUT reports)
uv run python scripts/batch_processing/run_batch.py

# Run for specific portfolio (using deterministic IDs)
# Individual portfolio: 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe
uv run python scripts/batch_processing/run_batch.py --portfolio 1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe

# High Net Worth portfolio: e23ab931-a033-edfe-ed4f-9d02474780b4
uv run python scripts/batch_processing/run_batch.py --portfolio e23ab931-a033-edfe-ed4f-9d02474780b4

# Hedge Fund portfolio: fcd71196-e93e-f000-5a74-31a9eead3118
uv run python scripts/batch_processing/run_batch.py --portfolio fcd71196-e93e-f000-5a74-31a9eead3118
```

**What Batch Processing Does:**
1. Market data sync (fetches latest prices)
2. Portfolio aggregation (calculates totals)
3. Greeks calculation (options sensitivities)
4. Factor analysis (7-factor regression)
5. Market risk scenarios (±5%, ±10%, ±20%)
6. Stress testing (15 extreme scenarios)
7. Portfolio snapshots (daily state capture)
8. Correlations (position correlations)

#### **4. Health Checks & Monitoring**
```bash
# Check database content
uv run python scripts/database/check_database_content.py

# List portfolios with details
uv run python scripts/database/list_portfolios.py

# Monitor API provider usage
uv run python scripts/monitor_provider_usage.py

# Monitor chat interface
uv run python scripts/monitoring/monitor_chat_interface.py
```

#### **5. Verification & Validation**
```bash
# Verify demo portfolios
uv run python scripts/verification/verify_demo_portfolios.py

# Validate system configuration
uv run python scripts/verification/validate_setup.py

# Check equity values
uv run python scripts/verification/check_equity_values.py
```

---

## 📁 Directory Structure

```
scripts/
├── automation/          # Automated batch jobs and scheduling
│   ├── railway_daily_batch.py  ⭐ Railway daily batch job
│   └── trading_calendar.py     NYSE trading calendar utilities
│
├── batch_processing/     # Main calculation processing
│   └── run_batch.py  ⭐ MAIN - Run all calculations (local)
│
├── database/            # Database setup, seeding, migrations
│   ├── reset_and_seed.py          ⭐ Authoritative seeding
│   ├── seed_database.py           ⭐ Seed without reset
│   ├── setup_dev_database_alembic.py
│   ├── check_database_content.py  ⭐ Daily health check
│   ├── list_portfolios.py         ⭐ Portfolio reference
│   └── list_users.py
│
├── data_operations/      # Data fetching, backfilling, exports
│   ├── populate_target_prices_via_service.py
│   ├── populate_target_prices.py
│   ├── fetch_factor_etf_data.py
│   ├── backfill_factor_etfs.py
│   ├── backfill_position_symbols.py
│   ├── populate_company_profiles.py  # Populate company data
│   ├── sync_position_prices.py       # Sync market prices
│   └── list_symbols.py               # List all symbols
│
├── railway/             # Railway deployment-specific ⭐ NEW
│   ├── audit_railway_data.py         ⭐ Audit portfolio/position data via API
│   ├── audit_railway_market_data.py  ⭐ Audit market data (detailed per-position)
│   ├── railway_run_migration.py      ⭐ Run migrations on Railway
│   ├── verify_railway_migration.py   Verify migration status
│   ├── railway_reset_database.py     Reset and reseed (DESTRUCTIVE)
│   ├── railway_initial_seed.sh       Initial setup workflow
│   └── RAILWAY_SEEDING_README.md     Seeding documentation
│
├── verification/        # Validation and verification scripts
│   ├── validate_setup.py             ⭐ Comprehensive validation
│   ├── verify_setup.py
│   ├── verify_demo_portfolios.py     ⭐ Portfolio integrity
│   ├── verify_batch_results.py       ⭐ Verify batch calculation results
│   ├── verify_database_state.py      ⭐ Comprehensive database state
│   ├── verify_factor_data.py
│   ├── verify_migrations.py          ⭐ Verify Alembic migrations
│   ├── check_equity_values.py
│   └── check_portfolio.py
│
├── monitoring/          # System monitoring scripts
│   ├── monitor_chat_interface.py     ⭐ Chat health
│   ├── monitor_provider_usage.py     ⭐ Monitor API usage/limits
│   └── simple_monitor.py
│
├── manual_tests/        # Browser automation & manual testing
│   ├── test_chat_flow.js         (Puppeteer)
│   ├── monitoring_session.js     (Puppeteer)
│   ├── package.json
│   ├── package-lock.json
│   └── node_modules/
│
├── testing/             # Automated test scripts
├── analysis/            # Analysis and debugging tools
├── migrations/          # Active one-time fixes and migrations
├── utilities/           # General utility scripts
└── test_api_providers/  # API provider testing

Note: 38 completed/deprecated scripts archived to ../_archive/scripts/ (see _archive/scripts/README.md)
```

---

## 🎯 Most Common Workflows

### Initial Setup (First Time)
```bash
cd backend

# 1. Apply migrations
uv run alembic upgrade head

# 2. Seed demo data
uv run python scripts/database/seed_database.py

# 3. Validate setup
uv run python scripts/verification/validate_setup.py

# 4. Run initial batch processing
uv run python scripts/batch_processing/run_batch.py
```

### Daily Workflow
```bash
cd backend

# 1. Pull latest code and apply migrations
git pull
uv run alembic upgrade head

# 2. Check database health
uv run python scripts/database/check_database_content.py

# 3. Update market data (inline Python)
uv run python -c "
import asyncio
from app.batch.market_data_sync import sync_market_data
asyncio.run(sync_market_data())
"

# 4. Run batch calculations
uv run python scripts/batch_processing/run_batch.py

# 5. Verify results
uv run python scripts/verification/verify_demo_portfolios.py
```

### Railway Production Workflow
```bash
# === IN RAILWAY SSH ===
railway shell

# 1. Run migrations
uv run python scripts/railway/railway_run_migration.py

# 2. Verify migration
uv run python scripts/railway/verify_railway_migration.py

# 3. Reset and reseed (DESTRUCTIVE - only if needed)
uv run python scripts/railway/railway_reset_database.py

# 4. Run daily batch job (--force for non-trading days)
uv run python scripts/automation/railway_daily_batch.py --force

# 5. Verify batch results
uv run python scripts/verification/verify_batch_results.py

# 6. Check database state
uv run python scripts/verification/verify_database_state.py


# === FROM LOCAL MACHINE (API Audits) ===

# Audit portfolio and position data
python scripts/railway/audit_railway_data.py

# Audit market data (detailed per-position historical coverage)
python scripts/railway/audit_railway_market_data.py
```

### Client Onboarding (Future)
```bash
cd backend

# Scripts to be created for production client onboarding:
# - scripts/onboard_client.py      (account creation)
# - scripts/verify_client.py       (verification)
# - app/db/client_onboarding.py    (onboarding utilities)

# See: _guides/ONBOARDING_NEW_ACCOUNT_PORTFOLIO.md
```

---

## 📊 Script Categories

### Critical for Setup ✅
- `alembic upgrade head` (migrations)
- `database/reset_and_seed.py` or `database/seed_database.py`
- `verification/validate_setup.py`
- `batch_processing/run_batch.py` (initial)

### Critical for Operations ⚙️
- `alembic upgrade head` (after every git pull)
- Market data sync (inline Python commands)
- `batch_processing/run_batch.py` (daily)
- `database/check_database_content.py` (health check)

### Monitoring & Debugging 🔍
- `database/list_portfolios.py`
- `verification/verify_demo_portfolios.py`
- `monitoring/monitor_chat_interface.py`
- `monitor_provider_usage.py`

### Data Operations 📈
- `data_operations/populate_target_prices_via_service.py`
- `data_operations/fetch_factor_etf_data.py`
- `data_operations/backfill_factor_etfs.py`

### Testing 🧪
- `testing/test_auth.py`
- `testing/test_calculations.py`
- `testing/test_market_data.py`
- `manual_tests/test_chat_flow.js` (Puppeteer)
- `manual_tests/monitoring_session.js` (Puppeteer)

---

## 💡 Important Notes

### Database Migrations
- **ALWAYS** run `alembic upgrade head` after pulling code
- Recent critical migration: `add_equity_balance_to_portfolio`
- Without migrations, API endpoints will return 500 errors

### Railway Deployment ⭐ NEW
- All Railway scripts (`scripts/railway/`) include automatic DATABASE_URL conversion
- Converts `postgresql://` → `postgresql+asyncpg://` for async driver compatibility
- Audit scripts (`audit_railway_*.py`) run from **local machine** and hit Railway API
- No SSH needed for audits - just Python 3.11+ and `requests` library

### Market Data
- Private positions (real estate, private equity, collectibles) are automatically excluded
- Historical data is preserved (not overwritten)
- Coverage checked per-symbol with 80% threshold
- GICS fetching is optional (defaults to False for performance)

### Batch Processing
- Pre-API reports (.md, .json, .csv) are deprecated
- Always use `--skip-reports` flag
- UTF-8 encoding handled automatically (fixed as of 2025-09-11)
- First run takes 30-60 seconds per portfolio (fetches historical data)

### Demo Portfolios (Deterministic IDs)
- `demo_individual@sigmasight.com`: `1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe`
- `demo_hnw@sigmasight.com`: `e23ab931-a033-edfe-ed4f-9d02474780b4`
- `demo_hedgefundstyle@sigmasight.com`: `fcd71196-e93e-f000-5a74-31a9eead3118`
- Password for all: `demo12345`

---

## 🛠️ Usage Guidelines

1. **Always run scripts from the `backend` directory**
2. **Database must be running** (`docker-compose up -d`)
3. **Environment variables** must be set in `.env` file (FMP_API_KEY required)
4. **Use `uv run python`** to execute scripts with proper dependencies
5. **Check for existing data** before running reset commands (DESTRUCTIVE!)

---

## 🗄️ Archived Scripts

**38 completed/deprecated scripts** have been archived to `../_archive/scripts/`:
- **20 migration scripts** - Completed one-time data migrations and fixes
- **2 deprecated scripts** - `run_batch_calculations.py` and `run_batch_with_reports.py` (both replaced by `run_batch.py`)
- **14 test scripts** - Completed version-specific and one-time tests
- **3 debug scripts** - Completed debugging/analysis tasks

**See**: [`../_archive/scripts/README.md`](../_archive/scripts/README.md) for complete listing and restoration instructions.

**Last Archive**: 2025-10-04

---

## 📚 Additional Resources

- **Complete Workflow Guides**: [`_guides/`](../_guides/)
- **Archived Scripts**: [`../_archive/scripts/README.md`](../_archive/scripts/README.md)
- **Batch Processing Details**: [`batch_processing/README.md`](batch_processing/README.md)
- **Database Scripts**: [`database/README.md`](database/README.md)
- **Data Operations**: [`data_operations/README.md`](data_operations/README.md)
- **API Documentation**: http://localhost:8000/docs (when server running)
- **Code Reference**: [`../CLAUDE.md`](../CLAUDE.md)

---

## ❓ Troubleshooting

### "No portfolios found"
```bash
uv run python scripts/database/seed_database.py
uv run python scripts/database/list_portfolios.py
```

### "Migration not applied" errors
```bash
uv run alembic upgrade head
```

### "Market data fetch failed"
- Check `.env` has valid API keys (FMP_API_KEY, POLYGON_API_KEY, FRED_API_KEY)
- Verify API rate limits not exceeded

### "Import errors" or module not found
- Ensure using `uv run python` prefix
- This activates the virtual environment automatically

### "Greeks are all zero"
- Expected - no reliable options chain data available
- Greeks approximated using simplified Black-Scholes

---

**Remember**: The first batch run takes longer as it fetches historical data. Subsequent runs are much faster!
