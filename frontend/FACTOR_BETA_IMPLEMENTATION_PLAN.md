# Factor Beta Cards Implementation Plan

## Executive Summary
This document outlines the implementation plan for adding Factor Beta cards to the portfolio page, displaying risk factor exposures from the backend analytics API. The cards will be placed below the Portfolio Exposure cards and above the Position cards, following the existing design patterns.

## 1. Current State Analysis

### API Endpoints Available
- **Portfolio-level Factor Exposures**: `/api/v1/analytics/portfolio/{id}/factor-exposures`
- **Position-level Factor Exposures**: `/api/v1/analytics/portfolio/{id}/positions/factor-exposures`

### Key Files Involved
- `frontend/app/portfolio/page.tsx` - Main portfolio page component
- `frontend/src/services/analyticsApi.ts` - Analytics API service layer
- `frontend/src/services/portfolioService.ts` - Portfolio data loading orchestration
- `frontend/src/types/analytics.ts` - TypeScript type definitions

### Performance Considerations (From Issue #19)
- **Resolved Issues**:
  - N+1 query problem fixed with batch fetching
  - Database connection pool increased to 20 connections
  - React StrictMode double-rendering handled gracefully
- **Lessons Learned**:
  - Implement proper error boundaries for each API call
  - Use Promise.allSettled() for parallel API calls
  - Ensure AbortController is properly handled for cleanup

## 2. Visual Design & Wireframe

### ASCII Wireframe - Current Layout
```
┌────────────────────────────────────────────────────────────┐
│ Header (SigmaSight Logo)                      [Theme Toggle]│
├────────────────────────────────────────────────────────────┤
│ Portfolio Name                            [Time Period Btns]│
│ Ask SigmaSight: [_________________________]               │
├────────────────────────────────────────────────────────────┤
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│ │Long Exp. │ │Short Exp.│ │Net Exp.  │ │Cash      │ ...   │
│ │$1.6M     │ │$364K     │ │$1.2M     │ │$200K     │       │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├────────────────────────────────────────────────────────────┤
│ Filter & Sort: [Tags] [Exposure] [Desc]                    │
├────────────────────────────────────────────────────────────┤
│ Long Positions (16)          │ Short Positions (0)         │
│ ┌──────────────────────────┐ │ ┌──────────────────────────┐│
│ │AAPL    Apple Inc.   $45K │ │ │(empty)                   ││
│ │MSFT    Microsoft    $38K │ │ └──────────────────────────┘│
│ └──────────────────────────┘ │                             │
├────────────────────────────────────────────────────────────┤
│ Bottom Navigation                                           │
└────────────────────────────────────────────────────────────┘
```

### ASCII Wireframe - New Layout with Factor Betas
```
┌────────────────────────────────────────────────────────────┐
│ Header (SigmaSight Logo)                      [Theme Toggle]│
├────────────────────────────────────────────────────────────┤
│ Portfolio Name                            [Time Period Btns]│
│ Ask SigmaSight: [_________________________]               │
├────────────────────────────────────────────────────────────┤
│ PORTFOLIO EXPOSURES                                        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│ │Long Exp. │ │Short Exp.│ │Net Exp.  │ │Cash      │ ...   │
│ │$1.6M     │ │$364K     │ │$1.2M     │ │$200K     │       │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├────────────────────────────────────────────────────────────┤
│ FACTOR BETAS  ℹ️                                            │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│ │Market    │ │Size      │ │Value     │ │Momentum  │       │
│ │Beta      │ │Beta      │ │Beta      │ │Beta      │       │
│ │🟢 1.15   │ │🔴 -0.32  │ │🟢 0.45   │ │⚪ 0.08   │       │
│ │High      │ │Negative  │ │Moderate  │ │Neutral   │       │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│ │Quality   │ │Volatility│ │Growth    │                    │
│ │Beta      │ │Beta      │ │Beta      │                    │
│ │🟢 0.22   │ │🔴 -0.18  │ │🟢 0.67   │                    │
│ │Low       │ │Low       │ │High      │                    │
│ └──────────┘ └──────────┘ └──────────┘                    │
├────────────────────────────────────────────────────────────┤
│ Filter & Sort: [Tags] [Exposure] [Desc]                    │
├────────────────────────────────────────────────────────────┤
│ PORTFOLIO POSITIONS                                        │
│ Long Positions (16)          │ Short Positions (0)         │
│ ┌──────────────────────────┐ │ ┌──────────────────────────┐│
│ │AAPL    Apple Inc.   $45K │ │ │(empty)                   ││
│ │MSFT    Microsoft    $38K │ │ └──────────────────────────┘│
│ └──────────────────────────┘ │                             │
├────────────────────────────────────────────────────────────┤
│ Bottom Navigation                                           │
└────────────────────────────────────────────────────────────┘
```

