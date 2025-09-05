# Portfolio Page API Mapping

## References
- **Backend API Specifications**: [API_SPECIFICATIONS_V1.4.5.md](/backend/_docs/requirements/API_SPECIFICATIONS_V1.4.5.md)
- **Implementation Status**: [API_IMPLEMENTATION_STATUS.md](/backend/API_IMPLEMENTATION_STATUS.md)

## Overview
This document maps the SigmaSight Portfolio Page UI components to **ACTUAL WORKING BACKEND APIs**. All fictional/placeholder APIs have been removed - only real, implemented endpoints are documented below.

**Status**: Updated to reflect real backend capabilities (19 implemented endpoints)  
**Last Updated**: 2025-09-05

## Page Structure

### 1. Navigation Header
- **Component**: Top navigation with SigmaSight logo (links to home) and theme toggle
- **Features**: Theme persistence via localStorage, navigation link
- **API Requirements**: None (purely UI component)

### 2. Portfolio Header Section
- **Component**: Portfolio header with title and navigation
- **API Endpoint**: `GET /api/v1/data/portfolios` ✅ **IMPLEMENTED**
- **Purpose**: Get portfolio metadata (name, position count, total value)

**Response Structure**:
```json
{
  "data": [
    {
      "id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
      "name": "Demo High Net Worth Investor Portfolio",
      "type": "HNW",
      "created_at": "2025-08-08T12:00:00Z",
      "positions_count": 21,
      "total_value": 1662126.38
    }
  ]
}
```

### 3. Chat Interface
- **Component**: "Ask SigmaSight" chat bar for AI-powered portfolio analysis
- **API Status**: ❌ **NOT IMPLEMENTED**
- **Frontend Status**: Mock responses implemented in V1.1
- **Implementation Plan**: Uses OpenAI Responses API (not Chat Completions)

**Note**: Chat functionality currently uses mock responses. Real backend integration planned for V1.1 with:
- Server-sent events (SSE) for streaming
- HttpOnly cookies for authentication
- OpenAI Responses API integration

### 4. Portfolio Summary Metrics Cards
- **Component**: Five summary metric cards (Long/Short/Gross/Net Exposure, Total P&L)
- **API Endpoint**: `GET /api/v1/analytics/portfolio/{id}/overview` ✅ **IMPLEMENTED**
- **Purpose**: Portfolio exposures, P&L, and position counts for dashboard cards

**Response Structure**:
```json
{
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "total_value": 1662126.38,
  "cash_balance": 83106.32,
  "exposures": {
    "long_exposure": 1579020.06,
    "short_exposure": 0.00,
    "gross_exposure": 1579020.06,
    "net_exposure": 1579020.06,
    "long_percentage": 95.0,
    "short_percentage": 0.0,
    "gross_percentage": 95.0,
    "net_percentage": 95.0
  },
  "pnl": {
    "total_pnl": 125432.18,
    "unrealized_pnl": 98765.43,
    "realized_pnl": 26666.75
  },
  "position_count": {
    "total_positions": 21,
    "long_count": 21,
    "short_count": 0,
    "option_count": 0
  },
  "last_updated": "2025-09-05T15:30:00Z"
}
```

### 5. Filter & Sort Bar
- **Component**: Filter and sort controls for position display
- **API Status**: ❌ **NOT IMPLEMENTED** 
- **Current Implementation**: Frontend-only filtering of position data
- **Data Source**: Client-side filtering of position data from endpoints below

**Note**: No dedicated filter API exists. Filtering is performed client-side on position data received from the position endpoints.

### 6. Long Positions Column (Left Side)
- **Component**: Individual cards for each long position
- **API Endpoint**: `GET /api/v1/data/positions/details?portfolio_id={id}&position_type=LONG` ✅ **IMPLEMENTED**
- **Purpose**: Get detailed position information with P&L calculations

**Response Structure**:
```json
{
  "data": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "symbol": "AAPL",
      "position_type": "LONG",
      "quantity": 100.0,
      "cost_basis": 160.00,
      "current_price": 175.25,
      "market_value": 17525.00,
      "unrealized_pnl": 1525.00,
      "unrealized_pnl_percent": 9.53,
      "day_change": 285.00,
      "day_change_percent": 1.65,
      "created_at": "2025-08-15T10:30:00Z",
      "updated_at": "2025-09-05T15:30:00Z"
    }
  ],
  "summary": {
    "total_positions": 21,
    "total_market_value": 1662126.38,
    "total_unrealized_pnl": 125432.18,
    "total_day_change": -8942.15,
    "long_positions": 15,
    "short_positions": 2,
    "options_positions": 4
  }
}
```

### 7. Short Positions Column (Right Side)
- **Component**: Individual cards for each short position
- **API Endpoint**: `GET /api/v1/data/positions/details?portfolio_id={id}&position_type=SHORT` ✅ **IMPLEMENTED**
- **Purpose**: Same structure as long positions, filtered by position type

**Note**: Uses same endpoint as long positions with `position_type=SHORT` parameter. Response structure is identical to the long positions endpoint above.

### 8. Bottom Navigation
- **Component**: Mobile-style bottom navigation with 5 tabs
- **Features**: Home, History, Risk Analytics, Performance, Tags
- **API Requirements**: None (navigation only)

---

## Available APIs for Additional Features

Based on the backend implementation status, these additional APIs are available:

### Historical Data
- **Endpoint**: `GET /api/v1/data/prices/historical/{symbol}` ✅ **IMPLEMENTED**
- **Purpose**: 292+ days of historical OHLCV data for charts
- **Use Case**: Price charts, historical analysis

### Market Quotes
- **Endpoint**: `GET /api/v1/data/prices/quotes?symbols=AAPL,MSFT` ✅ **IMPLEMENTED**
- **Purpose**: Real-time market quotes with bid/ask, volume
- **Use Case**: Live price updates, market status


---

## Implementation Guide

### Core Portfolio Page APIs (Required)

1. **Portfolio Header**: `GET /api/v1/data/portfolios` ✅
   - Gets portfolio metadata (name, position count, total value)

2. **Summary Cards**: `GET /api/v1/analytics/portfolio/{id}/overview` ✅  
   - Gets exposures, P&L, position counts for the 5 dashboard cards

3. **Position Data**: `GET /api/v1/data/positions/details?portfolio_id={id}` ✅
   - Gets all positions with P&L calculations
   - Filter by `position_type=LONG` or `position_type=SHORT` for columns

### Authentication Required
All data endpoints require JWT authentication:
```bash
Authorization: Bearer <jwt_token>
```

**Demo Credentials**:
- Email: `demo_hnw@sigmasight.com`  
- Password: `demo12345`
- Portfolio ID: `c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e`

### API Base URL
```
http://localhost:8000/api/v1
```

### Frontend Integration Notes
- **Real Data Available**: All 3 core endpoints return real database data
- **Client-side Filtering**: No server-side filtering APIs; filter positions client-side
- **Chat System**: Currently mock responses; V1.1 implementation planned
- **Error Handling**: Standard HTTP status codes with JSON error responses
- **Data Refresh**: Manual refresh recommended; no real-time WebSocket implemented yet

### Next Steps
1. Replace mock data with actual API calls to the 3 core endpoints above
2. Implement JWT authentication flow
3. Add loading states and error handling
4. Consider adding real-time price updates (manual refresh for now)