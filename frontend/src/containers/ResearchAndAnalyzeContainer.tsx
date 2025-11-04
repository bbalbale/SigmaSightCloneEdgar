'use client'

import React, { useMemo, useEffect, useState } from 'react'
import { useResearchStore } from '@/stores/researchStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { usePublicPositions } from '@/hooks/usePublicPositions'
import { usePrivatePositions } from '@/hooks/usePrivatePositions'
import { analyticsApi } from '@/services/analyticsApi'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ResearchTableView } from '@/components/research-and-analyze/ResearchTableView'
import { CompactTagBar } from '@/components/research-and-analyze/CompactTagBar'
import { ViewAllTagsModal } from '@/components/research-and-analyze/ViewAllTagsModal'
import { TagCreator } from '@/components/organize/TagCreator'
import { useRestoreSectorTags } from '@/hooks/useRestoreSectorTags'
import { useTags } from '@/hooks/useTags'
import { usePositionTags } from '@/hooks/usePositionTags'
import tagsApi from '@/services/tagsApi'
import { positionResearchService, type EnhancedPosition } from '@/services/positionResearchService'

export function ResearchAndAnalyzeContainer() {
  // Portfolio ID
  const { portfolioId } = usePortfolioStore()

  // Zustand store state
  const activeTab = useResearchStore((state) => state.activeTab)
  const setActiveTab = useResearchStore((state) => state.setActiveTab)

  // Correlation matrix state and actions
  const setCorrelationMatrix = useResearchStore((state) => state.setCorrelationMatrix)
  const setCorrelationMatrixLoading = useResearchStore((state) => state.setCorrelationMatrixLoading)
  const setCorrelationMatrixError = useResearchStore((state) => state.setCorrelationMatrixError)

  // Modal and UI state
  const [showViewAllModal, setShowViewAllModal] = React.useState(false)
  const [showTagCreator, setShowTagCreator] = React.useState(false)

  // Position type filter state (long/short)
  const [positionType, setPositionType] = useState<'long' | 'short'>('long')

  // Filter and sort state
  const [filterBy, setFilterBy] = useState<'all' | 'tag' | 'sector' | 'industry'>('all')
  const [filterValue, setFilterValue] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'percent_of_equity' | 'symbol' | 'target_return_eoy'>('percent_of_equity')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Data fetching - PHASE 1: Replace useResearchPageData with proven hooks
  const {
    longPositions,
    shortPositions,
    loading: publicLoading,
    error: publicError,
    aggregateReturns: publicAggregates,
    updatePositionTargetOptimistic: updatePublicTarget,
    refetch: refetchPublicPositions
  } = usePublicPositions()

  const {
    positions: privatePositions,
    loading: privateLoading,
    error: privateError,
    aggregateReturns: privateAggregates,
    updatePositionTargetOptimistic: updatePrivateTarget,
    refetch: refetchPrivatePositions
  } = usePrivatePositions()

  const { restoreTags, loading: restoringTags } = useRestoreSectorTags()

  // Tag management hooks
  const {
    tags: allTags,
    createTag,
    deleteTag,
    loading: tagsLoading
  } = useTags()

  const {
    addTagsToPosition,
    removeTagsFromPosition,
    loading: positionTagsLoading
  } = usePositionTags()

  // Get tags from public positions (they include tags) - kept for backwards compatibility
  const tags = useMemo(() => {
    const tagMap = new Map()
    const allPositions = [...longPositions, ...shortPositions, ...privatePositions]
    allPositions.forEach((pos: any) => {
      if (pos.tags) {
        pos.tags.forEach((tag: any) => {
          if (!tagMap.has(tag.id)) {
            tagMap.set(tag.id, tag)
          }
        })
      }
    })
    return Array.from(tagMap.values())
  }, [longPositions, shortPositions, privatePositions])

  // PHASE 2: Separate positions by type
  // usePublicPositions returns both PUBLIC and OPTIONS mixed together
  // Match the logic from PublicPositionsContainer - use position_type as source of truth

  // Helper to check if position is an option (same as PublicPositionsContainer)
  const isOption = (position: EnhancedPosition) => {
    return position.investment_class === 'OPTIONS' ||
           ['LC', 'LP', 'SC', 'SP'].includes(position.position_type as string)
  }

  const publicPositions = useMemo(() =>
    [...longPositions, ...shortPositions].filter(p => !isOption(p)),
    [longPositions, shortPositions]
  )

  const optionsPositions = useMemo(() =>
    [...longPositions, ...shortPositions].filter(p => isOption(p)),
    [longPositions, shortPositions]
  )

  // Separate public equities by long/short
  const publicLongs = useMemo(() =>
    publicPositions.filter(p => p.position_type === 'LONG'),
    [publicPositions]
  )

  const publicShorts = useMemo(() =>
    publicPositions.filter(p => p.position_type === 'SHORT'),
    [publicPositions]
  )

  // Separate options by long/short (using position_type codes)
  const optionLongs = useMemo(() =>
    optionsPositions.filter(p => ['LC', 'LP'].includes(p.position_type as string)),
    [optionsPositions]
  )

  const optionShorts = useMemo(() =>
    optionsPositions.filter(p => ['SC', 'SP'].includes(p.position_type as string)),
    [optionsPositions]
  )

  // PHASE 3: Calculate aggregate returns for all position groups
  const aggregates = useMemo(() => {
    return {
      // Section-level aggregates for Public tab
      publicLongs: {
        eoy: positionResearchService.calculateAggregateReturn(publicLongs, 'target_return_eoy', 'analyst_return_eoy'),
        nextYear: positionResearchService.calculateAggregateReturn(publicLongs, 'target_return_next_year')
      },
      publicShorts: {
        eoy: positionResearchService.calculateAggregateReturn(publicShorts, 'target_return_eoy', 'analyst_return_eoy'),
        nextYear: positionResearchService.calculateAggregateReturn(publicShorts, 'target_return_next_year')
      },

      // Section-level aggregates for Options tab
      optionLongs: {
        eoy: positionResearchService.calculateAggregateReturn(optionLongs, 'target_return_eoy', 'analyst_return_eoy'),
        nextYear: positionResearchService.calculateAggregateReturn(optionLongs, 'target_return_next_year')
      },
      optionShorts: {
        eoy: positionResearchService.calculateAggregateReturn(optionShorts, 'target_return_eoy', 'analyst_return_eoy'),
        nextYear: positionResearchService.calculateAggregateReturn(optionShorts, 'target_return_next_year')
      },
      allOptions: {
        eoy: positionResearchService.calculateAggregateReturn(optionsPositions, 'target_return_eoy', 'analyst_return_eoy'),
        nextYear: positionResearchService.calculateAggregateReturn(optionsPositions, 'target_return_next_year')
      },

      // Private investments
      private: {
        eoy: privateAggregates.eoy,
        nextYear: privateAggregates.next_year
      }
    }
  }, [publicPositions, optionsPositions, privatePositions, publicLongs, publicShorts, optionLongs, optionShorts, privateAggregates])

  // PHASE 4: Filter positions based on active tab and position type
  const { basePositions, currentAggregate } = useMemo(() => {
    let positions: EnhancedPosition[] = []
    let aggregate = { eoy: 0, nextYear: 0 }

    if (activeTab === 'public') {
      positions = positionType === 'long' ? publicLongs : publicShorts
      aggregate = positionType === 'long' ? aggregates.publicLongs : aggregates.publicShorts
    } else if (activeTab === 'options') {
      positions = positionType === 'long' ? optionLongs : optionShorts
      aggregate = positionType === 'long' ? aggregates.optionLongs : aggregates.optionShorts
    } else if (activeTab === 'private') {
      positions = privatePositions
      aggregate = aggregates.private
    }

    return { basePositions: positions, currentAggregate: aggregate }
  }, [activeTab, positionType, publicLongs, publicShorts, optionLongs, optionShorts, privatePositions, aggregates])

  // Filter options based on current base positions
  const filterOptions = useMemo(() => {
    if (filterBy === 'tag') {
      const tags = new Set<string>()
      basePositions.forEach(p => p.tags?.forEach(t => tags.add(t.name)))
      return Array.from(tags).sort()
    }
    if (filterBy === 'sector') {
      return Array.from(new Set(basePositions.map(p => p.sector).filter((s): s is string => Boolean(s)))).sort()
    }
    if (filterBy === 'industry') {
      return Array.from(new Set(basePositions.map(p => p.industry).filter((i): i is string => Boolean(i)))).sort()
    }
    return []
  }, [basePositions, filterBy])

  // Apply additional filtering and sorting
  const filteredPositions = useMemo(() => {
    // Filter
    let filtered = basePositions
    if (filterBy !== 'all' && filterValue !== 'all') {
      filtered = basePositions.filter(p => {
        if (filterBy === 'tag') {
          return p.tags?.some(t => t.name === filterValue)
        }
        if (filterBy === 'sector') {
          return p.sector === filterValue
        }
        if (filterBy === 'industry') {
          return p.industry === filterValue
        }
        return true
      })
    }

    // Sort
    return [...filtered].sort((a, b) => {
      const aValue = a[sortBy] as any
      const bValue = b[sortBy] as any

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortOrder === 'asc' ? aValue - bValue : bValue - aValue
      }

      return sortOrder === 'asc'
        ? String(aValue || '').localeCompare(String(bValue || ''))
        : String(bValue || '').localeCompare(String(aValue || ''))
    })
  }, [basePositions, filterBy, filterValue, sortBy, sortOrder])

  // Calculate aggregate returns for FILTERED positions (weighted by % of equity)
  const filteredAggregate = useMemo(() => {
    return {
      eoy: positionResearchService.calculateAggregateReturn(filteredPositions, 'target_return_eoy', 'analyst_return_eoy'),
      nextYear: positionResearchService.calculateAggregateReturn(filteredPositions, 'target_return_next_year')
    }
  }, [filteredPositions])

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

          const metadata = response.data.metadata
          const dataQuality = response.data.data?.data_quality || response.data.data_quality

          const transformedData = {
            position_symbols: symbols,
            correlation_matrix: correlationMatrix,
            lookback_days: metadata?.lookback_days ?? 90,
            min_overlap: metadata?.min_overlap ?? response.data.min_overlap ?? 30,
            data_quality: {
              total_pairs: dataQuality?.total_pairs ?? 0,
              valid_pairs: dataQuality?.valid_pairs ?? 0,
              coverage_percent: dataQuality?.coverage_percent ?? 0
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

  // Tag creation handler
  const handleCreateTag = async (name: string, color: string) => {
    try {
      await createTag(name, color)
      console.log(`Tag "${name}" created`)
      // Tags will be refetched automatically by useTags hook
    } catch (error) {
      console.error('Failed to create tag:', error)
      throw error
    }
  }

  // Tag deletion handler
  const handleDeleteTag = async (tagId: string) => {
    try {
      await deleteTag(tagId)
      console.log(`Tag ${tagId} deleted`)
      // Note: We may want to refresh positions here to update UI
    } catch (error) {
      console.error('Failed to delete tag:', error)
      throw error
    }
  }

  // Tag drop handler - when user drags tag onto a position row
  const handleTagDrop = async (positionId: string, tagId: string) => {
    console.log('handleTagDrop called:', { positionId, tagId })

    if (!positionId || !tagId) {
      console.error('Missing positionId or tagId:', { positionId, tagId })
      return
    }

    try {
      await addTagsToPosition(positionId, [tagId], false) // false = don't replace existing
      console.log(`Tag ${tagId} added to position ${positionId}`)

      // Invalidate cache so refetch gets fresh data with new tags
      positionResearchService.invalidateAllCache(portfolioId!)
      console.log('Cache invalidated after tag drop')

      // Refetch positions to show updated tags immediately
      await Promise.all([
        refetchPublicPositions(),
        refetchPrivatePositions()
      ])
      console.log('Positions refetched after tag drop')
    } catch (error) {
      console.error('Failed to add tag to position:', error)
    }
  }

  // Tag removal handler - when user removes tag from position
  const handleRemoveTag = async (positionId: string, tagId: string) => {
    console.log('handleRemoveTag called:', { positionId, tagId })

    if (!positionId || !tagId) {
      console.error('Missing positionId or tagId:', { positionId, tagId })
      return
    }

    try {
      await removeTagsFromPosition(positionId, [tagId])
      console.log(`Tag ${tagId} removed from position ${positionId}`)

      // Invalidate cache so refetch gets fresh data with updated tags
      positionResearchService.invalidateAllCache(portfolioId!)
      console.log('Cache invalidated after tag removal')

      // Refetch positions to show updated tags immediately
      await Promise.all([
        refetchPublicPositions(),
        refetchPrivatePositions()
      ])
      console.log('Positions refetched after tag removal')
    } catch (error) {
      console.error('Failed to remove tag from position:', error)
    }
  }

  const handleRestoreSectorTags = async () => {
    try {
    if (!portfolioId) {
      console.warn('[ResearchAndAnalyze] No portfolio ID available for sector tag restoration')
      return
    }

    await restoreTags(portfolioId)

      // Invalidate cache so refetch gets fresh data with restored tags
      positionResearchService.invalidateAllCache(portfolioId!)
      console.log('Cache invalidated after restoring sector tags')

      // Refetch positions to show restored tags immediately
      await Promise.all([
        refetchPublicPositions(),
        refetchPrivatePositions()
      ])
      console.log('Positions refetched after restoring sector tags')
    } catch (error) {
      console.error('Failed to restore sector tags:', error)
    }
  }


  // Loading state
  const loading = publicLoading || privateLoading
  const error = publicError || privateError

  if (loading && !publicPositions.length && !optionsPositions.length && !privatePositions.length) {
    return (
      <div className="min-h-screen transition-colors duration-300" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <div className="flex items-center justify-center py-20">
          <p style={{ color: 'var(--text-secondary)' }}>Loading positions...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen transition-colors duration-300" style={{ backgroundColor: 'var(--bg-primary)' }}>
        <div className="flex items-center justify-center py-20">
          <p style={{ color: 'var(--color-error)' }}>Error: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen transition-colors duration-300" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Page Description */}
      <div className="px-4 pt-4 pb-2">
        <div className="container mx-auto">
          <p className="text-sm text-muted-foreground">
            Position research, target prices, and analysis
          </p>
        </div>
      </div>

      {/* STICKY SECTION #1: Position Tags */}
      <section
        className="sticky z-50 transition-colors duration-300"
        style={{
          top: 0,
          backgroundColor: 'var(--bg-primary)'
        }}
      >
        <div className="container mx-auto px-4 py-4">
          <div
            className="rounded-lg px-4 py-3 transition-all duration-300"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-primary)'
            }}
          >
            <h2
              className="text-lg font-semibold mb-3 transition-colors duration-300"
              style={{
                color: 'var(--color-accent)'
              }}
            >
              Position Tags
            </h2>
            <CompactTagBar
              tags={allTags}
              onViewAll={() => setShowViewAllModal(true)}
              onCreate={() => setShowTagCreator(true)}
            />
          </div>
        </div>
      </section>

      {/* STICKY SECTION #2: Position Controls, Filters & Returns */}
      <section
        className="sticky z-40 transition-colors duration-300"
        style={{
          top: '100px',
          backgroundColor: 'var(--bg-primary)'
        }}
      >
        <div className="container mx-auto px-4 pb-4">
          <div
            className="rounded-lg px-4 py-4 transition-all duration-300"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-primary)'
            }}
          >
            {/* Row 1: Positions Header, Tabs, and Returns */}
            <div className="flex items-center justify-between mb-4">
              {/* Left: Positions Header + Tabs */}
              <div className="flex items-center gap-4">
                <h2
                  className="text-lg font-semibold flex-shrink-0 transition-colors duration-300"
                  style={{
                    color: 'var(--color-accent)'
                  }}
                >
                  Positions
                </h2>

                {/* Investment Class Tabs */}
                <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)} className="flex-shrink-0">
                  <TabsList>
                    <TabsTrigger value="public">Public</TabsTrigger>
                    <TabsTrigger value="options">Options</TabsTrigger>
                    <TabsTrigger value="private">Private</TabsTrigger>
                  </TabsList>
                </Tabs>

                {/* Position Type Toggles (hidden for Private) - styled as tabs */}
                {activeTab !== 'private' && (
                  <Tabs value={positionType} onValueChange={(value: any) => setPositionType(value)} className="flex-shrink-0">
                    <TabsList>
                      <TabsTrigger value="long">Long</TabsTrigger>
                      <TabsTrigger value="short">Short</TabsTrigger>
                    </TabsList>
                  </Tabs>
                )}
              </div>

              {/* Right: Aggregate Returns with Full Labels */}
              <div className="flex gap-6 flex-shrink-0">
                <div className="text-right">
                  <div
                    className="mb-1"
                    style={{
                      fontSize: '11px',
                      fontWeight: 500,
                      color: 'var(--text-secondary)'
                    }}
                  >
                    Expected Return EOY
                  </div>
                  <div
                    className="text-xl font-bold tabular-nums"
                    style={{
                      color: filteredAggregate.eoy >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                    }}
                  >
                    {filteredAggregate.eoy >= 0 ? '+' : ''}{filteredAggregate.eoy.toFixed(1)}%
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className="mb-1"
                    style={{
                      fontSize: '11px',
                      fontWeight: 500,
                      color: 'var(--text-secondary)'
                    }}
                  >
                    Expected Return Next Year
                  </div>
                  <div
                    className="text-xl font-bold tabular-nums"
                    style={{
                      color: filteredAggregate.nextYear >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                    }}
                  >
                    {filteredAggregate.nextYear >= 0 ? '+' : ''}{filteredAggregate.nextYear.toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Row 2: Filter and Sort Controls */}
            <div className="flex items-center justify-between gap-3">
              {/* Left: Filter Controls */}
              <div className="flex items-center gap-3">
                <Select value={filterBy} onValueChange={(v: any) => { setFilterBy(v); setFilterValue('all') }}>
                  <SelectTrigger className="w-[180px] transition-colors duration-300" style={{
                    backgroundColor: 'var(--bg-primary)',
                    borderColor: 'var(--border-primary)'
                  }}>
                    <SelectValue placeholder="Filter by..." />
                  </SelectTrigger>
                  <SelectContent className="themed-card">
                    <SelectItem value="all">All Positions</SelectItem>
                    <SelectItem value="tag">Filter by Tag</SelectItem>
                    <SelectItem value="sector">Filter by Sector</SelectItem>
                    <SelectItem value="industry">Filter by Industry</SelectItem>
                  </SelectContent>
                </Select>

                {filterBy !== 'all' && filterOptions.length > 0 && (
                  <Select value={filterValue} onValueChange={setFilterValue}>
                    <SelectTrigger className="w-[200px] transition-colors duration-300" style={{
                      backgroundColor: 'var(--bg-primary)',
                      borderColor: 'var(--border-primary)'
                    }}>
                      <SelectValue placeholder={`Select ${filterBy}...`} />
                    </SelectTrigger>
                    <SelectContent className="themed-card">
                      <SelectItem value="all">All {filterBy}s</SelectItem>
                      {filterOptions.map(option => (
                        <SelectItem key={option} value={option}>{option}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              {/* Right: Sort Controls */}
              <div className="flex items-center gap-3">
                <Select value={sortBy} onValueChange={(v: any) => setSortBy(v)}>
                  <SelectTrigger className="w-[180px] transition-colors duration-300" style={{
                    backgroundColor: 'var(--bg-primary)',
                    borderColor: 'var(--border-primary)'
                  }}>
                    <SelectValue placeholder="Sort by..." />
                  </SelectTrigger>
                  <SelectContent className="themed-card">
                    <SelectItem value="percent_of_equity">% of Portfolio</SelectItem>
                    <SelectItem value="symbol">Symbol (A-Z)</SelectItem>
                    <SelectItem value="target_return_eoy">Return EOY</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={sortOrder} onValueChange={(v: any) => setSortOrder(v)}>
                  <SelectTrigger className="w-[140px] transition-colors duration-300" style={{
                    backgroundColor: 'var(--bg-primary)',
                    borderColor: 'var(--border-primary)'
                  }}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="themed-card">
                    <SelectItem value="desc">High to Low</SelectItem>
                    <SelectItem value="asc">Low to High</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SCROLLING CONTENT: Single Unified Table */}
      <div className="container mx-auto px-4 py-2">
        <ResearchTableView
          positions={filteredPositions}
          title=""
          aggregateReturnEOY={filteredAggregate.eoy}
          aggregateReturnNextYear={filteredAggregate.nextYear}
          onTargetPriceUpdate={updatePublicTarget}
          onTagDrop={handleTagDrop}
          onRemoveTag={handleRemoveTag}
        />
      </div>

      {/* View All Tags Modal */}
      <ViewAllTagsModal
        open={showViewAllModal}
        onOpenChange={setShowViewAllModal}
        tags={allTags}
        onCreate={handleCreateTag}
        onDelete={handleDeleteTag}
      />

      {/* Tag Creator Modal */}
      {showTagCreator && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-xl max-w-md w-full">
            <TagCreator
              onCreate={async (name: string, color: string) => {
                await handleCreateTag(name, color)
                setShowTagCreator(false)
              }}
              onCancel={() => setShowTagCreator(false)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
