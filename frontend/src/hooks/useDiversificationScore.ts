import { useState, useEffect } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { analyticsApi } from '@/services/analyticsApi'
import type { DiversificationScoreResponse } from '@/types/analytics'

interface UseDiversificationScoreReturn {
  data: DiversificationScoreResponse | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useDiversificationScore(): UseDiversificationScoreReturn {
  const { portfolioId } = usePortfolioStore()
  const [data, setData] = useState<DiversificationScoreResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchDiversificationScore = async () => {
    if (!portfolioId) {
      setError(new Error('No portfolio ID available'))
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const response = await analyticsApi.getDiversificationScore(portfolioId)
      setData(response.data)
    } catch (err) {
      setError(err as Error)
      console.error('Error fetching diversification score:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDiversificationScore()
  }, [portfolioId])

  return {
    data,
    loading,
    error,
    refetch: fetchDiversificationScore,
  }
}
