# Research & Analyze Page - Implementation Plan

**Document Version**: 1.0
**Created**: October 31, 2025
**Status**: Detailed Implementation Plan
**Timeline**: 4-5 days with 4 checkpoints
**Approach**: Consolidate Public + Private + Organize pages into unified R&A workspace

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design Specifications](#design-specifications)
3. [Architecture Overview](#architecture-overview)
4. [State Management with Zustand](#state-management-with-zustand)
5. [Component Breakdown](#component-breakdown)
6. [Day-by-Day Agent Workflow](#day-by-day-agent-workflow)
7. [Correlations Integration](#correlations-integration)
8. [Tagging Integration](#tagging-integration)
9. [Code Reuse Matrix](#code-reuse-matrix)
10. [Success Criteria](#success-criteria)

---

## Executive Summary

### Goal
Consolidate 3 separate pages (Public Positions, Private Positions, Organize) into a single "Research & Analyze" workspace with:
- **3 tabs**: Public | Private | Options
- **Sticky tag bar** for drag-drop tagging (from Organize)
- **Side panel** for position details (click position → drawer with correlations, risk metrics, target prices)
- **Simplified position cards** (overview info only, details in side panel)
- **Bloomberg-inspired design** (following Command Center styling)

### What We're Reusing (70% of code)
✅ **Components**: ResearchPositionCard, EnhancedPositionsSection, TagManager, DragDropInterface
✅ **Hooks**: usePublicPositions, usePrivatePositions, useTags, useCorrelationMatrix, useFactorExposures
✅ **Services**: All existing API services (tagsApi, analyticsApi, portfolioService)

### What We're Building (30% new code)
❌ **New Components**: ResearchAndAnalyzeContainer, PositionSidePanel, StickyTagBar, SimplifiedPositionCard
❌ **New Hooks**: usePositionCorrelations, useResearchPageData
❌ **Total New LOC**: ~1,400 lines

### Key Features
1. **Correlations display** in side panel (top 5 correlated positions with risk warnings)
2. **Sticky tag bar** for drag-drop tagging across all tabs
3. **3 tabs** with shared filters and summary metrics
4. **Side panel** with 5 sections (Overview, Risk Metrics, Correlations, Target Price, Quick Actions)

---

## Design Specifications

### Visual Reference
Based on mockup in `10-DESIGN-MOCKUPS.md` (lines 262-310) and Command Center styling.

### Typography (Bloomberg-Inspired, Modern)

**From Command Center Pattern:**
```typescript
// Page Title
className="text-3xl font-bold text-white/text-gray-900"

// Section Labels (uppercase, tracked, small)
className="text-[10px] font-semibold uppercase tracking-wider text-slate-500"

// Primary Values (large, bold, monospace)
className="text-2xl font-bold tabular-nums text-orange-400"

// Secondary Values (small, medium, monospace)
className="text-xs font-medium tabular-nums text-slate-500"

// Card Text
className="text-sm text-slate-400/text-slate-600"
```

**Key Principles:**
- **Tabular numbers** (`tabular-nums`) for all financial data
- **Uppercase labels** with letter-spacing (`uppercase tracking-wider`)
- **Monospace appearance** for numbers (achieved via `tabular-nums`)
- **Font sizes**: 10px labels, 12px secondary, 14px body, 24px primary values, 32px page title

### Color Palette

**Dark Theme** (Primary):
```typescript
background: 'bg-slate-900'           // Page background
cardBg: 'bg-slate-900/50'            // Card backgrounds
border: 'border-slate-700/50'        // Borders
text: {
  primary: 'text-white',             // Headings
  secondary: 'text-slate-400',       // Body text
  muted: 'text-slate-500'            // Labels, hints
},
accent: {
  positive: 'text-emerald-400',      // Gains, positive metrics
  negative: 'text-red-400',          // Losses, negative metrics
  neutral: 'text-orange-400',        // Primary values
  info: 'text-blue-400'              // Links, actions
}
```

**Light Theme**:
```typescript
background: 'bg-gray-50'
cardBg: 'bg-white'
border: 'border-slate-300'
text: {
  primary: 'text-gray-900',
  secondary: 'text-gray-600',
  muted: 'text-slate-500'
},
accent: {
  positive: 'text-emerald-600',
  negative: 'text-red-600',
  neutral: 'text-slate-900',
  info: 'text-blue-600'
}
```

### Layout Grid

**Hero Section** (Always visible at top):
```
┌─────────────────────────────────────────────────────────────────┐
│ Research & Analyze                                    [User][AI] │
│ Position research, target prices, and analysis                  │
└─────────────────────────────────────────────────────────────────┘
```

**Sticky Tag Bar** (z-index: 40, hide on scroll down):
```
┌─────────────────────────────────────────────────────────────────┐
│ [Tech] [Growth] [Core] [Hedge] [+] [Restore Sector Tags]       │
└─────────────────────────────────────────────────────────────────┘
```

**Tabs + Filters** (z-index: 30):
```
┌─────────────────────────────────────────────────────────────────┐
│ [Public] [Private] [Options]                                    │
│ [🔍 Search...] [Tag ▼] [Sector ▼] [P/L ▼] [Sort ▼]            │
│ 63 positions | $500K total | +$24.5K (+5.1%)                    │
└─────────────────────────────────────────────────────────────────┘
```

**Position List + Side Panel**:
```
┌────────────────────────────────┬────────────────────────────────┐
│ Position Cards (scrollable)    │ Side Panel (position details)  │
│                                │ - Overview                     │
│ ┌──────────────────────────┐  │ - Risk Metrics                 │
│ │ NVDA  $88K  +15.8%  →    │  │ - Correlations ⭐              │
│ │ 200 shares | Long | Tech │  │ - Target Price                 │
│ └──────────────────────────┘  │ - Quick Actions                │
│                                │                                │
│ (more cards...)                │ [×] Close                      │
└────────────────────────────────┴────────────────────────────────┘
```

### Spacing System
```typescript
spacing: {
  xs: '4px',      // 0.5 Tailwind (tight card padding)
  sm: '8px',      // 1 Tailwind (card internal spacing)
  md: '16px',     // 4 Tailwind (section padding)
  lg: '24px',     // 6 Tailwind (page margins)
  xl: '32px'      // 8 Tailwind (major sections)
}
```

### Component Styling

**Position Card** (Simplified from current ResearchPositionCard):
```tsx
<div className={`border rounded transition-all duration-200 cursor-pointer p-3 ${
  theme === 'dark'
    ? 'bg-slate-900/50 border-slate-700/50 hover:bg-slate-800/50'
    : 'bg-white border-slate-300 hover:bg-slate-50'
}`}>
  {/* Symbol + P&L */}
  <div className="flex items-center justify-between mb-2">
    <span className="text-lg font-bold text-white/text-gray-900">NVDA</span>
    <span className="text-sm font-semibold tabular-nums text-emerald-400/text-emerald-600">
      +15.8%
    </span>
  </div>

  {/* Market Value */}
  <div className="text-xl font-bold tabular-nums text-orange-400/text-slate-900 mb-1">
    $88,000
  </div>

  {/* Details */}
  <div className="text-xs text-slate-500">
    200 shares | Long | Technology
  </div>

  {/* Tags */}
  <div className="flex gap-1 mt-2">
    <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">Core</span>
    <span className="text-[10px] px-2 py-0.5 rounded bg-green-500/20 text-green-400">Growth</span>
  </div>
</div>
```

**Side Panel Section** (Sheet from shadcn):
```tsx
<div className={`${theme === 'dark' ? 'bg-slate-900' : 'bg-white'} overflow-y-auto`}>
  {/* Section Header */}
  <div className="px-4 py-3 border-b">
    <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
      CORRELATIONS
    </h3>
  </div>

  {/* Section Content */}
  <div className="px-4 py-3">
    {/* Correlation items */}
  </div>
</div>
```

---

## Architecture Overview

### File Structure
```
frontend/
├── app/
│   └── research-and-analyze/
│       └── page.tsx (thin wrapper, 10 lines)
│
├── src/
│   ├── containers/
│   │   └── ResearchAndAnalyzeContainer.tsx (main logic, ~450 lines)
│   │
│   ├── components/
│   │   └── research-and-analyze/
│   │       ├── SimplifiedPositionCard.tsx (~100 lines)
│   │       ├── PositionSidePanel.tsx (~250 lines)
│   │       ├── StickyTagBar.tsx (~120 lines)
│   │       ├── ResearchFilterBar.tsx (~100 lines)
│   │       ├── SummaryMetricsBar.tsx (~80 lines)
│   │       ├── CorrelationsSection.tsx (~100 lines)
│   │       └── TabContent.tsx (~120 lines)
│   │
│   └── hooks/
│       ├── useResearchPageData.ts (~150 lines)
│       ├── usePositionCorrelations.ts (~80 lines)
│       └── useSharedFilters.ts (~100 lines)
```

### Data Flow Architecture

```
User opens /research-and-analyze
        ↓
ResearchAndAnalyzeContainer
        ↓
useResearchPageData hook
        ├─→ usePublicPositions (existing)
        ├─→ usePrivatePositions (existing)
        ├─→ useTags (existing)
        └─→ useCorrelationMatrix (existing)
        ↓
Returns categorized data:
{
  publicPositions: { longs, shorts, options },
  privatePositions: [],
  tags: [],
  correlationMatrix: NxN matrix,
  aggregateMetrics: { totalValue, totalPnL, ... },
  loading, error
}
        ↓
User clicks position card
        ↓
PositionSidePanel opens
        ↓
usePositionCorrelations(symbol)
        ├─→ Filters correlation matrix for selected position
        ├─→ Sorts by correlation strength
        └─→ Returns top 5 correlations + risk warning
```

---

## State Management with Zustand

### Overview

The Research & Analyze page requires a dedicated Zustand store to manage:
- **Tab state** (which tab is active: Public, Private, Options)
- **Filter state** (search, tags, sector, P/L, sort)
- **Side panel state** (open/closed, selected position)
- **UI state** (sticky bar visibility, loading states)
- **Optimistic updates** (tag additions before backend confirms)

This store will work alongside the existing `portfolioStore` (for portfolio ID) and `chatStore` (for AI interactions).

### Zustand Store Implementation

**File**: `src/stores/researchStore.ts`
**Lines**: ~200

```typescript
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
  // ... other fields
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
```

### Usage in Components

#### **ResearchAndAnalyzeContainer** (Main orchestrator)

```typescript
import { useResearchStore } from '@/stores/researchStore'

export function ResearchAndAnalyzeContainer() {
  // Subscribe to specific slices (avoids unnecessary re-renders)
  const activeTab = useResearchStore((state) => state.activeTab)
  const setActiveTab = useResearchStore((state) => state.setActiveTab)
  const sidePanelOpen = useResearchStore((state) => state.sidePanelOpen)
  const selectedPosition = useResearchStore((state) => state.selectedPosition)
  const openSidePanel = useResearchStore((state) => state.openSidePanel)
  const closeSidePanel = useResearchStore((state) => state.closeSidePanel)
  const filters = useResearchStore((state) => state.filters)

  // Data fetching with hooks
  const { publicPositions, privatePositions, tags, loading } = useResearchPageData()

  // Filter positions based on store state
  const filteredPositions = useMemo(() => {
    let positions = activeTab === 'public' ? publicPositions.longs :
                   activeTab === 'private' ? privatePositions :
                   publicPositions.options

    // Apply search filter
    if (filters.search) {
      positions = positions.filter(p =>
        p.symbol.toLowerCase().includes(filters.search.toLowerCase()) ||
        p.companyName?.toLowerCase().includes(filters.search.toLowerCase())
      )
    }

    // Apply tag filter
    if (filters.selectedTags.length > 0) {
      positions = positions.filter(p =>
        p.tags.some(tag => filters.selectedTags.includes(tag.id))
      )
    }

    // Apply sector filter
    if (filters.selectedSector) {
      positions = positions.filter(p => p.sector === filters.selectedSector)
    }

    // Apply P&L filter
    if (filters.plFilter === 'gainers') {
      positions = positions.filter(p => p.pnlPercent > 0)
    } else if (filters.plFilter === 'losers') {
      positions = positions.filter(p => p.pnlPercent < 0)
    }

    // Apply sort
    positions = sortPositions(positions, filters.sort, filters.sortDirection)

    return positions
  }, [activeTab, publicPositions, privatePositions, filters])

  return (
    <div>
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        {/* ... */}
      </Tabs>

      {/* Position list */}
      {filteredPositions.map(position => (
        <SimplifiedPositionCard
          key={position.id}
          position={position}
          onClick={() => openSidePanel(position)}
        />
      ))}

      {/* Side Panel */}
      <Sheet open={sidePanelOpen} onOpenChange={closeSidePanel}>
        <SheetContent>
          <PositionSidePanel position={selectedPosition} />
        </SheetContent>
      </Sheet>
    </div>
  )
}
```

#### **StickyTagBar** (Drag source)

```typescript
import { useResearchStore } from '@/stores/researchStore'

export function StickyTagBar({ tags }: StickyTagBarProps) {
  const stickyBarVisible = useResearchStore((state) => state.stickyBarVisible)

  const handleDragStart = (e: DragEvent, tagId: string) => {
    e.dataTransfer.setData('tagId', tagId)
  }

  return (
    <div className={`sticky top-0 transition-transform ${
      stickyBarVisible ? 'translate-y-0' : '-translate-y-full'
    }`}>
      {tags.map(tag => (
        <div
          key={tag.id}
          draggable
          onDragStart={(e) => handleDragStart(e, tag.id)}
        >
          {tag.name}
        </div>
      ))}
    </div>
  )
}
```

#### **SimplifiedPositionCard** (Drop target)

```typescript
import { useResearchStore } from '@/stores/researchStore'
import { tagsApi } from '@/services/tagsApi'

export function SimplifiedPositionCard({ position, onClick }: CardProps) {
  const addOptimisticTag = useResearchStore((state) => state.addOptimisticTag)
  const removeOptimisticTag = useResearchStore((state) => state.removeOptimisticTag)
  const optimisticTags = useResearchStore((state) => state.optimisticTags[position.id] || [])

  const handleDrop = async (e: DragEvent) => {
    e.preventDefault()
    const tagId = e.dataTransfer.getData('tagId')

    // Optimistic update (instant UI feedback)
    addOptimisticTag(position.id, tagId)

    try {
      // Backend call
      await tagsApi.tagPosition(position.id, tagId)
      // Success - keep optimistic update
    } catch (error) {
      // Failure - revert optimistic update
      removeOptimisticTag(position.id, tagId)
      toast.error('Failed to add tag')
    }
  }

  // Merge actual tags with optimistic tags for display
  const displayTags = useMemo(() => {
    const allTagIds = new Set([
      ...position.tags.map(t => t.id),
      ...optimisticTags
    ])
    return Array.from(allTagIds).map(id =>
      position.tags.find(t => t.id === id) || { id, name: 'Loading...', color: '#888' }
    )
  }, [position.tags, optimisticTags])

  return (
    <div
      onClick={onClick}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      {/* Position info */}

      {/* Tags */}
      <div className="flex gap-1">
        {displayTags.map(tag => (
          <TagBadge key={tag.id} tag={tag} />
        ))}
      </div>
    </div>
  )
}
```

#### **ResearchFilterBar** (Filter controls)

```typescript
import { useResearchStore } from '@/stores/researchStore'

export function ResearchFilterBar({ tags }: FilterBarProps) {
  const filters = useResearchStore((state) => state.filters)
  const setSearch = useResearchStore((state) => state.setSearch)
  const toggleTag = useResearchStore((state) => state.toggleTag)
  const setSector = useResearchStore((state) => state.setSector)
  const setPLFilter = useResearchStore((state) => state.setPLFilter)
  const clearFilters = useResearchStore((state) => state.clearFilters)

  // Debounced search
  const debouncedSetSearch = useDebouncedCallback(setSearch, 300)

  return (
    <div className="flex gap-2">
      {/* Search */}
      <Input
        placeholder="Search symbol or name..."
        defaultValue={filters.search}
        onChange={(e) => debouncedSetSearch(e.target.value)}
      />

      {/* Tag Filter (Multi-select) */}
      <Select
        value={filters.selectedTags}
        onValueChange={(tagIds) => {
          // Clear all selected tags first
          filters.selectedTags.forEach(id => toggleTag(id))
          // Add new selections
          tagIds.forEach(id => toggleTag(id))
        }}
        multiple
      >
        {tags.map(tag => (
          <SelectItem key={tag.id} value={tag.id}>
            {tag.name}
          </SelectItem>
        ))}
      </Select>

      {/* Sector Filter */}
      <Select value={filters.selectedSector || ''} onValueChange={setSector}>
        <SelectItem value="">All Sectors</SelectItem>
        <SelectItem value="Technology">Technology</SelectItem>
        <SelectItem value="Healthcare">Healthcare</SelectItem>
        {/* ... */}
      </Select>

      {/* P&L Filter */}
      <Select value={filters.plFilter} onValueChange={setPLFilter}>
        <SelectItem value="all">All</SelectItem>
        <SelectItem value="gainers">Gainers</SelectItem>
        <SelectItem value="losers">Losers</SelectItem>
      </Select>

      {/* Clear Filters */}
      <Button variant="ghost" onClick={clearFilters}>
        Clear All
      </Button>
    </div>
  )
}
```

### State Persistence Strategy

**Persisted to localStorage:**
- ✅ `activeTab` - Remember which tab user was on
- ✅ `filters` - Remember search, selected tags, sector, P&L, sort

**NOT Persisted (session-only):**
- ❌ `sidePanelOpen` - Always closed on page load
- ❌ `selectedPosition` - No position selected on page load
- ❌ `optimisticTags` - Cleared on page load (refetch real tags)
- ❌ `stickyBarVisible` - Always visible on page load

**Why?**
- Persisting tab + filters improves UX (user returns to same view)
- NOT persisting side panel avoids confusion (seeing a panel for a stale position)
- Optimistic tags are temporary (always refetch real state from backend)

### Integration with Existing Stores

**portfolioStore** (Existing):
```typescript
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useResearchStore } from '@/stores/researchStore'

// In ResearchAndAnalyzeContainer:
const { portfolioId } = usePortfolioStore()  // Get current portfolio
const activeTab = useResearchStore((state) => state.activeTab)  // Get R&A state

// Both stores work together - portfolioId drives data fetching,
// researchStore drives UI state
```

**chatStore** (Existing):
```typescript
// If user clicks "AI Explain" in side panel:
import { useChatStore } from '@/stores/chatStore'
import { useResearchStore } from '@/stores/researchStore'

const selectedPosition = useResearchStore((state) => state.selectedPosition)
const openAISidebar = useChatStore((state) => state.openSidebar)

const handleAIExplain = () => {
  openAISidebar({
    context: {
      page: 'research-and-analyze',
      position: selectedPosition
    },
    prompt: `Explain ${selectedPosition.symbol} and its role in my portfolio`
  })
}
```

### Reset on Logout

```typescript
// In logout handler (authManager or layout):
import { useResearchStore } from '@/stores/researchStore'

const handleLogout = () => {
  // ... other logout logic
  useResearchStore.getState().reset()  // Clear R&A store
  // This clears all state including persisted localStorage
}
```

### Performance Optimization with Selectors

**Good** (subscribes to specific slice):
```typescript
const activeTab = useResearchStore((state) => state.activeTab)
// Component only re-renders when activeTab changes
```

**Bad** (subscribes to entire store):
```typescript
const store = useResearchStore()
// Component re-renders on ANY store change
```

**Best** (memoized selector):
```typescript
const selectFilteredPositions = (positions: Position[]) => (state: ResearchStore) => {
  // Complex filtering logic here
  return filteredPositions
}

const filteredPositions = useResearchStore(selectFilteredPositions(allPositions))
```

### Testing Store

```typescript
// __tests__/stores/researchStore.test.ts
import { renderHook, act } from '@testing-library/react'
import { useResearchStore } from '@/stores/researchStore'

describe('researchStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useResearchStore.getState().reset()
  })

  it('should toggle tag filter', () => {
    const { result } = renderHook(() => useResearchStore())

    act(() => {
      result.current.toggleTag('tag-1')
    })

    expect(result.current.filters.selectedTags).toEqual(['tag-1'])

    act(() => {
      result.current.toggleTag('tag-1')
    })

    expect(result.current.filters.selectedTags).toEqual([])
  })

  it('should handle optimistic tag updates', () => {
    const { result } = renderHook(() => useResearchStore())

    act(() => {
      result.current.addOptimisticTag('pos-1', 'tag-1')
    })

    expect(result.current.optimisticTags['pos-1']).toEqual(['tag-1'])

    act(() => {
      result.current.removeOptimisticTag('pos-1', 'tag-1')
    })

    expect(result.current.optimisticTags['pos-1']).toEqual([])
  })
})
```

---

## Component Breakdown

### 1. ResearchAndAnalyzeContainer (Main Orchestrator)

**File**: `src/containers/ResearchAndAnalyzeContainer.tsx`
**Lines**: ~450
**Responsibilities**:
- Tab state management (Public, Private, Options)
- Data fetching via useResearchPageData
- Selected position state (for side panel)
- Drag-drop tag coordination
- Filter state coordination

**Key State:**
```typescript
interface ContainerState {
  activeTab: 'public' | 'private' | 'options'
  selectedPosition: Position | null  // For side panel
  sidePanelOpen: boolean
  filters: {
    search: string
    tags: string[]
    sector: string | null
    plFilter: 'all' | 'gainers' | 'losers'
    sort: 'weight' | 'returnEOY' | 'symbol' | 'pnl'
  }
}
```

**Layout:**
```tsx
<div className="min-h-screen bg-slate-900/bg-gray-50">
  {/* Page Header */}
  <section className="px-4 py-8 border-b">
    <h1>Research & Analyze</h1>
    <p>Position research, target prices, and analysis</p>
  </section>

  {/* Sticky Tag Bar */}
  <StickyTagBar tags={tags} onDragEnd={handleTagDrop} />

  {/* Tabs */}
  <Tabs value={activeTab} onValueChange={setActiveTab}>
    <TabsList>
      <TabsTrigger value="public">Public</TabsTrigger>
      <TabsTrigger value="private">Private</TabsTrigger>
      <TabsTrigger value="options">Options</TabsTrigger>
    </TabsList>

    {/* Filter Bar */}
    <ResearchFilterBar filters={filters} onFiltersChange={handleFiltersChange} />

    {/* Summary Metrics */}
    <SummaryMetricsBar metrics={aggregateMetrics} />

    {/* Tab Content */}
    <TabsContent value="public">
      <TabContent positions={filteredPublicPositions} onPositionClick={openSidePanel} />
    </TabsContent>

    {/* ... other tabs */}
  </Tabs>

  {/* Side Panel (Sheet) */}
  <Sheet open={sidePanelOpen} onOpenChange={setSidePanelOpen}>
    <SheetContent side="right" className="w-[500px]">
      <PositionSidePanel position={selectedPosition} />
    </SheetContent>
  </Sheet>
</div>
```

**Reuses from existing pages:**
- Tag bar logic from OrganizeContainer (lines 62-173, drag-drop handling)
- Filter logic from PublicPositionsContainer (lines 89-140, filter state)
- Aggregate metrics from PublicPositionsContainer (lines 216-256)

---

### 2. SimplifiedPositionCard (Clean, Click-to-Details)

**File**: `src/components/research-and-analyze/SimplifiedPositionCard.tsx`
**Lines**: ~100
**Props:**
```typescript
interface SimplifiedPositionCardProps {
  position: {
    id: string
    symbol: string
    marketValue: number
    pnlPercent: number
    quantity: number
    positionType: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP'
    sector: string
    tags: Tag[]
  }
  onClick: () => void
  onDrop: (tagId: string) => void  // For drag-drop tagging
  theme: 'dark' | 'light'
}
```

**Layout:**
```tsx
<div
  className="border rounded p-3 cursor-pointer hover:bg-slate-800/50 transition-all"
  onClick={onClick}
  onDragOver={handleDragOver}
  onDrop={handleDrop}
>
  {/* Top Row: Symbol + P&L */}
  <div className="flex items-center justify-between mb-2">
    <span className="text-lg font-bold text-white">{symbol}</span>
    <span className="text-sm font-semibold tabular-nums text-emerald-400">
      {formatPercentage(pnlPercent)}
    </span>
  </div>

  {/* Market Value */}
  <div className="text-xl font-bold tabular-nums text-orange-400 mb-1">
    {formatCurrency(marketValue)}
  </div>

  {/* Details */}
  <div className="text-xs text-slate-500">
    {quantity} shares | {positionType} | {sector}
  </div>

  {/* Tags */}
  {tags.length > 0 && (
    <div className="flex gap-1 mt-2 flex-wrap">
      {tags.map(tag => (
        <span
          key={tag.id}
          className="text-[10px] px-2 py-0.5 rounded"
          style={{ backgroundColor: `${tag.color}20`, color: tag.color }}
        >
          {tag.name}
        </span>
      ))}
    </div>
  )}
</div>
```

**Key Differences from ResearchPositionCard:**
- ❌ No inline target price editing (moved to side panel)
- ❌ No analyst estimates inline (moved to side panel)
- ✅ Cleaner, more compact (fits more on screen)
- ✅ Click anywhere → opens side panel
- ✅ Drop target for tag drag-drop

---

### 3. PositionSidePanel (5 Sections)

**File**: `src/components/research-and-analyze/PositionSidePanel.tsx`
**Lines**: ~250
**Props:**
```typescript
interface PositionSidePanelProps {
  position: Position | null
  onClose: () => void
}
```

**Layout (shadcn Sheet):**
```tsx
<SheetContent side="right" className="w-[500px] overflow-y-auto">
  <SheetHeader>
    <SheetTitle>{position.symbol} - Position Details</SheetTitle>
  </SheetHeader>

  {/* Section 1: Overview */}
  <div className="border-b py-4">
    <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
      OVERVIEW
    </h3>
    <div className="text-sm text-slate-400">
      <p className="font-medium text-white">{position.companyName}</p>
      <p>{position.quantity} shares @ ${position.currentPrice}</p>
      <p className="text-xl font-bold tabular-nums text-orange-400 my-2">
        Market Value: {formatCurrency(position.marketValue)}
      </p>
      <p>Avg Cost: {formatCurrency(position.avgCost)}</p>
      <p className={`text-sm font-semibold ${position.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
        Unrealized P&L: {formatCurrency(position.pnl)} ({formatPercentage(position.pnlPercent)})
      </p>
    </div>
  </div>

  {/* Section 2: Risk Metrics */}
  <div className="border-b py-4">
    <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
      RISK METRICS
    </h3>
    <div className="grid grid-cols-2 gap-2 text-sm">
      <div>
        <span className="text-slate-500">Beta:</span>{' '}
        <span className="font-semibold tabular-nums text-white">{position.beta?.toFixed(2) || 'N/A'}</span>
      </div>
      <div>
        <span className="text-slate-500">Volatility:</span>{' '}
        <span className="font-semibold tabular-nums text-white">{position.volatility ? `${position.volatility.toFixed(1)}%` : 'N/A'}</span>
      </div>
      <div className="col-span-2">
        <span className="text-slate-500">Sector:</span>{' '}
        <span className="font-medium text-white">{position.sector}</span>
      </div>
    </div>

    {/* Factor Exposures */}
    {position.factorExposures && (
      <div className="mt-3">
        <p className="text-xs text-slate-500 mb-1">Factor Exposures:</p>
        <ul className="text-xs space-y-1">
          <li>• Growth: <span className="font-semibold text-white">{position.factorExposures.growth > 0 ? '+' : ''}{position.factorExposures.growth.toFixed(1)}σ</span></li>
          <li>• Momentum: <span className="font-semibold text-white">{position.factorExposures.momentum > 0 ? '+' : ''}{position.factorExposures.momentum.toFixed(1)}σ</span></li>
          <li>• Size: <span className="font-semibold text-white">{position.factorExposures.size > 0 ? '+' : ''}{position.factorExposures.size.toFixed(1)}σ</span></li>
        </ul>
      </div>
    )}
  </div>

  {/* Section 3: Correlations ⭐ */}
  <CorrelationsSection positionSymbol={position.symbol} />

  {/* Section 4: Target Price */}
  <div className="border-b py-4">
    <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
      TARGET PRICE
    </h3>
    {position.targetPrice ? (
      <div className="text-sm">
        <p className="text-xl font-bold tabular-nums text-orange-400 mb-1">
          Target: ${position.targetPrice}
          <span className={`text-sm ml-2 ${position.targetReturn >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            (↑ {position.targetReturn}% upside)
          </span>
        </p>
        <p className="text-xs text-slate-500 mb-2">Set on: {formatDate(position.targetPriceDate)}</p>
        <Button size="sm" variant="outline" onClick={handleEditTarget}>Edit Target</Button>
      </div>
    ) : (
      <div>
        <p className="text-sm text-slate-400 mb-2">No target price set</p>
        <Button size="sm" onClick={handleSetTarget}>Set Target Price</Button>
      </div>
    )}
  </div>

  {/* Section 5: Quick Actions */}
  <div className="py-4">
    <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
      QUICK ACTIONS
    </h3>
    <div className="grid grid-cols-2 gap-2">
      <Button size="sm" variant="outline">Analyze Risk</Button>
      <Button size="sm" variant="outline">AI Explain ✨</Button>
      <Button size="sm" variant="outline">Edit Tags</Button>
      <Button size="sm" variant="outline">Set Target</Button>
    </div>
    <Button className="w-full mt-3" variant="secondary">Full Risk Analysis →</Button>
  </div>
</SheetContent>
```

**Data Sources:**
- Position data: From parent (already loaded)
- Correlations: usePositionCorrelations hook (computed from correlation matrix)
- Factor exposures: From position object (already has position_factor_exposures data)
- Target price: From position object (already has target_prices relation)

---

### 4. CorrelationsSection (Key Feature ⭐)

**File**: `src/components/research-and-analyze/CorrelationsSection.tsx`
**Lines**: ~100
**Props:**
```typescript
interface CorrelationsSectionProps {
  positionSymbol: string
}
```

**Implementation:**
```tsx
export function CorrelationsSection({ positionSymbol }: CorrelationsSectionProps) {
  const { theme } = useTheme()
  const { correlations, hasConcentrationRisk, riskMessage, loading } = usePositionCorrelations(positionSymbol)

  if (loading) {
    return <div className="py-4 text-center text-slate-500">Loading correlations...</div>
  }

  return (
    <div className="border-b py-4">
      <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
        CORRELATIONS
      </h3>

      {correlations.length > 0 ? (
        <>
          <p className="text-xs text-slate-500 mb-2">Highly correlated with:</p>
          <ul className="space-y-2">
            {correlations.map(({ symbol, correlation, marketValue }) => {
              const strength = Math.abs(correlation) > 0.85 ? 'very high' :
                               Math.abs(correlation) > 0.7 ? 'high' : 'moderate'

              return (
                <li key={symbol} className="flex items-center justify-between text-sm">
                  <div>
                    <span className="font-semibold text-white">{symbol}:</span>{' '}
                    <span className="tabular-nums text-orange-400">{correlation.toFixed(2)}</span>{' '}
                    <span className="text-xs text-slate-500">({strength})</span>
                  </div>
                  <span className="text-xs text-slate-500">{formatCurrency(marketValue)}</span>
                </li>
              )
            })}
          </ul>

          {/* Concentration Risk Warning */}
          {hasConcentrationRisk && (
            <div className={`mt-3 p-2 rounded text-xs border ${
              theme === 'dark'
                ? 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400'
                : 'bg-yellow-50 border-yellow-300 text-yellow-700'
            }`}>
              <span className="font-semibold">⚠ Concentration risk:</span> {riskMessage}
            </div>
          )}
        </>
      ) : (
        <p className="text-sm text-slate-400">No significant correlations found</p>
      )}
    </div>
  )
}
```

---

### 5. StickyTagBar (Drag-Drop Tagging)

**File**: `src/components/research-and-analyze/StickyTagBar.tsx`
**Lines**: ~120
**Props:**
```typescript
interface StickyTagBarProps {
  tags: Tag[]
  onCreateTag: () => void
  onRestoreSectorTags: () => void
}
```

**Implementation (Extract from OrganizeContainer):**
```tsx
export function StickyTagBar({ tags, onCreateTag, onRestoreSectorTags }: StickyTagBarProps) {
  const { theme } = useTheme()
  const [isVisible, setIsVisible] = useState(true)
  const [lastScrollY, setLastScrollY] = useState(0)

  // Auto-hide on scroll down, show on scroll up
  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false)  // Scrolling down
      } else {
        setIsVisible(true)   // Scrolling up
      }
      setLastScrollY(currentScrollY)
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [lastScrollY])

  const handleDragStart = (e: DragEvent, tagId: string) => {
    e.dataTransfer.setData('tagId', tagId)
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      className={`sticky top-0 z-40 transition-transform duration-300 ${
        isVisible ? 'translate-y-0' : '-translate-y-full'
      } ${
        theme === 'dark'
          ? 'bg-slate-900 border-b border-slate-700'
          : 'bg-white border-b border-slate-200'
      }`}
    >
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Tag Label */}
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mr-2">
            TAGS
          </span>

          {/* Draggable Tags */}
          {tags.map(tag => (
            <div
              key={tag.id}
              draggable
              onDragStart={(e) => handleDragStart(e, tag.id)}
              className="px-3 py-1.5 rounded text-xs font-medium cursor-move transition-all hover:scale-105"
              style={{
                backgroundColor: `${tag.color}20`,
                color: tag.color,
                border: `1px solid ${tag.color}40`
              }}
            >
              {tag.name}
            </div>
          ))}

          {/* Create Tag Button */}
          <Button
            size="sm"
            variant="outline"
            onClick={onCreateTag}
            className="text-xs"
          >
            + New Tag
          </Button>

          {/* Restore Sector Tags Button */}
          <Button
            size="sm"
            variant="default"
            onClick={onRestoreSectorTags}
            className="ml-auto text-xs"
          >
            Restore Sector Tags
          </Button>
        </div>
      </div>
    </div>
  )
}
```

**Drag-Drop Logic (Reuse from OrganizeContainer lines 62-135):**
- DragStart: Store tagId in dataTransfer
- DragOver: Prevent default, add visual feedback (border)
- Drop: Call tagsApi.tagPosition(positionId, tagId)
- Auto-scroll: If dragging near top/bottom of screen, auto-scroll

---

## Correlations Integration

### Backend Data Structure
```
GET /api/v1/analytics/portfolio/{id}/correlation-matrix

Response:
{
  "position_symbols": ["NVDA", "TSLA", "META", "AAPL", "MSFT", ...],
  "correlation_matrix": [
    [1.00, 0.15, 0.85, 0.78, 0.92, ...],  // NVDA correlations
    [0.15, 1.00, 0.20, 0.18, 0.16, ...],  // TSLA correlations
    [0.85, 0.20, 1.00, 0.75, 0.88, ...],  // META correlations
    [0.78, 0.18, 0.75, 1.00, 0.82, ...],  // AAPL correlations
    [0.92, 0.16, 0.88, 0.82, 1.00, ...],  // MSFT correlations
    ...
  ]
}
```

### Client-Side Hook: usePositionCorrelations

**File**: `src/hooks/usePositionCorrelations.ts`
**Lines**: ~80

```typescript
import { useMemo } from 'react'
import { useCorrelationMatrix } from './useCorrelationMatrix'
import { usePortfolioStore } from '@/stores/portfolioStore'

interface Correlation {
  symbol: string
  correlation: number
  marketValue: number
}

interface PositionCorrelationsResult {
  correlations: Correlation[]
  hasConcentrationRisk: boolean
  riskMessage: string | null
  loading: boolean
  error: string | null
}

export function usePositionCorrelations(positionSymbol: string): PositionCorrelationsResult {
  const { portfolioId } = usePortfolioStore()
  const { data: matrix, loading, error } = useCorrelationMatrix(portfolioId)
  const positions = usePositions({ portfolioId }) // Get all positions for market values

  const result = useMemo(() => {
    if (!matrix || !positions) {
      return {
        correlations: [],
        hasConcentrationRisk: false,
        riskMessage: null,
        loading: true,
        error: null
      }
    }

    // Find index of selected position in matrix
    const symbolIndex = matrix.position_symbols.indexOf(positionSymbol)
    if (symbolIndex === -1) {
      return {
        correlations: [],
        hasConcentrationRisk: false,
        riskMessage: 'Position not found in correlation matrix',
        loading: false,
        error: null
      }
    }

    // Extract correlations for this position
    const positionCorrelations = matrix.position_symbols
      .map((symbol, index) => ({
        symbol,
        correlation: matrix.correlation_matrix[symbolIndex][index],
        marketValue: positions.find(p => p.symbol === symbol)?.marketValue || 0
      }))
      .filter(c => c.symbol !== positionSymbol) // Exclude self (correlation = 1.0)
      .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation)) // Sort by strength
      .slice(0, 5) // Top 5

    // Calculate concentration risk
    const highCorrelations = positionCorrelations.filter(
      c => Math.abs(c.correlation) > 0.7
    )
    const hasConcentrationRisk = highCorrelations.length >= 2

    const riskMessage = hasConcentrationRisk
      ? `High correlation with ${highCorrelations.length} other positions reduces diversification benefits.`
      : null

    return {
      correlations: positionCorrelations,
      hasConcentrationRisk,
      riskMessage,
      loading: false,
      error: null
    }
  }, [matrix, positions, positionSymbol])

  return {
    ...result,
    loading: loading || result.loading,
    error: error || result.error
  }
}
```

**Why Client-Side Processing?**
- ✅ **No backend changes needed** - matrix is already computed and cached
- ✅ **Fast** - Client-side filtering is instant (array operations)
- ✅ **Flexible** - Easy to adjust thresholds (0.7 for "high" correlation)
- ✅ **Reusable** - Can call for any position without refetching full matrix

**Correlation Strength Thresholds:**
```typescript
const getCorrelationStrength = (correlation: number): string => {
  const abs = Math.abs(correlation)
  if (abs > 0.85) return 'very high'
  if (abs > 0.7) return 'high'
  if (abs > 0.5) return 'moderate'
  return 'low'
}
```

**Concentration Risk Logic:**
```typescript
// Risk warning triggers if:
// 1. Position has 2+ correlations > 0.7
// 2. OR position has 3+ correlations > 0.6
const hasConcentrationRisk =
  highCorrelations.length >= 2 || moderateCorrelations.length >= 3
```

---

## Tagging Integration

### Sticky Bar Behavior
- **Always visible** when scrolling up
- **Hides** when scrolling down (past 100px)
- **z-index: 40** (above content, below modals)
- **Sticky position** at top of page

### Drag-Drop Flow
```
User drags tag from StickyTagBar
        ↓
onDragStart: Store tagId in dataTransfer
        ↓
User drags over SimplifiedPositionCard
        ↓
onDragOver: Add border highlight (blue glow)
        ↓
User drops tag on card
        ↓
onDrop: Extract tagId from dataTransfer
        ↓
Call tagsApi.tagPosition(positionId, tagId)
        ↓
Optimistic update: Instantly show tag on card
        ↓
Backend confirms: Tag saved to database
        ↓
If error: Revert optimistic update, show error toast
```

### Tag Display on Cards
- Tags shown as colored badges below position info
- Max 3 tags visible, "+N more" for overflow
- Click tag badge → filter by that tag
- Small "x" on hover → remove tag (inline)

### Tag Management
- **Create new tag**: Click "+ New Tag" button → Modal with name + color picker
- **Restore sector tags**: Click "Restore Sector Tags" button → Auto-creates sector tags from company profiles
- **Edit tag**: Right-click tag badge → Edit modal (rename, recolor)
- **Delete tag**: In tag management modal (separate page, or expandable section)

---

## Day-by-Day Agent Workflow

### **DAY 1: Foundation & Data Layer** (Architecture + Data Agents in Parallel)

#### Morning: Architecture Agent

**Tasks:**
1. Create folder structure:
   ```
   /app/research-and-analyze/page.tsx
   /src/containers/ResearchAndAnalyzeContainer.tsx
   /src/components/research-and-analyze/
   ```
2. Set up routing: `/research-and-analyze` route
3. Create component skeletons (empty files with TypeScript interfaces)
4. Define TypeScript interfaces:
   - ContainerState
   - ResearchPageData
   - FilterState
   - TabConfig
5. Install/verify shadcn components: Tabs, Sheet, Button, Badge

**Deliverables:**
- ✅ Folder structure created
- ✅ Routing configured
- ✅ TypeScript interfaces defined
- ✅ Skeleton components created

**Files Created:**
- `app/research-and-analyze/page.tsx` (10 lines)
- `src/containers/ResearchAndAnalyzeContainer.tsx` (skeleton, 50 lines)
- `src/components/research-and-analyze/SimplifiedPositionCard.tsx` (skeleton)
- `src/components/research-and-analyze/PositionSidePanel.tsx` (skeleton)
- `src/components/research-and-analyze/StickyTagBar.tsx` (skeleton)
- `src/components/research-and-analyze/CorrelationsSection.tsx` (skeleton)

#### Afternoon: Data Integration Agent

**Tasks:**
1. Create `useResearchPageData` hook (~150 lines)
   - Integrates usePublicPositions, usePrivatePositions, useTags
   - Separates public positions into longs, shorts, options
   - Calculates aggregate metrics (total value, total P&L, count)
   - Returns categorized data for all 3 tabs
2. Create `usePositionCorrelations` hook (~80 lines)
   - Client-side processing of correlation matrix
   - Top 5 correlated positions
   - Concentration risk logic
3. Create `useSharedFilters` hook (~100 lines)
   - Search state (debounced 300ms)
   - Tag filter (multi-select)
   - Sector filter
   - P/L filter (gainers, losers, all)
   - Sort state
   - Filter function (applies all filters to position array)

**Deliverables:**
- ✅ 3 hooks created and tested
- ✅ Data loading works for all tabs
- ✅ Correlations computed correctly
- ✅ Filters apply correctly

**Files Created:**
- `src/hooks/useResearchPageData.ts` (~150 lines)
- `src/hooks/usePositionCorrelations.ts` (~80 lines)
- `src/hooks/useSharedFilters.ts` (~100 lines)

**CHECKPOINT 1**: Review architecture and data hooks, test data loading

---

### **DAY 2: Core UI Components** (3 Component Agents in Parallel)

#### Agent 1: Position Card Agent

**Tasks:**
1. Build `SimplifiedPositionCard.tsx` (~100 lines)
   - Clean card layout (symbol, value, P&L, details, tags)
   - Click handler to open side panel
   - Drag-drop target for tagging
   - Visual feedback on drag-over (blue border)
   - Tag badges display
   - Responsive (full width on mobile)
2. Apply Command Center styling:
   - Typography: tabular-nums, uppercase labels, font sizes
   - Colors: dark/light theme support
   - Spacing: tight padding (p-3)
   - Hover: subtle background change

**Deliverables:**
- ✅ SimplifiedPositionCard renders correctly
- ✅ Click opens side panel
- ✅ Drag-drop works (can drop tags)
- ✅ Styling matches Command Center

#### Agent 2: Side Panel Agent

**Tasks:**
1. Build `PositionSidePanel.tsx` (~250 lines)
   - shadcn Sheet component (right side, 500px width)
   - 5 sections: Overview, Risk Metrics, Correlations, Target Price, Quick Actions
   - Fetch detailed data on open (factor exposures, company profile)
   - Target price inline editing (reuse existing logic from ResearchPositionCard)
   - Quick action buttons (Analyze Risk, AI Explain, Edit Tags, Set Target)
2. Build `CorrelationsSection.tsx` (~100 lines)
   - Use usePositionCorrelations hook
   - Display top 5 correlations with strength labels
   - Show market value for each correlated position
   - Concentration risk warning (yellow box)
   - Handle loading/error states

**Deliverables:**
- ✅ Side panel opens/closes smoothly
- ✅ All 5 sections render correctly
- ✅ Correlations display with risk warning
- ✅ Target price editing works
- ✅ Styling consistent with Command Center

#### Agent 3: Sticky Bar & Filters Agent

**Tasks:**
1. Build `StickyTagBar.tsx` (~120 lines)
   - Extract drag-drop logic from OrganizeContainer (lines 62-135)
   - Sticky positioning (z-index 40)
   - Auto-hide on scroll down, show on scroll up
   - All tags as draggable badges
   - "+ New Tag" button
   - "Restore Sector Tags" button
2. Build `ResearchFilterBar.tsx` (~100 lines)
   - Search input (debounced 300ms)
   - Tag filter dropdown (multi-select)
   - Sector filter dropdown
   - P/L filter dropdown (All, Gainers, Losers)
   - Sort dropdown (Weight, Return EOY, Symbol, P&L)
   - Apply Command Center styling
3. Build `SummaryMetricsBar.tsx` (~80 lines)
   - Display: "X positions | $YYY total | +$ZZZ P&L (+W%)"
   - Sticky below filter bar (z-index 30)
   - Dynamic based on current tab + filters

**Deliverables:**
- ✅ Sticky tag bar works, hides on scroll down
- ✅ Drag-drop from tag bar to cards works
- ✅ All filters work correctly
- ✅ Summary metrics update dynamically

**CHECKPOINT 2**: Review all Day 2 components, test rendering and interactions

---

### **DAY 3: Tab Content & Integration** (Integration Agent)

#### Agent 4: Integration Agent

**Tasks:**
1. Wire up ResearchAndAnalyzeContainer (~450 lines)
   - Tab state management (Public, Private, Options)
   - Selected position state (for side panel)
   - Filter state coordination
   - Drag-drop tag coordination
   - Integrate all Day 2 components
2. Build `TabContent.tsx` (~120 lines)
   - Receives positions array, renders SimplifiedPositionCards
   - Groups by section (Longs, Shorts for Public tab)
   - Applies filters from useSharedFilters
   - Empty state if no positions match filters
3. Implement drag-drop handlers:
   - handleDragStart (on StickyTagBar)
   - handleDragOver (on SimplifiedPositionCard)
   - handleDrop (on SimplifiedPositionCard)
   - Call tagsApi.tagPosition
   - Optimistic update
4. Implement side panel handlers:
   - openSidePanel (on card click)
   - closeSidePanel (on sheet close)
   - handleEditTarget (in side panel)
   - handleSetTarget (in side panel)
5. Test all 3 tabs:
   - Public tab: Show longs, shorts, options in separate sections
   - Private tab: Show private positions
   - Options tab: Show long options, short options

**Deliverables:**
- ✅ All 3 tabs render correctly
- ✅ Filters work across all tabs
- ✅ Side panel opens/closes smoothly
- ✅ Drag-drop tagging works end-to-end
- ✅ Summary metrics update when switching tabs

**CHECKPOINT 3**: Full integration test, all features working

---

### **DAY 4: Polish, Mobile, QA** (Polish Agent + Mobile Agent in Parallel)

#### Morning: Mobile Responsive Agent

**Tasks:**
1. Make all components responsive:
   - SimplifiedPositionCard: Full width on mobile (<768px)
   - StickyTagBar: Hide on mobile, show "Tags" button → opens modal
   - ResearchFilterBar: Collapse into "Filters" button on mobile
   - PositionSidePanel: Full screen on mobile instead of side drawer
   - Summary metrics: Abbreviated on mobile (hide details)
2. Add mobile breakpoints:
   - Mobile: <768px
   - Tablet: 768-1023px
   - Desktop: ≥1024px
3. Test on mobile viewports:
   - iPhone 14 (390x844)
   - iPad Pro (1024x1366)
   - Samsung Galaxy S23 (360x780)
4. Touch optimizations:
   - Increase tap targets (min 44x44px)
   - Add touch feedback (active states)
   - Swipeable side panel dismiss

**Deliverables:**
- ✅ All components responsive
- ✅ Mobile looks good on real devices
- ✅ Touch interactions work smoothly

#### Afternoon: QA & Polish Agent

**Tasks:**
1. Unit tests for hooks:
   - useResearchPageData: Test data loading, categorization
   - usePositionCorrelations: Test correlation filtering, risk logic
   - useSharedFilters: Test filter combinations
2. E2E test scenarios (Playwright):
   - Navigate to /research-and-analyze
   - Switch between Public/Private/Options tabs
   - Drag tag from sticky bar onto position card
   - Click position → Side panel opens → Correlations displayed
   - Filter by tag → Only tagged positions shown
   - Search for "AAPL" → Only AAPL shown
3. Bug bash (manual testing):
   - Drag-drop edge cases (drag outside, rapid dragging)
   - Filter combinations (search + tag + sector + P/L)
   - Side panel data loading (slow network simulation)
   - Tag badge overflow (position with 5+ tags)
4. Performance check:
   - Large portfolios (63 positions) render smoothly
   - No memory leaks on tab switching
   - Correlation matrix computation fast (<100ms)
5. Accessibility audit:
   - Keyboard navigation (Tab, Enter, Escape)
   - Screen reader support (ARIA labels)
   - Color contrast (WCAG AA compliance)

**Deliverables:**
- ✅ All tests pass
- ✅ No critical bugs
- ✅ Performance acceptable
- ✅ Accessibility compliant

**CHECKPOINT 4**: Final QA pass, ready for user testing

---

### **DAY 5 (Optional): Advanced Features & Refinement**

#### Agent 5: Advanced Features Agent (Optional)

**Tasks (if time permits):**
1. Bulk operations:
   - Multi-select checkboxes on position cards
   - Bulk tag application modal
   - Export selected to CSV
2. Advanced filtering:
   - Date range filter (P&L over last 30/60/90 days)
   - Position size filter (Large, Medium, Small)
   - Investment class filter (combine with tabs)
3. Side panel enhancements:
   - Historical price chart (mini chart in side panel)
   - P&L timeline chart (daily P&L over last 30 days)
   - News feed integration (company news)
4. Performance optimizations:
   - Virtual scrolling for large position lists (>100 positions)
   - Memoization of expensive computations
   - Lazy loading of side panel data
5. Animations:
   - Smooth tab transitions
   - Side panel slide-in animation
   - Card hover effects (scale, shadow)

**Deliverables (if implemented):**
- ✅ Bulk operations functional
- ✅ Advanced filters working
- ✅ Side panel enhancements polished
- ✅ Performance optimized

**FINAL CHECKPOINT**: Demo-ready, production-ready, user acceptance testing

---

## Code Reuse Matrix

### Existing Components (Reuse As-Is or Extract)

| Component | Source | Reuse Strategy | Lines Reused |
|-----------|--------|----------------|--------------|
| ResearchPositionCard | Public/Private Positions | Reference for target price logic | ~100 |
| EnhancedPositionsSection | Public/Private Positions | Reference for filtering/sorting | ~150 |
| TagManager | Organize | Reuse for tag creation modal | ~80 |
| DragDropInterface | Organize | Extract drag-drop logic | ~120 |
| TagBadge | Organize | Reuse for tag display | ~30 |
| FilterBar | Portfolio Holdings | Reference for filter UI | ~80 |

**Total Reused**: ~560 lines

### Existing Hooks (Reuse As-Is)

| Hook | Source | Reuse Strategy | Lines Reused |
|------|--------|----------------|--------------|
| usePublicPositions | Public Positions | Use directly | ~150 |
| usePrivatePositions | Private Positions | Use directly | ~100 |
| useTags | Organize | Use directly | ~80 |
| useCorrelationMatrix | Risk Metrics | Use directly | ~100 |
| useFactorExposures | Risk Metrics | Use directly | ~100 |
| useRestoreSectorTags | Organize | Use directly | ~80 |

**Total Reused**: ~610 lines

### Existing Services (Reuse All)

| Service | Reuse Strategy | Lines Reused |
|---------|----------------|--------------|
| tagsApi | Use directly | ~150 |
| analyticsApi | Use directly | ~200 |
| portfolioService | Use directly | ~300 |
| positionApiService | Use directly | ~150 |

**Total Reused**: ~800 lines

### New Components (Build from Scratch)

| Component | Lines | Description |
|-----------|-------|-------------|
| ResearchAndAnalyzeContainer | ~450 | Main orchestrator |
| SimplifiedPositionCard | ~100 | Clean position card |
| PositionSidePanel | ~250 | Details drawer with 5 sections |
| CorrelationsSection | ~100 | Correlations display with risk warning |
| StickyTagBar | ~120 | Drag-drop tag bar |
| ResearchFilterBar | ~100 | Unified filter controls |
| SummaryMetricsBar | ~80 | Dynamic summary metrics |
| TabContent | ~120 | Tab content wrapper |

**Total New**: ~1,320 lines

### New Hooks (Build from Scratch)

| Hook | Lines | Description |
|------|-------|-------------|
| useResearchPageData | ~150 | Unified data management |
| usePositionCorrelations | ~80 | Correlation filtering & risk logic |
| useSharedFilters | ~100 | Filter state & logic |

**Total New**: ~330 lines

### Summary

**Total Reused Code**: ~1,970 lines (60%)
**Total New Code**: ~1,650 lines (40%)
**Grand Total**: ~3,620 lines

**Reuse Ratio**: 60% (aligns with audit estimate of 60-70%)

---

## Success Criteria

### Feature Completeness

✅ **Core Features**:
- [ ] 3 tabs functional (Public, Private, Options)
- [ ] Position cards display correctly with all data
- [ ] Side panel opens on click with 5 sections
- [ ] Correlations display with top 5 positions
- [ ] Concentration risk warning shows when appropriate
- [ ] Sticky tag bar with drag-drop tagging
- [ ] All filters work (search, tag, sector, P/L, sort)
- [ ] Summary metrics update dynamically
- [ ] Target price editing in side panel
- [ ] "Restore Sector Tags" button works

✅ **Data Accuracy**:
- [ ] Correlations computed correctly (matches backend matrix)
- [ ] Risk warnings trigger at correct thresholds (0.7 for "high")
- [ ] Aggregate metrics accurate (sum of filtered positions)
- [ ] Target returns calculate correctly
- [ ] P&L percentages accurate

✅ **User Experience**:
- [ ] No page navigation required (all in one page)
- [ ] Smooth transitions (tab switching, side panel)
- [ ] Fast (<100ms for filters, <500ms for tab switch)
- [ ] Visual feedback (drag-over, loading states)
- [ ] Error handling (graceful degradation)

### Technical Quality

✅ **Code Quality**:
- [ ] TypeScript compiles without errors
- [ ] No ESLint warnings
- [ ] All PropTypes defined
- [ ] Consistent naming conventions
- [ ] Comments on complex logic

✅ **Performance**:
- [ ] 63 positions render smoothly (<1s)
- [ ] Correlation computation fast (<100ms)
- [ ] No memory leaks on tab switching
- [ ] Smooth scrolling (60fps)
- [ ] Lighthouse performance >85

✅ **Testing**:
- [ ] Unit tests pass (hooks)
- [ ] E2E tests pass (user flows)
- [ ] Manual QA complete (bug bash)
- [ ] Tested on 3 browsers (Chrome, Firefox, Safari)
- [ ] Tested on mobile devices

✅ **Accessibility**:
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Screen reader support (ARIA labels)
- [ ] Color contrast WCAG AA compliant
- [ ] Focus indicators visible
- [ ] Semantic HTML structure

✅ **Design**:
- [ ] Matches mockup layout (lines 262-310)
- [ ] Follows Command Center styling (typography, colors, spacing)
- [ ] Bloomberg-inspired look (monospace numbers, uppercase labels)
- [ ] Dark/light theme support
- [ ] Responsive (mobile, tablet, desktop)

### Integration

✅ **Data Integration**:
- [ ] All backend APIs working correctly
- [ ] Correlation matrix fetched successfully
- [ ] Factor exposures displayed correctly
- [ ] Target prices sync correctly
- [ ] Tags apply/remove correctly

✅ **Navigation**:
- [ ] Accessible from main navigation
- [ ] URL routing works (/research-and-analyze)
- [ ] Back button works correctly
- [ ] Page refresh maintains state (filters)

✅ **Deprecation**:
- [ ] Public Positions page deprecated (or redirects)
- [ ] Private Positions page deprecated (or redirects)
- [ ] Organize page deprecated (or simplified to tag management only)
- [ ] Navigation dropdown updated

---

## Risk Mitigation

### Technical Risks

**Risk 1: Correlation matrix too large (performance)**
- **Likelihood**: Medium (if portfolio has 100+ positions)
- **Impact**: High (slow loading, UI freeze)
- **Mitigation**:
  - Client-side caching of matrix
  - Lazy load correlations (only when side panel opens)
  - Consider backend endpoint: `/api/v1/analytics/position/{id}/correlations` (top 10)

**Risk 2: Drag-drop conflicts with click handler**
- **Likelihood**: Medium
- **Impact**: Medium (UX confusion)
- **Mitigation**:
  - Use `onMouseDown` delay (200ms) before enabling drag
  - If click released quickly, treat as click (open side panel)
  - If drag detected, cancel click

**Risk 3: Side panel data loading slow**
- **Likelihood**: Low (all data already fetched)
- **Impact**: Medium (user waits)
- **Mitigation**:
  - Show skeleton loaders in side panel
  - Fetch correlations on hover (prefetch)
  - Cache correlation results per position

### User Experience Risks

**Risk 4: Users confused by deprecation of old pages**
- **Likelihood**: High
- **Impact**: Medium (support burden)
- **Mitigation**:
  - Add redirect from old pages to new page
  - Show migration banner: "We've combined Public, Private, and Organize into Research & Analyze"
  - Keep old pages temporarily with "New version available" banner

**Risk 5: Too much information in side panel**
- **Likelihood**: Medium
- **Impact**: Low (overwhelming)
- **Mitigation**:
  - Collapsible sections (expand/collapse each section)
  - Default: Overview + Correlations expanded, others collapsed
  - User preference saved to localStorage

**Risk 6: Sticky tag bar feels cluttered with many tags**
- **Likelihood**: High (users create many tags)
- **Impact**: Medium (hard to find tags)
- **Mitigation**:
  - Horizontal scroll for tag bar
  - Search/filter tags in bar
  - Group tags by category (Sector, Strategy, Custom)

### Data Risks

**Risk 7: Missing correlation data**
- **Likelihood**: Low (matrix computed nightly)
- **Impact**: Medium (correlations section empty)
- **Mitigation**:
  - Show fallback message: "Correlation data not yet available"
  - Add "Refresh" button to trigger batch computation
  - Graceful degradation (hide section if no data)

**Risk 8: Stale target prices**
- **Likelihood**: Low (user-managed data)
- **Impact**: Low (informational only)
- **Mitigation**:
  - Show "Last updated: X days ago" label
  - Highlight outdated targets (>90 days old)
  - Suggest refresh in side panel

---

## Appendix A: Component API Reference

### SimplifiedPositionCard

```typescript
interface SimplifiedPositionCardProps {
  position: {
    id: string
    symbol: string
    marketValue: number
    pnlPercent: number
    quantity: number
    positionType: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP'
    sector: string
    tags: Tag[]
  }
  onClick: () => void
  onDrop: (tagId: string) => void
  theme: 'dark' | 'light'
}

// Usage:
<SimplifiedPositionCard
  position={position}
  onClick={() => openSidePanel(position)}
  onDrop={handleTagDrop}
  theme={theme}
/>
```

### PositionSidePanel

```typescript
interface PositionSidePanelProps {
  position: Position | null
  onClose: () => void
}

// Usage:
<Sheet open={sidePanelOpen} onOpenChange={setSidePanelOpen}>
  <SheetContent side="right" className="w-[500px]">
    <PositionSidePanel
      position={selectedPosition}
      onClose={() => setSidePanelOpen(false)}
    />
  </SheetContent>
</Sheet>
```

### StickyTagBar

```typescript
interface StickyTagBarProps {
  tags: Tag[]
  onCreateTag: () => void
  onRestoreSectorTags: () => void
}

// Usage:
<StickyTagBar
  tags={tags}
  onCreateTag={handleCreateTag}
  onRestoreSectorTags={handleRestoreSectorTags}
/>
```

### CorrelationsSection

```typescript
interface CorrelationsSectionProps {
  positionSymbol: string
}

// Usage (inside PositionSidePanel):
<CorrelationsSection positionSymbol={position.symbol} />
```

### useResearchPageData

```typescript
interface ResearchPageDataResult {
  publicPositions: {
    longs: Position[]
    shorts: Position[]
    options: Position[]
  }
  privatePositions: Position[]
  tags: Tag[]
  aggregateMetrics: {
    totalValue: number
    totalPnl: number
    totalPnlPercent: number
    positionCount: number
  }
  loading: boolean
  error: string | null
}

// Usage:
const {
  publicPositions,
  privatePositions,
  tags,
  aggregateMetrics,
  loading,
  error
} = useResearchPageData()
```

### usePositionCorrelations

```typescript
interface PositionCorrelationsResult {
  correlations: Array<{
    symbol: string
    correlation: number
    marketValue: number
  }>
  hasConcentrationRisk: boolean
  riskMessage: string | null
  loading: boolean
  error: string | null
}

// Usage:
const {
  correlations,
  hasConcentrationRisk,
  riskMessage,
  loading,
  error
} = usePositionCorrelations('NVDA')
```

---

## Appendix B: Backend API Reference

### Required Endpoints (All Existing)

```
GET /api/v1/data/positions/details?portfolio_id={id}
- Returns all positions with details (qty, price, P&L, tags, etc.)

GET /api/v1/analytics/portfolio/{id}/correlation-matrix
- Returns NxN correlation matrix for all positions

GET /api/v1/analytics/portfolio/{id}/positions/factor-exposures
- Returns factor betas for each position

GET /api/v1/target-prices?portfolio_id={id}
- Returns all target prices for portfolio

GET /api/v1/tags?user_id={id}
- Returns all tags for user

POST /api/v1/position-tags
- Tags a position with a tag
Body: { position_id, tag_id }

DELETE /api/v1/position-tags/{id}
- Removes tag from position

POST /api/v1/data/positions/restore-sector-tags?portfolio_id={id}
- Auto-creates sector tags from company profiles
```

**No new backend endpoints needed** - all required APIs exist!

---

## Appendix C: Migration Guide

### Deprecating Old Pages

**Phase 1: Redirect (Week 1)**
```typescript
// app/public-positions/page.tsx
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function PublicPositionsPage() {
  const router = useRouter()

  useEffect(() => {
    // Show migration banner for 3 seconds
    setTimeout(() => {
      router.push('/research-and-analyze?tab=public')
    }, 3000)
  }, [router])

  return (
    <div className="p-8 text-center">
      <h1 className="text-2xl font-bold mb-4">We've moved!</h1>
      <p>Public Positions is now part of Research & Analyze.</p>
      <p className="text-sm text-slate-500 mt-2">Redirecting in 3 seconds...</p>
    </div>
  )
}
```

**Phase 2: Remove (Week 2)**
- Delete old page files
- Update navigation dropdown
- Remove references in documentation

### User Communication

**Email to Users:**
```
Subject: New Research & Analyze Page - All Your Positions in One Place!

Hi [Name],

We've consolidated Public Positions, Private Positions, and Organize into a single
"Research & Analyze" page to make it easier to manage all your positions.

What's New:
✅ 3 tabs: Switch between Public, Private, and Options with one click
✅ Click any position to see detailed risk metrics and correlations
✅ Drag tags from the top bar onto positions to organize them
✅ Faster workflow - no more page navigation!

The new page is live now at: /research-and-analyze

Your old pages will redirect automatically for the next week.

Questions? Reply to this email or check our help docs.

Best,
The SigmaSight Team
```

---

## Conclusion

This implementation plan provides a complete blueprint for building the Research & Analyze page in 4-5 days using specialized agents working in parallel. The plan emphasizes:

1. **High code reuse** (60%) - Leveraging existing components, hooks, and services
2. **Bloomberg-inspired design** - Following Command Center styling patterns
3. **Key feature: Correlations** - Client-side processing of correlation matrix with risk warnings
4. **Sticky tag bar** - Drag-drop tagging from Organize page
5. **Side panel** - Comprehensive position details without navigation
6. **No backend changes** - All required APIs already exist

**Next Steps:**
1. Review and approve this plan
2. Launch Architecture Agent (Day 1 morning)
3. Daily checkpoints for review and course-correction
4. Final demo on Day 4 or 5

**Estimated Total**: ~3,620 lines of code (1,650 new, 1,970 reused)

---

**Document End**

This plan is ready for execution. Upon approval, agents can begin implementation following the day-by-day workflow outlined above.
