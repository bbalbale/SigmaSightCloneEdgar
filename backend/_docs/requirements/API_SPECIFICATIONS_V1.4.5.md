# SigmaSight Backend API Specifications V1.4.5

**Version**: 1.4.5  
**Date**: September 5, 2025  
**Status**: Production + Development Planning  
**Source of Truth**: API_IMPLEMENTATION_STATUS.md  

> 📋 **Dual-Purpose Document**
> 
> **Part I**: ✅ Production-ready endpoints (18 endpoints) - fully implemented with real data  
> **Part II**: 🎯 Planned endpoints - development specifications for future implementation  

## Document Structure

### ✅ **Part I: Production-Ready Endpoints**
- 18 fully implemented endpoints returning real database data
- All endpoints tested and verified as working
- Ready for frontend integration and production use

### 🎯 **Part II: Planned Endpoints** 
- Development specifications for future API endpoints
- Design guidance for analytics, management, export, and system namespaces
- Implementation roadmap and priorities

---

## Strategic Direction

### Namespace Philosophy
- **`/data/`**: Data for LLM consumption
- **`/analytics/`**: All calculated metrics and derived values
- **`/management/`**: Portfolio and position CRUD operations
- **`/export/`**: Data export and report generation
- **`/system/`**: System utilities and job management

### Key Design Principles
1. **Clear Separation**: Raw data vs. calculated metrics have distinct namespaces
2. **Self-Documenting**: Endpoint paths immediately convey data type and purpose
3. **LLM-Optimized**: `/data/` endpoints return complete, denormalized datasets
4. **Consistent Depth**: All major features at the second namespace level

---

# PART I: PRODUCTION-READY ENDPOINTS ✅

This section documents the **18 fully implemented and production-ready endpoints** in the SigmaSight Backend API. These endpoints have been **code-verified** to access database data through direct ORM queries or service layers and are ready for frontend integration.

### Complete Endpoint List

