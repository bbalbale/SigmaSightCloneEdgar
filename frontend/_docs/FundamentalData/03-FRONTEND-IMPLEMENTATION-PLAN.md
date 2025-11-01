# Frontend Implementation Plan: Fundamental Financial Data on Research Page

**Date**: November 1, 2025
**Status**: Planning (First Thoughts - For Discussion)
**Current Page**: Research & Analyze (`/research-and-analyze`)

---

## Current Research Page Structure

### Existing Layout
The Research & Analyze page currently shows:

**Top Level**: Tab-based navigation
- PUBLIC positions (long + short)
- OPTIONS positions
- PRIVATE positions

**Per Tab**: Table view with collapsible rows
- Main table: Symbol, market value, % of equity, target return, tags
- Expanded row:
  - Company Profile (sector, industry, description, market cap)
  - Correlations with other positions
  - Risk metrics (beta, volatility, etc.)

**Key Files**:
- `app/research-and-analyze/page.tsx` - Route file
- `src/containers/ResearchAndAnalyzeContainer.tsx` - Business logic (~400 lines)
- `src/components/research-and-analyze/ResearchTableView.tsx` - Table display (~600 lines)
- `src/components/research-and-analyze/CorrelationsSection.tsx` - Correlations display

---

## Design Considerations: Where to Add Fundamental Data?

### Option 1: New Tab in Research Page ⭐ **RECOMMENDED**

**Add 4th tab**: "FINANCIALS" alongside PUBLIC/OPTIONS/PRIVATE

**Pros:**
- Clean separation from existing position data
- Doesn't clutter existing expanded rows
- Dedicated space for financial tables and charts
- Can focus on 1-2 selected symbols at a time
- Easy to implement without disrupting current layout

**Cons:**
- Requires symbol selection mechanism (dropdown or click-to-load)
- Can't view financials and position data simultaneously
- Adds another tab (UI complexity)

**User Flow:**
1. User clicks "FINANCIALS" tab
2. Selects a symbol from dropdown (or recent symbols)
3. Views comprehensive financial data for that symbol

---

### Option 2: Add to Expanded Row Details (Incremental)

**Add sub-tabs within expanded row**: Profile | Correlations | Financials | Forward Outlook

**Pros:**
- Contextual - view financials alongside position data
- No new top-level navigation
- Progressive disclosure (only loads when expanded)
- Natural fit with existing company profile

**Cons:**
- Expanded row could become very large/complex
- Harder to compare financials across multiple symbols
- Performance concerns (loading financials for multiple expanded rows)
- UI could feel cramped

**User Flow:**
1. User expands a position row
2. Clicks "Financials" sub-tab
3. Views financial data inline

---

### Option 3: Dedicated Financials Page (New Page)

**Create new page**: `/financials` (7th authenticated page)

**Pros:**
- Dedicated space for in-depth financial analysis
- Can show multiple companies side-by-side
- Room for advanced features (charting, comparisons)
- Doesn't modify existing Research page

**Cons:**
- Requires new navigation menu item
- Separated from portfolio context
- User must navigate away from Research page
- More implementation work

**User Flow:**
1. User navigates to /financials via dropdown
2. Selects symbols to analyze
3. Views comprehensive financial data

---

### Option 4: Modal/Drawer on Demand

**Add "View Financials" button** in expanded row → Opens modal/drawer

**Pros:**
- Overlay doesn't disrupt current page
- Can be large enough for comprehensive data
- Easy to dismiss and return to Research page
- Contextual access from position

**Cons:**
- Modal UX can feel detached
- Harder to reference position data while viewing financials
- Limited space compared to full page

**User Flow:**
1. User expands a position row
2. Clicks "View Financials" button
3. Modal opens with financial data
4. User closes modal to return

---

## Recommendation: Option 1 - New "FINANCIALS" Tab ⭐

### Rationale:

