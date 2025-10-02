'use client'

import { useState } from 'react'
import { StrategyListItem } from '@/services/strategiesApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Edit, Trash, ChevronDown, ChevronRight, Layers } from 'lucide-react'
import { formatCurrency } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'

interface StrategyCardProps {
  strategy: StrategyListItem
  onEdit: (strategy: StrategyListItem) => void
  onDelete: (strategyId: string) => void
  onDrop?: (strategyId: string, tagId: string) => void
  onDropStrategy?: (droppedStrategyId: string, targetStrategyId: string) => void
}

export function StrategyCard({
  strategy,
  onEdit,
  onDelete,
  onDrop,
  onDropStrategy
}: StrategyCardProps) {
  const { theme } = useTheme()
  const [isExpanded, setIsExpanded] = useState(false)

  // Drag start handler - make strategy draggable
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('strategyId', strategy.id)
    e.dataTransfer.setData('strategyName', strategy.name)
    e.dataTransfer.effectAllowed = 'move'
    e.currentTarget.classList.add('opacity-50')
  }

  const handleDragEnd = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('opacity-50')
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()

    // Check if we're dragging a strategy or a tag
    const draggedType = e.dataTransfer.types.includes('strategyid') ? 'strategy' : 'tag'

    if (draggedType === 'strategy') {
      // Strategy drag - green highlight for combination
      e.currentTarget.classList.add(
        theme === 'dark' ? 'bg-green-900/20' : 'bg-green-50'
      )
    } else {
      // Tag drag - blue highlight
      e.currentTarget.classList.add(
        theme === 'dark' ? 'bg-blue-900/20' : 'bg-blue-50'
      )
    }
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20', 'bg-green-50', 'bg-green-900/20')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20', 'bg-green-50', 'bg-green-900/20')

    // Check what was dropped
    const tagId = e.dataTransfer.getData('tagId')
    const droppedStrategyId = e.dataTransfer.getData('strategyId')

    if (tagId && onDrop) {
      // Tag was dropped
      onDrop(strategy.id, tagId)
    } else if (droppedStrategyId && onDropStrategy && droppedStrategyId !== strategy.id) {
      // Strategy was dropped (and it's not the same strategy)
      onDropStrategy(droppedStrategyId, strategy.id)
    }
  }

  const positionCount = strategy.position_count || 0
  const totalValue = strategy.total_market_value || 0
  const isPositive = totalValue >= 0
  const isIndividual = positionCount === 1
  const displayType = isIndividual ? 'Individual' : 'Combination'

  return (
    <Card
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={`transition-all cursor-move ${
        theme === 'dark'
          ? 'bg-card-bg-dark border-card-border-dark hover:bg-card-bg-hover-dark'
          : 'bg-card-bg border-card-border hover:bg-card-bg-hover'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Header with expand button */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className={`p-1 rounded transition-colors ${
                theme === 'dark' ? 'hover:bg-slate-700' : 'hover:bg-gray-100'
              }`}
            >
              {isExpanded ? (
                <ChevronDown className={`h-4 w-4 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`} />
              ) : (
                <ChevronRight className={`h-4 w-4 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`} />
              )}
            </button>

            <Layers className="h-4 w-4 text-blue-600" />

            <h3 className={`font-semibold transition-colors duration-300 ${
              theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
            }`}>{strategy.name}</h3>

            <Badge variant="outline" className="text-xs">
              {displayType}
            </Badge>
          </div>

          {/* Description */}
          {strategy.description && (
            <p className={`text-sm mt-2 ml-7 transition-colors duration-300 ${
              theme === 'dark' ? 'text-card-text-muted-dark' : 'text-card-text-muted'
            }`}>{strategy.description}</p>
          )}

          {/* Tags */}
          {strategy.tags && strategy.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2 ml-7">
              {strategy.tags.map((tag) => (
                <Badge
                  key={tag.id}
                  variant="secondary"
                  className="text-xs px-2 py-0.5"
                  style={{ backgroundColor: tag.color || '#3B82F6', color: 'white' }}
                >
                  {tag.name}
                </Badge>
              ))}
            </div>
          )}

          {/* Expanded positions list */}
          {isExpanded && strategy.positions && strategy.positions.length > 0 && (
            <div className={`mt-3 ml-7 space-y-2 border-l-2 pl-3 ${
              theme === 'dark' ? 'border-slate-700' : 'border-gray-200'
            }`}>
              {strategy.positions.map((position: any) => (
                <div key={position.id} className="text-sm">
                  <div className="flex items-center justify-between">
                    <span className={`font-medium transition-colors duration-300 ${
                      theme === 'dark' ? 'text-card-text-dark' : 'text-card-text'
                    }`}>{position.symbol}</span>
                    <span className={`transition-colors duration-300 ${
                      theme === 'dark' ? 'text-card-text-muted-dark' : 'text-card-text-muted'
                    }`}>
                      {position.quantity} @ {formatCurrency(position.current_price || 0)}
                    </span>
                  </div>
                  <div className={`text-xs transition-colors duration-300 ${
                    theme === 'dark' ? 'text-card-text-muted-dark' : 'text-card-text-muted'
                  }`}>
                    Value: {formatCurrency(position.market_value || 0)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(strategy)}
            className="h-8 w-8 p-0"
          >
            <Edit className={`h-4 w-4 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(strategy.id)}
            className="h-8 w-8 p-0"
          >
            <Trash className="h-4 w-4 text-red-600" />
          </Button>
        </div>
      </div>
      </CardContent>
    </Card>
  )
}
