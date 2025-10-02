/**
 * PortfolioStrategiesView Component
 *
 * Displays strategies in the same 3-column layout as PortfolioPositions.
 * Maintains exact same structure for seamless transition between views.
 *
 * Layout:
 * Row 1: Public Longs | Public Shorts | Private Investments
 * Row 2: Long Options | Short Options | (empty)
 *
 * Usage:
 * ```tsx
 * const { strategies } = useStrategies({ includePositions: true, includeTags: true })
 * <PortfolioStrategiesView strategies={strategies} />
 * ```
 */

'use client'

import React from 'react'
import { Badge } from '@/components/ui/badge'
import { StrategyPositionList } from '@/components/strategies/StrategyPositionList'
import { useStrategyFiltering } from '@/hooks/useStrategyFiltering'
import { useTheme } from '@/contexts/ThemeContext'
import type { StrategyListItem } from '@/types/strategies'

interface PortfolioStrategiesViewProps {
  strategies: StrategyListItem[]
  onEditTags?: (strategyId: string) => void
  className?: string
}

export function PortfolioStrategiesView({
  strategies,
  onEditTags,
  className = ''
}: PortfolioStrategiesViewProps) {
  const { theme } = useTheme()
  const {
    publicLongs,
    publicShorts,
    privateStrategies,
    optionLongs,
    optionShorts,
    counts
  } = useStrategyFiltering(strategies)

  return (
    <section className="flex-1 px-4 pb-6">
      <div className="container mx-auto">
        <div className={`space-y-8 ${className}`}>
          {/* Row 1: Public Longs | Public Shorts | Private Investments */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Public Longs */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <h3 className={`text-lg font-semibold transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Public Longs
            </h3>
            <Badge variant="secondary" className={`transition-colors duration-300 ${
              theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
            }`}>
              {counts.publicLongs}
            </Badge>
          </div>
          <StrategyPositionList
            strategies={publicLongs}
            onEditTags={onEditTags}
          />
        </div>

        {/* Public Shorts */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <h3 className={`text-lg font-semibold transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Public Shorts
            </h3>
            <Badge variant="secondary" className={`transition-colors duration-300 ${
              theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
            }`}>
              {counts.publicShorts}
            </Badge>
          </div>
          <StrategyPositionList
            strategies={publicShorts}
            onEditTags={onEditTags}
          />
        </div>

        {/* Private Investments */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <h3 className={`text-lg font-semibold transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Private Investments
            </h3>
            <Badge variant="secondary" className={`transition-colors duration-300 ${
              theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
            }`}>
              {counts.private}
            </Badge>
          </div>
          <StrategyPositionList
            strategies={privateStrategies}
            onEditTags={onEditTags}
          />
        </div>
      </div>

      {/* Row 2: Long Options | Short Options | (empty) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Long Options */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <h3 className={`text-lg font-semibold transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Long Options
            </h3>
            <Badge variant="secondary" className={`transition-colors duration-300 ${
              theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
            }`}>
              {counts.optionLongs}
            </Badge>
          </div>
          <StrategyPositionList
            strategies={optionLongs}
            onEditTags={onEditTags}
          />
        </div>

        {/* Short Options */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <h3 className={`text-lg font-semibold transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Short Options
            </h3>
            <Badge variant="secondary" className={`transition-colors duration-300 ${
              theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
            }`}>
              {counts.optionShorts}
            </Badge>
          </div>
          <StrategyPositionList
            strategies={optionShorts}
            onEditTags={onEditTags}
          />
        </div>

        {/* Empty third column (maintains grid structure) */}
        <div></div>
      </div>

          {/* Empty state */}
          {strategies.length === 0 && (
            <div className={`text-center py-12 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
            }`}>
              <p className="text-lg">No combinations found</p>
              <p className="text-sm mt-2">Positions will be automatically grouped into combinations</p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
