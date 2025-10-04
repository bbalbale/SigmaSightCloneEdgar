# DATABASE_DESIGN_ADDENDUM_V1.4.1.md

## Overview
This addendum resolves all 15 unresolved questions identified by the coding agent and provides complete database schemas, implementation details, and deployment configuration for SigmaSight V1.4.

## 1. Complete Database Schema

### 1.1 Users & Authentication Tables

```sql
-- Users table for authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_demo BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL  -- Soft delete
);

-- Single portfolio per user (enforced by unique constraint)
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL DEFAULT 'My Portfolio',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,  -- Soft delete
    UNIQUE(user_id)  -- Enforces single portfolio per user
);

-- No session table needed - JWTs are stateless
-- No refresh tokens for V1 - users login daily
```

### 1.2 Market Data Cache (Enhanced)

```sql
-- Enhanced market data cache with sector/industry
CREATE TABLE market_data_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4) NOT NULL,
    volume BIGINT,
    -- NEW FIELDS
    sector VARCHAR(100),        -- From YFinance
    industry VARCHAR(100),      -- From YFinance  
    data_source VARCHAR(20) NOT NULL DEFAULT 'polygon',  -- 'polygon' or 'yfinance'
    -- END NEW FIELDS
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);
```

### 1.3 Factor Definitions Table

```sql
-- Fixed factor definitions (8 factors)
CREATE TABLE factors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    etf_proxy VARCHAR(10) NOT NULL,  -- ETF ticker used as proxy
    factor_type VARCHAR(20) NOT NULL, -- 'style', 'sector', 'macro'
    calculation_method TEXT,          -- Description of calculation
    display_order INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert the 8 fixed factors
INSERT INTO factors (name, description, etf_proxy, factor_type, display_order) VALUES
('Market Beta', 'Exposure to overall market movements', 'SPY', 'macro', 1),
('Momentum', 'Exposure to recent price momentum', 'MTUM', 'style', 2),
('Value', 'Exposure to value characteristics', 'VTV', 'style', 3),
('Growth', 'Exposure to growth characteristics', 'VUG', 'style', 4),
('Quality', 'Exposure to quality metrics', 'QUAL', 'style', 5),
('Size', 'Exposure to small-cap stocks', 'IWM', 'style', 6),
('Low Volatility', 'Exposure to low volatility stocks', 'SPLV', 'style', 7),
('Short Interest', 'Custom calculation based on short interest', 'CUSTOM', 'macro', 8);
```

### 1.4 Tags Tables (Complete)

```sql
-- Tags with support for regular and strategy types
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    tag_type VARCHAR(20) NOT NULL CHECK (tag_type IN ('REGULAR', 'STRATEGY')),
    color VARCHAR(7) DEFAULT '#6B7280',  -- Hex color
    usage_count INTEGER DEFAULT 0,       -- Track popularity
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,  -- Soft delete
    UNIQUE(user_id, name)
);

-- Many-to-many relationship
CREATE TABLE position_tags (
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (position_id, tag_id)
);
```

### 1.5 Enhanced Positions Table

```sql
-- Positions with parsed options data
CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(30) NOT NULL,
    position_type position_type_enum NOT NULL,
    quantity DECIMAL(15,4) NOT NULL,
    
    -- Options-specific parsed fields
    underlying_symbol VARCHAR(10),     -- e.g., 'AAPL' from 'AAPL240119C00150000'
    expiration_date DATE,             -- e.g., '2024-01-19'
    strike_price DECIMAL(10,2),       -- e.g., 150.00
    option_type VARCHAR(4),           -- 'CALL' or 'PUT'
    
    -- Entry tracking
    entry_price DECIMAL(12,4) NOT NULL,
    entry_date DATE NOT NULL,
    
    -- Current values (updated by batch)
    last_price DECIMAL(12,4),         -- Used as fallback for daily P&L calculations when market_data_cache lacks historical data
    market_value DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2),
    unrealized_pnl_pct DECIMAL(8,4),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE DEFAULT NULL  -- Soft delete
);
```

