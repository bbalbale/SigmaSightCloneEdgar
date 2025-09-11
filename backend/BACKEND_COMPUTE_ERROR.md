# Backend Compute Error Documentation

> **Last Updated**: 2025-09-11 (CACHE-FIRST + EOD TIME CHECK + DATA PROVIDER OPTIMIZATION + SQL BUG FIXED + EQUITY SYSTEM)  
> **Purpose**: Document and track all computation errors encountered during batch processing and API services  
> **Status**: 13 Issues RESOLVED ✅, 1 Issue PARTIALLY RESOLVED, 7 Issues PENDING/ACTIVE

## 🎉 Major Updates Completed (2025-09-11)

### EOD Time Check Implementation
- **Problem**: System was attempting to fetch today's incomplete market data during trading hours
- **Solution**: Added time-based check to only fetch EOD data after 4:05 PM ET
- **Implementation**:
  - Added pytz timezone check in `update_market_data_cache()`
  - Market close time set to 4:05 PM ET (16:05)
  - `skip_today` flag adjusts end_date to yesterday when market is open
  - Enhanced logging to indicate when data fetch is deferred
- **Benefits**:
  - Reduces unnecessary API calls during market hours
  - Prevents rate limit errors from repeated intraday attempts
  - Uses complete EOD data from yesterday instead of partial intraday data
  - Improves batch processing efficiency

### SIZE Factor Fixed - Switched from SLY to IWM
- **Problem**: SLY ETF had stale data from 2022-2023 (820 days old)
- **Solution**: Switched SIZE factor to IWM (Russell 2000)
- **Results**:
  - Updated `app/constants/factors.py` and `market_data_sync.py`
  - Created `fetch_iwm_data.py` script for 180-day historical fetch
  - Successfully tested with 122 regression days available
  - SIZE factor beta: 0.6462 for demo portfolio
  - All 7 active factors now working correctly

### Data Provider Optimization & Cache-First Strategy IMPLEMENTED
- **Problem**: System was making unnecessary API calls even when data existed in cache
- **Solution 1**: Modified `update_market_data_cache` to check database cache first
- **Solution 2**: Prioritized data providers by asset type:
  - Stocks: Polygon first (better coverage), FMP as fallback
  - ETFs: FMP first (more reliable), Polygon as fallback
- **Results**:
  - ~80% reduction in API calls (most data served from cache)
  - 7,647 cached records covering 51 symbols with 182 days history
  - Only 5-10 symbols need updates per batch run
- **Implementation**: Added ETF detection logic and provider prioritization in `fetch_historical_data_hybrid`

### 1. Critical SQL Join Bug (#18) RESOLVED
- **Problem**: Analytics API was returning 127x inflated values due to bad SQL join
- **Solution**: Removed join with MarketDataCache, used Position.last_price field instead
- **Results**: 
  - Values now correct: Hedge fund shows $1.9M net (was $919M inflated)
  - Short exposures properly negative: -$2.0M (was +$288M wrong sign)
  - All portfolios returning accurate data

### 2. Equity-Based Portfolio System IMPLEMENTED (2025-09-11)
- **Added**: `equity_balance` field to Portfolio model (Decimal 16,2)
- **Created**: Database migration `add_equity_balance_to_portfolio.py`
- **Updated**: Portfolio analytics service with equity-based calculations
- **Added**: API response fields for `equity_balance` and `leverage`
- **Formula**: `Cash = Equity - Long MV + |Short MV|`
- **Result**: True risk management with leverage calculations working correctly
- **Current Equity Values**:
  - Demo Individual: $600,000 (0.90x leverage)
  - Demo HNW: $2,000,000 (0.81x leverage)
  - Demo Hedge Fund: $4,000,000 (1.47x leverage)

### 3. Factor Exposure API Flexibility IMPLEMENTED (2025-09-11)
- **Problem**: API required ALL 8 factors but Short Interest had no ETF proxy
- **Solution 1**: Marked Short Interest factor as inactive in database
- **Solution 2**: Updated FactorExposureService to accept ANY available factors
- **Result**: API now works with partial factor sets (minimum: Market Beta)
- **Current State**: All 3 portfolios have 7/7 active factors and API returns data correctly

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

