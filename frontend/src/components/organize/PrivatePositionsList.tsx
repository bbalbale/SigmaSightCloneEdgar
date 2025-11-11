'use client'

import { Position } from '@/hooks/usePositions'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { SelectablePositionCard } from './SelectablePositionCard'

interface PrivatePositionsListProps {
  positions: Position[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
}

export function PrivatePositionsList({
  positions,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag
}: PrivatePositionsListProps) {
  // Filter for private positions
  const privatePositions = positions.filter(p =>
    p.investment_class === 'PRIVATE'
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
        Positions
      </h3>
      {privatePositions.length === 0 ? (
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
          {privatePositions.map(position => (
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
