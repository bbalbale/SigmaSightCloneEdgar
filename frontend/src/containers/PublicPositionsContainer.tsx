// src/containers/PublicPositionsContainer.tsx
'use client'

import { useState, useMemo } from 'react'
import { usePublicPositions } from '@/hooks/usePublicPositions'
import { EnhancedPositionsSection } from '@/components/positions/EnhancedPositionsSection'
import { positionResearchService, type EnhancedPosition } from '@/services/positionResearchService'

type FilterType = 'all' | 'longs' | 'shorts' | 'options'

export function PublicPositionsContainer() {
  const { longPositions, shortPositions, loading, error, aggregateReturns, portfolioSnapshot, refetch, updatePositionTargetOptimistic } = usePublicPositions()
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')

  // Helper to check if position is an option (LC, LP, SC, SP)
  const isOption = (position: EnhancedPosition) => {
    // Check if investment_class is OPTIONS, or position_type is an option type
    return position.investment_class === 'OPTIONS' ||
           ['LC', 'LP', 'SC', 'SP'].includes(position.position_type as string)
  }

  // Separate positions into categories
  const { longEquities, longOptions, shortEquities, shortOptions, allOptions } = useMemo(() => {
    const longEquities = longPositions.filter(p => !isOption(p))
    const longOptions = longPositions.filter(p => isOption(p))
    const shortEquities = shortPositions.filter(p => !isOption(p))
    const shortOptions = shortPositions.filter(p => isOption(p))
    const allOptions = [...longOptions, ...shortOptions]

    return { longEquities, longOptions, shortEquities, shortOptions, allOptions }
  }, [longPositions, shortPositions])

  // Calculate aggregate returns for each section using service method with fallback logic
  const aggregates = useMemo(() => {
    // Combine all positions for portfolio-level aggregate
    const allPositions = [...longPositions, ...shortPositions]

    return {
      // Portfolio-level aggregate - CALCULATE ON FRONTEND for instant updates
      // Backend snapshot still updates in background for historical data
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
      allOptions: {
        eoy: positionResearchService.calculateAggregateReturn(
          allOptions,
          'target_return_eoy',
          'analyst_return_eoy' // Fallback to analyst if user target is null
        ),
        nextYear: positionResearchService.calculateAggregateReturn(
          allOptions,
          'target_return_next_year'
        )
      },
      longEquities: {
        eoy: positionResearchService.calculateAggregateReturn(
          longEquities,
          'target_return_eoy',
          'analyst_return_eoy'
        ),
        nextYear: positionResearchService.calculateAggregateReturn(
          longEquities,
          'target_return_next_year'
        )
      },
      longOptions: {
        eoy: positionResearchService.calculateAggregateReturn(
          longOptions,
          'target_return_eoy',
          'analyst_return_eoy'
        ),
        nextYear: positionResearchService.calculateAggregateReturn(
          longOptions,
          'target_return_next_year'
        )
      },
      shortEquities: {
        eoy: positionResearchService.calculateAggregateReturn(
          shortEquities,
          'target_return_eoy',
          'analyst_return_eoy'
        ),
        nextYear: positionResearchService.calculateAggregateReturn(
          shortEquities,
          'target_return_next_year'
        )
      },
      shortOptions: {
        eoy: positionResearchService.calculateAggregateReturn(
          shortOptions,
          'target_return_eoy',
          'analyst_return_eoy'
        ),
        nextYear: positionResearchService.calculateAggregateReturn(
          shortOptions,
          'target_return_next_year'
        )
      }
    }
  }, [longPositions, shortPositions, allOptions, longEquities, longOptions, shortEquities, shortOptions, portfolioSnapshot])

  // Determine which sections to show based on filter
  const showLongs = activeFilter === 'all' || activeFilter === 'longs'
  const showShorts = activeFilter === 'all' || activeFilter === 'shorts'
  const showOptionsOnly = activeFilter === 'options'

  if (loading && !longPositions.length && !shortPositions.length) {
    return (
      <div
        className="min-h-screen flex items-center justify-center transition-colors duration-300"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        <div className="text-center">
          <div
            className="inline-block animate-spin rounded-full h-12 w-12 mb-4"
            style={{ borderBottom: '2px solid var(--color-accent)' }}
          ></div>
          <p
            className="font-medium transition-colors duration-300"
            style={{
              fontSize: 'var(--text-lg)',
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-body)'
            }}
          >
            Loading positions...
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div
        className="min-h-screen transition-colors duration-300"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        <section className="px-6 py-12">
          <div className="max-w-7xl mx-auto">
            <div
              className="transition-all duration-300"
              style={{
                backgroundColor: 'rgba(255, 0, 0, 0.1)',
                border: '1px solid var(--color-error)',
                borderRadius: 'var(--border-radius)',
                padding: 'var(--card-padding)'
              }}
            >
              <h2
                className="font-bold mb-2 transition-colors duration-300"
                style={{
                  fontSize: 'var(--text-2xl)',
                  color: 'var(--color-error)',
                  fontFamily: 'var(--font-display)'
                }}
              >
                Error Loading Positions
              </h2>
              <p
                className="transition-colors duration-300"
                style={{
                  color: 'var(--color-error)',
                  fontFamily: 'var(--font-body)'
                }}
              >
                {error}
              </p>
            </div>
          </div>
        </section>
      </div>
    )
  }

  const filters: Array<{ value: FilterType; label: string; count: number }> = [
    { value: 'all', label: 'All Positions', count: longPositions.length + shortPositions.length },
    { value: 'longs', label: 'Longs', count: longPositions.length },
    { value: 'shorts', label: 'Shorts', count: shortPositions.length },
    { value: 'options', label: 'Options Only', count: allOptions.length },
  ]

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <h1
            className="font-bold mb-2 transition-colors duration-300"
            style={{
              fontSize: 'var(--text-2xl)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)'
            }}
          >
            Public Positions
          </h1>
          <p
            className="transition-colors duration-300"
            style={{
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-body)'
            }}
          >
            Deep analysis with price targets, analyst estimates, and forward projections
          </p>
        </div>
      </section>

      {/* Filter Tabs with Portfolio Aggregate Cards */}
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="flex justify-between items-end gap-4">
            {/* Filter Buttons - Left Side */}
            <div className="flex gap-2 overflow-x-auto">
              {filters.map((filter) => (
                <button
                  key={filter.value}
                  onClick={() => setActiveFilter(filter.value)}
                  className="px-4 py-2 font-medium transition-all duration-200 whitespace-nowrap"
                  style={{
                    borderRadius: 'var(--border-radius)',
                    backgroundColor: activeFilter === filter.value ? 'var(--color-accent)' : 'var(--bg-secondary)',
                    color: activeFilter === filter.value ? '#ffffff' : 'var(--text-primary)',
                    border: activeFilter === filter.value ? 'none' : '1px solid var(--border-primary)',
                    fontFamily: 'var(--font-body)'
                  }}
                  onMouseEnter={(e) => {
                    if (activeFilter !== filter.value) {
                      e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (activeFilter !== filter.value) {
                      e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'
                    }
                  }}
                >
                  {filter.label} ({filter.count})
                </button>
              ))}
            </div>

            {/* Portfolio Aggregate Cards - Right Side (always visible) */}
            <div className="flex gap-3">
              {/* EOY Return Card */}
              <div
                className="px-4 py-3 min-w-[180px] transition-all duration-300"
                style={{
                  borderRadius: 'var(--border-radius)',
                  border: '1px solid var(--border-primary)',
                  backgroundColor: 'var(--bg-secondary)'
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
                    fontFamily: 'var(--font-display)'
                  }}
                >
                  {aggregates.portfolio.eoy.toFixed(2)}%
                </p>
              </div>

              {/* Next Year Return Card */}
              <div
                className="px-4 py-3 min-w-[180px] transition-all duration-300"
                style={{
                  borderRadius: 'var(--border-radius)',
                  border: '1px solid var(--border-primary)',
                  backgroundColor: 'var(--bg-secondary)'
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
                    fontFamily: 'var(--font-display)'
                  }}
                >
                  {aggregates.portfolio.nextYear.toFixed(2)}%
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Options Only View */}
      {showOptionsOnly && (
        <section className="px-4 pb-8">
          <div className="container mx-auto">
            <EnhancedPositionsSection
              positions={allOptions}
              title="All Options"
              aggregateReturnEOY={aggregates.allOptions.eoy}
              aggregateReturnNextYear={aggregates.allOptions.nextYear}
              onTargetPriceUpdate={updatePositionTargetOptimistic}
            />
          </div>
        </section>
      )}

      {/* Longs Section */}
      {showLongs && !showOptionsOnly && (
        <>
          {longEquities.length > 0 && (
            <section className="px-4 pb-8">
              <div className="container mx-auto">
                <EnhancedPositionsSection
                  positions={longEquities}
                  title="Long Positions"
                  aggregateReturnEOY={aggregates.longEquities.eoy}
                  aggregateReturnNextYear={aggregates.longEquities.nextYear}
                  onTargetPriceUpdate={updatePositionTargetOptimistic}
                />
              </div>
            </section>
          )}

          {longOptions.length > 0 && (
            <section className="px-4 pb-8">
              <div className="container mx-auto">
                <EnhancedPositionsSection
                  positions={longOptions}
                  title="Long Options"
                  aggregateReturnEOY={aggregates.longOptions.eoy}
                  aggregateReturnNextYear={aggregates.longOptions.nextYear}
                  onTargetPriceUpdate={updatePositionTargetOptimistic}
                />
              </div>
            </section>
          )}
        </>
      )}

      {/* Shorts Section */}
      {showShorts && !showOptionsOnly && (
        <>
          {shortEquities.length > 0 && (
            <section className="px-4 pb-8">
              <div className="container mx-auto">
                <EnhancedPositionsSection
                  positions={shortEquities}
                  title="Short Positions"
                  aggregateReturnEOY={aggregates.shortEquities.eoy}
                  aggregateReturnNextYear={aggregates.shortEquities.nextYear}
                  onTargetPriceUpdate={updatePositionTargetOptimistic}
                />
              </div>
            </section>
          )}

          {shortOptions.length > 0 && (
            <section className="px-4 pb-8">
              <div className="container mx-auto">
                <EnhancedPositionsSection
                  positions={shortOptions}
                  title="Short Options"
                  aggregateReturnEOY={aggregates.shortOptions.eoy}
                  aggregateReturnNextYear={aggregates.shortOptions.nextYear}
                  onTargetPriceUpdate={updatePositionTargetOptimistic}
                />
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
