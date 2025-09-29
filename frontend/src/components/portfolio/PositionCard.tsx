import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { formatNumber } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'

interface Position {
  symbol: string
  name?: string
  marketValue: number
  pnl: number
  positive?: boolean
}

interface PositionCardProps {
  position: Position
}

// Company name mappings
const COMPANY_NAMES: Record<string, string> = {
  'AAPL': 'Apple Inc.',
  'MSFT': 'Microsoft Corporation',
  'GOOGL': 'Alphabet Inc.',
  'NVDA': 'NVIDIA Corporation',
  'AMZN': 'Amazon.com, Inc.',
  'META': 'Meta Platforms Inc.',
  'TSLA': 'Tesla, Inc.',
  'JPM': 'JPMorgan Chase & Co.',
  'JNJ': 'Johnson & Johnson',
  'V': 'Visa Inc.',
  'PG': 'Procter & Gamble Co.',
  'UNH': 'UnitedHealth Group Inc.',
  'HD': 'The Home Depot, Inc.',
  'MA': 'Mastercard Inc.',
  'DIS': 'The Walt Disney Company',
  'BAC': 'Bank of America Corp.',
  'ADBE': 'Adobe Inc.',
  'NFLX': 'Netflix, Inc.',
  'CRM': 'Salesforce, Inc.',
  'PFE': 'Pfizer Inc.'
}

export function PositionCard({ position }: PositionCardProps) {
  const { theme } = useTheme()

  const companyName = position.name || COMPANY_NAMES[position.symbol] || 'Company'

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
            }`}>{position.symbol}</div>
            <div className={`text-xs transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              {companyName}
            </div>
          </div>
          <div className="text-right">
            <div className={`text-sm font-medium transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>{formatNumber(position.marketValue)}</div>
            <div className={`text-sm font-medium ${
              position.pnl === 0 ? 'text-slate-400' : position.positive ? 'text-emerald-400' : 'text-red-400'
            }`}>
              {position.pnl === 0 ? '—' : `${position.positive ? '+' : ''}${formatNumber(position.pnl)}`}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}