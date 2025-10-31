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
    console.log('🔍 handleGenerateInsight called', { portfolioId, generatingInsight })

    if (!portfolioId) {
      console.error('❌ No portfolio ID')
      return
    }

    if (generatingInsight) {
      console.warn('⚠️ Already generating insight, skipping')
      return
    }

    console.log('✅ Starting insight generation...')
    setGeneratingInsight(true)
    setError(null)

    try {
      console.log('📡 Calling API...')
      const newInsight = await insightsApi.generateInsight({
        portfolio_id: portfolioId,
        insight_type: 'daily_summary'
      })

      console.log('✅ Insight generated:', newInsight.id)

      // FIX: Only add if not already in list (prevent duplicates)
      setInsights(prev => {
        // Check if this insight already exists
        const exists = prev.some(i => i.id === newInsight.id)
        if (exists) {
          console.warn('⚠️ Insight already in list, skipping duplicate')
          return prev
        }
        console.log('📝 Adding new insight to list')
        return [newInsight, ...prev]
      })
    } catch (err: any) {
      console.error('❌ Failed to generate insight:', err)
      setError(err.message || 'Failed to generate insight')
    } finally {
      console.log('🏁 Finished (setting generatingInsight = false)')
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
