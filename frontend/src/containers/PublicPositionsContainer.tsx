// src/containers/PublicPositionsContainer.tsx
'use client'

import { usePublicPositions } from '@/hooks/usePublicPositions'
import { EnhancedPositionsSection } from '@/components/positions/EnhancedPositionsSection'
import { useTheme } from '@/contexts/ThemeContext'

export function PublicPositionsContainer() {
  const { theme } = useTheme()
  const { longPositions, shortPositions, loading, error, aggregateReturns } = usePublicPositions()

  if (loading && !longPositions.length && !shortPositions.length) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-4 py-8">
          <div className="container mx-auto text-center">
            <p className={`text-lg transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Loading positions...
            </p>
          </div>
        </section>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-4 py-8">
          <div className="container mx-auto">
            <h1 className={`text-3xl font-bold mb-2 transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Public Positions Research
            </h1>
            <p className={`text-red-600 mt-4`}>{error}</p>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <h1 className={`text-3xl font-bold mb-2 transition-colors duration-300 ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>
            Public Positions Research
          </h1>
          <p className={`transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            Comprehensive analysis with targets, analyst estimates, and EPS/revenue projections
          </p>
        </div>
      </section>

      {/* Longs Section */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-3">
              <EnhancedPositionsSection
                positions={longPositions}
                title="Long Positions"
                aggregateReturnEOY={aggregateReturns.longs_eoy}
                aggregateReturnNextYear={aggregateReturns.longs_next_year}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Shorts Section */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-3">
              <EnhancedPositionsSection
                positions={shortPositions}
                title="Short Positions"
                aggregateReturnEOY={aggregateReturns.shorts_eoy}
                aggregateReturnNextYear={aggregateReturns.shorts_next_year}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
