# Target Price API Test Page Integration Plan - REVISED

## Executive Summary
This document outlines the plan to integrate 10 new Target Price management API endpoints into the existing API test page at `frontend/src/app/dev/api-test/page.tsx`, using the authenticated user's actual portfolio and real database data.

## Current State Analysis

### Authentication Flow
- **Login**: Users authenticate via `/login` page with demo credentials
- **Portfolio Resolution**: Each user has ONE portfolio with a deterministic UUID
- **Token Storage**: JWT stored in localStorage as `access_token`
- **User Email**: Stored in localStorage for portfolio resolution

### Existing API Test Page Structure
- **Location**: `frontend/src/app/dev/api-test/page.tsx`
- **Current Issue**: Uses hardcoded portfolio IDs (DEMO_PORTFOLIOS constants)
- **Categories**:
  - Analytics Lookthrough Endpoints (6 endpoints)
  - Raw Data Endpoints (3 endpoints)
- **Features**:
  - Authentication token detection from localStorage
  - Response time tracking
  - Expandable/collapsible data views
  - Custom data preview renderers for different endpoint types
  - Summary statistics (total tests, success/failure counts)

### New Target Price Endpoints to Add
Based on `backend/Summary_For_Ben_09-18-2025.md` and API implementation:

1. **Core Operations**
   - `POST /api/v1/target-prices/{portfolio_id}` - Create target price
   - `GET /api/v1/target-prices/{portfolio_id}` - List portfolio targets
   - `PUT /api/v1/target-prices/{target_id}` - Update target price
   - `DELETE /api/v1/target-prices/{target_id}` - Remove target price

2. **Bulk Operations**
   - `POST /api/v1/target-prices/portfolio/{portfolio_id}/bulk` - Bulk create/update
   - `DELETE /api/v1/target-prices/portfolio/{portfolio_id}` - Clear all targets
   - `POST /api/v1/target-prices/portfolio/{portfolio_id}/import-csv` - CSV import
   - `GET /api/v1/target-prices/portfolio/{portfolio_id}/export-csv` - CSV export

3. **Analytics**
   - `GET /api/v1/target-prices/portfolio/{portfolio_id}/summary` - Portfolio summary
   - `GET /api/v1/target-prices/position/{position_id}` - Position-specific targets

## Implementation Plan

### Phase 1: Using Existing Portfolio Selection (Priority 1)

#### 1.1 Keep Existing Portfolio Selection
```typescript
// KEEP the existing portfolio dropdown and selection mechanism
// The page already has:
const [selectedPortfolio, setSelectedPortfolio] = useState(DEMO_PORTFOLIOS.HIGH_NET_WORTH);

// And the dropdown selector (lines 305-311) with three portfolio options:
// - High Net Worth
// - Individual Investor
// - Hedge Fund

// We'll use this existing selectedPortfolio variable for all target price endpoints
```

#### 1.2 Add Target Price Category Section
```typescript
// Add new section similar to existing Analytics/Raw Data sections
<div className="space-y-2">
  <h3 className="text-lg font-medium text-gray-700 bg-purple-50 px-4 py-2 rounded">
    Target Price Management
  </h3>
  {/* Target price endpoint results */}
</div>
```

#### 1.3 Add GET Endpoints to testEndpoints Array
```typescript
// Add these to the testEndpoints array (using existing selectedPortfolio variable)
{
  name: '🎯 List Portfolio Target Prices',
  endpoint: `/api/proxy/api/v1/target-prices/${selectedPortfolio}`,
  method: 'GET',
  requiresAuth: true,
  category: 'target-prices',
  description: 'All target prices for portfolio with smart price resolution'
},
{
  name: '📊 Target Price Portfolio Summary',
  endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}/summary`,
  method: 'GET',
  requiresAuth: true,
  category: 'target-prices',
  description: 'Portfolio summary with risk metrics and target achievement'
},
{
  name: '📥 Export Target Prices to CSV',
  endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}/export-csv`,
  method: 'GET',
  requiresAuth: true,
  category: 'target-prices',
  description: 'Export all target prices to CSV format'
}
```

