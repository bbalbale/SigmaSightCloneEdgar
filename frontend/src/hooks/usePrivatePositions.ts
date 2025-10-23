// src/hooks/usePrivatePositions.ts
'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import {
  positionResearchService,
  type EnhancedPosition
} from '@/services/positionResearchService'
import targetPriceUpdateService, {
  type TargetPriceUpdate
} from '@/services/targetPriceUpdateService'

interface UsePrivatePositionsReturn {
  positions: EnhancedPosition[]
  loading: boolean
  error: string | null
  aggregateReturns: {
    eoy: number
    next_year: number
  }
  refetch: () => Promise<void>
  updatePositionTargetOptimistic: (update: TargetPriceUpdate) => Promise<void>
}

export function usePrivatePositions(): UsePrivatePositionsReturn {
  const { portfolioId } = usePortfolioStore()
  const [positions, setPositions] = useState<EnhancedPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    if (!portfolioId) return

    setLoading(true)
    setError(null)

    try {
      // Use service to fetch and merge all data
      const result = await positionResearchService.fetchEnhancedPositions({
        portfolioId,
        investmentClass: 'PRIVATE'
      })

      // Private positions are not separated into long/short
      // Combine all positions into a single array
      const allPositions = [...result.longPositions, ...result.shortPositions]
      setPositions(allPositions)
    } catch (err) {
      console.error('Failed to fetch private positions:', err)
      setError('Failed to load private positions data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (portfolioId) {
      fetchData()
    }
  }, [portfolioId])

  // Calculate aggregate returns for all private positions
  const aggregateReturns = useMemo(() => ({
    eoy: positionResearchService.calculateAggregateReturn(
      positions,
      'target_return_eoy',
      'analyst_return_eoy' // Fallback to analyst if user target is null
    ),
    next_year: positionResearchService.calculateAggregateReturn(
      positions,
      'target_return_next_year'
      // No fallback - analyst data doesn't include next year
    )
  }), [positions])

  // Optimistic update for target prices - instant UI feedback
  const updatePositionTargetOptimistic = useCallback(async (update: TargetPriceUpdate) => {
    if (!portfolioId) return

    // Update positions optimistically
    const handleOptimisticUpdate = (updatedPositions: EnhancedPosition[]) => {
      setPositions(updatedPositions)
    }

    // Use optimistic update service
    await targetPriceUpdateService.updatePositionTarget(
      portfolioId,
      update,
      positions,
      handleOptimisticUpdate,
      (error, previousState) => {
        console.error('Failed to sync target price, reverted:', error)
        setError(`Failed to update target price for ${update.symbol}`)
        // Error handling - state already reverted by service
      }
    )
  }, [portfolioId, positions])

  return {
    positions,
    loading,
    error,
    aggregateReturns,
    refetch: fetchData,
    updatePositionTargetOptimistic
  }
}
