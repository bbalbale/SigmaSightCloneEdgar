# API Endpoints Status

**Last Updated**: 2025-09-06  
**Author**: Ben Balbale
**Backend Base URL**: `http://localhost:8000`  
**Frontend Proxy**: `/api/proxy/*` → Backend API

## Summary

- **Total Endpoints Planned**: ~39 endpoints
- **Currently Working**: 12 endpoints (31%)
- **Partially Working**: 3 endpoints (8%)
- **Not Working/TODO**: 24 endpoints (61%)

---

## 1. Authentication Endpoints ✅ WORKING

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/auth/login` | POST | ✅ Working | JWT token generation |
| `/api/v1/auth/logout` | POST | ✅ Working | Session invalidation |
| `/api/v1/auth/refresh` | POST | ✅ Working | Token refresh |
| `/api/v1/auth/me` | GET | ✅ Working | Current user info |

**Usage Example**:
```javascript
// Login
POST /api/v1/auth/login
{
  "email": "demo_hnw@sigmasight.com",
  "password": "demo12345"
}
// Returns: { "access_token": "jwt_token_here", "token_type": "bearer" }
```

---

## 2. Raw Data APIs ✅ MOSTLY WORKING

### Portfolio Data
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/data/portfolio/{id}/complete` | GET | ✅ Working | Full portfolio snapshot with positions |
| `/api/v1/data/portfolio/{id}/data-quality` | GET | ✅ Working | Data completeness metrics |

| `/api/v1/data/portfolio/{id}/summary` | GET | ❌ TODO | Returns stub "Portfolio summary not implemented" |
Elliott: Remove this entirely, and implement /analytics/porfolio/{id}/overview instead


### Position Data  
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/data/positions/details` | GET | ✅ Working | Position details with P&L (P&L varies by portfolio) |
| `/api/v1/data/positions/greeks` | GET | ⚠️ Partial | Returns empty results for non-option positions |
Elliott: Remove entirely. If we want to add in the future, put in /analytics/ namespace

| `/api/v1/data/positions/factor-exposures` | GET | ⚠️ Partial | Returns empty/mock data |
Elliott: Remove entirely in /data/. Reimplement this in /analytics/ namespace

### Market Data
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/data/prices/historical/{id}` | GET | ✅ Working | Historical price data |
Elliott: still fixing the backend batch processing to pull data from FMP and put into the historical price tables
| `/api/v1/data/prices/quotes` | GET | ✅ Working | Real-time market quotes |
Elliott: not actually real-time, it's coming from our database.

| `/api/v1/data/factors/etf-prices` | GET | ✅ Working | Factor ETF prices |
Elliott: still fixing the backend batch processing to pull data from FMP and put into the factor ETF price tables

