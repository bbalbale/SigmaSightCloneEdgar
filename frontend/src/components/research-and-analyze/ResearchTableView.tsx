'use client'

import { useState, useMemo, useCallback, memo } from 'react'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { TagBadge } from '@/components/organize/TagBadge'
import { CorrelationsSection } from './CorrelationsSection'
import { usePositionRiskMetrics } from '@/hooks/usePositionRiskMetrics'
import { formatCurrency } from '@/lib/formatters'
import type { EnhancedPosition } from '@/services/positionResearchService'
import type { TargetPriceUpdate } from '@/services/targetPriceUpdateService'

interface ResearchTableViewProps {
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

export function ResearchTableView({
  positions,
  title,
  aggregateReturnEOY,
  aggregateReturnNextYear,
  onTargetPriceUpdate,
  onTagDrop,
  onRemoveTag
}: ResearchTableViewProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [filterBy, setFilterBy] = useState<'all' | 'tag' | 'sector' | 'industry'>('all')
  const [filterValue, setFilterValue] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'percent_of_equity' | 'symbol' | 'target_return_eoy'>('percent_of_equity')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Toggle row expansion
  const toggleRow = useCallback((positionId: string) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev)
      if (newSet.has(positionId)) {
        newSet.delete(positionId)
      } else {
        newSet.add(positionId)
      }
      return newSet
    })
  }, [])

  // Filter options
  const filterOptions = useMemo(() => {
    if (filterBy === 'tag') {
      const tags = new Set<string>()
      positions.forEach(p => p.tags?.forEach(t => tags.add(t.name)))
      return Array.from(tags).sort()
    }
    if (filterBy === 'sector') {
      return Array.from(new Set(positions.map(p => p.sector).filter((s): s is string => Boolean(s)))).sort()
    }
    if (filterBy === 'industry') {
      return Array.from(new Set(positions.map(p => p.industry).filter((i): i is string => Boolean(i)))).sort()
    }
    return []
  }, [positions, filterBy])

  // Filter and sort positions
  const processedPositions = useMemo(() => {
    // Filter
    let filtered = positions
    if (filterBy !== 'all' && filterValue !== 'all') {
      filtered = positions.filter(p => {
        if (filterBy === 'tag') {
          return p.tags?.some(t => t.name === filterValue)
        }
        if (filterBy === 'sector') {
          return p.sector === filterValue
        }
        if (filterBy === 'industry') {
          return p.industry === filterValue
        }
        return true
      })
    }

    // Sort
    return [...filtered].sort((a, b) => {
      const aValue = a[sortBy] as any
      const bValue = b[sortBy] as any

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortOrder === 'asc' ? aValue - bValue : bValue - aValue
      }

      return sortOrder === 'asc'
        ? String(aValue || '').localeCompare(String(bValue || ''))
        : String(bValue || '').localeCompare(String(aValue || ''))
    })
  }, [positions, filterBy, filterValue, sortBy, sortOrder])

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="rounded-lg border p-4 transition-all duration-300" style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)'
      }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="transition-colors duration-300" style={{
              fontSize: 'var(--text-lg)',
              fontWeight: 600,
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-display)'
            }}>
              {title}
            </h3>
            <Badge variant="secondary" className="transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--color-accent)'
            }}>
              {processedPositions.length}
            </Badge>
          </div>

          {/* Aggregate Returns */}
          <div className="flex gap-6">
            <div className="text-right">
              <div className="mb-1 transition-colors duration-300" style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}>
                Expected Return EOY
              </div>
              <div className="tabular-nums" style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 700,
                color: aggregateReturnEOY >= 0 ? 'var(--color-success)' : 'var(--color-error)'
              }}>
                {formatPercentage(aggregateReturnEOY)}
              </div>
            </div>
            <div className="text-right">
              <div className="mb-1 transition-colors duration-300" style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 500,
                color: 'var(--text-secondary)'
              }}>
                Expected Return Next Year
              </div>
              <div className="tabular-nums" style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 700,
                color: aggregateReturnNextYear >= 0 ? 'var(--color-success)' : 'var(--color-error)'
              }}>
                {formatPercentage(aggregateReturnNextYear)}
              </div>
            </div>
          </div>
        </div>

        {/* Filter and Sort Controls */}
        <div className="flex gap-3 flex-wrap">
          <Select value={filterBy} onValueChange={(v: any) => { setFilterBy(v); setFilterValue('all') }}>
            <SelectTrigger className="w-[180px] transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)'
            }}>
              <SelectValue placeholder="Filter by..." />
            </SelectTrigger>
            <SelectContent className="themed-card">
              <SelectItem value="all">All Positions</SelectItem>
              <SelectItem value="tag">Filter by Tag</SelectItem>
              <SelectItem value="sector">Filter by Sector</SelectItem>
              <SelectItem value="industry">Filter by Industry</SelectItem>
            </SelectContent>
          </Select>

          {filterBy !== 'all' && filterOptions.length > 0 && (
            <Select value={filterValue} onValueChange={setFilterValue}>
              <SelectTrigger className="w-[200px] transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-primary)',
                borderColor: 'var(--border-primary)'
              }}>
                <SelectValue placeholder={`Select ${filterBy}...`} />
              </SelectTrigger>
              <SelectContent className="themed-card">
                <SelectItem value="all">All {filterBy}s</SelectItem>
                {filterOptions.map(option => (
                  <SelectItem key={option} value={option}>{option}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Select value={sortBy} onValueChange={(v: any) => setSortBy(v)}>
            <SelectTrigger className="w-[180px] transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)'
            }}>
              <SelectValue placeholder="Sort by..." />
            </SelectTrigger>
            <SelectContent className="themed-card">
              <SelectItem value="percent_of_equity">% of Portfolio</SelectItem>
              <SelectItem value="symbol">Symbol (A-Z)</SelectItem>
              <SelectItem value="target_return_eoy">Return EOY</SelectItem>
            </SelectContent>
          </Select>

          <Select value={sortOrder} onValueChange={(v: any) => setSortOrder(v)}>
            <SelectTrigger className="w-[140px] transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)'
            }}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="themed-card">
              <SelectItem value="desc">High to Low</SelectItem>
              <SelectItem value="asc">Low to High</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-hidden transition-all duration-300" style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)'
      }}>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b transition-colors duration-300" style={{
                borderColor: 'var(--border-primary)',
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <th className="w-8"></th>
                <th className="text-left px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)',
                  maxWidth: '200px'
                }}>
                  Position
                </th>
                <th className="text-right px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  % Portfolio
                </th>
                <th className="text-right px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Current Price
                </th>
                <th className="text-right px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Your EOY Target
                </th>
                <th className="text-right px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  EOY Return %
                </th>
                <th className="text-right px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Next Year Target
                </th>
                <th className="text-right px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Next Year Return %
                </th>
                <th className="text-right px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)'
                }}>
                  Analyst Target
                </th>
                <th className="text-left px-4 py-3 font-semibold transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-secondary)',
                  width: '220px',
                  maxWidth: '220px'
                }}>
                  Tags
                </th>
              </tr>
            </thead>
            <tbody>
              {processedPositions.map((position) => (
                <ResearchTableRow
                  key={position.id}
                  position={position}
                  isExpanded={expandedRows.has(position.id)}
                  onToggle={() => toggleRow(position.id)}
                  onTargetPriceUpdate={onTargetPriceUpdate}
                  onTagDrop={onTagDrop}
                  onRemoveTag={onRemoveTag}
                />
              ))}
            </tbody>
          </table>
        </div>

        {processedPositions.length === 0 && (
          <div className="text-center py-12 transition-colors duration-300" style={{
            color: 'var(--text-secondary)'
          }}>
            No {title.toLowerCase()} found
          </div>
        )}
      </div>
    </div>
  )
}

