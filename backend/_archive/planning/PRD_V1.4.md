# SigmaSight Backend - Project Requirements Document (PRD) & Engineering Design Document (EDD)

## 1. Executive Summary

> ⚠️ **STATUS UPDATE (2025-08-26 15:00 PST)**: Backend development is complete through Phase 3.0 with Raw Data APIs (100% complete). Frontend and agent development can proceed without additional backend work. See [TODO3.md](../../TODO3.md) for current API development status.

SigmaSight is a portfolio risk management platform designed to provide institutional-quality analytics for long/short equity portfolios. This document outlines the backend requirements and technical design for a demonstration system that showcases core functionality through pre-computed analytics and batch processing.

**Key Principles**

- **Batch Processing First**: All computations run before demo to ensure snappy performance
- **PostgreSQL Only**: No distributed storage needed for 90-day demo dataset
- **Railway Deployment**: Zero-config deployment using UV package manager
- **API-First Design**: RESTful API matching the V5 frontend prototype requirements

## 2. Project Scope
### ~~In Scope – Phase 1 (Demo)~~ **[COMPLETED - See TODO1.md]** *(Updated 2025-08-26 15:00 PST)*
- Portfolio data ingestion via CSV upload
- Pre-calculated risk metrics and factor exposures
- Position management with tagging system
- JWT-based authentication for multiple demo accounts
- Daily batch processing of market data
- Mock options Greeks display
- API endpoints for frontend V5 prototype

### ~~In Scope – Phase 2 (Post-Demo)~~ **[COMPLETED - See TODO2.md]** *(Updated 2025-08-26 15:00 PST)*
- Real-time ProForma modeling with session management
- Dynamic Greeks calculation
- Real export functionality (FIX, CSV formats)
- WebSocket support for live updates

### Out of Scope
- Real-time market data feeds
- Actual options pricing models
- Complex authentication/authorization
- Multi-tenant architecture
- Audit logging

## 3. Functional Requirements
### 3.1 Portfolio Management
#### CSV Upload Endpoint
```
POST /api/v1/portfolio/upload
Content-Type: multipart/form-data
```
CSV Format:
```
csvticker,quantity,entry_price,entry_date,tags
AAPL,1000,150.00,2024-01-15,"momentum,tech"
MSFT,-500,380.00,2024-01-20,"hedge,tech"
AAPL240119C00150000,10,5.50,2024-01-10,"hedge,options"
```
Requirements:
- Support stocks (positive quantity = long, negative = short)
- Support options (OCC symbology)
- Multiple tags per position (comma-separated)
- Calculate current market value using latest prices ✅ **IMPLEMENTED Section 1.4.1**
- Generate 90 days of historical snapshots

**✅ Market Value Calculation Implementation (Section 1.4.1):**
- **Market Value**: Always positive using `abs(quantity) × price × multiplier`
- **Exposure**: Signed value `quantity × price × multiplier` (negative for shorts)
- **Options Multiplier**: 100x for contracts (LC, LP, SC, SP)
- **Stock Multiplier**: 1x for stocks (LONG, SHORT)
- **P&L Calculation**: Current exposure - cost basis
- **Database Integration**: Automated previous price lookup from market_data_cache
- **Fallback Logic**: Uses position.last_price if no market data available

#### ~~Historical Data Generation~~ *(REMOVED - Decision: Not needed for V1.4)*
~~Upon successful CSV upload:~~
- ~~System fetches 90 days of real historical market data from Polygon.io for all positions~~
- ~~Generates authentic historical portfolio snapshots using actual closing prices~~
- ~~Calculates real historical P&L based on actual market movements~~
- ~~Creates realistic risk metrics derived from true market volatility~~
- ~~Handles weekends/holidays by only creating snapshots for actual trading days~~

**Note:** *Historical data generation was removed from scope. V1.4 will focus on current portfolio state and daily forward snapshots only.*

#### Portfolio Overview
```
GET /api/v1/portfolio
```
Returns:
- Total portfolio value ✅ **IMPLEMENTED via calculate_single_portfolio_aggregation()**
- Long/short/gross/net exposures ✅ **IMPLEMENTED via Section 1.4.1 aggregations**
- Total P&L (daily, MTD, YTD) ✅ **Daily P&L IMPLEMENTED via calculate_daily_pnl()**
- Number of positions by type ✅ **IMPLEMENTED with long/short position counting**

**✅ Portfolio Aggregation Implementation:**
- **Total Market Value**: Sum of all position market values (always positive)
- **Gross Exposure**: Long value + short value (total capital at risk)
- **Net Exposure**: Long value - short value (directional exposure)
- **Long/Short Breakdown**: Separate aggregations for positive/negative quantity positions
- **Position Counts**: Automated counting of long vs short positions
- **Daily P&L**: Calculated via database-integrated previous price lookup

