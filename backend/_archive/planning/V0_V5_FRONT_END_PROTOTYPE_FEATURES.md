# SigmaSight V5 Prototype Features

> ⚠️ **BACKEND STATUS (2025-08-26 15:25 PST)**: Backend APIs are ready to support frontend development. Raw Data APIs (6/6 endpoints) are 100% complete at `/api/v1/data/` namespace. Frontend can proceed without additional backend work. See [TODO3.md](../../TODO3.md) for full API implementation status.

## 1. Overview
This document describes the features implemented in the SigmaSight V5 prototype (GitHub repository last updated ~5 days ago) that the backend API must support. The prototype is built with Next.js 15.2.4 and demonstrates the core user interface and workflows that will connect to the SigmaSight backend.

## 2. Navigation Structure
The prototype implements a tab-based navigation with the following main sections:

1. Dashboard (Home)
2. Positions
3. Risk Analytics
4. ProForma Analytics (Phase 2)

## 3. Dashboard Features

### 3.1 Exposure Summary Cards
The dashboard displays four key exposure metrics as cards:

1. Long Exposure - Total value of long positions
2. Short Exposure - Total value of short positions
3. Gross Exposure - Sum of absolute values (Long + |Short|)
4. Net Exposure - Net directional exposure (Long - |Short|)
5. Total P&L - Portfolio profit/loss

#### 3.1.1 Required API Support
- GET /api/v1/portfolio - Returns all exposure values
- GET /api/v1/portfolio/exposures - Period-based exposure data

#### 3.1.2 Display Modes
- Notional Exposure - Raw dollar values
- Delta-Adjusted - Options-adjusted exposure

#### 3.1.3 Time Period Filters
- Day
- Week
- Month
- YTD (Year to Date)

### 3.2 Visual Indicators
Each metric includes visual feedback:
- Percentage bars showing relative exposure
- Color coding: Green (healthy), Yellow (warning), Red (danger)
- Trend indicators for period-over-period changes

## 4. Positions Tab Features

### 4.1 Position Display Modes
Three viewing modes controlled by toggle chips:

1. Individual - Each position as a separate row
2. By Type - Grouped by position type with expandable sections
3. By Strategy - Grouped by strategy tags

#### 4.1.1 Position Types
- LONG - Long equity positions
- SHORT - Short equity positions
- LC - Long Call options
- LP - Long Put options
- SC - Short Call options
- SP - Short Put options

### 4.2 Position Table Columns

1. Ticker - Security symbol with expandable price chart
2. Type - Position type (LONG, SHORT, LC, LP, SC, SP)
3. Tags - Both regular tags and strategy tags
4. Quantity - Number of shares/contracts
5. Notional Exposure - Dollar exposure
6. Delta-Adjusted Exposure - Options-adjusted exposure
7. P&L - Profit/loss
8. Expiry Date - For options positions
9. Delta - Option delta
10. Gamma - Option gamma
11. Theta - Option theta
12. Vega - Option vega

### 4.3 Position Grouping Features

#### 4.3.1 By Type Grouping
- Shows summary bar with combined metrics for each type
- Expandable/collapsible sections
- Aggregate Greeks for options groups

#### 4.3.2 By Strategy Grouping
- Groups positions by strategy tags (e.g., "#strategy:pairs-trade")
- Shows net exposure and P&L for the strategy
- Expandable to show individual legs

### 4.4 Tag Management

- Create Tag functionality for grouping positions
- Strategy Tags - Special tags prefixed with "#strategy:"
- Bulk Tagging - Select multiple positions and apply tags
- Visual tag chips with custom colors

#### 4.4.1 Required API Support
- GET /api/v1/positions - List all positions with filtering
- GET /api/v1/positions/grouped - Grouped position data
- GET /api/v1/tags - Tag management
- PUT /api/v1/positions/{id}/tags - Update position tags

## 5. Risk Analytics Tab Features

### 5.1 Current Risk View
Risk Metrics Cards:

1. Portfolio Beta - vs SPY benchmark
2. Annualized Volatility - Standard deviation of returns
3. Position Correlation - Average pairwise correlation
4. Max Drawdown - Peak-to-trough decline

#### 5.1.1 View Filters
- Portfolio (all positions)
- Longs only
- Shorts only

#### 5.1.2 Period Filters
- Daily
- Weekly
- Monthly
- Annual

### 5.2 Factor Exposures
Eight factor exposure cards showing portfolio tilts:

1. Market Beta (SPY)
2. Momentum (MTUM)
3. Value (VTV)
4. Growth (VUG)
5. Quality (QUAL)
6. Size (IWM)
7. Short Interest (Custom)
8. Low Volatility (SPLV)

Each factor shows:
- Exposure value (-1 to +1)
- Visual bar indicator
- Color coding based on magnitude

### 5.3 Scenario Analysis
Stress test scenarios with impact calculations:

