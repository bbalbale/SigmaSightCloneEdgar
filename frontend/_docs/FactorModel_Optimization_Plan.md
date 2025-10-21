# Factor Model Optimization Plan - Growth/Value/Momentum Exposures

**Created:** 2025-10-18
**Status:** Planning - Ready for Implementation
**Priority:** High - Stress testing currently producing unreliable results
**Related Docs:** `RiskMetricClaudeConvo.md`, `RiskMetricsPlanning.md`, `RiskMetricsExecution.md`

---

## Executive Summary

**Problem:** Current 7-factor model has severe multicollinearity (VIF > 299), producing unreliable betas and noisy stress testing results.

**Solution:** Implement TWO factor models in parallel, compare outputs, then choose the best approach:
1. **Ridge Regression** - Regularized 7-factor model (keeps current structure) ⭐ **RECOMMENDED FIRST**
2. **Long-Short Spreads** - 4-factor orthogonal model (academically sound) - Phase 2

**Plus:** Add missing Interest Rate sensitivity calculation (required for rate shock scenarios)

**Timeline:**
- Week 1-2: Ridge implementation + IR sensitivity (priority)
- Week 3-4: Spreads implementation (optional comparison)
- Week 5: Decision & production deployment

**Recommendation:** Ship Ridge + IR in production (3 weeks), evaluate Spreads later as v2 enhancement.

---

## Current State Analysis

### What's Implemented Now

**7-Factor Model** (`backend/app/calculations/factors.py`):
```python
FACTOR_ETFS = {
    "Market": "SPY",       # VIF: 299.52 (!!!)
    "Value": "VTV",        # VIF: 51.99
    "Growth": "VUG",       # VIF: 172.50
    "Momentum": "MTUM",
    "Quality": "QUAL",     # VIF: 14.86
    "Size": "IWM",
    "Low Volatility": "USMV"
}
```

**Problems:**
- Market/Growth/Value are 93%+ correlated (overlapping portfolios)
- NVDA beta = -3 (should be +2.12)
- Stress testing produces inconsistent results
- All factor betas are statistically insignificant (high p-values)

**Stress Testing Integration** (`backend/app/config/stress_scenarios.json`):
- 15+ scenarios use Value/Growth/Momentum factors
- Examples: "Value Rotation 20%", "Growth Rally 15%", "Dot-Com Crash" (-60% growth)
- Relies on factor betas for P&L calculation

---

## Approach 1: Ridge Regression (Regularized 7-Factor)

### Mathematical Foundation

**Current OLS:**
```
Position Return = α + β₁(SPY) + β₂(VTV) + β₃(VUG) + ... + ε
```
Problem: SPY/VTV/VUG are too correlated → unstable βs

**Ridge Regression:**
```
Minimize: RSS + α * Σ(βᵢ²)
```
Where α (alpha) is regularization strength

**Effect:**
- Shrinks correlated coefficients toward each other
- Stabilizes betas (no more sign flips)
- Trades some bias for lower variance
- VIF drops from 299 → ~15-20 (tolerable)

### Implementation Details

**File:** `backend/app/calculations/factors_ridge.py` (new)

**Key Functions:**
```python
from sklearn.linear_model import Ridge

async def calculate_factor_betas_ridge(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    alpha: float = 1.0,  # Regularization strength
    use_delta_adjusted: bool = False,
    context: Optional[PortfolioContext] = None
) -> Dict[str, Any]:
    """
    Calculate factor betas using Ridge regression

    Args:
        alpha: Regularization strength (higher = more shrinkage)
               Recommended range: 0.1 to 10.0
               Start with 1.0, tune based on results

    Returns:
        Same structure as calculate_factor_betas_hybrid() but with:
        - 'method': 'RIDGE'
        - 'alpha': regularization parameter used
        - 'ridge_diagnostics': shrinkage metrics
    """
    # Fetch data (reuse existing functions)
    factor_returns = await fetch_factor_returns(...)
    position_returns = await calculate_position_returns(...)

    # Key difference: Use Ridge instead of OLS
    for position_id in position_returns.columns:
        X = factor_returns.values
        y = position_returns[position_id].values

        # Ridge regression
        model = Ridge(alpha=alpha, fit_intercept=True)
        model.fit(X, y)

        # Extract betas
        position_betas[position_id] = {
            factor_name: model.coef_[i]
            for i, factor_name in enumerate(factor_names)
        }

        # Calculate R² (same as OLS R²)
        r_squared = model.score(X, y)
```

**Database Storage:**
- Reuse existing `position_factor_exposures` table
- Add `method` column (if not exists): 'OLS', 'RIDGE', 'SPREAD'
- Add `alpha` column for Ridge: regularization parameter used

**Migration:**
```sql
ALTER TABLE position_factor_exposures
ADD COLUMN method VARCHAR(20) DEFAULT 'OLS',
ADD COLUMN regularization_alpha NUMERIC(10, 4) NULL;

CREATE INDEX idx_pfe_method ON position_factor_exposures(method, calculation_date);
```

### Alpha Parameter Tuning

