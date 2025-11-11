/**
 * AI Insights Custom Hooks
 *
 * Custom React hooks for managing AI insights state and operations.
 *
 * Pattern: Follows useTags.ts and usePortfolioData.ts patterns
 * State Management: Uses useState (no React Query)
 * Portfolio ID: From existing portfolioStore (Zustand)
 *
 * Hooks:
 * - useInsights: Fetch and manage insights list
 * - useInsightDetail: Fetch single insight detail
 * - useGenerateInsight: Generate new insight with loading state
 * - useInsightFeedback: Submit feedback/rating
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import insightsApi, { AIInsight, InsightType } from '@/services/insightsApi'

// ============================================================================
// useInsights - List insights for portfolio
// ============================================================================

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
 *
 * @param options - Optional filters (insightType, daysBack, limit, autoRefresh)
 * @returns Insights array, loading state, error, pagination info, refresh function
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

// ============================================================================
// useInsightDetail - Fetch single insight
// ============================================================================

interface UseInsightDetailReturn {
  insight: AIInsight | null
  loading: boolean
  error: Error | null
}

/**
 * Hook to fetch a single insight detail
 *
 * Note: This automatically marks the insight as viewed on the backend
 *
 * @param insightId - Insight UUID to fetch (null to skip fetching)
 * @returns Insight data, loading state, error
 */
export function useInsightDetail(insightId: string | null): UseInsightDetailReturn {
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

// ============================================================================
// useGenerateInsight - Generate new insight
// ============================================================================

interface UseGenerateInsightReturn {
  generate: (
    insightType: InsightType,
    focusArea?: string,
    userQuestion?: string
  ) => Promise<AIInsight | null>
  generating: boolean
  error: Error | null
}

/**
 * Hook to generate a new insight
 *
 * Cost: ~$0.02 per generation, Time: 25-30 seconds
 * Rate limit: Max 10 per portfolio per day
 *
 * @returns generate function, generating state, error
 */
export function useGenerateInsight(): UseGenerateInsightReturn {
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

// ============================================================================
// useInsightFeedback - Submit feedback/rating
// ============================================================================

interface UseInsightFeedbackReturn {
  submitFeedback: (
    insightId: string,
    rating: number,
    feedback?: string
  ) => Promise<void>
  submitting: boolean
  error: Error | null
}

/**
 * Hook to submit feedback for an insight
 *
 * @returns submitFeedback function, submitting state, error
 */
export function useInsightFeedback(): UseInsightFeedbackReturn {
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

// ============================================================================
// useUpdateInsight - Update insight metadata
// ============================================================================

interface UseUpdateInsightReturn {
  updateInsight: (
    insightId: string,
    updates: { viewed?: boolean; dismissed?: boolean }
  ) => Promise<AIInsight | null>
  updating: boolean
  error: Error | null
}

/**
 * Hook to update insight metadata (viewed, dismissed flags)
 *
 * @returns updateInsight function, updating state, error
 */
export function useUpdateInsight(): UseUpdateInsightReturn {
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const updateInsight = useCallback(async (
    insightId: string,
    updates: { viewed?: boolean; dismissed?: boolean }
  ): Promise<AIInsight | null> => {
    setUpdating(true)
    setError(null)

    try {
      const insight = await insightsApi.updateInsight(insightId, updates)
      return insight
    } catch (err) {
      console.error('Failed to update insight:', err)
      const error = err instanceof Error ? err : new Error('Failed to update insight')
      setError(error)
      throw error
    } finally {
      setUpdating(false)
    }
  }, [])

  return {
    updateInsight,
    updating,
    error,
  }
}
