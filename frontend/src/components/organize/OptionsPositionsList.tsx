'use client'

import { Position } from '@/hooks/usePositions'
import { StrategyListItem } from '@/services/strategiesApi'
import { PositionCard } from './PositionCard'
import { StrategyCard } from './StrategyCard'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
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
    <Card className={`transition-colors ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
    }`}>
      <CardHeader>
        <CardTitle className={`text-base font-semibold transition-colors duration-300 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>Options Positions</CardTitle>
      </CardHeader>
      <CardContent>
        {optionsPositions.length === 0 && optionsStrategies.length === 0 ? (
          <div className={`text-center py-8 transition-colors duration-300 ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
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
                    <PositionCard
                      key={position.id}
                      position={position}
                      isSelected={isSelected(position.id)}
                      onToggleSelection={onToggleSelection}
                      onDrop={onDropTag}
                    />
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
                    <PositionCard
                      key={position.id}
                      position={position}
                      isSelected={isSelected(position.id)}
                      onToggleSelection={onToggleSelection}
                      onDrop={onDropTag}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
