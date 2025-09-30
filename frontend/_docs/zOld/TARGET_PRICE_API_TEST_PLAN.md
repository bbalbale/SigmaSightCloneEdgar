# Target Price API Test Page Integration Plan - IMPLEMENTATION READY

## Executive Summary
This document outlines the plan to integrate 10 new Target Price management API endpoints into the existing API test page at `frontend/app/dev/api-test/page.tsx`, using the authenticated user's actual portfolio and real database data.

## Current State Analysis (UPDATED: December 18, 2024)

### ✅ COMPLETED FIXES
- **URL Construction**: Fixed analyticsApi.ts URL construction errors for correlation matrix, position factors, and stress test endpoints
- **Dynamic Symbol Fetching**: Prices/Quotes API now dynamically fetches symbols from portfolio positions instead of hardcoded values
- **All Analytics Endpoints Working**: All 11 endpoints currently tested on the page are functional

### Authentication Flow (WORKING)
- **Login**: Users authenticate via `/login` page with demo credentials
- **Portfolio Resolution**: Portfolio ID automatically detected from /auth/me response
- **Token Storage**: JWT stored in localStorage as `access_token`
- **User Email**: Stored in localStorage for portfolio resolution

### Existing API Test Page Structure (CURRENT)
- **Location**: `frontend/app/dev/api-test/page.tsx`
- **Portfolio ID**: Dynamically resolved from authenticated user
- **Categories**:
  - Auth Endpoints (1 endpoint)
  - Data Endpoints (5 endpoints)
  - Analytics Endpoints (5 endpoints)
  - Admin Endpoints (1 endpoint - returns 404 as expected)
- **Features**:
  - Authentication token detection from localStorage
  - Portfolio ID auto-detection via "Detect from /auth/me" button
  - Response time tracking
  - Expandable/collapsible data views
  - Custom data preview renderers for different endpoint types
  - Dynamic symbol fetching for prices/quotes endpoint

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

### Phase 1: Using Dynamic Portfolio ID (Priority 1)

#### 1.1 Use Auto-Detected Portfolio ID
```typescript
// The page NOW dynamically detects portfolio ID from /auth/me
// No hardcoded DEMO_PORTFOLIOS needed anymore

// Current implementation (lines ~700-720):
const detectPortfolioId = async () => {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/proxy/api/v1/auth/me', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await response.json();
  setPortfolioId(data.portfolio_id);
};

// Portfolio ID is stored in state and used for all endpoints
const [portfolioId, setPortfolioId] = useState('');
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

#### 1.3 Add GET Endpoints to Test Function
```typescript
// Add these to the testAPIs function (using dynamic portfolioId)
// Pattern similar to existing endpoints:

const targetPriceEndpoints = [
  {
    key: 'target_prices_list',
    name: 'Target Prices: List',
    url: `/api/proxy/api/v1/target-prices/${portfolioId}`,
    method: 'GET'
  },
  {
    key: 'target_prices_summary',
    name: 'Target Prices: Summary',
    url: `/api/proxy/api/v1/target-prices/portfolio/${portfolioId}/summary`,
    method: 'GET'
  },
  {
    key: 'target_prices_export',
    name: 'Target Prices: Export CSV',
    url: `/api/proxy/api/v1/target-prices/portfolio/${portfolioId}/export-csv`,
    method: 'GET'
  }
];

// Test each endpoint similar to existing pattern:
for (const endpoint of targetPriceEndpoints) {
  try {
    const response = await fetch(endpoint.url, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await response.json();

    setResults(prev => ({
      ...prev,
      [endpoint.key]: {
        status: response.status,
        success: response.ok,
        data: data,
        time: endTime - startTime
      }
    }));
  } catch (error) {
    // Error handling
  }
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
// CURRENT IMPLEMENTATION already fetches positions for symbols!
// See lines ~450-470 in current api-test page:

// Fetch positions to get symbols for prices/quotes
const positionsData = await apiClient.get(
  `/api/v1/data/positions/details?portfolio_id=${pid}&limit=5`,
  { headers: { Authorization: `Bearer ${token}` } }
);

// Extract symbols from positions
const extractedSymbols = positionsData.positions
  .slice(0, 5)
  .map((p: any) => p.symbol)
  .filter((s: any) => s)
  .join(',');

// This can be reused for target price creation

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
// Add POST/PUT/DELETE endpoints to test function
// These will need to be added as separate test buttons since they modify data

const testCreateTargetPrice = async () => {
  // Get first position from existing positions data
  const positionsResponse = await fetch(
    `/api/proxy/api/v1/data/positions/details?portfolio_id=${portfolioId}&limit=1`,
    { headers: { 'Authorization': `Bearer ${token}` } }
  );
  const positionsData = await positionsResponse.json();
  const firstPosition = positionsData.positions[0];

  // Create target price for first position
  const targetPriceData = {
    symbol: firstPosition.symbol,
    position_id: firstPosition.id,
    position_type: firstPosition.position_type || "LONG",
    target_price_eoy: firstPosition.last_price * 1.1,
    target_price_next_year: firstPosition.last_price * 1.2,
    downside_target_price: firstPosition.last_price * 0.9,
    current_price: firstPosition.last_price
  };

  const response = await fetch(
    `/api/proxy/api/v1/target-prices/${portfolioId}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(targetPriceData)
    }
  );

  const data = await response.json();
  // Store created ID for later UPDATE/DELETE tests
  setCreatedTargetPriceId(data.id);
};

// Similar functions for bulk create, update, delete
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
- ✅ Portfolio ID resolution already implemented (auto-detected from /auth/me)
- Add Target Price section to UI with purple theme
- Implement all GET endpoints (list, summary, export)
- Create custom preview renderers for target price data

### Phase 2: Dynamic Operations (2-3 hours)
- ✅ Portfolio positions fetching already implemented for symbols
- Implement POST/PUT/DELETE endpoints with dynamic data
- Add target price ID capture and management
- Test bulk operations with actual positions
- Implement CSV import with real portfolio symbols

### Phase 3: Polish & Testing (1-2 hours)
- ✅ User context already displayed (portfolio ID shown)
- Implement refresh functionality for target prices
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

## Key Clarifications (UPDATED)

### What's Already Working:
1. **Dynamic Portfolio ID**: Auto-detected from /auth/me - no hardcoded IDs
2. **Authentication**: Token from localStorage working perfectly
3. **Dynamic Symbol Fetching**: Already implemented for prices/quotes endpoint

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

## Next Steps for Implementation

### For AI Agent:
1. **Add Target Price Section** to api-test page UI with purple theme
2. **Implement GET Endpoints** in testAPIs function:
   - List target prices: `/api/v1/target-prices/${portfolioId}`
   - Portfolio summary: `/api/v1/target-prices/portfolio/${portfolioId}/summary`
   - Export CSV: `/api/v1/target-prices/portfolio/${portfolioId}/export-csv`
3. **Add Mutation Test Buttons** for:
   - Create single target price (POST)
   - Bulk create (POST)
   - Update target price (PUT)
   - Delete target price (DELETE)
   - Clear all (DELETE)
4. **Implement CSV Import** with dynamic position data
5. **Add Custom Renderers** for target price data display

### Code Location:
- **File**: `frontend/app/dev/api-test/page.tsx`
- **Current Lines**: ~1000 lines total
- **Portfolio ID**: Already in state, auto-detected
- **Positions Fetch**: Already implemented (~lines 450-470)

---

**Document Version**: 3.0 (Updated Post-Implementation)
**Date**: December 18, 2024
**Author**: Claude Code
**Status**: Ready for Target Price API Integration - Core Infrastructure Complete