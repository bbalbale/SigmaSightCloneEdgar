# Factor Beta Redesign (Phase 2.6.8)

Status: Proposed — Awaiting Review
Last Updated: 2025-08-09 (local time)
Owners: Risk/Analytics

---

## 1. Summary

Observed unrealistic portfolio factor betas (e.g., Market betas near ±3 and frequent capping). Root cause is upstream beta estimation combined with severe multicollinearity in factor ETFs (correlations up to 0.96, VIF values > 50). This document proposes an improved univariate regression approach with better data handling to produce stable, realistic factor betas while avoiding the numerical instability of multivariate methods.

Key points:
- **Recommended approach**: Improved univariate regression with data quality enhancements (no zero-fill, winsorization, mandatory delta adjustment for options)
- **Why not multivariate**: Severe multicollinearity (condition number 640+) makes multivariate regression numerically unstable without regularization
- Position-level attribution for factor dollar exposures in `aggregate_portfolio_factor_exposures()` is correct and should remain as-is
- Stress testing P&L uses `FactorExposure.exposure_value` (portfolio-level beta), not `exposure_dollar`
- Notional and delta-adjusted exposures are independent of factor betas and remain unaffected

Plain-English quick primer (what the terms mean):
- Beta: how sensitive a position/portfolio is to a risk factor. Beta = 1 to “Market” means if the market moves +1%, we expect about +1% move in the position (on average).
- Returns used in regressions: percentage daily changes (e.g., 0.01 = 1%), not dollars.
- OLS regression: a statistical fit that finds the line best explaining position returns from factor returns. “Univariate” = one factor at a time; “multivariate” = all factors together.
- Delta (for options): how much an option price changes when the underlying moves. Using delta-adjusted returns can make option-vs-factor relationships less noisy.
- NaN vs zero: missing data (NaN) should usually be dropped/aligned, not turned into zeros, which can bias results.

Do not implement until this plan is reviewed and approved.

---

## 2. Current Implementation (Relevant Code)

- `app/calculations/factors.py::calculate_factor_betas_hybrid()`
  - Per-position, per-factor univariate OLS regressions with intercept.
  - Capping betas at ±`BETA_CAP_LIMIT` (currently 3).
  - Uses position return series derived from exposure %. For options, delta adjustment is optional (default False).
  - Plain-English: “Univariate” means we fit one factor at a time. This is simple but can over-attribute risk to whichever factor looks strongest if factors move together. The cap is a safety net to prevent extreme numbers when data is noisy.
- `app/calculations/factors.py::calculate_position_returns()`
  - Builds a time series of exposure per position using price × quantity × multiplier; for options, optionally multiplies by delta.
  - Computes returns via `.pct_change()`; currently fills missing values with zeros.
- `app/calculations/factors.py::aggregate_portfolio_factor_exposures()` and `_aggregate_portfolio_betas()`
  - Correct position-level attribution for factor dollar exposures and exposure-weighted portfolio betas.
- `app/calculations/market_data.py::fetch_historical_prices()`
  - Provides close price histories; factor returns computed as decimal daily returns via `.pct_change()`.

---

## 3. Legacy Reference: Methods and Differences vs Current

This section summarizes the legacy reference scripts in
`backend/_docs/requirements/legacy_scripts_for_reference_only/legacy_analytics_for_reference/`
and contrasts them with the current SigmaSight implementation.

3.1) Legacy data and returns
- __Function__: `get_data.py::calculate_daily_returns()`
- __Method__: Uses NYSE trading calendar to step to the previous valid trading day; computes price-based daily returns per ticker as `close / prev_close - 1`.
- __Handling__: If no previous close, sets `NaN` (no zero-fill). Output columns are per-ticker return series (e.g., `SPY_ret`).

3.2) Legacy beta estimation
  - __Portfolio-level style betas__: `get_data.py::calculate_betas()` runs multivariate OLS via `statsmodels` with an intercept: predictors = factor return columns, dependent = portfolio return (last column). Betas taken from `model.params[1:]`.
  - __Position-level betas__: `factors_utils.py::calculate_position_betas()` merges long-form factor and position returns; sets
   `factor_rf = factor_return - mean(factor_return by factor)` and
   `position_rf = position_return - mean(factor_return by position)` (as coded), then computes
   `beta = cov(position_rf, factor_rf) / var(factor_rf)` via grouped covariance and variance.
   Note: The `position_rf` construction appears inconsistent (uses factor returns’ mean rather than position returns’ mean); and the covariance-ratio is per-factor (univariate), susceptible to omitted-variable bias.

