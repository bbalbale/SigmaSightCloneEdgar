// src/components/positions/ResearchPositionCard.tsx
'use client'

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { TagBadge } from '@/components/organize/TagBadge'
import { Input } from '@/components/ui/input'
import { formatCurrency } from '@/lib/formatters'
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
      className="group relative overflow-hidden rounded-lg border transition-all duration-300 hover:shadow-lg"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)',
        cursor: onClick ? 'pointer' : 'default'
      }}
    >
      {/* Header Section */}
      <div className="border-b px-4 py-3 transition-colors duration-300" style={{
        borderColor: 'var(--border-primary)'
      }}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-baseline gap-2 mb-1">
              <div>
                <h3 className="tracking-tight transition-colors duration-300" style={{
                  fontSize: 'var(--text-lg)',
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-display)'
                }}>
                  {position.symbol}
                </h3>
                <div className="transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  {position.company_name || position.symbol}
                </div>
              </div>
              {position.percent_of_equity !== undefined && (
                <span className="font-medium transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
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
              <div className="font-medium mb-0.5 transition-colors duration-300" style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)'
              }}>
                EOY Target
              </div>
              <div className="font-bold tabular-nums" style={{
                fontSize: 'var(--text-lg)',
                color: expectedReturnEOY !== null
                  ? expectedReturnEOY >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                  : 'var(--text-tertiary)'
              }}>
                {expectedReturnEOY !== null ? `${expectedReturnEOY >= 0 ? '+' : ''}${expectedReturnEOY.toFixed(1)}%` : '—'}
              </div>
            </div>
            <div className="text-right">
              <div className="font-medium mb-0.5 transition-colors duration-300" style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)'
              }}>
                Next Year
              </div>
              <div className="font-bold tabular-nums" style={{
                fontSize: 'var(--text-lg)',
                color: expectedReturnNextYear !== null
                  ? expectedReturnNextYear >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                  : 'var(--text-tertiary)'
              }}>
                {expectedReturnNextYear !== null ? `${expectedReturnNextYear >= 0 ? '+' : ''}${expectedReturnNextYear.toFixed(1)}%` : '—'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Price & Targets Section */}
      <div className="border-b px-4 py-3 transition-colors duration-300" style={{
        borderColor: 'var(--border-primary)'
      }}>
        <div className="grid grid-cols-4 gap-6">
          <div className="p-2 rounded-md transition-colors duration-300" style={{
            backgroundColor: 'var(--bg-tertiary)'
          }}>
            <div className="font-medium mb-1.5 transition-colors duration-300" style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)'
            }}>
              Current Price
            </div>
            <div className="font-semibold tabular-nums transition-colors duration-300" style={{
              fontSize: 'var(--text-base)',
              color: 'var(--text-primary)'
            }}>
              {formatCurrency(position.current_price)}
            </div>
          </div>

          <div className="p-2 rounded-md transition-colors duration-300" style={{
            backgroundColor: 'var(--bg-tertiary)'
          }}>
            <div className="font-medium mb-1.5 transition-colors duration-300" style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)'
            }}>
              Analyst Target
            </div>
            <div className="font-semibold tabular-nums transition-colors duration-300" style={{
              fontSize: 'var(--text-base)',
              color: 'var(--text-primary)'
            }}>
              {position.target_mean_price ? formatCurrency(position.target_mean_price) : '—'}
            </div>
          </div>

          <div>
            <label className="font-medium mb-1.5 block transition-colors duration-300" style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)'
            }}>
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
              className="h-8 font-semibold tabular-nums transition-colors duration-300"
              style={{
                fontSize: 'var(--text-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                borderColor: 'var(--border-primary)',
                color: 'var(--text-primary)'
              }}
            />
          </div>

          <div>
            <label className="font-medium mb-1.5 block transition-colors duration-300" style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)'
            }}>
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
              className="h-8 font-semibold tabular-nums transition-colors duration-300"
              style={{
                fontSize: 'var(--text-sm)',
                backgroundColor: 'var(--bg-tertiary)',
                borderColor: 'var(--border-primary)',
                color: 'var(--text-primary)'
              }}
            />
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="px-4 py-3">
        <div className="grid grid-cols-2 gap-6">
          {/* Current Year Metrics */}
          <div>
            <h4 className="font-semibold mb-3 uppercase tracking-wide transition-colors duration-300" style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)'
            }}>
              Current Year
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <div className="font-medium mb-1 transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  P/E Ratio
                </div>
                <div className="font-semibold tabular-nums transition-colors duration-300" style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)'
                }}>
                  {peThisYear !== null ? peThisYear.toFixed(1) : '—'}
                </div>
              </div>

              <div className="p-3 rounded-lg transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <div className="font-medium mb-1 transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  P/S Ratio
                </div>
                <div className="font-semibold tabular-nums transition-colors duration-300" style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)'
                }}>
                  {psThisYear !== null ? psThisYear.toFixed(2) : '—'}
                </div>
              </div>

              <div className="p-3 rounded-lg transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <div className="font-medium mb-1 transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  EPS
                </div>
                <div className="font-semibold tabular-nums transition-colors duration-300" style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)'
                }}>
                  {position.current_year_earnings_avg ? formatCurrency(position.current_year_earnings_avg) : '—'}
                </div>
              </div>

              <div className="p-3 rounded-lg transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <div className="font-medium mb-1 transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Revenue
                </div>
                <div className="font-semibold tabular-nums transition-colors duration-300" style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)'
                }}>
                  {position.current_year_revenue_avg ? `$${(position.current_year_revenue_avg / 1e9).toFixed(1)}B` : '—'}
                </div>
              </div>
            </div>
          </div>

          {/* Forward Year Metrics */}
          <div>
            <h4 className="font-semibold mb-3 uppercase tracking-wide transition-colors duration-300" style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-secondary)'
            }}>
              Forward Year
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <div className="font-medium mb-1 transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Fwd P/E
                </div>
                <div className="font-semibold tabular-nums transition-colors duration-300" style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)'
                }}>
                  {peNextYear !== null ? peNextYear.toFixed(1) : '—'}
                </div>
              </div>

              <div className="p-3 rounded-lg transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <div className="font-medium mb-1 transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Fwd P/S
                </div>
                <div className="font-semibold tabular-nums transition-colors duration-300" style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)'
                }}>
                  {psNextYear !== null ? psNextYear.toFixed(2) : '—'}
                </div>
              </div>

              <div className="p-3 rounded-lg transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <div className="font-medium mb-1 transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Fwd EPS
                </div>
                <div className="font-semibold tabular-nums transition-colors duration-300" style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)'
                }}>
                  {position.next_year_earnings_avg ? formatCurrency(position.next_year_earnings_avg) : '—'}
                </div>
              </div>

              <div className="p-3 rounded-lg transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <div className="font-medium mb-1 transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Fwd Revenue
                </div>
                <div className="font-semibold tabular-nums transition-colors duration-300" style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)'
                }}>
                  {position.next_year_revenue_avg ? `$${(position.next_year_revenue_avg / 1e9).toFixed(1)}B` : '—'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Hover effect overlay */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" style={{
        background: 'linear-gradient(to right, rgba(59, 130, 246, 0.03), rgba(147, 51, 234, 0.03))'
      }} />
    </div>
  )
}
