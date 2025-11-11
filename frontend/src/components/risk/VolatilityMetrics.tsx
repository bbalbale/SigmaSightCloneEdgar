"use client"

import React from 'react'
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { VolatilityMetricsResponse } from '@/types/analytics'

interface VolatilityMetricsProps {
  data: VolatilityMetricsResponse | null
  loading: boolean
  error: Error | null
  onRetry?: () => void
}

export function VolatilityMetrics({ data, loading, error, onRetry }: VolatilityMetricsProps) {
  const getTrendIcon = (volTrend: string | null) => {
    if (volTrend === 'increasing') return <TrendingUp className="h-5 w-5 text-red-500" />
    if (volTrend === 'decreasing') return <TrendingDown className="h-5 w-5 text-green-500" />
    return <Minus className="h-5 w-5 text-tertiary" />
  }

  const getTrendColor = (volTrend: string | null) => {
    if (volTrend === 'increasing') return 'text-red-500'
    if (volTrend === 'decreasing') return 'text-green-500'
    return 'text-tertiary'
  }

  const getVolatilityLevel = (vol: number): string => {
    if (vol < 0.15) return 'Very Low'
    if (vol < 0.25) return 'Low'
    if (vol < 0.35) return 'Moderate'
    if (vol < 0.50) return 'High'
    return 'Very High'
  }

  const getPercentileDescription = (percentile: number): string => {
    if (percentile >= 0.75) return 'Well above historical'
    if (percentile >= 0.5) return 'Above historical'
    if (percentile >= 0.25) return 'Near historical average'
    return 'Below historical'
  }

  const getPercentileColor = (percentile: number): string => {
    if (percentile >= 0.75) return 'bg-red-500'
    if (percentile >= 0.5) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  // Loading state
  if (loading) {
    return (
      <div className="rounded-lg border p-6 transition-colors duration-300 themed-card">
        <h3 className="text-xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Volatility Analysis
        </h3>
        <div className="flex items-center justify-center py-8">
          <div className="text-center text-secondary">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-current mx-auto mb-3"></div>
            <p className="text-sm">Loading...</p>
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border p-6 transition-colors duration-300 themed-card">
        <h3 className="text-xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Volatility Analysis
        </h3>
        <div className="rounded-lg border p-4 text-center bg-red-900/20 border-red-800 text-red-300">
          <p className="mb-3 text-sm">Error: {error.message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-3 py-1.5 rounded-md text-sm transition-colors bg-blue-600 hover:bg-blue-700 text-white"
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
      <div className="rounded-lg border p-6 transition-colors duration-300 themed-card">
        <h3 className="text-xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Volatility Analysis
        </h3>
        <div className="rounded-lg border p-4 text-center transition-colors duration-300" style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
          color: 'var(--text-primary)'
        }}>
          <p className="text-sm">Volatility metrics are not available</p>
          {data?.metadata?.error && (
            <p className="mt-2 text-xs opacity-70">Reason: {data.metadata.error}</p>
          )}
        </div>
      </div>
    )
  }

  const {
    realized_volatility_21d,
    realized_volatility_63d,
    expected_volatility_21d,
    volatility_trend,
    volatility_percentile
  } = data.data

  return (
    <div className="rounded-lg border p-6 transition-colors duration-300 themed-card">
      <div className="flex items-center gap-2 mb-6">
        <h3 className="text-xl font-bold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Volatility Analysis
        </h3>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              <Info className="h-4 w-4 text-secondary" />
            </TooltipTrigger>
            <TooltipContent>
              <p>Historical and forecasted portfolio volatility.</p>
              <p className="text-xs">Lower = more stable returns</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      <div className="space-y-4">
        {/* Current Volatility */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm font-medium text-primary">
              Current (21-day)
            </span>
            <span className="text-2xl font-bold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
              {(realized_volatility_21d * 100).toFixed(1)}%
            </span>
          </div>
          <p className="text-xs text-tertiary">
            {getVolatilityLevel(realized_volatility_21d)} volatility
          </p>
        </div>

        {/* Historical Windows */}
        {realized_volatility_63d !== null && (
          <div className="grid grid-cols-1 gap-4 py-2 border-t border-primary">
            <div>
              <p className="text-xs text-secondary">
                63-day (~3 months)
              </p>
              <p className="text-sm font-medium transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                {(realized_volatility_63d * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        )}

        {/* Expected Volatility */}
        {expected_volatility_21d !== null && (
          <div className="border-t pt-4 border-primary">
            <div className="flex justify-between items-center mb-1">
              <span className="text-sm font-medium text-primary">
                Expected (21-day forecast)
              </span>
              <span className="text-lg font-semibold text-blue-400">
                {(expected_volatility_21d * 100).toFixed(1)}%
              </span>
            </div>
            <p className="text-xs text-tertiary">
              HAR model forecast
            </p>
          </div>
        )}

        {/* Trend */}
        {volatility_trend && (
          <div className="flex items-center justify-between p-3 rounded-lg transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
            <div className="flex items-center gap-2">
              {getTrendIcon(volatility_trend)}
              <span className={`text-sm font-medium ${getTrendColor(volatility_trend)}`}>
                Volatility {volatility_trend}
              </span>
            </div>
            {volatility_percentile !== null && (
              <span className="text-xs text-secondary">
                {getPercentileDescription(volatility_percentile)}
              </span>
            )}
          </div>
        )}

        {/* Percentile Bar */}
        {volatility_percentile !== null && (
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-secondary">
                Volatility Percentile
              </span>
              <span className="font-medium text-primary">
                {(volatility_percentile * 100).toFixed(0)}th
              </span>
            </div>
            <div className="h-2 rounded-full overflow-hidden transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
              <div
                className={`h-full transition-all ${getPercentileColor(volatility_percentile)}`}
                style={{ width: `${volatility_percentile * 100}%` }}
              />
            </div>
            <p className="text-xs mt-1 text-tertiary">
              vs. 1-year historical distribution
            </p>
          </div>
        )}
      </div>

      {/* Metadata */}
      {data.calculation_date && (
        <div className="mt-4 text-xs text-center text-tertiary">
          Updated: {new Date(data.calculation_date).toLocaleDateString()}
        </div>
      )}
    </div>
  )
}
