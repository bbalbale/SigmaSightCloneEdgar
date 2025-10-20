# AI Analytical Reasoning Layer - Implementation Plan

**Status**: Phase 1-3 Complete (Production Ready)
**Last Updated**: 2025-10-19
**Owner**: SigmaSight Backend Team

---

## Executive Summary

The AI Analytical Reasoning Layer uses Claude Sonnet 4 to provide deep portfolio analysis beyond simple data retrieval. The system investigates portfolios, identifies anomalies, forms and tests hypotheses, and synthesizes actionable insights.

**Current State**: Core implementation complete and tested with real portfolio data. Ready for frontend integration.

**Key Achievement**: Successfully analyzed a $2.85M portfolio, identifying a 29.4% loss ($837K), root causes (40% alternative investment concentration), and providing 5 specific recommendations - all for $0.0178 (1.78 cents) in 25.7 seconds.

---

## What Has Been Completed

### Phase 1: Database Schema ✅ COMPLETE

**Files Created**:
- `backend/alembic/versions/xxx_add_ai_insights_tables.py` - Migration for ai_insights table
- `backend/app/models/ai_insights.py` - AIInsight and AIInsightTemplate models

**Database Tables**:
1. **ai_insights** - Stores AI-generated portfolio analyses
   - Portfolio linkage, insight type, severity
   - Full analysis markdown, key findings, recommendations
   - Data quality tracking, user feedback
   - Cost and performance metrics (tokens, generation time)
   - Smart caching (24-hour TTL with cache key matching)

2. **ai_insight_templates** - Prompt templates (future use)
   - Version-controlled system prompts
   - Investigation prompt templates
   - Tool definitions for future tool use

### Phase 2: Anthropic Claude Sonnet 4 Integration ✅ COMPLETE

**Files Created**:
- `backend/app/services/anthropic_provider.py` (416 lines)

**Key Features**:
- Direct integration with Anthropic Messages API
- Model: `claude-sonnet-4-20250514`
- Structured prompt system (system + investigation prompts)
- Response parsing for markdown analysis
- Cost tracking: $3.00/M input tokens, $15.00/M output tokens
- Token usage monitoring
- Error handling and retries
- Configurable via environment (.env):
  ```
  ANTHROPIC_API_KEY=sk-ant-api03-...
  ANTHROPIC_MODEL=claude-sonnet-4-20250514
  ANTHROPIC_MAX_TOKENS=8000
  ANTHROPIC_TEMPERATURE=0.7
  ANTHROPIC_TIMEOUT_SECONDS=120
  ```

**System Prompt Design**:
- Analytical reasoning approach: SCAN → HYPOTHESIZE → TEST → COMPARE → CONNECT → SYNTHESIZE
- Data quality awareness and transparency
- Structured output format (Title, Summary, Findings, Analysis, Recommendations, Limitations)
- Professional analyst tone

### Phase 3: Hybrid Context Builder ✅ COMPLETE

**Files Created**:
- `backend/app/services/hybrid_context_builder.py` (364 lines)

**Data Aggregation**:
The context builder queries multiple database sources and assembles comprehensive investigation context:

1. **Portfolio Summary**
   - Name, currency, equity balance
   - Description

2. **Latest Portfolio Snapshot**
   - Total value, gross/net exposure
   - Portfolio delta
   - 21-day realized volatility
   - 90-day calculated beta
   - Daily P&L

3. **Current Positions** (all positions)
   - Symbol, position type, quantity
   - Entry price, last price
   - Market value, unrealized P&L

4. **Risk Metrics**
   - Aggregated Greeks (delta, gamma, theta, vega)
   - Greeks count and last calculation date

5. **Factor Exposures**
   - Position-level factor exposures
   - Aggregated by factor name
   - Quality flags

6. **Correlation Metrics**
   - Overall portfolio correlation
   - Correlation concentration score
   - Effective positions (diversification measure)
   - Data quality indicator

7. **Data Quality Assessment**
   - Per-metric quality (complete/partial/incomplete)
   - Overall quality score
   - Transparent to AI for honest analysis

**Graceful Degradation**:
- Handles missing data without errors
- Marks unavailable metrics clearly
- AI works with whatever data exists

### Phase 4: Analytical Reasoning Service ✅ COMPLETE

**Files Updated**:
- `backend/app/services/analytical_reasoning_service.py`

