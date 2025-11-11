'use client'

import React from 'react'
import { PositionList } from '@/components/common/PositionList'
import { StockPositionCard } from '@/components/positions/StockPositionCard'
import { useSelectedPortfolio } from '@/hooks/useMultiPortfolio'
import type { PublicPositionView } from '@/types/positions'

interface PublicPositionsProps {
  positions: PublicPositionView[]
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
            marketValue: position.type === 'SHORT'
              ? -Math.abs(position.marketValue)
              : position.marketValue
          }}
          showAccountBadge={showAccountBadge}
        />
      )}
      emptyMessage="No positions"
    />
  )
}