1. **Clean Separation**: Fundamental data is different from position data - deserves its own space
2. **Scalability**: Room to add features without cluttering existing UI
3. **Focus**: Users analyzing financials want dedicated view, not squeezed into expanded row
4. **Performance**: Load data on-demand when tab is clicked, not with every position expand
5. **User Intent**: When researching fundamentals, users typically analyze 1-2 symbols deeply
6. **Implementation**: Cleanest architecture, doesn't modify existing working components

### Proposed UI Structure

```
Research & Analyze Page
├── Tabs: PUBLIC | OPTIONS | PRIVATE | FINANCIALS ⭐ NEW
│
└── FINANCIALS Tab:
    ├── Symbol Selector (dropdown or search)
    ├── Time Period Controls (Quarterly/Annual, # of periods)
    ├── Financial Statements Section
    │   ├── Income Statement (table view)
    │   ├── Balance Sheet (table view)
    │   ├── Cash Flow (table view)
    │   └── Toggle: Show All Fields vs. Key Metrics Only
    │
    ├── Forward Outlook Section
    │   ├── Analyst Estimates (revenue, EPS for 4 periods)
    │   ├── Price Targets (low, mean, high with upside %)
    │   └── Next Earnings (date, expected revenue/EPS)
    │
    ├── Financial Ratios Section (calculated)
    │   ├── Profitability Ratios (margins, ROE, ROA)
    │   ├── Efficiency Ratios (turnover, DSO)
    │   ├── Leverage Ratios (debt ratios, coverage)
    │   └── Liquidity Ratios (current, quick, cash)
    │
    └── Growth Trends Section (optional - charts)
        ├── Revenue Growth Chart (QoQ, YoY)
        ├── Earnings Growth Chart
        └── FCF Growth Chart
```

---

## Implementation Phases: Option 1 (Financials Tab)

### Phase 1: Foundation (Week 1)

**Backend Prerequisites:**
- ✅ Income statement endpoint
- ✅ Balance sheet endpoint
- ✅ Cash flow endpoint
- ✅ Analyst estimates endpoint
- ✅ Price targets endpoint

**Frontend Tasks:**

1. **Create New Service** (`src/services/fundamentalsApi.ts`)
```typescript
// New service for fundamental data API calls
export const fundamentalsApi = {
  getIncomeStatement: (symbol: string, frequency: 'q' | 'a', periods: number),
  getBalanceSheet: (symbol: string, frequency: 'q' | 'a', periods: number),
  getCashFlow: (symbol: string, frequency: 'q' | 'a', periods: number),
  getAllStatements: (symbol: string, frequency: 'q' | 'a', periods: number),
  getAnalystEstimates: (symbol: string),
  getPriceTargets: (symbol: string),
  getNextEarnings: (symbol: string)
}
```

2. **Create Custom Hook** (`src/hooks/useFundamentals.ts`)
```typescript
// Hook to manage fundamental data fetching and state
export function useFundamentals(symbol: string | null, frequency: 'q' | 'a', periods: number) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Fetch all statements, estimates, targets
  // Return organized data structure
}
```

3. **Create Symbol Selector Component** (`src/components/research-and-analyze/SymbolSelector.tsx`)
```typescript
// Dropdown/search to select symbol for analysis
// Shows symbols from current portfolio + search all symbols
interface SymbolSelectorProps {
  portfolioSymbols: string[]
  selectedSymbol: string | null
  onSelect: (symbol: string) => void
}
```

