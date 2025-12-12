# SigmaSight Backend API Reference V1.5.0

**Version**: 1.5.0
**Date**: December 11, 2025
**Status**: ✅ **PRODUCTION-READY** - Code-verified implemented endpoints
**Purpose**: Reference documentation for all implemented API endpoints

## Overview

This document provides comprehensive reference documentation for all **implemented and production-ready endpoints** in the SigmaSight Backend API. All endpoints have been **code-verified** to access database data through direct ORM queries or service layers and are ready for frontend integration.

### Namespace Organization
- **`/auth/`**: Authentication and user management
- **`/data/`**: Raw data endpoints optimized for LLM consumption
- **`/analytics/`**: Calculated metrics and derived analytics values (portfolio-level and aggregate)
- **`/chat/`**: AI chat conversation management
- **`/target-prices/`**: Portfolio target price management
- **`/tags/`**: Tag management
- **`/positions/`**: Position operations and tagging
- **`/portfolios/`**: Portfolio CRUD and calculations
- **`/fundamentals/`**: Fundamental data (financial statements, analyst estimates)
- **`/insights/`**: AI-powered portfolio analysis
- **`/onboarding/`**: User registration and portfolio setup
- **`/admin/`**: Administrative batch processing

### Key Design Principles
1. **Code-Verified**: All endpoints confirmed through direct code inspection
2. **Database-Backed**: Real data from PostgreSQL via SQLAlchemy ORM
3. **LLM-Optimized**: `/data/` endpoints return complete, denormalized datasets
4. **Self-Documenting**: Endpoint paths clearly convey data type and purpose

## ⚠️ Breaking Changes History

### October 2025
**Removed**: All `/api/v1/strategies/*` endpoints and strategy tables. The platform now uses **position-level tagging only**.

**Impact**:
- Multi-leg strategy containers and metrics are no longer supported
- SDKs or scripts calling `/strategies` routes must migrate to `/positions/{id}/tags`
- `usage_count` and related analytics reflect direct position-tag assignments

**Migration Path**:
1. Use `/api/v1/positions/{id}/tags` endpoints to assign tags directly to positions
2. Use `/api/v1/tags/{id}/positions` for reverse lookup instead of strategy queries
3. Remove any references to `strategy_id` columns or `Strategy*` models in integrations

---

# IMPLEMENTED ENDPOINTS ✅

This section documents all **fully implemented and production-ready endpoints** in the SigmaSight Backend API.

### Complete Endpoint Summary

**Total: 129+ endpoint decorators** across 17 categories

Base prefix for all endpoints: `/api/v1`

---

## A. Authentication Endpoints (5 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | User login - returns JWT token in body AND HttpOnly cookie |
| POST | `/auth/register` | User registration with email validation |
| GET | `/auth/me` | Get current authenticated user info |
| POST | `/auth/refresh` | Refresh JWT token |
| POST | `/auth/logout` | Logout - clears auth cookie |

### 1. Login
**Endpoint**: `POST /auth/login`
**Status**: ✅ Fully Implemented
**File**: `app/api/v1/auth.py`
**Authentication**: None required

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

### 2. Register
**Endpoint**: `POST /auth/register`
**Status**: ✅ Fully Implemented
**Authentication**: None required

**Request Body**:
```json
{
  "email": "newuser@example.com",
  "password": "secure_password",
  "full_name": "New User"
}
```

### 3. Get Current User
**Endpoint**: `GET /auth/me`
**Status**: ✅ Fully Implemented
**Authentication**: Required (Bearer token)

### 4. Refresh Token
**Endpoint**: `POST /auth/refresh`
**Status**: ✅ Fully Implemented
**Authentication**: Required (Bearer token)

### 5. Logout
**Endpoint**: `POST /auth/logout`
**Status**: ✅ Fully Implemented
**Authentication**: Required (Bearer token)

---

