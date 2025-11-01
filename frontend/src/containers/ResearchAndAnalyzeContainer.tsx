'use client'

import React, { useMemo, useEffect, useState } from 'react'
import { useResearchStore } from '@/stores/researchStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { usePublicPositions } from '@/hooks/usePublicPositions'
import { usePrivatePositions } from '@/hooks/usePrivatePositions'
import { analyticsApi } from '@/services/analyticsApi'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
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

  const { restoreSectorTags, loading: restoringTags } = useRestoreSectorTags()

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
  const { filteredPositions, currentAggregate } = useMemo(() => {
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

    return { filteredPositions: positions, currentAggregate: aggregate }
  }, [activeTab, positionType, publicLongs, publicShorts, optionLongs, optionShorts, privatePositions, aggregates])

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
      await restoreSectorTags()

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
              className="mb-3 font-semibold"
              style={{
                fontSize: '16px',
                color: 'var(--text-primary)'
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

      {/* STICKY SECTION #2: Position Controls & Returns */}
      <section
        className="sticky z-40 transition-colors duration-300"
        style={{
          top: '100px',
          backgroundColor: 'var(--bg-primary)'
        }}
      >
        <div className="container mx-auto px-4 pb-4">
          <div
            className="rounded-lg px-4 py-3 transition-all duration-300"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-primary)'
            }}
          >
            <div className="flex items-center gap-6">
              {/* Left: Positions Header + Controls */}
              <div className="flex-1 flex items-center gap-4">
                <h2
                  className="font-semibold flex-shrink-0"
                  style={{
                    fontSize: '16px',
                    color: 'var(--text-primary)'
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

                {/* Position Type Toggles (hidden for Private) */}
                {activeTab !== 'private' && (
                  <div className="flex gap-1 flex-shrink-0">
                    <Button
                      size="sm"
                      variant={positionType === 'long' ? 'default' : 'outline'}
                      onClick={() => setPositionType('long')}
                      className="h-8 px-3"
                    >
                      Long
                    </Button>
                    <Button
                      size="sm"
                      variant={positionType === 'short' ? 'default' : 'outline'}
                      onClick={() => setPositionType('short')}
                      className="h-8 px-3"
                    >
                      Short
                    </Button>
                  </div>
                )}
              </div>

              {/* Right: Aggregate Returns */}
              <div className="flex gap-6 flex-shrink-0">
                <div className="text-right">
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>EOY</div>
                  <div
                    className="text-lg font-bold tabular-nums"
                    style={{
                      color: currentAggregate.eoy >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                    }}
                  >
                    {currentAggregate.eoy >= 0 ? '+' : ''}{currentAggregate.eoy.toFixed(1)}%
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Next Year</div>
                  <div
                    className="text-lg font-bold tabular-nums"
                    style={{
                      color: currentAggregate.nextYear >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                    }}
                  >
                    {currentAggregate.nextYear >= 0 ? '+' : ''}{currentAggregate.nextYear.toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SCROLLING CONTENT: Single Unified Table */}
      <div className="container mx-auto px-4 py-6">
        <ResearchTableView
          positions={filteredPositions}
          title=""
          aggregateReturnEOY={currentAggregate.eoy}
          aggregateReturnNextYear={currentAggregate.nextYear}
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
