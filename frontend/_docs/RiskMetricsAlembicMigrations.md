# Risk Metrics Alembic Migrations

**Purpose:** Database schema changes required for Risk Metrics overhaul (market beta, sector analysis, volatility analytics, AI insights)

**Total Migrations:** 11 migrations across 4 phases (October 17-19, 2025)

**Execution Order:** Must be run sequentially (Migration 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10)

**Last Updated:** October 19, 2025

**Status:**
- ✅ Phase 0 (Market Beta): COMPLETE (Migrations 0-1 applied October 17, 2025)
- ✅ Phase 1 (Sector Analysis): COMPLETE (Migrations 2-3 applied October 17, 2025)
- ✅ Phase 2 (Volatility Analytics): COMPLETE (Migrations 4-5 applied October 17, 2025)
- ✅ Phase 3 (Beta Refactoring): COMPLETE (Migration 6 applied October 18, 2025)
- ✅ Phase 4 (AI Insights): COMPLETE (Migrations 7-8 applied October 19, 2025)

---

## Quick Reference

| # | Migration ID | Purpose | Tables Modified | New Columns/Tables | Date Applied |
|---|--------------|---------|-----------------|-------------------|--------------|
| 0 | a1b2c3d4e5f6 | Position-level market betas | Creates `position_market_betas` | New table (11 columns) | Oct 17, 2025 |
| 1 | b2c3d4e5f6g7 | Portfolio-level market beta | `portfolio_snapshots` | 4 new columns | Oct 17, 2025 |
| 2 | 7818709e948d | Benchmark sector weights | Creates `benchmarks_sector_weights` | New table (10 columns) | Oct 17, 2025 |
| 3 | f67a98539656 | Sector & concentration | `portfolio_snapshots` | 5 new columns | Oct 17, 2025 |
| 4 | c1d2e3f4g5h6 | Portfolio volatility analytics | `portfolio_snapshots` | 5 new columns | Oct 17, 2025 |
| 5 | d2e3f4g5h6i7 | Position volatility | Creates `position_volatility` | New table (15 columns) | Oct 17, 2025 |
| 6 | e65741f182c4 | Refactor beta field names | `portfolio_snapshots` | 1 new column, 4 renamed | Oct 18, 2025 |
| 7 | f8g9h0i1j2k3 | AI insights infrastructure | Creates 2 new tables | `ai_insights`, `ai_insight_templates` | Oct 19, 2025 |
| 8 | 7003a3be89fe | Sector exposure refinement | `portfolio_snapshots` + updates | HHI precision change | Oct 19, 2025 |
| 9 | h1i2j3k4l5m6 | Add portfolio_id to IR betas | `position_interest_rate_betas` | 1 new column + index | Oct 19, 2025 |

**Migration Chain:**
```
a1b2c3d4e5f6 → b2c3d4e5f6g7 → 7818709e948d → f67a98539656 → c1d2e3f4g5h6 →
d2e3f4g5h6i7 → e65741f182c4 → f8g9h0i1j2k3 → 7003a3be89fe → h1i2j3k4l5m6 (HEAD)
```

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

**Note:** These fields were later renamed in Migration 6 (e65741f182c4)

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

**Note:** HHI precision was later updated from NUMERIC(10,2) to NUMERIC(10,4) in Migration 8 (7003a3be89fe)

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

---

## Phase 3: Beta Field Refactoring

### Migration 6: Refactor Portfolio Beta Field Names ✅

**Status:** COMPLETE (Applied October 18, 2025)

**File:** `backend/alembic/versions/e65741f182c4_refactor_portfolio_beta_field_names_and_.py`

**Revision ID:** `e65741f182c4`

**Command:**
```bash
uv run alembic upgrade head
```

**What it changes:**
- **Modifies table:** `portfolio_snapshots`
- **Purpose:** Rename beta fields for clarity and add provider beta field