### Issue #1: Windows CP1252 Encoding ✅ PROPERLY RESOLVED (2025-09-11)
**Status**: ✅ **PROPERLY RESOLVED** - Scripts now handle UTF-8 internally
**Location**: Multiple Python scripts  
**Error Message**: 
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0: character maps to <undefined>
```

**Initial Workaround** (No longer needed):
```bash
# Previously required for every script run:
PYTHONIOENCODING=utf-8 uv run python <script.py>
```

**Proper Solution Applied (2025-09-11)**:
- Created `fix_utf8_encoding.py` script to add UTF-8 handling to all affected files
- Added to 9 critical scripts after imports:
```python
# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

**Files Fixed**:
- `run_batch_calculations.py` ✅
- `run_batch_with_reports.py` ✅
- `fetch_iwm_data.py` ✅
- `generate_all_reports.py` ✅
- `verify_setup.py` ✅
- `verify_demo_portfolios.py` ✅
- `test_factor_calculations.py` ✅
- `check_factor_exposures.py` ✅
- `app/batch/market_data_sync.py` ✅

**Resolution**: Scripts now run directly without PYTHONIOENCODING prefix - UTF-8 handling is built-in

---

## Market Data Issues

### Issue #2: Unexpected FMP Historical Data Format ✅ RESOLVED (Ticker Issue)
**Error**: `Unexpected FMP historical data format for ZOOM`  
**Location**: `app/services/market_data_service.py` during FMP API calls
**Status**: ✅ **RESOLVED** (2025-09-11)

**Root Cause Found**:
- **ZOOM is not a valid ticker symbol** - should be **ZM** (Zoom Video Communications)
- ZOOM was incorrectly used in seed_demo_portfolios.py line 287
- FMP API couldn't find data for non-existent ticker "ZOOM"

**Resolution Applied**:
1. Fixed seed_demo_portfolios.py: Changed ZOOM → ZM
2. Created fix_zoom_ticker.py script to update database
3. Successfully updated 1 position and deleted 1 invalid cache entry
4. Reran batch process - ZM data now fetching correctly (5 days retrieved)

**Technical Details**:
- FMP API returns unexpected JSON structure for invalid symbols
- Expected format: `{"historical": [{"date": "...", "close": ...}]}`
- For invalid tickers: Returns empty or error response
- System now correctly uses ZM ticker

### Issue #3: Missing Factor ETF Data ✅ RESOLVED (Switched to IWM)
**Status**: ✅ **RESOLVED** (2025-09-11)
**Error**: `Missing data points: {'SIZE': 2}`  
**Location**: `app/calculations/factors.py` line 45-72
**Root Cause**: SIZE factor ETF (SLY) had stale data from 2022-2023

**Investigation Findings**:
- SLY data was 820 days old (last update: 2022-2023)
- No recent data available from any provider for SLY
- Missing days were actually valid (market holidays), but data was completely stale

**Resolution Applied (2025-09-11)**:
1. **Switched SIZE factor from SLY to IWM (Russell 2000)**
   - Updated `app/constants/factors.py`: Changed SIZE ETF from "SLY" to "IWM"
   - Updated `app/batch/market_data_sync.py`: Changed factor_etfs list
2. **Created IWM data fetch script** (`scripts/fetch_iwm_data.py`)
   - Fetches 180 days of history (150 + 30 day buffer)
   - Successfully retrieved and cached IWM data
3. **Tested factor calculations with IWM**
   - All factor calculations working correctly
   - SIZE factor beta: 0.6462 for demo portfolio
   - 122 regression days available (sufficient for calculations)

**Technical Details**:
- Factor regression requires 150 days minimum (REGRESSION_WINDOW_DAYS)
- IWM (Russell 2000) is a better SIZE factor proxy than SLY
- IWM has current data with good liquidity and coverage

**Impact**: 
- ✅ SIZE factor exposures now calculated accurately for all positions
- ✅ Factor attribution complete for portfolio risk analysis
- ✅ All 7 active factors working properly