3.3) Legacy factor covariance/correlation and VaR
- __Covariance__: `var_utils.py::covariance_matrix()` uses `factor_returns.cov()`.
- __Exponential-decay covariance__: `var_utils.py::decay_covariance_matrix()` applies a 0.94 decay schedule before `cov()`.
- __Correlation__: `var_utils.py::correlation_matrix()` computes `factor_returns.corr()` and maps to factor names.
 - __VaR (matrix form)__: `var_utils.py::multiply_matrices()` computes
  `sqrt( exposure^T · betas · covariance · betas^T )`, i.e., a classic factor-model VaR.
  - Why this matters: this formula says total portfolio risk comes from how big your exposures are, how sensitive they are to factors (betas), and how those factors co-move (covariance).
 
  Plain-English: what these tools mean
  - Covariance vs correlation: covariance measures co-movement in units of returns; correlation is the unitless, scaled version of covariance in [-1, 1].
  - Exponentially decayed covariance: puts more weight on recent data to reflect current market regimes while still using history.
  - Matrix VaR: uses betas and the factor covariance matrix to turn exposures into a single probabilistic risk number (e.g., 95%/99% VaR). Diversification is naturally captured via off-diagonal covariances.
 
  Current system vs proposed redesign
  - We keep the existing correlation-based stress testing (exponentially weighted correlation with caps) and do not enable matrix VaR in this redesign.
  - The redesign focuses on improving betas (section 7), which will feed cleaner inputs into the same stress engine.
 
  Impact of not using matrix VaR now
  - Pros: simpler stakeholder communication; less sensitivity to noisy covariance estimation while we stabilize betas.
  - Cons: no single-number probabilistic risk metric or marginal risk contributions until matrix VaR is (re)introduced.
 
  Future addition (out of scope here)
  - After betas stabilize, we can add matrix VaR by reusing the legacy simple/decayed covariance patterns and matrix multiplication path alongside stress testing.

3.4) Legacy conventions and libraries
- __Missing data__: Preserves `NaN` rather than imputing zeros prior to regression.
- __Regression library__: `statsmodels` OLS.
- __Computation__: Primarily on-demand; no explicit caching visible.
  - Why this matters: treating missing data as “0% return” falsely implies no movement occurred; keeping `NaN` and aligning/dropping missing rows avoids systematic bias.

3.5) Comparison vs Recommended Redesign
- 3.5.1 __Returns__
  - Legacy: price-based returns per ticker; preserves `NaN`.
  - Current: exposure-based position returns via `calculate_position_returns()` using `.pct_change()` on exposure time series; currently zero-fills missing values.
  - **Redesign (Improved Univariate)**: remove zero-fill; inner-join with factor returns and drop `NaN`; default delta-adjusted path for options.
  - Plain-English: zero-filling is like pretending we had a flat return on missing days, which can artificially shrink or distort relationships. Dropping missing rows keeps analysis to days when both series exist.
- 3.5.2 __Betas__
  - Legacy: portfolio-level multivariate OLS; position-level per-factor covariance ratio (univariate with respect to each factor).
  - Current: univariate OLS per factor per position with hard cap ±`BETA_CAP_LIMIT`.
  - **Redesign (Improved Univariate)**: Keep univariate OLS but with quality improvements - winsorization instead of hard caps, better data alignment, mandatory delta adjustment for options. Accept omitted variable bias as trade-off for stability given severe multicollinearity.
- 3.5.3 __Missing data & quality__
  - Legacy: no zero-fill; fewer implicit biases from imputation.
  - Current: zero-fill introduces bias; warnings observed; many betas hit caps.
  - **Redesign**: enforce `MIN_REGRESSION_DAYS`, preserve `NaN` by inner-join and drop, store diagnostics (R², p-values, std err).
- 3.5.4 __Covariance/Correlation & VaR/Stress__
  - Legacy: provides simple and decayed covariance matrices and a VaR matrix multiplication routine.
  - Current: stress testing uses an exponentially weighted correlation matrix and scenario impacts; factor betas (`FactorExposure.exposure_value`) drive P&L, dollar exposures are reporting-only.
  - **Redesign**: no change to stress testing mechanics; improved betas should yield more realistic scenario P&L.
