# Team Microservice - Mission

## Objective
Complete the integration of StockFundamentals (SEC EDGAR data) into the main SigmaSight application.

## Current State
- **StockFundamentals repo**: `bbalbalbae/StockFundamentals`
- **StockFundamentals services**: Deployed to Railway, basic functionality working
- **SigmaSight repo**: Main application
- **Integration status**: Services are running but NOT yet integrated into SigmaSight backend/frontend
- **Feature flag**: `EDGAR_ENABLED` exists but integration code not complete

## What's Already Done
- [x] StockFundamentals microservice built and tested
- [x] Railway services deployed (stockfund-api, stockfund-worker, stockfund-db, stockfund-redis)
- [x] Private networking configured (stockfund-api.railway.internal)
- [x] Integration plan documented

## What This Team Must Build

### Phase 1: Backend Integration (SigmaSight repo)
Create these files in the SigmaSight backend:

1. **`backend/app/services/edgar_client.py`**
   - HTTP client to call StockFundamentals API
   - Use `httpx` for async HTTP calls
   - Handle authentication via `STOCKFUND_API_KEY` header
   - Base URL from `STOCKFUND_API_URL` env var
   - Include retry logic and timeout handling

2. **`backend/app/schemas/edgar_fundamentals.py`**
   - Pydantic models matching StockFundamentals API responses
   - Key models: `EdgarFinancials`, `EdgarPeriod`, `EdgarMetric`

3. **`backend/app/api/v1/edgar_fundamentals.py`**
   - Proxy endpoints that call edgar_client
   - Endpoints needed:
     - `GET /api/v1/edgar/health` - health check
     - `GET /api/v1/edgar/financials/{ticker}/periods` - multi-period data
     - `GET /api/v1/edgar/financials/{ticker}` - latest period
     - `POST /api/v1/edgar/financials/refresh/{ticker}` - trigger refresh

4. **Register router** in `backend/app/api/v1/router.py`

5. **Add config** to `backend/app/core/config.py`:
   - `STOCKFUND_API_URL: str`
   - `STOCKFUND_API_KEY: str`
   - `EDGAR_ENABLED: bool = False`

### Phase 2: Frontend Integration (SigmaSight repo)
1. **`frontend/src/services/edgarApi.ts`** - API client
2. **`frontend/src/hooks/useEdgarFundamentals.ts`** - React Query hook
3. **Financials table component** - display EDGAR data
4. **Data source badge** - show "SEC EDGAR" vs "Yahoo Finance"

### Phase 3: Orchestrator (Future - after validation)
- `fundamentals_orchestrator.py` - EDGAR-first with Yahoo fallback
- Admin endpoints for manual refresh
- Cron job configuration

## Definition of Done
- [ ] Backend can call StockFundamentals and return EDGAR data via API
- [ ] Frontend can display EDGAR financials for any ticker
- [ ] Feature flag `EDGAR_ENABLED=true` activates EDGAR endpoints
- [ ] Data source is clearly labeled in UI
- [ ] Error handling when StockFundamentals is unavailable

## Constraints
- Do NOT modify StockFundamentals repo (it's already working)
- Do NOT modify existing Yahoo Finance code yet (EDGAR is additive)
- All changes via pull requests to `feature/microservice-integration` branch
- Follow existing code patterns in SigmaSight repo
- Use `httpx` for HTTP client (async compatible with FastAPI)

## Environment Variables (already configured in Railway)
```
STOCKFUND_API_URL=http://stockfund-api.railway.internal:8000
STOCKFUND_API_KEY=(shared variable in Railway)
EDGAR_ENABLED=false
```

## StockFundamentals API Reference
Base URL: `http://stockfund-api.railway.internal:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/financials/{ticker}/periods` | GET | Multi-period financials |
| `/api/v1/financials/{ticker}` | GET | Latest period |
| `/api/v1/financials/refresh/{ticker}` | POST | Trigger data refresh |

## Key Files to Reference
- `backend/app/services/` - existing service patterns
- `backend/app/api/v1/` - existing endpoint patterns
- `backend/app/schemas/` - existing Pydantic patterns
- `frontend/src/services/` - existing API client patterns
- `frontend/src/hooks/` - existing React Query patterns

## Current Sprint
1. Create `edgar_client.py` with health check working
2. Create basic Pydantic schemas
3. Create `/api/v1/edgar/health` endpoint
4. Test end-to-end: SigmaSight → StockFundamentals → response
