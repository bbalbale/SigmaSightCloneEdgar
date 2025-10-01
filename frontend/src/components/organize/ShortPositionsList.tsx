'use client'

import { Position } from '@/hooks/usePositions'
import { StrategyListItem } from '@/services/strategiesApi'
import { PositionCard } from './PositionCard'
import { StrategyCard } from './StrategyCard'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'

interface ShortPositionsListProps {
  positions: Position[]
  strategies: StrategyListItem[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
  onEditStrategy?: (strategy: StrategyListItem) => void
  onDeleteStrategy?: (strategyId: string) => void
}

export function ShortPositionsList({
  positions,
  strategies,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag,
  onEditStrategy,
  onDeleteStrategy
}: ShortPositionsListProps) {
  const { theme } = useTheme()

  // Filter for short positions only
  const shortPositions = positions.filter(p => p.position_type === 'SHORT')

  // Filter for short strategies
  const shortStrategies = strategies.filter(s => s.type === 'SHORT')

  return (
    <Card className={`transition-colors ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
    }`}>
      <CardHeader>
        <CardTitle className={`text-base font-semibold transition-colors duration-300 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>Short Positions</CardTitle>
      </CardHeader>
      <CardContent>
        {shortPositions.length === 0 && shortStrategies.length === 0 ? (
          <div className={`text-center py-8 transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
          }`}>
            No short positions
          </div>
        ) : (
          <div className="space-y-2">
            {/* Render strategies first */}
            {shortStrategies.map(strategy => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                onEdit={onEditStrategy || (() => {})}
                onDelete={onDeleteStrategy || (() => {})}
                onDrop={onDropTag}
              />
            ))}

            {/* Render individual positions */}
            {shortPositions.map(position => (
              <PositionCard
                key={position.id}
                position={position}
                isSelected={isSelected(position.id)}
                onToggleSelection={onToggleSelection}
                onDrop={onDropTag}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
