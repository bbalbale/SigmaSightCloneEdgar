"use client"

import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import type { CorrelationMatrixResponse } from '@/types/analytics'

interface CorrelationMatrixProps {
  data: CorrelationMatrixResponse | null
  loading: boolean
  error: Error | null
  onRetry?: () => void
}

export function CorrelationMatrix({ data, loading, error, onRetry }: CorrelationMatrixProps) {
  const { theme } = useTheme()

  // Get color based on correlation value
  const getCorrelationColor = (value: number): string => {
    if (value >= 0.7) return theme === 'dark' ? 'bg-green-900/50 text-green-200' : 'bg-green-100 text-green-800'
    if (value >= 0.3) return theme === 'dark' ? 'bg-green-800/30 text-green-300' : 'bg-green-50 text-green-700'
    if (value > -0.3) return theme === 'dark' ? 'bg-slate-700/50 text-slate-300' : 'bg-gray-50 text-gray-700'
    if (value > -0.7) return theme === 'dark' ? 'bg-red-800/30 text-red-300' : 'bg-red-50 text-red-700'
    return theme === 'dark' ? 'bg-red-900/50 text-red-200' : 'bg-red-100 text-red-800'
  }

  // Loading state
  if (loading) {
    return (
      <div className={`rounded-lg border p-8 transition-colors duration-300 ${
        theme === 'dark'
          ? 'bg-slate-800 border-slate-700'
          : 'bg-white border-gray-200'
      }`}>
        <h2 className={`text-2xl font-bold mb-4 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>
          Correlation Matrix
        </h2>
        <div className="flex items-center justify-center py-12">
          <div className={`text-center ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
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
      <div className={`rounded-lg border p-8 transition-colors duration-300 ${
        theme === 'dark'
          ? 'bg-slate-800 border-slate-700'
          : 'bg-white border-gray-200'
      }`}>
        <h2 className={`text-2xl font-bold mb-4 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>
          Correlation Matrix
        </h2>
        <div className={`rounded-lg border p-6 text-center ${
          theme === 'dark'
            ? 'bg-red-900/20 border-red-800 text-red-300'
            : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          <p className="mb-4">Error loading correlation matrix: {error.message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className={`px-4 py-2 rounded-md text-sm transition-colors ${
                theme === 'dark'
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
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
      <div className={`rounded-lg border p-8 transition-colors duration-300 ${
        theme === 'dark'
          ? 'bg-slate-800 border-slate-700'
          : 'bg-white border-gray-200'
      }`}>
        <h2 className={`text-2xl font-bold mb-4 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>
          Correlation Matrix
        </h2>
        <div className={`rounded-lg border p-6 text-center ${
          theme === 'dark'
            ? 'bg-slate-700/50 border-slate-600 text-slate-300'
            : 'bg-gray-50 border-gray-200 text-gray-600'
        }`}>
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
    <div className={`rounded-lg border p-8 transition-colors duration-300 ${
      theme === 'dark'
        ? 'bg-slate-800 border-slate-700'
        : 'bg-white border-gray-200'
    }`}>
      <div className="mb-6">
        <h2 className={`text-2xl font-bold mb-2 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>
          Correlation Matrix
        </h2>

        {/* Metadata */}
        {data.metadata && (
          <div className={`flex flex-wrap gap-4 text-sm ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            <span>
              Positions: <strong className={theme === 'dark' ? 'text-slate-200' : 'text-gray-800'}>
                {data.metadata.positions_included}
              </strong>
            </span>
            <span>
              Lookback: <strong className={theme === 'dark' ? 'text-slate-200' : 'text-gray-800'}>
                {data.metadata.lookback_days} days
              </strong>
            </span>
            <span>
              Average Correlation: <strong className={theme === 'dark' ? 'text-slate-200' : 'text-gray-800'}>
                {data.data.average_correlation.toFixed(3)}
              </strong>
            </span>
            <span>
              Calculated: <strong className={theme === 'dark' ? 'text-slate-200' : 'text-gray-800'}>
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
              <th className={`sticky left-0 z-10 px-3 py-2 text-left text-xs font-semibold ${
                theme === 'dark'
                  ? 'bg-slate-800 text-slate-300 border-slate-600'
                  : 'bg-white text-gray-700 border-gray-300'
              } border-b border-r`}>
                Symbol
              </th>
              {symbols.map((symbol) => (
                <th
                  key={symbol}
                  className={`px-3 py-2 text-center text-xs font-semibold whitespace-nowrap ${
                    theme === 'dark'
                      ? 'bg-slate-800 text-slate-300 border-slate-600'
                      : 'bg-white text-gray-700 border-gray-300'
                  } border-b`}
                >
                  {symbol}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {symbols.map((rowSymbol, rowIndex) => (
              <tr key={rowSymbol}>
                <td className={`sticky left-0 z-10 px-3 py-2 text-xs font-medium whitespace-nowrap ${
                  theme === 'dark'
                    ? 'bg-slate-800 text-slate-300 border-slate-600'
                    : 'bg-white text-gray-700 border-gray-300'
                } border-r`}>
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
                          ? theme === 'dark' ? 'bg-blue-900/30 text-blue-200' : 'bg-blue-50 text-blue-800'
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
      <div className={`mt-6 p-4 rounded-lg ${
        theme === 'dark' ? 'bg-slate-700/50' : 'bg-gray-50'
      }`}>
        <h3 className={`text-sm font-semibold mb-2 ${
          theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
        }`}>
          Correlation Scale
        </h3>
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${
              theme === 'dark' ? 'bg-red-900/50' : 'bg-red-100'
            }`}></div>
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Strong Negative (&lt; -0.7)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${
              theme === 'dark' ? 'bg-red-800/30' : 'bg-red-50'
            }`}></div>
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Moderate Negative (-0.7 to -0.3)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${
              theme === 'dark' ? 'bg-slate-700/50' : 'bg-gray-50'
            }`}></div>
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Weak (-0.3 to 0.3)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${
              theme === 'dark' ? 'bg-green-800/30' : 'bg-green-50'
            }`}></div>
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Moderate Positive (0.3 to 0.7)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${
              theme === 'dark' ? 'bg-green-900/50' : 'bg-green-100'
            }`}></div>
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Strong Positive (&gt; 0.7)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded ${
              theme === 'dark' ? 'bg-blue-900/30' : 'bg-blue-50'
            }`}></div>
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Self Correlation (1.0)
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
