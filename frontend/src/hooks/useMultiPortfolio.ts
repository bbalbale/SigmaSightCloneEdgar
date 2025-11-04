/**
 * Multi-Portfolio Hooks - November 3, 2025
 * Provides hooks for managing multiple portfolios with aggregate and filtered views
 */

import { useEffect, useState, useCallback } from 'react'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { portfolioService } from '@/services/portfolioApi'
import type {
  PortfolioListItem,
  AggregateAnalytics,
  PortfolioBreakdown,
  CreatePortfolioRequest,
  UpdatePortfolioRequest,
  PortfolioResponse,
} from '@/services/portfolioApi'

/**
 * Hook: usePortfolios
 * Fetches and manages the list of all user portfolios
 */
interface UsePortfoliosReturn {
  portfolios: PortfolioListItem[]
  loading: boolean
  error: string | null
  refetch: () => void
}

export function usePortfolios(): UsePortfoliosReturn {
  const [portfolios, setPortfolios] = useState<PortfolioListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refetchTrigger, setRefetchTrigger] = useState(0)

  const setPortfoliosInStore = usePortfolioStore((state) => state.setPortfolios)

  useEffect(() => {
    const abortController = new AbortController()

    const fetchPortfolios = async () => {
      setLoading(true)
      setError(null)

      try {
        const data = await portfolioService.getPortfolios()
        console.log('[usePortfolios] Fetched portfolios from API:', data)
        setPortfolios(data)

        // Update Zustand store with portfolio list
        console.log('[usePortfolios] Calling setPortfoliosInStore with:', data)
        setPortfoliosInStore(data)

        // Verify it was stored
        const stored = usePortfolioStore.getState().portfolios
        console.log('[usePortfolios] Verified stored portfolios:', stored)

        setError(null)
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return
        }
        console.error('Failed to fetch portfolios:', err)
        setError(err.message || 'Failed to load portfolios')
        setPortfolios([])
      } finally {
        setLoading(false)
      }
    }

    fetchPortfolios()

    return () => {
      abortController.abort()
    }
  }, [refetchTrigger, setPortfoliosInStore])

  const refetch = useCallback(() => {
    setRefetchTrigger((prev) => prev + 1)
  }, [])

  return { portfolios, loading, error, refetch }
}

/**
 * Hook: useAggregateAnalytics
 * Fetches aggregate analytics across all portfolios
 */
interface UseAggregateAnalyticsReturn {
  analytics: AggregateAnalytics | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useAggregateAnalytics(): UseAggregateAnalyticsReturn {
  const [analytics, setAnalytics] = useState<AggregateAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refetchTrigger, setRefetchTrigger] = useState(0)

  useEffect(() => {
    const abortController = new AbortController()

    const fetchAnalytics = async () => {
      setLoading(true)
      setError(null)

      try {
        const data = await portfolioService.getAggregateAnalytics()
        setAnalytics(data)
        setError(null)
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return
        }
        console.error('Failed to fetch aggregate analytics:', err)
        setError(err.message || 'Failed to load aggregate analytics')
        setAnalytics(null)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()

    return () => {
      abortController.abort()
    }
  }, [refetchTrigger])

  const refetch = useCallback(() => {
    setRefetchTrigger((prev) => prev + 1)
  }, [])

  return { analytics, loading, error, refetch }
}

/**
 * Hook: usePortfolioBreakdown
 * Fetches portfolio breakdown showing each portfolio's contribution
 */
interface UsePortfolioBreakdownReturn {
  breakdown: PortfolioBreakdown | null
  loading: boolean
  error: string | null
  refetch: () => void
}

export function usePortfolioBreakdown(): UsePortfolioBreakdownReturn {
  const [breakdown, setBreakdown] = useState<PortfolioBreakdown | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refetchTrigger, setRefetchTrigger] = useState(0)

  useEffect(() => {
    const abortController = new AbortController()

    const fetchBreakdown = async () => {
      setLoading(true)
      setError(null)

      try {
        const data = await portfolioService.getPortfolioBreakdown()
        setBreakdown(data)
        setError(null)
      } catch (err: any) {
        if (err.name === 'AbortError') {
          return
        }
        console.error('Failed to fetch portfolio breakdown:', err)
        setError(err.message || 'Failed to load portfolio breakdown')
        setBreakdown(null)
      } finally {
        setLoading(false)
      }
    }

    fetchBreakdown()

    return () => {
      abortController.abort()
    }
  }, [refetchTrigger])

