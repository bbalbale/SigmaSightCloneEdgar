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
  onDropPosition?: (droppedPositionId: string, targetPositionId: string) => void
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
  onDropPosition,
  onEditStrategy,
  onDeleteStrategy
}: ShortPositionsListProps) {
  const { theme } = useTheme()

  // Filter for short strategies (by direction field), excluding private positions
  // Note: All positions should be in strategies (either standalone or combined)
  const shortStrategies = strategies.filter(s =>
    s.direction === 'SHORT' && s.primary_investment_class !== 'PRIVATE'
  )

  return (
    <div>
      <h3 className={`text-base font-semibold mb-3 transition-colors duration-300 ${
        theme === 'dark' ? 'text-white' : 'text-gray-900'
      }`}>
        Short Stocks
      </h3>
      {shortStrategies.length === 0 ? (
        <div className={`text-sm p-3 rounded-lg border transition-colors duration-300 ${
          theme === 'dark'
            ? 'text-empty-text-dark bg-empty-bg-dark border-empty-border-dark'
            : 'text-empty-text bg-empty-bg border-empty-border'
        }`}>
          No positions
        </div>
      ) : (
        <div className="space-y-2">
          {/* Render all strategies (both individual and combinations) */}
          {shortStrategies.map(strategy => (
            <StrategyCard
              key={strategy.id}
              strategy={strategy}
              onEdit={onEditStrategy || (() => {})}
              onDelete={onDeleteStrategy || (() => {})}
              onDrop={onDropTag}
              onDropStrategy={onDropPosition}
            />
          ))}
        </div>
      )}
    </div>
  )
}
