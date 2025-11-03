'use client'

import React from 'react'
import { FinancialYearData } from '@/hooks/useFundamentals'
import { formatCurrency, formatEPS, formatPercent, formatGrowth, getGrowthColor } from '@/lib/financialFormatters'

interface MetricSectionProps {
  title: string
  years: FinancialYearData[]
  getValue: (year: FinancialYearData) => number | null
  getMargin: (year: FinancialYearData) => number | null
  getGrowth: (year: FinancialYearData) => number | null
  showMargin: boolean
  isEPS?: boolean
}

/**
 * MetricSection Component
 *
 * Displays a single metric section with 2-3 rows:
 * 1. Metric value row (currency or EPS formatted)
 * 2. Margin row (optional - only for metrics with margins)
 * 3. YoY growth row (with color coding)
 *
 * Example:
 * ┌─────────────────────────────────────────────────────────────┐
 * │ Revenue      $366B     $394B     $383B     $391B     $420B  │
 * │ YoY %        +33.3%    +7.8%     -2.8%     +2.1%     +7.4%  │
 * ├─────────────────────────────────────────────────────────────┤
 * │ Gross Profit $152B     $171B     $170B     $178B       N/A  │
 * │ Margin       41.5%     43.3%     44.1%     45.6%       N/A  │
 * │ YoY %        +46.2%    +12.5%    -0.6%     +4.7%       N/A  │
 * └─────────────────────────────────────────────────────────────┘
 */
export function MetricSection({
  title,
  years,
  getValue,
  getMargin,
  getGrowth,
  showMargin,
  isEPS = false
}: MetricSectionProps) {
  const formatValue = isEPS ? formatEPS : formatCurrency

  return (
    <>
      {/* Metric Title Row */}
      <tr className="border-b transition-colors duration-300" style={{ borderColor: 'var(--border-primary)' }}>
        <td
          colSpan={years.length + 1}
          className="px-4 py-2 font-semibold transition-colors duration-300"
          style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--text-secondary)',
            backgroundColor: 'var(--bg-tertiary)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em'
          }}
        >
          {title}
        </td>
      </tr>

      {/* Value Row */}
      <tr className="transition-colors duration-300 hover:bg-opacity-50" style={{ backgroundColor: 'var(--bg-secondary)' }}>
        <td className="px-4 py-2 text-left font-medium transition-colors duration-300" style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--text-secondary)'
        }}>
          {title}
        </td>
        {years.map((year) => {
          const value = getValue(year)
          return (
            <td
              key={`${title}-${year.year}-value`}
              className="px-4 py-2 text-right tabular-nums font-medium transition-colors duration-300"
              style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-primary)'
              }}
            >
              {formatValue(value)}
            </td>
          )
        })}
      </tr>

      {/* Margin Row (optional) */}
      {showMargin && (
        <tr className="transition-colors duration-300 hover:bg-opacity-50" style={{ backgroundColor: 'var(--bg-secondary)' }}>
          <td className="px-4 py-2 text-left transition-colors duration-300" style={{
            fontSize: 'var(--text-xs)',
            color: 'var(--text-tertiary)',
            paddingLeft: '2rem'
          }}>
            Margin
          </td>
          {years.map((year) => {
            const margin = getMargin(year)
            return (
              <td
                key={`${title}-${year.year}-margin`}
                className="px-4 py-2 text-right tabular-nums transition-colors duration-300"
                style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-secondary)'
                }}
              >
                {formatPercent(margin)}
              </td>
            )
          })}
        </tr>
      )}

      {/* YoY Growth Row */}
      <tr className="border-b transition-colors duration-300" style={{ borderColor: 'var(--border-primary)', backgroundColor: 'var(--bg-secondary)' }}>
        <td className="px-4 py-2 text-left transition-colors duration-300" style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--text-tertiary)',
          paddingLeft: '2rem'
        }}>
          YoY %
        </td>
        {years.map((year) => {
          const growth = getGrowth(year)
          const colorClass = getGrowthColor(growth)
          return (
            <td
              key={`${title}-${year.year}-growth`}
              className={`px-4 py-2 text-right tabular-nums font-semibold ${colorClass}`}
              style={{
                fontSize: 'var(--text-sm)'
              }}
            >
              {formatGrowth(growth)}
            </td>
          )
        })}
      </tr>
    </>
  )
}