- 3.5.5 __Aggregation & usage__
  - Legacy: matrix-based VaR uses exposures × betas × covariances.
  - Current: Option B position-level attribution for factor dollar exposures is in place and correct; stress uses portfolio betas.
  - **Redesign**: preserve existing storage and attribution paths; only change beta estimation pipeline.

3.6) Legacy Implementation Insight
 - Discovery: The legacy system used a mixed approach - multivariate for portfolio-level betas but univariate (covariance method) for position-level betas.
 - Interpretation: The legacy developers likely recognized multicollinearity issues and avoided them at the position level.
 - **Our approach**: Given empirical evidence of severe multicollinearity (VIF > 50, condition number 640+), we adopt improved univariate regression as the pragmatic solution, similar to the legacy position-level approach but with better data handling.


## 4. (unused)
---

## 5. Problems Observed

### 5.1 Critical Discovery: Severe Multicollinearity (2025-01-10)

Investigation of the factor ETFs revealed extreme multicollinearity:
- **Factor correlations**: Up to 0.96 (Size vs Value), with 17 pairs having |r| > 0.7
- **VIF values**: Quality (39.0), Growth (27.4), Value (19.6), Size (18.8) - all indicating severe multicollinearity
- **Condition number**: 644.86 indicating numerical instability
- **Impact**: Standard multivariate OLS produces MORE extreme betas than univariate due to this multicollinearity
- **Root cause**: Factor ETFs have overlapping holdings and similar market exposures (all US equity-based)

This discovery validates keeping univariate regression - it avoids multicollinearity-induced instability entirely.

### 5.2 Current Implementation Issues

- **Data quality**: Zero-filling returns distorts variance/covariance and biases regressions
- **Options handling**: Option-price returns (high variance) vs factor ETF returns (lower variance) yield oversized slopes without delta adjustment
- **Hard caps**: Frequent beta truncation at ±3 indicates underlying estimation problems
- **Insufficient data handling**: No minimum data requirements lead to unstable fits

Plain-English: why these problems matter
- Zero-filling is like pretending nothing happened on missing days; this artificially reduces volatility and correlations
- Options can swing 10x more than their underlying; without delta adjustment, regressions capture noise not signal
- Hard caps hide the problem but don't fix it; we need better estimation not just truncation
- With too few data points, statistical fits become unreliable gambling

---

## 6. Design Goals

- Produce realistic, stable factor betas at the position and portfolio levels.
- Use appropriately scaled, comparable daily return series for regressions.
- Be robust to missing data without biasing estimates.
- Preserve existing interfaces: continue storing position-level and portfolio-level betas, with factor dollar exposures computed from position-level attribution.
- Ensure downstream stress testing remains correct (P&L uses betas, not dollar exposures).

Plain-English: what “stable and realistic” looks like
- Fewer extreme betas pinned at the cap; most equity betas near sensible ranges (e.g., around 1 vs “Market”, unless hedged or special cases).
- Better model fit diagnostics (higher R² where appropriate, reasonable p-values), indicating factors explain position moves without overfitting.
- Consistent results across adjacent days; small changes in inputs don’t swing betas wildly.

---

## 7. Proposed Redesign: Improved Univariate Regression

### 7.1 Primary Approach: Enhanced Univariate with Data Quality Improvements
    
**Core Design**: Keep univariate regression (one factor at a time) to avoid multicollinearity-induced numerical instability entirely.

**Key Improvements**:
- **Remove zero-filling**: Preserve NaN values and handle via proper alignment
- **Better data alignment**: Inner-join position and factor returns, drop NaN rows
- **Winsorization instead of hard caps**: Apply 1st/99th percentile winsorization on final betas
- **Mandatory delta adjustment for options**: Enforce `use_delta_adjusted=True` for all options positions
- **Minimum data requirements**: Enforce `MIN_REGRESSION_DAYS` (60 days) for reliable estimates
- **Quality diagnostics**: Store R², p-values, standard errors for each regression

**Rationale**: Given severe multicollinearity (correlations > 0.95, VIF > 30, condition number 645), univariate regression is the most stable approach. We accept some omitted variable bias as a reasonable trade-off for numerical stability and interpretability.

### 7.2 Return Computation Improvements
- Compute position returns on prices directly: `prices.pct_change()`
- Under constant quantity/multiplier, `pct_change(price × constant) == pct_change(price)`
- Remove zero-filling from return series completely
- Handle NaN via inner-join with factor returns and drop missing rows before regression
- Plain-English: Only use days where both position and factor data exist; no artificial "flat" days

