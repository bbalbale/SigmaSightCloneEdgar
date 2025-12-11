# Financial Summary Tab - Detailed Specification

**Date**: November 2, 2025
**Status**: Planning - Ready for Implementation
**Location**: Research & Analyze Page → Expanded Row → Financials Sub-Tab

---

## Executive Summary

Add a "Financials" sub-tab to the Research & Analyze page's expanded row view that displays a clean, focused financial summary table showing:
- **6 key metrics**: Revenue, Gross Profit, EBIT, Net Income, EPS, Free Cash Flow
- **4 historical years** (2021-2024): Actual reported financial data
- **2 forward years** (2025E-2026E): Analyst consensus estimates
- **YoY growth rates** for all metrics
- **Annual data only** (MVP - quarterly in Phase 2)

---

## User Flow

```
1. User navigates to Research & Analyze page
2. User clicks to expand a position row (e.g., AAPL)
3. Expanded row shows sub-tabs: [Company Profile] [Correlations] [Financials] ⭐ NEW
4. User clicks "Financials" sub-tab
5. System fetches fundamental data from backend (3 API calls)
6. Table displays with 6 metrics × 6 years (4 historical + 2 forward)
7. User can view growth trends, compare historical to estimates
```

---

## Visual Specification

### Complete Table Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 📊 Financial Summary - AAPL                                 Currency: USD │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│              Historical (Actual)          Forward (Estimates)              │
│   Metric        2021      2022      2023      2024      2025E     2026E   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   Revenue                                                                  │
│   Amount       $366B     $394B     $383B     $391B     $420B     $448B    │
│   YoY %        +33.3%    +7.8%     -2.8%     +2.1%     +7.4%     +6.7%    │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                            │
│   Gross Profit                                                             │
│   Amount       $152B     $171B     $170B     $178B       N/A       N/A    │
│   Margin       41.5%     43.3%     44.1%     45.6%       N/A       N/A    │
│   YoY %        +46.2%    +12.5%    -0.6%     +4.7%       N/A       N/A    │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                            │
│   EBIT (Operating Income)                                                  │
│   Amount       $109B     $119B     $114B     $123B       N/A       N/A    │
│   Margin       29.8%     30.2%     29.8%     31.5%       N/A       N/A    │
│   YoY %        +62.5%    +9.2%     -4.2%     +7.9%       N/A       N/A    │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                            │
│   Net Income                                                               │
│   Amount        $95B     $100B      $97B     $100B     $110B     $121B    │
│   Margin       25.9%     25.3%     25.3%     25.6%     26.2%     27.0%    │
│   YoY %        +64.9%    +5.3%     -2.8%     +3.1%     +10.0%    +10.0%   │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                            │
│   Diluted EPS                                                              │
│   Amount       $5.61     $6.11     $5.89     $6.42     $6.95     $7.68    │
│   YoY %        +64.9%    +8.9%     -3.6%     +9.0%     +8.3%     +10.5%   │
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                                            │
│   Free Cash Flow                                                           │
│   Amount        $93B     $111B     $100B     $108B       N/A       N/A    │
│   Margin       25.4%     28.2%     26.1%     27.6%       N/A       N/A    │
│   YoY %        +28.7%    +19.4%    -9.9%     +8.0%       N/A       N/A    │
└──────────────────────────────────────────────────────────────────────────┘

📅 Fiscal Year: Ends September 30 (FY 2024 = Oct 2023 - Sep 2024)
💡 Forward estimates: Revenue & EPS based on 34 analysts | Updated: Nov 2, 2025
    Net Income calculated: EPS × Diluted Shares Outstanding
ℹ️  EBIT, Gross Profit, and FCF estimates not provided by analysts

