import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { formatCurrency } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'

interface OptionPosition {
  id?: string
  symbol: string
  type?: string  // LC, LP, SC, SP
  marketValue: number
  pnl: number
  positive?: boolean
}

interface OptionCardProps {
  position: OptionPosition
}

export function OptionCard({ position }: OptionCardProps) {
  const { theme } = useTheme()

  const optionTypeLabel = {
    'LC': 'Long Call',
    'LP': 'Long Put',
    'SC': 'Short Call',
    'SP': 'Short Put'
  }[position.type || ''] || 'Option'

  return (
    <Card className={`transition-colors cursor-pointer ${
      theme === 'dark'
        ? 'bg-slate-800 border-slate-700 hover:bg-slate-750'
        : 'bg-white border-gray-200 hover:bg-gray-50'
    }`}>
      <CardContent className="p-4">
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
      </CardContent>
    </Card>
  )
}