**Tuning Strategy:**
1. Test alphas: [0.01, 0.1, 1.0, 5.0, 10.0]
2. For each alpha, calculate betas for NVDA, AAPL, SPY
3. Check:
   - NVDA beta > 0 (no sign flip)
   - SPY beta ≈ 1.0 (should be perfect)
   - R² still reasonable (> 0.3)

**Expected Results:**
```python
# Alpha too low (0.01): Still unstable
NVDA: Market=-2.8, Growth=1.2  # Sign flip still happens

# Alpha optimal (1.0): Stable
NVDA: Market=1.75, Growth=0.65, Value=-0.45  # Makes sense

# Alpha too high (10.0): Over-shrunk
NVDA: Market=1.1, Growth=0.1, Value=0.05  # All betas near zero
```

**Recommended:** Start with alpha=1.0, validate on 3 demo portfolios

---

## Approach 2: Long-Short Spread Factors (4-Factor Orthogonal)

### Mathematical Foundation

**Key Insight:**
- SPY = Large cap blend (mix of growth + value)
- VUG = Large cap growth (overlaps heavily with SPY)
- VTV = Large cap value (overlaps heavily with SPY)
- Correlation(SPY, VUG) = 0.93 (too high!)

**Solution: Use Spreads**
```
Growth-Value Spread = VUG returns - VTV returns
```
- Correlation(SPY, VUG-VTV) = 0.30 (much better!)
- Measures pure growth vs value tilt
- Orthogonal to market factor

**New 4-Factor Model:**
```python
FACTOR_SPREADS = {
    "Market": "SPY",
    "Growth-Value": "VUG - VTV",  # Positive = growth tilt
    "Momentum": "MTUM - SPY",      # Excess momentum
    "Size": "IWM - SPY"            # Small cap premium
}
```

**Regression:**
```
Position Return = α + β₁(SPY) + β₂(VUG-VTV) + β₃(MTUM-SPY) + β₄(IWM-SPY) + ε
```

**Properties:**
- VIF < 5 (excellent)
- All factors statistically significant
- Betas are stable (no sign flips)
- Industry standard (Fama-French approach)

### Implementation Details

**File:** `backend/app/calculations/factor_spreads.py` (new)

**Key Functions:**
```python
async def calculate_spread_returns(
    factor_returns: pd.DataFrame
) -> pd.DataFrame:
    """
    Convert factor ETF returns to spread returns

    Input:
        factor_returns with columns: SPY, VUG, VTV, MTUM, IWM, ...

    Output:
        spread_returns with columns:
        - Market (SPY unchanged)
        - Growth-Value (VUG - VTV)
        - Momentum (MTUM - SPY)
        - Size (IWM - SPY)
    """
    spreads = pd.DataFrame(index=factor_returns.index)

    # Market unchanged
    spreads['Market'] = factor_returns['SPY']

    # Spread calculations
    spreads['Growth-Value'] = factor_returns['VUG'] - factor_returns['VTV']
    spreads['Momentum'] = factor_returns['MTUM'] - factor_returns['SPY']
    spreads['Size'] = factor_returns['IWM'] - factor_returns['SPY']

    return spreads


async def calculate_factor_betas_spreads(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    use_delta_adjusted: bool = False,
    context: Optional[PortfolioContext] = None
) -> Dict[str, Any]:
    """
    Calculate factor betas using long-short spread factors

    Returns:
        Same structure as calculate_factor_betas_hybrid() but with:
        - 'method': 'SPREAD'
        - 'spread_definitions': mapping of spread names to components
        - Lower VIF (< 5)
    """
    # Fetch raw factor returns
    raw_factor_returns = await fetch_factor_returns(...)

    # Convert to spreads
    spread_returns = await calculate_spread_returns(raw_factor_returns)

    # OLS regression (no need for Ridge with orthogonal factors)
    for position_id in position_returns.columns:
        X = spread_returns.values
        y = position_returns[position_id].values

        model = sm.OLS(y, sm.add_constant(X)).fit()

        # Extract spread betas
        position_betas[position_id] = {
            'Market': model.params['Market'],
            'Growth-Value': model.params['Growth-Value'],
            'Momentum': model.params['Momentum'],
            'Size': model.params['Size']
        }
```

**Database Storage:**
- Same `position_factor_exposures` table
- `method` = 'SPREAD'
- Factor names: 'Market', 'Growth-Value', 'Momentum', 'Size'

**New Factor Definitions:**
```sql
-- Add new factor definitions
INSERT INTO factor_definitions (name, description, factor_type, calculation_method, etf_proxy)
VALUES
('Growth-Value', 'Growth vs Value spread (VUG - VTV)', 'style', 'SPREAD', 'VUG-VTV'),
('Momentum', 'Momentum premium (MTUM - SPY)', 'style', 'SPREAD', 'MTUM-SPY'),
('Size', 'Size premium (IWM - SPY)', 'style', 'SPREAD', 'IWM-SPY');
```

### Interpreting Spread Betas

**Example: NVDA**
```python
# Ridge 7-factor result:
Market: 1.75, Growth: 0.82, Value: -0.35, ...

# Spread 4-factor result:
Market: 1.73, Growth-Value: +0.85, Momentum: +0.45, Size: -0.10
```

