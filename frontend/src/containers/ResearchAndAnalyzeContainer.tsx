'use client'

import React, { useMemo, useEffect } from 'react'
import { useResearchStore } from '@/stores/researchStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { usePublicPositions } from '@/hooks/usePublicPositions'
import { usePrivatePositions } from '@/hooks/usePrivatePositions'
import { analyticsApi } from '@/services/analyticsApi'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { PositionSidePanel } from '@/components/research-and-analyze/PositionSidePanel'
import { StickyTagBar } from '@/components/research-and-analyze/StickyTagBar'
import { EnhancedPositionsSection } from '@/components/positions/EnhancedPositionsSection'
import { useRestoreSectorTags } from '@/hooks/useRestoreSectorTags'
import tagsApi from '@/services/tagsApi'
import { positionResearchService, type EnhancedPosition } from '@/services/positionResearchService'

export function ResearchAndAnalyzeContainer() {
  // Portfolio ID
  const { portfolioId } = usePortfolioStore()

  // Zustand store state
  const activeTab = useResearchStore((state) => state.activeTab)
  const setActiveTab = useResearchStore((state) => state.setActiveTab)
  const sidePanelOpen = useResearchStore((state) => state.sidePanelOpen)
  const selectedPosition = useResearchStore((state) => state.selectedPosition)
  const openSidePanel = useResearchStore((state) => state.openSidePanel)
  const closeSidePanel = useResearchStore((state) => state.closeSidePanel)

  // Correlation matrix state and actions
  const setCorrelationMatrix = useResearchStore((state) => state.setCorrelationMatrix)
  const setCorrelationMatrixLoading = useResearchStore((state) => state.setCorrelationMatrixLoading)
  const setCorrelationMatrixError = useResearchStore((state) => state.setCorrelationMatrixError)

  // Data fetching - PHASE 1: Replace useResearchPageData with proven hooks
  const {
    longPositions,
    shortPositions,
    loading: publicLoading,
    error: publicError,
    aggregateReturns: publicAggregates,
    updatePositionTargetOptimistic: updatePublicTarget
  } = usePublicPositions()

  const {
    positions: privatePositions,
    loading: privateLoading,
    error: privateError,
    aggregateReturns: privateAggregates,
    updatePositionTargetOptimistic: updatePrivateTarget
  } = usePrivatePositions()

  const { restoreSectorTags, loading: restoringTags } = useRestoreSectorTags()

  // Get tags from public positions (they include tags)
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

  // DEBUG: Log position counts and investment_class distribution
  useEffect(() => {
    const allFetched = [...longPositions, ...shortPositions, ...privatePositions]
    const investmentClassDistribution = allFetched.reduce((acc, p) => {
      acc[p.investment_class] = (acc[p.investment_class] || 0) + 1
      return acc
    }, {} as Record<string, number>)

    console.log('📊 Position Analysis:', {
      totalFetched: allFetched.length,
      investmentClassDistribution,
      fromUsePublicPositions: {
        longs: longPositions.length,
        shorts: shortPositions.length,
        total: longPositions.length + shortPositions.length
      },
      fromUsePrivatePositions: privatePositions.length,
      afterFiltering: {
        publicPositions: publicPositions.length,
        publicLongs: publicLongs.length,
        publicShorts: publicShorts.length,
        optionsPositions: optionsPositions.length,
        optionLongs: optionLongs.length,
        optionShorts: optionShorts.length,
        privatePositions: privatePositions.length
      },
      optionsPositionTypes: optionsPositions.map(p => p.position_type),
      sampleData: {
        publicSample: publicPositions[0] && {
          symbol: publicPositions[0].symbol,
          investment_class: publicPositions[0].investment_class,
          position_type: publicPositions[0].position_type
        },
        optionsSample: optionsPositions[0] && {
          symbol: optionsPositions[0].symbol,
          investment_class: optionsPositions[0].investment_class,
          position_type: optionsPositions[0].position_type
        },
        privateSample: privatePositions[0] && {
          symbol: privatePositions[0].symbol,
          investment_class: privatePositions[0].investment_class,
          position_type: privatePositions[0].position_type
        }
      }
    })
  }, [longPositions, shortPositions, publicPositions, publicLongs, publicShorts, optionsPositions, optionLongs, optionShorts, privatePositions])

  // PHASE 3: Calculate aggregate returns for all position groups
  const aggregates = useMemo(() => {
    // Combine all positions for portfolio-level aggregate
    const allPositions = [...publicPositions, ...optionsPositions, ...privatePositions]

    return {
      // Portfolio-level (shown in cards at top)
      portfolio: {
        eoy: positionResearchService.calculateAggregateReturn(
          allPositions,
          'target_return_eoy',
          'analyst_return_eoy' // Fallback to analyst if user target is null
        ),
        nextYear: positionResearchService.calculateAggregateReturn(
          allPositions,
          'target_return_next_year'
        )
      },

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

  const handleCreateTag = () => {
    // TODO: Implement tag creation modal
    console.log('Create tag clicked')
  }

  const handleRestoreSectorTags = async () => {
    try {
      await restoreSectorTags()
      // Tags will be refetched automatically by usePublicPositions
    } catch (error) {
      console.error('Failed to restore sector tags:', error)
    }
  }

  // PHASE 7: Type compatibility - cast EnhancedPosition to Position for side panel
  const handlePositionClick = (position: EnhancedPosition) => {
    openSidePanel(position as any)
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
      {/* Page Header */}
      <section
        className="px-4 py-8 border-b transition-colors duration-300"
        style={{ borderColor: 'var(--border-primary)' }}
      >
        <div className="container mx-auto">
          <div className="flex items-start justify-between">
            <div>
              <h1
                className="font-bold transition-colors duration-300"
                style={{
                  fontSize: 'var(--text-3xl)',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}
              >
                Research & Analyze
              </h1>
              <p
                className="mt-2 transition-colors duration-300"
                style={{
                  fontSize: 'var(--text-lg)',
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-body)'
                }}
              >
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

            {/* PHASE 6: Portfolio Aggregate Cards (always visible) */}
            <section className="px-4 pb-6 mt-4">
              <div className="flex gap-3 justify-end">
                {/* EOY Return Card */}
                <div
                  className="rounded-lg px-4 py-3 min-w-[180px] transition-all duration-300"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-primary)'
                  }}
                >
                  <p
                    className="mb-1 transition-colors duration-300"
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-secondary)',
                      fontFamily: 'var(--font-body)'
                    }}
                  >
                    Portfolio Return EOY
                  </p>
                  <p
                    className="font-bold transition-colors duration-300"
                    style={{
                      fontSize: 'var(--text-xl)',
                      color: aggregates.portfolio.eoy >= 0 ? 'var(--color-success)' : 'var(--color-error)',
                      fontFamily: 'var(--font-mono)'
                    }}
                  >
                    {aggregates.portfolio.eoy.toFixed(2)}%
                  </p>
                </div>

                {/* Next Year Return Card */}
                <div
                  className="rounded-lg px-4 py-3 min-w-[180px] transition-all duration-300"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-primary)'
                  }}
                >
                  <p
                    className="mb-1 transition-colors duration-300"
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-secondary)',
                      fontFamily: 'var(--font-body)'
                    }}
                  >
                    Portfolio Return Next Year
                  </p>
                  <p
                    className="font-bold transition-colors duration-300"
                    style={{
                      fontSize: 'var(--text-xl)',
                      color: aggregates.portfolio.nextYear >= 0 ? 'var(--color-success)' : 'var(--color-error)',
                      fontFamily: 'var(--font-mono)'
                    }}
                  >
                    {aggregates.portfolio.nextYear.toFixed(2)}%
                  </p>
                </div>
              </div>
            </section>

            {/* PHASE 4: Public Tab - PUBLIC investment_class only */}
            <TabsContent value="public" className="mt-4">
              {/* Long Public Positions */}
              {publicLongs.length > 0 && (
                <section className="px-4 pb-8">
                  <EnhancedPositionsSection
                    positions={publicLongs}
                    title="Long Positions"
                    aggregateReturnEOY={aggregates.publicLongs.eoy}
                    aggregateReturnNextYear={aggregates.publicLongs.nextYear}
                    onTargetPriceUpdate={updatePublicTarget}
                    onPositionClick={handlePositionClick}
                  />
                </section>
              )}

              {/* Short Public Positions */}
              {publicShorts.length > 0 && (
                <section className="px-4 pb-8">
                  <EnhancedPositionsSection
                    positions={publicShorts}
                    title="Short Positions"
                    aggregateReturnEOY={aggregates.publicShorts.eoy}
                    aggregateReturnNextYear={aggregates.publicShorts.nextYear}
                    onTargetPriceUpdate={updatePublicTarget}
                    onPositionClick={handlePositionClick}
                  />
                </section>
              )}
            </TabsContent>

            {/* Options Tab - OPTIONS investment_class only */}
            <TabsContent value="options" className="mt-4">
              {console.log('🎯 OPTIONS TAB RENDER:', {
                optionLongs: optionLongs.length,
                optionShorts: optionShorts.length,
                optionLongsData: optionLongs.map(p => ({ symbol: p.symbol, investment_class: p.investment_class, position_type: p.position_type })),
                aggregates: {
                  eoy: aggregates.optionLongs.eoy,
                  nextYear: aggregates.optionLongs.nextYear
                }
              })}

              {/* Long Options */}
              {optionLongs.length > 0 ? (
                <section className="px-4 pb-8">
                  <EnhancedPositionsSection
                    positions={optionLongs}
                    title="Long Options"
                    aggregateReturnEOY={aggregates.optionLongs.eoy}
                    aggregateReturnNextYear={aggregates.optionLongs.nextYear}
                    onTargetPriceUpdate={updatePublicTarget}
                    onPositionClick={handlePositionClick}
                  />
                </section>
              ) : (
                <div className="px-4 py-8 text-center text-secondary">
                  No long options found
                </div>
              )}

              {/* Short Options */}
              {optionShorts.length > 0 ? (
                <section className="px-4 pb-8">
                  <EnhancedPositionsSection
                    positions={optionShorts}
                    title="Short Options"
                    aggregateReturnEOY={aggregates.optionShorts.eoy}
                    aggregateReturnNextYear={aggregates.optionShorts.nextYear}
                    onTargetPriceUpdate={updatePublicTarget}
                    onPositionClick={handlePositionClick}
                  />
                </section>
              ) : (
                <div className="px-4 py-8 text-center text-secondary">
                  No short options found
                </div>
              )}
            </TabsContent>

            {/* Private Tab */}
            <TabsContent value="private" className="mt-4">
              <section className="px-4 pb-8">
                <EnhancedPositionsSection
                  positions={privatePositions}
                  title="Private Investments"
                  aggregateReturnEOY={aggregates.private.eoy}
                  aggregateReturnNextYear={aggregates.private.nextYear}
                  onTargetPriceUpdate={updatePrivateTarget}
                  onPositionClick={handlePositionClick}
                />
              </section>
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
    </div>
  )
}
