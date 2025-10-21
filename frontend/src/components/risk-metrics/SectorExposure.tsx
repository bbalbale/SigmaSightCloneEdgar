'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useTheme } from '@/contexts/ThemeContext'
import type { SectorExposureResponse } from '@/types/analytics'

interface SectorExposureProps {
  data: SectorExposureResponse | null
  loading: boolean
  error: string | null
  onRetry?: () => void
}

export function SectorExposure({ data, loading, error, onRetry }: SectorExposureProps) {
  const { theme } = useTheme()

  if (loading) {
    return (
      <Card className={`transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <CardHeader>
          <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
            Sector Exposure vs S&P 500
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`text-center py-8 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
            Loading sector exposure data...
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || !data?.available || !data?.data) {
    return (
      <Card className={`transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <CardHeader>
          <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
            Sector Exposure vs S&P 500
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className={`mb-4 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
              {error || data?.metadata?.error || 'Sector exposure data not available'}
            </p>
            {onRetry && (
              <button
                onClick={onRetry}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Retry
              </button>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  const { portfolio_weights, benchmark_weights, over_underweight } = data.data
  const benchmarkCode = data.metadata?.benchmark || 'S&P 500'

  // Get all sector names from benchmark weights (not portfolio, which might be empty)
  // This ensures we show all sectors even if portfolio has 0% allocation
  const sectors = Object.keys(benchmark_weights)

  console.log('🎯 SectorExposure Render:', {
    portfolio_weights,
    benchmark_weights,
    over_underweight,
    sectors,
    sectorsLength: sectors.length
  })

  if (sectors.length === 0) {
    return (
      <Card className={`transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
      }`}>
        <CardHeader>
          <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
            Sector Exposure vs {benchmarkCode}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`text-center py-8 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
            No sector data available
          </div>
        </CardContent>
      </Card>
    )
  }

  // Calculate max absolute over/underweight for scaling
  const maxOverweight = Math.max(...Object.values(over_underweight).map(v => Math.abs(v)))

  return (
    <Card className={`transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
    }`}>
      <CardHeader>
        <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
          Sector Exposure vs {benchmarkCode}
        </CardTitle>
        <p className={`text-sm mt-1 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
          Portfolio sector allocation compared to benchmark
        </p>
      </CardHeader>
      <CardContent>
        {/* Info message if portfolio has no classified positions */}
        {Object.keys(portfolio_weights).length === 0 && (
          <div className={`mb-4 p-3 rounded-lg ${
            theme === 'dark' ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'
          }`}>
            <p className={`text-sm ${theme === 'dark' ? 'text-blue-300' : 'text-blue-800'}`}>
              ℹ️ Your portfolio currently has no positions with sector classifications.
              This may be due to private investments, options contracts, or positions without sector data.
            </p>
          </div>
        )}

        <div className="space-y-4">
          {sectors.map((sector) => {
            // Handle cases where sector might not exist in portfolio_weights
            const portfolioWeight = portfolio_weights[sector] || 0
            const benchmarkWeight = benchmark_weights[sector] || 0
            const overUnder = over_underweight[sector] || 0

            const portfolioPct = (portfolioWeight * 100).toFixed(1)
            const benchmarkPct = (benchmarkWeight * 100).toFixed(1)
            const overUnderPct = (overUnder * 100).toFixed(1)
            const isOverweight = overUnder > 0
            const barWidth = Math.abs(overUnder) / maxOverweight * 100

            return (
              <div key={sector} className="space-y-2">
                {/* Sector name and weights */}
                <div className="flex justify-between items-center">
                  <span className={`text-sm font-medium ${
                    theme === 'dark' ? 'text-white' : 'text-gray-900'
                  }`}>
                    {sector}
                  </span>
                  <div className="flex gap-4 text-sm">
                    <span className={theme === 'dark' ? 'text-slate-300' : 'text-gray-700'}>
                      Portfolio: <span className="font-semibold">{portfolioPct}%</span>
                    </span>
                    <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-500'}>
                      {benchmarkCode}: {benchmarkPct}%
                    </span>
                  </div>
                </div>

                {/* Over/underweight bar */}
                <div className="relative h-6 bg-slate-100 dark:bg-slate-700 rounded">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className={`text-xs font-medium ${
                      theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
                    }`}>
                      {isOverweight ? '+' : ''}{overUnderPct}%
                    </span>
                  </div>
                  <div
                    className={`absolute top-0 h-full rounded transition-all ${
                      isOverweight
                        ? 'bg-emerald-500/60 right-1/2'
                        : 'bg-red-500/60 left-1/2'
                    }`}
                    style={{
                      width: `${barWidth}%`,
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>

        {/* Legend */}
        <div className="mt-6 pt-4 border-t flex justify-center gap-6 text-xs"
          style={{
            borderColor: theme === 'dark' ? 'rgb(51 65 85)' : 'rgb(229 231 235)'
          }}
        >
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-emerald-500/60 rounded"></div>
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Overweight vs {benchmarkCode}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500/60 rounded"></div>
            <span className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
              Underweight vs {benchmarkCode}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