**Translation for users:**
- **Market 1.73**: If market moves 1%, NVDA moves 1.73% (standard beta)
- **Growth-Value +0.85**: If growth outperforms value by 1%, NVDA gains 0.85%
  - Positive = growth stock
  - Negative = value stock
  - Zero = balanced
- **Momentum +0.45**: NVDA follows momentum trends (positive momentum loading)
- **Size -0.10**: Slight large-cap bias (negative small cap exposure)

**Practical meaning:**
> "NVDA is a high-beta growth stock (1.73 market, +0.85 growth tilt) with strong momentum characteristics (+0.45). In a value rotation scenario (growth underperforms value), NVDA would underperform the market by 0.85% for every 1% of growth-value spread reversal."

---

## Stress Testing Integration

### Current Scenario Format (stress_scenarios.json)

```json
"value_rotation_20": {
    "name": "Value Rotation 20%",
    "shocked_factors": {
        "Value": 0.20,
        "Growth": -0.10
    }
}
```

### Translation Layer for Spreads

**File:** `backend/app/calculations/stress_testing_spreads.py` (new)

```python
def translate_scenario_to_spreads(scenario_config: Dict) -> Dict:
    """
    Convert traditional factor shocks to spread-based shocks

    Example:
        Input: {"Value": 0.20, "Growth": -0.10}
        Output: {"Market": 0.0, "Growth-Value": -0.30}

    Logic:
        Growth-Value spread = Growth return - Value return
        If Growth=-10%, Value=+20%, spread = -10% - 20% = -30%
        (Value outperforms growth by 30%)
    """
    shocked = scenario_config.get('shocked_factors', {})
    spread_shocks = {}

    # Market shock (unchanged)
    if 'Market' in shocked:
        spread_shocks['Market'] = shocked['Market']

    # Growth-Value spread
    growth_shock = shocked.get('Growth', 0)
    value_shock = shocked.get('Value', 0)
    if growth_shock != 0 or value_shock != 0:
        spread_shocks['Growth-Value'] = growth_shock - value_shock

    # Momentum spread (if present)
    momentum_shock = shocked.get('Momentum', 0)
    market_shock = shocked.get('Market', 0)
    if momentum_shock != 0:
        spread_shocks['Momentum'] = momentum_shock - market_shock

    # Size spread (if present)
    size_shock = shocked.get('Size', 0)
    if size_shock != 0:
        spread_shocks['Size'] = size_shock - market_shock

    return spread_shocks
```

**Example Translations:**

| Original Scenario | Spread Translation |
|------------------|-------------------|
| Value: +20%, Growth: -10% | Market: 0%, GV Spread: -30% |
| Growth: +15%, Momentum: +10% | Market: 0%, GV: +15%, Mom: +10% |
| Market: -35%, Growth: +15%, Value: -40% | Market: -35%, GV: +55% |

**P&L Calculation (spreads):**
```python
# Traditional (Ridge):
pnl = portfolio_value × beta_growth × growth_shock

# Spread-based:
pnl = portfolio_value × beta_growth_value × spread_shock
```

---

## Interest Rate Sensitivity (Missing Critical Component)

### Current State

**Problem:** Stress testing scenarios include rate shocks ("Rates Up 50bp", "Rate Spike 300bp") but NO actual IR sensitivity calculation exists.

**Evidence:**
- ✅ Database table exists: `position_interest_rate_betas`
- ✅ Stress scenarios reference: `"Interest_Rate": "Treasury_10Y"`
- ❌ No calculation code in `app/calculations/`
- ❌ Likely returning zero IR impact or using placeholder data

### Recommended Approach: Treasury Yield Regression

**Why this method:**
- Standard practice in equity risk management
- Theoretically sound (discount rate effect)
- Easy to interpret ("For 100bp rate rise, position loses X%")
- Works for both stocks and bonds

**Data source:** FRED API (10-year Treasury yield)

**Calculation method:**
```python
# Regress position returns vs daily Treasury yield CHANGES
Position Return = α + β_IR × ΔYield + ε

# Negative beta typical for stocks (rates up → prices down)
# Interpretation: β_IR = -0.25 means:
#   "100bp rate increase → 25% price decline"
```

### Implementation Plan

**File:** `backend/app/calculations/interest_rate_beta.py` (NEW)

**Database:** Use existing `position_interest_rate_betas` table (no migration needed)

**Timeline:** 3-5 days (parallel to Ridge Week 1)

**Integration:** Works with BOTH Ridge and Spread models (independent calculation)

See detailed code below in "Sample IR Calculation Code" section.

---

## Implementation Roadmap

### Week 1: Ridge Regression + IR Sensitivity (Priority)

**Day 1-2: Core Ridge Calculation**
- [ ] Create `backend/app/calculations/factors_ridge.py`
- [ ] Implement `calculate_factor_betas_ridge()`
- [ ] Add database migration for `method` and `alpha` columns
- [ ] Write unit tests with known datasets

