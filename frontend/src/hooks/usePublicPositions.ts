// src/hooks/usePublicPositions.ts
'use client'

import { useState, useEffect, useMemo } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import {
  positionResearchService,
  type EnhancedPosition
} from '@/services/positionResearchService'
import {
  fetchPortfolioSnapshot,
  type PortfolioSnapshot
} from '@/services/portfolioService'

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
  portfolioSnapshot: PortfolioSnapshot | null
  refetch: () => Promise<void>
}

export function usePublicPositions(): UsePublicPositionsReturn {
  const { portfolioId } = usePortfolioStore()
  const [longPositions, setLongPositions] = useState<EnhancedPosition[]>([])
  const [shortPositions, setShortPositions] = useState<EnhancedPosition[]>([])
  const [portfolioSnapshot, setPortfolioSnapshot] = useState<PortfolioSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    if (!portfolioId) return

    setLoading(true)
    setError(null)

    try {
      // Fetch both positions and snapshot in parallel
      const [positionsResult, snapshotData] = await Promise.all([
        positionResearchService.fetchEnhancedPositions({ portfolioId }),
        fetchPortfolioSnapshot(portfolioId)
      ])

      // Filter to only show PUBLIC and OPTIONS positions
      const filteredLongPositions = positionsResult.longPositions.filter(
        p => p.investment_class === 'PUBLIC' || p.investment_class === 'OPTIONS'
      )
      const filteredShortPositions = positionsResult.shortPositions.filter(
        p => p.investment_class === 'PUBLIC' || p.investment_class === 'OPTIONS'
      )

      setLongPositions(filteredLongPositions)
      setShortPositions(filteredShortPositions)
      setPortfolioSnapshot(snapshotData)
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
    portfolioSnapshot,
    refetch: fetchData
  }
}
