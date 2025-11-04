/**
 * Portfolio Store - Multi-Portfolio Management (Version 4)
 * Handles multiple portfolios with aggregate view support
 * Portfolio switching requires logout (no in-app switching)
 *
 * Version History:
 * - v1: Initial implementation
 * - v2: Added portfolio name
 * - v3: Multi-portfolio support with aggregate view
 * - v4: Restored legacy portfolioId alias for backward compatibility
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Portfolio list item interface
export interface PortfolioListItem {
  id: string
  account_name: string
  account_type: string
  net_asset_value: number
  total_value: number
  position_count: number
  is_active: boolean
}

interface PortfolioStore {
  // State
  portfolios: PortfolioListItem[]
  selectedPortfolioId: string | null  // null = aggregate view
  portfolioId: string | null  // Legacy alias for single-portfolio consumers

  // Portfolio CRUD Actions
  setPortfolios: (portfolios: PortfolioListItem[]) => void
  setSelectedPortfolio: (id: string | null) => void
  addPortfolio: (portfolio: PortfolioListItem) => void
  updatePortfolio: (id: string, updates: Partial<PortfolioListItem>) => void
  removePortfolio: (id: string) => void
  clearAll: () => void

  // Computed Getters
  getTotalValue: () => number
  getPortfolioCount: () => number
  getActivePortfolios: () => PortfolioListItem[]
  getSelectedPortfolio: () => PortfolioListItem | null
  isAggregateView: () => boolean
  hasPortfolio: () => boolean
}

export const usePortfolioStore = create<PortfolioStore>()(
  persist(
    (set, get) => ({
      // Initial state
      portfolios: [],
      selectedPortfolioId: null, // null = aggregate view by default
      portfolioId: null,

      // Set all portfolios (called on login/data load)
      setPortfolios: (portfolios) => {
        const selectedId = get().selectedPortfolioId
        const fallbackId = selectedId ?? (portfolios[0]?.id ?? null)
        set({ portfolios, portfolioId: fallbackId })
      },

      // Set selected portfolio ID (null for aggregate view)
      setSelectedPortfolio: (id) => {
        set((state) => ({
          selectedPortfolioId: id,
          portfolioId: id ?? (state.portfolios[0]?.id ?? null)
        }))
      },

      // Add a portfolio to the list
      addPortfolio: (portfolio) => {
        set((state) => {
          const portfolios = [...state.portfolios, portfolio]
          const selectedId = state.selectedPortfolioId
          const portfolioId = selectedId ?? (portfolios[0]?.id ?? null)
          return { portfolios, portfolioId }
        })
      },

      // Update a portfolio in the list
      updatePortfolio: (id, updates) => {
        set((state) => ({
          portfolios: state.portfolios.map((p) =>
            p.id === id ? { ...p, ...updates } : p
          )
        }))
      },

      // Remove a portfolio from the list
      removePortfolio: (id) => {
        set((state) => {
          const portfolios = state.portfolios.filter((p) => p.id !== id)
          const selectedPortfolioId = state.selectedPortfolioId === id ? null : state.selectedPortfolioId
          const portfolioId = selectedPortfolioId ?? (portfolios[0]?.id ?? null)
          return {
            portfolios,
            selectedPortfolioId,
            portfolioId
          }
        })
      },

      // Clear all portfolio data (called on logout)
      clearAll: () => {
        set({
          portfolios: [],
          selectedPortfolioId: null,
          portfolioId: null
        })
      },

      // Get total value across all portfolios
      getTotalValue: () => {
        return get().portfolios.reduce((sum, p) => sum + (p.net_asset_value ?? p.total_value ?? 0), 0)
      },

      // Get count of portfolios
      getPortfolioCount: () => {
        return get().portfolios.length
      },

      // Get only active portfolios
      getActivePortfolios: () => {
        return get().portfolios.filter((p) => p.is_active)
      },

      // Get currently selected portfolio (null if aggregate view)
      getSelectedPortfolio: () => {
        const { portfolios, selectedPortfolioId } = get()
        if (selectedPortfolioId === null) return null
        return portfolios.find((p) => p.id === selectedPortfolioId) || null
      },

      // Check if currently in aggregate view
      isAggregateView: () => {
        return get().selectedPortfolioId === null
      },

      // Check if any portfolio is set
      hasPortfolio: () => {
        return get().portfolios.length > 0
      }
    }),
    {
      name: 'portfolio-storage', // localStorage key
      version: 4, // v4 adds portfolioId alias for backward compatibility
      migrate: (persistedState: any, version: number) => {
        if (version <= 2) {
          // Legacy versions used a single portfolioId field only
          return {
            portfolios: [],
            selectedPortfolioId: null,
            portfolioId: null
          }
        }

        const state = persistedState as Partial<PortfolioStore> & { portfolios?: PortfolioListItem[] }
        const portfolios = state.portfolios ?? []
        const selectedPortfolioId = state.selectedPortfolioId ?? null
        const portfolioId = state.portfolioId ?? selectedPortfolioId ?? (portfolios[0]?.id ?? null)

        return {
          portfolios,
          selectedPortfolioId,
          portfolioId
        }
      },
      // Only persist portfolios, selection, and legacy alias
      partialize: (state) => ({
        portfolios: state.portfolios,
        selectedPortfolioId: state.selectedPortfolioId,
        portfolioId: state.portfolioId
      })
    }
  )
)

// Selector hooks for common use cases
export const usePortfolios = () => usePortfolioStore((state) => state.portfolios)
export const useSelectedPortfolioId = () => usePortfolioStore((state) => state.selectedPortfolioId)
export const useSelectedPortfolio = () => usePortfolioStore((state) => state.getSelectedPortfolio())
export const useIsAggregateView = () => usePortfolioStore((state) => state.isAggregateView())
export const useHasPortfolio = () => usePortfolioStore((state) => state.hasPortfolio())
export const usePortfolioCount = () => usePortfolioStore((state) => state.getPortfolioCount())
export const useTotalValue = () => usePortfolioStore((state) => state.getTotalValue())

// Helper functions to get/set portfolio data outside of React components
export const getPortfolios = () => usePortfolioStore.getState().portfolios
export const getSelectedPortfolioId = () => usePortfolioStore.getState().selectedPortfolioId
export const getSelectedPortfolio = () => usePortfolioStore.getState().getSelectedPortfolio()
export const isAggregateView = () => usePortfolioStore.getState().isAggregateView()

// Legacy exports for backward compatibility (will return first portfolio if exists)
export const getPortfolioId = () => {
  return usePortfolioStore.getState().portfolioId
}

export const usePortfolioId = () => {
  return usePortfolioStore((state) => state.portfolioId)
}

export const clearPortfolioState = () => usePortfolioStore.getState().clearAll()

export const setPortfolioState = (id: string, name?: string | null) => {
  // Legacy function for backward compatibility
  // Convert to new multi-portfolio format
  const existingPortfolio = usePortfolioStore.getState().portfolios.find(p => p.id === id)

  if (!existingPortfolio) {
    // Add as new portfolio with minimal data (will be populated later)
    usePortfolioStore.getState().addPortfolio({
      id,
      account_name: name || 'Portfolio',
      account_type: 'taxable',
      total_value: 0,
      position_count: 0,
      is_active: true
    })
  }

  // Select this portfolio
  usePortfolioStore.getState().setSelectedPortfolio(id)
}
