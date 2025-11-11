import { useState, useEffect } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { analyticsApi } from '@/services/analyticsApi'
import type { VolatilityMetricsResponse } from '@/types/analytics'

interface UseVolatilityReturn {
  data: VolatilityMetricsResponse | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useVolatility(): UseVolatilityReturn {
  const { portfolioId } = usePortfolioStore()
  const [data, setData] = useState<VolatilityMetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchVolatility = async () => {
    if (!portfolioId) {
      setError(new Error('No portfolio ID available'))
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const response = await analyticsApi.getVolatility(portfolioId)
      setData(response.data)
    } catch (err) {
      setError(err as Error)
      console.error('Error fetching volatility metrics:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchVolatility()
  }, [portfolioId])

  return {
    data,
    loading,
    error,
    refetch: fetchVolatility,
  }
}