#### 1.3 Custom Preview Renderer for Target Price Data
```typescript
// Add to renderDataPreview function
if (endpoint.includes('target-prices')) {
  if (endpoint.includes('summary')) {
    return (
      <div className="space-y-1">
        <div className="text-sm font-semibold">
          Count: {data.total_targets || 0} targets
        </div>
        {data.portfolio_metrics && (
          <div className="text-xs text-gray-600">
            Total Value: ${(data.portfolio_metrics.total_value / 1000000).toFixed(2)}M
          </div>
        )}
      </div>
    );
  }

  if (Array.isArray(data)) {
    return (
      <div className="space-y-1">
        <div className="text-xs">{data.length} target prices</div>
        {data.length > 0 && (
          <div className="text-xs text-gray-600">
            Symbols: {data.slice(0, 3).map(tp => tp.symbol).join(', ')}
            {data.length > 3 && ` ... +${data.length - 3} more`}
          </div>
        )}
      </div>
    );
  }
}
```

### Phase 2: Dynamic Data Operations (Priority 2)

#### 2.1 Fetch Portfolio Positions for Real Data
```typescript
// First fetch the user's actual positions to create target prices for real symbols
const [portfolioPositions, setPortfolioPositions] = useState<any[]>([]);

useEffect(() => {
  const fetchPositions = async () => {
    if (!selectedPortfolio) return;

    const response = await fetch(
      `/api/proxy/api/v1/data/positions/details?portfolio_id=${selectedPortfolio}`,
      {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      }
    );

    if (response.ok) {
      const data = await response.json();
      setPortfolioPositions(data.positions || []);
    }
  };

  fetchPositions();
}, [selectedPortfolio, authToken]);

// Create target price data using EXISTING database fields
const createTargetPriceData = (position: any) => ({
  symbol: position.symbol,
  position_id: position.id, // Link to actual position
  position_type: position.position_type || "LONG",

  // Using the EXISTING target price fields from database schema
  target_price_eoy: position.last_price * 1.1, // 10% upside for EOY
  target_price_next_year: position.last_price * 1.2, // 20% upside for next year
  downside_target_price: position.last_price * 0.9, // 10% downside scenario
  current_price: position.last_price,

  // No conviction_level or investment_class - these don't exist in our schema
});
```

#### 2.2 Add Mutation Endpoints with Real Data
```typescript
// Dynamic endpoints that use actual portfolio data
{
  name: '➕ Create Target Price (First Position)',
  endpoint: `/api/proxy/api/v1/target-prices/${selectedPortfolio}`,
  method: 'POST',
  body: portfolioPositions[0] ? createTargetPriceData(portfolioPositions[0]) : null,
  requiresAuth: true,
  category: 'target-prices-mutations',
  description: 'Create target price for first position in portfolio',
  disabled: !portfolioPositions.length
},
{
  name: '📦 Bulk Create Target Prices (Top 3 Positions)',
  endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}/bulk`,
  method: 'POST',
  body: {
    target_prices: portfolioPositions.slice(0, 3).map(createTargetPriceData)
  },
  requiresAuth: true,
  category: 'target-prices-mutations',
  description: 'Bulk create target prices for top 3 positions',
  disabled: portfolioPositions.length < 3
},
{
  name: '🗑️ Clear All Target Prices',
  endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}`,
  method: 'DELETE',
  requiresAuth: true,
  category: 'target-prices-mutations',
  description: 'Remove all target prices for portfolio'
}
```

#### 2.3 Handle Body Data in Test Execution
```typescript
// Modify runTests function to handle body data
const response = await fetch(test.endpoint, {
  method: test.method,
  headers,
  body: test.body ? JSON.stringify(test.body) : undefined,
});
```

### Phase 3: Advanced Features with Dynamic IDs (Priority 3)

