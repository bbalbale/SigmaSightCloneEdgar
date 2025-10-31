import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

// Types
export type TabType = 'public' | 'private' | 'options'
export type PLFilter = 'all' | 'gainers' | 'losers'
export type SortOption = 'weight' | 'returnEOY' | 'symbol' | 'pnl'

export interface Position {
  id: string
  symbol: string
  marketValue: number
  pnlPercent: number
  quantity: number
  positionType: string
  sector: string
  tags: Tag[]
  companyName?: string
  currentPrice?: number
  avgCost?: number
  pnl?: number
  beta?: number
  volatility?: number
  factorExposures?: {
    growth: number
    momentum: number
    size: number
  }
  targetPrice?: number
  targetReturn?: number
  targetPriceDate?: string
}

export interface Tag {
  id: string
  name: string
  color: string
}

export interface FilterState {
  search: string
  selectedTags: string[]  // Tag IDs
  selectedSector: string | null
  plFilter: PLFilter
  sort: SortOption
  sortDirection: 'asc' | 'desc'
}

export interface ResearchStore {
  // Tab State
  activeTab: TabType
  setActiveTab: (tab: TabType) => void

  // Side Panel State
  sidePanelOpen: boolean
  selectedPosition: Position | null
  openSidePanel: (position: Position) => void
  closeSidePanel: () => void

  // Filter State
  filters: FilterState
  setSearch: (search: string) => void
  toggleTag: (tagId: string) => void
  setSector: (sector: string | null) => void
  setPLFilter: (filter: PLFilter) => void
  setSort: (sort: SortOption) => void
  toggleSortDirection: () => void
  clearFilters: () => void

  // UI State
  stickyBarVisible: boolean
  setStickyBarVisible: (visible: boolean) => void

  // Optimistic Updates (for tagging)
  optimisticTags: Record<string, string[]>  // positionId -> tagIds[]
  addOptimisticTag: (positionId: string, tagId: string) => void
  removeOptimisticTag: (positionId: string, tagId: string) => void
  clearOptimisticTags: (positionId: string) => void

  // Reset (for logout)
  reset: () => void
}

// Initial state
const initialFilterState: FilterState = {
  search: '',
  selectedTags: [],
  selectedSector: null,
  plFilter: 'all',
  sort: 'weight',
  sortDirection: 'desc'
}

// Create store with persistence for tab and filters only
export const useResearchStore = create<ResearchStore>()(
  persist(
    (set, get) => ({
      // Tab State
      activeTab: 'public',
      setActiveTab: (tab) => set({ activeTab: tab }),

      // Side Panel State (NOT persisted)
      sidePanelOpen: false,
      selectedPosition: null,
      openSidePanel: (position) =>
        set({ sidePanelOpen: true, selectedPosition: position }),
      closeSidePanel: () =>
        set({ sidePanelOpen: false, selectedPosition: null }),

      // Filter State (persisted)
      filters: initialFilterState,

      setSearch: (search) =>
        set((state) => ({
          filters: { ...state.filters, search }
        })),

      toggleTag: (tagId) =>
        set((state) => {
          const selectedTags = state.filters.selectedTags.includes(tagId)
            ? state.filters.selectedTags.filter(id => id !== tagId)
            : [...state.filters.selectedTags, tagId]
          return {
            filters: { ...state.filters, selectedTags }
          }
        }),

      setSector: (sector) =>
        set((state) => ({
          filters: { ...state.filters, selectedSector: sector }
        })),

      setPLFilter: (filter) =>
        set((state) => ({
          filters: { ...state.filters, plFilter: filter }
        })),

      setSort: (sort) =>
        set((state) => ({
          filters: { ...state.filters, sort }
        })),

      toggleSortDirection: () =>
        set((state) => ({
          filters: {
            ...state.filters,
            sortDirection: state.filters.sortDirection === 'asc' ? 'desc' : 'asc'
          }
        })),

      clearFilters: () =>
        set({ filters: initialFilterState }),

      // UI State
      stickyBarVisible: true,
      setStickyBarVisible: (visible) => set({ stickyBarVisible: visible }),

      // Optimistic Updates
      optimisticTags: {},

      addOptimisticTag: (positionId, tagId) =>
        set((state) => ({
          optimisticTags: {
            ...state.optimisticTags,
            [positionId]: [
              ...(state.optimisticTags[positionId] || []),
              tagId
            ]
          }
        })),

      removeOptimisticTag: (positionId, tagId) =>
        set((state) => ({
          optimisticTags: {
            ...state.optimisticTags,
            [positionId]: (state.optimisticTags[positionId] || [])
              .filter(id => id !== tagId)
          }
        })),

      clearOptimisticTags: (positionId) =>
        set((state) => {
          const { [positionId]: _, ...rest } = state.optimisticTags
          return { optimisticTags: rest }
        }),

      // Reset
      reset: () => set({
        activeTab: 'public',
        sidePanelOpen: false,
        selectedPosition: null,
        filters: initialFilterState,
        stickyBarVisible: true,
        optimisticTags: {}
      })
    }),
    {
      name: 'research-store', // localStorage key
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist these fields
        activeTab: state.activeTab,
        filters: state.filters
        // Do NOT persist: sidePanelOpen, selectedPosition, optimisticTags
      })
    }
  )
)

// Selectors (for performance optimization)
export const selectActiveTab = (state: ResearchStore) => state.activeTab
export const selectFilters = (state: ResearchStore) => state.filters
export const selectSidePanelOpen = (state: ResearchStore) => state.sidePanelOpen
export const selectSelectedPosition = (state: ResearchStore) => state.selectedPosition

// Export helper for non-React contexts
export const getResearchState = () => useResearchStore.getState()
