# Frontend TODO: Portfolio Data Integration

> **Goal**: Connect backend demo portfolio data to frontend portfolio display
> **Backend Data Source**: `/backend/reports/demo-*-portfolio_2025-08-23/portfolio_report.json`
> **API Endpoints**: 9 fully implemented `/api/v1/data/*` endpoints with real data
> **Estimated Timeline**: 8-10 hours total

## 📊 **Current State**

### ✅ **Available Backend Resources**
- **3 Demo Portfolios**: Individual Investor, High Net Worth, Hedge Fund Style
- **JSON Reports**: Complete portfolio data including positions, metrics, calculations
- **Working API Endpoints**: 9 `/data/` endpoints with real data (see `/backend/API_IMPLEMENTATION_STATUS.md`)
- **Sample Data**: Demo Individual Investor Portfolio (ID: `a3209353-9ed5-4885-81e8-d4bbc995f96c`)

### ⚠️ **Current Frontend Issues**
- **Mock Data**: Hardcoded positions and metrics in `/src/app/(app)/portfolio/page.tsx`
- **No API Integration**: No connection to backend services
- **Static Display**: Cannot switch between different portfolios
- **Outdated Data**: Mock positions don't reflect actual portfolio holdings

## 🚀 **Implementation Phases**

### **Phase 1: API Integration Foundation** ⏱️ *~2 hours*

#### ❌ **1.1 Create API Service Layer** 
**Priority**: High | **Complexity**: Medium
```typescript
// File: /src/services/portfolioApi.ts
// Tasks:
- [ ] Create TypeScript interfaces matching backend JSON structure
- [ ] Implement API client using fetch with proper error handling
- [ ] Add loading states and retry mechanisms
- [ ] Create data transformation functions for UI compatibility
- [ ] Add authentication headers if needed

// Example Interface:
interface PortfolioReport {
  version: string;
  metadata: PortfolioMetadata;
  portfolio_info: PortfolioInfo;
  calculation_engines: CalculationEngines;
  positions_summary: PositionsSummary;
}
```

#### ❌ **1.2 Environment Configuration**
**Priority**: High | **Complexity**: Low
```typescript
// File: /src/config/api.ts
// Tasks:
- [ ] Set backend API base URL (http://localhost:8000)
- [ ] Configure CORS settings if needed
- [ ] Add API endpoints mapping constants
- [ ] Create environment-based configuration (dev/prod)

// API Endpoints to integrate:
- GET /api/v1/data/portfolios (list portfolios)
- GET /api/v1/data/portfolio/{id}/complete (full portfolio data)
- GET /api/v1/data/positions/details (position-level details)
- GET /api/v1/data/prices/quotes (real-time quotes - optional)
```

### **Phase 2: Data Models & Types** ⏱️ *~1 hour*

#### ❌ **2.1 TypeScript Interfaces**
**Priority**: High | **Complexity**: Low
```typescript
// File: /src/types/portfolio.ts
// Tasks:
- [ ] Create interfaces matching backend JSON structure
- [ ] Add calculation engines interfaces
- [ ] Define position and market data types
- [ ] Add UI-specific derived types
- [ ] Export all types for reuse across components

// Key Interfaces:
- PortfolioReport (main container)
- CalculationEngines (exposures, factor analysis, etc.)
- PositionData (individual position details)
- MarketQuote (real-time price data)
```

#### ❌ **2.2 Data Transformation Layer**
**Priority**: Medium | **Complexity**: Medium
```typescript
// File: /src/utils/dataTransform.ts
// Tasks:
- [ ] Transform backend portfolio_snapshot to UI metrics
- [ ] Convert position_exposures to summary cards
- [ ] Transform positions to long/short arrays for tables
- [ ] Handle missing/null calculation data gracefully
- [ ] Format currencies, percentages, dates consistently
- [ ] Create utility functions for data validation

// Transform Examples:
- total_value → "298,845.30" → "$298.8K"
- daily_return → "0.000000" → "0.00%"
- position_count → 12 → "12 Positions"
```

### **Phase 3: Portfolio Data Integration** ⏱️ *~3 hours*

