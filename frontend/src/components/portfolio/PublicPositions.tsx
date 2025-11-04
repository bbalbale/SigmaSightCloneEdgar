'use client'

import React from 'react'
import { PositionList } from '@/components/common/PositionList'
import { StockPositionCard } from '@/components/positions/StockPositionCard'
import { useSelectedPortfolio } from '@/hooks/useMultiPortfolio'

interface Position {
  id?: string
  symbol: string
  company_name?: string
  quantity: number
  marketValue: number
  pnl: number
  positive?: boolean
  type?: string
  investment_class?: string
  investment_subtype?: string
  price?: number
  account_name?: string  // NEW: Portfolio/account name for multi-portfolio
}

interface PublicPositionsProps {
  positions: Position[]
}

export function PublicPositions({ positions }: PublicPositionsProps) {
  const { isAggregateView, portfolioCount } = useSelectedPortfolio()

  // Show account badge only in aggregate view with multiple portfolios
  const showAccountBadge = isAggregateView && portfolioCount > 1

  return (
    <PositionList
      items={positions}
      renderItem={(position, index) => (
        <StockPositionCard
          key={position.id || `public-${index}`}
          position={{
            ...position,
            // Ensure negative display for shorts
            marketValue: position.type === 'SHORT' ? -Math.abs(position.marketValue) : position.marketValue
          }}
          showAccountBadge={showAccountBadge}
        />
      )}
      emptyMessage="No positions"
    />
  )
}