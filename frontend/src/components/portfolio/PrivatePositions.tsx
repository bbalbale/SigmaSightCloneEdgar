import React from 'react'
import { Badge } from '@/components/ui/badge'
import { useTheme } from '@/contexts/ThemeContext'
import { PrivatePositionCard } from '@/components/positions/PrivatePositionCard'

interface PrivatePosition {
  id?: string
  symbol: string
  name?: string
  quantity: number
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
  investment_subtype?: string
  price?: number
}

interface PrivatePositionsProps {
  positions: PrivatePosition[]
}

export function PrivatePositions({ positions }: PrivatePositionsProps) {
  const { theme } = useTheme()

  // Group by investment subtype
  const groupedPositions = positions.reduce((acc, position) => {
    const subtype = position.investment_subtype || 'Alternative Investment'
    if (!acc[subtype]) acc[subtype] = []
    acc[subtype].push(position)
    return acc
  }, {} as Record<string, PrivatePosition[]>)

  if (positions.length === 0) {
    return (
      <div className={`text-sm p-3 rounded-lg border ${
        theme === 'dark'
          ? 'text-empty-text-dark bg-empty-bg-dark border-empty-border-dark'
          : 'text-empty-text bg-empty-bg border-empty-border'
      }`}>
        No private or alternative investments
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {Object.entries(groupedPositions).map(([subtype, subtypePositions]) => (
        <div key={subtype}>
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-sm font-medium text-primary">{subtype}</h4>
            <Badge variant="outline" className="text-xs">
              {subtypePositions.length}
            </Badge>
          </div>
          <div className="space-y-2">
            {subtypePositions.map((position, index) => (
              <PrivatePositionCard
                key={position.id || `private-${subtype}-${index}`}
                position={position}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}