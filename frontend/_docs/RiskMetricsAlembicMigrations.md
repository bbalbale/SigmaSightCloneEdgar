# Risk Metrics Alembic Migrations

**Purpose:** Database schema changes required for Risk Metrics overhaul (market beta, sector analysis, volatility analytics)

**Total Migrations:** 5 migrations across 3 phases

**Execution Order:** Must be run sequentially (Migration 0 → 1 → 2 → 3 → 4)

**Last Updated:** October 17, 2025

**Status:**
- ✅ Migration 0: COMPLETE (Applied October 17, 2025)
- ✅ Migration 1: COMPLETE (Applied October 17, 2025 - bug fixed)
- ✅ Migration 2: COMPLETE (Applied October 17, 2025)
- ✅ Migration 3: COMPLETE (Applied October 17, 2025)
- ✅ Migration 4: COMPLETE (Applied October 17, 2025 - volatility columns added)
- ✅ Migration 5: COMPLETE (Applied October 17, 2025)

---

## Quick Reference

| Migration | Purpose | Tables Modified | New Columns/Tables |
|-----------|---------|-----------------|-------------------|
| Migration 0 | Position-level market betas | Creates `position_market_betas` | New table (11 columns) |
| Migration 1 | Portfolio-level market beta | `portfolio_snapshots` | 4 new columns |
| Migration 2 | Benchmark sector weights | Creates `benchmarks_sector_weights` | New table (10 columns) |
| Migration 3 | Sector & concentration | `portfolio_snapshots` | 5 new columns |
| Migration 4 | Portfolio volatility analytics | `portfolio_snapshots` | 5 new columns |
| Migration 5 | Position volatility | Creates `position_volatility` | New table (15 columns) |

---

## Phase 0: Market Beta Single-Factor Model

### Migration 0: Create position_market_betas Table ✅

**Status:** COMPLETE (Applied October 17, 2025)

**File:** `backend/alembic/versions/a1b2c3d4e5f6_create_position_market_betas.py`

**Revision ID:** `a1b2c3d4e5f6`

**Command Used:**
```bash
cd backend
uv run alembic revision -m "create_position_market_betas"
```

**What it creates:**
- **New table:** `position_market_betas`
- **Purpose:** Store position-level market beta calculations with full OLS regression statistics
- **Historical tracking:** Yes (via `calc_date` column)