**Day 3-4: Alpha Tuning & Validation**
- [ ] Create `backend/scripts/testing/tune_ridge_alpha.py`
- [ ] Test alphas [0.01, 0.1, 1.0, 5.0, 10.0] on 3 demo portfolios
- [ ] Validate NVDA beta is positive and reasonable
- [ ] Document optimal alpha value

**Day 5: Integration & Testing**
- [ ] Update batch orchestrator to run Ridge calculation
- [ ] Store Ridge betas in database with `method='RIDGE'`
- [ ] Verify stress testing works with Ridge betas
- [ ] Compare Ridge vs OLS results

**Deliverable:** Ridge betas stored in database, stress testing functional

---

### Week 2: Spread Factor Implementation

**Day 1-2: Core Spread Calculation**
- [ ] Create `backend/app/calculations/factor_spreads.py`
- [ ] Implement `calculate_spread_returns()`
- [ ] Implement `calculate_factor_betas_spreads()`
- [ ] Add new factor definitions to database

**Day 3-4: Stress Testing Integration**
- [ ] Create `backend/app/calculations/stress_testing_spreads.py`
- [ ] Implement `translate_scenario_to_spreads()`
- [ ] Update stress testing to work with spread betas
- [ ] Test all 15+ scenarios with spread model

**Day 5: Validation**
- [ ] Run spread model on 3 demo portfolios
- [ ] Verify VIF < 5 for all positions
- [ ] Check R² values comparable to Ridge
- [ ] Store spread betas in database with `method='SPREAD'`

**Deliverable:** Spread betas calculated, stress testing works with spreads

---

### Week 3: Comparison & Analysis

**Day 1-2: Comparison Script**
- [ ] Create `backend/scripts/analysis/compare_factor_models.py`
- [ ] Run BOTH models on all demo portfolios
- [ ] Generate comparison report:
  - Beta differences (position-level)
  - Stress testing P&L differences
  - VIF comparison
  - R² comparison
  - Statistical significance

**Day 3-4: Validation Scenarios**
- [ ] Test historical scenarios: COVID crash, Dot-com, 2008
- [ ] Which model better predicts actual outcomes?
- [ ] Check beta stability over time (re-run on different dates)
- [ ] User comprehension testing (which is easier to explain?)

**Day 5: Documentation & Decision**
- [ ] Document findings in comparison report
- [ ] Create recommendation with pros/cons
- [ ] Update stress testing to use chosen model
- [ ] Archive non-chosen implementation

**Deliverable:** Decision on which model to use in production

---

## Comparison Criteria

### Quantitative Metrics

**1. Beta Stability**
- Ridge: Check if NVDA beta stays positive across all portfolios
- Spreads: Check if spread betas have consistent interpretation

**2. Multicollinearity (VIF)**
- Ridge: Target VIF < 20 (acceptable)
- Spreads: Expect VIF < 5 (excellent)

**3. Model Fit (R²)**
- Both should maintain R² > 0.3 for high-beta stocks
- Spreads may have slightly lower R² (fewer factors)

**4. Statistical Significance**
- Ridge: May still have high p-values (correlated factors)
- Spreads: Expect significant coefficients (p < 0.05)

**5. Stress Testing Accuracy**
- Compare predicted vs actual COVID crash impact (-35% market)
- Which model gives more consistent scenario results?

### Qualitative Metrics

**1. Interpretability**
- Ridge: "NVDA has 1.75 market beta, 0.82 growth beta"
- Spreads: "NVDA has 1.73 market beta, +0.85 growth tilt"
- **Which is clearer to users?**

**2. Stress Scenario Mapping**
- Ridge: Direct mapping ("Value +20%")
- Spreads: Requires translation ("Value outperforms growth by 30%")
- **Which is more intuitive?**

**3. Implementation Complexity**
- Ridge: Simple (sklearn Ridge)
- Spreads: Moderate (spread calculation + translation layer)

**4. Maintenance**
- Ridge: Tune alpha parameter over time
- Spreads: More stable (orthogonal factors)

---

## Database Schema Changes

### Migration 1: Add Method Column

```sql
-- File: backend/alembic/versions/XXXX_add_factor_method_column.py
ALTER TABLE position_factor_exposures
ADD COLUMN method VARCHAR(20) DEFAULT 'OLS';

ALTER TABLE factor_exposures
ADD COLUMN method VARCHAR(20) DEFAULT 'OLS';

CREATE INDEX idx_pfe_method ON position_factor_exposures(method, calculation_date);
CREATE INDEX idx_fe_method ON factor_exposures(method, calculation_date);
```

### Migration 2: Add Ridge Parameters

```sql
-- File: backend/alembic/versions/XXXX_add_ridge_parameters.py
ALTER TABLE position_factor_exposures
ADD COLUMN regularization_alpha NUMERIC(10, 4) NULL;

ALTER TABLE factor_exposures
ADD COLUMN regularization_alpha NUMERIC(10, 4) NULL;
```

### Migration 3: Add Spread Factor Definitions

