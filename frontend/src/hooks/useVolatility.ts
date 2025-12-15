/**
 * Hook: useVolatility
 *
 * Fetches volatility metrics via analyticsApi.
 * Supports aggregate view (when selectedPortfolioId is null) by calling
 * the aggregate endpoint for equity-weighted averages across all portfolios.
 *
 * Updated for aggregate support (Dec 2025).
 */

import { useState, useEffect, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { analyticsApi } from '@/services/analyticsApi'
import type { VolatilityMetricsResponse, AggregateVolatilityResponse } from '@/types/analytics'

interface UseVolatilityReturn {
  data: VolatilityMetricsResponse | null
  loading: boolean
  error: Error | null
  isAggregate: boolean
  refetch: () => Promise<void>
}

// Convert aggregate response to single-portfolio format for consistent UI
function normalizeAggregateVolatility(response: AggregateVolatilityResponse): VolatilityMetricsResponse {
  return {
    available: true,
    portfolio_id: 'aggregate',
    calculation_date: response.calculation_date,
    data: {
      realized_volatility_21d: response.aggregate_volatility_21d,
      realized_volatility_63d: response.aggregate_volatility_63d,
      expected_volatility_21d: response.aggregate_expected_volatility_21d,
      volatility_trend: null,
      volatility_percentile: null,
    },
    metadata: {
      forecast_model: 'equity_weighted_aggregate',
      trading_day_windows: '21d, 63d',
    },
  }
}

export function useVolatility(): UseVolatilityReturn {
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const isAggregateView = selectedPortfolioId === null

  const [data, setData] = useState<VolatilityMetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchVolatility = useCallback(async () => {
    // For aggregate view, we don't need a portfolioId
    // For single-portfolio view, we need the portfolioId
    if (!isAggregateView && !portfolioId) {
      setError(new Error('No portfolio ID available'))
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      if (isAggregateView) {
        // Call aggregate endpoint for equity-weighted average across all portfolios
        const response = await analyticsApi.getAggregateVolatility()
        setData(normalizeAggregateVolatility(response.data))
      } else {
        // Call single-portfolio endpoint
        const response = await analyticsApi.getVolatility(portfolioId!)
        setData(response.data)
      }
    } catch (err) {
      setError(err as Error)
      console.error('Error fetching volatility metrics:', err)
    } finally {
      setLoading(false)
    }
  }, [isAggregateView, portfolioId])

  useEffect(() => {
    fetchVolatility()
  }, [fetchVolatility])

  return {
    data,
    loading,
    error,
    isAggregate: isAggregateView,
    refetch: fetchVolatility,
  }
}
