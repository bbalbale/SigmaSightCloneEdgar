# Target Prices Import Script

This document explains how to use the target prices import script to populate target prices for non-option symbols across all demo portfolios.

## Files Created

1. **CSV Data File**: `data/target_prices_import.csv`
   - Contains target price data for 35 symbols
   - Includes EOY, next year, and downside price targets

2. **Import Scripts**: 
   - `scripts/data_operations/populate_target_prices_via_service.py` ⭐ **RECOMMENDED**
     - Uses TargetPriceService.import_from_csv() - same method as the API
     - Proper Decimal precision handling
     - Returns service response format: {created, updated, errors, total}
   - `scripts/data_operations/populate_target_prices.py` (Legacy)
     - Custom implementation with direct database operations

## CSV Format

The CSV file must match the TargetPriceService expected format:

```csv
symbol,position_type,target_eoy,target_next_year,downside,current_price
AAPL,LONG,261.38,300.59,200.00,180.00
AMD,LONG,183.05,223.33,125.00,150.00
...
```

**Required Fields**:
- `symbol`: Stock symbol (e.g., AAPL, TSLA)
- `position_type`: Position type (typically "LONG")
- `target_eoy`: End-of-year target price
- `target_next_year`: Next year target price
- `downside`: Downside target price
- `current_price`: Current market price (for reference)

## Usage

### Using the Service-Based Script (Recommended)

#### Preview Changes (Recommended First)
```bash
# See what would be created without making changes
uv run python scripts/data_operations/populate_target_prices_via_service.py \
  --csv-file data/target_prices_import.csv \
  --dry-run
```

#### Execute Import
```bash
# Actually create the target price records
uv run python scripts/data_operations/populate_target_prices_via_service.py \
  --csv-file data/target_prices_import.csv \
  --execute
```

### Using the Legacy Script (Alternative)
```bash
# See what would be created without making changes
uv run python scripts/data_operations/populate_target_prices.py \
  --csv-file data/target_prices_import.csv \
  --dry-run

# Actually create the target price records
uv run python scripts/data_operations/populate_target_prices.py \
  --csv-file data/target_prices_import.csv \
  --execute
```

## What the Script Does

1. **Loads CSV Data**: Reads target prices for 35 symbols
2. **Finds Matching Positions**: Identifies non-option positions across all portfolios
3. **Gets Current Prices**: Fetches latest market prices from database
4. **Creates Target Prices**: Generates target price records with:
   - Target EOY and next year prices from CSV
   - Downside target price from CSV
   - Current market price from database
   - Calculated expected returns (automatic)
   - Links to specific positions

## Expected Results

Based on current demo data:
- **Portfolios**: 3 demo portfolios
- **Non-option positions**: 55 total across all portfolios
- **Matching symbols**: 34 out of 35 CSV symbols match positions
- **Target price records**: 54 (some positions exist in multiple portfolios)

### Symbol Coverage
- **Matched**: 34 symbols (AAPL, AMD, AMZN, etc.)
- **CSV but not in positions**: ZM (Zoom symbol mismatch)
- **Positions but not in CSV**: ZOOM (actual symbol in database)

## Safety Features

1. **Dry Run by Default**: Script runs in preview mode unless `--execute` is specified
2. **Duplicate Check**: Won't create target prices if they already exist
3. **Current Price Validation**: Requires valid market price data
4. **Non-Option Filter**: Only processes stocks/ETFs, skips complex option symbols
5. **Portfolio Coverage**: Works across all portfolios automatically

## Schema Mapping

| CSV Field | Database Field | Notes |
|-----------|---------------|-------|
| `symbol` | `symbol` | Stock symbol |
| `position_type` | `position_type` | Position type (LONG/SHORT) |
| `target_eoy` | `target_price_eoy` | End of year target |
| `target_next_year` | `target_price_next_year` | Next year target |
| `downside` | `downside_target_price` | Downside scenario |
| `current_price` | `current_price` | Market price reference |
| Calculated | `expected_return_eoy` | Auto-calculated |
| Calculated | `expected_return_next_year` | Auto-calculated |
| Calculated | `downside_return` | Auto-calculated |