```sql
-- File: backend/alembic/versions/XXXX_add_spread_factors.py
INSERT INTO factor_definitions (id, name, description, factor_type, calculation_method, etf_proxy, display_order)
VALUES
(gen_random_uuid(), 'Growth-Value', 'Growth vs Value spread (VUG - VTV)', 'style', 'SPREAD', 'VUG-VTV', 10),
(gen_random_uuid(), 'Momentum', 'Momentum premium (MTUM - SPY)', 'style', 'SPREAD', 'MTUM-SPY', 11),
(gen_random_uuid(), 'Size', 'Size premium (IWM - SPY)', 'style', 'SPREAD', 'IWM-SPY', 12);
```

---

## Testing Strategy

### Unit Tests

**Ridge Regression:**
```python
# tests/test_factors_ridge.py
async def test_ridge_nvda_beta_positive():
    """NVDA should have positive market beta with Ridge"""
    result = await calculate_factor_betas_ridge(
        db, nvda_portfolio_id, date.today(), alpha=1.0
    )
    nvda_beta = result['position_betas'][nvda_position_id]['Market']
    assert nvda_beta > 0, "NVDA market beta should be positive"
    assert 1.5 < nvda_beta < 2.5, "NVDA beta should be 1.5-2.5"

async def test_ridge_spy_beta_one():
    """SPY should have beta ~1.0"""
    result = await calculate_factor_betas_ridge(...)
    spy_beta = result['position_betas'][spy_position_id]['Market']
    assert 0.95 < spy_beta < 1.05, "SPY beta should be ~1.0"
```

**Spread Factors:**
```python
# tests/test_factor_spreads.py
async def test_spread_vif_low():
    """VIF should be < 5 for all spread factors"""
    result = await calculate_factor_betas_spreads(...)
    vif_values = result['multicollinearity']['vif']
    assert all(vif < 5 for vif in vif_values.values())

async def test_spread_interpretation():
    """Growth-value spread should be interpretable"""
    # Portfolio of 100% VUG should have GV spread ≈ +1
    # Portfolio of 100% VTV should have GV spread ≈ -1
    pass
```

### Integration Tests

**Stress Testing:**
```python
# tests/test_stress_testing_models.py
async def test_value_rotation_ridge():
    """Value rotation should produce consistent P&L with Ridge"""
    result = await calculate_direct_stress_impact(
        db, portfolio_id, value_rotation_scenario, method='RIDGE'
    )
    # Value portfolio should gain, growth portfolio should lose
    assert result['total_direct_pnl'] > 0  # For value-heavy portfolio

async def test_value_rotation_spreads():
    """Same scenario should work with spread factors"""
    result = await calculate_direct_stress_impact(
        db, portfolio_id, value_rotation_scenario, method='SPREAD'
    )
    # Results should be similar to Ridge
    pass
```

---

## Comparison Output Format

**Script:** `backend/scripts/analysis/compare_factor_models.py`

**Output:** `factor_model_comparison_report.txt`

```
========================================
Factor Model Comparison Report
Generated: 2025-10-18
Portfolios: 3 demo portfolios (63 positions)
========================================

SECTION 1: BETA STABILITY
--------------------------
                    Ridge (α=1.0)          Spreads (4-factor)
Position            Market    Growth       Market    GV-Spread
--------            ------    ------       ------    ---------
NVDA                1.75      0.82         1.73      +0.85
AAPL                1.18      0.45         1.16      +0.42
SPY                 1.00      0.00         1.00      0.00
BRK-B               0.45     -0.25         0.47      -0.30

✅ Ridge: All market betas positive
✅ Spreads: Consistent spread interpretation

SECTION 2: MULTICOLLINEARITY (VIF)
-----------------------------------
Ridge (7 factors):
  Market: 18.5 (acceptable, down from 299)
  Growth: 12.3
  Value: 9.8
  Average: 11.2

Spreads (4 factors):
  Market: 1.2 (excellent)
  Growth-Value: 2.8
  Momentum: 3.1
  Average: 2.3

✅ Spreads: Superior VIF scores

SECTION 3: MODEL FIT (R²)
--------------------------
                Ridge         Spreads
NVDA            0.34          0.32
AAPL            0.28          0.26
Tech Portfolio  0.42          0.38

✅ Ridge: Slightly higher R² (more factors)
✅ Spreads: Still acceptable (>0.3)

SECTION 4: STRESS TESTING P&L
------------------------------
Scenario: Value Rotation 20%
Portfolio: Balanced Individual

Ridge Method:
  Direct P&L: -$12,450
  Breakdown: Growth -$15k, Value +$3k

Spread Method:
  Direct P&L: -$11,800
  Breakdown: GV Spread -$11.8k

Difference: $650 (5%)

✅ Both methods produce similar results

SECTION 5: HISTORICAL VALIDATION
---------------------------------
COVID Crash (March 2020): Market -35%
Actual Portfolio Loss: -42%

Ridge Prediction: -38% (error: 4%)
Spread Prediction: -41% (error: 1%)

✅ Spreads: More accurate prediction

SECTION 6: INTERPRETABILITY
----------------------------
User Question: "Is my portfolio growth or value oriented?"

Ridge Answer:
"Your portfolio has growth beta of 0.65 and value beta of -0.35"
User Response: "What does that mean?"

Spread Answer:
"Your portfolio has +0.65 growth tilt (positive = growth oriented)"
User Response: "Clear!"

✅ Spreads: More intuitive

========================================
RECOMMENDATION: [TBD after analysis]
========================================
```

