'use client'

import React from 'react'
import { Badge } from '@/components/ui/badge'
import { PrivatePositionCard } from '@/components/positions/PrivatePositionCard'
import { useSelectedPortfolio } from '@/hooks/useMultiPortfolio'
import type { PrivatePositionView } from '@/types/positions'

interface PrivatePositionsProps {
  positions: PrivatePositionView[]
}

export function PrivatePositions({ positions }: PrivatePositionsProps) {
  const { isAggregateView, portfolioCount } = useSelectedPortfolio()

  // Show account badge only in aggregate view with multiple portfolios
  const showAccountBadge = isAggregateView && portfolioCount > 1

  // Group by investment subtype
  const groupedPositions = positions.reduce((acc, position) => {
    const subtype =
      position.investmentSubtype ||
      (position as any).investment_subtype ||
      'Alternative Investment'
    if (!acc[subtype]) acc[subtype] = []
    acc[subtype].push(position)
    return acc
  }, {} as Record<string, PrivatePositionView[]>)

  if (positions.length === 0) {
    return (
      <div className="p-3 rounded-lg transition-colors duration-300" style={{
        fontSize: 'var(--text-sm)',
        color: 'var(--text-secondary)',
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-primary)'
      }}>
        No private or alternative investments
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {Object.entries(groupedPositions).map(([subtype, subtypePositions]) => (
        <div key={subtype}>
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-sm font-medium text-primary">{subtype}</h4>
            <Badge variant="outline" className="text-xs">
              {subtypePositions.length}
            </Badge>
          </div>
          <div className="space-y-2">
            {subtypePositions.map((position, index) => (
              <PrivatePositionCard
                key={position.id || `private-${subtype}-${index}`}
                position={position}
                showAccountBadge={showAccountBadge}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

