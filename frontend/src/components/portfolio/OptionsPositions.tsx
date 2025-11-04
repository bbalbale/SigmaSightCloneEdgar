'use client'

import React from 'react'
import { PositionList } from '@/components/common/PositionList'
import { OptionPositionCard } from '@/components/positions/OptionPositionCard'
import { useSelectedPortfolio } from '@/hooks/useMultiPortfolio'
import type { OptionPositionView } from '@/types/positions'

interface OptionsPositionsProps {
  positions: OptionPositionView[]
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
