# Historical Data Seeding - Implementation Summary

**Date**: October 14, 2025
**Issue**: CURRENT_PRICES dictionary contained hardcoded, outdated mock prices causing data corruption
**Solution**: Replace mock seeding with real 180-day YFinance historical data fetch

---

## What Was Changed

### 1. **Created Shared Module** (`app/db/fetch_historical_data.py`)
- **Purpose**: Reusable YFinance data fetching for both seeding and refresh operations
- **Functions**:
  - `fetch_and_store_historical_data()`: Fetch and store historical data for multiple symbols
  - `filter_stock_symbols()`: Filter out options symbols, keep stocks/ETFs only

### 2. **Rewrote Seeding** (`app/db/seed_initial_prices.py`)
- **Before**: Used hardcoded `CURRENT_PRICES` dictionary with wrong prices (NVDA=$700)
- **After**: Fetches 180 days of real data from YFinance during seeding
- **Backward Compatible**: Old `seed_initial_prices()` function redirects to new `seed_historical_prices()`
- **No Breaking Changes**: `scripts/database/seed_database.py` works without modification

### 3. **Refactored Refresh Script** (`scripts/testing/refresh_180_days_yfinance.py`)
- **Before**: 195 lines with duplicated fetching logic
- **After**: 110 lines using shared module
- **Benefit**: DRY principle - single source of truth for YFinance fetching

---

## How It Works Now

### Seeding Process (Automatic)

When you run `python scripts/reset_and_seed.py seed`:

1. **Get Symbols**: Queries database for all unique symbols in demo portfolios
2. **Filter Options**: Removes options symbols (e.g., `SPY250919C00460000`), keeps stocks/ETFs only
3. **Fetch 180 Days**: Downloads real historical data from YFinance
   - Date range: Today - 180 days to Today
   - ~123 actual trading days (excludes weekends/holidays)
4. **Store Data**: Upserts to `market_data_cache` table with `data_source='yfinance'`
5. **Update Positions**: Calculates market values using latest real prices

**Duration**: ~2-3 minutes (fetches 40+ symbols × 180 days)

### Manual Refresh (As Needed)

If you need to refresh data later:

```bash
cd backend
uv run python scripts/testing/refresh_180_days_yfinance.py
```

This overwrites existing data with fresh YFinance data.

---

## Benefits

### ✅ **Data Quality**
- **Real Prices**: No more NVDA=$700 corrupted seed data
- **Accurate**: Actual market prices from YFinance
- **Complete**: 180 days of history immediately available

### ✅ **Calculation Ready**
- **Correlations**: Enough data for statistically significant correlations
- **Factor Analysis**: Historical returns for beta calculations
- **No Manual Steps**: Database is fully ready after seeding

### ✅ **Code Quality**
- **DRY**: Shared module eliminates duplication
- **Maintainable**: Single place to update YFinance fetching logic
- **Backward Compatible**: No changes needed to existing scripts

---

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `app/db/fetch_historical_data.py` | **NEW** - Shared fetching module | 184 |
| `app/db/seed_initial_prices.py` | **REWRITE** - Use real YFinance data | 180 |
| `scripts/testing/refresh_180_days_yfinance.py` | **REFACTOR** - Use shared module | 110 |

**Total**: 1 new file, 2 files rewritten, ~85 lines removed (de-duplication)

---

## Testing Results

### Import Verification ✅
```bash
cd backend
uv run python -c "from app.db.fetch_historical_data import fetch_and_store_historical_data, filter_stock_symbols; from app.db.seed_initial_prices import seed_historical_prices; print('All imports working')"
```
**Result**: All imports successful

### Symbol Filter Test ✅
```python
Input: ['NVDA', 'META', 'SPY', 'SPY250919C00460000', 'QQQ251017P00420000']
Filtered: ['NVDA', 'META', 'SPY']  # Options removed
```
**Result**: Correctly filters out options, keeps stocks/ETFs

