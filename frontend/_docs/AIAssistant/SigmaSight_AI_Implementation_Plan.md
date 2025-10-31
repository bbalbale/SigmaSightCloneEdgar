# SigmaSight AI - Frontend Implementation Plan

**Status**: Ready to Implement
**Last Updated**: 2025-10-22
**Page**: `/sigmasight-ai`
**Backend Status**: ✅ Complete (Phases 1-4)

---

## Executive Summary

This document outlines the implementation plan for the SigmaSight AI Analytical Reasoning feature on the frontend. The backend is fully complete with Claude Sonnet 4 integration, database schema, and service layer. We need to build the frontend UI to surface this capability to users.

**Key Capabilities** (Backend Ready):
- Generate AI-powered portfolio insights (~$0.02, 25-30 seconds)
- 7 insight types (Daily Summary, Volatility Analysis, Concentration Risk, etc.)
- Smart 24-hour caching
- Cost and performance tracking
- User feedback system (database ready)

**Implementation Approach**:
- Use existing `/sigmasight-ai` page (already in menu)
- Follow container pattern (already set up)
- Build incrementally with 3 phases
- Test with real demo portfolios

---

## Current State

### What Exists ✅

**Frontend**:
- ✅ Route: `/app/sigmasight-ai/page.tsx` (8 lines, follows container pattern)
- ✅ Container: `/src/containers/SigmaSightAIContainer.tsx` (45 lines, basic shell)
- ✅ Navigation: Already in dropdown menu
- ✅ Styling: Theme support (dark/light mode)

**Backend** (All Complete):
- ✅ Database: `ai_insights` and `ai_insight_templates` tables
- ✅ Models: `AIInsight` and `AIInsightTemplate` ORM models
- ✅ Service: `analytical_reasoning_service.py` (orchestration)
- ✅ Provider: `anthropic_provider.py` (Claude Sonnet 4 integration)
- ✅ Context: `hybrid_context_builder.py` (data aggregation)
- ✅ Testing: Validated with real portfolio data

### What Needs to Be Built 🔨

**Phase 1 - Core Experience** (MVP):
1. Backend API endpoints (5 endpoints)
2. Frontend service layer (`insightsApi.ts`)
3. Data hooks (`useInsights.ts`, `useGenerateInsight.ts`)
4. Core UI components (list, detail, generate)
5. Basic SigmaSightAIContainer implementation

**Phase 2 - Enhanced Features**:
1. User feedback/rating system
2. All 7 insight types enabled
3. Focus area and custom questions
4. Advanced filtering and sorting
5. Performance metrics display

**Phase 3 - Polish**:
1. Dashboard widget (for portfolio page)
2. Loading and error states refinement
3. Responsive design optimization
4. Export/share capabilities
5. Documentation

---

## Architecture Overview

### Page Structure

```
/sigmasight-ai                          # Main route (existing)
  └─ SigmaSightAIContainer              # Container component (existing shell)
       ├─ InsightsList                  # List of insights (NEW)
       │    └─ InsightCard              # Individual insight preview (NEW)
       ├─ InsightDetailModal            # Full insight view (NEW)
       ├─ GenerateInsightModal          # Generate new insight form (NEW)
       └─ InsightFilters                # Filter/sort controls (NEW)
```

**Design Decision**: Use modals for detail/generate instead of separate routes
- **Rationale**: Keeps user on main page, better UX for reviewing multiple insights
- **Alternative**: Could add `/sigmasight-ai/[insight_id]` route later if needed

### Data Flow

```
User Action (Generate Insight)
    ↓
GenerateInsightModal
    ↓
useGenerateInsight hook (gets portfolioId from portfolioStore)
    ↓
insightsApi.generateInsight()
    ↓
apiClient.post('/api/v1/insights/generate')
    ↓
Next.js Proxy (/api/proxy/*)
    ↓
Backend: analytical_reasoning_service.investigate_portfolio()
    ↓
Backend: hybrid_context_builder (aggregates portfolio data)
    ↓
Claude Sonnet 4 API
    ↓
Database: ai_insights table
    ↓
Response to Frontend
    ↓
Custom hook updates local state
    ↓
UI re-renders with new insight
```

### State Management Pattern (Matches Existing App Architecture)

**Zustand Store** (EXISTING `portfolioStore`):
- `portfolioId` - Accessed via `usePortfolioStore(state => state.portfolioId)`
- No new Zustand store needed!

**Custom Hooks** (useState pattern like `useTags`, `usePortfolioData`):
- `useInsights()` - List insights, loading, error
- `useGenerateInsight()` - Generate mutation with loading state
- `useInsightDetail()` - Single insight detail
- `useSubmitFeedback()` - Feedback submission

**Local Component State** (useState):
- Selected insight ID (for modal)
- Filter/sort preferences
- Modal open/closed state
- Form inputs

**Service Layer** (like `tagsApi.ts`, `portfolioService.ts`):
- `insightsApi.ts` - All API calls
- Uses existing `apiClient` for authentication

---

## Phase 1: Core Experience (MVP)

**Goal**: Users can generate and view AI insights for their portfolio
**Timeline**: 3-5 days
**Cost**: ~$0.02 per insight generation

### 1.0 Backend Context Enhancement (FIRST STEP)

**CRITICAL**: Before building API endpoints, we need to update the backend to send volatility analytics and spread factors to Claude.

**File**: `backend/app/services/hybrid_context_builder.py` (UPDATE)

**Add Two New Methods**:

