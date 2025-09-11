# Backend Compute Error Documentation

> **Last Updated**: 2025-09-11 (CRITICAL SQL JOIN BUG FIXED)  
> **Purpose**: Document and track all computation errors encountered during batch processing and API services  
> **Status**: 4 Issues Resolved (including P0 SQL bug), 15 Active

## 🎉 Major Fix Completed (2025-09-11)

**Critical SQL Join Bug (#18) RESOLVED**:
- **Problem**: Analytics API was returning 127x inflated values due to bad SQL join
- **Solution**: Removed join with MarketDataCache, used Position.last_price field instead
- **Results**: 
  - Values now correct: Hedge fund shows $1.9M net (was $919M inflated)
  - Short exposures properly negative: -$2.0M (was +$288M wrong sign)
  - All portfolios returning accurate data

## Table of Contents
1. [Critical Issues](#critical-issues)
2. [Unicode Encoding Errors](#unicode-encoding-errors)
3. [Market Data Issues](#market-data-issues)
4. [Database Table Issues](#database-table-issues)
5. [Batch Processing Issues](#batch-processing-issues)
6. [Calculation Engine Issues](#calculation-engine-issues)
7. [API Rate Limiting](#api-rate-limiting)
8. [Resolution Steps](#resolution-steps)

---

## Critical Issues

### 1. Incomplete Portfolio Processing (RESOLVED)
**Severity**: HIGH  
**Impact**: ~~Only 1 of 3 portfolios have calculation data~~ ✅ All portfolios now have data

**Current Status (UPDATED 2025-09-10)**:
- ✅ Demo Individual Portfolio (`1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe`): Complete with 8/8 factors
- ✅ Demo High Net Worth Portfolio (`e23ab931-a033-edfe-ed4f-9d02474780b4`): Complete with 7/8 factors  
- ✅ Demo Hedge Fund Portfolio (`fcd71196-e93e-f000-5a74-31a9eead3118`): Complete with 7/8 factors

**Resolution**: Successfully ran batch processing for all portfolios after fixing portfolio IDs and using UTF-8 encoding

---

## Unicode Encoding Errors

### Issue #1: Windows CP1252 Encoding
**Location**: Multiple Python scripts  
**Error Message**: 
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0: character maps to <undefined>
```

**Affected Files**:
- `scripts/verify_demo_portfolios.py` (line 69)
- `scripts/run_batch_with_reports.py` (line 243, 374)
- Various logging statements with emoji characters

**Solution Required**: 
```bash
# Run all Python scripts with UTF-8 encoding
PYTHONIOENCODING=utf-8 uv run python <script.py>
```

---

## Market Data Issues

### Issue #2: Unexpected FMP Historical Data Format
**Error**: `Unexpected FMP historical data format for ZOOM`  
**Location**: `app/services/market_data_service.py` during FMP API calls
**Frequency**: Repeated 4 times during batch run  

**Technical Details**:
- FMP API returns unexpected JSON structure for certain symbols (ZOOM, PTON, etc.)
- Expected format: `{"historical": [{"date": "...", "close": ...}]}`
- Actual format varies or returns empty/malformed response
- Affects tickers that may have been delisted or have limited history

**Impact**: 
- Market data sync failures for 4-6 symbols
- Positions with these symbols cannot calculate current market values
- Falls back to last cached price if available

### Issue #3: Missing Factor ETF Data
**Error**: `Missing data points: {'SIZE': 2}`  
**Location**: `app/calculations/factors.py` line 45-72
**Root Cause**: SIZE factor ETF (SLY) has insufficient historical data

**Technical Details**:
- Factor regression requires 150 days of price history
- SLY ETF only has 148 days available (missing 2 days)
- Regression calculation uses returns correlation between position and factor ETF
- Missing data causes regression to fail or produce unreliable coefficients

**Affected ETFs**: 
- SLY (SIZE factor): Missing 2 days
- Other factor ETFs have complete data

**Impact**: 
- SIZE factor exposure cannot be accurately calculated
- Factor attribution incomplete for portfolio risk analysis
- May affect 10-15% of positions depending on correlation with SIZE

### Issue #4: Insufficient Historical Data for Options
**Error Messages**:
```
❌ SLY: 0 days (needs 150 more)
❌ TSLA250815C00300000: 1 days (needs 149 more)
❌ MSFT250919P00380000: 1 days (needs 149 more)
❌ VIX250716C00025000: 1 days (needs 149 more)
❌ NVDA251017C00800000: 1 days (needs 149 more)
❌ AAPL250815P00200000: 1 days (needs 149 more)
❌ SPY250919C00460000: 1 days (needs 149 more)
❌ META250919P00450000: 1 days (needs 149 more)
❌ QQQ250815C00420000: 1 days (needs 149 more)
```
**Location**: `app/calculations/options_pricing.py` historical data validation
**Required**: 150 days for volatility calculation

**Technical Details**:
- Options contracts are new (just listed)
- Historical data starts from listing date, not 150 days ago
- Volatility calculation needs:
  ```python
  # Need 150 days of underlying price history
  returns = underlying_prices.pct_change()
  volatility = returns.std() * sqrt(252)  # Annualized
  ```
- Options with 1 day history = just started trading

**Why This Matters**:
- Can't calculate implied volatility without historical volatility baseline
- Greeks (Delta, Gamma, Vega, Theta) require volatility input
- Black-Scholes model needs: S, K, r, T, σ (missing σ)

**Workaround Options**:
1. Use underlying stock's volatility (SPY for SPY options)
2. Use VIX as volatility proxy
3. Use similar option's implied volatility

**Impact**: 
- 8 option positions (~25% of hedge fund) lack Greeks
- Risk metrics incomplete for derivatives
- Hedge effectiveness cannot be measured

### Issue #5: Low FMP Stock Data Success Rate
**Error**: `FMP stock success rate low (50.0%), using Polygon fallback for failed symbols`  
**Location**: `app/services/market_data_service.py` FMP batch fetch
**Frequency**: Occurs on every market data sync batch

**Technical Details**:
- FMP batch endpoint attempts to fetch 20-30 symbols simultaneously
- Success rate: 15/30 symbols (50%) return valid data
- Failed symbols include: Options contracts, some mutual funds, delisted stocks
- System automatically retries failed symbols with Polygon API

**Failure Reasons**:
- Options symbols not supported by FMP (e.g., SPY250919C00460000)
- Mutual fund tickers have different format requirements
- Some symbols may be incorrectly formatted or delisted

**Impact**: 
- Doubles API call volume (FMP attempt + Polygon fallback)
- Increases processing time by ~30 seconds per batch
- May hit rate limits faster on both providers

---

## Database Table Issues

### Issue #6: Factor Exposures Incomplete Factor Sets (PARTIALLY RESOLVED)
**Error**: Factor exposures API returns `"available": false` with `"no_complete_set"`  
**Location**: `/api/v1/analytics/portfolio/{id}/factor-exposures` endpoint  
**Root Cause**: API requires ALL 8 active style factors - missing "Short Interest" factor
**Details**:
- ✅ Schema is CORRECT - service properly joins `factor_exposures` with `factor_definitions`
- ✅ Batch processing successfully ran for all 3 portfolios
- ❌ Only 7 of 8 factors calculated (no ETF proxy for "Short Interest" in FACTOR_ETFS)
- Service expects exactly 8 factors: Market Beta, Size, Value, Momentum, Quality, Low Volatility, Growth, Short Interest

**Current Data State (UPDATED 2025-09-10)**:
- Individual portfolio: 8/8 factors ✅ (API should work)
- HNW portfolio: 7/8 factors (missing Short Interest)
- Hedge Fund portfolio: 7/8 factors (missing Short Interest)
- Total records: 22 portfolio-level, 490 position-level exposures

**Impact**: Factor exposure API fails for 2/3 portfolios due to incomplete factor sets

### Issue #7: Missing Stress Test Results Table
**Error**: `relation "stress_test_results" does not exist`  
**Location**: `app/calculations/stress_testing.py` line 287
**Database Query**: `INSERT INTO stress_test_results ...`

**Technical Details**:
- Table was never created in initial migrations
- Referenced in stress test calculation engine (Job #7)
- Expected schema based on code:
  ```sql
  CREATE TABLE stress_test_results (
      id UUID PRIMARY KEY,
      portfolio_id UUID REFERENCES portfolios(id),
      scenario_id UUID REFERENCES stress_scenarios(id),
      calculation_date DATE,
      total_impact DECIMAL,
      created_at TIMESTAMP
  )
  ```

**Impact**: 
- Stress test calculations complete but cannot persist results
- API endpoints for stress tests return empty data
- Historical stress test tracking unavailable
- Affects all portfolio risk reporting features

### Issue #8: Position Correlations Table Name Mismatch
**Error**: `relation "position_correlations" does not exist`  
**Location**: Various queries in calculation engines
**Actual Table Name**: `pairwise_correlations`  

**Technical Details**:
- Code references `position_correlations` table
- Database has `pairwise_correlations` table
- Schema mismatch between code and migrations
- Affected queries:
  ```sql
  -- Code expects:
  SELECT * FROM position_correlations WHERE portfolio_id = ?
  
  -- Database has:
  SELECT * FROM pairwise_correlations WHERE portfolio_id = ?
  ```

**Table Structure (Actual)**:
```sql
CREATE TABLE pairwise_correlations (
    id UUID PRIMARY KEY,
    portfolio_id UUID,
    symbol1 VARCHAR(20),
    symbol2 VARCHAR(20),
    correlation DECIMAL,
    calculation_date DATE
)
```

**Impact**: 
- Correlation-based calculations fail silently
- Diversification metrics unavailable
- Risk parity calculations incorrect
- Affects portfolio optimization features

---

## Batch Processing Issues

### Issue #9: Portfolio ID Mismatches (RESOLVED)
**Error**: Portfolio IDs in `scripts/run_batch_calculations.py` don't match actual database IDs  
**Attempted IDs**:
- `51134ffd-2f13-49bd-b1f5-0c327e801b69` (not found)
- `c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e` (not found)
- `2ee7435f-379f-4606-bdb7-dadce587a182` (not found)

**Actual IDs**:
- `1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe` (Individual)
- `e23ab931-a033-edfe-ed4f-9d02474780b4` (HNW)
- `fcd71196-e93e-f000-5a74-31a9eead3118` (Hedge Fund)

**Resolution**: ✅ Updated scripts with correct portfolio IDs from database

### Issue #10: Batch Orchestrator Method Names
**Error**: `AttributeError: 'BatchOrchestratorV2' object has no attribute 'run'`  
**Also**: `AttributeError: 'BatchOrchestratorV2' object has no attribute '_run_factor_analysis'`  
**Location**: `app/batch/batch_orchestrator_v2.py`

**Technical Details**:
- Documentation refers to `.run()` method that doesn't exist
- Actual method is `.run_portfolio_batch(portfolio_id)`
- Private methods like `_run_factor_analysis` were refactored
- Current working syntax:
  ```python
  orchestrator = BatchOrchestratorV2()
  await orchestrator.run_portfolio_batch(portfolio_id)
  ```

**Documentation Mismatch**:
- README shows: `orchestrator.run()`
- Actual API: `orchestrator.run_portfolio_batch(portfolio_id)`

**Impact**: 
- Scripts fail when following documentation
- Manual batch runs require code inspection to find correct methods
- Automation scripts using old API break after updates

---

## Calculation Engine Issues

### Issue #11: Beta Capping Warnings
**Warning**: `Beta capped for position b9d5970d-6ec4-b3b1-9044-2e5f8c37376f, factor Market: -6.300 -> -3.000`  
**Location**: `app/calculations/factors.py` lines 124-130
**Frequency**: 3 positions affected (10% of hedge fund portfolio)

**Technical Details**:
- Beta calculation produces extreme values (-6.3) for some positions
- System caps betas at [-3.0, 3.0] range for stability
- Extreme betas typically indicate:
  - Insufficient data points (< 60 days)
  - High leverage positions (options)
  - Data quality issues (gaps, outliers)

**Affected Positions**:
- Short positions with high volatility (ZOOM, PTON)
- Options contracts with non-linear payoffs
- Positions with < 90 days of price history

**Calculation Method**:
```python
beta = covariance(position_returns, market_returns) / variance(market_returns)
if abs(beta) > 3.0:
    beta = 3.0 * sign(beta)  # Cap at ±3.0
```

**Impact**: 
- Risk metrics may underestimate true volatility
- VaR calculations could be off by 10-20% for affected positions
- Portfolio optimization may suggest incorrect hedges

### Issue #12: Missing Interest Rate Factor
**Error**: `No exposure found for shocked factor: Interest_Rate (mapped to Interest Rate Beta)`  
**Location**: `app/calculations/stress_testing.py` factor mapping
**Frequency**: 10 occurrences (once per stress scenario)

**Technical Details**:
- Stress scenarios reference "Interest_Rate" factor
- Factor definitions use "Interest Rate Beta" (with space)
- Mismatch in naming convention causes lookup failure
- Mapping logic:
  ```python
  factor_map = {
      'Interest_Rate': 'Interest Rate Beta',  # Doesn't match
      'Market': 'Market Beta',  # Works
  }
  ```

**Database State**:
- Factor exists in `factor_definitions` as "Interest Rate Beta"
- No calculations exist for this factor (not in FACTOR_ETFS)
- Stress scenarios expect it but can't find it

**Impact**: 
- Interest rate stress tests return zero impact
- Fixed income positions not properly stressed
- Duration risk not captured in risk reports
- Particularly affects bond ETF positions (BND, etc.)

### Issue #13: Excessive Stress Loss Clipping
**Warnings**:
```
Direct stress loss of $-599,760 exceeds 99% of portfolio. Clipping at $-537,057
Correlated stress loss of $-1,315,393 exceeds 99% of portfolio. Clipping at $-537,057
Correlated stress loss of $-1,011,357 exceeds 99% of portfolio. Clipping at $-537,057
Correlated stress loss of $-1,086,798 exceeds 99% of portfolio. Clipping at $-537,057
```
**Location**: `app/calculations/stress_testing.py` lines 195-210
**Portfolio**: Individual Investor ($543K total value)

**Technical Details**:
- Stress scenarios produce losses exceeding portfolio value
- System clips losses at 99% of portfolio to prevent > 100% loss
- Indicates either:
  - Scenario shocks too extreme (50% market crash)
  - Correlation matrix amplifying shocks
  - Leveraged/derivative positions creating non-linear losses

**Scenario Parameters Causing Issue**:
- Market shock: -30% to -50%
- Correlation amplification: 2.4x due to factor correlations
- Portfolio has no hedges to offset losses

**Mathematical Issue**:
```python
# Direct loss calculation
direct_loss = position_value * market_shock * beta
# Correlated loss includes cross-factor effects
correlated_loss = direct_loss * correlation_multiplier
# Clipping logic
if abs(loss) > portfolio_value * 0.99:
    loss = portfolio_value * 0.99 * sign(loss)
```

**Impact**: 
- Stress test results don't show true tail risk
- Risk reports understate potential losses in extreme scenarios
- May give false confidence about portfolio resilience

### Issue #14: Pandas FutureWarning
**Warning**: `The default fill_method='pad' in DataFrame.pct_change is deprecated`  
**Location**: `app/calculations/factors.py` line 69
**Pandas Version**: 2.1.0 (will break in 3.0)

**Current Code**:
```python
# Line 69 - using deprecated default
returns_df = price_df.pct_change().dropna()
```

**Required Fix**:
```python
# Explicit fill_method parameter
returns_df = price_df.pct_change(fill_method=None).dropna()
# Or use ffill() explicitly if forward-fill needed
returns_df = price_df.ffill().pct_change().dropna()
```

**Why This Changed**:
- Pandas removing implicit forward-fill behavior
- Makes data handling more explicit
- Prevents silent data manipulation

**Timeline**:
- Warning introduced: Pandas 2.1.0 (Sept 2023)
- Will error in: Pandas 3.0 (Est. 2025)

**Impact**: 
- Currently just a warning (calculations still work)
- Will cause complete failure when Pandas 3.0 releases
- Affects all factor calculations and return computations

---

## API Rate Limiting

### Issue #15: Polygon API Rate Limits
**Error**: `HTTPSConnectionPool(host='api.polygon.io', port=443): Max retries exceeded with url: /v2/aggs/ticker/SPY250919C00460000/range/1/day/2025-09-05/2025-09-10?adjusted=true&sort=asc&limit=50000 (Caused by ResponseError('too many 429 error responses'))`  
**Location**: `app/services/market_data_service.py` Polygon API client
**Rate Limit**: 5 requests/minute on free tier

**Technical Details**:
- Attempting to fetch 8 option contracts simultaneously
- Each option requires separate API call
- Exceeds 5 req/min limit immediately
- Retry logic makes it worse (3 retries × 8 options = 24 requests)

**Current Implementation Issues**:
```python
# Current: Parallel requests exceed rate limit
for option in options:
    tasks.append(fetch_polygon_data(option))  # All fire at once
await asyncio.gather(*tasks)  # 429 errors

# Should be: Rate-limited sequential or batched
for option in options:
    data = await fetch_polygon_data(option)
    await asyncio.sleep(12)  # 5 req/min = 12 sec between
```

**Impact**: 
- Options data completely unavailable
- Greeks calculations fail for all options positions
- Portfolio risk metrics incomplete for hedge fund portfolio

### Issue #16: FMP Rate Limiting
**Log Messages**:
```
Rate limit: waited 11.45s (request #6, avg rate: 0.34 req/s)
Rate limit: waited 11.29s (request #7, avg rate: 0.23 req/s)
Rate limit: waited 11.94s (request #8, avg rate: 0.19 req/s)
Rate limit: waited 11.96s (request #9, avg rate: 0.17 req/s)
```
**Location**: `app/services/market_data_service.py` FMP rate limiter
**Rate Limit**: 300 requests/minute (5/second) on standard plan

**Technical Details**:
- Rate limiter being overly conservative
- Waiting 11-12 seconds between requests (should be 0.2 seconds)
- Possible causes:
  - Previous 429 errors triggering exponential backoff
  - Shared rate limit across multiple processes
  - Incorrect rate limit configuration

**Configuration Issue**:
```python
# Current configuration (too conservative)
RATE_LIMIT = 0.1  # requests per second (6/min)

# Should be (based on plan)
RATE_LIMIT = 5.0  # requests per second (300/min)
```

**Time Impact**:
- Current: 30 symbols × 12 seconds = 6 minutes
- Optimal: 30 symbols × 0.2 seconds = 6 seconds
- **100x slower than necessary**

**Impact**: 
- Batch calculations take 30+ minutes instead of 3 minutes
- Daily updates may timeout
- User experience degraded waiting for fresh data

---

## API-Database Alignment Issues

### Issue #17: Factor Exposure Service Misalignment (RESOLVED)
**Error**: API returns "no_calculation_available" with "no_complete_set" reason  
**Root Cause**: Not a schema issue - API requires ALL 8 active style factors present

**Investigation Findings**:
- ✅ Database schema is CORRECT (uses `factor_id` and `exposure_value` as designed)
- ✅ Service correctly joins `FactorExposure` with `FactorDefinition` tables
- ✅ Individual portfolio has 8/8 factors (should work)
- ❌ HNW portfolio has 7/8 factors (missing one, causes API failure)  
- ❌ Hedge Fund portfolio has 7/8 factors (missing one, causes API failure)
- ❌ Batch processing only calculates 7 factors (no ETF proxy for "Short Interest")

**Current Data State (After Batch Runs)**:
- Individual portfolio: 8 factor exposures at portfolio level ✅
- HNW portfolio: 7 factor exposures (missing Short Interest)
- Hedge Fund portfolio: 7 factor exposures (missing Short Interest)
- Total position-level exposures: 490 records across all portfolios

**Impact**: Factor exposure API fails for 2/3 portfolios due to incomplete factor sets

### Issue #18: Analytics API SQL Join Bug ✅ RESOLVED (2025-09-11)
**Error**: Portfolio Analytics API returns zeros or massively inflated values  
**Location**: `/api/v1/analytics/portfolio/{id}/overview` endpoint  
**Root Cause**: Bad SQL join with MarketDataCache creates duplicate rows

**Investigation Findings (2025-09-10)**:
- **Critical Bug**: Bad SQL join with MarketDataCache table
- Creates 127x duplicate rows (3,831 instead of 30 positions)
- Results in massively inflated values: $919M instead of $6M
- Returns zeros for exposures in production due to calculation errors

**Technical Details**:
- SQL join creates one row per historical price date instead of latest price only
- The problematic join on line 64-65 of `portfolio_analytics_service.py`:
  ```python
  .outerjoin(MarketDataCache, MarketDataCache.symbol == Position.symbol)
  ```
  Returns ALL historical prices for each position, not just the latest
- For hedge fund: 30 positions × ~127 price dates = 3,831 rows
- Calculation then sums all these duplicate rows, inflating values by 127x

**✅ RESOLUTION IMPLEMENTED (2025-09-11)**:
1. **Removed the problematic SQL join** with MarketDataCache entirely
2. **Used Position.last_price field instead** - already updated by batch jobs
3. **Fixed short exposure calculation** to keep negative values

**Fix Applied**:
```python
# BEFORE (problematic join):
positions_query = select(
    Position.id,
    Position.symbol,
    # ... other fields
    MarketDataCache.close.label('current_price')
).outerjoin(
    MarketDataCache, MarketDataCache.symbol == Position.symbol
)

# AFTER (no join, use Position.last_price):
positions_query = select(
    Position.id,
    Position.symbol,
    Position.position_type,
    Position.quantity,
    Position.entry_price,
    Position.last_price,  # Use this field directly
    Position.market_value,
    Position.unrealized_pnl,
    Position.realized_pnl
).where(
    Position.portfolio_id == portfolio_id
)
```

**Results After Fix**:
- Demo Individual: $542K total (16 positions) ✅
- Demo HNW: $1.6M total (17 positions) ✅  
- Demo Hedge Fund: $1.9M net with $3.9M long, **-$2.0M short** ✅
- Short exposures correctly shown as negative values
- No more 127x inflation
- All values match expected ranges

**Actual vs Expected Values (Hedge Fund Portfolio)**:
```
Actual from /complete endpoint (CORRECT):
  - Long Exposure: $3,906,913.25
  - Short Exposure: $1,990,680.60  
  - Total Value: $6,188,950.79
  
Analytics API returns (WRONG):
  - Long Exposure: $0.00
  - Short Exposure: $0.00
  - Total Value: $342,781,453.15 (55x inflated)
```

**SQL Bug Location**: `app/services/portfolio_analytics_service.py` lines 52-68
```python
# Current (BROKEN) - creates cartesian product with all historical dates
).outerjoin(
    MarketDataCache, MarketDataCache.symbol == Position.symbol
)

# Should be - only latest price per symbol
).outerjoin(
    select(MarketDataCache.symbol, func.max(MarketDataCache.date))
    .group_by(MarketDataCache.symbol)
    .subquery()
)
```

**Impact**: Complete failure of portfolio overview analytics for all portfolios

### Issue #19: Frontend Short Position Assumption
**Error**: Frontend assumes all portfolios have zero short exposure  
**Location**: `frontend/src/services/portfolioService.ts` line 177  
**Code**: `const shortValue = 0 // No short positions in demo data`

**Investigation Findings (2025-09-11)**:
- **Critical**: Hedge Fund has 13 short positions worth ~$2M
- Frontend hardcodes `shortValue = 0`, missing 33% of exposure
- Data exists in database with negative quantities
- Frontend receives the data but ignores it

**Actual Short Positions (Hedge Fund)**:
```javascript
// From database seed_demo_portfolios.py
Short Stocks: 
- NFLX: -600 shares @ $490 = $294,000
- SHOP: -1000 shares @ $195 = $195,000  
- ZOOM: -2000 shares @ $70 = $140,000
- XOM: -2000 shares @ $110 = $220,000
- F: -10000 shares @ $12 = $120,000
// ... total ~$1,990,680 short exposure
```

**Required Fix**:
```javascript
// Calculate from actual position data
const shortPositions = data.holdings.filter(h => 
  h.quantity < 0 || ['SHORT', 'SC', 'SP'].includes(h.position_type)
)
const shortValue = shortPositions.reduce(
  (sum, p) => sum + Math.abs(p.quantity * p.last_price), 0
)
```

**Impact**: 
- Gross exposure understated by $2M (33%)
- Net exposure shows $6M instead of $4M (50% error)
- Risk metrics completely wrong for hedge fund
- Misleading portfolio analytics for sophisticated strategies

---

## Resolution Steps

### Immediate Actions Required

1. **Fix Analytics API SQL Join Bug (CRITICAL - P0)**
   
   **Backend Fix Required**:
   ```python
   # In app/services/portfolio_analytics_service.py
   # Replace the bad join (lines 52-68) with:
   
   # Create subquery for latest prices only
   latest_prices = select(
       MarketDataCache.symbol,
       MarketDataCache.close,
       func.max(MarketDataCache.date).label('latest_date')
   ).group_by(
       MarketDataCache.symbol, 
       MarketDataCache.close
   ).subquery()
   
   # Use in main query
   positions_query = select(
       Position.id,
       Position.symbol,
       # ... other fields
       latest_prices.c.close.label('current_price')
   ).outerjoin(
       latest_prices, latest_prices.c.symbol == Position.symbol
   )
   ```
   
   **Alternative Quick Fix**:
   - Use `Position.last_price` instead of joining MarketDataCache
   - This avoids the join entirely but may have stale prices

2. **Fix Frontend Short Position Calculation (P0)**
   
   **Frontend Fix Required**:
   ```javascript
   // In frontend/src/services/portfolioService.ts line 177
   // Replace:
   const shortValue = 0 // No short positions in demo data
   
   // With:
   const shortValue = data.holdings
     .filter(h => ['SHORT', 'SC', 'SP'].includes(h.position_type))
     .reduce((sum, h) => sum + Math.abs(h.market_value), 0)
   ```

3. **Fix Factor Exposure API (CRITICAL - P0)**
   
   **Option A: Quick Database Fix (Recommended)**
   ```sql
   -- Add missing Short Interest factor with neutral values
   INSERT INTO factor_exposures (
       id, portfolio_id, factor_id, calculation_date, 
       exposure_value, exposure_dollar, created_at, updated_at
   )
   SELECT 
       gen_random_uuid(),
       portfolio_id,
       (SELECT id FROM factor_definitions WHERE name = 'Short Interest'),
       '2025-09-10',
       0.0,  -- Neutral exposure since we can't calculate it
       NULL,
       NOW(),
       NOW()
   FROM (VALUES 
       ('e23ab931-a033-edfe-ed4f-9d02474780b4'::uuid),
       ('fcd71196-e93e-f000-5a74-31a9eead3118'::uuid)
   ) AS t(portfolio_id)
   WHERE NOT EXISTS (
       SELECT 1 FROM factor_exposures fe
       WHERE fe.portfolio_id = t.portfolio_id
       AND fe.factor_id = (SELECT id FROM factor_definitions WHERE name = 'Short Interest')
       AND fe.calculation_date = '2025-09-10'
   );
   ```
   
   **Option B: Make API More Flexible**
   ```python
   # File: app/services/factor_exposure_service.py, Line 74
   # Change from requiring exact match:
   .where(counts_subq.c.cnt == target_count)
   # To allowing one missing factor:
   .where(counts_subq.c.cnt >= target_count - 1)
   ```
   
   **Option C: Disable Short Interest Factor**
   ```sql
   UPDATE factor_definitions SET is_active = false WHERE name = 'Short Interest';
   ```

2. **Fix Unicode Encoding** ✅ COMPLETED
   - Add `PYTHONIOENCODING=utf-8` to all script runners
   - Successfully used in all batch runs

3. **Update Portfolio IDs** ✅ COMPLETED
   - Fixed hardcoded IDs in `scripts/run_batch_calculations.py`
   - All three portfolios now process correctly

4. **Complete Missing Calculations** ✅ COMPLETED
   - Batch processing ran for all portfolios
   - HNW: 168.28s, Hedge Fund: 165.47s
   - Factor exposures increased from 224 to 490 records

5. **Create Missing Database Tables**
   ```sql
   -- Add stress_test_results table via migration
   uv run alembic revision --autogenerate -m "Add stress_test_results table"
   uv run alembic upgrade head
   ```

6. **Fix Table Name References**
   - Update queries to use `pairwise_correlations` instead of `position_correlations`

### Long-term Fixes

1. **Improve Data Provider Fallback Logic**
   - Implement smarter fallback between FMP and Polygon
   - Cache successful provider choices per symbol

2. **Optimize Batch Processing**
   - Implement parallel portfolio processing
   - Add checkpointing to resume after timeouts
   - Split large batches into smaller chunks

3. **Enhanced Error Handling**
   - Add retry logic for rate-limited requests
   - Implement exponential backoff
   - Better error reporting with actionable messages

4. **Data Quality Improvements**
   - Pre-validate data availability before calculations
   - Implement data backfill strategies for options
   - Add data quality monitoring dashboard

5. **Fix Pandas Deprecation**
   ```python
   # In app/calculations/factors.py line 69
   # Change from:
   returns_df = price_df.pct_change().dropna()
   # To:
   returns_df = price_df.pct_change(fill_method=None).dropna()
   ```

---

## Monitoring Commands

```bash
# Check calculation status
cd backend && PYTHONIOENCODING=utf-8 uv run python -c "
from app.database import get_async_session
from sqlalchemy import select, func, text
import asyncio

async def check():
    async with get_async_session() as db:
        # Count factor exposures
        result = await db.execute(text(
            'SELECT p.name, COUNT(pfe.id) as exposures ' +
            'FROM portfolios p ' +
            'LEFT JOIN positions pos ON pos.portfolio_id = p.id ' +
            'LEFT JOIN position_factor_exposures pfe ON pfe.position_id = pos.id ' +
            'GROUP BY p.name'
        ))
        for row in result:
            print(f'{row[0]}: {row[1]} exposures')

asyncio.run(check())
"

# Check correlation data
cd backend && PYTHONIOENCODING=utf-8 uv run python -c "
from app.database import get_async_session
from sqlalchemy import text
import asyncio

async def check():
    async with get_async_session() as db:
        result = await db.execute(text(
            'SELECT COUNT(*) FROM pairwise_correlations'
        ))
        print(f'Pairwise correlations: {result.scalar()}')
        
        result = await db.execute(text(
            'SELECT COUNT(*) FROM correlation_calculations'
        ))
        print(f'Correlation calculations: {result.scalar()}')

asyncio.run(check())
"
```

---

## Migration Strategy: /complete to Analytics APIs

### Current State
- **Frontend**: Uses `/api/v1/data/portfolio/{id}/complete` endpoint
- **Analytics**: `/api/v1/analytics/portfolio/{id}/overview` endpoint broken
- **Data Flow**: Frontend calculates exposures client-side from raw data

### Migration Options

#### Option 1: Fix Backend Analytics (Recommended)
1. Fix SQL join bug in `PortfolioAnalyticsService`
2. Test with all three portfolios to ensure accuracy
3. Update frontend to use analytics endpoints
4. Keep `/complete` as fallback

**Pros**: Centralized calculations, consistent metrics  
**Cons**: Requires backend deployment

#### Option 2: Quick Frontend Fix
1. Fix short position calculation in `portfolioService.ts`
2. Continue using `/complete` endpoint
3. Defer analytics API migration

**Pros**: No backend changes needed  
**Cons**: Client-side calculations remain

#### Option 3: Hybrid Approach
1. Add exposure calculations to `/complete` endpoint
2. Return both raw data and calculated metrics
3. Frontend uses pre-calculated values

**Pros**: Minimal frontend changes  
**Cons**: Duplicates calculation logic

### Testing Requirements
- Verify all three portfolios display correct exposures
- Confirm short positions calculated correctly for hedge fund
- Test error handling when APIs fail
- Validate performance with large portfolios

## Issue #20: Portfolio Data Source Discovery

**Component**: Database Seeding  
**Date**: 2025-09-11  
**Location**: `backend/app/db/seed_demo_portfolios.py`

### Discovery
The portfolio data is **hardcoded** in the seed script, not loaded from external files:
- 3 demo users with fixed credentials (all use password: `demo12345`)
- Portfolio specifications defined in `DEMO_PORTFOLIOS` list (lines 67-176)
- Uses deterministic UUIDs via MD5 hash for consistent IDs across environments

### Portfolio Details
1. **Individual Portfolio** ($485K): 16 positions (all long)
   - 9 stocks, 4 mutual funds, 3 ETFs
   
2. **High Net Worth Portfolio** ($2.85M): 17 positions (all long)
   - 2 ETFs, 13 large cap stocks, 2 alternative assets
   
3. **Hedge Fund Portfolio** ($3.2M): 34 positions (mixed)
   - 13 long stocks
   - **13 short positions** (negative quantities: NFLX -600, SHOP -1000, XOM -2000, etc.)
   - 8 options (4 long calls, 4 short puts)

### Key Finding
The hedge fund portfolio has ~$2M in short positions defined in the seed data, but the frontend shows $0 short exposure because it hardcodes `shortValue = 0` instead of calculating from negative quantities.

---

## Frontend Data Fetching Best Practices

### Architecture Recommendations

#### 1. Hybrid Approach (Production Recommended)
```typescript
// Primary data from overview endpoint
const overview = await fetch('/analytics/portfolio/{id}/overview')
// Supplementary data only when needed
const positions = await fetch('/analytics/portfolio/{id}/positions?page=1')
```

#### 2. Backend-First Calculation Strategy
- **Principle**: "Calculate once, use everywhere"
- **Benefits**: Single source of truth, testable, consistent
- **Implementation**: Fix SQL bug, ensure calculations match

#### 3. Progressive Migration Strategy

**Phase 1: Fix Backend (Priority)**
1. Fix SQL join bug in `portfolio_analytics_service.py`
2. Add proper short position calculations
3. Ensure all 8 factors returned

**Phase 2: Feature Flag Migration**
```typescript
const useAnalyticsAPI = process.env.NEXT_PUBLIC_USE_ANALYTICS_API === 'true'
if (useAnalyticsAPI) {
  return fetchAnalyticsExposures(portfolioId)
} else {
  return calculateExposuresLocally(completeData)
}
```

**Phase 3: Performance Optimization**
- Implement response caching (Redis/CDN)
- Add ETags for conditional requests
- Consider WebSocket for real-time updates

### When to Use Each Approach

**Use `/complete` endpoint when:**
- Initial page load (avoid waterfall)
- Offline-capable applications needed
- Raw data needed for multiple calculations

**Use Analytics APIs when:**
- Dashboard widgets (independent updates)
- Real-time components (smaller payloads)
- Mobile apps (bandwidth conscious)
- Expensive calculations (options Greeks)

### Immediate Fix (Minimal Changes)
```typescript
// Fix short calculations in frontend
function calculateExposures(data: PortfolioData) {
  const shortPositions = data.holdings.filter(h => h.quantity < 0)
  const shortValue = shortPositions.reduce((sum, p) => 
    sum + Math.abs(p.quantity * p.last_price), 0
  )
  // ... proper calculation
}
```

### Performance Comparison
- **Current `/complete`**: ~100KB payload, single trip, includes unnecessary historical data
- **Optimized Analytics**: ~5KB overview + 20KB positions (on-demand) = 75% bandwidth reduction

## Notes

- All errors documented from batch run on 2025-09-10
- Analytics API investigation completed 2025-09-10
- Portfolio data source discovery completed 2025-09-11
- Frontend best practices documented 2025-09-11
- **SQL Join Bug (#18) RESOLVED 2025-09-11**: Analytics API now returns correct values
- Backend server running on Windows (CP1252 encoding issues)
- Database: PostgreSQL 15 in Docker container
- Python version: 3.11.13
- The system is functional with major SQL bug fixed, minor issues remain

---

## Priority Matrix

| Priority | Issue | Impact | Effort | Status |
|----------|-------|--------|--------|--------|
| P0 | Analytics API SQL join bug (#18) | CRITICAL - Analytics API returns wrong values | LOW - Fix SQL query | ✅ **RESOLVED** |
| P0 | Frontend short position assumption (#19) | CRITICAL - Wrong exposures for hedge fund | LOW - Calculate from data | **NEW** |
| P0 | Factor exposure incomplete sets (#6,#17) | CRITICAL - API fails for 2/3 portfolios | LOW - Add missing factor | **PARTIALLY RESOLVED** |
| P1 | Missing database tables (#7) | HIGH - Stress tests unavailable | MEDIUM - Create migrations | **PENDING** |
| P2 | Rate limiting issues (#15,#16) | MEDIUM - Slow processing | HIGH - Implement retry logic | **ACTIVE** |
| P2 | Insufficient options data (#4) | MEDIUM - Options calc fail | HIGH - Historical backfill | **PENDING** |
| P3 | Portfolio data hardcoded (#20) | LOW - Works but inflexible | MEDIUM - Externalize data | **DOCUMENTED** |
| P3 | Pandas deprecation (#14) | LOW - Future issue | LOW - Update code | **PENDING** |
| P3 | Beta capping warnings (#11) | LOW - Working as designed | LOW - Adjust thresholds | **MONITORING** |
| ✅ | Incomplete portfolio processing (#1) | ~~HIGH - No data for 2/3 portfolios~~ | ~~LOW - Run batch again~~ | **RESOLVED** |
| ✅ | Unicode encoding errors (#1) | ~~HIGH - Scripts fail to run~~ | ~~LOW - Add env variable~~ | **RESOLVED** |
| ✅ | Portfolio ID mismatches (#9) | ~~HIGH - Batch jobs fail~~ | ~~LOW - Update scripts~~ | **RESOLVED** |

---

## Equity-Based Portfolio Calculation Plan (2025-09-11)

### Problem Statement
Currently, portfolio totals are calculated by summing position values, which doesn't account for:
- Cash balances (positive or negative/margin)
- True equity (NAV)
- Leverage ratios
- Risk metrics for long/short portfolios

### Solution: Equity-First Model

#### Core Formula
```
Equity = Long MV - |Short MV| + Cash

Rearranging for Cash:
Cash = Equity - Long MV + |Short MV|

Where:
- Equity: User-provided NAV (net asset value)
- Long MV: Market value of long positions
- Short MV: Market value of short positions (negative number)
- Cash: Calculated value (can be negative if leveraged)
```

#### Implementation Plan

**Phase 1: Database Changes**
1. Add `equity_balance` field to Portfolio model (Decimal, nullable)
2. Create Alembic migration
3. Set default values:
   - Demo Individual: $500,000
   - Demo HNW: $1,500,000
   - Demo Hedge Fund: $2,000,000

**Phase 2: Update Analytics Service**
```python
def _calculate_portfolio_metrics(self, db, portfolio_id, positions, equity_balance):
    # Calculate exposures from positions
    long_exposure = sum(pos.value for pos if pos.quantity > 0)
    short_exposure = sum(pos.value for pos if pos.quantity < 0)  # negative
    
    # Core calculations
    gross_exposure = long_exposure + abs(short_exposure)
    net_exposure = long_exposure + short_exposure
    
    # Calculate cash from equity
    cash_balance = equity_balance - long_exposure + abs(short_exposure)
    
    # Risk metrics
    leverage = gross_exposure / equity_balance if equity_balance > 0 else 0
    
    # Portfolio total equals equity (not sum of positions)
    portfolio_total = equity_balance
```

**Phase 3: API Endpoints**
- `PUT /portfolio/{id}/equity` - Update equity balance
- Update `/analytics/portfolio/{id}/overview` to include:
  - equity_balance
  - cash_balance (calculated)
  - leverage ratio
  - margin usage percentage

**Phase 4: Risk Metrics**
- Show leverage prominently (warn if > 2x)
- Display cash/margin status
- Calculate margin usage if cash negative
- Add risk indicators for high leverage scenarios

#### Example Calculations

**Demo Individual (Equity: $500k)**
- Long: $542k, Short: $0
- Cash: $500k - $542k + $0 = -$42k (margin debt)
- Leverage: 1.08x

**Demo HNW (Equity: $1.5M)**
- Long: $1.63M, Short: $0
- Cash: $1.5M - $1.63M + $0 = -$130k (margin debt)
- Leverage: 1.09x

**Demo Hedge Fund (Equity: $2M)**
- Long: $3.9M, Short: -$2.0M
- Cash: $2M - $3.9M + $2M = $0.1M
- Gross: $5.9M
- Leverage: 2.95x (~3x leveraged)

#### Benefits
1. **Risk-focused**: Shows true leverage and margin usage
2. **Simple**: User provides one number (equity)
3. **Accurate**: Reflects real portfolio mechanics
4. **Flexible**: Works for long-only and long/short portfolios
5. **No P&L tracking**: Just current positions + equity

---

## Database Schema Analysis & Join Fix Strategy

### Database Structure & Data Sources

```
═══════════════════════════════════════════════════════════════════
                    DATABASE SCHEMA & DATA SOURCES
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│                           USERS                                  │
├─────────────────────────────────────────────────────────────────┤
│ id, email, full_name, hashed_password                           │
│ SOURCE: 🔧 DEMO DATA (seed_demo_portfolios.py)                  │
│ - 3 hardcoded demo users                                        │
│ - Fixed passwords: "demo12345"                                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ 1:1
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        PORTFOLIOS                                │
├─────────────────────────────────────────────────────────────────┤
│ id, user_id, name, description, currency                        │
│ SOURCE: 🔧 DEMO DATA (seed_demo_portfolios.py)                  │
│ - 3 hardcoded portfolios                                        │
│ - Individual ($485K), HNW ($2.85M), Hedge Fund ($3.2M)         │
│ ❌ NO cash_balance field (calculated from positions)            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ 1:N
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         POSITIONS                                │
├─────────────────────────────────────────────────────────────────┤
│ id, portfolio_id, symbol, position_type, quantity               │
│ entry_price, entry_date, exit_price, exit_date                  │
│ ---                                                             │
│ last_price ──────> 📊 CALCULATED (batch job updates)            │
│ market_value ────> 📊 CALCULATED (quantity × last_price)        │
│ unrealized_pnl ──> 📊 CALCULATED (market_value - cost_basis)    │
│ realized_pnl ────> 📊 CALCULATED (from exits)                   │
│ ---                                                             │
│ SOURCE: 🔧 DEMO DATA for base fields                            │
│         📊 BATCH JOBS for calculated fields                     │
│ - 63 total positions across 3 portfolios                        │
│ - Hedge fund has negative quantities (shorts)                   │
└─────────────────────────────────────────────────────────────────┘
          │                           │
          │                           │ N:1 per position
          │                           ▼
          │         ┌─────────────────────────────────────────────┐
          │         │            POSITION_GREEKS                   │
          │         ├─────────────────────────────────────────────┤
          │         │ position_id, delta, gamma, theta, vega      │
          │         │ SOURCE: 📊 CALCULATED (Black-Scholes)       │
          │         │ - Only for options positions                │
          │         │ - Uses market data + volatility             │
          │         └─────────────────────────────────────────────┘
          │
          │ ⚠️ THE PROBLEMATIC JOIN!
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MARKET_DATA_CACHE                            │
├─────────────────────────────────────────────────────────────────┤
│ id, symbol, date, open, high, low, close, volume               │
│ sector, industry, exchange, country, market_cap                 │
│ data_source: 'polygon' | 'fmp' | 'tradefeeds' | 'yfinance'     │
│ ---                                                             │
│ SOURCE: 🌐 EXTERNAL APIs                                        │
│ - FMP: Primary for stocks (50% success rate)                    │
│ - Polygon: Fallback + options (rate limited 5/min)             │
│ ---                                                             │
│ ⚠️ PROBLEM: Contains 127+ days of history per symbol!           │
│ ⚠️ JOIN creates: 30 positions × 127 days = 3,831 rows         │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
                    CALCULATED TABLES (Batch Jobs)
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│                     FACTOR_EXPOSURES                             │
├─────────────────────────────────────────────────────────────────┤
│ portfolio_id, factor_id, exposure_value, exposure_dollar        │
│ SOURCE: 📊 CALCULATED (7-factor regression)                     │
│ - Uses 150 days of price history                                │
│ - Missing "Short Interest" factor (no ETF proxy)                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                POSITION_FACTOR_EXPOSURES                         │
├─────────────────────────────────────────────────────────────────┤
│ position_id, factor_id, beta_value                              │
│ SOURCE: 📊 CALCULATED (position-level betas)                    │
│ - 490 records after batch processing                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  PAIRWISE_CORRELATIONS                           │
├─────────────────────────────────────────────────────────────────┤
│ portfolio_id, symbol1, symbol2, correlation                     │
│ SOURCE: 📊 CALCULATED (return correlations)                     │
│ ❌ Code expects "position_correlations" table                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   STRESS_TEST_RESULTS                            │
├─────────────────────────────────────────────────────────────────┤
│ ❌ TABLE DOESN'T EXIST! (Issue #7)                              │
│ Should contain: portfolio_id, scenario_id, impact               │
└─────────────────────────────────────────────────────────────────┘
```

### Key Insights & Join Avoidance Strategy

#### 🔴 The Core Problem
The `MarketDataCache` table is a **time-series table** with multiple dates per symbol, but the analytics service is treating it like a **lookup table** with one row per symbol.

#### 💡 Join Avoidance Options

**Option A: Use Position.last_price (NO JOIN NEEDED!)**
```sql
-- Current problematic query
SELECT p.*, m.close FROM positions p 
JOIN market_data_cache m ON p.symbol = m.symbol  -- Gets ALL dates!

-- Simple fix - no join
SELECT p.*, p.last_price as current_price FROM positions p
WHERE portfolio_id = ?
```

**Option B: Create a Materialized View or Summary Table**
```sql
-- Create a latest_prices view/table
CREATE VIEW latest_market_prices AS
SELECT DISTINCT ON (symbol) 
    symbol, close as last_price, date as price_date
FROM market_data_cache
ORDER BY symbol, date DESC;

-- Then join with this instead
```

**Option C: Update Position.last_price in Batch Jobs**
- Batch jobs already update `last_price` field
- Just need to ensure it's current
- Analytics can trust this field

### 📊 Data Flow Summary

1. **Demo Data** → Users, Portfolios, Position basics
2. **External APIs** → MarketDataCache (historical prices)
3. **Batch Jobs** → Calculate and UPDATE Position fields:
   - `last_price` ← Latest from MarketDataCache
   - `market_value` ← quantity × last_price
   - `unrealized_pnl` ← market_value - (quantity × entry_price)
4. **Analytics Service** → Should read Position fields, NOT join with MarketDataCache

### ✅ Recommended Approach

**Don't join at all!** The Position table already has everything we need:
- `last_price` - Updated by batch jobs
- `market_value` - Pre-calculated
- `unrealized_pnl` - Pre-calculated

The analytics service should just aggregate these pre-calculated values rather than trying to recalculate from raw market data.

This avoids the join entirely and uses the work that's already been done by the batch processing system.

---

## Cash Balance & Margin Considerations

### The Missing Cash Balance Problem

The Portfolio table lacks a `cash_balance` field, but the reality is more complex than just adding a simple field.

### Real-World Complexities

1. **Negative Cash (Margin/Leverage)**
   - Hedge funds borrow to amplify positions
   - Cash balance could be -$500K if leveraged
   - Interest charges accrue on margin debt

2. **Money Market Funds as "Cash"**
   - Cash often held as SPAXX, VMFXX, SWVXX, etc.
   - These are actual positions with tickers
   - They have NAV (usually ~$1.00) and earn yield

### Implementation Options

#### Option 1: Add cash_balance Field
```sql
ALTER TABLE portfolios 
ADD COLUMN cash_balance NUMERIC(16, 2);  -- Can be negative!
ADD COLUMN margin_debt NUMERIC(16, 2) DEFAULT 0;  -- Track separately?
```

**For demo hedge fund:**
```python
"cash_balance": -200000,  # Borrowed $200K on margin
"margin_debt": 200000,     # Explicit tracking
```

#### Option 2: Money Market as Position (Reflects Reality)
**This is how real brokerages work:**
```python
# In positions table
{
    "symbol": "SPAXX",  # Fidelity Government Money Market
    "position_type": PositionType.LONG,
    "quantity": Decimal("300000"),  # 300K shares
    "entry_price": Decimal("1.00"),  # NAV ~$1
    "last_price": Decimal("1.0001"),  # Slight fluctuation
}
```

**Advantages:**
- Reflects reality (cash IS in a money market fund)
- Automatically included in position calculations
- Tracks yield/interest naturally
- No schema changes needed!

#### Option 3: Hybrid Approach (Most Accurate)
Track both:
1. **Actual cash/margin balance** (could be negative)
2. **Money market positions** (the "sweep" funds)

```python
# Portfolio table
cash_balance: -200000  # Margin debt
margin_available: 500000  # Borrowing capacity

# Positions table
SPAXX: 300000 shares  # Money market fund
SPY: 1000 shares      # Regular positions
```

### Impact on Portfolio Calculations

**Total Portfolio Value:**
```python
# Old (wrong)
total_value = sum(position_values)

# New (correct)
total_value = cash_balance + sum(position_values)
# Where cash_balance can be negative (margin debt)
# And position_values includes money market funds
```

**Leverage Calculation:**
```python
gross_exposure = sum(abs(position_values))
net_assets = cash_balance + sum(position_values)  # Can be less than gross!
leverage = gross_exposure / net_assets  # Could be 2x, 3x, etc.
```

**Example for Hedge Fund:**
```python
# Positions
Long positions: $4M
Short positions: $2M (held as negative quantities)
Money market (SPAXX): $300K
Cash balance: -$200K (margin debt)

# Calculations
Gross exposure: $6M (4M + 2M)
Net assets: $2.1M (4M - 2M + 0.3M - 0.2M)
Leverage: 2.86x (6M / 2.1M)
```

### Recommended Implementation

**Use Option 2 + Small Schema Change:**

1. **Add money market positions** to seed data:
```python
# Add to hedge fund positions
{
    "symbol": "SPAXX",
    "position_type": PositionType.LONG,
    "quantity": Decimal("300000"),
    "entry_price": Decimal("1.00"),
}
```

2. **Add margin_balance to Portfolio** (one field):
```sql
ALTER TABLE portfolios 
ADD COLUMN margin_balance NUMERIC(16, 2) DEFAULT 0;
-- Negative = margin debt, Positive = excess cash
```

3. **Portfolio calculations:**
```python
def calculate_portfolio_metrics(positions, margin_balance):
    # Money market funds are just positions
    position_values = sum(p.market_value for p in positions)
    
    # Total equity
    net_equity = position_values + margin_balance
    
    # Leverage
    gross_exposure = sum(abs(p.market_value) for p in positions)
    leverage = gross_exposure / net_equity if net_equity > 0 else 0
    
    return {
        "gross_exposure": gross_exposure,
        "net_equity": net_equity,
        "margin_balance": margin_balance,
        "leverage": leverage
    }
```

This approach:
- Reflects real brokerage practices
- Handles negative cash (margin debt)
- Treats money markets as positions (which they are)
- Enables proper leverage calculations
- Minimal schema changes