**Orchestration Flow**:
```python
async def investigate_portfolio(
    db: AsyncSession,
    portfolio_id: UUID,
    insight_type: InsightType,
    focus_area: Optional[str] = None,
    user_question: Optional[str] = None
) -> AIInsight
```

**Features**:
1. **Smart Caching** - Checks for recent similar analyses (24-hour window)
2. **Context Building** - Aggregates data via hybrid context builder
3. **AI Investigation** - Calls Anthropic provider with formatted prompt
4. **Result Storage** - Saves to database with full metadata
5. **Performance Tracking** - Logs cost, time, tokens per investigation

**Supported Insight Types**:
- `DAILY_SUMMARY` - Comprehensive daily portfolio review
- `VOLATILITY_ANALYSIS` - Volatility patterns and risk factors
- `CONCENTRATION_RISK` - Concentration and diversification assessment
- `HEDGE_QUALITY` - Hedge effectiveness evaluation
- `FACTOR_EXPOSURE` - Factor exposure and systematic risk analysis
- `STRESS_TEST_REVIEW` - Stress test results review
- `CUSTOM` - User-defined custom analysis

### Testing & Validation ✅ COMPLETE

**Test Scripts Created**:
- `backend/scripts/test_claude_investigation.py` - Basic Claude API test
- `backend/scripts/test_full_integration.py` - End-to-end real data test

**Test Results** (2025-10-19):
```
Portfolio: Demo High Net Worth Investor Portfolio (30 positions, $2.85M equity)
Analysis Type: Daily Summary
Cost: $0.0178 (1.78 cents)
Time: 25.7 seconds
Tokens: 1,410 input + 902 output = 2,312 total
Severity: CRITICAL

Key Finding: 29.4% portfolio loss ($837K)
Root Causes:
- 40% concentration in alternative investments
- Healthcare sector underperformance (UNH -$55.4K)
- Low diversification (4.6 effective positions from 30 holdings)
- High volatility (6.28% 21-day realized)

Recommendations: 5 specific, actionable steps
- Reduce alternatives from 40% → 20-25%
- Review healthcare positions for tax-loss harvesting
- Enhance diversification (reduce overlapping ETFs)
- Implement position sizing limits (max 5%)
- Establish 10-15% cash buffer
```

**Data Quality Handling**:
✅ Handled incomplete Greeks data gracefully
✅ Worked with partial factor exposures
✅ Transparently noted data limitations in output
✅ Identified potential data duplication (BRK-B entries)

---

## Frontend Integration Plan

### Phase 5: API Endpoints (Next Step)

**Recommended Endpoint Structure**:

#### 1. Generate New Insight
```http
POST /api/v1/insights/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "portfolio_id": "uuid",
  "insight_type": "daily_summary",
  "focus_area": "portfolio_overview",  // optional
  "user_question": "Why is my tech exposure so high?"  // optional
}

Response: 201 Created
{
  "id": "insight-uuid",
  "title": "Daily Summary Analysis",
  "severity": "critical",
  "summary": "This $2.85M equity portfolio...",
  "key_findings": ["...", "..."],
  "recommendations": ["...", "..."],
  "full_analysis": "# Markdown analysis...",
  "data_limitations": "Alternative investments valued at cost...",
  "created_at": "2025-10-19T22:58:55Z",
  "performance": {
    "cost_usd": 0.0178,
    "generation_time_ms": 25657,
    "token_count": 2312
  }
}
```

#### 2. List Portfolio Insights
```http
GET /api/v1/insights/portfolio/{portfolio_id}
  ?insight_type=daily_summary  // optional filter
  &days_back=7                  // optional, default 30
  &limit=10                     // optional, default 20

Response: 200 OK
{
  "insights": [
    {
      "id": "uuid",
      "title": "...",
      "severity": "critical",
      "summary": "...",
      "created_at": "...",
      "viewed": false
    }
  ],
  "total": 15,
  "has_more": true
}
```

#### 3. Get Single Insight
```http
GET /api/v1/insights/{insight_id}

Response: 200 OK
{
  "id": "uuid",
  "portfolio_id": "uuid",
  "insight_type": "daily_summary",
  "title": "...",
  "severity": "critical",
  "summary": "...",
  "key_findings": [...],
  "recommendations": [...],
  "full_analysis": "...",
  "data_limitations": "...",
  "focus_area": "portfolio_overview",
  "created_at": "...",
  "viewed": true,
  "dismissed": false,
  "user_rating": null,
  "user_feedback": null,
  "performance": {...}
}
```