**Field Renames** (portfolio_snapshots):
```
OLD NAME                    NEW NAME                            PURPOSE
market_beta_weighted    →   beta_calculated_90d                 Equity-weighted average of position betas (90-day OLS)
market_beta_r_squared   →   beta_calculated_90d_r_squared       Weighted average R-squared from position betas
market_beta_observations →  beta_calculated_90d_observations    Minimum observations across all positions
market_beta_direct      →   beta_portfolio_regression           Direct OLS regression (Phase 3 future work)
```

**New Column Added:**
```
beta_provider_1y        NUMERIC(10,4)   Provider-reported 1-year beta from company profile API
```

**Rationale:**
- Makes clear that `beta_calculated_90d` is derived from position-level regressions (bottom-up)
- Distinguishes from `beta_portfolio_regression` which will be direct portfolio-level regression (top-down)
- Adds `beta_provider_1y` for comparison with external data sources

---

## Phase 4: AI Insights Infrastructure

### Migration 7: Create AI Insights Tables ✅

**Status:** COMPLETE (Applied October 19, 2025)

**File:** `backend/alembic/versions/f8g9h0i1j2k3_add_ai_insights_tables.py`

**Revision ID:** `f8g9h0i1j2k3`

**Command:**
```bash
uv run alembic upgrade head
```

**What it creates:**
- **New tables:** `ai_insights` and `ai_insight_templates`
- **Purpose:** AI analytical reasoning layer infrastructure for portfolio analysis

**New Table 1: `ai_insights`**

Stores AI-generated portfolio analysis and investigations.

**Columns:**
```
id                      UUID            Primary key
portfolio_id            UUID            Foreign key to portfolios

-- Insight metadata
insight_type            ENUM            daily_summary, volatility_analysis, concentration_risk, etc.
title                   VARCHAR(200)    Insight title
severity                ENUM            info, normal, elevated, warning, critical

-- Content
summary                 TEXT            Brief summary of insight
full_analysis           TEXT            Detailed analysis
key_findings            JSON            Structured findings array
recommendations         JSON            Action recommendations array
data_limitations        TEXT            Known data quality issues

-- Investigation context
context_data            JSON            Snapshot data, positions, calculations used
data_quality            JSON            Completeness metrics per data type
focus_area              VARCHAR(100)    Specific area investigated
user_question           TEXT            Original user question (if custom insight)

-- AI model information
model_used              VARCHAR(50)     Model name (e.g., "claude-sonnet-4")
provider                VARCHAR(20)     AI provider (default: "anthropic")
prompt_version          VARCHAR(20)     Template version used

-- Performance metrics
cost_usd                NUMERIC(10,6)   API cost in USD
generation_time_ms      NUMERIC(10,2)   Generation time in milliseconds
token_count_input       NUMERIC(10,0)   Input tokens consumed
token_count_output      NUMERIC(10,0)   Output tokens consumed
tool_calls_count        NUMERIC(3,0)    Number of tool calls made

-- Caching
cache_hit               BOOLEAN         Whether this was served from cache
cache_source_id         UUID            Foreign key to ai_insights (original insight)
cache_key               VARCHAR(64)     Cache key for deduplication

-- User interaction
user_rating             NUMERIC(2,1)    User rating (0.0 to 5.0)
user_feedback           TEXT            User feedback text
viewed                  BOOLEAN         Whether user has viewed
dismissed               BOOLEAN         Whether user dismissed

-- Timestamps
created_at              TIMESTAMP       Creation timestamp
expires_at              TIMESTAMP       Expiration timestamp (optional)
updated_at              TIMESTAMP       Last update timestamp
```

**Indexes (ai_insights):**
- `ix_ai_insights_portfolio_id` (portfolio_id)
- `ix_ai_insights_insight_type` (insight_type)
- `ix_ai_insights_created_at` (created_at)
- `ix_ai_insights_cache_key` (cache_key)
- `ix_ai_insights_portfolio_created` (portfolio_id, created_at)
- `ix_ai_insights_type_severity` (insight_type, severity)
- `ix_ai_insights_cache_lookup` (cache_key, created_at)

---

**New Table 2: `ai_insight_templates`**

Stores versioned prompt templates for different insight types.