## Service-Based Implementation

The recommended script uses the same TargetPriceService.import_from_csv() method that powers the API endpoints:

**Benefits:**
- Identical validation logic as the REST API
- Consistent error handling and response format  
- Automatic precision handling for Decimal fields
- Returns structured response: `{created, updated, errors, total}`
- Same CSV contract as API endpoint

## Troubleshooting

### Common Issues

1. **Symbol Mismatch**: Check if symbol in CSV exactly matches database symbol
2. **No Current Price**: Ensure market data exists for the symbol
3. **Duplicate Records**: Script will warn and skip existing target prices
4. **Options Symbols**: Long option symbols are automatically filtered out

### Validation

After running the script, verify results with:
```bash
# Check created records
uv run python -c "
import asyncio
from app.database import get_async_session
from sqlalchemy import select, func
from app.models.target_prices import TargetPrice

async def check():
    async with get_async_session() as db:
        count = await db.scalar(select(func.count(TargetPrice.id)))
        print(f'Total target price records: {count}')

asyncio.run(check())
"
```

## Ready to Execute

The script is ready to use against the current database schema. All 35 symbols from your data have been loaded into the CSV file and the script will handle:

- Creating target price records for matching positions
- Calculating expected returns automatically  
- Using current market prices from the database
- Skipping duplicates and invalid records safely

Run with `--dry-run` first to preview, then `--execute` to create the actual records.

---

## Appendix: Target Prices Rationale (09-18 Version)

### Rationale for Upside vs Downside Targets

#### **Upside Case (Bullish EOY & Next Year)**

**Market Assumption**: Soft landing scenario with corporate earnings expanding double digits in 2025 and ~10% in 2026, while valuation multiples hold near historical highs.

**By Sector/Category**:

- **Tech/AI Beneficiaries** (NVDA, MSFT, META, AMD, GOOGL, AMZN, NFLX, TSLA): Given sustained AI/streaming/EV investment, these companies receive premium multiples and outsized upside (+30–50% next year).

- **Defensives** (JNJ, PG, UNH, XOM): Lower growth expectations but stable fundamentals. Upside is modest (10–20%).

- **Bonds** (BND, FXNAX): Interest rates ease, producing small but steady NAV gains.

- **Gold** (GLD): Mild tailwind from weaker USD and modest geopolitical premium.

- **Broad ETFs** (SPY, QQQ, VTI, VNQ, VTIAX): Track index-level assumptions (8–12% EOY, ~20–30% next year in a continued bull market).

#### **Downside Case (Severe Correction)**

**Market Assumption**: Economic downturn with significant multiple compression and demand destruction.

**By Sector/Category**:

- **Equities Overall**: S&P (SPY, VTI) drops ~25%. QQQ more volatile, down ~25–30%.

- **High-Beta Tech** (NVDA, AMD, TSLA, ROKU, SHOP, META, NFLX): 35–45% drawdowns possible due to valuation compression and cyclical demand hit.

- **Financials** (JPM, C, BRK-B): Down ~20–25% as higher rates pressure credit conditions.

- **Defensives** (JNJ, PG, UNH): Hold better relative performance, down ~10–15%.

- **Energy** (XOM): Oil demand slows, prices retrace, ~20% downside.

- **Gold** (GLD): Mixed performance—can rally as safe haven, but liquidity crunches often hit metals first; modeled ~10–15% downside.

- **Bonds** (BND, FXNAX): Could actually gain if Fed forced to cut aggressively, so modest upside/downside balance (kept relatively stable).

- **Speculative Small Caps** (PTON, ROKU, ZOOM): Higher beta characteristics, 40–50% downside possible.

### **Methodology Notes**

- Target prices reflect fundamental analysis combined with scenario-based modeling
- Upside targets assume continued multiple expansion in favorable macro environment
- Downside targets model stress conditions while considering sector-specific resilience
- Current price references provide baseline for return calculations
- All targets subject to revision based on evolving market conditions and company fundamentals