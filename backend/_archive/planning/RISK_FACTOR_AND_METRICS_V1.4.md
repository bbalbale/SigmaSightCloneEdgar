# Risk Factor Analysis Implementation Planning (V1.4)
## Section 1.4.4 Design Document

> ⚠️ **IMPLEMENTATION STATUS (2025-08-26 15:40 PST)**: Risk Factor Analysis has been fully implemented as part of Phase 1. See [TODO1.md](../../TODO1.md) Section 1.5 for completion details. Factor exposures are calculated and stored in the database.

**Created:** 2025-07-17  
**Updated:** 2025-08-04  
**Purpose:** Planning document for Risk Factor Analysis implementation  
**Dependencies:** Sections 1.4.1, 1.4.2, 1.4.3 (all completed)

---

## Document Scope

This document covers the planning and design decisions for implementing Risk Factor Analysis (Section 1.4.4) in V1.4.

### **Section 1.4.4: Risk Factor Analysis (V1.4 Scope)**
- 7-factor model implementation with ETF proxies (excluding Short Interest)
- Factor beta calculations using regression analysis
- Portfolio-level factor exposure aggregation
- Integration with existing portfolio aggregation functions

**IMPORTANT UPDATE:** Section 1.4.5 (Risk Metrics) has been postponed to V1.5. See the "Postponed Features" section at the end of this document.

---

# SECTION 1.4.4: RISK FACTOR ANALYSIS (V1.4 IMPLEMENTATION)

## 1. Factor Model Architecture

### Q1.1: Factor Return Data Source & Calculation Method
**DECISION:**
- Calculate factor returns from ETF price changes for 7 factors with ETF proxies:
  - Market (SPY)
  - Value (VTV)
  - Growth (VUG)
  - Momentum (MTUM)
  - Quality (QUAL)
  - Size (SIZE)
  - Low Volatility (USMV)
- Short Interest factor is POSTPONED to V1.5

### Q1.2: Factor Beta Calculation Window
**DECISION:**
- Use 252-day (12-month) window for factor beta calculations for better forward-looking prediction
- 12-month timeframe provides more stable relationships and predictive power
- Configuration capability will be added in future versions

### Q1.3: Position vs Portfolio Level Betas
**DECISION:**
- Calculate position-level betas first, then aggregate to portfolio level
- This provides position-level granularity for detailed analysis
- Portfolio-level betas derived from position-level calculations

## 2. Data Requirements & Sources

### Q2.1: Historical Return Data Calculation
**DECISION:**
- Use exposure-based returns (accounts for position size changes)
- For stocks: use dollar exposure (signed: quantity × price × multiplier)
- For options: configurable exposure type via `use_delta_adjusted` parameter:
  - **Option A (default):** Dollar exposure (signed: quantity × price × multiplier)
  - **Option B:** Delta-adjusted exposure (signed: dollar_exposure × delta)
- Backend supports both exposure types for factor regression calculations
- Frontend can toggle between "include options" or "exclude options" (future)

### Q2.2: Missing Data Handling
**DECISIONS:**
- Scenario 1: New positions with <60 day history → Skip factor calculation, return zeros with quality flag
- Scenario 2: Missing market data → Skip calculations for that day, log warning
- Scenario 3: ETF proxy data gaps → Skip that day from regression, require minimum 60 days (3 months)
- Scenario 4: Complete data failure → Return error, do NOT fallback to mock factor exposures
- Scenario 5: Market holidays/weekend gaps → Skip data pull and calculations for that day
- Scenario 6: Corporate actions/stock splits → Use adjusted close prices from Polygon (they handle splits/dividends)

### Q2.3: Factor Return Data Storage
**DECISION:**
- Calculate factor returns from ETF prices on-demand
- No pre-calculation or caching of factor returns

### Q2.4: Missing Data Handling Strategy
**DECISION:**
- Require minimum 60 trading days for regression (3-month minimum for 12-month window)
- Log warning for positions with limited history
- Include data quality flag in response
- Graceful degradation rather than hard failure

## 3. Calculation Implementation

