# SigmaSight API Endpoints Specification v1.4.4

> 🚫 SUPERSEDED DOCUMENT (2025-09-06)
>
> This specification is superseded by the newer version: [API_SPECIFICATIONS_V1.4.5.md](./API_SPECIFICATIONS_V1.4.5.md).
>
> Status: Reference only. Content is out of date and may not reflect current endpoints, contracts, or implementation details.
>
> AI coding agents: Do not treat this file as the project source of truth or as a list of current requirements. Always use the latest spec above and corroborate with `backend/TODO3.md` and the code.

> ⚠️ **IMPLEMENTATION STATUS (2025-08-26 15:30 PST)**: Raw Data APIs (`/data/` namespace) are 100% complete (6/6 endpoints). See [TODO3.md](../../TODO3.md) for full API implementation progress (30% overall, 12/39 endpoints complete).

## Document Version Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.4.0 | 2024-06-27 | Initial | Initial V1.4 API specification |
| 1.4.1 | 2025-08-04 | Cascade | Updated for V1.4 implementation decisions: 150-day regression, position-level factor storage, mibian-only Greeks, 7-factor model, rate limiting completion |
| 1.4.2 | 2025-08-26 | Elliott/Claude | Added Section 2: Raw Data Mode APIs for LLMs (5 new endpoints). Renumbered all subsequent sections (2→3, 3→4, etc.) to accommodate new Raw Data Mode priority |
| 1.4.3 | 2025-08-26 | Elliott/Claude | Major namespace reorganization for clarity: /data/ for raw data, /analytics/ for calculations, /management/ for CRUD, /export/ for outputs, /system/ for utilities. Removed /simulation/, /market/, and /ai/ endpoints. |
| 1.4.4 | 2025-08-26 | Elliott/Claude | Added scenario analysis endpoint (/analytics/risk/{id}/scenarios) and market quotes endpoint (/data/prices/quotes) to support frontend requirements. |

## 1. Overview

This document specifies the REST API endpoints for SigmaSight V1.4.4, with a refined namespace organization that clearly distinguishes between raw data access and calculated analytics.

### 1.1 Strategic Direction (V1.4.4)

#### Namespace Philosophy
- **`/data/`**: Raw, unprocessed data for LLM consumption
- **`/analytics/`**: All calculated metrics and derived values
- **`/management/`**: Portfolio and position CRUD operations
- **`/export/`**: Data export and report generation
- **`/system/`**: System utilities and job management

#### Key Design Principles
1. **Clear Separation**: Raw data vs. calculated metrics have distinct namespaces
2. **Self-Documenting**: Endpoint paths immediately convey data type and purpose
3. **LLM-Optimized**: `/data/` endpoints return complete, denormalized datasets
4. **Consistent Depth**: All major features at the second namespace level

### 1.2 Authentication & Headers

#### Required Headers
```http
Authorization: Bearer {token}
Content-Type: application/json
```

### 1.3 Standard Response Format
```json
{
  "success": true,
  "data": {},
  "meta": {
    "timestamp": "2024-06-27T14:32:15Z",
    "request_id": "req_abc123",
    "execution_time_ms": 123
  },
  "errors": []
}
```

## 2. Raw Data APIs (/data/)

Raw Data Mode provides unprocessed, complete datasets that enable LLMs to perform their own calculations and analytics. These endpoints return fundamental data without any calculated metrics.

### 2.1 Portfolio Raw Data

#### 2.1.1 Get Complete Portfolio Data
```http
GET /api/v1/data/portfolio/{portfolio_id}/complete
```

Returns comprehensive portfolio overview including all positions, current market values, and portfolio metadata in a single response. No calculated metrics like Greeks or factor exposures.

**Query Parameters**:
- `include_positions` (boolean, default: true) - Include position list
- `include_cash` (boolean, default: true) - Include cash balance
- `as_of_date` (string, optional) - ISO date for historical snapshot

