# Command Center - Primary Dashboard Specification

**Document Version**: 1.0
**Last Updated**: October 30, 2025
**Status**: Detailed Specification
**Replaces**: Current Dashboard page

---

## Table of Contents

1. [Overview](#overview)
2. [Layout Specification](#layout-specification)
3. [Component Specifications](#component-specifications)
4. [Data Sources & APIs](#data-sources--apis)
5. [Interactions & Behaviors](#interactions--behaviors)
6. [Responsive Design](#responsive-design)
7. [Implementation Guide](#implementation-guide)

---

## Overview

### Purpose

The **Command Center** is the primary landing page and decision-making hub for SigmaSight users. It replaces the current Dashboard with an exposure-first, AI-enhanced interface that provides portfolio health, risk posture, and actionable insights at a glance.

### Key Objectives

1. **Exposure-First**: Net/gross/long/short metrics prominently displayed (not buried)
2. **Portfolio Health**: Single composite score indicating overall portfolio status
3. **Proactive AI**: Insights and alerts surfaced automatically (not on-demand)
4. **Benchmark Context**: Always show metrics vs S&P 500 for meaningful comparison
5. **Action-Oriented**: Quick actions and AI suggestions for next steps

### User Questions Answered

Within 5 seconds of landing on Command Center, users should be able to answer:
- ✅ "What's my overall portfolio health?" → **Portfolio Health Score**
- ✅ "What's my net worth and recent change?" → **Hero Metrics**
- ✅ "Am I net long or net short?" → **Exposure Gauge**
- ✅ "What's my biggest risk?" → **AI Insights Cards**
- ✅ "How am I positioned vs the market?" → **Sector Exposure vs S&P 500**
- ✅ "What changed recently?" → **Recent Activity Feed**

---

## Layout Specification

### Desktop Layout (≥1024px)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ TOP NAVIGATION BAR                                                       │
│ [SigmaSight] Command Center Positions Risk Organize    [User] [AI ✨]   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                         COMMAND CENTER                                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓  │
│  ┃  PORTFOLIO HEALTH SCORE                                          ┃  │
│  ┃  ╔═══════════════════════════════════════════════════════════╗  ┃  │
│  ┃  ║  82/100  ████████████████░░░░░░░░                         ║  ┃  │
│  ┃  ║  ● Beta: 1.15  ● Volatility: 18%  ● Concentration: Low    ║  ┃  │
│  ┃  ╚═══════════════════════════════════════════════════════════╝  ┃  │
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛  │
│                                                                          │
│  ┌────────────────┬────────────────┬────────────────┬────────────────┐  │
│  │ NET WORTH      │ NET EXPOSURE   │ GROSS EXPOSURE │ P&L MTD        │  │
│  │ $500,000       │ $100K (20%)    │ $500K (100%)   │ +$12,500       │  │
│  │ +2.5% MTD ↑    │ [Gauge ────→]  │                │ +2.5% ↑        │  │
│  │ +8.2% YTD      │                │                │                │  │
│  └────────────────┴────────────────┴────────────────┴────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ EXPOSURE BREAKDOWN                                               │  │
│  │ Long:  $300K (60%) ████████████░░░░░░░░░░░░░░░░░░░░            │  │
│  │ Short: $200K (40%) ████████░░░░░░░░░░░░░░░░░░░░░░░░            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ ✨ AI INSIGHTS & ALERTS                                    [3]   │  │
│  │ ──────────────────────────────────────────────────────────────── │  │
│  │ ⚠  Tech Concentration Alert                          [Details ▶] │  │
│  │    Your tech exposure is 45%, +15% above S&P 500.                │  │
│  │    Consider diversifying into other sectors.                     │  │
│  │    [AI Explain] [Suggest Rebalancing]                            │  │
│  │                                                                   │  │
│  │ ℹ  Volatility Spike Detected                         [Details ▶] │  │
│  │    Portfolio volatility increased to 21% (from 15%) due to       │  │
│  │    tech sector rotation. Your portfolio is more sensitive now.   │  │
│  │    [Show Breakdown] [AI Explain]                                 │  │
│  │                                                                   │  │
│  │ ✅ On Track for Annual Return Goal                   [Details ▶] │  │
│  │    You're up 8.2% YTD, on pace for 12% annual return.            │  │
│  │    [View Performance Details]                                    │  │
│  │                                                                   │  │
│  │                                                      [View All →] │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────┬───────────────────────────────────┐  │
│  │ SECTOR EXPOSURE vs S&P 500   │  FACTOR EXPOSURES                 │  │
│  │ ────────────────────────────  │  ─────────────────────────────    │  │
│  │ Technology                    │  Size (Small Cap)       +0.8σ    │  │
│  │  45% ████████ +15% vs SPY    │  Value                  -1.2σ    │  │
│  │ Financials                    │  Momentum               +2.1σ    │  │
│  │  12% ██       -1% vs SPY     │  Quality                +0.5σ    │  │
│  │ Healthcare                    │  Market Beta            +1.15    │  │
│  │  14% ███      +0% vs SPY     │                                   │  │
│  │ Industrials                   │  [View Full Factors →]           │  │
│  │   8% █        -1% vs SPY     │                                   │  │
│  │ Energy                        │                                   │  │
│  │   5% █        -1% vs SPY     │                                   │  │
│  │ ...                           │                                   │  │
│  │ [View All Sectors →]         │                                   │  │
│  └──────────────────────────────┴───────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ TOP POSITIONS (by absolute value)                      [View All] │  │
│  │ ────────────────────────────────────────────────────────────────  │  │
│  │ 1. NVDA  │ $88,000  │ LONG   │ +$12,000 (15.8%) │ [AI Explain]  │  │
│  │ 2. TSLA  │ $40,000  │ SHORT  │ -$2,100 (-5.2%)  │ [AI Explain]  │  │
│  │ 3. META  │ $75,000  │ LONG   │ +$8,500 (12.8%)  │ [AI Explain]  │  │
│  │ 4. AAPL  │ $62,000  │ LONG   │ +$4,200 (7.3%)   │ [AI Explain]  │  │
│  │ 5. MSFT  │ $55,000  │ LONG   │ +$6,800 (14.1%)  │ [AI Explain]  │  │
│  │ ...                                                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ RECENT ACTIVITY (Last 7 Days)                         [View All]  │  │
│  │ ────────────────────────────────────────────────────────────────  │  │
│  │ Oct 29 • NVDA price +$25 (6.0%) → Position value +$5,000         │  │
│  │ Oct 28 • Portfolio volatility increased to 21% (from 18%)         │  │
│  │ Oct 27 • Tech sector concentration reached 45% (+5% this week)    │  │
│  │ Oct 26 • TSLA short position down $1,200 (short squeeze)          │  │
│  │ Oct 25 • Correlation between NVDA and MSFT increased to 0.92      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Visual Hierarchy

**Layer 1: Hero Section** (top, most prominent)
- Portfolio Health Score (largest, attention-grabbing)

**Layer 2: Key Metrics** (sub-hero, 4 cards)
- Net Worth, Net Exposure, Gross Exposure, P&L MTD

**Layer 3: Exposure Visualization**
- Exposure breakdown bars (long vs short)

**Layer 4: AI Insights** (proactive alerts)
- Insight cards with actions

**Layer 5: Analytics Summaries** (2 columns)
- Sector Exposure vs S&P 500 (left)
- Factor Exposures (right)

**Layer 6: Position & Activity Details** (tables)
- Top Positions
- Recent Activity Feed

---

## Component Specifications

### 1. Portfolio Health Score

**Purpose**: Single composite metric indicating overall portfolio status

**Visual Design**:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  PORTFOLIO HEALTH SCORE                            ┃
┃  ╔════════════════════════════════════════════╗    ┃
┃  ║  82/100  ████████████████░░░░░░░░          ║    ┃
┃  ║  ● Beta: 1.15  ● Volatility: 18%           ║    ┃
┃  ║  ● Concentration: Low (HHI: 0.08)          ║    ┃
┃  ║                              [Details ▼]   ║    ┃
┃  ╚════════════════════════════════════════════╝    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Score Calculation**:
```typescript
portfolioHealthScore = weighted_average({
  beta_score: inverse_normalize(abs(beta - 1.0)),  // Ideal beta = 1.0, weight: 25%
  volatility_score: inverse_normalize(volatility),  // Lower is better, weight: 30%
  concentration_score: inverse_normalize(HHI),      // Lower is better, weight: 25%
  diversification_score: correlation_avg_score,     // Lower avg correlation is better, weight: 20%
})

// Normalize to 0-100 scale
// 90-100: Excellent (green)
// 70-89: Good (blue)
// 50-69: Fair (yellow)
// <50: Poor (red)
```

**Data Sources**:
- Beta: `/api/v1/analytics/portfolio/{id}/overview` → `beta`
- Volatility: `/api/v1/analytics/portfolio/{id}/volatility` → `annualized_volatility`
- HHI: `/api/v1/analytics/portfolio/{id}/concentration` → `hhi`
- Correlations: `/api/v1/analytics/portfolio/{id}/correlation-matrix` → avg correlation

**Interactions**:
- Hover → Tooltip explains score breakdown
- Click "Details" → Expands to show component scores and AI explanation
- Click "AI Explain" → AI sidebar opens: "Your portfolio health is 82/100. Here's why..."

**Component API**:
```typescript
<PortfolioHealthScore
  score={82}
  beta={1.15}
  volatility={0.18}
  hhi={0.08}
  loading={false}
  onDetailsClick={() => expandScoreBreakdown()}
/>
```

---

### 2. Hero Metrics Cards (4 Cards)

**Card 1: Net Worth**
```
┌────────────────────┐
│ NET WORTH          │
│ $500,000           │
│ +$12,500 (+2.5%) ↑ │  ← MTD change
│ +$38,200 (+8.2%) ↑ │  ← YTD change
│ [Sparkline chart]  │  ← Trend last 30 days
└────────────────────┘
```

**Data Sources**:
- Net Worth: Sum of all position market values (long - short)
- MTD Change: Compare to value 30 days ago
- YTD Change: Compare to value on January 1
- Sparkline: Daily values for last 30 days

**Card 2: Net Exposure**
```
┌────────────────────┐
│ NET EXPOSURE       │
│ $100,000 (20%)     │  ← Net long
│                    │
│ ┌─────────────────┐│
│ │░░░░░░█░░░░░░░░░ ││  ← Gauge visualization
│ │ -100%  0%  100% ││
│ └─────────────────┘│
│ 20% Net Long       │
└────────────────────┘
```

**Calculation**:
```typescript
net_exposure = long_exposure - short_exposure
net_exposure_pct = net_exposure / gross_exposure * 100
// Range: -100% (fully short) to +100% (fully long)
```

**Gauge Color Coding**:
- Net Long (>10%): Green zone
- Neutral (-10% to +10%): Gray zone
- Net Short (<-10%): Red zone

**Card 3: Gross Exposure**
```
┌────────────────────┐
│ GROSS EXPOSURE     │
│ $500,000 (100%)    │  ← % of net worth
│                    │
│ Long:  $300K (60%) │
│ Short: $200K (40%) │
└────────────────────┘
```

**Calculation**:
```typescript
gross_exposure = abs(long_exposure) + abs(short_exposure)
gross_exposure_pct = gross_exposure / net_worth * 100
// Can exceed 100% with leverage
```

**Card 4: P&L MTD**
```
┌────────────────────┐
│ P&L MTD            │
│ +$12,500           │
│ +2.5% ↑            │
│ [Sparkline chart]  │  ← Daily P&L last 30 days
│ Best: NVDA +$5K    │  ← Top contributor
│ Worst: TSLA -$2K   │  ← Bottom contributor
└────────────────────┘
```

**Data Sources**:
- P&L: `/api/v1/data/positions/details` → sum of `unrealized_pnl`
- MTD: Filter to positions held for >30 days, calculate change
- Contributors: Sort positions by P&L, show top gainer/loser

**Component API**:
```typescript
<MetricCard
  title="Net Worth"
  value={500000}
  change={{ amount: 12500, percentage: 2.5, period: 'MTD' }}
  ytdChange={{ amount: 38200, percentage: 8.2 }}
  sparkline={dailyValues}
  loading={false}
/>
```

---

### 3. Exposure Breakdown Bars

**Visual Design**:
```
┌──────────────────────────────────────────────────────────┐
│ EXPOSURE BREAKDOWN                                       │
│ ──────────────────────────────────────────────────────── │
│ Long:  $300,000 (60%)  ████████████░░░░░░░░░░░░░░░░░   │
│ Short: $200,000 (40%)  ████████░░░░░░░░░░░░░░░░░░░░░   │
│                                                          │
│ Net Exposure: $100,000 (20% Net Long)                    │
└──────────────────────────────────────────────────────────┘
```

**Bar Chart**:
- Stacked horizontal bars
- Long bar: Green
- Short bar: Red
- Width proportional to % of gross exposure

**Interactions**:
- Hover → Tooltip shows detailed breakdown (# positions, top 3 positions)
- Click Long bar → Navigate to Positions workspace, Long tab
- Click Short bar → Navigate to Positions workspace, Short tab

---

### 4. AI Insights & Alerts

**Purpose**: Proactively surface anomalies, risks, and opportunities

**Insight Card Structure**:
```
┌─────────────────────────────────────────────────────────┐
│ [Icon] Insight Title                       [Details ▶]  │
│ ──────────────────────────────────────────────────────  │
│ Plain-English summary of the insight (2-3 sentences).   │
│ Explains what happened and why it matters.              │
│ [Primary Action Button] [Secondary Action Button]       │
└─────────────────────────────────────────────────────────┘
```

**Insight Types**:

**1. Concentration Alert** (⚠ Warning Icon)
```
⚠  Tech Concentration Alert
   Your tech exposure is 45%, +15% above S&P 500.
   This creates concentration risk if the sector declines.
   [AI Explain] [Suggest Rebalancing]
```

**2. Volatility Spike** (ℹ Info Icon)
```
ℹ  Volatility Spike Detected
   Portfolio volatility increased to 21% (from 15%) due to
   tech sector rotation. Your portfolio is more sensitive now.
   [Show Breakdown] [AI Explain]
```

**3. Performance Update** (✅ Success Icon)
```
✅ On Track for Annual Return Goal
   You're up 8.2% YTD, on pace for 12% annual return.
   Portfolio health score: 82/100.
   [View Performance Details]
```

**4. Correlation Risk** (⚠ Warning Icon)
```
⚠  High Correlation Detected
   NVDA and MSFT correlation increased to 0.92 (from 0.75).
   This reduces diversification benefits.
   [Show Correlations] [Suggest Hedge]
```

**5. Rebalancing Opportunity** (💡 Suggestion Icon)
```
💡 Rebalancing Opportunity
   3 positions have drifted >5% from target allocations.
   Consider rebalancing to maintain strategy.
   [View Positions] [AI Calculate Trades]
```

**Data Sources**:
- Generated by backend batch job (nightly or hourly)
- Stored in database table: `ai_insights`
- Fetched via: `/api/v1/insights/portfolio/{id}` (new endpoint)

**AI Generation Logic** (Backend):
```python
async def generate_insights(portfolio_id: UUID):
    insights = []

    # Check sector concentration
    sector_exposure = await get_sector_exposure(portfolio_id)
    for sector, pct in sector_exposure.items():
        benchmark_pct = SPY_SECTOR_WEIGHTS[sector]
        if pct > benchmark_pct + 15:  # >15% overweight
            insights.append({
                'type': 'concentration_alert',
                'severity': 'warning',
                'title': f'{sector} Concentration Alert',
                'summary': f'Your {sector.lower()} exposure is {pct}%, +{pct - benchmark_pct}% above S&P 500. This creates concentration risk if the sector declines.',
                'actions': ['AI Explain', 'Suggest Rebalancing']
            })

    # Check volatility changes
    current_vol = await get_volatility(portfolio_id)
    prev_vol = await get_volatility(portfolio_id, days_ago=7)
    if current_vol > prev_vol * 1.3:  # >30% increase
        insights.append({
            'type': 'volatility_spike',
            'severity': 'info',
            'title': 'Volatility Spike Detected',
            'summary': f'Portfolio volatility increased to {current_vol:.0%} (from {prev_vol:.0%}) due to recent market movements. Your portfolio is more sensitive to market swings now.',
            'actions': ['Show Breakdown', 'AI Explain']
        })

    # Check performance vs goal
    ytd_return = await get_ytd_return(portfolio_id)
    target_return = 0.12  # 12% annual target (from user settings or default)
    if ytd_return >= target_return * (days_ytd / 365):  # On track
        insights.append({
            'type': 'performance_update',
            'severity': 'success',
            'title': 'On Track for Annual Return Goal',
            'summary': f"You're up {ytd_return:.1%} YTD, on pace for {ytd_return / (days_ytd / 365):.1%} annual return.",
            'actions': ['View Performance Details']
        })

    # ... more insight types

    return insights
```

**Component API**:
```typescript
<AIInsightsSection
  insights={[
    {
      id: '1',
      type: 'concentration_alert',
      severity: 'warning',
      title: 'Tech Concentration Alert',
      summary: 'Your tech exposure is 45%, +15% above S&P 500...',
      actions: [
        { label: 'AI Explain', onClick: () => openAI('explain concentration') },
        { label: 'Suggest Rebalancing', onClick: () => openAI('suggest rebalancing') }
      ]
    },
    // ... more insights
  ]}
  maxVisible={3}  // Show top 3, rest hidden behind "View All"
  onViewAll={() => navigate('/insights')}
/>
```

---

### 5. Sector Exposure vs S&P 500

**Purpose**: Show portfolio sector weights compared to benchmark

**Visual Design**:
```
┌─────────────────────────────────────────┐
│ SECTOR EXPOSURE vs S&P 500              │
│ ───────────────────────────────────────  │
│ Technology                               │
│  Portfolio: 45%  ████████  +15% vs SPY │
│  S&P 500:   30%  ──────                 │
│                                          │
│ Financials                               │
│  Portfolio: 12%  ██        -1% vs SPY  │
│  S&P 500:   13%  ───                    │
│                                          │
│ Healthcare                               │
│  Portfolio: 14%  ███       +0% vs SPY  │
│  S&P 500:   14%  ───                    │
│                                          │
│ ... (top 5 sectors shown, rest collapsed)│
│ [View All Sectors →]                    │
└─────────────────────────────────────────┘
```

**Bar Chart Details**:
- Portfolio bar (filled, color-coded):
  - Green if overweight (>2% vs benchmark)
  - Red if underweight (<-2% vs benchmark)
  - Gray if neutral (-2% to +2%)
- Benchmark line (dashed gray line at benchmark %)
- Delta label (+X% or -X%)

**Data Sources**:
- Portfolio sectors: `/api/v1/analytics/portfolio/{id}/sector-exposure` → `sector_exposures`
- Benchmark (S&P 500): Hardcoded constants or API (`SPY_SECTOR_WEIGHTS`)

**Benchmark Data** (S&P 500 approximate weights):
```typescript
const SPY_SECTOR_WEIGHTS = {
  'Technology': 0.30,
  'Financials': 0.13,
  'Healthcare': 0.14,
  'Consumer Discretionary': 0.11,
  'Communication Services': 0.09,
  'Industrials': 0.08,
  'Consumer Staples': 0.06,
  'Energy': 0.04,
  'Utilities': 0.03,
  'Real Estate': 0.02,
  'Materials': 0.02
}
```

**Interactions**:
- Hover sector → Tooltip shows top 3 positions in that sector
- Click sector → Navigate to Positions workspace, filtered by sector
- Click "View All" → Navigate to Risk Analytics > Exposure tab

---

### 6. Factor Exposures Summary

**Purpose**: Show portfolio's factor tilts (Growth, Value, Size, Momentum, Quality)

**Visual Design**:
```
┌──────────────────────────────────────┐
│ FACTOR EXPOSURES                     │
│ ────────────────────────────────────  │
│ Size (Small Cap)        +0.8σ  ████ │
│ Value                   -1.2σ  █    │
│ Momentum (Growth)       +2.1σ  ████ │
│ Quality                 +0.5σ  ██   │
│ Market Beta              1.15       │
│                                      │
│ [View Full Factors →]               │
└──────────────────────────────────────┘
```

**Factor Interpretation**:
- **Positive σ**: Exposure to factor (e.g., +2.1σ = strong growth tilt)
- **Negative σ**: Opposite exposure (e.g., -1.2σ = value tilt, not growth)
- **Market Beta**: Overall market sensitivity (1.0 = matches market)

**Data Sources**:
- Factor exposures: `/api/v1/analytics/portfolio/{id}/factor-exposures` → `factor_exposures`

**Component displays**:
- Top 4 factors (highest absolute σ)
- Market Beta always shown
- Bar chart: Length = abs(σ), color = direction (green positive, red negative)

**Interactions**:
- Hover factor → Tooltip explains (e.g., "Growth +2.1σ: Your portfolio tilts toward high-growth stocks")
- Click factor → Navigate to Risk Analytics > Factors tab
- Click "View Full Factors" → Navigate to Risk Analytics > Factors tab

---

### 7. Top Positions Table

**Purpose**: Show largest positions by absolute value (long and short)

**Table Structure**:
```
┌──────────────────────────────────────────────────────────────────┐
│ TOP POSITIONS (by absolute value)                   [View All →] │
│ ────────────────────────────────────────────────────────────────  │
│ Rank │ Symbol │ Value    │ Type  │ P&L            │ Actions      │
│ ─────┼────────┼──────────┼───────┼────────────────┼──────────────│
│  1   │ NVDA   │ $88,000  │ LONG  │ +$12K (+15.8%) │ [AI Explain] │
│  2   │ TSLA   │ $40,000  │ SHORT │ -$2.1K (-5.2%) │ [AI Explain] │
│  3   │ META   │ $75,000  │ LONG  │ +$8.5K (+12.8%)│ [AI Explain] │
│  4   │ AAPL   │ $62,000  │ LONG  │ +$4.2K (+7.3%) │ [AI Explain] │
│  5   │ MSFT   │ $55,000  │ LONG  │ +$6.8K (+14.1%)│ [AI Explain] │
│ ...                                                                │
└──────────────────────────────────────────────────────────────────┘
```

**Columns**:
1. **Rank**: 1-10 (top 10 shown by default)
2. **Symbol**: Stock ticker
3. **Value**: Absolute market value (abs for shorts)
4. **Type**: LONG, SHORT, OPTION, PRIVATE
5. **P&L**: Unrealized P&L ($ and %)
6. **Actions**: "AI Explain" button

**Sorting**:
- Default: By absolute value (descending)
- User can click column headers to re-sort

**Data Sources**:
- Positions: `/api/v1/data/positions/details` → filter by portfolio
- Sort by `abs(market_value)`, take top 10

**Interactions**:
- Click row → Navigate to Positions workspace, expand position details (side panel)
- Click "AI Explain" → AI sidebar opens: "NVDA is your largest position at $88K (17.6% of portfolio). It's up 15.8% recently due to..."
- Click "View All" → Navigate to Positions workspace

---

### 8. Recent Activity Feed

**Purpose**: Show recent changes and events (last 7 days)

**Feed Structure**:
```
┌──────────────────────────────────────────────────────────────────┐
│ RECENT ACTIVITY (Last 7 Days)                      [View All →]  │
│ ────────────────────────────────────────────────────────────────  │
│ Oct 29 • NVDA price +$25 (6.0%) → Position value +$5,000         │
│ Oct 28 • Portfolio volatility increased to 21% (from 18%)         │
│ Oct 27 • Tech sector concentration reached 45% (+5% this week)    │
│ Oct 26 • TSLA short position down $1,200 (short squeeze)          │
│ Oct 25 • Correlation between NVDA and MSFT increased to 0.92      │
│ ...                                                                │
└──────────────────────────────────────────────────────────────────┘
```

**Activity Types**:
1. **Price changes** (>5% in a day)
2. **Volatility changes** (>20% change in portfolio vol)
3. **Sector concentration changes** (>5% change in sector weight)
4. **Position P&L changes** (>10% change in position P&L)
5. **Correlation changes** (>0.1 change in correlation)
6. **New insights generated** (AI detected anomaly)

**Data Sources**:
- Generated by batch job, stored in `activity_feed` table
- Fetched via: `/api/v1/activity/portfolio/{id}?days=7` (new endpoint)

**Interactions**:
- Click activity → Navigate to relevant view (position, risk metric, etc.)
- Click "View All" → Navigate to full activity log page

---

## Data Sources & APIs

### Required API Endpoints

**Existing Endpoints** (already implemented):
1. `/api/v1/analytics/portfolio/{id}/overview` - Portfolio metrics (beta, Sharpe, etc.)
2. `/api/v1/analytics/portfolio/{id}/sector-exposure` - Sector weights vs S&P 500
3. `/api/v1/analytics/portfolio/{id}/concentration` - HHI, top 10 positions %
4. `/api/v1/analytics/portfolio/{id}/factor-exposures` - Portfolio factor betas
5. `/api/v1/analytics/portfolio/{id}/volatility` - Volatility metrics, HAR forecast
6. `/api/v1/analytics/portfolio/{id}/correlation-matrix` - Position correlations
7. `/api/v1/data/positions/details` - Position details with P&L
8. `/api/v1/data/portfolio/{id}/complete` - Full portfolio snapshot

**New Endpoints** (need to implement):
9. `/api/v1/insights/portfolio/{id}` - AI-generated insights and alerts
10. `/api/v1/activity/portfolio/{id}?days=N` - Recent activity feed
11. `/api/v1/analytics/portfolio/{id}/health-score` - Portfolio health score calculation

### Data Refresh Strategy

**Real-Time** (on page load, every refresh):
- Net worth, exposures, P&L (from positions)
- Position prices (market data)

**Cached** (updated every 5 minutes):
- Sector exposures
- Factor exposures
- Volatility metrics

**Batch** (updated daily via batch job):
- Correlations
- Stress test results
- AI insights

**User-Triggered** (on demand):
- "Refresh" button re-fetches all data
- Show loading states during refresh

---

## Interactions & Behaviors

### Page Load Sequence

1. **Skeleton Loading** (0-500ms):
   - Show skeleton placeholders for all components
   - Ensures no layout shift

2. **Initial Data Fetch** (500-2000ms):
   - Fetch critical data in parallel:
     - Portfolio overview
     - Position details
     - Sector exposure
     - AI insights
   - Render components as data arrives (progressive rendering)

3. **Secondary Data** (2000-4000ms):
   - Fetch nice-to-have data:
     - Factor exposures
     - Recent activity feed
     - Sparkline historical data
   - Render when available (non-blocking)

4. **Ready State** (4000ms+):
   - All components rendered
   - User can interact

### Loading States

**Skeleton Placeholders**:
```
┌────────────────────┐
│ ███████            │  ← Shimmer effect
│ ████████████       │
│ ██████             │
└────────────────────┘
```

**Spinners**:
- Use for user-triggered actions (e.g., "Refresh" button clicked)
- Small inline spinners for component-level loading

**Error States**:
- If API fails, show error message with "Retry" button
- Graceful degradation (show what data is available, hide failed sections)

### Responsive Behavior

**Desktop** (≥1024px):
- Multi-column layout (2-4 columns)
- All components visible

**Tablet** (768px - 1023px):
- 2-column layout
- Some components stack vertically
- Collapsible sections (expand on tap)

**Mobile** (<768px):
- Single column (all components stack)
- Priority ordering (hero metrics first, less critical content below fold)
- Swipeable metrics cards (horizontal scroll)
- Collapsed activity feed (show top 3, "View More" button)

---

## Implementation Guide

### File Structure

```
app/command-center/
├── page.tsx                          # Main page component
├── components/
│   ├── PortfolioHealthScore.tsx     # Hero component
│   ├── MetricCard.tsx                # Reusable metric card
│   ├── ExposureGauge.tsx             # Net exposure gauge
│   ├── ExposureBreakdown.tsx         # Long/short bars
│   ├── AIInsightsSection.tsx         # Insights cards
│   ├── SectorExposureChart.tsx       # Sector vs benchmark
│   ├── FactorExposuresSummary.tsx    # Factor tilts
│   ├── TopPositionsTable.tsx         # Top positions
│   └── RecentActivityFeed.tsx        # Activity feed
├── hooks/
│   ├── usePortfolioHealth.ts         # Fetch health score
│   ├── useExposures.ts               # Fetch exposure data
│   ├── useAIInsights.ts              # Fetch insights
│   └── useRecentActivity.ts          # Fetch activity feed
└── utils/
    ├── healthScoreCalculator.ts      # Health score logic
    └── exposureCalculator.ts         # Exposure calculations
```

### Component Hierarchy

```
<CommandCenterPage>
  <TopNavigationBar />
  <CommandCenterContainer>
    <PortfolioHealthScore />
    <MetricsRow>
      <MetricCard type="net-worth" />
      <MetricCard type="net-exposure" />
      <MetricCard type="gross-exposure" />
      <MetricCard type="pnl-mtd" />
    </MetricsRow>
    <ExposureBreakdown />
    <AIInsightsSection />
    <AnalyticsRow>
      <SectorExposureChart />
      <FactorExposuresSummary />
    </AnalyticsRow>
    <TopPositionsTable />
    <RecentActivityFeed />
  </CommandCenterContainer>
  <AICopilotSidebar />
</CommandCenterPage>
```

### Data Fetching Pattern

```typescript
// app/command-center/page.tsx
'use client'

import { usePortfolioHealth } from './hooks/usePortfolioHealth'
import { useExposures } from './hooks/useExposures'
import { useAIInsights } from './hooks/useAIInsights'

export default function CommandCenterPage() {
  const { portfolioId } = usePortfolioStore()

  // Parallel data fetching
  const { data: health, loading: healthLoading } = usePortfolioHealth(portfolioId)
  const { data: exposures, loading: exposuresLoading } = useExposures(portfolioId)
  const { data: insights, loading: insightsLoading } = useAIInsights(portfolioId)

  if (healthLoading || exposuresLoading) {
    return <CommandCenterSkeleton />
  }

  return (
    <CommandCenterContainer>
      <PortfolioHealthScore {...health} />
      <MetricsRow>
        <MetricCard type="net-worth" data={exposures} />
        <MetricCard type="net-exposure" data={exposures} />
        {/* ... */}
      </MetricsRow>
      <AIInsightsSection insights={insights} loading={insightsLoading} />
      {/* ... */}
    </CommandCenterContainer>
  )
}
```

### Performance Optimization

**Code Splitting**:
- Lazy load heavy components (charts, tables)
- Use dynamic imports for below-the-fold content

**Memoization**:
- Memoize expensive calculations (health score, exposure calcs)
- Use `useMemo` for derived data

**Virtual Scrolling**:
- If activity feed is long, use virtual scrolling (react-window)

**Image Optimization**:
- Use Next.js Image component for any logos/icons

---

## Success Metrics

**User Engagement**:
- Time on Command Center: Avg 2+ minutes per session
- Click-through rate on AI insights: 40%+
- "AI Explain" button usage: 50%+ of users per session

**Performance**:
- First Contentful Paint (FCP): <1.5s
- Largest Contentful Paint (LCP): <2.5s
- Time to Interactive (TTI): <3.5s

**User Satisfaction**:
- "Command Center shows what I need": 85%+ agree
- "I can assess my portfolio in <5 seconds": 80%+ agree
- "AI insights are helpful": 80%+ agree

---

## Conclusion

The Command Center replaces the current Dashboard with an exposure-first, AI-enhanced interface that provides portfolio health, risk posture, and actionable insights at a glance. By prominently displaying net/gross/long/short metrics, surfacing AI insights proactively, and always showing benchmark comparisons, we create a professional-grade experience that rivals Bloomberg while remaining accessible.

**Next**: Read `04-POSITIONS-WORKSPACE.md` for the unified positions view specification.