### Q3.1: Regression Library Choice
**DECISION:**
- Use statsmodels OLS regression
- Matches legacy implementation
- Provides statistical significance metrics
- Industry standard for financial factor models
- Already included in project dependencies

### Q3.2: Portfolio Beta Aggregation Method
**DECISION:**
- Use exposure-weighted average for aggregation
- Standard practice in portfolio management
- Reflects true portfolio risk exposure
- Consistent with Section 1.4.3 aggregation methods

### Q3.4: Outlier Handling for Factor Betas
**DECISION:**
- Cap factor betas at ±3 to prevent extreme outliers
- Maintains mathematical interpretability
- Simple to implement and explain
- Can be made configurable in future versions

## 4. Database & Storage

### Q4.1: Factor Exposure Storage Strategy
**DECISION:**
- Store factor exposures daily in database
- Consistent with portfolio snapshot approach
- Enables historical factor analysis
- Database schema already supports this

### Q4.2: Position-Level Factor Storage
**DECISION:**
- Store portfolio-level factor exposures and position-level factor exposures

## 5. Performance & Caching

### Q5.1: Calculation Performance Targets
**DECISION:**
- Individual portfolio: <30 seconds for factor calculation
- Batch processing: <10 minutes for all portfolios
- API response: <5 seconds for cached results
- Timeout: 60 seconds max per portfolio

### Q5.2: Caching Strategy
**DECISION:**
- Use 24-hour cache TTL for factor calculations
- Factor exposures change slowly
- Expensive calculations justify longer cache
- Daily batch job refreshes cache anyway

### Q5.3: Real-time vs Batch Calculation Trade-offs
**DECISION:**
- Use batch-first approach for all factor calculations
- API serves cached results from daily batch
- Real-time triggers can be added later if needed
- Optimize for reliability over latency

## 6. Integration & API

### Q6.1: API Endpoint Design
**DECISION:**
- API endpoints under `/api/v1/risk/factors/...`
- GET `/exposures` - Portfolio factor exposures
- GET `/definitions` - Available factors
- POST `/calculate` - Trigger calculation
- GET `/history` - Historical factor exposures

### Q6.2: Batch Job Integration
**DECISION:**
- Run factor calculation job at 5:15 PM daily
- After market data update (4 PM)
- Before portfolio snapshots (5:30 PM)
- Separate job for better error isolation

## 7. Testing & Validation

### Q7.1: Regression Testing Strategy
**DECISION:**
- Unit tests with synthetic data (known factor relationships)
- Integration tests with historical ETF data
- Manual testing scripts for validation

### Q7.2: Data Quality Monitoring
**DECISION:**
- Add quality_score field to calculation results
- Log warnings for suspicious data patterns
- Include diagnostic stats in metadata
- Don't block calculations, just flag issues

## 8. Implementation Functions Specification

Based on the decisions above, here are the required functions for V1.4:

### `calculate_factor_betas_hybrid(portfolio_id: UUID, calculation_date: date, use_delta_adjusted: bool = False) -> Dict[str, Decimal]`
- **Input:** Portfolio ID, calculation date, and exposure type option
- **Process:** Fetch 252-day returns, calculate regression betas for 7 factors
- **Output:** Dictionary mapping factor names to beta values
- **Exposure Types:** 
  - `use_delta_adjusted=False`: Dollar exposure (quantity × price × multiplier)
  - `use_delta_adjusted=True`: Delta-adjusted exposure (dollar_exposure × delta)
- **Dependencies:** Market data service, factor definitions, Greeks (if delta-adjusted)
- **Minimum Data:** 60 trading days required for calculation
- **File:** `app/calculations/factors.py`

### `fetch_factor_returns(symbols: List[str], start_date: date, end_date: date) -> pd.DataFrame`
- **Input:** Factor ETF symbols and date range
- **Process:** Fetch ETF historical prices, calculate daily returns
- **Output:** DataFrame with factor returns
- **Dependencies:** MarketDataService
- **File:** `app/calculations/factors.py`