**Columns:**
```
id                      UUID            Primary key

-- Template metadata
insight_type            ENUM            Type of insight this template generates
name                    VARCHAR(100)    Template name
description             TEXT            Template description
version                 VARCHAR(20)     Template version (e.g., "v1.2")

-- Prompt templates
system_prompt           TEXT            System prompt for AI
investigation_prompt    TEXT            Investigation/task prompt

-- Configuration
model_preference        VARCHAR(50)     Preferred model for this template
max_tokens              NUMERIC(6,0)    Max tokens setting
temperature             NUMERIC(3,2)    Temperature setting (0.00 to 1.00)

-- Tools configuration
required_tools          JSON            Required tool names array
optional_tools          JSON            Optional tool names array

-- Quality metrics
active                  BOOLEAN         Whether template is currently active
avg_quality_score       NUMERIC(3,2)    Average user rating
usage_count             NUMERIC(10,0)   Number of times used

-- Timestamps
created_at              TIMESTAMP       Creation timestamp
updated_at              TIMESTAMP       Last update timestamp
deprecated_at           TIMESTAMP       Deprecation timestamp (null if active)
```

**Indexes (ai_insight_templates):**
- `ix_ai_templates_insight_type` (insight_type)
- `ix_ai_templates_type_active` (insight_type, active)
- `ix_ai_templates_version` (insight_type, version)

**ENUM Types Created:**
- `insight_type`: daily_summary, volatility_analysis, concentration_risk, hedge_quality, factor_exposure, stress_test_review, custom
- `insight_severity`: info, normal, elevated, warning, critical

---

### Migration 8: Sector Exposure & Concentration Refinement ✅

**Status:** COMPLETE (Applied October 19, 2025)

**File:** `backend/alembic/versions/7003a3be89fe_add_sector_exposure_and_concentration_.py`

**Revision ID:** `7003a3be89fe` (HEAD)

**Command:**
```bash
uv run alembic upgrade head
```

**What it changes:**
- **Modifies table:** `portfolio_snapshots` (refinement of Migration 3)
- **Updates:** All previous tables to clean up comments and constraints
- **Purpose:** Finalize schema after multiple phases of additions

**Key Changes:**

1. **HHI Precision Update** (portfolio_snapshots):
   - Changed `hhi` from NUMERIC(10,2) to NUMERIC(10,4)
   - Provides finer granularity for concentration measurements

2. **Index Cleanup** (portfolio_snapshots):
   - Removed `idx_snapshots_beta` (redundant after refactoring)
   - Removed `idx_snapshots_volatility` (will be recreated as needed)

3. **Foreign Key Constraint Updates**:
   - Updated all foreign keys to use proper naming conventions
   - Removed CASCADE deletes from position_market_betas and position_volatility

4. **Column Comment Cleanup**:
   - Removed inline comments from all tables (Alembic autogenerate artifact)
   - Comments preserved in model definitions instead

5. **Timestamp Consistency**:
   - Ensured all `created_at` and `updated_at` columns use proper timezone handling
   - Made timestamps non-nullable where appropriate

**Tables Affected:**
- `portfolio_snapshots` - HHI precision, index cleanup
- `position_market_betas` - Foreign key updates, timestamp fixes
- `position_volatility` - Foreign key updates, timestamp type consistency
- `benchmarks_sector_weights` - Timestamp nullability fixes
- `ai_insights` - Timestamp updates
- `ai_insight_templates` - Index rename (ix_ai_templates_insight_type → ix_ai_insight_templates_insight_type)

---

### Migration 9: Add Portfolio ID to Interest Rate Betas ✅

**Status:** COMPLETE (Applied October 19, 2025)

**File:** `backend/alembic/versions/h1i2j3k4l5m6_add_portfolio_id_to_interest_rate_betas.py`

**Revision ID:** `h1i2j3k4l5m6` (HEAD)

**Command:**
```bash
uv run alembic upgrade head
```

**What it changes:**
- **Modifies table:** `position_interest_rate_betas`
- **Purpose:** Add portfolio_id column for efficient deletion by portfolio and consistency with other calculation tables

**Migration Steps:**

1. **Add Column (nullable initially)**
   ```sql
   ALTER TABLE position_interest_rate_betas
   ADD COLUMN portfolio_id UUID;
   ```

