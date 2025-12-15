# Plan: Multi-Portfolio Aggregate Risk Metrics with Equity-Weighted Averages

**Created**: December 14, 2025
**Status**: Phases 1-6 Complete (Core Implementation Done)
**Approach**: Option B - Backend endpoints as single source of truth

## Summary
1. Default to "All Accounts" aggregate view across the application
2. Use backend aggregate endpoints as the single source of truth for all aggregate calculations
3. Refactor Command Center to use backend endpoints (currently does client-side aggregation)
4. Update Risk Metrics page to use backend aggregate endpoints

## Database Migration Required?
**NO** - No Alembic migration needed. All data already exists:
- Portfolio NAV stored in `portfolios.equity_balance` and `portfolio_snapshots.net_asset_value`
- Risk metrics stored in existing tables (factor exposures, correlations, stress tests, etc.)
- Aggregate endpoints just read and combine existing data

---

## Current State Analysis

### Backend Aggregate Endpoints (Existing)
| Endpoint | Status | Used By |
|----------|--------|---------|
| `/aggregate/overview` | ✅ Exists | Command Center (partially) |
| `/aggregate/breakdown` | ✅ Exists | Not used |
| `/aggregate/beta` | ✅ Exists | Not used (CC calculates client-side) |
| `/aggregate/volatility` | ✅ Exists | Not used (CC calculates client-side) |
| `/aggregate/factor-exposures` | ✅ Exists | Not used |

### Backend Aggregate Endpoints (Missing - Need to Add)
| Endpoint | Purpose |
|----------|---------|
| `/aggregate/sector-exposure` | Combined sector allocation vs S&P 500 |
| `/aggregate/concentration` | HHI, top positions across all portfolios |
| `/aggregate/correlation-matrix` | Correlations of top 25 positions |
| `/aggregate/stress-test` | Aggregate scenario impacts |

### Command Center Current Implementation (`useCommandCenterData.ts`)
**Problem**: Does client-side equity-weighted aggregation instead of using backend endpoints
- Lines 550-575: Client-side beta aggregation
- Lines 580-621: Client-side volatility aggregation
- Lines 459-539: Client-side holdings aggregation

**Should be refactored to**: Call backend `/aggregate/*` endpoints

### Risk Metrics Current Implementation (`RiskMetricsContainer.tsx`)
**Problem**: Shows first portfolio's data in aggregate view, not true aggregate
- Hooks use `portfolioId` which always points to a specific portfolio
- No aggregate endpoint integration

---

## Implementation Plan

### Phase 1: Backend - Add 4 Missing Aggregate Endpoints

**File: `backend/app/api/v1/analytics/aggregate.py`**

```python
# Add these endpoints:

@router.get("/sector-exposure")
async def get_aggregate_sector_exposure(...)
    """
    Aggregate sector weights across all portfolios.
    - Combines positions from all portfolios
    - Calculates sector weights relative to total equity
    - Compares to S&P 500 benchmark
    """

@router.get("/concentration")
async def get_aggregate_concentration(...)
    """
    Aggregate concentration metrics across all portfolios.
    - HHI calculated across ALL positions from ALL portfolios
    - Top 3, Top 10 concentration across entire household
    - Effective number of positions
    """

@router.get("/correlation-matrix")
async def get_aggregate_correlation_matrix(...)
    """
    Correlation matrix for largest positions across all portfolios.
    - Select top 25 positions by weight across all portfolios
    - Return pairwise correlations
    """

@router.get("/stress-test")
async def get_aggregate_stress_test(...)
    """
    Aggregate stress test scenarios.
    - Weight each portfolio's scenario impact by equity
    - Return total dollar impact and percentage
    """
```

**File: `backend/app/services/portfolio_aggregation_service.py`**

Add calculation methods:
- `aggregate_sector_exposure()`
- `aggregate_concentration()`
- `aggregate_correlation_matrix()`
- `aggregate_stress_test()`