[View Full Statements →]  [Export to CSV →]
```

---

## Data Specification

### 6 Metrics - What We Show

| Metric | Historical Data Source | Forward Data Source | Calculation Notes |
|--------|----------------------|-------------------|------------------|
| **Revenue** | Income Statement: `total_revenue` | Analyst Estimates: `current_year_revenue_avg`, `next_year_revenue_avg` | Direct from backend |
| **Gross Profit** | Income Statement: `gross_profit` | N/A | Direct from backend |
| **EBIT** | Income Statement: `operating_income` | N/A | EBIT ≈ Operating Income |
| **Net Income** | Income Statement: `net_income` | Calculated: EPS × Shares | Forward: EPS × `diluted_average_shares` (from latest historical) |
| **EPS (Diluted)** | Income Statement: `diluted_eps` | Analyst Estimates: `current_year_earnings_avg`, `next_year_earnings_avg` | Direct from backend |
| **Free Cash Flow** | Cash Flow: `free_cash_flow` | N/A | FCF = Operating CF - CapEx |

### Margin Calculations

| Margin | Formula | Data Source |
|--------|---------|-------------|
| **Gross Margin** | `gross_profit / total_revenue × 100` | Income Statement: `gross_margin` (pre-calculated) |
| **EBIT Margin** | `operating_income / total_revenue × 100` | Income Statement: `operating_margin` (pre-calculated) |
| **Net Margin** | `net_income / total_revenue × 100` | Income Statement: `net_margin` (pre-calculated) OR calculate for forward years |
| **FCF Margin** | `free_cash_flow / total_revenue × 100` | Cash Flow: `fcf_margin` (pre-calculated) |

### YoY Growth Calculations

```typescript
// For all metrics
yoy_growth = ((current_year - previous_year) / previous_year) × 100

// Example:
// Revenue 2022: $394B
// Revenue 2021: $366B
// YoY Growth = (($394B - $366B) / $366B) × 100 = 7.8%
```

---

## Backend API Calls

### Required Endpoints (3 calls per symbol)

#### 1. Income Statement
```http
GET /api/v1/fundamentals/AAPL/income-statement?frequency=a&periods=4
```

**Returns** (4 annual periods):
```json
{
  "symbol": "AAPL",
  "frequency": "a",
  "periods": [
    {
      "period_date": "2024-09-30",
      "fiscal_year": 2024,
      "total_revenue": "391035000000.00",
      "gross_profit": "178178000000.00",
      "gross_margin": "0.456000",
      "operating_income": "123216000000.00",
      "operating_margin": "0.315000",
      "net_income": "100389000000.00",
      "net_margin": "0.256700",
      "diluted_eps": "6.42",
      "diluted_average_shares": "15634000000"
    },
    // ... 3 more years (2023, 2022, 2021)
  ]
}
```

**Fields Used**:
- `fiscal_year` → Column header
- `total_revenue` → Revenue amount
- `gross_profit` → Gross Profit amount
- `gross_margin` → Gross Profit margin
- `operating_income` → EBIT amount
- `operating_margin` → EBIT margin
- `net_income` → Net Income amount
- `net_margin` → Net Income margin
- `diluted_eps` → EPS amount
- `diluted_average_shares` → Used to calculate forward Net Income

---

#### 2. Cash Flow Statement
```http
GET /api/v1/fundamentals/AAPL/cash-flow?frequency=a&periods=4
```

**Returns** (4 annual periods):
```json
{
  "symbol": "AAPL",
  "frequency": "a",
  "periods": [
    {
      "period_date": "2024-09-30",
      "fiscal_year": 2024,
      "free_cash_flow": "108000000000.00",
      "fcf_margin": "0.276000"
    },
    // ... 3 more years
  ]
}
```

**Fields Used**:
- `fiscal_year` → Match to income statement year
- `free_cash_flow` → FCF amount
- `fcf_margin` → FCF margin

---

#### 3. Analyst Estimates
```http
GET /api/v1/fundamentals/AAPL/analyst-estimates
```

**Returns**:
```json
{
  "symbol": "AAPL",
  "estimates": {
    "current_year_revenue_avg": "420000000000.00",
    "current_year_revenue_low": "415000000000.00",
    "current_year_revenue_high": "428000000000.00",
    "current_year_analyst_count": 34,
    "current_year_earnings_avg": "6.95",
    "next_year_revenue_avg": "448000000000.00",
    "next_year_earnings_avg": "7.68"
  }
}
```

**Fields Used**:
- `current_year_revenue_avg` → 2025E Revenue
- `current_year_earnings_avg` → 2025E EPS
- `current_year_analyst_count` → Footer note
- `next_year_revenue_avg` → 2026E Revenue
- `next_year_earnings_avg` → 2026E EPS

---

#### 4. Company Profile (for fiscal year info)
```http
GET /api/v1/data/company-profiles?symbols=AAPL
```

**Returns**:
```json
{
  "AAPL": {
    "symbol": "AAPL",
    "company_name": "Apple Inc.",
    "current_year_end_date": "2025-09-30",
    "next_year_end_date": "2026-09-30"
  }
}
```

**Fields Used**:
- `current_year_end_date` → Determine fiscal year end for footer note
- Map to determine if fiscal year = calendar year

---

## Data Transformation Logic

### Step 1: Fetch All Data

```typescript
async function fetchFinancialData(symbol: string) {
  const [incomeData, cashFlowData, estimatesData, profileData] = await Promise.all([
    fundamentalsApi.getIncomeStatement(symbol, 4, 'a'),
    fundamentalsApi.getCashFlow(symbol, 4, 'a'),
    fundamentalsApi.getAnalystEstimates(symbol),
    companyProfilesApi.get([symbol])
  ]);

  return { incomeData, cashFlowData, estimatesData, profileData };
}
```

### Step 2: Transform to Table Data Structure

```typescript
interface FinancialYearData {
  year: number;
  isEstimate: boolean;