2. **Backfill Data**
   ```sql
   UPDATE position_interest_rate_betas pirb
   SET portfolio_id = p.portfolio_id
   FROM positions p
   WHERE pirb.position_id = p.id;
   ```

3. **Make NOT NULL**
   ```sql
   ALTER TABLE position_interest_rate_betas
   ALTER COLUMN portfolio_id SET NOT NULL;
   ```

4. **Add Foreign Key**
   ```sql
   ALTER TABLE position_interest_rate_betas
   ADD CONSTRAINT fk_position_ir_betas_portfolio
   FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
   ON DELETE CASCADE;
   ```

5. **Create Index**
   ```sql
   CREATE INDEX idx_ir_betas_portfolio_date
   ON position_interest_rate_betas (portfolio_id, calculation_date);
   ```

**New Column:**
```
portfolio_id        UUID            Foreign key to portfolios, NOT NULL
```

**New Index:**
- `idx_ir_betas_portfolio_date` (portfolio_id, calculation_date)

**Rationale:**
- Enables efficient deletion of all IR beta records for a portfolio without joining through positions
- Maintains consistency with `position_market_betas` and `position_volatility` tables (which both have portfolio_id)
- Improves query performance for portfolio-level IR beta lookups
- Required for the `reset_and_reprocess.py` utility script to efficiently clean calculation results

**Before/After Comparison:**

| Feature | Before Migration | After Migration |
|---------|-----------------|-----------------|
| Portfolio deletion | Requires JOIN through positions table | Direct WHERE portfolio_id = X |
| Query efficiency | 2-table JOIN required | Single table query possible |
| Consistency | Inconsistent with market_betas/volatility | Consistent across all calculation tables |
| Index support | Only position_id indexed | Both position_id and portfolio_id indexed |

**Validation:**
```bash
# Check column added
uv run python -c "
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text('''
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'position_interest_rate_betas'
            AND column_name = 'portfolio_id'
        '''))
        for row in result:
            print(f'Column: {row[0]}, Type: {row[1]}, Nullable: {row[2]}')

asyncio.run(check())
"
```

**Note:** This migration uses a 3-step approach (add nullable → backfill → make NOT NULL) to safely add a required column to an existing table with data.

---

## Running All Migrations

### Step 1: Apply all migrations
```bash
cd backend

# Apply all migrations to HEAD
uv run alembic upgrade head

# Check current migration version
uv run alembic current

# View migration history
uv run alembic history --verbose
```

### Step 2: Seed benchmark data (one-time)
```bash
# Seed S&P 500 sector weights
uv run python scripts/seed_benchmark_weights.py
```

