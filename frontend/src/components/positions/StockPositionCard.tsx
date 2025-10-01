import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatNumber } from '@/lib/formatters'

interface StockPosition {
  symbol: string
  name?: string
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
}

interface StockPositionCardProps {
  position: StockPosition
  onClick?: () => void
}

// Company name mappings (moved from old PositionCard)
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

export function StockPositionCard({ position, onClick }: StockPositionCardProps) {
  const companyName = position.name || COMPANY_NAMES[position.symbol] || 'Company'

  return (
    <BasePositionCard
      primaryText={position.symbol}
      secondaryText={companyName}
      primaryValue={formatNumber(position.marketValue)}
      secondaryValue={
        position.pnl === 0
          ? '—'
          : `${position.positive ? '+' : ''}${formatNumber(position.pnl)}`
      }
      secondaryValueColor={
        position.pnl === 0
          ? 'neutral'
          : position.positive
            ? 'positive'
            : 'negative'
      }
      onClick={onClick}
    />
  )
}