## 3. Component Architecture

### 3.1 New Component Structure
```typescript
// components/FactorBetaCard.tsx
interface FactorBetaCardProps {
  factorName: string;
  betaValue: number;
  description?: string;
  theme: 'dark' | 'light';
}

// components/FactorBetaSection.tsx
interface FactorBetaSectionProps {
  factorExposures: PortfolioFactorExposuresResponse | null;
  loading: boolean;
  error: string | null;
  theme: 'dark' | 'light';
}
```

### 3.2 Data Flow
```
portfolioService.ts
    ↓
loadPortfolioData()
    ↓
Promise.allSettled([
  analyticsApi.getOverview(),
  analyticsApi.getPortfolioFactorExposures(), // NEW
  positionApiService.getPositions()
])
    ↓
portfolio/page.tsx
    ↓
<FactorBetaSection />
```

## 4. Implementation Steps

### Phase 1: Backend Integration (1-2 hours)
1. **Update Type Definitions** (`types/analytics.ts`)
   - Ensure `PortfolioFactorExposuresResponse` type is complete
   - Add helper types for factor categorization

2. **Extend Portfolio Service** (`services/portfolioService.ts`)
   ```typescript
   // Add to loadPortfolioData function
   const [overviewResult, positionsResult, factorExposuresResult] = await Promise.allSettled([
     analyticsApi.getOverview(portfolioId),
     apiClient.get(`/api/v1/data/positions/details?portfolio_id=${portfolioId}`),
     analyticsApi.getPortfolioFactorExposures(portfolioId) // NEW
   ]);
   ```

3. **Handle API Errors Gracefully**
   - Use same pattern as positions API error handling
   - Provide fallback empty state if API fails
   - Log errors for debugging

### Phase 2: Component Development (2-3 hours)
1. **Create FactorBetaCard Component**
   ```typescript
   const FactorBetaCard = ({ factorName, betaValue, description, theme }) => {
     const getColorIndicator = (value: number) => {
       if (Math.abs(value) < 0.1) return '⚪'; // Neutral
       return value > 0 ? '🟢' : '🔴';
     };
     
     const getInterpretation = (value: number) => {
       const absValue = Math.abs(value);
       if (absValue < 0.1) return 'Neutral';
       if (absValue < 0.5) return value > 0 ? 'Low' : 'Negative Low';
       if (absValue < 1.0) return value > 0 ? 'Moderate' : 'Negative Moderate';
       return value > 0 ? 'High' : 'Negative High';
     };
     
     // Card rendering logic...
   };
   ```

2. **Create FactorBetaSection Component**
   - Grid layout (responsive: 1 col mobile, 4 cols desktop)
   - Section header with info tooltip
   - Loading skeleton states
   - Error state with retry button

3. **Integrate into Portfolio Page**
   - Add state for factor exposures
   - Place between exposure cards and position cards
   - Apply consistent styling with existing cards

### Phase 3: Error Handling & Performance (1-2 hours)
1. **Implement Retry Logic**
   - Use requestManager pattern from existing code
   - Exponential backoff for failed requests
   - Maximum 3 retry attempts

2. **Add Loading States**
   - Skeleton cards while loading
   - Maintain layout stability during load
   - Progressive enhancement approach

3. **Performance Optimizations**
   - Memoize factor calculations
   - Lazy load factor tooltips
   - Cache factor data for 5 minutes

### Phase 4: Polish & Testing (1 hour)
1. **Visual Polish**
   - Color coding for beta ranges
   - Smooth transitions and animations
   - Responsive design testing
   - Dark/light theme consistency

2. **Testing Checklist**
   - [ ] Test with all 3 portfolio types
   - [ ] Verify error handling when API fails
   - [ ] Check loading states
   - [ ] Validate data accuracy
   - [ ] Test theme switching
   - [ ] Mobile responsiveness
   - [ ] Performance with slow network

