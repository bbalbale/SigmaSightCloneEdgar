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
      console.log('🔍 Correlation Matrix: No portfolio ID available')
      setError(new Error('No portfolio ID available'))
      setLoading(false)
      return
    }

    try {
      console.log('🔍 Correlation Matrix: Fetching for portfolio', portfolioId)
      setLoading(true)
      setError(null)

      const response = await analyticsApi.getCorrelationMatrix(portfolioId, params)
      console.log('🔍 Correlation Matrix: Response received', response)
      console.log('🔍 Correlation Matrix: Data structure', {
        hasData: !!response.data,
        hasSymbols: !!response.data?.position_symbols,
        hasMatrix: !!response.data?.correlation_matrix,
        symbolsCount: response.data?.position_symbols?.length,
        matrixRows: response.data?.correlation_matrix?.length
      })
      setData(response.data)
    } catch (err) {
      console.error('❌ Correlation Matrix: Error fetching', err)
      setError(err as Error)
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
