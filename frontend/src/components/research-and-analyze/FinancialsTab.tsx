'use client'

import React from 'react'
import { useFundamentals } from '@/hooks/useFundamentals'
import { FinancialSummaryTable } from './FinancialSummaryTable'

interface FinancialsTabProps {
  symbol: string
}

/**
 * FinancialsTab Component
 *
 * Displays comprehensive financial summary table with:
 * - 4 years historical data (2021-2024)
 * - 2 years forward estimates (2025E, 2026E)
 * - 6 metrics: Revenue, Gross Profit, EBIT, Net Income, EPS, FCF
 * - YoY growth rates for all metrics
 *
 * Data fetched from backend fundamental data endpoints:
 * - Income statements (revenue, margins, EPS)
 * - Cash flows (operating CF, FCF)
 * - Analyst estimates (forward revenue, EPS)
 */
export function FinancialsTab({ symbol }: FinancialsTabProps) {
  const { data, loading, error, refetch } = useFundamentals(symbol, 'a', 4)

  // Loading state
  if (loading) {
    return (
      <div className="p-8 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 transition-colors duration-300"
          style={{ borderColor: 'var(--color-accent)' }}
        />
        <p className="mt-4 text-sm transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          Loading financial data...
        </p>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="text-sm transition-colors duration-300" style={{ color: 'var(--color-error)' }}>
          Failed to load financial data
        </div>
        <p className="mt-2 text-xs transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          {error.message}
        </p>
        <button
          onClick={refetch}
          className="mt-4 px-4 py-2 text-sm rounded transition-all duration-200 hover:opacity-80"
          style={{
            backgroundColor: 'var(--color-accent)',
            color: 'white'
          }}
        >
          Retry
        </button>
      </div>
    )
  }

  // No data state
  if (!data || data.years.length === 0) {
    return (
      <div className="p-8 text-center">
        <p className="text-sm transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          No financial data available for {symbol}
        </p>
      </div>
    )
  }

  // Success - render table
  return (
    <div className="p-6">
      <FinancialSummaryTable data={data} />
    </div>
  )
}
