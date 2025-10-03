import React from 'react'
import { BasePositionCard } from '@/components/common/BasePositionCard'
import { formatCurrency } from '@/lib/formatters'
import { TagBadge } from '@/components/organize/TagBadge'
import { useTheme } from '@/contexts/ThemeContext'

// Tag interface
interface Tag {
  id: string
  name: string
  color: string
}

// Position interface from usePositions hook
interface Position {
  id: string
  symbol: string
  company_name?: string
  market_value: number
  investment_class: string
  position_type: string
  strike_price?: number
  expiration_date?: string
  investment_subtype?: string
  tags?: Tag[]
}

interface OrganizePositionCardProps {
  position: Position
  onClick?: () => void
}

const OPTION_TYPE_LABELS: Record<string, string> = {
  'LC': 'Long Call',
  'LP': 'Long Put',
  'SC': 'Short Call',
  'SP': 'Short Put'
}

export function OrganizePositionCard({ position, onClick }: OrganizePositionCardProps) {
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
    return {
      primaryText: position.symbol,
      secondaryText: position.company_name || 'Company',
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
            <TagBadge key={tag.id} tag={tag} draggable={false} />
          ))}
        </div>
      )}
    </div>
  )
}
