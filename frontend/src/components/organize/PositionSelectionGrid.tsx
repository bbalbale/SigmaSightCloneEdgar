'use client'

import { Position } from '@/hooks/usePositions'
import { LongPositionsList } from './LongPositionsList'
import { ShortPositionsList } from './ShortPositionsList'
import { OptionsPositionsList } from './OptionsPositionsList'
import { ShortOptionsPositionsList } from './ShortOptionsPositionsList'

interface PositionSelectionGridProps {
  positions: Position[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
}

export function PositionSelectionGrid({
  positions,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag
}: PositionSelectionGridProps) {
  // Filter positions by investment class for each quadrant
  const publicPositions = positions.filter(p => p.investment_class === 'PUBLIC')
  const optionsPositions = positions.filter(p => p.investment_class === 'OPTIONS')

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Top-left: Long Positions */}
      <LongPositionsList
        positions={publicPositions}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
        onDropTag={onDropTag}
      />

      {/* Top-right: Short Positions */}
      <ShortPositionsList
        positions={publicPositions}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
        onDropTag={onDropTag}
      />

      {/* Bottom-left: Long Options Positions */}
      <OptionsPositionsList
        positions={optionsPositions}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
        onDropTag={onDropTag}
      />

      {/* Bottom-right: Short Options Positions */}
      <ShortOptionsPositionsList
        positions={optionsPositions}
        selectedIds={selectedIds}
        isSelected={isSelected}
        onToggleSelection={onToggleSelection}
        onDropTag={onDropTag}
      />
    </div>
  )
}