**Response (200 OK)**:
```json
{
  "portfolio": {
    "id": "51134ffd-2f13-49bd-b1f5-0c327e801b69",
    "name": "Demo Individual Portfolio",
    "total_value": 485000.00,
    "cash_balance": 25000.00,
    "position_count": 16,
    "timestamp": "2024-06-27T15:30:00Z"
  },
  "positions_summary": {
    "long_count": 14,
    "short_count": 2,
    "option_count": 0,
    "total_market_value": 460000.00
  },
  "positions": [
    {
      "id": "e5e29f33-ac9f-411b-9494-bff119f435b2",
      "symbol": "FCNTX",
      "quantity": 1000,
      "position_type": "LONG",
      "market_value": 72795.00,
      "last_price": 72.795,
      "has_complete_history": true
    }
  ],
  "data_quality": {
    "complete_data_positions": 14,
    "partial_data_positions": 2,
    "data_as_of": "2024-06-27T15:30:00Z"
  }
}
```

#### 2.1.2 Get Portfolio Data Quality
```http
GET /api/v1/data/portfolio/{portfolio_id}/data-quality
```

Provides comprehensive data availability assessment, indicating which calculations are feasible given available data.

**Query Parameters**:
- `check_factors` (boolean, default: true) - Check factor data completeness
- `check_correlations` (boolean, default: true) - Check correlation feasibility

**Response (200 OK)**:
```json
{
  "portfolio_id": "51134ffd-2f13-49bd-b1f5-0c327e801b69",
  "assessment_date": "2024-06-27",
  "position_data_quality": {
    "complete_history": ["AAPL", "MSFT", "FCNTX", "FMAGX"],
    "partial_history": [
      {
        "symbol": "NVDA",
        "days_available": 45,
        "days_missing": 105
      }
    ],
    "insufficient_data": [
      {
        "symbol": "IPO",
        "days_available": 10,
        "reason": "recent_listing"
      }
    ]
  },
  "calculation_feasibility": {
    "correlation_matrix": {
      "feasible": true,
      "positions_eligible": 14,
      "positions_excluded": 2,
      "min_days_overlap": 30
    },
    "factor_regression": {
      "feasible": true,
      "positions_eligible": 13,
      "positions_excluded": 3,
      "min_days_required": 60
    }
  },
  "last_update": "2024-06-27T15:30:00Z"
}
```

### 2.2 Position Raw Data

#### 2.2.1 Get Position Details
```http
GET /api/v1/data/positions/details
```

Returns detailed position-level information for all holdings in specified portfolio(s).

**Query Parameters**:
- `portfolio_id` (uuid, required unless position_ids provided)
- `position_ids` (string, optional) - Comma-separated position IDs
- `include_closed` (boolean, default: false) - Include closed positions

**Response (200 OK)**:
```json
{
  "positions": [
    {
      "id": "e5e29f33-ac9f-411b-9494-bff119f435b2",
      "portfolio_id": "51134ffd-2f13-49bd-b1f5-0c327e801b69",
      "symbol": "FCNTX",
      "position_type": "LONG",
      "quantity": 1000,
      "entry_date": "2024-01-15",
      "entry_price": 70.50,
      "cost_basis": 70500.00,
      "current_price": 72.795,
      "market_value": 72795.00,
      "unrealized_pnl": 2295.00,
      "unrealized_pnl_percent": 3.26
    }
  ],
  "summary": {
    "total_positions": 16,
    "total_cost_basis": 470000.00,
    "total_market_value": 485000.00,
    "total_unrealized_pnl": 15000.00
  }
}
```

### 2.3 Price Data

#### 2.3.1 Get Historical Prices
```http
GET /api/v1/data/prices/historical/{portfolio_id}
```

Provides complete historical price data for all portfolio positions.

**Query Parameters**:
- `lookback_days` (integer, default: 150) - Number of trading days
- `include_factor_etfs` (boolean, default: true) - Include factor ETF prices
- `date_format` (string, default: "iso") - Date format (iso|unix)

