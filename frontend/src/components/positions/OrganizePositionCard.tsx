import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatCurrency } from '@/lib/formatters'
import { TagBadge } from '@/components/organize/TagBadge'
import { useTheme } from '@/contexts/ThemeContext'
import { Position } from '@/hooks/usePositions'

interface OrganizePositionCardProps {
  position: Position
  onClick?: () => void
  onRemoveTag?: (positionId: string, tagId: string) => void
}

const OPTION_TYPE_LABELS: Record<string, string> = {
  'LC': 'Long Call',
  'LP': 'Long Put',
  'SC': 'Short Call',
  'SP': 'Short Put'
}

export function OrganizePositionCard({ position, onClick, onRemoveTag }: OrganizePositionCardProps) {
  const { theme } = useTheme()

  // Determine card content based on investment class
  const getCardContent = () => {
    if (position.investment_class === 'OPTIONS') {
      const optionType = OPTION_TYPE_LABELS[position.position_type] || 'Option'
      const strikeInfo = position.strike_price ? ` • Strike: $${position.strike_price}` : ''
      const expInfo = position.expiration_date ? ` • Exp: ${position.expiration_date}` : ''

      return {
        primaryText: position.symbol,
        secondaryText: `${optionType}${strikeInfo}${expInfo}`,
        primaryValue: formatCurrency(Math.abs(position.market_value)),
        secondaryValue: '', // NO P&L on organize page
        secondaryValueColor: 'neutral' as const
      }
    }

    if (position.investment_class === 'PRIVATE') {
      return {
        primaryText: position.symbol,
        secondaryText: position.investment_subtype || 'Alternative Investment',
        primaryValue: formatCurrency(Math.abs(position.market_value)),
        secondaryValue: '', // NO P&L on organize page
        secondaryValueColor: 'neutral' as const
      }
    }

    // PUBLIC (stocks/ETFs)
    const companyInfo = position.company_name || position.symbol
    const sectorInfo = (position as any).sector ? ` • ${(position as any).sector}` : ''

    return {
      primaryText: position.symbol,
      secondaryText: `${companyInfo}${sectorInfo}`,
      primaryValue: formatCurrency(position.market_value),
      secondaryValue: '', // NO P&L on organize page
      secondaryValueColor: 'neutral' as const
    }
  }

  const content = getCardContent()

  return (
    <div className="space-y-2">
      <BasePositionCard {...content} onClick={onClick} />
      {position.tags && position.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 px-1">
          {position.tags.map(tag => (
            <div key={tag.id} className="relative inline-flex items-center">
              <TagBadge tag={tag} draggable={false} />
              {onRemoveTag && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onRemoveTag(position.id, tag.id)
                  }}
                  className="ml-0.5 px-1 py-0 text-xs rounded transition-all duration-200 hover:scale-110"
                  style={{
                    backgroundColor: theme === 'dark' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(239, 68, 68, 0.1)',
                    color: theme === 'dark' ? '#ef4444' : '#dc2626',
                    border: `1px solid ${theme === 'dark' ? '#ef4444' : '#dc2626'}`,
                    fontSize: '10px',
                    lineHeight: '14px',
                    minWidth: '14px',
                    height: '14px'
                  }}
                  title={`Remove ${tag.name} tag`}
                  aria-label={`Remove ${tag.name} tag from ${position.symbol}`}
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
