'use client'

import React from 'react'
import { PositionList } from '@/components/common/PositionList'
import { OptionPositionCard } from '@/components/positions/OptionPositionCard'
import { useSelectedPortfolio } from '@/hooks/useMultiPortfolio'

interface OptionPosition {
  id?: string
  symbol: string
  type?: string  // LC, LP, SC, SP
  quantity: number
  marketValue: number
  pnl: number
  positive?: boolean
  price?: number
  strike_price?: number
  expiration_date?: string
  underlying_symbol?: string
  account_name?: string  // NEW: Portfolio/account name for multi-portfolio
}

interface OptionsPositionsProps {
  positions: OptionPosition[]
}

export function OptionsPositions({ positions }: OptionsPositionsProps) {
  const { isAggregateView, portfolioCount } = useSelectedPortfolio()

  // Show account badge only in aggregate view with multiple portfolios
  const showAccountBadge = isAggregateView && portfolioCount > 1

  return (
    <PositionList
      items={positions}
      renderItem={(position, index) => (
        <OptionPositionCard
          key={position.id || `option-${index}`}
          position={position}
          showAccountBadge={showAccountBadge}
        />
      )}
      emptyMessage="No options positions"
    />
  )
}