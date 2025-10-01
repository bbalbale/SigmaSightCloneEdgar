'use client'

import { Position } from '@/hooks/usePositions'
import { StrategyListItem } from '@/services/strategiesApi'
import { SelectablePositionCard } from './SelectablePositionCard'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { StrategyCard } from './StrategyCard'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'

interface LongPositionsListProps {
  positions: Position[]
  strategies: StrategyListItem[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
  onEditStrategy?: (strategy: StrategyListItem) => void
  onDeleteStrategy?: (strategyId: string) => void
}

export function LongPositionsList({
  positions,
  strategies,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag,
  onEditStrategy,
  onDeleteStrategy
}: LongPositionsListProps) {
  const { theme } = useTheme()

  // Filter for long positions only
  const longPositions = positions.filter(p => p.position_type === 'LONG')

  // Filter for long strategies
  const longStrategies = strategies.filter(s => s.type === 'LONG')

  return (
    <Card className={`transition-colors ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
    }`}>
      <CardHeader>
        <CardTitle className={`text-base font-semibold transition-colors duration-300 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>Long Positions</CardTitle>
      </CardHeader>
      <CardContent>
        {longPositions.length === 0 && longStrategies.length === 0 ? (
          <div className={`text-center py-8 transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
          }`}>
            No long positions
          </div>
        ) : (
          <div className="space-y-2">
            {/* Render strategies first */}
            {longStrategies.map(strategy => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                onEdit={onEditStrategy || (() => {})}
                onDelete={onDeleteStrategy || (() => {})}
                onDrop={onDropTag}
              />
            ))}

            {/* Render individual positions */}
            {longPositions.map(position => (
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
      </CardContent>
    </Card>
  )
}
