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

interface HoldingsTableMobileProps {
  holdings: HoldingRow[]
  loading: boolean
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

function HoldingCard({ holding }: { holding: HoldingRow }) {
  const isProfitable = holding.pnlTotal >= 0
  const isShort = holding.positionType === 'SHORT'

  return (
    <div
      className="rounded-lg p-3 transition-all duration-200 border"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)'
      }}
    >
      {/* Header row: Symbol + Type + Weight */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-bold text-base" style={{ color: 'var(--color-accent)' }}>
            {holding.symbol}
          </span>
          {isShort && (
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                color: 'var(--color-error)'
              }}
            >
              SHORT
            </span>
          )}
          {holding.investmentClass === 'OPTIONS' && (
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                color: 'var(--color-info)'
              }}
            >
              OPTION
            </span>
          )}
          {holding.investmentClass === 'PRIVATE' && (
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: 'rgba(168, 85, 247, 0.2)',
                color: '#a855f7'
              }}
            >
              PRIVATE
            </span>
          )}
        </div>
        {/* Weight badge */}
        <span
          className="text-xs font-semibold px-2 py-0.5 rounded"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            color: 'var(--text-secondary)'
          }}
        >
          {holding.weight.toFixed(1)}%
        </span>
      </div>

      {/* Value row */}
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Market Value
        </span>
        <span
          className="text-lg font-bold tabular-nums"
          style={{ color: 'var(--text-primary)' }}
        >
          {formatCurrency(holding.marketValue)}
        </span>
      </div>

      {/* P&L row */}
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Total P&L
        </span>
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-medium tabular-nums"
            style={{
              color: isProfitable ? 'var(--color-success)' : 'var(--color-error)'
            }}
          >
            {formatCurrency(holding.pnlTotal)}
          </span>
          <span
            className="text-sm font-bold tabular-nums"
            style={{
              color: isProfitable ? 'var(--color-success)' : 'var(--color-error)'
            }}
          >
            ({isProfitable ? '+' : ''}
            {holding.returnPct.toFixed(1)}%)
          </span>
        </div>
      </div>

      {/* Additional info row */}
      <div className="flex items-center justify-between pt-2 border-t" style={{ borderColor: 'var(--border-primary)' }}>
        <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
          <span>{holding.quantity.toLocaleString()} @ ${holding.todaysPrice.toFixed(2)}</span>
        </div>
        {holding.beta !== null && (
          <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            <span>β {holding.beta.toFixed(2)}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export function HoldingsTableMobile({ holdings, loading }: HoldingsTableMobileProps) {
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

  // Render category section
  const renderCategorySection = (
    title: string,
    categoryKey: string,
    categoryHoldings: HoldingRow[]
  ) => {
    if (categoryHoldings.length === 0) return null

    const isExpanded = expandedSections.has(categoryKey)

    return (
      <div key={categoryKey} className="mb-4">
        {/* Category Header */}
        <button
          className="w-full flex items-center justify-between px-3 py-2 rounded-t-lg transition-colors"
          onClick={() => toggleSection(categoryKey)}
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            border: '1px solid var(--border-primary)'
          }}
        >
          <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
            {title} <span className="font-mono">({categoryHoldings.length})</span>
          </h3>
          <svg
            className={`w-4 h-4 transition-transform ${
              isExpanded ? 'rotate-180' : ''
            }`}
            style={{ color: 'var(--text-tertiary)' }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Category Cards */}
        {isExpanded && (
          <div className="space-y-2 mt-2">
            {categoryHoldings.map((holding) => (
              <HoldingCard key={holding.id} holding={holding} />
            ))}
          </div>
        )}
      </div>
    )
  }

  if (loading) {
    return (
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--color-accent)' }}>
            Holdings
          </h2>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="animate-pulse rounded-lg p-4 h-32"
                style={{ backgroundColor: 'var(--bg-secondary)' }}
              />
            ))}
          </div>
        </div>
      </section>
    )
  }

  if (holdings.length === 0) {
    return (
      <section className="px-4 pb-8">
        <div className="container mx-auto">
          <h2 className="text-sm font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--color-accent)' }}>
            Holdings
          </h2>
          <div
            className="rounded-lg p-8 text-center"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-primary)'
            }}
          >
            <p style={{ color: 'var(--text-secondary)' }}>
              No positions found
            </p>
          </div>
        </div>
      </section>
    )
  }

  const categories = categorizeHoldings()

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        {/* Main Header */}
        <h2 className="text-sm font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--text-secondary)' }}>
          Holdings ({holdings.length})
        </h2>

        {/* Category Sections */}
        <div>
          {renderCategorySection('Long Positions', 'longs', categories.longs)}
          {renderCategorySection('Short Positions', 'shorts', categories.shorts)}
          {renderCategorySection('Options', 'options', categories.options)}
          {renderCategorySection('Private Positions', 'privates', categories.privates)}
        </div>
      </div>
    </section>
  )
}