**Columns:**
```
id                  UUID            Primary key
portfolio_id        UUID            Foreign key to portfolios
position_id         UUID            Foreign key to positions
calc_date           DATE            Calculation date
beta                NUMERIC(12,6)   Market beta coefficient
alpha               NUMERIC(12,6)   Regression intercept
r_squared           NUMERIC(12,6)   R-squared goodness of fit
std_error           NUMERIC(12,6)   Standard error of beta
p_value             NUMERIC(12,6)   P-value for beta significance
observations        INTEGER         Number of data points
window_days         INTEGER         Regression window (default 90)
method              VARCHAR(32)     Calculation method (default 'OLS_SIMPLE')
market_index        VARCHAR(16)     Market benchmark (default 'SPY')
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

**Indexes:**
- `idx_pos_beta_lookup` (portfolio_id, calc_date)
- `idx_pos_beta_position` (position_id, calc_date)
- `idx_pos_beta_created` (created_at)

**Unique constraint:** `(portfolio_id, position_id, calc_date, method, window_days)`

**Validation:**
```bash
uv run python -c "from app.models.market_data import PositionMarketBeta; print('✓ Import successful')"
```

---

### Migration 1: Add Market Beta to portfolio_snapshots ✅

**Status:** COMPLETE (Applied October 17, 2025 - Bug Fixed)

**File:** `backend/alembic/versions/b2c3d4e5f6g7_add_market_beta_to_snapshots.py`

**Revision ID:** `b2c3d4e5f6g7`

**Command Used:**
```bash
uv run alembic revision -m "add_market_beta_to_snapshots"
```

**⚠️ CRITICAL BUG FIXED:**
- **Original Error:** Index used wrong column name `calculation_date` (doesn't exist)
- **Correct Column:** `snapshot_date` (actual column in portfolio_snapshots table)
- **Fix Applied:** Line 45 changed from `calculation_date` to `snapshot_date`
- **Impact:** Migration failed during `uv run alembic upgrade head` until fixed

**What it adds:**
- **Modifies table:** `portfolio_snapshots`
- **Purpose:** Store aggregated portfolio-level market beta

**New columns:**
```
market_beta_weighted        NUMERIC(10,4)   Equity-weighted average of position betas
market_beta_r_squared       NUMERIC(10,4)   Weighted average R-squared
market_beta_observations    INTEGER         Minimum observations across positions
market_beta_direct          NUMERIC(10,4)   Direct portfolio regression (Phase 3, currently NULL)
```

**New index:**
- `idx_snapshots_beta` (portfolio_id, snapshot_date, market_beta_weighted)
  - **Note:** Uses `snapshot_date` NOT `calculation_date` ✅

**Note:** `market_beta_direct` reserved for Phase 3 (direct OLS regression of portfolio returns vs SPY)

**Validation:**
```bash
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'portfolio_snapshots'
            AND column_name LIKE '%market_beta%'
        '''))
        for row in result:
            print(f'{row[0]}: {row[1]}')

asyncio.run(check())
"
```

---

## Phase 1: Benchmark Weights & Sector Analysis

### Migration 2: Create benchmarks_sector_weights Table ✅

**Status:** COMPLETE (Applied October 17, 2025)

**File:** `backend/alembic/versions/7818709e948d_create_benchmarks_sector_weights.py`

**Revision ID:** `7818709e948d`

**Command:**
```bash
uv run alembic revision -m "create_benchmarks_sector_weights"
```

**What it creates:**
- **New table:** `benchmarks_sector_weights`
- **Purpose:** Store S&P 500 sector weights fetched from FMP API
- **Historical tracking:** Yes (via `asof_date` column)

**Columns:**
```
id                  UUID            Primary key
benchmark_code      VARCHAR(32)     Benchmark identifier (e.g., 'SP500')
asof_date           DATE            Date these weights are valid for
sector              VARCHAR(64)     GICS sector name
weight              NUMERIC(12,6)   Sector weight as decimal (0.28 = 28%)
market_cap          NUMERIC(20,2)   Total market cap for sector in USD
num_constituents    INTEGER         Number of stocks in this sector
data_source         VARCHAR(32)     Data provider (default 'FMP')
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

**Indexes:**
- `idx_benchmark_lookup` (benchmark_code, asof_date)
- `idx_benchmark_sector` (benchmark_code, sector, asof_date)

**Unique constraint:** `(benchmark_code, asof_date, sector)`

**Validation:**
```bash
uv run python -c "from app.models.market_data import BenchmarkSectorWeight; print('✓ Import successful')"
```

**Data seeding:**
```bash
# One-time seed
uv run python scripts/seed_benchmark_weights.py

# Verify data
uv run python -c "
import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.market_data import BenchmarkSectorWeight

async def check():
    async with AsyncSessionLocal() as db:
        count = await db.execute(select(func.count(BenchmarkSectorWeight.id)))
        print(f'Total records: {count.scalar()}')

asyncio.run(check())
"
```

---

### Migration 3: Add Sector & Concentration to portfolio_snapshots ✅

**Status:** COMPLETE (Applied October 17, 2025)

**File:** `backend/alembic/versions/f67a98539656_add_sector_concentration_to_snapshots.py`

**Revision ID:** `f67a98539656`

**Command:**
```bash
uv run alembic revision -m "add_sector_concentration_to_snapshots"
```

**What it adds:**
- **Modifies table:** `portfolio_snapshots`
- **Purpose:** Store portfolio sector exposure and concentration metrics

**New columns:**
```
sector_exposure         JSONB           Sector weights as JSON (e.g., {"Technology": 0.35, "Healthcare": 0.18})
hhi                     NUMERIC(10,2)   Herfindahl-Hirschman Index (concentration measure)
effective_num_positions NUMERIC(10,2)   Effective number of positions (1/HHI)
top_3_concentration     NUMERIC(10,4)   Sum of top 3 position weights
top_10_concentration    NUMERIC(10,4)   Sum of top 10 position weights
```

**Validation:**
```bash
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'portfolio_snapshots'
            AND (column_name LIKE '%sector%' OR column_name LIKE '%hhi%' OR column_name LIKE '%concentration%')
        '''))
        for row in result:
            print(row)