#### 3.1 Target Price ID Management
```typescript
// Store created target price IDs for UPDATE/DELETE testing
const [createdTargetPrices, setCreatedTargetPrices] = useState<any[]>([]);

// After successful POST, capture the created target price
const handleTargetPriceCreated = (response: any) => {
  if (response.id) {
    setCreatedTargetPrices(prev => [...prev, response]);
  }
};

// Dynamic UPDATE endpoint
{
  name: '✏️ Update Target Price (First Created)',
  endpoint: createdTargetPrices[0]
    ? `/api/proxy/api/v1/target-prices/${createdTargetPrices[0].id}`
    : null,
  method: 'PUT',
  body: createdTargetPrices[0] ? {
    ...createdTargetPrices[0],
    target_price: createdTargetPrices[0].target_price * 1.05,
    conviction_level: "HIGH",
    notes: "Updated via API test"
  } : null,
  requiresAuth: true,
  category: 'target-prices-mutations',
  description: 'Update first created target price',
  disabled: !createdTargetPrices.length
},

// Dynamic DELETE endpoint
{
  name: '🗑️ Delete Target Price (First Created)',
  endpoint: createdTargetPrices[0]
    ? `/api/proxy/api/v1/target-prices/${createdTargetPrices[0].id}`
    : null,
  method: 'DELETE',
  requiresAuth: true,
  category: 'target-prices-mutations',
  description: 'Delete first created target price',
  disabled: !createdTargetPrices.length
}
```

#### 3.2 Position-Specific Endpoint Testing
```typescript
// Test position-specific endpoint with actual position IDs
{
  name: '🎯 Get Target Prices by Position',
  endpoint: portfolioPositions[0]
    ? `/api/proxy/api/v1/target-prices/position/${portfolioPositions[0].id}`
    : null,
  method: 'GET',
  requiresAuth: true,
  category: 'target-prices',
  description: 'Get all target prices for specific position',
  disabled: !portfolioPositions.length
}
```

#### 3.3 CSV Import Testing
```typescript
// Generate CSV using EXISTING database field names
const generateCSV = () => {
  // Headers match the schema from TargetPriceImportCSV
  const headers = 'symbol,position_type,target_eoy,target_next_year,downside';
  const rows = portfolioPositions.slice(0, 5).map(pos =>
    `${pos.symbol},LONG,${(pos.last_price * 1.1).toFixed(2)},${(pos.last_price * 1.2).toFixed(2)},${(pos.last_price * 0.9).toFixed(2)}`
  );
  return [headers, ...rows].join('\n');
};

{
  name: '📤 Import Target Prices from CSV',
  endpoint: `/api/proxy/api/v1/target-prices/portfolio/${selectedPortfolio}/import-csv`,
  method: 'POST',
  body: {
    csv_content: generateCSV(),
    update_existing: false // Don't update if exists
  },
  requiresAuth: true,
  category: 'target-prices-mutations',
  description: 'Import target prices via CSV',
  disabled: !portfolioPositions.length
}

## Technical Considerations

### Authentication Requirements
All target price endpoints require authentication via JWT token:
- Token must be present in localStorage as `access_token`
- User must login first at `/login` before testing
- Token included in Authorization header: `Bearer ${token}`

### Error Handling
Expected error scenarios to test:
- 401: No authentication token
- 403: User doesn't own portfolio
- 404: Portfolio/target price not found
- 400: Invalid input data
- 500: Server errors

### Response Schema Validation
Target price responses use our EXISTING database schema:
```typescript
interface TargetPriceResponse {
  id: string;
  portfolio_id: string;
  position_id?: string;
  symbol: string;
  position_type?: string; // LONG, SHORT, LC, LP, SC, SP

  // Target price fields (existing in database)
  target_price_eoy?: number;        // End of year target
  target_price_next_year?: number;  // Next year target
  downside_target_price?: number;   // Downside scenario
  current_price: number;            // Current market price

  // Calculated returns
  expected_return_eoy?: number;
  expected_return_next_year?: number;
  downside_return?: number;

  // Risk metrics
  position_weight?: number;
  contribution_to_portfolio_return?: number;
  contribution_to_portfolio_risk?: number;

  // Metadata
  price_updated_at?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}