### 3.2 Position Management
#### List Positions
```
GET /api/v1/positions?groupBy=type|tag&tags=momentum,hedge&tagMode=any|all
```
Features:
- Filter by position type (LONG, SHORT, LC, LP, SC, SP)
- Filter by tags with AND/OR logic
- Group by type or tag
- Include current market values and P&L ✅ **IMPLEMENTED via Section 1.4.1**

**✅ Position Value Calculation Implementation:**
- **Market Values**: Calculated via `calculate_position_market_value()` function
- **Daily P&L**: Calculated via `calculate_daily_pnl()` with database integration
- **Real-time Updates**: Bulk position updates via `bulk_update_position_values()`
- **Options Detection**: Automatic detection via `is_options_position()` helper
- **Error Handling**: Graceful fallback to cached prices when API fails
- **Database Updates**: Automatic persistence of calculated values to positions table

#### Position Greeks (Mibian-only)
```
GET /api/v1/risk/greeks?view=portfolio|longs|shorts
```
**V1.4 Implementation**:
- **Real calculations** for options using `mibian` (Black-Scholes)
- **No mock fallback**; if calculation fails or inputs are missing, nulls are returned with warnings
- **Stocks have no Greeks**; delta-adjusted exposure for stocks is handled in the portfolio aggregation engine, not as a Greek

**📝 Implementation Note**: Originally planned to use `py_vollib` but encountered `_testcapi` import issues on Python 3.11. `mibian` provides the same Black-Scholes calculations with better compatibility.

### 3.3 Risk Analytics
#### Factor Exposures
```
GET /api/v1/risk/factors
```
Seven Factors (with ETF proxies):
1. Market Beta (SPY)
2. Momentum (MTUM)
3. Value (VTV)
4. Growth (VUG)
5. Quality (QUAL)
6. Size (IWM)
7. Low Volatility (SPLV)
8. Short Interest (custom calculation)

**V1.4 Hybrid Calculation Method**:
- **Real calculations** for 7 of 8 factors using `statsmodels` regression
- 60-day rolling window with daily returns
- Position-level betas aggregated by portfolio weights
- **Mock calculation** only for Short Interest factor (custom logic TBD)
- Leverages legacy `factors_utils.py` calculation logic

#### Risk Metrics
```
GET /api/v1/risk/metrics
```
**V1.4 Hybrid Risk Metrics**:
- **Real calculations** using `empyrical` library:
  - Portfolio Beta (weighted average vs SPY)
  - Annualized Volatility (60-day rolling)
  - Sharpe Ratio (with risk-free rate)
  - Maximum Drawdown (90-day period)
  - Value at Risk (95% confidence, 1-day)
- Leverages legacy `var_utils.py` for covariance matrix calculations
- All metrics calculated during batch processing and cached

### 3.4 Tag Management
CRUD Operations
```
GET    /api/v1/tags
POST   /api/v1/tags          {"name": "momentum", "color": "#FF5733"}
PUT    /api/v1/tags/{id}     {"name": "momentum_v2"}
DELETE /api/v1/tags/{id}

GET    /api/v1/positions/{id}/tags
PUT    /api/v1/positions/{id}/tags   {"tag_ids": [1, 2, 3]}
```
** IMPORTANT: please review PRD_TAGS_V1.4.1.md for more details **

### 3.5 Authentication
#### Login
```
POST /api/v1/auth/login
{
  "username": "demo_user_1",
  "password": "demo123"
}
```
Response:
```
{
  "token": "eyJ...",
  "expires_in": 86400,
  "portfolio_id": 1
}
```
Demo Users (pre-seeded):
- demo_user_1 / demo123 – Main portfolio
- demo_user_2 / demo123 – Secondary portfolio
- demo_admin  / admin123 – Admin access

### 3.6 Batch Processing
#### Daily Update Process
```
POST /api/v1/admin/daily-update
```
Steps:
1. Fetch latest prices from Polygon.io
2. Calculate new market values using real market data
3. Generate P&L based on actual price movements
4. Recalculate all risk metrics using historical volatility
5. Update factor exposures
6. Create new portfolio snapshot

~~Historical Backfill Process~~ *(REMOVED - V1.4 scope change)*:
- ~~Triggered automatically after CSV upload~~
- ~~Fetches 90 days of historical daily prices for all positions~~
- ~~Respects Polygon.io rate limits (implements retry logic)~~
- ~~Caches historical data to minimize API calls~~
- ~~Generates portfolio snapshots for each trading day using real prices~~

##### Rate Limiting Strategy for Polygon.io

**1. Token Bucket Implementation**
- Free tier: 5 requests/minute rate limit
- Implement token bucket algorithm with configurable rate
- Queue requests with priority levels (real-time > batch > backfill)

**2. Exponential Backoff**
```python
def exponential_backoff(attempt):
    """Calculate wait time for retry attempts"""
    base_wait = 2  # seconds
    max_wait = 300  # 5 minutes
    wait_time = min(base_wait * (2 ** attempt), max_wait)
    return wait_time + random.uniform(0, 1)  # Add jitter
```

**3. Caching Strategy**
- Check `market_data_cache` before API calls
- Cache TTL: 24 hours for EOD data
- Implement cache warming during off-peak hours

