'use client'

import { useState } from 'react'
import { StrategyListItem } from '@/services/strategiesApi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Edit, Trash, ChevronDown, ChevronRight, Layers } from 'lucide-react'
import { formatCurrency } from '@/lib/formatters'

interface StrategyCardProps {
  strategy: StrategyListItem
  onEdit: (strategy: StrategyListItem) => void
  onDelete: (strategyId: string) => void
  onDrop?: (strategyId: string, tagId: string) => void
}

export function StrategyCard({
  strategy,
  onEdit,
  onDelete,
  onDrop
}: StrategyCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.add('bg-blue-50')
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('bg-blue-50')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.remove('bg-blue-50')

    const tagId = e.dataTransfer.getData('tagId')
    if (tagId && onDrop) {
      onDrop(strategy.id, tagId)
    }
  }

  const positionCount = strategy.position_count || 0
  const totalValue = strategy.total_market_value || 0
  const isPositive = totalValue >= 0
  const isIndividual = positionCount === 1
  const displayType = isIndividual ? 'Individual' : 'Combination'

  return (
    <div
      className="border rounded-lg p-4 bg-white hover:bg-gray-50 transition-all"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Header with expand button */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-gray-100 rounded transition-colors"
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-500" />
              )}
            </button>

            <Layers className="h-4 w-4 text-blue-600" />

            <h3 className="font-semibold text-gray-900">{strategy.name}</h3>

            <Badge variant="outline" className="text-xs">
              {displayType}
            </Badge>
          </div>

          {/* Description */}
          {strategy.description && (
            <p className="text-sm text-gray-600 mt-2 ml-7">{strategy.description}</p>
          )}

          {/* Metrics */}
          <div className="flex items-center gap-4 mt-2 ml-7 text-sm">
            <span className="text-gray-500">{positionCount} {positionCount === 1 ? 'position' : 'positions'}</span>
            {strategy.total_market_value !== undefined && strategy.total_market_value !== null && (
              <span className={`font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                Value: {formatCurrency(strategy.total_market_value)}
              </span>
            )}
          </div>

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
            <div className="mt-3 ml-7 space-y-2 border-l-2 border-gray-200 pl-3">
              {strategy.positions.map((position: any) => (
                <div key={position.id} className="text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{position.symbol}</span>
                    <span className="text-gray-600">
                      {position.quantity} @ {formatCurrency(position.current_price || 0)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500">
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
            <Edit className="h-4 w-4 text-gray-600" />
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
    </div>
  )
}