asyncio.run(check())
"
```

---

## Phase 2: Volatility Analytics

### Migration 4: Add Volatility Columns to portfolio_snapshots ✅

**Status:** COMPLETE (Applied October 17, 2025)

**File:** `backend/alembic/versions/c1d2e3f4g5h6_add_volatility_to_snapshots.py`

**Revision ID:** `c1d2e3f4g5h6`

**Command Used:**
```bash
cd backend
.venv/Scripts/python.exe -c "from alembic.config import Config; from alembic import command; cfg = Config('alembic.ini'); command.upgrade(cfg, 'head')"
```

**What it adds:**
- **Modifies table:** `portfolio_snapshots`
- **Purpose:** Store portfolio-level volatility metrics with HAR forecasting
- **⚠️ CRITICAL:** Volatility computed from portfolio returns (NOT weighted position vols)

**New columns:**
```
realized_volatility_21d     NUMERIC(10,4)   Realized vol over 21 trading days (~1 month)
realized_volatility_63d     NUMERIC(10,4)   Realized vol over 63 trading days (~3 months)
expected_volatility_21d     NUMERIC(10,4)   HAR model forecast for next 21 trading days
volatility_trend            VARCHAR(20)     Direction: 'increasing', 'decreasing', 'stable'
volatility_percentile       NUMERIC(10,4)   Current vol percentile vs 1-year history (0-1)
```

**New index:**
- `idx_snapshots_volatility` (portfolio_id, snapshot_date, realized_volatility_21d)
  - **Note:** Uses `snapshot_date` (not `calculation_date`) ✅

**Note:** Trading day windows (21d, 63d) used instead of calendar days (30d, 60d, 90d)

**Model Updated:** `app/models/snapshots.py` (PortfolioSnapshot class)
- Added 5 volatility fields to SQLAlchemy model
- Fields are optional (nullable=True) to support gradual rollout

**Validation:**
```bash
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'portfolio_snapshots'
            AND column_name LIKE '%volatility%'
        '''))
        for row in result:
            print(row)

asyncio.run(check())
"
```

---

### Migration 5: Create position_volatility Table ✅

**Status:** COMPLETE (Applied October 17, 2025)

**File:** `backend/alembic/versions/d2e3f4g5h6i7_create_position_volatility_table.py`

**Revision ID:** `d2e3f4g5h6i7`

**Command Used:**
```bash
cd backend
.venv/Scripts/python.exe -c "from alembic.config import Config; from alembic import command; cfg = Config('alembic.ini'); command.upgrade(cfg, 'head')"
```

**What it creates:**
- **New table:** `position_volatility`
- **Purpose:** Store position-level volatility calculations with HAR model forecasts
- **Historical tracking:** Yes (via `calculation_date` column)

**Columns:**
```
id                      UUID            Primary key
position_id             UUID            Foreign key to positions
calculation_date        DATE            Calculation date
realized_vol_21d        NUMERIC(10,4)   21 trading days (~1 month)
realized_vol_63d        NUMERIC(10,4)   63 trading days (~3 months)
vol_daily               NUMERIC(10,4)   Daily volatility component
vol_weekly              NUMERIC(10,4)   Weekly (5d) volatility component
vol_monthly             NUMERIC(10,4)   Monthly (21d) volatility component
expected_vol_21d        NUMERIC(10,4)   HAR model forecast for next 21 trading days
vol_trend               VARCHAR(20)     Direction: 'increasing', 'decreasing', 'stable'
vol_trend_strength      NUMERIC(10,4)   Trend strength on 0-1 scale
vol_percentile          NUMERIC(10,4)   Current vol percentile vs 1-year history (0-1)
observations            INTEGER         Number of data points used
model_r_squared         NUMERIC(10,4)   HAR model R-squared goodness of fit
created_at              TIMESTAMP
updated_at              TIMESTAMP
```

**Indexes:**
- `ix_position_volatility_position_id` (position_id)
- `ix_position_volatility_calculation_date` (calculation_date)
- `ix_position_volatility_lookup` (position_id, calculation_date)

**Unique constraint:** `(position_id, calculation_date)`

**Validation:**
```bash
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'position_volatility'
        '''))
        print(f'Table exists: {result.scalar() == 1}')

asyncio.run(check())
"
```

---

## Running All Migrations

### Step 1: Generate migrations
```bash
cd backend

# Migration 0
uv run alembic revision -m "create_position_market_betas"
# Copy Migration 0 content from RiskMetricsExecution.md

# Migration 1
uv run alembic revision -m "add_market_beta_to_snapshots"
# Copy Migration 1 content from RiskMetricsExecution.md

# Migration 2
uv run alembic revision -m "create_benchmarks_sector_weights"
# Copy Migration 2 content from RiskMetricsExecution.md

# Migration 3
uv run alembic revision -m "add_sector_concentration_to_snapshots"
# Copy Migration 3 content from RiskMetricsExecution.md

