'use client'

import { Position } from '@/hooks/usePositions'
import { StrategyListItem } from '@/services/strategiesApi'
import { SelectablePositionCard } from './SelectablePositionCard'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { StrategyCard } from './StrategyCard'
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
    <div>
      <h3 className={`text-base font-semibold mb-3 transition-colors duration-300 ${
        theme === 'dark' ? 'text-white' : 'text-gray-900'
      }`}>
        Short Positions
      </h3>
      {shortPositions.length === 0 && shortStrategies.length === 0 ? (
        <div className={`text-sm p-3 rounded-lg border transition-colors duration-300 ${
          theme === 'dark'
            ? 'text-empty-text-dark bg-empty-bg-dark border-empty-border-dark'
            : 'text-empty-text bg-empty-bg border-empty-border'
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
            <SelectablePositionCard
              key={position.id}
              isSelected={isSelected(position.id)}
              onToggleSelection={() => onToggleSelection(position.id)}
              tags={position.tags || []}
              onDropTag={(tagId) => onDropTag?.(position.id, tagId)}
            >
              <OrganizePositionCard position={position} />
            </SelectablePositionCard>
          ))}
        </div>
      )}
    </div>
  )
}
