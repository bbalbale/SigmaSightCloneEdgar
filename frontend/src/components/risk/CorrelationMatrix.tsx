"use client"

import React from 'react'
import type { CorrelationMatrixResponse } from '@/types/analytics'

interface CorrelationMatrixProps {
  data: CorrelationMatrixResponse | null
  loading: boolean
  error: Error | null
  onRetry?: () => void
}

export function CorrelationMatrix({ data, loading, error, onRetry }: CorrelationMatrixProps) {
  // Get color based on correlation value (using Tailwind classes for color coding)
  const getCorrelationColor = (value: number): string => {
    if (value >= 0.7) return 'bg-green-900/50 text-green-200 dark:bg-green-900/50 dark:text-green-200'
    if (value >= 0.3) return 'bg-green-800/30 text-green-300 dark:bg-green-800/30 dark:text-green-300'
    if (value > -0.3) return 'bg-slate-700/50 dark:bg-slate-700/50'
    if (value > -0.7) return 'bg-red-800/30 text-red-300 dark:bg-red-800/30 dark:text-red-300'
    return 'bg-red-900/50 text-red-200 dark:bg-red-900/50 dark:text-red-200'
  }

  // Loading state
  if (loading) {
    return (
      <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
        <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Correlation Matrix
        </h2>
        <div className="flex items-center justify-center py-12">
          <div className="text-center text-secondary">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-current mx-auto mb-4"></div>
            <p>Loading correlation matrix...</p>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
        <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Correlation Matrix
        </h2>
        <div className="rounded-lg border p-6 text-center bg-red-900/20 border-red-800 text-red-300">
          <p className="mb-4">Error loading correlation matrix: {error.message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-4 py-2 rounded-md text-sm transition-colors bg-blue-600 hover:bg-blue-700 text-white"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    )
  }

  // Data not available
  if (!data?.available || !data?.data) {
    return (
      <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
        <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Correlation Matrix
        </h2>
        <div className="rounded-lg border p-6 text-center transition-colors duration-300" style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
          color: 'var(--text-primary)'
        }}>
          <p>Correlation matrix is not available</p>
          {data?.reason && (
            <p className="mt-2 text-sm opacity-70">Reason: {data.reason}</p>
          )}
        </div>
      </div>
    )
  }

  // Extract symbols from matrix
  const symbols = Object.keys(data.data.matrix)

  return (
    <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Correlation Matrix
        </h2>

        {/* Metadata */}
        {data.metadata && (
          <div className="flex flex-wrap gap-4 text-sm text-secondary">
            <span>
              Positions: <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                {data.metadata.positions_included}
              </strong>
            </span>
            <span>
              Lookback: <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                {data.metadata.lookback_days} days
              </strong>
            </span>
            <span>
              Average Correlation: <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                {data.data.average_correlation.toFixed(3)}
              </strong>
            </span>
            <span>
              Calculated: <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                {new Date(data.metadata.calculation_date).toLocaleDateString()}
              </strong>
            </span>
          </div>
        )}
      </div>

      {/* Correlation Matrix Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 px-3 py-2 text-left text-xs font-semibold border-b border-r transition-colors duration-300" style={{
                backgroundColor: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                borderColor: 'var(--border-primary)'
              }}>
                Symbol
              </th>
              {symbols.map((symbol) => (
                <th
                  key={symbol}
                  className="px-3 py-2 text-center text-xs font-semibold whitespace-nowrap border-b transition-colors duration-300"
                  style={{
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    borderColor: 'var(--border-primary)'
                  }}
                >
                  {symbol}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {symbols.map((rowSymbol, rowIndex) => (
              <tr key={rowSymbol}>
                <td className="sticky left-0 z-10 px-3 py-2 text-xs font-medium whitespace-nowrap border-r transition-colors duration-300" style={{
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  borderColor: 'var(--border-primary)'
                }}>
                  {rowSymbol}
                </td>
                {symbols.map((colSymbol) => {
                  const value = data.data!.matrix[rowSymbol]?.[colSymbol] ?? 0
                  const isDiagonal = rowSymbol === colSymbol

                  return (
                    <td
                      key={colSymbol}
                      className={`px-3 py-2 text-center text-xs font-mono transition-colors ${
                        isDiagonal
                          ? 'bg-blue-900/30 text-blue-200'
                          : getCorrelationColor(value)
                      }`}
                    >
                      {value.toFixed(2)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="mt-6 p-4 rounded-lg transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
        <h3 className="text-sm font-semibold mb-2 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Correlation Scale
        </h3>
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-red-900/50"></div>
            <span className="text-secondary">
              Strong Negative (&lt; -0.7)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-red-800/30"></div>
            <span className="text-secondary">
              Moderate Negative (-0.7 to -0.3)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-slate-700/50"></div>
            <span className="text-secondary">
              Weak (-0.3 to 0.3)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-green-800/30"></div>
            <span className="text-secondary">
              Moderate Positive (0.3 to 0.7)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-green-900/50"></div>
            <span className="text-secondary">
              Strong Positive (&gt; 0.7)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-blue-900/30"></div>
            <span className="text-secondary">
              Self Correlation (1.0)
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
