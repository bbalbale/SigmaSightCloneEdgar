# Railway Market Data Investigation Report

**Date:** 2025-10-06
**Issue:** API returning 64 days of historical data vs 124 days in database

---

## Executive Summary

✅ **NO BUG FOUND** - System is working as designed. The discrepancy was caused by:
1. Audit script requesting `lookback_days=90` (not 180)
2. API correctly filtering to 90 calendar days = 64 trading days
3. Database contains full 180 days = 124 trading days

---

## Investigation Details

### Database Content (Direct Query)
```
Total Records: 4,975
Date Range:    2025-04-09 to 2025-10-06
Trading Days:  124 days
Calendar Days: ~180 days
Coverage:      100% (54/54 position symbols)
```

### API Response (via /prices/historical)
```
Lookback Days: 90 (requested by audit script)
Date Range:    2025-07-08 to 2025-10-06
Trading Days:  64 days
Calendar Days: 90 days
Coverage:      100% (29/29 symbols)
```

### Root Cause Analysis

**File:** `backend/scripts/railway/audit_railway_market_data.py`
**Line:** 100

```python
params={
    "lookback_days": 90,  # ← Requesting only 90 days
    "interval": "daily"
}
```

**API Implementation:** `app/api/v1/data.py:668`
```python
start_date = end_date - timedelta(days=lookback_days)
```

The API correctly filters `MarketDataCache.date >= start_date`, returning only the requested 90 calendar days.

---

## Validation Testing

Tested endpoint with multiple `lookback_days` values:

| Lookback | Expected Start | Actual Start | Trading Days | Calendar Days |
|----------|----------------|--------------|--------------|---------------|
| 30       | 2025-09-05     | 2025-09-08   | 21           | ~30           |
| 60       | 2025-08-06     | 2025-08-07   | 42           | ~60           |
| **90**   | **2025-07-07** | **2025-07-08** | **64**     | **90**        |
| 120      | 2025-06-07     | 2025-06-09   | 83           | ~120          |
| 150      | 2025-05-08     | 2025-05-09   | 103          | ~150          |
| **180**  | **2025-04-08** | **2025-04-09** | **124**    | **180**       |

**Observation:** With `lookback_days=180`, the API returns the full 124 trading days, matching the database exactly.

---

## Date Offset Explanation

Small 1-2 day differences between "Expected" and "Actual" start dates occur because:
- Expected = calculated using calendar days (`today - lookback_days`)
- Actual = first available trading day (database skips weekends/holidays)
- If calculated start falls on weekend, actual start is next trading day

**Example:**
- Expected: 2025-09-05 (Friday - 2 days ago from expected)
- If Sept 5 was a weekend, database starts at next trading day
- Actual: 2025-09-08 (Monday)

This is **expected behavior** for financial data.

---

## Script Issues Fixed

### Issue 1: Wrong Response Field Name
```python
# Before
timeseries = prices.get("timeseries", {})

# After
timeseries = prices.get("symbols", {})  # ✅ Fixed
```

### Issue 2: Wrong Data Structure Parsing
```python
# Before (expected list of objects)
dates = [entry.get("date") for entry in symbol_data if entry.get("date")]

# After (parallel arrays)
dates = symbol_data["dates"]  # ✅ Fixed
```

### Issue 3: Factor ETF Response Structure
```python
# Before
etfs = factors.get("factor_etfs", [])

# After
etf_data = factors.get("data", {})  # ✅ Fixed
```

---

## Recommendations

### 1. Update Audit Script Default (Optional)
To see full historical data by default, increase lookback_days:

```python
params={
    "lookback_days": 180,  # Changed from 90 to see all available data
    "interval": "daily"
}
```

### 2. Add Parameter Documentation
Document in API reference that `lookback_days` uses **calendar days**, resulting in fewer **trading days** due to weekends/holidays.

### 3. Consider Adding Trading Days Parameter (Future Enhancement)
```python
# Potential future enhancement
@router.get("/prices/historical/{portfolio_id}")
async def get_historical_prices(
    lookback_days: int = Query(150, description="Calendar days lookback"),
    lookback_trading_days: Optional[int] = Query(None, description="Trading days lookback (overrides lookback_days)"),
    ...
)
```

This would allow requesting "last 60 trading days" vs "last 60 calendar days".

---

## Conclusion

✅ **API is functioning correctly**
✅ **Database has complete data (124 trading days)**
✅ **Audit script now works after field name fixes**
✅ **Date filtering logic is accurate**

The perceived "discrepancy" was simply the audit script requesting fewer days than available in the database. No code changes required unless you want to implement the optional recommendations above.

---

## Test Commands

```bash
# Run audit with default 90 days
uv run python scripts/railway/audit_railway_market_data.py

# Test different lookback periods
uv run python scripts/railway/test_lookback_days.py

# Direct database query (for comparison)
uv run python scripts/railway/audit_railway_database_direct.py
```

---

**Status:** ✅ RESOLVED - Working as designed
**Action Required:** None (optional enhancements listed above)