  // Revenue
  revenue: number | null;
  revenueGrowth: number | null;

  // Gross Profit
  grossProfit: number | null;
  grossMargin: number | null;
  grossProfitGrowth: number | null;

  // EBIT
  ebit: number | null;
  ebitMargin: number | null;
  ebitGrowth: number | null;

  // Net Income
  netIncome: number | null;
  netMargin: number | null;
  netIncomeGrowth: number | null;

  // EPS
  eps: number | null;
  epsGrowth: number | null;

  // FCF
  fcf: number | null;
  fcfMargin: number | null;
  fcfGrowth: number | null;
}

function transformToTableData(
  incomeData: IncomeStatementResponse,
  cashFlowData: CashFlowResponse,
  estimatesData: AnalystEstimatesResponse
): FinancialYearData[] {

  // 1. Map historical years (2021-2024)
  const historical: FinancialYearData[] = incomeData.periods.map((stmt, index, array) => {
    const prevStmt = array[index + 1]; // Previous year for growth calc
    const matchingCashFlow = cashFlowData.periods.find(cf => cf.fiscal_year === stmt.fiscal_year);

    return {
      year: stmt.fiscal_year,
      isEstimate: false,

      revenue: parseFloat(stmt.total_revenue),
      revenueGrowth: prevStmt ? calculateGrowth(stmt.total_revenue, prevStmt.total_revenue) : null,

      grossProfit: parseFloat(stmt.gross_profit),
      grossMargin: parseFloat(stmt.gross_margin) * 100, // Convert to percentage
      grossProfitGrowth: prevStmt ? calculateGrowth(stmt.gross_profit, prevStmt.gross_profit) : null,

      ebit: parseFloat(stmt.operating_income),
      ebitMargin: parseFloat(stmt.operating_margin) * 100,
      ebitGrowth: prevStmt ? calculateGrowth(stmt.operating_income, prevStmt.operating_income) : null,

      netIncome: parseFloat(stmt.net_income),
      netMargin: parseFloat(stmt.net_margin) * 100,
      netIncomeGrowth: prevStmt ? calculateGrowth(stmt.net_income, prevStmt.net_income) : null,

      eps: parseFloat(stmt.diluted_eps),
      epsGrowth: prevStmt ? calculateGrowth(stmt.diluted_eps, prevStmt.diluted_eps) : null,

      fcf: matchingCashFlow ? parseFloat(matchingCashFlow.free_cash_flow) : null,
      fcfMargin: matchingCashFlow ? parseFloat(matchingCashFlow.fcf_margin) * 100 : null,
      fcfGrowth: null // Calculate if we have previous CF data
    };
  });

  // 2. Create forward years (2025E, 2026E)
  const latestYear = historical[0]; // Most recent historical year (2024)
  const latestShares = parseFloat(incomeData.periods[0].diluted_average_shares);

  const currentYearEstimate: FinancialYearData = {
    year: latestYear.year + 1, // 2025
    isEstimate: true,

    revenue: parseFloat(estimatesData.estimates.current_year_revenue_avg),
    revenueGrowth: calculateGrowth(
      estimatesData.estimates.current_year_revenue_avg,
      latestYear.revenue
    ),

    grossProfit: null,
    grossMargin: null,
    grossProfitGrowth: null,

    ebit: null,
    ebitMargin: null,
    ebitGrowth: null,

    // Calculate Net Income from EPS × Shares
    netIncome: parseFloat(estimatesData.estimates.current_year_earnings_avg) * latestShares,
    netMargin: (parseFloat(estimatesData.estimates.current_year_earnings_avg) * latestShares) /
               parseFloat(estimatesData.estimates.current_year_revenue_avg) * 100,
    netIncomeGrowth: calculateGrowth(
      parseFloat(estimatesData.estimates.current_year_earnings_avg) * latestShares,
      latestYear.netIncome
    ),

    eps: parseFloat(estimatesData.estimates.current_year_earnings_avg),
    epsGrowth: calculateGrowth(
      estimatesData.estimates.current_year_earnings_avg,
      latestYear.eps
    ),

    fcf: null,
    fcfMargin: null,
    fcfGrowth: null
  };

  const nextYearEstimate: FinancialYearData = {
    year: latestYear.year + 2, // 2026
    isEstimate: true,

    revenue: parseFloat(estimatesData.estimates.next_year_revenue_avg),
    revenueGrowth: calculateGrowth(
      estimatesData.estimates.next_year_revenue_avg,
      estimatesData.estimates.current_year_revenue_avg
    ),

    grossProfit: null,
    grossMargin: null,
    grossProfitGrowth: null,

    ebit: null,
    ebitMargin: null,
    ebitGrowth: null,

    netIncome: parseFloat(estimatesData.estimates.next_year_earnings_avg) * latestShares,
    netMargin: (parseFloat(estimatesData.estimates.next_year_earnings_avg) * latestShares) /
               parseFloat(estimatesData.estimates.next_year_revenue_avg) * 100,
    netIncomeGrowth: calculateGrowth(
      parseFloat(estimatesData.estimates.next_year_earnings_avg) * latestShares,
      parseFloat(estimatesData.estimates.current_year_earnings_avg) * latestShares
    ),

    eps: parseFloat(estimatesData.estimates.next_year_earnings_avg),
    epsGrowth: calculateGrowth(
      estimatesData.estimates.next_year_earnings_avg,
      estimatesData.estimates.current_year_earnings_avg
    ),

    fcf: null,
    fcfMargin: null,
    fcfGrowth: null
  };

  // Return: [2024, 2023, 2022, 2021, 2025E, 2026E]
  // Sort descending by year for display
  return [...historical, currentYearEstimate, nextYearEstimate].sort((a, b) => a.year - b.year);
}

