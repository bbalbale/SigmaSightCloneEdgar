# SigmaSight AI - Hybrid Interpretation-First Implementation Plan

**Date**: December 17, 2025
**Author**: Claude Code
**Version**: 3.0 - **Option C: Hybrid Interpretation-First with Tools on Demand**
**Status**: Planning - Ready for Implementation

---

## Executive Summary

**Core Philosophy**: AI is a **smart interpreter** that gets pre-calculated metrics upfront BUT can call tools when needed for deep dives.

**Hybrid Approach (Best of Both Worlds)**:
- ✅ **Default: Fast Interpretation** - AI gets full analytics bundle, interprets in ~15-20s (80% of cases)
- ✅ **On-Demand: Tool Calling** - AI can call tools for deep dives when needed (20% of cases)
- ✅ **Conversational Tone** - "Trusted partner" voice, not robotic
- ✅ **Flexible & Future-Proof** - Easy to add metrics or tools

**What We're NOT Doing**:
- ❌ Forcing AI to always call tools (slow, expensive)
- ❌ Removing tools entirely (lose flexibility)
- ❌ Duplicating what Risk Metrics page already shows
- ❌ Creating a "hero panel" that mirrors Command Center

**What We ARE Doing**:
- ✅ **Always fetch analytics bundle first** (pre-calculated metrics)
- ✅ **Prompt AI to prefer interpretation** (use tools only when needed)
- ✅ **Keep tools available** (for deep dives and specific questions)
- ✅ **Track tool usage** (monitor and optimize)

**Estimated Effort**: 4-5 hours (Option C is incremental change)

---

## Part I: Current State Analysis

### What Data Already Exists

#### Command Center Page
Displays real-time portfolio metrics:
- Equity balance, target return EOY
- Gross/net exposure, long/short exposure
- Capital flows (total, net 30d, last change)
- YTD/MTD P&L, cash balance
- Portfolio beta (90d, 1y)
- Stress test summary
- Volatility metrics (21d current, 63d historical, 21d forward forecast)

#### Risk Metrics Page
Displays comprehensive risk analytics:
- Factor exposures (Market, Value, Growth, Momentum, Quality, Size, Low Vol)
- Spread factors (detailed breakdown)
- Stress test scenarios (8 scenarios with impact)
- Correlation matrix (position correlations)
- Volatility metrics with HAR forecasting
- Sector exposure vs S&P 500
- Market beta comparison

#### Available Backend Endpoints (Pre-Calculated)
All calculated by `batch_orchestrator`, NOT by AI:

1. `/api/v1/analytics/portfolio/{id}/overview` - Portfolio summary
2. `/api/v1/analytics/portfolio/{id}/sector-exposure` - Sector breakdown
3. `/api/v1/analytics/portfolio/{id}/concentration` - HHI, top positions %
4. `/api/v1/analytics/portfolio/{id}/volatility` - HAR forecasting
5. `/api/v1/analytics/portfolio/{id}/factor-exposures` - Factor loadings
6. `/api/v1/analytics/portfolio/{id}/correlation-matrix` - Correlations
7. `/api/v1/analytics/portfolio/{id}/stress-test` - Scenario analysis
8. `/api/v1/data/portfolio/{id}/complete` - Full snapshot
9. `/api/v1/data/company-profile/{symbol}` - Company fundamentals

### Current SigmaSight AI Page

**Layout**: Two-column split
- **Left**: Daily Summary Analysis (insight generation)
- **Right**: Chat with SigmaSight AI (Claude streaming)

**What Works**:
- ✅ Insight generation via `/api/v1/insights/generate`
- ✅ SSE streaming chat with conversation history
- ✅ Severity badges (Critical, Warning, Elevated, Normal, Info)
- ✅ Insight cards with expand/collapse
- ✅ Dismiss functionality
- ✅ Performance tracking (cost, tokens, generation time)

