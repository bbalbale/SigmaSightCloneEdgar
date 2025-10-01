import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatCurrency } from '@/lib/formatters'

interface PrivatePosition {
  id?: string
  symbol: string
  investment_subtype?: string
  marketValue: number
  pnl: number
}

interface PrivatePositionCardProps {
  position: PrivatePosition
  onClick?: () => void
}

export function PrivatePositionCard({ position, onClick }: PrivatePositionCardProps) {
  const subtype = position.investment_subtype || 'Alternative Investment'

  return (
    <BasePositionCard
      primaryText={position.symbol}
      secondaryText={subtype}
      primaryValue={formatCurrency(Math.abs(position.marketValue))}
      secondaryValue={
        position.pnl === 0
          ? '—'
          : `${position.pnl >= 0 ? '+' : ''}${formatCurrency(position.pnl)}`
      }
      secondaryValueColor={
        position.pnl === 0
          ? 'neutral'
          : position.pnl >= 0
            ? 'positive'
            : 'negative'
      }
      onClick={onClick}
    />
  )
}
