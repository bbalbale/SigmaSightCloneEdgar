'use client'

import { Position } from '@/hooks/usePositions'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'

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
  const { theme } = useTheme()
  const isPositive = position.unrealized_pnl >= 0

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (theme === 'dark') {
      e.currentTarget.classList.add('bg-blue-900')
    } else {
      e.currentTarget.classList.add('bg-blue-50')
    }
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900')

    const tagId = e.dataTransfer.getData('tagId')
    if (tagId && onDrop) {
      onDrop(position.id, tagId)
    }
  }

  return (
    <Card
      className={`transition-all cursor-pointer ${
        isSelected
          ? theme === 'dark'
            ? 'bg-blue-900 border-blue-500'
            : 'bg-blue-50 border-blue-400'
          : theme === 'dark'
          ? 'bg-slate-800 border-slate-700 hover:bg-slate-750'
          : 'bg-white border-gray-200 hover:bg-gray-50'
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <CardContent className="p-4">
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
              <h4 className={`font-semibold text-sm transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>{position.symbol}</h4>
              <Badge variant="outline" className="text-xs">
                {position.position_type}
              </Badge>
            </div>

            {position.company_name && (
              <p className={`text-xs transition-colors duration-300 truncate ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>{position.company_name}</p>
            )}

            {/* Options-specific details */}
            {position.investment_class === 'OPTIONS' && (
              <div className={`text-xs mt-1 ${
                theme === 'dark' ? 'text-slate-500' : 'text-gray-500'
              }`}>
                Strike: ${position.strike_price} | Exp: {position.expiration_date}
              </div>
            )}

            <div className="flex items-center gap-4 mt-2 text-sm">
              <span className={`font-medium transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                {formatCurrency(position.market_value)}
              </span>
              <span className={`font-medium ${
                position.unrealized_pnl === 0 ? 'text-slate-400' : isPositive ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {position.unrealized_pnl === 0 ? '—' : `${isPositive ? '+' : ''}${formatCurrency(position.unrealized_pnl)} (${isPositive ? '+' : ''}${formatNumber(position.unrealized_pnl_percent, 2)}%)`}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