### Reports
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/data/reports` | GET | ✅ Working | List generated reports |
| `/api/v1/data/reports/{id}` | GET | ✅ Working | Get specific report |
Elliott not sure what this is, need to research is.  Is it for the frontend? or chat? or the report generator?
Ben: this might be a 2nd thing that the portfolio page is trying.
Ben: maybe this was created as a fallback?
---

## 3. Analytics APIs ❌ NOT WORKING

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|

**P0: Portfolio Overview**
| `/api/v1/analytics/portfolio/{id}/overview` | GET | ❌ 404 | Endpoint exists in code but not registered in router |
Elliott: Need to investigate and fix this.  Maybe it is not registered in the router? Maybe the data is not in the database on Ben's side?
Ben: Confirms that the 1st thing it tries is to get this API.
Ben: need Cash balance
Elliott: add Cash balance.  Register with router.

| `/api/v1/analytics/portfolio/{id}/risk-metrics` | GET | ❌ TODO | Not implemented |
| `/api/v1/analytics/portfolio/{id}/performance` | GET | ❌ TODO | Not implemented |

**P1: Factor Exposures**
| `/api/v1/analytics/portfolio/{id}/factor-attribution` | GET | ❌ TODO | Not implemented |
Ben: P1 priority is the factor exposures.  Both position level factor betas and portfolio level factor betas.
Elliott: not sure what this was originally supposed to be.  Look at previous 1.4.4 definitions
Elliott: I think we already calculate portfolio factor betas.
Ben: Create 2 separate API calls: (1) portfolio level factor betas, (2) position level factor betas.
Elliott: related problem is we don't have the factor ETF historical data.  So we need to fix that first.
Elliott: after getting the data, we need to test the calculation engine with the real data.
Elliott: confirm that it's being put in the database
Elliott: then look at how we will implement the API calls (what service level python supports this or do we go straight to the database)
TTD for right now: look at existing 1.4.4 factor exposure specs

| `/api/v1/analytics/portfolio/{id}/var` | GET | ❌ TODO | Not implemented |
| `/api/v1/analytics/portfolio/{id}/stress-test` | GET | ❌ TODO | Not implemented |
| `/api/v1/analytics/portfolio/{id}/optimization` | POST | ❌ TODO | Not implemented |

**P1:  Correlation Matrix API**
Ben: idea is we have 500 stocks (we haven't done this yet) and then create the correlation matrix for those stocks and put in the database.
Ben: then would display portfolio tickers and correlation matrix between those tickers
Elliott: current concept is: pull historical data for every ticker in every data portfolio (not 500 stocks). so we can live with this right now.  later add the proactive pulling of 3000 stocks.
Ben: will display the correlation matrix.  And also a diversification score.
Elliott: did we implementa diversification score already and where is it in the database.
Elliott: create 2 APIs, 1 is a diversification score API call, 1 is a correlation matrix data call. Confirm.
Elliott: what params do you want to have for the API call?


We might be able to use the API Specification 1.4.4 correlation matrix API as a reference.
Get Correlation Matrix
```http
GET /api/v1/analytics/correlation/{portfolio_id}/matrix
```

Returns position correlation matrix.

**Query Parameters**:
- `lookback_days` (integer, default: 90) - number of days to look back for correlation calculation
Elliott: kill this param bc we are using pre-calcuated amounts in the database (60 day based calculation)
- `min_overlap_days` (integer, default: 30)  - minimum number of days of overlap between 2 ticker symbols
Elliott: let's kill this too, but we need to confirm what we're enforcing in the pre-calculation.

Elliott: this assumes there is some kind of realtime calculation but not sure if we support this.
Ben: doesn't have to be perfect.
Elliott: maybe we kill lookback days and just use the default pre-calcuated amounts in the database which would be based on some default (60 days? 90 days?)  Ben: start with 60 trading days.

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

**P1: Diversification Score API**
Elliott: remove average correlation and move to a separate API because we would use that score elsewhere as a card on other pages.

Ben: implement the language around the diversification score in the frontend.  great.







## 4. Market Data Service APIs ❌ NOT WORKING

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/market-data/prices/{symbol}` | GET | ❌ TODO | Individual symbol prices |
| `/api/v1/market-data/batch-prices` | POST | ❌ TODO | Batch price fetching |
| `/api/v1/market-data/options/{symbol}` | GET | ❌ TODO | Options chain data |
| `/api/v1/market-data/fundamentals/{symbol}` | GET | ❌ TODO | Company fundamentals |

---

## 5. Chat/AI Endpoints ⚠️ PARTIAL

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/chat/send` | POST | ⚠️ Mock | Returns hardcoded responses |
| `/api/v1/chat/stream` | POST | ❌ TODO | SSE streaming not implemented |
| `/api/v1/chat/history` | GET | ❌ TODO | Chat history not implemented |
| `/api/v1/chat/clear` | POST | ❌ TODO | Clear chat not implemented |

**Note**: Backend is configured for OpenAI Responses API (not Chat Completions API)

---

## 6. Portfolio Management ❌ NOT WORKING

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/portfolios` | GET | ❌ TODO | List user portfolios |
| `/api/v1/portfolios` | POST | ❌ TODO | Create new portfolio |
| `/api/v1/portfolios/{id}` | PUT | ❌ TODO | Update portfolio |
| `/api/v1/portfolios/{id}` | DELETE | ❌ TODO | Delete portfolio |
| `/api/v1/portfolios/{id}/positions` | POST | ❌ TODO | Add position |
| `/api/v1/portfolios/{id}/positions/{pos_id}` | PUT | ❌ TODO | Update position |
| `/api/v1/portfolios/{id}/positions/{pos_id}` | DELETE | ❌ TODO | Delete position |

