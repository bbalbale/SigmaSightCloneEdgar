# Demo Overview

> ⚠️ **BACKEND STATUS (2025-08-26 15:15 PST)**: Backend APIs are ready for demo with Raw Data APIs 100% complete. Frontend can proceed with implementation. Demo users available with password "demo12345". See [TODO3.md](../../TODO3.md) for API development status.

## 0.1 Overview
Duration: 15-20 minutes
Objective: Get feedback from target customers and potential investors.

## 1. Product Tour (5 minutes)

### 1.1 Home / Dashboard Tab

Click on Dashboard (default view)

Script: "The Dashboard gives you an instant visual understanding of your portfolio's health. Unlike other platforms that just show positions, we're exposure-centric."

#### 1.1.1 Key Actions

##### 1.1.1.1 Summary Cards - Delta/$ toggled to Notional Exposure
- Long Exposure
- Short Exposure
- Gross Exposure
- Net Exposure
- Total P&L

Click through different time ranges:
- Day
- Week
- Monthly
- YTD

##### 1.1.1.2 Summary Cards - Delta/$ toggled to Delta-adjusted
- Long Exposure
- Short Exposure
- Gross Exposure
- Net Exposure
- Total P&L

Click through different time ranges
- Day
- Week
- Monthly
- YTD

### 1.2 Positions Tab

Click on Positions

Script: "This isn't just a position list - it's a complete portfolio management system with types, tags, and strategy grouping via what we call strategy tags."

#### 1.2.1 Key Actions

##### 1.2.1.1 Introduce Positions Table
- Toggle Chips: Individual, By Type, By Strategy
  - Individual shows each ticker as a row without any grouping
  - By Type groups by Long (N positions), Short (N positions), Long Option (N positions), Short Option (N positions)
  - Each group shows a summary bar with combined metrics
  - By Strategy groups by Strategy Tags

##### 1.2.1.2 Table Columns
- Ticker (with expandable Ticker Graph view)
- Type (Long, Short, Long Options, Short Options, Bullish?, Bearish?)
- Tags (Strategy Tags and Tags)
- Quantity
- Notional Exposure
- Delta-Adjusted Exposure
- P&L
- Expiry Date
- Delta
- Gamma
- Theta
- Vega

##### 1.2.1.3 Show Strategy View Example
Script: "Notice how we can group related positions - like this pairs trade"

- Select Strategy View toggle
- All strategies start out in Contracted state
- Expand a strategy tag group
- Show combined metrics and positions underneath
Script: "Strategies are set up using a special type of strategy tag, such as #strategy:pairs-trade"

##### 1.2.1.4 Explain Tags
Script: "Tags provide a flexible way to show user defined parts of your portfolio, for example: #high-conviction vs #core-holding"

### 1.3 Modeling / Risk & Factor Analytics Tab

Click on Modeling / Risk & Factor Analytics

#### 1.3.1 Key Actions

##### 1.3.1.1 Describe Overview Tab
Script: "shows most important portfolio level aggregate risk metrics, factor exposures, and scenario analysis"

- Top Type Selectors: Portfolio | Longs | Shorts
- Top Date Selectors: Daily | Weekly | Monthly | Annual

##### 1.3.1.2 Summary Cards
- Beta - vs. SPY
- Annualized Volatility - std. Deviation of returns
- Position Correlation - avg. pairwise correlation
- Max Drawdown - peak-to-trough decline

##### 1.3.1.3 Factor Exposure Cards
Script: "See your market exposures"

- Market Beta
- Momentum
- Value
- Growth
- Quality
- Size
- Short Interest
- Volatility

##### 1.3.1.4 Scenario Analysis Cards
- Market Up 10%
- Rates up 0.25%
- Market Down 10%
- Rates down 0.25%
- Oil Up 5%
- DAX Up 10%
- Oil Down 5%
- Dax Down 10%

### 1.4 Tagging

#### 1.4.1 Tagging a Pairs Trade