function calculateGrowth(current: string | number, previous: string | number): number {
  const curr = typeof current === 'string' ? parseFloat(current) : current;
  const prev = typeof previous === 'string' ? parseFloat(previous) : previous;
  return ((curr - prev) / prev) * 100;
}
```

---

## Component Architecture

### Component Hierarchy

```
FinancialsTab (new)
  └── FinancialSummaryTable (new)
        ├── TableHeader
        │     ├── Title ("📊 Financial Summary - AAPL")
        │     └── CurrencyLabel ("Currency: USD")
        ├── TableColumnHeaders
        │     └── YearColumns (2021, 2022, 2023, 2024, 2025E, 2026E)
        ├── MetricSection (Revenue)
        │     ├── MetricRow (Amount)
        │     └── MetricRow (YoY %)
        ├── MetricSection (Gross Profit)
        │     ├── MetricRow (Amount)
        │     ├── MetricRow (Margin)
        │     └── MetricRow (YoY %)
        ├── MetricSection (EBIT)
        ├── MetricSection (Net Income)
        ├── MetricSection (EPS)
        ├── MetricSection (FCF)
        └── TableFooter
              ├── FiscalYearNote
              ├── EstimateNote
              └── ActionButtons
```

### File Structure

```
src/components/research-and-analyze/
  ├── FinancialsTab.tsx                    ⭐ NEW (Container, ~200 lines)
  └── financials/                           ⭐ NEW FOLDER
        ├── FinancialSummaryTable.tsx       ⭐ NEW (Table component, ~300 lines)
        ├── MetricSection.tsx                ⭐ NEW (Metric group, ~80 lines)
        ├── MetricRow.tsx                    ⭐ NEW (Single row, ~50 lines)
        └── TableFooter.tsx                  ⭐ NEW (Footer notes, ~60 lines)

src/hooks/
  └── useFundamentals.ts                    ⭐ NEW (Data fetching hook, ~150 lines)

src/lib/
  └── financialFormatters.ts                ⭐ NEW (Number formatting utilities, ~100 lines)