#### 4. Mark Insight as Viewed/Dismissed
```http
PATCH /api/v1/insights/{insight_id}
Content-Type: application/json

{
  "viewed": true,
  "dismissed": false
}

Response: 200 OK
```

#### 5. Rate Insight (User Feedback)
```http
POST /api/v1/insights/{insight_id}/feedback
Content-Type: application/json

{
  "rating": 4.5,  // 1-5 scale
  "feedback": "Very helpful analysis, identified issues I missed"
}

Response: 200 OK
```

### Frontend UI Components

#### Component 1: Insights Dashboard
**Location**: `/app/insights` or `/app/portfolio/{id}/insights`

**Features**:
- List of recent insights for portfolio
- Severity badges (Critical, Warning, Elevated, Normal, Info)
- Quick summary preview
- Unread/new indicator
- Filter by insight type
- Generate new insight button

**Mock Layout**:
```
┌─────────────────────────────────────────────────────┐
│ Portfolio Insights                    [+ Generate] │
├─────────────────────────────────────────────────────┤
│ Filters: [All Types ▼] [Last 30 Days ▼]          │
├─────────────────────────────────────────────────────┤
│ 🔴 CRITICAL • Today 3:58 PM                        │
│ Daily Summary Analysis                              │
│ Portfolio has experienced substantial value         │
│ erosion of 29.4% ($837K loss)...                   │
│ [View Details →]                                    │
├─────────────────────────────────────────────────────┤
│ ⚠️  WARNING • Yesterday                            │
│ Volatility Analysis                                 │
│ 21-day realized volatility elevated at 6.28%...   │
│ [View Details →]                                    │
└─────────────────────────────────────────────────────┘
```

#### Component 2: Insight Detail View
**Location**: `/app/insights/{insight_id}`

**Sections**:
1. **Header**
   - Title
   - Severity badge
   - Timestamp
   - Performance metrics (cost, time, tokens)

2. **Executive Summary**
   - 2-3 sentence summary
   - Data quality indicator

3. **Key Findings**
   - Bulleted list with icons
   - Highlight important numbers

4. **Detailed Analysis**
   - Full markdown rendering
   - Charts/graphs (if data available)
   - Expandable sections

5. **Recommendations**
   - Actionable steps
   - Prioritized list
   - Link to relevant portfolio actions

6. **Data Limitations**
   - Transparency section
   - Expandable detail

7. **User Feedback**
   - Star rating (1-5)
   - Text feedback box
   - "Was this helpful?" thumbs up/down

**Mock Layout**:
```
┌─────────────────────────────────────────────────────┐
│ ← Back to Insights                                  │
├─────────────────────────────────────────────────────┤
│ 🔴 CRITICAL                        Today 3:58 PM   │
│                                                      │
│ Daily Summary Analysis                              │
│                                                      │
│ This $2.85M equity portfolio has experienced        │
│ substantial value erosion of 29.4% ($837K loss)... │
│                                                      │
│ ⚡ Generated in 25.7s • $0.02 • 2,312 tokens       │
├─────────────────────────────────────────────────────┤
│ 📊 Key Findings                                     │
│                                                      │
│ • Severe underperformance: $2.01M vs $2.85M        │
│   equity balance (29.4% loss)                       │
│                                                      │
│ • Alternative investment concentration: $712.5K     │
│   (40% of equity) in illiquid positions            │
│                                                      │
│ • Low diversification: Only 4.6 effective           │
│   positions despite 30 holdings                     │
│   ...                                               │
├─────────────────────────────────────────────────────┤
│ 📝 Detailed Analysis               [Expand All ▼] │
│                                                      │
│ [Markdown content rendered here...]                 │
├─────────────────────────────────────────────────────┤
│ 💡 Recommendations                                  │
│                                                      │
│ 1. Immediate rebalancing: Reduce alternatives       │
│    from 40% → 20-25%                                │
│    [View Positions →]                               │
│                                                      │
│ 2. Healthcare review: Conduct fundamental           │
│    analysis on UNH position                         │
│    [Analyze Position →]                             │
│    ...                                              │
├─────────────────────────────────────────────────────┤
│ ⚠️  Data Limitations                               │
│                                                      │
│ Alternative investment positions valued at cost...  │
├─────────────────────────────────────────────────────┤
│ Was this insight helpful?                           │
│ ⭐⭐⭐⭐⭐                                          │
│ [Optional feedback...]                              │
│ [Submit Feedback]                                   │
└─────────────────────────────────────────────────────┘
```

