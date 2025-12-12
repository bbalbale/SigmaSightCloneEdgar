# SigmaSight AI Page Architecture

**Created**: December 10, 2025

This document explains how the SigmaSight AI page (`/sigmasight-ai`) works and how it connects to the chat agent.

---

## Overview

The page has a **two-column layout** with two distinct AI features:

```
┌──────────────────────────────────────────────────────────────────┐
│  SigmaSight AI Page                                              │
├─────────────────────────────┬────────────────────────────────────┤
│  LEFT COLUMN                │  RIGHT COLUMN                      │
│  Daily Summary Analysis     │  Chat with SigmaSight AI           │
│  (Pre-generated insights)   │  (Live conversational chat)        │
│                             │                                    │
│  Uses: insightsApi          │  Uses: claudeInsightsService       │
│  Endpoint: /insights/*      │  Endpoint: /insights/chat (SSE)    │
└─────────────────────────────┴────────────────────────────────────┘
```

---

## File Structure & Flow

```
app/sigmasight-ai/page.tsx          → Thin route file (7 lines)
    ↓
containers/SigmaSightAIContainer.tsx → Main layout & orchestration
    ↓
    ├── useAIInsights hook           → Left column data
    │       ↓
    │   services/insightsApi.ts      → REST API calls to backend
    │
    └── ClaudeChatInterface          → Right column component
            ↓
        stores/claudeInsightsStore.ts  → Zustand state (messages, streaming)
            ↓
        services/claudeInsightsService.ts → SSE streaming to backend
```

---

## Left Column: Daily Summary Analysis

**Files involved:**
- `src/hooks/useAIInsights.ts` - React hook for state management
- `src/services/insightsApi.ts` - API client for insights endpoints
- `src/components/command-center/AIInsightsRow.tsx` - Display component

**How it works:**

1. **On page load**, `useAIInsights` hook fetches existing insights:
   ```typescript
   insightsApi.listInsights(portfolioId, { daysBack: 30, limit: 20 })
   ```
   Calls: `GET /api/v1/insights/portfolio/{portfolio_id}`

2. **When user clicks "Generate"**, it creates a new insight:
   ```typescript
   insightsApi.generateInsight({
     portfolio_id: portfolioId,
     insight_type: 'daily_summary'
   })
   ```
   Calls: `POST /api/v1/insights/generate`

   Takes ~25-30 seconds because the backend calls Anthropic's API to analyze portfolio data.

3. **Backend** uses **OpenAI Responses API** (per CLAUDE.md) to generate structured insights with:
   - Title, severity, summary
   - Key findings, recommendations
   - Full analysis text

---

## Right Column: Interactive Chat

**Files involved:**
- `src/components/claude-insights/ClaudeChatInterface.tsx` - Chat UI
- `src/stores/claudeInsightsStore.ts` - Zustand store for chat state
- `src/services/claudeInsightsService.ts` - SSE streaming service

**How it works:**

1. **User types message** in the textarea and presses Enter or clicks Send

2. **`sendMessage()` function** (`claudeInsightsService.ts:194-211`):
   ```typescript
   // Add user message to local store immediately
   store.addMessage(userMessage)

   // Send to backend via SSE
   await sendClaudeMessage({ message, conversationId })
   ```

3. **`sendClaudeMessage()` function** (`claudeInsightsService.ts:28-115`):
   - Makes POST to `${BACKEND_API_URL}/insights/chat` with:
     - JWT token from localStorage
     - Message content
     - Optional conversation_id for context continuity
   - Sets header `Accept: text/event-stream` for SSE

4. **SSE Stream Processing** - The backend returns Server-Sent Events:
   ```
   event: start
   data: {"conversation_id": "...", "run_id": "..."}

   event: message
   data: {"delta": "Here's what I found..."}

   event: message
   data: {"delta": " in your portfolio..."}

   event: done
   data: {"final_text": "...", "tool_calls_count": 3}
   ```

5. **`handleSSEEvent()` function** (`claudeInsightsService.ts:120-181`) processes events:
   - `start` → Sets conversation ID, starts streaming indicator
   - `message` → Appends text chunks to `streamingText` in store
   - `done` → Creates final message, stops streaming
   - `error` → Sets error state

6. **Store updates** trigger React re-renders, showing:
   - Typing indicator during streaming
   - Real-time text appearing character by character
   - Final formatted message when complete

---

## State Management (Zustand Store)

`claudeInsightsStore.ts` manages:

```typescript
{
  conversationId: string | null     // Persists across messages
  messages: ClaudeMessage[]         // Chat history
  isStreaming: boolean              // Show typing indicator
  streamingText: string             // Partial response being built
  currentRunId: string | null       // Backend run tracking
  error: string | null              // Error display
}
```

Key actions:
- `addMessage()` - Add user/assistant message
- `appendStreamingText()` - Build response incrementally
- `startStreaming()` / `stopStreaming()` - Manage streaming state
- `reset()` - Start new conversation