### Step 3: Verify database schema
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
                'position_volatility',
                'ai_insights',
                'ai_insight_templates'
            )
        '''))
        tables = [row[0] for row in result]
        print(f'New tables created: {len(tables)}/5')
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
# Roll back to before Phase 0
uv run alembic downgrade 19c513d3bf90  # Revision before a1b2c3d4e5f6
```

---

## Database Size Impact

**Estimated storage requirements:**

| Table | Rows (3 portfolios, 63 positions) | Storage | With 1 Year History |
|-------|----------------------------------|---------|---------------------|
| `position_market_betas` | ~63 per calc date | ~15 KB/day | ~5.5 MB/year |
| `benchmarks_sector_weights` | ~11 per date | ~2 KB/day | ~730 KB/year |
| `position_volatility` | ~63 per calc date | ~20 KB/day | ~7.3 MB/year |
| `ai_insights` | ~3-10 per day | ~10 KB/day | ~3.7 MB/year |
| `ai_insight_templates` | ~10 total | ~5 KB total | ~5 KB (static) |
| `portfolio_snapshots` (new columns) | ~3 per calc date | ~1 KB/day | ~365 KB/year |

**Total estimated increase:** ~17.7 MB per year for demo data (3 portfolios, 63 positions)

---

## Key Technical Notes

### ⚠️ Critical Design Decisions

1. **Trading Day Windows:** All volatility uses trading days (21d, 63d) instead of calendar days (30d, 60d, 90d)

2. **Portfolio Volatility Calculation:** MUST compute from portfolio returns, NOT equity-weighted position volatilities
   - **Wrong:** `portfolio_vol = Σ(position_vol[i] * weight[i])`  ← Ignores correlations
   - **Correct:** Compute portfolio returns first, then calculate volatility ← Captures correlations

3. **Historical Tracking:** `position_market_betas`, `benchmarks_sector_weights`, `position_volatility`, and `ai_insights` preserve history via date columns

4. **Benchmark Data Source:** S&P 500 sector weights from FMP API (requires `FMP_API_KEY` in `.env`)

5. **Beta Naming Convention:**
   - `beta_calculated_90d`: Bottom-up (equity-weighted average of position betas)
   - `beta_portfolio_regression`: Top-down (direct portfolio-level regression, future Phase 3)
   - `beta_provider_1y`: External data source (company profile API)

6. **AI Insights Caching:** Uses `cache_key` and `cache_source_id` for deduplication and cost optimization

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
ANTHROPIC_API_KEY=your_anthropic_key  # Required for AI insights
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

### Check current migration status
```bash
# Show current HEAD
uv run alembic current

# Show full history
uv run alembic history --verbose

# Show pending migrations
uv run alembic heads
```

---

## Related Documentation

- **Execution Plan:** `frontend/_docs/RiskMetricsExecution.md`
- **Planning Document:** `frontend/_docs/RiskMetricsPlanning.md`
- **AI Insights Guide:** `backend/AI_AGENT_REFERENCE.md`
- **Backend CLAUDE.md:** `backend/CLAUDE.md` (Risk Metrics context)

---

## Migration Timeline

```
October 17, 2025 (Phase 0: Market Beta)
├── a1b2c3d4e5f6 - Create position_market_betas table
└── b2c3d4e5f6g7 - Add market beta to snapshots

October 17, 2025 (Phase 1: Sector Analysis)
├── 7818709e948d - Create benchmarks_sector_weights table
└── f67a98539656 - Add sector concentration to snapshots

October 17, 2025 (Phase 2: Volatility)
├── c1d2e3f4g5h6 - Add volatility to snapshots
└── d2e3f4g5h6i7 - Create position_volatility table

October 18, 2025 (Phase 3: Refactoring)
└── e65741f182c4 - Refactor portfolio beta field names

October 19, 2025 (Phase 4: AI & Refinements)
├── f8g9h0i1j2k3 - Add AI insights infrastructure
├── 7003a3be89fe - Add sector exposure & concentration
└── h1i2j3k4l5m6 - Add portfolio_id to interest rate betas (HEAD)
```

---

**Last Updated:** October 19, 2025
**Status:** All Risk Metrics & AI Insights Migrations Complete (11/11 migrations applied)

**Summary:**
- ✅ Phase 0: Market Beta (Oct 17) - 2 migrations
- ✅ Phase 1: Sector Analysis (Oct 17) - 2 migrations
- ✅ Phase 2: Volatility Analytics (Oct 17) - 2 migrations
- ✅ Phase 3: Beta Refactoring (Oct 18) - 1 migration
- ✅ Phase 4: AI Insights & Schema Updates (Oct 19) - 4 migrations

**New Tables Created:** 5
- position_market_betas (Phase 0)
- benchmarks_sector_weights (Phase 1)
- position_volatility (Phase 2)
- ai_insights (Phase 4)
- ai_insight_templates (Phase 4)

**Portfolio Snapshots Enhancements:**
- 4 market beta columns (renamed in Phase 3)
- 5 sector/concentration columns (refined in Phase 4)
- 5 volatility analytics columns
- 1 provider beta column (Phase 3)
- **Total:** 15 new columns in portfolio_snapshots

**Database Ready For:**
- Market beta calculations (position-level and portfolio-level)
- Interest rate beta calculations (TLT-based sensitivity)
- Sector exposure and concentration analysis
- Volatility analytics with HAR forecasting
- AI-powered portfolio insights and investigations
- Efficient calculation cleanup and reprocessing
- Multi-phase risk metrics dashboard