**Response (200 OK)**:
```json
{
  "metadata": {
    "lookback_days": 150,
    "start_date": "2024-01-01",
    "end_date": "2024-06-27",
    "trading_days_included": 105
  },
  "symbols": {
    "AAPL": {
      "dates": ["2024-01-01", "2024-01-02"],
      "open": [187.15, 187.37],
      "high": [188.44, 188.95],
      "low": [186.76, 187.04],
      "close": [187.68, 188.42],
      "volume": [48087688, 50546742],
      "adjusted_close": [187.68, 188.42]
    }
  }
}
```

### 2.4 Market Quotes

#### 2.4.1 Get Current Market Quotes
```http
GET /api/v1/data/prices/quotes
```

Returns current market prices for specified symbols. Used for real-time position value updates.

**Query Parameters**:
- `symbols` (string, required) - Comma-separated list of ticker symbols
- `include_options` (boolean, default: false) - Include options chains for symbols

**Response (200 OK)**:
```json
{
  "data": {
    "quotes": [
      {
        "symbol": "AAPL",
        "last_price": 189.25,
        "bid": 189.24,
        "ask": 189.26,
        "bid_size": 100,
        "ask_size": 200,
        "volume": 48087688,
        "day_change": 1.57,
        "day_change_percent": 0.84,
        "day_high": 189.95,
        "day_low": 187.04,
        "timestamp": "2024-06-27T15:30:00Z"
      },
      {
        "symbol": "MSFT",
        "last_price": 425.30,
        "bid": 425.28,
        "ask": 425.32,
        "bid_size": 50,
        "ask_size": 75,
        "volume": 22543210,
        "day_change": -2.15,
        "day_change_percent": -0.50,
        "day_high": 428.00,
        "day_low": 424.50,
        "timestamp": "2024-06-27T15:30:00Z"
      }
    ],
    "last_update": "2024-06-27T15:30:00Z"
  }
}
```

### 2.5 Factor Data

#### 2.5.1 Get Factor ETF Prices
```http
GET /api/v1/data/factors/etf-prices
```

Provides historical prices for all factor ETFs used in the 7-factor risk model.

**Query Parameters**:
- `lookback_days` (integer, default: 150) - Number of trading days
- `factors` (string, optional) - Comma-separated factor names to filter

**Response (200 OK)**:
```json
{
  "factor_model": {
    "version": "7-factor",
    "regression_window": 150,
    "minimum_data_points": 60
  },
  "factors": {
    "Market Beta": {
      "etf_symbol": "SPY",
      "dates": ["2024-01-01", "2024-01-02"],
      "prices": [470.00, 471.23],
      "returns": [null, 0.00262]
    },
    "Value": {
      "etf_symbol": "VTV",
      "dates": ["2024-01-01", "2024-01-02"],
      "prices": [155.00, 155.45],
      "returns": [null, 0.00290]
    }
  }
}
```

## 3. Analytics APIs (/analytics/)

All calculated metrics and derived values. These endpoints perform calculations on raw data and return processed results.

### 3.1 Portfolio Analytics

#### 3.1.1 Get Portfolio Overview
```http
GET /api/v1/analytics/portfolio/{portfolio_id}/overview
```

Returns calculated portfolio metrics including exposures, P&L, and risk metrics.

**Response (200 OK)**:
```json
{
  "data": {
    "total_value": 1200000,
    "total_pl": 87360,
    "total_pl_percent": 7.28,
    "exposures": {
      "long": {
        "value": 1100000,
        "percentage": 92
      },
      "short": {
        "value": -567000,
        "percentage": 47
      },
      "gross": {
        "value": 1667000,
        "percentage": 139
      },
      "net": {
        "value": 533000,
        "percentage": 44
      }
    }
  }
}
```

#### 3.1.2 Get Portfolio Performance
```http
GET /api/v1/analytics/portfolio/{portfolio_id}/performance
```