---

## Backend Connection Summary

| Feature | Frontend Service | Backend Endpoint | Protocol |
|---------|-----------------|------------------|----------|
| List insights | `insightsApi.listInsights()` | `GET /api/v1/insights/portfolio/{id}` | REST |
| Generate insight | `insightsApi.generateInsight()` | `POST /api/v1/insights/generate` | REST |
| Chat message | `claudeInsightsService.sendClaudeMessage()` | `POST /api/v1/insights/chat` | SSE |

Both features authenticate using the JWT token from `localStorage.getItem('access_token')`.

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/sigmasight-ai/page.tsx` | Route file - renders container |
| `src/containers/SigmaSightAIContainer.tsx` | Main layout with 2-column grid |
| `src/hooks/useAIInsights.ts` | Hook for daily insights (left column) |
| `src/services/insightsApi.ts` | REST API for insights CRUD |
| `src/components/claude-insights/ClaudeChatInterface.tsx` | Chat UI component (right column) |
| `src/stores/claudeInsightsStore.ts` | Zustand store for chat state |
| `src/services/claudeInsightsService.ts` | SSE streaming for chat |
| `src/components/command-center/AIInsightsRow.tsx` | Displays insight cards |

---

## Tool Calling Implementation

The AI chat system has **full tool calling support** with 16 implemented tools. The AI can autonomously call these tools during conversations to retrieve portfolio data and analytics.

### Implemented Tools (16 Total)

#### Phase 1 Core Tools (Original)
| Tool Name | Purpose | Status |
|-----------|---------|--------|
| `get_portfolio_complete` | Comprehensive portfolio snapshot with positions, values | ✅ Implemented |
| `get_positions_details` | Detailed position information with P&L and metadata | ✅ Implemented |
| `get_prices_historical` | Historical prices for top portfolio positions | ✅ Implemented |
| `get_current_quotes` | Real-time market quotes for specified symbols | ✅ Implemented |
| `get_portfolio_data_quality` | Assess data completeness and analysis feasibility | ✅ Implemented |
| `get_factor_etf_prices` | Historical prices for factor ETFs (SPY, IWM, etc.) | ✅ Implemented |

#### Phase 1 Analytics Tools (October 31, 2025)
| Tool Name | Purpose | Status |
|-----------|---------|--------|
| `get_analytics_overview` | Portfolio metrics overview | ✅ Implemented |
| `get_factor_exposures` | Portfolio factor betas | ✅ Implemented |
| `get_sector_exposure` | Sector exposure vs S&P 500 | ✅ Implemented |
| `get_correlation_matrix` | Position correlation matrix | ✅ Implemented |
| `get_stress_test_results` | Stress test scenarios | ✅ Implemented |
| `get_company_profile` | Company profile data (53 fields) | ✅ Implemented |

#### Phase 5 Enhanced Analytics Tools (December 3, 2025)
| Tool Name | Purpose | Status |
|-----------|---------|--------|
| `get_concentration_metrics` | Concentration metrics (HHI) | ✅ Implemented |
| `get_volatility_analysis` | Volatility analytics with HAR forecasting | ✅ Implemented |
| `get_target_prices` | Target price data for positions | ✅ Implemented |
| `get_position_tags` | Position tagging information | ✅ Implemented |

### Backend Tool Architecture

**Key Files:**
- `backend/app/agent/tools/tool_registry.py` - Central registry with dispatch
- `backend/app/agent/tools/handlers.py` - Provider-agnostic tool implementations
- `backend/app/agent/docs/TOOL_REFERENCE.md` - Tool documentation

**SSE Events for Tools:**
The chat stream emits tool-related events that the frontend can display:
```
event: tool_call
data: {"tool_name": "get_portfolio_complete", "tool_args": {...}}

event: tool_result
data: {"tool_call_id": "...", "result": {...}}
```

**Frontend Display:**
The `ClaudeChatInterface` shows tool usage count in messages:
```tsx
{message.tool_calls_count > 0 && (
  <div>Used {message.tool_calls_count} analytics tool(s)</div>
)}
```

---

## Future Enhancement: Analytical Tools for Claude

The following 4 tools were planned in the original architecture but not yet implemented. They would enable Claude to perform **calculations** during investigation rather than just analyzing pre-calculated data.

### Tool 1: Scenario Calculator 🎯 **HIGH PRIORITY**

**Value Proposition:**
- Claude can test "what-if" scenarios proactively
- Example: "I notice high tech exposure. Let me test a 15% tech correction scenario..."
- Enables predictive risk analysis vs. just descriptive

**Proposed Implementation:**
```python
{
  "name": "calculate_scenario_impact",
  "description": "Calculate portfolio impact of market scenario",
  "input_schema": {
    "type": "object",
    "properties": {
      "scenarios": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "asset": {"type": "string"},  # "SPY", "VIX", "QQQ"
            "change": {"type": "number"}   # -0.10 for -10%
          }
        }
      }
    }
  }
}