**4. Progress Tracking**
```sql
CREATE TABLE historical_backfill_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID REFERENCES portfolios(id),
    total_symbols INTEGER NOT NULL,
    processed_symbols INTEGER DEFAULT 0,
    failed_symbols INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL, -- 'pending', 'processing', 'completed', 'failed'
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**5. Batch Processing Architecture**
```python
# Pseudo-code for rate-limited batch processing
async def process_historical_backfill(portfolio_id: UUID):
    tracker = await create_backfill_tracker(portfolio_id)
    rate_limiter = TokenBucket(rate=5, per_minute=True)
    
    for symbol in get_portfolio_symbols(portfolio_id):
        try:
            # Check cache first
            if cached_data := await get_cached_data(symbol):
                await update_progress(tracker, symbol, 'cached')
                continue
                
            # Rate-limited API call
            await rate_limiter.acquire()
            data = await polygon_client.get_aggs(
                ticker=symbol,
                from_date=datetime.now() - timedelta(days=90),
                to_date=datetime.now()
            )
            
            await save_to_cache(symbol, data)
            await update_progress(tracker, symbol, 'completed')
            
        except RateLimitError:
            await asyncio.sleep(60)  # Wait full minute
            retry_queue.add(symbol, priority='low')
            
        except Exception as e:
            await update_progress(tracker, symbol, 'failed', error=str(e))
```

Scheduling:
- **Automatic**: Daily batch runs at specific times
- **Manual**: Admin endpoint trigger

#### Batch Job Implementation Details

##### 1. Market Data Update Job (4 PM EST)
```python
def update_market_data():
    """
    Fetch and store latest market data for all active securities
    IMPLEMENTED: Section 1.4.1 Market Data Calculations
    """
    # Steps:
    # 1. Get list of unique symbols from positions ✅ IMPLEMENTED
    # 2. Fetch EOD prices from Polygon.io ✅ IMPLEMENTED via fetch_and_cache_prices()
    # 3. Fetch sector/industry from YFinance for new symbols ✅ IMPLEMENTED
    # 4. Update market_data_cache table ✅ IMPLEMENTED with upsert operations
    # 5. Update last_price in positions table ✅ IMPLEMENTED
    # 6. Calculate market values and P&L ✅ IMPLEMENTED via Section 1.4.1 functions
```

**Section 1.4.1 Implementation Status: ✅ COMPLETED (2025-07-15)**

**Core Functions Implemented:**

1. **`calculate_position_market_value(position, current_price)`**
   - **Location**: `app/calculations/market_data.py:32`
   - **Business Logic**: Market value = abs(quantity) × price × multiplier
   - **Options Support**: 100x multiplier for contracts (LC, LP, SC, SP)
   - **Stock Support**: 1x multiplier for stocks (LONG, SHORT)
   - **Returns**: market_value, exposure (signed), unrealized_pnl, cost_basis

2. **`calculate_daily_pnl(db, position, current_price)`**
   - **Location**: `app/calculations/market_data.py:78`
   - **Database Integration**: Automatically queries market_data_cache for previous price
   - **Fallback Logic**: Uses position.last_price if no market data found
   - **Error Handling**: Returns zero P&L with error message if no previous price
   - **Returns**: daily_pnl, daily_return, price_change, previous/current values

3. **`fetch_and_cache_prices(db, symbols_list)`**
   - **Location**: `app/calculations/market_data.py:298`
   - **Integration**: Uses existing MarketDataService.fetch_current_prices()
   - **Caching**: Updates market_data_cache table for valid prices
   - **Fallback**: Retrieves cached prices for failed API calls
   - **Returns**: Dictionary mapping symbol to current price

**Batch Processing Integration:**
- **Updated**: `app/batch/daily_calculations.py` with Section 1.4.1 functions
- **Function**: `bulk_update_position_values()` - Efficient batch updates for all portfolios
- **Aggregations**: Portfolio-level calculations (total value, exposure, long/short breakdown)
- **Error Resilience**: Comprehensive error handling and reporting

**Testing Status:**
- ✅ **Unit Tests**: 4/4 tests passing (stock long/short, options, position detection)
- ✅ **Integration Tests**: Batch processing and database integration verified
- ✅ **Manual Testing**: `scripts/test_calculations.py` - All calculations validated

##### 2. Risk Metrics Calculation Job (5 PM EST)
```python
def calculate_all_risk_metrics():
    """
    Calculate portfolio-level risk metrics and factor exposures
    """
    # Steps:
    # 1. Calculate position-level Greeks (using mock values)
    # 2. Aggregate portfolio Greeks
    # 3. Calculate factor exposures (using mock values):
    #    - Use MOCK_FACTOR_EXPOSURES dictionary
    #    - Apply to each position based on characteristics
    # 4. Update position_greeks table
    # 5. Update factor_exposures table
    # 6. Calculate portfolio beta and volatility