### Phase 2: Frontend - Add Aggregate API Methods

**File: `frontend/src/services/analyticsApi.ts`**

```typescript
// Add aggregate methods (some already exist in portfolioApi.ts, consolidate here)
getAggregateOverview(): Promise<AggregateOverviewResponse>
getAggregateBeta(): Promise<AggregateBetaResponse>
getAggregateVolatility(): Promise<AggregateVolatilityResponse>
getAggregateFactorExposures(): Promise<AggregateFactorExposuresResponse>
getAggregateSectorExposure(): Promise<AggregateSectorExposureResponse>      // NEW
getAggregateConcentration(): Promise<AggregateConcentrationResponse>        // NEW
getAggregateCorrelationMatrix(): Promise<AggregateCorrelationMatrixResponse> // NEW
getAggregateStressTest(): Promise<AggregateStressTestResponse>              // NEW
```

### Phase 3: Frontend - Add TypeScript Types

**File: `frontend/src/types/analytics.ts`**

Add types for all aggregate endpoint responses matching backend schemas.

### Phase 4: Frontend - Update Risk Metrics Hooks

Update each hook to detect aggregate view and call appropriate endpoint:

**Files to modify:**
- `frontend/src/hooks/useFactorExposures.ts`
- `frontend/src/hooks/useVolatility.ts`
- `frontend/src/hooks/useSectorExposure.ts`
- `frontend/src/hooks/useCorrelationMatrix.ts`
- `frontend/src/hooks/useStressTest.ts`

**Pattern:**
```typescript
const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
const portfolioId = usePortfolioStore(state => state.portfolioId)
const isAggregate = selectedPortfolioId === null

useEffect(() => {
  if (isAggregate) {
    // Call aggregate endpoint
    const data = await analyticsApi.getAggregateFactorExposures()
  } else if (portfolioId) {
    // Call single portfolio endpoint
    const data = await analyticsApi.getPortfolioFactorExposures(portfolioId)
  }
}, [selectedPortfolioId, portfolioId])
```

### Phase 5: Frontend - Update Portfolio Store Default

**File: `frontend/src/stores/portfolioStore.ts`**

Ensure aggregate view (`selectedPortfolioId = null`) is the default:
- Verify `setPortfolios()` does NOT auto-select a portfolio
- Keep `portfolioId` as fallback for backwards compatibility with single-portfolio pages

### Phase 6: Frontend - Update RiskMetricsContainer

**File: `frontend/src/containers/RiskMetricsContainer.tsx`**

- Remove logic that only shows first public portfolio in aggregate view
- Display aggregate metrics from hooks (which now fetch aggregate data)
- Show "All Accounts" header with total NAV
- Keep AccountFilter for switching to individual portfolios

### Phase 7: Frontend - Refactor Command Center to Use Backend Endpoints

**File: `frontend/src/hooks/useCommandCenterData.ts`**

Refactor to use backend aggregate endpoints instead of client-side calculations:

**Current (client-side):**
```typescript
// Lines 550-575: Manual beta aggregation
const betaAccumulator = validSections.reduce(...)
const weightedBeta90d = betaAccumulator.beta90dSum / betaAccumulator.totalWeight
```

**New (backend endpoint):**
```typescript
const aggregateBeta = await analyticsApi.getAggregateBeta()
const aggregateVolatility = await analyticsApi.getAggregateVolatility()
const aggregateFactors = await analyticsApi.getAggregateFactorExposures()
```

**Benefits:**
- Single source of truth (backend)
- Consistent calculations across Command Center and Risk Metrics
- Less client-side complexity
- Easier to maintain and test

---

## Files to Modify

### Backend (3 files)
1. `backend/app/api/v1/analytics/aggregate.py` - Add 4 new endpoints
2. `backend/app/services/portfolio_aggregation_service.py` - Add calculation methods
3. `backend/app/schemas/analytics.py` - Add response schemas (if needed)

