# Command Center - Functional Specification

**Document Version**: 1.0
**Last Updated**: October 31, 2025
**Status**: Approved for Development

---

## Overview

The Command Center is the primary landing page for SigmaSight users. It provides an at-a-glance view of portfolio health, exposure metrics, holdings, and risk analytics in a professional, information-dense layout inspired by Bloomberg PORT.

**Design Philosophy**: Professional, Bloomberg-style information density. No "consumer app" feel - this is a tool for sophisticated investors managing complex portfolios.

---

## Hero Metrics - Single Row Layout

**Layout**: 6 metrics in a single horizontal row, equal visual weight, consistent typography.

```
┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ EQUITY BAL   │ TARGET RET   │ GROSS EXP    │ NET EXP      │ LONG EXP     │ SHORT EXP    │
│ $2,847,392   │ 12.5%        │ $5.2M        │ +$1.8M       │ $3.5M        │ -$1.7M       │
│ +$124K MTD ↑ │ +4.2% upside │ 182% NAV     │ +63% NAV     │ 122% NAV     │ -59% NAV     │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**Priority Order** (most important first):
1. **Equity Balance** - Total portfolio market value
2. **Target Return** - Weighted average target return from current prices
3. **Gross Exposure** - Sum of absolute values (longs + |shorts|)
4. **Net Exposure** - Net directional risk (longs - |shorts|)
5. **Long Exposure** - Total long position value
6. **Short Exposure** - Total short position value (shown as negative)

**Data Per Card**:
- **Line 1**: Metric label (all caps, consistent size)
- **Line 2**: Primary value (large, prominent)
- **Line 3**: Secondary context (MTD change, % of NAV, upside, etc.)

**Specifications**:
- Each card: ~16% width (6 columns, equal)
- Consistent padding, borders, typography
- Minimal decoration (no gradients, shadows - flat, professional)
- Color coding: Green for gains, red for losses, neutral for exposures

---

## Holdings Table - Bloomberg PORT Style

**Purpose**: Excel-like table showing all positions with performance, pricing, targets, and risk metrics. Sortable, scannable, actionable.

**Columns** (in order):

| Position | Quantity | Today's Price | Target Price | Market Value | Weight | P&L Today | P&L Total | Return % | Target Return | Beta | Actions |
|----------|----------|---------------|--------------|--------------|--------|-----------|-----------|----------|---------------|------|---------|
| NVDA     | 1,200    | $740.20       | $895.00      | $888,240     | 31.2%  | +$12,240  | +$142,350 | +19.1%   | 25%          | 1.85 | [AI] [•••] |
| TSLA     | -500     | $242.50       | $180.00      | -$121,250    | -4.3%  | -$1,850   | +$18,420  | +17.9%   | 18%          | 2.12 | [AI] [•••] |
| META     | 2,400    | $312.80       | $380.00      | $750,720     | 26.4%  | +$4,920   | +$88,240  | +13.3%   | 21.5%        | 1.24 | [AI] [•••] |

**Column Definitions**:
1. **Position** - Ticker symbol, SHORT indicator for short positions
2. **Quantity** - Number of shares (negative for shorts)
3. **Today's Price** - Current market price
4. **Target Price** - User-defined target price (from target_prices table)
5. **Market Value** - Quantity × Today's Price
6. **Weight** - % of total portfolio equity
7. **P&L Today** - Intraday profit/loss
8. **P&L Total** - Total realized + unrealized P&L since inception
9. **Return %** - Total return percentage
10. **Target Return** - Upside from current price to target price (calculated as `(Target Price - Today's Price) / Today's Price`)
11. **Beta** - Position beta (market sensitivity)
12. **Actions** - [AI] button for position analysis, [•••] menu for other actions (tag, edit, delete)

**Features**:
- ✅ **Sortable columns** - Click header to sort ascending/descending
- ✅ **Color coding** - Green/red for P&L, visual weight bars for concentration
- ✅ **Mini sparklines** - Optional 30-day price trend in P&L column
- ✅ **Sticky header** - Header stays visible when scrolling long lists
- ✅ **Row selection** - Click to highlight, shift-click for multi-select
- ✅ **Keyboard navigation** - Arrow keys to navigate, Enter to open details
- ✅ **Responsive** - Collapses to mobile card view on small screens

**Information Flow**:
Position → Quantity → Pricing (Today/Target) → Aggregate Value → Performance (P&L/Return) → Forward-Looking (Target Return/Beta) → Actions

**Rationale for Column Order**:
- Early left: Identity (Position, Quantity)
- Left-middle: Pricing transparency (shows Target Return calculation clearly)
- Middle: Performance metrics (P&L, Return %)
- Right-middle: Forward-looking (Target Return, Beta)
- Far right: Actions (AI, menu)

---

## Risk Metrics Section

**Purpose**: 5 key risk indicators that sophisticated investors use for portfolio construction and monitoring.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ RISK METRICS                                                            │
├──────────────┬──────────────┬──────────────┬──────────────┬────────────┤
│ Portfolio    │ Top Sector   │ Largest      │ S&P 500      │ Stress     │
│ Beta         │ Concentration│ Position     │ Correlation  │ Test       │
│              │              │              │              │            │
│ 1.32         │ Tech: 45%    │ NVDA: 31.2%  │ 0.76         │ ±1% Mkt:   │
│ (High risk)  │ vs 28% S&P   │ (High conc)  │ (Diversified)│ +$37.5K    │
│              │              │              │              │ -$39.2K    │
└──────────────┴──────────────┴──────────────┴──────────────┴────────────┘
```

**Metrics**:

1. **Portfolio Beta**
   - Calculation: Weighted average of position betas
   - Data source: `/api/v1/analytics/portfolio/{id}/overview` (beta field)
   - Interpretation: Beta > 1.2 = "High risk", 0.8-1.2 = "Moderate", < 0.8 = "Low risk"
   - Why it matters: Shows market sensitivity - how much portfolio moves vs S&P 500

2. **Top Sector Concentration**
   - Calculation: Largest sector exposure as % of portfolio, compared to S&P 500 benchmark
   - Data source: `/api/v1/analytics/portfolio/{id}/sector-exposure`
   - Display: "Tech: 45% vs 28% S&P" (shows overweight/underweight)
   - Why it matters: Sector concentration risk - are you too concentrated in one sector?

3. **Largest Position**
   - Calculation: Position with highest absolute weight
   - Data source: Derived from holdings table (max Weight column)
   - Display: "NVDA: 31.2%" with context label "(High conc)" if > 20%
   - Why it matters: Single-name risk - one position going wrong can sink portfolio

4. **S&P 500 Correlation**
   - Calculation: Portfolio correlation to S&P 500 index
   - Data source: `/api/v1/analytics/portfolio/{id}/correlation-matrix` (find SPY correlation)
   - Interpretation: > 0.8 = "Highly correlated", 0.5-0.8 = "Diversified", < 0.5 = "Uncorrelated"
   - Why it matters: Shows diversification benefit - lower correlation = more alpha potential

5. **Stress Test (±1% Market Move)**
   - Calculation:
     - Market +1%: `Net Exposure × Portfolio Beta × 1%`
     - Market -1%: `Net Exposure × Portfolio Beta × -1%`
   - Data source: Net Exposure from hero metrics, Beta from analytics
   - Display: "+$37.5K / -$39.2K" (up move / down move)
   - Example: Net Exposure = $1.8M, Beta = 1.32 → 1% up = $1.8M × 1.32 × 1% = $23,760
   - Why it matters: Real dollar impact of market moves - helps size exposure appropriately

**Layout**: 5 equal-width cards in a single row, consistent with hero metrics style.

---

## AI Integration - Contextual Buttons (Not Persistent Sidebar)

**Key Decision**: Side panel AI agent hasn't worked well in testing. Instead, use contextual AI buttons that open focused modals.

**AI Touchpoints**:

1. **Per-Row AI Buttons** (Holdings Table)
   - Button: [AI] in Actions column
   - Behavior: Click → Opens modal with 3-5 key insights about that position
   - Example for NVDA:
     ```
     ┌─────────────────────────────────────────────┐
     │ NVIDIA (NVDA) - AI Analysis                 │
     ├─────────────────────────────────────────────┤
     │ • Your largest position at 31% of portfolio │
     │ • Up 19% vs 25% target - on track          │
     │ • Beta 1.85 adds significant market risk   │
     │ • Tech sector now 45% of portfolio (vs     │
     │   28% S&P 500 weight)                       │
     │ • High correlation (0.82) with 4 other     │
     │   tech positions                            │
     │                                             │
     │ [View Full Analysis] [Dismiss]              │
     └─────────────────────────────────────────────┘
     ```

2. **AI Explain Buttons** (Risk Metrics)
   - Button: Small [?] icon on each risk metric card
   - Behavior: Click → Opens modal explaining what the metric means and why it matters FOR THIS PORTFOLIO
   - Example for Portfolio Beta = 1.32:
     ```
     ┌─────────────────────────────────────────────┐
     │ Portfolio Beta - Explained                  │
     ├─────────────────────────────────────────────┤
     │ Your portfolio beta is 1.32, which means    │
     │ when the market moves 1%, your portfolio    │
     │ typically moves 1.32%.                      │
     │                                             │
     │ This is driven by:                          │
     │ • Large positions in high-beta tech stocks  │
     │   (NVDA: β=1.85, TSLA: β=2.12)             │
     │ • Net long exposure of $1.8M               │
     │                                             │
     │ Your beta is higher than average (1.0),     │
     │ indicating above-average market risk.       │
     │                                             │
     │ [Dismiss]                                   │
     └─────────────────────────────────────────────┘
     ```

3. **Key Findings Section** (Below Hero Metrics, Optional)
   - Collapsible section showing 3-5 most important overnight batch insights
   - Example:
     ```
     ┌─────────────────────────────────────────────────────────┐
     │ ✨ KEY FINDINGS (3)                        [Expand ▼]   │
     ├─────────────────────────────────────────────────────────┤
     │ ⚠ Tech concentration increased to 45% (from 38% last    │
     │   week) - consider rebalancing                          │
     │ ℹ Portfolio beta rose from 1.18 to 1.32 - increased    │
     │   market sensitivity                                    │
     │ ✓ 8 of 12 positions are above target price - strong    │
     │   performance                                           │
     └─────────────────────────────────────────────────────────┘
     ```

**Design Principles**:
- ✅ **User-invoked**: User clicks AI button when they want analysis (not auto-displayed)
- ✅ **Focused insights**: 3-5 bullets max, specific to the context (position or metric)
- ✅ **Modal-based**: Opens in centered modal/dialog, easy to dismiss
- ✅ **No recommendations**: Analytical insights only, no "Buy/Sell/Hold" advice
- ✅ **Fast**: Pre-computed insights from overnight batch (not real-time LLM calls)

---

## Data Sources (Backend APIs)

**Hero Metrics**:
- `/api/v1/analytics/portfolio/{id}/overview` - Equity balance, exposures, net/gross/long/short
- Target Return: Calculated from `/api/v1/target-prices` (weighted average of position target returns)

**Holdings Table**:
- `/api/v1/data/positions/details` - Position details with P&L, quantities, market values
- `/api/v1/data/prices/quotes` - Real-time today's prices
- `/api/v1/target-prices` - Target prices (user-defined)
- `/api/v1/analytics/portfolio/{id}/positions/factor-exposures` - Position betas

**Risk Metrics**:
- `/api/v1/analytics/portfolio/{id}/overview` - Portfolio beta
- `/api/v1/analytics/portfolio/{id}/sector-exposure` - Sector concentration vs S&P 500
- `/api/v1/analytics/portfolio/{id}/correlation-matrix` - S&P 500 correlation
- Largest Position: Derived from holdings table
- Stress Test: Calculated from net exposure + beta

**AI Insights**:
- `/api/v1/chat/conversations/{id}/send` - Send message to AI agent (SSE streaming)
- Pre-computed insights: To be implemented (batch job generates overnight insights)

---

## User Interactions

**On Page Load**:
1. Fetch portfolio overview data (hero metrics + risk metrics)
2. Fetch positions data (holdings table)
3. Fetch target prices
4. Calculate derived metrics (Target Return weighted avg, Stress Test)
5. Sort holdings table by Weight descending (largest positions first)

**User Actions**:
- **Sort table**: Click column header → Re-sort rows
- **Select rows**: Click row → Highlight, Shift+Click → Multi-select
- **AI analysis**: Click [AI] button → Open modal with position insights
- **Risk explanations**: Click [?] on risk metric → Open explanation modal
- **Expand Key Findings**: Click "Expand ▼" → Show/hide overnight insights
- **Edit position**: Click [•••] menu → Options (Tag, Edit, Delete, etc.)

---

## Layout Structure (Top to Bottom)

```
┌─────────────────────────────────────────────────────────────────────┐
│ COMMAND CENTER                                      [Portfolio ▼]   │ ← Header
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────┬─────┬─────┬─────┬─────┬─────┐                             │
│ │ EQ  │ TGT │ GRS │ NET │ LNG │ SHT │  ← Hero Metrics Row         │
│ │ BAL │ RET │ EXP │ EXP │ EXP │ EXP │                             │
│ └─────┴─────┴─────┴─────┴─────┴─────┘                             │
│                                                                     │
│ ✨ KEY FINDINGS (3)                              [Expand ▼]        │ ← Optional
│                                                                     │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ HOLDINGS                                    [🔍 Search] [↓CSV] │ │
│ ├─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─┤ │
│ │ Pos │ Qty │ $ │ Tgt │ Val │ Wgt │ P&L │ P&L │ Ret │ Tgt │ β│ │
│ │     │     │   │  $  │     │     │ Tdy │ Tot │  %  │ Ret │  │ │
│ ├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─┤ │
│ │ NVDA│ 1.2K│ 740 │ 895 │888K │31.2%│+12K │+142K│+19% │ 25% │••│ │
│ │ META│ 2.4K│ 313 │ 380 │751K │26.4%│+4.9K│+88K │+13% │21.5%│••│ │
│ │ ... │ ... │ ... │ ... │ ... │ ... │ ... │ ... │ ... │ ... │••│ │
│ └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─┘ │
│                                                                     │
│ ┌───────────────────────────────────────────────────────────────┐ │
│ │ RISK METRICS                                                  │ │
│ ├─────┬─────┬─────┬─────┬─────┐                                │ │
│ │ β   │ Sect│ Top │ Corr│Strss│  ← 5 Risk Cards                │ │
│ │1.32 │Tech │NVDA │0.76 │±1%: │                                │ │
│ │     │ 45% │31.2%│     │+37K │                                │ │
│ └─────┴─────┴─────┴─────┴─────┘                                │ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Responsive Behavior

**Desktop (≥1024px)**:
- Hero metrics: 6-column row, equal width
- Holdings table: All columns visible
- Risk metrics: 5-column row, equal width

**Tablet (768-1023px)**:
- Hero metrics: 6-column row (may need horizontal scroll)
- Holdings table: Hide Today's Price, Target Price columns (show on row tap)
- Risk metrics: 5-column row or stack to 3+2 layout

**Mobile (<768px)**:
- Hero metrics: Swipeable horizontal scroll, 2 visible at a time
- Holdings table: Card view (not table), show Position, Value, Return %, Target Return only
- Risk metrics: Stack vertically (5 cards, full width each)

---

## Success Metrics

**Usage KPIs**:
- Time to key insight < 5 seconds (view portfolio health + largest positions)
- Holdings table interaction rate > 60% (users sort/select rows)
- AI button click rate > 20% (users invoke AI analysis)

**Business KPIs**:
- Daily active users (DAU) increase 2x
- Session duration increase 30%+
- User satisfaction (NPS) > 50

---

## Technical Implementation Notes

**Frontend Components**:
- `<CommandCenter />` - Main page container
- `<HeroMetricsRow />` - 6 metric cards
- `<HoldingsTable />` - Bloomberg-style data table (sortable, selectable)
- `<RiskMetricsRow />` - 5 risk metric cards
- `<AIInsightModal />` - Position-level AI analysis modal
- `<RiskExplanationModal />` - Risk metric explanation modal
- `<KeyFindingsSection />` - Collapsible overnight insights

**State Management**:
- Use `usePortfolioData()` hook to fetch all data
- Store selected portfolio ID in Zustand (`usePortfolioStore`)
- Table sort state in local component state (not global)

**Performance**:
- Lazy load holdings table (virtualized rows if > 100 positions)
- Pre-compute Target Return weighted average (not real-time)
- Cache AI insights (don't re-fetch on every modal open)

---

## Open Questions / Future Enhancements

1. **Key Findings Section**: Should this be collapsed by default or expanded? User testing needed.
2. **Sparklines**: Do we need mini price charts in P&L columns, or is this too cluttered?
3. **Real-time updates**: Should prices update live (WebSocket) or on refresh only?
4. **Export to CSV**: Should holdings table have "Export to CSV" button?
5. **Custom columns**: Should users be able to show/hide table columns?

---

## Appendix: Target Return Calculation Logic

**Position-Level Target Return**:
```python
target_return = (target_price - today_price) / today_price
# Example: (895 - 740) / 740 = 0.2095 = 20.95%
```

**Portfolio-Level Target Return** (Weighted Average):
```python
portfolio_target_return = sum(
    position_weight × position_target_return
    for each position with target price
)
# Example:
# NVDA: 31.2% weight × 25% target = 7.8%
# META: 26.4% weight × 21.5% target = 5.68%
# ... sum all positions = 12.5% portfolio target return
```

---

**Status**: ✅ Approved for visual design and development
**Next Steps**: Create Tailwind visual specs, then begin component development
