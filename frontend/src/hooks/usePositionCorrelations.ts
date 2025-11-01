'use client'

import { useMemo } from 'react'
import { useResearchStore } from '@/stores/researchStore'
import { usePublicPositions } from './usePublicPositions'
import { usePrivatePositions } from './usePrivatePositions'

export interface Correlation {
  symbol: string
  correlation: number
  marketValue: number
}

export interface PositionCorrelationsResult {
  correlations: Correlation[]
  hasConcentrationRisk: boolean
  riskMessage: string | null
  loading: boolean
  error: string | null
}

/**
 * Hook for client-side correlation processing
 * Filters the correlation matrix to show top 5 correlations for a given position
 * Includes concentration risk warning logic
 *
 * NOTE: Reads from Zustand researchStore - correlation matrix is fetched once in container
 */
export function usePositionCorrelations(positionSymbol: string): PositionCorrelationsResult {
  // Read from Zustand store (single source of truth)
  const matrix = useResearchStore((state) => state.correlationMatrix)
  const matrixLoading = useResearchStore((state) => state.correlationMatrixLoading)
  const matrixError = useResearchStore((state) => state.correlationMatrixError)

  // Get all positions to map symbols to market values
  const { longPositions, shortPositions, loading: publicLoading } = usePublicPositions()
  const { positions: privatePositions, loading: privateLoading } = usePrivatePositions()
  const positionsLoading = publicLoading || privateLoading

  const result = useMemo(() => {
    console.log('🔍 Position Correlations: Processing for symbol', positionSymbol)
    console.log('🔍 Position Correlations: Matrix data', {
      hasMatrix: !!matrix,
      positionsLoading,
      matrixSymbols: matrix?.position_symbols?.length
    })

    // Return loading state if data not yet available
    if (!matrix || positionsLoading) {
      console.log('🔍 Position Correlations: Still loading data')
      return {
        correlations: [],
        hasConcentrationRisk: false,
        riskMessage: null,
        loading: true,
        error: null
      }
    }

    // Check if matrix has the required data structure
    if (!matrix.position_symbols || !matrix.correlation_matrix) {
      console.log('❌ Position Correlations: Matrix missing required fields', {
        hasSymbols: !!matrix.position_symbols,
        hasMatrix: !!matrix.correlation_matrix
      })
      return {
        correlations: [],
        hasConcentrationRisk: false,
        riskMessage: 'Correlation data not available',
        loading: false,
        error: null
      }
    }

    // Build position lookup map for market values
    const allPositions = [
      ...longPositions,
      ...shortPositions,
      ...privatePositions
    ]

    const positionMap = new Map(
      allPositions.map((p: any) => [
        p.symbol,
        Math.abs(p.current_market_value || p.marketValue || 0)
      ])
    )

    // Find index of selected position in matrix
    const symbolIndex = matrix.position_symbols.indexOf(positionSymbol)
    if (symbolIndex === -1) {
      console.log('❌ Position Correlations: Symbol not found in matrix', {
        symbol: positionSymbol,
        availableSymbols: matrix.position_symbols
      })
      return {
        correlations: [],
        hasConcentrationRisk: false,
        riskMessage: 'Position not found in correlation matrix',
        loading: false,
        error: null
      }
    }

    // Extract correlations for this position
    const positionCorrelations = matrix.position_symbols
      .map((symbol, index) => ({
        symbol,
        correlation: matrix.correlation_matrix[symbolIndex][index],
        marketValue: positionMap.get(symbol) || 0
      }))
      .filter(c => c.symbol !== positionSymbol) // Exclude self (correlation = 1.0)
      .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation)) // Sort by strength
      .slice(0, 3) // Top 3 only (as per spec)

    // Calculate concentration risk
    const highCorrelations = positionCorrelations.filter(
      c => Math.abs(c.correlation) > 0.7
    )

    const moderateCorrelations = positionCorrelations.filter(
      c => Math.abs(c.correlation) > 0.6 && Math.abs(c.correlation) <= 0.7
    )

    const hasConcentrationRisk =
      highCorrelations.length >= 2 ||
      moderateCorrelations.length >= 3

    let riskMessage: string | null = null
    if (hasConcentrationRisk) {
      if (highCorrelations.length >= 2) {
        riskMessage = `High correlation with ${highCorrelations.length} other positions reduces diversification benefits.`
      } else if (moderateCorrelations.length >= 3) {
        riskMessage = `Moderate correlation with ${moderateCorrelations.length} positions may reduce portfolio diversification.`
      }
    }

    console.log('✅ Position Correlations: Successfully calculated', {
      symbol: positionSymbol,
      correlationsCount: positionCorrelations.length,
      hasConcentrationRisk,
      highCorrelations: highCorrelations.length,
      moderateCorrelations: moderateCorrelations.length
    })

    return {
      correlations: positionCorrelations,
      hasConcentrationRisk,
      riskMessage,
      loading: false,
      error: null
    }
  }, [matrix, positionsLoading, positionSymbol, longPositions, shortPositions, privatePositions])

  return {
    ...result,
    loading: matrixLoading || result.loading,
    error: matrixError || result.error || null
  }
}

/**
 * Helper function to get correlation strength label
 */
export function getCorrelationStrength(correlation: number): string {
  const abs = Math.abs(correlation)
  if (abs > 0.85) return 'very high'
  if (abs > 0.7) return 'high'
  if (abs > 0.5) return 'moderate'
  return 'low'
}
