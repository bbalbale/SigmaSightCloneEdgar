'use client'

import { useState, useEffect, useCallback } from 'react'
import strategiesApi, { StrategyListItem } from '@/services/strategiesApi'
import { usePortfolioStore } from '@/stores/portfolioStore'

interface UseStrategiesOptions {
  tagIds?: string[]
  tagMode?: 'any' | 'all'
  strategyType?: string
  includePositions?: boolean
  includeTags?: boolean
  limit?: number
  offset?: number
}

interface UseStrategiesReturn {
  strategies: StrategyListItem[]
  loading: boolean
  error: Error | null
  refresh: () => Promise<void>
  total: number
  addTags: (strategyId: string, tagIds: string[]) => Promise<void>
  removeTags: (strategyId: string, tagIds: string[]) => Promise<void>
  replaceTags: (strategyId: string, tagIds: string[]) => Promise<void>
}

export function useStrategies(options: UseStrategiesOptions = {}): UseStrategiesReturn {
  const {
    tagIds,
    tagMode = 'any',
    strategyType,
    includePositions = false,
    includeTags = true,
    limit = 200,
    offset = 0
  } = options

  const portfolioId = usePortfolioStore(state => state.portfolioId)

  const [strategies, setStrategies] = useState<StrategyListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchStrategies = useCallback(async () => {
    if (!portfolioId) {
      setStrategies([])
      setTotal(0)
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

      const response = await strategiesApi.listByPortfolio({
        portfolioId,
        tagIds,
        tagMode,
        strategyType,
        includePositions,
        includeTags,
        limit,
        offset
      })

      setStrategies(response.strategies || [])
      setTotal(response.total || 0)
    } catch (err) {
      console.error('Failed to fetch strategies:', err)
      setError(err instanceof Error ? err : new Error('Failed to fetch strategies'))
      setStrategies([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [portfolioId, tagIds, tagMode, strategyType, includePositions, includeTags, limit, offset])

  // Fetch strategies on mount and when dependencies change
  useEffect(() => {
    fetchStrategies()
  }, [fetchStrategies])

  // Tag management functions
  const addTags = useCallback(async (strategyId: string, tagIds: string[]) => {
    try {
      await strategiesApi.addStrategyTags(strategyId, tagIds)
      // Refresh strategies to get updated tags
      await fetchStrategies()
    } catch (err) {
      console.error('Failed to add tags:', err)
      throw err
    }
  }, [fetchStrategies])

  const removeTags = useCallback(async (strategyId: string, tagIds: string[]) => {
    try {
      await strategiesApi.removeStrategyTags(strategyId, tagIds)
      // Refresh strategies to get updated tags
      await fetchStrategies()
    } catch (err) {
      console.error('Failed to remove tags:', err)
      throw err
    }
  }, [fetchStrategies])

  const replaceTags = useCallback(async (strategyId: string, tagIds: string[]) => {
    try {
      await strategiesApi.replaceStrategyTags(strategyId, tagIds)
      // Refresh strategies to get updated tags
      await fetchStrategies()
    } catch (err) {
      console.error('Failed to replace tags:', err)
      throw err
    }
  }, [fetchStrategies])

  return {
    strategies,
    loading,
    error,
    refresh: fetchStrategies,
    total,
    addTags,
    removeTags,
    replaceTags
  }
}

// Helper hook for strategy statistics
export function useStrategyStats(strategies: StrategyListItem[]) {
  const syntheticStrategies = strategies.filter(s => s.is_synthetic)
  const regularStrategies = strategies.filter(s => !s.is_synthetic)

  const strategiesWithTags = strategies.filter(s => s.tags && s.tags.length > 0)
  const strategiesWithoutTags = strategies.filter(s => !s.tags || s.tags.length === 0)

  const strategiesByType = strategies.reduce((acc, strategy) => {
    const type = strategy.type || 'Unknown'
    acc[type] = (acc[type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return {
    totalStrategies: strategies.length,
    syntheticCount: syntheticStrategies.length,
    regularCount: regularStrategies.length,
    withTags: strategiesWithTags.length,
    withoutTags: strategiesWithoutTags.length,
    byType: strategiesByType,
    averagePositions: strategies.reduce((sum, s) => sum + (s.position_count || 0), 0) / (strategies.length || 1)
  }
}