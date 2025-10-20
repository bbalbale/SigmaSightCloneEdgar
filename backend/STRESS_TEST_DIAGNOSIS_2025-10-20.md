# Stress Test Inverse Behavior - Root Cause Analysis
**Date:** 2025-10-20
**Portfolio:** HNW (Demo High Net Worth Investor Portfolio)
**Issue:** Portfolio shows inverse behavior in stress tests (loses money when market goes up)

---

## Executive Summary

**ROOT CAUSE IDENTIFIED:** The HNW portfolio has **ZERO traditional Market Beta** exposure calculated, meaning stress tests based on "Market" shocks show no impact or incorrect behavior.

The portfolio *does* have spread factor exposures (Growth-Value, Quality, Size, Momentum spreads), but the stress testing logic is looking for the traditional "Market" factor which is missing/zero.

---

## Diagnostic Findings

### 1. Factor Exposures (as of 2025-10-20)

| Factor | Beta | Dollar Exposure | Status |
|--------|------|-----------------|--------|
| **Market Beta** | **+0.0000** | **$0** | **❌ ZERO (PROBLEM)** |
| Low Volatility | +0.0000 | $0 | Missing |
| Value | +0.0000 | $0 | Missing |
| Growth | +0.0000 | $0 | Missing |
| Momentum | +0.0000 | $0 | Missing |
| Quality | +0.0000 | $0 | Missing |
| Size | +0.0000 | $0 | Missing |
| **Momentum Spread** | **+0.0151** | **+$64,572** | ✅ Present |
| **Growth-Value Spread** | **+0.3909** | **+$1,676,715** | ✅ Present |
| **Quality Spread** | **-1.0831** | **-$4,645,786** | ⚠️ Large Negative |
| **Size Spread** | **-0.0404** | **-$173,091** | ✅ Present |

### 2. Portfolio Details
- **Equity Balance:** $4,289,250
- **Active Positions:** 30 (all LONG)
- **Position Types:** No shorts, no sign inconsistencies

### 3. Stress Test Impact
When "Market" goes up +5%:
- **Expected P&L (current):** $0 (because Market Beta = 0)
- **Actual behavior:** Portfolio may lose money due to spread factor movements
- **Quality Spread:** Strong negative exposure (-$4.6M) could drive inverse behavior

---

## Why This Happens

### Recent System Changes
The system recently switched from **traditional 7-factor model** to **spread factors** (Growth-Value, Quality, Size, Momentum spreads) to eliminate multicollinearity issues.

**The problem:**
- Spread factors were calculated and stored
- Traditional factors (Market, Value, Growth, etc.) were **NOT** re-calculated
- They remain at ZERO in the database
- **Stress testing still references traditional "Market" factor**

### Factor Calculation History
Looking at `factors.py` lines 1006-1011 (modified recently):
```python
# Get all factor names from position_betas (includes both traditional and spread factors)
factor_names = set()
for pos_betas in position_betas.values():
    factor_names.update(pos_betas.keys())
```

This suggests the system *can* handle both traditional and spread factors, but only spread factors were calculated for the most recent run.

---

## Solutions

### Option 1: Re-calculate Traditional Factors (RECOMMENDED)
**Action:** Run factor calculation with **traditional 7-factor model** (not spread factors)

**How:**
```bash
cd backend
uv run python -c "
import asyncio
from datetime import date
from uuid import UUID
from app.database import AsyncSessionLocal
from app.calculations.factors import calculate_factor_betas_hybrid

async def main():
    async with AsyncSessionLocal() as db:
        portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
        result = await calculate_factor_betas_hybrid(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=date.today(),
            use_delta_adjusted=False
        )
        print('Market Beta:', result['factor_betas'].get('Market', 0))
        print('Exposure $:', result['storage_results'])

asyncio.run(main())
"
```

**Expected Result:**
- Market Beta: ~0.8 to 1.2 (typical for long portfolio)
- Market Dollar Exposure: $3M to $5M range

**Pros:**
- Quick fix, works with existing stress test logic
- Provides traditional factor exposures for analysis
- No code changes required

**Cons:**
- May have multicollinearity issues (why spread factors were introduced)
- Doesn't leverage new spread factor framework

### Option 2: Update Stress Testing to Use Spread Factors
**Action:** Modify `stress_testing.py` to map "Market" shocks to appropriate spread factors

**Changes needed:**
1. Add mapping: "Market" shock → combination of spread factors
2. Update `calculate_direct_stress_impact()` to use spread exposures
3. Test with all stress scenarios

**Pros:**
- Leverages new spread factor architecture
- Avoids multicollinearity issues
- More sophisticated factor model

**Cons:**
- Requires code changes and testing
- More complex to implement
- Need to define how market shocks translate to spread shocks

### Option 3: Calculate BOTH Traditional and Spread Factors
**Action:** Run both calculation types and store both sets of exposures

**Pros:**
- Most comprehensive approach
- Works with both old and new systems
- Provides maximum flexibility

**Cons:**
- More database storage
- Slightly longer calculation time
- Need to ensure no conflicts between factor types

---

## Recommended Next Steps

### Immediate Fix (5 minutes)
1. Re-run traditional factor calculation for HNW portfolio
2. Verify Market Beta is now non-zero
3. Test stress scenario: "Market Up 5%"
4. Confirm portfolio gains money (not loses)

### Long-term Solution (30-60 minutes)
1. Decide on factor model strategy (traditional, spread, or both)
2. Update batch processing to calculate chosen factors consistently
3. Update stress testing logic to match factor model
4. Document factor model architecture decision

---

## Technical Details

### Factor Calculation Code
- **Main calculation:** `app/calculations/factors.py::calculate_factor_betas_hybrid()`
- **Spread factors:** `app/calculations/factors_ridge.py` (if using Ridge regression)
- **Factor definitions:** `app/constants/factors.py::FACTOR_ETFS`
- **Spread definitions:** `app/constants/factors.py::SPREAD_FACTORS`

### Stress Testing Code
- **Main logic:** `app/calculations/stress_testing.py::calculate_direct_stress_impact()`
- **Scenario config:** `app/config/stress_scenarios.json`
- **Factor lookup:** Lines 506-510 use `FACTOR_NAME_MAP = {'Market': 'Market Beta', ...}`

### Database Tables
- **Portfolio factors:** `factor_exposures` (portfolio-level betas)
- **Position factors:** `position_factor_exposures` (position-level betas)
- **Factor definitions:** `factor_definitions` (factor metadata)

---

## Verification Script

After implementing the fix, run this to verify:

```bash
cd backend
uv run python scripts/analysis/diagnose_stress_test_issue.py
```

**Expected output:**
```
Market Beta         : Beta=+0.8500  $+3,645,962 [OK] MARKET FACTOR
Expected P&L for +5% market shock: $+182,298
[OK] Portfolio should gain money when market goes up (correct)
```

---

## Questions for User

1. **Do you want to keep spread factors or revert to traditional factors?**
   - Spread factors: Better for multicollinearity, but need stress test updates
   - Traditional factors: Works immediately with current stress tests

2. **When was the last time traditional Market Beta was calculated?**
   - Check batch processing logs
   - Review factor calculation history

3. **Are other portfolios affected?**
   - Run diagnostic on Balanced Individual and Hedge Fund Style portfolios
   - Check if this is system-wide or HNW-specific

---

**Created by:** Diagnostic script `scripts/analysis/diagnose_stress_test_issue.py`
**Full diagnostic output:** `backend/stress_test_diagnosis.txt`
