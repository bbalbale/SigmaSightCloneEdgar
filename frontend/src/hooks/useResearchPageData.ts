'use client'

import { useMemo } from 'react'
import { usePublicPositions } from './usePublicPositions'
import { usePrivatePositions } from './usePrivatePositions'
import { useTags } from './useTags'
import { Position } from '@/stores/researchStore'

export interface ResearchPageData {
  publicPositions: {
    longs: Position[]
    shorts: Position[]
    options: Position[]
  }
  privatePositions: Position[]
  tags: any[]
  aggregateMetrics: {
    totalValue: number
    totalPnl: number
    totalPnlPercent: number
    positionCount: number
  }
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

// Check if position is an option based ONLY on investment_class
// We rely on usePublicPositions to pre-filter to PUBLIC and OPTIONS only
// So we just need to separate OPTIONS from PUBLIC here
const isOptionsPosition = (position: any): boolean => {
  return position.investment_class === 'OPTIONS'
}

export function useResearchPageData(): ResearchPageData {
  // Fetch data from existing hooks
  const {
    longPositions,
    shortPositions,
    loading: publicLoading,
    error: publicError,
    refetch: refetchPublic
  } = usePublicPositions()

  const {
    positions: privatePositions,
    loading: privateLoading,
    error: privateError,
    refetch: refetchPrivate
  } = usePrivatePositions()

  const {
    tags,
    loading: tagsLoading,
    error: tagsError
  } = useTags()

  // Separate options from longs based on investment_class OR position_type
  const publicPositionsData = useMemo(() => {
    const options: Position[] = []
    const actualLongs: Position[] = []

    longPositions.forEach((pos: any) => {
      if (isOptionsPosition(pos)) {
        options.push(pos as any)
      } else {
        actualLongs.push(pos as any)
      }
    })

    return {
      longs: actualLongs,
      shorts: shortPositions as any[],
      options
    }
  }, [longPositions, shortPositions])

  // Calculate aggregate metrics across all positions
  const aggregateMetrics = useMemo(() => {
    const allPositions = [
      ...publicPositionsData.longs,
      ...publicPositionsData.shorts,
      ...publicPositionsData.options,
      ...privatePositions
    ]

    const totalValue = allPositions.reduce((sum, pos: any) => {
      return sum + (Math.abs(pos.current_market_value || pos.marketValue || 0))
    }, 0)

    const totalPnl = allPositions.reduce((sum, pos: any) => {
      return sum + (pos.unrealized_pnl || pos.pnl || 0)
    }, 0)

    const totalPnlPercent = totalValue > 0 ? (totalPnl / totalValue) * 100 : 0

    return {
      totalValue,
      totalPnl,
      totalPnlPercent,
      positionCount: allPositions.length
    }
  }, [publicPositionsData, privatePositions])

  // Unified loading and error states
  const loading = publicLoading || privateLoading || tagsLoading
  const error = publicError || privateError || (tagsError?.message || null)

  // Unified refetch function
  const refetch = async () => {
    await Promise.all([refetchPublic(), refetchPrivate()])
  }

  return {
    publicPositions: publicPositionsData,
    privatePositions: privatePositions as any[],
    tags: tags || [],
    aggregateMetrics,
    loading,
    error,
    refetch
  }
}