```python
async def _get_volatility_analytics(
    self,
    db: AsyncSession,
    portfolio_id: UUID,
) -> Dict[str, Any]:
    """Get portfolio and position volatility analytics."""
    from app.models.market_data import PositionVolatility
    from app.models.snapshots import PortfolioSnapshot

    # Get latest portfolio snapshot for portfolio-level volatility
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(desc(PortfolioSnapshot.snapshot_date))
        .limit(1)
    )
    snapshot = result.scalar_one_or_none()

    if not snapshot:
        return {"available": False}

    return {
        "available": True,
        "portfolio_level": {
            "realized_volatility_21d": float(snapshot.realized_volatility_21d) if snapshot.realized_volatility_21d else None,
            "realized_volatility_63d": float(snapshot.realized_volatility_63d) if snapshot.realized_volatility_63d else None,
            "expected_volatility_21d": float(snapshot.expected_volatility_21d) if snapshot.expected_volatility_21d else None,
            "volatility_trend": snapshot.volatility_trend,
            "volatility_percentile": float(snapshot.volatility_percentile) if snapshot.volatility_percentile else None,
        }
    }

async def _get_spread_factors(
    self,
    db: AsyncSession,
    portfolio_id: UUID,
) -> Dict[str, Any]:
    """Get spread factor exposures (Growth-Value, Momentum, Size, Quality)."""
    from app.models.market_data import FactorDefinition, FactorExposure

    # Get active spread factors
    spread_factors_stmt = (
        select(FactorDefinition.id, FactorDefinition.name)
        .where(and_(
            FactorDefinition.is_active == True,
            FactorDefinition.factor_type == 'spread'
        ))
        .order_by(FactorDefinition.display_order.asc())
    )
    spread_result = await db.execute(spread_factors_stmt)
    spread_factor_ids = [row[0] for row in spread_result.all()]

    if not spread_factor_ids:
        return {"available": False}

    # Find latest calculation date
    latest_date_stmt = (
        select(func.max(FactorExposure.calculation_date))
        .where(and_(
            FactorExposure.portfolio_id == portfolio_id,
            FactorExposure.factor_id.in_(spread_factor_ids)
        ))
    )
    latest_date_result = await db.execute(latest_date_stmt)
    latest_date = latest_date_result.scalar_one_or_none()

    if not latest_date:
        return {"available": False}

    # Load spread factor exposures
    exposures_stmt = (
        select(FactorExposure, FactorDefinition)
        .join(FactorDefinition, FactorExposure.factor_id == FactorDefinition.id)
        .where(and_(
            FactorExposure.portfolio_id == portfolio_id,
            FactorExposure.calculation_date == latest_date,
            FactorExposure.factor_id.in_(spread_factor_ids)
        ))
    )
    exposures_result = await db.execute(exposures_stmt)
    exposure_rows = exposures_result.all()

    if not exposure_rows:
        return {"available": False}

    # Build spread factors dict
    factors = {}
    for exposure, definition in exposure_rows:
        from app.calculations.factor_interpretation import interpret_spread_beta

        beta = float(exposure.exposure_value)
        interpretation = interpret_spread_beta(definition.name, beta)

        factors[definition.name] = {
            "beta": beta,
            "direction": interpretation['direction'],
            "magnitude": interpretation['magnitude'],
            "risk_level": interpretation['risk_level'],
            "explanation": interpretation['explanation']
        }

    return {
        "available": True,
        "calculation_date": latest_date.isoformat(),
        "factors": factors
    }
```

**Update `build_context()` method**:

```python
async def build_context(
    self,
    db: AsyncSession,
    portfolio_id: UUID,
    focus_area: Optional[str] = None,
) -> Dict[str, Any]:
    # ... existing code ...

    # 6. Get correlations
    correlations = await self._get_correlations(db, portfolio_id)
    context["correlations"] = correlations

    # 7. Get volatility analytics (NEW)
    volatility_analytics = await self._get_volatility_analytics(db, portfolio_id)
    context["volatility_analytics"] = volatility_analytics

    # 8. Get spread factors (NEW)
    spread_factors = await self._get_spread_factors(db, portfolio_id)
    context["spread_factors"] = spread_factors

    # 9. Assess data quality (update to include new metrics)
    data_quality = self._assess_data_quality(context)
    context["data_quality"] = data_quality

    # ... rest of existing code ...
```

**Update `_assess_data_quality()` to include new metrics**:

```python
def _assess_data_quality(self, context: Dict[str, Any]) -> Dict[str, str]:
    quality = {}

    # ... existing quality checks ...

    # Volatility analytics
    vol = context.get("volatility_analytics", {})
    if vol.get("available"):
        quality["volatility_analytics"] = "complete"
    else:
        quality["volatility_analytics"] = "incomplete"

    # Spread factors
    spread = context.get("spread_factors", {})
    if spread.get("available"):
        quality["spread_factors"] = "complete"
    else:
        quality["spread_factors"] = "incomplete"

    # Update overall quality calculation
    complete_count = sum(1 for v in quality.values() if v == "complete")
    if complete_count >= 6:  # Increased threshold
        quality["overall"] = "complete"
    elif complete_count >= 3:
        quality["overall"] = "partial"
    else:
        quality["overall"] = "incomplete"

    return quality
```

**Testing**:
```bash
# Test that context builder includes new data
cd backend
uv run python -c "
import asyncio
from uuid import UUID
from app.services.hybrid_context_builder import hybrid_context_builder
from app.database import get_async_session

async def test():
    async with get_async_session() as db:
        # Use a demo portfolio ID
        context = await hybrid_context_builder.build_context(
            db=db,
            portfolio_id=UUID('your-demo-portfolio-id')
        )
        print('Volatility available:', context.get('volatility_analytics', {}).get('available'))
        print('Spread factors available:', context.get('spread_factors', {}).get('available'))

asyncio.run(test())
"
```

---

### 1.1 Backend API Endpoints

**Location**: `backend/app/api/v1/insights.py` (NEW)

#### Endpoint 1: Generate Insight
```python
@router.post("/insights/generate")
async def generate_insight(
    request: GenerateInsightRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> AIInsightResponse:
    """
    Generate a new AI insight for a portfolio.

    Request Body:
        {
            "portfolio_id": "uuid",
            "insight_type": "daily_summary",
            "focus_area": "optional string",
            "user_question": "optional string"
        }

    Returns:
        Full AIInsight object with analysis, findings, recommendations

    Cost: ~$0.02, Time: 25-30 seconds
    """
```

#### Endpoint 2: List Portfolio Insights
```python
@router.get("/insights/portfolio/{portfolio_id}")
async def list_portfolio_insights(
    portfolio_id: UUID,
    insight_type: Optional[InsightType] = None,
    days_back: int = 30,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> InsightsListResponse:
    """
    List insights for a portfolio with filtering.

    Query Params:
        - insight_type: Filter by type (optional)
        - days_back: How far back to look (default 30)
        - limit: Max results (default 20)
        - offset: Pagination offset (default 0)

    Returns:
        {
            "insights": [...],
            "total": int,
            "has_more": bool
        }
    """
```