```

---

## Formatting Specifications

### Number Formatting

```typescript
// Revenue, amounts
formatCurrency(366000000000) → "$366B"
formatCurrency(5610000000)   → "$5.61B"
formatCurrency(93000000)     → "$93M"

// Margins, percentages
formatPercent(0.298)  → "29.8%"
formatPercent(0.0074) → "0.7%"
formatPercent(-0.028) → "-2.8%"

// Growth rates
formatGrowth(0.333)   → "+33.3%"  (green color)
formatGrowth(-0.028)  → "-2.8%"   (red color)
formatGrowth(0.021)   → "+2.1%"   (green color)

// N/A handling
formatValue(null)     → "N/A"     (gray color, lighter font)
```

### Color Specifications

```typescript
// Growth rates
positive_growth: text-green-600    // +33.3%
negative_growth: text-red-600      // -2.8%
neutral: text-gray-700             // 0.0%

// Estimates
estimate_value: text-gray-600      // Lighter than historical
estimate_suffix: text-gray-400     // "E" suffix

// N/A values
na_value: text-gray-400 italic     // "N/A"

// Margins
margin_value: text-gray-600        // 29.8%
```

---

## Loading & Error States

### Loading State (Skeleton)

```
┌──────────────────────────────────────────────────────────────┐
│ 📊 Financial Summary - AAPL                                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   Loading financial data...                                  │
│                                                               │
│   ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░                   │
│   ████████████████████░░░░░░░░░░░░░░░░░░░                   │
│   ████████████████░░░░░░░░░░░░░░░░░░░░░░░                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Error State

```
┌──────────────────────────────────────────────────────────────┐
│ 📊 Financial Summary - AAPL                                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   ⚠️  Unable to load financial data                          │
│                                                               │
│   We couldn't fetch financial statements for AAPL.           │
│   This may be because:                                       │
│   • Financial data has not been collected yet                │
│   • The symbol doesn't have available financial data         │
│   • There was a temporary network issue                      │
│                                                               │
│   [Retry]                                                     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Empty State (No Data)

```
┌──────────────────────────────────────────────────────────────┐
│ 📊 Financial Summary - AAPL                                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   📋 No financial data available                             │
│                                                               │
│   Financial statements have not been collected for this      │
│   symbol yet. The batch process will collect this data       │
│   during the next earnings update.                           │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Footer Notes Specification

### Fiscal Year Note

**Condition**: Display if fiscal year end != December 31

**Format**:
```
📅 Fiscal Year: Ends {month} {day} (FY {year} = {start_month} {start_year} - {end_month} {end_year})
```

**Examples**:
```
📅 Fiscal Year: Ends September 30 (FY 2024 = Oct 2023 - Sep 2024)
📅 Fiscal Year: Ends January 31 (FY 2024 = Feb 2023 - Jan 2024)  // Walmart
```

**If calendar year** (ends Dec 31):
```
📅 Fiscal Year: Calendar Year
```

---

### Estimate Note

**Always Display**:
```
💡 Forward estimates: Revenue & EPS based on {analyst_count} analysts | Updated: {date}
    Net Income calculated: EPS × Diluted Shares Outstanding
```

**Example**:
```
💡 Forward estimates: Revenue & EPS based on 34 analysts | Updated: Nov 2, 2025
    Net Income calculated: EPS × Diluted Shares Outstanding
```

---

### N/A Explanation Note

**Always Display**:
```
ℹ️  EBIT, Gross Profit, and FCF estimates not provided by analysts
```

---

## Responsive Design

### Desktop (> 1024px)
- Show full table with all 6 columns
- All metrics visible
- All growth rates visible

### Tablet (768px - 1024px)
- Show full table with horizontal scroll
- Sticky first column (metric names)
- All data visible via scroll

### Mobile (< 768px)
- **Option 1**: Horizontal scroll (entire table)
- **Option 2**: Show 2 columns at a time with pagination
- **Option 3**: Switch to card-based layout

**Recommendation for MVP**: Option 1 (horizontal scroll) - simplest, preserves all data

---

## Performance Considerations

### Data Fetching
- **Fetch on tab click**: Only load when Financials tab is selected
- **Cache duration**: 24 hours (financial data changes infrequently)
- **Debounce**: 500ms delay if user switches symbols rapidly
- **Loading skeleton**: Show immediately while fetching

### Rendering
- **Table size**: ~30 cells (6 metrics × 3 rows × 6 years) = manageable
- **Memoization**: Use `React.memo` for `MetricRow` components
- **Virtual scrolling**: Not needed for this table size