---

## Decision Framework

### If Ridge Wins

**Advantages:**
- Keeps 7-factor structure (familiar)
- Stress scenarios unchanged (no translation)
- Easier database migration (just add alpha column)

**Implementation:**
1. Set alpha = 1.0 as default
2. Update `batch_orchestrator_v2.py` to use Ridge
3. Deprecate OLS method
4. Update frontend to show Ridge betas

### If Spreads Win

**Advantages:**
- Mathematically superior (low VIF)
- More accurate predictions
- Easier for users to understand
- Publishable methodology

**Implementation:**
1. Create spread calculation pipeline
2. Add translation layer for stress scenarios
3. Update factor definitions in database
4. Create frontend tooltips for spread interpretation

### If Both Are Needed

**Use Cases:**
- Ridge: Quick calculations, backward compatibility
- Spreads: Detailed analysis, research, publications

**Implementation:**
- Let batch orchestrator run BOTH
- Store both in database with `method` column
- Frontend shows spreads by default, Ridge available in "Advanced"

---

## Frontend Implications

### Display Changes (Future - Not in Scope Yet)

**Current:**
```
Factor Exposures:
Market Beta: 1.2
Growth Beta: 0.8
Value Beta: -0.3
```

**Ridge (Minimal Change):**
```
Factor Exposures (Regularized):
Market Beta: 1.2
Growth Beta: 0.7
Value Beta: -0.2
ℹ️ Regularization applied to reduce correlation effects
```

**Spreads (New Format):**
```
Factor Exposures:
Market Beta: 1.2
Growth Tilt: +0.75 (Growth-oriented)
Momentum: +0.45 (Following trends)
Size: -0.10 (Large cap bias)

ℹ️ Growth tilt measures growth vs value preference
  Positive = Growth oriented
  Negative = Value oriented
```

---

## Risk Mitigation

### Risks & Mitigations

**Risk 1:** Ridge alpha parameter needs frequent tuning
- **Mitigation:** Add alpha validation to batch process, alert if betas diverge

**Risk 2:** Users don't understand spread interpretation
- **Mitigation:** Add comprehensive tooltips, translation layer in frontend

**Risk 3:** Stress scenario translations are wrong
- **Mitigation:** Extensive unit tests on known scenarios (COVID, Dot-com)

**Risk 4:** Both models give different recommendations
- **Mitigation:** Document differences, let users choose in "Advanced" mode

**Risk 5:** Database grows too large (storing 2x factor exposures)
- **Mitigation:** Deprecate OLS method, only keep Ridge OR Spreads long-term

---

## Success Criteria

**Both Implementations Complete When:**
- ✅ Ridge produces positive NVDA beta (1.5-2.5)
- ✅ Ridge VIF < 20 for all factors
- ✅ Spreads produce VIF < 5 for all factors
- ✅ Stress testing works with both methods
- ✅ Comparison report generated
- ✅ All unit tests pass
- ✅ Documentation complete

**Choose Model When:**
- ✅ Historical validation shows prediction accuracy
- ✅ User comprehension testing complete
- ✅ Team consensus on interpretability vs accuracy tradeoff
- ✅ Production implementation plan finalized

---

## Sample IR Calculation Code

### Complete Implementation

**File:** `backend/app/calculations/interest_rate_beta.py` (NEW)

