# Missing API Endpoints Diagnosis

**Date**: 2025-10-23
**Branch**: RiskMetricsLocal
**Issue**: Developer reporting 404 errors on risk metrics endpoints

---

## Executive Summary

**CRITICAL FINDING**: All the reported "missing" API endpoints ARE ALREADY IMPLEMENTED in the backend code on the RiskMetricsLocal branch. The 404 errors are NOT due to missing code - they are configuration or environment issues.

---

## Verified Backend Implementation Status

All endpoints exist and are properly implemented:

### ✅ 1. Volatility Metrics
- **Endpoint**: `GET /api/v1/analytics/portfolio/{portfolio_id}/volatility`
- **File**: `backend/app/api/v1/analytics/portfolio.py:566`
- **Status**: IMPLEMENTED
- **Returns**: 21-day and 63-day realized volatility from PortfolioSnapshot table

### ✅ 2. Beta Comparison
- **Endpoint**: `GET /api/v1/analytics/portfolio/{portfolio_id}/beta-comparison`
- **File**: `backend/app/api/v1/analytics/portfolio.py:658`
- **Status**: IMPLEMENTED
- **Returns**: Market beta vs calculated beta for each position

### ✅ 3. Sector Exposure
- **Endpoint**: `GET /api/v1/analytics/portfolio/{portfolio_id}/sector-exposure`
- **File**: `backend/app/api/v1/analytics/portfolio.py:379`
- **Status**: IMPLEMENTED
- **Returns**: Portfolio sector weights vs S&P 500 benchmark

### ✅ 4. Concentration Metrics
- **Endpoint**: `GET /api/v1/analytics/portfolio/{portfolio_id}/concentration`
- **File**: `backend/app/api/v1/analytics/portfolio.py:469`
- **Status**: IMPLEMENTED
- **Returns**: HHI, effective positions, top N concentration

### ✅ 5. Spread Factor Exposures
- **Endpoint**: `GET /api/v1/analytics/portfolio/{portfolio_id}/spread-factors`
- **File**: `backend/app/api/v1/analytics/spread_factors.py:53`
- **Status**: IMPLEMENTED
- **Returns**: 4 spread factors (Growth-Value, Momentum, Size, Quality)

### ✅ 6. Diversification Score
- **Endpoint**: `GET /api/v1/analytics/portfolio/{portfolio_id}/diversification-score`
- **File**: `backend/app/api/v1/analytics/portfolio.py:175`
- **Status**: IMPLEMENTED
- **Returns**: Weighted correlation score from correlation calculations

---

## Frontend Integration Status

All frontend components are already built and integrated:

### ✅ Dashboard Page (`/dashboard`)
- **Component**: `SpreadFactorCards` displaying spread factors
- **Hook**: `useSpreadFactors` fetching from `/spread-factors` endpoint
- **File**: `frontend/src/components/portfolio/SpreadFactorCards.tsx`

### ✅ Risk Metrics Page (`/risk-metrics`)
- **Components**:
  - `VolatilityMetrics` - volatility analysis
  - `MarketBetaComparison` - beta comparison
  - `SectorExposure` - sector exposure
  - `ConcentrationMetrics` - concentration metrics
- **Hooks**:
  - `useVolatility`
  - `useMarketBetas`
  - `useSectorExposure`
  - `useConcentration`
  - `useDiversificationScore`
- **File**: `frontend/src/containers/RiskMetricsContainer.tsx`

### ✅ Services Layer
- **File**: `frontend/src/services/analyticsApi.ts`
- All 6 endpoints have corresponding service methods
- All properly configured in `frontend/src/config/api.ts`

---

## Root Cause Analysis

The 404 errors are likely caused by ONE of these issues:

### 1. Backend Not on RiskMetricsLocal Branch ⚠️ MOST LIKELY
```bash
# Developer's backend might be on wrong branch (main, develop, etc.)
# RiskMetricsLocal branch has all the endpoints
# Other branches may not
```

### 2. Backend Server Not Running
```bash
# Backend process not started
# Frontend trying to connect to localhost:8000 but nothing listening
```

### 3. Router Registration Issue
```bash
# Analytics router not properly included in main router
# Check backend/app/api/v1/router.py line 30
```

### 4. Data Not Calculated (Not a 404, but returns `available: false`)
```bash
# Endpoints work but return available: false
# Batch calculations haven't been run
# This is EXPECTED behavior, not an error
```

### 5. Frontend Environment Configuration
```bash
# Frontend pointing to wrong backend URL
# Docker container using old cached build
```

---

## Diagnostic Steps (Run These First)

### Step 1: Verify Backend Branch
```bash
cd backend
git branch  # Should show: * RiskMetricsLocal
git log --oneline -5  # Check recent commits include risk metrics work
```

**Expected**: Should see commits related to risk metrics, volatility, sector analysis

### Step 2: Verify Backend is Running
```bash
# Check if backend is responding
curl http://localhost:8000/api/v1/auth/login

# Or open in browser:
open http://localhost:8000/docs
```

**Expected**: Should see FastAPI docs with all endpoints listed

### Step 3: Verify Analytics Router is Loaded
```bash
# Check backend startup logs for analytics endpoints
# Look for lines like:
# INFO:     Application startup complete.
# Should list /api/v1/analytics/ routes
```

### Step 4: Test Endpoints Directly with cURL

First, get authentication token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}'
```

Save the `access_token` from response.

Then test each endpoint:
```bash
# Replace {TOKEN} and {PORTFOLIO_ID} with actual values