---

## 7. Batch Processing ❌ NOT ACCESSIBLE VIA API

| Process | Status | Notes |
|---------|--------|-------|
| Greeks Calculation | ✅ Backend | Runs via batch orchestrator, no API endpoint |
| Factor Exposure | ✅ Backend | Runs via batch orchestrator, no API endpoint |
| Risk Metrics | ✅ Backend | Runs via batch orchestrator, no API endpoint |
| Report Generation | ✅ Backend | Runs via batch orchestrator, no API endpoint |

**Note**: These processes run via `batch_orchestrator_v2.py` but have no direct API access

---

## Known Issues & Limitations

### 1. P&L Data Inconsistency
- **High-Net-Worth Portfolio**: Returns zero P&L (entry_price = current_price in seed data)
- **Hedge Fund Portfolio**: Returns actual P&L values
- **Individual Portfolio**: Limited test data

### 2. Analytics Endpoint Registration
- Analytics endpoints exist in code (`backend/app/api/v1/analytics/`)
- Not properly registered in the main router
- Returns 404 when called

### 3. Mock/Stub Responses
- Many endpoints return TODO stubs or mock data
- Portfolio summary returns "not implemented"
- Chat endpoints return hardcoded responses

### 4. Missing Real-Time Features
- No WebSocket support
- SSE streaming not implemented for chat
- No real-time position updates

---

## Portfolio IDs for Testing

```javascript
const PORTFOLIO_IDS = {
  'individual': '0193e2f7-39b0-7311-90e5-0fb5126528f5',
  'high-net-worth': 'e23ab931-a033-edfe-ed4f-9d02474780b4',
  'hedge-fund': 'fcd71196-e93e-f000-5a74-31a9eead3118'
}
```

---

## Demo Credentials

```javascript
const DEMO_CREDENTIALS = {
  'individual': { 
    email: 'demo_individual@sigmasight.com', 
    password: 'demo12345' 
  },
  'high-net-worth': { 
    email: 'demo_hnw@sigmasight.com', 
    password: 'demo12345' 
  },
  'hedge-fund': { 
    email: 'demo_hedgefundstyle@sigmasight.com', 
    password: 'demo12345' 
  }
}
```

---

## Frontend Integration Status

### Currently Using
- ✅ Authentication (all endpoints)
- ✅ Portfolio complete data (`/api/v1/data/portfolio/{id}/complete`)
- ✅ Position details (`/api/v1/data/positions/details`)
- ⚠️ Chat (mock responses only)

### Not Yet Integrated
- ❌ Analytics endpoints (404 errors)
- ❌ Portfolio management (CRUD operations)
- ❌ Real-time market data
- ❌ Greeks and factor exposures
- ❌ Risk metrics and stress testing

---

## Recommendations for Backend Team

1. **Priority 1 - Fix Analytics Router**
   - Register analytics endpoints in main router
   - These are partially implemented but return 404

2. **Priority 2 - Standardize P&L Data**
   - Update seed data with realistic entry prices
   - Ensure consistent P&L calculations across portfolios

3. **Priority 3 - Complete Portfolio Summary**
   - Replace TODO stub with actual implementation
   - Critical for portfolio overview page

4. **Priority 4 - Implement Chat Streaming**
   - Add SSE support for real-time chat
   - Integrate with OpenAI Responses API

5. **Priority 5 - Portfolio Management**
   - Add CRUD operations for portfolios
   - Enable position management via API

---

## Testing Commands

```bash
# Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo_hnw@sigmasight.com", "password": "demo12345"}'

# Test portfolio data (replace TOKEN)
curl http://localhost:8000/api/v1/data/portfolio/e23ab931-a033-edfe-ed4f-9d02474780b4/complete \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Test positions with P&L
curl "http://localhost:8000/api/v1/data/positions/details?portfolio_id=e23ab931-a033-edfe-ed4f-9d02474780b4" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

*Document generated from frontend investigation and backend API testing on 2025-09-06*