// Individual table row with expandable detail
interface ResearchTableRowProps {
  position: EnhancedPosition
  isExpanded: boolean
  onToggle: () => void
  onTargetPriceUpdate?: (update: TargetPriceUpdate) => Promise<void>
  onTagDrop?: (positionId: string, tagId: string) => Promise<void>
  onRemoveTag?: (positionId: string, tagId: string) => Promise<void>
}

const ResearchTableRow = memo(function ResearchTableRow({ position, isExpanded, onToggle, onTargetPriceUpdate, onTagDrop, onRemoveTag }: ResearchTableRowProps) {
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

  // Drag and drop handlers for tag application
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
    console.log('Tag dropped on position:', { positionId: position.id, tagId })

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
    <>
      {/* Main Row */}
      <tr
        className="border-b transition-all duration-200 hover:bg-opacity-50"
        style={{
          borderColor: isDragOver ? 'var(--color-accent)' : 'var(--border-primary)',
          backgroundColor: isDragOver
            ? 'rgba(59, 130, 246, 0.1)'
            : isExpanded ? 'var(--bg-tertiary)' : 'transparent',
          borderWidth: isDragOver ? '2px' : '1px'
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Expand/Collapse Button */}
        <td className="px-2">
          <button
            onClick={onToggle}
            className="p-1 rounded hover:bg-opacity-20 transition-colors duration-200"
            style={{
              color: 'var(--text-secondary)'
            }}
          >
            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>
        </td>

        {/* Position */}
        <td className="px-4 py-3" style={{ maxWidth: '200px' }}>
          <div>
            <div className="font-semibold transition-colors duration-300" style={{
              fontSize: 'var(--text-sm)',
              color: 'var(--text-primary)'
            }}>
              {position.symbol}
            </div>
            <div
              className="transition-colors duration-300"
              style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)'
              }}
              title={position.company_name || position.symbol}
            >
              {truncateText(position.company_name || position.symbol, 30)}
            </div>
          </div>
        </td>

        {/* % Portfolio */}
        <td className="px-4 py-3 text-right tabular-nums transition-colors duration-300" style={{
          fontSize: 'var(--text-sm)',
          color: 'var(--text-primary)'
        }}>
          {position.percent_of_equity?.toFixed(1)}%
        </td>

        {/* Current Price */}
        <td className="px-4 py-3 text-right tabular-nums transition-colors duration-300" style={{
          fontSize: 'var(--text-sm)',
          color: 'var(--text-primary)'
        }}>
          {formatCurrency(position.current_price)}
        </td>

        {/* Your EOY Target (Editable) */}
        <td className="px-4 py-3">
          <Input
            type="number"
            step="0.01"
            value={userTargetEOY}
            onChange={(e) => setUserTargetEOY(e.target.value)}
            onBlur={handleSaveTargets}
            placeholder="—"
            disabled={isSaving}
            className="w-24 h-8 text-right tabular-nums transition-colors duration-300"
            style={{
              fontSize: 'var(--text-sm)',
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)',
              color: 'var(--text-primary)'
            }}
          />
        </td>

        {/* EOY Return % */}
        <td className="px-4 py-3 text-right font-semibold tabular-nums" style={{
          fontSize: 'var(--text-sm)',
          color: expectedReturnEOY !== null
            ? expectedReturnEOY >= 0 ? 'var(--color-success)' : 'var(--color-error)'
            : 'var(--text-tertiary)'
        }}>
          {formatPercentage(expectedReturnEOY)}
        </td>

        {/* Next Year Target (Editable) */}
        <td className="px-4 py-3">
          <Input
            type="number"
            step="0.01"
            value={userTargetNextYear}
            onChange={(e) => setUserTargetNextYear(e.target.value)}
            onBlur={handleSaveTargets}
            placeholder="—"
            disabled={isSaving}
            className="w-24 h-8 text-right tabular-nums transition-colors duration-300"
            style={{
              fontSize: 'var(--text-sm)',
              backgroundColor: 'var(--bg-primary)',
              borderColor: 'var(--border-primary)',
              color: 'var(--text-primary)'
            }}
          />
        </td>

        {/* Next Year Return % */}
        <td className="px-4 py-3 text-right font-semibold tabular-nums" style={{
          fontSize: 'var(--text-sm)',
          color: expectedReturnNextYear !== null
            ? expectedReturnNextYear >= 0 ? 'var(--color-success)' : 'var(--color-error)'
            : 'var(--text-tertiary)'
        }}>
          {formatPercentage(expectedReturnNextYear)}
        </td>

        {/* Analyst Target */}
        <td className="px-4 py-3 text-right tabular-nums transition-colors duration-300" style={{
          fontSize: 'var(--text-sm)',
          color: 'var(--text-secondary)'
        }}>
          {position.target_mean_price ? formatCurrency(position.target_mean_price) : '—'}
        </td>

        {/* Tags */}
        <td className="px-4 py-3" style={{ width: '220px', maxWidth: '220px' }}>
          <div className="flex gap-1 items-center overflow-hidden">
            {position.tags?.slice(0, 1).map(tag => (
              <div key={tag.id} className="inline-flex items-center gap-1 flex-shrink-0">
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
                      lineHeight: '12px',
                      minWidth: '12px',
                      height: '12px'
                    }}
                    title={`Remove ${tag.name} tag`}
                    aria-label={`Remove ${tag.name} tag from ${position.symbol}`}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            {position.tags && position.tags.length > 1 && (
              <span className="text-xs px-2 py-0.5 rounded transition-colors duration-300 flex-shrink-0" style={{
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-secondary)'
              }}>
                +{position.tags.length - 1}
              </span>
            )}
          </div>
        </td>
      </tr>

      {/* Expanded Detail Row */}
      {isExpanded && (
        <tr>
          <td colSpan={10} className="border-b transition-colors duration-300" style={{
            borderColor: 'var(--border-primary)',
            backgroundColor: 'var(--bg-secondary)'
          }}>
            <ExpandedRowDetail
              position={position}
              riskMetrics={riskMetrics}
              riskMetricsLoading={riskMetricsLoading}
              onRemoveTag={onRemoveTag}
            />
          </td>
        </tr>
      )}
    </>
  )
})

