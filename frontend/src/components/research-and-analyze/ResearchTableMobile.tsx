'use client'

import { useState, useCallback, memo } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { TagBadge } from '@/components/organize/TagBadge'
import { CorrelationsSection } from './CorrelationsSection'
import { usePositionRiskMetrics } from '@/hooks/usePositionRiskMetrics'
import { formatCurrency } from '@/lib/formatters'
import type { EnhancedPosition } from '@/services/positionResearchService'
import type { TargetPriceUpdate } from '@/services/targetPriceUpdateService'

interface ResearchTableMobileProps {
  positions: EnhancedPosition[]
  title: string
  aggregateReturnEOY: number
  aggregateReturnNextYear: number
  onTargetPriceUpdate?: (update: TargetPriceUpdate) => Promise<void>
  onTagDrop?: (positionId: string, tagId: string) => Promise<void>
  onRemoveTag?: (positionId: string, tagId: string) => Promise<void>
}

function formatPercentage(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}

function truncateText(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

export function ResearchTableMobile({
  positions,
  title,
  aggregateReturnEOY,
  aggregateReturnNextYear,
  onTargetPriceUpdate,
  onTagDrop,
  onRemoveTag
}: ResearchTableMobileProps) {
  if (positions.length === 0) {
    return (
      <div className="px-4 py-8">
        <div className="rounded-lg p-8 text-center transition-colors duration-300" style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-primary)'
        }}>
          <p className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
            No {title.toLowerCase()} found
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pb-4 space-y-3">
      {positions.map((position) => (
        <PositionCard
          key={position.id}
          position={position}
          onTargetPriceUpdate={onTargetPriceUpdate}
          onTagDrop={onTagDrop}
          onRemoveTag={onRemoveTag}
        />
      ))}
    </div>
  )
}

// Individual position card
interface PositionCardProps {
  position: EnhancedPosition
  onTargetPriceUpdate?: (update: TargetPriceUpdate) => Promise<void>
  onTagDrop?: (positionId: string, tagId: string) => Promise<void>
  onRemoveTag?: (positionId: string, tagId: string) => Promise<void>
}