Returns portfolio performance metrics over various time periods.

**Query Parameters**:
- `period` (string) - daily|weekly|monthly|annual

**Response (200 OK)**:
```json
{
  "data": {
    "period": "monthly",
    "returns": {
      "1d": 0.015,
      "1w": 0.032,
      "1m": 0.078,
      "3m": 0.145,
      "ytd": 0.234,
      "1y": 0.289
    },
    "sharpe_ratio": 1.45,
    "sortino_ratio": 2.01,
    "max_drawdown": -0.123
  }
}
```

### 3.2 Position Analytics

#### 3.2.1 Get Position Attribution
```http
GET /api/v1/analytics/positions/attribution
```

Returns P&L attribution analysis for positions.

**Query Parameters**:
- `portfolio_id` (uuid, required)
- `date` (string, default: today)
- `group_by` (string) - position|tag|type

**Response (200 OK)**:
```json
{
  "data": {
    "date": "2024-06-27",
    "total_pl": 15420,
    "positions": [
      {
        "id": "pos_123",
        "ticker": "AAPL",
        "pnl": 5000,
        "pnl_percent": 5.9,
        "contribution_percent": 32.4
      }
    ]
  }
}
```

### 3.3 Risk Analytics

#### 3.3.1 Get Risk Overview
```http
GET /api/v1/analytics/risk/{portfolio_id}/overview
```

Returns comprehensive risk metrics for the portfolio.

**Query Parameters**:
- `view` (string) - portfolio|longs|shorts
- `period` (string) - daily|weekly|monthly|annual

**Response (200 OK)**:
```json
{
  "data": {
    "metrics": {
      "beta": {
        "value": 0.85,
        "description": "vs. SPY"
      },
      "annualized_volatility": {
        "value": 0.185,
        "description": "Std. dev of returns"
      },
      "var_1d": {
        "value": -9700,
        "confidence": 0.95
      }
    }
  }
}
```

#### 3.3.2 Get Portfolio Greeks
```http
GET /api/v1/analytics/risk/{portfolio_id}/greeks
```

Returns calculated Greeks for the portfolio.

**Query Parameters**:
- `include_after_expiry` (boolean, default: false)
- `view` (string) - portfolio|longs|shorts

**Response (200 OK)**:
```json
{
  "data": {
    "current": {
      "delta": 3250,
      "gamma": -450,
      "theta": -185,
      "vega": 820
    },
    "after_expiry": {
      "delta": 2800,
      "gamma": -35
    }
  }
}
```

#### 3.3.3 Calculate Greeks
```http
POST /api/v1/analytics/risk/greeks/calculate
```

Performs real-time Greeks calculation for specified positions.

**Request Body**:
```json
{
  "positions": [
    {
      "ticker": "AAPL",
      "type": "LC",
      "quantity": 20,
      "strike": 200,
      "expiration": "2025-12-19"
    }
  ]
}
```

#### 3.3.4 Run Scenario Analysis
```http
GET /api/v1/analytics/risk/{portfolio_id}/scenarios
```

Runs predefined stress test scenarios and returns portfolio impact.

**Query Parameters**:
- `scenarios` (string, optional) - Comma-separated scenario IDs. If omitted, runs all standard scenarios
- `view` (string) - portfolio|longs|shorts

