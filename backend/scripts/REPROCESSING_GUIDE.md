# Historical Calculation Reprocessing Guide

## Purpose

This guide explains how to reprocess analytical calculations from September 30, 2025 onwards after making fixes to calculation logic. This ensures all calculations use the latest code without making expensive API calls for market data.

## When to Reprocess

Reprocess calculations after making changes to:
- Calculation formulas or algorithms
- Data key names (e.g., volatility key alignment)
- Factor definitions or ticker mappings (e.g., SIZE → IWM)
- New calculation engines (e.g., spread factors)

## What the Script Does

### `reset_and_reprocess.py`

**Process for each of 3 demo portfolios:**

1. **Reset Starting Equity** - Restores portfolio equity to Sept 30 baseline
2. **Delete Old Calculations** - Removes calculation results from Sept 30 onwards
   - Respects foreign key constraints (deletes children first)
   - Preserves market data cache (no API calls needed)
3. **Reprocess Each Trading Day** - Runs full batch job for each trading day
   - Uses cached market data (fast, no API costs)
   - Runs 14 calculation engines per day:
     - Market data update
     - Position values update
     - Equity balance rollforward
     - Portfolio aggregation
     - Market beta (OLS)
     - Interest rate beta
     - Ridge factors (6 factors)
     - **Spread factors** (4 long-short factors - NEW)
     - Sector concentration
     - Volatility analytics (with aligned keys)
     - Market risk scenarios
     - Portfolio snapshots
     - Stress testing
     - Position correlations

## Tables Cleaned

### Direct Portfolio Tables
- `portfolio_snapshots` - Daily portfolio state
- `position_market_betas` - Market beta calculations
- `position_interest_rate_betas` - IR beta calculations

### Position-Linked Tables (via JOIN)
- `position_factor_exposures` - All factor betas (ridge + spread)
- `position_volatility` - Volatility metrics

### Correlation Tables (FK chain)
- `correlation_cluster_positions` (deepest child)
- `correlation_clusters` (child)
- `pairwise_correlations` (child)
- `correlation_calculations` (parent)

### Tables NOT Cleaned
- `market_data_cache` - Preserved to avoid API calls
- `positions` - Position definitions unchanged
- `portfolios` - Portfolio definitions unchanged

## How to Run

### Full Reprocessing (All 3 Portfolios)

```bash
cd backend
uv run python scripts/reset_and_reprocess.py
```

**Expected Runtime:**
- ~15-20 trading days from Sept 30 to present
- ~3 portfolios
- ~30-60 seconds per portfolio-day
- **Total: 15-30 minutes**

### What You'll See

```
================================================================================
RESET AND REPROCESS HISTORICAL CALCULATIONS
With Volatility Key Alignment + Size Factor Consistency + Spread Factors
================================================================================

Processing 3 portfolios
Date range: 2025-09-30 to 2025-10-20

================================================================================
TRADING DAYS
================================================================================
Found 15 trading days to process
First: 2025-09-30, Last: 2025-10-17

================================================================================
PORTFOLIO: High Net Worth
================================================================================
ID: e23ab931-a033-edfe-ed4f-9d02474780b4
Starting Equity: $2,850,000.00

[1/15] Processing 2025-09-30...
  OK Complete - Equity: $2,873,450.00

[2/15] Processing 2025-10-01...
  OK Complete - Equity: $2,881,200.00

...

================================================================================
ALL PORTFOLIOS COMPLETE
================================================================================
Total Successful: 45/45
Total Failed: 0/45

✅ Reprocessing complete with:
   - Volatility key alignment (realized_vol_21d → realized_volatility_21d)
   - Size factor consistency (SIZE → IWM)
   - Spread factor calculations (4 long-short factors)
```

## Portfolios Processed

1. **High Net Worth** - `e23ab931-a033-edfe-ed4f-9d02474780b4`
   - Starting Equity: $2,850,000
   - 17 positions

2. **Individual Investor** - `1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe`
   - Starting Equity: $250,000
   - 16 positions

3. **Hedge Fund Style** - `fcd71196-e93e-f000-5a74-31a9eead3118`
   - Starting Equity: $5,000,000
   - 30 positions (includes options)