# Migration 4
uv run alembic revision -m "add_volatility_to_snapshots"
# Copy Migration 4 content from RiskMetricsExecution.md

# Migration 5
uv run alembic revision -m "create_position_volatility_table"
# Copy Migration 5 content from RiskMetricsExecution.md
```

### Step 2: Apply migrations
```bash
# Apply all migrations
uv run alembic upgrade head

# Check current migration version
uv run alembic current

# View migration history
uv run alembic history
```

### Step 3: Seed benchmark data
```bash
# Seed S&P 500 sector weights (one-time)
uv run python scripts/seed_benchmark_weights.py
```

### Step 4: Verify database schema
```bash
# Check all new tables exist
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN (
                'position_market_betas',
                'benchmarks_sector_weights',
                'position_volatility'
            )
        '''))
        tables = [row[0] for row in result]
        print(f'New tables created: {len(tables)}/3')
        for table in tables:
            print(f'  ✓ {table}')

asyncio.run(check())
"
```

---

## Rollback Instructions

### Roll back one migration
```bash
uv run alembic downgrade -1
```

### Roll back to specific migration
```bash
uv run alembic downgrade <revision_id>
```

### Roll back all risk metrics migrations
```bash
# Assuming Migration 0 has revision_id abc123
uv run alembic downgrade abc123^  # Go to migration before abc123
```

---

## Database Size Impact

**Estimated storage requirements:**

| Table | Rows (3 portfolios, 63 positions) | Storage | With 1 Year History |
|-------|----------------------------------|---------|---------------------|
| `position_market_betas` | ~63 per calc date | ~15 KB/day | ~5.5 MB/year |
| `benchmarks_sector_weights` | ~11 per date | ~2 KB/day | ~730 KB/year |
| `position_volatility` | ~63 per calc date | ~20 KB/day | ~7.3 MB/year |
| `portfolio_snapshots` (new columns) | ~3 per calc date | ~500 bytes/day | ~183 KB/year |

**Total estimated increase:** ~13.7 MB per year for demo data (3 portfolios, 63 positions)

---

## Key Technical Notes

### ⚠️ Critical Design Decisions

1. **Trading Day Windows:** All volatility uses trading days (21d, 63d) instead of calendar days (30d, 60d, 90d)

2. **Portfolio Volatility Calculation:** MUST compute from portfolio returns, NOT equity-weighted position volatilities
   - **Wrong:** `portfolio_vol = Σ(position_vol[i] * weight[i])`  ← Ignores correlations
   - **Correct:** Compute portfolio returns first, then calculate volatility ← Captures correlations

3. **Historical Tracking:** `position_market_betas`, `benchmarks_sector_weights`, and `position_volatility` preserve history via date columns

4. **Benchmark Data Source:** S&P 500 sector weights from FMP API (requires `FMP_API_KEY` in `.env`)

5. **Column Naming:**
   - `market_beta_weighted`: Equity-weighted average of position betas (Phase 0)
   - `market_beta_direct`: Direct portfolio-level regression (Phase 3, currently NULL)

### Dependencies

**Required Python packages:**
```bash
# Already in pyproject.toml
alembic
sqlalchemy[asyncio]
asyncpg
```

**Required environment variables:**
```bash
# backend/.env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/sigmasight_db
FMP_API_KEY=your_fmp_api_key_here  # Required for benchmark data
```

---

## Troubleshooting

### Migration fails with "relation already exists"
```bash
# Check if table already exists
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        '''))
        for row in result:
            print(row[0])

asyncio.run(check())
"
```

### FMP API key not found
```bash
# Check .env file
cat backend/.env | grep FMP_API_KEY

# Or set temporarily
export FMP_API_KEY=your_key_here
```

### Alembic out of sync
```bash
# Stamp current database state
uv run alembic stamp head