```

## UI Enhancement Recommendations

### Visual Improvements
1. **User Context Display**: Show logged-in user email and portfolio ID at the top
2. **Color Coding**: Use purple theme for Target Price section (bg-purple-50)
3. **Icons**: Add appropriate emoji icons for each endpoint
4. **Status Indicators**: Show success/failure with colored badges
5. **Data Formatting**: Format currency values, percentages, dates
6. **Real Data Indicators**: Show when using actual portfolio positions vs placeholders

### Interactive Features
1. **Expandable Details**: Keep existing expand/collapse functionality
2. **Dynamic State Display**: Show count of created target prices, available positions
3. **Refresh Data**: Button to refresh portfolio positions and target prices
4. **Clear Created Items**: Button to clean up test-created target prices
5. **Export Results**: Export test results to JSON/CSV

## Testing Strategy

### Prerequisites
1. **Backend Running**: Ensure backend is running on `localhost:8000`
2. **Database Seeded**: Demo users and portfolios must exist in database
3. **Login Required**: Must authenticate via `/login` page first

### Manual Testing Steps
1. Login at `/login` with demo credentials (e.g., `demo_hnw@sigmasight.com` / `demo12345`)
2. Navigate to `/dev/api-test`
3. Wait for portfolio ID resolution and position loading
4. Run GET endpoints to check existing target prices
5. Create new target prices using actual portfolio positions
6. Test UPDATE operations on created target prices
7. Test bulk operations and CSV import/export
8. Verify data persistence by refreshing and re-running GET operations
9. Clean up test data with DELETE operations

### Expected Results
- GET operations: 200 status with data or empty arrays
- POST operations: 200/201 status with created resource
- PUT operations: 200 status with updated resource
- DELETE operations: 200/204 status with confirmation
- All operations: < 500ms response time (typical)

## Implementation Timeline

### Phase 1: Core Integration (2-3 hours)
- Remove hardcoded portfolio selection dropdown
- Implement dynamic portfolio ID resolution via portfolioResolver
- Add Target Price section to UI with purple theme
- Implement all GET endpoints (list, summary, export)
- Create custom preview renderers for target price data

### Phase 2: Dynamic Operations (2-3 hours)
- Fetch actual portfolio positions for real data
- Implement POST/PUT/DELETE endpoints with dynamic data
- Add target price ID capture and management
- Test bulk operations with actual positions
- Implement CSV import with real portfolio symbols

### Phase 3: Polish & Testing (1-2 hours)
- Add user context display (email, portfolio ID)
- Implement refresh functionality
- Complete end-to-end testing with all endpoints
- Document any discovered issues

## Success Criteria

✅ Authentication uses logged-in user's actual portfolio (no hardcoded IDs)
✅ All 10 target price endpoints visible and functional
✅ Dynamic data from real portfolio positions (no dummy data)
✅ Target price creation uses actual portfolio symbols
✅ UPDATE/DELETE operations work with dynamically created target prices
✅ CSV import/export uses real portfolio data
✅ Custom preview renderers show relevant target price information
✅ Clear visual separation with purple-themed section
✅ User context displayed (email, portfolio ID)
✅ Error handling with meaningful messages
✅ Response time tracking and statistics

## Key Clarifications (Based on Feedback)

### What We're Keeping:
1. **Existing Portfolio Selection**: Using the dropdown already in place with DEMO_PORTFOLIOS
2. **Current Authentication**: Using existing auth token from localStorage
3. **Database Schema**: Using EXISTING fields (target_price_eoy, target_price_next_year, downside_target_price)

### What We're Adding:
1. **To testEndpoints Array**: Adding 10 target price endpoints to the existing array (not creating new APIs)
2. **New UI Section**: Purple-themed "Target Price Management" section
3. **Dynamic Data Fetching**: Getting real positions from selected portfolio for testing

### Database Fields We're Using (EXISTING):
- `target_price_eoy` - End of year target price
- `target_price_next_year` - Next year target price
- `downside_target_price` - Downside scenario price
- `current_price` - Current market price
- `position_type` - LONG, SHORT, LC, LP, SC, SP

### CSV Format (Matching Backend Schema):
- Headers: `symbol,position_type,target_eoy,target_next_year,downside`

## Questions for Clarification

1. **Existing Target Price Data**: Are there already target prices in the database for the demo portfolios, or will we be creating them fresh through the API test page?

2. **Position Selection**: Should we automatically select the first N positions for testing, or provide a UI to select specific positions?

3. **CSV Format**: Is there a specific CSV format already defined in the backend, or should we use the format shown in the test script?

4. **Error Scenarios**: Should we intentionally test error cases (invalid data, missing fields, etc.) or focus on happy path testing?

5. **Cleanup Strategy**: Should test-created target prices be automatically cleaned up, or left for manual inspection?

---

**Document Version**: 2.0 (Revised for Real Data)
**Date**: September 18, 2025
**Author**: Claude Code
**Status**: Updated - Using Real Authentication & Database Data