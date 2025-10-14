import { useState, useEffect } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { analyticsApi } from '@/services/analyticsApi'
import type { CorrelationMatrixResponse } from '@/types/analytics'

interface UseCorrelationMatrixParams {
  lookback_days?: number
  min_overlap?: number
}

interface UseCorrelationMatrixReturn {
  data: CorrelationMatrixResponse | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useCorrelationMatrix(
  params?: UseCorrelationMatrixParams
): UseCorrelationMatrixReturn {
  const { portfolioId } = usePortfolioStore()
  const [data, setData] = useState<CorrelationMatrixResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchCorrelationMatrix = async () => {
    if (!portfolioId) {
      setError(new Error('No portfolio ID available'))
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const response = await analyticsApi.getCorrelationMatrix(portfolioId, params)
      setData(response.data)
    } catch (err) {
      setError(err as Error)
      console.error('Error fetching correlation matrix:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCorrelationMatrix()
  }, [portfolioId, params?.lookback_days, params?.min_overlap])

  return {
    data,
    loading,
    error,
    refetch: fetchCorrelationMatrix,
  }
}