const PositionCard = memo(function PositionCard({
  position,
  onTargetPriceUpdate,
  onTagDrop,
  onRemoveTag
}: PositionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [userTargetEOY, setUserTargetEOY] = useState(
    position.user_target_eoy?.toString() || position.target_mean_price?.toString() || ''
  )
  const [userTargetNextYear, setUserTargetNextYear] = useState(
    position.user_target_next_year?.toString() || ''
  )
  const [isSaving, setIsSaving] = useState(false)
  const [isDragOver, setIsDragOver] = useState(false)

  // Fetch risk metrics for expanded view
  const { metrics: riskMetrics, loading: riskMetricsLoading } = usePositionRiskMetrics(
    isExpanded ? position.id : '',
    isExpanded ? position.symbol : ''
  )

  // Save targets
  const handleSaveTargets = useCallback(async () => {
    if (!onTargetPriceUpdate) return

    try {
      setIsSaving(true)
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
    } finally {
      setIsSaving(false)
    }
  }, [position, userTargetEOY, userTargetNextYear, onTargetPriceUpdate])

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'copy'
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const tagId = e.dataTransfer.getData('text/plain')
    if (tagId && onTagDrop) {
      await onTagDrop(position.id, tagId)
    }
  }, [position.id, onTagDrop])

  // Check if position is short
  const isShort = ['SHORT', 'SC', 'SP'].includes(position.position_type)

  // Calculate expected returns
  const expectedReturnEOY = userTargetEOY && position.current_price
    ? isShort
      ? ((position.current_price - parseFloat(userTargetEOY)) / position.current_price * 100)
      : ((parseFloat(userTargetEOY) - position.current_price) / position.current_price * 100)
    : position.target_mean_price && position.current_price
      ? isShort
        ? ((position.current_price - position.target_mean_price) / position.current_price * 100)
        : ((position.target_mean_price - position.current_price) / position.current_price * 100)
      : null

  const expectedReturnNextYear = userTargetNextYear && position.current_price
    ? isShort
      ? ((position.current_price - parseFloat(userTargetNextYear)) / position.current_price * 100)
      : ((parseFloat(userTargetNextYear) - position.current_price) / position.current_price * 100)
    : null

  return (
    <div
      className="rounded-lg p-3 transition-all duration-200"
      style={{
        backgroundColor: isExpanded ? 'var(--bg-tertiary)' : 'var(--bg-secondary)',
        border: isDragOver ? '2px solid var(--color-accent)' : '1px solid var(--border-primary)',
        borderColor: isDragOver ? 'var(--color-accent)' : 'var(--border-primary)'
      }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Header: Symbol + Expand + Weight */}
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 flex-1"
        >
          <div className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </div>
          <div className="flex-1">
            <div className="font-bold text-base transition-colors duration-300" style={{ color: 'var(--color-accent)' }}>
              {position.symbol}
            </div>
            <div className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
              {truncateText(position.company_name || position.symbol, 25)}
            </div>
          </div>
        </button>
        <span className="text-xs font-semibold px-2 py-1 rounded transition-colors duration-300" style={{
          backgroundColor: 'var(--bg-tertiary)',
          color: 'var(--text-secondary)'
        }}>
          {position.percent_of_equity?.toFixed(1)}%
        </span>
      </div>

      {/* Current Price */}
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          Current Price
        </span>
        <span className="text-sm font-medium tabular-nums transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          {formatCurrency(position.current_price)}
        </span>
      </div>

      {/* EOY Target (Editable) */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          Your EOY Target
        </span>
        <Input
          type="number"
          step="0.01"
          value={userTargetEOY}
          onChange={(e) => setUserTargetEOY(e.target.value)}
          onBlur={handleSaveTargets}
          placeholder="—"
          disabled={isSaving}
          className="w-20 h-7 text-right text-xs tabular-nums transition-colors duration-300"
          style={{
            backgroundColor: 'var(--bg-primary)',
            borderColor: 'var(--border-primary)',
            color: 'var(--text-primary)'
          }}
        />
      </div>

      {/* EOY Return % */}
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          EOY Return
        </span>
        <span className="text-sm font-bold tabular-nums transition-colors duration-300" style={{
          color: expectedReturnEOY !== null
            ? expectedReturnEOY >= 0 ? 'var(--color-success)' : 'var(--color-error)'
            : 'var(--text-tertiary)'
        }}>
          {formatPercentage(expectedReturnEOY)}
        </span>
      </div>

      {/* Next Year Target (Editable) */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          Next Year Target
        </span>
        <Input
          type="number"
          step="0.01"
          value={userTargetNextYear}
          onChange={(e) => setUserTargetNextYear(e.target.value)}
          onBlur={handleSaveTargets}
          placeholder="—"
          disabled={isSaving}
          className="w-20 h-7 text-right text-xs tabular-nums transition-colors duration-300"
          style={{
            backgroundColor: 'var(--bg-primary)',
            borderColor: 'var(--border-primary)',
            color: 'var(--text-primary)'
          }}
        />
      </div>

      {/* Next Year Return % */}
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          Next Year Return
        </span>
        <span className="text-sm font-bold tabular-nums transition-colors duration-300" style={{
          color: expectedReturnNextYear !== null
            ? expectedReturnNextYear >= 0 ? 'var(--color-success)' : 'var(--color-error)'
            : 'var(--text-tertiary)'
        }}>
          {formatPercentage(expectedReturnNextYear)}
        </span>
      </div>

      {/* Tags */}
      <div className="pt-2 border-t transition-colors duration-300" style={{ borderColor: 'var(--border-primary)' }}>
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
            Tags:
          </span>
          {position.tags && position.tags.length > 0 ? (
            position.tags.map(tag => (
              <div key={tag.id} className="inline-flex items-center gap-1">
                <TagBadge tag={tag} draggable={false} size="sm" />
                {onRemoveTag && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onRemoveTag(position.id, tag.id)
                    }}
                    className="px-1 py-0 text-xs rounded transition-all duration-200 hover:scale-110"
                    style={{
                      backgroundColor: 'var(--color-error-bg, rgba(239, 68, 68, 0.1))',
                      color: 'var(--color-error)',
                      border: '1px solid var(--color-error)',
                      fontSize: '10px',
                      lineHeight: '10px',
                      minWidth: '10px',
                      height: '10px'
                    }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))
          ) : (
            <span className="text-xs transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
              None
            </span>
          )}
        </div>
      </div>

      {/* Expanded Detail */}
      {isExpanded && (
        <ExpandedDetail
          position={position}
          riskMetrics={riskMetrics}
          riskMetricsLoading={riskMetricsLoading}
          onRemoveTag={onRemoveTag}
        />
      )}
    </div>
  )
})

