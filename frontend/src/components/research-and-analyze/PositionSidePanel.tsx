'use client'

import React from 'react'
import { Position } from '@/stores/researchStore'
import { SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { CorrelationsSection } from './CorrelationsSection'
import { useTheme } from '@/contexts/ThemeContext'

export interface PositionSidePanelProps {
  position: Position | null
  onClose: () => void
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(2)}`
}

function formatPercentage(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatDate(dateString?: string): string {
  if (!dateString) return 'Not set'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function PositionSidePanel({ position, onClose }: PositionSidePanelProps) {
  const { theme } = useTheme()

  if (!position) {
    return (
      <div className={`p-4 ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
        No position selected
      </div>
    )
  }

  // Extract values with comprehensive fallbacks (matches SimplifiedPositionCard logic)
  const quantity = position.quantity || (position as any).shares || 0
  const currentPrice = (position as any).currentPrice || (position as any).current_price || (position as any).price || 0
  const avgCost = (position as any).avgCost || (position as any).avg_cost || (position as any).cost_basis || 0

  // Market value with calculation fallback
  const marketValue = (position as any).marketValue ||
                      (position as any).current_market_value ||
                      (position as any).market_value ||
                      (quantity * currentPrice)

  // P&L values
  const pnl = (position as any).pnl || (position as any).unrealized_pnl || 0
  const pnlPercent = (position as any).pnlPercent || (position as any).unrealized_pnl_percent || 0

  const pnlColor = pnlPercent >= 0
    ? (theme === 'dark' ? 'text-emerald-400' : 'text-emerald-600')
    : (theme === 'dark' ? 'text-red-400' : 'text-red-600')

  const sectionHeaderClass = "text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-3"
  const sectionContainerClass = `border-b py-4 px-4 ${theme === 'dark' ? 'border-slate-700' : 'border-slate-200'}`
  const labelClass = `text-xs ${theme === 'dark' ? 'text-slate-500' : 'text-slate-600'}`
  const valueClass = `text-sm font-medium ${theme === 'dark' ? 'text-slate-200' : 'text-slate-900'}`

  return (
    <div className="h-full overflow-y-auto">
      <SheetHeader className="px-4 pt-4 pb-2">
        <SheetTitle className={theme === 'dark' ? 'text-white' : 'text-slate-900'}>
          {position.symbol}
        </SheetTitle>
        <p className={`text-sm ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
          {(position as any).company_name || position.companyName || 'Position Details'}
        </p>
      </SheetHeader>

      {/* Section 1: Overview */}
      <div className={sectionContainerClass}>
        <h3 className={sectionHeaderClass}>OVERVIEW</h3>

        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className={labelClass}>Market Value</span>
            <span className={valueClass}>{formatCurrency(marketValue)}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className={labelClass}>Quantity</span>
            <span className={valueClass}>{quantity.toLocaleString()} shares</span>
          </div>

          <div className="flex justify-between items-center">
            <span className={labelClass}>Current Price</span>
            <span className={valueClass}>{currentPrice > 0 ? formatCurrency(currentPrice) : 'N/A'}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className={labelClass}>Avg Cost</span>
            <span className={valueClass}>{avgCost > 0 ? formatCurrency(avgCost) : 'N/A'}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className={labelClass}>P&L</span>
            <span className={`${valueClass} ${pnlColor}`}>{formatCurrency(pnl)}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className={labelClass}>P&L %</span>
            <span className={`${valueClass} ${pnlColor} font-bold`}>{formatPercentage(pnlPercent)}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className={labelClass}>Position Type</span>
            <span className={valueClass}>{position.positionType || (position as any).position_type || 'N/A'}</span>
          </div>

          {position.sector && (
            <div className="flex justify-between items-center">
              <span className={labelClass}>Sector</span>
              <span className={valueClass}>{position.sector}</span>
            </div>
          )}
        </div>
      </div>

      {/* Section 2: Correlations */}
      <div className={sectionContainerClass}>
        <h3 className={sectionHeaderClass}>CORRELATIONS</h3>
        <CorrelationsSection position={position} theme={theme} />
      </div>

      {/* Section 3: Target Price */}
      <div className={sectionContainerClass}>
        <h3 className={sectionHeaderClass}>TARGET PRICE</h3>

        {(() => {
          // EnhancedPosition uses user_target_eoy / user_target_next_year
          const targetPrice = (position as any).user_target_eoy || (position as any).user_target_next_year || position.targetPrice
          const targetReturn = (position as any).target_return_eoy || (position as any).target_return_next_year || position.targetReturn

          if (targetPrice) {
            return (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className={labelClass}>Target Price</span>
                  <span className={valueClass}>{formatCurrency(targetPrice)}</span>
                </div>

                {targetReturn !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={labelClass}>Upside</span>
                    <span className={`${valueClass} ${targetReturn >= 0 ? pnlColor : 'text-red-400'}`}>
                      {formatPercentage(targetReturn)}
                    </span>
                  </div>
                )}

                {(position as any).target_date && (
                  <div className="flex justify-between items-center">
                    <span className={labelClass}>Target Date</span>
                    <span className={valueClass}>{formatDate((position as any).target_date)}</span>
                  </div>
                )}
              </div>
            )
          } else {
            return (
              <p className={`text-sm ${theme === 'dark' ? 'text-slate-500' : 'text-slate-600'}`}>
                No target price set
              </p>
            )
          }
        })()}
      </div>

      {/* Section 4: Tags & Analysis */}
      <div className={sectionContainerClass}>
        <h3 className={sectionHeaderClass}>TAGS & ANALYSIS</h3>

        {position.tags && position.tags.length > 0 ? (
          <div className="flex gap-2 flex-wrap mb-3">
            {position.tags.map((tag) => (
              <span
                key={tag.id}
                className="text-xs px-2 py-1 rounded"
                style={{
                  backgroundColor: `${tag.color}20`,
                  color: tag.color,
                  border: `1px solid ${tag.color}40`
                }}
              >
                {tag.name}
              </span>
            ))}
          </div>
        ) : (
          <p className={`text-sm ${theme === 'dark' ? 'text-slate-500' : 'text-slate-600'} mb-3`}>
            No tags applied
          </p>
        )}

        {/* Placeholder for notes/thesis */}
        <div className="mt-4">
          <span className={labelClass}>Investment Thesis</span>
          <p className={`text-sm mt-1 ${theme === 'dark' ? 'text-slate-400' : 'text-slate-700'}`}>
            Add notes and analysis here...
          </p>
        </div>
      </div>

      {/* Section 5: Risk Metrics */}
      <div className={sectionContainerClass}>
        <h3 className={sectionHeaderClass}>RISK METRICS</h3>

        {(() => {
          // EnhancedPosition may use volatility_30d instead of volatility
          const beta = position.beta || (position as any).market_beta
          const volatility = (position as any).volatility_30d || position.volatility
          const factorExposures = position.factorExposures

          const hasAnyMetrics = beta !== undefined || volatility !== undefined || factorExposures

          if (hasAnyMetrics) {
            return (
              <div className="space-y-3">
                {beta !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={labelClass}>Beta</span>
                    <span className={valueClass}>{Number(beta).toFixed(2)}</span>
                  </div>
                )}

                {volatility !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className={labelClass}>Volatility (30d)</span>
                    <span className={valueClass}>{formatPercentage(volatility)}</span>
                  </div>
                )}

                {factorExposures && (
                  <>
                    <div className="flex justify-between items-center">
                      <span className={labelClass}>Growth Factor</span>
                      <span className={valueClass}>{factorExposures.growth.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className={labelClass}>Momentum Factor</span>
                      <span className={valueClass}>{factorExposures.momentum.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className={labelClass}>Size Factor</span>
                      <span className={valueClass}>{factorExposures.size.toFixed(2)}</span>
                    </div>
                  </>
                )}
              </div>
            )
          } else {
            return (
              <p className={`text-sm ${theme === 'dark' ? 'text-slate-500' : 'text-slate-600'}`}>
                Risk metrics not available
              </p>
            )
          }
        })()}
      </div>
    </div>
  )
}
