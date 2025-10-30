// src/components/positions/ResearchPositionCard.tsx
'use client'

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { TagBadge } from '@/components/organize/TagBadge'
import { Input } from '@/components/ui/input'
import { formatCurrency } from '@/lib/formatters'
import { useTheme } from '@/contexts/ThemeContext'
import { usePortfolioStore } from '@/stores/portfolioStore'
import type { EnhancedPosition } from '@/services/positionResearchService'
import targetPriceService from '@/services/targetPriceService'
import type { TargetPriceUpdate } from '@/services/targetPriceUpdateService'

interface ResearchPositionCardProps {
  position: EnhancedPosition
  onClick?: () => void
  onTargetPriceUpdate?: (update: TargetPriceUpdate) => Promise<void>
}

export function ResearchPositionCard({ position, onClick, onTargetPriceUpdate }: ResearchPositionCardProps) {
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
  const hasAutoSavedRef = useRef(false)

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

  // Auto-save analyst target as user target when no user target exists
  useEffect(() => {
    // Only run once per position
    if (hasAutoSavedRef.current) return

    // Check if we need to auto-save analyst target as user target
    const needsAutoSave =
      portfolioId &&
      !position.user_target_eoy && // No user target exists (0, null, undefined)
      position.target_mean_price && // Analyst target exists
      position.target_mean_price > 0 // Valid analyst target

    if (needsAutoSave) {
      hasAutoSavedRef.current = true

      // Automatically save analyst target as user target
      targetPriceService.createOrUpdate(portfolioId, {
        symbol: position.symbol,
        position_type: position.position_type,
        target_price_eoy: position.target_mean_price, // Save analyst as user target
        current_price: position.current_price,
        position_id: position.id,
      }).catch(error => {
        console.error('Failed to auto-save analyst target:', error)
        // Reset flag on error so it can retry
        hasAutoSavedRef.current = false
      })
    }
  }, [portfolioId, position.user_target_eoy, position.target_mean_price, position.symbol, position.position_type, position.current_price, position.id])

  // Debounced save handler - saves both targets when either input changes
  // Uses optimistic update for instant UI feedback
  const handleSaveTargets = useCallback(async () => {
    if (!portfolioId || !onTargetPriceUpdate) return

    try {
      setIsSaving(true)

      // Call optimistic update callback with target data
      // This will update UI instantly and sync to backend in background
      await onTargetPriceUpdate({
        symbol: position.symbol,
        position_type: position.position_type,
        position_id: position.id,
        current_price: position.current_price,
        target_price_eoy: userTargetEOY ? parseFloat(userTargetEOY) : undefined,
        target_price_next_year: userTargetNextYear ? parseFloat(userTargetNextYear) : undefined,
      })
    } catch (error) {
      console.error('Failed to update target prices:', error)
      // Error is already handled by optimistic update service (rollback)
    } finally {
      setIsSaving(false)
    }
  }, [portfolioId, position, userTargetEOY, userTargetNextYear, onTargetPriceUpdate])

  // Debounce save on blur (500ms delay)
  const debouncedSave = useCallback(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    saveTimeoutRef.current = setTimeout(() => {
      handleSaveTargets()
    }, 500)
  }, [handleSaveTargets])

  // Handle Enter key - save immediately without debounce
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      // Clear any pending debounced save
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      // Save immediately
      handleSaveTargets()
      // Blur the input to give visual feedback
      e.currentTarget.blur()
    }
  }, [handleSaveTargets])

  // Check if position is short (return calculation needs to be inverted)
  const isShort = ['SHORT', 'SC', 'SP'].includes(position.position_type)

  // Calculate expected returns from current price
  // For shorts: if target price goes UP, we LOSE money (inverse calculation)
  // EOY: Use user target first, fallback to analyst target
  const expectedReturnEOY = userTargetEOY && position.current_price
    ? isShort
      ? ((position.current_price - parseFloat(userTargetEOY)) / position.current_price * 100)
      : ((parseFloat(userTargetEOY) - position.current_price) / position.current_price * 100)
    : position.target_mean_price && position.current_price
      ? isShort
        ? ((position.current_price - position.target_mean_price) / position.current_price * 100)
        : ((position.target_mean_price - position.current_price) / position.current_price * 100)
      : null

  // Next Year: Use user target only (no analyst data available for next year)
  const expectedReturnNextYear = userTargetNextYear && position.current_price
    ? isShort
      ? ((position.current_price - parseFloat(userTargetNextYear)) / position.current_price * 100)
      : ((parseFloat(userTargetNextYear) - position.current_price) / position.current_price * 100)
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
                  {position.percent_of_equity.toFixed(2)}% of equity
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
                {expectedReturnEOY !== null ? `${expectedReturnEOY >= 0 ? '+' : ''}${expectedReturnEOY.toFixed(1)}%` : '—'}
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
                {expectedReturnNextYear !== null ? `${expectedReturnNextYear >= 0 ? '+' : ''}${expectedReturnNextYear.toFixed(1)}%` : '—'}
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
              onKeyDown={handleKeyDown}
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
              onKeyDown={handleKeyDown}
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
                  {peThisYear !== null ? peThisYear.toFixed(1) : '—'}
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
                  {psThisYear !== null ? psThisYear.toFixed(2) : '—'}
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
                  {peNextYear !== null ? peNextYear.toFixed(1) : '—'}
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
                  {psNextYear !== null ? psNextYear.toFixed(2) : '—'}
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
