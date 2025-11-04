import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatNumber } from '@/lib/formatters'
import { TagBadge } from '@/components/organize/TagBadge'
import { Badge } from '@/components/ui/badge'

// Tag interface
interface Tag {
  id: string
  name: string
  color: string
}

interface StockPosition {
  symbol: string
  company_name?: string
  sector?: string  // NEW: Sector classification
  industry?: string  // NEW: Industry classification
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
  tags?: Tag[]
  account_name?: string  // NEW: Portfolio/account name for multi-portfolio
}

interface StockPositionCardProps {
  position: StockPosition
  onClick?: () => void
  showAccountBadge?: boolean  // NEW: Show account badge (for aggregate view)
}

export function StockPositionCard({ position, onClick, showAccountBadge = false }: StockPositionCardProps) {
  const companyName = position.company_name || position.symbol
  const sectorInfo = position.sector ? ` • ${position.sector}` : ''

  return (
    <div className="space-y-2">
      <BasePositionCard
        primaryText={position.symbol}
        secondaryText={`${companyName}${sectorInfo}`}
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

      {/* Account Badge (for aggregate view) and Tags */}
      {(showAccountBadge && position.account_name) || (position.tags && position.tags.length > 0) ? (
        <div className="flex flex-wrap gap-1 px-1">
          {/* Account Badge - shown first when in aggregate view */}
          {showAccountBadge && position.account_name && (
            <Badge variant="outline" className="text-xs">
              {position.account_name}
            </Badge>
          )}

          {/* Tags */}
          {position.tags && position.tags.map(tag => (
            <TagBadge key={tag.id} tag={tag} draggable={false} />
          ))}
        </div>
      ) : null}
    </div>
  )
}
