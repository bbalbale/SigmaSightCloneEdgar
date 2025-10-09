// src/containers/PublicPositionsContainer.tsx
'use client'

import { useState, useMemo } from 'react'
import { usePublicPositions } from '@/hooks/usePublicPositions'
import { EnhancedPositionsSection } from '@/components/positions/EnhancedPositionsSection'
import { useTheme } from '@/contexts/ThemeContext'
import { positionResearchService, type EnhancedPosition } from '@/services/positionResearchService'

type FilterType = 'all' | 'longs' | 'shorts' | 'options'

export function PublicPositionsContainer() {
  const { theme } = useTheme()
  const { longPositions, shortPositions, loading, error, aggregateReturns } = usePublicPositions()
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
  const aggregates = useMemo(() => ({
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
  }), [allOptions, longEquities, longOptions, shortEquities, shortOptions])

  // Determine which sections to show based on filter
  const showLongs = activeFilter === 'all' || activeFilter === 'longs'
  const showShorts = activeFilter === 'all' || activeFilter === 'shorts'
  const showOptionsOnly = activeFilter === 'options'

  if (loading && !longPositions.length && !shortPositions.length) {
    return (
      <div className={`min-h-screen flex items-center justify-center transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-4"></div>
          <p className={`text-lg font-medium transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            Loading positions...
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-6 py-12">
          <div className="max-w-7xl mx-auto">
            <div className={`rounded-xl border p-8 transition-all duration-300 ${
              theme === 'dark'
                ? 'bg-red-900/20 border-red-700/50'
                : 'bg-red-50 border-red-200'
            }`}>
              <h2 className={`text-2xl font-bold mb-2 transition-colors duration-300 ${
                theme === 'dark' ? 'text-red-400' : 'text-red-900'
              }`}>
                Error Loading Positions
              </h2>
              <p className={`transition-colors duration-300 ${
                theme === 'dark' ? 'text-red-300' : 'text-red-700'
              }`}>
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
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <h1 className={`text-2xl font-bold mb-2 transition-colors duration-300 ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>
            Public Positions
          </h1>
          <p className={`transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            Deep analysis with price targets, analyst estimates, and forward projections
          </p>
        </div>
      </section>

      {/* Filter Tabs */}
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="flex gap-2 overflow-x-auto">
            {filters.map((filter) => (
              <button
                key={filter.value}
                onClick={() => setActiveFilter(filter.value)}
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 whitespace-nowrap ${
                  activeFilter === filter.value
                    ? theme === 'dark'
                      ? 'bg-blue-600 text-white'
                      : 'bg-blue-500 text-white'
                    : theme === 'dark'
                    ? 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-200'
                }`}
              >
                {filter.label} ({filter.count})
              </button>
            ))}
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
                />
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
