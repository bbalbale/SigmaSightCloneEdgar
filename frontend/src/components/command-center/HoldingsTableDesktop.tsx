'use client'

import React, { useState } from 'react'
import positionManagementService from '@/services/positionManagementService'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface HoldingRow {
  id: string
  symbol: string
  quantity: number
  entryPrice: number
  todaysPrice: number
  targetPrice: number | null
  marketValue: number
  weight: number
  pnlToday: number | null
  pnlTotal: number
  returnPct: number
  targetReturn: number | null
  beta: number | null
  positionType: string
  investmentClass: string
}

interface AggregatedHolding {
  symbol: string
  lots: HoldingRow[]
  totalQuantity: number
  avgPrice: number
  totalMarketValue: number
  totalWeight: number
  totalPnL: number
  avgReturnPct: number
  positionType: string
  investmentClass: string
  targetPrice: number | null
  targetReturn: number | null
  beta: number | null
}

interface HoldingsTableProps {
  holdings: HoldingRow[]
  loading: boolean
  onRefresh?: () => void
}

type SortColumn = 'symbol' | 'quantity' | 'todaysPrice' | 'targetPrice' | 'marketValue' | 'weight' | 'pnlToday' | 'pnlTotal' | 'returnPct' | 'targetReturn' | 'beta'
type SortDirection = 'asc' | 'desc'

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
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}