#### Authentication Endpoints (4)
- [`POST /auth/login`](#11-login) - Authenticate user and return JWT token
- [`POST /auth/register`](#12-register) - Register a new user
- [`GET /auth/me`](#13-get-current-user) - Get current authenticated user information  
- [`POST /auth/refresh`](#14-refresh-token) - Refresh JWT token

#### Data Endpoints (13)
- [`GET /data/portfolios`](#21-get-portfolios) - Get all portfolios for authenticated user
- [`GET /data/portfolio/{portfolio_id}/complete`](#22-get-complete-portfolio) - Get complete portfolio data with optional sections
- [`GET /data/portfolio/{portfolio_id}/data-quality`](#23-get-data-quality) - Get data quality metrics for portfolio
- [`GET /data/positions/details`](#24-get-position-details) - Get detailed position information with P&L calculations
- [`GET /data/prices/historical/{symbol_or_position_id}`](#25-get-historical-prices) - Get historical price data for symbol or position
- [`GET /data/prices/quotes`](#26-get-market-quotes) - Get real-time market quotes for symbols
- [`GET /data/factors/etf-prices`](#27-get-factor-etf-prices) - Get current and historical prices for factor ETFs
- [`GET /data/greeks/{portfolio_id}`](#28-get-greeks-data) - Get Greeks data for portfolio positions
- [`GET /data/factors/{portfolio_id}`](#29-get-factor-exposures) - Get factor exposure data for portfolio
- [`GET /data/portfolios/{portfolio_id}/aggregations`](#210-get-portfolio-aggregations) - Get portfolio-level aggregated metrics
- [`GET /data/portfolios/{portfolio_id}/risk-summary`](#211-get-risk-summary) - Get comprehensive risk metrics for portfolio
- [`GET /data/portfolios/{portfolio_id}/positions/summary`](#212-get-position-summary) - Get position summary with key metrics
- [`GET /data/positions/{position_id}/details`](#213-get-position-details-by-id) - Get detailed information for specific position

#### Administration Endpoints (5)
- [`GET /admin/batch/jobs/status`](#31-get-batch-job-status) - Get status of recent batch jobs
- [`GET /admin/batch/jobs/summary`](#32-get-batch-job-summary) - Get summary statistics of batch jobs  
- [`DELETE /admin/batch/jobs/{job_id}/cancel`](#33-cancel-batch-job) - Cancel a running batch job
- [`GET /admin/batch/data-quality`](#34-get-data-quality-status) - Get data quality status and metrics for portfolios
- [`POST /admin/batch/data-quality/refresh`](#35-refresh-market-data-for-quality) - Refresh market data to improve data quality scores

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
All data endpoints require JWT authentication via Bearer token:
```
Authorization: Bearer <jwt_token>
```

---

## 1. Authentication Endpoints

### 1.1 Login
**Endpoint**: `POST /auth/login`  
**Status**: ✅ Fully Implemented  
**Authentication**: None required  
**OpenAPI Description**: "Authenticate user and return JWT token (in response body AND cookie)"  
**Database Access**: Direct ORM queries to `User` and `Portfolio` tables  
**Service Layer**: Uses `verify_password`, `create_token_response` from auth core  

Authenticates a user and returns JWT token in both response body and HTTP-only cookie.

**Request Body**:
```json
{
  "email": "demo_hnw@sigmasight.com", 
  "password": "demo12345"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 2592000
}
```

### 1.2 Register
**Endpoint**: `POST /auth/register`  
**Status**: ✅ Fully Implemented  
**Authentication**: None required  
**OpenAPI Description**: "Register a new user (admin-only initially)"  
**Database Access**: Direct ORM queries - Creates `User` and `Portfolio` records  
**Service Layer**: Uses `get_password_hash` from auth core  

**Request Body**:
```json
{
  "email": "newuser@example.com",
  "password": "secure_password",
  "full_name": "New User"
}
```

**Response**:
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "email": "newuser@example.com",
  "full_name": "New User",
  "is_active": true,
  "created_at": "2025-09-05T12:30:45Z"
}
```

### 1.3 Get Current User
**Endpoint**: `GET /auth/me`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Get current authenticated user information"  
**Database Access**: Via JWT token validation in `get_current_user` dependency  
**Service Layer**: Uses auth core dependencies  

**Response**:
```json
{
  "id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "email": "demo_hnw@sigmasight.com",
  "full_name": "Demo HNW User",
  "is_active": true,
  "created_at": "2025-08-08T12:00:00Z",
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e"
}
```  

### 1.4 Refresh Token
**Endpoint**: `POST /auth/refresh`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required (Bearer token)  
**OpenAPI Description**: "Refresh JWT token (returns new token in body AND cookie)"  
**Database Access**: Direct ORM query to `Portfolio` table for consistent portfolio_id  
**Service Layer**: Uses `create_token_response` from auth core  

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 2592000
}
```

---

## 2. Data Endpoints

### 2.1 Get Portfolios
**Endpoint**: `GET /data/portfolios`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get all portfolios for authenticated user"  
**Database Access**: Direct ORM query to `Portfolio` table  
**Service Layer**: None - direct database access  

Returns all portfolios for the authenticated user with real database data.

**Response**:
```json
{
  "data": [
    {
      "id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
      "name": "Demo High Net Worth Investor Portfolio",
      "type": "HNW",
      "created_at": "2025-08-08T12:00:00Z",
      "positions_count": 21,
      "total_value": 1662126.38
    }
  ]
}
```

### 2.2 Get Complete Portfolio
**Endpoint**: `GET /data/portfolio/{portfolio_id}/complete`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get complete portfolio data with optional sections"  
**Database Access**: Portfolio, Position, MarketDataCache, PositionGreeks, PositionFactorExposure tables  
**Service Layer**: PortfolioDataService (portfolio overview), MarketDataService (market data), direct ORM queries for positions and calculations  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `sections` (query, optional): Comma-separated list of sections to include
- `as_of_date` (query, optional): Date for historical data (YYYY-MM-DD format)

**Special Notes**: Cash balance calculated as 5% of portfolio value (not stored in database)

**Response**:
```json
{
  "portfolio": {
    "id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
    "name": "Demo High Net Worth Investor Portfolio",
    "description": "Diversified portfolio with options strategies",
    "currency": "USD",
    "created_at": "2025-08-08T12:00:00Z",
    "updated_at": "2025-09-05T10:00:00Z"
  },
  "positions": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "symbol": "AAPL",
      "position_type": "LONG",
      "quantity": 100.0,
      "current_price": 175.25,
      "market_value": 17525.00,
      "unrealized_pnl": 1525.00,
      "cost_basis": 160.00
    }
  ],
  "summary": {
    "total_value": 1662126.38,
    "cash_balance": 83106.32,
    "total_pnl": 125432.18,
    "positions_count": 21
  },
  "market_data": {
    "last_updated": "2025-09-05T15:30:00Z",
    "data_quality": 95.5
  }
}
```

### 2.3 Get Data Quality
**Endpoint**: `GET /data/portfolio/{portfolio_id}/data-quality`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get data quality metrics for portfolio"  
**Database Access**: Position, MarketDataCache tables  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID

**Response**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "overall_score": 95.5,
  "metrics": {
    "price_coverage": {
      "score": 98.0,
      "total_positions": 21,
      "positions_with_prices": 21,
      "missing_prices": 0
    },
    "data_freshness": {
      "score": 93.0,
      "last_updated": "2025-09-05T15:30:00Z",
      "hours_since_update": 2.5
    },
    "greeks_coverage": {
      "score": 85.0,
      "options_positions": 8,
      "positions_with_greeks": 7,
      "missing_greeks": 1
    }
  },
  "recommendations": [
    "Update options Greeks for SPY position",
    "Refresh intraday prices during market hours"
  ],
  "last_assessed": "2025-09-05T18:00:00Z"
}
```

### 2.4 Get Position Details
**Endpoint**: `GET /data/positions/details`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get detailed position information with P&L calculations"  
**Database Access**: Position, MarketDataCache tables  
**Service Layer**: Direct ORM queries with P&L calculations  

**Parameters**:
- `portfolio_id` (query): Portfolio UUID
- `position_type` (query, optional): Filter by position type
- `include_inactive` (query, optional): Include soft-deleted positions

**Response**:
```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "symbol": "AAPL",
      "position_type": "LONG",
      "quantity": 100.0,
      "cost_basis": 160.00,
      "current_price": 175.25,
      "market_value": 17525.00,
      "unrealized_pnl": 1525.00,
      "unrealized_pnl_percent": 9.53,
      "day_change": 285.00,
      "day_change_percent": 1.65,
      "created_at": "2025-08-15T10:30:00Z",
      "updated_at": "2025-09-05T15:30:00Z"
    },
    {
      "id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
      "symbol": "SPY_240920C00550000",
      "position_type": "CALL",
      "quantity": 5.0,
      "cost_basis": 2.85,
      "current_price": 4.20,
      "market_value": 2100.00,
      "unrealized_pnl": 675.00,
      "unrealized_pnl_percent": 47.37,
      "day_change": 125.00,
      "day_change_percent": 6.33,
      "created_at": "2025-08-20T14:15:00Z",
      "updated_at": "2025-09-05T15:30:00Z"
    }
  ],
  "summary": {
    "total_positions": 21,
    "total_market_value": 1662126.38,
    "total_unrealized_pnl": 125432.18,
    "total_day_change": -8942.15,
    "long_positions": 15,
    "short_positions": 2,
    "options_positions": 4
  }
}
```

### 2.5 Get Historical Prices
**Endpoint**: `GET /data/prices/historical/{symbol_or_position_id}`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get historical price data for symbol or position"  
**Database Access**: MarketDataCache table  
**Service Layer**: MarketDataService  

**Parameters**:
- `symbol_or_position_id` (path): Symbol or position UUID
- `days` (query, optional): Number of days of history (default 30)
- `start_date` (query, optional): Start date (YYYY-MM-DD)
- `end_date` (query, optional): End date (YYYY-MM-DD)

**Response**:
```json
{
  "symbol": "AAPL",
  "data_points": 30,
  "start_date": "2025-08-06",
  "end_date": "2025-09-05",
  "prices": [
    {
      "date": "2025-09-05",
      "open": 174.80,
      "high": 176.15,
      "low": 174.25,
      "close": 175.25,
      "volume": 58432100,
      "adjusted_close": 175.25
    },
    {
      "date": "2025-09-04",
      "open": 173.50,
      "high": 175.20,
      "low": 173.10,
      "close": 174.65,
      "volume": 62145800,
      "adjusted_close": 174.65
    }
  ],
  "statistics": {
    "period_return": 0.0953,
    "volatility": 0.285,
    "max_price": 178.95,
    "min_price": 160.12,
    "avg_volume": 55328450
  },
  "last_updated": "2025-09-05T20:00:00Z"
}
```

### 2.6 Get Market Quotes
**Endpoint**: `GET /data/prices/quotes`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get real-time market quotes for symbols"  
**Database Access**: MarketDataCache table (latest prices)  
**Service Layer**: MarketDataService  

**Parameters**:
- `symbols` (query): Comma-separated list of symbols

**Response**:
```json
{
  "quotes": [
    {
      "symbol": "AAPL",
      "price": 175.25,
      "change": 0.60,
      "change_percent": 0.34,
      "volume": 58432100,
      "bid": 175.20,
      "ask": 175.30,
      "bid_size": 200,
      "ask_size": 300,
      "high_52_week": 199.62,
      "low_52_week": 164.08,
      "market_cap": 2658745000000,
      "timestamp": "2025-09-05T20:00:00Z"
    },
    {
      "symbol": "MSFT",
      "price": 425.18,
      "change": -2.42,
      "change_percent": -0.57,
      "volume": 24785900,
      "bid": 425.10,
      "ask": 425.25,
      "bid_size": 100,
      "ask_size": 150,
      "high_52_week": 468.35,
      "low_52_week": 362.90,
      "market_cap": 3158924000000,
      "timestamp": "2025-09-05T20:00:00Z"
    }
  ],
  "market_status": "closed",
  "last_updated": "2025-09-05T20:00:00Z"
}
```

### 2.7 Get Factor ETF Prices
**Endpoint**: `GET /data/factors/etf-prices`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get current and historical prices for factor ETFs"  
**Database Access**: MarketDataCache table  
**Service Layer**: MarketDataService  

**Parameters**:
- `symbols` (query, optional): Specific ETF symbols to retrieve
- `days` (query, optional): Number of days of history

**Response**:
```json
{
  "factor_etfs": [
    {
      "symbol": "VTI",
      "name": "Vanguard Total Stock Market ETF",
      "factor_type": "market",
      "current_price": 268.45,
      "change": -1.25,
      "change_percent": -0.46,
      "volume": 2845200,
      "last_updated": "2025-09-05T20:00:00Z",
      "historical_prices": [
        {"date": "2025-09-05", "close": 268.45},
        {"date": "2025-09-04", "close": 269.70},
        {"date": "2025-09-03", "close": 271.15}
      ]
    },
    {
      "symbol": "VEA",
      "name": "Vanguard FTSE Developed Markets ETF",
      "factor_type": "international",
      "current_price": 52.18,
      "change": 0.15,
      "change_percent": 0.29,
      "volume": 5928400,
      "last_updated": "2025-09-05T20:00:00Z",
      "historical_prices": [
        {"date": "2025-09-05", "close": 52.18},
        {"date": "2025-09-04", "close": 52.03},
        {"date": "2025-09-03", "close": 51.89}
      ]
    },
    {
      "symbol": "VWO",
      "name": "Vanguard FTSE Emerging Markets ETF",
      "factor_type": "emerging_markets",
      "current_price": 45.32,
      "change": 0.87,
      "change_percent": 1.96,
      "volume": 8234600,
      "last_updated": "2025-09-05T20:00:00Z",
      "historical_prices": [
        {"date": "2025-09-05", "close": 45.32},
        {"date": "2025-09-04", "close": 44.45},
        {"date": "2025-09-03", "close": 44.12}
      ]
    }
  ],
  "summary": {
    "total_etfs": 7,
    "data_coverage": "100%",
    "last_updated": "2025-09-05T20:00:00Z"
  }
}
```

### 2.8 Get Greeks Data
**Endpoint**: `GET /data/greeks/{portfolio_id}`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get Greeks data for portfolio positions"  
**Database Access**: PositionGreeks table  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `position_id` (query, optional): Filter by specific position

**Response**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "greeks_data": [
    {
      "position_id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
      "symbol": "SPY_240920C00550000",
      "position_type": "CALL",
      "quantity": 5.0,
      "greeks": {
        "delta": 0.65,
        "gamma": 0.012,
        "theta": -0.08,
        "vega": 0.15,
        "rho": 0.032,
        "implied_volatility": 0.185
      },
      "underlying_price": 550.25,
      "strike_price": 550.0,
      "expiration_date": "2024-09-20",
      "days_to_expiry": 15,
      "last_updated": "2025-09-05T15:30:00Z"
    },
    {
      "position_id": "c3d4e5f6-g7h8-9012-cdef-345678901234",
      "symbol": "QQQ_241018P00380000",
      "position_type": "PUT",
      "quantity": -3.0,
      "greeks": {
        "delta": -0.35,
        "gamma": 0.008,
        "theta": -0.06,
        "vega": 0.12,
        "rho": -0.025,
        "implied_volatility": 0.195
      },
      "underlying_price": 385.42,
      "strike_price": 380.0,
      "expiration_date": "2024-10-18",
      "days_to_expiry": 43,
      "last_updated": "2025-09-05T15:30:00Z"
    }
  ],
  "portfolio_greeks": {
    "total_delta": 2.20,
    "total_gamma": 0.056,
    "total_theta": -0.42,
    "total_vega": 0.81,
    "total_rho": 0.071,
    "net_delta_exposure": 385420.00
  },
  "summary": {
    "options_positions": 8,
    "positions_with_greeks": 7,
    "coverage_percentage": 87.5,
    "last_updated": "2025-09-05T15:30:00Z"
  }
}
```

### 2.9 Get Factor Exposures
**Endpoint**: `GET /data/factors/{portfolio_id}`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get factor exposure data for portfolio"  
**Database Access**: PositionFactorExposure table  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `position_id` (query, optional): Filter by specific position

**Response**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "factor_exposures": [
    {
      "position_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "symbol": "AAPL",
      "market_value": 17525.00,
      "weight": 0.1054,
      "exposures": {
        "market": 1.12,
        "size": -0.25,
        "value": 0.08,
        "momentum": 0.35,
        "quality": 0.42,
        "low_volatility": -0.18,
        "dividend_yield": 0.12
      },
      "last_updated": "2025-09-05T10:00:00Z"
    },
    {
      "position_id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
      "symbol": "MSFT",
      "market_value": 85036.00,
      "weight": 0.5117,
      "exposures": {
        "market": 1.08,
        "size": -0.22,
        "value": -0.15,
        "momentum": 0.28,
        "quality": 0.58,
        "low_volatility": -0.12,
        "dividend_yield": 0.18
      },
      "last_updated": "2025-09-05T10:00:00Z"
    }
  ],
  "portfolio_exposures": {
    "market": 0.98,
    "size": -0.185,
    "value": 0.045,
    "momentum": 0.225,
    "quality": 0.385,
    "low_volatility": -0.095,
    "dividend_yield": 0.165
  },
  "risk_attribution": {
    "systematic_risk": 0.78,
    "idiosyncratic_risk": 0.22,
    "factor_concentration": {
      "market": 0.45,
      "quality": 0.18,
      "momentum": 0.12,
      "other": 0.25
    }
  },
  "summary": {
    "total_positions": 21,
    "positions_with_exposures": 19,
    "coverage_percentage": 90.5,
    "last_updated": "2025-09-05T10:00:00Z"
  }
}
```

### 2.10 Get Portfolio Aggregations
**Endpoint**: `GET /data/portfolios/{portfolio_id}/aggregations`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get portfolio-level aggregated metrics"  
**Database Access**: Position, MarketDataCache, PositionGreeks, PositionFactorExposure tables  
**Service Layer**: Direct ORM queries with aggregation calculations  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `include_greeks` (query, optional): Include Greeks aggregations
- `include_factors` (query, optional): Include factor aggregations

**Response**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "basic_aggregations": {
    "total_value": 1662126.38,
    "cash_balance": 83106.32,
    "invested_value": 1579020.06,
    "total_pnl": 125432.18,
    "total_pnl_percent": 8.63,
    "day_change": -8942.15,
    "day_change_percent": -0.54
  },
  "position_breakdown": {
    "by_type": {
      "LONG": {"count": 15, "value": 1425680.50, "percentage": 90.29},
      "SHORT": {"count": 2, "value": -45250.00, "percentage": -2.87},
      "CALL": {"count": 3, "value": 126450.00, "percentage": 8.01},
      "PUT": {"count": 1, "value": 72139.56, "percentage": 4.57}
    },
    "by_sector": {
      "Technology": {"count": 8, "value": 845250.00, "percentage": 53.54},
      "Healthcare": {"count": 4, "value": 285640.00, "percentage": 18.09},
      "Financial": {"count": 3, "value": 195320.00, "percentage": 12.37},
      "Consumer": {"count": 3, "value": 142580.00, "percentage": 9.03},
      "Other": {"count": 3, "value": 110230.06, "percentage": 6.98}
    }
  },
  "concentration_metrics": {
    "top_5_positions_weight": 0.68,
    "herfindahl_index": 0.125,
    "effective_positions": 8.7,
    "largest_position_weight": 0.189
  },
  "greeks_aggregations": {
    "total_delta": 2.20,
    "total_gamma": 0.056,
    "total_theta": -0.42,
    "total_vega": 0.81,
    "net_delta_exposure": 385420.00,
    "options_notional": 198589.56
  },
  "factor_aggregations": {
    "portfolio_beta": 0.98,
    "factor_loadings": {
      "market": 0.98,
      "size": -0.185,
      "value": 0.045,
      "momentum": 0.225,
      "quality": 0.385,
      "low_volatility": -0.095,
      "dividend_yield": 0.165
    },
    "r_squared": 0.785
  },
  "performance_metrics": {
    "ytd_return": 0.142,
    "trailing_30d_return": 0.035,
    "trailing_90d_return": 0.089,
    "sharpe_ratio_30d": 1.42,
    "max_drawdown_30d": -0.048
  },
  "last_updated": "2025-09-05T15:30:00Z"
}
```

### 2.11 Get Risk Summary
**Endpoint**: `GET /data/portfolios/{portfolio_id}/risk-summary`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get comprehensive risk metrics for portfolio"  
**Database Access**: Position, PositionGreeks, PositionFactorExposure tables  
**Service Layer**: Direct ORM queries with risk calculations  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `confidence_level` (query, optional): VaR confidence level (default 95)

**Response**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "risk_summary": {
    "portfolio_value": 1662126.38,
    "confidence_level": 95,
    "calculation_date": "2025-09-05",
    "lookback_period": 252
  },
  "value_at_risk": {
    "1_day": {
      "absolute": -42350.85,
      "percentage": -2.55
    },
    "5_day": {
      "absolute": -94720.15,
      "percentage": -5.70
    },
    "10_day": {
      "absolute": -133852.45,
      "percentage": -8.05
    }
  },
  "expected_shortfall": {
    "1_day": {
      "absolute": -56420.75,
      "percentage": -3.39
    },
    "5_day": {
      "absolute": -126185.25,
      "percentage": -7.59
    },
    "10_day": {
      "absolute": -178450.85,
      "percentage": -10.74
    }
  },
  "risk_metrics": {
    "portfolio_beta": 1.15,
    "correlation_with_spy": 0.78,
    "tracking_error": 0.125,
    "information_ratio": 0.35,
    "sortino_ratio": 1.89,
    "maximum_drawdown": -0.185,
    "volatility_30d": 0.164,
    "volatility_90d": 0.189
  },
  "component_var": [
    {
      "symbol": "MSFT",
      "position_weight": 0.512,
      "component_var": -18650.25,
      "marginal_var": -36420.15,
      "percentage_contribution": 44.1
    },
    {
      "symbol": "AAPL",
      "position_weight": 0.105,
      "component_var": -8945.75,
      "marginal_var": -85185.42,
      "percentage_contribution": 21.1
    }
  ],
  "stress_scenarios": {
    "2008_financial_crisis": {
      "scenario_return": -0.385,
      "portfolio_impact": -639748.66
    },
    "covid_march_2020": {
      "scenario_return": -0.285,
      "portfolio_impact": -473806.02
    },
    "interest_rate_shock": {
      "scenario_return": -0.125,
      "portfolio_impact": -207765.80
    }
  },
  "greeks_risk": {
    "delta_equivalent": 385420.00,
    "gamma_risk": {
      "1_percent_move": 1925.50,
      "2_percent_move": 7702.00
    },
    "vega_risk": {
      "1_vol_point_move": 810.00
    },
    "theta_decay": {
      "1_day": -420.00
    }
  },
  "risk_warnings": [
    "High concentration in technology sector (53.5%)",
    "Options positions have 15 days average to expiry",
    "Portfolio beta above 1.0 indicates higher market sensitivity"
  ],
  "last_updated": "2025-09-05T18:00:00Z"
}
```

### 2.12 Get Position Summary
**Endpoint**: `GET /data/portfolios/{portfolio_id}/positions/summary`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get position summary with key metrics"  
**Database Access**: Position, MarketDataCache tables  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `portfolio_id` (path): Portfolio UUID
- `group_by` (query, optional): Group positions by field
- `include_closed` (query, optional): Include closed positions

**Response**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "summary_statistics": {
    "total_positions": 21,
    "active_positions": 21,
    "closed_positions": 0,
    "total_market_value": 1662126.38,
    "total_cost_basis": 1536694.20,
    "total_unrealized_pnl": 125432.18,
    "total_unrealized_pnl_percent": 8.16
  },
  "position_summary": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "symbol": "AAPL",
      "position_type": "LONG",
      "quantity": 100.0,
      "market_value": 17525.00,
      "weight": 0.1054,
      "unrealized_pnl": 1525.00,
      "unrealized_pnl_percent": 9.53,
      "day_change": 285.00,
      "day_change_percent": 1.65
    },
    {
      "id": "b2c3d4e5-f6g7-8901-bcde-f23456789012",
      "symbol": "MSFT",
      "position_type": "LONG",
      "quantity": 200.0,
      "market_value": 85036.00,
      "weight": 0.5117,
      "unrealized_pnl": 8536.00,
      "unrealized_pnl_percent": 11.16,
      "day_change": -484.00,
      "day_change_percent": -0.57
    }
  ],
  "groupings": {
    "by_asset_type": {
      "stocks": {"count": 17, "value": 1463426.38, "percentage": 88.04},
      "options": {"count": 4, "value": 198700.00, "percentage": 11.96}
    },
    "by_sector": {
      "Technology": {"count": 8, "value": 845250.00, "percentage": 50.86},
      "Healthcare": {"count": 4, "value": 285640.00, "percentage": 17.18},
      "Financial": {"count": 3, "value": 195320.00, "percentage": 11.75},
      "Consumer": {"count": 3, "value": 142580.00, "percentage": 8.58},
      "Industrial": {"count": 2, "value": 98156.38, "percentage": 5.90},
      "Energy": {"count": 1, "value": 95180.00, "percentage": 5.73}
    },
    "by_position_type": {
      "LONG": {"count": 15, "value": 1425680.50, "percentage": 85.77},
      "SHORT": {"count": 2, "value": -45250.00, "percentage": -2.72},
      "CALL": {"count": 3, "value": 126450.00, "percentage": 7.61},
      "PUT": {"count": 1, "value": 155245.88, "percentage": 9.34}
    }
  },
  "performance_metrics": {
    "winners": 15,
    "losers": 6,
    "best_performer": {
      "symbol": "NVDA",
      "unrealized_pnl_percent": 28.45
    },
    "worst_performer": {
      "symbol": "TSLA",
      "unrealized_pnl_percent": -12.85
    }
  },
  "last_updated": "2025-09-05T15:30:00Z"
}
```

### 2.13 Get Position Details by ID
**Endpoint**: `GET /data/positions/{position_id}/details`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required  
**OpenAPI Description**: "Get detailed information for specific position"  
**Database Access**: Position, MarketDataCache, PositionGreeks, PositionFactorExposure tables  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `position_id` (path): Position UUID
- `include_history` (query, optional): Include historical data

**Response**:
```json
{
  "position": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "symbol": "AAPL",
    "position_type": "LONG",
    "quantity": 100.0,
    "cost_basis": 160.00,
    "current_price": 175.25,
    "market_value": 17525.00,
    "weight_in_portfolio": 0.1054,
    "created_at": "2025-08-15T10:30:00Z",
    "updated_at": "2025-09-05T15:30:00Z",
    "is_active": true
  },
  "pnl_analysis": {
    "unrealized_pnl": 1525.00,
    "unrealized_pnl_percent": 9.53,
    "day_change": 285.00,
    "day_change_percent": 1.65,
    "total_cost": 16000.00,
    "total_proceeds": 0.00
  },
  "market_data": {
    "current_price": 175.25,
    "bid": 175.20,
    "ask": 175.30,
    "volume": 58432100,
    "day_high": 176.15,
    "day_low": 174.25,
    "year_high": 199.62,
    "year_low": 164.08,
    "last_updated": "2025-09-05T20:00:00Z"
  },
  "fundamentals": {
    "market_cap": 2658745000000,
    "pe_ratio": 28.5,
    "dividend_yield": 0.0045,
    "beta": 1.25,
    "sector": "Technology",
    "industry": "Consumer Electronics"
  },
  "greeks": null,
  "factor_exposures": {
    "market": 1.12,
    "size": -0.25,
    "value": 0.08,
    "momentum": 0.35,
    "quality": 0.42,
    "low_volatility": -0.18,
    "dividend_yield": 0.12,
    "last_updated": "2025-09-05T10:00:00Z"
  },
  "risk_metrics": {
    "position_var_95": -1250.85,
    "position_var_99": -1875.25,
    "component_var": -8945.75,
    "marginal_var": -85185.42,
    "beta_to_portfolio": 0.85,
    "correlation_to_portfolio": 0.62
  },
  "historical_performance": {
    "returns": [
      {"date": "2025-09-05", "return": 0.0165},
      {"date": "2025-09-04", "return": -0.0089},
      {"date": "2025-09-03", "return": 0.0234}
    ],
    "volatility_30d": 0.285,
    "sharpe_ratio_30d": 1.15,
    "max_drawdown_30d": -0.078
  },
  "transactions": [
    {
      "date": "2025-08-15",
      "type": "BUY",
      "quantity": 100.0,
      "price": 160.00,
      "value": 16000.00,
      "fees": 4.95
    }
  ],
  "alerts": [
    "Position weight above 10% of portfolio",
    "Strong positive momentum factor exposure"
  ],
  "last_updated": "2025-09-05T15:30:00Z"
}
```

---

## 3. Administration Endpoints

### 3.1 Get Batch Job Status
**Endpoint**: `GET /admin/batch/jobs/status`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Get status of recent batch jobs"  
**Database Access**: BatchJob table  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `job_name` (query, optional): Filter by job name
- `status` (query, optional): Filter by status
- `portfolio_id` (query, optional): Filter by portfolio
- `days_back` (query, optional): Number of days to look back (default 1)

**Response**:
```json
{
  "jobs": [
    {
      "id": "job_20250905_183045_market_data_update",
      "job_name": "market_data_update",
      "status": "completed",
      "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
      "started_at": "2025-09-05T18:30:45Z",
      "completed_at": "2025-09-05T18:32:15Z",
      "duration_seconds": 90,
      "processed_items": 21,
      "successful_items": 21,
      "failed_items": 0,
      "error_message": null,
      "metadata": {
        "source": "batch_orchestrator_v2",
        "calculation_engines": ["market_data", "greeks", "factor_exposure"]
      }
    },
    {
      "id": "job_20250905_120030_full_calculation",
      "job_name": "full_portfolio_calculation",
      "status": "running",
      "portfolio_id": "d1621bc9-d6c6-444d-becd-4f85f1ecdb5f",
      "started_at": "2025-09-05T12:00:30Z",
      "completed_at": null,
      "duration_seconds": null,
      "processed_items": 45,
      "successful_items": 38,
      "failed_items": 2,
      "error_message": null,
      "metadata": {
        "source": "api_trigger",
        "calculation_engines": ["all"]
      }
    },
    {
      "id": "job_20250905_060015_data_quality_check",
      "job_name": "data_quality_assessment",
      "status": "failed",
      "portfolio_id": null,
      "started_at": "2025-09-05T06:00:15Z",
      "completed_at": "2025-09-05T06:02:45Z",
      "duration_seconds": 150,
      "processed_items": 0,
      "successful_items": 0,
      "failed_items": 0,
      "error_message": "API rate limit exceeded for market data provider",
      "metadata": {
        "source": "scheduled_job",
        "retry_count": 3
      }
    }
  ],
  "summary": {
    "total_jobs": 3,
    "completed": 1,
    "running": 1,
    "failed": 1,
    "pending": 0
  },
  "filters_applied": {
    "days_back": 1,
    "job_name": null,
    "status": null,
    "portfolio_id": null
  },
  "last_updated": "2025-09-05T18:45:00Z"
}
```

### 3.2 Get Batch Job Summary
**Endpoint**: `GET /admin/batch/jobs/summary`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Get summary statistics of batch jobs"  
**Database Access**: BatchJob table  
**Service Layer**: Direct ORM queries with statistical calculations  

**Parameters**:
- `days_back` (query, optional): Number of days for summary (default 7)

**Response**:
```json
{
  "period": {
    "start_date": "2025-08-29",
    "end_date": "2025-09-05",
    "days_covered": 7
  },
  "job_statistics": {
    "total_jobs": 42,
    "completed_jobs": 35,
    "running_jobs": 2,
    "failed_jobs": 4,
    "pending_jobs": 1,
    "success_rate": 83.33,
    "avg_duration_seconds": 125.5
  },
  "by_job_type": {
    "market_data_update": {
      "total": 14,
      "completed": 13,
      "failed": 1,
      "success_rate": 92.86,
      "avg_duration": 85.2
    },
    "full_portfolio_calculation": {
      "total": 12,
      "completed": 10,
      "failed": 1,
      "success_rate": 83.33,
      "avg_duration": 245.8
    },
    "greeks_calculation": {
      "total": 8,
      "completed": 7,
      "failed": 1,
      "success_rate": 87.5,
      "avg_duration": 65.4
    },
    "factor_analysis": {
      "total": 6,
      "completed": 5,
      "failed": 1,
      "success_rate": 83.33,
      "avg_duration": 125.3
    },
    "data_quality_assessment": {
      "total": 2,
      "completed": 0,
      "failed": 0,
      "success_rate": 0.0,
      "avg_duration": null
    }
  },
  "performance_trends": {
    "daily_job_counts": [
      {"date": "2025-09-05", "total": 8, "completed": 6, "failed": 1},
      {"date": "2025-09-04", "total": 6, "completed": 5, "failed": 1},
      {"date": "2025-09-03", "total": 7, "completed": 7, "failed": 0},
      {"date": "2025-09-02", "total": 5, "completed": 4, "failed": 1},
      {"date": "2025-09-01", "total": 6, "completed": 5, "failed": 0},
      {"date": "2025-08-31", "total": 5, "completed": 4, "failed": 1},
      {"date": "2025-08-30", "total": 5, "completed": 4, "failed": 0}
    ],
    "avg_duration_trend": {
      "current_week": 125.5,
      "previous_week": 135.2,
      "improvement_percent": 7.2
    }
  },
  "error_analysis": {
    "top_error_types": [
      {
        "error_pattern": "API rate limit exceeded",
        "count": 2,
        "percentage": 50.0
      },
      {
        "error_pattern": "Database connection timeout",
        "count": 1,
        "percentage": 25.0
      },
      {
        "error_pattern": "Invalid portfolio data",
        "count": 1,
        "percentage": 25.0
      }
    ],
    "most_failed_job_type": "market_data_update"
  },
  "recommendations": [
    "Consider implementing exponential backoff for API rate limits",
    "Monitor database connection pool during peak hours",
    "Add data validation checks before portfolio calculations"
  ],
  "last_updated": "2025-09-05T18:45:00Z"
}
```

### 3.3 Cancel Batch Job
**Endpoint**: `DELETE /admin/batch/jobs/{job_id}/cancel`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Cancel a running batch job"  
**Database Access**: BatchJob table (UPDATE operation)  
**Service Layer**: Direct ORM queries  

**Parameters**:
- `job_id` (path): Batch job ID to cancel

**Response**:
```json
{
  "message": "Batch job cancelled successfully",
  "job_details": {
    "id": "job_20250905_120030_full_calculation",
    "job_name": "full_portfolio_calculation",
    "previous_status": "running",
    "new_status": "cancelled",
    "cancelled_at": "2025-09-05T18:47:30Z",
    "runtime_before_cancellation": 385,
    "processed_items": 45,
    "successful_items": 38,
    "items_in_progress": 5
  },
  "cleanup_actions": [
    "Released database connections",
    "Cleared temporary calculation cache",
    "Updated job status in database"
  ],
  "impact_assessment": {
    "affected_portfolios": 1,
    "incomplete_calculations": 5,
    "data_consistency_status": "maintained",
    "rollback_required": false
  }
}
```

### 3.4 Get Data Quality Status
**Endpoint**: `GET /admin/batch/data-quality`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Get data quality status and metrics for portfolios"  
**Database Access**: Portfolio, Position, MarketDataCache tables  
**Service Layer**: Uses pre_flight_validation function  

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio ID or all portfolios

**Response**:
```json
{
  "system_overview": {
    "total_portfolios": 8,
    "active_portfolios": 8,
    "total_positions": 74,
    "overall_data_quality_score": 88.5,
    "last_assessment": "2025-09-05T18:45:00Z"
  },
  "portfolio_quality": [
    {
      "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
      "portfolio_name": "Demo High Net Worth Investor Portfolio",
      "quality_score": 95.5,
      "position_count": 21,
      "data_completeness": {
        "price_coverage": 100.0,
        "greeks_coverage": 87.5,
        "factor_coverage": 90.5,
        "historical_data_coverage": 98.2
      },
      "data_freshness": {
        "last_price_update": "2025-09-05T20:00:00Z",
        "hours_since_update": 2.75,
        "freshness_score": 93.0
      },
      "issues": [
        "Missing Greeks for 1 options position",
        "Historical data gap for 2 positions"
      ]
    },
    {
      "portfolio_id": "d1621bc9-d6c6-444d-becd-4f85f1ecdb5f",
      "portfolio_name": "Demo Retail Investor Portfolio",
      "quality_score": 82.3,
      "position_count": 15,
      "data_completeness": {
        "price_coverage": 93.3,
        "greeks_coverage": 75.0,
        "factor_coverage": 86.7,
        "historical_data_coverage": 89.5
      },
      "data_freshness": {
        "last_price_update": "2025-09-05T19:30:00Z",
        "hours_since_update": 3.25,
        "freshness_score": 85.0
      },
      "issues": [
        "Missing prices for 1 position",
        "Stale Greeks data for 2 positions",
        "Factor exposures need recalculation"
      ]
    }
  ],
  "data_source_status": {
    "market_data_providers": {
      "fmp": {
        "status": "operational",
        "last_successful_call": "2025-09-05T20:00:00Z",
        "daily_api_calls": 1245,
        "daily_limit": 10000,
        "error_rate_24h": 0.02
      },
      "polygon": {
        "status": "operational",
        "last_successful_call": "2025-09-05T19:45:00Z",
        "daily_api_calls": 358,
        "daily_limit": 5000,
        "error_rate_24h": 0.01
      }
    },
    "database_health": {
      "status": "healthy",
      "connection_pool_usage": 45,
      "avg_query_time_ms": 12.5,
      "slow_queries_24h": 3
    }
  },
  "quality_trends": {
    "score_history_7d": [
      {"date": "2025-09-05", "score": 88.5},
      {"date": "2025-09-04", "score": 87.2},
      {"date": "2025-09-03", "score": 89.1},
      {"date": "2025-09-02", "score": 85.8},
      {"date": "2025-09-01", "score": 84.5},
      {"date": "2025-08-31", "score": 86.9},
      {"date": "2025-08-30", "score": 88.0}
    ],
    "improvement_areas": [
      "Options Greeks calculation frequency",
      "Factor exposure refresh timing",
      "Historical data backfill for new positions"
    ]
  },
  "recommendations": [
    "Increase Greeks calculation frequency to twice daily",
    "Implement real-time factor exposure updates",
    "Set up automated data quality alerts for scores below 80%",
    "Consider adding backup data provider for critical market data"
  ],
  "last_updated": "2025-09-05T18:45:00Z"
}
```

### 3.5 Refresh Market Data for Quality
**Endpoint**: `POST /admin/batch/data-quality/refresh`  
**Status**: ✅ Fully Implemented  
**Authentication**: Required (Admin)  
**OpenAPI Description**: "Refresh market data to improve data quality scores"  
**Database Access**: Uses pre_flight_validation and batch orchestrator  
**Service Layer**: Background task execution via batch_orchestrator._update_market_data  

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio ID or all portfolios

**Response**:
```json
{
  "refresh_initiated": true,
  "job_details": {
    "job_id": "job_20250905_184800_data_quality_refresh",
    "job_name": "data_quality_refresh",
    "status": "running",
    "initiated_at": "2025-09-05T18:48:00Z",
    "estimated_duration_minutes": 15
  },
  "scope": {
    "portfolios_targeted": 8,
    "positions_to_refresh": 74,
    "data_types": [
      "market_prices",
      "options_greeks",
      "factor_exposures",
      "historical_data"
    ]
  },
  "pre_refresh_quality": {
    "overall_score": 88.5,
    "portfolios_below_threshold": 2,
    "critical_issues": [
      "Missing prices for 1 position",
      "Stale Greeks for 3 options",
      "Factor exposures outdated by 2 days"
    ]
  },
  "expected_improvements": {
    "estimated_score_increase": 6.5,
    "target_quality_score": 95.0,
    "issues_to_resolve": 5,
    "data_freshness_improvement": "Will bring all data to within 1 hour"
  },
  "monitoring": {
    "progress_endpoint": "/admin/batch/jobs/job_20250905_184800_data_quality_refresh/status",
    "completion_webhook": null,
    "notification_channels": ["system_log", "admin_dashboard"]
  },
  "backup_plan": {
    "fallback_providers": ["polygon", "manual_entry"],
    "rollback_available": true,
    "previous_data_retained": true
  },
  "message": "Data quality refresh initiated successfully. Monitor progress via job status endpoint."
}
```

---

## Error Handling

All endpoints follow consistent error response format:

### Authentication Error (401)
```json
{
  "detail": "Could not validate credentials"
}
```

### Not Found Error (404)
```json
{
  "detail": "Portfolio not found"
}
```

### Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["query", "symbols"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Server Error (500)
```json
{
  "detail": "Internal server error"
}
```

---

## Data Quality Guarantee

All endpoints in this specification:

✅ Return **REAL DATA** from the database  
✅ Have been tested and verified  
✅ Include comprehensive error handling  
✅ Support production workloads  
✅ Follow consistent response schemas  

### Historical Data Coverage
- **Stock prices**: 297 days (2024-06-24 to 2025-09-04)
- **Factor ETFs**: 7 ETFs with real market prices
- **Portfolio data**: 8 portfolios, 74+ active positions
- **Market quotes**: Real-time data with volume and timestamps

---

## Getting Started

### 1. Authentication
```bash
# Get JWT token
TOKEN=$(curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_hnw@sigmasight.com", "password": "demo12345"}' | \
  jq -r '.access_token')
```

### 2. Get Portfolio Data
```bash
# List portfolios
curl -X GET "http://localhost:8000/api/v1/data/portfolios" \
  -H "Authorization: Bearer $TOKEN"

# Get complete portfolio
curl -X GET "http://localhost:8000/api/v1/data/portfolio/c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e/complete" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. Get Market Data
```bash
# Historical prices
curl -X GET "http://localhost:8000/api/v1/data/prices/historical/AAPL?days=30" \
  -H "Authorization: Bearer $TOKEN"

# Real-time quotes
curl -X GET "http://localhost:8000/api/v1/data/prices/quotes?symbols=AAPL,MSFT" \
  -H "Authorization: Bearer $TOKEN"
```

---

# PART II: PLANNED ENDPOINTS 🎯

This section provides development specifications for future API endpoints. These are **NOT YET IMPLEMENTED** but serve as design guidance for development teams.

> ⚠️ **Development Planning Section**
> 
> **Status**: Not implemented - design specifications only  
> **Purpose**: Guide development of analytics, management, export, and system namespaces  
> **Source**: API_SPECIFICATIONS_V1.4.4.md planned endpoints  

## Namespace Organization

### 🎯 **Planned Namespace Structure**
- **`/analytics/`**: All calculated metrics and derived values
- **`/management/`**: Portfolio and position CRUD operations  
- **`/export/`**: Data export and report generation
- **`/system/`**: System utilities and job management

### 🔄 **Migration Strategy**
- **Current Focus**: `/data/` namespace (✅ Complete - 9 endpoints)
- **Phase 1 Priority**: `/analytics/` endpoints for calculated metrics
- **Phase 2 Priority**: `/management/` endpoints for CRUD operations  
- **Phase 3 Priority**: `/export/` and `/system/` utilities

---

## Analytics Endpoints (/analytics/) 🧮

**Status**: 📋 Planned - Not Yet Implemented  
**Priority**: High - Core calculations and derived metrics

### Portfolio Analytics

#### A1. Portfolio Overview **✅ APPROVED FOR IMPLEMENTATION**
```http
GET /api/v1/analytics/portfolio/{id}/overview
```

**Purpose**: Portfolio aggregate metrics for dashboard cards (exposures, P&L, totals)  
**Implementation Notes**: 
- Uses existing aggregation engine results from batch processing
- Returns calculated exposures (long/short/gross/net)
- Includes P&L metrics and portfolio totals
- Leverages existing calculation data with graceful degradation
- **Frontend Integration**: Required for portfolio page aggregate cards at `http://localhost:3005/portfolio`

**Response Format**:
```json
{
  "portfolio_id": "uuid",
  "total_value": 1250000.00,
  "cash_balance": 62500.00,
  "exposures": {
    "long_exposure": 1187500.00,
    "short_exposure": 0.00,
    "gross_exposure": 1187500.00,
    "net_exposure": 1187500.00,
    "long_percentage": 95.0,
    "short_percentage": 0.0,
    "gross_percentage": 95.0,
    "net_percentage": 95.0
  },
  "pnl": {
    "total_pnl": "Data Not Available",
    "unrealized_pnl": "Data Not Available",
    "realized_pnl": "Data Not Available"
  },
  "position_count": {
    "total_positions": 21,
    "long_count": 21,
    "short_count": 0,
    "option_count": 0
  },
  "last_updated": "2025-01-15T10:30:00Z"
}
```

### Risk Analytics

#### A2. Portfolio Risk Metrics
```http
GET /api/v1/analytics/risk/{portfolio_id}/metrics
```

**Purpose**: Calculated risk metrics (VaR, expected shortfall, beta, correlation)  
**Implementation Notes**: 
- Requires completed factor analysis and historical data
- Should leverage existing batch calculation results
- Return cached values with calculation timestamps

**Planned Response**:
```json
{
  "portfolio_id": "uuid",
  "risk_metrics": {
    "value_at_risk": {
      "1_day": {"confidence_95": -12500.0, "confidence_99": -18750.0},
      "5_day": {"confidence_95": -28000.0, "confidence_99": -42000.0}
    },
    "expected_shortfall": {
      "1_day": {"confidence_95": -15600.0, "confidence_99": -23400.0}
    },
    "portfolio_beta": 1.15,
    "sharpe_ratio": 1.42,
    "sortino_ratio": 1.89,
    "max_drawdown": -0.185,
    "correlation_with_spy": 0.78
  },
  "calculation_metadata": {
    "calculated_at": "2025-09-05T10:00:00Z",
    "lookback_days": 252,
    "confidence_levels": [0.95, 0.99]
  }
}
```

#### A2. Factor Exposures
```http
GET /api/v1/analytics/factor/{portfolio_id}/exposures
```

**Purpose**: Portfolio exposures to 7-factor model  
**Implementation Notes**:
- Use existing `PositionFactorExposure` database table
- Aggregate position-level exposures to portfolio level
- Include factor attribution analysis

#### A3. Scenario Analysis  
```http
GET /api/v1/analytics/risk/{portfolio_id}/scenarios
```

**Purpose**: Stress testing results across 15 market scenarios  
**Implementation Notes**:
- Leverage existing batch stress testing calculations
- Include both systematic and idiosyncratic risk impacts

---

## Management Endpoints (/management/) 📋

**Status**: 📋 Planned - Not Yet Implemented  
**Priority**: Medium - CRUD operations for portfolios and positions

### Portfolio Management

#### M1. Create Portfolio
```http
POST /api/v1/management/portfolios
```

#### M2. Update Portfolio
```http
PUT /api/v1/management/portfolios/{portfolio_id}
```

#### M3. Delete Portfolio (Soft Delete)
```http
DELETE /api/v1/management/portfolios/{portfolio_id}
```

### Position Management

#### M4. Add Position
```http
POST /api/v1/management/portfolios/{portfolio_id}/positions
```

#### M5. Update Position
```http
PUT /api/v1/management/positions/{position_id}
```

#### M6. Close Position
```http
POST /api/v1/management/positions/{position_id}/close
```

**Implementation Priority**: 
1. Portfolio CRUD (M1-M3)
2. Position management (M4-M6)
3. Batch operations and validation

---

## Export Endpoints (/export/) 📊

**Status**: 📋 Planned - Not Yet Implemented  
**Priority**: Medium - Report generation and data export

### Report Generation

#### E1. Generate Portfolio Report
```http
POST /api/v1/export/reports/portfolio/{portfolio_id}
```

**Purpose**: Generate comprehensive portfolio reports in multiple formats  
**Implementation Notes**:
- Leverage existing report generation infrastructure
- Support MD, JSON, CSV, PDF formats
- Async job processing with status tracking

#### E2. Export Historical Data
```http
GET /api/v1/export/data/historical
```

**Purpose**: Bulk historical data export for analysis  
**Query Parameters**: `portfolio_id`, `start_date`, `end_date`, `format`, `include_calculated`

---

## System Endpoints (/system/) ⚙️

**Status**: 📋 Planned - Not Yet Implemented  
**Priority**: Low - System utilities and monitoring

### Job Management

#### S1. List Background Jobs
```http
GET /api/v1/system/jobs
```

#### S2. Job Details
```http
GET /api/v1/system/jobs/{job_id}
```

### System Health

#### S3. System Status
```http
GET /api/v1/system/status
```

**Purpose**: Comprehensive system health including database, external APIs, batch processing  

---

## Implementation Roadmap 🗺️

### Phase 1: Core Analytics (Priority: High)
**Target**: Q4 2025
- [ ] Risk metrics endpoint (A1)
- [ ] Factor exposures endpoint (A2) 
- [ ] Scenario analysis endpoint (A3)
- [ ] Greeks calculations integration

### Phase 2: Management Operations (Priority: Medium)  
**Target**: Q1 2026
- [ ] Portfolio CRUD operations (M1-M3)
- [ ] Position management (M4-M6)
- [ ] Data validation and business rules

### Phase 3: Export & System (Priority: Low)
**Target**: Q2 2026  
- [ ] Report generation (E1-E2)
- [ ] System monitoring (S1-S3)
- [ ] Advanced export formats

### Implementation Notes

#### Dependencies
- **Analytics**: Requires completed batch processing infrastructure
- **Management**: Needs proper authorization and validation frameworks
- **Export**: Depends on analytics endpoints for calculated data
- **System**: Can be implemented independently

#### Data Quality Requirements
- All analytical endpoints must handle graceful degradation for missing data
- Calculated metrics should include confidence intervals and calculation metadata
- Real-time vs. cached data strategy needs definition

#### Authentication & Authorization
- Extend existing JWT authentication to all new endpoints
- Implement role-based access for management operations
- Add audit logging for CRUD operations

---

## Version History

**V1.4.5** (September 5, 2025)
- **NEW**: Added Part II - Planned Endpoints development specifications
- **NEW**: Dual-purpose document structure (Production + Planning)
- **BREAKING CHANGE**: Restructured from V1.4.4 to focus on implemented vs planned
- **MAJOR UPDATE**: All 18 documented endpoints in Part I verified with real data (previously claimed only 9)
- **NEW**: Added comprehensive response examples for all 18 endpoints (16 were missing examples)
- Updated based on source code verification rather than API_IMPLEMENTATION_STATUS.md
- Added OpenAPI descriptions, full parameters, and service layer documentation for each endpoint
- Response examples include realistic data based on SigmaSight's portfolio risk analytics domain

**Previous Versions**
- V1.4.4: Included mixed implemented/unimplemented endpoints
- Earlier: Mixed real and mock endpoint documentation

---

## Support

### Part I (Production Endpoints)
For questions about production-ready endpoints:
1. Verify endpoint status in `API_IMPLEMENTATION_STATUS.md`
2. Test endpoints using the examples above  
3. Check server logs for detailed error information

**Server Health Check**: `GET /health` (no authentication required)

### Part II (Planned Endpoints)
For development planning questions:
1. Review implementation roadmap and priorities
2. Check dependencies and requirements before starting development
3. Update this document as endpoints are implemented

---

**Document Status**: ✅ Part I Production Ready | 🎯 Part II Development Planning  
**Last Verified**: September 5, 2025  
**Production endpoints confirmed working with real database data**