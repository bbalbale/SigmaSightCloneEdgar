'use client'

import React, { useMemo, useEffect } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { useResearchStore } from '@/stores/researchStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useResearchPageData } from '@/hooks/useResearchPageData'
import { analyticsApi } from '@/services/analyticsApi'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { SimplifiedPositionCard } from '@/components/research-and-analyze/SimplifiedPositionCard'
import { PositionSidePanel } from '@/components/research-and-analyze/PositionSidePanel'
import { StickyTagBar } from '@/components/research-and-analyze/StickyTagBar'
import { ResearchFilterBar } from '@/components/research-and-analyze/ResearchFilterBar'
import { SummaryMetricsBar } from '@/components/research-and-analyze/SummaryMetricsBar'
import { TabContent } from '@/components/research-and-analyze/TabContent'
import { useRestoreSectorTags } from '@/hooks/useRestoreSectorTags'
import { CorrelationDebugger } from '@/components/research-and-analyze/CorrelationDebugger'
import tagsApi from '@/services/tagsApi'

export function ResearchAndAnalyzeContainer() {
  const { theme } = useTheme()

  // Portfolio ID
  const { portfolioId } = usePortfolioStore()

  // Zustand store state
  const activeTab = useResearchStore((state) => state.activeTab)
  const setActiveTab = useResearchStore((state) => state.setActiveTab)
  const sidePanelOpen = useResearchStore((state) => state.sidePanelOpen)
  const selectedPosition = useResearchStore((state) => state.selectedPosition)
  const openSidePanel = useResearchStore((state) => state.openSidePanel)
  const closeSidePanel = useResearchStore((state) => state.closeSidePanel)
  const filters = useResearchStore((state) => state.filters)
  const setSearch = useResearchStore((state) => state.setSearch)
  const clearFilters = useResearchStore((state) => state.clearFilters)
  const addOptimisticTag = useResearchStore((state) => state.addOptimisticTag)

  // Correlation matrix state and actions
  const setCorrelationMatrix = useResearchStore((state) => state.setCorrelationMatrix)
  const setCorrelationMatrixLoading = useResearchStore((state) => state.setCorrelationMatrixLoading)
  const setCorrelationMatrixError = useResearchStore((state) => state.setCorrelationMatrixError)

  // Data fetching
  const {
    publicPositions,
    privatePositions,
    tags,
    aggregateMetrics,
    loading,
    error
  } = useResearchPageData()

  const { restoreSectorTags, loading: restoringTags } = useRestoreSectorTags()

  // Fetch correlation matrix once on mount and store in Zustand
  useEffect(() => {
    const fetchCorrelationMatrix = async () => {
      if (!portfolioId) {
        console.log('🔍 Correlation Matrix: No portfolio ID available')
        setCorrelationMatrixError('No portfolio ID available')
        return
      }

      try {
        console.log('🔍 Correlation Matrix: Fetching for portfolio', portfolioId)
        setCorrelationMatrixLoading(true)
        setCorrelationMatrixError(null)

        const response = await analyticsApi.getCorrelationMatrix(portfolioId)
        console.log('🔍 Correlation Matrix: Raw backend response', response)

        // Transform backend nested dict structure to frontend flat arrays
        if (response.data?.available && response.data?.data?.matrix) {
          const backendMatrix = response.data.data.matrix
          const symbols = Object.keys(backendMatrix)

          // Build 2D array from nested dict
          const correlationMatrix = symbols.map(symbol1 =>
            symbols.map(symbol2 => backendMatrix[symbol1]?.[symbol2] ?? 0)
          )

          const transformedData = {
            position_symbols: symbols,
            correlation_matrix: correlationMatrix,
            lookback_days: response.data.metadata?.lookback_days || 90,
            min_overlap: response.data.metadata?.min_overlap || 30,
            data_quality: {
              total_pairs: response.data.data_quality?.total_pairs || 0,
              valid_pairs: response.data.data_quality?.valid_pairs || 0,
              coverage_percent: response.data.data_quality?.coverage_percent || 0
            }
          }

          console.log('✅ Correlation Matrix: Transformed', {
            symbolsCount: transformedData.position_symbols.length,
            matrixRows: transformedData.correlation_matrix.length,
            symbols: transformedData.position_symbols
          })

          setCorrelationMatrix(transformedData)
        } else {
          console.warn('⚠️ Correlation Matrix: No data available from backend')
          setCorrelationMatrix(null)
        }

        setCorrelationMatrixLoading(false)
      } catch (err) {
        console.error('❌ Correlation Matrix: Error fetching', err)
        setCorrelationMatrixError(err instanceof Error ? err.message : 'Failed to fetch correlation matrix')
        setCorrelationMatrixLoading(false)
      }
    }

    fetchCorrelationMatrix()
  }, [portfolioId, setCorrelationMatrix, setCorrelationMatrixLoading, setCorrelationMatrixError])

  // Get active positions for current tab
  const activePositions = useMemo(() => {
    if (activeTab === 'public') {
      return publicPositions.longs
    } else if (activeTab === 'options') {
      return publicPositions.options
    } else {
      return privatePositions
    }
  }, [activeTab, publicPositions, privatePositions])

  // Apply filters to active positions
  const filteredPositions = useMemo(() => {
    let positions = [...activePositions]

    // Search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      positions = positions.filter((p: any) =>
        p.symbol?.toLowerCase().includes(searchLower) ||
        p.company_name?.toLowerCase().includes(searchLower)
      )
    }

    // Tag filter
    if (filters.selectedTags.length > 0) {
      positions = positions.filter((p: any) =>
        p.tags?.some((tag: any) => filters.selectedTags.includes(tag.id))
      )
    }

    // Sector filter
    if (filters.selectedSector) {
      positions = positions.filter((p: any) => p.sector === filters.selectedSector)
    }

    // P&L filter
    if (filters.plFilter === 'gainers') {
      positions = positions.filter((p: any) => (p.unrealized_pnl_percent || 0) > 0)
    } else if (filters.plFilter === 'losers') {
      positions = positions.filter((p: any) => (p.unrealized_pnl_percent || 0) < 0)
    }

    // Sort
    positions.sort((a: any, b: any) => {
      let aVal = 0, bVal = 0

      switch (filters.sort) {
        case 'weight':
          aVal = Math.abs(a.current_market_value || a.marketValue || 0)
          bVal = Math.abs(b.current_market_value || b.marketValue || 0)
          break
        case 'returnEOY':
          aVal = a.target_return_eoy || 0
          bVal = b.target_return_eoy || 0
          break
        case 'symbol':
          return filters.sortDirection === 'asc'
            ? a.symbol.localeCompare(b.symbol)
            : b.symbol.localeCompare(a.symbol)
        case 'pnl':
          aVal = a.unrealized_pnl_percent || 0
          bVal = b.unrealized_pnl_percent || 0
          break
      }

      return filters.sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })

    return positions
  }, [activePositions, filters])

  // Handle tag drop on position
  const handleTagDrop = async (positionId: string, tagId: string) => {
    // Optimistic update
    addOptimisticTag(positionId, tagId)

    try {
      await tagsApi.tagPosition(positionId, tagId)
      // Success - refetch to get updated data
      // refetch() // Can add this if needed
    } catch (error) {
      console.error('Failed to tag position:', error)
      // Could add removeOptimisticTag here for rollback
    }
  }

  const handleCreateTag = () => {
    // TODO: Implement tag creation modal
    console.log('Create tag clicked')
  }

  const handleRestoreSectorTags = async () => {
    try {
      await restoreSectorTags()
      // Tags will be refetched automatically by useResearchPageData
    } catch (error) {
      console.error('Failed to restore sector tags:', error)
    }
  }

  if (loading && !publicPositions.longs.length) {
    return (
      <div className="min-h-screen transition-colors duration-300 bg-primary">
        <div className="flex items-center justify-center py-20">
          <p className="text-secondary">Loading positions...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen transition-colors duration-300 bg-primary">
        <div className="flex items-center justify-center py-20">
          <p className="text-red-400">Error: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen transition-colors duration-300 bg-primary">
      {/* Page Header */}
      <section className={`px-4 py-8 border-b transition-colors duration-300 ${
        theme === 'dark' ? 'border-primary' : 'border-slate-200'
      }`}>
        <div className="container mx-auto">
          <div className="flex items-start justify-between">
            <div>
              <h1 className={`text-3xl font-bold ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                Research & Analyze
              </h1>
              <p className="mt-2 text-lg text-secondary">
                Position research, target prices, and analysis
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Sticky Tag Bar */}
      <StickyTagBar
        tags={tags}
        onCreateTag={handleCreateTag}
        onRestoreSectorTags={handleRestoreSectorTags}
      />

      {/* Tabs Section */}
      <section className="px-4 pt-4">
        <div className="container mx-auto">
          <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)}>
            <TabsList>
              <TabsTrigger value="public">Public</TabsTrigger>
              <TabsTrigger value="options">Options</TabsTrigger>
              <TabsTrigger value="private">Private</TabsTrigger>
            </TabsList>

            {/* Filter Bar */}
            <div className="mt-4">
              <ResearchFilterBar
                filters={filters}
                onSearchChange={setSearch}
                onClearFilters={clearFilters}
              />
            </div>

            {/* Summary Metrics */}
            <SummaryMetricsBar metrics={aggregateMetrics} />

            {/* Tab Content */}
            <TabsContent value="public" className="mt-4">
              <TabContent
                positions={filteredPositions}
                onPositionClick={openSidePanel}
                onTagDrop={handleTagDrop}
                theme={theme}
              />
            </TabsContent>

            <TabsContent value="options" className="mt-4">
              <TabContent
                positions={filteredPositions}
                onPositionClick={openSidePanel}
                onTagDrop={handleTagDrop}
                theme={theme}
              />
            </TabsContent>

            <TabsContent value="private" className="mt-4">
              <TabContent
                positions={filteredPositions}
                onPositionClick={openSidePanel}
                onTagDrop={handleTagDrop}
                theme={theme}
              />
            </TabsContent>
          </Tabs>
        </div>
      </section>

      {/* Side Panel */}
      <Sheet open={sidePanelOpen} onOpenChange={closeSidePanel}>
        <SheetContent side="right" className="w-[500px] overflow-y-auto">
          <PositionSidePanel
            position={selectedPosition}
            onClose={closeSidePanel}
          />
        </SheetContent>
      </Sheet>

      {/* DEBUG: Correlation Matrix State - Remove after debugging */}
      <CorrelationDebugger />
    </div>
  )
}