### 1.6 Portfolio Snapshots

```sql
-- Daily portfolio snapshots for historical tracking
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    
    -- Portfolio metrics
    total_value DECIMAL(15,2) NOT NULL,
    cash_value DECIMAL(15,2) DEFAULT 0,
    long_value DECIMAL(15,2) NOT NULL,
    short_value DECIMAL(15,2) NOT NULL,
    
    -- Exposures
    gross_exposure DECIMAL(15,2) NOT NULL,
    net_exposure DECIMAL(15,2) NOT NULL,
    
    -- P&L
    daily_pnl DECIMAL(15,2),
    daily_pnl_pct DECIMAL(8,4),
    cumulative_pnl DECIMAL(15,2),
    
    -- Risk metrics
    portfolio_beta DECIMAL(6,3),
    portfolio_volatility DECIMAL(6,4),
    sharpe_ratio DECIMAL(6,3),
    max_drawdown DECIMAL(6,4),
    
    -- Greeks aggregates
    total_delta DECIMAL(10,4),
    total_gamma DECIMAL(10,4),
    total_theta DECIMAL(10,4),
    total_vega DECIMAL(10,4),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, snapshot_date)
);
```

### 1.7 Batch Processing Tables

```sql
-- Simple batch job tracking
CREATE TABLE batch_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL,  -- 'market_data', 'risk_calc', 'snapshot'
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    metadata JSONB,  -- Job-specific data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Track last successful run for each job type
CREATE TABLE batch_job_schedules (
    job_type VARCHAR(50) PRIMARY KEY,
    cron_expression VARCHAR(100) NOT NULL,  -- e.g., '0 16 * * *' for 4 PM daily
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    is_enabled BOOLEAN DEFAULT true
);
```

## 2. Data Transformation Specifications

### 2.1 CSV Import Transformation

```python
def parse_csv_row(row: dict, user_id: str, portfolio_id: str) -> dict:
    """Transform CSV row to position record"""
    
    symbol = row['ticker'].strip().upper()
    quantity = float(row['quantity'])
    
    # Parse position type
    position_type = determine_position_type(symbol, quantity)
    
    # Parse options data if applicable
    options_data = parse_options_symbol(symbol) if is_options_symbol(symbol) else {}
    
    # Parse tags
    tags = [tag.strip() for tag in row.get('tags', '').split(',') if tag.strip()]
    
    return {
        'portfolio_id': portfolio_id,
        'symbol': symbol,
        'position_type': position_type,
        'quantity': abs(quantity),  # Always store positive
        'entry_price': float(row['entry_price']),
        'entry_date': row['entry_date'],  # Expected format: YYYY-MM-DD
        'tags': tags,
        **options_data  # Includes underlying_symbol, expiration_date, etc.
    }

def determine_position_type(symbol: str, quantity: float) -> str:
    """Determine position type from symbol and quantity"""
    
    if is_options_symbol(symbol):
        # OCC format check
        option_type = 'C' if 'C' in symbol[-9] else 'P'
        
        if quantity > 0:
            return 'LC' if option_type == 'C' else 'LP'
        else:
            return 'SC' if option_type == 'C' else 'SP'
    else:
        # Stock position
        return 'LONG' if quantity > 0 else 'SHORT'

def is_options_symbol(symbol: str) -> bool:
    """Check if symbol is OCC format option"""
    # OCC format: AAPL240119C00150000 (min 15 chars)
    return len(symbol) >= 15 and symbol[-9:-7].isdigit()

def parse_options_symbol(symbol: str) -> dict:
    """Parse OCC format option symbol"""
    if not is_options_symbol(symbol):
        return {}
    
    # Example: AAPL240119C00150000
    # Find where the date starts (first digit after letters)
    date_start = next(i for i, c in enumerate(symbol) if c.isdigit())
    
    underlying = symbol[:date_start]
    date_str = symbol[date_start:date_start+6]  # YYMMDD
    option_type = 'CALL' if 'C' in symbol[date_start+6] else 'PUT'
    strike_str = symbol[-8:]  # 00150000 = $150.00
    
    return {
        'underlying_symbol': underlying,
        'expiration_date': f'20{date_str[:2]}-{date_str[2:4]}-{date_str[4:6]}',
        'strike_price': float(strike_str) / 1000,
        'option_type': option_type
    }
```

