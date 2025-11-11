# Multi-Portfolio API Reference

**Version**: 1.0.0
**Created**: 2025-11-01
**Status**: Production Ready

Complete API reference for multi-portfolio functionality in SigmaSight.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Portfolio Management (CRUD)](#portfolio-management-crud)
4. [Aggregate Analytics](#aggregate-analytics)
5. [Migration from Single Portfolio](#migration-from-single-portfolio)
6. [Examples](#examples)

---

## Overview

The multi-portfolio system allows users to manage multiple investment accounts (taxable, IRA, 401k, etc.) within a single SigmaSight account. Analytics can be viewed:
- **Per portfolio**: Traditional single-portfolio analytics
- **Aggregated**: Combined metrics across all portfolios using weighted averages

### Key Features

- **Unlimited portfolios** per user account
- **Portfolio-as-asset** aggregation model
- **Weighted average** calculations for risk metrics
- **Backward compatible** with existing single-portfolio users
- **Soft delete** for portfolio archival
- **Progressive disclosure** ready (hide multi-portfolio features when user has 1 portfolio)

### Account Types Supported

- `taxable` - Standard brokerage account
- `ira` - Traditional IRA
- `roth_ira` - Roth IRA
- `401k` - 401(k) retirement plan
- `403b` - 403(b) retirement plan
- `529` - 529 education savings plan
- `hsa` - Health Savings Account
- `trust` - Trust account
- `other` - Other account types

---

## Architecture

### Portfolio-as-Asset Model

Each portfolio is treated as a conceptual investment in the aggregate view:

```
Portfolio A: $500k, Beta=1.2  →  Weight: 50%
Portfolio B: $300k, Beta=0.8  →  Weight: 30%
Portfolio C: $200k, Beta=1.0  →  Weight: 20%

Total Value: $1,000k

Aggregate Beta = (1.2 × 0.50) + (0.8 × 0.30) + (1.0 × 0.20) = 1.04
```

### Weight Calculation

```
Weight_i = Portfolio_Value_i / Total_Value

Where:
- Portfolio_Value_i = Latest snapshot.total_value OR portfolio.equity_balance
- Total_Value = Σ(Portfolio_Value_i) for all active portfolios
```

### Aggregation Formulas

- **Beta**: `Σ(Beta_i × Weight_i)`
- **Volatility**: `Σ(Volatility_i × Weight_i)` (approximation)
- **Factor Exposures**: `Σ(Factor_i × Weight_i)` for each factor

### Data Sources

- **Portfolio values**: `PortfolioSnapshot.total_value` (preferred) or `Portfolio.equity_balance`
- **Beta**: `PortfolioSnapshot.beta_calculated_90d` or `beta_provider_1y`
- **Volatility**: `PortfolioSnapshot.realized_volatility_21d`
- **Factors**: `PositionFactorExposure` (per position, averaged per portfolio)

---

## Portfolio Management (CRUD)

Base path: `/api/v1/portfolios`

### Create Portfolio

**`POST /api/v1/portfolios`**

Create a new portfolio for the authenticated user.

**Request Body:**
```json
{
  "name": "My Retirement Account",
  "account_name": "Fidelity IRA",
  "account_type": "ira",
  "description": "Traditional IRA at Fidelity",
  "currency": "USD",
  "equity_balance": 100000.00,
  "is_active": true
}
```

**Response:** `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "My Retirement Account",
  "account_name": "Fidelity IRA",
  "account_type": "ira",
  "description": "Traditional IRA at Fidelity",
  "currency": "USD",
  "equity_balance": 100000.00,
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "deleted_at": null,
  "position_count": 0,
  "total_value": 100000.00
}
```

**Validation:**
- `name`: Required, 1-255 characters
- `account_name`: Required, 1-100 characters
- `account_type`: Must be one of: taxable, ira, roth_ira, 401k, 403b, 529, hsa, trust, other
- `currency`: 3-character code (e.g., "USD")
- `equity_balance`: Optional, >= 0
- `is_active`: Default true

---

### List Portfolios

**`GET /api/v1/portfolios?include_inactive={bool}`**

Get all portfolios for the authenticated user.

**Query Parameters:**
- `include_inactive` (optional, default: false): Include inactive/deleted portfolios

**Response:** `200 OK`
```json
{
  "portfolios": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "660e8400-e29b-41d4-a716-446655440000",
      "account_name": "Schwab Taxable",
      "account_type": "taxable",
      "value": 500000.00,
      "weight": 0.50,
      "position_count": 25,
      "is_active": true,
      ...
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "account_name": "Fidelity IRA",
      "account_type": "ira",
      "value": 300000.00,
      "weight": 0.30,
      "position_count": 15,
      "is_active": true,
      ...
    }
  ],
  "total_count": 2,
  "active_count": 2,
  "total_value": 800000.00
}
```

---

### Get Portfolio

**`GET /api/v1/portfolios/{portfolio_id}`**

Get a specific portfolio by ID.

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "660e8400-e29b-41d4-a716-446655440000",
  "account_name": "Schwab Taxable",
  "account_type": "taxable",
  "description": "Main taxable brokerage",
  "currency": "USD",
  "equity_balance": 500000.00,
  "is_active": true,
  "position_count": 25,
  "total_value": 520000.00,
  ...
}
```

**Errors:**
- `404`: Portfolio not found or user doesn't have access

---

### Update Portfolio

**`PUT /api/v1/portfolios/{portfolio_id}`**

Update an existing portfolio. All fields are optional.

**Request Body:**
```json
{
  "account_name": "Schwab Roth IRA (Updated)",
  "account_type": "roth_ira",
  "is_active": false
}
```

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "account_name": "Schwab Roth IRA (Updated)",
  "account_type": "roth_ira",
  "is_active": false,
  ...
}
```

**Errors:**
- `404`: Portfolio not found
- `400`: Invalid update data

---

### Delete Portfolio (Soft Delete)

**`DELETE /api/v1/portfolios/{portfolio_id}`**

Soft delete a portfolio. Sets `deleted_at` timestamp and `is_active=false`.

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Portfolio soft deleted successfully",
  "portfolio_id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted_at": "2025-01-01T12:00:00Z"
}
```

**Business Rules:**
- Cannot delete the last active portfolio
- Positions are NOT deleted (allows restoration)
- Soft-deleted portfolios don't appear in default lists (unless `include_inactive=true`)

**Errors:**
- `404`: Portfolio not found
- `400`: Cannot delete last active portfolio

---

## Aggregate Analytics

Base path: `/api/v1/analytics/aggregate`

All endpoints support optional `portfolio_ids` query parameter to filter specific portfolios.

### Overview

**`GET /api/v1/analytics/aggregate/overview`**

Get aggregate portfolio overview.

**Query Parameters:**
- `portfolio_ids` (optional): List of portfolio UUIDs to aggregate. If omitted, aggregates all active portfolios.

**Response:** `200 OK`
```json
{
  "total_value": 1000000.00,
  "portfolio_count": 3,
  "portfolios": [
    {
      "id": "550e8400-...",
      "account_name": "Schwab Taxable",
      "account_type": "taxable",
      "value": 500000.00,
      "weight": 0.50
    },
    {
      "id": "660e8400-...",
      "account_name": "Fidelity IRA",
      "account_type": "ira",
      "value": 300000.00,
      "weight": 0.30
    },
    {
      "id": "770e8400-...",
      "account_name": "Vanguard 401k",
      "account_type": "401k",
      "value": 200000.00,
      "weight": 0.20
    }
  ],
  "aggregate_metrics": {}
}
```

---

### Breakdown

**`GET /api/v1/analytics/aggregate/breakdown`**

Get detailed breakdown with enhanced metrics.

**Response:** `200 OK`
```json
{
  "total_value": 1000000.00,
  "portfolio_count": 3,
  "portfolios": [
    {
      "id": "550e8400-...",
      "account_name": "Schwab Taxable",
      "value": 500000.00,
      "weight": 0.50,
      "weight_pct": 50.00,
      "contribution_dollars": 500000.00
    },
    ...
  ],
  "summary": {
    "total_weight": 1.00,
    "average_value": 333333.33
  }
}
```

---

### Aggregate Beta

**`GET /api/v1/analytics/aggregate/beta`**

Get weighted average beta across portfolios.

**Response:** `200 OK`
```json
{
  "aggregate_beta": 1.04,
  "total_value": 1000000.00,
  "portfolio_count": 3,
  "portfolios": [
    {
      "portfolio_id": "550e8400-...",
      "account_name": "Schwab Taxable",
      "value": 500000.00,
      "weight": 0.50,
      "beta": 1.20,
      "contribution": 0.60
    },
    {
      "portfolio_id": "660e8400-...",
      "account_name": "Fidelity IRA",
      "value": 300000.00,
      "weight": 0.30,
      "beta": 0.80,
      "contribution": 0.24
    },
    {
      "portfolio_id": "770e8400-...",
      "account_name": "Vanguard 401k",
      "value": 200000.00,
      "weight": 0.20,
      "beta": 1.00,
      "contribution": 0.20
    }
  ],
  "calculation_method": "weighted_average",
  "formula": "Σ(Beta_i × Weight_i) where Weight_i = Value_i / Total_Value"
}
```

---

### Aggregate Volatility

**`GET /api/v1/analytics/aggregate/volatility`**

Get weighted average volatility (approximation).

**Response:** `200 OK`
```json
{
  "aggregate_volatility": 0.181,
  "total_value": 1000000.00,
  "portfolio_count": 3,
  "portfolios": [
    {
      "portfolio_id": "550e8400-...",
      "account_name": "Schwab Taxable",
      "value": 500000.00,
      "weight": 0.50,
      "volatility": 0.20,
      "contribution": 0.10
    },
    ...
  ],
  "calculation_method": "weighted_average",
  "note": "Simplified approximation. True volatility should account for correlations.",
  "formula": "Σ(Volatility_i × Weight_i) where Weight_i = Value_i / Total_Value"
}
```

**Note**: This is a simplified approximation. True portfolio volatility should account for correlations between portfolios, which this endpoint does NOT do.

---

### Aggregate Factor Exposures

**`GET /api/v1/analytics/aggregate/factor-exposures`**

Get aggregate exposures for the 5-factor model.

**Response:** `200 OK`
```json
{
  "aggregate_factors": {
    "market": 1.05,
    "size": -0.25,
    "value": 0.15,
    "momentum": 0.40,
    "quality": 0.70
  },
  "total_value": 1000000.00,
  "portfolio_count": 3,
  "calculation_method": "weighted_average",
  "factors": {
    "market": "SPY - S&P 500",
    "size": "IWM - Russell 2000",
    "value": "IVE - S&P 500 Value",
    "momentum": "MTUM - Momentum",
    "quality": "QUAL - Quality"
  },
  "formula": "For each factor: Σ(Exposure_i × Weight_i)"
}
```

---

## Migration from Single Portfolio

### Backward Compatibility

The multi-portfolio system is **100% backward compatible** with existing single-portfolio users:

**Mathematical Identity:**
```
Single Portfolio: Value=$500k, Beta=1.2
Weight = $500k / $500k = 1.0
Aggregate Beta = 1.2 × 1.0 = 1.2 ✓
```

For users with one portfolio, weighted average returns the same value as the single portfolio.

### Existing Endpoints

All existing single-portfolio endpoints continue to work unchanged:

```
GET /api/v1/analytics/portfolio/{portfolio_id}/overview
GET /api/v1/analytics/portfolio/{portfolio_id}/beta
GET /api/v1/analytics/portfolio/{portfolio_id}/volatility
GET /api/v1/analytics/portfolio/{portfolio_id}/factor-exposures
... (all other endpoints)
```

### Progressive Disclosure

Frontend can implement progressive disclosure:

```typescript
const isSinglePortfolio = portfolios.length === 1;

if (isSinglePortfolio) {
  // Show simplified single-portfolio view
  // Hide "account breakdown" and "% allocation" charts
  return <SinglePortfolioView />;
} else {
  // Show full multi-portfolio view with aggregates
  return <MultiPortfolioView />;
}
```

---

## Examples

### Example 1: Creating Multiple Portfolios

```bash
# Create taxable account
POST /api/v1/portfolios
{
  "name": "Schwab Taxable",
  "account_name": "Schwab Taxable Account",
  "account_type": "taxable",
  "equity_balance": 500000
}

# Create IRA
POST /api/v1/portfolios
{
  "name": "Fidelity IRA",
  "account_name": "Fidelity Traditional IRA",
  "account_type": "ira",
  "equity_balance": 300000
}

# Create 401k
POST /api/v1/portfolios
{
  "name": "Vanguard 401k",
  "account_name": "Vanguard 401(k)",
  "account_type": "401k",
  "equity_balance": 200000
}
```

### Example 2: Viewing Aggregate Analytics

```bash
# Get aggregate overview
GET /api/v1/analytics/aggregate/overview
# Returns: 3 portfolios, $1M total value

# Get aggregate beta
GET /api/v1/analytics/aggregate/beta
# Returns: Weighted average beta across all portfolios

# Filter specific portfolios
GET /api/v1/analytics/aggregate/beta?portfolio_ids=550e8400-...&portfolio_ids=660e8400-...
# Returns: Beta for just taxable and IRA (excludes 401k)
```

### Example 3: Single Portfolio User Experience

```bash
# User with one portfolio
GET /api/v1/portfolios
# Returns: 1 portfolio with weight=1.0

GET /api/v1/analytics/aggregate/beta
# Returns: Same beta as single portfolio (identity)
```

---

## Best Practices

### For API Consumers

1. **Check portfolio count** before showing multi-portfolio UI elements
2. **Use aggregate endpoints** for "total household" views
3. **Use single-portfolio endpoints** for individual account analysis
4. **Handle optional `portfolio_ids`** to allow filtering
5. **Display calculation methodology** so users understand aggregation

### For Backend Developers

1. **Always use PortfolioAggregationService** for aggregation logic
2. **Prefer snapshot data** over equity_balance for accuracy
3. **Log aggregate calculations** for debugging
4. **Handle missing data gracefully** (some portfolios may lack beta/volatility)
5. **Test with n=1 portfolios** to verify backward compatibility

---

## Related Documentation

- **Database Schema**: See `backend/alembic/versions/9b0768a49ad8_add_multi_portfolio_support.py`
- **Service Layer**: See `backend/app/services/portfolio_aggregation_service.py`
- **Planning Docs**: See `frontend/_docs/Multi-Portfolio/`
- **Unit Tests**: See `backend/tests/test_portfolio_aggregation_service.py`

---

**Last Updated**: 2025-11-01
**Maintained By**: SigmaSight Development Team