### Issue #4: Insufficient Historical Data for Options & New Stocks
**Error Messages**:
```
❌ SLY: 0 days (needs 150 more)
❌ ZM: 5 days (needs 145 more)
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

**Why We Can't Get Prior 145 Days**:

1. **Options Contracts - Fundamental Limitation**:
   - Options have **expiration dates** embedded in their symbols (e.g., SPY250919C00460000 expires 2025-09-19)
   - They are **created when first traded**, not 150 days in advance
   - Historical data literally doesn't exist before the contract was listed
   - Example: SPY250919C00460000 might have been created on 2025-09-10, so only 1 day of data exists
   - **This is NOT a data provider issue** - the data doesn't exist anywhere

2. **ZM (Zoom) - Recent Data Only**:
   - After fixing ZOOM → ZM ticker, we now get data
   - But only 5 days available (needs 145 more)
   - Possible reasons:
     - Our API plan may have limited historical depth
     - FMP free/basic tier often limits to 5 days
     - Need premium tier for 150+ days of history

**Technical Details**:
- Volatility calculation needs 150 days for statistical significance:
  ```python
  # Need 150 days of underlying price history
  returns = underlying_prices.pct_change()
  volatility = returns.std() * sqrt(252)  # Annualized
  ```
- Options with 1 day history = just started trading
- Can't "backfill" option prices - they didn't exist

**Why This Matters**:
- Can't calculate implied volatility without historical volatility baseline
- Greeks (Delta, Gamma, Vega, Theta) require volatility input
- Black-Scholes model needs: S, K, r, T, σ (missing σ)

**Workaround Options**:
1. **Use underlying stock's volatility** (SPY volatility for SPY options)
2. **Use VIX as volatility proxy** for index options
3. **Use similar option's implied volatility** if available
4. **Upgrade API plan** for more historical data on stocks
5. **Accept limited calculations** for new options

**Impact**: 
- 8 option positions (~25% of hedge fund) lack Greeks
- Risk metrics incomplete for derivatives
- Hedge effectiveness cannot be measured
- ZM position missing factor exposures

### Issue #5: Low FMP Stock Data Success Rate ✅ RESOLVED
**Status**: ✅ **RESOLVED** (2025-09-11)
**Error**: `FMP stock success rate low (50.0%), using Polygon fallback for failed symbols`  
**Location**: `app/services/market_data_service.py` FMP batch fetch

**Resolution Applied**:
1. **Cache-First Strategy** - System checks database cache before API calls (~80% reduction)
2. **Data Provider Prioritization** - ETFs use FMP first, stocks use Polygon first
3. **EOD Time Check** - Only fetches after 4:05 PM ET, reducing unnecessary attempts
4. **Expected Behavior** - 50% FMP success rate is normal since options aren't supported

**Technical Details**:
- Options symbols correctly fall back to Polygon (by design)
- Mutual funds and special tickers handled by fallback mechanism
- Cache-first prevents repeated failures for same symbols
- Provider prioritization reduces initial failures

**Original Impact** (Now Resolved): 
- ~~Doubles API call volume~~ → Cache eliminates 80%+ of calls
- ~~Increases processing time~~ → Provider prioritization speeds up fetching
- ~~May hit rate limits~~ → Dramatically reduced with cache + EOD check

---

## Database Table Issues

### Issue #6: Factor Exposures Incomplete Factor Sets ✅ RESOLVED
**Status**: ✅ **RESOLVED** (2025-09-11)
**Error**: ~~Factor exposures API returns `"available": false` with `"no_complete_set"`~~  
**Location**: `/api/v1/analytics/portfolio/{id}/factor-exposures` endpoint  
**Root Cause**: ~~API requires ALL 8 active style factors - missing "Short Interest" factor~~

**Solution Applied**:
1. Marked Short Interest factor as `is_active = false` in database
2. Updated FactorExposureService to accept ANY available factors (not require all)
3. API now flexible: works with 1-7 factors (Market Beta is minimum)

**Current Data State (UPDATED 2025-09-11)**:
- ✅ Individual portfolio: 7/7 active factors (API works)
- ✅ HNW portfolio: 7/7 active factors (API works)
- ✅ Hedge Fund portfolio: 7/7 active factors (API works)
- All portfolios show `"completeness": "complete"` with Market Beta available

**Impact**: Factor exposure API now works for all portfolios with flexible factor requirements

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

### Issue #15: Polygon API Rate Limits (IMPROVED with Cache-First)
**Error**: `HTTPSConnectionPool(host='api.polygon.io', port=443): Max retries exceeded with url: /v2/aggs/ticker/SPY250919C00460000/range/1/day/2025-09-05/2025-09-10?adjusted=true&sort=asc&limit=50000 (Caused by ResponseError('too many 429 error responses'))`  
**Location**: `app/services/market_data_service.py` Polygon API client
**Rate Limit**: 5 requests/minute on free tier
**Status**: ⚠️ **PARTIALLY RESOLVED** (2025-09-11)

**Cache-First Implementation Added (2025-09-11)**:
- ✅ Modified `update_market_data_cache` to check database cache first
- ✅ Only fetches data for symbols with missing dates
- ✅ Tracks `api_calls_saved` metric
- ✅ Reduces API calls by ~80% for symbols with complete data

**Implementation Details**:
```python
# NEW: Cache-aware approach (implemented)
async def update_market_data_cache(self, db, symbols, days_back=5):
    symbols_needing_data = []
    cached_count = 0
    
    # Check what data we already have cached
    for symbol in symbols:
        cached_dates = await self._get_cached_dates(db, symbol)
        missing_dates = self._find_missing_dates(cached_dates, days_back)
        
        if missing_dates:
            symbols_needing_data.append(symbol)
        else:
            cached_count += 1
            logger.info(f"✓ {symbol}: Using cached data (no API call needed)")
    
    if not symbols_needing_data:
        logger.info("All symbols have complete cached data, skipping API calls")
        return {..., 'api_calls_saved': len(symbols)}
    
    # Only fetch for symbols with missing data
    return await self.bulk_fetch_and_cache(db, symbols_needing_data, days_back)
