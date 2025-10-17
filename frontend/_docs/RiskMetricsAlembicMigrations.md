# Risk Metrics Alembic Migrations

**Purpose:** Database schema changes required for Risk Metrics overhaul (market beta, sector analysis, volatility analytics)

**Total Migrations:** 5 migrations across 3 phases

**Execution Order:** Must be run sequentially (Migration 0 → 1 → 2 → 3 → 4)

---

## Quick Reference

| Migration | Purpose | Tables Modified | New Columns/Tables |
|-----------|---------|-----------------|-------------------|
| Migration 0 | Position-level market betas | Creates `position_market_betas` | New table (11 columns) |
| Migration 1 | Portfolio-level market beta | `portfolio_snapshots` | 4 new columns |
| Migration 2 | Benchmark sector weights | Creates `benchmarks_sector_weights` | New table (10 columns) |
| Migration 3 | Sector & concentration | `portfolio_snapshots` | 5 new columns |
| Migration 4 | Position volatility | Creates `position_volatility` | New table (15 columns) |

---

## Phase 0: Market Beta Single-Factor Model

### Migration 0: Create position_market_betas Table

**File:** `backend/alembic/versions/XXXX_create_position_market_betas.py`

**Command:**
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

### Migration 1: Add Market Beta to portfolio_snapshots

**File:** `backend/alembic/versions/XXXX_add_market_beta_to_snapshots.py`

**Command:**
```bash
uv run alembic revision -m "add_market_beta_to_snapshots"
```

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
- `idx_snapshots_beta` (portfolio_id, calculation_date, market_beta_weighted)

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

### Migration 2: Create benchmarks_sector_weights Table

**File:** `backend/alembic/versions/XXXX_create_benchmarks_sector_weights.py`

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

### Migration 3: Add Sector & Concentration to portfolio_snapshots

**File:** `backend/alembic/versions/XXXX_add_sector_concentration_to_snapshots.py`

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

### Migration 4: Add Volatility Columns to portfolio_snapshots

**File:** `backend/alembic/versions/XXXX_add_volatility_to_snapshots.py`

**Command:**
```bash
uv run alembic revision -m "add_volatility_to_snapshots"
```

**What it adds:**
- **Modifies table:** `portfolio_snapshots`
- **Purpose:** Store portfolio-level volatility metrics
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
- `idx_snapshots_volatility` (portfolio_id, calculation_date, realized_volatility_21d)

**Note:** Trading day windows (21d, 63d) used instead of calendar days (30d, 60d, 90d)

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

### Migration 5: Create position_volatility Table

**File:** `backend/alembic/versions/XXXX_create_position_volatility_table.py`

**Command:**
```bash
uv run alembic revision -m "create_position_volatility_table"
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

**Last Updated:** 2025-10-17
**Status:** Ready for implementation
**Phase:** 0-2 (Market Beta, Sector Analysis, Volatility)