# Test Volatility
curl "http://localhost:8000/api/v1/analytics/portfolio/{PORTFOLIO_ID}/volatility" \
  -H "Authorization: Bearer {TOKEN}"

# Test Beta Comparison
curl "http://localhost:8000/api/v1/analytics/portfolio/{PORTFOLIO_ID}/beta-comparison" \
  -H "Authorization: Bearer {TOKEN}"

# Test Sector Exposure
curl "http://localhost:8000/api/v1/analytics/portfolio/{PORTFOLIO_ID}/sector-exposure" \
  -H "Authorization: Bearer {TOKEN}"

# Test Concentration
curl "http://localhost:8000/api/v1/analytics/portfolio/{PORTFOLIO_ID}/concentration" \
  -H "Authorization: Bearer {TOKEN}"

# Test Spread Factors
curl "http://localhost:8000/api/v1/analytics/portfolio/{PORTFOLIO_ID}/spread-factors" \
  -H "Authorization: Bearer {TOKEN}"

# Test Diversification Score
curl "http://localhost:8000/api/v1/analytics/portfolio/{PORTFOLIO_ID}/diversification-score" \
  -H "Authorization: Bearer {TOKEN}"
```

### Step 5: Check Frontend Environment
```bash
cd frontend
cat .env.local

# Should show:
# BACKEND_URL=http://localhost:8000
# NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
```

---

## Fix Procedures

### Fix 1: Backend on Wrong Branch (Most Likely)

```bash
cd backend

# Check current branch
git branch

# If not on RiskMetricsLocal, switch to it
git checkout RiskMetricsLocal
git pull origin RiskMetricsLocal

# Restart backend
uv run python run.py
```

**Test**: Try accessing endpoints again from frontend

### Fix 2: Backend Not Running

```bash
cd backend

# Start backend server
uv run python run.py

# Or alternative method:
uvicorn app.main:app --reload --port 8000
```

**Verify**: Open http://localhost:8000/docs and check endpoints are listed

### Fix 3: Data Not Available (Batch Calculations Needed)

If endpoints return `available: false`, run batch calculations:

```bash
cd backend

# Run batch calculations to generate risk metrics data
uv run python scripts/run_batch_calculations.py

# This will populate:
# - PortfolioSnapshot (volatility data)
# - PositionMarketBeta (beta comparison data)
# - FactorExposure (spread factors)
# - Market data cache (sector data)
```

**Note**: This is expected - endpoints are designed to gracefully return `available: false` when data hasn't been calculated yet.

### Fix 4: Frontend Environment/Cache Issue

```bash
cd frontend

# Check environment
cat .env.local

# Should be pointing to local backend:
# BACKEND_URL=http://localhost:8000
# NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1

# If using Docker, rebuild to clear cache:
docker-compose down
docker-compose up -d --build

# If using npm, restart dev server:
# Ctrl+C to stop
npm run dev
```

### Fix 5: Router Registration Issue (Unlikely but Check)

```bash
# Verify analytics router is included
cat backend/app/api/v1/router.py | grep analytics

# Should see line 30:
# api_router.include_router(analytics_router)
```

If missing, this is a code issue and the router needs to be registered.

---

## Expected API Responses

### Successful Response (Data Available)

```json
{
  "available": true,
  "portfolio_id": "uuid-here",
  "calculation_date": "2025-10-23",
  "data": {
    // Endpoint-specific data
  },
  "metadata": {
    // Calculation metadata
  }
}
```

### Graceful Degradation (Data Not Available)

```json
{
  "available": false,
  "portfolio_id": "uuid-here",
  "metadata": {
    "error": "No volatility data available"
  }
}
```

**This is NOT an error** - it's expected behavior when batch calculations haven't run yet.

---

## Verification Checklist

After applying fixes, verify:

- [ ] Backend is on RiskMetricsLocal branch
- [ ] Backend server is running (http://localhost:8000/docs accessible)
- [ ] All 6 endpoints appear in FastAPI docs
- [ ] Can login and get authentication token
- [ ] Each endpoint returns 200 OK (may have `available: false` - that's OK)
- [ ] No actual 404 errors
- [ ] Frontend pages load without errors
- [ ] If `available: false`, batch calculations have been run

---

## Questions for Developer

Before implementing fixes, ask the developer:

1. **What branch is your backend on?**
   ```bash
   cd backend && git branch
   ```

2. **Is your backend running?**
   ```bash
   curl http://localhost:8000/docs
   ```

3. **What's the exact error?**
   - True HTTP 404 Not Found?
   - Or 200 OK with `available: false` in response?
   - Check browser DevTools Network tab for actual response

4. **Can you access ANY `/api/v1/analytics/` endpoints?**
   - Try `/api/v1/analytics/portfolio/{id}/overview`
   - If that works, narrow down the issue

5. **What do backend logs show?**
   - Check terminal running `uv run python run.py`
   - Any errors or warnings?

---

## Contact Points

- **Backend Code**: `backend/app/api/v1/analytics/` (portfolio.py, spread_factors.py)
- **Frontend Code**: `frontend/src/containers/RiskMetricsContainer.tsx`
- **Services**: `frontend/src/services/analyticsApi.ts`
- **API Config**: `frontend/src/config/api.ts`

---

## Conclusion

**All the code exists and is implemented.** The 404 errors are environment/configuration issues, NOT missing features. Most likely the developer's backend is not on the RiskMetricsLocal branch.

Follow the diagnostic steps above to identify the exact issue, then apply the appropriate fix.