#### ❌ **3.1 Replace Mock Data in Portfolio Page**
**Priority**: Critical | **Complexity**: High
```typescript
// File: /src/app/(app)/portfolio/page.tsx
// Tasks:
- [ ] Remove hardcoded portfolioSummaryMetrics array
- [ ] Remove hardcoded longPositions and shortPositions arrays  
- [ ] Add useEffect hooks for data fetching
- [ ] Implement loading states and error boundaries
- [ ] Add portfolio selection state management
- [ ] Handle API errors gracefully with user-friendly messages
- [ ] Add data refresh mechanisms (manual/automatic)

// Current Mock Data to Replace:
- portfolioSummaryMetrics (5 metrics) → Real calculation_engines data
- longPositions (20 positions) → Real positions from /data/positions/details
- shortPositions (6 positions) → Real short positions if any
```

#### ❌ **3.2 Dynamic Portfolio Loading**
**Priority**: High | **Complexity**: Medium  
```typescript
// File: /src/app/(app)/portfolio/page.tsx (updated)
// Tasks:
- [ ] Fetch portfolio list from /api/v1/data/portfolios
- [ ] Load specific portfolio using /api/v1/data/portfolio/{id}/complete
- [ ] Handle portfolio switching with smooth transitions
- [ ] Add URL parameter support (?portfolio=uuid)
- [ ] Persist selected portfolio in localStorage
- [ ] Add breadcrumb/navigation showing current portfolio
- [ ] Show portfolio metadata (name, created date, position count)

// Default Portfolio IDs (from backend reports):
- Individual Investor: a3209353-9ed5-4885-81e8-d4bbc995f96c
- High Net Worth: [ID from backend]
- Hedge Fund Style: [ID from backend]
```

#### ❌ **3.3 Metrics Calculation & Display**
**Priority**: High | **Complexity**: Medium
```typescript
// File: /src/utils/metricsCalculator.ts
// Tasks:
- [ ] Transform portfolio_snapshot to summary metrics
- [ ] Calculate exposures from position_exposures engine
- [ ] Handle unavailable calculation engines gracefully
- [ ] Add metric change indicators (positive/negative)
- [ ] Format large numbers appropriately (1.1M, 567K)
- [ ] Add tooltips explaining each metric

// Mapping Backend → Frontend:
- total_value → Long Exposure card
- gross_exposure → Gross Exposure card  
- net_exposure → Net Exposure card
- daily_pnl → Total P&L card
- position_count → Position summary
```

### **Phase 4: Position Data Integration** ⏱️ *~2 hours*

#### ❌ **4.1 Position Details API Integration**
**Priority**: High | **Complexity**: Medium
```typescript
// File: /src/services/positionsApi.ts
// Tasks:
- [ ] Fetch position data from /api/v1/data/positions/details
- [ ] Transform backend position format to UI table format
- [ ] Separate long and short positions automatically
- [ ] Calculate market values and P&L from current prices
- [ ] Handle missing price data with appropriate fallbacks
- [ ] Add position-level metadata (symbols, quantities, etc.)
- [ ] Sort positions by market value, P&L, or alphabetically

// Position Data Fields:
- symbol, quantity, current_price, market_value
- unrealized_pnl, percent_change, position_type
```

#### ❌ **4.2 Real-time Market Data (Optional)**
**Priority**: Low | **Complexity**: Medium
```typescript
// File: /src/hooks/useMarketData.ts
// Tasks:
- [ ] Integrate /api/v1/data/prices/quotes for live prices
- [ ] Update position market values in real-time
- [ ] Add price change indicators and animations
- [ ] Implement periodic refresh (every 15-30 seconds)
- [ ] Add WebSocket support for real-time updates (future)
- [ ] Handle market closed/delayed data scenarios
- [ ] Add manual refresh button for immediate updates

// Real-time Features:
- Live price updates
- P&L change animations
- Market status indicators
- Last updated timestamps
```

### **Phase 5: Portfolio Selection System** ⏱️ *~2 hours*