### `calculate_position_returns(portfolio_id: UUID, start_date: date, end_date: date, use_delta_adjusted: bool = False) -> pd.DataFrame`
- **Input:** Portfolio ID, date range, and exposure type option
- **Process:** Calculate daily position returns from exposure changes
- **Output:** DataFrame with position returns
- **Exposure Types:** 
  - `use_delta_adjusted=False`: Returns based on dollar exposure changes
  - `use_delta_adjusted=True`: Returns based on delta-adjusted exposure changes
- **Dependencies:** Position data, market data, Greeks (if delta-adjusted)
- **File:** `app/calculations/factors.py`

### `store_position_factor_exposures(position_betas: Dict, calculation_date: date) -> None`
- **Input:** Position-level betas dictionary and calculation date
- **Process:** Store individual position factor exposures in database
- **Output:** Records stored in `position_factor_exposures` table
- **Storage:** One record per position per factor per date
- **Dependencies:** Database session, position IDs
- **File:** `app/calculations/factors.py`

### `aggregate_portfolio_factor_exposures(position_betas: Dict, portfolio_exposures: Dict) -> Dict[str, Decimal]`
- **Input:** Position-level betas and current portfolio exposures
- **Process:** Exposure-weighted aggregation to portfolio level
- **Output:** Portfolio factor exposures stored in `factor_exposures` table
- **Dependencies:** Portfolio aggregation from Section 1.4.3
- **File:** `app/calculations/factors.py`

## 9. Implementation Timeline

### Phase 1: Core Implementation (3-4 days)
1. **Day 1:** Factor return calculation and data fetching
2. **Day 2:** Position return calculation and regression functions
3. **Day 3:** Portfolio aggregation and database integration
4. **Day 4:** Testing and validation

### Phase 2: Integration (1-2 days)
1. **Day 5:** Batch job integration and API endpoints
2. **Day 6:** Performance optimization and error handling

### Total Estimate: 5-6 days for Section 1.4.4 completion

---

## 10. Implementation Decisions

The following implementation decisions have been made:

### 10.1: Batch Job Runtime Environment
**DECISION:** Use APScheduler
- Runs within the FastAPI application
- No additional infrastructure required
- Simple to implement and test locally
- Sufficient for V1.4 daily batch job needs

### 10.2: Database Schema for Factor Exposures
**DECISION:** Implement dual-level storage (both position and portfolio level)
- **Position-level:** New `position_factor_exposures` table for detailed analysis
  - Fields: position_id, factor_id, calculation_date, exposure_value
  - Enables drill-down analysis and debugging
  - One record per position per factor per date
- **Portfolio-level:** Existing `factor_exposures` table for aggregated views
  - Fields: portfolio_id, factor_id, calculation_date, exposure_value  
  - Enables fast portfolio-level queries and reporting
  - Aggregated from position-level data using exposure weighting
- **Benefits:** Maximum flexibility for both detailed analysis and fast reporting

### 10.3: API Error-Handling Conventions
**DECISION:** Follow existing FastAPI HTTPException pattern
- Use standard HTTP status codes:
  - 400: Bad Request (invalid parameters)
  - 401: Unauthorized (authentication required)
  - 404: Not Found (portfolio/data not found)
  - 500: Internal Server Error (calculation failures)
- Error format: `{"detail": "Error message"}`
- Log full error details server-side
- Keep client-facing messages concise and secure

### 10.4: Configuration Parameters
**DECISION:** Use centralized config with two tiers
- **Environment variables** (via .env/settings):
  - FACTOR_CACHE_TTL (default: 86400 seconds)
  - FACTOR_CALCULATION_TIMEOUT (default: 60 seconds)
  - BATCH_JOB_ENABLED (default: true)
  - FACTOR_USE_DELTA_ADJUSTED (default: false)
- **Config constants** (in app/constants/factors.py):
  - REGRESSION_WINDOW_DAYS = 150  # 6-month window (previously 252d/12-month, changed due to data feed limitations)
  - MIN_REGRESSION_DAYS = 60      # 3-month minimum
  - BETA_CAP_LIMIT = 3.0
  - FACTOR_JOB_SCHEDULE = "0 17 15 * * *"  # 5:15 PM daily
  - POSITION_CHUNK_SIZE = 1000
