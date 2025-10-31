'use client'

import React, { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'

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
  const { theme } = useTheme()
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
      className={`px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider cursor-pointer hover:bg-opacity-80 transition-colors ${
        align === 'right' ? 'text-right' : 'text-left'
      } ${theme === 'dark' ? 'text-slate-500 hover:bg-slate-700/30' : 'text-slate-500 hover:bg-slate-200/50'}`}
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
          <div className={`rounded-lg border overflow-hidden transition-colors duration-300 ${
            theme === 'dark'
              ? 'bg-slate-900 border-slate-700'
              : 'bg-white border-slate-200'
          }`}>
            <div className={`px-4 py-3 border-b ${
              theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
            }`}>
              <h2 className={`text-lg font-semibold ${
                theme === 'dark' ? 'text-slate-50' : 'text-slate-900'
              }`}>
                Holdings
              </h2>
            </div>
            <div className="p-8 text-center">
              <p className={theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}>
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
          <div className={`rounded-lg border overflow-hidden transition-colors duration-300 ${
            theme === 'dark'
              ? 'bg-slate-900 border-slate-700'
              : 'bg-white border-slate-200'
          }`}>
            <div className={`px-4 py-3 border-b ${
              theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
            }`}>
              <h2 className={`text-lg font-semibold ${
                theme === 'dark' ? 'text-slate-50' : 'text-slate-900'
              }`}>
                Holdings
              </h2>
            </div>
            <div className="p-8 text-center">
              <p className={theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}>
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
        className={`border overflow-hidden ${
          theme === 'dark' ? 'bg-slate-900/30 border-slate-700/50' : 'bg-white border-slate-300'
        }`}
      >
        {/* Category Header */}
        <div
          className={`px-3 py-2 border-b flex items-center justify-between cursor-pointer transition-colors hover:bg-opacity-50 ${
            theme === 'dark' ? 'border-slate-700/50 bg-slate-900/50 hover:bg-slate-800/50' : 'border-slate-300 bg-slate-50 hover:bg-slate-100'
          }`}
          onClick={() => toggleSection(categoryKey)}
        >
          <h3 className={`text-xs font-semibold uppercase tracking-wider ${
            theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
          }`}>
            {title} <span className="font-mono">({categoryHoldings.length})</span>
          </h3>
          <svg
            className={`w-4 h-4 transition-transform ${
              isExpanded ? 'rotate-180' : ''
            } ${theme === 'dark' ? 'text-slate-500' : 'text-slate-500'}`}
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
              <thead className={`sticky top-0 ${theme === 'dark' ? 'bg-slate-900/90' : 'bg-slate-100'}`}>
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
              <tbody className={`${
                theme === 'dark' ? 'divide-y divide-slate-700' : 'divide-y divide-slate-200'
              }`}>
                {sortedCategoryHoldings.map((holding) => (
                  <tr
                    key={holding.id}
                    className={`transition-colors cursor-pointer ${
                      theme === 'dark' ? 'hover:bg-slate-800' : 'hover:bg-slate-50'
                    }`}
                  >
                    {/* Position */}
                    <td className={`px-2 py-2 font-semibold ${
                      theme === 'dark' ? 'text-orange-400' : 'text-slate-900'
                    }`}>
                      <div className="flex items-center gap-2">
                        <span>{holding.symbol}</span>
                        {showShortBadge && (
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            theme === 'dark'
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-red-100 text-red-700'
                          }`}>
                            SHORT
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Quantity */}
                    <td className={`px-2 py-2 text-right font-medium tabular-nums ${
                      theme === 'dark' ? 'text-slate-300' : 'text-slate-700'
                    }`}>
                      {holding.quantity.toLocaleString()}
                    </td>

                    {/* Today's Price */}
                    <td className={`px-2 py-2 text-right font-medium tabular-nums ${
                      theme === 'dark' ? 'text-slate-300' : 'text-slate-700'
                    }`}>
                      ${holding.todaysPrice.toFixed(2)}
                    </td>

                    {/* Target Price */}
                    <td className={`px-2 py-2 text-right font-medium tabular-nums ${
                      theme === 'dark' ? 'text-slate-300' : 'text-slate-700'
                    }`}>
                      {holding.targetPrice ? `$${holding.targetPrice.toFixed(2)}` : '—'}
                    </td>

                    {/* Market Value */}
                    <td className={`px-2 py-2 text-right tabular-nums font-semibold ${
                      theme === 'dark' ? 'text-slate-50' : 'text-slate-900'
                    }`}>
                      {formatCurrency(holding.marketValue)}
                    </td>

                    {/* Weight - with visual bar */}
                    <td className="px-2 py-2 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <div className={`w-12 h-1 rounded-full overflow-hidden ${
                          theme === 'dark' ? 'bg-slate-700/50' : 'bg-slate-200'
                        }`}>
                          <div
                            className={`h-full ${theme === 'dark' ? 'bg-blue-500/80' : 'bg-blue-500'}`}
                            style={{ width: `${Math.min(Math.abs(holding.weight), 100)}%` }}
                          ></div>
                        </div>
                        <span className={`font-medium tabular-nums ${
                          theme === 'dark' ? 'text-slate-300' : 'text-slate-700'
                        }`}>
                          {holding.weight.toFixed(1)}%
                        </span>
                      </div>
                    </td>

                    {/* P&L Today */}
                    <td className={`px-2 py-2 text-right font-medium tabular-nums ${
                      holding.pnlToday !== null
                        ? holding.pnlToday >= 0
                          ? theme === 'dark' ? 'text-emerald-400' : 'text-emerald-600'
                          : theme === 'dark' ? 'text-red-400' : 'text-red-600'
                        : theme === 'dark' ? 'text-slate-500' : 'text-slate-500'
                    }`}>
                      {holding.pnlToday !== null ? formatCurrency(holding.pnlToday) : '—'}
                    </td>

                    {/* P&L Total */}
                    <td className={`px-2 py-2 text-right font-medium tabular-nums ${
                      holding.pnlTotal >= 0
                        ? theme === 'dark' ? 'text-emerald-400' : 'text-emerald-600'
                        : theme === 'dark' ? 'text-red-400' : 'text-red-600'
                    }`}>
                      {formatCurrency(holding.pnlTotal)}
                    </td>

                    {/* Return % */}
                    <td className={`px-2 py-2 text-right tabular-nums font-semibold ${
                      holding.returnPct >= 0
                        ? theme === 'dark' ? 'text-emerald-400' : 'text-emerald-600'
                        : theme === 'dark' ? 'text-red-400' : 'text-red-600'
                    }`}>
                      {formatPercentage(holding.returnPct)}
                    </td>

                    {/* Target Return */}
                    <td className={`px-2 py-2 text-right tabular-nums font-semibold ${
                      theme === 'dark' ? 'text-slate-300' : 'text-slate-700'
                    }`}>
                      {holding.targetReturn !== null ? formatPercentage(holding.targetReturn) : '—'}
                    </td>

                    {/* Beta */}
                    <td className={`px-2 py-2 text-right font-medium tabular-nums ${
                      theme === 'dark' ? 'text-slate-300' : 'text-slate-700'
                    }`}>
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
        <h2 className={`text-sm font-semibold uppercase tracking-wider mb-2 ${
          theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
        }`}>
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