### 2.2 Greeks Calculation (V1.4, Mibian-only)

```python
import mibian
from typing import Dict
import logging

logger = logging.getLogger(__name__)

async def calculate_greeks(position: Dict) -> Dict[str, float]:
    """Calculate Greeks using mibian Black-Scholes. Stocks: no Greeks. Expired options: zero Greeks. Return None values on error."""
    position_type = position['position_type']
    quantity = position['quantity']

    # Stocks: no Greeks
    if position_type in ['LONG', 'SHORT']:
        return {'delta': float(quantity > 0) - float(quantity < 0), 'gamma': 0.0, 'theta': 0.0, 'vega': 0.0, 'rho': 0.0}

    try:
        underlying_price = position.get('underlying_price')
        strike = position.get('strike_price')
        days_to_expiry = position.get('days_to_expiry', 0)
        volatility = position.get('implied_volatility', 0.25)  # Default 25%
        risk_free_rate = 5.0  # Percent for mibian

        if days_to_expiry <= 0:
            return {'delta': 0.0, 'gamma': 0.0, 'theta': 0.0, 'vega': 0.0, 'rho': 0.0}

        if not all([underlying_price, strike]):
            raise ValueError("Missing required option parameters")

        is_call = position_type in ['LC', 'SC']

        bs = mibian.BS([underlying_price, strike, risk_free_rate, days_to_expiry], volatility=volatility * 100)

        delta = bs.callDelta if is_call else bs.putDelta
        gamma = bs.gamma
        theta = bs.callTheta if is_call else bs.putTheta
        vega = bs.vega
        rho = bs.callRho if is_call else bs.putRho

        scale = quantity if position_type in ['LC', 'LP'] else -quantity

        return {
            'delta': float(delta) * scale,
            'gamma': float(gamma) * scale,
            'theta': float(theta) * scale,
            'vega': float(vega) * scale,
            'rho': float(rho) * scale
        }
    except Exception as e:
        logger.warning(f"Greeks calculation failed: {e}")
        return {'delta': None, 'gamma': None, 'theta': None, 'vega': None, 'rho': None}
    base_greeks = MOCK_GREEKS[position_type].copy()
    
    # Scale by quantity (contracts for options, shares/100 for stocks)
    scale = quantity if position_type in ['LC', 'SC', 'LP', 'SP'] else quantity / 100
    
    return {
        'delta': base_greeks['delta'] * scale,
        'gamma': base_greeks['gamma'] * scale,
        'theta': base_greeks['theta'] * scale,
        'vega': base_greeks['vega'] * scale,
        'rho': base_greeks['rho'] * scale
    }
```

## 3. Database Indexes

```sql
-- Primary key indexes are automatic

-- Foreign key indexes (some automatic, explicitly ensure)
CREATE INDEX idx_portfolios_user_id ON portfolios(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_positions_portfolio_id ON positions(portfolio_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_position_tags_position_id ON position_tags(position_id);
CREATE INDEX idx_position_tags_tag_id ON position_tags(tag_id);

-- Common query patterns
CREATE INDEX idx_positions_symbol ON positions(symbol) WHERE deleted_at IS NULL;
CREATE INDEX idx_positions_type ON positions(position_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_market_data_symbol_date ON market_data_cache(symbol, date DESC);
CREATE INDEX idx_snapshots_portfolio_date ON portfolio_snapshots(portfolio_id, snapshot_date DESC);

-- Tag queries
CREATE INDEX idx_tags_user_type ON tags(user_id, tag_type) WHERE deleted_at IS NULL;

-- Options queries
CREATE INDEX idx_positions_expiration ON positions(expiration_date) 
    WHERE expiration_date IS NOT NULL AND deleted_at IS NULL;

-- Batch job monitoring
CREATE INDEX idx_batch_jobs_status_created ON batch_jobs(status, created_at DESC);
```

