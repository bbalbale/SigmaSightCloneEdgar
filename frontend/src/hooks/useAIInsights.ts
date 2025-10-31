import { useState, useEffect, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import insightsApi, { AIInsight } from '@/services/insightsApi'

interface UseAIInsightsReturn {
  insights: AIInsight[]
  loading: boolean
  error: string | null
  generatingInsight: boolean
  handleGenerateInsight: () => Promise<void>
  handleDismissInsight: (insightId: string) => Promise<void>
  refetchInsights: () => Promise<void>
}

export function useAIInsights(): UseAIInsightsReturn {
  const { portfolioId } = usePortfolioStore()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generatingInsight, setGeneratingInsight] = useState(false)
  const [insights, setInsights] = useState<AIInsight[]>([])

  // Fetch insights
  const fetchInsights = useCallback(async () => {
    if (!portfolioId) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const insightsData = await insightsApi.listInsights(portfolioId, {
        daysBack: 30, // Show last 30 days on dedicated page
        limit: 20     // Show more insights on dedicated page
      })

      setInsights(insightsData.insights || [])
      setLoading(false)
    } catch (err: any) {
      console.error('Failed to load AI insights:', err)
      setError(err.message || 'Failed to load insights')
      setLoading(false)
    }
  }, [portfolioId])

  // Initial load
  useEffect(() => {
    fetchInsights()
  }, [fetchInsights])

  // Generate new insight
  const handleGenerateInsight = useCallback(async () => {
    if (!portfolioId || generatingInsight) return

    setGeneratingInsight(true)
    setError(null)

    try {
      const newInsight = await insightsApi.generateInsight({
        portfolio_id: portfolioId,
        insight_type: 'daily_summary'
      })

      // Add to insights list at the beginning
      setInsights(prev => [newInsight, ...prev])
    } catch (err: any) {
      console.error('Failed to generate insight:', err)
      setError(err.message || 'Failed to generate insight')
    } finally {
      setGeneratingInsight(false)
    }
  }, [portfolioId, generatingInsight])

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

  // Manual refetch
  const refetchInsights = useCallback(async () => {
    await fetchInsights()
  }, [fetchInsights])

  return {
    insights,
    loading,
    error,
    generatingInsight,
    handleGenerateInsight,
    handleDismissInsight,
    refetchInsights
  }
}
