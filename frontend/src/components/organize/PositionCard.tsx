'use client'

import { Position } from '@/hooks/usePositions'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatNumber } from '@/lib/formatters'

interface PositionCardProps {
  position: Position
  isSelected: boolean
  onToggleSelection: (id: string) => void
  onDrop?: (positionId: string, tagId: string) => void
}

export function PositionCard({
  position,
  isSelected,
  onToggleSelection,
  onDrop
}: PositionCardProps) {
  const isPositive = position.unrealized_pnl >= 0

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
      onDrop(position.id, tagId)
    }
  }

  return (
    <div
      className={`
        border rounded-lg p-3 transition-all
        ${isSelected ? 'bg-blue-50 border-blue-400' : 'bg-white hover:bg-gray-50 border-gray-200'}
      `}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onToggleSelection(position.id)}
          className="mt-1 h-4 w-4 cursor-pointer"
        />

        {/* Position Details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-gray-900">{position.symbol}</h4>
            <Badge variant="outline" className="text-xs">
              {position.position_type}
            </Badge>
          </div>

          {position.company_name && (
            <p className="text-sm text-gray-600 truncate">{position.company_name}</p>
          )}

          {/* Options-specific details */}
          {position.investment_class === 'OPTIONS' && (
            <div className="text-xs text-gray-500 mt-1">
              Strike: ${position.strike_price} | Exp: {position.expiration_date}
            </div>
          )}

          <div className="flex items-center gap-4 mt-2 text-sm">
            <span className="text-gray-700 font-medium">
              {formatCurrency(position.market_value)}
            </span>
            <span className={isPositive ? 'text-green-600' : 'text-red-600'}>
              {isPositive ? '+' : ''}{formatCurrency(position.unrealized_pnl)}
              {' '}({isPositive ? '+' : ''}{formatNumber(position.unrealized_pnl_percent, 2)}%)
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