export function HoldingsTableDesktop({ holdings, loading, onRefresh }: HoldingsTableProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn>('weight')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['longs', 'shorts', 'options', 'privates'])
  )
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [editingLot, setEditingLot] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<{ quantity: string; avg_cost: string; notes: string }>({
    quantity: '',
    avg_cost: '',
    notes: ''
  })

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  const toggleRow = (symbol: string) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(symbol)) {
        next.delete(symbol)
      } else {
        next.add(symbol)
      }
      return next
    })
  }

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const getSortedHoldings = (holdingsToSort: AggregatedHolding[]) => {
    const sorted = [...holdingsToSort].sort((a, b) => {
      let aValue: number | string = 0
      let bValue: number | string = 0

      switch (sortColumn) {
        case 'symbol':
          aValue = a.symbol
          bValue = b.symbol
          break
        case 'quantity':
          aValue = a.totalQuantity
          bValue = b.totalQuantity
          break
        case 'todaysPrice':
          aValue = a.avgPrice
          bValue = b.avgPrice
          break
        case 'targetPrice':
          aValue = a.targetPrice || 0
          bValue = b.targetPrice || 0
          break
        case 'marketValue':
          aValue = Math.abs(a.totalMarketValue)
          bValue = Math.abs(b.totalMarketValue)
          break
        case 'weight':
          aValue = Math.abs(a.totalWeight)
          bValue = Math.abs(b.totalWeight)
          break
        case 'pnlTotal':
          aValue = a.totalPnL
          bValue = b.totalPnL
          break
        case 'returnPct':
          aValue = a.avgReturnPct
          bValue = b.avgReturnPct
          break
        case 'targetReturn':
          aValue = a.targetReturn || 0
          bValue = b.targetReturn || 0
          break
        case 'beta':
          aValue = a.beta || 0
          bValue = b.beta || 0
          break
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue)
      }

      return sortDirection === 'asc'
        ? (aValue as number) - (bValue as number)
        : (bValue as number) - (aValue as number)
    })

    return sorted
  }

  // Aggregate holdings by symbol
  const aggregateHoldings = (positions: HoldingRow[]): AggregatedHolding[] => {
    const symbolMap = new Map<string, HoldingRow[]>()

    // Group by symbol
    positions.forEach(position => {
      const key = position.symbol
      if (!symbolMap.has(key)) {
        symbolMap.set(key, [])
      }
      symbolMap.get(key)!.push(position)
    })

    // Aggregate each symbol
    return Array.from(symbolMap.entries()).map(([symbol, lots]) => {
      const totalQuantity = lots.reduce((sum, lot) => sum + lot.quantity, 0)
      const totalMarketValue = lots.reduce((sum, lot) => sum + lot.marketValue, 0)
      const totalWeight = lots.reduce((sum, lot) => sum + lot.weight, 0)
      const totalPnL = lots.reduce((sum, lot) => sum + lot.pnlTotal, 0)
      const avgPrice = lots.reduce((sum, lot) => sum + lot.todaysPrice, 0) / lots.length
      const avgReturnPct = lots.reduce((sum, lot) => sum + lot.returnPct, 0) / lots.length

      return {
        symbol,
        lots,
        totalQuantity,
        avgPrice,
        totalMarketValue,
        totalWeight,
        totalPnL,
        avgReturnPct,
        positionType: lots[0].positionType,
        investmentClass: lots[0].investmentClass,
        targetPrice: lots[0].targetPrice,
        targetReturn: lots[0].targetReturn,
        beta: lots[0].beta
      }
    })
  }

  // Categorize aggregated holdings
  const categorizeHoldings = () => {
    const aggregated = aggregateHoldings(holdings)

    const longs = aggregated.filter(
      (h) => h.investmentClass === 'PUBLIC' && h.positionType === 'LONG'
    )
    const shorts = aggregated.filter(
      (h) => h.investmentClass === 'PUBLIC' && h.positionType === 'SHORT'
    )
    const options = aggregated.filter((h) => h.investmentClass === 'OPTIONS')
    const privates = aggregated.filter((h) => h.investmentClass === 'PRIVATE')

    return { longs, shorts, options, privates }
  }

  const handleEditLot = (lot: HoldingRow) => {
    setEditingLot(lot.id)
    setEditForm({
      quantity: lot.quantity.toString(),
      avg_cost: lot.entryPrice.toFixed(2),
      notes: ''
    })
  }

  const handleCancelEdit = () => {
    setEditingLot(null)
    setEditForm({ quantity: '', avg_cost: '', notes: '' })
  }

  const handleSaveEdit = async (lotId: string) => {
    try {
      await positionManagementService.updatePosition(lotId, {
        quantity: parseFloat(editForm.quantity),
        avg_cost: parseFloat(editForm.avg_cost),
        notes: editForm.notes || undefined
      })

      // Reset edit state
      handleCancelEdit()

      // Trigger refresh via callback
      onRefresh?.()
    } catch (error) {
      console.error('Failed to update position:', error)
      alert('Failed to update position')
    }
  }

  const handleSellLot = async (lot: HoldingRow) => {
    const salePrice = prompt(`Enter sale price for ${lot.symbol}:`, lot.todaysPrice.toString())
    if (!salePrice) return

    try {
      await positionManagementService.closePosition(
        lot.id,
        parseFloat(salePrice),
        new Date().toISOString().split('T')[0]
      )

      // Trigger refresh via callback
      onRefresh?.()
    } catch (error) {
      console.error('Failed to sell position:', error)
      alert('Failed to sell position')
    }
  }

  const SortableHeader = ({ column, children, align = 'left' }: { column: SortColumn; children: React.ReactNode; align?: 'left' | 'right' }) => (
    <th
      className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider cursor-pointer hover:bg-opacity-80 transition-colors text-secondary ${
        align === 'right' ? 'text-right' : 'text-left'
      }`}
      onClick={() => handleSort(column)}
    >
      <div className={`flex items-center gap-0.5 ${align === 'right' ? 'justify-end' : 'justify-start'}`}>
        <span>{children}</span>
        {sortColumn === column && (
          <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {sortDirection === 'asc' ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            )}
          </svg>
        )}
      </div>
    </th>
  )

  if (loading) {
    return (
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <div className="overflow-hidden transition-colors duration-300 themed-card">
            <div className="px-4 py-3 transition-colors duration-300" style={{
              borderBottom: '1px solid var(--border-primary)'
            }}>
              <h2 className="text-lg font-semibold transition-colors duration-300" style={{
                color: 'var(--color-accent)'
              }}>
                Holdings
              </h2>
            </div>
            <div className="p-8 text-center">
              <p className="text-secondary">
                Loading holdings...
              </p>
            </div>
          </div>
        </div>
      </section>
    )
  }

  if (holdings.length === 0) {
    return (
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <div className="overflow-hidden transition-colors duration-300 themed-card">
            <div className="px-4 py-3 transition-colors duration-300" style={{
              borderBottom: '1px solid var(--border-primary)'
            }}>
              <h2 className="text-lg font-semibold transition-colors duration-300" style={{
                color: 'var(--color-accent)'
              }}>
                Holdings
              </h2>
            </div>
            <div className="p-8 text-center">
              <p className="text-secondary">
                No positions found
              </p>
            </div>
          </div>
        </div>
      </section>
    )
  }

  const categories = categorizeHoldings()

  // Helper to render a category section
  const renderCategorySection = (
    title: string,
    categoryKey: string,
    categoryHoldings: AggregatedHolding[],
    showShortBadge: boolean = false
  ) => {
    if (categoryHoldings.length === 0) return null

    const isExpanded = expandedSections.has(categoryKey)
    const sortedCategoryHoldings = getSortedHoldings(categoryHoldings)

    return (
      <div
        key={categoryKey}
        className="overflow-hidden transition-colors duration-300"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderRadius: 'var(--border-radius)',
          border: '1px solid var(--border-primary)'
        }}
      >
        {/* Category Header */}
        <div
          className="px-3 py-2 flex items-center justify-between cursor-pointer transition-colors hover:bg-opacity-80"
          onClick={() => toggleSection(categoryKey)}
          style={{
            borderBottom: '1px solid var(--border-primary)',
            backgroundColor: 'var(--bg-tertiary)'
          }}
        >
          <h3 className="text-xs font-semibold uppercase tracking-wider text-secondary">
            {title} <span className="font-mono">({categoryHoldings.length})</span>
          </h3>
          <svg
            className={`w-4 h-4 transition-transform ${
              isExpanded ? 'rotate-180' : ''
            } text-tertiary`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        {/* Category Table */}
        {isExpanded && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              {/* Header Row */}
              <thead className="sticky top-0 transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-tertiary)'
              }}>
                <tr>
                  <th className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-secondary text-left w-8"></th>
                  <SortableHeader column="symbol">Position</SortableHeader>
                  <SortableHeader column="quantity" align="right">Quantity</SortableHeader>
                  <SortableHeader column="todaysPrice" align="right">Today's Price</SortableHeader>
                  <SortableHeader column="targetPrice" align="right">Target Price</SortableHeader>
                  <SortableHeader column="marketValue" align="right">Market Value</SortableHeader>
                  <SortableHeader column="weight" align="right">Weight</SortableHeader>
                  <SortableHeader column="pnlTotal" align="right">P&L Total</SortableHeader>
                  <SortableHeader column="returnPct" align="right">Return %</SortableHeader>
                  <SortableHeader column="targetReturn" align="right">Target Return</SortableHeader>
                  <SortableHeader column="beta" align="right">Beta</SortableHeader>
                </tr>
              </thead>

              {/* Body Rows */}
              <tbody className="divide-y transition-colors duration-300" style={{
                borderColor: 'var(--border-primary)'
              }}>
                {sortedCategoryHoldings.map((holding) => (
                  <React.Fragment key={holding.symbol}>
                    {/* Main aggregated row */}
                    <tr
                      className="transition-colors cursor-pointer hover:bg-opacity-50"
                      style={{
                        backgroundColor: 'transparent'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--bg-tertiary)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }}
                    >
                      {/* Expand/collapse caret */}
                      <td className="px-2 py-2">
                        <button
                          onClick={() => toggleRow(holding.symbol)}
                          className="text-secondary hover:text-primary transition-colors"
                        >
                          <svg
                            className={`w-3 h-3 transition-transform ${
                              expandedRows.has(holding.symbol) ? 'rotate-90' : ''
                            }`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                      </td>

                      {/* Position */}
                      <td className="px-2 py-2 font-semibold transition-colors duration-300" style={{
                        color: 'var(--color-accent)'
                      }}>
                        <div className="flex items-center gap-2">
                          <span>{holding.symbol}</span>
                          {holding.lots.length > 1 && (
                            <span className="text-xs px-1.5 py-0.5 rounded transition-colors duration-300" style={{
                              backgroundColor: 'rgba(59, 130, 246, 0.2)',
                              color: 'var(--color-accent)'
                            }}>
                              {holding.lots.length} lots
                            </span>
                          )}
                          {showShortBadge && (
                            <span className="text-xs px-1.5 py-0.5 rounded transition-colors duration-300" style={{
                              backgroundColor: 'rgba(239, 68, 68, 0.2)',
                              color: 'var(--color-error)'
                            }}>
                              SHORT
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Quantity */}
                      <td className="px-2 py-2 text-right font-medium tabular-nums text-primary">
                        {holding.totalQuantity.toLocaleString()}
                      </td>

                      {/* Today's Price */}
                      <td className="px-2 py-2 text-right font-medium tabular-nums text-primary">
                        ${holding.avgPrice.toFixed(2)}
                      </td>

                      {/* Target Price */}
                      <td className="px-2 py-2 text-right font-medium tabular-nums text-primary">
                        {holding.targetPrice ? `$${holding.targetPrice.toFixed(2)}` : '—'}
                      </td>

                      {/* Market Value */}
                      <td className="px-2 py-2 text-right tabular-nums font-semibold transition-colors duration-300" style={{
                        color: 'var(--text-primary)'
                      }}>
                        {formatCurrency(holding.totalMarketValue)}
                      </td>

                      {/* Weight - with visual bar */}
                      <td className="px-2 py-2 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <div className="w-12 h-1 rounded-full overflow-hidden transition-colors duration-300" style={{
                            backgroundColor: 'var(--bg-tertiary)'
                          }}>
                            <div
                              className="h-full transition-colors duration-300"
                              style={{
                                width: `${Math.min(Math.abs(holding.totalWeight), 100)}%`,
                                backgroundColor: 'var(--color-accent)'
                              }}
                            ></div>
                          </div>
                          <span className="font-medium tabular-nums text-primary">
                            {holding.totalWeight.toFixed(1)}%
                          </span>
                        </div>
                      </td>

                      {/* P&L Total */}
                      <td className="px-2 py-2 text-right font-medium tabular-nums transition-colors duration-300" style={{
                        color: holding.totalPnL >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                      }}>
                        {formatCurrency(holding.totalPnL)}
                      </td>

                      {/* Return % */}
                      <td className="px-2 py-2 text-right tabular-nums font-semibold transition-colors duration-300" style={{
                        color: holding.avgReturnPct >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                      }}>
                        {formatPercentage(holding.avgReturnPct)}
                      </td>

                      {/* Target Return */}
                      <td className="px-2 py-2 text-right tabular-nums font-semibold text-primary">
                        {holding.targetReturn !== null ? formatPercentage(holding.targetReturn) : '—'}
                      </td>

                      {/* Beta */}
                      <td className="px-2 py-2 text-right font-medium tabular-nums text-primary">
                        {holding.beta !== null ? holding.beta.toFixed(2) : '—'}
                      </td>
                    </tr>

                    {/* Expanded row showing individual lots */}
                    {expandedRows.has(holding.symbol) && (
                      <tr>
                        <td colSpan={11} className="px-4 py-3" style={{
                          backgroundColor: 'var(--bg-tertiary)'
                        }}>
                          <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-2">
                              Individual Lots ({holding.lots.length})
                            </h4>
                            {holding.lots.map((lot) => (
                              <div
                                key={lot.id}
                                className="p-3 rounded transition-colors duration-300"
                                style={{
                                  backgroundColor: 'var(--bg-secondary)',
                                  border: '1px solid var(--border-primary)'
                                }}
                              >
                                {editingLot === lot.id ? (
                                  <div className="space-y-3">
                                    <div className="grid grid-cols-3 gap-3">
                                      <div>
                                        <label className="text-xs text-secondary mb-1 block">Quantity</label>
                                        <Input
                                          type="number"
                                          value={editForm.quantity}
                                          onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })}
                                          className="text-xs"
                                        />
                                      </div>
                                      <div>
                                        <label className="text-xs text-secondary mb-1 block">Avg Cost</label>
                                        <Input
                                          type="number"
                                          value={editForm.avg_cost}
                                          onChange={(e) => setEditForm({ ...editForm, avg_cost: e.target.value })}
                                          className="text-xs"
                                        />
                                      </div>
                                      <div>
                                        <label className="text-xs text-secondary mb-1 block">Notes</label>
                                        <Input
                                          type="text"
                                          value={editForm.notes}
                                          onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                                          className="text-xs"
                                          placeholder="Optional"
                                        />
                                      </div>
                                    </div>
                                    <div className="flex gap-2">
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={handleCancelEdit}
                                      >
                                        Cancel
                                      </Button>
                                      <Button
                                        size="sm"
                                        onClick={() => handleSaveEdit(lot.id)}
                                      >
                                        Save Changes
                                      </Button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-6 text-xs">
                                      <div>
                                        <span className="text-secondary">Qty:</span>{' '}
                                        <span className="font-medium text-primary">{lot.quantity.toLocaleString()}</span>
                                      </div>
                                      <div>
                                        <span className="text-secondary">Avg Cost:</span>{' '}
                                        <span className="font-medium text-primary">
                                          ${lot.entryPrice.toFixed(2)}
                                        </span>
                                      </div>
                                      <div>
                                        <span className="text-secondary">Market Value:</span>{' '}
                                        <span className="font-medium text-primary">{formatCurrency(lot.marketValue)}</span>
                                      </div>
                                      <div>
                                        <span className="text-secondary">P&L:</span>{' '}
                                        <span
                                          className="font-medium"
                                          style={{
                                            color: lot.pnlTotal >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                                          }}
                                        >
                                          {formatCurrency(lot.pnlTotal)} ({formatPercentage(lot.returnPct)})
                                        </span>
                                      </div>
                                    </div>
                                    <div className="flex gap-2">
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleEditLot(lot)}
                                      >
                                        Edit
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={() => handleSellLot(lot)}
                                      >
                                        Sell
                                      </Button>
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        {/* Main Header */}
        <h2
          className="text-lg font-semibold mb-3 transition-colors duration-300"
          style={{ color: 'var(--color-accent)' }}
        >
          Holdings ({Object.values(categorizeHoldings()).reduce((sum, cat) => sum + cat.length, 0)} positions)
        </h2>

        {/* Category Sections */}
        <div className="space-y-2">
          {renderCategorySection('Long Positions', 'longs', categories.longs, false)}
          {renderCategorySection('Short Positions', 'shorts', categories.shorts, true)}
          {renderCategorySection('Options', 'options', categories.options, false)}
          {renderCategorySection('Private Positions', 'privates', categories.privates, false)}
        </div>
      </div>
    </section>
  )
}
