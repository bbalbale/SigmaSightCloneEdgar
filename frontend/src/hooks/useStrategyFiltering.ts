/**
 * useStrategyFiltering Hook
 *
 * Filters strategies by investment class and direction to maintain the same
 * 3-column layout structure as the position-based portfolio view.
 *
 * Layout Structure:
 * Row 1: Public Longs | Public Shorts | Private Investments
 * Row 2: Long Options | Short Options | (empty)
 *
 * Usage:
 * ```tsx
 * const { strategies } = useStrategies({ includePositions: true })
 * const filtered = useStrategyFiltering(strategies)
 * // filtered.publicLongs, filtered.publicShorts, etc.
 * ```
 */

import { useMemo } from 'react'
import type { StrategyListItem } from '@/types/strategies'

export interface FilteredStrategies {
  // Public positions (Row 1, Columns 1-3)
  publicLongs: StrategyListItem[]
  publicShorts: StrategyListItem[]
  privateStrategies: StrategyListItem[]

  // Options (Row 2, Columns 1-2)
  optionLongs: StrategyListItem[]
  optionShorts: StrategyListItem[]

  // Counts for badges
  counts: {
    publicLongs: number
    publicShorts: number
    private: number
    optionLongs: number
    optionShorts: number
    total: number
  }
}

/**
 * Filter strategies by investment class and direction
 */
export function useStrategyFiltering(strategies: StrategyListItem[]): FilteredStrategies {
  return useMemo(() => {
    // Public Longs: PUBLIC investment class, LONG direction
    const publicLongs = strategies.filter(
      s => s.primary_investment_class === 'PUBLIC' && s.direction === 'LONG'
    )

    // Public Shorts: PUBLIC investment class, SHORT direction
    const publicShorts = strategies.filter(
      s => s.primary_investment_class === 'PUBLIC' && s.direction === 'SHORT'
    )

    // Private Investments: PRIVATE investment class (any direction)
    const privateStrategies = strategies.filter(
      s => s.primary_investment_class === 'PRIVATE'
    )

    // Long Options: OPTIONS investment class, LC or LP direction
    const optionLongs = strategies.filter(
      s => s.primary_investment_class === 'OPTIONS' &&
           (s.direction === 'LC' || s.direction === 'LP')
    )

    // Short Options: OPTIONS investment class, SC or SP direction
    const optionShorts = strategies.filter(
      s => s.primary_investment_class === 'OPTIONS' &&
           (s.direction === 'SC' || s.direction === 'SP')
    )

    return {
      publicLongs,
      publicShorts,
      privateStrategies,
      optionLongs,
      optionShorts,
      counts: {
        publicLongs: publicLongs.length,
        publicShorts: publicShorts.length,
        private: privateStrategies.length,
        optionLongs: optionLongs.length,
        optionShorts: optionShorts.length,
        total: strategies.length
      }
    }
  }, [strategies])
}

/**
 * Helper function to check if a strategy should be displayed in a specific category
 */
export function isStrategyInCategory(
  strategy: StrategyListItem,
  category: 'public-long' | 'public-short' | 'private' | 'option-long' | 'option-short'
): boolean {
  switch (category) {
    case 'public-long':
      return strategy.primary_investment_class === 'PUBLIC' && strategy.direction === 'LONG'

    case 'public-short':
      return strategy.primary_investment_class === 'PUBLIC' && strategy.direction === 'SHORT'

    case 'private':
      return strategy.primary_investment_class === 'PRIVATE'

    case 'option-long':
      return strategy.primary_investment_class === 'OPTIONS' &&
             (strategy.direction === 'LC' || strategy.direction === 'LP')

    case 'option-short':
      return strategy.primary_investment_class === 'OPTIONS' &&
             (strategy.direction === 'SC' || strategy.direction === 'SP')

    default:
      return false
  }
}
