'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/services/apiClient'
import { usePortfolioStore } from '@/stores/portfolioStore'

export interface Position {
  id: string
  symbol: string
  quantity: number
  position_type: string
  investment_class?: string  // PUBLIC, OPTIONS, PRIVATE
  investment_subtype?: string
  current_price: number
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  realized_pnl: number
  // Option-specific fields
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
  // UI fields
  pnl?: number
  positive?: boolean
}

interface UsePositionsOptions {
  investmentClass?: 'PUBLIC' | 'OPTIONS' | 'PRIVATE'
  includeDetails?: boolean
}

interface UsePositionsReturn {
  positions: Position[]
  loading: boolean
  error: Error | null
  refresh: () => Promise<void>
  totalValue: number
  totalPnl: number
}

export function usePositions(options: UsePositionsOptions = {}): UsePositionsReturn {
  const { investmentClass, includeDetails = true } = options
  const portfolioId = usePortfolioStore(state => state.portfolioId)

  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchPositions = useCallback(async () => {
    if (!portfolioId) {
      setPositions([])
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        throw new Error('Not authenticated')
      }

      // Build query parameters
      const params = new URLSearchParams({
        portfolio_id: portfolioId
      })

      if (investmentClass) {
        params.append('investment_class', investmentClass)
      }

      // Fetch positions from API
      const response = await apiClient.get<{ positions: Position[] }>(
        `/api/v1/data/positions/details?${params.toString()}`,
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      )

      let filteredPositions = response.positions || []

      // Apply investment class filter if specified
      if (investmentClass) {
        filteredPositions = filteredPositions.filter(
          pos => pos.investment_class === investmentClass
        )
      }

      // Add UI fields
      const enhancedPositions = filteredPositions.map(pos => ({
        ...pos,
        pnl: pos.unrealized_pnl,
        positive: pos.unrealized_pnl >= 0
      }))

      setPositions(enhancedPositions)
    } catch (err) {
      console.error('Failed to fetch positions:', err)
      setError(err instanceof Error ? err : new Error('Failed to fetch positions'))
      setPositions([])
    } finally {
      setLoading(false)
    }
  }, [portfolioId, investmentClass])

  // Fetch positions on mount and when dependencies change
  useEffect(() => {
    fetchPositions()
  }, [fetchPositions])

  // Calculate totals
  const totalValue = positions.reduce((sum, pos) => sum + pos.market_value, 0)
  const totalPnl = positions.reduce((sum, pos) => sum + pos.unrealized_pnl, 0)

  return {
    positions,
    loading,
    error,
    refresh: fetchPositions,
    totalValue,
    totalPnl
  }
}

// Helper hook for position summary statistics
export function usePositionStats(positions: Position[]) {
  const longPositions = positions.filter(p => p.quantity > 0)
  const shortPositions = positions.filter(p => p.quantity < 0)

  const longValue = longPositions.reduce((sum, p) => sum + p.market_value, 0)
  const shortValue = Math.abs(shortPositions.reduce((sum, p) => sum + p.market_value, 0))
  const grossExposure = longValue + shortValue
  const netExposure = longValue - shortValue

  const gainers = positions.filter(p => p.unrealized_pnl > 0)
  const losers = positions.filter(p => p.unrealized_pnl < 0)

  return {
    totalPositions: positions.length,
    longPositions: longPositions.length,
    shortPositions: shortPositions.length,
    longValue,
    shortValue,
    grossExposure,
    netExposure,
    gainers: gainers.length,
    losers: losers.length,
    totalGains: gainers.reduce((sum, p) => sum + p.unrealized_pnl, 0),
    totalLosses: losers.reduce((sum, p) => sum + p.unrealized_pnl, 0)
  }
}