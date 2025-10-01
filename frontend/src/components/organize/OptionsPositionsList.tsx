'use client'

import { Position } from '@/hooks/usePositions'
import { StrategyListItem } from '@/services/strategiesApi'
import { SelectablePositionCard } from './SelectablePositionCard'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { StrategyCard } from './StrategyCard'
import { useTheme } from '@/contexts/ThemeContext'

interface OptionsPositionsListProps {
  positions: Position[]
  strategies: StrategyListItem[]
  selectedIds: string[]
  isSelected: (id: string) => boolean
  onToggleSelection: (id: string) => void
  onDropTag?: (targetId: string, tagId: string) => void
  onEditStrategy?: (strategy: StrategyListItem) => void
  onDeleteStrategy?: (strategyId: string) => void
}

export function OptionsPositionsList({
  positions,
  strategies,
  selectedIds,
  isSelected,
  onToggleSelection,
  onDropTag,
  onEditStrategy,
  onDeleteStrategy
}: OptionsPositionsListProps) {
  const { theme } = useTheme()

  // Filter for options positions
  const optionsPositions = positions.filter(p => p.investment_class === 'OPTIONS')

  // Separate long and short options
  const longOptions = optionsPositions.filter(p => ['LC', 'LP'].includes(p.position_type))
  const shortOptions = optionsPositions.filter(p => ['SC', 'SP'].includes(p.position_type))

  // Filter for options strategies (those containing options positions)
  const optionsStrategies = strategies.filter(s =>
    s.positions?.some((p: any) => p.investment_class === 'OPTIONS')
  )

  return (
    <div>
      <h3 className={`text-base font-semibold mb-3 transition-colors duration-300 ${
        theme === 'dark' ? 'text-white' : 'text-gray-900'
      }`}>
        Options Positions
      </h3>
      {optionsPositions.length === 0 && optionsStrategies.length === 0 ? (
        <div className={`text-sm p-3 rounded-lg border transition-colors duration-300 ${
          theme === 'dark'
            ? 'text-empty-text-dark bg-empty-bg-dark border-empty-border-dark'
            : 'text-empty-text bg-empty-bg border-empty-border'
        }`}>
          No options positions
        </div>
      ) : (
        <div className="space-y-4">
          {/* Strategies */}
          {optionsStrategies.length > 0 && (
            <div className="space-y-2">
              {optionsStrategies.map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  onEdit={onEditStrategy || (() => {})}
                  onDelete={onDeleteStrategy || (() => {})}
                  onDrop={onDropTag}
                />
              ))}
            </div>
          )}

          {/* Long Options */}
          {longOptions.length > 0 && (
            <div>
              <h4 className={`text-sm font-medium mb-2 transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
              }`}>Long Options</h4>
              <div className="space-y-2">
                {longOptions.map(position => (
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
            </div>
          )}

          {/* Short Options */}
          {shortOptions.length > 0 && (
            <div>
              <h4 className={`text-sm font-medium mb-2 transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
              }`}>Short Options</h4>
              <div className="space-y-2">
                {shortOptions.map(position => (
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
            </div>
          )}
        </div>
      )}
    </div>
  )
}
