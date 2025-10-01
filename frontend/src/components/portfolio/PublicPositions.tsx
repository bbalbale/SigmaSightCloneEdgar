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

  return (
    <div className="space-y-2">
      {positions.map((position, index) => (
        <PositionCard
          key={position.id || `public-${index}`}
          position={{
            ...position,
            // Ensure negative display for shorts
            marketValue: position.type === 'SHORT' ? -Math.abs(position.marketValue) : position.marketValue
          }}
        />
      ))}
      {positions.length === 0 && (
        <div className={`text-sm p-3 rounded-lg border ${
          theme === 'dark'
            ? 'text-slate-400 bg-slate-800/50 border-slate-700'
            : 'text-gray-500 bg-gray-50 border-gray-200'
        }`}>
          No positions
        </div>
      )}
    </div>
  )
}