## B. Data Endpoints (12+ endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/data/portfolios` | List all portfolios for authenticated user |
| GET | `/data/portfolio/{portfolio_id}/complete` | Full portfolio snapshot with optional holdings, timeseries, attribution |
| GET | `/data/portfolio/{portfolio_id}/snapshot` | Latest portfolio snapshot with target prices and betas |
| GET | `/data/portfolio/{portfolio_id}/data-quality` | Data completeness assessment and calculation feasibility |
| GET | `/data/positions/details` | Detailed position info (portfolio_id or position_ids query param) |
| POST | `/data/positions/restore-sector-tags` | Restore sector tags for all positions in portfolio |
| GET | `/data/prices/historical/{portfolio_id}` | Historical OHLCV data for portfolio positions |
| GET | `/data/prices/quotes` | Current market quotes (symbols query param) |
| GET | `/data/factors/etf-prices` | Factor ETF prices (7-factor model) |
| GET | `/data/positions/top/{portfolio_id}` | Top N positions sorted by market value/weight |
| GET | `/data/demo/{portfolio_type}` | Demo portfolio data (no auth - testing only) |
| GET | `/data/test-demo` | Simple test endpoint |
| GET | `/data/company-profiles` | Company profile data by symbols/positions/portfolio |

### Get Position Details
**Endpoint**: `GET /data/positions/details`
**Status**: ✅ Fully Implemented
**Authentication**: Required

Returns detailed position information including entry prices, cost basis, P&L calculations, company names, and tags.

**Parameters**:
- `portfolio_id` (query, optional): Portfolio UUID - returns all positions in portfolio
- `position_ids` (query, optional): Comma-separated position IDs - returns specific positions
- `include_closed` (query, optional): Include closed positions (default: false)

**Response Fields**:
- Position fields: id, portfolio_id, symbol, company_name, position_type, investment_class, quantity, entry_date, entry_price, cost_basis, current_price, market_value, unrealized_pnl, unrealized_pnl_percent, strike_price, expiration_date, underlying_symbol, notes, tags

### Get Company Profiles
**Endpoint**: `GET /data/company-profiles`
**Status**: ✅ Fully Implemented
**Authentication**: Required

**Query Modes** (exactly one required):
- `symbols`: Direct symbol lookup (e.g., `?symbols=AAPL,MSFT,GOOGL`)
- `position_ids`: Fetch profiles for specific positions
- `portfolio_id`: Fetch profiles for all portfolio symbols

**Company Profile Fields** (53 total):
- Basic Info: company_name, sector, industry, exchange, country, market_cap, description
- Company Type: is_etf, is_fund
- Company Details: ceo, employees, website
- Valuation Metrics: pe_ratio, forward_pe, dividend_yield, beta, week_52_high, week_52_low
- Analyst Data: target_mean_price, target_high_price, target_low_price, number_of_analyst_opinions, recommendation_mean, recommendation_key
- Forward Estimates: forward_eps, earnings_growth, revenue_growth, earnings_quarterly_growth
- Profitability: profit_margins, operating_margins, gross_margins, return_on_assets, return_on_equity, total_revenue
- Current/Next Year Estimates: revenue avg/low/high, earnings avg/low/high, growth, end_date
- Quarterly Estimates (0q, +1q): target_period_date, revenue/eps avg/low/high, analyst_count
- Fiscal Calendar: fiscal_year_end, fiscal_quarter_offset
- Next Earnings: next_earnings_date, next_earnings_expected_eps, next_earnings_expected_revenue

---

## C. Portfolio CRUD Endpoints (7 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/portfolios` | Create new portfolio |
| GET | `/portfolios` | List portfolios (with include_inactive filter) |
| GET | `/portfolios/{portfolio_id}` | Get single portfolio details |
| PUT | `/portfolios/{portfolio_id}` | Update portfolio (name, description, etc.) |
| DELETE | `/portfolios/{portfolio_id}` | Soft delete portfolio |
| POST | `/portfolios/{portfolio_id}/calculate` | Trigger batch calculations (non-admin) |
| GET | `/portfolios/{portfolio_id}/batch-status/{batch_run_id}` | Poll batch processing status |

---

