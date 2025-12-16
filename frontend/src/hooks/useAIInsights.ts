import { useState, useEffect, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import insightsApi, { AIInsight, InsightType } from '@/services/insightsApi'

interface UseAIInsightsReturn {
  insights: AIInsight[]
  loading: boolean
  loadingMore: boolean
  error: string | null
  generatingInsight: boolean
  hasMore: boolean
  total: number
  filters: {
    insightType?: InsightType
    daysBack: number
    limit: number
  }
  handleGenerateInsight: (options?: { insightType?: InsightType, focusArea?: string, userQuestion?: string }) => Promise<void>
  handleDismissInsight: (insightId: string) => Promise<void>
  handleFeedback: (insightId: string, rating: number, feedback?: string) => Promise<void>
  loadMore: () => Promise<void>
  updateFilters: (next: Partial<{ insightType?: InsightType, daysBack: number, limit: number }>) => void
  refetchInsights: () => Promise<void>
}

export function useAIInsights(): UseAIInsightsReturn {
  const { portfolioId } = usePortfolioStore()

  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [generatingInsight, setGeneratingInsight] = useState(false)
  const [insights, setInsights] = useState<AIInsight[]>([])
  const [filters, setFilters] = useState<{ insightType?: InsightType, daysBack: number, limit: number }>({
    insightType: 'daily_summary',
    daysBack: 30,
    limit: 10
  })
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)

  // Fetch insights
  const fetchInsights = useCallback(async ({ append = false, nextOffset }: { append?: boolean, nextOffset?: number } = {}) => {
    if (!portfolioId) {
      setLoading(false)
      setLoadingMore(false)
      return
    }

    const targetOffset = typeof nextOffset === 'number'
      ? nextOffset
      : append
        ? offset + filters.limit
        : 0

    if (append) {
      setLoadingMore(true)
    } else {
      setLoading(true)
    }
    setError(null)

    try {
      const insightsData = await insightsApi.listInsights(portfolioId, {
        insightType: filters.insightType,
        daysBack: filters.daysBack,
        limit: filters.limit,
        offset: targetOffset
      })

      setOffset(targetOffset)
      setHasMore(Boolean(insightsData.has_more))
      setTotal(insightsData.total || 0)

      setInsights(prev => {
        const incoming = insightsData.insights || []
        if (!append) {
          return incoming
        }
        const existingIds = new Set(prev.map(i => i.id))
        const merged = [...prev]
        for (const insight of incoming) {
          if (!existingIds.has(insight.id)) {
            merged.push(insight)
            existingIds.add(insight.id)
          }
        }
        return merged
      })
    } catch (err: any) {
      console.error('Failed to load AI insights:', err)
      setError(err.message || 'Failed to load insights')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [portfolioId, filters.insightType, filters.daysBack, filters.limit, offset])

  // Initial load
  useEffect(() => {
    fetchInsights({ append: false, nextOffset: 0 })
  }, [fetchInsights])

  // Generate new insight
  const handleGenerateInsight = useCallback(async (
    options?: { insightType?: InsightType, focusArea?: string, userQuestion?: string }
  ) => {
    console.log('🔍 handleGenerateInsight called', { portfolioId, generatingInsight })

    if (!portfolioId) {
      console.error('❌ No portfolio ID')
      return
    }

    if (generatingInsight) {
      console.warn('⚠️ Already generating insight, skipping')
      return
    }

    const insightType = options?.insightType || filters.insightType || 'daily_summary'

    console.log('✅ Starting insight generation...', { insightType })
    setGeneratingInsight(true)
    setError(null)

    try {
      console.log('📡 Calling API...')
      const newInsight = await insightsApi.generateInsight({
        portfolio_id: portfolioId,
        insight_type: insightType,
        focus_area: options?.focusArea,
        user_question: options?.userQuestion
      })

      console.log('✅ Insight generated:', newInsight.id)

      setInsights(prev => {
        const exists = prev.some(i => i.id === newInsight.id)
        if (exists) {
          console.warn('⚠️ Insight already in list, skipping duplicate')
          return prev
        }
        console.log('📝 Adding new insight to list')
        return [newInsight, ...prev]
      })
      setTotal(prev => prev + 1)
    } catch (err: any) {
      console.error('❌ Failed to generate insight:', err)
      setError(err.message || 'Failed to generate insight')
    } finally {
      console.log('🏁 Finished (setting generatingInsight = false)')
      setGeneratingInsight(false)
    }
  }, [portfolioId, generatingInsight, filters.insightType])

  // Dismiss insight
  const handleDismissInsight = useCallback(async (insightId: string) => {
    try {
      await insightsApi.updateInsight(insightId, { dismissed: true })

      // Update local state
      setInsights(prev =>
        prev.map(i => i.id === insightId ? { ...i, dismissed: true } : i)
      )
    } catch (err: any) {
      console.error('Failed to dismiss insight:', err)
    }
  }, [])

  // Submit feedback (rating only for now)
  const handleFeedback = useCallback(async (insightId: string, rating: number, feedback?: string) => {
    try {
      await insightsApi.submitFeedback(insightId, { rating, feedback })

      setInsights(prev => prev.map(insight =>
        insight.id === insightId
          ? { ...insight, user_rating: rating, user_feedback: feedback ?? insight.user_feedback }
          : insight
      ))
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }
  }, [])

  // Manual refetch
  const refetchInsights = useCallback(async () => {
    await fetchInsights({ append: false, nextOffset: 0 })
  }, [fetchInsights])

  const loadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return
    await fetchInsights({ append: true, nextOffset: offset + filters.limit })
  }, [fetchInsights, loading, loadingMore, hasMore, offset, filters.limit])

  const updateFilters = useCallback((next: Partial<{ insightType?: InsightType, daysBack: number, limit: number }>) => {
    setFilters(prev => ({ ...prev, ...next }))
    setOffset(0)
  }, [])

  return {
    insights,
    loading,
    loadingMore,
    error,
    generatingInsight,
    hasMore,
    total,
    filters,
    handleGenerateInsight,
    handleDismissInsight,
    loadMore,
    updateFilters,
    handleFeedback,
    refetchInsights
  }
}
