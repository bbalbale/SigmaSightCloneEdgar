import React from 'react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'
import { formatCurrency } from '@/lib/formatters'

interface PrivatePosition {
  id?: string
  symbol: string
  name?: string
  quantity: number
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
  investment_subtype?: string
  price?: number
}

interface PrivatePositionsProps {
  positions: PrivatePosition[]
}

export function PrivatePositions({ positions }: PrivatePositionsProps) {
  const { theme } = useTheme()

  // Group by investment subtype if available
  const groupedPositions = positions.reduce((acc, position) => {
    const subtype = position.investment_subtype || 'Alternative Investment'
    if (!acc[subtype]) acc[subtype] = []
    acc[subtype].push(position)
    return acc
  }, {} as Record<string, PrivatePosition[]>)

  const renderPrivateCard = (position: PrivatePosition) => {
    return (
      <Card
        key={position.id || `private-${position.symbol}`}
        className={`p-4 transition-all duration-300 hover:shadow-md cursor-pointer ${
          theme === 'dark'
            ? 'bg-slate-800 border-slate-700 hover:bg-slate-750'
            : 'bg-white border-gray-200 hover:bg-gray-50'
        }`}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h4 className={`font-medium ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                {position.name || position.symbol}
              </h4>
              {position.investment_subtype && (
                <Badge variant="outline" className="text-xs text-purple-600">
                  {position.investment_subtype}
                </Badge>
              )}
            </div>
            <div className={`text-sm space-y-1 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              <div className="flex items-center gap-4">
                <span>Symbol: {position.symbol}</span>
                {position.quantity && (
                  <span>Shares: {position.quantity.toLocaleString()}</span>
                )}
              </div>
              <div className="flex items-center gap-4">
                <span>Investment Value: {formatCurrency(Math.abs(position.marketValue))}</span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <p className={`text-lg font-semibold ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              {formatCurrency(Math.abs(position.marketValue))}
            </p>
            <p className={`text-sm font-medium mt-1 ${
              position.pnl >= 0
                ? theme === 'dark' ? 'text-emerald-400' : 'text-emerald-600'
                : theme === 'dark' ? 'text-red-400' : 'text-red-600'
            }`}>
              {position.pnl >= 0 ? '+' : ''}{formatCurrency(position.pnl)}
              <span className="text-xs ml-1">
                ({position.pnl >= 0 ? '+' : ''}{((position.pnl / Math.abs(position.marketValue)) * 100).toFixed(1)}%)
              </span>
            </p>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {Object.entries(groupedPositions).map(([subtype, subtypePositions]) => (
        <div key={subtype}>
          <div className="flex items-center gap-2 mb-3">
            <h4 className={`text-sm font-medium ${
              theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
            }`}>{subtype}</h4>
            <Badge variant="outline" className="text-xs">
              {subtypePositions.length}
            </Badge>
          </div>
          <div className="space-y-2">
            {subtypePositions.map(renderPrivateCard)}
          </div>
        </div>
      ))}

      {positions.length === 0 && (
        <div className={`text-sm p-3 rounded-lg border ${
          theme === 'dark'
            ? 'text-slate-400 bg-slate-800/50 border-slate-700'
            : 'text-gray-500 bg-gray-50 border-gray-200'
        }`}>
          No private or alternative investments
        </div>
      )}
    </div>
  )
}