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

      {/* Longs Section */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <EnhancedPositionsSection
            positions={longPositions}
            title="Long Positions"
            aggregateReturnEOY={aggregateReturns.longs_eoy}
            aggregateReturnNextYear={aggregateReturns.longs_next_year}
          />
        </div>
      </section>

      {/* Shorts Section */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <EnhancedPositionsSection
            positions={shortPositions}
            title="Short Positions"
            aggregateReturnEOY={aggregateReturns.shorts_eoy}
            aggregateReturnNextYear={aggregateReturns.shorts_next_year}
          />
        </div>
      </section>
    </div>
  )
}
