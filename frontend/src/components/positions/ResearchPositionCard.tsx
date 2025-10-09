// src/components/positions/ResearchPositionCard.tsx
'use client'

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { TagBadge } from '@/components/organize/TagBadge'
import { Input } from '@/components/ui/input'
import { formatCurrency, formatNumber } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'
import { usePortfolioStore } from '@/stores/portfolioStore'
import targetPriceService from '@/services/targetPriceService'
import type { EnhancedPosition } from '@/services/positionResearchService'

interface ResearchPositionCardProps {
  position: EnhancedPosition
  onClick?: () => void
}

export function ResearchPositionCard({ position, onClick }: ResearchPositionCardProps) {
  const { theme } = useTheme()
  const { portfolioId } = usePortfolioStore()
  // Prepopulate EOY target with analyst target if no user target exists (treat 0 as no target)
  const [userTargetEOY, setUserTargetEOY] = useState(
    position.user_target_eoy
      ? position.user_target_eoy.toString()
      : position.target_mean_price?.toString() || ''
  )
  const [userTargetNextYear, setUserTargetNextYear] = useState(
    position.user_target_next_year
      ? position.user_target_next_year.toString()
      : ''
  )
  const [isSaving, setIsSaving] = useState(false)
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Update state when position data changes (handles async data loading)
  useEffect(() => {
    // Prepopulate EOY target: user target takes precedence (if > 0), fallback to analyst
    const eoyShouldBe = position.user_target_eoy
      ? position.user_target_eoy.toString()
      : position.target_mean_price?.toString() || ''

    if (eoyShouldBe && !userTargetEOY) {
      setUserTargetEOY(eoyShouldBe)
    }

    // Prepopulate next year target
    const nextYearShouldBe = position.user_target_next_year
      ? position.user_target_next_year.toString()
      : ''

    if (nextYearShouldBe && !userTargetNextYear) {
      setUserTargetNextYear(nextYearShouldBe)
    }
  }, [position.user_target_eoy, position.target_mean_price, position.user_target_next_year])

  // Debounced save handler - saves both targets when either input changes
  const handleSaveTargets = useCallback(async () => {
    if (!portfolioId) return

    try {
      setIsSaving(true)

      await targetPriceService.createOrUpdate(portfolioId, {
        symbol: position.symbol,
        position_type: position.position_type,
        target_price_eoy: userTargetEOY ? parseFloat(userTargetEOY) : undefined,
        target_price_next_year: userTargetNextYear ? parseFloat(userTargetNextYear) : undefined,
        current_price: position.current_price,
        position_id: position.id,
      })
    } catch (error) {
      console.error('Failed to save target prices:', error)
    } finally {
      setIsSaving(false)
    }
  }, [portfolioId, position, userTargetEOY, userTargetNextYear])

  // Debounce save on blur (500ms delay)
  const debouncedSave = useCallback(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    saveTimeoutRef.current = setTimeout(() => {
      handleSaveTargets()
    }, 500)
  }, [handleSaveTargets])

  // Calculate returns for display
  const targetReturnEOY = userTargetEOY && position.current_price
    ? ((parseFloat(userTargetEOY) - position.current_price) / position.current_price * 100)
    : null

  const targetReturnNextYear = userTargetNextYear && position.current_price
    ? ((parseFloat(userTargetNextYear) - position.current_price) / position.current_price * 100)
    : null

  // Calculate expected returns from current price (based on analyst target and user targets)
  const expectedReturnEOY = position.target_mean_price && position.current_price
    ? ((position.target_mean_price - position.current_price) / position.current_price * 100)
    : null

  const expectedReturnNextYear = userTargetNextYear && position.current_price
    ? ((parseFloat(userTargetNextYear) - position.current_price) / position.current_price * 100)
    : null

  // Calculate P/E ratios
  const peThisYear = position.current_year_earnings_avg && position.current_price
    ? position.current_price / position.current_year_earnings_avg
    : null

  const peNextYear = position.next_year_earnings_avg && position.current_price
    ? position.current_price / position.next_year_earnings_avg
    : null

  // Calculate P/S ratios (Price to Sales)
  // Formula: Market Cap / Total Revenue
  const psThisYear = position.market_cap && position.current_year_revenue_avg
    ? position.market_cap / position.current_year_revenue_avg
    : null

  const psNextYear = position.market_cap && position.next_year_revenue_avg
    ? position.market_cap / position.next_year_revenue_avg
    : null

  return (
    <div
      onClick={onClick}
      className={`group relative overflow-hidden rounded-lg border transition-all duration-300 ${
        theme === 'dark'
          ? 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600 hover:shadow-lg hover:shadow-slate-900/50'
          : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-lg hover:shadow-gray-200/50'
      } ${onClick ? 'cursor-pointer' : ''}`}
    >
      {/* Header Section */}
      <div className={`border-b px-4 py-3 transition-colors duration-300 ${
        theme === 'dark' ? 'border-slate-700/50' : 'border-gray-100'
      }`}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-baseline gap-2 mb-1">
              <div>
                <h3 className={`text-lg font-bold tracking-tight transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {position.symbol}
                </h3>
                <div className={`text-xs transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  {position.company_name || position.symbol}
                </div>
              </div>
              {position.percent_of_equity !== undefined && (
                <span className={`text-xs font-medium transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  {formatNumber(position.percent_of_equity, 2)}% of equity
                </span>
              )}
            </div>

            {/* Tags */}
            {position.tags && position.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {position.tags.map(tag => (
                  <TagBadge key={tag.id} tag={tag} draggable={false} />
                ))}
              </div>
            )}
          </div>

          {/* Expected Returns - Prominent Display */}
          <div className="flex gap-4 ml-4">
            <div className="text-right">
              <div className={`text-xs font-medium mb-0.5 transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
              }`}>
                EOY Target
              </div>
              <div className={`text-lg font-bold tabular-nums ${
                expectedReturnEOY !== null
                  ? expectedReturnEOY >= 0 ? 'text-emerald-500' : 'text-rose-500'
                  : theme === 'dark' ? 'text-slate-600' : 'text-gray-300'
              }`}>
                {expectedReturnEOY !== null ? `${expectedReturnEOY >= 0 ? '+' : ''}${formatNumber(expectedReturnEOY, 1)}%` : '—'}
              </div>
            </div>
            <div className="text-right">
              <div className={`text-xs font-medium mb-0.5 transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
              }`}>
                Next Year
              </div>
              <div className={`text-lg font-bold tabular-nums ${
                expectedReturnNextYear !== null
                  ? expectedReturnNextYear >= 0 ? 'text-emerald-500' : 'text-rose-500'
                  : theme === 'dark' ? 'text-slate-600' : 'text-gray-300'
              }`}>
                {expectedReturnNextYear !== null ? `${expectedReturnNextYear >= 0 ? '+' : ''}${formatNumber(expectedReturnNextYear, 1)}%` : '—'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Price & Targets Section */}
      <div className={`border-b px-4 py-3 transition-colors duration-300 ${
        theme === 'dark' ? 'border-slate-700/50' : 'border-gray-100'
      }`}>
        <div className="grid grid-cols-4 gap-6">
          <div className={`p-2 rounded-md transition-colors duration-300 ${
            theme === 'dark' ? 'bg-slate-900/30' : 'bg-white/50'
          }`}>
            <div className={`text-xs font-medium mb-1.5 transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
            }`}>
              Current Price
            </div>
            <div className={`text-base font-semibold tabular-nums transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              {formatCurrency(position.current_price)}
            </div>
          </div>

          <div className={`p-2 rounded-md transition-colors duration-300 ${
            theme === 'dark' ? 'bg-slate-900/30' : 'bg-white/50'
          }`}>
            <div className={`text-xs font-medium mb-1.5 transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
            }`}>
              Analyst Target
            </div>
            <div className={`text-base font-semibold tabular-nums transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              {position.target_mean_price ? formatCurrency(position.target_mean_price) : '—'}
            </div>
          </div>

          <div>
            <label className={`text-xs font-medium mb-1.5 block transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
            }`}>
              Your EOY Target
            </label>
            <Input
              type="number"
              step="0.01"
              value={userTargetEOY}
              onChange={(e) => setUserTargetEOY(e.target.value)}
              onBlur={debouncedSave}
              placeholder="Enter"
              disabled={isSaving}
              className={`h-8 text-sm font-semibold tabular-nums transition-colors duration-300 ${
                theme === 'dark'
                  ? 'bg-slate-900/50 border-slate-600 focus:border-blue-500 text-white placeholder:text-slate-500'
                  : 'bg-white border-gray-300 focus:border-blue-500 text-gray-900 placeholder:text-gray-400'
              }`}
            />
          </div>

          <div>
            <label className={`text-xs font-medium mb-1.5 block transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
            }`}>
              Next Year Target
            </label>
            <Input
              type="number"
              step="0.01"
              value={userTargetNextYear}
              onChange={(e) => setUserTargetNextYear(e.target.value)}
              onBlur={debouncedSave}
              placeholder="Enter"
              disabled={isSaving}
              className={`h-8 text-sm font-semibold tabular-nums transition-colors duration-300 ${
                theme === 'dark'
                  ? 'bg-slate-900/50 border-slate-600 focus:border-blue-500 text-white placeholder:text-slate-500'
                  : 'bg-white border-gray-300 focus:border-blue-500 text-gray-900 placeholder:text-gray-400'
              }`}
            />
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="px-4 py-3">
        <div className="grid grid-cols-2 gap-6">
          {/* Current Year Metrics */}
          <div>
            <h4 className={`text-xs font-semibold mb-3 uppercase tracking-wide transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Current Year
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div className={`p-3 rounded-lg transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-900/50' : 'bg-gray-50'
              }`}>
                <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  P/E Ratio
                </div>
                <div className={`text-sm font-semibold tabular-nums transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {peThisYear !== null ? formatNumber(peThisYear, 1) : '—'}
                </div>
              </div>

              <div className={`p-3 rounded-lg transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-900/50' : 'bg-gray-50'
              }`}>
                <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  P/S Ratio
                </div>
                <div className={`text-sm font-semibold tabular-nums transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {psThisYear !== null ? formatNumber(psThisYear, 2) : '—'}
                </div>
              </div>

              <div className={`p-3 rounded-lg transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-900/50' : 'bg-gray-50'
              }`}>
                <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  EPS
                </div>
                <div className={`text-sm font-semibold tabular-nums transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {position.current_year_earnings_avg ? formatCurrency(position.current_year_earnings_avg) : '—'}
                </div>
              </div>

              <div className={`p-3 rounded-lg transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-900/50' : 'bg-gray-50'
              }`}>
                <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  Revenue
                </div>
                <div className={`text-sm font-semibold tabular-nums transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {position.current_year_revenue_avg ? `$${(position.current_year_revenue_avg / 1e9).toFixed(1)}B` : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Forward Year Metrics */}
          <div>
            <h4 className={`text-xs font-semibold mb-3 uppercase tracking-wide transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Forward Year
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div className={`p-3 rounded-lg transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-900/50' : 'bg-gray-50'
              }`}>
                <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  Fwd P/E
                </div>
                <div className={`text-sm font-semibold tabular-nums transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {peNextYear !== null ? formatNumber(peNextYear, 1) : '—'}
                </div>
              </div>

              <div className={`p-3 rounded-lg transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-900/50' : 'bg-gray-50'
              }`}>
                <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  Fwd P/S
                </div>
                <div className={`text-sm font-semibold tabular-nums transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {psNextYear !== null ? formatNumber(psNextYear, 2) : '—'}
                </div>
              </div>

              <div className={`p-3 rounded-lg transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-900/50' : 'bg-gray-50'
              }`}>
                <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  Fwd EPS
                </div>
                <div className={`text-sm font-semibold tabular-nums transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {position.next_year_earnings_avg ? formatCurrency(position.next_year_earnings_avg) : '—'}
                </div>
              </div>

              <div className={`p-3 rounded-lg transition-colors duration-300 ${
                theme === 'dark' ? 'bg-slate-900/50' : 'bg-gray-50'
              }`}>
                <div className={`text-xs font-medium mb-1 transition-colors duration-300 ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                }`}>
                  Fwd Revenue
                </div>
                <div className={`text-sm font-semibold tabular-nums transition-colors duration-300 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {position.next_year_revenue_avg ? `$${(position.next_year_revenue_avg / 1e9).toFixed(1)}B` : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Hover effect overlay */}
      <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none ${
        theme === 'dark' ? 'bg-gradient-to-r from-blue-500/5 to-purple-500/5' : 'bg-gradient-to-r from-blue-500/3 to-purple-500/3'
      }`} />
    </div>
  )
}