```

##### 3. Portfolio Snapshot Job (5:30 PM EST)
```python
def create_portfolio_snapshots():
    """
    Create daily snapshots for historical tracking
    """
    # Steps:
    # 1. Calculate daily P&L for each portfolio
    # 2. Calculate portfolio metrics:
    #    - Total value, gross/net exposure
    #    - Aggregated Greeks
    #    - Risk metrics
    # 3. Create portfolio_snapshots record
    # 4. Update portfolio performance metrics
    # 5. Clean up old snapshots (>365 days)
```

##### Batch Job Configuration
```python
BATCH_SCHEDULE = {
    'market_data': {
        'function': update_market_data,
        'schedule': '0 16 * * 1-5',  # 4 PM weekdays
        'timeout': 300,
        'retry_count': 3
    },
    'risk_metrics': {
        'function': calculate_all_risk_metrics,
        'schedule': '0 17 * * 1-5',  # 5 PM weekdays
        'timeout': 600,
        'retry_count': 2
    },
    'snapshots': {
        'function': create_portfolio_snapshots,
        'schedule': '30 17 * * 1-5',  # 5:30 PM weekdays
        'timeout': 300,
        'retry_count': 2
    }
}
```

### 3.7 Technology Stack and Quantitative Libraries

#### Core Calculation Libraries
Our technology choices align with institutional quantitative finance practices:

##### Options Pricing and Greeks
- **Library**: `mibian` (pure Python Black-Scholes implementation)
- **Rationale**: Simple, reliable Black-Scholes calculations with excellent Python 3.11+ compatibility
- **Usage**: Real-time options pricing, delta/gamma/theta/vega/rho calculations
- **Alternative Considered**: `py_vollib` (encountered `_testcapi` import issues), QuantLib (too heavyweight for our equity/options focus)

**📝 Implementation Update**: Originally specified `py_vollib` but switched to `mibian` due to compatibility issues with Python 3.11. The `py_vollib` library has a dependency on `py_lets_be_rational` which tries to import `_testcapi` - a private CPython testing module not available in standard Python installations. `mibian` provides equivalent Black-Scholes calculations with better stability.

##### Risk Metrics and Performance Analytics  
- **Library**: `empyrical` (from Quantopian)
- **Rationale**: Battle-tested by thousands of quants, maintained by "ML for Algorithmic Trading" author
- **Usage**: Sharpe ratio, maximum drawdown, VaR calculations
- **Institutional Validation**: Used by Point72-backed platform, standard for Python quants

##### Statistical Analysis and Factor Modeling
- **Library**: `statsmodels`  
- **Rationale**: Academic-grade statistics, used by Federal Reserve and major banks
- **Usage**: Factor regression analysis, beta calculations
- **Method**: 150-day rolling OLS regression for factor exposures

##### Data Infrastructure
- **Libraries**: `pandas`, `numpy`, `scipy`
- **Rationale**: Industry standard at Two Sigma, AQR, Man Group
- **Evidence**: Public contributions from major funds to these libraries

#### Calculation Architecture Decisions

1. **Greeks Implementation (V1.4)**
   - Options Greeks calculated with `mibian` only (Black-Scholes)
   - No mock fallback; on error or missing inputs, fields are null
   - Stocks have no Greeks; expired options return zero Greeks

2. **Historical Volatility Proxy**
   - Using 30-day historical volatility as implied volatility proxy
   - Industry-standard approach when options market data unavailable

3. **Factor Model Implementation**
   - 8 factors with ETF proxies (matching institutional approaches)
   - Real regression-based calculations for 7 factors
   - Simplified covariance matrix with real correlations

#### Alignment with Institutional Practices

This stack mirrors typical hedge fund infrastructure:
- Scientific Python ecosystem (same as Two Sigma, AQR)
- Standard risk metrics for investor reporting
- Flexibility to add proprietary models later
- Version-controlled, reproducible calculations

## 4. Technical Architecture
### 4.1 Technology Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Package Manager**: UV
- **Deployment**: Railway
- **External APIs**: Polygon.io for market data

### 4.2 Project Structure
```
backend/
├── alembic/
│   └── versions/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py
│   │       ├── portfolio.py
│   │       ├── positions.py
│   │       ├── risk.py
│   │       ├── tags.py
│   │       └── admin.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/
│   │   ├── portfolio.py
│   │   ├── position.py
│   │   ├── market_data.py
│   │   └── user.py
│   ├── services/
│   │   ├── market_data.py
│   │   ├── risk_calc.py
│   │   ├── factor_calc.py
│   │   └── batch.py
│   ├── schemas/
│   └── main.py
├── scripts/
│   ├── seed_data.py
│   └── daily_batch.py
├── tests/
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

### 4.3 Database Schema
*(See SQL definitions in original document)*

### 4.4 Development Environment Setup
Prerequisites: Python 3.11+, PostgreSQL 15, UV, Git

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repo
git clone https://github.com/your-org/sigmasight-backend.git
cd backend

# Create env
uv venv && source .venv/bin/activate