## 4. Environment Configuration

### 4.1 Local Development (.env)

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sigmasight_dev

# Authentication
JWT_SECRET=local-development-secret-do-not-use-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# External APIs
POLYGON_API_KEY=your_polygon_api_key_here
YFINANCE_CACHE_DIR=./cache/yfinance

# Application
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Batch Processing
BATCH_MARKET_DATA_HOUR=16  # 4 PM
BATCH_RISK_CALC_HOUR=17    # 5 PM
```

### 4.2 Railway Production Environment

```bash
# Set these in Railway dashboard:

# DATABASE_URL - Automatically provided by Railway Postgres
JWT_SECRET=<generate with: openssl rand -hex 32>
POLYGON_API_KEY=<your production API key>
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 4.3 Configuration Management

```python
# config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    
    # APIs
    polygon_api_key: str
    
    # App
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
```

## 5. Demo Data Specifications

### 5.1 Demo Users

```sql
-- Create 3 demo users with different portfolio strategies
INSERT INTO users (username, email, password_hash, is_demo) VALUES
('demo_individual', 'demo_individual@sigmasight.com', '<bcrypt hash of "demo123">', true),
('demo_hnw', 'demo_hnw@sigmasight.com', '<bcrypt hash of "demo123">', true),
('demo_hedgefundstyle', 'demo_hedgefundstyle@sigmasight.com', '<bcrypt hash of "demo123">', true);
```

### 5.2 Demo Portfolio Characteristics

1. **demo_growth**: Tech-heavy, momentum plays, some options
   - 25 positions: 18 long stocks, 3 short stocks, 4 options
   - Heavy NASDAQ exposure
   
2. **demo_value**: Traditional value investing
   - 20 positions: 15 long stocks, 5 short stocks
   - Focus on financials, energy
   
3. **demo_balanced**: Mixed strategies
   - 30 positions: 20 stocks, 10 options
   - Includes pairs trades and hedges

### 5.3 Demo Data Requirements

For the V1.4 demo, we need realistic portfolio data:

1. ~~**Historical Market Data**~~ *(REMOVED - V1.4 scope change)*:
   - ~~Fetch real 90-day historical prices from Polygon.io for all positions~~
   - ~~Store in `market_data_cache` table with `data_source='polygon'`~~
   - ~~Include OHLCV data for accurate calculations~~

2. **Portfolio Snapshots** *(MODIFIED - Forward-only)*:
   - ~~Generate 90 daily snapshots using actual historical closing prices~~
   - ~~Calculate real P&L based on actual market movements~~
   - ~~Only create snapshots for trading days (skip weekends/holidays)~~
   - ~~Each snapshot should reflect realistic portfolio values~~
   - **NEW**: Generate daily forward snapshots from CSV upload date only
   - **NEW**: Use current market data for daily P&L calculations

3. **Demo Users** (demo_growth, demo_value, demo_balanced) *(MODIFIED)*:
   - ~~Each portfolio will show actual historical performance~~
   - ~~Risk metrics calculated from real price volatility~~
   - ~~Factor exposures based on actual market correlations~~
   - **NEW**: Demo portfolios will show forward performance from upload date
   - **NEW**: Risk metrics calculated from daily forward data collection

## 6. Batch Processing Schedule

