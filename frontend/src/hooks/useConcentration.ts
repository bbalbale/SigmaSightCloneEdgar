import { useState, useEffect, useCallback } from 'react'
import analyticsApi from '@/services/analyticsApi'
import { usePortfolioStore } from '@/stores/portfolioStore'
import type { ConcentrationMetricsResponse } from '@/types/analytics'

export function useConcentration() {
  const { portfolioId } = usePortfolioStore()
  const [data, setData] = useState<ConcentrationMetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    if (!portfolioId) {
      setError('No portfolio ID available')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const result = await analyticsApi.getConcentration(portfolioId)
      setData(result.data)
    } catch (err) {
      console.error('Error fetching concentration metrics:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch concentration metrics')
    } finally {
      setLoading(false)
    }
  }, [portfolioId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  }
}
