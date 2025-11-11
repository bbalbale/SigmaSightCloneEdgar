import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatCurrency } from '@/lib/formatters'
import { TagBadge } from '@/components/organize/TagBadge'
import { Badge } from '@/components/ui/badge'
import type { PrivatePositionView } from '@/types/positions'

interface PrivatePositionCardProps {
  position: PrivatePositionView
  onClick?: () => void
  showAccountBadge?: boolean
}

export function PrivatePositionCard({
  position,
  onClick,
  showAccountBadge = false
}: PrivatePositionCardProps) {
  const subtype = position.investmentSubtype || (position as any).investment_subtype || 'Alternative Investment'
  const accountName = position.accountName || (position as any).account_name
  const tags = position.tags || (position as any).tags || []

  return (
    <div className="space-y-2">
      <BasePositionCard
        primaryText={position.symbol}
        secondaryText={subtype}
        primaryValue={formatCurrency(Math.abs(position.marketValue))}
        secondaryValue={
          position.pnl === 0
            ? '--'
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
