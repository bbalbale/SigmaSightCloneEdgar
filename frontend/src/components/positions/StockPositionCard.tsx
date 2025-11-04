import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatNumber } from '@/lib/formatters'
import { TagBadge } from '@/components/organize/TagBadge'
import { Badge } from '@/components/ui/badge'
import type { PublicPositionView } from '@/types/positions'

interface StockPositionCardProps {
  position: PublicPositionView
  onClick?: () => void
  showAccountBadge?: boolean
}

export function StockPositionCard({
  position,
  onClick,
  showAccountBadge = false
}: StockPositionCardProps) {
  const companyName = position.companyName || (position as any).company_name || position.symbol
  const accountName = position.accountName || (position as any).account_name
  const tags = position.tags || (position as any).tags || []
  const sectorInfo = position.sector ? ` - ${position.sector}` : ''

  return (
    <div className="space-y-2">
      <BasePositionCard
        primaryText={position.symbol}
        secondaryText={`${companyName}${sectorInfo}`}
        primaryValue={formatNumber(position.marketValue)}
        secondaryValue={
          position.pnl === 0
            ? '--'
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

      {(showAccountBadge && accountName) || tags.length > 0 ? (
        <div className="flex flex-wrap gap-1 px-1">
          {showAccountBadge && accountName && (
            <Badge variant="outline" className="text-xs">
              {accountName}
            </Badge>
          )}

          {tags.map((tag: any) => (
            <TagBadge key={tag.id} tag={tag} draggable={false} />
          ))}
        </div>
      ) : null}
    </div>
  )
}