#### Component 3: Generate Insight Modal
**Trigger**: "Generate Insight" button

**Form Fields**:
- Insight Type (dropdown)
  - Daily Summary
  - Volatility Analysis
  - Concentration Risk
  - Hedge Quality
  - Factor Exposure
  - Custom Question
- Focus Area (optional text, e.g., "tech exposure", "options risk")
- Custom Question (shown if "Custom Question" selected)

**UX Flow**:
1. User clicks "Generate Insight"
2. Modal opens with form
3. User selects insight type
4. (Optional) Adds focus area or custom question
5. Clicks "Generate"
6. Loading state: "Claude is analyzing your portfolio..."
7. Progress indicator (estimated 20-30s)
8. On completion: Redirect to insight detail view
9. Show success toast: "Insight generated ($0.02)"

#### Component 4: Insights Widget (Dashboard)
**Location**: Main portfolio dashboard

**Mini widget showing**:
- Latest critical/warning insight
- Count of unread insights
- Quick link to full insights page

```
┌─────────────────────────────────┐
│ Latest Insight          [View All →] │
├─────────────────────────────────┤
│ 🔴 Portfolio Value Erosion      │
│ Critical issues detected in     │
│ alternative investments...      │
│                                  │
│ 3 unread insights               │
└─────────────────────────────────┘
```

### Frontend Implementation Files

**Recommended Structure**:
```
frontend/
├── app/
│   └── insights/
│       ├── page.tsx                    # Insights list page
│       ├── [insight_id]/
│       │   └── page.tsx                # Insight detail page
│       └── generate/
│           └── page.tsx                # Generate insight form
├── components/
│   └── insights/
│       ├── InsightsList.tsx            # List of insights
│       ├── InsightCard.tsx             # Single insight preview
│       ├── InsightDetail.tsx           # Full insight view
│       ├── InsightSeverityBadge.tsx    # Severity indicator
│       ├── GenerateInsightModal.tsx    # Generation form
│       ├── InsightFeedback.tsx         # Rating/feedback form
│       └── InsightWidget.tsx           # Dashboard widget
└── hooks/
    └── useInsights.ts                  # API hooks for insights
```

### API Integration Code Example

**hooks/useInsights.ts**:
```typescript
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface AIInsight {
  id: string;
  portfolio_id: string;
  insight_type: string;
  title: string;
  severity: 'critical' | 'warning' | 'elevated' | 'normal' | 'info';
  summary: string;
  key_findings: string[];
  recommendations: string[];
  full_analysis: string;
  data_limitations: string;
  created_at: string;
  viewed: boolean;
  dismissed: boolean;
  performance: {
    cost_usd: number;
    generation_time_ms: number;
    token_count: number;
  };
}

export function useInsights(portfolioId: string) {
  return useQuery({
    queryKey: ['insights', portfolioId],
    queryFn: async () => {
      const res = await apiClient.get(`/insights/portfolio/${portfolioId}`);
      return res.data.insights as AIInsight[];
    }
  });
}

export function useGenerateInsight() {
  return useMutation({
    mutationFn: async (params: {
      portfolio_id: string;
      insight_type: string;
      focus_area?: string;
      user_question?: string;
    }) => {
      const res = await apiClient.post('/insights/generate', params);
      return res.data as AIInsight;
    }
  });
}

export function useInsightFeedback(insightId: string) {
  return useMutation({
    mutationFn: async (feedback: { rating: number; feedback?: string }) => {
      await apiClient.post(`/insights/${insightId}/feedback`, feedback);
    }
  });
}
```

### Progressive Rollout Strategy

**Phase 5A: MVP Launch** (Week 1)
- ✅ Generate insight API endpoint
- ✅ List insights API endpoint
- ✅ Get single insight API endpoint
- ✅ Basic insights list page
- ✅ Insight detail view
- ✅ Generate insight button (daily summary only)
- 🎯 Target: Get first user feedback

**Phase 5B: Enhanced UX** (Week 2)
- ✅ Mark viewed/dismissed endpoints
- ✅ All insight types available
- ✅ Focus area and custom questions
- ✅ Dashboard widget
- ✅ User feedback/rating
- 🎯 Target: Collect usage analytics