4. **Add "FINANCIALS" Tab** to `ResearchAndAnalyzeContainer.tsx`
- Add new tab to existing Tabs component
- Wire up state management for selected symbol
- Add time period controls (quarterly/annual, # periods)

5. **Create Placeholder View** (`src/components/research-and-analyze/FinancialsView.tsx`)
- Basic layout structure
- Show "Select a symbol" when none selected
- Show loading state while fetching
- Show error state if fetch fails

**Deliverables:**
- ✅ New tab visible in Research page
- ✅ Symbol selector working
- ✅ Service layer integrated
- ✅ Data fetching hook functional

---

### Phase 2: Financial Statements Display (Week 2)

**Components to Create:**

1. **IncomeStatementTable** (`src/components/financials/IncomeStatementTable.tsx`)
```typescript
// Table displaying income statement line items across periods
interface IncomeStatementTableProps {
  data: IncomeStatementPeriod[]
  frequency: 'q' | 'a'
  compactMode?: boolean  // Show key metrics only vs all fields
}
```

**Table Structure:**
```
| Line Item               | Q4 2024    | Q3 2024    | Q2 2024    | Q1 2024    |
|-------------------------|------------|------------|------------|------------|
| Revenue                 | $94.9B     | $85.8B     | $81.8B     | $90.8B     |
| Cost of Revenue         | $52.3B     | $46.2B     | $45.9B     | $50.2B     |
| Gross Profit            | $42.6B     | $39.6B     | $35.9B     | $40.6B     |
| Gross Margin            | 44.9%      | 46.2%      | 43.9%      | 44.7%      |
| R&D                     | $7.8B      | $7.4B      | $7.2B      | $7.7B      |
| SG&A                    | $6.6B      | $6.2B      | $5.9B      | $6.5B      |
| Operating Income        | $28.2B     | $26.0B     | $22.8B     | $26.4B     |
| Operating Margin        | 29.7%      | 30.3%      | 27.9%      | 29.1%      |
| ... (more rows)
```

**Features:**
- Sortable columns (click header to see time series trends)
- Compact/Full view toggle
- Calculated fields (margins) highlighted differently
- Conditional formatting (green for positive trends, red for negative)
- Currency formatting with proper abbreviations (B, M)

2. **BalanceSheetTable** (similar structure)
3. **CashFlowTable** (similar structure)

4. **FinancialStatementsSection** (`src/components/financials/FinancialStatementsSection.tsx`)
```typescript
// Container for all three statement tables
// Sub-tabs: Income Statement | Balance Sheet | Cash Flow | All
```

**UI Pattern:**
- Sub-tab navigation for statement type
- Frequency toggle (Quarterly/Annual)
- Period selector (Last 4, 8, 12 quarters OR 1, 2, 3, 4 years)
- Compact/Full toggle
- Export to CSV button (future)

**Deliverables:**
- ✅ All three financial statements rendering
- ✅ Data displays correctly with proper formatting
- ✅ Compact vs Full mode working
- ✅ Responsive table design

---

### Phase 3: Forward-Looking Data Display (Week 3)

**Components to Create:**

1. **AnalystEstimatesSection** (`src/components/financials/AnalystEstimatesSection.tsx`)
```typescript
interface AnalystEstimatesSectionProps {
  estimates: AnalystEstimatesData  // Current Q, Next Q, Current Y, Next Y
}
```

**UI Design:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Analyst Estimates                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Current Quarter (Q1 2025) - Ends Dec 31, 2025                  │
│  ┌────────────────────┬──────────────────────┐                   │
│  │ Revenue Estimates  │ EPS Estimates        │                   │
│  ├────────────────────┼──────────────────────┤                   │
│  │ Average: $137.96B  │ Average: $2.64       │                   │
│  │ Low: $136.68B      │ Low: $2.40           │                   │
│  │ High: $140.67B     │ High: $2.80          │                   │
│  │ # Analysts: 24     │ # Analysts: 27       │                   │
│  │ YoY Growth: +11.0% │ YoY Growth: +10.0%   │                   │
│  └────────────────────┴──────────────────────┘                   │
│                                                                   │
│  Next Quarter (Q2 2025)                                          │
│  [Similar card layout]                                           │
│                                                                   │
│  Current Year (FY 2025)                                          │
│  [Similar card layout]                                           │
│                                                                   │
│  Next Year (FY 2026)                                             │
│  [Similar card layout]                                           │
│                                                                   │
│  ┌─────────────────────────────────────────┐                     │
│  │ EPS Estimate Revisions (Last 30 Days)  │                     │
│  │ Upgrades: ↑ 8    Downgrades: ↓ 0       │                     │
│  └─────────────────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

2. **PriceTargetsCard** (`src/components/financials/PriceTargetsCard.tsx`)
```
┌─────────────────────────────────────────────────────────────────┐
│ Analyst Price Targets                      Current: $225.50     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Low         Mean           Median         High         │    │
│  │  $200        $274.97        $270.00        $345.00      │    │
│  │                                                           │    │
│  │  [────────|─────────●────────|──────────]               │    │
│  │  $200                   ^$225.50                 $345    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Upside to Mean: +21.9%  |  Upside to High: +53.0%              │
│  # Analysts: 41          |  Recommendation: Buy (2.0/5.0)       │
│                                                                   │
│  ┌────────────────────────────────────────────────┐             │
│  │ Recommendation Breakdown:                       │             │
│  │ Strong Buy: 15  Buy: 18  Hold: 7  Sell: 1      │             │
│  │ [■■■■■■■■■■■■■■■░░░░░░░]                        │             │
│  └────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

3. **NextEarningsCard** (`src/components/financials/NextEarningsCard.tsx`)
```
┌─────────────────────────────────────────────────────────────────┐
│ Next Earnings Date: January 29, 2026 (3:00 PM ET)               │
├─────────────────────────────────────────────────────────────────┤
│  Expected Revenue: $137.96B (Low: $136.68B, High: $140.67B)     │
│  Expected EPS: $2.63 (Low: $2.40, High: $2.71)                  │
│                                                                   │
│  Last Earnings (Q4 2024 - Oct 31, 2024):                        │
│  Revenue: $94.93B vs Est. $94.36B → Beat by 0.6% ✓             │
│  EPS: $1.64 vs Est. $1.60 → Beat by 2.5% ✓                     │
└─────────────────────────────────────────────────────────────────┘
```

**Deliverables:**
- ✅ Analyst estimates display (4 periods)
- ✅ Price targets with visual chart
- ✅ Next earnings card with beat/miss indicators
- ✅ Clean, professional design

---

### Phase 4: Calculated Metrics (Week 4)

**Components to Create:**

1. **FinancialRatiosGrid** (`src/components/financials/FinancialRatiosGrid.tsx`)

**UI Design**: 4-column grid of ratio categories
```
┌──────────────────────┬──────────────────────┬──────────────────────┬──────────────────────┐
│ Profitability        │ Efficiency           │ Leverage             │ Liquidity            │
├──────────────────────┼──────────────────────┼──────────────────────┼──────────────────────┤
│ Gross Margin: 44.9%  │ Asset Turnover: 1.2x │ Debt/Equity: 0.3x    │ Current Ratio: 1.8x  │
│ Operating Margin: 30%│ Inventory Turn: N/A  │ Debt/Assets: 0.15x   │ Quick Ratio: 1.5x    │
│ Net Margin: 25.2%    │ DSO: 45 days         │ Interest Cov: N/A    │ Cash Ratio: 0.9x     │
│ ROE: 42.5%           │                      │                      │                      │
│ ROA: 18.3%           │                      │                      │                      │
└──────────────────────┴──────────────────────┴──────────────────────┴──────────────────────┘
```

2. **GrowthMetricsChart** (`src/components/financials/GrowthMetricsChart.tsx`)
- Line chart showing growth rates over time
- Multiple series: Revenue, Earnings, FCF
- Toggle QoQ vs YoY vs 3Y CAGR
- Optional: Use recharts or similar library

**Deliverables:**
- ✅ Financial ratios calculated and displayed
- ✅ Growth trends visualization (optional charts)
- ✅ Responsive grid layout

---

## Data Structure & State Management

### Research Store Extension (`src/stores/researchStore.ts`)

**Add to existing Zustand store:**
```typescript
interface ResearchStore {
  // ... existing state ...

  // Financials tab state
  selectedSymbol: string | null
  setSelectedSymbol: (symbol: string | null) => void

  financialsFrequency: 'q' | 'a'
  setFinancialsFrequency: (frequency: 'q' | 'a') => void

  financialsPeriods: number
  setFinancialsPeriods: (periods: number) => void

  compactMode: boolean
  setCompactMode: (compact: boolean) => void
}
```

**Rationale**: Keep financials state separate from position data, but in same store for tab switching persistence

---

## Open Questions & Discussion Points

### 1. Symbol Selection Mechanism

**Question**: How should users select symbols to analyze?

**Options:**
- **A**: Dropdown with portfolio symbols only (simple, contextual)
- **B**: Dropdown with portfolio symbols + search all public symbols (flexible)
- **C**: Click-to-load from position table in other tabs (natural flow)
- **D**: Multi-select to compare multiple symbols side-by-side (advanced)

**My Recommendation**: Start with Option A (portfolio only), add B in Phase 2

### 2. Default Symbol Selection

**Question**: What symbol should be selected by default when user opens Financials tab?

**Options:**
- **A**: None - show "Select a symbol to begin"
- **B**: Largest position by market value
- **C**: Last viewed symbol (persist in localStorage)
- **D**: First alphabetically

**My Recommendation**: Option A for clarity, add C (persistence) later

### 3. Data Caching Strategy

**Question**: Should we cache financial data to reduce API calls?

**Considerations:**
- Financial statements change infrequently (quarterly)
- Analyst estimates change daily
- Price targets update throughout day

**Options:**
- **A**: No caching - always fetch fresh
- **B**: Cache statements for 24 hours, estimates for 1 hour
- **C**: Let backend handle caching, frontend always fetches

**My Recommendation**: Start with Option C (simple), add client-side caching later if needed

### 4. Compact vs Full Mode Default

**Question**: Should compact mode (key metrics only) be default?

**Pros of Compact Default:**
- Less overwhelming for average users
- Faster to scan key metrics
- Better for smaller screens

**Pros of Full Default:**
- Shows all available data immediately
- No need to toggle for power users
- Demonstrates data completeness

**My Recommendation**: Compact mode default, with persistent toggle preference

### 5. Mobile Responsiveness

**Question**: How should financial tables display on mobile?

**Challenges:**
- Tables with 4-12 columns are wide
- Horizontal scroll on mobile is awkward

**Options:**
- **A**: Horizontal scroll (simple, shows all data)
- **B**: Card-based layout on mobile (different component)
- **C**: Show 2 periods at a time with pagination
- **D**: Hide all but most recent period on mobile

**My Recommendation**: Start with Option A, refine based on user feedback

### 6. Chart Library

**Question**: Should we use a charting library for growth trends?

**Options:**
- **A**: Recharts (React-focused, good docs, 25KB)
- **B**: Chart.js (popular, flexible, 37KB)
- **C**: Victory (modular, 60KB)
- **D**: No charts initially, add later if needed

**My Recommendation**: Option D - focus on tables first, add charts in Phase 5

### 7. Integration with AI Chat

**Question**: Should fundamental data be available to AI chat?

**Considerations:**
- AI could answer questions like "What's AAPL's revenue growth?"
- Would require backend integration
- Increases AI utility significantly

**My Recommendation**: **YES** - Add fundamentals to AI tools in Phase 5
- High value feature
- Natural extension of analytical reasoning
- Differentiates SigmaSight

### 8. Export Functionality

**Question**: Should users be able to export financial data?

**Options:**
- **A**: CSV export (simple, widely compatible)
- **B**: Excel export (formatted, richer)
- **C**: PDF export (presentation-ready)
- **D**: Copy to clipboard

**My Recommendation**: Add CSV export in Phase 4 or 5 (not MVP)

---

## Alternative Architectures (For Comparison)

### Alternative: Separate Financials Page (/financials)

**Pros:**
- Could show multiple symbols side-by-side for comparison
- Room for advanced features (charts, screeners, custom metrics)
- Doesn't modify existing Research page

**Cons:**
- Adds 7th authenticated page
- Requires navigation menu update
- Separates from portfolio context
- More complex state management

**When to Consider**: If users frequently want to compare financials across 3+ symbols simultaneously

---

## Performance Considerations

### Bundle Size Impact

**New Dependencies:**
- None required initially (use existing UI components)
- Optional: Chart library if we add visualizations (~25-60KB)

**Code Splitting:**
- Financials tab loads on-demand (lazy load component)
- ~30-50KB estimated for fundamental components
- No impact on initial page load

### API Call Optimization

**Patterns:**
- Fetch all statements at once with `/all-statements` endpoint
- Debounce symbol changes (500ms delay before API call)
- Show loading skeleton while fetching
- Cache in component state (avoid refetch on re-render)

### Rendering Performance

**Large Tables:**
- Income statement: ~20-40 rows × 4-12 columns = 80-480 cells
- Balance sheet: ~60-100 rows × 4-12 columns = 240-1200 cells
- Cash flow: ~20-30 rows × 4-12 columns = 80-360 cells

**Optimization:**
- Virtualize tables if > 50 rows (react-window or similar)
- Memoize table rows (React.memo)
- Lazy render collapsed sections

---

## Success Metrics

### User Engagement
- % of users who click Financials tab
- Average time spent on Financials tab
- # of different symbols analyzed per session

### Feature Adoption
- Compact vs Full mode usage split
- Most viewed statement type (income, balance, cash flow)
- Forward estimates view rate

### Performance
- Time to first render < 300ms after symbol select
- Table scroll performance 60fps
- API response time < 500ms (backend responsibility)

---

## Implementation Checklist

### Pre-Implementation
- [ ] Review and approve this plan
- [ ] Decide on open questions (#1-8 above)
- [ ] Confirm backend endpoints ready
- [ ] Design approval (mockups if needed)

### Phase 1: Foundation
- [ ] Create fundamentalsApi service
- [ ] Create useFundamentals hook
- [ ] Add Financials tab to Research page
- [ ] Create SymbolSelector component
- [ ] Wire up state management

### Phase 2: Statements
- [ ] Create IncomeStatementTable
- [ ] Create BalanceSheetTable
- [ ] Create CashFlowTable
- [ ] Create FinancialStatementsSection
- [ ] Test with multiple companies

### Phase 3: Forward Data
- [ ] Create AnalystEstimatesSection
- [ ] Create PriceTargetsCard
- [ ] Create NextEarningsCard
- [ ] Test with companies with varying analyst coverage

### Phase 4: Calculations
- [ ] Create FinancialRatiosGrid
- [ ] Implement ratio calculations
- [ ] Create GrowthMetricsChart (optional)
- [ ] Test accuracy of calculations

### Phase 5: Polish (Future)
- [ ] Add charts/visualizations
- [ ] Export to CSV
- [ ] AI chat integration
- [ ] Mobile optimization
- [ ] Performance optimization

---

## Summary & Next Steps

### Recommended Approach: New "FINANCIALS" Tab

**Why:**
1. Clean, focused experience for fundamental analysis
2. Doesn't clutter existing position views
3. Room to grow features without UI constraints
4. Natural fit with Research page's investigative purpose
5. Straightforward implementation path

**Implementation Timeline:**
- **Week 1**: Foundation + symbol selection
- **Week 2**: Financial statements display
- **Week 3**: Forward-looking data
- **Week 4**: Calculated metrics
- **Week 5+**: Polish and advanced features

**Immediate Next Steps:**
1. ✅ Review this plan
2. 🔄 Decide on open questions (#1-8)
3. 🔄 Confirm backend implementation timeline
4. 🔄 Create mockups/designs (optional but helpful)
5. 🔄 Begin Phase 1 implementation

---

## Questions for Discussion

1. **Tab placement**: Do we agree "FINANCIALS" tab is the right approach vs. other options?

2. **Symbol selection**: Portfolio-only or allow searching all symbols?

3. **Default view**: Compact (key metrics) or Full (all fields) by default?

4. **Priority**: Are all 4 phases needed for MVP, or can we ship after Phase 2 or 3?

5. **Charts**: Include charts in initial release or defer to later version?

6. **AI integration**: Should we plan for AI chat access to fundamental data from the start?

7. **Comparison feature**: Do users need to view multiple symbols side-by-side?

8. **Mobile strategy**: Accept horizontal scroll or invest in mobile-specific layout?

---

**End of Planning Document - Ready for Discussion**
