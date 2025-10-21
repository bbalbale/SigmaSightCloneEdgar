import { useState, useEffect, useCallback } from 'react'
import analyticsApi from '@/services/analyticsApi'
import { usePortfolioStore } from '@/stores/portfolioStore'
import type { SectorExposureResponse } from '@/types/analytics'

export function useSectorExposure() {
  const { portfolioId } = usePortfolioStore()
  const [data, setData] = useState<SectorExposureResponse | null>(null)
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
      const result = await analyticsApi.getSectorExposure(portfolioId)
      console.log('🔍 Sector Exposure API Response:', result.data)
      console.log('📊 Available:', result.data?.available)
      console.log('📁 Data:', result.data?.data)
      console.log('⚠️ Metadata:', result.data?.metadata)
      setData(result.data)
    } catch (err) {
      console.error('❌ Error fetching sector exposure:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch sector exposure')
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
