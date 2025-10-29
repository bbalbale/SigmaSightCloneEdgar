# Historical Ridge Regression Recalculation

## Problem Fixed

Ridge regression was storing betas in **standardized units** instead of raw return units, causing values to be **100-200x too small**. The dashboard displayed all factors as "0.00" because values like 0.003172 formatted to "0.00".

## Root Cause

In `factors_ridge.py` line 249, betas were extracted from a ridge model trained on standardized features (StandardScaler), but weren't transformed back to original scale.

## Fix Applied

Added 4 lines to `factors_ridge.py` after line 249:

```python
# Transform betas back to original scale
# Ridge was fit on standardized features, so betas are in standard deviation units
# We need to convert back to raw return units for interpretability
betas = betas / scaler.scale_
```

This converts betas from standardized units (SD) to raw return units, fixing the 100-200x scaling issue.

## Historical Data Affected

**Before fix** (Sept 30 - Oct 21):
- `FactorExposure`: Portfolio-level betas with incorrect scaling (100-200x too small)
- `PositionFactorExposure`: Missing position-level betas for ridge factors

**After fix** (Oct 22 - present):
- Both tables now have correctly scaled data

## Recalculation Scripts

### 1. `recalculate_historical_ridge.py`
Main recalculation script with full logging and control options.

**Usage:**
```bash
# Dry run (test without committing)
cd backend
uv run python scripts/recalculate_historical_ridge.py --dry-run

# Process limited dates for testing
uv run python scripts/recalculate_historical_ridge.py --max-dates 3

# Full recalculation (all historical dates)
uv run python scripts/recalculate_historical_ridge.py

# Include today's date (already corrected by default)
uv run python scripts/recalculate_historical_ridge.py --include-today
```

**Features:**
- Processes all portfolios automatically
- Skips today's date (already corrected)
- Shows detailed progress per portfolio/date
- Reports success/failure statistics
- Dry-run mode for testing

### 2. `run_historical_recalc.py`
Simple wrapper with cleaner output (suppresses SQL logs).

**Usage:**
```bash
cd backend
uv run python scripts/run_historical_recalc.py
```

### 3. `check_historical_ridge_data.py`
Diagnostic script to inspect historical data.

**Usage:**
```bash
cd backend
uv run python scripts/check_historical_ridge_data.py
```

Shows:
- Date ranges for portfolio-level exposures
- Date ranges for position-level exposures
- Number of historical records per portfolio

## What Gets Updated

### Position-Level (`PositionFactorExposure` table)
- Creates missing position-level betas for ridge factors:
  - Momentum
  - Value
  - Growth
  - Quality
  - Size
  - Low Volatility

### Portfolio-Level (`FactorExposure` table)
- Updates existing portfolio-level betas with correct scaling
- Preserves `exposure_dollar` calculations

## Expected Results

**Before recalculation:**
```
Momentum: 0.004197 → Dashboard shows "0.00"
Growth: 0.009613 → Dashboard shows "0.00"
Value: 0.000256 → Dashboard shows "0.00"
```

**After recalculation:**
```
Momentum: -0.098253 → Dashboard shows "-0.10"
Growth: 1.410432 → Dashboard shows "1.41"
Value: 0.545211 → Dashboard shows "0.55"
```

## Data Integrity

- ✅ Calculation method unchanged (same ridge regression algorithm)
- ✅ Only scaling fix applied (divide by scaler.scale_)
- ✅ All position relationships preserved
- ✅ Calculation dates preserved
- ✅ Quality flags preserved
- ✅ Spread factors untouched (already correct)

## Portfolio Snapshots

**Note:** Portfolio snapshots do NOT store ridge factor data. Factor data is stored in:
- `FactorExposure` (portfolio-level)
- `PositionFactorExposure` (position-level)

Snapshots only contain aggregated metrics like:
- Beta calculations (market beta)
- Greeks
- P&L metrics
- Sector exposure

## Verification

After running recalculation, verify results:

```bash
# Check a specific date
cd backend
uv run python -c "
import asyncio
from datetime import date
from sqlalchemy import select
from app.database import get_async_session
from app.models.market_data import FactorExposure, FactorDefinition
from app.models.users import Portfolio

async def check():
    async with get_async_session() as db:
        # Get first portfolio
        port = (await db.execute(select(Portfolio).limit(1))).scalar_one()

        # Get Growth factor for Sept 30
        result = await db.execute(
            select(FactorExposure, FactorDefinition)
            .join(FactorDefinition)
            .where(FactorExposure.portfolio_id == port.id)
            .where(FactorDefinition.name == 'Growth')
            .where(FactorExposure.calculation_date == date(2025, 9, 30))
        )
        fe, fd = result.one()

        print(f'Portfolio: {port.name}')
        print(f'Date: {fe.calculation_date}')
        print(f'Growth beta: {fe.exposure_value}')
        print(f'Should be > 1.0 (was ~0.01 before fix)')

asyncio.run(check())
"
```

## Cleanup

Temporary diagnostic scripts (already removed):
- `debug_today_betas.py`
- `debug_public_position_betas.py`
- `debug_position_betas.py`
- `debug_factor_api.py`
- `trace_ridge_factor_names.py`
- `check_factor_definitions.py`
- `verify_scaler_hypothesis.py`

Keep these for reference:
- `recalculate_historical_ridge.py` ✅
- `check_historical_ridge_data.py` ✅

## Timeline

- **Oct 18**: Ridge regression introduced (commit f7dcb947)
- **Sept 30 - Oct 21**: Historical data stored with incorrect scaling
- **Oct 22**: Bug discovered and fixed
- **Oct 22**: Recalculation script created to fix historical data

## Notes

- Recalculation is **idempotent** - safe to run multiple times
- Each run deletes existing records for the date before recreating them
- Options positions without price data are skipped (expected for expired/future options)
- Recalculation uses current market data, so slight variations may occur vs original calculations