**Response (200 OK)**:
```json
{
  "data": {
    "scenarios": [
      {
        "id": "market_up_10",
        "name": "Market Up 10%",
        "description": "S&P 500 rises 10%",
        "impact": {
          "dollar_impact": 48500,
          "percentage_impact": 10.0,
          "new_portfolio_value": 533500
        },
        "severity": "positive"
      },
      {
        "id": "market_down_10",
        "name": "Market Down 10%",
        "description": "S&P 500 falls 10%",
        "impact": {
          "dollar_impact": -48500,
          "percentage_impact": -10.0,
          "new_portfolio_value": 436500
        },
        "severity": "moderate"
      },
      {
        "id": "rates_up_25bp",
        "name": "Rates Up 0.25%",
        "description": "Federal Reserve raises rates by 25 basis points",
        "impact": {
          "dollar_impact": -2425,
          "percentage_impact": -0.5,
          "new_portfolio_value": 482575
        },
        "severity": "mild"
      },
      {
        "id": "rates_down_25bp",
        "name": "Rates Down 0.25%",
        "description": "Federal Reserve cuts rates by 25 basis points",
        "impact": {
          "dollar_impact": 2425,
          "percentage_impact": 0.5,
          "new_portfolio_value": 487425
        },
        "severity": "positive"
      },
      {
        "id": "oil_up_5",
        "name": "Oil Up 5%",
        "description": "Crude oil prices rise 5%",
        "impact": {
          "dollar_impact": -1212,
          "percentage_impact": -0.25,
          "new_portfolio_value": 483788
        },
        "severity": "mild"
      },
      {
        "id": "oil_down_5",
        "name": "Oil Down 5%",
        "description": "Crude oil prices fall 5%",
        "impact": {
          "dollar_impact": 1212,
          "percentage_impact": 0.25,
          "new_portfolio_value": 486212
        },
        "severity": "positive"
      }
    ],
    "portfolio_value": 485000,
    "calculation_date": "2024-06-27T15:30:00Z"
  }
}
```

### 3.4 Factor Analytics

#### 3.4.1 Get Factor Exposures
```http
GET /api/v1/analytics/factors/{portfolio_id}/exposures
```

Returns calculated factor exposures for the portfolio.

**Query Parameters**:
- `view` (string) - portfolio|positions

**Response (200 OK)**:
```json
{
  "data": {
    "portfolio_exposures": {
      "Market Beta": 0.7,
      "Momentum": 0.23,
      "Value": -0.15,
      "Growth": 0.42
    }
  }
}
```

#### 3.4.2 Get Factor Definitions
```http
GET /api/v1/analytics/factors/definitions
```

Returns definitions and metadata for all factors.

**Response (200 OK)**:
```json
{
  "data": [
    {
      "factor_name": "Market Beta",
      "etf_ticker": "SPY",
      "description": "Sensitivity to overall market movements",
      "calculation_method": "real",
      "display_order": 1
    }
  ]
}
```

### 3.5 Correlation Analytics

#### 3.5.1 Get Correlation Matrix
```http
GET /api/v1/analytics/correlation/{portfolio_id}/matrix
```

Returns position correlation matrix.

**Query Parameters**:
- `lookback_days` (integer, default: 90)
- `min_overlap` (integer, default: 30)

**Response (200 OK)**:
```json
{
  "data": {
    "matrix": {
      "AAPL": {
        "AAPL": 1.0,
        "MSFT": 0.82,
        "NVDA": 0.75
      },
      "MSFT": {
        "AAPL": 0.82,
        "MSFT": 1.0,
        "NVDA": 0.68
      }
    },
    "average_correlation": 0.75
  }
}
```

## 4. Portfolio Management APIs (/management/)

CRUD operations for portfolios, positions, and related entities.

### 4.1 Portfolio Management

#### 4.1.1 List Portfolios
```http
GET /api/v1/management/portfolios
```

Returns list of user's portfolios.

**Response (200 OK)**:
```json
{
  "data": {
    "portfolios": [
      {
        "id": "51134ffd-2f13-49bd-b1f5-0c327e801b69",
        "name": "Demo Individual Portfolio",
        "created_at": "2024-01-15T10:00:00Z",
        "position_count": 16,
        "total_value": 485000.00
      }
    ]
  }
}
```

#### 4.1.2 Create Portfolio
```http
POST /api/v1/management/portfolios
```

Creates a new portfolio.

