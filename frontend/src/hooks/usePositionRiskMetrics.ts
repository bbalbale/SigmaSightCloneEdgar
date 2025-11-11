'use client'

import { useState, useEffect } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { positionRiskService, type PositionRiskMetrics } from '@/services/positionRiskService'

export interface UsePositionRiskMetricsResult {
  metrics: PositionRiskMetrics | null
  loading: boolean
  error: string | null
}

/**
 * Hook to fetch complete risk metrics for a position
 * Combines data from:
 * - position_factor_exposures table (Market Beta, Growth, Momentum, etc.)
 * - company_profiles table (sector, industry)
 * - calculations (volatility)
 */
export function usePositionRiskMetrics(
  positionId: string,
  symbol: string
): UsePositionRiskMetricsResult {
  const { portfolioId } = usePortfolioStore()
  const [metrics, setMetrics] = useState<PositionRiskMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMetrics = async () => {
      if (!portfolioId || !positionId || !symbol) {
        console.log('🔍 Position Risk Metrics: Missing required params', { portfolioId, positionId, symbol })
        setLoading(false)
        return
      }

      try {
        console.log('🔍 Position Risk Metrics: Fetching for', { symbol, positionId })
        setLoading(true)
        setError(null)

        const metricsData = await positionRiskService.getPositionRiskMetrics(
          portfolioId,
          positionId,
          symbol
        )

        console.log('✅ Position Risk Metrics: Received', metricsData)
        setMetrics(metricsData)
      } catch (err) {
        console.error('❌ Position Risk Metrics: Error', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch risk metrics')
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
  }, [portfolioId, positionId, symbol])

  return {
    metrics,
    loading,
    error
  }
}