**Phase 5C: Polish** (Week 3)
- ✅ Insight filtering and search
- ✅ Performance metrics display
- ✅ Data quality indicators
- ✅ Export insights as PDF
- ✅ Email notifications for critical insights
- 🎯 Target: Production-ready

---

## Future Enhancements (Post-MVP)

### Enhancement 1: Analytical Tools for Claude

**Purpose**: Enable Claude to perform calculations during investigation rather than just analyzing pre-calculated data.

#### Tool 1: Scenario Calculator 🎯 **HIGH PRIORITY**

**Value Proposition**:
- Claude can test "what-if" scenarios proactively
- Example: "I notice high tech exposure. Let me test a 15% tech correction scenario..."
- Enables predictive risk analysis vs. just descriptive

**Implementation**:
```python
# Tool definition
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

# Backend service
class ScenarioCalculator:
    async def calculate_impact(
        self,
        portfolio_id: UUID,
        scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate portfolio impact of market scenarios.

        Returns:
          - position_impacts: P&L per position
          - total_pnl: Overall portfolio P&L
          - greeks_changes: How Greeks shift
          - risk_metrics: Updated volatility, beta, etc.
        """
```

**Estimated Effort**: 1-2 days
**API Cost Impact**: +500-800 tokens per tool call (~$0.005)

#### Tool 2: Historical Trend Analysis 🎯 **MEDIUM PRIORITY**

**Value Proposition**:
- Claude can determine if current metrics are elevated vs. historical norms
- Example: "Current volatility of 6.28% is in the 85th percentile for this portfolio..."
- Contextualizes point-in-time metrics

**Implementation**:
```python
# Tool definition
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

# Backend service
class MetricsHistoryService:
    async def get_time_series(
        self,
        portfolio_id: UUID,
        metrics: List[str],
        days_back: int = 180
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query portfolio_snapshots table for historical metrics.

        Returns time series data per metric with percentile calculations.
        """
```

**Estimated Effort**: 1 day
**API Cost Impact**: +300-500 tokens per call (~$0.003)

#### Tool 3: Market Context 🎯 **MEDIUM PRIORITY**

**Value Proposition**:
- Distinguish between portfolio-specific vs. market-wide issues
- Example: "Portfolio down 8%, but SPY only down 2% - underperformance is idiosyncratic"

**Implementation**:
```python
# Tool definition
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

# Backend service
class MarketContextService:
    async def get_current_conditions(
        self,
        include_sectors: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch real-time market data:
        - VIX level
        - Major index performance (SPY, QQQ, IWM)
        - Sector ETF performance (XLK, XLF, XLE, etc.)
        - Market breadth indicators
        """
```

**Estimated Effort**: 1-2 days
**API Cost Impact**: +400-600 tokens (~$0.004)
**External API Costs**: 1-2 FMP API calls per insight

#### Tool 4: Portfolio Simulation 🎯 **LOW PRIORITY**

**Value Proposition**:
- Test recommendations before suggesting them
- Example: "Adding $100K in SPY puts would reduce beta from 1.2 to 0.8..."

**Implementation**:
```python
# Tool definition
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

**Estimated Effort**: 2-3 days (complex)
**API Cost Impact**: +600-1000 tokens (~$0.006)

#### Tool 5: Deep Position Drill-Down 🎯 **LOW PRIORITY**

**Not recommended** - duplicates data already in prompt. Only needed if prompt becomes too large.

### Implementation Decision Matrix

| Tool | Value | Complexity | Cost Impact | Recommendation |
|------|-------|------------|-------------|----------------|
| Scenario Calculator | HIGH | Medium | Low (+$0.005) | **Implement Post-MVP** |
| Historical Trends | MEDIUM | Low | Low (+$0.003) | **Implement Post-MVP** |
| Market Context | MEDIUM | Medium | Low (+$0.004) | **Nice to Have** |
| Portfolio Simulation | MEDIUM | High | Medium (+$0.006) | **Future** |
| Position Drill-Down | LOW | Low | Low | **Skip** |

**Recommended Approach**:
1. **Ship MVP** with current implementation (no tools)
2. **Monitor user questions** - What do they ask Claude?
3. **Add tools based on actual needs**:
   - If users ask "what if?" → Add Scenario Calculator
   - If users ask "is this normal?" → Add Historical Trends
   - If users blame market → Add Market Context

### Enhancement 2: Scheduled/Automated Insights

**Feature**: Automatically generate daily summaries for all portfolios

**Implementation**:
```python
# Celery task or APScheduler job
@scheduler.scheduled_job('cron', hour=6, minute=0)  # 6 AM daily
async def generate_daily_insights():
    """Generate daily summary for all active portfolios."""
    async with get_async_session() as db:
        portfolios = await db.execute(select(Portfolio))

        for portfolio in portfolios.scalars():
            # Only generate if no insight in last 24h
            recent = await check_recent_insight(portfolio.id, "daily_summary")
            if not recent:
                await analytical_reasoning_service.investigate_portfolio(
                    db=db,
                    portfolio_id=portfolio.id,
                    insight_type=InsightType.DAILY_SUMMARY
                )