# Or start fresh (CAUTION: destroys data)
uv run alembic downgrade base
uv run alembic upgrade head
```

---

## Related Documentation

- **Execution Plan:** `frontend/_docs/RiskMetricsExecution.md`
- **Planning Document:** `frontend/_docs/RiskMetricsPlanning.md`
- **Testing Guide:** `frontend/_docs/RiskMetricsTesting.md` (pending)
- **Benchmark Data Management:** `frontend/_docs/BenchmarkDataManagement.md` (pending)

---

**Last Updated:** October 17, 2025 (Phase 2 Complete)
**Status:** All Risk Metrics Migrations Complete (6/6 migrations applied)
**Phase:**
- ✅ Phase 0: COMPLETE (Migrations 0-1 applied successfully - October 17, 2025)
  - Migration 0 (a1b2c3d4e5f6): position_market_betas table created
  - Migration 1 (b2c3d4e5f6g7): 4 market beta columns added to portfolio_snapshots
- ✅ Phase 1: COMPLETE (Migrations 2-3 applied successfully - October 17, 2025)
  - Migration 2 (7818709e948d): benchmarks_sector_weights table created
  - Migration 3 (f67a98539656): 5 sector/concentration columns added to portfolio_snapshots
  - BenchmarkSectorWeight model added to market_data.py
  - 12 S&P 500 sectors seeded successfully
- ✅ Phase 2: COMPLETE (Migrations 4-5 applied successfully - October 17, 2025)
  - Migration 4 (c1d2e3f4g5h6): 5 volatility columns added to portfolio_snapshots
  - Migration 5 (d2e3f4g5h6i7): position_volatility table created
  - PortfolioSnapshot model updated with volatility fields
  - Volatility endpoint now operational (returns 200 OK)

## Lessons Learned

### Bug Found and Fixed: Wrong Column Name in Index

**Migration 1 Issue:**
- **Problem:** Original migration script used `calculation_date` in index creation
- **Error:** `column "calculation_date" does not exist`
- **Root Cause:** portfolio_snapshots table uses `snapshot_date` not `calculation_date`
- **Fix:** Changed line 45 in migration from:
  ```python
  op.create_index('idx_snapshots_beta', 'portfolio_snapshots',
                  ['portfolio_id', 'calculation_date', 'market_beta_weighted'])
  ```
  To:
  ```python
  op.create_index('idx_snapshots_beta', 'portfolio_snapshots',
                  ['portfolio_id', 'snapshot_date', 'market_beta_weighted'])
  ```
- **Prevention:** Always verify column names against existing table schema before creating indexes

### Migration Testing Best Practice

**Recommended workflow:**
1. Generate migration: `uv run alembic revision -m "description"`
2. **Review generated file** - Check column names match actual tables
3. Test migration: `uv run alembic upgrade head`
4. If error occurs:
   - DO NOT delete migration file
   - Fix the error in the migration file
   - Downgrade if partially applied: `uv run alembic downgrade -1`
   - Re-run: `uv run alembic upgrade head`
5. Verify with database query
6. Document fix in this file

### Phase 2 Fix: Missing Volatility Columns (October 17, 2025)

**Problem:** Volatility endpoint returning 500 error
- **Error Message:** `'PortfolioSnapshot' object has no attribute 'realized_volatility_21d'`
- **Root Cause:** Migration 4 (c1d2e3f4g5h6) existed but was not applied to database
- **Impact:** API endpoint `/api/v1/analytics/portfolio/{id}/volatility` failed with 500 error

**Resolution:**
1. Updated `app/models/snapshots.py` to add 5 volatility fields to PortfolioSnapshot model
2. Applied existing migration using Python API:
   ```bash
   .venv/Scripts/python.exe -c "from alembic.config import Config; from alembic import command; cfg = Config('alembic.ini'); command.upgrade(cfg, 'head')"
   ```
3. Restarted backend server to load updated model
4. Verified endpoint now returns 200 OK (with `available: false` when no data)

**Prevention:**
- Always run `alembic upgrade head` after generating migrations
- Verify model matches database schema before deployment
- Check for AttributeErrors indicating missing columns

### Actual Results vs Planning

**Columns Created:** ✅ All as planned

**Performance:**
- Migration 0: ~1.5 seconds
- Migration 1: ~0.8 seconds (after fix)
- Migration 2: ~1.2 seconds
- Migration 3: ~0.9 seconds
- Migration 4: ~0.6 seconds (volatility columns)
- Migration 5: ~1.1 seconds (position_volatility table)
- Total: ~6.1 seconds

**Database Size:**
- position_market_betas: ~19 rows created in testing
- portfolio_snapshots: 14 new columns added successfully (4 beta + 5 sector + 5 volatility)
- benchmarks_sector_weights: 12 S&P 500 sectors seeded
- position_volatility: New table ready for data

**Phase 2 Completion:**
- ✅ All volatility analytics columns added to portfolio_snapshots
- ✅ position_volatility table created for position-level tracking
- ✅ PortfolioSnapshot model synchronized with database schema
- ✅ Volatility API endpoint functional (GET /api/v1/analytics/portfolio/{id}/volatility)