// Expanded detail section
interface ExpandedDetailProps {
  position: EnhancedPosition
  riskMetrics: any
  riskMetricsLoading: boolean
  onRemoveTag?: (positionId: string, tagId: string) => Promise<void>
}

const ExpandedDetail = memo(function ExpandedDetail({
  position,
  riskMetrics,
  riskMetricsLoading,
  onRemoveTag
}: ExpandedDetailProps) {
  const quantity = position.quantity || 0
  const avgCost = position.avg_cost || position.cost_basis || 0
  const marketValue = position.current_market_value || position.market_value || (quantity * position.current_price)
  const pnl = position.unrealized_pnl || 0
  const pnlPercent = position.unrealized_pnl_percent || 0

  // Calculate P/E ratios
  const peThisYear = position.current_year_earnings_avg && position.current_price
    ? position.current_price / position.current_year_earnings_avg
    : null
  const peNextYear = position.next_year_earnings_avg && position.current_price
    ? position.current_price / position.next_year_earnings_avg
    : null

  return (
    <div className="mt-3 pt-3 space-y-3 border-t transition-colors duration-300" style={{
      borderColor: 'var(--border-primary)'
    }}>
      {/* Position Detail */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-2 transition-colors duration-300" style={{
          color: 'var(--text-secondary)'
        }}>
          Position Detail
        </h4>
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>Exposure</span>
            <span className="font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>{formatCurrency(marketValue)}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>Quantity</span>
            <span className="font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>{quantity.toLocaleString()}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>Avg Cost</span>
            <span className="font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>{avgCost > 0 ? formatCurrency(avgCost) : '—'}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>P&L</span>
            <span className="font-medium transition-colors duration-300" style={{
              color: pnl >= 0 ? 'var(--color-success)' : 'var(--color-error)'
            }}>
              {formatCurrency(pnl)} ({formatPercentage(pnlPercent)})
            </span>
          </div>
        </div>
      </div>

      {/* Fundamentals */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-2 transition-colors duration-300" style={{
          color: 'var(--text-secondary)'
        }}>
          Fundamentals
        </h4>
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
            <div className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>P/E (This Yr)</div>
            <div className="text-sm font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>{peThisYear?.toFixed(1) || '—'}</div>
          </div>
          <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
            <div className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>Fwd P/E</div>
            <div className="text-sm font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>{peNextYear?.toFixed(1) || '—'}</div>
          </div>
          <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
            <div className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>EPS</div>
            <div className="text-sm font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
              {position.current_year_earnings_avg ? formatCurrency(position.current_year_earnings_avg) : '—'}
            </div>
          </div>
          <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
            <div className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>Fwd EPS</div>
            <div className="text-sm font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
              {position.next_year_earnings_avg ? formatCurrency(position.next_year_earnings_avg) : '—'}
            </div>
          </div>
        </div>
      </div>

      {/* Risk Metrics */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-2 transition-colors duration-300" style={{
          color: 'var(--text-secondary)'
        }}>
          Risk Metrics
        </h4>
        {riskMetricsLoading ? (
          <p className="text-xs transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
            Loading...
          </p>
        ) : riskMetrics ? (
          <div className="space-y-1.5">
            {riskMetrics.beta !== undefined && (
              <div className="flex justify-between text-xs">
                <span className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>Beta</span>
                <span className="font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>{riskMetrics.beta.toFixed(2)}</span>
              </div>
            )}
            {riskMetrics.volatility_30d !== undefined && (
              <div className="flex justify-between text-xs">
                <span className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>Volatility (30d)</span>
                <span className="font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>{formatPercentage(riskMetrics.volatility_30d)}</span>
              </div>
            )}
            {(riskMetrics.sector || position.sector) && (
              <div className="flex justify-between text-xs">
                <span className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>Sector</span>
                <span className="font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>{riskMetrics.sector || position.sector}</span>
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
            Not available
          </p>
        )}
      </div>

      {/* Correlations */}
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide mb-2 transition-colors duration-300" style={{
          color: 'var(--text-secondary)'
        }}>
          Correlations
        </h4>
        <CorrelationsSection position={position as any} theme="dark" />
      </div>
    </div>
  )
})
