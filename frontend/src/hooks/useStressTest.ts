import { useState, useEffect } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { analyticsApi } from '@/services/analyticsApi'
import type { StressTestResponse } from '@/types/analytics'

interface UseStressTestParams {
  scenarios?: string
}

interface UseStressTestReturn {
  data: StressTestResponse | null
  loading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

export function useStressTest(
  params?: UseStressTestParams
): UseStressTestReturn {
  const { portfolioId } = usePortfolioStore()
  const [data, setData] = useState<StressTestResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchStressTest = async () => {
    if (!portfolioId) {
      setError(new Error('No portfolio ID available'))
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      const response = await analyticsApi.getStressTest(portfolioId, params)
      setData(response.data)
    } catch (err) {
      setError(err as Error)
      console.error('Error fetching stress test:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStressTest()
  }, [portfolioId, params?.scenarios])

  return {
    data,
    loading,
    error,
    refetch: fetchStressTest,
  }
}