```

**Cost Consideration**:
- ~$0.02 per portfolio per day
- 100 portfolios = $2/day = $60/month
- Add budget controls and user opt-in

**Estimated Effort**: 1 day

### Enhancement 3: Alert Triggers

**Feature**: Generate insights when specific conditions detected

**Triggers**:
- Volatility > 10% (volatility spike analysis)
- Daily loss > 5% (risk event investigation)
- Correlation > 0.9 (concentration risk analysis)
- Beta shift > 0.3 (market exposure change)

**Implementation**:
```python
class InsightTriggerMonitor:
    """Monitor portfolio metrics and trigger insights when thresholds exceeded."""

    async def check_triggers(self, portfolio_id: UUID):
        snapshot = await get_latest_snapshot(portfolio_id)

        triggers = []
        if snapshot.realized_volatility_21d > 0.10:
            triggers.append(InsightType.VOLATILITY_ANALYSIS)
        if snapshot.daily_pnl / snapshot.total_value < -0.05:
            triggers.append(InsightType.DAILY_SUMMARY)
        # ... more conditions

        for insight_type in triggers:
            await generate_insight(portfolio_id, insight_type)
```

**Estimated Effort**: 2-3 days

### Enhancement 4: Comparative Analysis

**Feature**: Compare portfolio to benchmarks or peer portfolios

**Example Questions**:
- "How does my portfolio compare to a 60/40 stock/bond mix?"
- "Am I taking more risk than similar portfolios?"
- "What's my Sharpe ratio vs. SPY?"

**Implementation**:
- Query benchmark data (SPY, AGG, 60/40 mix)
- Calculate comparative metrics
- Pass to Claude for interpretation

**Estimated Effort**: 3-4 days

### Enhancement 5: Multi-Portfolio Roll-Up

**Feature**: Analyze multiple portfolios together (for wealth management)

**Use Case**:
- Family office with 5 portfolios
- "Overall exposure across all portfolios"
- "Cross-portfolio correlations"

**Implementation**:
- Aggregate context from multiple portfolios
- Generate combined insight
- Identify cross-portfolio risks

**Estimated Effort**: 2-3 days

---

## Cost Management & Monitoring

### Cost Projections

**Current Costs** (based on testing):
- Daily Summary: ~$0.018 per analysis
- Average tokens: 2,300 total (1,400 input + 900 output)

**Projected Monthly Costs**:

| Scenario | Portfolios | Insights/Day | Monthly Cost |
|----------|------------|--------------|--------------|
| Light Use | 50 | 0.5 | $13.50 |
| Medium Use | 100 | 1.0 | $54.00 |
| Heavy Use | 500 | 2.0 | $540.00 |
| Enterprise | 2000 | 3.0 | $3,240.00 |

### Cost Controls

**Recommended Safeguards**:

1. **Rate Limiting**
   - Max 10 insights per portfolio per day
   - Max 5 custom questions per day per user
   - Cooldown: 5 minutes between generations

2. **Budget Alerts**
   - Email admin if daily spend > $10
   - Hard stop if monthly spend > $1,000
   - Per-user spend tracking

3. **Caching Strategy**
   - 24-hour cache for daily summaries
   - Same portfolio + same insight type → return cached
   - Custom questions always fresh

4. **Tiered Pricing** (future)
   - Free tier: 5 insights/month
   - Pro tier: 50 insights/month
   - Enterprise: Unlimited

**Implementation**:
```python
# Cost monitoring
class CostMonitor:
    async def check_budget(self, user_id: UUID) -> bool:
        daily_spend = await get_daily_spend(user_id)
        monthly_spend = await get_monthly_spend(user_id)

        if daily_spend > 10.0:
            await alert_admin(f"User {user_id} daily spend: ${daily_spend}")
        if monthly_spend > 1000.0:
            return False  # Block generation
        return True
