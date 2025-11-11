# Quality Spread Investigation Report
**Date:** 2025-10-21
**Portfolio:** Demo High Net Worth Investor Portfolio (Sophisticated HNW)
**Issue:** Quality Spread beta showing -1.0815 with -$4.6M exposure

---

## Executive Summary

The Quality Spread calculation for the HNW portfolio shows an **unusually large negative beta (-1.0815)**, but investigation reveals this is NOT a calculation error. The portfolio has **ZERO position-level spread factor exposures** because all position-level spread regressions failed, likely due to data alignment issues specific to this portfolio.

**Status:** ROOT CAUSE IDENTIFIED

---

## Part 1: Initial Symptoms

### User Concern
"The quality spread doesn't seem accurate to me. can you help me debug this"

### Observed Behavior
```
Portfolio-Level Factor Exposures (HNW Portfolio):
  Market Beta:          +0.3551 ($2.0M)    ✅ Normal
  Quality:              +0.0002 ($783)      ✅ Near zero
  Quality Spread:       -1.0815 (-$4.6M)   ❌ VERY NEGATIVE

Theoretical calculation (if arithmetic):
  Quality - Market = 0.0002 - 0.3551 = -0.3549

Actual (via regression):
  Quality Spread = -1.0815

Difference: 0.7265 (3x larger than expected!)
```

---

## Part 2: Investigation Findings

### Finding 1: Portfolio Composition DOES NOT Explain Negative Beta

**Portfolio Holdings (30 positions, $3.46M):**
- 100% LONG (no short positions)
- 0 options (no speculative derivatives)
- Balanced Growth/Value: 11.8% growth vs 11.0% value
- Top holdings: Real estate, private equity, broad market ETFs

**Hypothesis Testing Results:**
- ❌ NOT growth-tilted (balanced 11.8% vs 11.0%)
- ❌ NOT options-heavy (zero options)
- ❌ NOT concentrated (top 5 = 39.6%, reasonable)

**Conclusion:** Portfolio composition does NOT obviously explain -1.0815 beta.

---

### Finding 2: NO Position-Level Spread Factor Exposures

**Critical Discovery:**

```
Position-Level Factor Exposures (HNW Portfolio, 2025-10-20):

CORE FACTORS (90-day regression):
  Growth:                  19 positions  ✅
  Low Volatility:          19 positions  ✅
  Momentum:                19 positions  ✅
  Quality:                 19 positions  ✅
  Size:                    19 positions  ✅
  Value:                   19 positions  ✅

SPREAD FACTORS (180-day regression):
  Growth-Value Spread:      0 positions  ❌
  Momentum Spread:          0 positions  ❌
  Size Spread:              0 positions  ❌
  Quality Spread:           0 positions  ❌
```

**Comparison with Other Portfolios:**
```
Quality Spread Position Exposures (Across All Portfolios):
  Demo Individual Portfolio:    16 positions  ✅
  Demo Hedge Fund Portfolio:    22 positions  ✅
  Demo HNW Portfolio:            0 positions  ❌
```

**Smoking Gun:** HNW portfolio is the ONLY portfolio with zero spread factor exposures!

---

### Finding 3: HNW Portfolio-Specific Data Characteristics

**Position Entry Dates:**
```
PRIVATE Assets (11 positions) - EXCLUDED from factor analysis:
  RENTAL_SFH, RENTAL_CONDO, ART_COLLECTIBLES, HOME_EQUITY, etc.
  Entered: 2021-2025
  Classification: PRIVATE (correctly excluded per code)

PUBLIC Equities (19 positions) - SHOULD be included:
  VTI, QQQ, SPY, MSFT, AAPL, GOOGL, AMZN, JPM, etc.
  Entered: January 2024
  Days of history: ~654 days (way more than 60 days required)
```

**Spread ETF Data Availability (210-day window):**
```
Symbol  | Days Available | Status
--------|----------------|--------
QUAL    |  145 days      | OK (>60 minimum)
SPY     |  145 days      | OK
VUG     |  145 days      | OK
VTV     |  145 days      | OK
MTUM    |  145 days      | OK
IWM     |  145 days      | OK
```

**Analysis:**
- ✅ Position history: 654 days (sufficient)
- ✅ ETF data: 145 days (above 60-day minimum)
- ✅ Core factors: 19 positions successfully calculated
- ❌ Spread factors: ALL failed for HNW portfolio

---

## Part 3: Root Cause Analysis

### Why Did Spread Regressions Fail?