### 7.3 Delta Adjustment for Options (Mandatory)
- In `calculate_factor_betas_hybrid()`, enforce `use_delta_adjusted=True` for all options
- No per-portfolio override in this phase
- Fallback to dollar exposure when delta unavailable, but mark as low-quality
- Future enhancement: construct exposure series from underlying price × delta × multiplier × quantity
- Plain-English: Options move as scaled versions of their underlying; delta captures this scaling

### 7.4 Alternative Approaches (Not Recommended Due to Multicollinearity)

**Multivariate OLS (Original Proposal - Now Rejected)**
- Would fit all factors simultaneously to remove omitted variable bias
- Testing revealed this produces MORE extreme betas due to multicollinearity
- Condition number 645 indicates severe numerical instability
- Not viable without regularization

**Ridge Regression (Future Enhancement)**
- L2 regularization could handle multicollinearity
- Requires tuning regularization parameter (alpha)
- More complex to implement and explain
- Consider as Phase 2 enhancement after stabilizing with univariate

**Other Regularization Methods**
- Principal Component Regression: transforms to orthogonal space but loses interpretability
- Elastic Net: combines L1/L2 but adds complexity
- LASSO: feature selection but unstable with correlated predictors

### 7.5 Missing Data Handling and Alignment
- Remove zero-filling of returns completely
- For each position, inner-join position returns with factor returns
- Drop rows with NaNs prior to regression
- Enforce `MIN_REGRESSION_DAYS` (60 days minimum)
- If insufficient data: skip regression, set betas to 0, mark as low-quality
- Plain-English: Only use overlapping clean data; require sufficient history for reliability

### 7.6 Quality Controls and Outlier Handling
- Replace hard ±3 cap with winsorization at 1st/99th percentiles
- Check regression quality metrics: R², p-values, standard errors
- Log and alert on extreme values post-winsorization
- No emergency caps - rely on winsorization and quality checks
- Plain-English: Use statistical methods not arbitrary cutoffs; preserve information about extremes

### 7.7 Diagnostics, Logging, and Observability
- Persist regression statistics per position:
  - R² (goodness of fit)
  - p-values (statistical significance)
  - Standard errors (uncertainty bounds)
  - Sample size used
- Generate analysis reports:
  - Beta distributions before/after redesign
  - R² distribution across positions
  - Count of outliers beyond winsorization thresholds
- Plain-English: Track everything to prove improvements and catch issues early

### 7.8 Storage and Downstream Usage
    - Continue storing position-level betas and portfolio-level betas as currently done.
    - Factor dollar exposures remain position-level contributions: sum(position signed dollar exposure × position beta) — unchanged.
    - Stress testing continues to use `FactorExposure.exposure_value` (beta) for P&L; `exposure_dollar` remains reporting-only.

---

## 8. Implementation Plan

The detailed implementation plan, including the task list and progress, is tracked in the main project `TODO2.md` file under **Phase 2.7: Factor Beta Redesign**.

This document will remain the source of truth for the *design*, while `TODO2.md` is the source of truth for the *execution*.

---

## 9. Acceptance Criteria

- No betas truncated by a hard cap; outliers beyond winsorization thresholds are near-zero (target: ~0%).
- Market betas for equities mostly within [-1.5, 1.5]; options may extend but with significantly fewer extreme values.
- Improved R² distribution; reduction in regression warnings.
- Factor dollar exposures no longer each claim ~90% of gross exposure; more reasonable splits by factor.
- Stress test scenario impacts become more realistic without code changes in stress testing modules.

---

## 10. Non-Goals / Out of Scope

- Redesign of factor dollar exposure attribution (already corrected by Option B).
- Changes to notional or delta-adjusted exposure calculations (remain independent and correct).
- Database schema changes; continue using existing `PositionFactorExposure` and `FactorExposure` records.

---

## 11. Risks and Mitigations

- **Omitted variable bias from univariate** → Accept as trade-off for stability; multicollinearity makes multivariate worse not better
- **Data sparsity for some symbols** → Enforce MIN_REGRESSION_DAYS (60); mark low-quality when insufficient
- **Options noise even with delta adjustment** → Future: use underlying price × delta for exposure series
- **Continued beta inflation for correlated moves** → Monitor via diagnostics; consider Ridge regression in Phase 2

---

## 12. Decisions

- **Regression approach**: **Improved Univariate Regression** (avoiding multicollinearity-induced instability)
  - Keep univariate OLS to avoid numerical problems from factor correlations > 0.95
  - Focus on data quality: remove zero-fill, proper NaN handling, mandatory delta adjustment
  - Winsorization instead of hard caps
  - Ridge regression deferred to future enhancement
