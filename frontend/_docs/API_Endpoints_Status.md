# API Endpoints Status

**Last Updated**: 2025-09-06  
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

### Position Data  
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/data/positions/details` | GET | ✅ Working | Position details with P&L (P&L varies by portfolio) |
| `/api/v1/data/positions/greeks` | GET | ⚠️ Partial | Returns empty results for non-option positions |
| `/api/v1/data/positions/factor-exposures` | GET | ⚠️ Partial | Returns empty/mock data |

### Market Data
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/data/prices/historical/{id}` | GET | ✅ Working | Historical price data |
| `/api/v1/data/prices/quotes` | GET | ✅ Working | Real-time market quotes |
| `/api/v1/data/factors/etf-prices` | GET | ✅ Working | Factor ETF prices |

### Reports
| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/data/reports` | GET | ✅ Working | List generated reports |
| `/api/v1/data/reports/{id}` | GET | ✅ Working | Get specific report |

---

## 3. Analytics APIs ❌ NOT WORKING

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/v1/analytics/portfolio/{id}/overview` | GET | ❌ 404 | Endpoint exists in code but not registered in router |
| `/api/v1/analytics/portfolio/{id}/risk-metrics` | GET | ❌ TODO | Not implemented |
| `/api/v1/analytics/portfolio/{id}/performance` | GET | ❌ TODO | Not implemented |
| `/api/v1/analytics/portfolio/{id}/factor-attribution` | GET | ❌ TODO | Not implemented |
| `/api/v1/analytics/portfolio/{id}/var` | GET | ❌ TODO | Not implemented |
| `/api/v1/analytics/portfolio/{id}/stress-test` | GET | ❌ TODO | Not implemented |
| `/api/v1/analytics/portfolio/{id}/optimization` | POST | ❌ TODO | Not implemented |

---

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