##### 1.4.1.1 Step 1: Navigate to Tagging Page
Action: Click on the "Tagging & Attribution" tab

Script: "We're on the Tagging page — this is where I can organize trades into strategic groups and see their combined impact on the portfolio."

##### 1.4.1.2 Step 2: Select Two Opposing Positions
Action: Locate General Motors (GM) and Ford (F) in the portfolio

Click: Checkboxes next to both

Script: "Let's group a simple pairs trade: long GM, short Ford. These two names represent a directional view on relative performance."

##### 1.4.1.3 Step 3: Create a Tag
Action: Click "Create Tag" → Enter tag name: Auto OEM Spread

Click: Save

Script: "I'll create a new tag called 'Auto OEM Spread'. The system now treats these positions as one strategy."

#### 1.4.2 Tagging an Options Spread

##### 1.4.2.1 Step 1: Select Two Option Legs
Action: Locate TSLA $250 Call (Long) and TSLA $270 Call (Short)

Click: Check both

Script: "Now let's look at an options trade — a basic call spread on Tesla. Long $250, short $270."
"I'll tag both as 'TSLA Call Spread – Earnings'. Now they're grouped as a single trade."

### 1.5 ProForma Analytics Tab

Click on ProForma Analytics

Script: "Before you trade, model the exact impact on your portfolio risk - and export ready-to-execute trade lists."

#### 1.5.1 Key Actions

##### 1.5.1.1 Changes Summary
- Show empty area at top
- Explain tracking of all changes
- Point out Export Function
Script: "Generate broker-ready trade lists in CSV, JSON, or FIX format"

##### 1.5.1.2 Introduce Sub Sections
###### 1.5.1.2.1 Exposure Impact Analysis
(default up arrow and expanded)
"See how any trade affects your exposures before execution"
- Long Exposure
- Short Exposure
- Gross Exposure
- Net Exposure

###### 1.5.1.2.2 Factor Impact Analysis
(default down arrow and collapsed)
- Market Beta
- Momentum
- Value
- Growth
- Quality
- Size
- Short Interest
- Volatility

###### 1.5.1.2.3 Trade Builder
(default down arrow and collapsed)
"Single trades or complex strategies"
- Toggle selector: Position (default) | Multi-Leg | Basket

In Single Position mode:
- Ticker: (enter sample ticker)
- Exposure: (enter exposure amount)
- Side: (short | long selector)
- Tag (optional): text entry field
- Button: +Add to Model

Show update to Changes Summary

## Part 3: Closing Summary (1 minute)

Script: "Let's recap what makes SigmaSight unique:"

### ~~Historical Data Processing~~ *(REMOVED - V1.4 scope change)*
~~- After uploading the CSV, the system automatically fetches 90 days of real historical market data~~
~~- This creates authentic portfolio performance history based on actual market movements~~
~~- The historical charts and metrics shown reflect real market conditions~~
~~- Processing typically takes 5-10 minutes for a full portfolio~~

**Updated Demo Flow (2025-08-26 15:15 PST)**: Portfolio snapshots and performance tracking begin from CSV upload date, building forward daily performance history. Demo data with 3 portfolios and 63 positions is pre-seeded and ready for demonstration.

## Demo Environment Setup Notes

### Portfolio Composition for Demo:
- Mix of long/short equity positions
- Several options positions (calls, puts, spreads)
- At least one pairs trade
- Sector concentration in technology
- Negative inflation beta

### Key Visual Elements to Emphasize:
- Color transitions (green → yellow → red)
- Real-time number updates in modeling sessions
- Progress bar animations for async operations
- Before/after comparisons in ProForma
- Export dialog with trade list previews

### Technical Implementation Notes:
- Market data should be pulled and cached from feeds at the beginning of demo.
- Implement live data feeds as available.
- Implement modeling sessions for all "what-if" analysis
- Generate actual CSV/FIX format trade lists for demo