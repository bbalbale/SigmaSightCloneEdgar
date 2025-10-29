# Risk Metrics System - Planning & Implementation

**Created:** 2025-10-15
**Status:** Planning Phase
**Priority:** High - Current factor beta calculations are unreliable due to severe multicollinearity

---

## Executive Summary

**Problem Identified:**
- Current 7-factor model has severe multicollinearity (VIF > 299 for Market factor)
- Market beta showing -3 for NVDA (should be +2.12)
- All factor betas are statistically insignificant and unreliable
- Root cause: Factor ETFs (SPY, VUG, VTV, QUAL) are 93%+ correlated

**Solution Approach:**
Replace complex 7-factor model with practical, investor-focused risk analytics:

**Phase 1 - Core Risk Metrics (For All Users):**
1. Market beta (single factor, mathematically sound)
2. Sector exposure analysis (vs S&P 500 benchmark)
3. Concentration metrics (HHI, Top N positions)
4. Stress scenario testing (market moves, sector shocks)

**Phase 2 - Enhanced Analytics:**
5. Volatility forecasting (realized + expected)
6. Downside risk metrics (semi-deviation, max drawdown)
7. Historical scenario analysis (2008, 2020, etc.)

**Phase 3+ - Advanced (Optional, User-Driven):**
8. 3-factor model IF users request it (Market + Style Spreads)
9. Vol-of-vol risk metrics

**Philosophy:** Start simple and useful. Add complexity only if users demand it.

---

## Phase 0: Fix Market Beta (CRITICAL)

### Problem
- Multivariate regression with 7 highly correlated factors producing garbage betas
- VIF diagnostics show severe multicollinearity:
  - Market (SPY): VIF = 299.52 (!!!!)
  - Growth (VUG): VIF = 172.50
  - Value (VTV): VIF = 51.99
  - Quality (QUAL): VIF = 14.86

### Solution Options

#### Option A: Single Market Beta Calculation (SIMPLEST) ⭐ RECOMMENDED
**What:** Calculate market beta using simple univariate regression
```
Position Return = α + β × Market Return + ε
```

**Pros:**
- No multicollinearity (single factor)
- Mathematically sound
- Easy to explain to investors
- Matches how market beta is typically calculated

**Cons:**
- Doesn't capture style tilts (value/growth)
- "Omitted variable bias" if position has strong style exposure

**Implementation:**
- Separate script: `calculate_market_beta.py`
- Input: Position returns + SPY returns
- Output: Single beta per position
- Store in: `position_market_beta` table (new)

#### Option B: 3-Factor Model (Market + 2 Spreads)
**What:** Use long-short factors to reduce correlation
```
Factors:
1. Market = SPY returns
2. Value-Growth Spread = VTV - VUG
3. Size Spread = IWM - SPY
```

**Pros:**
- Lower multicollinearity (expect VIF < 5)
- Captures style tilts
- More academically sound

**Cons:**
- More complex
- Style factors may not be intuitive to investors
- Still need to transform for display

**Decision Point:** Which approach?

---

## Phase 1: Core Risk Metrics

### 1.1 Market Beta
**Status:** BROKEN - needs immediate fix

**Current Issues:**
- File: `backend/app/calculations/factors.py`
- Function: `calculate_factor_betas_hybrid()`
- Uses 7-factor multivariate regression
- Produces unreliable betas due to multicollinearity

**Proposed Changes:**

**Script Organization:**
```
backend/app/calculations/
├── market_beta.py          [NEW] Single market beta calculation
├── sector_analysis.py      [NEW] Sector exposure & concentration
├── volatility_analysis.py  [NEW] Vol forecasting (Phase 2)
└── factors.py             [DEPRECATE or simplify to 3 factors]
```