// Expanded row detail component
interface ExpandedRowDetailProps {
  position: EnhancedPosition
  riskMetrics: any
  riskMetricsLoading: boolean
  onRemoveTag?: (positionId: string, tagId: string) => Promise<void>
}

const ExpandedRowDetail = memo(function ExpandedRowDetail({ position, riskMetrics, riskMetricsLoading, onRemoveTag }: ExpandedRowDetailProps) {
  const quantity = position.quantity || 0
  const avgCost = position.avg_cost || position.cost_basis || 0
  const marketValue = position.current_market_value || position.market_value || (quantity * position.current_price)
  const pnl = position.unrealized_pnl || 0
  const pnlPercent = position.unrealized_pnl_percent || 0

  // Calculate P/E and P/S ratios
  const peThisYear = position.current_year_earnings_avg && position.current_price
    ? position.current_price / position.current_year_earnings_avg
    : null
  const peNextYear = position.next_year_earnings_avg && position.current_price
    ? position.current_price / position.next_year_earnings_avg
    : null
  const psThisYear = position.market_cap && position.current_year_revenue_avg
    ? position.market_cap / position.current_year_revenue_avg
    : null
  const psNextYear = position.market_cap && position.next_year_revenue_avg
    ? position.market_cap / position.next_year_revenue_avg
    : null

  const labelClass = "text-xs transition-colors duration-300"
  const valueClass = "text-sm font-medium transition-colors duration-300"
  const sectionTitleClass = "text-xs font-semibold uppercase tracking-wide mb-3 transition-colors duration-300"

  return (
    <div className="px-8 py-6 space-y-6">
      {/* Top Row: Position Detail, Current Year, Forward Year */}
      <div className="grid grid-cols-3 gap-8">
        {/* Left Column: Position Detail */}
        <div>
          <h4 className={sectionTitleClass} style={{ color: 'var(--text-secondary)' }}>
            Position Detail
          </h4>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Exposure</span>
              <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{formatCurrency(marketValue)}</span>
            </div>
            <div className="flex justify-between">
              <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Quantity</span>
              <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{quantity.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Avg Cost</span>
              <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{avgCost > 0 ? formatCurrency(avgCost) : '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>P&L</span>
              <span className={valueClass} style={{ color: pnl >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}>
                {formatCurrency(pnl)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>P&L %</span>
              <span className={valueClass} style={{ color: pnl >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}>
                {formatPercentage(pnlPercent)}
              </span>
            </div>
          </div>
        </div>

        {/* Middle Column: Current Year Metrics */}
        <div>
          <h4 className={sectionTitleClass} style={{ color: 'var(--text-secondary)' }}>
            Current Year
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
              <div className={labelClass} style={{ color: 'var(--text-secondary)' }}>P/E</div>
              <div className={valueClass} style={{ color: 'var(--text-primary)' }}>{peThisYear?.toFixed(1) || '—'}</div>
            </div>
            <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
              <div className={labelClass} style={{ color: 'var(--text-secondary)' }}>P/S</div>
              <div className={valueClass} style={{ color: 'var(--text-primary)' }}>{psThisYear?.toFixed(2) || '—'}</div>
            </div>
            <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
              <div className={labelClass} style={{ color: 'var(--text-secondary)' }}>EPS</div>
              <div className={valueClass} style={{ color: 'var(--text-primary)' }}>
                {position.current_year_earnings_avg ? formatCurrency(position.current_year_earnings_avg) : '—'}
              </div>
            </div>
            <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
              <div className={labelClass} style={{ color: 'var(--text-secondary)' }}>Revenue</div>
              <div className={valueClass} style={{ color: 'var(--text-primary)' }}>
                {position.current_year_revenue_avg ? `$${(position.current_year_revenue_avg / 1e9).toFixed(1)}B` : '—'}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Forward Year Metrics */}
        <div>
          <h4 className={sectionTitleClass} style={{ color: 'var(--text-secondary)' }}>
            Forward Year
          </h4>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
              <div className={labelClass} style={{ color: 'var(--text-secondary)' }}>Fwd P/E</div>
              <div className={valueClass} style={{ color: 'var(--text-primary)' }}>{peNextYear?.toFixed(1) || '—'}</div>
            </div>
            <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
              <div className={labelClass} style={{ color: 'var(--text-secondary)' }}>Fwd P/S</div>
              <div className={valueClass} style={{ color: 'var(--text-primary)' }}>{psNextYear?.toFixed(2) || '—'}</div>
            </div>
            <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
              <div className={labelClass} style={{ color: 'var(--text-secondary)' }}>Fwd EPS</div>
              <div className={valueClass} style={{ color: 'var(--text-primary)' }}>
                {position.next_year_earnings_avg ? formatCurrency(position.next_year_earnings_avg) : '—'}
              </div>
            </div>
            <div className="p-2 rounded transition-colors duration-300" style={{ backgroundColor: 'var(--bg-tertiary)' }}>
              <div className={labelClass} style={{ color: 'var(--text-secondary)' }}>Fwd Revenue</div>
              <div className={valueClass} style={{ color: 'var(--text-primary)' }}>
                {position.next_year_revenue_avg ? `$${(position.next_year_revenue_avg / 1e9).toFixed(1)}B` : '—'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Row: Correlations, Tags, Risk Metrics */}
      <div className="grid grid-cols-3 gap-8">
        {/* Left Column: Correlations */}
        <div>
          <h4 className={sectionTitleClass} style={{ color: 'var(--text-secondary)' }}>
            Correlations
          </h4>
          <CorrelationsSection position={position as any} theme="dark" />
        </div>

        {/* Middle Column: Tags */}
        <div>
          <h4 className={sectionTitleClass} style={{ color: 'var(--text-secondary)' }}>
            Tags
          </h4>
          {position.tags && position.tags.length > 0 ? (
            <div className="flex gap-2 flex-wrap">
              {position.tags.map(tag => (
                <div key={tag.id} className="inline-flex items-center gap-1">
                  <TagBadge tag={tag} draggable={false} />
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
                        lineHeight: '14px',
                        minWidth: '14px',
                        height: '14px'
                      }}
                      title={`Remove ${tag.name} tag`}
                      aria-label={`Remove ${tag.name} tag from ${position.symbol}`}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
              No tags applied
            </p>
          )}
        </div>

        {/* Right Column: Risk Metrics */}
        <div>
          <h4 className={sectionTitleClass} style={{ color: 'var(--text-secondary)' }}>
            Risk Metrics
          </h4>
          {riskMetricsLoading ? (
            <p className="text-sm transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
              Loading...
            </p>
          ) : riskMetrics ? (
            <div className="space-y-2">
              {/* Calculated Beta (from our factor model) */}
              {riskMetrics.beta !== undefined && (
                <div className="flex justify-between">
                  <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Calculated Beta</span>
                  <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{riskMetrics.beta.toFixed(2)}</span>
                </div>
              )}
              {/* 1-Year Beta (from company profile or other source) */}
              {position.beta !== undefined && (
                <div className="flex justify-between">
                  <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>1-Year Beta</span>
                  <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{position.beta.toFixed(2)}</span>
                </div>
              )}
              {riskMetrics.volatility_30d !== undefined && (
                <div className="flex justify-between">
                  <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Volatility (30d)</span>
                  <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{formatPercentage(riskMetrics.volatility_30d)}</span>
                </div>
              )}
              {(riskMetrics.sector || position.sector) && (
                <div className="flex justify-between">
                  <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Sector</span>
                  <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{riskMetrics.sector || position.sector}</span>
                </div>
              )}

              {/* Factor Exposures */}
              {riskMetrics.factor_exposures && (
                <>
                  <div className="mt-4 mb-2">
                    <span className="text-xs font-semibold uppercase tracking-wide transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
                      Factor Exposures
                    </span>
                  </div>
                  {riskMetrics.factor_exposures.Growth !== undefined && (
                    <div className="flex justify-between">
                      <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Growth</span>
                      <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{riskMetrics.factor_exposures.Growth.toFixed(2)}</span>
                    </div>
                  )}
                  {riskMetrics.factor_exposures.Momentum !== undefined && (
                    <div className="flex justify-between">
                      <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Momentum</span>
                      <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{riskMetrics.factor_exposures.Momentum.toFixed(2)}</span>
                    </div>
                  )}
                  {riskMetrics.factor_exposures.Size !== undefined && (
                    <div className="flex justify-between">
                      <span className={labelClass} style={{ color: 'var(--text-secondary)' }}>Size</span>
                      <span className={valueClass} style={{ color: 'var(--text-primary)' }}>{riskMetrics.factor_exposures.Size.toFixed(2)}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          ) : (
            <p className="text-sm transition-colors duration-300" style={{ color: 'var(--text-tertiary)' }}>
              Not available
            </p>
          )}
        </div>
      </div>
    </div>
  )
})
