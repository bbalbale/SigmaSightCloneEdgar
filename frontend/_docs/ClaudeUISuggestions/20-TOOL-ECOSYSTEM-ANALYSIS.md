# Tool Ecosystem Analysis - Current vs Available vs Needed

**Date**: October 31, 2025
**Purpose**: Analyze the current tool landscape, identify gaps, and map to available data
**Status**: Comprehensive Analysis

---

## 🎯 Implementation Decision (October 31, 2025)

**DECISION**: Prioritize tool implementation first, then return to conversational tone improvements.

**Rationale**:
- Tools unlock core functionality (AI can answer risk analytics questions)
- Tone improvements are valuable but secondary to capability
- Better to have working insights with formal tone than great tone with limited capabilities

**Implementation Order**:
1. **Phase 1 (Week 1-2)**: Add 6 critical analytics tools
   - `get_analytics_overview`, `get_factor_exposures`, `get_sector_exposure`
   - `get_correlation_matrix`, `get_stress_test_results`, `get_company_profile`
   - **Deliverable**: AI can answer "Why is my portfolio volatile?" type questions

2. **Phase 2 (Week 3)**: Add 4 enhanced tools
   - `get_concentration_metrics`, `get_volatility_analysis`
   - `get_target_prices`, `get_position_tags`
   - **Deliverable**: AI can track goals and filter by strategy

3. **Phase 3 (Week 4+)**: Conversational tone improvements
   - Implement guidance from `18-CONVERSATIONAL-AI-PARTNER-VISION.md`
   - Add "ask, don't tell" patterns
   - Calibrate severity levels
   - **Deliverable**: AI feels like trusted partner, not alarmist robot

**Cross-Reference**:
- Tool implementation plan: This document (sections below)
- Tone improvement plan: `18-CONVERSATIONAL-AI-PARTNER-VISION.md`
- Tool access architecture: `19-CLAUDE-INSIGHTS-TOOL-ACCESS.md`

---

## Table of Contents

