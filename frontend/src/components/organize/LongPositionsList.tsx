'use client'

import { Position } from '@/hooks/usePositions'
import { StrategyListItem } from '@/services/strategiesApi'
import { PositionCard } from './PositionCard'
import { StrategyCard } from './StrategyCard'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

interface LongPositionsListProps {
  positions: Position[]
  strategies: StrategyListItem[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
  onEditStrategy?: (strategy: StrategyListItem) => void
  onDeleteStrategy?: (strategyId: string) => void
}

export function LongPositionsList({
  positions,
  strategies,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag,
  onEditStrategy,
  onDeleteStrategy
}: LongPositionsListProps) {
  // Filter for long positions only
  const longPositions = positions.filter(p => p.position_type === 'LONG')

  // Filter for long strategies
  const longStrategies = strategies.filter(s => s.type === 'LONG')

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">Long Positions</CardTitle>
      </CardHeader>
      <CardContent>
        {longPositions.length === 0 && longStrategies.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No long positions
          </div>
        ) : (
          <div className="space-y-2">
            {/* Render strategies first */}
            {longStrategies.map(strategy => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                onEdit={onEditStrategy || (() => {})}
                onDelete={onDeleteStrategy || (() => {})}
                onDrop={onDropTag}
              />
            ))}

            {/* Render individual positions */}
            {longPositions.map(position => (
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
