# SigmaSight User Onboarding Guide

## Overview

This guide walks you through the complete process of creating a SigmaSight account and importing your investment portfolio.

**Time Required**: 5-10 minutes
**Prerequisites**: Investment portfolio data (positions, quantities, entry prices)

---

## Step 1: Register Your Account

### Requirements
- Valid email address
- Strong password (8+ characters, uppercase, lowercase, number)
- Beta invite code (provided by SigmaSight)

### API Call
```bash
POST /api/v1/onboarding/register
```

### Example Request
```bash
curl -X POST https://api.sigmasight.io/api/v1/onboarding/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your.email@example.com",
    "password": "YourSecurePass123",
    "full_name": "Your Full Name",
    "invite_code": "YOUR-INVITE-CODE"
  }'
```

### Response
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "your.email@example.com",
  "full_name": "Your Full Name",
  "message": "Account created successfully! You can now log in and create your portfolio.",
  "next_step": {
    "action": "login",
    "endpoint": "/api/v1/auth/login",
    "description": "Log in with your email and password to get access token"
  }
}
```

### Common Errors
- **401 ERR_INVITE_001**: Invalid invite code
- **409 ERR_USER_001**: Email already registered
- **422 ERR_USER_002**: Invalid email format
- **422 ERR_USER_003**: Weak password

---

## Step 2: Log In

### API Call
```bash
POST /api/v1/auth/login
```

### Example Request
```bash
curl -X POST https://api.sigmasight.io/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your.email@example.com",
    "password": "YourSecurePass123"
  }'
```

### Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "your.email@example.com",
    "full_name": "Your Full Name"
  }
}
```

**Save your access token** - you'll need it for all subsequent requests.

---

## Step 3: Prepare Your Portfolio CSV

### Download Template

```bash
curl https://api.sigmasight.io/api/v1/onboarding/csv-template \
  -o portfolio_template.csv
```

### CSV Format (12 Columns)

| Column | Required | Description | Example |
|--------|----------|-------------|---------|
| Symbol | ✅ | Stock/ETF/Option symbol | AAPL |
| Quantity | ✅ | Number of shares (negative = short) | 100 |
| Entry Price Per Share | ✅ | Purchase price | 158.50 |
| Entry Date | ✅ | YYYY-MM-DD format | 2024-01-15 |
| Investment Class | ❌ | PUBLIC, OPTIONS, or PRIVATE | PUBLIC |
| Investment Subtype | ❌ | STOCK, ETF, MUTUAL_FUND, etc. | STOCK |
| Underlying Symbol | ❌ | For options only | SPY |
| Strike Price | ❌ | For options only | 450.00 |
| Expiration Date | ❌ | For options (YYYY-MM-DD) | 2024-03-15 |
| Option Type | ❌ | CALL or PUT | CALL |
| Exit Date | ❌ | For closed positions | 2024-02-15 |
| Exit Price Per Share | ❌ | For closed positions | 175.00 |

### Example CSV

```csv
Symbol,Quantity,Entry Price Per Share,Entry Date,Investment Class,Investment Subtype,Underlying Symbol,Strike Price,Expiration Date,Option Type,Exit Date,Exit Price Per Share
AAPL,100,158.00,2024-01-15,PUBLIC,STOCK,,,,,,
SPY,50,445.20,2024-01-20,PUBLIC,ETF,,,,,,
,10,5.50,2024-02-01,OPTIONS,,SPY,450.00,2024-03-15,CALL,,
SHOP,-25,62.50,2024-02-10,PUBLIC,STOCK,,,,,,
SPAXX,10000,1.00,2024-01-01,PUBLIC,CASH,,,,,,
```

### Converting From Broker Exports

#### From Schwab
1. Export positions to CSV from Schwab website
2. Map columns to SigmaSight template:
   - **Symbol** → Symbol
   - **Qty** → Quantity
   - **Price** → Entry Price Per Share
   - **Cost Basis** ÷ Quantity → Entry Price Per Share (if total provided)