#### Endpoint 3: Get Single Insight
```python
@router.get("/insights/{insight_id}")
async def get_insight(
    insight_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> AIInsightResponse:
    """
    Get detailed view of a single insight.

    Automatically marks insight as viewed.

    Returns:
        Full AIInsight object with all fields
    """
```

#### Endpoint 4: Update Insight Status
```python
@router.patch("/insights/{insight_id}")
async def update_insight(
    insight_id: UUID,
    request: UpdateInsightRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> AIInsightResponse:
    """
    Update insight metadata (viewed, dismissed).

    Request Body:
        {
            "viewed": true,
            "dismissed": false
        }
    """
```

#### Endpoint 5: Submit Feedback
```python
@router.post("/insights/{insight_id}/feedback")
async def submit_feedback(
    insight_id: UUID,
    request: InsightFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
) -> MessageResponse:
    """
    Submit user feedback/rating for an insight.

    Request Body:
        {
            "rating": 4.5,  // 1-5 scale
            "feedback": "Very helpful analysis"
        }
    """
```

**Implementation Notes**:
- Add router to `backend/app/api/v1/router.py`
- Create Pydantic schemas in `backend/app/api/v1/schemas/insights.py`
- Use existing `analytical_reasoning_service.investigate_portfolio()`
- Add authentication checks (verify portfolio ownership)
- Add rate limiting (max 10 per portfolio per day)

### 1.2 Frontend Service Layer

**File**: `frontend/src/services/insightsApi.ts` (NEW)

```typescript
import { apiClient } from './apiClient'

export type InsightType =
  | 'daily_summary'
  | 'volatility_analysis'
  | 'concentration_risk'
  | 'hedge_quality'
  | 'factor_exposure'
  | 'stress_test_review'
  | 'custom'

export type InsightSeverity =
  | 'critical'
  | 'warning'
  | 'elevated'
  | 'normal'
  | 'info'

export interface AIInsight {
  id: string
  portfolio_id: string
  insight_type: InsightType
  title: string
  severity: InsightSeverity
  summary: string
  key_findings: string[]
  recommendations: string[]
  full_analysis: string  // Markdown
  data_limitations: string
  focus_area: string | null
  user_question: string | null
  created_at: string
  viewed: boolean
  dismissed: boolean
  user_rating: number | null
  user_feedback: string | null
  performance: {
    cost_usd: number
    generation_time_ms: number
    token_count: number
  }
}

export interface GenerateInsightRequest {
  portfolio_id: string
  insight_type: InsightType
  focus_area?: string
  user_question?: string
}

const insightsApi = {
  /**
   * Generate a new AI insight for a portfolio
   * Cost: ~$0.02, Time: 25-30 seconds
   */
  async generateInsight(request: GenerateInsightRequest): Promise<AIInsight> {
    const response = await apiClient.post('/insights/generate', request)
    return response as AIInsight
  },

  /**
   * List insights for a portfolio
   */
  async listInsights(
    portfolioId: string,
    options?: {
      insightType?: InsightType
      daysBack?: number
      limit?: number
      offset?: number
    }
  ): Promise<{ insights: AIInsight[]; total: number; has_more: boolean }> {
    const params = new URLSearchParams()
    if (options?.insightType) params.append('insight_type', options.insightType)
    if (options?.daysBack) params.append('days_back', options.daysBack.toString())
    if (options?.limit) params.append('limit', options.limit.toString())
    if (options?.offset) params.append('offset', options.offset.toString())

    const response = await apiClient.get(
      `/insights/portfolio/${portfolioId}?${params.toString()}`
    )
    return response as { insights: AIInsight[]; total: number; has_more: boolean }
  },

  /**
   * Get a single insight by ID
   */
  async getInsight(insightId: string): Promise<AIInsight> {
    const response = await apiClient.get(`/insights/${insightId}`)
    return response as AIInsight
  },

  /**
   * Update insight status (viewed, dismissed)
   */
  async updateInsight(
    insightId: string,
    updates: { viewed?: boolean; dismissed?: boolean }
  ): Promise<AIInsight> {
    const response = await apiClient.patch(`/insights/${insightId}`, updates)
    return response as AIInsight
  },

  /**
   * Submit user feedback/rating
   */
  async submitFeedback(
    insightId: string,
    feedback: { rating: number; feedback?: string }
  ): Promise<void> {
    await apiClient.post(`/insights/${insightId}/feedback`, feedback)
  },
}

export default insightsApi
```

### 1.3 Data Hooks (Following Existing Pattern)

**File**: `frontend/src/hooks/useInsights.ts` (NEW)

**Pattern Reference**: Follows `useTags.ts` and `usePortfolioData.ts` patterns