**New Script: `market_beta.py`**
```python
async def calculate_position_market_beta(
    db: AsyncSession,
    position_id: UUID,
    calculation_date: date,
    window_days: int = 90
) -> Dict[str, Any]:
    """
    Calculate single market beta vs SPY using OLS regression.

    Returns:
        {
            'beta': float,
            'r_squared': float,
            'std_error': float,
            'p_value': float,
            'observations': int
        }
    """
    # Fetch position returns + SPY returns
    # Run simple OLS: position_return ~ spy_return
    # Return beta with diagnostics
```

**Database Storage:**

**Option A: New table `position_market_beta`**
```sql
CREATE TABLE position_market_beta (
    id UUID PRIMARY KEY,
    position_id UUID REFERENCES positions(id),
    calculation_date DATE NOT NULL,
    beta NUMERIC(10, 4),
    r_squared NUMERIC(10, 4),
    std_error NUMERIC(10, 4),
    p_value NUMERIC(10, 4),
    observations INT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Option B: Add to `portfolio_snapshots`**
- Store aggregated portfolio beta only
- Don't store position-level betas separately
- Simpler schema, less granularity

**Portfolio Beta Calculation:**

**Method 1: Equity-Weighted Average (Current)**
```
Portfolio Beta = Σ(position_market_value_i × position_beta_i) / portfolio_equity
```

**Method 2: Direct Regression (Alternative)**
```
Calculate portfolio daily returns = Σ(position_i returns × weight_i)
Regress portfolio returns ~ SPY returns
Get single portfolio beta
```

**Question:** Do we need BOTH methods?
- Method 1: Shows how individual positions contribute
- Method 2: More accurate for actual portfolio behavior (accounts for rebalancing)
- Consensus: Start with Method 1 (need ~90 days of data for Method 2)

**Alembic Migration:**
```bash
# Create migration
alembic revision --autogenerate -m "add_position_market_beta_table"

