/**
 * Portfolio Store - Multi-Portfolio Management (Version 3)
 * Handles multiple portfolios with aggregate view support
 * Portfolio switching requires logout (no in-app switching)
 *
 * Version History:
 * - v1: Initial implementation
 * - v2: Added portfolio name
 * - v3: Multi-portfolio support with aggregate view
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

      // Set all portfolios (called on login/data load)
      setPortfolios: (portfolios) => {
        set({ portfolios })
      },

      // Set selected portfolio ID (null for aggregate view)
      setSelectedPortfolio: (id) => {
        set({ selectedPortfolioId: id })
      },

      // Add a portfolio to the list
      addPortfolio: (portfolio) => {
        set((state) => ({
          portfolios: [...state.portfolios, portfolio]
        }))
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
        set((state) => ({
          portfolios: state.portfolios.filter((p) => p.id !== id),
          // If removing selected portfolio, switch to aggregate view
          selectedPortfolioId: state.selectedPortfolioId === id ? null : state.selectedPortfolioId
        }))
      },

      // Clear all portfolio data (called on logout)
      clearAll: () => {
        set({
          portfolios: [],
          selectedPortfolioId: null
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
      version: 3, // Updated from v2 to v3
      // Migration from version 2 to version 3
      migrate: (persistedState: any, version: number) => {
        if (version === 2) {
          // Migrate from v2 (single portfolio) to v3 (multiple portfolios)
          const oldPortfolioId = persistedState.portfolioId

          if (oldPortfolioId) {
            // Convert single portfolio ID to portfolios array
            // Will be populated with real data on next login
            return {
              portfolios: [],
              selectedPortfolioId: null // Start with aggregate view
            }
          }
        }

        return persistedState as PortfolioStore
      },
      // Only persist portfolios and selectedPortfolioId
      partialize: (state) => ({
        portfolios: state.portfolios,
        selectedPortfolioId: state.selectedPortfolioId
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
  const state = usePortfolioStore.getState()
  // For backward compatibility: return selected portfolio ID or first portfolio ID
  if (state.selectedPortfolioId) {
    return state.selectedPortfolioId
  }
  if (state.portfolios.length > 0) {
    return state.portfolios[0].id
  }
  return null
}

export const usePortfolioId = () => {
  const selectedId = useSelectedPortfolioId()
  const portfolios = usePortfolios()

  // For backward compatibility: return selected portfolio ID or first portfolio ID
  if (selectedId) {
    return selectedId
  }
  if (portfolios.length > 0) {
    return portfolios[0].id
  }
  return null
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