```typescript
'use client'

import { useState, useEffect, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import insightsApi, { AIInsight, InsightType } from '@/services/insightsApi'

interface UseInsightsOptions {
  insightType?: InsightType
  daysBack?: number
  limit?: number
  autoRefresh?: boolean
}

interface UseInsightsReturn {
  insights: AIInsight[]
  loading: boolean
  error: Error | null
  total: number
  hasMore: boolean
  refresh: () => Promise<void>
}

/**
 * Hook to fetch and manage insights list for current portfolio
 *
 * Pattern: Same as useTags - uses useState, calls service layer
 */
export function useInsights(options: UseInsightsOptions = {}): UseInsightsReturn {
  const {
    insightType,
    daysBack = 30,
    limit = 20,
    autoRefresh = true
  } = options

  // Get portfolioId from existing Zustand store (like usePortfolioData does)
  const portfolioId = usePortfolioStore(state => state.portfolioId)

  // Local state (like useTags pattern)
  const [insights, setInsights] = useState<AIInsight[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  const fetchInsights = useCallback(async () => {
    if (!portfolioId) {
      setInsights([])
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await insightsApi.listInsights(portfolioId, {
        insightType,
        daysBack,
        limit,
      })

      setInsights(response.insights || [])
      setTotal(response.total || 0)
      setHasMore(response.has_more || false)
    } catch (err) {
      console.error('Failed to fetch insights:', err)
      setError(err instanceof Error ? err : new Error('Failed to fetch insights'))
      setInsights([])
    } finally {
      setLoading(false)
    }
  }, [portfolioId, insightType, daysBack, limit])

  // Auto-fetch on mount and when dependencies change (like useTags)
  useEffect(() => {
    if (autoRefresh) {
      fetchInsights()
    }
  }, [fetchInsights, autoRefresh])

  return {
    insights,
    loading,
    error,
    total,
    hasMore,
    refresh: fetchInsights,
  }
}

/**
 * Hook to fetch a single insight detail
 */
export function useInsightDetail(insightId: string | null) {
  const [insight, setInsight] = useState<AIInsight | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!insightId) {
      setInsight(null)
      return
    }

    const fetchInsight = async () => {
      setLoading(true)
      setError(null)

      try {
        const data = await insightsApi.getInsight(insightId)
        setInsight(data)
      } catch (err) {
        console.error('Failed to fetch insight:', err)
        setError(err instanceof Error ? err : new Error('Failed to fetch insight'))
        setInsight(null)
      } finally {
        setLoading(false)
      }
    }

    fetchInsight()
  }, [insightId])

  return { insight, loading, error }
}

/**
 * Hook to generate a new insight
 */
export function useGenerateInsight() {
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const generate = useCallback(async (
    insightType: InsightType,
    focusArea?: string,
    userQuestion?: string
  ): Promise<AIInsight | null> => {
    if (!portfolioId) {
      throw new Error('No portfolio ID')
    }

    setGenerating(true)
    setError(null)

    try {
      const insight = await insightsApi.generateInsight({
        portfolio_id: portfolioId,
        insight_type: insightType,
        focus_area: focusArea,
        user_question: userQuestion,
      })

      return insight
    } catch (err) {
      console.error('Failed to generate insight:', err)
      const error = err instanceof Error ? err : new Error('Failed to generate insight')
      setError(error)
      throw error
    } finally {
      setGenerating(false)
    }
  }, [portfolioId])

  return {
    generate,
    generating,
    error,
  }
}

/**
 * Hook to submit feedback for an insight
 */
export function useInsightFeedback() {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const submitFeedback = useCallback(async (
    insightId: string,
    rating: number,
    feedback?: string
  ) => {
    setSubmitting(true)
    setError(null)

    try {
      await insightsApi.submitFeedback(insightId, { rating, feedback })
    } catch (err) {
      console.error('Failed to submit feedback:', err)
      const error = err instanceof Error ? err : new Error('Failed to submit feedback')
      setError(error)
      throw error
    } finally {
      setSubmitting(false)
    }
  }, [])

  return {
    submitFeedback,
    submitting,
    error,
  }
}
```

### 1.4 Core UI Components

#### Component 1: InsightCard.tsx

**File**: `frontend/src/components/insights/InsightCard.tsx` (NEW)

```typescript
'use client'

import React from 'react'
import { AIInsight } from '@/services/insightsApi'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { formatDistanceToNow } from 'date-fns'

interface InsightCardProps {
  insight: AIInsight
  onView: (insight: AIInsight) => void
}

const severityConfig = {
  critical: { label: 'CRITICAL', color: 'bg-red-500', icon: '🔴' },
  warning: { label: 'WARNING', color: 'bg-orange-500', icon: '⚠️' },
  elevated: { label: 'ELEVATED', color: 'bg-yellow-500', icon: '🟡' },
  normal: { label: 'NORMAL', color: 'bg-blue-500', icon: '🔵' },
  info: { label: 'INFO', color: 'bg-gray-500', icon: 'ℹ️' },
}

export function InsightCard({ insight, onView }: InsightCardProps) {
  const config = severityConfig[insight.severity]
  const timeAgo = formatDistanceToNow(new Date(insight.created_at), { addSuffix: true })

  return (
    <Card className={`cursor-pointer hover:shadow-lg transition-shadow ${
      !insight.viewed ? 'border-l-4 border-l-blue-500' : ''
    }`}
      onClick={() => onView(insight)}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">{config.icon}</span>
            <Badge className={config.color}>{config.label}</Badge>
            {!insight.viewed && (
              <Badge variant="outline">New</Badge>
            )}
          </div>
          <span className="text-sm text-muted-foreground">{timeAgo}</span>
        </div>
        <CardTitle className="mt-2">{insight.title}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-3">
          {insight.summary}
        </CardDescription>
        <div className="mt-4 flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            {insight.key_findings.length} findings • {insight.recommendations.length} recommendations
          </div>
          <Button variant="ghost" size="sm">
            View Details →
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

#### Component 2: InsightsList.tsx

**File**: `frontend/src/components/insights/InsightsList.tsx` (NEW)

```typescript
'use client'

import React, { useState } from 'react'
import { useInsights } from '@/hooks/useInsights'
import { InsightCard } from './InsightCard'
import { AIInsight, InsightType } from '@/services/insightsApi'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface InsightsListProps {
  onSelectInsight: (insight: AIInsight) => void
  filterType?: InsightType
  daysBack?: number
}

export function InsightsList({
  onSelectInsight,
  filterType,
  daysBack = 30
}: InsightsListProps) {
  const { data, isLoading, error } = useInsights({
    insightType: filterType,
    daysBack,
    limit: 20,
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>
          Failed to load insights. Please try again.
        </AlertDescription>
      </Alert>
    )
  }

  if (!data || data.insights.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">
          No insights yet. Generate your first AI analysis!
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {data.insights.map((insight) => (
        <InsightCard
          key={insight.id}
          insight={insight}
          onView={onSelectInsight}
        />
      ))}

      {data.has_more && (
        <div className="text-center py-4">
          <Button variant="outline" onClick={() => {
            // TODO: Implement pagination
          }}>
            Load More
          </Button>
        </div>
      )}
    </div>
  )
}
```

#### Component 3: GenerateInsightModal.tsx

**File**: `frontend/src/components/insights/GenerateInsightModal.tsx` (NEW)

```typescript
'use client'

