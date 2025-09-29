import React from 'react'
import { Badge } from '@/components/ui/badge'
import { PositionCard } from './PositionCard'
import { useTheme } from '@/contexts/ThemeContext'

interface Position {
  id?: string
  symbol: string
  name?: string
  quantity: number
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
  investment_class?: string
  investment_subtype?: string
  price?: number
}

interface PublicPositionsProps {
  positions: Position[]
}

export function PublicPositions({ positions }: PublicPositionsProps) {
  const { theme } = useTheme()

  // Group positions by type (LONG vs SHORT)
  const longPositions = positions.filter(p => p.type === 'LONG' || !p.type)
  const shortPositions = positions.filter(p => p.type === 'SHORT')

  return (
    <div className="space-y-6">
      {/* Long Positions */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <h4 className={`text-sm font-medium transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
          }`}>Long Positions</h4>
          <Badge variant="outline" className="text-xs">
            {longPositions.length}
          </Badge>
        </div>
        <div className="space-y-2">
          {longPositions.map((position, index) => (
            <PositionCard key={position.id || `public-long-${index}`} position={position} />
          ))}
          {longPositions.length === 0 && (
            <div className={`text-sm p-3 rounded-lg border ${
              theme === 'dark'
                ? 'text-slate-400 bg-slate-800/50 border-slate-700'
                : 'text-gray-500 bg-gray-50 border-gray-200'
            }`}>
              No long equity positions
            </div>
          )}
        </div>
      </div>

      {/* Short Positions */}
      {shortPositions.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <h4 className={`text-sm font-medium transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
            }`}>Short Positions</h4>
            <Badge variant="outline" className="text-xs">
              {shortPositions.length}
            </Badge>
          </div>
          <div className="space-y-2">
            {shortPositions.map((position, index) => (
              <PositionCard
                key={position.id || `public-short-${index}`}
                position={{
                  ...position,
                  marketValue: -Math.abs(position.marketValue) // Ensure negative display for shorts
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}