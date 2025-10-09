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

interface OptionPosition {
  id?: string
  symbol: string
  type?: string  // LC, LP, SC, SP
  marketValue: number
  pnl: number
  tags?: Tag[]
}

interface OptionPositionCardProps {
  position: OptionPosition
  onClick?: () => void
}

const OPTION_TYPE_LABELS: Record<string, string> = {
  'LC': 'Long Call',
  'LP': 'Long Put',
  'SC': 'Short Call',
  'SP': 'Short Put'
}

export function OptionPositionCard({ position, onClick }: OptionPositionCardProps) {
  const optionTypeLabel = OPTION_TYPE_LABELS[position.type || ''] || 'Option'

  return (
    <div className="space-y-2">
      <BasePositionCard
        primaryText={position.symbol}
        secondaryText={optionTypeLabel}
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