1. [Current Tool Inventory](#current-tool-inventory)
2. [Available Backend Data (Not Yet Toolified)](#available-backend-data-not-yet-toolified)
3. [Tool Comparison: OpenAI Chat vs Claude Insights](#tool-comparison-openai-chat-vs-claude-insights)
4. [Competitor Tool Analysis](#competitor-tool-analysis)
5. [Gap Analysis](#gap-analysis)
6. [Recommended New Tools](#recommended-new-tools)
7. [Implementation Priority](#implementation-priority)

---

## Current Tool Inventory

### The 6 Existing Tools

Both **OpenAI Chat** (`/ai-chat`) and **Claude Insights** (`/sigmasight-ai`) have access to these tools via `tool_registry.py`:

| Tool Name | Purpose | Parameters | Returns |
|-----------|---------|------------|---------|
| **get_portfolio_complete** | Full portfolio snapshot | `portfolio_id`, `include_holdings`, `include_timeseries`, `include_attrib` | Complete portfolio data with positions, values, timeseries, attribution |
| **get_positions_details** | Detailed position info | `portfolio_id`, `position_ids`, `include_closed` | Position details with P&L, market values, characteristics |
| **get_prices_historical** | Historical price data | `portfolio_id`, `lookback_days` (max 180), `include_factor_etfs` | Price history for all portfolio symbols |
| **get_current_quotes** | Real-time market quotes | `symbols` (max 5), `include_options` | Real-time prices, volumes, market status |
| **get_portfolio_data_quality** | Data completeness check | `portfolio_id`, `check_factors`, `check_correlations` | Data quality metrics, missing fields, coverage |
| **get_factor_etf_prices** | Factor ETF prices | `lookback_days` (max 180), `factors` (SPY, VTV, VUG, etc.) | Factor ETF price history |

### Tool Architecture

```python
# Tool flow
AI requests tool → tool_registry.dispatch_tool_call()
                → PortfolioTools.{tool_method}()
                → httpx call to backend API
                → Returns uniform envelope with meta/data/error

# Uniform envelope format
{
  "meta": {
    "requested": {...},      # What AI asked for
    "applied": {...},        # What was actually used
    "as_of": "2025-10-31T...",
    "truncated": false,
    "limits": {...},
    "retryable": false,
    "cache_hit": false,
    "request_id": "uuid"
  },
  "data": {...},            # Actual response data
  "error": null             # Error details if failed
}
```

### Tool Coverage Assessment

**What current tools cover well**:
- ✅ Portfolio-level snapshot (complete data)
- ✅ Position-level details (individual holdings)
- ✅ Historical prices (time series)
- ✅ Market quotes (real-time data)
- ✅ Data quality assessment
- ✅ Factor benchmark prices

**What current tools DON'T cover**:
- ❌ Risk analytics (betas, correlations, volatility, stress tests)
- ❌ Sector/factor exposures
- ❌ Company profiles (fundamentals, earnings, etc.)
- ❌ Tags and organization
- ❌ Target prices
- ❌ Scenario analysis
- ❌ Performance attribution
- ❌ Trade recommendation / rebalancing

---

## Available Backend Data (Not Yet Toolified)

### From Research Findings Doc + Backend Audit

The backend has **59 endpoints across 9 categories**. Here's what's available but NOT yet accessible via tools:

### 1. Analytics Endpoints (9 endpoints) - **MAJOR GAP**

| Endpoint | Purpose | Returns | Tool Status |
|----------|---------|---------|-------------|
| `/api/v1/analytics/portfolio/{id}/overview` | Portfolio metrics overview | NAV, returns, Sharpe, drawdown, beta | ❌ **NO TOOL** |
| `/api/v1/analytics/portfolio/{id}/correlation-matrix` | Correlation matrix | Position correlations, factor correlations | ❌ **NO TOOL** |
| `/api/v1/analytics/portfolio/{id}/diversification-score` | Diversification metrics | HHI, effective N, concentration | ❌ **NO TOOL** |
| `/api/v1/analytics/portfolio/{id}/factor-exposures` | Portfolio factor betas | 5 factor exposures (Market, Value, Growth, Momentum, Quality, Size, Low Vol) | ❌ **NO TOOL** |
| `/api/v1/analytics/portfolio/{id}/positions/factor-exposures` | Position-level factors | Factor betas for each position | ❌ **NO TOOL** |
| `/api/v1/analytics/portfolio/{id}/stress-test` | Stress test scenarios | 8 scenarios (tech selloff, rate shock, etc.) | ❌ **NO TOOL** |
| `/api/v1/analytics/portfolio/{id}/sector-exposure` | Sector exposure vs S&P 500 | Sector weights + benchmark comparison | ❌ **NO TOOL** |
| `/api/v1/analytics/portfolio/{id}/concentration` | Concentration metrics | HHI, top N concentration, single-name risk | ❌ **NO TOOL** |
| `/api/v1/analytics/portfolio/{id}/volatility` | Volatility analytics | Realized vol, forecasted vol (HAR model), vol attribution | ❌ **NO TOOL** |

**Analysis**: This is the **BIGGEST GAP**. All the sophisticated risk analytics exist but AI can't access them!

### 2. Company Profile Data (1 endpoint) - **GAP**

| Endpoint | Purpose | Returns | Tool Status |
|----------|---------|---------|-------------|
| `/api/v1/data/company-profile/{symbol}` | Company fundamentals | 53 fields: sector, industry, market cap, revenue, earnings, P/E, beta, description, etc. | ❌ **NO TOOL** |

**Use case**: "Tell me about NVDA" → AI should fetch company profile

### 3. Target Prices (10 endpoints) - **GAP**

| Endpoint | Purpose | Returns | Tool Status |
|----------|---------|---------|-------------|
| `GET /api/v1/target-prices` | List target prices | All target prices for portfolio/position | ❌ **NO TOOL** |
| `POST /api/v1/target-prices` | Create target price | New target price record | ❌ **NO TOOL** |
| `PUT /api/v1/target-prices/{id}` | Update target price | Updated record | ❌ **NO TOOL** |
| `DELETE /api/v1/target-prices/{id}` | Delete target price | Confirmation | ❌ **NO TOOL** |
| ... | (6 more bulk/import/export endpoints) | ... | ❌ **NO TOOL** |

**Use case**: "Which positions are near target prices?" → AI should check target price data

### 4. Position Tagging (12 endpoints) - **GAP**

| Endpoint | Purpose | Returns | Tool Status |
|----------|---------|---------|-------------|
| `GET /api/v1/tags` | List tags | All tags for portfolio | ❌ **NO TOOL** |
| `GET /api/v1/position-tags` | Get position tags | Tags for specific positions | ❌ **NO TOOL** |
| `POST /api/v1/position-tags` | Tag a position | New tag assignment | ❌ **NO TOOL** |
| ... | (9 more tag management endpoints) | ... | ❌ **NO TOOL** |

**Use case**: "Show me all my 'core holdings' positions" → AI should query tags

### 5. Batch Admin (6 endpoints) - **MAYBE**

| Endpoint | Purpose | Returns | Tool Status |
|----------|---------|---------|-------------|
| `POST /api/v1/admin/batch/run` | Trigger batch processing | Real-time batch status | ❌ **NO TOOL** |
| `GET /api/v1/admin/batch/run/current` | Get batch status | Current batch execution state | ❌ **NO TOOL** |
| `GET /api/v1/admin/batch/data-quality` | Data quality metrics | Coverage, missing data, freshness | ⚠️ **PARTIAL** (via `get_portfolio_data_quality`) |

**Use case**: "Refresh my market data" → AI could trigger batch job

---

## Tool Comparison: OpenAI Chat vs Claude Insights

### Current State (Both Systems Use Same Tools)

| System | AI Model | Tool Access | Purpose |
|--------|----------|-------------|---------|
| **OpenAI Chat** (`/ai-chat`) | OpenAI Responses API | ✅ Yes (6 tools) | Conversational Q&A |
| **Claude Insights** (`/sigmasight-ai`) | Claude Sonnet 4 | ⚠️ **PLANNED** (will add) | Deep portfolio analysis |

**Key Insight**: Once we add tool access to Claude Insights (Doc 19), both systems will have the **same 6 tools** available.

### Tool Usage Patterns (Expected)

**OpenAI Chat** (Interactive):
```
User: "What's my tech exposure?"
AI: Let me check your positions...
    [Calls get_positions_details]
AI: You're 42% tech with AAPL (20%), MSFT (10%), NVDA (8%), META (4%)
```

**Claude Insights** (Investigative):
```
System: Generate daily summary
Claude: I see 42% tech exposure. Let me investigate...
        [Calls get_positions_details to see breakdown]
        [Calls get_prices_historical to check if AAPL grew via appreciation]
        [Calls get_portfolio_complete to check correlations]
Claude: Your 42% tech is driven by AAPL appreciation - it grew from 14% to 20%
        in 90 days through price gains. Classic winner concentration...
```

**Difference**:
- Chat: Reactive (answers specific questions)
- Insights: Proactive (investigates patterns)

---

## Competitor Tool Analysis

### Bloomberg Terminal

**Equivalent "Tools"** (what Bloomberg AI would need):

1. **Portfolio Analytics** (`PRTU` function)
   - Exposure summary (gross/net/long/short)
   - Sector weights vs benchmark
   - Factor exposures
   - Risk metrics (beta, tracking error, Sharpe)
   - → **SigmaSight equivalent**: `get_analytics_overview` (missing)

2. **Position Lookup** (`DES` function)
   - Company description
   - Fundamentals (P/E, revenue, earnings)
   - Real-time price
   - News and events
   - → **SigmaSight equivalent**: `get_company_profile` (missing)

3. **Charting** (`GP` function)
   - Historical prices with technical indicators
   - Relative performance vs benchmark
   - → **SigmaSight equivalent**: `get_prices_historical` (✅ have)

4. **Risk Analytics** (`BETA`, `CORR` functions)
   - Beta calculation
   - Correlation matrix
   - Factor decomposition
   - → **SigmaSight equivalent**: `get_risk_analytics` (missing)

5. **News & Events** (`N`, `CN` functions)
   - Real-time news on holdings
   - Earnings calendars
   - Event alerts
   - → **SigmaSight equivalent**: N/A (future)

**SigmaSight Gap vs Bloomberg**:
- Missing: Analytics tools (risk, correlation, factors)
- Missing: Company profile tools
- Missing: Scenario/stress test tools

### Addepar

**Equivalent "Tools"**:

1. **Portfolio Summary**
   - Net worth, asset allocation
   - Account hierarchy
   - → **SigmaSight equivalent**: `get_portfolio_complete` (✅ have)

2. **Performance Attribution**
   - What drove returns this month?
   - Contribution by position/sector
   - → **SigmaSight equivalent**: `get_performance_attribution` (missing)

3. **Scenario Planning**
   - "What if I withdraw $X/year?"
   - Monte Carlo projections
   - → **SigmaSight equivalent**: `run_scenario` (missing)

4. **Tax Analysis**
   - Unrealized gains/losses
   - Tax-loss harvesting opportunities
   - → **SigmaSight equivalent**: `get_tax_analysis` (missing)

**SigmaSight Gap vs Addepar**:
- Missing: Performance attribution
- Missing: Scenario planning
- Missing: Tax analysis

### Eze Castle (Institutional)

**Equivalent "Tools"**:

1. **Real-Time Exposure**
   - Gross/net/long/short
   - By sector, by strategy
   - → **SigmaSight equivalent**: `get_exposure_summary` (missing)

2. **P&L Attribution**
   - Intraday P&L by position
   - By sector, by strategy
   - → **SigmaSight equivalent**: `get_pnl_attribution` (missing)

3. **Compliance Monitoring**
   - Position limits
   - Risk budget violations
   - → **SigmaSight equivalent**: `check_risk_limits` (missing)

4. **Order Management**
   - Generate rebalancing orders
   - Trade optimization
   - → **SigmaSight equivalent**: `generate_rebalance_orders` (missing)

**SigmaSight Gap vs Eze Castle**:
- Missing: Exposure analytics tools
- Missing: P&L attribution
- Missing: Risk limit checking
- Missing: Order generation

---

## Gap Analysis

### Critical Gaps (P0 - Needed for Conversational Partner)

These are data/endpoints that **exist in backend** but **not accessible via tools**:

| Gap | Backend Endpoint | Why Critical | Impact |
|-----|------------------|--------------|--------|
| **Risk Analytics** | `/api/v1/analytics/portfolio/{id}/overview` | Can't explain volatility, beta, Sharpe | AI can't answer "Why is my portfolio volatile?" |
| **Correlation Matrix** | `/api/v1/analytics/portfolio/{id}/correlation-matrix` | Can't explain concentration risk | AI can't answer "Are my positions correlated?" |
| **Factor Exposures** | `/api/v1/analytics/portfolio/{id}/factor-exposures` | Can't explain factor tilts | AI can't answer "What factors am I exposed to?" |
| **Sector Exposure** | `/api/v1/analytics/portfolio/{id}/sector-exposure` | Can't compare vs benchmark | AI can't answer "Am I overweight tech?" |
| **Stress Tests** | `/api/v1/analytics/portfolio/{id}/stress-test` | Can't show scenario impacts | AI can't answer "What happens if tech drops 20%?" |
| **Company Profiles** | `/api/v1/data/company-profile/{symbol}` | Can't explain positions | AI can't answer "Tell me about NVDA" |

**Analysis**: Without these tools, AI is **blind to the most important analytics**. It's like having a car with no steering wheel.

### Important Gaps (P1 - Enhance AI capabilities)

| Gap | Backend Endpoint | Why Important | Impact |
|-----|------------------|---------------|--------|
| **Target Prices** | `/api/v1/target-prices` | Can't check goal proximity | AI can't answer "Which positions are near target?" |
| **Position Tags** | `/api/v1/tags`, `/api/v1/position-tags` | Can't filter by strategy | AI can't answer "Show my core holdings" |
| **Concentration** | `/api/v1/analytics/portfolio/{id}/concentration` | Can't quantify single-name risk | AI can't answer "How concentrated am I?" |
| **Volatility** | `/api/v1/analytics/portfolio/{id}/volatility` | Can't forecast vol or attribute | AI can't answer "Will my vol stay high?" |

### Nice-to-Have Gaps (P2 - Future enhancements)

| Gap | Backend Endpoint | Why Nice | Impact |
|-----|------------------|----------|--------|
| **Batch Trigger** | `/api/v1/admin/batch/run` | Manual data refresh | User could ask "Refresh my data" |
| **Diversification** | `/api/v1/analytics/portfolio/{id}/diversification-score` | Quantify diversification | AI could score portfolio health |

### Missing Entirely (P3 - Not in backend yet)

These would require new backend endpoints:

| Missing Feature | Why Useful | Implementation Effort |
|----------------|-------------|----------------------|
| **Performance Attribution** | Explain what drove returns | HIGH (new calculation engine) |
| **Tax Analysis** | Unrealized gains, tax-loss harvesting | MEDIUM (need cost basis tracking) |
| **Scenario Builder** | Custom "what if" modeling | HIGH (new modeling engine) |
| **Order Generation** | Rebalancing trade lists | MEDIUM (order optimization logic) |
| **News/Events** | Real-time news on holdings | HIGH (external API integration) |
| **Risk Limit Checking** | Position/sector limit alerts | MEDIUM (rules engine) |

---

## Recommended New Tools

### Priority 0: Critical (Add Immediately)

These unlock the core value proposition (AI explaining risk analytics):

#### 1. `get_analytics_overview`
**Maps to**: `/api/v1/analytics/portfolio/{id}/overview`

```python
{
  "name": "get_analytics_overview",
  "description": "Get comprehensive portfolio risk analytics including beta, volatility, Sharpe ratio, max drawdown, and tracking error. Use this when user asks about portfolio risk, performance metrics, or wants overall health check.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {
        "type": "string",
        "description": "Portfolio UUID"
      }
    },
    "required": ["portfolio_id"]
  }
}
```

**Returns**:
```json
{
  "beta": 1.15,
  "volatility_21d": 0.21,
  "sharpe_ratio": 1.32,
  "max_drawdown": -0.12,
  "tracking_error": 0.042,
  "as_of": "2025-10-31"
}
```

**Use case**:
```
User: "Why is my portfolio volatile?"
AI: Let me check your risk metrics...
    [Calls get_analytics_overview]
AI: Your 21-day volatility is 21% (vs S&P 500's 15%). This is driven by your
    tech concentration at 42% - tech is a high-volatility sector.
```

#### 2. `get_factor_exposures`
**Maps to**: `/api/v1/analytics/portfolio/{id}/factor-exposures`

```python
{
  "name": "get_factor_exposures",
  "description": "Get portfolio factor exposures (Market Beta, Value, Growth, Momentum, Quality, Size, Low Volatility). Returns factor betas showing portfolio tilts. Use when user asks about factor exposures, style analysis, or what's driving returns.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

**Returns**:
```json
{
  "factor_exposures": {
    "market_beta": 1.15,
    "value_tilt": -0.3,
    "growth_tilt": 2.1,
    "momentum_tilt": 1.2,
    "quality_tilt": 0.5,
    "size_tilt": -0.8,
    "low_vol_tilt": -1.2
  }
}
```

**Use case**:
```
User: "What factors am I exposed to?"
AI: [Calls get_factor_exposures]
AI: You have a strong Growth tilt (+2.1σ) and Momentum tilt (+1.2σ). This means
    your portfolio is heavy in growth stocks with strong recent performance.
    That's typical for tech-heavy portfolios like yours.
```

#### 3. `get_sector_exposure`
**Maps to**: `/api/v1/analytics/portfolio/{id}/sector-exposure`

```python
{
  "name": "get_sector_exposure",
  "description": "Get sector exposure breakdown with S&P 500 benchmark comparison. Shows over/underweights by sector. Use when user asks about sector allocation, diversification, or wants to compare vs market.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

**Returns**:
```json
{
  "sectors": [
    {
      "sector": "Technology",
      "portfolio_weight": 0.42,
      "benchmark_weight": 0.28,
      "overweight": 0.14
    },
    {
      "sector": "Financials",
      "portfolio_weight": 0.12,
      "benchmark_weight": 0.13,
      "overweight": -0.01
    }
  ]
}
```

**Use case**:
```
User: "Am I overweight tech?"
AI: [Calls get_sector_exposure]
AI: Yes, you're 42% tech vs S&P 500's 28% - that's a +14% overweight. This
    creates sector concentration risk.
```

#### 4. `get_correlation_matrix`
**Maps to**: `/api/v1/analytics/portfolio/{id}/correlation-matrix`

```python
{
  "name": "get_correlation_matrix",
  "description": "Get correlation matrix showing how positions move together. Returns pairwise correlations. Use when user asks about diversification, correlation risk, or if positions are related.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

**Returns**:
```json
{
  "correlations": {
    "AAPL_MSFT": 0.78,
    "AAPL_NVDA": 0.82,
    "MSFT_NVDA": 0.85
  },
  "average_correlation": 0.72
}
```

**Use case**:
```
User: "Are my tech positions correlated?"
AI: [Calls get_correlation_matrix]
AI: Yes, your tech positions are highly correlated. AAPL and NVDA have 0.82
    correlation, meaning they tend to move together. This reduces diversification
    benefits - when one drops, they all tend to drop.
```

#### 5. `get_stress_test_results`
**Maps to**: `/api/v1/analytics/portfolio/{id}/stress-test`

```python
{
  "name": "get_stress_test_results",
  "description": "Get stress test scenario results showing portfolio impact under various market conditions (tech selloff, rate shock, recession, etc.). Use when user asks 'what if' questions or wants to see downside risk.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

**Returns**:
```json
{
  "scenarios": [
    {
      "name": "Tech Selloff",
      "description": "Tech sector drops 20%",
      "portfolio_impact": -0.084,
      "pnl_impact": -42000
    },
    {
      "name": "Rate Shock",
      "description": "Rates increase 1%",
      "portfolio_impact": -0.032,
      "pnl_impact": -16000
    }
  ]
}
```

**Use case**:
```
User: "What happens if tech drops 20%?"
AI: [Calls get_stress_test_results]
AI: If tech drops 20%, your portfolio would lose about $42K (-8.4%) based on
    your current 42% tech exposure and position correlations.
```

#### 6. `get_company_profile`
**Maps to**: `/api/v1/data/company-profile/{symbol}`

```python
{
  "name": "get_company_profile",
  "description": "Get detailed company profile including sector, industry, market cap, revenue, earnings, P/E ratio, description, and other fundamentals. Use when user asks about a specific company or wants to understand a position better.",
  "input_schema": {
    "type": "object",
    "properties": {
      "symbol": {
        "type": "string",
        "description": "Stock ticker symbol"
      }
    },
    "required": ["symbol"]
  }
}
```

**Returns**:
```json
{
  "symbol": "NVDA",
  "company_name": "NVIDIA Corporation",
  "sector": "Technology",
  "industry": "Semiconductors",
  "market_cap": 1200000000000,
  "pe_ratio": 45.2,
  "revenue_ttm": 26000000000,
  "description": "Designs graphics processors..."
}
```

**Use case**:
```
User: "Tell me about NVDA"
AI: [Calls get_company_profile]
AI: NVIDIA (NVDA) is a semiconductor company with $1.2T market cap. They design
    graphics processors for gaming and AI. Trading at P/E of 45.2 with $26B
    annual revenue. Your position is $88K (17.6% of portfolio).
```

### Priority 1: Important (Add Next)

#### 7. `get_concentration_metrics`
**Maps to**: `/api/v1/analytics/portfolio/{id}/concentration`

```python
{
  "name": "get_concentration_metrics",
  "description": "Get concentration risk metrics including HHI (Herfindahl-Hirschman Index), top N concentration, and single-name risk. Use when user asks about diversification or if portfolio is too concentrated.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

#### 8. `get_volatility_analysis`
**Maps to**: `/api/v1/analytics/portfolio/{id}/volatility`

```python
{
  "name": "get_volatility_analysis",
  "description": "Get volatility analytics including realized volatility, forecasted volatility (HAR model), and vol attribution by position. Use when user asks about volatility trends or what's driving vol.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

#### 9. `get_target_prices`
**Maps to**: `GET /api/v1/target-prices`

```python
{
  "name": "get_target_prices",
  "description": "Get target prices for portfolio positions. Shows which positions are near target, above target, or below target. Use when user asks about investment goals or which positions to trim/add.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

#### 10. `get_position_tags`
**Maps to**: `GET /api/v1/position-tags`

```python
{
  "name": "get_position_tags",
  "description": "Get tags for positions (e.g., 'core holdings', 'speculative', 'income', etc.). Use when user asks to filter positions by strategy or category.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

### Priority 2: Nice-to-Have (Future)

#### 11. `refresh_market_data`
**Maps to**: `POST /api/v1/admin/batch/trigger/market-data`

```python
{
  "name": "refresh_market_data",
  "description": "Manually trigger market data refresh for portfolio. Use when user says data looks stale or requests a refresh.",
  "input_schema": {
    "type": "object",
    "properties": {
      "portfolio_id": {"type": "string"}
    },
    "required": ["portfolio_id"]
  }
}
```

---

## Implementation Priority

### Phase 1: Core Analytics Tools (Week 1-2)
**Goal**: Enable AI to explain risk analytics

- [ ] `get_analytics_overview` - Portfolio risk metrics
- [ ] `get_factor_exposures` - Factor analysis
- [ ] `get_sector_exposure` - Sector breakdown vs benchmark
- [ ] `get_correlation_matrix` - Position correlations
- [ ] `get_stress_test_results` - Scenario analysis
- [ ] `get_company_profile` - Company fundamentals

**Impact**: AI can now answer 80% of risk-related questions

**Effort**: 2-3 days (tool definitions + handler methods + testing)

### Phase 2: Enhanced Analytics (Week 3)
**Goal**: Add concentration, volatility, targets, tags

- [ ] `get_concentration_metrics` - Diversification analysis
- [ ] `get_volatility_analysis` - Vol trends and forecasts
- [ ] `get_target_prices` - Goal tracking
- [ ] `get_position_tags` - Strategy filtering

**Impact**: AI becomes more sophisticated, can track goals and strategies

**Effort**: 1-2 days

### Phase 3: Admin Tools (Week 4)
**Goal**: Allow AI to trigger actions

- [ ] `refresh_market_data` - Manual data refresh

**Impact**: AI can respond to "my data looks old" requests

**Effort**: 1 day

---

## Tool Design Principles

### 1. **Descriptive Names**
- ✅ `get_factor_exposures` (clear what it does)
- ❌ `get_factors` (ambiguous - factors what?)

### 2. **Clear Descriptions**
Include:
- What the tool returns
- When to use it (user question patterns)
- Example use case

### 3. **Minimal Required Parameters**
- Most tools only need `portfolio_id`
- Optional parameters for advanced use (with sensible defaults)

### 4. **Uniform Response Format**
All tools return:
```json
{
  "meta": {
    "as_of": "timestamp",
    "truncated": false,
    "request_id": "uuid"
  },
  "data": {...},
  "error": null
}
```

### 5. **Error Handling**
- Return `{"error": "message", "retryable": true/false}`
- Let AI decide how to handle (retry, ask user, skip)

---

## Success Metrics

### Tool Coverage
- **Current**: 6 tools covering ~30% of backend data
- **Target**: 16 tools covering ~80% of backend data

### AI Capability
- **Current**: Can answer basic position questions
- **Target**: Can explain risk, analyze scenarios, track goals

### User Questions Answerable
- **Current**: ~40% of user questions have tool support
- **Target**: ~85% of user questions have tool support

### Examples of Questions Unlocked

**Current tools can answer**:
- ✅ "What positions do I own?"
- ✅ "What's the price of AAPL?"
- ✅ "How's my data quality?"

**New tools would enable**:
- ✅ "Why is my portfolio volatile?"
- ✅ "What factors am I exposed to?"
- ✅ "Am I overweight tech vs S&P 500?"
- ✅ "Are my positions correlated?"
- ✅ "What happens if tech drops 20%?"
- ✅ "Tell me about NVDA"
- ✅ "Which positions are near my target prices?"
- ✅ "Show my core holdings"

---

## Comparison to Competitors

### Bloomberg Terminal (Estimated 100+ AI-accessible functions)
- Portfolio analytics: PRTU, PORT, RV, EQS
- Risk analytics: BETA, CORR, VOL, VaR
- Fundamental data: FA, DDIS, ERN, REV
- News: N, CN, NH
- Charting: GP, GIP
- **SigmaSight coverage**: ~15% (will be ~40% after Phase 1-2)

### Addepar (Estimated 30+ tools)
- Portfolio summary
- Performance attribution
- Scenario modeling
- Tax analysis
- Document vault
- **SigmaSight coverage**: ~30% (will be ~50% after Phase 1-2)

### Eze Castle (Estimated 50+ tools)
- Real-time exposure
- P&L attribution
- Order management
- Compliance monitoring
- **SigmaSight coverage**: ~20% (will be ~35% after Phase 1-2)

**Analysis**: We'll never match Bloomberg's 100+ functions, but we can cover the **80% of use cases** with 15-20 well-designed tools + AI explanations.

---

## Next Steps

1. **Review this analysis** - Agree on priority tools
2. **Implement Phase 1 tools** - Add 6 critical analytics tools
3. **Test with real queries** - "Why is my portfolio volatile?" type questions
4. **Measure impact** - % of questions now answerable
5. **Iterate to Phase 2** - Add remaining tools based on usage

**Question**: Should we proceed with Phase 1 implementation (6 analytics tools)?

---

## Appendix: Tool Implementation Template

```python
# In backend/app/agent/tools/handlers.py

async def get_analytics_overview(
    self,
    portfolio_id: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Get comprehensive portfolio risk analytics.

    Args:
        portfolio_id: Portfolio UUID

    Returns:
        Risk metrics with meta object
    """
    try:
        endpoint = f"/api/v1/analytics/portfolio/{portfolio_id}/overview"
        response = await self._make_request(
            method="GET",
            endpoint=endpoint
        )
        return response

    except Exception as e:
        logger.error(f"Error in get_analytics_overview: {e}")
        return {
            "error": str(e),
            "retryable": isinstance(e, (httpx.TimeoutException, httpx.HTTPStatusError))
        }
```

```python
# In backend/app/agent/tools/tool_registry.py

# Add to registry
self.registry: Dict[str, Callable] = {
    # ... existing tools ...
    "get_analytics_overview": self.tools.get_analytics_overview,
}
```

```python
# In backend/app/agent/services/openai_service.py (and anthropic_provider.py)

# Add to tool definitions
{
    "name": "get_analytics_overview",
    "type": "function",
    "description": "Get comprehensive portfolio risk analytics including beta, volatility, Sharpe ratio, max drawdown, and tracking error. Use this when user asks about portfolio risk, performance metrics, or wants overall health check.",
    "parameters": {
        "type": "object",
        "properties": {
            "portfolio_id": {
                "type": "string",
                "description": "Portfolio UUID"
            }
        },
        "required": ["portfolio_id"]
    }
}
```

---

**End of Tool Ecosystem Analysis**