# Install deps
uv sync

# Setup DB
createdb sigmasight_dev
cp .env.example .env
# Edit .env

# Migrations
alembic upgrade head

# Seed data
python scripts/seed_data.py

# Run server
uvicorn app.main:app --reload
```

### 4.5 Configuration Management
Environment variables (.env) and UV `pyproject.toml` settings are defined for database, security, external APIs, and batch processing.

## 5. Implementation Phases
1. **Phase 1 – Core Infrastructure (Week 1)**: project setup, auth, CSV upload.
2. **Phase 2 – Data Pipeline (Week 2)**: Polygon integration, batch, risk metrics.
3. **Phase 3 – API Development (Week 3)**: endpoints, hybrid calculations, tag CRUD.
4. **Phase 4 – Testing & Deployment (Week 4)**: tests, Railway deploy, performance.

## 6. Calculation Architecture Summary

### 6.1 Overview
V1.4 implements real calculations for core analytics with clear error handling and no mock fallbacks for Greeks. Portfolio aggregation uses a hybrid storage model (store summaries, compute details on-demand) for performance.

### 6.2 Real Calculations

#### Options Greeks
- **Libraries**: `mibian` (Black-Scholes)
- **Inputs**: Current price, strike, expiration, volatility, risk-free rate
- **Outputs**: Delta, Gamma, Theta, Vega, Rho
  - Calculation errors or missing inputs yield nulls; no mock fallback

#### Factor Betas (7 Factors)
- **Library**: `statsmodels` for OLS regression
- **Method**: 150-day rolling regression of position returns vs factor ETF returns
- **Factors**: Market Beta (SPY), Momentum (MTUM), Value (VTV), Growth (VUG), Quality (QUAL), Size (SIZE), Low Volatility (USMV)
- **Legacy**: Leverages `factors_utils.py` calculation logic

#### Risk Metrics
- **Library**: `empyrical` for financial metrics
- **Metrics**: Sharpe ratio, max drawdown, volatility, VaR
- **Legacy**: Uses `var_utils.py` for covariance matrix calculations

#### Portfolio Aggregations (Section 1.4.3)

**Libraries**: `numpy`, `pandas` (vectorised DataFrame operations ⟶ <200 ms for ≤200 positions)

**Input Contract**
- `positions`: List[Dict] – pre-enriched by Section 1.4.1 and 1.4.2, containing:
  - `id`, `symbol`, `quantity`, `market_value`, `exposure`, `is_option`
  - `sector`, `industry`, `tags` (List[str])
  - `greeks`: Dict[str, float] from `calculate_position_greeks()` (delta, gamma, theta, vega, rho)

**Core Aggregations**
1. Gross / Net / Long / Short exposure (USD, Decimal)
2. Portfolio-level Greeks = Σ signed position Greeks
3. Delta-adjusted notional exposure (stock Δ = ±1, option Δ from Greeks)
4. Position counts: `total`, `long`, `short`
5. Optional drill-downs (lazy-evaluated):
   • Sector / Industry  • Tag groups  • Underlying symbol

**Output Schema**
```json
{
  "gross_exposure": "Decimal",
  "net_exposure": "Decimal",
  "long_exposure": "Decimal",
  "short_exposure": "Decimal",
  "position_counts": { "total": 0, "long": 0, "short": 0 },
  "portfolio_greeks": { "delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0 },
  "delta_adjusted_exposure": "Decimal",
  "calculated_at": "ISO8601 timestamp"
}
```

**Design Decisions**
- Stock positions use Δ = +1 (long) / −1 (short).
- Option multiplier (100) already applied in `market_value` & `exposure`.
- Monetary fields persisted as `Decimal(18,4)`; Greeks as `FLOAT`.
- Results recomputed nightly by 17:00 batch job and upserted into `portfolio_snapshots`.
- Empty portfolios return zeroed structure with `success: false` & log warning.

**Implementation Decisions**
- **Precision & Rounding**
  - Monetary values: 2 decimal places (stored as DECIMAL in database)
  - Greeks: 4 decimal places (for accuracy in aggregations)
  - Percentages: 2 decimal places
  - Apply rounding at the API response layer, not in calculations or storage

- **Underlying-Symbol Breakdowns**
  - Implement `aggregate_by_underlying()` function
  - Critical for options portfolios (e.g., all SPY positions together)
  - Include both stock and options positions for each underlying
  - Required for proper risk analysis in options-heavy portfolios

- **Option Sign Conventions**
  - Use signed-by-quantity Greeks consistently
  - Maintain mathematical correctness from `calculate_position_greeks()`
  - Short call delta remains negative, short put delta remains positive
  - No overrides or transformations - preserve the signs for accurate hedging calculations

- **Point-in-Time Parameter**
  - Current positions only for V1.4
  - No `as_of_date` parameter needed for the demo
  - All aggregations work on current positions from latest batch job
  - Add comment for future enhancement: `# TODO: Add as_of_date support for historical analysis`

- **Storage vs. On-Demand**
  - **Store in portfolio_snapshots** (via 5:30 PM batch job):
    - Portfolio-level exposures (gross/net/long/short)
    - Aggregated Greeks totals
    - Position counts by type
  - **Compute on-demand** for API requests:
    - Tag-based aggregations
    - Underlying-based aggregations
    - Any custom groupings

- **Notional vs. Dollar Exposures**
  - Include both notional and dollar exposures:
```python
{
    "exposures": {
        "gross": Decimal,     # Dollar exposure
        "net": Decimal,       # Dollar exposure
        "notional": Decimal   # Sum of abs(quantity × price × multiplier)
    }
}
```
  - Notional exposure helps assess leverage, especially for options positions

- **API Pagination/Filtering**
  - Basic filtering only, no pagination for V1.4
  - Support query parameters: `?tag=momentum` or `?underlying=AAPL`
  - Return all results (unlikely to exceed 100 items in demo)
  - Document pagination structure for future: `# TODO: Add pagination for production`

- **Concurrency Requirements**
  - No special concurrency handling for V1.4
  - Single-threaded batch processing is sufficient
  - Read-only aggregations don't need locking
  - Demo is single-user per portfolio

- **Caching & TTL**
  - Simple in-memory caching with 60-second TTL
  - Cache configuration:
```python
AGGREGATION_CACHE_TTL = 60  # seconds
CACHE_KEY_FORMAT = "portfolio_agg:{user_id}:{agg_type}:{filters}"
```
  - Use `functools.lru_cache` for simple method-level caching

- **Configurability**
  - Hard-code with named constants in `app/constants/portfolio.py`:
```python
# Multipliers
OPTIONS_MULTIPLIER = 100
DEFAULT_SECTOR = "Unknown"
DEFAULT_INDUSTRY = "Unknown"

# Greeks precision
GREEKS_DECIMAL_PLACES = 4
MONETARY_DECIMAL_PLACES = 2

# Cache settings
AGGREGATION_CACHE_TTL = 60
```

**Testing Matrix** (see TESTING_GUIDE.md §1.4.3):
- Mixed portfolios (stocks + options)
- Empty portfolios
- Large portfolios (1000+ positions)
- Positions with missing Greeks
- Performance benchmarks (<200ms for 200 positions)
- All-short portfolio (edge)
- Missing market data / Greeks fallback

### 6.3 Mock Calculations

#### Short Interest Factor
- Custom calculation logic (TBD)
- No reliable real-time data source in V1.4

#### Fallback Greeks
- Pre-defined values by position type
- Used when real calculation fails

### 6.4 Required Dependencies

```toml
# pyproject.toml dependencies
[project]
dependencies = [
    # Core framework
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    
    # Database
    "sqlalchemy>=2.0",
    "asyncpg>=0.29.0",
    "alembic>=1.12.0",
    
    # Authentication
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    
    # Calculation libraries (V1.4 Hybrid)
    "mibian>=0.1.3",         # Options pricing (primary)
    "py-vollib>=1.0.1",      # Options pricing (fallback, has compatibility issues)
    "empyrical>=0.5.5",      # Risk metrics
    "statsmodels>=0.14.0",   # Factor regression
    "numpy>=1.24.0",         # Numerical operations
    "pandas>=2.0.0",         # Data manipulation
    
    # Market data
    "httpx>=0.25.0",         # Async HTTP client
    "yfinance>=0.2.28",      # GICS data
    
    # Utilities
    "python-multipart>=0.0.6",  # File uploads
    "python-dotenv>=1.0.0",     # Environment variables
]
```

**📝 Dependency Update**: `mibian` is now the primary options pricing library, with `py-vollib` kept as a fallback option (though it has known compatibility issues with Python 3.11+).

### 6.5 Calculation Pattern

```python
async def calculate_with_fallback(calculation_func, fallback_value, **kwargs):
    """Standard pattern for hybrid calculations"""
    try:
        # Attempt real calculation
        result = await calculation_func(**kwargs)
        if result is None or math.isnan(result):
            raise ValueError("Invalid calculation result")
        return result
    except Exception as e:
        logger.warning(f"Calculation failed, using fallback: {e}")
        return fallback_value
```
5. **Phase 5 – ProForma Modeling (Post-Demo)**: session management, real-time calcs.

## 6. API Endpoint Summary
*(Detailed list provided earlier; see section 3)*

## 7. Sample Data Specifications
Portfolio: $3M total with 20 longs, 15 shorts, 15 options; 90-day historical return +7.3%.

## 8. Development Guidelines
- **Git workflow**: feature branches, conventional commits.
- **Code standards**: type hints, docstrings, Black, Ruff, 90% test coverage.
- **Migrations**: Alembic revision management.

### 8.1 Pydantic Schema Organization

#### Directory Structure
```
app/schemas/
├── __init__.py
├── base.py          # Base schema classes with common fields
├── auth.py          # Authentication schemas
├── portfolio.py     # Portfolio-related schemas
├── positions.py     # Position CRUD schemas
├── market_data.py   # Market data schemas
├── modeling.py      # Modeling session schemas
└── exports.py       # Export-related schemas
```

#### Schema Pattern Guidelines

**1. Base Schema Classes**
```python
# base.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID

class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(
        from_attributes=True,  # Support ORM model conversion
        str_strip_whitespace=True,  # Auto-strip strings
        use_enum_values=True  # Use enum values not names
    )

class TimestampedSchema(BaseSchema):
    """Schema with timestamp fields"""
    created_at: datetime
    updated_at: Optional[datetime] = None
```

**2. CRUD Schema Pattern**
```python
# positions.py
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from app.schemas.base import BaseSchema, TimestampedSchema

class PositionBase(BaseSchema):
    """Shared position fields"""
    symbol: str
    quantity: Decimal
    position_type: PositionType
    
class PositionCreate(PositionBase):
    """Required fields for position creation"""
    # Additional create-only fields
    initial_price: Optional[Decimal] = None
    tags: Optional[List[str]] = None
    
class PositionUpdate(BaseSchema):
    """All fields optional for partial updates"""
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    position_type: Optional[PositionType] = None
    tags: Optional[List[str]] = None
    
class PositionInDB(PositionBase, TimestampedSchema):
    """Full database model"""
    id: UUID
    portfolio_id: UUID
    cost_basis: Decimal
    
class PositionResponse(PositionInDB):
    """API response with computed fields"""
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    tags: List[TagResponse] = []
```

**3. Schema Benefits**
- **Type Safety**: Prevents wrong schema usage at compile time
- **Clear Intent**: Schema name indicates its purpose
- **Validation**: Different rules for create vs update
- **Documentation**: Auto-generated API docs
- **Separation**: Database fields vs API response fields
- **Reusability**: Base classes reduce duplication

**4. Request/Response Patterns**
```python
# Standard response wrapper
class ResponseWrapper(BaseSchema, Generic[T]):
    """Standard API response wrapper"""
    success: bool = True
    data: T
    message: Optional[str] = None
    
# Paginated response
class PaginatedResponse(BaseSchema, Generic[T]):
    """Paginated list response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
```

## 9. Deployment to Railway
CLI steps for initial setup, environment variables, and continuous deployment on `main` branch.

## 10. Testing Strategy
Unit, integration, and end-to-end tests covering services, calculations, and workflows.

## 11. Performance Considerations
Caching, database indexing, response-time targets, and pagination guidelines.

## 12. Security Considerations
JWT auth, bcrypt hashing, HTTPS, rate limiting, and environment-based secrets.

## 13. Future Enhancements
Features planned for Phases 2-4, including websocket updates, ML predictions, and webhooks.

## 14. Success Criteria
Demo requirements, performance metrics, and availability targets.

## 15. AI Agent Implementation Notes
Error handling, validation, logging, and consistent implementation order for building the backend.

## Appendix A: Legacy Script Migration Strategy

### Overview of Migration Approach
The SigmaSight backend will adapt three categories of scripts from the legacy Dockyard system. Rather than using these scripts as-is, we will extract their core calculation logic and data processing patterns while modernizing the architecture for our demo needs. The key principle is to preserve the mathematical and business logic while replacing the infrastructure components (S3, Parquet) with our simpler PostgreSQL-based approach.

### A.1 Data Architecture Scripts Migration Strategy

#### Portfolio Data Ingestion (investment_portfolio_holdings_collection.py)
**Legacy Functionality:**

- Reads daily Excel files from Paragon system
- Processes multiple years of historical holdings
- Standardizes column names and data types
- Uploads to S3 in Parquet format
- Handles various Excel format variations

**Migration Strategy:**
The AI agent should extract the core data transformation logic while replacing the Excel/S3 infrastructure:

- Replace Excel parsing with CSV ingestion - The column standardization logic (exposure(v) → exposure, pl(v) → pnl) should be preserved but applied to CSV inputs
- Preserve position type determination - The logic for determining long/short based on quantity sign should be maintained
- Adapt the exposure percentage calculations - The fund-level calculations for exposure% should be reimplemented
- Replace S3 uploads with direct database writes - Instead of creating Parquet files, write directly to PostgreSQL tables
- ~~Generate historical snapshots programmatically - Rather than processing years of files, create 90 days of synthetic historical data based on the uploaded positions~~ *(REMOVED - V1.4 scope change)*

**Key Business Logic to Preserve:**

- Position exposure as percentage of total portfolio
- Long/short classification based on quantity
- P&L field mappings and standardization
- Portfolio aggregation calculations

#### Market Data Collection (polygon_collection.py)
**Legacy Functionality:**

- Fetches daily OHLCV data from Polygon.io
- Handles multiple timeframes (minute/daily)
- Manages API rate limits and retries
- Stores data in S3/Parquet format

**Migration Strategy:**
The AI agent should maintain the Polygon API integration while simplifying the storage:

- Keep the same API endpoints and parameters - The Polygon API calls should remain identical
- Remove minute-level data handling - Focus only on daily data for the demo
- Replace S3 storage with PostgreSQL - Write market data directly to the database
- ~~**CRITICAL**: Use this integration to fetch real historical data for all positions after CSV upload~~ *(REMOVED - V1.4 scope change)*
- ~~**Generate authentic 90-day historical snapshots using actual market prices, not mock data**~~ *(REMOVED - V1.4 scope change)*
- Implement proper rate limiting and caching to optimize API usage

**Key Integration Points:**

- Preserve the exact Polygon API request format
- Maintain the data field mappings (o→open, h→high, etc.)
- Keep the same date handling logic
- Add support for both stocks and ETFs (for factor calculations)

#### Security Enrichment (yfinance_gics_industry_sector.py)
**Legacy Functionality:**

- Fetches GICS sector/industry classification
- Enriches securities with metadata
- Runs as a separate batch process

**Migration Strategy:**
The AI agent should integrate this into the security creation workflow:

- Make enrichment synchronous - Call during security creation rather than as a batch
- Add option parsing logic - Extend to handle OCC option symbols
- Cache enrichment data - Avoid repeated API calls for the same security
- Handle failures gracefully - Don't block position creation if enrichment fails

### A.2 Calculation Engine Migration Strategy

#### Risk and Analytics Engine (reporting_plotting_analytics.py)
This is the most complex script with multiple calculation types. The AI agent should break it into focused services:

##### Factor Exposure Calculations
**Legacy Functionality:**

- Calculates position-level betas to factor ETFs
- Uses 60-day rolling regression
- Aggregates to portfolio level using position weights
- Creates factor covariance matrix

**Migration Strategy:**

- Extract the beta calculation methodology - The covariance/variance approach should be preserved exactly
- Maintain the same factor definitions - Use the same ETF proxies (SPY, VTV, VUG, etc.)
- Preserve the regression window - Keep the 60-day lookback period
- Store results in database - Pre-calculate and store rather than computing on-demand
- Add the 8th factor - Implement custom logic for "Short Interest" factor

**Mathematical Preservations:**

- Beta = Covariance(asset, factor) / Variance(factor)
- Portfolio exposure = Σ(position_weight × position_beta)
- Minimum 20 observations for valid regression
- Handle missing data appropriately

##### Portfolio Risk Metrics
**Legacy Functionality:**

- Calculates portfolio volatility
- Computes Sharpe ratios
- Tracks maximum drawdown
- Generates VaR estimates

**Migration Strategy:**

- Extract return calculation logic - Preserve the exact method for calculating daily returns
- Maintain volatility calculations - Use the same annualization factor (√252)
- Preserve drawdown methodology - Keep the peak-to-trough calculation
- Simplify VaR calculation - Use parametric approach for demo

##### Performance Attribution
**Legacy Functionality:**

- Calculates position-level P&L
- Aggregates by various groupings
- Handles currency and basis adjustments

**Migration Strategy:**

- Simplify to price-based P&L - Remove complex currency handling
- Preserve aggregation logic - Keep grouping by sector/strategy
- Store daily snapshots - Pre-calculate for performance

### A.3 Implementation Guidelines for AI Agent

#### Code Organization Principles

- Service Layer Architecture - Each calculation type should be its own service class
- Preserve Core Logic - Mathematical calculations must match exactly
- Modernize Infrastructure - Replace S3/Parquet with PostgreSQL, replace synchronous with async
- Add Type Safety - Use type hints and Pydantic models throughout
- Improve Error Handling - Add comprehensive logging and error recovery

#### Data Flow Architecture

**Batch Processing Pipeline:**

- CSV Upload → Security Enrichment → Position Creation → Historical Generation
- Market Data Fetch → Price Storage → Return Calculation → Risk Metrics
- Factor Data → Beta Calculation → Exposure Aggregation → Storage

**Calculation Dependencies:**

- Returns depend on prices
- Betas depend on returns
- Exposures depend on betas and weights
- Risk metrics depend on returns and exposures

#### Testing Strategy

- Unit Tests for Calculations - Verify mathematical accuracy against known results
- Integration Tests for Data Flow - Ensure pipeline processes correctly
- Regression Tests - Compare results with legacy system outputs where possible

#### Performance Optimizations

- Vectorized Calculations - Use pandas/numpy operations rather than loops
- Bulk Database Operations - Insert many records at once
- Parallel Processing - Calculate betas for multiple securities concurrently
- Caching Strategy - Store immutable calculations permanently

#### Key Differences from Legacy

- No S3/Parquet - All data in PostgreSQL
- No Real-time Updates - Batch processing only
- Simplified Portfolio Structure - Single portfolio per user
- Mock Greeks - No complex option pricing
- Pre-calculated Metrics - Compute during batch, serve from database

The AI agent should focus on extracting the business logic and calculations while building a modern, maintainable architecture suitable for the demo requirements.

---

*This PRD/EDD provides a comprehensive blueprint for building the SigmaSight backend demonstration system.*