import React, { useState } from 'react'
import { useGenerateInsight } from '@/hooks/useInsights'
import { InsightType } from '@/services/insightsApi'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'

interface GenerateInsightModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (insightId: string) => void
}

const insightTypes = [
  { value: 'daily_summary', label: 'Daily Summary', description: 'Comprehensive portfolio review' },
  { value: 'volatility_analysis', label: 'Volatility Analysis', description: 'Volatility patterns and risk factors' },
  { value: 'concentration_risk', label: 'Concentration Risk', description: 'Concentration and diversification' },
  { value: 'hedge_quality', label: 'Hedge Quality', description: 'Hedge effectiveness evaluation' },
  { value: 'factor_exposure', label: 'Factor Exposure', description: 'Factor exposure and systematic risk' },
  { value: 'custom', label: 'Custom Question', description: 'Ask a specific question' },
]

export function GenerateInsightModal({
  open,
  onOpenChange,
  onSuccess
}: GenerateInsightModalProps) {
  const [insightType, setInsightType] = useState<InsightType>('daily_summary')
  const [focusArea, setFocusArea] = useState('')
  const [userQuestion, setUserQuestion] = useState('')

  const generateMutation = useGenerateInsight()

  const handleGenerate = async () => {
    try {
      const result = await generateMutation.mutateAsync({
        insight_type: insightType,
        focus_area: focusArea || undefined,
        user_question: insightType === 'custom' ? userQuestion : undefined,
      })

      toast.success(`Insight generated! Cost: $${result.performance.cost_usd.toFixed(4)}`)
      onOpenChange(false)
      onSuccess(result.id)

      // Reset form
      setInsightType('daily_summary')
      setFocusArea('')
      setUserQuestion('')
    } catch (error) {
      toast.error('Failed to generate insight. Please try again.')
      console.error(error)
    }
  }

  const selectedType = insightTypes.find(t => t.value === insightType)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Generate AI Insight</DialogTitle>
          <DialogDescription>
            Claude will analyze your portfolio and provide detailed insights.
            Cost: ~$0.02, Time: 25-30 seconds
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Insight Type */}
          <div className="space-y-2">
            <Label htmlFor="insight-type">Analysis Type</Label>
            <Select
              value={insightType}
              onValueChange={(value) => setInsightType(value as InsightType)}
            >
              <SelectTrigger id="insight-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {insightTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div>
                      <div className="font-medium">{type.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {type.description}
                      </div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Focus Area (Optional) */}
          {insightType !== 'custom' && (
            <div className="space-y-2">
              <Label htmlFor="focus-area">
                Focus Area <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                id="focus-area"
                placeholder="e.g., tech exposure, options risk, healthcare sector"
                value={focusArea}
                onChange={(e) => setFocusArea(e.target.value)}
              />
            </div>
          )}

          {/* Custom Question */}
          {insightType === 'custom' && (
            <div className="space-y-2">
              <Label htmlFor="user-question">Your Question</Label>
              <Textarea
                id="user-question"
                placeholder="e.g., Why is my portfolio underperforming the market?"
                rows={4}
                value={userQuestion}
                onChange={(e) => setUserQuestion(e.target.value)}
              />
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={generateMutation.isPending || (insightType === 'custom' && !userQuestion)}
          >
            {generateMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Generate Insight
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

#### Component 4: InsightDetailModal.tsx

**File**: `frontend/src/components/insights/InsightDetailModal.tsx` (NEW)

```typescript
'use client'

import React, { useEffect, useState } from 'react'
import { useInsight, useUpdateInsight, useSubmitFeedback } from '@/hooks/useInsights'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { formatDistanceToNow } from 'date-fns'
import ReactMarkdown from 'react-markdown'
import { Star } from 'lucide-react'

interface InsightDetailModalProps {
  insightId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

const severityConfig = {
  critical: { label: 'CRITICAL', color: 'bg-red-500', icon: '🔴' },
  warning: { label: 'WARNING', color: 'bg-orange-500', icon: '⚠️' },
  elevated: { label: 'ELEVATED', color: 'bg-yellow-500', icon: '🟡' },
  normal: { label: 'NORMAL', color: 'bg-blue-500', icon: '🔵' },
  info: { label: 'INFO', color: 'bg-gray-500', icon: 'ℹ️' },
}

export function InsightDetailModal({
  insightId,
  open,
  onOpenChange
}: InsightDetailModalProps) {
  const { data: insight, isLoading } = useInsight(insightId)
  const updateMutation = useUpdateInsight()
  const feedbackMutation = useSubmitFeedback()
  const [rating, setRating] = useState(0)

  // Mark as viewed when opened
  useEffect(() => {
    if (insight && !insight.viewed && insightId) {
      updateMutation.mutate({
        insightId,
        updates: { viewed: true },
      })
    }
  }, [insight, insightId])

  const handleRating = (newRating: number) => {
    setRating(newRating)
    if (insightId) {
      feedbackMutation.mutate({
        insightId,
        rating: newRating,
      })
    }
  }

  if (isLoading || !insight) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <Skeleton className="h-96 w-full" />
        </DialogContent>
      </Dialog>
    )
  }

  const config = severityConfig[insight.severity]
  const timeAgo = formatDistanceToNow(new Date(insight.created_at), { addSuffix: true })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">{config.icon}</span>
            <Badge className={config.color}>{config.label}</Badge>
            <span className="text-sm text-muted-foreground">{timeAgo}</span>
          </div>
          <DialogTitle className="text-2xl">{insight.title}</DialogTitle>
        </DialogHeader>

        {/* Performance Metrics */}
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>⚡ {(insight.performance.generation_time_ms / 1000).toFixed(1)}s</span>
          <span>💰 ${insight.performance.cost_usd.toFixed(4)}</span>
          <span>📊 {insight.performance.token_count.toLocaleString()} tokens</span>
        </div>

        <Separator />

        {/* Summary */}
        <div>
          <h3 className="font-semibold mb-2">Summary</h3>
          <p className="text-muted-foreground">{insight.summary}</p>
        </div>

        {/* Key Findings */}
        {insight.key_findings.length > 0 && (
          <div>
            <h3 className="font-semibold mb-2">📊 Key Findings</h3>
            <ul className="space-y-2">
              {insight.key_findings.map((finding, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-blue-500 mt-1">•</span>
                  <span>{finding}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Detailed Analysis */}
        <div>
          <h3 className="font-semibold mb-2">📝 Detailed Analysis</h3>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown>{insight.full_analysis}</ReactMarkdown>
          </div>
        </div>

        {/* Recommendations */}
        {insight.recommendations.length > 0 && (
          <div>
            <h3 className="font-semibold mb-2">💡 Recommendations</h3>
            <ol className="space-y-3">
              {insight.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="font-semibold text-blue-500">{idx + 1}.</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Data Limitations */}
        {insight.data_limitations && (
          <div className="bg-muted p-4 rounded-lg">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              ⚠️ Data Limitations
            </h3>
            <p className="text-sm text-muted-foreground">{insight.data_limitations}</p>
          </div>
        )}

        <Separator />

        {/* Rating */}
        <div>
          <h3 className="font-semibold mb-2">Was this insight helpful?</h3>
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => handleRating(star)}
                className="hover:scale-110 transition-transform"
              >
                <Star
                  className={`h-6 w-6 ${
                    star <= (rating || insight.user_rating || 0)
                      ? 'fill-yellow-400 text-yellow-400'
                      : 'text-gray-300'
                  }`}
                />
              </button>
            ))}
            {(rating || insight.user_rating) && (
              <span className="text-sm text-muted-foreground ml-2">
                {rating || insight.user_rating}/5
              </span>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

### 1.5 Update SigmaSightAIContainer

**File**: `frontend/src/containers/SigmaSightAIContainer.tsx` (UPDATE)

```typescript
'use client'

import React, { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { Button } from '@/components/ui/button'
import { InsightsList } from '@/components/insights/InsightsList'
import { GenerateInsightModal } from '@/components/insights/GenerateInsightModal'
import { InsightDetailModal } from '@/components/insights/InsightDetailModal'
import { AIInsight } from '@/services/insightsApi'
import { Plus } from 'lucide-react'

export function SigmaSightAIContainer() {
  const { theme } = useTheme()
  const [generateModalOpen, setGenerateModalOpen] = useState(false)
  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null)
  const [detailModalOpen, setDetailModalOpen] = useState(false)

  const handleSelectInsight = (insight: AIInsight) => {
    setSelectedInsightId(insight.id)
    setDetailModalOpen(true)
  }

  const handleGenerateSuccess = (insightId: string) => {
    // Automatically open the newly generated insight
    setSelectedInsightId(insightId)
    setDetailModalOpen(true)
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className={`text-3xl font-bold mb-2 transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                SigmaSight AI
              </h1>
              <p className={`transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>
                AI-powered portfolio insights and analysis
              </p>
            </div>
            <Button onClick={() => setGenerateModalOpen(true)} size="lg">
              <Plus className="mr-2 h-4 w-4" />
              Generate Insight
            </Button>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <InsightsList onSelectInsight={handleSelectInsight} />
        </div>
      </section>

      {/* Modals */}
      <GenerateInsightModal
        open={generateModalOpen}
        onOpenChange={setGenerateModalOpen}
        onSuccess={handleGenerateSuccess}
      />

      <InsightDetailModal
        insightId={selectedInsightId}
        open={detailModalOpen}
        onOpenChange={setDetailModalOpen}
      />
    </div>
  )
}
```

### 1.6 Testing Checklist

**Phase 1 MVP Testing**:
- [ ] Backend endpoints respond correctly
- [ ] API returns proper error messages
- [ ] Generate insight works (check cost ~$0.02)
- [ ] List insights displays properly
- [ ] Insight detail modal shows all data
- [ ] Markdown rendering works
- [ ] Rating system submits feedback
- [ ] Mark as viewed works
- [ ] Dark/light theme support
- [ ] Loading states display
- [ ] Error states display

---

## Phase 2: Enhanced Features

**Goal**: Full feature set with all insight types, filtering, and polish
**Timeline**: 2-3 days

### 2.1 Features to Add

1. **Insight Filters Component**
   - Filter by insight type
   - Filter by severity
   - Filter by date range
   - Sort options (newest, oldest, highest severity)

2. **All Insight Types**
   - Enable all 7 insight types in generation modal
   - Add descriptions/help text
   - Custom question support

3. **User Feedback System**
   - Star rating (already in Phase 1)
   - Text feedback textarea
   - Thumbs up/down quick feedback
   - Feedback submission

4. **Performance Metrics Display**
   - Cost breakdown
   - Token usage visualization
   - Generation time chart
   - Cache hit rate indicator

5. **Data Quality Indicators**
   - Show data completeness percentage
   - Highlight data limitations
   - Warning badges for incomplete data

### 2.2 Components to Build

- `InsightFilters.tsx` - Filter and sort controls
- `InsightFeedbackForm.tsx` - Extended feedback form
- `PerformanceMetrics.tsx` - Metrics visualization
- `DataQualityBadge.tsx` - Data quality indicator

---

## Phase 3: Polish & Production Ready

**Goal**: Production-ready feature with dashboard widget
**Timeline**: 2-3 days

### 3.1 Features to Add

1. **Dashboard Widget** (for `/portfolio` page)
   - Latest critical/warning insight
   - Count of unread insights
   - Quick link to SigmaSight AI page

2. **Advanced UX**
   - Pagination for insights list
   - Infinite scroll option
   - Search insights by keyword
   - Export insight as PDF
   - Share insight (copy link)

3. **Loading & Error States**
   - Skeleton loaders
   - Empty states with illustrations
   - Error boundaries
   - Retry mechanisms

4. **Responsive Design**
   - Mobile-optimized modals
   - Tablet layout
   - Touch-friendly interactions

5. **Documentation**
   - User guide (how to use)
   - Tooltips and help text
   - FAQ section

### 3.2 Components to Build

- `InsightWidget.tsx` - Dashboard widget for portfolio page
- `InsightEmptyState.tsx` - Empty state component
- `InsightErrorBoundary.tsx` - Error boundary
- `InsightPagination.tsx` - Pagination controls

---

## Technical Considerations

### React Query Setup

Ensure React Query is configured in `app/providers.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

// Wrap app with QueryClientProvider
```

### Dependencies to Install

```bash
npm install @tanstack/react-query
npm install react-markdown
npm install date-fns
npm install lucide-react  # (may already be installed)
npm install sonner  # Toast notifications (may already be installed)
```

### API Proxy Configuration

Ensure Next.js proxy handles `/api/v1/insights/*` routes:

```typescript
// app/api/proxy/[...path]/route.ts
// Should already handle all /api/v1/* routes
```

### Cost Management

**Rate Limiting** (Backend):
- Max 10 insights per portfolio per day
- 5-minute cooldown between generations
- Monthly budget alerts

**Frontend Safeguards**:
- Show cost estimate before generation
- Confirm for custom questions (higher token usage)
- Display running monthly cost

### Error Handling

**Common Errors**:
1. **Portfolio has no data** - Show friendly message
2. **API timeout** - Insight generation takes 25-30s, show progress
3. **Rate limit exceeded** - Show cooldown timer
4. **Budget exceeded** - Contact admin message

---

## File Structure Summary

```
frontend/
├── app/
│   └── sigmasight-ai/
│       └── page.tsx                         # ✅ Exists (thin wrapper)
│
├── src/
│   ├── containers/
│   │   └── SigmaSightAIContainer.tsx        # ✅ Exists → UPDATE
│   │
│   ├── components/
│   │   └── insights/                        # 🆕 NEW FOLDER
│   │       ├── InsightCard.tsx              # Phase 1
│   │       ├── InsightsList.tsx             # Phase 1
│   │       ├── GenerateInsightModal.tsx     # Phase 1
│   │       ├── InsightDetailModal.tsx       # Phase 1
│   │       ├── InsightFilters.tsx           # Phase 2
│   │       ├── InsightFeedbackForm.tsx      # Phase 2
│   │       ├── PerformanceMetrics.tsx       # Phase 2
│   │       ├── DataQualityBadge.tsx         # Phase 2
│   │       ├── InsightWidget.tsx            # Phase 3 (dashboard)
│   │       ├── InsightEmptyState.tsx        # Phase 3
│   │       └── InsightPagination.tsx        # Phase 3
│   │
│   ├── services/
│   │   └── insightsApi.ts                   # 🆕 NEW - Phase 1
│   │
│   └── hooks/
│       └── useInsights.ts                   # 🆕 NEW - Phase 1
│
backend/
└── app/
    └── api/v1/
        ├── insights.py                       # 🆕 NEW - Phase 1
        └── schemas/
            └── insights.py                   # 🆕 NEW - Phase 1
```

---

## Implementation Order

### Week 1: Phase 1 MVP

**Day 1: Backend Context Enhancement** ✅ **COMPLETE** (2025-10-22)
1. ✅ Added `_get_volatility_analytics()` method to `hybrid_context_builder.py`
2. ✅ Added `_get_spread_factors()` method to `hybrid_context_builder.py`
3. ✅ Updated `build_context()` to include new data
4. ✅ Updated `_assess_data_quality()` for new metrics
5. ✅ Tested - context now includes volatility and spread factors
6. ✅ Verified - no breaking changes, existing functionality preserved

**Test Results** (Demo Individual Portfolio - 16 positions):
- Volatility Analytics: 12.3% (21d), 10.59% (63d), Expected 9.42%, Trend: increasing
- Spread Factors: 4 factors calculated (Growth +1.99, Momentum +0.23, Size -0.12, Quality -4.93)
- Target Prices: 56.25% coverage (9 of 16 positions have analyst targets)
- Data Quality: 8/8 metrics complete

**Bonus Addition**: Target price analytics added to snapshot data:
- Portfolio-level returns (EOY, next year, downside scenarios)
- Dollar upside/downside calculations
- Coverage percentage and position counts
- Last updated timestamps

**Day 2-3: Backend API** ✅ **COMPLETE** (2025-10-22)
1. ✅ Created `backend/app/api/v1/insights.py` (600+ lines)
2. ✅ Created Pydantic schemas (inline, following project pattern)
3. ✅ Implemented all 5 endpoints:
   - POST `/api/v1/insights/generate` - Generate new insight
   - GET `/api/v1/insights/portfolio/{portfolio_id}` - List insights with filtering
   - GET `/api/v1/insights/{insight_id}` - Get single insight (auto-marks as viewed)
   - PATCH `/api/v1/insights/{insight_id}` - Update metadata (viewed/dismissed)
   - POST `/api/v1/insights/{insight_id}/feedback` - Submit rating/feedback
4. ✅ Added to router in `app/api/v1/router.py`
5. ✅ Verified all routes registered in FastAPI app

**Implementation Details**:
- Rate limiting: Max 10 insights per portfolio per day
- Authentication: All endpoints require valid JWT token
- Authorization: Validates portfolio ownership for all operations
- Auto-mark viewed: GET endpoint automatically marks insights as viewed
- Filtering: List endpoint supports insight_type, days_back, pagination
- Performance tracking: Each insight records cost_usd, generation_time_ms, token_count
- Error handling: Comprehensive error messages and HTTP status codes

**Day 4: Frontend Service & Hooks** ✅ **COMPLETE** (2025-10-22)
1. ✅ Created `frontend/src/services/insightsApi.ts` (225 lines)
2. ✅ Created `frontend/src/hooks/useInsights.ts` (329 lines)
3. ✅ Added `patch()` method to `apiClient.ts` (previously missing)
4. ✅ Verified TypeScript compilation (no errors in insights code)

**Implementation Details**:
- Service layer: All 5 API methods implemented (generate, list, get, update, submit feedback)
- Hooks: 5 custom hooks following existing app patterns:
  - `useInsights()` - List insights with auto-refresh (matches `useTags` pattern)
  - `useInsightDetail()` - Single insight detail
  - `useGenerateInsight()` - Generate mutation with loading state
  - `useInsightFeedback()` - Submit rating/feedback
  - `useUpdateInsight()` - Update viewed/dismissed metadata
- State management: Uses Zustand `portfolioStore` for portfolioId (no new stores needed)
- API client: Added missing `patch()` HTTP method to support PATCH requests
- Type safety: Full TypeScript interfaces for all request/response types
- Error handling: Comprehensive try/catch with user-friendly error messages
- Pattern compliance: Follows existing service layer and hooks patterns exactly

**Day 5: Core UI Components** ✅ **COMPLETE** (2025-10-22)
1. ✅ Created `InsightCard.tsx` - Preview card with severity badges, timestamps, and click-to-view
2. ✅ Created `InsightsList.tsx` - List component with loading, error, and empty states
3. ✅ Created `GenerateInsightModal.tsx` - Modal form with insight type selection and custom questions
4. ✅ Created `InsightDetailModal.tsx` - Full detail view with markdown rendering and ratings
5. ✅ Created missing UI components: `Textarea`, `Separator`, `Skeleton`
6. ✅ Created index export file for easier imports
7. ✅ Verified TypeScript compilation (no errors)

**Implementation Details**:
- **InsightCard.tsx** (87 lines): Severity badges with color coding, new indicator for unviewed, click handler
- **InsightsList.tsx** (119 lines): Loading skeletons, error retry, empty state with emoji, load more pagination
- **GenerateInsightModal.tsx** (235 lines): 6 insight types, focus area input, custom question textarea, form validation
- **InsightDetailModal.tsx** (297 lines): Full detail display, custom markdown renderer, star ratings, auto-mark as viewed
- **UI Components**: Added 3 shadcn/ui components following project patterns (textarea, separator, skeleton)
- **Styling**: Full dark/light theme support, responsive design, hover states, loading animations
- **Pattern Compliance**: All components follow React best practices and project conventions

**Day 6: Container Integration & Testing** ✅ **COMPLETE** (2025-10-22)
1. ✅ Updated `SigmaSightAIContainer.tsx` with full component integration (110 lines)
2. ✅ Wired all modals and list together with proper callbacks
3. ✅ Implemented complete flow: generate → auto-open detail → rate
4. ✅ Verified dark/light theme support throughout
5. ✅ Verified TypeScript compilation (no errors)

**Implementation Details**:
- **Header Section**: Sparkles icon, title, description, cost/time info, "Generate Insight" button
- **Main Content**: InsightsList component with auto-refresh
- **Modal Management**: State management for both modals (generate and detail)
- **Flow Implementation**:
  - Click "Generate Insight" → Opens GenerateInsightModal
  - Select insight type and submit → Generates insight (~25-30s)
  - On success → Automatically opens InsightDetailModal with new insight
  - Click any insight card → Opens detail modal for that insight
  - Rate insight → Submits feedback to backend
  - List auto-refreshes after generation via useInsights hook
- **Theme Support**: Full dark/light mode transitions on all elements
- **Responsive**: Button placement adapts to screen size

---

## 🎉 Phase 1 MVP Status: READY FOR TESTING

All core functionality is now implemented and ready for end-to-end testing!

**What's Working** ✅:
- ✅ Backend: 5 API endpoints with rate limiting and auth
- ✅ Backend: Enhanced context with volatility, spread factors, and target prices
- ✅ Frontend: Complete service layer (insightsApi.ts)
- ✅ Frontend: 5 custom hooks following app patterns
- ✅ Frontend: 4 core UI components (Card, List, Generate Modal, Detail Modal)
- ✅ Frontend: 3 new UI primitives (Textarea, Separator, Skeleton)
- ✅ Frontend: Full container integration with modal flow
- ✅ TypeScript: Zero compilation errors
- ✅ Theme: Full dark/light mode support

**Ready to Test**:
1. **Start Backend**: `cd backend && uv run python run.py`
2. **Start Frontend**: `cd frontend && npm run dev` (or Docker)
3. **Login**: Use demo credentials (e.g., `demo_hnw@sigmasight.com` / `demo12345`)
4. **Navigate**: Go to `/sigmasight-ai` page
5. **Test Flow**:
   - Click "Generate Insight" button
   - Select "Daily Summary" (or any type)
   - Wait 25-30 seconds for generation
   - View auto-opened insight detail
   - Rate the insight (1-5 stars)
   - Close modal and see insight in list
   - Click insight card to re-open detail

**Expected Costs**:
- Each insight generation: ~$0.02
- Rate limit: 10 per portfolio per day
- Token usage: ~10,000-15,000 tokens per insight

---

**Day 7: Testing & Bug Fixes** (Optional - if needed)
1. Manual testing of all flows
2. Fix any bugs discovered
3. Polish UI/UX issues
4. Add any missing error handling

### Week 2: Phase 2 Enhanced Features

**Days 6-8**: Implement filters, all insight types, feedback system, metrics

### Week 3: Phase 3 Polish

**Days 9-11**: Dashboard widget, pagination, responsive design, documentation

---

## Success Criteria

### Phase 1 Success
- [ ] User can generate AI insight from UI
- [ ] Insights list displays correctly
- [ ] Detail modal shows full analysis
- [ ] Rating system works
- [ ] Cost is ~$0.02 per insight
- [ ] Generation time is 25-30 seconds

### Phase 2 Success
- [ ] All 7 insight types available
- [ ] Filtering works correctly
- [ ] User feedback captured
- [ ] Performance metrics visible

### Phase 3 Success
- [ ] Dashboard widget live on portfolio page
- [ ] Mobile responsive
- [ ] Production deployed
- [ ] User documentation complete

---

## Next Steps

1. **Read This Document** - Understand the full plan
2. **Backend First** - Implement the 5 API endpoints
3. **Test Backend** - Verify with Postman/curl
4. **Frontend Service** - Build `insightsApi.ts`
5. **Frontend Hooks** - Build `useInsights.ts`
6. **UI Components** - Build one at a time
7. **Integration** - Wire everything together
8. **Testing** - Test with demo portfolios
9. **Deploy** - Ship Phase 1 MVP

---

**Questions or Issues?** Check:
- Backend PRD: `frontend\_docs\AI_Analytical_Reasoning_Implementation_Plan.md`
- API Reference: `frontend\_docs\API_AND_DATABASE_SUMMARY.md`
- Frontend Patterns: `frontend\_docs\requirements\README.md`