### Frontend (9 files)
1. `frontend/src/services/analyticsApi.ts` - Add 8 aggregate API methods
2. `frontend/src/types/analytics.ts` - Add aggregate response types
3. `frontend/src/hooks/useFactorExposures.ts` - Add aggregate support
4. `frontend/src/hooks/useVolatility.ts` - Add aggregate support
5. `frontend/src/hooks/useSectorExposure.ts` - Add aggregate support
6. `frontend/src/hooks/useCorrelationMatrix.ts` - Add aggregate support
7. `frontend/src/hooks/useStressTest.ts` - Add aggregate support
8. `frontend/src/stores/portfolioStore.ts` - Verify default is aggregate view
9. `frontend/src/containers/RiskMetricsContainer.tsx` - Show aggregate data
10. `frontend/src/hooks/useCommandCenterData.ts` - Refactor to use backend endpoints

---

## Equity-Weighted Calculation Formula

For all aggregate metrics:
```
Weight_i = NAV_i / Total_NAV

Aggregate_Metric = Σ(Metric_i × Weight_i)
```

Example with 3 portfolios:
- Portfolio A: $500k NAV, Beta 1.2 → Weight 0.385
- Portfolio B: $300k NAV, Beta 0.8 → Weight 0.231
- Portfolio C: $500k NAV, Beta 1.0 → Weight 0.385
- Total: $1.3M
- Aggregate Beta = (1.2 × 0.385) + (0.8 × 0.231) + (1.0 × 0.385) = 1.03

---

## Implementation Status (December 14, 2025)

### Completed Phases

**Phase 1: Backend Aggregate Endpoints** ✅
- Added `/aggregate/sector-exposure` - equity-weighted sector weights
- Added `/aggregate/concentration` - HHI and top position concentration
- Added `/aggregate/correlation-matrix` - correlations for top 25 positions
- Added `/aggregate/stress-test` - equity-weighted scenario impacts

**Phase 2: Frontend API Methods** ✅
- Added 9 aggregate methods to `analyticsApi.ts`
- All methods follow existing patterns with auth headers

**Phase 3: TypeScript Types** ✅
- Added 9 aggregate response types to `analytics.ts`
- Types match backend response schemas

**Phase 4: Hook Updates** ✅
- Updated `useFactorExposures` - auto-detects aggregate mode
- Updated `useVolatility` - auto-detects aggregate mode
- Updated `useSectorExposure` - auto-detects aggregate mode
- Updated `useCorrelationMatrix` - auto-detects aggregate mode
- Updated `useStressTest` - auto-detects aggregate mode
- Updated `useConcentration` - auto-detects aggregate mode
- All hooks use `selectedPortfolioId === null` to detect aggregate view

**Phase 5: Portfolio Store** ✅
- Verified `selectedPortfolioId` defaults to `null` (aggregate view)
- No changes needed - store already configured correctly

**Phase 6: RiskMetricsContainer** ✅
- Updated to show true aggregate metrics (equity-weighted)
- Added total NAV display in header
- Added "Equity-Weighted Aggregate View" info banner
- Removed per-portfolio sections in aggregate view
- Hooks auto-fetch aggregate data when in aggregate mode

**Phase 7: Command Center Refactor** (Optional - Not Yet Done)
- Would eliminate client-side aggregation in favor of backend endpoints
- Lower priority since Risk Metrics page is the primary aggregate display

---

## Testing Checklist

- [x] Backend: All 9 aggregate endpoints return correct data
- [x] Backend: Equity-weighted calculations match expected values
- [x] Frontend: Risk Metrics shows aggregate data when "All Accounts" selected
- [x] Frontend: Risk Metrics shows single portfolio data when specific portfolio selected
- [ ] Frontend: Command Center uses backend aggregate endpoints (Phase 7 - optional)
- [x] Frontend: Default view is "All Accounts" on login
- [x] Frontend: AccountFilter switches correctly between aggregate and individual views