## 5. MANDATORY: Lessons from Issue #19 - MUST IMPLEMENT

### 🚨 **These are NOT optional - Issue #19 proved these will break without proper implementation**

#### ✅ **REQUIRED: Prevent N+1 Query Problem**
**What Broke Before:** Positions endpoint made separate DB query for each position (17 positions = 17 queries)
**Solution Already Proven:** Batch fetch all data in single query

**MUST IMPLEMENT FROM START:**
```typescript
// In portfolioService.ts - Use Promise.allSettled, NOT Promise.all
const [overviewResult, positionsResult, factorResult] = await Promise.allSettled([
  analyticsApi.getOverview(portfolioId),
  positionApiService.getPositions(portfolioId),
  analyticsApi.getPortfolioFactorExposures(portfolioId)
]);

// Handle each result independently
const factorData = factorResult.status === 'fulfilled' 
  ? factorResult.value 
  : null;
```

#### ✅ **REQUIRED: Handle React StrictMode Double-Rendering**
**What Broke Before:** StrictMode caused duplicate API calls, exhausting connection pool
**Solution Already Proven:** Proper cleanup and request deduplication

**MUST IMPLEMENT FROM START:**
```typescript
// Request deduplication in apiClient
const pendingRequests = new Map<string, Promise<any>>();

const fetchWithDedup = async (url: string) => {
  if (pendingRequests.has(url)) {
    return pendingRequests.get(url);
  }
  
  const promise = fetch(url).finally(() => {
    pendingRequests.delete(url);
  });
  
  pendingRequests.set(url, promise);
  return promise;
};
```

#### ✅ **REQUIRED: Fix AbortController Signal Reuse**
**What Broke Before:** Retry logic reused aborted signal, causing phantom timeouts
**Solution Already Proven:** Fresh controller for each retry

**MUST IMPLEMENT FROM START:**
```typescript
// DO NOT reuse signal on retry
const fetchWithRetry = async (url: string, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    const controller = new AbortController(); // Fresh controller each time
    
    try {
      const timeout = setTimeout(() => controller.abort(), 10000);
      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(timeout);
      return response;
    } catch (error) {
      if (i === retries - 1) throw error;
      // DO NOT pass original signal to retry
    }
  }
};
```

#### ✅ **REQUIRED: Proper Database Session Usage**
**What Broke Before:** Double context manager `async with db as session`
**Backend Must Implement:** Direct session usage without nesting

---

## 6. Additional Risk Analysis & Mitigation Strategies

### 6.1 New Risks (Not Yet Encountered)

#### 🔴 **CRITICAL: API Response Structure Mismatch**
**What Could Break:**
- Backend returns different JSON structure than expected
- Field names change (e.g., `value` → `beta_value`)
- Nested structure changes (e.g., factors array becomes object)

**Impact:** Complete feature failure, white screen of death

**Mitigation Strategy:**
```typescript
// Add response validation layer
const validateFactorResponse = (data: any): boolean => {
  return data?.factors && Array.isArray(data.factors) &&
         data.factors.every(f => 
           typeof f.name === 'string' && 
           typeof f.value === 'number'
         );
};

// Defensive data access with fallbacks
const factorValue = data?.factors?.[0]?.value ?? 0;
```

**Monitoring:** Add Sentry error tracking for schema mismatches

---