# Or if adding to snapshots:
alembic revision --autogenerate -m "add_market_beta_to_snapshots"
```

### 1.2 Sector Exposure Analysis

**What to Calculate:**

1. **Portfolio Sector Weights**
   ```
   Tech Weight = Σ(Tech position values) / Total portfolio value
   ```

2. **S&P 500 Benchmark Weights** (Static Reference)
   ```
   Tech (XLK): ~28%
   Healthcare (XLV): ~13%
   Financials (XLF): ~13%
   Consumer Discretionary (XLY): ~10%
   Industrials (XLI): ~8%
   Communication (XLC): ~8%
   Consumer Staples (XLP): ~6%
   Energy (XLE): ~4%
   Utilities (XLU): ~3%
   Real Estate (XLRE): ~2%
   Materials (XLB): ~2%
   ```

3. **Over/Underweight**
   ```
   Tech Overweight = Portfolio Tech % - S&P 500 Tech %
   ```

**Data Source:**
- Position sectors: `market_data_cache.sector` (already have this!)
- Validate: Check if all positions have sector assigned
- Fallback: Use GICS sector classification API if missing

**Script: `sector_analysis.py`**
```python
async def calculate_sector_exposure(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate sector exposure vs S&P 500 benchmark.

    Returns:
        {
            'portfolio_weights': {'Technology': 0.45, 'Healthcare': 0.15, ...},
            'benchmark_weights': {'Technology': 0.28, 'Healthcare': 0.13, ...},
            'over_underweight': {'Technology': 0.17, 'Healthcare': 0.02, ...},
            'largest_overweight': 'Technology',
            'largest_underweight': 'Energy'
        }
    """
```

**Database Storage:**

**Option A: New table `portfolio_sector_exposure`**
```sql
CREATE TABLE portfolio_sector_exposure (
    id UUID PRIMARY KEY,
    portfolio_id UUID REFERENCES portfolios(id),
    calculation_date DATE NOT NULL,
    sector VARCHAR(50) NOT NULL,
    portfolio_weight NUMERIC(10, 4),
    benchmark_weight NUMERIC(10, 4),
    over_underweight NUMERIC(10, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(portfolio_id, calculation_date, sector)
);
```

**Option B: JSON column in `portfolio_snapshots`**
```sql
ALTER TABLE portfolio_snapshots
ADD COLUMN sector_exposure JSONB;

-- Example data:
{
  "Technology": {"portfolio": 0.45, "benchmark": 0.28, "diff": 0.17},
  "Healthcare": {"portfolio": 0.15, "benchmark": 0.13, "diff": 0.02}
}
```

**Recommendation:** Separate table (Option A) for easier querying/filtering

### 1.3 Concentration Metrics

**What to Calculate:**

1. **Herfindahl-Hirschman Index (HHI)**
   ```
   HHI = Σ(weight_i²) × 10,000

   Where weight_i = position_value_i / portfolio_value

   Interpretation:
   - 10,000 = single position (max concentration)
   - 1,000 = 10 equal positions
   - 100 = 100 equal positions (highly diversified)
   ```

2. **Effective Number of Positions**
   ```
   N_effective = 10,000 / HHI

   Interpretation:
   - Portfolio "acts like" N_effective equal-sized positions
   ```

3. **Top-N Concentration**
   ```
   Top 3 = % of portfolio in 3 largest positions
   Top 10 = % of portfolio in 10 largest positions
   ```

**Database Storage:**

Add to `portfolio_snapshots` table:
```sql
ALTER TABLE portfolio_snapshots
ADD COLUMN hhi NUMERIC(10, 2),
ADD COLUMN effective_num_positions NUMERIC(10, 2),
ADD COLUMN top_3_concentration NUMERIC(10, 4),
ADD COLUMN top_10_concentration NUMERIC(10, 4);
```

**Alembic Migration:**
```bash
alembic revision -m "add_concentration_metrics_to_snapshots"
```

---

## Phase 2: Volatility Analysis

### 2.1 Current (Realized) Volatility

**What:** Calculate historical volatility from recent price movements

**Standard Windows:**
- 21-day (1 month)
- 63-day (3 months)
- 252-day (1 year)

**Formula:**
```python
# Daily returns
returns = prices.pct_change()

# 21-day volatility (annualized)
vol_21d = returns.rolling(21).std() * np.sqrt(252)
```

**Libraries:**
- Pure pandas/numpy (no external library needed)
- `pandas_ta` if want more indicators

**Data Points Needed:**
- Minimum: 21 days for 1-month vol
- Recommended: 252 days (1 year) for longer-term analysis

**Position-Level vs Portfolio-Level:**

**Position-Level:**
```python
# Calculate for each position
position_vol = position_returns.rolling(21).std() * np.sqrt(252)
```

**Portfolio-Level:**
```python
# Method 1: Weighted average (WRONG - ignores correlations!)
portfolio_vol = Σ(weight_i × vol_i)  # DON'T USE

# Method 2: Portfolio return volatility (CORRECT)
portfolio_returns = Σ(weight_i × return_i)  # Daily portfolio returns
portfolio_vol = portfolio_returns.rolling(21).std() * np.sqrt(252)
```

**Key Point:** Portfolio volatility ≠ weighted average of position volatilities
- Must account for correlations
- Calculate portfolio returns first, then volatility

### 2.2 Expected (Forecasted) Volatility

**Option A: Simple Moving Average (Baseline)**
```python
# Forecast = average of recent volatilities
expected_vol = vol_21d.rolling(5).mean()
```

**Option B: EWMA (Exponentially Weighted Moving Average)**
```python
# More weight on recent observations
expected_vol = returns.ewm(span=21).std() * np.sqrt(252)
```

**Option C: HAR Model (Best Practice)**
```python
# Heterogeneous Autoregressive Model
# Forecasts based on daily, weekly, monthly volatility

from sklearn.linear_model import LinearRegression

# Calculate realized volatility at different horizons
RV_daily = returns.rolling(1).std()
RV_weekly = returns.rolling(5).std()
RV_monthly = returns.rolling(21).std()

# Regression
X = pd.DataFrame({
    'RV_daily': RV_daily,
    'RV_weekly': RV_weekly,
    'RV_monthly': RV_monthly
})
y = RV_daily.shift(-1)  # Tomorrow's volatility

model = LinearRegression()
model.fit(X, y)

# Forecast
forecast = model.predict(X.iloc[-1:])
```

**Option D: GARCH (Advanced)**
```python
# Requires `arch` library
from arch import arch_model

model = arch_model(returns, vol='Garch', p=1, q=1)
result = model.fit()

# Forecast next 30 days
forecast = result.forecast(horizon=30)
```

**Recommendation:**
- Start with HAR (good balance of simplicity/accuracy)
- Later add GARCH as "advanced" feature

**Libraries:**
- `numpy`/`pandas` - Basic calculations
- `scikit-learn` - HAR model
- `arch` - GARCH models (Phase 3)

### 2.3 Volatility Trend

**What:** Is volatility rising or falling?

**Simple Approach:**
```python
# Compare current vol to average
current_vol = vol_21d.iloc[-1]
avg_vol = vol_21d.rolling(63).mean().iloc[-1]

trend = "Rising" if current_vol > avg_vol * 1.1 else \
        "Falling" if current_vol < avg_vol * 0.9 else \
        "Stable"
```

**Regression Approach:**
```python
from scipy.stats import linregress

# Fit line to recent volatilities
recent_vol = vol_21d.tail(21)
slope, _, _, p_value, _ = linregress(range(len(recent_vol)), recent_vol)

trend = "Rising" if slope > 0 and p_value < 0.05 else \
        "Falling" if slope < 0 and p_value < 0.05 else \
        "Stable"
```

### 2.4 Volatility Percentile

**What:** Where is current vol vs historical distribution?

```python
# Calculate percentile
vol_history = vol_21d.tail(252)  # Last year
current_vol = vol_21d.iloc[-1]

percentile = (vol_history < current_vol).sum() / len(vol_history)

interpretation = "Very Low" if percentile < 0.20 else \
                "Below Average" if percentile < 0.40 else \
                "Average" if percentile < 0.60 else \
                "Elevated" if percentile < 0.80 else \
                "Very High"
```

### Database Storage for Phase 2

**Option A: New table `portfolio_volatility`**
```sql
CREATE TABLE portfolio_volatility (
    id UUID PRIMARY KEY,
    portfolio_id UUID REFERENCES portfolios(id),
    calculation_date DATE NOT NULL,
    realized_vol_21d NUMERIC(10, 4),
    realized_vol_63d NUMERIC(10, 4),
    expected_vol_30d NUMERIC(10, 4),
    vol_trend VARCHAR(20),  -- 'Rising', 'Falling', 'Stable'
    vol_percentile NUMERIC(10, 4),
    forecast_method VARCHAR(20),  -- 'HAR', 'GARCH', 'EWMA'
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(portfolio_id, calculation_date)
);
```

**Option B: Add to `portfolio_snapshots`**
```sql
ALTER TABLE portfolio_snapshots
ADD COLUMN realized_vol_21d NUMERIC(10, 4),
ADD COLUMN expected_vol_30d NUMERIC(10, 4),
ADD COLUMN vol_trend VARCHAR(20),
ADD COLUMN vol_percentile NUMERIC(10, 4);
```

**Recommendation:** Add to snapshots (Option B) - keeps all daily metrics in one place

**Alembic Migration:**
```bash
alembic revision -m "add_volatility_metrics_to_snapshots"
```

---

## Phase 3: Advanced Volatility (Vol-of-Vol)

### 3.1 Volatility-of-Volatility

**What:** Measures uncertainty in volatility itself

**Method 1: Rolling Vol of Vol**
```python
# Step 1: Calculate rolling volatility
rolling_vol = returns.rolling(21).std()

# Step 2: Calculate volatility OF that volatility
vol_of_vol = rolling_vol.rolling(21).std()
```

**Method 2: GARCH Conditional Variance**
```python
from arch import arch_model

# Fit GARCH(1,1)
model = arch_model(returns, vol='Garch', p=1, q=1)
result = model.fit()

# Conditional variance (time-varying forecast)
conditional_vol = result.conditional_volatility

# Vol of vol = std of conditional vol
vol_of_vol = conditional_vol.rolling(21).std()
```

**Interpretation:**
- High vol-of-vol = high uncertainty about future volatility
- Often rises before market stress
- Can be early warning signal

### 3.2 Downside Deviation

**What:** Volatility of negative returns only

```python
# Separate positive and negative returns
downside_returns = returns[returns < 0]

# Downside deviation
downside_vol = downside_returns.std() * np.sqrt(252)

# Semi-deviation (vs mean)
target = 0  # or use mean return
downside_deviation = returns[returns < target].std() * np.sqrt(252)
```

**Why:** Investors care more about downside than upside volatility

### 3.3 Maximum Drawdown

**What:** Largest peak-to-trough decline

```python
# Calculate cumulative returns
cumulative = (1 + returns).cumprod()

# Running maximum
running_max = cumulative.expanding().max()

# Drawdown
drawdown = (cumulative - running_max) / running_max

# Maximum drawdown
max_drawdown = drawdown.min()
```

### Database Storage for Phase 3

```sql
CREATE TABLE portfolio_advanced_risk (
    id UUID PRIMARY KEY,
    portfolio_id UUID REFERENCES portfolios(id),
    calculation_date DATE NOT NULL,
    vol_of_vol NUMERIC(10, 4),
    downside_deviation NUMERIC(10, 4),
    max_drawdown NUMERIC(10, 4),
    sortino_ratio NUMERIC(10, 4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(portfolio_id, calculation_date)
);
```

**Alembic Migration:**
```bash
alembic revision -m "add_advanced_risk_metrics_table"
```

---

## Phase 4: Advanced Factor Model (Optional - User-Driven)

### DECISION: Skip Multi-Factor Models Initially

**Rationale:**
After deep analysis and discussion, we've decided to **NOT** implement multi-factor models in initial release. Here's why:

### What Users Actually Need (Phase 1 & 2)

**Instead of:**
```
Market Beta: 1.2
Value Factor: -0.65
Growth Factor: +0.85
Momentum Factor: +0.45
Quality Factor: +0.32
```

**Users want:**
```
Market Beta: 1.2
Sector Exposure: 45% Technology (17% overweight)
P/E Ratio: 28 (Growth-oriented)
12-Month Return: +32% (Strong momentum)
Concentration: Top 3 = 35%
```

### Why This Decision Makes Sense

**1. More Actionable**
- "45% in Tech" → Can rebalance
- "Growth spread beta +0.85" → What do I do with this?

**2. Mathematically Sound**
- Single market beta: VIF = 1 (perfect)
- Sector exposure: No multicollinearity (mutually exclusive)
- Stress tests: Use single market beta

**3. User Research**
- Investors think in sectors, not factors
- "I own tech stocks" not "I'm long the growth-value spread"
- Characteristics (P/E, momentum) more intuitive than dynamic betas

**4. Faster Time to Value**
- Phase 1 deliverable in 2 weeks
- Multi-factor model would add 2-3 weeks
- Can always add later if users demand

### If We Add Factors Later (Phase 3+)

**Only if users explicitly request it, build:**

**3-Factor Model (Long-Short Spreads):**
1. **Market** = SPY returns
2. **Growth-Value Spread** = VUG - VTV
3. **Momentum Spread** = MTUM - SPY

**Benefits:**
- Low multicollinearity (VIF < 5)
- Captures dynamic style exposures
- For sophisticated users who hedge

**Implementation:**
- Behind "Advanced Analytics" toggle
- Clear tooltips explaining meaning
- Translation layer: "Growth spread +0.85 means..."

### Current Status

**Phase 1-2: Build This First**
- Market beta (single factor)
- Sector exposure vs S&P 500
- Concentration metrics
- Volatility forecasting
- Stress scenarios

**Phase 3+: Add IF Requested**
- 3-factor model (long-short spreads)
- Only if users ask: "How do I hedge my style exposures?"
- Progressive disclosure approach

---

## Debugging Current Issues

### Issue 1: Stress Testing Not Working

**Location:** `backend/app/calculations/market_risk.py`

**Likely Problems:**
1. **Same multicollinearity issue**
   - Stress tests use `calculate_portfolio_market_beta()`
   - Which calls buggy `calculate_factor_betas_hybrid()`
   - Fix: Use new single market beta calculation

2. **Missing data**
   - Check if SPY prices available for all dates
   - Check if positions have last_price set

**Debug Script:**
```bash
# Create: backend/scripts/debug_stress_testing.py
uv run python scripts/debug_stress_testing.py --portfolio-id <uuid>
```

### Issue 2: Position Correlations Giving Bad Output

**Location:** `backend/app/calculations/correlations.py`

**Likely Problems:**
1. **Date alignment issues**
   - Not all positions have same date range
   - Missing data creates gaps

2. **Short data windows**
   - Need at least 21 days for meaningful correlation
   - Check actual overlap

3. **Return calculation errors**
   - Check if using signed returns correctly
   - Verify no NaN/Inf values

**Debug Script:**
```bash
# Create: backend/scripts/debug_correlations.py
uv run python scripts/debug_correlations.py --portfolio-id <uuid>
```

**Diagnostic Checks:**
```python
# Check data availability
for pos1, pos2 in position_pairs:
    overlap = get_common_dates(pos1, pos2)
    print(f"{pos1} vs {pos2}: {len(overlap)} common days")

    if len(overlap) < 21:
        print(f"  WARNING: Insufficient data for correlation")

    # Check for NaN
    if returns[pos1].isna().sum() > 0:
        print(f"  WARNING: {pos1} has {returns[pos1].isna().sum()} NaN values")
```

---

## Implementation Roadmap

### Phase 1: Core Risk Metrics (Weeks 1-2)

**Sprint 1: Fix Market Beta (Week 1)**
**Goal:** Get accurate, reliable market betas

1. Create `calculate_market_beta.py` script
2. Implement single-factor regression (position vs SPY)
3. Create database migration for storage
4. Test on demo portfolios
5. Verify NVDA shows beta ~2.12 (not -3!)
6. Update batch orchestrator to use new calculation
7. Fix stress testing to use new market beta

**Deliverable:** ✅ Working market beta + stress tests

**Sprint 2: Sector Exposure & Concentration (Week 2)**
**Goal:** Clear picture of portfolio composition

1. Create `sector_analysis.py` script
2. Implement sector aggregation logic
3. Add S&P 500 benchmark weights (static)
4. Calculate over/underweight by sector
5. Implement concentration metrics (HHI, Top N)
6. Database migrations (add to portfolio_snapshots)
7. Test on all demo portfolios

**Deliverable:** ✅ Sector analysis + concentration metrics

**Phase 1 Success Criteria:**
- Market beta accurate (NVDA = 1.7-2.2)
- Sector weights sum to 100%
- Stress tests working with new betas
- All metrics stored in portfolio_snapshots

---

### Phase 2: Enhanced Analytics (Weeks 3-4)

**Sprint 3: Volatility Analysis (Week 3)**
**Goal:** Current + expected volatility

1. Create `volatility_analysis.py` script
2. Implement realized volatility (21d, 63d)
3. Implement HAR model for forecasting
4. Calculate vol trend & percentile
5. Database migrations (add to portfolio_snapshots)
6. Test forecasts vs actual outcomes

**Deliverable:** ✅ Volatility metrics + forecasting

**Sprint 4: Downside Risk & Historical Scenarios (Week 4)**
**Goal:** Tail risk and crisis scenarios

1. Implement downside deviation (semi-volatility)
2. Calculate maximum drawdown
3. Add historical crisis scenarios (2008, 2020, etc.)
4. Enhance stress testing with sector-specific shocks
5. Database migrations (advanced risk table)
6. Comprehensive testing & validation

**Deliverable:** ✅ Complete risk analytics suite

**Phase 2 Success Criteria:**
- Volatility forecasts within 20% of realized
- Downside deviation > total volatility (asymmetric risk)
- Historical scenarios match actual market moves
- Users can stress test custom scenarios

---

### Phase 3+: Advanced Features (User-Driven)

**Only build if users request:**
- Vol-of-vol risk metrics
- 3-factor model (long-short spreads)
- Dynamic correlation analysis
- Custom scenario builder
- Hedge recommendation engine

**Philosophy:** Ship Phase 1-2, gather feedback, then decide Phase 3 priorities

---

## Success Criteria

### Phase 0 (Market Beta)
- ✅ NVDA market beta: 1.7-2.2 (not -3!)
- ✅ All positions have valid betas
- ✅ R² > 0.3 for high-beta stocks
- ✅ No VIF warnings (single factor)

### Phase 1 (Core Metrics)
- ✅ Sector weights sum to 100%
- ✅ All positions have sector assigned
- ✅ HHI matches manual calculation
- ✅ Top 10 concentration makes sense

### Phase 2 (Volatility)
- ✅ Current vol in reasonable range (10-50% annualized)
- ✅ Forecast vol within 20% of realized
- ✅ Vol trend matches visual inspection
- ✅ Percentile ranks correctly

### Phase 3+ (Advanced)
- ✅ Vol-of-vol spikes before market stress
- ✅ Downside deviation > total volatility
- ✅ Max drawdown matches historical

---

## Architecture Decisions Made ✅

### RESOLVED: Core Approach

**1. Market Beta Storage:**
- ✅ **DECISION:** Add to `portfolio_snapshots` table
- Rationale: Keep all daily risk metrics together
- Store both position-level and portfolio-level betas

**2. Portfolio Beta Calculation:**
- ✅ **DECISION:** Start with equity-weighted average
- Add direct regression later when we have 90 days of portfolio history
- Store both methods once available for validation

**3. Sector Exposure Storage:**
- ✅ **DECISION:** JSONB column in `portfolio_snapshots`
- Rationale: Flexible schema, easy to query, keeps everything together
- Format: `{"Technology": {"portfolio": 45, "benchmark": 28, "diff": 17}}`

**4. Factor Model Approach:**
- ✅ **DECISION:** Skip multi-factor models initially
- Rationale: Users want actionable insights, not academic models
- Build Phase 1 (market beta + sectors + concentration) first
- Add 3-factor model ONLY if users request it

**5. Volatility Forecasting:**
- ✅ **DECISION:** Start with HAR model
- Rationale: Good balance of simplicity and accuracy
- Add GARCH in Phase 3 if users need it
- Use scikit-learn (already have it)

### Open Questions Remaining

**1. Characteristic Data Sources:**
- Where do we get P/E, P/B ratios? (FMP API? Bloomberg?)
- How often to update? (Daily vs weekly vs monthly)

**2. Historical Scenario Data:**
- Need to fetch historical market moves for 2008, 2020, etc.
- Store as constants or dynamic calculation?

**3. Sector Shocks:**
- What sector-specific scenarios to include?
- User-defined or pre-set library?

**4. Frontend Display:**
- How to visualize sector over/underweight?
- How much detail to show on volatility forecasts?

---

## Next Steps - Ready to Implement ✅

### Immediate Actions (Today)

1. ✅ **Plan Reviewed & Approved** - Phase 1/2 approach confirmed
2. ✅ **Architecture Decisions Made** - All major questions resolved
3. **Create Development Branch** - `feature/risk-metrics-overhaul`
4. **Begin Sprint 1** - Start implementing market beta

### Sprint 1 Tasks (Week 1)

**Day 1-2: Create market_beta.py**
- [ ] New file: `backend/app/calculations/market_beta.py`
- [ ] Implement `calculate_position_market_beta()`
- [ ] Single-factor OLS regression (position vs SPY)
- [ ] Return beta + diagnostics (R², p-value, observations)

**Day 3: Database Migration**
- [ ] Create Alembic migration
- [ ] Add columns to `portfolio_snapshots`:
  - `market_beta` (portfolio level)
  - `market_beta_r_squared` (fit quality)
- [ ] Test migration on dev database

**Day 4: Testing & Validation**
- [ ] Test on demo portfolios
- [ ] Verify NVDA beta = 1.7-2.2 (not -3!)
- [ ] Check all positions have valid betas
- [ ] Validate R² values reasonable

**Day 5: Integration**
- [ ] Update batch orchestrator to call new market_beta.py
- [ ] Fix stress testing to use new market beta
- [ ] Run full batch on all demo portfolios
- [ ] Document changes

**Sprint 1 Goal:** ✅ Accurate market betas + working stress tests

### Ready to Start?

All planning is complete. We have:
- ✅ Clear problem definition
- ✅ Agreed solution approach
- ✅ Technical implementation details
- ✅ Database architecture
- ✅ Success criteria
- ✅ 4-week roadmap

**Let's build Phase 1!**

---

## References

**Diagnostic Scripts Created:**
- `backend/scripts/check_nvda_prices.py` - Price data validation
- `backend/scripts/debug_multivariate_regression.py` - Factor analysis debugging

**Key Files to Modify:**
- `backend/app/calculations/factors.py` - Current (broken) factor analysis
- `backend/app/calculations/market_risk.py` - Stress testing (uses broken betas)
- `backend/app/calculations/correlations.py` - Correlation analysis (debug needed)
- `backend/app/batch/batch_orchestrator_v2.py` - Batch processing orchestration

**Documentation:**
- Fama-French factor research
- HAR volatility model (Corsi, 2009)
- GARCH models for volatility forecasting
- Volatility-of-volatility risk premium literature

---

**Last Updated:** 2025-10-15
**Owner:** Ben Balbale
**Status:** ✅ Planning Complete - Ready for Implementation

---

## Key Insights from Planning Discussion

### Why We're Not Doing Multi-Factor Models (Initially)

**The Realization:**
After deep analysis, we discovered that what investors actually need is different from what academic finance says they need.

**What Investors Ask:**
- "How concentrated am I in Tech?"
- "What happens if the market drops 20%?"
- "Am I chasing too much momentum?"

**What They DON'T Ask:**
- "What's my loading on the HML factor?"
- "What's my exposure to the growth-value spread?"

**The Decision:**
Build what users actually need (Phase 1-2), not what sounds impressive in academic papers.

### Philosophy: Simple > Complex

**Warren Buffett's metrics:**
- P/E ratio, debt-to-equity, return on equity
- No fancy factor models
- Works for world's best investor

**SigmaSight approach:**
- Market beta (clear, actionable)
- Sector exposure (intuitive, visual)
- Concentration (obvious risk)
- Stress scenarios (concrete outcomes)

**Result:** Users get insights they can act on, not metrics they need to research.

### Progressive Disclosure

**Phase 1-2:** Core metrics everyone needs
- If users say "I understand this, give me more" → Phase 3

**Phase 3+:** Advanced analytics for sophisticated users
- If users say "What's a growth-value spread?" → We built the right thing in Phase 1-2

**Philosophy:** Start lean, add complexity only when users explicitly demand it.

### Measuring Success

**Wrong metric:** "We have a 7-factor risk model!"
**Right metric:** "Users rebalanced their portfolio based on our insights."

Action > Sophistication
