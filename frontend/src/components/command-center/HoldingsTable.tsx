'use client'

import React, { useState } from 'react'

interface HoldingRow {
  id: string
  symbol: string
  quantity: number
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

interface HoldingsTableProps {
  holdings: HoldingRow[]
  loading: boolean
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

export function HoldingsTable({ holdings, loading }: HoldingsTableProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn>('weight')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['longs', 'shorts', 'options', 'privates'])
  )

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

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const getSortedHoldings = (holdingsToSort: HoldingRow[]) => {
    const sorted = [...holdingsToSort].sort((a, b) => {
      let aValue: number | string = 0
      let bValue: number | string = 0

      switch (sortColumn) {
        case 'symbol':
          aValue = a.symbol
          bValue = b.symbol
          break
        case 'quantity':
          aValue = a.quantity
          bValue = b.quantity
          break
        case 'todaysPrice':
          aValue = a.todaysPrice
          bValue = b.todaysPrice
          break
        case 'targetPrice':
          aValue = a.targetPrice || 0
          bValue = b.targetPrice || 0
          break
        case 'marketValue':
          aValue = Math.abs(a.marketValue)
          bValue = Math.abs(b.marketValue)
          break
        case 'weight':
          aValue = Math.abs(a.weight)
          bValue = Math.abs(b.weight)
          break
        case 'pnlToday':
          aValue = a.pnlToday || 0
          bValue = b.pnlToday || 0
          break
        case 'pnlTotal':
          aValue = a.pnlTotal
          bValue = b.pnlTotal
          break
        case 'returnPct':
          aValue = a.returnPct
          bValue = b.returnPct
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

  // Categorize holdings
  const categorizeHoldings = () => {
    const longs = holdings.filter(
      (h) => h.investmentClass === 'PUBLIC' && h.positionType === 'LONG'
    )
    const shorts = holdings.filter(
      (h) => h.investmentClass === 'PUBLIC' && h.positionType === 'SHORT'
    )
    const options = holdings.filter((h) => h.investmentClass === 'OPTIONS')
    const privates = holdings.filter((h) => h.investmentClass === 'PRIVATE')

    return { longs, shorts, options, privates }
  }

  const SortableHeader = ({ column, children, align = 'left' }: { column: SortColumn; children: React.ReactNode; align?: 'left' | 'right' }) => (
    <th
      className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider cursor-pointer hover:bg-opacity-80 transition-colors text-tertiary ${
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
                color: 'var(--text-primary)'
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
                color: 'var(--text-primary)'
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
    categoryHoldings: HoldingRow[],
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
                  <SortableHeader column="symbol">Position</SortableHeader>
                  <SortableHeader column="quantity" align="right">Quantity</SortableHeader>
                  <SortableHeader column="todaysPrice" align="right">Today's Price</SortableHeader>
                  <SortableHeader column="targetPrice" align="right">Target Price</SortableHeader>
                  <SortableHeader column="marketValue" align="right">Market Value</SortableHeader>
                  <SortableHeader column="weight" align="right">Weight</SortableHeader>
                  <SortableHeader column="pnlToday" align="right">P&L Today</SortableHeader>
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
                  <tr
                    key={holding.id}
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
                    {/* Position */}
                    <td className="px-2 py-2 font-semibold transition-colors duration-300" style={{
                      color: 'var(--color-accent)'
                    }}>
                      <div className="flex items-center gap-2">
                        <span>{holding.symbol}</span>
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
                      {holding.quantity.toLocaleString()}
                    </td>

                    {/* Today's Price */}
                    <td className="px-2 py-2 text-right font-medium tabular-nums text-primary">
                      ${holding.todaysPrice.toFixed(2)}
                    </td>

                    {/* Target Price */}
                    <td className="px-2 py-2 text-right font-medium tabular-nums text-primary">
                      {holding.targetPrice ? `$${holding.targetPrice.toFixed(2)}` : '—'}
                    </td>

                    {/* Market Value */}
                    <td className="px-2 py-2 text-right tabular-nums font-semibold transition-colors duration-300" style={{
                      color: 'var(--text-primary)'
                    }}>
                      {formatCurrency(holding.marketValue)}
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
                              width: `${Math.min(Math.abs(holding.weight), 100)}%`,
                              backgroundColor: 'var(--color-accent)'
                            }}
                          ></div>
                        </div>
                        <span className="font-medium tabular-nums text-primary">
                          {holding.weight.toFixed(1)}%
                        </span>
                      </div>
                    </td>

                    {/* P&L Today */}
                    <td className="px-2 py-2 text-right font-medium tabular-nums text-tertiary">
                      {holding.pnlToday !== null ? formatCurrency(holding.pnlToday) : '—'}
                    </td>

                    {/* P&L Total */}
                    <td className="px-2 py-2 text-right font-medium tabular-nums transition-colors duration-300" style={{
                      color: holding.pnlTotal >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                    }}>
                      {formatCurrency(holding.pnlTotal)}
                    </td>

                    {/* Return % */}
                    <td className="px-2 py-2 text-right tabular-nums font-semibold transition-colors duration-300" style={{
                      color: holding.returnPct >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                    }}>
                      {formatPercentage(holding.returnPct)}
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
        <h2 className="text-sm font-semibold uppercase tracking-wider mb-2 text-secondary">
          Holdings ({holdings.length})
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