### Backward Compatibility ✅
- `seed_database.py` calls `seed_initial_prices()` (line 74)
- Function redirects to `seed_historical_prices(db, days=180)`
- No changes needed to seeding orchestrator

---

## Expected Seeding Output

When you run seeding, you'll see:

```
================================================================================
HISTORICAL PRICE SEEDING
================================================================================
Fetching 180 days of real market data from YFinance
This replaces the old hardcoded CURRENT_PRICES approach

Found 41 unique symbols in demo portfolios
Symbols to seed: AAPL, AMD, AMZN, BND, BRK-B, ...

Batch 1/5: Processing 10 symbols
  [AAPL] Fetching...
  [AAPL] ✅ 123 days stored
  [AMD] Fetching...
  [AMD] ✅ 123 days stored
  ...

================================================================================
SEEDING COMPLETE
================================================================================
✅ Stored 5,043 price records for 41 symbols
✅ Updated market values for 63 positions
🎯 Database ready for correlation and factor analysis!
```

---

## Migration Guide

### For Fresh Database Setup
**No changes needed!** Just run:
```bash
python scripts/reset_and_seed.py seed
```

Seeding now automatically fetches real historical data.

### For Existing Database
If you have existing corrupted seed data:

```bash
# Option 1: Full reset (recommended)
python scripts/reset_and_seed.py reset  # Drops all data
python scripts/reset_and_seed.py seed   # Seeds with real data

# Option 2: Refresh only (keeps demo portfolios)
cd backend
uv run python scripts/testing/refresh_180_days_yfinance.py
```

---

## Correlation Calculation Fix Reference

This seeding improvement works in conjunction with the correlation calculation fix documented in the conversation summary:

**Problem**: Date misalignment when calculating returns
- NVDA missing 9/29 → 9/30 return = 2-day return
- META has 9/29 → 9/30 return = 1-day return
- Correlating multi-day vs single-day returns = wrong correlation

**Solution**: Align dates BEFORE calculating returns
```python
# Fixed in 3 functions:
# - correlation_service.py: _get_position_returns()
# - factors.py: fetch_factor_returns()
# - factors.py: calculate_position_returns()
```

**Result**: NVDA-META correlation changed from -0.941 (impossible) to +0.252 (correct)

**With Real Historical Data**: Now seeding provides 180 days of clean, aligned data from day 1

---

## Troubleshooting

### Seeding Takes Too Long
- **Expected**: 2-3 minutes for 40+ symbols × 180 days
- **Normal**: YFinance API can be slow during market hours
- **Solution**: Run seeding during off-market hours if needed

### YFinance API Errors
- **Rate Limits**: YFinance is generally permissive, but can throttle heavy usage
- **Mitigation**: Batch size of 10 symbols with built-in delays
- **Retry**: Script includes error handling and continues on failures

### Missing Data for Some Symbols
- **Normal**: Not all symbols have 180 days of history (new listings, delisted stocks)
- **Handled**: Script logs warnings but continues
- **Impact**: Positions without prices show warning during market value update

---

## Next Steps

1. **Test Seeding**: Run `python scripts/reset_and_seed.py seed` to verify
2. **Check Correlations**: Run `scripts/testing/diagnose_nvda_meta_correlation.py`
   - Expected: NVDA-META correlation ~0.25 with clean data
   - No warnings about extreme price moves
3. **Verify Data**: Check `market_data_cache` table has ~5,000 records
4. **Run Batch**: Execute `scripts/batch_processing/run_batch.py`
   - Should complete all 8 engines with sufficient historical data

---

## Summary

**Before**:
- Hardcoded CURRENT_PRICES with wrong values (NVDA=$700)
- Only 1 day of mock data created during seeding
- Correlation calculations failed due to insufficient data
- Manual refresh required after seeding

**After**:
- Real YFinance data fetched automatically during seeding
- 180 days (123 trading days) of historical data available immediately
- Correlation and factor calculations work from day 1
- No manual refresh needed - database is ready to use

**Impact**: Clean data → Accurate correlations → Reliable risk analytics