- **Delta-adjustment**: **Mandatory for all options** - no exceptions or per-portfolio overrides
- **Data requirements**: **Minimum 60 days** of overlapping data for regression
- **Outlier handling**: **Winsorization at 1st/99th percentiles** - no hard emergency caps
- **Diagnostics**: **Comprehensive tracking** - R², p-values, standard errors, sample sizes for all regressions

---

## 13. References

- `app/calculations/factors.py`
- `app/calculations/market_data.py`
- `backend/_docs/requirements/FACTOR_EXPOSURE_REDESIGN.md`

---

## Appendix A: Empirical Evidence of Factor ETF Multicollinearity

### A.1 Factor Correlation Matrix

The following correlation matrix was calculated from 204 days of historical returns (2024-06-19 to 2025-01-10) for the seven factor ETFs used in our factor model. Values show Pearson correlation coefficients.

| Factor | Market (SPY) | Value (VTV) | Growth (VUG) | Momentum (MTUM) | Quality (QUAL) | Size (SIZE) | Low Vol (USMV) |
|--------|-------------|------------|--------------|-----------------|----------------|-------------|----------------|
| **Market (SPY)** | 1.000 | 0.664 | 0.727 | 0.699 | 0.735 | 0.704 | 0.586 |
| **Value (VTV)** | 0.664 | 1.000 | 0.759 | 0.826 | 0.897 | **0.954** | 0.907 |
| **Growth (VUG)** | 0.727 | 0.759 | 1.000 | 0.921 | **0.942** | 0.847 | 0.658 |
| **Momentum (MTUM)** | 0.699 | 0.826 | 0.921 | 1.000 | 0.909 | 0.872 | 0.735 |
| **Quality (QUAL)** | 0.735 | 0.897 | **0.942** | 0.909 | 1.000 | **0.937** | 0.829 |
| **Size (SIZE)** | 0.704 | **0.954** | 0.847 | 0.872 | **0.937** | 1.000 | 0.857 |
| **Low Vol (USMV)** | 0.586 | 0.907 | 0.658 | 0.735 | 0.829 | 0.857 | 1.000 |

**Key Observations:**
- **17 out of 21 pairs** have correlations > 0.7 (highlighted values > 0.9 in bold)
- **Highest correlation**: Value-Size at 0.954
- **Average pairwise correlation**: 0.81 (excluding diagonal)
- Market (SPY) has the lowest average correlation with others, yet still > 0.58 with all factors

### A.2 Variance Inflation Factor (VIF) Analysis

VIF measures how much the variance of a regression coefficient increases due to multicollinearity. Values > 10 indicate problematic multicollinearity.

| Factor | VIF | Interpretation |
|--------|-----|----------------|
| Market (SPY) | 2.26 | Low multicollinearity |
| Value (VTV) | 19.63 | **High multicollinearity** |
| Growth (VUG) | 27.45 | **High multicollinearity** |
| Momentum (MTUM) | 9.53 | Moderate multicollinearity |
| Quality (QUAL) | **39.04** | **Severe multicollinearity** |
| Size (SIZE) | 18.77 | **High multicollinearity** |
| Low Volatility (USMV) | 7.28 | Moderate multicollinearity |

**Condition Number**: 644.86 (severe multicollinearity; values > 100 indicate problems)

### A.3 Implications for Beta Estimation

This empirical evidence demonstrates why multivariate regression fails for our factor model:

1. **Numerical Instability**: With condition number > 600, the regression matrix is nearly singular
2. **Coefficient Explosion**: High VIF values mean small data changes cause large beta swings
3. **Sign Reversals**: Multicollinearity can cause economically meaningless negative betas
4. **Overfitting**: The model fits noise rather than true relationships

The improved univariate approach avoids these issues entirely by estimating each factor's beta independently, accepting some omitted variable bias as a reasonable trade-off for numerical stability and interpretability.

### A.4 Data Source and Methodology

- **Data Period**: 2024-06-19 to 2025-01-10 (204 trading days)
- **Source**: Market data cache from FMP API
- **Returns Calculation**: Daily percentage change using pandas `pct_change()`
- **Correlation Method**: Pearson correlation on aligned return series
- **VIF Calculation**: Standard VIF formula using statsmodels
- **Export Script**: `scripts/export_factor_etf_data.py`