#### 5.3.1 Bullish Scenarios
- Market Up 10%
- Oil Up 5%
- Rates Up 0.25%
- DAX Up 10%

#### 5.3.2 Bearish Scenarios
- Market Down 10%
- Oil Down 5%
- Rates Down 0.25%
- DAX Down 10%

Each scenario card shows:
- Dollar impact
- Percentage impact
- Color-coded severity

#### 5.3.3 Required API Support
- GET /api/v1/risk/metrics - Portfolio risk metrics
- GET /api/v1/risk/factors - Factor exposures
- GET /api/v1/risk/greeks - Aggregate Greeks

## 6. ProForma Analytics Tab (Phase 2)

### 6.1 Modeling Session Features

1. Changes Summary - Track all modifications
2. Export Function - Generate trade lists (CSV, JSON, FIX)
3. Before/After Comparison - Visual impact analysis

### 6.2 Analysis Sections

#### 6.2.1 Exposure Impact Analysis
- Shows how trades affect exposures
- Real-time recalculation
- Visual delta indicators

#### 6.2.2 Factor Impact Analysis
- Shows factor exposure changes
- All 8 factors with before/after

#### 6.2.3 Trade Builder
- Single position entry
- Multi-leg strategies (Phase 2)
- Basket trades (Phase 2)

### 6.3 Trade Builder Interface

#### 6.3.1 Single Position Mode
- Ticker input field
- Exposure amount
- Side selector (Long/Short)
- Optional tag field
- "+Add to Model" button

#### 6.3.2 Position Modification
- Adjust existing positions
- Close positions
- Add hedges

#### 6.3.3 Required API Support (Phase 2)
- POST /api/v1/modeling/sessions - Create session
- PUT /api/v1/modeling/sessions/{id}/positions - Update positions
- GET /api/v1/modeling/sessions/{id}/export - Export trades

## 7. Visual Design Patterns

### 7.1 Color Scheme

- Background: Dark theme (#0A0A0A)
- Surface: Dark gray (#1A1A1A)
- Borders: Subtle gray (#2A2A2A)
- Text: White primary, gray secondary
- Accent: Blue (#3B82F6)

### 7.2 Status Colors

- Success: Green (#10B981)
- Warning: Yellow (#F59E0B)
- Danger: Red (#EF4444)
- Info: Blue (#3B82F6)

### 7.3 Interactive Elements

- Hover effects on all clickable elements
- Smooth transitions (150ms)
- Loading states with spinners
- Empty states with helpful messages

### 7.4 Responsive Design

- Mobile-first approach
- Grid layouts that stack on small screens
- Touch-friendly tap targets
- Horizontal scrolling for wide tables

## 8. Data Update Patterns

### 8.1 Real-time Updates

- Price updates for positions
- P&L calculations
- Exposure recalculations
- Greeks updates (mock for demo)

### 8.2 Batch Updates

- Daily batch for risk metrics
- Factor exposures calculation
- Historical snapshots

### 8.3 User-Triggered Updates

- Manual refresh buttons
- Pull-to-refresh on mobile
- Last updated timestamps

## 9. Key UI Components

### 9.1 Summary Cards

- Metric value (large, bold)
- Description text
- Visual indicator (bar/percentage)
- Trend arrow
- Period selector

### 9.2 Data Tables

- Sortable columns
- Expandable rows
- Bulk selection
- Sticky headers
- Horizontal scroll

### 9.3 Forms

- Validated inputs
- Clear error messages
- Loading states
- Success feedback
- Auto-save drafts

### 9.4 Modals

- Confirmation dialogs
- Tag creation
- Position details
- Export options

## 10. Performance Considerations

### 10.1 Optimizations

- Virtualized lists for large datasets
- Debounced search inputs
- Memoized calculations
- Lazy loading for charts

### 10.2 Caching Strategy

- Client-side caching of static data
- Optimistic UI updates
- Background data refresh
- Stale-while-revalidate pattern

## 11. Backend Requirements Summary
~~To support this V5 prototype, the backend must provide:~~

**CURRENT STATUS (2025-08-26 15:25 PST)**: The backend currently provides:

1. ✅ **Portfolio Overview Data** - Raw data APIs complete at `/api/v1/data/portfolios`
2. ✅ **Position Management** - Raw data APIs complete at `/api/v1/data/positions`  
3. ✅ **Risk Calculations** - Raw data APIs complete at `/api/v1/data/risk_metrics`
4. ✅ **Market Data** - Available via batch processing and market data cache
5. ✅ **Batch Processing** - Daily automated updates operational
6. 🚧 **Session Management** - For ProForma modeling (in progress, see TODO3.md)
7. 🚧 **Export Functionality** - Trade list generation (planned)

The API returns data in formats that directly map to the UI components. Frontend developers can proceed with implementation using the Raw Data APIs.
