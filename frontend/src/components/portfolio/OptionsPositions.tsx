import React from 'react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'
import { formatCurrency } from '@/lib/formatters'

interface OptionPosition {
  id?: string
  symbol: string
  type?: string  // LC, LP, SC, SP
  quantity: number
  marketValue: number
  pnl: number
  positive?: boolean
  price?: number
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
}

interface OptionsPositionsProps {
  positions: OptionPosition[]
}

export function OptionsPositions({ positions }: OptionsPositionsProps) {
  const { theme } = useTheme()

  // Group options by type
  const longCalls = positions.filter(p => p.type === 'LC')
  const longPuts = positions.filter(p => p.type === 'LP')
  const shortCalls = positions.filter(p => p.type === 'SC')
  const shortPuts = positions.filter(p => p.type === 'SP')

  const renderOptionCard = (position: OptionPosition) => {
    const optionTypeLabel = {
      'LC': 'Long Call',
      'LP': 'Long Put',
      'SC': 'Short Call',
      'SP': 'Short Put'
    }[position.type || ''] || 'Option'

    return (
      <Card
        key={position.id || `option-${position.symbol}`}
        className={`transition-colors cursor-pointer ${
          theme === 'dark'
            ? 'bg-slate-800 border-slate-700 hover:bg-slate-750'
            : 'bg-white border-gray-200 hover:bg-gray-50'
        }`}
      >
        <div className="p-4">
          <div className="flex justify-between items-start">
            <div>
              <div className={`font-semibold text-sm transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                {position.symbol}
              </div>
              <div className={`text-xs transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>
                {optionTypeLabel}
              </div>
            </div>
            <div className="text-right">
              <div className={`text-sm font-medium transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                {formatCurrency(Math.abs(position.marketValue))}
              </div>
              <div className={`text-sm font-medium ${
                position.pnl === 0 ? 'text-slate-400' : position.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
              }`}>
                {position.pnl === 0 ? '—' : `${position.pnl >= 0 ? '+' : ''}${formatCurrency(position.pnl)}`}
              </div>
            </div>
          </div>
        </div>
      </Card>
    )
  }

  const renderOptionGroup = (title: string, options: OptionPosition[], colorClass: string) => {
    if (options.length === 0) return null

    return (
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <h4 className={`text-sm font-medium ${
            theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
          }`}>{title}</h4>
          <Badge variant="outline" className={`text-xs ${colorClass}`}>
            {options.length}
          </Badge>
        </div>
        <div className="space-y-2">
          {options.map(renderOptionCard)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {renderOptionGroup('Long Calls', longCalls, 'text-green-600')}
      {renderOptionGroup('Long Puts', longPuts, 'text-green-600')}
      {renderOptionGroup('Short Calls', shortCalls, 'text-red-600')}
      {renderOptionGroup('Short Puts', shortPuts, 'text-red-600')}

      {positions.length === 0 && (
        <div className={`text-sm p-3 rounded-lg border ${
          theme === 'dark'
            ? 'text-slate-400 bg-slate-800/50 border-slate-700'
            : 'text-gray-500 bg-gray-50 border-gray-200'
        }`}>
          No options positions
        </div>
      )}
    </div>
  )
}