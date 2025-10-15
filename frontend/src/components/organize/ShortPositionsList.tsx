'use client'

import { Position } from '@/hooks/usePositions'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { SelectablePositionCard } from './SelectablePositionCard'
import { useTheme } from '@/contexts/ThemeContext'

interface ShortPositionsListProps {
  positions: Position[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
}

export function ShortPositionsList({
  positions,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag
}: ShortPositionsListProps) {
  const { theme } = useTheme()

  // Filter for short positions, excluding private
  const shortPositions = positions.filter(p =>
    p.position_type === 'SHORT' && p.investment_class !== 'PRIVATE'
  )

  return (
    <div>
      <h3 className={`text-base font-semibold mb-3 transition-colors duration-300 ${
        theme === 'dark' ? 'text-white' : 'text-gray-900'
      }`}>
        Short Stocks
      </h3>
      {shortPositions.length === 0 ? (
        <div className={`text-sm p-3 rounded-lg border transition-colors duration-300 ${
          theme === 'dark'
            ? 'text-empty-text-dark bg-empty-bg-dark border-empty-border-dark'
            : 'text-empty-text bg-empty-bg border-empty-border'
        }`}>
          No positions
        </div>
      ) : (
        <div className="space-y-2">
          {shortPositions.map(position => (
            <SelectablePositionCard
              key={position.id}
              positionId={position.id}
              symbol={position.symbol}
              isSelected={isSelected(position.id)}
              onToggleSelection={() => onToggleSelection(position.id)}
              tags={position.tags}
              onDropTag={onDropTag ? (tagId) => onDropTag(position.id, tagId) : undefined}
            >
              <OrganizePositionCard position={position} />
            </SelectablePositionCard>
          ))}
        </div>
      )}
    </div>
  )
}
