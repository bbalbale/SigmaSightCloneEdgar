  Problem with Current Schema

  The MarketDataCache table is designed for daily price data (OHLCV), not company profiles:
  - Has date field for each day's prices
  - Has unique constraint on (symbol, date)
  - Company info (sector, industry) is duplicated across every date row for the same symbol

  This is inefficient - company_name doesn't change daily, but would be stored thousands of times.      

  Recommended Approach: Create Separate CompanyProfiles Table

  Option 1: New Table (RECOMMENDED)
  class CompanyProfile(Base):
      """Company profile information - relatively static company metadata"""
      __tablename__ = "company_profiles"

      symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
      company_name: Mapped[Optional[str]] = mapped_column(String(200))
      sector: Mapped[Optional[str]] = mapped_column(String(100))
      industry: Mapped[Optional[str]] = mapped_column(String(100))
      exchange: Mapped[Optional[str]] = mapped_column(String(20))
      country: Mapped[Optional[str]] = mapped_column(String(10))
      market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
      description: Mapped[Optional[str]] = mapped_column(Text)  # Long text

      # Company type flags
      is_etf: Mapped[bool] = mapped_column(default=False)
      is_fund: Mapped[bool] = mapped_column(default=False)

      # Company details
      ceo: Mapped[Optional[str]] = mapped_column(String(100))
      employees: Mapped[Optional[int]]
      website: Mapped[Optional[str]] = mapped_column(String(200))

      # Valuation metrics (updated periodically)
      pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
      forward_pe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
      dividend_yield: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
      beta: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
      week_52_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      week_52_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

      # Analyst estimates and targets
      target_mean_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      target_high_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      target_low_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      number_of_analyst_opinions: Mapped[Optional[int]]
      recommendation_mean: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))  # 1-5 scale
      recommendation_key: Mapped[Optional[str]] = mapped_column(String(20))  # "buy", "hold", "sell"

      # Forward estimates
      forward_eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      earnings_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))  # As decimal
      revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))  # As decimal
      earnings_quarterly_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))

      # Profitability metrics
      profit_margins: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
      operating_margins: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
      gross_margins: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
      return_on_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
      return_on_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
      total_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))  # TTM

      # Current year estimates (0y period) - NEW from yahooquery!
      current_year_revenue_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
      current_year_revenue_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
      current_year_revenue_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
      current_year_revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
      current_year_earnings_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      current_year_earnings_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      current_year_earnings_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      current_year_end_date: Mapped[Optional[date]] = mapped_column(Date)

      # Next year estimates (+1y period) - NEW from yahooquery!
      next_year_revenue_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
      next_year_revenue_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
      next_year_revenue_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
      next_year_revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
      next_year_earnings_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      next_year_earnings_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      next_year_earnings_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
      next_year_end_date: Mapped[Optional[date]] = mapped_column(Date)

      # Data tracking
      data_source: Mapped[str] = mapped_column(String(50), default='yahooquery')
      last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True))
      created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
      updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

  Why separate table?
  - Company names don't change often
  - No need to duplicate across thousands of daily price rows
  - Can update profile data independently from price data
  - Better performance for lookups

  Option 2: Add to MarketDataCache (NOT RECOMMENDED)
  - Would add company_name column to existing table
  - Company name would be duplicated for every date row
  - Wasteful storage and harder to update

  What We Need to Do

  1. Create new database table via Alembic migration
  2. Modify market data service to fetch and cache company profiles
  3. Update /positions/details endpoint to join with company_profiles and include company_name
  4. Frontend already ready - it's looking for position.name field

  This would give us:
  - Proper company names for all positions (stocks, ETFs, etc.)
  - Company stock beta (market volatility metric)
  - Analyst price targets and recommendations
  - Forward earnings and revenue growth estimates
  - Profitability metrics (margins, ROA, ROE)
  - Additional company data (sector, industry, description, CEO, etc.)
  - Efficient storage (one row per symbol, not per date)
  - Easy to update profiles independently

  ## Implementation Plan: Add CompanyProfile Table (Phased Approach)

  ### Strategy: Incremental Implementation

  **Phase 1 (NOW)**: Create CompanyProfile table + use yahooquery for company profiles ONLY
  - Low risk - isolated change
  - Gets revenue estimates and comprehensive company data
  - yfinance continues handling prices, historical data, everything else
  - Test yahooquery reliability in production with limited scope

  **Phase 2 (FUTURE)**: Optionally migrate fully from yfinance to yahooquery
  - Only if Phase 1 proves yahooquery is reliable
  - Only if full migration benefits are needed
  - Can be done on your timeline

  ### Overview
  Create a new `company_profiles` table to store comprehensive company metadata (including revenue estimates from yahooquery) separately from daily price data. This solves the missing company names issue and provides rich fundamental data for future features.

  **Data Sources:**
  - yahooquery: Company profiles, revenue/earnings estimates (NEW - Phase 1)
  - yfinance: Prices, historical data, options (UNCHANGED - continues working)

  **Data Categories:**
  - Basic company info (name, sector, industry, description)
  - Valuation metrics (P/E ratios, beta, dividend yield)
  - Analyst coverage (price targets, recommendations)
  - Growth estimates (earnings/revenue projections)
  - **Current year estimates (0y)** - Revenue and earnings for current fiscal year ← **NEW from yahooquery**
  - **Next year estimates (+1y)** - Revenue and earnings for next fiscal year ← **NEW from yahooquery**
  - Profitability metrics (margins, ROA, ROE)
  - Fiscal year end dates for proper time tracking

  ### Phase 1: Database Schema (Backend)

  #### 1.1 Create CompanyProfile Model
  **File**: `backend/app/models/market_data.py`
  - Add new `CompanyProfile` class after existing models
  - **Basic Fields**: symbol (PK), company_name, sector, industry, exchange, country, market_cap, description, is_etf, is_fund, ceo, employees, website
  - **Valuation Metrics**: pe_ratio, forward_pe, dividend_yield, beta, week_52_high, week_52_low
  - **Analyst Estimates**: target_mean_price, target_high_price, target_low_price, number_of_analyst_opinions, recommendation_mean, recommendation_key
  - **Forward Estimates**: forward_eps, earnings_growth, revenue_growth, earnings_quarterly_growth
  - **Profitability Metrics**: profit_margins, operating_margins, gross_margins, return_on_assets, return_on_equity, total_revenue (TTM)
  - **Current Year Estimates (0y)**: current_year_revenue_avg, current_year_revenue_low, current_year_revenue_high, current_year_revenue_growth, current_year_earnings_avg, current_year_earnings_low, current_year_earnings_high, current_year_end_date
  - **Next Year Estimates (+1y)**: next_year_revenue_avg, next_year_revenue_low, next_year_revenue_high, next_year_revenue_growth, next_year_earnings_avg, next_year_earnings_low, next_year_earnings_high, next_year_end_date
  - **Tracking Fields**: data_source, last_updated, created_at, updated_at
  - Add index on symbol for fast lookups
  - **Total: ~50 columns**

  #### 1.2 Create Alembic Migration
  **Command**: `cd backend && uv run alembic revision --autogenerate -m "Add company_profiles
  table"`
  - Review the generated migration
  - Ensure all fields and indexes are correct
  - Run migration: `uv run alembic upgrade head`

  ### Phase 2: Install yahooquery & Create Profile Fetcher (Backend)

  #### 2.1 Install yahooquery Package
  **Command**:
  ```bash
  cd backend
  uv add yahooquery
  ```

  #### 2.2 Create yahooquery Profile Fetcher (NEW FILE)
  **File**: `backend/app/services/yahooquery_profile_fetcher.py` (NEW)

  **Purpose**: Lightweight module for fetching company profiles using yahooquery
  - NOT a full provider client replacement
  - ONLY handles company profile data
  - yfinance continues to handle everything else (prices, historical, options)

  **Key Functions**:

  `fetch_company_profiles(symbols: List[str]) -> Dict[str, Dict[str, Any]]`:
  - Uses yahooquery's Ticker class
  - Fetches from multiple yahooquery modules:
    - `summary_profile` - Basic company info
    - `summary_detail` - Valuation metrics
    - `earnings_trend` - **Revenue estimates** (avg, low, high, growth) ← KEY
    - `earnings_trend` - **Earnings estimates** (avg, low, high, growth) ← KEY
    - `financial_data` - Profitability metrics
  - Returns standardized dict matching CompanyProfile schema
  - Handles errors gracefully (missing data, API failures)
  - Includes rate limiting (yahooquery is free, no API key needed)

  **Data Extraction Map**:

  From `summary_profile`:
  - company_name (longName), sector, industry, website, description (longBusinessSummary)
  - ceo, employees (fullTimeEmployees), country

  From `summary_detail`:
  - exchange, market_cap (marketCap), beta
  - pe_ratio (trailingPE), forward_pe (forwardPE)
  - dividend_yield (dividendYield)
  - week_52_high (fiftyTwoWeekHigh), week_52_low (fiftyTwoWeekLow)
  - is_etf, is_fund (based on quoteType)

  From `earnings_trend` ← **This is the goldmine**:

  **IMPORTANT**: earnings_trend returns data for multiple periods. Extract "0y" (current year) and "+1y" (next year):

  **Period "0y" (Current Year)**:
  - current_year_revenue_avg (revenueEstimate.avg)
  - current_year_revenue_low (revenueEstimate.low)
  - current_year_revenue_high (revenueEstimate.high)
  - current_year_revenue_growth (revenueEstimate.growth)
  - current_year_earnings_avg (earningsEstimate.avg)
  - current_year_earnings_low (earningsEstimate.low)
  - current_year_earnings_high (earningsEstimate.high)
  - current_year_end_date (endDate)

  **Period "+1y" (Next Year)**:
  - next_year_revenue_avg (revenueEstimate.avg)
  - next_year_revenue_low (revenueEstimate.low)
  - next_year_revenue_high (revenueEstimate.high)
  - next_year_revenue_growth (revenueEstimate.growth)
  - next_year_earnings_avg (earningsEstimate.avg)
  - next_year_earnings_low (earningsEstimate.low)
  - next_year_earnings_high (earningsEstimate.high)
  - next_year_end_date (endDate)

  **Also extract** (from trend array):
  - target_mean_price, target_high_price, target_low_price
  - number_of_analyst_opinions, recommendation_mean, recommendation_key

  From `financial_data`:
  - profit_margins, operating_margins, gross_margins
  - return_on_assets (returnOnAssets), return_on_equity (returnOnEquity)
  - total_revenue (totalRevenue - TTM)
  - forward_eps, earnings_growth, revenue_growth

  #### 2.3 Update market_data_service.py
  **File**: `backend/app/services/market_data_service.py`

  **Add new function** `store_company_profile()`:
  - Takes symbol and profile data (from yahooquery)
  - Inserts or updates company_profiles table
  - Uses PostgreSQL UPSERT (on conflict do update)
  - All fields optional for graceful degradation

  **Add new function** `fetch_and_cache_company_profiles()`:
  - Calls `yahooquery_profile_fetcher.fetch_company_profiles(symbols)`
  - Iterates results and calls `store_company_profile()` for each
  - Batch processing with rate limit delays
  - Returns success/failure status per symbol

  **Optional: Update** `update_security_metadata()`:
  - Could add call to fetch_and_cache_company_profiles()
  - Or keep separate - company profiles updated independently
  - Decision: Probably keep separate for now

  ### Phase 3: API Updates (Backend)

  #### 3.1 Update /positions/details Endpoint
  **File**: `backend/app/api/v1/data.py`
  **Line**: ~433 (positions/details endpoint)

  **Changes**:
  1. Join with `company_profiles` table when fetching positions
  2. Add company profile fields to response schema:
     - `company_name` (critical for frontend)
     - `beta` (company stock beta)
     - `sector`, `industry` (currently in MarketDataCache, move to profile)
     - `description`, `is_etf`, `is_fund` (nice to have)

  **SQL Join**:
  ```python
  query = (
      select(Position, CompanyProfile)
      .outerjoin(CompanyProfile, Position.symbol == CompanyProfile.symbol)
      .where(Position.portfolio_id == portfolio_id)
  )

  3.2 Update Response Schema (if needed)

  File: backend/app/schemas/ (check if position schema needs update)
  - Add company_name field to position response
  - Make it optional (nullable) for backwards compatibility

  ### Phase 4: Data Population Scripts

  #### 4.1 Create Population Script
  **File**: `backend/scripts/populate_company_profiles.py` (NEW)

  **Purpose**: Backfill company profiles for all existing position symbols

  **Logic**:
  ```python
  async def main():
      # 1. Get all unique symbols from positions table
      # 2. Batch process symbols (10 at a time to avoid rate limits)
      # 3. Call market_data_service.fetch_and_cache_company_profiles()
      # 4. Log success/failure for each symbol
      # 5. Sleep 1 second between batches
  ```

  **Usage**:
  ```bash
  cd backend
  uv run python scripts/populate_company_profiles.py
  ```

  #### 4.2 Optional: Add to Batch Processing
  **File**: `backend/app/batch/batch_orchestrator_v2.py`

  **Decision**: Probably NOT needed initially
  - Company profiles don't change frequently
  - Can run population script manually when needed
  - Or add later if want weekly/monthly profile updates
  - Keep it simple for Phase 1

  ### Phase 5: Testing & Verification

  #### 5.1 Database Verification
  ```bash
  # Check model imports correctly
  cd backend
  uv run python -c "from app.models.market_data import CompanyProfile; print('✅ CompanyProfile model works')"

  # Check migration applied
  uv run alembic current

  # Check table exists in database
  uv run python -c "import asyncio; from app.database import get_async_session; from sqlalchemy import text; async def check(): async with get_async_session() as db: result = await db.execute(text('SELECT COUNT(*) FROM company_profiles')); print(f'✅ Table exists, rows: {result.scalar()}'); asyncio.run(check())"
  ```

  #### 5.2 Test yahooquery Profile Fetcher
  ```bash
  # Test fetching profiles for a few symbols
  cd backend
  uv run python -c "
  import asyncio
  from app.services.yahooquery_profile_fetcher import fetch_company_profiles
  async def test():
      profiles = await fetch_company_profiles(['AAPL', 'MSFT', 'SPY'])
      for symbol, data in profiles.items():
          print(f'{symbol}: {data.get(\"company_name\")}, Revenue Est: {data.get(\"revenue_estimate_avg\")}')
  asyncio.run(test())
  "
  ```

  #### 5.3 Test Population Script
  ```bash
  # Run population script
  cd backend
  uv run python scripts/populate_company_profiles.py

  # Check data was inserted
  uv run python -c "import asyncio; from app.database import get_async_session; from app.models.market_data import CompanyProfile; from sqlalchemy import select; async def check(): async with get_async_session() as db: result = await db.execute(select(CompanyProfile).limit(5)); profiles = result.scalars().all(); for p in profiles: print(f'{p.symbol}: {p.company_name}'); print(f'  CY Revenue: ${p.current_year_revenue_avg/1e9 if p.current_year_revenue_avg else 0:.1f}B, NY Revenue: ${p.next_year_revenue_avg/1e9 if p.next_year_revenue_avg else 0:.1f}B'); asyncio.run(check())"
  ```

  #### 5.4 API Testing
  ```bash
  # Test endpoint returns company_name and profile data
  curl "http://localhost:8000/api/v1/data/positions/details?portfolio_id=<id>" | jq '.positions[0] | {symbol, company_name, beta, current_year_revenue_avg, next_year_revenue_avg, current_year_earnings_avg, next_year_earnings_avg}'
  ```

  #### 5.5 Frontend Verification
  1. Navigate to `/portfolio` page
     - Verify position cards show actual company names (e.g., "Apple Inc." for AAPL)
     - Verify ETF names display correctly (e.g., "SPDR S&P 500 ETF Trust" for SPY)

  2. Navigate to `/organize` page
     - Verify position cards show actual company names (not "Company")
     - Verify fallback to symbol if company_name missing

  3. Check browser console
     - No errors related to missing company_name field

  ### Success Criteria

  ✅ **Database**
  - CompanyProfile table exists with all fields (40+ columns)
  - Alembic migration runs successfully
  - Indexes created on symbol column

  ✅ **yahooquery Integration**
  - yahooquery package installed
  - yahooquery_profile_fetcher.py created and working
  - Successfully fetches profiles for test symbols
  - **Current year (0y) estimates populated** - revenue and earnings with end date
  - **Next year (+1y) estimates populated** - revenue and earnings with end date
  - Period tracking working correctly (0y vs +1y)

  ✅ **Data Population**
  - Population script runs without errors
  - Company profiles stored for all position symbols
  - UPSERT logic working (no duplicate key errors)

  ✅ **API Endpoint**
  - /positions/details endpoint joins with company_profiles
  - Returns company_name for all positions
  - Returns current year and next year revenue estimates (if available)
  - Returns current year and next year earnings estimates (if available)
  - Returns fiscal year end dates for context
  - Graceful handling when profile missing (null values)

  ✅ **Frontend Display**
  - Portfolio page shows actual company names
  - Organize page shows actual company names
  - No hardcoded company names in frontend code
  - Fallback to symbol works when company_name missing

  ✅ **yfinance Unchanged**
  - yfinance still handles prices, historical data, options
  - No disruption to existing functionality
  - All existing batch processing still works

  Benefits

  1. **Fixes missing company names** - Primary goal achieved
  2. **Stores company stock beta** - Market beta available for display
  3. **Analyst estimates & targets** - Price targets, recommendations, analyst coverage
  4. **Forward growth estimates** - Earnings growth, revenue growth projections
  5. **Profitability metrics** - Margins, ROA, ROE for fundamental analysis
  6. **Efficient storage** - One row per symbol vs. thousands of duplicates
  7. **Future-ready** - Rich dataset for advanced features (screeners, alerts, fundamental analysis)
  8. **Clean separation** - Price data separate from company metadata

  ### Estimated Changes (Phase 1 Only)

  - **New files**: 3 (yahooquery_profile_fetcher.py, Alembic migration, population script)
  - **Modified files**: 2 (market_data.py models, data.py API endpoint)
  - **New dependency**: yahooquery package
  - **Database**: 1 new table with ~50 columns
    - Includes 8 current year estimate fields
    - Includes 8 next year estimate fields
    - Total: Basic info + valuations + analyst data + current year + next year + profitability + tracking
  - **Lines of code**: ~400-500 total
  - **Time estimate**: 3-4 hours implementation + testing
  - **Unchanged**: yfinance client (continues working as-is)

  Notes

  - Frontend already expects position.name - no frontend changes needed
  - yfinance provides all analyst/fundamental data - just need to extract and store it
  - UPSERT pattern ensures profiles stay updated
  - Optional fields allow graceful degradation if API data missing
  - All new fields (analyst estimates, profitability) are optional - won't break if data unavailable

  ### Future Use Cases Enabled

  With analyst estimates and profitability metrics stored, we can build:

  1. **Position cards with price targets** - "Analyst target: $185 (18% upside)"
  2. **Recommendation badges** - Show "Strong Buy", "Hold", "Sell" on position cards
  3. **Fundamental screeners** - Filter by P/E ratio, ROE, profit margins
  4. **Growth opportunities** - Highlight positions with high earnings growth estimates
  5. **Valuation alerts** - "AAPL trading 15% below analyst target"
  6. **Profitability analysis** - Compare portfolio positions by margins and returns
  7. **Analyst coverage dashboard** - Track most/least covered positions
  8. **Revenue estimate tracking** - "FY 2026 revenue estimate: $500B (12% growth)"
  9. **Year-over-year comparison** - Compare current year vs next year estimates
  10. **Valuation multiples** - Calculate P/E on next year earnings, Price/Sales on current year revenue

  ---

  ## Step-by-Step Implementation Guide

  ### Prerequisites
  - Backend server running (yfinance already configured)
  - PostgreSQL database accessible
  - Alembic migrations working

  ### Step 1: Create CompanyProfile Model
  ```bash
  # Edit backend/app/models/market_data.py
  # Add CompanyProfile class (40+ fields as specified above)
  # Save file
  ```

  **Verification**:
  ```bash
  cd backend
  uv run python -c "from app.models.market_data import CompanyProfile; print('✅ Model imports')"
  ```

  ### Step 2: Generate and Run Migration
  ```bash
  cd backend

  # Generate migration
  uv run alembic revision --autogenerate -m "Add company_profiles table"

  # Review the generated migration in alembic/versions/
  # Check that all columns and indexes look correct

  # Run migration
  uv run alembic upgrade head

  # Verify
  uv run alembic current
  # Should show: "Add company_profiles table (head)"
  ```

  ### Step 3: Install yahooquery
  ```bash
  cd backend
  uv add yahooquery

  # Verify installation
  uv run python -c "import yahooquery; print('✅ yahooquery installed')"
  ```

  ### Step 4: Create yahooquery Profile Fetcher
  ```bash
  # Create new file: backend/app/services/yahooquery_profile_fetcher.py
  # Implement fetch_company_profiles() function
  # See Phase 2.2 above for detailed data extraction map
  ```

  **Verification**:
  ```bash
  cd backend
  uv run python -c "
  import asyncio
  from app.services.yahooquery_profile_fetcher import fetch_company_profiles

  async def test():
      profiles = await fetch_company_profiles(['AAPL', 'MSFT'])
      for symbol, data in profiles.items():
          print(f'{symbol}: {data.get(\"company_name\")}')
          print(f'  Current Year Revenue: ${data.get(\"current_year_revenue_avg\")/1e9:.1f}B')
          print(f'  Next Year Revenue: ${data.get(\"next_year_revenue_avg\")/1e9:.1f}B')
          print(f'  Current Year EPS: ${data.get(\"current_year_earnings_avg\"):.2f}')
          print(f'  Next Year EPS: ${data.get(\"next_year_earnings_avg\"):.2f}')

  asyncio.run(test())
  "
  # Should print Apple Inc. and Microsoft Corporation with current/next year estimates
  ```

  ### Step 5: Add Service Functions
  ```bash
  # Edit backend/app/services/market_data_service.py
  # Add store_company_profile() function
  # Add fetch_and_cache_company_profiles() function
  # See Phase 2.3 above for function signatures
  ```

  **Verification**:
  ```bash
  cd backend
  uv run python -c "
  from app.services.market_data_service import store_company_profile, fetch_and_cache_company_profiles
  print('✅ Service functions imported')
  "
  ```

  ### Step 6: Create Population Script
  ```bash
  # Create new file: backend/scripts/populate_company_profiles.py
  # Implement main() function (see Phase 4.1 for logic)
  ```

  **Test Run**:
  ```bash
  cd backend
  uv run python scripts/populate_company_profiles.py

  # Should see output like:
  # "Fetching profiles for 63 symbols..."
  # "Batch 1: 10/10 successful"
  # "Batch 2: 10/10 successful"
  # etc.
  ```

  ### Step 7: Update API Endpoint
  ```bash
  # Edit backend/app/api/v1/data.py
  # Find /positions/details endpoint (line ~433)
  # Add join with CompanyProfile table
  # Add company_name to response
  # See Phase 3.1 for SQL join example
  ```

  **Verification**:
  ```bash
  # Start backend server
  cd backend
  uv run python run.py

  # In another terminal:
  curl "http://localhost:8000/api/v1/data/positions/details?portfolio_id=<your-id>" | jq '.positions[0] | {symbol, company_name, beta}'

  # Should see:
  # {
  #   "symbol": "AAPL",
  #   "company_name": "Apple Inc.",
  #   "beta": 1.24
  # }
  ```

  ### Step 8: Frontend Testing
  ```bash
  # No code changes needed - frontend already expects position.name

  # 1. Start frontend (if not running)
  cd frontend
  npm run dev

  # 2. Navigate to http://localhost:3005/login
  # 3. Login with demo credentials
  # 4. Navigate to /portfolio page
  #    - Verify position cards show "Apple Inc." not "Company"
  #    - Verify ETF names display correctly

  # 5. Navigate to /organize page
  #    - Verify position cards show company names
  ```

  ### Step 9: Validation Checklist

  **Database**:
  - [ ] company_profiles table exists
  - [ ] Table has 40+ columns
  - [ ] Symbol is primary key
  - [ ] Index on symbol exists

  **Data**:
  - [ ] Profiles populated for all position symbols
  - [ ] Revenue estimates present (revenue_estimate_avg not null)
  - [ ] Earnings estimates present (earnings_estimate_avg not null)
  - [ ] Company names populated

  **API**:
  - [ ] /positions/details returns company_name
  - [ ] Revenue estimates included in response
  - [ ] Null handling works (positions without profiles don't crash)

  **Frontend**:
  - [ ] Portfolio page shows company names
  - [ ] Organize page shows company names
  - [ ] No "Company" placeholders
  - [ ] No console errors

  **yfinance**:
  - [ ] Prices still updating
  - [ ] Historical data still working
  - [ ] Options data still working
  - [ ] No disruption to existing functionality

  ### Troubleshooting

  **Issue**: Migration fails
  - Check that CompanyProfile model syntax is correct
  - Verify database connection works
  - Check if table already exists (drop manually if testing)

  **Issue**: yahooquery returns None for some symbols
  - Normal - not all symbols have complete data
  - Check that error handling is in place
  - Verify null fields are allowed in database

  **Issue**: Population script slow
  - yahooquery is free but has rate limits
  - Adjust batch size (default 10)
  - Adjust sleep time between batches (default 1 second)

  **Issue**: Frontend still shows "Company"
  - Check that API actually returns company_name
  - Verify database has data for that symbol
  - Check frontend is reading position.name field
  - Clear browser cache

  **Issue**: Revenue estimates null for all symbols
  - Not all companies have revenue estimates
  - Check yahooquery is fetching earnings_trend module
  - Verify data extraction logic in yahooquery_profile_fetcher.py

  ### Post-Implementation

  **Optional Enhancements**:
  1. Add weekly cron job to refresh company profiles
  2. Add company_name to other API endpoints
  3. Build position cards with analyst targets
  4. Create fundamental screener using profitability metrics

  **Future Migration (Phase 2)**:
  - Only proceed if yahooquery proves reliable in Phase 1
  - Would replace yfinance completely
  - Create full yahooquery_client.py implementing MarketDataProvider
  - Update factory.py to use yahooquery as primary provider
  - Keep this plan for reference when ready

  ---

  ## Quick Reference Commands

  ```bash
  # Complete implementation in one go:

  cd backend

  # 1. Model & Migration
  # (Edit market_data.py manually)
  uv run alembic revision --autogenerate -m "Add company_profiles table"
  uv run alembic upgrade head

  # 2. Install yahooquery
  uv add yahooquery

  # 3. Create files
  # (Create yahooquery_profile_fetcher.py manually)
  # (Edit market_data_service.py manually)
  # (Create populate_company_profiles.py manually)
  # (Edit data.py manually)

  # 4. Populate data
  uv run python scripts/populate_company_profiles.py

  # 5. Test
  uv run python run.py  # Start backend
  # Test in browser at http://localhost:3005

  # Done! Company names should now display on frontend.
  ```