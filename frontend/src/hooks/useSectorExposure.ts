/**
 * Hook: useSectorExposure
 *
 * Fetches sector exposure metrics via analyticsApi.
 * Supports aggregate view (when selectedPortfolioId is null) by calling
 * the aggregate endpoint for equity-weighted averages across all portfolios.
 *
 * Updated for aggregate support (Dec 2025).
 */

import { useState, useEffect, useCallback } from 'react'
import analyticsApi from '@/services/analyticsApi'
import { usePortfolioStore } from '@/stores/portfolioStore'
import type { SectorExposureResponse, AggregateSectorExposureResponse } from '@/types/analytics'

// Convert aggregate response to single-portfolio format for consistent UI
function normalizeAggregateSectorExposure(response: AggregateSectorExposureResponse): SectorExposureResponse {
  return {
    available: true,
    portfolio_id: 'aggregate',
    calculation_date: response.calculation_date,
    data: {
      portfolio_weights: response.aggregate_portfolio_weights,
      benchmark_weights: response.benchmark_weights,
      over_underweight: response.over_underweight,
      largest_overweight: response.largest_overweight,
      largest_underweight: response.largest_underweight,
      total_portfolio_value: response.total_value,
      positions_by_sector: {}, // Not available in aggregate
      unclassified_value: 0,
      unclassified_count: 0,
    },
    metadata: {
      benchmark: 'S&P 500',
    },
  }
}

export function useSectorExposure() {
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const isAggregateView = selectedPortfolioId === null

  const [data, setData] = useState<SectorExposureResponse | null>(null)
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
        // Call aggregate endpoint for equity-weighted average across all portfolios
        const result = await analyticsApi.getAggregateSectorExposure()
        console.log('🔍 Aggregate Sector Exposure API Response:', result.data)
        setData(normalizeAggregateSectorExposure(result.data))
      } else {
        // Call single-portfolio endpoint
        const result = await analyticsApi.getSectorExposure(portfolioId!)
        console.log('🔍 Sector Exposure API Response:', result.data)
        console.log('📊 Available:', result.data?.available)
        console.log('📁 Data:', result.data?.data)
        console.log('⚠️ Metadata:', result.data?.metadata)
        setData(result.data)
      }
    } catch (err) {
      console.error('❌ Error fetching sector exposure:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch sector exposure')
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