3. Add **Entry Date** (Schwab doesn't export this - use your records)
4. Remove any summary rows or headers

#### From Fidelity
1. Export positions from Fidelity
2. Map columns similarly
3. Watch for date format differences (MM/DD/YYYY → YYYY-MM-DD)
4. Handle cash positions (map to SPAXX or similar)

#### From Vanguard
1. Export holdings
2. Convert mutual fund symbols if needed
3. Map date formats
4. Add entry dates from transaction history

### Validation Rules

**Symbol**:
- Required, max 100 characters
- Alphanumeric, dash, dot, underscore only

**Quantity**:
- Required, cannot be zero
- Max 6 decimal places
- Negative = short position

**Entry Price**:
- Required, must be positive
- Max 2 decimal places

**Entry Date**:
- Required, YYYY-MM-DD format
- Cannot be in future
- Cannot be >100 years old

**Options** (if Investment Class = OPTIONS):
- Must provide: Underlying Symbol, Strike Price, Expiration Date, Option Type
- Option Type must be CALL or PUT

**Exit Date** (if provided):
- Cannot be before Entry Date
- Must be in YYYY-MM-DD format

---

## Step 4: Create Portfolio with CSV

### API Call
```bash
POST /api/v1/onboarding/create-portfolio
```

### Example Request
```bash
curl -X POST https://api.sigmasight.io/api/v1/onboarding/create-portfolio \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "portfolio_name=My Investment Portfolio" \
  -F "equity_balance=250000" \
  -F "description=Conservative growth portfolio" \
  -F "csv_file=@my_positions.csv"
```

### Parameters
- **portfolio_name**: Display name for your portfolio (required)
- **equity_balance**: Total account value/equity (required)
- **description**: Optional portfolio description
- **csv_file**: Your positions CSV file (required)

### Response (Success)
```json
{
  "portfolio_id": "456e7890-e89b-12d3-a456-426614174000",
  "portfolio_name": "My Investment Portfolio",
  "equity_balance": 250000.0,
  "positions_imported": 45,
  "positions_failed": 0,
  "total_positions": 45,
  "message": "Portfolio created successfully. Use the /calculate endpoint to run risk analytics.",
  "next_step": {
    "action": "calculate",
    "endpoint": "/api/v1/portfolio/456e7890-e89b-12d3-a456-426614174000/calculate",
    "description": "Trigger batch calculations to populate risk metrics"
  }
}
```

### Common Errors

**CSV Validation Errors**:
- **ERR_CSV_001**: File too large (>10MB)
- **ERR_CSV_002**: Invalid file type (must be .csv)
- **ERR_CSV_003**: Empty file
- **ERR_CSV_004**: Missing required column
- **ERR_CSV_006**: Malformed CSV

**Position Errors**:
- **ERR_POS_001**: Missing symbol
- **ERR_POS_004**: Missing quantity
- **ERR_POS_008**: Missing entry price
- **ERR_POS_012**: Missing entry date
- **ERR_POS_023**: Duplicate position (same symbol + entry date)

**Portfolio Errors**:
- **ERR_PORT_001**: User already has a portfolio (one per user)
- **ERR_PORT_002**: Portfolio name required
- **ERR_PORT_004**: Equity balance required

### Response (Validation Errors)
```json
{
  "error": {
    "code": "ERR_PORT_008",
    "message": "CSV validation failed with 3 error(s)",
    "details": {
      "errors": [
        {
          "code": "ERR_POS_004",
          "message": "Quantity is required",
          "row": 5,
          "field": "Quantity"
        },
        {
          "code": "ERR_POS_012",
          "message": "Entry date is required",
          "row": 8,
          "field": "Entry Date"
        }
      ],
      "total_errors": 2
    }
  }
}
```

**What to do**: Fix the errors in your CSV and retry the upload.

---

## Step 5: Trigger Portfolio Calculations

After importing your portfolio, trigger the calculation engine to populate risk metrics.

### API Call
```bash
POST /api/v1/portfolio/{portfolio_id}/calculate
```

### Example Request
```bash
curl -X POST https://api.sigmasight.io/api/v1/portfolio/456e7890-e89b-12d3-a456-426614174000/calculate \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### What Happens
1. **Preprocessing (10-30 seconds)**:
   - Enriches security master data (sector, industry)
   - Bootstraps price cache (30 days historical data)
   - Validates data coverage (>80% required)

2. **Batch Processing (30-60 seconds)**:
   - Runs 8 calculation engines:
     - Position Greeks (options)
     - Factor exposures
     - Correlations
     - Market risk scenarios
     - Stress testing
     - Portfolio aggregation
     - Volatility metrics
     - Beta calculations

### Response
```json
{
  "status": "started",
  "batch_run_id": "789e0123-e89b-12d3-a456-426614174000",
  "portfolio_id": "456e7890-e89b-12d3-a456-426614174000",
  "preprocessing": {
    "symbols_count": 45,
    "security_master_enriched": 43,
    "prices_bootstrapped": 42,
    "price_coverage_percentage": 93.3,
    "ready_for_batch": true,
    "warnings": [],
    "recommendations": []
  },
  "message": "Portfolio calculations started. This may take 30-60 seconds to complete. Poll the status endpoint to check progress.",
  "poll_url": "/api/v1/portfolio/456e7890-e89b-12d3-a456-426614174000/batch-status/789e0123-e89b-12d3-a456-426614174000"
}
```

### Network Failures

If historical price data cannot be fetched (network issues):
```json
{
  "preprocessing": {
    "network_failure": true,
    "warnings": [
      "Price data unavailable due to network issues. Batch processing will use entry prices."
    ],
    "recommendations": [
      "Run price update later when network is available"
    ]
  }
}
```

The system will still proceed with calculations using your entry prices.

### Force Re-run

To re-run preprocessing (e.g., after network is restored):
```bash
curl -X POST "https://api.sigmasight.io/api/v1/portfolio/{portfolio_id}/calculate?force=true" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Step 6: View Your Portfolio

Once calculations complete, access your portfolio analytics:

### Portfolio Overview
```bash
GET /api/v1/analytics/portfolio/{portfolio_id}/overview
```

Returns:
- Total value, P&L, return %
- Asset allocation
- Greeks (delta, gamma, theta, vega)
- Risk metrics

### Risk Metrics
```bash
GET /api/v1/analytics/portfolio/{portfolio_id}/risk-metrics
```

Returns:
- VaR (Value at Risk)
- Expected shortfall
- Maximum drawdown
- Sharpe ratio
- Beta to market

### Factor Exposures
```bash
GET /api/v1/analytics/portfolio/{portfolio_id}/factor-exposures
```

Returns exposures to:
- Market (SPY)
- Tech (QQQ)
- Small Cap (IWM)
- Bonds (TLT)
- Gold (GLD)
- Energy (XLE)
- Real Estate (VNQ)
- International (EFA)

### Correlation Matrix
```bash
GET /api/v1/analytics/portfolio/{portfolio_id}/correlations
```

### Stress Testing
```bash
GET /api/v1/analytics/portfolio/{portfolio_id}/stress-test
```

Returns portfolio impact under 18 market scenarios:
- Market crashes (-10%, -20%, -30%)
- Sector rotations
- Interest rate shocks
- Volatility spikes
- Black swan events

---

## Troubleshooting

### Registration Issues

**Problem**: Invalid invite code
**Solution**: Double-check your invite code. Contact support if issue persists.

**Problem**: Email already exists
**Solution**: Use a different email or reset your password if you forgot it.

**Problem**: Weak password error
**Solution**: Ensure password has 8+ characters with uppercase, lowercase, and numbers.

### CSV Import Issues

**Problem**: "Missing required column"
**Solution**: Ensure CSV has all required columns in the header row. Download template for reference.

**Problem**: "Entry date is required"
**Solution**: Every position needs an entry date. Add dates from your transaction history.

**Problem**: "Duplicate position detected"
**Solution**: Same symbol with same entry date appears twice. Combine positions or use different dates.

**Problem**: File too large (>10MB)
**Solution**: Split into multiple portfolios or contact support for increased limit.

### Calculation Issues

**Problem**: "Batch already running"
**Solution**: Wait for current calculations to complete (30-60 seconds).

**Problem**: Low price coverage (<80%)
**Solution**: System will still proceed. Run with `force=true` later to retry price fetch.

**Problem**: Network timeout during preprocessing
**Solution**: Calculations proceed with entry prices. Re-run when network is stable.

---

## Support

**Documentation**: https://docs.sigmasight.io
**API Reference**: https://api.sigmasight.io/docs
**Email**: support@sigmasight.io

---

## API Endpoint Reference

| Endpoint | Method | Authentication | Description |
|----------|--------|----------------|-------------|
| `/onboarding/register` | POST | ❌ | Create account |
| `/auth/login` | POST | ❌ | Get access token |
| `/onboarding/csv-template` | GET | ❌ | Download CSV template |
| `/onboarding/create-portfolio` | POST | ✅ | Import portfolio |
| `/portfolio/{id}/calculate` | POST | ✅ | Trigger calculations |
| `/analytics/portfolio/{id}/overview` | GET | ✅ | Portfolio summary |
| `/analytics/portfolio/{id}/risk-metrics` | GET | ✅ | Risk analytics |
| `/analytics/portfolio/{id}/factor-exposures` | GET | ✅ | Factor analysis |
| `/analytics/portfolio/{id}/correlations` | GET | ✅ | Correlation matrix |
| `/analytics/portfolio/{id}/stress-test` | GET | ✅ | Stress scenarios |

---

## Next Steps

After onboarding:
1. **Explore Analytics**: Review all available analytics endpoints
2. **AI Chat**: Use the AI assistant to ask questions about your portfolio
3. **Update Positions**: Add/remove positions as your portfolio changes
4. **Scheduled Calculations**: Set up automatic daily recalculations
5. **Export Reports**: Generate PDF reports of your risk metrics

Welcome to SigmaSight! 🎉