```python
"""
Interest Rate Sensitivity Calculation
Calculates position-level interest rate beta via regression against Treasury yields
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import statsmodels.api as sm

from app.models.positions import Position
from app.models.market_data import PositionInterestRateBeta, MarketDataCache
from app.core.logging import get_logger

logger = get_logger(__name__)

# Constants
IR_REGRESSION_WINDOW = 90  # Days of data for regression
MIN_IR_OBSERVATIONS = 30   # Minimum observations required
TREASURY_SYMBOL = 'DGS10'  # FRED 10-year Treasury yield symbol


async def fetch_treasury_yields(
    db: AsyncSession,
    start_date: date,
    end_date: date
) -> pd.Series:
    """
    Fetch 10-year Treasury yields from database (FRED data)

    Returns:
        Series with dates as index, yield values (e.g., 0.0425 for 4.25%)
    """
    stmt = select(MarketDataCache).where(
        and_(
            MarketDataCache.symbol == TREASURY_SYMBOL,
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date)

    result = await db.execute(stmt)
    records = result.scalars().all()

    if not records:
        logger.warning(f"No Treasury yield data found for {start_date} to {end_date}")
        return pd.Series()

    # Build Series (use 'close' column for yield value)
    data = {rec.date: float(rec.close) for rec in records}
    yields = pd.Series(data).sort_index()

    logger.info(f"Fetched {len(yields)} days of Treasury yields")
    return yields


async def calculate_position_ir_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    window_days: int = IR_REGRESSION_WINDOW
) -> Dict[str, Any]:
    """
    Calculate interest rate beta for a single position

    Method: OLS regression of position returns vs Treasury yield changes

    Args:
        db: Database session
        position_id: Position UUID
        calculation_date: Date for calculation
        window_days: Lookback window for regression (default 90 days)

    Returns:
        {
            'ir_beta': float,          # Interest rate sensitivity
            'r_squared': float,        # Model fit quality
            'p_value': float,          # Statistical significance
            'observations': int,       # Data points used
            'interpretation': str,     # Human-readable explanation
            'success': bool
        }
    """
    logger.info(f"Calculating IR beta for position {position_id}")

    try:
        # Get position details
        stmt = select(Position).where(Position.id == position_id)
        result = await db.execute(stmt)
        position = result.scalar_one_or_none()

        if not position:
            return {'success': False, 'error': 'Position not found'}

        # Calculate date range
        end_date = calculation_date
        start_date = end_date - timedelta(days=window_days + 30)  # Buffer for trading days

        # Fetch position price data
        price_stmt = select(MarketDataCache).where(
            and_(
                MarketDataCache.symbol == position.symbol,
                MarketDataCache.date >= start_date,
                MarketDataCache.date <= end_date
            )
        ).order_by(MarketDataCache.date)

        price_result = await db.execute(price_stmt)
        price_records = price_result.scalars().all()

        if len(price_records) < MIN_IR_OBSERVATIONS:
            logger.warning(f"Insufficient price data for {position.symbol}: {len(price_records)} days")
            return {'success': False, 'error': 'Insufficient price data'}

        # Build price series
        prices = pd.Series({rec.date: float(rec.close) for rec in price_records}).sort_index()

        # Calculate position returns
        position_returns = prices.pct_change().dropna()

        # Fetch Treasury yields
        yields = await fetch_treasury_yields(db, start_date, end_date)

        if len(yields) < MIN_IR_OBSERVATIONS:
            logger.warning(f"Insufficient Treasury yield data: {len(yields)} days")
            return {'success': False, 'error': 'Insufficient yield data'}

        # Calculate yield CHANGES (basis points per day)
        yield_changes = yields.diff().dropna()

        # Align dates (only use days where both are available)
        common_dates = position_returns.index.intersection(yield_changes.index)

        if len(common_dates) < MIN_IR_OBSERVATIONS:
            logger.warning(f"Insufficient overlapping data: {len(common_dates)} days")
            return {'success': False, 'error': 'Insufficient overlapping data'}

        # Align both series
        y = position_returns.loc[common_dates].values  # Position returns
        X = yield_changes.loc[common_dates].values     # Yield changes

        # OLS Regression
        X_with_const = sm.add_constant(X)
        model = sm.OLS(y, X_with_const).fit()

        # Extract results
        ir_beta = float(model.params[1])  # Coefficient on yield changes
        r_squared = float(model.rsquared)
        p_value = float(model.pvalues[1])

        # Interpretation
        # Beta is typically negative for stocks (rates up → stocks down)
        # Beta units: % return per 1% point (100bp) yield change
        direction = "decreases" if ir_beta < 0 else "increases"
        abs_beta = abs(ir_beta)

        interpretation = (
            f"For every 100bp increase in 10Y Treasury yield, "
            f"position {direction} by {abs_beta:.2%}"
        )

        logger.info(f"IR Beta for {position.symbol}: {ir_beta:.4f} (R²={r_squared:.3f}, p={p_value:.3f})")

        return {
            'success': True,
            'ir_beta': ir_beta,
            'r_squared': r_squared,
            'p_value': p_value,
            'std_error': float(model.bse[1]),
            'observations': len(common_dates),
            'interpretation': interpretation,
            'calculation_date': calculation_date,
            'position_id': str(position_id)
        }

    except Exception as e:
        logger.error(f"Error calculating IR beta for position {position_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


async def calculate_portfolio_ir_betas(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate IR betas for all positions in a portfolio

    Returns:
        {
            'position_betas': {position_id: ir_beta, ...},
            'successful': int,
            'failed': int,
            'portfolio_weighted_beta': float  # Equity-weighted portfolio IR beta
        }
    """
    logger.info(f"Calculating IR betas for portfolio {portfolio_id}")

    # Get all active positions
    stmt = select(Position).where(
        and_(
            Position.portfolio_id == portfolio_id,
            Position.exit_date.is_(None)
        )
    )
    result = await db.execute(stmt)
    positions = result.scalars().all()

    position_betas = {}
    successful = 0
    failed = 0

    for position in positions:
        result = await calculate_position_ir_beta(
            db=db,
            position_id=position.id,
            calculation_date=calculation_date
        )

        if result['success']:
            position_betas[str(position.id)] = result['ir_beta']
            successful += 1

            # Store in database
            await store_ir_beta(db, position.id, calculation_date, result)
        else:
            logger.warning(f"Failed to calculate IR beta for position {position.id}: {result.get('error')}")
            failed += 1

    # Calculate portfolio-weighted IR beta
    portfolio_beta = await calculate_portfolio_weighted_ir_beta(
        db, portfolio_id, position_betas
    )

    await db.commit()

    logger.info(f"Portfolio IR calculation complete: {successful} successful, {failed} failed")

    return {
        'position_betas': position_betas,
        'successful': successful,
        'failed': failed,
        'portfolio_weighted_beta': portfolio_beta
    }


async def store_ir_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    result: Dict[str, Any]
) -> None:
    """Store IR beta in database"""

    # Check if record exists
    stmt = select(PositionInterestRateBeta).where(
        and_(
            PositionInterestRateBeta.position_id == position_id,
            PositionInterestRateBeta.calculation_date == calculation_date
        )
    )
    existing = await db.execute(stmt)
    record = existing.scalar_one_or_none()

    if record:
        # Update existing
        record.ir_beta = Decimal(str(result['ir_beta']))
        record.r_squared = Decimal(str(result['r_squared']))
    else:
        # Create new
        record = PositionInterestRateBeta(
            position_id=position_id,
            calculation_date=calculation_date,
            ir_beta=Decimal(str(result['ir_beta'])),
            r_squared=Decimal(str(result['r_squared'])) if result.get('r_squared') else None
        )
        db.add(record)


async def calculate_portfolio_weighted_ir_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    position_betas: Dict[str, float]
) -> float:
    """
    Calculate equity-weighted portfolio IR beta

    Formula: Σ(position_market_value × position_ir_beta) / portfolio_equity
    """
    from app.models.users import Portfolio

    # Get portfolio equity
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    result = await db.execute(stmt)
    portfolio = result.scalar_one()

    portfolio_equity = float(portfolio.equity_balance)

    if portfolio_equity <= 0:
        return 0.0

    # Get positions with market values
    weighted_sum = 0.0

    for pos_id_str, ir_beta in position_betas.items():
        pos_id = UUID(pos_id_str)
        stmt = select(Position).where(Position.id == pos_id)
        result = await db.execute(stmt)
        position = result.scalar_one()

        if position.market_value:
            market_value = float(position.market_value)
            weighted_sum += market_value * ir_beta

    portfolio_ir_beta = weighted_sum / portfolio_equity

    logger.info(f"Portfolio weighted IR beta: {portfolio_ir_beta:.4f}")

    return portfolio_ir_beta
```

