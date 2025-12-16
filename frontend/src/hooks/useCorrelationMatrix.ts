/**
 * Hook: useCorrelationMatrix
 *
 * Fetches correlation matrix via analyticsApi.
 * Supports aggregate view (when selectedPortfolioId is null) by calling
 * the aggregate endpoint for correlations of top 25 positions across all portfolios.
 *
 * Updated for aggregate support (Dec 2025).
 */

import { useState, useEffect, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { analyticsApi } from '@/services/analyticsApi'
import type { CorrelationMatrixResponse, AggregateCorrelationMatrixResponse } from '@/types/analytics'

interface UseCorrelationMatrixParams {
  lookback_days?: number
  min_overlap?: number
  max_positions?: number  // Only used for aggregate view
}

interface UseCorrelationMatrixReturn {
  data: CorrelationMatrixResponse | null
  loading: boolean
  error: Error | null
  isAggregate: boolean
  refetch: () => Promise<void>
}

// Convert aggregate response to single-portfolio format for consistent UI
function normalizeAggregateCorrelationMatrix(response: AggregateCorrelationMatrixResponse): CorrelationMatrixResponse {
  // Build matrix record from array format
  const matrix: Record<string, Record<string, number>> = {}
  response.symbols.forEach((symbol, i) => {
    matrix[symbol] = {}
    response.symbols.forEach((otherSymbol, j) => {
      matrix[symbol][otherSymbol] = response.correlation_matrix[i]?.[j] ?? 0
    })
  })

  return {
    available: response.available,
    data: {
      matrix,
      average_correlation: response.average_correlation,
      position_symbols: response.symbols,
      correlation_matrix: response.correlation_matrix,
      data_quality: response.data_quality,
    },
    position_symbols: response.symbols,
    correlation_matrix: response.correlation_matrix,
    data_quality: response.data_quality,
    metadata: {
      calculation_date: response.calculation_date,
      lookback_days: 252,  // Default
      positions_included: response.total_positions_analyzed,
    },
  }
}

export function useCorrelationMatrix(
  params?: UseCorrelationMatrixParams
): UseCorrelationMatrixReturn {
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const isAggregateView = selectedPortfolioId === null

  const [data, setData] = useState<CorrelationMatrixResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchCorrelationMatrix = useCallback(async () => {
    // For aggregate view, we don't need a portfolioId
    // For single-portfolio view, we need the portfolioId
    if (!isAggregateView && !portfolioId) {
      console.log('🔍 Correlation Matrix: No portfolio ID available')
      setError(new Error('No portfolio ID available'))
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      if (isAggregateView) {
        // Call aggregate endpoint for top 25 positions across all portfolios
        console.log('🔍 Aggregate Correlation Matrix: Fetching')
        const response = await analyticsApi.getAggregateCorrelationMatrix({
          lookback_days: params?.lookback_days,
          max_positions: params?.max_positions ?? 25,
        })
        console.log('🔍 Aggregate Correlation Matrix: Response received', response)
        setData(normalizeAggregateCorrelationMatrix(response.data))
      } else {
        // Call single-portfolio endpoint
        console.log('🔍 Correlation Matrix: Fetching for portfolio', portfolioId)
        const response = await analyticsApi.getCorrelationMatrix(portfolioId!, {
          lookback_days: params?.lookback_days,
          min_overlap: params?.min_overlap,
        })
        console.log('🔍 Correlation Matrix: Response received', response)
        console.log('🔍 Correlation Matrix: Data structure', {
          hasData: !!response.data,
          hasSymbols: !!response.data?.position_symbols,
          hasMatrix: !!response.data?.correlation_matrix,
          symbolsCount: response.data?.position_symbols?.length,
          matrixRows: response.data?.correlation_matrix?.length
        })
        setData(response.data)
      }
    } catch (err) {
      console.error('❌ Correlation Matrix: Error fetching', err)
      setError(err as Error)
    } finally {
      setLoading(false)
    }
  }, [isAggregateView, portfolioId, params?.lookback_days, params?.min_overlap, params?.max_positions])

  useEffect(() => {
    fetchCorrelationMatrix()
  }, [fetchCorrelationMatrix])

  return {
    data,
    loading,
    error,
    isAggregate: isAggregateView,
    refetch: fetchCorrelationMatrix,
  }
}
