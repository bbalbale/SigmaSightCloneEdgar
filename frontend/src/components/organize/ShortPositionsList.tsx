'use client'

import { Position } from '@/hooks/usePositions'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { SelectablePositionCard } from './SelectablePositionCard'

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
  // Filter for short positions, excluding private
  const shortPositions = positions.filter(p =>
    p.position_type === 'SHORT' && p.investment_class !== 'PRIVATE'
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
        Short Stocks
      </h3>
      {shortPositions.length === 0 ? (
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