```

### Performance Optimization

**Reduce Token Usage**:
1. **Smart Context Truncation**
   - Limit positions to top 20 by absolute value
   - Summarize factor exposures < 0.01
   - Skip positions with $0 market value

2. **Prompt Engineering**
   - Shorter system prompts for simple insight types
   - Use bullet points vs. full sentences for data
   - Reference format instead of verbose descriptions

3. **Streaming Responses** (future)
   - Show partial analysis as it generates
   - Better UX, same cost
   - Requires frontend SSE support

---

## Security & Compliance

### Data Privacy

**Considerations**:
- Portfolio data sent to Anthropic API
- No Anthropic data retention (per their API policy)
- User consent for AI analysis

**Recommendations**:
1. **Terms of Service Update**
   - Disclose AI analysis uses external API
   - User opt-in for AI features

2. **Data Anonymization** (optional)
   - Remove PII from prompts
   - Use generic labels ("Position 1", "Position 2")

3. **Audit Logging**
   - Log all API calls to Anthropic
   - Track what data sent when
   - Compliance trail

### API Key Security

**Current**: API key in `.env` file (backend only)

**Production Recommendations**:
- Store in environment variables (Railway/AWS)
- Rotate keys quarterly
- Monitor for unauthorized usage
- Use separate keys for dev/staging/prod

---

## Testing Strategy

### Unit Tests (TODO)

**Files to Test**:
```python
# tests/test_anthropic_provider.py
class TestAnthropicProvider:
    async def test_investigate_with_mock_response()
    async def test_cost_calculation()
    async def test_response_parsing()
    async def test_error_handling()

# tests/test_hybrid_context_builder.py
class TestHybridContextBuilder:
    async def test_build_context_complete_data()
    async def test_build_context_missing_data()
    async def test_data_quality_assessment()
    async def test_factor_exposure_aggregation()

# tests/test_analytical_reasoning_service.py
class TestAnalyticalReasoningService:
    async def test_cache_hit()
    async def test_cache_miss()
    async def test_insight_storage()
```

### Integration Tests (TODO)

**Test Scenarios**:
1. End-to-end generation with test portfolio
2. Cost tracking accuracy
3. Caching behavior (24-hour TTL)
4. Graceful degradation with missing data
5. Error handling (API timeout, invalid response)

### Load Testing

**Questions to Answer**:
- Can we handle 10 concurrent insight generations?
- Database performance under load?
- API rate limits from Anthropic?

**Tools**: Locust or Apache JMeter

---

## Deployment Checklist

### Environment Variables

**Required in Production**:
```bash
# Anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_MAX_TOKENS=8000
ANTHROPIC_TEMPERATURE=0.7
ANTHROPIC_TIMEOUT_SECONDS=120

# Database (already configured)
DATABASE_URL=postgresql+asyncpg://...