```

**Results**:
- Database has 7,647 cached records covering 51 symbols
- Most symbols have 182 days of history
- Only 5-10 symbols typically need updates per batch
- API calls reduced from ~50 to ~5-10 per batch run

**Remaining Issues**:
- Still hits rate limits for symbols needing updates (MSFT, PG, JPM, F, BRK-B)
- Options contracts with minimal history still problematic
- Need to implement sequential fetching with delays for remaining API calls

**Impact**: 
- ✅ Most data now served from cache (no API calls)
- ⚠️ Some symbols still trigger rate limits when updating
- Overall batch processing time improved significantly

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
   
   **Option C: Disable Short Interest Factor** ✅ **IMPLEMENTED**
   ```sql
   UPDATE factor_definitions SET is_active = false WHERE name = 'Short Interest';
   ```
   
   **Additional Fix Applied**: Updated FactorExposureService to be flexible:
   - Changed from requiring ALL active factors to accepting ANY available factors
   - Minimum requirement: at least one factor (preferably Market Beta)
   - Returns metadata showing completeness and factor count

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

## Equity System Implementation Details (2025-09-11)

### Files Modified
1. **`app/models/users.py`**: Added `equity_balance` field to Portfolio model
2. **`alembic/versions/add_equity_balance_to_portfolio.py`**: Created migration
3. **`app/services/portfolio_analytics_service.py`**: Updated calculations to use equity
4. **`app/schemas/analytics.py`**: Added equity_balance and leverage to response model
5. **`scripts/update_equity_values.py`**: Script to update equity values
6. **`scripts/test_equity_calculations.py`**: Comprehensive test script

### Test Results
All three portfolios now correctly calculate:
- ✅ Equity balances match database values
- ✅ Cash balances calculated correctly using formula
- ✅ Leverage ratios accurate (gross exposure / equity)
- ✅ API returns equity_balance and leverage fields

### Migration Applied
```sql
ALTER TABLE portfolios ADD COLUMN equity_balance NUMERIC(16, 2);
UPDATE portfolios SET equity_balance = CASE 
    WHEN id = '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe' THEN 600000.00
    WHEN id = 'e23ab931-a033-edfe-ed4f-9d02474780b4' THEN 2000000.00
    WHEN id = 'fcd71196-e93e-f000-5a74-31a9eead3118' THEN 4000000.00
