# Portfolio Page API Mapping

## Overview
This document defines the API requirements for the SigmaSight Portfolio Page components based on the current UI implementation. The page includes theme switching (light/dark mode), chat functionality, and card-based position display.

## Page Structure

### 1. Navigation Header
- **Component**: Top navigation with SigmaSight logo (links to home) and theme toggle
- **Features**: Theme persistence via localStorage, navigation link
- **API Requirements**: None (purely UI component)

### 2. Portfolio Header Section
- **Component**: Portfolio header with title and navigation
- **API Requirements**: 
  - Portfolio metadata (name, total positions count)
  - User permissions for action buttons

```typescript
// API Endpoint: GET /api/v1/portfolio/{id}/metadata
interface PortfolioMetadata {
  id: string
  name: string
  description: string
  totalPositions: number
  lastUpdated: string
  permissions: {
    canBuy: boolean
    canModify: boolean
    canViewReports: boolean
  }
}
```

### 3. Chat Interface
- **Component**: "Ask SigmaSight" chat bar for AI-powered portfolio analysis
- **Layout**: Inline header with full-width input field
- **API Requirements**: AI chat integration

```typescript
// API Endpoint: POST /api/v1/chat/portfolio/{id}/query
interface ChatRequest {
  portfolioId: string
  query: string
  context?: {
    timeframe?: 'daily' | 'weekly' | 'monthly' | 'ytd'
    analysisType?: 'risk' | 'performance' | 'correlation' | 'general'
  }
}

interface ChatResponse {
  response: string
  analysisData?: {
    charts?: any[]
    metrics?: Record<string, any>
    recommendations?: string[]
  }
  sources?: string[]
  timestamp: string
}
```

### 4. Portfolio Summary Metrics Cards
Five summary metric cards displayed horizontally. Based on current implementation:

```typescript
// API Endpoint: GET /api/v1/portfolio/{id}/summary-metrics
interface PortfolioSummaryMetrics {
  longExposure: {
    title: string // "Long Exposure"
    value: string // "1.1M"
    subValue: string // "91.7%"
    description: string // "Notional exposure"
    positive: boolean
  }
  shortExposure: {
    title: string // "Short Exposure"
    value: string // "(567K)"
    subValue: string // "47.3%"
    description: string // "Notional exposure"
    positive: boolean
  }
  grossExposure: {
    title: string // "Gross Exposure"
    value: string // "1.7M"
    subValue: string // "141.7%"
    description: string // "Notional total"
    positive: boolean
  }
  netExposure: {
    title: string // "Net Exposure"
    value: string // "574K"
    subValue: string // "47.8%"
    description: string // "Notional net"
    positive: boolean
  }
  totalPnL: {
    title: string // "Total P&L"
    value: string // "+285,000"
    subValue: string // "23.8%"
    description: string // "Equity: +1,200,000"
    positive: boolean
  }
}
```

### 5. Filter & Sort Bar
- **Component**: Filter and sort controls for position display
- **Features**: Tags, Exposure, Desc sorting options
- **API Requirements**: 

```typescript
// API Endpoint: GET /api/v1/portfolio/{id}/filters
interface FilterOptions {
  availableTags: string[]
  sortOptions: Array<{
    key: string
    label: string
    direction: 'asc' | 'desc'
  }>
  exposureTypes: string[]
}
```

### 6. Long Positions Column (Left Side)
Individual cards for each long position, automatically populated from database positions.

```typescript
// API Endpoint: GET /api/v1/portfolio/{id}/positions?type=long
interface Position {
  id: string
  symbol: string
  companyName: string // "Apple Inc.", "Microsoft Corporation", etc.
  quantity: number
  price: number
  marketValue: number
  pnl: number
  positive: boolean // for P&L color coding
  assetType?: 'stock' | 'option' | 'bond' | 'etf'
  lastUpdated?: string
  
  // Option-specific fields (if applicable)
  optionDetails?: {
    strike: number
    expiration: string
    type: 'call' | 'put'
    impliedVolatility: number
  }
  
  // Additional risk metrics
  riskMetrics?: {
    beta: number
    delta?: number
    gamma?: number
    theta?: number
    vega?: number
  }
}

interface LongPositionsResponse {
  positions: Position[]
  summary: {
    totalCount: number
    totalMarketValue: number
    totalPnL: number
  }
}
```

### 7. Short Positions Column (Right Side)
Individual cards for each short position, similar structure to long positions.

```typescript
// API Endpoint: GET /api/v1/portfolio/{id}/positions?type=short
interface ShortPositionsResponse {
  positions: Position[] // Same Position interface as above
  summary: {
    totalCount: number
    totalMarketValue: number
    totalPnL: number
  }
}
```

### 8. Bottom Navigation
- **Component**: Mobile-style bottom navigation with 5 tabs
- **Features**: Home, History, Risk Analytics, Performance, Tags
- **API Requirements**: None (navigation only)

## Component Architecture

### Current Implementation:
The UI is built with the following components:

