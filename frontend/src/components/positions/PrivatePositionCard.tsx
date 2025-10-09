import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatCurrency } from '@/lib/formatters'
import { TagBadge } from '@/components/organize/TagBadge'

// Tag interface
interface Tag {
  id: string
  name: string
  color: string
}

interface PrivatePosition {
  id?: string
  symbol: string
  investment_subtype?: string
  marketValue: number
  pnl: number
  tags?: Tag[]
}

interface PrivatePositionCardProps {
  position: PrivatePosition
  onClick?: () => void
}

export function PrivatePositionCard({ position, onClick }: PrivatePositionCardProps) {
  const subtype = position.investment_subtype || 'Alternative Investment'

  return (
    <div className="space-y-2">
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
