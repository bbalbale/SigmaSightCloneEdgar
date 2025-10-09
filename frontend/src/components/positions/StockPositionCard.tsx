import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatNumber } from '@/lib/formatters'
import { TagBadge } from '@/components/organize/TagBadge'

// Tag interface
interface Tag {
  id: string
  name: string
  color: string
}

interface StockPosition {
  symbol: string
  company_name?: string
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
  tags?: Tag[]
}

interface StockPositionCardProps {
  position: StockPosition
  onClick?: () => void
}

export function StockPositionCard({ position, onClick }: StockPositionCardProps) {
  const companyName = position.company_name || position.symbol

  return (
    <div className="space-y-2">
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
      {position.tags && position.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 px-1">
          {position.tags.map(tag => (
            <TagBadge key={tag.id} tag={tag} draggable={false} />
          ))}
        </div>
      )}
    </div>
  )
}