**Request Body**:
```json
{
  "name": "Growth Portfolio",
  "description": "Focus on high-growth technology stocks",
  "initial_cash": 100000.00
}
```

#### 4.1.3 Upload Portfolio CSV
```http
POST /api/v1/management/portfolios/upload
```

Uploads portfolio positions from CSV file.

**Request**:
```http
Content-Type: multipart/form-data
```

**Response (200 OK)**:
```json
{
  "portfolio_id": "new-portfolio-id",
  "positions_created": 35,
  "positions_updated": 0,
  "message": "Portfolio uploaded successfully."
}
```

### 4.2 Position Management

#### 4.2.1 List Positions
```http
GET /api/v1/management/positions
```

Returns list of positions.

**Query Parameters**:
- `portfolio_id` (uuid, required)
- `group_by` (string) - type|strategy|tag
- `tags` (string) - Comma-separated tags
- `tag_mode` (string) - any|all

**Response (200 OK)**:
```json
{
  "data": {
    "positions": [
      {
        "id": "pos_123",
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "type": "LONG",
        "quantity": 500,
        "price": 180,
        "value": 90000,
        "tags": ["#momentum", "#tech"]
      }
    ],
    "summary": {
      "total_positions": 24,
      "gross_exposure": 1667000,
      "net_exposure": 533000
    }
  }
}
```

#### 4.2.2 Add Position
```http
POST /api/v1/management/positions
```

Adds a new position to portfolio.

**Request Body**:
```json
{
  "portfolio_id": "51134ffd-2f13-49bd-b1f5-0c327e801b69",
  "ticker": "AAPL",
  "type": "LONG",
  "quantity": 500,
  "price": 178.50,
  "tags": ["#momentum", "#tech"]
}
```

#### 4.2.3 Update Position
```http
PUT /api/v1/management/positions/{position_id}
```

Updates an existing position.

**Request Body**:
```json
{
  "quantity": 600,
  "tags": ["#momentum", "#tech", "#core"]
}
```

#### 4.2.4 Delete Position
```http
DELETE /api/v1/management/positions/{position_id}
```

Deletes a position from portfolio.

### 4.3 Strategy Management

#### 4.3.1 List Strategies
```http
GET /api/v1/management/strategies
```

Returns list of defined strategies.

**Query Parameters**:
- `portfolio_id` (uuid, required)

**Response (200 OK)**:
```json
{
  "data": {
    "strategies": [
      {
        "id": "strat_001",
        "name": "Tech Momentum",
        "description": "Long technology stocks with momentum",
        "position_count": 8,
        "total_value": 250000
      }
    ]
  }
}
```

### 4.4 Tag Management

#### 4.4.1 List Tags
```http
GET /api/v1/management/tags
```

Returns all tags used in portfolio.

**Query Parameters**:
- `portfolio_id` (uuid, required)

**Response (200 OK)**:
```json
{
  "data": {
    "tags": [
      {
        "name": "#tech",
        "count": 12,
        "type": "sector"
      },
      {
        "name": "#momentum",
        "count": 8,
        "type": "strategy"
      }
    ]
  }
}
```

#### 4.4.2 Create Tag
```http
POST /api/v1/management/tags
```

Creates a new tag.

**Request Body**:
```json
{
  "name": "#defensive",
  "type": "strategy",
  "description": "Defensive positions for market downturns"
}
```

#### 4.4.3 Update Position Tags
```http
PUT /api/v1/management/positions/{position_id}/tags
```

Updates tags for a specific position.

**Request Body**:
```json
{
  "tags": ["#tech", "#momentum", "#core"]
}
```

### 4.5 Alert Management

#### 4.5.1 List Alerts
```http
GET /api/v1/management/alerts
```

Returns active alerts.

**Query Parameters**:
- `portfolio_id` (uuid, required)
- `priority` (string) - critical|high|medium|low

