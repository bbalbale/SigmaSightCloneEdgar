# Home Page Implementation Plan

**Created**: December 2025
**Status**: Planning

## Overview
Create a new `/home` page featuring portfolio metrics with inline AI insight cards, benchmark comparisons (SPY/QQQ), and AI chat integration.

## Route
- **Path**: `/home`
- **Pattern**: Container pattern (thin route file + container component)

---

## File Structure

```
frontend/
├── app/home/page.tsx                          # Route file (5 lines)
└── src/
    ├── containers/HomeContainer.tsx            # Main container (~300 lines)
    ├── hooks/useHomePageData.ts                # Data aggregation hook (~250 lines)
    ├── services/benchmarkService.ts            # Benchmark data service (~150 lines)
    └── components/home/
        ├── ReturnsRow.tsx                      # Row 1: Returns + AI insight
        ├── ExposuresRow.tsx                    # Row 2: Exposures + AI insight
        ├── VolatilityRow.tsx                   # Row 3: Volatility + AI insight
        ├── HomeAIChatRow.tsx                   # Row 4: CopilotPanel
        ├── MetricCard.tsx                      # Reusable metric card
        ├── BenchmarkMetricGroup.tsx            # Grouped benchmark metrics (1M/3M/YTD/1Y)
        └── InlineInsightCard.tsx               # Compact AI insight card
```

---

## Component Layout

```
HomeContainer
├── Header Section ("Portfolio Overview")
│
├── ReturnsRow (grid: 6 cols)
│   ├── MetricCard: Target Return EOY
│   ├── MetricCard: Target Return Next Year
│   ├── BenchmarkMetricGroup: SPY Returns (1M, 3M, YTD, 1Y)
│   ├── BenchmarkMetricGroup: QQQ Returns (1M, 3M, YTD, 1Y)
│   └── InlineInsightCard: Returns Analysis
│
├── ExposuresRow (grid: 6 cols)
│   ├── MetricCard: Equity Balance
│   ├── MetricCard: Long Exposure
│   ├── MetricCard: Short Exposure
│   ├── MetricCard: Gross Exposure
│   ├── MetricCard: Net Exposure
│   └── InlineInsightCard: Exposure Positioning
│
├── VolatilityRow (grid: 4 cols)
│   ├── BenchmarkMetricGroup: Portfolio Vol (1Y, 90D, Forward)
│   ├── BenchmarkMetricGroup: SPY Vol (1Y, 90D, Forward)
│   ├── BenchmarkMetricGroup: QQQ Vol (1Y, 90D, Forward)
│   └── InlineInsightCard: Volatility Context
│
└── HomeAIChatRow
    └── CopilotPanel (compact variant)
```

---

## Data Sources

### Existing APIs (No Backend Changes)
| Data | Endpoint | Service |
|------|----------|---------|
| Exposures | `/api/v1/analytics/portfolio/{id}/overview` | `analyticsApi.getOverview()` |
| Target Returns | `/api/v1/target-prices/{id}/summary` | `targetPriceService.summary()` |
| Portfolio Vol (21d, 63d) | `/api/v1/analytics/portfolio/{id}/volatility` | `analyticsApi.getVolatility()` |
| Historical Prices | `/api/v1/data/prices/historical/{id}` | For 1Y vol calculation |
| Factor ETF Prices | `/api/v1/data/factors/etf-prices` | SPY/QQQ historical data |

### New Service: `benchmarkService.ts`
Calculate benchmark returns and volatility on frontend from historical price data:

```typescript
// benchmarkService.ts
export const benchmarkService = {
  async getBenchmarkReturns(symbols: string[]): Promise<BenchmarkReturns>
  async getBenchmarkVolatility(symbols: string[]): Promise<BenchmarkVolatility>
}

// Types
interface BenchmarkReturns {
  SPY: { m1: number; m3: number; ytd: number; y1: number }
  QQQ: { m1: number; m3: number; ytd: number; y1: number }
}

interface BenchmarkVolatility {
  SPY: { y1: number; d90: number; forward: number | null }
  QQQ: { y1: number; d90: number; forward: number | null }
}
```

---

## AI Insight Integration

### InlineInsightCard Design
A compact insight card (~120px height) that:
- Shows a brief AI-generated summary (2-3 sentences)
- Has a "Generate" button to refresh insight
- Has an "Expand" option to see full analysis
- Uses severity-based styling (info/normal/warning/critical)

### Insight Generation Strategy
**Option 1 (Recommended)**: Use existing `useAIInsights` hook with row-specific prompts
- Generate insights on-demand when user clicks "Analyze"
- Cache insights for the session
- Show loading spinner during generation (~25-30s)

### Row-Specific Insight Prompts
```typescript
const insightPrompts = {
  returns: "Analyze portfolio target returns vs SPY/QQQ benchmarks. Brief assessment.",
  exposures: "Assess portfolio exposure positioning. Risk implications in 2-3 points.",
  volatility: "Compare portfolio volatility to SPY/QQQ. What does this imply?"
}
```

---

## Implementation Steps

### Phase 1: Foundation
1. Create `app/home/page.tsx` (5-line route file)
2. Create `HomeContainer.tsx` skeleton with 4 row placeholders
3. Create `useHomePageData.ts` hook with existing API calls only
4. Create `MetricCard.tsx` component (copy pattern from HeroMetricsRow)

### Phase 2: Exposures Row (Uses Existing APIs)
5. Implement `ExposuresRow.tsx` with 5 metric cards + insight placeholder
6. Wire up exposures data from `analyticsApi.getOverview()`
7. Test with loading states and error handling

