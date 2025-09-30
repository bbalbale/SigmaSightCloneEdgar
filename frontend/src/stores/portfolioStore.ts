/**
 * Portfolio Store - Global portfolio ID management
 * Handles portfolio persistence across pages
 * Portfolio switching requires logout (no in-app switching)
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface PortfolioStore {
  // State
  portfolioId: string | null
  portfolioName: string | null

  // Actions
  setPortfolio: (id: string, name?: string | null) => void
  clearPortfolio: () => void

  // Computed
  hasPortfolio: () => boolean
}

export const usePortfolioStore = create<PortfolioStore>()(
  persist(
    (set, get) => ({
      // Initial state
      portfolioId: null,
      portfolioName: null,

      // Set portfolio data (called on login/data load)
      setPortfolio: (id, name) => {
        set({
          portfolioId: id,
          portfolioName: name ?? null
        })
      },

      // Clear portfolio (called on logout)
      clearPortfolio: () => {
        set({
          portfolioId: null,
          portfolioName: null
        })
      },

      // Check if portfolio is set
      hasPortfolio: () => {
        return get().portfolioId !== null
      }
    }),
    {
      name: 'portfolio-storage', // localStorage key
      version: 2,
      // Only persist the portfolioId, fetch name fresh on reload
      partialize: (state) => ({
        portfolioId: state.portfolioId
      })
    }
  )
)

// Selector hooks for common use cases
export const usePortfolioId = () => usePortfolioStore((state) => state.portfolioId)
export const usePortfolioName = () => usePortfolioStore((state) => state.portfolioName)
export const useHasPortfolio = () => usePortfolioStore((state) => state.hasPortfolio())

// Helper to get portfolio data outside of React components
export const getPortfolioId = () => usePortfolioStore.getState().portfolioId
export const clearPortfolioState = () => usePortfolioStore.getState().clearPortfolio()
export const setPortfolioState = (id: string, name?: string | null) => {
  usePortfolioStore.getState().setPortfolio(id, name)
}
