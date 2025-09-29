import React from 'react'
import { Badge } from '@/components/ui/badge'
import { PositionCard } from './PositionCard'
import { useTheme } from '@/contexts/ThemeContext'

interface Position {
  symbol: string
  name?: string
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
}

interface PortfolioPositionsProps {
  longPositions: Position[]
  shortPositions: Position[]
}

export function PortfolioPositions({ longPositions, shortPositions }: PortfolioPositionsProps) {
  const { theme } = useTheme()

  return (
    <section className="flex-1 px-4 pb-6">
      <div className="container mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Long Positions Column */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>Long Positions</h3>
              <Badge variant="secondary" className={`transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
              }`}>
                {longPositions.length}
              </Badge>
            </div>
            <div className="space-y-3">
              {longPositions.map((position, index) => (
                <PositionCard key={`long-${index}`} position={position} />
              ))}
            </div>
          </div>

          {/* Short Positions Column */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>Short Positions</h3>
              <Badge variant="secondary" className={`transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
              }`}>
                {shortPositions.length}
              </Badge>
            </div>
            <div className="space-y-3">
              {shortPositions.map((position, index) => (
                <PositionCard
                  key={`short-${index}`}
                  position={{
                    ...position,
                    marketValue: -Math.abs(position.marketValue) // Ensure negative display for shorts
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}