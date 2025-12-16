/**
 * Hook: useStressTest
 *
 * Fetches stress test scenarios via analyticsApi.
 * Supports aggregate view (when selectedPortfolioId is null) by calling
 * the aggregate endpoint for equity-weighted stress test impacts across all portfolios.
 *
 * Updated for aggregate support (Dec 2025).
 */

import { useState, useEffect, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { analyticsApi } from '@/services/analyticsApi'
import type { StressTestResponse, AggregateStressTestResponse } from '@/types/analytics'

interface UseStressTestParams {
  scenarios?: string
}

interface UseStressTestReturn {
  data: StressTestResponse | null
  loading: boolean
  error: Error | null
  isAggregate: boolean
  refetch: () => Promise<void>
}

// Convert aggregate response to single-portfolio format for consistent UI
function normalizeAggregateStressTest(response: AggregateStressTestResponse): StressTestResponse {
  // Backend returns scenarios nested in data.scenarios
  const scenarios = response.data?.scenarios || []
  const portfolioValue = response.data?.portfolio_value || response.net_asset_value || 0

  return {
    available: response.available,
    data: {
      scenarios: scenarios.map(s => ({
        id: s.id,
        name: s.name,
        description: s.description,
        category: s.category,
        impact: s.impact,
      })),
      portfolio_value: portfolioValue,
      calculation_date: new Date().toISOString(),
    },
    metadata: {
      scenarios_requested: scenarios.map(s => s.id),
    },
  }
}

export function useStressTest(
  params?: UseStressTestParams
): UseStressTestReturn {
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const isAggregateView = selectedPortfolioId === null

  const [data, setData] = useState<StressTestResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchStressTest = useCallback(async () => {
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
        // Call aggregate endpoint for equity-weighted stress test impacts
        const response = await analyticsApi.getAggregateStressTest()
        setData(normalizeAggregateStressTest(response.data))
      } else {
        // Call single-portfolio endpoint
        const response = await analyticsApi.getStressTest(portfolioId!, params)
        setData(response.data)
      }
    } catch (err) {
      setError(err as Error)
      console.error('Error fetching stress test:', err)
    } finally {
      setLoading(false)
    }
  }, [isAggregateView, portfolioId, params?.scenarios])

  useEffect(() => {
    fetchStressTest()
  }, [fetchStressTest])

  return {
    data,
    loading,
    error,
    isAggregate: isAggregateView,
    refetch: fetchStressTest,
  }
}