### Bundle Size
- **New components**: ~15-20KB estimated
- **Dependencies**: None (use existing UI components)
- **Lazy loading**: Load `FinancialsTab` only when Research page is accessed

---

## Testing Strategy

### Unit Tests
- [ ] Test `transformToTableData()` with sample backend data
- [ ] Test growth calculations (positive, negative, zero, null)
- [ ] Test number formatting (billions, millions, decimals)
- [ ] Test N/A handling (null values)

### Integration Tests
- [ ] Test API calls (mock responses)
- [ ] Test loading state display
- [ ] Test error state handling
- [ ] Test empty state (no data)

### Manual Testing
- [ ] Test with AAPL (fiscal year Sept 30)
- [ ] Test with MSFT (fiscal year June 30)
- [ ] Test with GOOGL (calendar year)
- [ ] Test with smaller company (fewer analysts)
- [ ] Test with company missing some data

### Edge Cases
- [ ] Company with only 2 years of historical data
- [ ] Company with no analyst estimates
- [ ] Company with $0 revenue (division by zero in margins)
- [ ] Negative earnings (negative EPS growth)

---

## Success Metrics

### User Engagement
- **Adoption**: % of users who click Financials tab (target: >30%)
- **Time spent**: Average time viewing financials (target: >45 seconds)
- **Return rate**: % of users who view financials multiple times (target: >50%)

### Performance
- **Load time**: Time from tab click to data displayed (target: < 2 seconds)
- **Error rate**: % of failed data fetches (target: < 5%)

### Data Quality
- **Coverage**: % of symbols with financial data available (target: >80%)
- **Accuracy**: Match against source data (target: 100%)

---

## Implementation Checklist

### Phase 1: Foundation (Days 1-2)
- [ ] Create `useFundamentals` hook with API calls
- [ ] Create data transformation logic (`transformToTableData`)
- [ ] Create `FinancialsTab` container component
- [ ] Add "Financials" sub-tab to expanded row
- [ ] Wire up data fetching on tab click
- [ ] Implement loading/error states

### Phase 2: Table Display (Days 3-4)
- [ ] Create `FinancialSummaryTable` component
- [ ] Create `MetricSection` component
- [ ] Create `MetricRow` component
- [ ] Implement all 6 metrics with proper formatting
- [ ] Add YoY growth calculations and display
- [ ] Handle N/A values correctly

### Phase 3: Polish (Day 5)
- [ ] Create `TableFooter` with fiscal year note
- [ ] Add estimate details note
- [ ] Add N/A explanation note
- [ ] Implement number formatting utilities
- [ ] Add color coding (green/red for growth)
- [ ] Test with multiple companies

### Phase 4: Testing & Refinement (Day 6)
- [ ] Manual testing with 5+ companies
- [ ] Fix edge cases
- [ ] Responsive design testing
- [ ] Performance optimization
- [ ] Documentation updates

---

## Future Enhancements (Phase 2+)

### Short-term (Next Sprint)
- [ ] Quarterly data toggle
- [ ] "View Full Statements" modal (all fields)
- [ ] Export to CSV
- [ ] Comparison with S&P 500 averages

### Medium-term (Next Month)
- [ ] Charts (revenue growth trend)
- [ ] Peer comparison (show 3 competitors)
- [ ] Custom metric selection
- [ ] Detailed mode (show R&D, SG&A, etc.)

### Long-term (Future)
- [ ] Historical estimates vs actuals (beat/miss analysis)
- [ ] Consensus change tracking (upgrades/downgrades)
- [ ] AI-generated insights on financials
- [ ] Custom calculated metrics (ROIC, Piotroski F-Score)

---

## Open Questions / Decisions Needed

✅ **Resolved**:
- Metrics to show: 6 metrics (Revenue, Gross Profit, EBIT, Net Income, EPS, FCF)
- Growth rates: Show for all metrics
- Forward EBIT: Show N/A (not calculated)
- Forward Net Income: Calculate from EPS × Shares
- Annual vs Quarterly: Annual only for MVP
- Fiscal year notation: Show at bottom as note

❓ **Still Open**:
- Mobile layout: Horizontal scroll acceptable, or need card view?
- "View Full Statements" link: Modal or new page?
- Export format: CSV only, or also Excel/PDF?

---

**End of Specification - Ready for Implementation**