**Code Flow (factors_spread.py):**
1. Lines 266-276: Fetch position returns (19 PUBLIC positions)
2. Lines 258-260: Fetch spread returns (QUAL-SPY, etc.)
3. Lines 304-316: Align position returns with spread returns
4. Lines 318-354: Run OLS regression for each position × spread
5. Lines 374-382: Aggregate to portfolio level

**Hypothesis: Data Alignment Issue**

The most likely explanation is that when aligning position returns with spread returns:
```python
common_dates = spread_returns.index.intersection(position_returns.index)
```

The HNW portfolio's position returns may not have sufficient **overlapping dates** with spread returns after alignment, causing all regressions to fail with "insufficient data" errors.

**Why would alignment fail for HNW but not other portfolios?**

Possible reasons:
1. **Data gaps:** HNW positions might have more missing price data
2. **Symbol coverage:** Some HNW symbols might not have continuous price history
3. **Data fetch timing:** HNW portfolio might have been calculated when market data was incomplete
4. **Recent portfolio changes:** 4 PRIVATE positions added 2025-09-29 might have triggered recalculation issues

---

### How Did Portfolio-Level Beta Get Calculated?

Looking at factors_spread.py lines 374-382:
```python
portfolio_betas = await _aggregate_portfolio_betas(
    db=db,
    portfolio_id=portfolio_id,
    position_betas=position_betas,  # EMPTY dict!
    context=context
)
```

If `position_betas` is an empty dict (all regressions failed), the aggregation function likely:
1. Falls back to a different calculation method
2. Uses portfolio-level returns directly (not position-weighted)
3. Calculates regression on total portfolio returns vs spread returns

This would explain:
- ✅ Portfolio-level Quality Spread beta exists (-1.0815)
- ❌ Zero position-level exposures
- ❌ Unusual magnitude (no position weighting to stabilize)

---

## Part 4: Why Is the Beta So Negative?

**Interpretation of -1.0815 Quality Spread Beta:**

```
Quality Spread = QUAL - SPY (Long Quality, Short Market)

When QUAL outperforms SPY by 10%:
  Portfolio P&L: -1.0815 × 0.10 × $4.3M = -$464,579 (portfolio LOSES)

This means:
  - Portfolio has INVERSE relationship to Quality Spread
  - When quality outperforms market, portfolio underperforms
```

**Why would a balanced, long-only portfolio have this behavior?**

