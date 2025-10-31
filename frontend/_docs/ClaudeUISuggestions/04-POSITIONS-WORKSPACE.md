# Positions Workspace - Unified Position Management

**Document Version**: 1.0
**Last Updated**: October 30, 2025
**Status**: Detailed Specification
**Replaces**: Dashboard, Portfolio Holdings, Public Positions, Private Positions

---

## Overview

The **Positions Workspace** consolidates 4 separate pages (Dashboard positions, Portfolio Holdings, Public Positions, Private Positions) into a single unified view with tabbed navigation. This eliminates redundancy and context-switching while providing comprehensive position management capabilities.

### Key Improvements

**Current Pain Points**:
- 4 different pages show position data (fragmented)
- Users confused about "where do I see my holdings?"
- Context-switching required to view long vs short vs options

**New Solution**:
- Single workspace with tabs: All | Long | Short | Options | Private
- Unified filters (tag, sector, P&L, search)
- Side panel for position details (no page navigation)
- Inline actions (Analyze, Tag, AI Explain)
- Multi-select for bulk operations

---

## Layout Specification

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Positions                                                     [User] [AI]│
│ ─────────                                                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│ [All] [Long] [Short] [Options] [Private]                                │
│ ═══                                                                      │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────┐   │
│ │ [🔍 Search...]  [Tag ▼]  [Sector ▼]  [P/L ▼]  [View: Cards ▼]  │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ Summary: 63 positions │ $500,000 total │ +$24,500 P&L (+5.1%)           │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────┐   │
│ │ ☑ NVDA │ NVIDIA Corp │ $88,000 │ +$12,000 (+15.8%) │ [Actions ▼]│   │
│ │   200 shares @ $440.00 │ Long │ Tech │ Core, Growth                │   │
│ │   [Analyze Risk] [Tag] [Target Price] [AI Explain]              │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ ┌──────────────────────────────────────────────────────────────────┐   │
│ │ ☐ TSLA │ Tesla Inc │ $40,000 │ -$2,100 (-5.2%) │ [Actions ▼]    │   │
│ │   100 shares @ $400.00 │ Short │ Auto │ Hedge                   │   │
│ │   [Analyze Risk] [Tag] [Target Price] [AI Explain]              │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ ... (more positions)                                                     │
│                                                                          │
│ [Bulk Actions: □ Tag Selected  □ Export CSV  □ Analyze as Group]        │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Tab Navigation

**Tabs**: All | Long | Short | Options | Private

**Filtering Logic**:
- **All**: Shows all positions (default)
- **Long**: `position_type IN ('LONG')`, excludes options/private
- **Short**: `position_type IN ('SHORT')`
- **Options**: `position_type IN ('LC', 'LP', 'SC', 'SP')` (Long Call, Long Put, Short Call, Short Put)
- **Private**: `investment_class = 'PRIVATE'`

**URL Pattern**: `/positions/long`, `/positions/options`, etc.

---

### 2. Filters & Search

**Search Bar**:
- Search by symbol, company name, tags
- Real-time filtering (debounced 300ms)

**Filter Dropdowns**:
1. **By Tag**: Show all tags, multi-select
2. **By Sector**: Technology, Healthcare, Financials, etc.
3. **By P&L**: Gainers (>0%), Losers (<0%), All
4. **By Size**: Large (>$50K), Medium ($10K-$50K), Small (<$10K)

**View Toggle**:
- Cards (default, visual, good for <50 positions)
- Table (compact, good for >50 positions)

---

### 3. Position Cards

**Card Layout**:
```
┌────────────────────────────────────────────────────────────────┐
│ ☑ NVDA │ NVIDIA Corporation                      [Actions ▼]  │
│ ──────────────────────────────────────────────────────────────  │
│ Market Value: $88,000  │  P&L: +$12,000 (+15.8%)  │  🟢        │
│ Quantity: 200 shares   │  Avg Cost: $380.00       │            │
│ Current Price: $440.00 │  Long │ Technology │ Beta: 1.85       │
│ Tags: [Core] [Growth]  │  Target Price: $500 (↑ 13.6%)         │
│                                                                 │
│ [Analyze Risk] [Edit Tags] [Set Target Price] [AI Explain]     │
└────────────────────────────────────────────────────────────────┘
```

**Quick Actions**:
- **Analyze Risk**: Opens side panel with risk metrics
- **Edit Tags**: Modal to add/remove tags
- **Set Target Price**: Modal to set/edit target price
- **AI Explain**: Opens AI sidebar with position analysis

---

### 4. Side Panel (Position Details)

**Trigger**: Click anywhere on position card (except action buttons)

**Layout**:
```
┌────────────────────────────────┬────────────────────────────────┐
│ Positions List                 │ NVDA - Position Details   [×]  │
│ ...                            │ ──────────────────────────────  │
│                                │ OVERVIEW                        │
│                                │ 200 shares @ $440.00            │
│                                │ Market Value: $88,000           │
│                                │ Avg Cost: $380.00               │
│                                │ Unrealized P&L: +$12,000 (15.8%)│
│                                │                                 │
│                                │ RISK METRICS                    │
│                                │ Beta: 1.85  Volatility: 32%     │
│                                │ Sector: Technology              │
│                                │ Factor Exposures:               │
│                                │ • Growth: +2.3σ                 │
│                                │ • Momentum: +1.8σ               │
│                                │                                 │
│                                │ CORRELATIONS                    │
│                                │ MSFT: 0.92 (high)               │
│                                │ META: 0.85                      │
│                                │ AAPL: 0.78                      │
│                                │                                 │
│                                │ TARGET PRICE                    │
│                                │ Target: $500 (↑ 13.6%)          │
│                                │ Set on: Oct 15, 2025            │
│                                │ [Edit Target]                   │
│                                │                                 │
│                                │ [Full Risk Analysis →]          │
└────────────────────────────────┴────────────────────────────────┘
```

**Data Sources**:
- Position data: `/api/v1/data/positions/details`
- Risk metrics: `/api/v1/analytics/portfolio/{id}/positions/factor-exposures`
- Correlations: `/api/v1/analytics/portfolio/{id}/correlation-matrix`
- Target price: `/api/v1/target-prices?position_id={id}`

---

## Data Sources & Implementation

**API Endpoints**:
- `/api/v1/data/positions/details` - All position data
- `/api/v1/tags` - Available tags
- `/api/v1/position-tags` - Position-tag relationships
- `/api/v1/target-prices` - Target prices by position
- `/api/v1/data/company-profile/{symbol}` - Company info

**State Management**:
```typescript
interface PositionsState {
  activeTab: 'all' | 'long' | 'short' | 'options' | 'private'
  filters: {
    search: string
    tags: string[]
    sectors: string[]
    plFilter: 'all' | 'gainers' | 'losers'
    sizeFilter: 'all' | 'large' | 'medium' | 'small'
  }
  view: 'cards' | 'table'
  selectedPositions: string[]  // For bulk actions
  sidePanelPosition: Position | null
}
```

**Next**: See `05-RISK-ANALYTICS-WORKSPACE.md` for risk analysis specification.
