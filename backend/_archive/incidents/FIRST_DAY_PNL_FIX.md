# First Calculation Day P&L Fix

**Date**: November 7, 2025
**Issue**: $26K equity discrepancy in Individual Investor portfolio
**Root Cause**: First calculation day didn't account for unrealized gains between entry prices and first market prices

## Problem Description

When portfolios were seeded:
- **Entry equity**: $484,860 (cash used to buy positions)
- **Entry market value**: $508,522 (positions already up $23,662 at entry prices)
- **July 1 market value**: $508,522 (using July 1 market prices)

The first calculation day (July 1) would:
1. Start with equity = $484,860 (from seed data)
2. Calculate P&L = 0 (because it used July 1 price as both current and "previous" price)
3. End with equity = $484,860 (unchanged)

But equity **should have been** $508,522 to reflect the position market values.

This $23,662 gap persisted throughout all calculations, growing to $26K by November 6 due to compounding effects.

## Solution: Option 4 - Initial Position Gain

Modified `app/batch/pnl_calculator.py` to detect first calculation day and use **entry_price** as baseline instead of current_price.

### Code Changes

**File**: `app/batch/pnl_calculator.py`
**Lines**: 460-497
**Function**: `_calculate_position_pnl()`

#### Logic Flow:

**First Calculation Day** (no previous snapshot):
```python
if previous_snapshot is None:
    # Use entry_price as baseline
    previous_price = position.entry_price
    # P&L = (current_price - entry_price) × quantity × multiplier
```

**Normal Days** (previous snapshot exists):
```python
else:
    # Use previous trading day price
    previous_price = get_previous_trading_day_price(...)
    # P&L = (current_price - previous_price) × quantity × multiplier
```

### Expected Results

After clearing snapshots and re-running batch calculations:

**July 1, 2025** (First Day):
- Entry equity: $484,860
- Entry market value: $508,522
- Daily P&L: +$23,662 (unrealized gain from entry to July 1 prices)
- New equity: $508,522 ✅

**July 2, 2025** (Normal Day):
- Previous equity: $508,522
- Daily P&L: (July 2 market value - July 1 market value)
- New equity: $508,522 + daily_pnl ✅

**November 6, 2025**:
- Equity should match market value (no $26K gap) ✅

## Benefits

✅ Works for all portfolios (leverage, no leverage, options, stocks)
✅ No seed data changes needed
✅ Survives calculation table clears
✅ Accurate unrealized gain tracking from entry
✅ Handles positions with different entry dates
✅ Graceful fallback if entry_price is missing

## Testing Instructions

1. **Clear existing snapshots**:
   ```sql
   DELETE FROM portfolio_snapshots WHERE portfolio_id = '<individual_investor_id>';
   ```

2. **Reset portfolio equity to seed value**:
   ```sql
   UPDATE portfolios
   SET equity_balance = 484860.00
   WHERE id = '<individual_investor_id>';
   ```

3. **Run batch calculations**:
   ```bash
   cd backend
   uv run python scripts/batch_processing/run_batch.py --start-date 2025-07-01 --end-date 2025-11-06
   ```

4. **Verify results**:
   ```bash
   uv run python scripts/debug/trace_individual_investor_exposure.py
   ```

   Expected output:
   - July 1 equity: $508,522 (matches market value)
   - November 6 equity: ~$560,664 (matches market value)
   - No $26K discrepancy

## Logging

The fix includes detailed debug logging:

```
[POSITION PNL] AAPL: First calculation day, using entry price $207.58 as baseline
  Current price: $207.58, Previous price: $207.58
  Price change: $0.00, Quantity: 85
  Position P&L: $0.00
```

Or for positions with gain:

```
[POSITION PNL] NVDA: First calculation day, using entry price $153.29 as baseline
  Current price: $153.29, Previous price: $140.00 (entry)
  Price change: $13.29, Quantity: 25
  Position P&L: $332.25
```

## Edge Cases Handled

1. **Positions with different entry dates**: Only positions where `entry_date <= calculation_date` are included
2. **Missing entry prices**: Falls back to current price (P&L = 0) with warning log
3. **Options positions**: Correctly applies 100x multiplier
4. **Private positions**: Skipped (no market prices)
5. **Staggered portfolio entries**: Each position calculates its own initial gain only on first day it's included

## Status

✅ Code changes complete
⏳ Testing required (user will clear snapshots and re-run batch)
📝 Documentation updated