## D. Analytics Endpoints - Portfolio Level (16+ endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/portfolio/{portfolio_id}/overview` | Portfolio metrics: exposures, P&L, position counts |
| GET | `/analytics/portfolio/{portfolio_id}/correlation-matrix` | Pairwise correlations between positions |
| GET | `/analytics/portfolio/{portfolio_id}/diversification-score` | HHI-based diversification metrics |
| GET | `/analytics/portfolio/{portfolio_id}/factor-exposures` | Portfolio-level factor betas (5 factors) |
| GET | `/analytics/portfolio/{portfolio_id}/positions/factor-exposures` | Position-level factor exposures |
| GET | `/analytics/portfolio/{portfolio_id}/stress-test` | Market stress scenario analysis |
| GET | `/analytics/portfolio/{portfolio_id}/sector-exposure` | Sector exposure vs S&P 500 |
| GET | `/analytics/portfolio/{portfolio_id}/concentration` | Concentration metrics and HHI |
| GET | `/analytics/portfolio/{portfolio_id}/volatility` | Volatility analytics with HAR forecasting |
| GET | `/analytics/portfolio/{portfolio_id}/beta-comparison` | Market beta comparison metrics |
| GET | `/analytics/portfolio/{portfolio_id}/market-beta` | Single factor market beta |
| GET | `/analytics/portfolio/{portfolio_id}/beta-calculated-90d` | 90-day calculated beta |
| GET | `/analytics/portfolio/{portfolio_id}/beta-provider-1y` | 1-year provider beta |
| PUT | `/analytics/portfolio/{portfolio_id}/equity` | Update portfolio equity balance |
| POST | `/analytics/portfolio/{portfolio_id}/calculate` | Trigger analytics recalculation |
| GET | `/analytics/portfolio/{portfolio_id}/batch-status/{batch_run_id}` | Poll calculation status |

### Sector Exposure
**Endpoint**: `GET /analytics/portfolio/{portfolio_id}/sector-exposure`
**Status**: ✅ Fully Implemented (October 17, 2025)

Returns portfolio sector weights vs S&P 500 benchmark with over/underweight analysis.

**Response Fields**:
- `portfolio_weights`: Portfolio sector weights (0-1, sum to 1.0)
- `benchmark_weights`: S&P 500 sector weights (0-1, sum to 1.0)
- `over_underweight`: Difference (portfolio - benchmark)
- `largest_overweight`, `largest_underweight`: Sector names
- `total_portfolio_value`, `positions_by_sector`, `unclassified_value`, `unclassified_count`

### Concentration Metrics
**Endpoint**: `GET /analytics/portfolio/{portfolio_id}/concentration`
**Status**: ✅ Fully Implemented (October 17, 2025)

**HHI Interpretation**:
- HHI > 2500: Highly concentrated portfolio
- HHI 1500-2500: Moderately concentrated
- HHI < 1500: Well diversified

**Response Fields**:
- `hhi`: Herfindahl-Hirschman Index (0-10000)
- `effective_num_positions`: Effective number of positions (10000 / HHI)
- `top_3_concentration`, `top_10_concentration`: Sum of top position weights (0-1)
- `total_positions`

### Volatility Analytics
**Endpoint**: `GET /analytics/portfolio/{portfolio_id}/volatility`
**Status**: ✅ Fully Implemented (October 17, 2025)

Returns portfolio volatility analytics with HAR (Heterogeneous Autoregressive) forecasting model.

**Response Fields**:
- `realized_volatility_21d`: 21-day (~1 month) realized volatility (annualized)
- `realized_volatility_63d`: 63-day (~3 months) realized volatility (annualized)
- `expected_volatility_21d`: HAR model forecast for next 21 trading days
- `volatility_trend`: Direction of volatility change ('increasing', 'decreasing', 'stable')
- `volatility_percentile`: Current volatility vs 1-year historical distribution (0-1 scale)

**Volatility Interpretation**:
- < 15%: Very Low (stable portfolio)
- 15-25%: Low (typical for diversified portfolios)
- 25-35%: Moderate (typical for growth portfolios)
- 35-50%: High (aggressive/concentrated positions)
- > 50%: Very High (speculative/leveraged)

---

## E. Analytics Endpoints - Aggregate/Multi-Portfolio (5 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/overview` | Aggregate metrics across all user portfolios |
| GET | `/analytics/breakdown` | Position breakdown across portfolios |
| GET | `/analytics/beta` | Aggregate beta metrics |
| GET | `/analytics/volatility` | Aggregate volatility across portfolios |
| GET | `/analytics/factor-exposures` | Aggregate factor exposures |