END;
```

## Summary of Issue Status (2025-09-11)

### ✅ RESOLVED Issues (13)
1. **SQL Join Bug (#18)** - Analytics API now returns correct values
2. **Equity System** - Full equity-based calculations implemented and working
3. **Factor Exposure API (#6)** - Fixed with flexible factor requirements
4. **Incomplete Portfolio Processing (#1)** - All 3 portfolios have calculation data
5. **Unicode Encoding (#1)** - Scripts run with UTF-8 encoding
6. **Portfolio ID Mismatches (#9)** - Correct IDs in all scripts
7. **Batch Orchestrator Methods (#10)** - Using correct method names
8. **Portfolio Data Discovery (#20)** - Documented hardcoded data source
9. **ZOOM Ticker Error (#2)** - Fixed ZOOM→ZM, database updated, batch rerun successful
10. **Cache-First Data Fetching** - System checks database cache before API calls
11. **Missing Factor ETF Data (#3)** - Switched SIZE factor from SLY to IWM, now working
12. **EOD Time Check** - Only fetches market data after 4:05 PM ET market close
13. **Low FMP Stock Data Success Rate (#5)** - Resolved via cache-first + provider prioritization

### ⚠️ PARTIALLY RESOLVED Issues (1)
1. **Rate Limiting (#15)** - Cache-first + EOD time check reduces API calls by ~90%, minimal rate limit issues remain

### 🔴 PENDING/ACTIVE Issues (7)
1. **Frontend Short Position (#19)** - Frontend hardcodes shortValue = 0
2. **Missing Database Tables (#7)** - stress_test_results table doesn't exist
3. **Insufficient Options Data (#4)** - Options need 150 days history (fundamental limitation)
4. **Table Name Mismatch (#8)** - position_correlations vs pairwise_correlations
5. **Beta Capping (#11)** - Extreme betas being capped at ±3.0
6. **Missing Interest Rate Factor (#12)** - Factor name mismatch in stress tests
7. **Excessive Stress Loss (#13)** - Losses exceed 99% of portfolio
8. **Pandas Deprecation (#14)** - Need to update pct_change() calls

## Notes

- All errors documented from batch run on 2025-09-10
- Analytics API investigation completed 2025-09-10
- Portfolio data source discovery completed 2025-09-11
- Frontend best practices documented 2025-09-11
- **SQL Join Bug (#18) RESOLVED 2025-09-11**: Analytics API now returns correct values
- **Equity System IMPLEMENTED 2025-09-11**: Full equity-based calculations working
- Backend server running on Windows (CP1252 encoding issues)
- Database: PostgreSQL 15 in Docker container
- Python version: 3.11.13
- The system is functional with major bugs fixed, minor issues remain

---

## Priority Matrix

| Priority | Issue | Impact | Effort | Status |
|----------|-------|--------|--------|--------|
| ✅ | Analytics API SQL join bug (#18) | ~~CRITICAL - Analytics API returns wrong values~~ | ~~LOW - Fix SQL query~~ | ✅ **RESOLVED** |
| ✅ | Equity-based portfolio system | ~~CRITICAL - No leverage/cash calculations~~ | ~~MEDIUM - Add equity field~~ | ✅ **IMPLEMENTED** |
| P0 | Frontend short position assumption (#19) | CRITICAL - Wrong exposures for hedge fund | LOW - Calculate from data | **PENDING** |
| P1 | Missing database tables (#7) | HIGH - Stress tests unavailable | MEDIUM - Create migrations | **PENDING** |
| P2 | Rate limiting issues (#15,#16) | MEDIUM - Slow processing | HIGH - Implement retry logic | **ACTIVE** |
| P2 | Insufficient options data (#4) | MEDIUM - Options calc fail | HIGH - Historical backfill | **PENDING** |
| P3 | Portfolio data hardcoded (#20) | LOW - Works but inflexible | MEDIUM - Externalize data | **DOCUMENTED** |
| P3 | Pandas deprecation (#14) | LOW - Future issue | LOW - Update code | **PENDING** |
| P3 | Beta capping warnings (#11) | LOW - Working as designed | LOW - Adjust thresholds | **MONITORING** |
| ✅ | Incomplete portfolio processing (#1) | ~~HIGH - No data for 2/3 portfolios~~ | ~~LOW - Run batch again~~ | ✅ **RESOLVED** |
| ✅ | Unicode encoding errors (#1) | ~~HIGH - Scripts fail to run~~ | ~~LOW - Add env variable~~ | ✅ **RESOLVED** |
| ✅ | Portfolio ID mismatches (#9) | ~~HIGH - Batch jobs fail~~ | ~~LOW - Update scripts~~ | ✅ **RESOLVED** |

---

## Equity-Based Portfolio Calculation Plan ✅ IMPLEMENTED (2025-09-11)

### Problem Statement (RESOLVED)
~~Currently, portfolio totals are calculated by summing position values, which doesn't account for:~~
- ~~Cash balances (positive or negative/margin)~~
- ~~True equity (NAV)~~
- ~~Leverage ratios~~
- ~~Risk metrics for long/short portfolios~~

### Solution: Equity-First Model ✅ IMPLEMENTED

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

#### Implementation Plan ✅ ALL PHASES COMPLETED

**Phase 1: Database Changes** ✅ COMPLETED
1. ✅ Added `equity_balance` field to Portfolio model (Decimal 16,2)
2. ✅ Created Alembic migration `add_equity_balance_to_portfolio.py`
3. ✅ Set actual values:
   - Demo Individual: $600,000
   - Demo HNW: $2,000,000
   - Demo Hedge Fund: $4,000,000

**Phase 2: Update Analytics Service** ✅ COMPLETED
- ✅ Updated `portfolio_analytics_service.py` with equity-based calculations
- ✅ Cash calculated using formula: `Cash = Equity - Long MV + |Short MV|`
- ✅ Leverage calculated as: `Gross Exposure / Equity`
- ✅ Portfolio total now equals equity (not sum of positions)

**Phase 3: API Endpoints** ✅ COMPLETED
- ✅ Added equity_balance and leverage to `/analytics/portfolio/{id}/overview` response
- ✅ Updated PortfolioOverviewResponse schema in `analytics.py`
- ✅ API now returns:
  - equity_balance (user-provided NAV)
  - cash_balance (calculated)
  - leverage ratio (gross/equity)

**Phase 4: Risk Metrics** ✅ COMPLETED
- ✅ Leverage calculations working correctly:
  - Demo Individual: 0.90x (conservative)
  - Demo HNW: 0.81x (conservative)
  - Demo Hedge Fund: 1.47x (moderate leverage)
- ✅ Cash balances properly calculated including margin

#### Example Calculations ✅ VERIFIED

**Demo Individual (Equity: $600k)** ✅ WORKING
- Long: $542k, Short: $0
- Cash: $600k - $542k + $0 = $58k (positive cash)
- Leverage: 0.90x (unleveraged)

**Demo HNW (Equity: $2M)** ✅ WORKING
- Long: $1.63M, Short: $0
- Cash: $2M - $1.63M + $0 = $374k (positive cash)
- Leverage: 0.81x (unleveraged)

**Demo Hedge Fund (Equity: $4M)** ✅ WORKING
- Long: $3.9M, Short: -$2.0M
- Cash: $4M - $3.9M + $2M = $2.1M (positive cash)
- Gross: $5.9M
- Leverage: 1.47x (moderate leverage)

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
│ ✅ equity_balance: NUMERIC(16,2) (added 2025-09-11)             │
│ SOURCE: 🔧 DEMO DATA (seed_demo_portfolios.py)                  │
│ - 3 hardcoded portfolios with equity values:                    │
│   • Individual: $600,000 equity → 0.90x leverage                │
│   • HNW: $2,000,000 equity → 0.81x leverage                    │
│   • Hedge Fund: $4,000,000 equity → 1.47x leverage             │
│ - Cash calculated: Cash = Equity - Long MV + |Short MV|         │
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
          │ ✅ NO LONGER JOINED! (Fixed 2025-09-11)
          │ Analytics service now uses Position.last_price
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
│ ✅ FIXED: Analytics no longer joins this table                  │
│ ✅ Position.last_price updated by batch jobs instead            │
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