# Cost Monitoring (new)
INSIGHTS_DAILY_BUDGET=10.0
INSIGHTS_MONTHLY_BUDGET=1000.0
INSIGHTS_MAX_PER_PORTFOLIO_DAILY=10
```

### Database Migration

**Run on Production**:
```bash
uv run alembic upgrade head
```

**Verify Tables**:
```sql
SELECT COUNT(*) FROM ai_insights;  -- Should be 0
SELECT COUNT(*) FROM ai_insight_templates;  -- Should be 0
```

### Monitoring Setup

**Metrics to Track**:
- Insight generation count (per hour/day)
- Average generation time
- Average cost per insight
- Cache hit rate
- User satisfaction rating (from feedback)
- Error rate

**Alerting**:
- Error rate > 5%
- Generation time > 60s
- Daily cost > budget
- API timeout errors

### Documentation

**Update for Launch**:
- [ ] API Reference docs (add insights endpoints)
- [ ] User guide (how to generate insights)
- [ ] Developer docs (how the system works)
- [ ] Pricing/billing docs (cost transparency)

---

## Success Metrics

### Product Metrics

**Track After Launch**:
1. **Adoption**
   - % of users who generate at least 1 insight
   - Insights generated per active user per week
   - Insight types most commonly used

2. **Engagement**
   - % of insights viewed (not just generated)
   - % of insights rated/given feedback
   - Average user rating (1-5 stars)
   - Time spent reading insights

3. **Value**
   - User quotes from feedback
   - Reported actions taken based on insights
   - NPS score correlation

### Technical Metrics

**Monitor Ongoing**:
1. **Performance**
   - P50/P95/P99 generation time
   - Cache hit rate (target > 30%)
   - Error rate (target < 1%)

2. **Cost**
   - Average cost per insight
   - Monthly total cost
   - Cost per active user

3. **Quality**
   - Average user rating
   - % of insights dismissed
   - User feedback sentiment

---

## Timeline & Resources

### Immediate Next Steps (This Week)

**Day 1-2: API Development**
- [ ] Create `/api/v1/insights/` endpoint module
- [ ] Implement generate endpoint (POST /generate)
- [ ] Implement list endpoint (GET /portfolio/{id})
- [ ] Implement detail endpoint (GET /{id})
- [ ] Add to API router
- [ ] Test with Postman/curl

**Day 3-4: Frontend Foundation**
- [ ] Create insights routes (`/app/insights/`)
- [ ] Build InsightsList component
- [ ] Build InsightDetail component
- [ ] Implement useInsights hook
- [ ] Basic styling

**Day 5: Testing & Polish**
- [ ] End-to-end testing
- [ ] Error handling
- [ ] Loading states
- [ ] Documentation

### Medium Term (Weeks 2-3)

**Week 2: Enhanced Features**
- [ ] User feedback/rating system
- [ ] All insight types enabled
- [ ] Focus area and custom questions
- [ ] Dashboard widget
- [ ] Mark viewed/dismissed

**Week 3: Production Ready**
- [ ] Cost monitoring dashboard
- [ ] Rate limiting
- [ ] Budget alerts
- [ ] Unit tests
- [ ] Integration tests
- [ ] Production deployment

### Long Term (Months 2-3)

**Month 2: Tools Enhancement** (if user feedback warrants)
- [ ] Scenario calculator tool
- [ ] Historical trends tool
- [ ] Market context tool
- [ ] Testing and validation

**Month 3: Automation**
- [ ] Scheduled daily insights
- [ ] Alert triggers
- [ ] Email notifications
- [ ] Multi-portfolio support

---

## Team & Responsibilities

**Backend Developer**:
- API endpoint implementation
- Cost monitoring and rate limiting
- Tool development (if pursuing)
- Database optimization
- Testing

**Frontend Developer**:
- UI components for insights
- API integration
- User feedback system
- Dashboard widget
- Mobile responsiveness

**Product Manager**:
- User feedback collection
- Feature prioritization
- Success metrics tracking
- Cost/benefit analysis for tools

**QA/Testing**:
- Integration testing
- Load testing
- Security review
- User acceptance testing

---

## Questions & Decisions Needed

### Open Questions

1. **Pricing Strategy**
   - Free tier limits?
   - How to monetize AI features?
   - Cost pass-through vs. bundled?

2. **User Experience**
   - Auto-generate daily summaries or user-initiated only?
   - Push notifications for critical insights?
   - Email digest of insights?

3. **Data Privacy**
   - User consent approach?
   - Data anonymization needed?
   - Regional compliance (GDPR, etc.)?

4. **Tool Priority**
   - Wait for user feedback or build proactively?
   - Which tool provides most value?
   - Cost/benefit of tool development?

### Decisions Needed

- [ ] **Frontend routing**: `/insights` or `/portfolio/{id}/insights`?
- [ ] **Default insight type**: Always daily summary or ask user?
- [ ] **Auto-generation**: Scheduled daily or on-demand only?
- [ ] **Tool development**: MVP first or include scenario calculator?
- [ ] **Budget limits**: Hard caps or soft warnings?

---

## Conclusion

The AI Analytical Reasoning Layer is **production-ready** for MVP launch. The core implementation provides sophisticated portfolio analysis at low cost (~$0.02 per insight) with 25-30 second generation time.

**Immediate Priority**: Frontend integration to surface this capability to users.

**Next Enhancement**: Based on user feedback, potentially add analytical tools for scenario testing and historical trend analysis.

**Success Criteria**:
- 60%+ of active users generate at least 1 insight per week
- Average user rating > 4.0/5.0
- Monthly cost < $100 for first 100 users

---

**Document Location**: `backend/_docs/AI_Analytical_Reasoning_Implementation_Plan.md`

For questions or updates, contact the backend team.