---

## F. Analytics Endpoints - Spread Factors (1 endpoint)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/{portfolio_id}/spread-factors` | Spread factor analysis for portfolio |

---

## G. Chat Endpoints (6 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/conversations` | Create new conversation with portfolio context |
| GET | `/chat/conversations/{conversation_id}` | Get specific conversation |
| GET | `/chat/conversations` | List conversations for user |
| PUT | `/chat/conversations/{conversation_id}/mode` | Change conversation mode |
| DELETE | `/chat/conversations/{conversation_id}` | Delete conversation |
| POST | `/chat/send` | Send message with SSE streaming response |

### Send Message (SSE Streaming)
**Endpoint**: `POST /chat/send`
**Status**: ✅ Fully Implemented
**Response Type**: `text/event-stream`

Streams standardized SSE events: `message_created`, `start`, `message` tokens, `done`, with error and heartbeat events.

**Uses**: OpenAI Responses API (NOT Chat Completions API)

---

## H. Target Prices Endpoints (10+ endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/target-prices/{portfolio_id}` | Create target price |
| GET | `/target-prices/{portfolio_id}` | List target prices for portfolio |
| GET | `/target-prices/{portfolio_id}/summary` | Target price summary metrics |
| GET | `/target-prices/target/{id}` | Get specific target price |
| PUT | `/target-prices/target/{id}` | Update target price |
| DELETE | `/target-prices/target/{id}` | Delete target price |
| POST | `/target-prices/{portfolio_id}/bulk` | Bulk create target prices |
| PUT | `/target-prices/{portfolio_id}/bulk-update` | Bulk update target prices |
| POST | `/target-prices/{portfolio_id}/import-csv` | Import target prices from CSV |
| POST | `/target-prices/{portfolio_id}/export` | Export target prices to CSV |

---

## I. Position Management Endpoints (8+ endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/positions` | Create single position (requires portfolio_id query) |
| POST | `/positions/bulk` | Bulk create positions |
| GET | `/positions/{id}` | Get single position |
| PUT | `/positions/{id}` | Update position |
| DELETE | `/positions/{id}` | Delete position (soft/hard) |
| DELETE | `/positions/bulk` | Bulk delete positions |
| POST | `/positions/validate-symbol` | Validate ticker symbol |
| GET | `/positions/check-duplicate` | Check for duplicate symbols |
| GET | `/positions/tags-for-symbol` | Get tags to inherit for symbol |

---

## J. Position Tagging Endpoints (5 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/positions/{position_id}/tags` | Assign tags to position |
| DELETE | `/positions/{position_id}/tags` | Remove tags from position |
| GET | `/positions/{position_id}/tags` | Get position's tags |
| PATCH | `/positions/{position_id}/tags` | Replace all position tags |
| GET | `/tags/{tag_id}/positions` | Get positions by tag (reverse lookup) |

---

## K. Tag Management Endpoints (7 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tags` | Create new tag |
| GET | `/tags` | List user's tags |
| GET | `/tags/{id}` | Get tag details |
| PATCH | `/tags/{id}` | Update tag |
| POST | `/tags/{id}/archive` | Archive tag (soft delete) |
| POST | `/tags/{id}/restore` | Restore archived tag |
| POST | `/tags/defaults` | Create/get default tags |

---

## L. Equity Changes Endpoints (7 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/portfolios/{portfolio_id}/equity-changes` | List equity changes with pagination |
| POST | `/portfolios/{portfolio_id}/equity-changes` | Create contribution/withdrawal |
| GET | `/portfolios/{portfolio_id}/equity-changes/summary` | Equity change summary metrics |
| GET | `/portfolios/{portfolio_id}/equity-changes/export` | Export equity changes (CSV) |
| GET | `/portfolios/{portfolio_id}/equity-changes/{equity_change_id}` | Get single equity change |
| PUT | `/portfolios/{portfolio_id}/equity-changes/{equity_change_id}` | Update equity change |
| DELETE | `/portfolios/{portfolio_id}/equity-changes/{equity_change_id}` | Delete equity change |

---

