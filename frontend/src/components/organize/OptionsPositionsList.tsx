'use client'

import { Position } from '@/hooks/usePositions'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { SelectablePositionCard } from './SelectablePositionCard'

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
  // Filter for long options positions (LC = Long Call, LP = Long Put)
  const optionsPositions = positions.filter(p =>
    p.investment_class === 'OPTIONS' &&
    (p.position_type === 'LC' || p.position_type === 'LP')
  )

  return (
    <div>
      <h3 className="transition-colors duration-300" style={{
        fontSize: 'var(--text-base)',
        fontWeight: 600,
        marginBottom: '0.75rem',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-display)'
      }}>
        Long Options
      </h3>
      {optionsPositions.length === 0 ? (
        <div className="p-3 rounded-lg border transition-colors duration-300" style={{
          fontSize: 'var(--text-sm)',
          backgroundColor: 'var(--bg-tertiary)',
          borderColor: 'var(--border-primary)',
          color: 'var(--text-secondary)'
        }}>
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