### Integration with Batch Orchestrator

**File:** `backend/app/batch/batch_orchestrator_v2.py`

```python
# Add to run_daily_batch_sequence()

# After factor calculations
logger.info("Step 5: Calculating interest rate sensitivities")
from app.calculations.interest_rate_beta import calculate_portfolio_ir_betas

ir_results = await calculate_portfolio_ir_betas(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=calculation_date
)

results['interest_rate_betas'] = ir_results

logger.info(
    f"IR calculation complete: {ir_results['successful']} positions, "
    f"portfolio IR beta: {ir_results['portfolio_weighted_beta']:.4f}"
)
```

### Integration with Stress Testing

**File:** `backend/app/calculations/stress_testing.py`

```python
# In calculate_direct_stress_impact()

async def get_position_ir_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date
) -> float:
    """Get IR beta from database or return 0"""
    stmt = select(PositionInterestRateBeta).where(
        and_(
            PositionInterestRateBeta.position_id == position_id,
            PositionInterestRateBeta.calculation_date <= calculation_date
        )
    ).order_by(PositionInterestRateBeta.calculation_date.desc()).limit(1)

    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    return float(record.ir_beta) if record else 0.0


# In stress scenario P&L calculation:
if "Interest_Rate" in shocked_factors:
    ir_shock_bp = shocked_factors["Interest_Rate"]  # e.g., 0.01 for 100bp

    for position in positions:
        ir_beta = await get_position_ir_beta(db, position.id, calculation_date)
        position_value = float(position.market_value)

        # P&L = position_value × ir_beta × shock
        # Shock is already in decimal form (0.01 = 100bp = 1% yield change)
        ir_pnl = position_value * ir_beta * ir_shock_bp

        total_pnl += ir_pnl

    logger.info(f"Interest rate shock {ir_shock_bp*100:.0f}bp → P&L: ${total_pnl:,.0f}")
```

---

## Why Ridge + IR is the Right First Step

**1. Speed to Working Product:**
- Ridge: 2 weeks
- IR: 3 days (parallel)
- Total: 2-3 weeks vs 4-5 weeks for Spreads

**2. Risk Mitigation:**
- Ridge fixes 80% of the problem (stabilizes betas)
- Can always enhance to Spreads later
- No user education needed (keep familiar factor names)

**3. Complete Coverage:**
- Equity risk: ✅ Ridge (7 factors)
- Rate risk: ✅ Treasury yield regression
- All stress scenarios: ✅ Functional

**4. Future-Proof:**
- IR calculation works with BOTH Ridge and Spreads
- Database supports multiple methods (`method` column)
- Can run comparison whenever you want

---

## Next Steps

1. **Review this updated plan** - Confirm Ridge + IR approach
2. **Verify Treasury yield data** - Check if FRED 10Y data exists in database
3. **Start Week 1** - Parallel implementation (Ridge + IR)
4. **Test on rate-sensitive positions** - Verify IR betas make sense (REITs, utilities, bonds)
5. **Decision point (Week 3)** - Ship Ridge+IR to production, or continue with Spreads comparison

---

**Questions? Concerns? Adjustments needed?**
Ready to begin implementation when you approve this plan.