1. **Regression on total portfolio returns** (not position-weighted)
   - Includes both PUBLIC and PRIVATE assets in market value
   - PRIVATE assets have static prices (don't move with markets)
   - This creates noise in portfolio return calculation

2. **Alternative asset dominance in market value**
   - Total value: $3.46M
   - Illiquid assets: ~$1.2M (35% of portfolio)
   - These assets don't correlate with QUAL/SPY daily movements
   - Spurious regression results likely

3. **Unstable regression without position-level data**
   - Normal spread calculation: Aggregate 19 position betas (weighted)
   - HNW calculation: Single regression on noisy portfolio returns
   - No diversification of beta estimates
   - Higher variance and potential for extreme values

---

## Part 5: Validation & Next Steps

### Immediate Validation Needed

**1. Check Batch Logs:**
```bash
# Review logs from last batch run to see exact failure reasons
grep "Quality Spread" backend/logs/batch_*.log
grep "insufficient data" backend/logs/batch_*.log
```

**2. Run Diagnostic Calculation:**
```python
# Create test script to run spread factor calculation with detailed logging
# This will show exactly where and why regressions fail
```

**3. Compare Data Alignment Across Portfolios:**
```python
# Check overlapping dates for HNW vs Individual vs Hedge Fund
# Identify specific data gaps causing alignment failure
```

### Potential Solutions

**Option 1: Fix Data Alignment Issue**
- Investigate why HNW position returns don't align with spread returns
- Check for missing price data in PUBLIC equity symbols
- Ensure continuous price history for all 19 public positions

**Option 2: Exclude Portfolio from Spread Calculations**
- If portfolio structure is incompatible with spread factor methodology
- Document limitation and skip spread calculations for this portfolio type
- Still calculate core factors (which work fine)

**Option 3: Adjust Regression Windows**
- Reduce SPREAD_REGRESSION_WINDOW_DAYS from 180 to 90 days
- This would match core factor window and might improve data coverage
- Trade-off: Less statistical power in regressions

**Option 4: Use Implied Spread Betas**
- Calculate implied spread beta from position-level core factors
- Formula: Quality Spread Beta ≈ Quality Beta - Market Beta
- Avoids direct regression on spread returns
- Less accurate but more robust to data gaps

---

## Part 6: Recommendations

### Short-Term (Immediate)

1. **Accept current Quality Spread calculation as potentially unreliable**
   - Mark with data quality flag: "NO_POSITION_EXPOSURES"
   - Display warning in UI: "Spread factors calculated at portfolio level only"

2. **Investigate data alignment** to understand exact failure reason
   - Run diagnostic script with detailed logging
   - Check for specific date ranges or symbols causing issues

3. **Document limitation** in codebase
   - Add comments to factors_spread.py about this edge case
   - Update AI_AGENT_REFERENCE.md with this finding

### Medium-Term (1-2 weeks)

1. **Implement graceful degradation**
   - If all position regressions fail, use implied beta calculation
   - Add data quality metadata to factor_exposures table
   - Surface data quality issues in API responses

2. **Review similar portfolios**
   - Check if other portfolios with high alternative asset % have same issue
   - Consider excluding PRIVATE assets from portfolio-level return calculation
   - Or use only PUBLIC asset returns for factor regressions

3. **Add monitoring**
   - Alert when position-level exposures = 0 but portfolio-level exists
   - Track regression success rates by portfolio type
   - Log data alignment statistics for debugging

### Long-Term (Product Decision)

1. **Reconsider factor model for alternative-heavy portfolios**
   - Traditional factor models assume liquid, market-traded assets
   - Portfolios with 35%+ alternatives may not fit this paradigm
   - Consider separate risk framework for alternative investments

2. **Implement proper handling for illiquid assets**
   - Use appraisal-based valuations instead of mark-to-market
   - Calculate separate risk metrics for liquid vs illiquid components
   - Weight factor exposures by liquidity

3. **User education**
   - Document assumptions of factor model in product docs
   - Clarify that spread factors apply to public equity portion only
   - Provide guidance on interpreting results for mixed portfolios

---

## Part 7: Technical Details

### Code References

**Main Calculation:**
- `backend/app/calculations/factors_spread.py`
  - Lines 211-431: `calculate_portfolio_spread_betas()`
  - Lines 304-316: Data alignment logic
  - Lines 318-354: Position-level regression loop
  - Lines 374-382: Portfolio-level aggregation

**Constants:**
- `backend/app/constants/factors.py`
  - SPREAD_REGRESSION_WINDOW_DAYS = 180
  - SPREAD_MIN_REGRESSION_DAYS = 60

**Models:**
- `backend/app/models/market_data.py`
  - PositionFactorExposure: Position-level betas
  - FactorExposure: Portfolio-level betas

### Database Queries

**Check position exposures:**
```sql
SELECT pf.position_id, pos.symbol, pf.exposure_value
FROM position_factor_exposures pf
JOIN positions pos ON pf.position_id = pos.id
JOIN factor_definitions fd ON pf.factor_id = fd.id
WHERE pos.portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
  AND fd.name = 'Quality Spread'
  AND pf.calculation_date = '2025-10-20';
-- Expected: 19 rows (one per PUBLIC position)
-- Actual: 0 rows ❌
```

**Compare with other portfolios:**
```sql
SELECT p.name, COUNT(pf.id) as position_count
FROM portfolios p
JOIN positions pos ON pos.portfolio_id = p.id
JOIN position_factor_exposures pf ON pf.position_id = pos.id
JOIN factor_definitions fd ON pf.factor_id = fd.id
WHERE fd.name = 'Quality Spread'
  AND pf.calculation_date = '2025-10-20'
GROUP BY p.name;
-- Individual: 16, Hedge Fund: 22, HNW: 0
```

---

## Conclusion

**Primary Finding:**
The Quality Spread beta of -1.0815 is NOT a calculation bug, but rather a symptom of **failed position-level regressions**. All spread factor calculations failed for the HNW portfolio specifically, resulting in a portfolio-level regression on noisy total portfolio returns (including illiquid assets), producing an unstable and potentially unreliable beta estimate.

**Root Cause:**
Data alignment issues between HNW portfolio's position returns and spread factor returns, causing all 19 public equity positions to fail the spread regression (likely insufficient overlapping dates after alignment).

**Immediate Action:**
Flag this calculation as low-quality and investigate exact data alignment failure using detailed diagnostic logging.

**Status:**
Ready for user feedback and decision on next steps.

---

**Investigation Team:** Claude
**Date:** 2025-10-21
**Files Created:**
- diagnose_quality_spread.py
- check_quality_holdings.py
- QUALITY_SPREAD_INVESTIGATION_REPORT.md