#### ❌ **5.1 Portfolio Selector Component**
**Priority**: Medium | **Complexity**: Medium
```typescript
// File: /src/components/PortfolioSelector.tsx
// Tasks:
- [ ] Create dropdown/tabs for 3 demo portfolios
- [ ] Display portfolio metadata (name, value, position count)
- [ ] Add portfolio switching with loading states
- [ ] Style component to match existing UI design
- [ ] Add keyboard navigation support
- [ ] Show selected portfolio prominently
- [ ] Add "last updated" timestamps

// Portfolio Display Format:
- Demo Individual Investor Portfolio ($298.8K, 12 positions)
- Demo High Net Worth Portfolio ($X.XM, XX positions) 
- Demo Hedge Fund Style Portfolio ($X.XM, XX positions)
```

#### ❌ **5.2 URL-based Portfolio Navigation**
**Priority**: Low | **Complexity**: Low
```typescript
// File: /src/hooks/usePortfolioRoute.ts
// Tasks:
- [ ] Support URLs like /portfolio?id=uuid
- [ ] Parse portfolio ID from URL parameters
- [ ] Default to Individual Investor if no ID specified
- [ ] Update URL when portfolio selection changes
- [ ] Add browser back/forward navigation support
- [ ] Share portfolio links (bookmarking)
- [ ] Add route validation for invalid portfolio IDs

// URL Examples:
- /portfolio (default to Individual Investor)
- /portfolio?id=a3209353-9ed5-4885-81e8-d4bbc995f96c
- /portfolio?name=individual-investor (friendly URLs)
```

### **Phase 6: Error Handling & User Experience** ⏱️ *~1 hour*

#### ❌ **6.1 Graceful Degradation**
**Priority**: Medium | **Complexity**: Low
```typescript
// File: /src/components/ErrorBoundary.tsx
// Tasks:
- [ ] Handle missing calculation engines gracefully
- [ ] Show "Calculating..." for unavailable data
- [ ] Display informative error messages
- [ ] Add retry mechanisms for failed API calls
- [ ] Fall back to basic portfolio info when calculations fail
- [ ] Log errors for debugging without breaking UI
- [ ] Add "Report Issue" functionality for persistent errors

// Error Scenarios:
- Backend API unavailable
- Calculation engines not ready
- Network timeouts
- Invalid portfolio IDs
```

#### ❌ **6.2 Loading States & Performance**
**Priority**: Medium | **Complexity**: Low
```typescript
// File: /src/components/LoadingStates.tsx
// Tasks:
- [ ] Add skeleton screens while data loads
- [ ] Implement progressive data loading (metrics first, then positions)
- [ ] Add loading spinners for long operations
- [ ] Create smooth transitions between loading states
- [ ] Add toast notifications for successful operations
- [ ] Implement client-side caching to reduce API calls
- [ ] Add prefetching for likely next portfolio selections

// Loading UX:
- Skeleton cards for metrics
- Table row skeletons for positions
- Shimmer effects during transitions
- Progress indicators for multi-step operations
```

## 🏗️ **Technical Architecture**

### **File Structure (New Files to Create)**
```
frontend/src/
├── services/
│   ├── portfolioApi.ts          # Main API client for portfolios
│   ├── positionsApi.ts          # Position-specific API calls
│   └── marketDataApi.ts         # Real-time price data (optional)
├── types/
│   ├── portfolio.ts             # Portfolio and calculation engine types
│   ├── positions.ts             # Position and market data types
│   └── api.ts                   # API request/response types
├── utils/
│   ├── dataTransform.ts         # Backend → Frontend data transformation
│   ├── formatters.ts            # Currency, percentage, date formatting
│   ├── metricsCalculator.ts     # Derive UI metrics from raw data
│   └── validation.ts            # Data validation utilities
├── hooks/
│   ├── usePortfolioData.ts      # Portfolio data fetching hook
│   ├── useMarketData.ts         # Real-time market data hook (optional)
│   └── usePortfolioRoute.ts     # URL parameter management
├── components/
│   ├── PortfolioSelector.tsx    # Portfolio switcher dropdown/tabs
│   ├── LoadingStates.tsx        # Skeleton screens and spinners
│   └── ErrorBoundary.tsx        # Error handling component
└── config/
    └── api.ts                   # API configuration and endpoints
```

### **Files to Modify**
```
frontend/src/
└── app/(app)/portfolio/page.tsx # Replace mock data with API integration
```

### **Data Flow Architecture**
```
Backend Reports → FastAPI Endpoints → Frontend API Services → 
Data Transformation → React State → UI Components → User Display
```