- No magic numbers scattered in code
- All config values in one place for easy review/modification

### 10.5: Large Portfolio Handling
**DECISION:** Process in chunks
- Chunk positions into batches of 1000
- Calculate factors for each batch independently
- Aggregate results at portfolio level
- Benefits:
  - Maintains <30 second target even for large portfolios
  - Reasonable memory usage
  - Allows progress tracking/logging
  - Graceful handling of very large portfolios
- Add POSITION_CHUNK_SIZE = 1000 to config constants

---

# POSTPONED FEATURES (V1.5 AND BEYOND)

The following features have been postponed to reduce scope and complexity for V1.4:

## Section 1.4.5: Risk Metrics (ENTIRE SECTION POSTPONED)

### Postponed Risk Metrics Features:
1. **Portfolio VaR Calculations**
   - Factor model VaR using matrix multiplication
   - 95% and 99% confidence levels
   - Requires factor covariance matrix (also postponed)

2. **Empyrical Risk Metrics**
   - Sharpe ratio
   - Maximum drawdown
   - Volatility
   - Historical VaR
   - Other performance metrics

3. **Portfolio Return Calculations**
   - Historical return series generation
   - 252-day lookback window
   - Integration with risk metrics

4. **Risk-Free Rate Integration**
   - Dynamic Treasury rate fetching
   - Integration with Sharpe ratio calculations

## Factor Model Enhancements (Postponed)

### 1. Factor Covariance Matrix
- **What:** Real factor correlations instead of identity matrix
- **Why postponed:** Requires significant historical analysis and adds complexity
- **V1.4 workaround:** Not needed without VaR calculations

### 2. Short Interest Factor (8th Factor)
- **What:** Implementation of Short Interest as 8th factor
- **Why postponed:** No ETF proxy available, requires alternative data source
- **V1.4 workaround:** 7-factor model is sufficient for initial release

### 3. Greeks Integration with Factor Models ✅ IMPLEMENTED IN V1.4
- **What:** Optional delta-adjusted exposures for options in factor calculations
- **Implementation:** `use_delta_adjusted` parameter in factor calculation functions
- **Default:** Dollar exposure (false), but delta-adjusted available when needed

### 4. Correlation Stability Monitoring
- **What:** Time-varying correlations between factors
- **Why postponed:** Requires factor covariance matrix implementation
- **V1.4 workaround:** Not applicable without covariance matrix

## Additional Postponed Features

### 1. Factor Attribution Reporting
- Shows which factors drove portfolio performance
- Requires return decomposition logic

### 2. Stress Testing Scenarios
- Pre-defined market stress scenarios
- Tail risk analysis beyond VaR

### 3. Benchmark-Relative Risk Metrics
- Tracking error and information ratio
- Requires benchmark selection and integration

### 4. Multi-Currency Support
- FX risk factors and currency hedging
- International portfolio support

### 5. Position-Level Factor Storage
- Detailed factor exposures for each position
- Would require new database table

### 6. Real-Time Factor Calculations
- On-demand factor updates throughout the day
- Would require significant performance optimization

---

## Summary of V1.4 Scope

**What we ARE implementing in V1.4:**
- 7-factor model with ETF proxies
- Daily factor beta calculations via batch job
- Portfolio-level factor exposure storage
- Basic API endpoints for factor data retrieval
- 252-day regression window with 60-day minimum
- Quality flags for data issues
- Configurable exposure types (dollar vs delta-adjusted) for options
- Greeks integration for delta-adjusted calculations
- Position-level factor exposure storage in database
- Portfolio-level factor exposure aggregation

**What we are NOT implementing in V1.4:**
- Any risk metrics (VaR, Sharpe, drawdown, etc.)
- Factor covariance matrix
- Short Interest factor (8th factor)
- Real-time calculations

**Next Steps:** 
1. Review and resolve open questions in Section 10
2. Update TODO.md to reflect these decisions
3. Proceed with Section 1.4.4 implementation only