**What's Missing**:
- ❌ AI interprets pre-calculated data (currently generates generic insights)
- ❌ Connection between insights and chat (no "Send to Chat" button)
- ❌ Quick-start prompts for users
- ❌ Severity legend (users don't know what levels mean)
- ❌ Focus area picker for targeted analysis
- ❌ Context-aware chat responses (doesn't reference portfolio metrics)
- ❌ Conversational tone (currently too robotic/alarmist)

---

## Part II: Implementation Strategy - Option C (Hybrid)

### High-Level Architecture

```
User Request: "What are my biggest risks?"
    ↓
Frontend UI (SigmaSight AI page)
    ↓
Backend Insight Service
    ↓
STEP 1: ALWAYS Fetch Analytics Bundle FIRST (1-2s)
    ├─→ GET /api/v1/analytics/portfolio/{id}/overview
    ├─→ GET /api/v1/analytics/portfolio/{id}/sector-exposure
    ├─→ GET /api/v1/analytics/portfolio/{id}/concentration
    ├─→ GET /api/v1/analytics/portfolio/{id}/volatility
    ├─→ GET /api/v1/analytics/portfolio/{id}/factor-exposures
    ├─→ GET /api/v1/analytics/portfolio/{id}/correlation-matrix
    └─→ GET /api/v1/analytics/portfolio/{id}/stress-test
    ↓
STEP 2: Build Hybrid Context
    ├─→ Pre-calculated analytics (from bundle)
    ├─→ Portfolio snapshot (from hybrid_context_builder)
    └─→ Merge both into comprehensive context
    ↓
STEP 3: Send to Claude with BOTH:
    ├─→ Full analytics bundle (in prompt) ← NEW
    ├─→ Tools available (optional) ← KEEP
    └─→ Interpretation-first guidance ← NEW
    ↓
STEP 4: Claude Decides (Based on Prompt Guidance)
    ├─→ [80% of cases] "I have enough data" → Interpret directly (FAST - 15-20s)
    │   - Reference specific metrics
    │   - Synthesize across data
    │   - Conversational tone
    │   - No tool calls
    │
    └─→ [20% of cases] "I need more info" → Call tool → Then interpret (SLOWER - 30-40s)
        - User asks about specific company
        - Need target prices or tags
        - Missing data in bundle
    ↓
Return to User
    ├─→ Conversational insight with specific metrics
    ├─→ Performance tracking (tool_calls_count: 0-3)
    └─→ Fast most of the time, deep when needed
```

### Key Differences from Pure Interpretation (Option B)

| Aspect | Option B (Pure) | Option C (Hybrid) |
|--------|-----------------|-------------------|
| **Analytics Bundle** | Fetched | Fetched (SAME) |
| **Tools Available** | ❌ No | ✅ Yes (optional) |
| **Prompt Strategy** | N/A | "Prefer interpretation, use tools when needed" |
| **Speed (avg)** | 15-18s | 18-22s |
| **Speed (P95)** | 20s | 35s (when tools used) |
| **Flexibility** | Low | High |
| **Tool Usage** | 0% | 15-20% |
| **Cost** | $0.02 | $0.022 |

### Key Principles

1. **AI Never Calculates** - Only interprets pre-calculated numbers
2. **No Duplicate UI** - Don't show metrics that Command Center/Risk Metrics already display
3. **Conversational Tone** - Ask questions, don't prescribe (see `18-CONVERSATIONAL-AI-PARTNER-VISION.md`)
4. **Cross-Metric Synthesis** - AI's value is connecting dots across metrics
5. **User Control** - Focus area picker, quick prompts, "Send to Chat" actions

---

## Part III: Detailed Implementation Plan

### Phase 1: Backend - Insight Generation as Interpretation (Week 1, Days 1-2)

**Goal**: Update backend to fetch pre-calculated data and send to AI for interpretation

#### Step 1.1: Create Analytics Bundle Fetcher (3-4 hours)

**File**: `backend/app/services/analytics_bundle.py` (NEW)

```python
"""
Analytics Bundle Service

Fetches all pre-calculated analytics for a portfolio.
Used by AI insight generation to provide context for interpretation.

NO CALCULATIONS ARE DONE HERE - just fetching from existing services.
"""

from uuid import UUID
from typing import Dict, Any, Optional
from app.services.analytics_service import analytics_service
from app.core.logging import get_logger

logger = get_logger(__name__)

class AnalyticsBundleService:
    """Fetches pre-calculated analytics from existing endpoints"""

    async def fetch_portfolio_analytics_bundle(
        self,
        portfolio_id: UUID,
        focus_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all pre-calculated analytics for a portfolio.

        This is the data that batch_orchestrator already calculated.
        AI will interpret this data, not recalculate it.

        Args:
            portfolio_id: Portfolio UUID
            focus_area: Optional focus area to prioritize certain metrics

        Returns:
            Dict with all pre-calculated metrics
        """
        logger.info(f"Fetching analytics bundle for portfolio {portfolio_id}")

        # Fetch all metrics in parallel (all pre-calculated by batch_orchestrator)
        bundle = {
            "overview": await analytics_service.get_portfolio_overview(portfolio_id),
            "sector_exposure": await analytics_service.get_sector_exposure(portfolio_id),
            "concentration": await analytics_service.get_concentration(portfolio_id),
            "volatility": await analytics_service.get_volatility(portfolio_id),
            "factor_exposures": await analytics_service.get_factor_exposures(portfolio_id),
            "correlation_matrix": await analytics_service.get_correlation_matrix(portfolio_id),
            "stress_test": await analytics_service.get_stress_test_results(portfolio_id),
        }

        # Optional: Prioritize certain metrics based on focus area
        if focus_area:
            bundle["focus_area"] = focus_area

        logger.info(f"Analytics bundle fetched: {len(bundle)} metric categories")
        return bundle

analytics_bundle_service = AnalyticsBundleService()
```

**Dependencies**:
- Existing `analytics_service` (already has all methods)
- No new API endpoints needed (all exist)

**Testing**:
```python
# Test in Python console
from app.services.analytics_bundle import analytics_bundle_service
from uuid import UUID
import asyncio

async def test():
    portfolio_id = UUID("your-demo-portfolio-id")
    bundle = await analytics_bundle_service.fetch_portfolio_analytics_bundle(portfolio_id)
    print(f"Bundle keys: {bundle.keys()}")
    print(f"Overview: {bundle['overview']}")

asyncio.run(test())
```

---

#### Step 1.2: Update Analytical Reasoning Service (4-5 hours) - OPTION C CHANGES

**File**: `backend/app/services/analytical_reasoning_service.py` (MODIFY)

**Current Behavior**:
- Uses `hybrid_context_builder` to build context
- Has tool calling infrastructure available

**New Behavior (Option C - Hybrid)**:
- ✅ **ALWAYS fetch analytics bundle first** (pre-calculated metrics)
- ✅ **Merge** analytics bundle with hybrid_context_builder
- ✅ **Keep tools available** (don't disable)
- ✅ **Prompt AI to prefer interpretation** (use tools only when needed)

**Key Changes**:

```python
from app.services.analytics_bundle import analytics_bundle_service

class AnalyticalReasoningService:

    async def investigate_portfolio(
        self,
        portfolio_id: UUID,
        insight_type: str,
        focus_area: Optional[str] = None,
        user_question: Optional[str] = None,
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        OPTION C: Hybrid Interpretation-First with Tools on Demand

        1. ALWAYS fetch analytics bundle first (pre-calculated data)
        2. Merge with existing hybrid_context_builder
        3. Prompt Claude to prefer interpretation (but tools available)
        4. Claude decides when to use tools (target: <20% of cases)
        """

        # 1. Fetch pre-calculated analytics (NEW - Phase 1.1 completed)
        logger.info(f"Fetching analytics bundle for portfolio {portfolio_id}")
        analytics_bundle = await analytics_bundle_service.fetch_portfolio_analytics_bundle(
            portfolio_id=portfolio_id,
            focus_area=focus_area
        )

        # 2. Build existing hybrid context (KEEP - don't remove)
        logger.info("Building hybrid context")
        hybrid_context = await hybrid_context_builder.build_context(
            portfolio_id=portfolio_id,
            auth_token=auth_token
        )

        # 3. MERGE both contexts
        merged_context = {
            **hybrid_context,
            "pre_calculated_analytics": analytics_bundle,  # Add bundle
            "analytics_bundle_available": True
        }

        # 4. Build interpretation-first prompt (NEW method)
        prompt = self._build_hybrid_interpretation_prompt(
            merged_context=merged_context,
            insight_type=insight_type,
            focus_area=focus_area,
            user_question=user_question
        )

        # 5. Send to Claude with BOTH analytics AND tools available
        logger.info("Sending to Claude (interpretation-first, tools optional)")
        response = await anthropic_provider.investigate(
            context=merged_context,
            prompt=prompt,
            enable_tools=True  # CRITICAL: Tools AVAILABLE but discouraged by prompt
        )

        # 6. Track tool usage (for monitoring)
        tool_calls_count = response.get("tool_calls_count", 0)
        logger.info(f"Tool calls made: {tool_calls_count} ({'INTERPRETED' if tool_calls_count == 0 else 'DEEP DIVE'})")

        return response

    def _build_hybrid_interpretation_prompt(
        self,
        merged_context: Dict[str, Any],
        insight_type: str,
        focus_area: Optional[str] = None,
        user_question: Optional[str] = None
    ) -> str:
        """
        OPTION C: Build hybrid prompt that prefers interpretation but keeps tools available.

        Includes:
        - Pre-calculated metrics as primary context
        - Guidance to prefer interpretation over tool calling
        - Tools available for deep dives (20% of cases)
        - Conversational tone guidelines
        - Severity calibration rules
        """

        # Extract analytics bundle
        analytics_bundle = merged_context.get("pre_calculated_analytics", {})

        # Format metrics for AI consumption
        metrics_summary = self._format_metrics_for_ai(analytics_bundle)

        # Build hybrid prompt
        prompt = f"""You are a trusted portfolio advisor with PRE-CALCULATED metrics AND tools available.

YOUR ROLE:
- You have pre-calculated risk metrics (shown below)
- You also have tools to fetch additional data IF NEEDED
- **PREFER INTERPRETATION** over tool calling (use tools <20% of time)

Think of yourself as a knowledgeable colleague reviewing a portfolio over coffee - not a compliance robot.

PRE-CALCULATED METRICS (USE THESE FIRST):
{metrics_summary}

YOUR TASK: Generate a {insight_type} insight

INTERPRETATION-FIRST STRATEGY:

**Default Approach (80% of cases):**
- Use the pre-calculated metrics above
- Interpret, synthesize, and explain
- Reference specific numbers from the data
- No need to call tools

**When to Use Tools (20% of cases):**
- User asks about a SPECIFIC company not in the data
- Need target prices or tags
- Missing data in pre-calculated bundle
- User explicitly asks for "more detail" or "deep dive"

INTERPRETATION GUIDELINES:

1. NOTICE PATTERNS
   - Look for relationships across metrics (e.g., high tech concentration + high correlation)
   - Identify what's notable or unusual compared to typical portfolios

2. ADD CONTEXT
   - Acknowledge the user might have good reasons for their portfolio structure
   - Ask questions instead of making assumptions
   - Example: "Is this concentration intentional for your strategy?"

3. BE CONVERSATIONAL (Trusted Partner Tone)
   - Use "I noticed..." instead of "You have a problem..."
   - Ask curious questions: "What's your thinking on...?"
   - Provide options, not directives: "A few ways to think about this..."
   - Acknowledge data limitations naturally

4. CALIBRATE SEVERITY (Be Conservative)
   - CRITICAL: Only truly threatening (>50% single position, negative equity, margin call risk)
   - WARNING: Worth discussing (20-40% single position, >50% sector concentration)
   - ELEVATED: Notable patterns (10-20% single position, significant factor tilts)
   - NORMAL: Healthy portfolio observations
   - INFO: Neutral findings and context

5. SYNTHESIZE ACROSS METRICS
   - This is your value-add: connecting dots the user might not see
   - Example: "Your tech overweight (42%) combined with momentum factor tilt (0.8) suggests..."

EXAMPLE GOOD ANALYSIS:
"I noticed your tech exposure is 42% compared to S&P 500's 28%. This creates a concentrated bet on
the sector, with AAPL and MSFT making up 30% combined. I'm seeing high correlation (0.78) between
these positions, meaning they tend to move together. This can amplify both gains and losses.

Is this concentration intentional - maybe you have high conviction on mega-cap tech? Or would you
like to talk through diversification options? A few things to consider: the stress test shows a
tech selloff would impact your portfolio by about 12-15%, which might be fine if you have a long
time horizon."

EXAMPLE BAD ANALYSIS:
"CRITICAL: Dangerous tech concentration detected. You must reduce AAPL and MSFT immediately to
avoid catastrophic losses."
"""

        # Add focus area if specified
        if focus_area:
            prompt += f"\n\nFOCUS AREA: Pay special attention to {focus_area}"

        # Add user question if specified
        if user_question:
            prompt += f"\n\nUSER QUESTION: {user_question}"

        return prompt

    def _format_metrics_for_ai(self, analytics_bundle: Dict[str, Any]) -> str:
        """Format analytics bundle into readable text for AI"""

        sections = []

        # Overview
        if "overview" in analytics_bundle and analytics_bundle["overview"]:
            ov = analytics_bundle["overview"]
            sections.append(f"""
PORTFOLIO OVERVIEW:
- Total Value: ${ov.get('total_value', 0):,.2f}
- Beta (90d): {ov.get('portfolio_beta_90d', 'N/A')}
- Sharpe Ratio: {ov.get('sharpe_ratio', 'N/A')}
- Max Drawdown: {ov.get('max_drawdown', 'N/A')}%
- Volatility (annualized): {ov.get('volatility_annualized', 'N/A')}%
""")

        # Sector Exposure
        if "sector_exposure" in analytics_bundle and analytics_bundle["sector_exposure"]:
            se = analytics_bundle["sector_exposure"]
            sections.append(f"""
SECTOR EXPOSURE (vs S&P 500):
- Top Overweight: {se.get('top_overweight_sector', 'N/A')} (+{se.get('top_overweight_diff', 0):.1f}%)
- Top Underweight: {se.get('top_underweight_sector', 'N/A')} ({se.get('top_underweight_diff', 0):.1f}%)
- Portfolio's largest sector: {se.get('largest_sector', 'N/A')} ({se.get('largest_sector_pct', 0):.1f}%)
""")

        # Concentration
        if "concentration" in analytics_bundle and analytics_bundle["concentration"]:
            conc = analytics_bundle["concentration"]
            sections.append(f"""
CONCENTRATION METRICS:
- HHI Score: {conc.get('hhi', 'N/A')} (0=perfect diversification, 1=all in one position)
- Top Position: {conc.get('top_position_name', 'N/A')} ({conc.get('top_position_pct', 0):.1f}%)
- Top 3 Positions: {conc.get('top3_pct', 0):.1f}% of portfolio
- Top 5 Positions: {conc.get('top5_pct', 0):.1f}% of portfolio
""")

        # Volatility
        if "volatility" in analytics_bundle and analytics_bundle["volatility"]:
            vol = analytics_bundle["volatility"]
            sections.append(f"""
VOLATILITY METRICS (HAR Forecasting):
- Realized 21d: {vol.get('realized_21d', 'N/A')}%
- Realized 63d: {vol.get('realized_63d', 'N/A')}%
- Forecast 21d: {vol.get('forecast_21d', 'N/A')}% (forward-looking)
- Trend: {vol.get('trend', 'N/A')}
""")

        # Factor Exposures
        if "factor_exposures" in analytics_bundle and analytics_bundle["factor_exposures"]:
            factors = analytics_bundle["factor_exposures"]
            sections.append(f"""
FACTOR EXPOSURES (Style Tilts):
- Market Beta: {factors.get('market', 'N/A')}
- Value Tilt: {factors.get('value', 'N/A')}
- Growth Tilt: {factors.get('growth', 'N/A')}
- Momentum: {factors.get('momentum', 'N/A')}
- Quality: {factors.get('quality', 'N/A')}
""")

        # Correlations (summary)
        if "correlation_matrix" in analytics_bundle and analytics_bundle["correlation_matrix"]:
            corr = analytics_bundle["correlation_matrix"]
            sections.append(f"""
CORRELATION ANALYSIS:
- Average Correlation: {corr.get('average_correlation', 'N/A')}
- Highest Correlation Pair: {corr.get('highest_pair', 'N/A')} ({corr.get('highest_value', 0):.2f})
- Interpretation: {corr.get('interpretation', 'Higher correlation means positions move together')}
""")

        # Stress Test (summary)
        if "stress_test" in analytics_bundle and analytics_bundle["stress_test"]:
            stress = analytics_bundle["stress_test"]
            worst_scenario = stress.get('worst_scenario', {})
            sections.append(f"""
STRESS TEST RESULTS:
- Worst Scenario: {worst_scenario.get('name', 'N/A')} ({worst_scenario.get('impact', 0):.1f}% impact)
- Market Crash (-20% SPY): {stress.get('market_crash_impact', 'N/A')}% impact
- Rate Shock: {stress.get('rate_shock_impact', 'N/A')}% impact
""")

        return "\n".join(sections)

# Update service instance
analytical_reasoning_service = AnalyticalReasoningService()
```

**Testing**:
1. Call `/api/v1/insights/generate` with demo portfolio
2. Verify no tool calls are made (check logs)
3. Verify AI response references specific metrics
4. Check severity level is calibrated (not everything CRITICAL)

---

#### Step 1.3: Update Anthropic Provider Prompt (1-2 hours) - OPTION C CHANGES

**File**: `backend/app/services/anthropic_provider.py` (MODIFY)

**Change**: Update system prompt to guide interpretation-first behavior (no structural changes needed)

**Option C Approach**:
- ✅ **Keep tools enabled** (don't disable)
- ✅ **Add interpretation-first guidance** to system prompt
- ✅ **Track tool usage** for monitoring

```python
class AnthropicProvider:

    async def investigate(
        self,
        context: Dict[str, Any],
        prompt: str,
        enable_tools: bool = True  # Always True for Option C
    ) -> Dict[str, Any]:
        """
        Generate response from Claude.

        OPTION C: Tools always available, but prompt guides to prefer interpretation.
        """

        # Check if analytics bundle is available
        has_analytics_bundle = context.get("analytics_bundle_available", False)

        # Build system prompt with interpretation-first guidance
        system_prompt = self._build_system_prompt(
            has_analytics_bundle=has_analytics_bundle
        )

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Tools are ALWAYS available (Option C)
        tools = self._get_tool_schemas()

        # Call Claude
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,  # NEW: Add system prompt
            messages=messages,
            tools=tools  # Always available
        )

        # Extract response and track tool usage
        result = self._extract_response_with_tool_tracking(response)

        # Log tool usage for monitoring
        tool_count = result.get("tool_calls_count", 0)
        logger.info(f"Tool usage: {tool_count} calls ({'interpreted' if tool_count == 0 else 'deep dive'})")

        return result

    def _build_system_prompt(self, has_analytics_bundle: bool) -> str:
        """
        Build system prompt that guides interpretation-first behavior.
        """
        if has_analytics_bundle:
            return """You are a portfolio advisor with access to pre-calculated analytics AND tools.

CRITICAL GUIDANCE:
- You have comprehensive pre-calculated metrics in the user message
- **PREFER interpreting these metrics** over calling tools
- Only call tools when you genuinely need additional data (target <20% of cases)

When you have the data you need: Interpret directly, don't call tools.
When data is missing or user asks for specifics: Use tools as needed.

Maintain conversational tone and calibrated severity."""
        else:
            return """You are a portfolio advisor with access to analytical tools.
Use tools as needed to answer user questions."""

    def _extract_response_with_tool_tracking(self, response) -> Dict[str, Any]:
        """
        Extract response text and count tool calls made.
        """
        # Count tool use blocks
        tool_calls_count = sum(
            1 for block in response.content
            if hasattr(block, 'type') and block.type == 'tool_use'
        )

        # Extract text
        text = self._extract_response_text(response)

        return {
            "text": text,
            "tool_calls_count": tool_calls_count,
            "stop_reason": response.stop_reason
        }
```

**Testing**:
- Generate insight and verify tool_calls_count is logged
- Check that most insights have tool_calls_count = 0 (interpretation)
- Verify tools still work when needed (e.g., specific company questions)

---

### Phase 2: Frontend - Analytics Bundle & UI Enhancements (Week 1, Day 3 - Week 2, Day 1)

#### Step 2.1: Create Analytics Bundle Service (3-4 hours)

**File**: `frontend/src/services/analyticsBundle.ts` (NEW)

```typescript
/**
 * Analytics Bundle Service
 *
 * Fetches all pre-calculated analytics for a portfolio in one go.
 * Used by AI insight generation and chat to provide context.
 *
 * NO CALCULATIONS - just fetching from existing endpoints.
 */

import analyticsApi from './analyticsApi'
import portfolioService from './portfolioService'

export interface AnalyticsBundle {
  overview: any
  sectorExposure: any
  concentration: any
  volatility: any
  factorExposures: any
  correlationMatrix: any
  stressTest: any
  portfolio: any
  timestamp: Date
}

class AnalyticsBundleService {
  /**
   * Fetch all pre-calculated analytics for a portfolio
   *
   * All data is calculated by batch_orchestrator on backend.
   * This just fetches the results for AI interpretation.
   */
  async fetchPortfolioAnalyticsBundle(portfolioId: string): Promise<AnalyticsBundle> {
    console.log('📦 Fetching analytics bundle for portfolio:', portfolioId)

    try {
      // Fetch all metrics in parallel (all pre-calculated by backend)
      const [
        overview,
        sectorExposure,
        concentration,
        volatility,
        factorExposures,
        correlationMatrix,
        stressTest,
        portfolio
      ] = await Promise.all([
        analyticsApi.getOverview(portfolioId),
        analyticsApi.getSectorExposure(portfolioId),
        analyticsApi.getConcentration(portfolioId),
        analyticsApi.getVolatility(portfolioId),
        analyticsApi.getFactorExposures(portfolioId),
        analyticsApi.getCorrelationMatrix(portfolioId),
        analyticsApi.getStressTests(portfolioId),
        portfolioService.getComplete(portfolioId)
      ])

      console.log('✅ Analytics bundle fetched successfully')

      return {
        overview,
        sectorExposure,
        concentration,
        volatility,
        factorExposures,
        correlationMatrix,
        stressTest,
        portfolio,
        timestamp: new Date()
      }
    } catch (error) {
      console.error('❌ Failed to fetch analytics bundle:', error)
      throw error
    }
  }

  /**
   * Format bundle into human-readable summary
   * Useful for debugging and UI display
   */
  formatBundleSummary(bundle: AnalyticsBundle): string {
    return `
Analytics Bundle Summary:
- Portfolio Value: $${bundle.overview?.total_value?.toLocaleString()}
- Beta (90d): ${bundle.overview?.portfolio_beta_90d || 'N/A'}
- Top Sector: ${bundle.sectorExposure?.largest_sector || 'N/A'} (${bundle.sectorExposure?.largest_sector_pct}%)
- HHI: ${bundle.concentration?.hhi || 'N/A'}
- Volatility (21d): ${bundle.volatility?.realized_21d || 'N/A'}%
- Fetched: ${bundle.timestamp.toLocaleString()}
    `.trim()
  }
}

export const analyticsBundleService = new AnalyticsBundleService()
export default analyticsBundleService
```

**Testing**:
```typescript
// Test in browser console
import analyticsBundleService from '@/services/analyticsBundle'

const bundle = await analyticsBundleService.fetchPortfolioAnalyticsBundle('your-portfolio-id')
console.log(analyticsBundleService.formatBundleSummary(bundle))
```

---

#### Step 2.2: Add Quick-Start Prompts Component (2-3 hours)

**File**: `frontend/src/components/sigmasight-ai/QuickStartPrompts.tsx` (NEW)

```typescript
/**
 * Quick-Start Prompts Component
 *
 * Provides suggested questions that reference pre-calculated metrics.
 * Helps users get started with AI interpretation.
 */

'use client'

import React from 'react'
import { Button } from '@/components/ui/button'
import { Sparkles, TrendingUp, AlertTriangle, PieChart, BarChart3, Zap } from 'lucide-react'

interface QuickPrompt {
  id: string
  text: string
  description: string
  icon: React.ComponentType<{ className?: string }>
}

const QUICK_PROMPTS: QuickPrompt[] = [
  {
    id: 'biggest_risks',
    text: "What are my biggest portfolio risks?",
    description: "AI will interpret your risk metrics and highlight key concerns",
    icon: AlertTriangle
  },
  {
    id: 'concentration',
    text: "Walk me through my concentration risk",
    description: "AI explains your HHI score and top position percentages",
    icon: PieChart
  },
  {
    id: 'sector_exposure',
    text: "Explain my sector exposures vs S&P 500",
    description: "AI interprets your sector tilts and what they mean",
    icon: BarChart3
  },
  {
    id: 'factor_tilts',
    text: "What do my factor exposures tell you?",
    description: "AI analyzes your style tilts (value, growth, momentum, etc.)",
    icon: TrendingUp
  },
  {
    id: 'stress_test',
    text: "Help me understand my stress test results",
    description: "AI explains which scenarios hurt most and why",
    icon: Zap
  }
]

interface QuickStartPromptsProps {
  onPromptClick: (prompt: string) => void
  disabled?: boolean
  visible?: boolean
}

export function QuickStartPrompts({
  onPromptClick,
  disabled = false,
  visible = true
}: QuickStartPromptsProps) {
  if (!visible) return null

  return (
    <div className="mb-4 p-4 rounded-lg border transition-colors duration-300" style={{
      backgroundColor: 'var(--bg-secondary)',
      borderColor: 'var(--border-primary)'
    }}>
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-4 w-4" style={{ color: 'var(--color-accent)' }} />
        <h4 className="text-sm font-semibold transition-colors duration-300" style={{
          color: 'var(--text-primary)'
        }}>
          Quick Start
        </h4>
      </div>

      <div className="space-y-2">
        {QUICK_PROMPTS.map((prompt) => {
          const Icon = prompt.icon
          return (
            <Button
              key={prompt.id}
              variant="ghost"
              className="w-full justify-start text-left h-auto py-2 px-3"
              onClick={() => onPromptClick(prompt.text)}
              disabled={disabled}
            >
              <Icon className="h-4 w-4 mr-2 flex-shrink-0" />
              <div className="flex-1">
                <div className="text-sm font-medium">{prompt.text}</div>
                <div className="text-xs opacity-70">{prompt.description}</div>
              </div>
            </Button>
          )
        })}
      </div>
    </div>
  )
}
```

**Integration**:
- Add to `ClaudeChatInterface.tsx` above message input
- Hide after first message is sent
- Track which prompts are used most (analytics)

---

#### Step 2.3: Add Severity Legend Component (1-2 hours)

**File**: `frontend/src/components/sigmasight-ai/SeverityLegend.tsx` (NEW)

```typescript
/**
 * Severity Legend Component
 *
 * Explains what each severity level means.
 * Helps users calibrate expectations and understand AI's assessment.
 */

'use client'

import React, { useState } from 'react'
import { ChevronDown, ChevronUp, AlertCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SeverityDefinition {
  level: string
  label: string
  description: string
  examples: string[]
  color: string
  icon: React.ComponentType<{ className?: string }>
}

const SEVERITY_DEFINITIONS: SeverityDefinition[] = [
  {
    level: 'critical',
    label: 'Critical',
    description: 'Portfolio-threatening issues requiring immediate attention',
    examples: [
      'Single position >50% of portfolio',
      'Negative equity or margin call risk',
      'Severe data quality issues affecting analysis'
    ],
    color: 'var(--color-error)',
    icon: AlertCircle
  },
  {
    level: 'warning',
    label: 'Warning',
    description: 'Meaningful risks worth discussing with your advisor',
    examples: [
      'Concentration: Single position 20-40% or sector >50%',
      'High correlation (>0.8) limiting diversification',
      'Significant stress test vulnerability'
    ],
    color: 'var(--color-warning)',
    icon: AlertTriangle
  },
  {
    level: 'elevated',
    label: 'Elevated',
    description: 'Notable patterns to be aware of - may be intentional',
    examples: [
      'Moderate concentration (10-20% single position)',
      'Factor tilts vs benchmark',
      'Higher than typical volatility'
    ],
    color: 'var(--color-accent)',
    icon: Info
  },
  {
    level: 'normal',
    label: 'Normal',
    description: 'Healthy portfolio observations',
    examples: [
      'Balanced sector exposures',
      'Reasonable diversification',
      'Metrics in line with typical portfolios'
    ],
    color: 'var(--text-secondary)',
    icon: CheckCircle
  },
  {
    level: 'info',
    label: 'Info',
    description: 'General observations and context',
    examples: [
      'Neutral findings about portfolio structure',
      'Background information',
      'Data limitations and notes'
    ],
    color: 'var(--color-info)',
    icon: Info
  }
]

export function SeverityLegend() {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="mb-4 rounded-lg border transition-colors duration-300" style={{
      backgroundColor: 'var(--bg-primary)',
      borderColor: 'var(--border-primary)'
    }}>
      <Button
        variant="ghost"
        className="w-full justify-between px-4 py-3"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4" />
          <span className="text-sm font-semibold">How we rate severity</span>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </Button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {SEVERITY_DEFINITIONS.map((def) => {
            const Icon = def.icon
            return (
              <div key={def.level} className="space-y-1">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4" style={{ color: def.color }} />
                  <span className="text-sm font-semibold" style={{ color: def.color }}>
                    {def.label}
                  </span>
                </div>
                <p className="text-xs ml-6 transition-colors duration-300" style={{
                  color: 'var(--text-secondary)'
                }}>
                  {def.description}
                </p>
                <ul className="text-xs ml-6 space-y-1 list-disc list-inside transition-colors duration-300" style={{
                  color: 'var(--text-tertiary)'
                }}>
                  {def.examples.map((example, idx) => (
                    <li key={idx}>{example}</li>
                  ))}
                </ul>
              </div>
            )
          })}

          <p className="text-xs mt-4 pt-3 border-t transition-colors duration-300" style={{
            borderColor: 'var(--border-primary)',
            color: 'var(--text-tertiary)'
          }}>
            We're conservative with severity levels to avoid alarm fatigue. Not everything is CRITICAL.
            Many portfolio characteristics (like concentration) might be intentional for your strategy.
          </p>
        </div>
      )}
    </div>
  )
}
```

**Integration**:
- Add to left column below "Daily Summary Analysis" header
- Save expanded/collapsed state to localStorage

---

#### Step 2.4: Add "Send to Chat" Button to Insights (1-2 hours)

**File**: `frontend/src/components/command-center/AIInsightsRow.tsx` (MODIFY)

```typescript
// Add to InsightCard component

interface InsightCardProps {
  insight: AIInsight
  onDismiss: (id: string) => void
  onExpand: () => void
  onSendToChat: (insight: AIInsight) => void  // NEW
  isExpanded: boolean
}

function InsightCard({ insight, onDismiss, onExpand, onSendToChat, isExpanded }: InsightCardProps) {
  // ... existing code ...

  // Generate context-aware chat prompt based on insight
  const generateChatPrompt = (insight: AIInsight): string => {
    const severityContext = insight.severity === 'critical' || insight.severity === 'warning'
      ? "This seems important."
      : "I'd like to understand this better."

    return `You mentioned: "${insight.title}"\n\n${severityContext} Can you help me think through whether this is something I should act on, or if it might be intentional given my investment strategy?`
  }

  return (
    <div className="..." style={cardStyle}>
      {/* ... existing header, summary, findings ... */}

      {/* Footer with new "Send to Chat" button */}
      <div className="flex items-center justify-between pt-2 border-t">
        <div className="text-[10px] text-tertiary">
          Generated {createdDate} • ${insight.performance.cost_usd.toFixed(3)} • {(insight.performance.generation_time_ms / 1000).toFixed(1)}s
        </div>

        <div className="flex items-center gap-2">
          {/* NEW: Send to Chat button */}
          <button
            onClick={() => onSendToChat(insight)}
            className="text-xs font-medium px-2 py-1 rounded transition-colors"
            style={{
              backgroundColor: 'var(--color-accent)',
              color: '#000000'
            }}
            onMouseEnter={(e) => e.currentTarget.style.opacity = '0.8'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          >
            → Send to Chat
          </button>

          {/* Existing expand/collapse buttons */}
          {!isExpanded && (
            <button onClick={onExpand} className="...">
              View full analysis
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
```

**Integration in Container**:

```typescript
// In SigmaSightAIContainer.tsx

const handleSendToChat = (insight: AIInsight) => {
  // Generate context-aware prompt
  const prompt = generateChatPrompt(insight)

  // Prefill chat input (add method to store)
  useClaudeInsightsStore.getState().prefillMessage(prompt)

  // Scroll to chat interface
  const chatElement = document.getElementById('claude-chat-interface')
  chatElement?.scrollIntoView({ behavior: 'smooth' })

  // Track analytics
  console.log('📊 Send to Chat:', { insightId: insight.id, type: insight.insight_type })
}

// Pass to AIInsightsRow
<AIInsightsRow
  insights={insights}
  onSendToChat={handleSendToChat}  // NEW
  // ... other props
/>
```

**Store Update** (`claudeInsightsStore.ts`):

```typescript
interface ClaudeInsightsStore {
  // ... existing fields ...
  prefillText: string

  // ... existing actions ...
  prefillMessage: (text: string) => void
}

export const useClaudeInsightsStore = create<ClaudeInsightsStore>((set) => ({
  // ... existing state ...
  prefillText: '',

  // ... existing actions ...
  prefillMessage: (text: string) => {
    set({ prefillText: text })
  }
}))
```

---

#### Step 2.5: Add Focus Area Picker (2-3 hours)

**File**: `frontend/src/components/sigmasight-ai/FocusAreaPicker.tsx` (NEW)

```typescript
/**
 * Focus Area Picker Component
 *
 * Allows users to specify what aspect of their portfolio
 * the AI should focus on when generating insights.
 *
 * Backend already supports this via focus_area parameter.
 */

'use client'

import React from 'react'
import { Target, Droplet, Grid, PieChart, Activity, TrendingUp } from 'lucide-react'

interface FocusArea {
  id: string
  label: string
  description: string
  icon: React.ComponentType<{ className?: string }>
}

const FOCUS_AREAS: FocusArea[] = [
  {
    id: 'concentration',
    label: 'Concentration Risk',
    description: 'HHI score, top positions, diversification',
    icon: Target
  },
  {
    id: 'liquidity',
    label: 'Liquidity Analysis',
    description: 'Cash levels, illiquid positions, capital flows',
    icon: Droplet
  },
  {
    id: 'factor_exposure',
    label: 'Factor Exposures',
    description: 'Value, growth, momentum, quality tilts',
    icon: Grid
  },
  {
    id: 'sector',
    label: 'Sector Balance',
    description: 'Sector weights vs S&P 500 benchmark',
    icon: PieChart
  },
  {
    id: 'volatility',
    label: 'Volatility & Beta',
    description: 'Risk levels, beta analysis, volatility trends',
    icon: Activity
  },
  {
    id: 'options',
    label: 'Options & Greeks',
    description: 'Options positions, delta, gamma, theta exposure',
    icon: TrendingUp
  }
]

interface FocusAreaPickerProps {
  selectedFocus: string | null
  onFocusChange: (focusId: string | null) => void
  disabled?: boolean
}

export function FocusAreaPicker({
  selectedFocus,
  onFocusChange,
  disabled = false
}: FocusAreaPickerProps) {
  return (
    <div className="mb-4">
      <label className="text-xs font-semibold mb-2 block transition-colors duration-300" style={{
        color: 'var(--text-secondary)'
      }}>
        Focus Area (Optional)
      </label>

      <select
        value={selectedFocus || ''}
        onChange={(e) => onFocusChange(e.target.value || null)}
        disabled={disabled}
        className="w-full px-3 py-2 rounded border text-sm transition-colors duration-300"
        style={{
          backgroundColor: 'var(--bg-primary)',
          borderColor: 'var(--border-primary)',
          color: 'var(--text-primary)'
        }}
      >
        <option value="">All Areas (General Summary)</option>
        {FOCUS_AREAS.map((area) => (
          <option key={area.id} value={area.id}>
            {area.label} - {area.description}
          </option>
        ))}
      </select>

      {selectedFocus && (
        <p className="text-xs mt-1 transition-colors duration-300" style={{
          color: 'var(--text-tertiary)'
        }}>
          AI will pay special attention to {FOCUS_AREAS.find(a => a.id === selectedFocus)?.label.toLowerCase()}
        </p>
      )}
    </div>
  )
}
```

**Integration**:
- Add to left column above "Generate" button
- Pass `focus_area` to `generateInsight()` API call
- Track which focus areas are used most

---

### Phase 3: Chat Integration with Context (Week 2, Days 2-3)

#### Step 3.1: Update Chat to Include Portfolio Context (4-5 hours)

**Goal**: When user asks questions in chat, provide pre-calculated metrics for context

**File**: `frontend/src/services/claudeInsightsService.ts` (MODIFY)

```typescript
import analyticsBundleService from './analyticsBundle'
import { usePortfolioStore } from '@/stores/portfolioStore'

/**
 * Send a message with portfolio context
 *
 * Fetches pre-calculated analytics and includes in prompt
 * so AI can reference actual metrics when answering.
 */
export async function sendMessageWithContext(message: string): Promise<void> {
  const store = useClaudeInsightsStore.getState()
  const portfolioId = usePortfolioStore.getState().portfolioId

  if (!portfolioId) {
    throw new Error('No portfolio selected')
  }

  try {
    // 1. Fetch pre-calculated analytics
    console.log('📦 Fetching analytics bundle for context...')
    const analytics = await analyticsBundleService.fetchPortfolioAnalyticsBundle(portfolioId)

    // 2. Build context-aware prompt
    const contextualMessage = buildContextualPrompt(message, analytics)

    // 3. Add user message to store (original message, not with context)
    const userMessage: ClaudeMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: message,  // Show user's original message
      timestamp: new Date()
    }
    store.addMessage(userMessage)

    // 4. Send contextual message to backend (includes analytics)
    await sendClaudeMessage({
      message: contextualMessage,  // Backend gets context
      conversationId: store.conversationId || undefined
    })

  } catch (error) {
    console.error('Failed to send message with context:', error)
    throw error
  }
}

/**
 * Build prompt that includes pre-calculated metrics
 */
function buildContextualPrompt(
  userMessage: string,
  analytics: AnalyticsBundle
): string {
  return `
User Question: ${userMessage}

PORTFOLIO CONTEXT (Pre-Calculated Metrics):
You have access to the following pre-calculated metrics. Reference these when answering the user's question. DO NOT recalculate anything - just interpret and explain.

Portfolio Overview:
- Total Value: $${analytics.overview?.total_value?.toLocaleString() || 'N/A'}
- Beta (90d): ${analytics.overview?.portfolio_beta_90d || 'N/A'}
- Sharpe Ratio: ${analytics.overview?.sharpe_ratio?.toFixed(2) || 'N/A'}
- Volatility (annualized): ${analytics.overview?.volatility_annualized?.toFixed(2) || 'N/A'}%

Sector Exposure (vs S&P 500):
- Largest Sector: ${analytics.sectorExposure?.largest_sector || 'N/A'} (${analytics.sectorExposure?.largest_sector_pct?.toFixed(1) || 'N/A'}%)
- Top Overweight: ${analytics.sectorExposure?.top_overweight_sector || 'N/A'} (+${analytics.sectorExposure?.top_overweight_diff?.toFixed(1) || 'N/A'}%)

Concentration:
- HHI Score: ${analytics.concentration?.hhi?.toFixed(3) || 'N/A'}
- Top Position: ${analytics.concentration?.top_position_name || 'N/A'} (${analytics.concentration?.top_position_pct?.toFixed(1) || 'N/A'}%)
- Top 5 Positions: ${analytics.concentration?.top5_pct?.toFixed(1) || 'N/A'}% of portfolio

Volatility (HAR Forecasting):
- Realized 21d: ${analytics.volatility?.realized_21d?.toFixed(2) || 'N/A'}%
- Forecast 21d: ${analytics.volatility?.forecast_21d?.toFixed(2) || 'N/A'}%

Factor Exposures:
- Market Beta: ${analytics.factorExposures?.market?.toFixed(2) || 'N/A'}
- Value Tilt: ${analytics.factorExposures?.value?.toFixed(2) || 'N/A'}
- Growth Tilt: ${analytics.factorExposures?.growth?.toFixed(2) || 'N/A'}
- Momentum: ${analytics.factorExposures?.momentum?.toFixed(2) || 'N/A'}

Stress Test:
- Worst Scenario: ${analytics.stressTest?.worst_scenario?.name || 'N/A'} (${analytics.stressTest?.worst_scenario?.impact?.toFixed(1) || 'N/A'}% impact)

---

YOUR TASK:
Answer the user's question using these pre-calculated metrics. Be conversational and helpful.
- Reference specific numbers when relevant
- Explain what the metrics mean in plain language
- Ask clarifying questions if needed
- Maintain the "trusted partner" tone (not robotic)

Remember: You're interpreting these numbers, not calculating them.
  `.trim()
}

// Update the existing sendMessage to use context
export async function sendMessage(message: string): Promise<void> {
  return sendMessageWithContext(message)
}
```

**Testing**:
1. Ask "What are my biggest risks?"
2. Verify AI response references actual portfolio metrics
3. Check response quality (conversational, specific, helpful)

---

#### Step 3.2: Add Macro Action Buttons (3-4 hours)

**File**: `frontend/src/components/sigmasight-ai/MacroActions.tsx` (NEW)

```typescript
/**
 * Macro Actions Component
 *
 * Pre-crafted high-value prompts that trigger comprehensive analysis.
 * Each macro references specific pre-calculated metrics.
 */

'use client'

import React from 'react'
import { Button } from '@/components/ui/button'
import { Zap, TrendingUp, Shield, PieChart, Target } from 'lucide-react'

interface MacroAction {
  id: string
  label: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  prompt: string
}

const MACRO_ACTIONS: MacroAction[] = [
  {
    id: 'stress_test_deep_dive',
    label: 'Stress Test Review',
    description: 'Explain stress test results in plain English',
    icon: Zap,
    prompt: `Look at my stress test results and explain:
1. Which scenarios hurt me most and why?
2. What positions drive the vulnerability?
3. Should I be concerned about these scenarios?
4. Any hedging ideas to reduce stress test losses?

Use my actual stress test data - don't recalculate.`
  },
  {
    id: 'concentration_check',
    label: 'Concentration Check',
    description: 'Review HHI and top positions',
    icon: Target,
    prompt: `Review my concentration metrics (HHI, top positions %) and tell me:
1. Is my concentration level concerning?
2. Which specific positions create the concentration?
3. Might this be intentional for my strategy?
4. What are the pros/cons of this concentration level?

Reference my actual HHI and position weights.`
  },
  {
    id: 'sector_deep_dive',
    label: 'Sector Analysis',
    description: 'Sector tilts vs S&P 500',
    icon: PieChart,
    prompt: `Walk me through my sector exposures vs S&P 500:
1. Which sectors am I overweight/underweight?
2. What does this say about my portfolio's characteristics?
3. Are these tilts creating meaningful risks or opportunities?
4. Should I rebalance any sectors?

Use my actual sector exposure data.`
  },
  {
    id: 'factor_interpretation',
    label: 'Factor Breakdown',
    description: 'Explain factor tilts',
    icon: TrendingUp,
    prompt: `Explain my factor exposures in plain English:
1. What do my factor loadings (value, growth, momentum, etc.) mean?
2. How do these tilts align with current market conditions?
3. Are there any concerning factor concentrations?
4. What happens if market rotates away from my tilts?

Reference my actual factor exposures.`
  },
  {
    id: 'risk_profile',
    label: 'Full Risk Profile',
    description: 'Comprehensive risk assessment',
    icon: Shield,
    prompt: `Give me a comprehensive risk assessment:
1. What are my 3 biggest risks right now?
2. What's working well (risk-wise)?
3. Any blind spots I should be aware of?
4. Priority areas to address or monitor?

Synthesize across all my metrics (concentration, sectors, factors, stress tests, correlations).`
  }
]

interface MacroActionsProps {
  onMacroClick: (prompt: string) => void
  disabled?: boolean
}

export function MacroActions({ onMacroClick, disabled = false }: MacroActionsProps) {
  return (
    <div className="mb-4 p-4 rounded-lg border transition-colors duration-300" style={{
      backgroundColor: 'var(--bg-secondary)',
      borderColor: 'var(--border-primary)'
    }}>
      <h4 className="text-sm font-semibold mb-3 transition-colors duration-300" style={{
        color: 'var(--text-primary)'
      }}>
        Quick Analysis
      </h4>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {MACRO_ACTIONS.map((action) => {
          const Icon = action.icon
          return (
            <Button
              key={action.id}
              variant="outline"
              className="justify-start text-left h-auto py-3 px-3"
              onClick={() => onMacroClick(action.prompt)}
              disabled={disabled}
            >
              <Icon className="h-4 w-4 mr-2 flex-shrink-0" />
              <div className="flex-1">
                <div className="text-sm font-medium">{action.label}</div>
                <div className="text-xs opacity-70">{action.description}</div>
              </div>
            </Button>
          )
        })}
      </div>
    </div>
  )
}
```

**Integration**:
- Add to chat interface below quick-start prompts
- Track which macros are used most
- Consider showing relevant macro based on insight severity

---

### Phase 4: Testing & Refinement (Week 2, Day 4)

#### Step 4.1: End-to-End Testing (4-5 hours)

**Test Scenarios**:

1. **Insight Generation**
   - Generate daily summary insight
   - Verify AI references specific metrics (not generic)
   - Check severity is calibrated (not alarmist)
   - Confirm tone is conversational ("I noticed..." not "You must...")
   - Validate no tool calls made (check logs)

2. **Quick-Start Prompts**
   - Click each prompt
   - Verify chat prefills correctly
   - Check AI responses reference portfolio metrics
   - Confirm responses are helpful and specific

3. **Send to Chat**
   - Generate insight
   - Click "Send to Chat"
   - Verify prompt prefills with context
   - Confirm AI response builds on insight

4. **Focus Area Picker**
   - Select "Concentration Risk" focus
   - Generate insight
   - Verify AI pays attention to concentration metrics
   - Test other focus areas

5. **Macro Actions**
   - Click "Stress Test Review"
   - Verify comprehensive analysis with actual data
   - Check response quality
   - Test other macros

6. **Severity Legend**
   - Expand legend
   - Verify definitions match backend logic
   - Check examples are clear
   - Confirm visual consistency

**Performance Testing**:
- Insight generation time: Target <30s
- Chat response time: Target <5s to first token
- Analytics bundle fetch: Target <2s
- Page load time: Target <2s
- Check no memory leaks (long chat sessions)

**Cross-Browser Testing**:
- Chrome (primary)
- Firefox
- Safari
- Edge

**Responsive Testing**:
- Desktop (1920x1080, 1440x900)
- Tablet (iPad, 768x1024)
- Mobile (iPhone, 375x667)

---

#### Step 4.2: User Acceptance Criteria

**Insight Quality**:
- [ ] AI references specific metrics (not generic statements)
- [ ] Severity levels are calibrated (not everything CRITICAL)
- [ ] Tone is conversational ("I noticed..." not "You have a problem...")
- [ ] Acknowledges user might have good reasons for portfolio structure
- [ ] Asks questions instead of prescribing solutions
- [ ] Includes data limitations naturally

**UX Quality**:
- [ ] Quick-start prompts are helpful and clear
- [ ] "Send to Chat" workflow is smooth
- [ ] Focus area picker affects insight content
- [ ] Macro actions provide comprehensive analysis
- [ ] Severity legend is informative
- [ ] All interactions feel responsive (<100ms UI feedback)

**Technical Quality**:
- [ ] No duplicate calculations (batch_orchestrator already did work)
- [ ] Analytics bundle fetches efficiently (<2s)
- [ ] No tool calls during insight generation (logs confirm)
- [ ] Chat includes portfolio context
- [ ] Error handling is graceful
- [ ] Works across browsers and devices

---

## Part IV: Success Metrics (Option C)

### Quantitative Metrics

**Engagement**:
- Quick prompt usage rate: Target >60% of users
- "Send to Chat" click rate: Target >40% of insights
- Macro action usage: Target >30% of chat sessions
- Average session duration: Target >3 minutes
- Insights expanded/read: Target >80%

**Quality**:
- User feedback ratings: Target >4.0/5.0
- Insight dismissal rate: Target <20%
- Chat conversation depth: Target >3 messages per session
- Severity distribution: CRITICAL <5%, WARNING <30%, rest distributed

**Performance (Option C)**:
- Insight generation time: Target <25s avg (18-22s typical, 30-40s when tools used)
- Insight generation time (P95): Target <40s (includes tool calling cases)
- Chat response latency: Target <5s first token
- Analytics bundle fetch: Target <2s
- Error rate: Target <1%

**Cost (Option C)**:
- Cost per insight: Target <$0.025 (mostly interpretation, occasional tool calls)
- Cost per chat message: Target <$0.02
- Monthly cost per active user: Target <$2.50 (slightly higher than pure interpretation)

**Tool Usage Tracking (NEW - Critical for Option C)**:
- **Tool usage rate**: Target <20% of insights call tools
- **Interpretation-only rate**: Target >80% of insights use pre-calculated data only
- **Average tools per insight**: Target <0.3 (most use 0, some use 1-3)
- **Tool usage by focus area**: Track which areas trigger more tool calls

### Qualitative Metrics

**User Sentiment**:
- Insights feel conversational (not robotic)
- Users feel understood (not lectured)
- AI maintains credibility (calibrated severity)
- Users find value (actionable insights)

**Feedback Themes** (track via user feedback):
- "Too aggressive" complaints: Target <5%
- "Not helpful" ratings: Target <10%
- "Just right" sentiment: Target >70%

---

## Part V: Risks & Mitigation (Option C)

### Technical Risks

**Risk**: Analytics bundle fetch fails
**Impact**: Medium - Falls back to tool calling (slower but works)
**Mitigation**:
- Graceful degradation (tools still available)
- Clear error message to user
- Retry logic with exponential backoff
- **Option C Advantage**: System still works with tools

**Risk**: AI responses are generic (despite having metrics)
**Impact**: High - Defeats purpose of hybrid approach
**Mitigation**:
- Extensive prompt testing with demo portfolios
- A/B test different prompt templates
- Monitor user feedback for "generic" complaints
- Iterate on prompt engineering
- Track tool usage patterns

**Risk**: Performance degrades with large portfolios
**Impact**: Medium - Slow insights for power users
**Mitigation**:
- Paginate analytics bundle if needed
- Cache analytics bundle (5 min TTL)
- Show progressive loading states

**Risk**: AI over-relies on tools (>30% tool usage rate)
**Impact**: Medium - Loses speed advantage
**Mitigation**:
- Monitor tool usage rate daily
- Strengthen interpretation-first guidance in prompt
- Add examples of good interpretation
- Track which focus areas trigger more tools

**Risk**: AI under-utilizes tools when needed
**Impact**: Low - Misses opportunities for deep analysis
**Mitigation**:
- Monitor user feedback for "need more detail"
- Track user "Send to Chat" actions (indicates wanting more)
- Add macro prompts that explicitly request deep dives

### Product Risks

**Risk**: Users expect AI to calculate, not interpret
**Impact**: Medium - Confusion about AI's role
**Mitigation**:
- Clear copy explaining AI's role
- "How it works" tooltip
- Onboarding tour for first-time users
- **Option C Advantage**: AI can calculate when needed

**Risk**: Severity levels still feel off
**Impact**: Medium - Credibility issues
**Mitigation**:
- Conservative calibration by default
- User feedback mechanism
- Iterate based on data

**Risk**: Chat responses lack portfolio context
**Impact**: High - Defeats hybrid value prop
**Mitigation**:
- Extensive testing of context inclusion
- Log analytics bundle in responses
- Monitor for "generic" complaints
- Track tool usage in chat vs insights

---

## Part VI: Future Enhancements

### Phase 5 (Post-Launch)

**Multi-Portfolio Comparison** (2-3 days):
- Compare risk metrics across user's portfolios
- "Portfolio A has 2x concentration of Portfolio B"
- Useful for family offices managing multiple accounts

**Historical Trend Analysis** (3-4 days):
- "Your concentration has increased from 0.05 to 0.12 over 90 days"
- Show metric trends over time
- Alert on significant changes

**Custom Alerts** (2-3 days):
- User-defined thresholds
- "Alert me if HHI >0.15"
- "Notify if volatility increases >20%"

**Insight Scheduling** (2-3 days):
- Auto-generate daily/weekly insights
- Email summary
- Push notifications for critical insights

**Export & Sharing** (1-2 days):
- Export insights to PDF
- Share via email
- Integration with portfolio reporting

---

## Part VII: Appendix

### A. Key Files Modified/Created

**Backend Files (Modified)**:
- `app/services/analytical_reasoning_service.py` - Switch to interpretation
- `app/services/anthropic_provider.py` - Disable tools when needed

**Backend Files (New)**:
- `app/services/analytics_bundle.py` - Fetch all metrics

**Frontend Files (Modified)**:
- `app/sigmasight-ai/page.tsx` - No changes (thin wrapper)
- `src/containers/SigmaSightAIContainer.tsx` - Add new components
- `src/components/command-center/AIInsightsRow.tsx` - Add "Send to Chat"
- `src/services/claudeInsightsService.ts` - Add context to messages
- `src/stores/claudeInsightsStore.ts` - Add prefill state

**Frontend Files (New)**:
- `src/services/analyticsBundle.ts` - Analytics bundle fetcher
- `src/components/sigmasight-ai/QuickStartPrompts.tsx` - Quick prompts
- `src/components/sigmasight-ai/SeverityLegend.tsx` - Severity explanation
- `src/components/sigmasight-ai/FocusAreaPicker.tsx` - Focus selection
- `src/components/sigmasight-ai/MacroActions.tsx` - Macro prompts

### B. Environment Variables

No new environment variables required - uses existing:
- `OPENAI_API_KEY` (for chat - already configured)
- `ANTHROPIC_API_KEY` (for insights - already configured)

### C. Dependencies

No new dependencies required - uses existing:
- `@anthropic-ai/sdk` (backend)
- `zustand` (frontend state)
- `lucide-react` (icons)

### D. Related Documentation

Reference these docs during implementation:
- `18-CONVERSATIONAL-AI-PARTNER-VISION.md` - Tone guidelines
- `27-SIGMASIGHT-AI-EXPERIENCE-REFINEMENT.md` - Original plan
- `frontend/CLAUDE.md` - Frontend architecture
- `backend/CLAUDE.md` - Backend architecture
- `frontend/_docs/requirements/05-AIChat-Implementation.md` - Chat system

---

## Conclusion

This implementation plan transforms SigmaSight AI using **Option C: Hybrid Interpretation-First with Tools on Demand**:

**Before**:
- AI calls analytics tools to recalculate metrics (slow)
- Generic insights ("High concentration detected")
- Duplicates Risk Metrics page
- Always 30-40s response time

**After (Option C)**:
- ✅ **AI fetches pre-calculated data FIRST** (fast, 15-20s)
- ✅ **Tools available when needed** (flexibility, 30-40s when used)
- ✅ **Specific insights** ("Your tech concentration is 42% vs S&P's 28%, driven by AAPL (20%) and MSFT (10%). Is this intentional?")
- ✅ **Best of both worlds**: Fast interpretation (80%) + deep dives (20%)
- ✅ **Conversational tone** with calibrated severity

**Key Differences from Pure Interpretation (Option B)**:
- Keep existing tool calling infrastructure (don't remove)
- Add analytics bundle fetching (Phase 1.1 ✅ COMPLETED)
- Merge contexts (analytics + hybrid_context_builder)
- Prompt engineering to guide interpretation-first behavior
- Track tool usage rate (monitor and optimize)

**Estimated Timeline**: 4-5 hours (Option C is incremental change)

**Implementation Status**:
- ✅ Phase 1.1: Analytics Bundle Service COMPLETED
- ⏳ Phase 1.2: Update analytical_reasoning_service.py (merge contexts)
- ⏳ Phase 1.3: Update anthropic_provider.py (prompt guidance + tracking)
- ⏳ Phase 2-4: Frontend enhancements

**Ready to continue?** Next step: Phase 1.2 (Update analytical_reasoning_service.py)

---

**Last Updated**: December 17, 2025
**Version**: 3.0 - Option C: Hybrid Interpretation-First with Tools on Demand
**Status**: Phase 1.1 Complete, Ready for Phase 1.2
**Next Step**: Update `backend/app/services/analytical_reasoning_service.py` to merge analytics_bundle with hybrid_context_builder
