# Database Fixes

## 2025-11-11: Fixed Short Interest Factor Status

**Issue**: Market factors were not displaying on the risk metrics page because the `Short Interest` factor was marked as `is_active=True` in the `factor_definitions` table, but it was not being calculated by the batch process.

**Root Cause**: The `FactorExposureService.get_portfolio_exposures()` method requires ALL active style/macro factors to be present on the same calculation date. With Short Interest marked as active but not calculated, the service returned `available=False`.

**Fix Applied**: Updated the `factor_definitions` table to set `Short Interest` factor to `is_active=False`:

```sql
UPDATE factor_definitions
SET is_active = FALSE, updated_at = NOW()
WHERE name = 'Short Interest';
```

**Result**:
- Service now correctly identifies 9 active style/macro factors
- Market factors now display properly on risk metrics page
- Factor exposures endpoint returns `available=True` with complete data

**Active Factors After Fix** (9 total):
1. Provider Beta (1Y) - style
2. Market Beta (90D) - style
3. Momentum - style
4. IR Beta - macro
5. Value - style
6. Growth - style
7. Quality - style
8. Size - style
9. Low Volatility - style

**Note**: This aligns with the code comment in `backend/app/services/factor_exposure_service.py:222-223` which states "We now have 8 active factors: 7 style factors + IR Beta macro factor (Short Interest is inactive)".