### **API Integration Points**
- **Authentication**: JWT tokens from `/api/v1/auth/login` (if required)
- **Portfolio List**: `/api/v1/data/portfolios` (returns 3 demo portfolios)
- **Portfolio Details**: `/api/v1/data/portfolio/{id}/complete` (full portfolio data)
- **Position Data**: `/api/v1/data/positions/details` (individual positions)
- **Market Quotes**: `/api/v1/data/prices/quotes` (real-time pricing)

## ✅ **Success Criteria**

### **Phase 1-2 Complete When:**
- [ ] API service layer can fetch all 3 demo portfolios
- [ ] TypeScript interfaces match backend JSON structure exactly
- [ ] Data transformation functions convert backend format to UI format
- [ ] Error handling works for network failures and invalid responses

### **Phase 3-4 Complete When:**
- [ ] Portfolio page displays real data from Individual Investor portfolio
- [ ] All 5 summary metric cards show calculated values from backend
- [ ] Position tables show actual holdings with correct symbols and quantities
- [ ] P&L calculations match backend calculation engine results

### **Phase 5-6 Complete When:**
- [ ] Users can switch between all 3 demo portfolios seamlessly
- [ ] URL parameters work for direct portfolio access
- [ ] Loading states provide smooth user experience
- [ ] Error scenarios are handled gracefully without breaking the UI

### **Final Success Metrics:**
- [ ] **Data Accuracy**: Frontend displays match backend JSON reports exactly
- [ ] **Performance**: Portfolio switching takes <2 seconds
- [ ] **Reliability**: Handles backend unavailability without crashes
- [ ] **Usability**: Clear loading states and error messages
- [ ] **Scalability**: Adding new portfolios requires no frontend changes

## 🚨 **Known Risks & Mitigation**

### **Risk 1: Backend API Changes**
- **Mitigation**: Use TypeScript interfaces to catch breaking changes early
- **Fallback**: Maintain backward compatibility in data transformation layer

### **Risk 2: Slow API Response Times** 
- **Mitigation**: Implement client-side caching and loading states
- **Fallback**: Progressive loading (metrics first, detailed data second)

### **Risk 3: Missing Calculation Data**
- **Mitigation**: Graceful degradation with informative messages
- **Fallback**: Show available data and indicate what's still calculating

### **Risk 4: Network Connectivity Issues**
- **Mitigation**: Retry mechanisms and offline indicators
- **Fallback**: Cache last successful data load for offline viewing

## 🔮 **Future Enhancements (Post-Implementation)**

### **Real-time Features**
- [ ] WebSocket integration for live portfolio updates
- [ ] Push notifications for significant P&L changes
- [ ] Market hours indicators and delayed data warnings

### **Advanced Analytics**
- [ ] Historical performance charts using `/api/v1/data/prices/historical/{id}`
- [ ] Factor exposure visualization from backend factor_analysis
- [ ] Correlation heatmaps between positions
- [ ] Risk metrics dashboard (VaR, CVaR, Greeks)

### **Export & Sharing**
- [ ] PDF portfolio reports using backend report generation
- [ ] CSV export for positions and performance data
- [ ] Portfolio snapshots and sharing links
- [ ] Email reports and alerts

### **Performance Optimizations**
- [ ] Virtual scrolling for large position lists
- [ ] Pagination for historical data
- [ ] Service worker caching for offline capability
- [ ] GraphQL integration for optimized data fetching

---

## 📝 **Development Notes**

### **Backend Dependency**
- Requires backend server running on `http://localhost:8000`
- Depends on `/api/v1/data/*` endpoints (9 confirmed working)
- Uses demo portfolio data from backend reports directory

### **Testing Strategy**
- Unit tests for data transformation functions
- Integration tests for API service layer
- E2E tests for portfolio switching workflow
- Performance tests for large portfolio loading

### **Deployment Considerations**
- Environment variables for API URLs (dev/staging/production)
- CORS configuration for cross-origin requests
- Error monitoring for production API failures
- Analytics tracking for portfolio usage patterns

---

**Last Updated**: 2025-08-31  
**Status**: Planning Phase - Ready to Begin Implementation  
**Next Action**: Start with Phase 1.1 (API Service Layer Creation)