#### 🔴 **CRITICAL: Database Connection Pool Exhaustion**
**What Could Break:**
- Multiple parallel API calls exhaust connection pool
- Happened before with positions endpoint (Issue #19)
- Backend has 20 connections max

**Impact:** API timeouts, data disappears after initial load

**Mitigation Strategy:**
```typescript
// Stagger API calls instead of parallel
const loadFactorData = async () => {
  await loadOverview();
  await delay(100); // Small delay
  await loadFactorExposures();
};

// Or use sequential loading for factor data
const results = [];
for (const endpoint of endpoints) {
  results.push(await fetchWithTimeout(endpoint, 5000));
}
```

---

#### 🟡 **HIGH: Authentication Token Expiry During Session**
**What Could Break:**
- JWT token expires while user viewing page
- Factor API returns 401 Unauthorized
- User sees error instead of data

**Impact:** Factor cards show error state

**Mitigation Strategy:**
```typescript
// Auto-refresh token on 401
const fetchWithAuthRetry = async (url: string) => {
  try {
    return await fetch(url, { headers: getAuthHeader() });
  } catch (error) {
    if (error.status === 401) {
      await refreshAuthToken();
      return await fetch(url, { headers: getAuthHeader() });
    }
    throw error;
  }
};

// Add token expiry check
const isTokenExpired = () => {
  const token = localStorage.getItem('access_token');
  const payload = JSON.parse(atob(token.split('.')[1]));
  return Date.now() >= payload.exp * 1000;
};
```

---

#### 🟡 **HIGH: Batch Calculation Not Run for Portfolio**
**What Could Break:**
- Factor exposures never calculated for portfolio
- API returns 404 or empty data
- New portfolios without batch runs

**Impact:** No factor data to display

**Mitigation Strategy:**
```typescript
// Check calculation status first
const checkCalculationStatus = async (portfolioId: string) => {
  const status = await apiClient.get(
    `/api/v1/data/portfolio/${portfolioId}/data-quality`
  );
  return status.factor_calculations_complete;
};

// Show appropriate message
if (!calculationStatus) {
  return (
    <Card>
      <CardContent>
        <Alert>
          Factor calculations pending. Data will appear after next batch run (runs daily at 4:05 PM ET).
        </Alert>
      </CardContent>
    </Card>
  );
}
```

---

#### 🟡 **HIGH: Race Condition with Portfolio ID Resolution**
**What Could Break:**
- Portfolio ID not resolved before factor API call
- Calls API with undefined/null portfolio ID
- GET request to `/api/v1/analytics/portfolio/undefined/factor-exposures`

**Impact:** 404 errors, no data loads

**Mitigation Strategy:**
```typescript
// Guard against undefined portfolio ID
const loadFactorExposures = async (portfolioId: string | null) => {
  if (!portfolioId) {
    console.warn('Portfolio ID not available yet');
    return null;
  }
  
  // Validate UUID format
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(portfolioId)) {
    throw new Error(`Invalid portfolio ID format: ${portfolioId}`);
  }
  
  return await analyticsApi.getPortfolioFactorExposures(portfolioId);
};
```

---

### 5.2 Performance & UX Risks

#### 🟠 **MEDIUM: Slow API Response Times**
**What Could Break:**
- Factor calculations take 5-10 seconds
- User sees loading skeleton for too long
- Other parts of page blocked

**Impact:** Poor user experience, perceived slowness

**Mitigation Strategy:**
```typescript
// Progressive loading with timeout
const FACTOR_TIMEOUT = 3000; // 3 seconds max

const loadWithTimeout = Promise.race([
  analyticsApi.getPortfolioFactorExposures(portfolioId),
  new Promise((_, reject) => 
    setTimeout(() => reject(new Error('Timeout')), FACTOR_TIMEOUT)
  )
]);

// Show partial UI immediately
return (
  <>
    <ExposureCards data={exposureData} /> {/* Shows immediately */}
    <FactorBetaSection 
      data={factorData} 
      loading={factorLoading}
      showSkeleton={true} 
    />
  </>
);
```

---

#### 🟠 **MEDIUM: Memory Leaks from Abandoned Requests**
**What Could Break:**
- User navigates away during API call
- AbortController not properly cleaned up
- Memory accumulates over time

**Impact:** Browser slowdown, eventual crash

**Mitigation Strategy:**
```typescript
useEffect(() => {
  const controller = new AbortController();
  let mounted = true;
  
  const loadData = async () => {
    try {
      const data = await fetch(url, { signal: controller.signal });
      if (mounted) {
        setFactorData(data);
      }
    } catch (error) {
      if (error.name !== 'AbortError' && mounted) {
        setError(error);
      }
    }
  };
  
  loadData();
  
  return () => {
    mounted = false;
    controller.abort();
  };
}, [portfolioId]);
```

---

### 5.3 Data Integrity Risks

#### 🟠 **MEDIUM: Stale Factor Data**
**What Could Break:**
- Factor calculations from yesterday
- Market moved significantly today
- User expects real-time data

**Impact:** Misleading risk metrics

**Mitigation Strategy:**
```typescript
// Show calculation timestamp
<Card>
  <CardHeader>
    <CardTitle>Factor Betas</CardTitle>
    <CardDescription>
      As of {formatDate(data.calculation_date)} 4:00 PM ET
      {isStale(data.calculation_date) && (
        <Badge variant="warning">Stale Data</Badge>
      )}
    </CardDescription>
  </CardHeader>
</Card>

// Define staleness
const isStale = (date: string) => {
  const calcDate = new Date(date);
  const now = new Date();
  const hoursDiff = (now - calcDate) / (1000 * 60 * 60);
  return hoursDiff > 24;
};
```

---

#### 🟠 **MEDIUM: Inconsistent Factor Values Across Pages**
**What Could Break:**
- Different endpoints return different factor values
- Position-level vs portfolio-level aggregation mismatch
- Rounding differences

**Impact:** User confusion, trust issues

**Mitigation Strategy:**
```typescript
// Single source of truth
const factorDataStore = createStore({
  portfolioFactors: null,
  positionFactors: null,
  lastUpdated: null,
  
  // Ensure consistency
  getFactorValue: (factorName: string) => {
    // Always use portfolio-level as source of truth
    return portfolioFactors?.find(f => f.name === factorName)?.value;
  }
});
```

---

### 5.4 Edge Cases & Browser Issues

#### 🟢 **LOW: Browser Compatibility Issues**
**What Could Break:**
- CSS Grid not supported in IE11
- Promise.allSettled not available
- AbortController not supported

**Impact:** Layout broken, features don't work

**Mitigation Strategy:**
```typescript
// Polyfills in app entry point
import 'core-js/features/promise/all-settled';
import 'abortcontroller-polyfill/dist/polyfill-patch-fetch';

// CSS fallbacks
.factor-grid {
  display: flex; /* Fallback */
  flex-wrap: wrap;
  display: grid; /* Progressive enhancement */
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}
```

---

#### 🟢 **LOW: Extreme Beta Values**
**What Could Break:**
- Beta value of 999 or -999
- NaN or Infinity values
- Text overflow in cards

**Impact:** UI breaks, cards misaligned

**Mitigation Strategy:**
```typescript
// Sanitize and cap values
const sanitizeBeta = (value: any): number => {
  const num = parseFloat(value);
  if (isNaN(num)) return 0;
  if (!isFinite(num)) return 0;
  // Cap at reasonable range
  return Math.max(-10, Math.min(10, num));
};

// Format with overflow handling
const formatBeta = (value: number): string => {
  if (Math.abs(value) > 99) {
    return value > 0 ? '>99' : '<-99';
  }
  return value.toFixed(2);
};
```

---

### 5.5 Deployment & Integration Risks

#### 🔴 **CRITICAL: Backend API Not Deployed**
**What Could Break:**
- Frontend deployed but backend endpoints don't exist
- API returns 404 for factor endpoints
- Version mismatch between frontend/backend

**Impact:** Complete feature failure in production

**Mitigation Strategy:**
```typescript
// Feature flag for gradual rollout
const FACTOR_BETAS_ENABLED = process.env.NEXT_PUBLIC_FACTOR_BETAS_ENABLED === 'true';

if (!FACTOR_BETAS_ENABLED) {
  return null; // Don't show section at all
}

// API version checking
const checkApiVersion = async () => {
  const health = await apiClient.get('/api/v1/admin/health');
  return health.version >= '1.2.0'; // Minimum version for factors
};
```

---

### 5.6 Testing Strategy to Prevent Breakage

#### Pre-Deployment Checklist
```typescript
// Test scenarios that MUST pass
const criticalTests = [
  'Load factors for all 3 portfolio types',
  'Handle API timeout gracefully',
  'Handle 401 unauthorized',
  'Handle empty factor data',
  'Handle malformed response',
  'Verify no memory leaks',
  'Test with slow 3G network',
  'Test with backend down',
  'Test token expiry during session',
  'Test rapid portfolio switching'
];
```

#### Monitoring & Alerts
```typescript
// Add telemetry
const trackFactorLoad = (success: boolean, duration: number, error?: string) => {
  analytics.track('factor_beta_load', {
    success,
    duration,
    error,
    portfolio_type: portfolioType,
    factor_count: factorData?.length || 0
  });
  
  // Alert on high failure rate
  if (!success) {
    Sentry.captureException(new Error(`Factor load failed: ${error}`));
  }
};
```

---

### 5.7 Rollback Strategy

If critical issues discovered post-deployment:

1. **Immediate:** Feature flag to disable factor cards
2. **Quick Fix:** Return empty array from API (keeps UI stable)
3. **Full Rollback:** Revert frontend deployment
4. **Data Fix:** Clear corrupted factor calculations, re-run batch

## 6. Factor Interpretation Guide

### Beta Value Ranges
- **High Positive** (> 1.0): Strong positive correlation
- **Moderate Positive** (0.5 - 1.0): Moderate positive correlation
- **Low Positive** (0.1 - 0.5): Weak positive correlation
- **Neutral** (-0.1 - 0.1): No significant correlation
- **Low Negative** (-0.5 - -0.1): Weak negative correlation
- **Moderate Negative** (-1.0 - -0.5): Moderate negative correlation
- **High Negative** (< -1.0): Strong negative correlation

### Standard Factors (7 Active)
1. **Market Beta** - Overall market exposure
2. **Size Beta** - Small vs Large cap exposure
3. **Value Beta** - Value vs Growth exposure
4. **Momentum Beta** - Momentum factor exposure
5. **Quality Beta** - Quality factor exposure
6. **Volatility Beta** - Low volatility factor exposure
7. **Growth Beta** - Growth factor exposure

## 7. Success Criteria

### Functional Requirements
- ✅ Factor beta cards display for all portfolios
- ✅ Data pulls from backend analytics API
- ✅ Error states handled gracefully
- ✅ Loading states show appropriately
- ✅ Responsive design works on all screen sizes

### Performance Requirements
- ✅ Factor data loads within 2 seconds
- ✅ No blocking of other page elements
- ✅ Smooth animations and transitions
- ✅ Memory usage stays within bounds

### User Experience
- ✅ Clear visual hierarchy maintained
- ✅ Consistent with existing design language
- ✅ Intuitive interpretation of beta values
- ✅ Helpful tooltips for factor explanations

## 8. Future Enhancements

### Phase 2 Considerations
- Interactive factor charts showing historical trends
- Drill-down to position-level factor contributions
- Factor attribution analysis
- Custom factor definitions
- Export factor data to CSV/PDF

## 9. Technical Notes

### API Response Structure
```json
{
  "portfolio_id": "uuid",
  "calculation_date": "2025-09-12",
  "factors": [
    {
      "name": "Market Beta",
      "value": 1.15,
      "dollar_exposure": 1840000,
      "contribution_to_risk": 0.42
    }
  ],
  "metadata": {
    "completeness": "complete",
    "missing_factors": [],
    "calculation_method": "regression"
  }
}
```

### Component Props Flow
```
portfolio/page.tsx
  ├── factorExposures (state)
  ├── loadingFactors (state)
  └── factorError (state)
      └── <FactorBetaSection
            factorExposures={factorExposures}
            loading={loadingFactors}
            error={factorError}
            theme={theme}
          />
            └── <FactorBetaCard /> (mapped for each factor)
```

## 10. Estimated Timeline

- **Total Estimated Time**: 5-8 hours
- **Phase 1 (Backend)**: 1-2 hours
- **Phase 2 (Components)**: 2-3 hours
- **Phase 3 (Error/Perf)**: 1-2 hours
- **Phase 4 (Polish)**: 1 hour

## Appendix A: Color Scheme

### Light Theme
- Positive Beta: `text-emerald-600`, `bg-emerald-50`
- Negative Beta: `text-red-600`, `bg-red-50`
- Neutral Beta: `text-gray-600`, `bg-gray-50`

### Dark Theme
- Positive Beta: `text-emerald-400`, `bg-emerald-900/20`
- Negative Beta: `text-red-400`, `bg-red-900/20`
- Neutral Beta: `text-slate-400`, `bg-slate-800`

## Appendix B: Error Messages

- **API Timeout**: "Factor data is temporarily unavailable. Showing cached values."
- **No Data**: "Factor exposures not yet calculated for this portfolio."
- **Partial Data**: "Some factors unavailable. Showing {n} of 7 factors."
- **Network Error**: "Unable to load factor data. Please check your connection."

---

**Document Version**: 1.0
**Created**: 2025-09-12
**Author**: Implementation Planning System