```python
# Batch job configuration
BATCH_JOBS = {
    'market_data_update': {
        'cron': '0 16 * * 1-5',  # 4 PM weekdays
        'function': 'update_market_data',
        'timeout': 300  # 5 minutes
    },
    'calculate_risk_metrics': {
        'cron': '0 17 * * 1-5',  # 5 PM weekdays
        'function': 'calculate_all_risk_metrics',
        'timeout': 600  # 10 minutes
    },
    'create_daily_snapshot': {
        'cron': '30 17 * * 1-5',  # 5:30 PM weekdays
        'function': 'create_portfolio_snapshots',
        'timeout': 300
    }
}
```

## 7. Implementation Priority

### Phase 1 - Core Tables (Week 1)
1. Users & Authentication
2. Portfolios
3. Positions (with options parsing)
4. Market Data Cache
5. Tags

### Phase 2 - Analytics (Week 2)
1. Portfolio Snapshots
2. Position Greeks
3. Factor Definitions
4. Risk Metrics

### Phase 3 - Operations (Week 3)
1. Batch Jobs
2. Demo Data Generation
3. Historical Snapshots

## 8. Key Decisions Summary

1. **Single Portfolio**: Enforced by unique constraint
2. **Mock Greeks**: Use provided values, no pricing library
3. **Sync API**: No async job management
4. **Batch Processing**: All calculations run on schedule
5. **Soft Deletes**: Track deleted_at, never hard delete
6. **JWT Auth**: Stateless, 24-hour expiry
7. **Tag System**: Supports both regular and strategy tags

## 9. Data Requirements for Real Calculations

To support real calculations in V1.4, ensure:

1. **market_data_cache**: Minimum 90 days of historical prices
2. **Factor ETF data**: Daily prices for SPY, VTV, VUG, MTUM, QUAL, SLY, USMV
3. **Risk-free rate**: Configure as environment variable (default 5%)
4. **Calculation frequency**: Daily batch after market close

## 10. Migration Commands

```bash
# Create database
createdb sigmasight_dev

# Run migrations (using Alembic)
alembic init migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head

# Load demo data
python scripts/load_demo_data.py
```

This addendum provides complete resolution to all identified issues and clear implementation guidance for the SigmaSight V1 database.

## 11. Database Integration for Calculation Functions (V1.4.1 Update)

### 11.1 Enhanced Function Signatures

The core calculation functions have been updated to integrate directly with the database for improved robustness and performance:

#### Updated: `calculate_daily_pnl(db, position, current_price)`
- **Previous signature**: `calculate_daily_pnl(position, previous_price, current_price)`
- **New signature**: `calculate_daily_pnl(db, position, current_price)`
- **Enhancement**: Automatically queries `market_data_cache` for previous trading day price
- **Fallback behavior**: Uses `position.last_price` when historical data is unavailable
- **Benefits**: Eliminates need for caller to fetch previous price, reduces API calls

#### Enhanced: `calculate_position_market_value(position, current_price)`
- **Integration**: Works seamlessly with database-cached prices
- **Fallback behavior**: Uses `position.last_price` for missing current price data
- **Performance**: Reduces external API dependencies through intelligent caching

### 11.2 Database Fallback Strategy

The calculation engine implements a robust fallback hierarchy:

1. **Primary**: Real-time data from Polygon.io API
2. **Secondary**: Cached data from `market_data_cache` table
3. **Tertiary**: Position-stored `last_price` field
4. **Fallback**: Mock/estimated values where appropriate

This approach ensures calculation functions never fail due to missing market data while maintaining accuracy when data is available.

### 11.3 Performance Optimizations

- **Indexed queries**: All market data queries use optimized indexes on `(symbol, date)`
- **Batch processing**: Multiple position calculations can reuse cached price data
- **Smart caching**: Only fetches missing data, leverages existing cache entries
- **Database connection pooling**: Efficient resource usage for calculation-heavy operations