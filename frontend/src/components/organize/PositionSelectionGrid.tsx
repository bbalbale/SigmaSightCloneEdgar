'use client'

import { Position } from '@/hooks/usePositions'
import { StrategyListItem } from '@/services/strategiesApi'
import { LongPositionsList } from './LongPositionsList'
import { ShortPositionsList } from './ShortPositionsList'
import { OptionsPositionsList } from './OptionsPositionsList'
import { ShortOptionsPositionsList } from './ShortOptionsPositionsList'

interface PositionSelectionGridProps {
  positions: Position[]
  strategies: StrategyListItem[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
  onDropPosition?: (droppedPositionId: string, targetPositionId: string) => void
  onEditStrategy?: (strategy: StrategyListItem) => void
  onDeleteStrategy?: (strategyId: string) => void
}

export function PositionSelectionGrid({
  positions,
  strategies,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag,
  onDropPosition,
  onEditStrategy,
  onDeleteStrategy
}: PositionSelectionGridProps) {
  // Filter positions by investment class for each quadrant
  const publicPositions = positions.filter(p => p.investment_class === 'PUBLIC')
  const optionsPositions = positions.filter(p => p.investment_class === 'OPTION')
  const privatePositions = positions.filter(p => p.investment_class === 'PRIVATE')

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Top-left: Long Positions */}
      <LongPositionsList
        positions={publicPositions}
        strategies={strategies}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
        onDropTag={onDropTag}
        onDropPosition={onDropPosition}
        onEditStrategy={onEditStrategy}
        onDeleteStrategy={onDeleteStrategy}
      />

      {/* Top-right: Short Positions */}
      <ShortPositionsList
        positions={publicPositions}
        strategies={strategies}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
        onDropTag={onDropTag}
        onDropPosition={onDropPosition}
        onEditStrategy={onEditStrategy}
        onDeleteStrategy={onDeleteStrategy}
      />

      {/* Bottom-left: Long Options Positions */}
      <OptionsPositionsList
        positions={optionsPositions}
        strategies={strategies}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
        onDropTag={onDropTag}
        onDropPosition={onDropPosition}
        onEditStrategy={onEditStrategy}
        onDeleteStrategy={onDeleteStrategy}
      />

      {/* Bottom-right: Short Options Positions */}
      <ShortOptionsPositionsList
        positions={optionsPositions}
        strategies={strategies}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
        onDropTag={onDropTag}
        onDropPosition={onDropPosition}
        onEditStrategy={onEditStrategy}
        onDeleteStrategy={onDeleteStrategy}
      />
    </div>
  )
}
