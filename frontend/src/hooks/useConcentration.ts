/**
 * Hook: useConcentration
 *
 * Fetches concentration metrics (HHI, top position weights) via analyticsApi.
 * Supports aggregate view (when selectedPortfolioId is null) by calling
 * the aggregate endpoint for concentration metrics across all portfolios.
 *
 * Updated for aggregate support (Dec 2025).
 */

import { useState, useEffect, useCallback } from 'react'
import analyticsApi from '@/services/analyticsApi'
import { usePortfolioStore } from '@/stores/portfolioStore'
import type { ConcentrationMetricsResponse, AggregateConcentrationResponse } from '@/types/analytics'

// Convert aggregate response to single-portfolio format for consistent UI
function normalizeAggregateConcentration(response: AggregateConcentrationResponse): ConcentrationMetricsResponse {
  // Build position weights from top positions
  const position_weights: Record<string, number> = {}
  response.top_positions.forEach(p => {
    position_weights[p.symbol] = p.weight
  })

  return {
    available: true,
    portfolio_id: 'aggregate',
    calculation_date: response.calculation_date,
    data: {
      hhi: response.aggregate_hhi,
      effective_num_positions: response.aggregate_effective_num_positions,
      top_3_concentration: response.aggregate_top_3_concentration,
      top_10_concentration: response.aggregate_top_10_concentration,
      total_positions: response.total_positions,
      position_weights,
    },
    metadata: {
      calculation_method: 'equity_weighted_aggregate',
      interpretation: response.aggregate_hhi < 1500
        ? 'Diversified (HHI < 1500)'
        : response.aggregate_hhi < 2500
          ? 'Moderately Concentrated (HHI 1500-2500)'
          : 'Highly Concentrated (HHI > 2500)',
    },
  }
}

export function useConcentration() {
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const isAggregateView = selectedPortfolioId === null

  const [data, setData] = useState<ConcentrationMetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    // For aggregate view, we don't need a portfolioId
    // For single-portfolio view, we need the portfolioId
    if (!isAggregateView && !portfolioId) {
      setError('No portfolio ID available')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      if (isAggregateView) {
        // Call aggregate endpoint for concentration across all portfolios
        const result = await analyticsApi.getAggregateConcentration()
        setData(normalizeAggregateConcentration(result.data))
      } else {
        // Call single-portfolio endpoint
        const result = await analyticsApi.getConcentration(portfolioId!)
        setData(result.data)
      }
    } catch (err) {
      console.error('Error fetching concentration metrics:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch concentration metrics')
    } finally {
      setLoading(false)
    }
  }, [isAggregateView, portfolioId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return {
    data,
    loading,
    error,
    isAggregate: isAggregateView,
    refetch: fetchData,
  }
}
