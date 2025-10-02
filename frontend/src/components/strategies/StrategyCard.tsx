'use client'

import React, { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { TagBadge } from '@/components/organize/TagBadge'
import type { StrategyListItem, StrategyTag } from '@/types/strategies'
import { ChevronDown, ChevronRight, Tag as TagIcon } from 'lucide-react'

interface StrategyCardProps {
  strategy: StrategyListItem
  children: React.ReactNode
  tags?: StrategyTag[]
  onExpand?: () => void
  isExpanded?: boolean
  onEditTags?: () => void
  onEdit?: () => void
  onDelete?: () => void
  showAggregates?: boolean
  className?: string
}

/**
 * StrategyCard - Wrapper component for position cards that adds strategy features
 *
 * Follows the SelectablePositionCard pattern - wraps existing position cards
 * as children and adds strategy-specific functionality (tags, expansion, etc.)
 *
 * Usage:
 * ```tsx
 * // Standalone strategy (wraps single position card)
 * <StrategyCard strategy={strategy} tags={tags}>
 *   <StockPositionCard position={strategy.positions[0]} />
 * </StrategyCard>
 *
 * // Multi-leg strategy (wraps multiple position cards)
 * <StrategyCard
 *   strategy={strategy}
 *   tags={tags}
 *   onExpand={() => toggle()}
 *   isExpanded={expanded}
 *   showAggregates
 * >
 *   {expanded && strategy.positions.map(pos => (
 *     <OptionPositionCard key={pos.id} position={pos} />
 *   ))}
 * </StrategyCard>
 * ```
 */
export function StrategyCard({
  strategy,
  children,
  tags = [],
  onExpand,
  isExpanded = false,
  onEditTags,
  onEdit,
  onDelete,
  showAggregates = false,
  className = ''
}: StrategyCardProps) {
  const { theme } = useTheme()
  const isMultiLeg = strategy.strategy_type !== 'standalone'

  return (
    <div
      className={`
        rounded-lg transition-all
        ${theme === 'dark' ? 'bg-slate-800/50' : 'bg-white'}
        ${className}
      `}
    >
      {/* Strategy Header - Only show for multi-leg strategies */}
      {isMultiLeg && (
        <div
          className={`
            px-4 py-3 flex items-center justify-between border-b
            ${theme === 'dark' ? 'border-slate-700' : 'border-gray-200'}
          `}
        >
          {/* Left: Expand button + Strategy name/type */}
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {/* Expand/Collapse button */}
            {onExpand && (
              <button
                onClick={onExpand}
                className={`
                  p-1 rounded transition-colors
                  ${theme === 'dark'
                    ? 'hover:bg-slate-700 text-slate-400 hover:text-slate-200'
                    : 'hover:bg-gray-100 text-gray-500 hover:text-gray-700'
                  }
                `}
                aria-label={isExpanded ? 'Collapse strategy' : 'Expand strategy'}
              >
                {isExpanded ? (
                  <ChevronDown className="h-5 w-5" />
                ) : (
                  <ChevronRight className="h-5 w-5" />
                )}
              </button>
            )}

            {/* Strategy name and type */}
            <div className="flex-1 min-w-0">
              <div className={`
                font-medium truncate
                ${theme === 'dark' ? 'text-slate-200' : 'text-gray-900'}
              `}>
                {strategy.name}
              </div>
              <div className={`
                text-sm truncate
                ${theme === 'dark' ? 'text-slate-400' : 'text-gray-500'}
              `}>
                {formatStrategyType(strategy.strategy_type)}
                {strategy.position_count && ` • ${strategy.position_count} legs`}
              </div>
            </div>
          </div>

          {/* Right: Tags + Actions */}
          <div className="flex items-center gap-2">
            {/* Tags */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tags.map(tag => (
                  <TagBadge key={tag.id} tag={tag} />
                ))}
              </div>
            )}

            {/* Tag edit button */}
            {onEditTags && (
              <button
                onClick={onEditTags}
                className={`
                  p-2 rounded transition-colors
                  ${theme === 'dark'
                    ? 'hover:bg-slate-700 text-slate-400 hover:text-slate-200'
                    : 'hover:bg-gray-100 text-gray-500 hover:text-gray-700'
                  }
                `}
                aria-label="Edit tags"
              >
                <TagIcon className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Position cards (children) */}
      <div className={isMultiLeg && isExpanded ? 'p-2 space-y-2' : ''}>
        {children}
      </div>

      {/* Tags for standalone strategies - show below position card */}
      {!isMultiLeg && tags.length > 0 && (
        <div className="px-4 pb-3 flex items-center gap-2">
          <div className="flex flex-wrap gap-1">
            {tags.map(tag => (
              <TagBadge key={tag.id} tag={tag} />
            ))}
          </div>
          {onEditTags && (
            <button
              onClick={onEditTags}
              className={`
                p-1 rounded transition-colors
                ${theme === 'dark'
                  ? 'hover:bg-slate-700 text-slate-400 hover:text-slate-200'
                  : 'hover:bg-gray-100 text-gray-500 hover:text-gray-700'
                }
              `}
              aria-label="Edit tags"
            >
              <TagIcon className="h-3 w-3" />
            </button>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Format strategy type for display
 */
function formatStrategyType(type: string): string {
  const typeMap: Record<string, string> = {
    standalone: 'Standalone',
    covered_call: 'Covered Call',
    protective_put: 'Protective Put',
    iron_condor: 'Iron Condor',
    straddle: 'Straddle',
    strangle: 'Strangle',
    butterfly: 'Butterfly',
    pairs_trade: 'Pairs Trade',
    custom: 'Custom Strategy'
  }
  return typeMap[type] || type
}