## M. Fundamental Data Endpoints (4 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/fundamentals/{symbol}/income-statement` | Historical income statements |
| GET | `/fundamentals/{symbol}/balance-sheet` | Historical balance sheets |
| GET | `/fundamentals/{symbol}/cash-flow` | Historical cash flow statements |
| GET | `/fundamentals/{symbol}/analyst-estimates` | Analyst estimates and recommendations |

### Income Statement
**Endpoint**: `GET /fundamentals/{symbol}/income-statement`
**Status**: ✅ Fully Implemented (November 2, 2025)

**Query Parameters**:
- `periods` (default: 4, range: 1-20): Number of periods to return
- `frequency` (default: "q", options: "q" or "a"): Quarterly or annual

**Response Fields** (22 financial fields per period):
- Period Info: period_date, frequency, fiscal_year, fiscal_quarter
- Revenue & Costs: total_revenue, cost_of_revenue, gross_profit, gross_margin
- Operating: operating_income, operating_margin, ebit, ebitda
- Net Income: net_income, net_margin, diluted_eps, basic_eps
- Share Counts: basic_average_shares, diluted_average_shares (BIGINT)
- Tax & Interest: tax_provision, interest_expense, depreciation_and_amortization

### Balance Sheet
**Endpoint**: `GET /fundamentals/{symbol}/balance-sheet`
**Status**: ✅ Fully Implemented (November 2, 2025)

**Response Fields** (29 financial fields per period):
- Assets: total_assets, current_assets, cash_and_cash_equivalents, accounts_receivable, inventory
- Liabilities: total_liabilities, current_liabilities, accounts_payable, short_term_debt, long_term_debt, total_debt
- Equity: total_stockholders_equity, retained_earnings, common_stock
- Calculated Metrics: working_capital, net_debt, current_ratio, debt_to_equity

### Cash Flow
**Endpoint**: `GET /fundamentals/{symbol}/cash-flow`
**Status**: ✅ Fully Implemented (November 2, 2025)

**Response Fields** (19 financial fields per period):
- Operating Activities: operating_cash_flow, stock_based_compensation
- Investing Activities: investing_cash_flow, capital_expenditures
- Financing Activities: financing_cash_flow, dividends_paid, stock_repurchases
- Calculated Metrics: free_cash_flow (operating CF - CapEx), fcf_margin

### Analyst Estimates
**Endpoint**: `GET /fundamentals/{symbol}/analyst-estimates`
**Status**: ✅ Fully Implemented (November 2, 2025)

Returns all 4 periods: 0q (current quarter), +1q (next quarter), 0y (current year), +1y (next year).

**Response Fields** (24 estimate fields):
- Current Quarter (0q): eps_avg/low/high, revenue_avg/low/high, analyst_count, target_period_date
- Next Quarter (+1q): eps_avg/low/high, revenue_avg/low/high, analyst_count, target_period_date
- Current Year (0y): earnings_avg/low/high, revenue_avg/low/high, analyst_count, end_date
- Next Year (+1y): earnings_avg/low/high, revenue_avg/low/high, analyst_count, end_date

---

## N. Insights / AI-Powered Analysis Endpoints (5 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/insights/generate` | Generate AI insights for portfolio |
| GET | `/insights/portfolio/{portfolio_id}` | List portfolio insights |
| GET | `/insights/{insight_id}` | Get single insight |
| PATCH | `/insights/{insight_id}` | Update insight metadata |
| POST | `/insights/{insight_id}/feedback` | Submit feedback/rating on insight |

---

## O. Onboarding Endpoints (3 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/onboarding/register` | Register new user with invite code |
| POST | `/onboarding/create-portfolio` | Create portfolio with CSV import |
| GET | `/onboarding/csv-template` | Download CSV template |

---

## P. Admin Batch Processing Endpoints (7 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/batch/run` | Trigger batch processing with real-time tracking |
| GET | `/admin/batch/run/current` | Get current batch status (polling endpoint) |
| POST | `/admin/batch/trigger/market-data` | Manually trigger market data update |
| POST | `/admin/batch/trigger/correlations` | Manually trigger correlation calculations |
| POST | `/admin/batch/trigger/company-profiles` | ⚠️ **DEPRECATED** - Now runs automatically via Railway cron |
| GET | `/admin/batch/data-quality` | Get data quality status and metrics |
| POST | `/admin/batch/data-quality/refresh` | Refresh market data for quality improvement |