**Response (200 OK)**:
```json
{
  "data": {
    "alerts": [
      {
        "id": "alert_001",
        "type": "expiration_risk",
        "priority": "critical",
        "title": "Options Expiration Risk",
        "message": "2 positions expiring TODAY",
        "triggered_at": "2024-06-28T09:00:00Z"
      }
    ]
  }
}
```

#### 4.5.2 Create Alert Rule
```http
POST /api/v1/management/alerts/rules
```

Creates a new alert rule.

**Request Body**:
```json
{
  "name": "Tech Concentration Alert",
  "condition": {
    "metric": "sector_exposure",
    "sector": "technology",
    "operator": "greater_than",
    "threshold": 0.20
  },
  "priority": "high"
}
```

## 5. Export APIs (/export/)

Data export and report generation endpoints.

### 5.1 Portfolio Export

#### 5.1.1 Export Portfolio Data
```http
GET /api/v1/export/portfolio/{portfolio_id}
```

Exports portfolio data in various formats.

**Query Parameters**:
- `format` (string) - csv|excel|json
- `include` (string) - positions,greeks,exposures

**Response (200 OK)**:
```json
{
  "data": {
    "format": "csv",
    "file_url": "/exports/portfolio_20240627.csv",
    "expires_at": "2024-06-28T00:00:00Z"
  }
}
```

### 5.2 Report Generation

#### 5.2.1 Generate Report
```http
POST /api/v1/export/reports/generate
```

Generates a portfolio report.

**Request Body**:
```json
{
  "portfolio_id": "51134ffd-2f13-49bd-b1f5-0c327e801b69",
  "type": "risk_summary",
  "format": "pdf",
  "sections": ["exposure", "greeks", "factors", "scenarios"]
}
```

**Response (202 Accepted)**:
```json
{
  "job_id": "job_report_789",
  "status": "queued",
  "poll_url": "/api/v1/system/jobs/job_report_789"
}
```

#### 5.2.2 Get Report Templates
```http
GET /api/v1/export/reports/templates
```

Returns available report templates.

**Response (200 OK)**:
```json
{
  "data": {
    "templates": [
      {
        "id": "risk_summary",
        "name": "Risk Summary Report",
        "description": "Complete risk analysis",
        "sections": ["exposure", "greeks", "factors"]
      }
    ]
  }
}
```

#### 5.2.3 Schedule Report
```http
POST /api/v1/export/reports/schedule
```

Schedules recurring report generation.

**Request Body**:
```json
{
  "portfolio_id": "51134ffd-2f13-49bd-b1f5-0c327e801b69",
  "template_id": "weekly_risk",
  "frequency": "weekly",
  "day_of_week": 5,
  "time": "16:00",
  "email": "user@example.com"
}
```

### 5.3 Trade Lists

#### 5.3.1 Export Trade List
```http
POST /api/v1/export/trades
```

Generates trade list for execution.

**Request Body**:
```json
{
  "trades": [
    {
      "symbol": "AAPL",
      "action": "SELL",
      "quantity": 200
    }
  ],
  "format": "csv",
  "broker": "generic"
}
```

**Response (200 OK)**:
```json
{
  "data": {
    "format": "csv",
    "file_url": "/exports/trades_20240627.csv",
    "trade_count": 1
  }
}
```

## 6. System APIs (/system/)

System utilities, job management, and UI synchronization.

### 6.1 Job Management

#### 6.1.1 Get Job Status
```http
GET /api/v1/system/jobs/{job_id}
```

Returns status of an async job.

**Response (200 OK)**:
```json
{
  "data": {
    "job_id": "job_report_789",
    "status": "processing",
    "created_at": "2024-06-27T14:32:15Z",
    "estimated_completion": "2024-06-27T14:32:20Z"
  }
}
```

#### 6.1.2 Get Job Result
```http
GET /api/v1/system/jobs/{job_id}/result
```

Returns result of completed job.

**Response (200 OK)**:
```json
{
  "data": {
    "job_id": "job_report_789",
    "status": "completed",
    "result": {
      "file_url": "/exports/report_20240627.pdf"
    }
  }
}
```

