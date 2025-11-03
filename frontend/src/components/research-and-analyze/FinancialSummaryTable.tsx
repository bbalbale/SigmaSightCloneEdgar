'use client'

import React from 'react'
import { FundamentalsData } from '@/hooks/useFundamentals'
import { MetricSection } from './MetricSection'
import { TableFooter } from './TableFooter'

interface FinancialSummaryTableProps {
  data: FundamentalsData
}

/**
 * FinancialSummaryTable Component
 *
 * Displays comprehensive financial summary with:
 * - Header row with year columns (historical + estimates)
 * - 6 metric sections (Revenue, Gross Profit, EBIT, Net Income, EPS, FCF)
 * - Footer with fiscal year end notation
 *
 * Layout:
 * ┌──────────────────────────────────────────────────────────────────────────┐
 * │              Historical (Actual)          Forward (Estimates)              │
 * │   Metric        2021      2022      2023      2024      2025E     2026E   │
 * ├──────────────────────────────────────────────────────────────────────────┤
 * │   Revenue      $366B     $394B     $383B     $391B     $420B     $448B    │
 * │   YoY %        +33.3%    +7.8%     -2.8%     +2.1%     +7.4%     +6.7%    │
 * │   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
 * │   ...                                                                      │
 * └──────────────────────────────────────────────────────────────────────────┘
 */
export function FinancialSummaryTable({ data }: FinancialSummaryTableProps) {
  const { years, symbol } = data

  // Separate historical and estimate years
  const historicalYears = years.filter(y => !y.isEstimate)
  const estimateYears = years.filter(y => y.isEstimate)
  const allYears = [...historicalYears, ...estimateYears]

  return (
    <div className="space-y-4">
      {/* Header - Standard Section Heading */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider transition-colors duration-300" style={{ color: 'var(--color-accent)' }}>
          Financial Summary
        </h3>
        <span className="text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          {symbol} · Annual Data
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            {/* Super Header Row: Historical vs Forward */}
            <tr className="border-b transition-colors duration-300" style={{ borderColor: 'var(--border-primary)' }}>
              <th className="text-left px-4 py-2 font-semibold transition-colors duration-300 w-40" style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-secondary)'
              }}>
                Metric
              </th>
              {historicalYears.length > 0 && (
                <th
                  colSpan={historicalYears.length}
                  className="text-center px-4 py-2 font-semibold transition-colors duration-300"
                  style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-secondary)',
                    backgroundColor: 'var(--bg-tertiary)'
                  }}
                >
                  Historical (Actual)
                </th>
              )}
              {estimateYears.length > 0 && (
                <th
                  colSpan={estimateYears.length}
                  className="text-center px-4 py-2 font-semibold transition-colors duration-300"
                  style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-secondary)',
                    backgroundColor: 'var(--bg-secondary)'
                  }}
                >
                  Forward (Estimates)
                </th>
              )}
            </tr>

            {/* Year Header Row */}
            <tr className="border-b transition-colors duration-300" style={{ borderColor: 'var(--border-primary)' }}>
              <th className="text-left px-4 py-2"></th>
              {allYears.map((year) => (
                <th
                  key={year.year}
                  className="text-right px-4 py-2 font-semibold tabular-nums transition-colors duration-300"
                  style={{
                    fontSize: 'var(--text-sm)',
                    color: year.isEstimate ? 'var(--color-accent)' : 'var(--text-primary)',
                    backgroundColor: year.isEstimate ? 'var(--bg-secondary)' : 'var(--bg-tertiary)',
                    minWidth: '100px'
                  }}
                >
                  {year.isEstimate ? `${year.year}E` : year.year}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {/* Revenue */}
            <MetricSection
              title="Revenue"
              years={allYears}
              getValue={(year) => year.revenue}
              getMargin={() => null}
              getGrowth={(year) => year.revenueGrowth}
              showMargin={false}
            />

            {/* Gross Profit */}
            <MetricSection
              title="Gross Profit"
              years={allYears}
              getValue={(year) => year.grossProfit}
              getMargin={(year) => year.grossMargin}
              getGrowth={(year) => year.grossProfitGrowth}
              showMargin={true}
            />

            {/* EBIT (Operating Income) */}
            <MetricSection
              title="EBIT"
              years={allYears}
              getValue={(year) => year.ebit}
              getMargin={(year) => year.ebitMargin}
              getGrowth={(year) => year.ebitGrowth}
              showMargin={true}
            />

            {/* Net Income */}
            <MetricSection
              title="Net Income"
              years={allYears}
              getValue={(year) => year.netIncome}
              getMargin={(year) => year.netMargin}
              getGrowth={(year) => year.netIncomeGrowth}
              showMargin={true}
            />

            {/* EPS */}
            <MetricSection
              title="EPS"
              years={allYears}
              getValue={(year) => year.eps}
              getMargin={() => null}
              getGrowth={(year) => year.epsGrowth}
              showMargin={false}
              isEPS={true}
            />

            {/* Free Cash Flow */}
            <MetricSection
              title="Free Cash Flow"
              years={allYears}
              getValue={(year) => year.fcf}
              getMargin={(year) => year.fcfMargin}
              getGrowth={(year) => year.fcfGrowth}
              showMargin={true}
            />
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <TableFooter
        fiscalYearEnd={data.fiscalYearEnd}
        analystCount={data.analystCount}
        lastUpdated={data.lastUpdated}
      />
    </div>
  )
}
