// src/containers/PrivatePositionsContainer.tsx
'use client'

import { usePrivatePositions } from '@/hooks/usePrivatePositions'
import { EnhancedPositionsSection } from '@/components/positions/EnhancedPositionsSection'
import { useTheme } from '@/contexts/ThemeContext'

export function PrivatePositionsContainer() {
  const { theme } = useTheme()
  const { positions, loading, error, aggregateReturns } = usePrivatePositions()

  if (loading && !positions.length) {
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
            Private Positions
          </h1>
          <p className={`transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            Private equity, venture capital, and alternative investments
          </p>
        </div>
      </section>

      {/* Positions Section */}
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <EnhancedPositionsSection
            positions={positions}
            title="Private Investments"
            aggregateReturnEOY={aggregateReturns.eoy}
            aggregateReturnNextYear={aggregateReturns.next_year}
          />
        </div>
      </section>
    </div>
  )
}