  const refetch = useCallback(() => {
    setRefetchTrigger((prev) => prev + 1)
  }, [])

  return { breakdown, loading, error, refetch }
}

/**
 * Hook: usePortfolioMutations
 * Provides functions for creating, updating, and deleting portfolios
 */
interface UsePortfolioMutationsReturn {
  createPortfolio: (data: CreatePortfolioRequest) => Promise<PortfolioResponse>
  updatePortfolio: (id: string, data: UpdatePortfolioRequest) => Promise<PortfolioResponse>
  deletePortfolio: (id: string) => Promise<void>
  creating: boolean
  updating: boolean
  deleting: boolean
  error: string | null
}

export function usePortfolioMutations(): UsePortfolioMutationsReturn {
  const [creating, setCreating] = useState(false)
  const [updating, setUpdating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const addPortfolio = usePortfolioStore((state) => state.addPortfolio)
  const updatePortfolioInStore = usePortfolioStore((state) => state.updatePortfolio)
  const removePortfolio = usePortfolioStore((state) => state.removePortfolio)

  const createPortfolio = useCallback(
    async (data: CreatePortfolioRequest): Promise<PortfolioResponse> => {
      setCreating(true)
      setError(null)

      try {
        const response = await portfolioService.createPortfolio(data)

        // Update Zustand store
        addPortfolio({
          id: response.id,
          account_name: response.account_name,
          account_type: response.account_type,
          net_asset_value: response.net_asset_value ?? response.equity_balance ?? 0,
          total_value: response.net_asset_value ?? response.equity_balance ?? 0,
          position_count: 0,
          is_active: response.is_active,
        })

        return response
      } catch (err: any) {
        console.error('Failed to create portfolio:', err)
        const errorMessage = err.message || 'Failed to create portfolio'
        setError(errorMessage)
        throw new Error(errorMessage)
      } finally {
        setCreating(false)
      }
    },
    [addPortfolio]
  )

  const updatePortfolio = useCallback(
    async (id: string, data: UpdatePortfolioRequest): Promise<PortfolioResponse> => {
      setUpdating(true)
      setError(null)

      try {
        const response = await portfolioService.updatePortfolio(id, data)

        // Update Zustand store
        updatePortfolioInStore(id, {
          account_name: response.account_name,
          account_type: response.account_type,
          is_active: response.is_active,
        })

        return response
      } catch (err: any) {
        console.error('Failed to update portfolio:', err)
        const errorMessage = err.message || 'Failed to update portfolio'
        setError(errorMessage)
        throw new Error(errorMessage)
      } finally {
        setUpdating(false)
      }
    },
    [updatePortfolioInStore]
  )

  const deletePortfolio = useCallback(
    async (id: string): Promise<void> => {
      setDeleting(true)
      setError(null)

      try {
        await portfolioService.deletePortfolio(id)

        // Update Zustand store
        removePortfolio(id)
      } catch (err: any) {
        console.error('Failed to delete portfolio:', err)
        const errorMessage = err.message || 'Failed to delete portfolio'
        setError(errorMessage)
        throw new Error(errorMessage)
      } finally {
        setDeleting(false)
      }
    },
    [removePortfolio]
  )

  return {
    createPortfolio,
    updatePortfolio,
    deletePortfolio,
    creating,
    updating,
    deleting,
    error,
  }
}

/**
 * Hook: useSelectedPortfolio
 * Returns the currently selected portfolio or null for aggregate view
 */
interface UseSelectedPortfolioReturn {
  selectedPortfolio: PortfolioListItem | null
  isAggregateView: boolean
  portfolioCount: number
}

export function useSelectedPortfolio(): UseSelectedPortfolioReturn {
  const selectedPortfolio = usePortfolioStore((state) => state.getSelectedPortfolio())
  const isAggregateView = usePortfolioStore((state) => state.isAggregateView())
  const portfolioCount = usePortfolioStore((state) => state.getPortfolioCount())

  return {
    selectedPortfolio,
    isAggregateView,
    portfolioCount,
  }
}
