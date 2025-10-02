'use client'

import React, { useState } from 'react'
import { StrategyCard } from './StrategyCard'
import { StockPositionCard } from '@/components/positions/StockPositionCard'
import { OptionPositionCard } from '@/components/positions/OptionPositionCard'
import type { StrategyListItem } from '@/types/strategies'

interface StrategyPositionListProps {
  strategies: StrategyListItem[]
  onEditTags?: (strategyId: string) => void
  className?: string
}

/**
 * StrategyPositionList - Displays strategies with their positions
 *
 * This component demonstrates the StrategyCard wrapper pattern:
 * - Standalone strategies: StrategyCard wraps single position card
 * - Multi-leg strategies: StrategyCard wraps multiple position cards with expand/collapse
 *
 * Usage:
 * ```tsx
 * const { strategies } = useStrategies({ includePositions: true, includeTags: true })
 * <StrategyPositionList strategies={strategies} />
 * ```
 */
export function StrategyPositionList({
  strategies,
  onEditTags,
  className = ''
}: StrategyPositionListProps) {
  // Track which multi-leg strategies are expanded
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const toggleExpand = (strategyId: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(strategyId)) {
        next.delete(strategyId)
      } else {
        next.add(strategyId)
      }
      return next
    })
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {strategies.map(strategy => {
        const isMultiLeg = strategy.strategy_type !== 'standalone'
        const isExpanded = expandedIds.has(strategy.id)

        return (
          <StrategyCard
            key={strategy.id}
            strategy={strategy}
            tags={strategy.tags || []}
            onExpand={isMultiLeg ? () => toggleExpand(strategy.id) : undefined}
            isExpanded={isExpanded}
            onEditTags={onEditTags ? () => onEditTags(strategy.id) : undefined}
            showAggregates={isMultiLeg}
          >
            {/* Render position cards based on strategy type */}
            {isMultiLeg && isExpanded ? (
              // Multi-leg strategy - show all positions when expanded
              <div className="space-y-2 pl-8">
                {(strategy as any).positions?.map((position: any, idx: number) => (
                  <div key={position.id || idx}>
                    {renderPositionCard(position)}
                  </div>
                ))}
              </div>
            ) : !isMultiLeg && (strategy as any).positions?.length > 0 ? (
              // Standalone strategy - show single position
              renderPositionCard((strategy as any).positions[0])
            ) : null}
          </StrategyCard>
        )
      })}

      {strategies.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No combinations found
        </div>
      )}
    </div>
  )
}

/**
 * Render the appropriate position card based on investment class
 */
function renderPositionCard(position: any) {
  const investmentClass = position.investment_class || 'PUBLIC'

  switch (investmentClass) {
    case 'OPTIONS':
      return (
        <OptionPositionCard
          position={{
            id: position.id,
            symbol: position.symbol || position.underlying_symbol,
            type: position.position_type,
            marketValue: position.market_value || 0,
            pnl: position.unrealized_pnl || 0
          }}
        />
      )

    case 'PRIVATE':
      // For private positions, use StockPositionCard with special formatting
      return (
        <StockPositionCard
          position={{
            symbol: position.symbol,
            name: position.name || 'Private Investment',
            marketValue: position.market_value || 0,
            pnl: position.unrealized_pnl || 0,
            positive: (position.unrealized_pnl || 0) >= 0,
            type: position.position_type
          }}
        />
      )

    case 'PUBLIC':
    default:
      return (
        <StockPositionCard
          position={{
            symbol: position.symbol,
            name: position.name,
            marketValue: position.market_value || 0,
            pnl: position.unrealized_pnl || 0,
            positive: (position.unrealized_pnl || 0) >= 0,
            type: position.position_type
          }}
        />
      )
  }
}
