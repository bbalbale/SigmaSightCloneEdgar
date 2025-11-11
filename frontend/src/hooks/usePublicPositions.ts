// src/hooks/usePublicPositions.ts
'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import {
  positionResearchService,
  type EnhancedPosition
} from '@/services/positionResearchService'
import {
  fetchPortfolioSnapshot,
  type PortfolioSnapshot
} from '@/services/portfolioService'
import targetPriceUpdateService, {
  type TargetPriceUpdate
} from '@/services/targetPriceUpdateService'

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
  updatePositionTargetOptimistic: (update: TargetPriceUpdate) => Promise<void>
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

  // Optimistic update for target prices - instant UI feedback
  const updatePositionTargetOptimistic = useCallback(async (update: TargetPriceUpdate) => {
    if (!portfolioId) return

    // Combine all positions for optimistic update
    const allPositions = [...longPositions, ...shortPositions]

    // Update positions optimistically
    const handleOptimisticUpdate = (updatedPositions: EnhancedPosition[]) => {
      // Split back into longs and shorts
      const updatedLongs = updatedPositions.filter(
        p => p.investment_class === 'PUBLIC' || p.investment_class === 'OPTIONS'
      ).filter(
        p => p.position_type === 'LONG' || p.position_type === 'LC' || p.position_type === 'LP'
      )
      const updatedShorts = updatedPositions.filter(
        p => p.investment_class === 'PUBLIC' || p.investment_class === 'OPTIONS'
      ).filter(
        p => p.position_type === 'SHORT' || p.position_type === 'SC' || p.position_type === 'SP'
      )

      setLongPositions(updatedLongs)
      setShortPositions(updatedShorts)
    }

    // Use optimistic update service
    await targetPriceUpdateService.updatePositionTarget(
      portfolioId,
      update,
      allPositions,
      handleOptimisticUpdate,
      (error, previousState) => {
        console.error('Failed to sync target price, reverted:', error)
        setError(`Failed to update target price for ${update.symbol}`)
        // Error handling - state already reverted by service
      }
    )
  }, [portfolioId, longPositions, shortPositions])

  return {
    longPositions,
    shortPositions,
    loading,
    error,
    aggregateReturns,
    portfolioSnapshot,
    refetch: fetchData,
    updatePositionTargetOptimistic
  }
}
