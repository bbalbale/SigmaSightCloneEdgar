// src/hooks/usePublicPositions.ts
'use client'

import { useState, useEffect, useMemo } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import {
  positionResearchService,
  type EnhancedPosition
} from '@/services/positionResearchService'

interface UsePublicPositionsReturn {
  longPositions: EnhancedPosition[]
  shortPositions: EnhancedPosition[]
  loading: boolean
  error: string | null
  aggregateReturns: {
    longs_eoy: number
    longs_next_year: number
    shorts_eoy: number
    shorts_next_year: number
  }
  refetch: () => Promise<void>
}

export function usePublicPositions(): UsePublicPositionsReturn {
  const { portfolioId } = usePortfolioStore()
  const [longPositions, setLongPositions] = useState<EnhancedPosition[]>([])
  const [shortPositions, setShortPositions] = useState<EnhancedPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    if (!portfolioId) return

    setLoading(true)
    setError(null)

    try {
      // Use service to fetch and merge all data
      // Don't filter by investment class - we want both PUBLIC and OPTIONS
      const result = await positionResearchService.fetchEnhancedPositions({
        portfolioId
      })

      setLongPositions(result.longPositions)
      setShortPositions(result.shortPositions)
    } catch (err) {
      console.error('Failed to fetch positions:', err)
      setError('Failed to load positions data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (portfolioId) {
      fetchData()
    }
  }, [portfolioId])

  // Calculate aggregate returns using service method
  // EOY returns use analyst targets as fallback when user hasn't entered targets
  const aggregateReturns = useMemo(() => ({
    longs_eoy: positionResearchService.calculateAggregateReturn(
      longPositions,
      'target_return_eoy',
      'analyst_return_eoy' // Fallback to analyst if user target is null
    ),
    longs_next_year: positionResearchService.calculateAggregateReturn(
      longPositions,
      'target_return_next_year'
      // No fallback - analyst data doesn't include next year
    ),
    shorts_eoy: positionResearchService.calculateAggregateReturn(
      shortPositions,
      'target_return_eoy',
      'analyst_return_eoy' // Fallback to analyst if user target is null
    ),
    shorts_next_year: positionResearchService.calculateAggregateReturn(
      shortPositions,
      'target_return_next_year'
      // No fallback - analyst data doesn't include next year
    )
  }), [longPositions, shortPositions])

  return {
    longPositions,
    shortPositions,
    loading,
    error,
    aggregateReturns,
    refetch: fetchData
  }
}