## Recent Fixes Applied

### 1. Volatility Key Alignment (Oct 20, 2025)
**Problem**: Calculation returned `realized_vol_21d` but snapshot expected `realized_volatility_21d`
**Fix**: Aligned all volatility keys in `volatility_analytics.py:294-304`
**Result**: Volatility data now persists correctly to snapshots

### 2. Size Factor Consistency (Oct 20, 2025)
**Problem**: Size factor used "SIZE" placeholder in some files, "IWM" in others
**Fix**: Standardized all references to "IWM" (Russell 2000 small-cap index)
**Files Changed**:
- `stress_scenarios.json` - factor_mappings
- `seed_factors.py` - etf_proxy
- `market_data_service.py` - KNOWN_ETFS
**Result**: Consistent data across stress testing, seeding, and market data fetching

### 3. Spread Factor Implementation (Oct 20, 2025)
**Added**: 4 long-short factor calculations with 180-day window
- Growth-Value Spread (VUG/VTV)
- Momentum Spread (MTUM/SPY)
- Size Spread (IWM/SPY)
- Quality Spread (QUAL/SPY)
**Purpose**: Eliminates multicollinearity in factor analysis

## Verification After Reprocessing

### Check Volatility Data
```bash
cd backend
uv run python -c "
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot

async def check():
    async with get_async_session() as db:
        result = await db.execute(
            select(func.count(PortfolioSnapshot.id))
            .where(PortfolioSnapshot.realized_volatility_21d.isnot(None))
        )
        count = result.scalar()
        print(f'Snapshots with volatility data: {count}')

asyncio.run(check())
"
```

### Check Spread Factors
```bash
cd backend
uv run python -c "
import asyncio
from sqlalchemy import select, text
from app.database import get_async_session

async def check():
    async with get_async_session() as db:
        result = await db.execute(text('''
            SELECT DISTINCT factor_name
            FROM position_factor_exposures
            WHERE factor_name LIKE '%Spread%'
            ORDER BY factor_name
        '''))
        factors = result.fetchall()
        print('Spread factors found:')
        for f in factors:
            print(f'  - {f[0]}')

asyncio.run(check())
"
```

### Check Size Factor Data
```bash
cd backend
uv run python -c "
import asyncio
from sqlalchemy import select, text
from app.database import get_async_session

async def check():
    async with get_async_session() as db:
        result = await db.execute(text('''
            SELECT DISTINCT etf_proxy
            FROM factor_definitions
            WHERE name = 'Size'
        '''))
        proxy = result.scalar()
        print(f'Size factor ETF proxy: {proxy}')

        result = await db.execute(text('''
            SELECT COUNT(*)
            FROM position_factor_exposures
            WHERE factor_name = 'Size'
        '''))
        count = result.scalar()
        print(f'Size factor exposures: {count}')

asyncio.run(check())
"
```

## Troubleshooting

### "ERROR Portfolio not found"
- Check portfolio ID matches one of the 3 demo portfolios
- Verify database connection is working

### "ERROR ... (via FK chain)"
- Foreign key constraint violations
- Script already handles proper deletion order
- Check database logs for specific constraint

### "Warning: Market data failed"
- Some symbols may have gaps in market data cache
- Calculations continue with available data
- Not a critical error

### Script Hangs on a Date
- Press Ctrl+C to stop
- Check batch orchestrator logs for specific error
- Can resume from next date by updating start_date

## Safety Features

1. **FK-Safe Deletion** - Deletes children before parents
2. **Market Data Preservation** - Never deletes cached prices
3. **Error Isolation** - One portfolio failure doesn't stop others
4. **Progress Tracking** - Clear per-date and per-portfolio status
5. **Equity Rollforward** - Maintains proper equity chain

## Next Steps After Reprocessing

1. Verify data using verification scripts above
2. Check frontend portfolio dashboard for updated metrics
3. Run analytics API endpoints to confirm correct data
4. Optional: Generate portfolio reports with new data

## File Location

`backend/scripts/reset_and_reprocess.py`