#### 6.1.3 Cancel Job
```http
POST /api/v1/system/jobs/{job_id}/cancel
```

Cancels a running job.

### 6.2 UI Synchronization

#### 6.2.1 Navigate UI
```http
POST /api/v1/system/ui/navigate
```

Triggers UI navigation.

**Request Body**:
```json
{
  "target": "positions_tab",
  "params": {
    "filter": "expiring_today",
    "sort": "gamma_risk_desc"
  }
}
```

#### 6.2.2 Highlight Elements
```http
POST /api/v1/system/ui/highlight
```

Highlights UI elements.

**Request Body**:
```json
{
  "elements": [
    {
      "id": "pos_020",
      "style": "critical",
      "reason": "expiring_today"
    }
  ]
}
```

#### 6.2.3 Apply Filter
```http
POST /api/v1/system/ui/filter
```

Applies filter preset to UI.

**Request Body**:
```json
{
  "view": "positions",
  "filter": {
    "preset": "expiring_today",
    "sort": {
      "field": "gamma_risk",
      "order": "desc"
    }
  }
}
```

## 7. Authentication

### 7.1 Login
```http
POST /api/v1/auth/login
```

Authenticates user and returns JWT token.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response (200 OK)**:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 7.2 Refresh Token
```http
POST /api/v1/auth/refresh
```

Refreshes expired JWT token.

**Request Body**:
```json
{
  "refresh_token": "..."
}
```

### 7.3 Logout
```http
POST /api/v1/auth/logout
```

Invalidates current session.

## 8. Error Handling

### 8.1 Standard Error Response
```json
{
  "success": false,
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "Invalid portfolio ID",
      "field": "portfolio_id"
    }
  ]
}
```

### 8.2 HTTP Status Codes
- `200 OK` - Successful request
- `201 Created` - Resource created
- `202 Accepted` - Async job started
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Access denied
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## 9. Rate Limiting

### 9.1 Limits
- **Standard**: 100 requests/minute per user
- **Burst**: 10 requests/second max
- **Headers**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### 9.2 429 Response
```json
{
  "success": false,
  "errors": [
    {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Too many requests",
      "retry_after": 30
    }
  ]
}
```

## 10. Implementation Notes

### 10.1 Raw Data Endpoints (/data/)
- No calculations performed
- Complete datasets returned (no pagination)
- Optimized for LLM consumption
- Typical response size: 50-150k tokens
- All monetary values as raw numbers

### 10.2 Analytics Endpoints (/analytics/)
- All calculations performed server-side
- Results may be cached for performance
- Standard pagination for large result sets
- Visual indicators included where appropriate

### 10.3 Async Operations
- Report generation always async
- Complex calculations may be async
- Poll job status endpoint for results
- Jobs timeout after 5 minutes

### 10.4 Data Freshness
- Raw data includes timestamps
- Analytics use latest available data
- Market data cached for 1 minute
- Factor calculations updated daily

## 11. V1.4.4 Summary

This specification represents a major reorganization of the API namespace structure to provide:

1. **Clear separation** between raw data and calculated analytics
2. **LLM-optimized** raw data endpoints for independent analysis
3. **Self-documenting** endpoint paths
4. **Consistent** namespace depth and organization
5. **Simplified** architecture without unnecessary complexity

### Key Updates in v1.4.4:
- **Added**: Scenario analysis endpoint at `/api/v1/analytics/risk/{id}/scenarios` to support frontend risk analysis tab
- **Added**: Market quotes endpoint at `/api/v1/data/prices/quotes` for real-time price updates
- **Supports**: All features in V0_V5_FRONT_END_PROTOTYPE_FEATURES.md and DEMO_SCRIPT_V1.4.md (except ProForma modeling)

The new structure supports both traditional frontend applications and LLM-based analysis tools, with a clear distinction between data access and analytical capabilities.
