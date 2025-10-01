'use client'

import { Position } from '@/hooks/usePositions'
import { StrategyListItem } from '@/services/strategiesApi'
import { PositionCard } from './PositionCard'
import { StrategyCard } from './StrategyCard'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

interface PrivatePositionsListProps {
  positions: Position[]
  strategies: StrategyListItem[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
  onEditStrategy?: (strategy: StrategyListItem) => void
  onDeleteStrategy?: (strategyId: string) => void
}

export function PrivatePositionsList({
  positions,
  strategies,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag,
  onEditStrategy,
  onDeleteStrategy
}: PrivatePositionsListProps) {
  // Filter for private positions only
  const privatePositions = positions.filter(p => p.investment_class === 'PRIVATE')

  // Filter for private strategies
  const privateStrategies = strategies.filter(s =>
    s.positions?.some((p: any) => p.investment_class === 'PRIVATE')
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base font-semibold">Private Positions</CardTitle>
      </CardHeader>
      <CardContent>
        {privatePositions.length === 0 && privateStrategies.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No private positions
          </div>
        ) : (
          <div className="space-y-2">
            {/* Render strategies first */}
            {privateStrategies.map(strategy => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                onEdit={onEditStrategy || (() => {})}
                onDelete={onDeleteStrategy || (() => {})}
                onDrop={onDropTag}
              />
            ))}

            {/* Render individual positions */}
            {privatePositions.map(position => (
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