1. **ThemeProvider & ThemeToggle**
   - Manages light/dark theme state
   - Persists theme preference in localStorage
   - Applies theme classes throughout the application

2. **ChatInput**
   - Full-width input with theme-aware styling
   - Flexible layout support (centered vs inline)
   - Placeholder text for user guidance

### Card Types Required:

1. **PortfolioSummaryCard** (Implemented)
   - Displays metric title, main value, sub-value, and description
   - Color coding for positive/negative values (emerald/red)
   - Theme-aware backgrounds and text colors
   - Compact grid layout (5 cards per row on desktop)

2. **PositionCard** (Implemented)
   - Displays symbol, company name, market value, P&L
   - Color coding for P&L (emerald for positive, red for negative)
   - Theme-aware styling with hover effects
   - Responsive design with cursor pointer
   - Format numbers with K/M abbreviations

3. **SectionHeader** (Implemented)
   - "Long Positions" and "Short Positions" headers
   - Position counts with badges
   - Theme-aware text and badge colors
   - Consistent styling with chat section header

## Chat Integration Requirements

### AI Chat Backend Integration
The chat bar requires integration with an AI service for portfolio analysis:

```typescript
// Service integration pattern
class PortfolioChatService {
  async sendQuery(portfolioId: string, query: string): Promise<ChatResponse> {
    // Integration with OpenAI, Claude, or custom AI service
    const response = await fetch('/api/v1/chat/portfolio/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ portfolioId, query })
    });
    return response.json();
  }
}
```

### Common Chat Queries to Handle:
- "What are my biggest risks?"
- "How correlated are my positions?"
- "Show me my sector exposure"
- "What's driving my P&L today?"
- "Should I rebalance my portfolio?"

## API Integration Strategy

### Real-time Updates
```typescript
// WebSocket endpoint for real-time price updates
// WS: /api/v1/portfolio/{id}/live-updates
interface LiveUpdate {
  symbol: string
  newPrice: number
  newMarketValue: number
  newPnL: number
  timestamp: string
}
```

### Data Refresh Strategy
1. **Initial Load**: Fetch all data on page load
2. **Periodic Refresh**: Every 30 seconds for prices during market hours
3. **Real-time Updates**: WebSocket for live price feeds (if available)
4. **Manual Refresh**: User-triggered refresh button

### Error Handling
```typescript
interface APIError {
  code: string
  message: string
  details?: any
}

// Handle cases like:
// - Stale data warnings
// - Market closed indicators
// - Missing price data
// - API rate limiting
```

## Database Schema Requirements

### Tables Needed:
1. **portfolios** - Portfolio metadata
2. **positions** - Individual position records  
3. **market_data** - Current and historical prices
4. **portfolio_metrics** - Calculated summary metrics
5. **users** - User permissions and settings
6. **chat_sessions** - Chat history and context
7. **user_preferences** - Theme settings and UI preferences

### Key Relationships:
- Portfolio → Positions (1:many)
- Positions → Market Data (many:1 on symbol)
- Portfolio → Portfolio Metrics (1:1)

## Implementation Priority

### Phase 1: Static Layout ✅ (COMPLETED)
- ✅ Built card components with mock data
- ✅ Implemented responsive layout
- ✅ Added theme switching functionality
- ✅ Integrated chat interface
- ✅ Added navigation and filtering UI

### Phase 2: API Integration (CURRENT PHASE)
- [ ] Implement portfolio summary metrics API
- [ ] Connect position data from database
- [ ] Add AI chat integration
- [ ] Implement filter and sort functionality
- [ ] Add loading states and error handling
- [ ] Connect theme persistence across sessions

### Phase 3: Real-time Features (FUTURE)
- [ ] WebSocket integration for live prices
- [ ] Real-time P&L updates
- [ ] Chat message history
- [ ] Performance optimizations
- [ ] Advanced filtering and search

## Implementation Notes

### Styling & Theming:
- ✅ Theme system implemented with light/dark modes
- ✅ Color coding: Emerald for positive, Red for negative values
- ✅ Cards have hover effects and proper spacing
- ✅ Typography uses consistent sizing (lg for headers, sm for content)
- ✅ Layout is fully responsive

### Data Formatting:
- ✅ Numbers formatted with K/M abbreviations (formatNumber function)
- ✅ Prices formatted with $ symbol (formatPrice function)
- ✅ P&L values show + prefix for positive values
- ✅ Consistent spacing and alignment

### Key Functions to Connect:
```typescript
// These functions need backend data:
const portfolioSummaryMetrics // Replace mock data array
const longPositions // Connect to GET /api/v1/portfolio/{id}/positions?type=long  
const shortPositions // Connect to GET /api/v1/portfolio/{id}/positions?type=short

// Chat functionality:
const handleChatSubmit // Connect to POST /api/v1/chat/portfolio/{id}/query

// Filter functionality:
const handleFilterChange // Connect to position filtering API
const handleSortChange // Connect to position sorting API
```

### Current Mock Data Structure:
The UI currently uses hardcoded mock data that matches the expected API structure. This should be replaced with actual API calls in Phase 2.