### Trigger Batch Processing
**Endpoint**: `POST /admin/batch/run`
**Status**: ✅ Fully Implemented
**Authentication**: Required (Admin)

**Concurrent Run Prevention**: Returns 409 Conflict if a batch is already running, unless `force=true` is specified.

**Parameters**:
- `portfolio_id` (query, optional): Specific portfolio UUID or omit for all portfolios
- `force` (query, optional): Set to `true` to force run even if batch already running

**Response**:
```json
{
  "status": "started",
  "batch_run_id": "84728a8c-f7ac-4c72-a7cb-8cdb212198c4",
  "portfolio_id": "all",
  "triggered_by": "admin@sigmasight.com",
  "timestamp": "2025-10-06T13:28:00Z",
  "poll_url": "/api/v1/admin/batch/run/current"
}
```

### Get Current Batch Status
**Endpoint**: `GET /admin/batch/run/current`
**Status**: ✅ Fully Implemented
**Polling Recommendation**: Poll every 2-5 seconds for real-time updates.

**Response** (Running):
```json
{
  "status": "running",
  "batch_run_id": "84728a8c-f7ac-4c72-a7cb-8cdb212198c4",
  "started_at": "2025-10-06T13:28:00Z",
  "elapsed_seconds": 135.2,
  "triggered_by": "admin@sigmasight.com",
  "jobs": {
    "total": 8,
    "completed": 3,
    "failed": 0,
    "pending": 5
  },
  "current_job": "position_factor_analysis_c0510ab8...",
  "current_portfolio": "Demo High Net Worth Portfolio",
  "progress_percent": 37.5
}
```

---

## Q. Admin Fix / Data Operations Endpoints (5 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/fix/clear-calculations` | Clear all calculation results |
| POST | `/admin/fix/seed-portfolios` | Seed demo portfolios |
| POST | `/admin/fix/run-batch` | Run batch processing |
| POST | `/admin/fix/fix-all` | Complete fix workflow (background) |
| GET | `/admin/fix/jobs/{job_id}` | Get fix job status |

---

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All data endpoints require JWT authentication via Bearer token:
```
Authorization: Bearer <jwt_token>
```

---

## Summary Statistics

### Endpoint Count by Category
| Category | Endpoints |
|----------|-----------|
| Authentication | 5 |
| Data | 12+ |
| Portfolio CRUD | 7 |
| Analytics (Portfolio) | 16+ |
| Analytics (Aggregate) | 5 |
| Analytics (Spread Factors) | 1 |
| Chat | 6 |
| Target Prices | 10+ |
| Position Management | 8+ |
| Position Tagging | 5 |
| Tag Management | 7 |
| Equity Changes | 7 |
| Fundamental Data | 4 |
| Insights | 5 |
| Onboarding | 3 |
| Admin Batch | 7 |
| Admin Fix | 5 |
| **Total** | **~129+ endpoints** |

### Technology Stack
- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM
- **AI**: OpenAI Responses API (NOT Chat Completions)
- **Streaming**: Server-Sent Events (SSE) for chat
- **State Management**: In-memory batch run tracker for real-time progress
- **Market Data**: YFinance (primary), FMP (secondary), Polygon (options)

---

## Changelog

### V1.5.0 (December 11, 2025)
- Added Fundamental Data endpoints (4 new: income-statement, balance-sheet, cash-flow, analyst-estimates)
- Added Insights/AI Analysis endpoints (5 new)
- Added Onboarding endpoints (3 new)
- Added Admin Fix endpoints (5 new)
- Added Equity Changes endpoints (7 new)
- Added Analytics Aggregate endpoints (5 new)
- Added Analytics Spread Factors endpoint (1 new)
- Added Portfolio CRUD endpoints (7 new)
- Added Position Management endpoints (8+ new)
- Updated total endpoint count from 57 to 129+
- Comprehensive documentation of all categories

### V1.4.6 (October 4, 2025)
- Initial documented version
- 57 endpoints across 8 categories
- Strategies system removed, position tagging added