### Phase 3: Returns Row
8. Implement `ReturnsRow.tsx` with target returns + benchmark placeholders
9. Wire up target returns from `targetPriceService.summary()`
10. Create `benchmarkService.ts` for SPY/QQQ returns calculation
11. Create `BenchmarkMetricGroup.tsx` for multi-timeframe display
12. Integrate benchmark returns data

### Phase 4: Volatility Row
13. Implement `VolatilityRow.tsx` with portfolio + benchmark volatility
14. Add 1-year volatility calculation (252 trading days) from historical prices
15. Add benchmark volatility to `benchmarkService.ts`
16. Wire up all volatility data

### Phase 5: AI Insights
17. Create `InlineInsightCard.tsx` component
18. Adapt existing `useAIInsights` hook for row-specific insights
19. Add insight cards to each row
20. Implement generate/refresh functionality

### Phase 6: AI Chat Integration
21. Implement `HomeAIChatRow.tsx` with CopilotPanel (compact variant)
22. Wire up existing `useCopilot` hook
23. Add contextual quick prompts related to home page metrics

### Phase 7: Polish & Navigation
24. Add `/home` to NavigationDropdown
25. Add loading skeletons for all rows
26. Test responsive design (mobile breakpoints)
27. Add error boundaries and graceful degradation

---

## Critical Files to Modify

### New Files to Create
- `frontend/app/home/page.tsx`
- `frontend/src/containers/HomeContainer.tsx`
- `frontend/src/hooks/useHomePageData.ts`
- `frontend/src/services/benchmarkService.ts`
- `frontend/src/components/home/ReturnsRow.tsx`
- `frontend/src/components/home/ExposuresRow.tsx`
- `frontend/src/components/home/VolatilityRow.tsx`
- `frontend/src/components/home/HomeAIChatRow.tsx`
- `frontend/src/components/home/MetricCard.tsx`
- `frontend/src/components/home/BenchmarkMetricGroup.tsx`
- `frontend/src/components/home/InlineInsightCard.tsx`

### Existing Files to Modify
- `frontend/src/components/navigation/NavigationDropdown.tsx` - Add /home link

### Reference Files (Copy Patterns From)
- `frontend/src/components/command-center/HeroMetricsRow.tsx` - MetricCard pattern
- `frontend/src/components/command-center/AIInsightsRow.tsx` - InsightCard pattern
- `frontend/src/containers/CommandCenterContainer.tsx` - Container structure
- `frontend/src/hooks/useCommandCenterData.ts` - Data aggregation pattern
- `frontend/src/components/copilot/CopilotPanel.tsx` - AI chat integration

---

## Styling Reference

```typescript
// Grid layouts
"grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4"

// Card styling
"themed-border-r p-3 transition-all duration-200 bg-secondary hover:bg-tertiary"

// Labels
"text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-secondary"

// Values
"text-2xl font-bold tabular-nums"

// Colors
positive: "text-emerald-400"
negative: "text-red-400"
neutral: "text-accent"
```

---

## Notes & Considerations

1. **Benchmark Data**: Calculate on frontend from historical prices (no new backend endpoint needed)
2. **1-Year Volatility**: Calculate from 252 trading days of historical data
3. **AI Insights**: Use existing infrastructure, generate on-demand to avoid slow page loads
4. **Multi-Portfolio**: Support aggregate view when `portfolioId` is null
5. **Caching**: Cache benchmark calculations for session to reduce API calls
6. **Error Handling**: Graceful degradation - show available data even if some APIs fail

---

## Wireframe Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PORTFOLIO OVERVIEW                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  RETURNS                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌────────────────┐ ┌────────────────┐ ┌─────────┐│
│  │ Target   │ │ Target   │ │ SPY Returns    │ │ QQQ Returns    │ │ AI      ││
│  │ EOY      │ │ Next Yr  │ │ 1M 3M YTD 1Y   │ │ 1M 3M YTD 1Y   │ │ Insight ││
│  │ +15.2%   │ │ +22.1%   │ │ +2% +5% +15%   │ │ +3% +7% +20%   │ │ Card    ││
│  └──────────┘ └──────────┘ └────────────────┘ └────────────────┘ └─────────┘│
│                                                                              │
│  EXPOSURES                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐│
│  │ Equity   │ │ Long     │ │ Short    │ │ Gross    │ │ Net      │ │ AI      ││
│  │ Balance  │ │ Exposure │ │ Exposure │ │ Exposure │ │ Exposure │ │ Insight ││
│  │ $2.5M    │ │ $2.1M    │ │ ($400K)  │ │ $2.5M    │ │ $1.7M    │ │ Card    ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘│
│                                                                              │
│  VOLATILITY                                                                  │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌─────────────────┐│
│  │ Portfolio Vol  │ │ SPY Volatility │ │ QQQ Volatility │ │ AI Insight      ││
│  │ 1Y  90D  Fwd   │ │ 1Y  90D  Fwd   │ │ 1Y  90D  Fwd   │ │ Card            ││
│  │ 18% 15%  14%   │ │ 15% 12%  11%   │ │ 22% 18%  17%   │ │                 ││
│  └────────────────┘ └────────────────┘ └────────────────┘ └─────────────────┘│
│                                                                              │
│  AI ASSISTANT                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                                                                          ││
│  │  CopilotPanel (compact variant)                                          ││
│  │  - Message history                                                       ││
│  │  - Quick prompts for home page context                                   ││
│  │  - Input field                                                           ││
│  │                                                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```