# Backend service would calculate:
# - position_impacts: P&L per position
# - total_pnl: Overall portfolio P&L
# - greeks_changes: How Greeks shift
# - risk_metrics: Updated volatility, beta, etc.
```

**Estimated Effort:** 1-2 days
**API Cost Impact:** +500-800 tokens per tool call (~$0.005)

---

### Tool 2: Historical Trend Analysis 🎯 **MEDIUM PRIORITY**

**Value Proposition:**
- Claude can determine if current metrics are elevated vs. historical norms
- Example: "Current volatility of 6.28% is in the 85th percentile for this portfolio..."
- Contextualizes point-in-time metrics

**Proposed Implementation:**
```python
{
  "name": "get_historical_metrics",
  "description": "Retrieve historical time series for portfolio metrics",
  "input_schema": {
    "type": "object",
    "properties": {
      "metrics": {
        "type": "array",
        "items": {"type": "string"}  # ["realized_volatility_21d", "beta_calculated_90d"]
      },
      "days_back": {"type": "integer", "default": 180}
    }
  }
}

# Backend would query portfolio_snapshots table for historical metrics
# Returns time series data per metric with percentile calculations
```

**Estimated Effort:** 1 day
**API Cost Impact:** +300-500 tokens per call (~$0.003)

---

### Tool 3: Market Context 🎯 **MEDIUM PRIORITY**

**Value Proposition:**
- Distinguish between portfolio-specific vs. market-wide issues
- Example: "Portfolio down 8%, but SPY only down 2% - underperformance is idiosyncratic"

**Proposed Implementation:**
```python
{
  "name": "get_market_conditions",
  "description": "Get current market conditions and indices",
  "input_schema": {
    "type": "object",
    "properties": {
      "include_sectors": {"type": "boolean", "default": true}
    }
  }
}

# Backend would fetch real-time market data:
# - VIX level
# - Major index performance (SPY, QQQ, IWM)
# - Sector ETF performance (XLK, XLF, XLE, etc.)
# - Market breadth indicators
```

**Estimated Effort:** 1-2 days
**API Cost Impact:** +400-600 tokens (~$0.004)
**External API Costs:** 1-2 FMP API calls per insight

---

### Tool 4: Portfolio Simulation 🎯 **LOW PRIORITY**

**Value Proposition:**
- Test recommendations before suggesting them
- Example: "Adding $100K in SPY puts would reduce beta from 1.2 to 0.8..."

**Proposed Implementation:**
```python
{
  "name": "simulate_trade",
  "description": "Simulate adding/removing positions",
  "input_schema": {
    "type": "object",
    "properties": {
      "action": {"enum": ["add", "remove", "modify"]},
      "symbol": {"type": "string"},
      "quantity": {"type": "number"},
      "position_type": {"enum": ["LONG", "SHORT", "LC", "LP", "SC", "SP"]}
    }
  }
}
```

**Estimated Effort:** 2-3 days (complex)
**API Cost Impact:** +600-1000 tokens (~$0.006)

---

### Implementation Decision Matrix

| Tool | Value | Complexity | Cost Impact | Recommendation |
|------|-------|------------|-------------|----------------|
| Scenario Calculator | HIGH | Medium | Low (+$0.005) | **Implement Next** |
| Historical Trends | MEDIUM | Low | Low (+$0.003) | **Implement Next** |
| Market Context | MEDIUM | Medium | Low (+$0.004) | **Nice to Have** |
| Portfolio Simulation | MEDIUM | High | Medium (+$0.006) | **Future** |

**Recommended Approach:**
1. Monitor user questions - What do they ask the AI?
2. Add tools based on actual needs:
   - If users ask "what if?" → Add Scenario Calculator
   - If users ask "is this normal?" → Add Historical Trends
   - If users blame market → Add Market Context

---

## Other Planned Enhancements (From Original Docs)

### Scheduled/Automated Insights
- Automatically generate daily summaries for all portfolios
- Run at 6 AM daily via APScheduler
- Cost: ~$0.02 per portfolio per day

### Alert Triggers
- Generate insights when specific conditions detected:
  - Volatility > 10% → volatility spike analysis
  - Daily loss > 5% → risk event investigation
  - Correlation > 0.9 → concentration risk analysis
  - Beta shift > 0.3 → market exposure change

### Comparative Analysis
- Compare portfolio to benchmarks (SPY, 60/40 mix)
- Calculate comparative metrics (Sharpe ratio vs. SPY)

### Multi-Portfolio Roll-Up
- Analyze multiple portfolios together (for wealth management)
- Cross-portfolio correlations and overall exposure

---

## Document History

- **December 10, 2025**: Initial creation - documented current AI page architecture
- **December 11, 2025**: Added tool implementation status (16 tools) and future enhancement planning material from AIAssistant folder
