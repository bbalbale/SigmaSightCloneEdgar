'use client'

import { Position } from '@/hooks/usePositions'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { SelectablePositionCard } from './SelectablePositionCard'
import { useTheme } from '@/contexts/ThemeContext'

interface OptionsPositionsListProps {
  positions: Position[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
}

export function OptionsPositionsList({
  positions,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag
}: OptionsPositionsListProps) {
  const { theme } = useTheme()

  // Filter for long options positions (LC = Long Call, LP = Long Put)
  const optionsPositions = positions.filter(p =>
    p.investment_class === 'OPTIONS' &&
    (p.position_type === 'LC' || p.position_type === 'LP')
  )

  return (
    <div>
      <h3 className={`text-base font-semibold mb-3 transition-colors duration-300 ${
        theme === 'dark' ? 'text-white' : 'text-gray-900'
      }`}>
        Long Options
      </h3>
      {optionsPositions.length === 0 ? (
        <div className={`text-sm p-3 rounded-lg border transition-colors duration-300 ${
          theme === 'dark'
            ? 'text-empty-text-dark bg-empty-bg-dark border-empty-border-dark'
            : 'text-empty-text bg-empty-bg border-empty-border'
        }`}>
          No positions
        </div>
      ) : (
        <div className="space-y-2">
          {optionsPositions.map(position => (
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
