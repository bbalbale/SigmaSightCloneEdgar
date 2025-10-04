import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatNumber } from '@/lib/formatters'

interface StockPosition {
  symbol: string
  company_name?: string
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
}

interface StockPositionCardProps {
  position: StockPosition
  onClick?: () => void
}

export function StockPositionCard({ position, onClick }: StockPositionCardProps) {
  const companyName = position.company_name || position.symbol

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
