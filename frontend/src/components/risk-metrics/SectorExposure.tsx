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

  // Get all sector names from both benchmark and portfolio weights
  // This ensures we show all sectors including ETFs and Unclassified (which are portfolio-only)
  const allSectors = new Set([
    ...Object.keys(benchmark_weights),
    ...Object.keys(portfolio_weights)
  ])

  // Separate classified sectors from ETFs and Unclassified
  const classifiedSectors = Array.from(allSectors).filter(s => s !== 'Unclassified' && s !== 'ETFs')
  const hasETFs = portfolio_weights['ETFs'] !== undefined
  const hasUnclassified = portfolio_weights['Unclassified'] !== undefined

  console.log('🎯 SectorExposure Render:', {
    portfolio_weights,
    benchmark_weights,
    over_underweight,
    classifiedSectors,
    hasETFs,
    hasUnclassified,
    classifiedSectorsLength: classifiedSectors.length
  })

  if (classifiedSectors.length === 0 && !hasETFs && !hasUnclassified) {
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

        {/* Butterfly Chart - Mirror Design */}
        <div className="space-y-3">
          {/* Header Row */}
          <div className="flex items-center gap-2 pb-2 border-b"
            style={{
              borderColor: theme === 'dark' ? 'rgb(51 65 85)' : 'rgb(229 231 235)'
            }}
          >
            <div className={`flex-1 text-right text-sm font-semibold ${
              theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
            }`}>
              {benchmarkCode}
            </div>
            <div className={`min-w-[180px] text-center text-sm font-semibold ${
              theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
            }`}>
              Sector
            </div>
            <div className={`flex-1 text-left text-sm font-semibold ${
              theme === 'dark' ? 'text-blue-400' : 'text-blue-600'
            }`}>
              Portfolio
            </div>
          </div>

          {/* Classified sector rows sorted by benchmark weight */}
          {classifiedSectors
            .map(sector => ({
              sector,
              portfolioWeight: portfolio_weights[sector] || 0,
              benchmarkWeight: benchmark_weights[sector] || 0,
              overUnder: over_underweight[sector] || 0
            }))
            .sort((a, b) => b.benchmarkWeight - a.benchmarkWeight)
            .map(({ sector, portfolioWeight, benchmarkWeight, overUnder }) => {
              const portfolioPct = (portfolioWeight * 100).toFixed(1)
              const benchmarkPct = (benchmarkWeight * 100).toFixed(1)
              const overUnderPct = (overUnder * 100).toFixed(1)
              const isOverweight = overUnder > 0

              // Calculate bar widths (scale to max for visual consistency)
              // Use max from both benchmark AND portfolio weights
              const maxWeight = Math.max(
                ...Object.values(benchmark_weights),
                ...Object.values(portfolio_weights)
              )
              const portfolioBarWidth = (portfolioWeight / maxWeight) * 100
              const benchmarkBarWidth = (benchmarkWeight / maxWeight) * 100

              return (
                <div key={sector} className="flex items-center gap-2">
                  {/* Benchmark bar (left side, extends left from center) */}
                  <div className="flex-1 flex justify-end items-center">
                    <div className="flex items-center gap-2 w-full justify-end">
                      <span className={`text-xs font-medium min-w-[40px] text-right transition-colors duration-300 ${
                        theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
                      }`}>
                        {benchmarkPct}%
                      </span>
                      <div className="flex-1 max-w-[300px] h-7 flex justify-end">
                        <div
                          className="h-full bg-gray-400 dark:bg-gray-500 rounded-l transition-all duration-300"
                          style={{ width: `${benchmarkBarWidth}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Center label with delta badge */}
                  <div className="flex flex-col items-center min-w-[180px]">
                    <span className={`text-sm font-medium transition-colors duration-300 ${
                      theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
                    }`}>
                      {sector}
                    </span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded mt-0.5 transition-colors duration-300 ${
                      isOverweight
                        ? theme === 'dark'
                          ? 'bg-emerald-900/30 text-emerald-400'
                          : 'bg-emerald-100 text-emerald-700'
                        : Math.abs(overUnder) < 0.01
                        ? theme === 'dark'
                          ? 'bg-gray-800 text-gray-400'
                          : 'bg-gray-100 text-gray-600'
                        : theme === 'dark'
                        ? 'bg-rose-900/30 text-rose-400'
                        : 'bg-rose-100 text-rose-700'
                    }`}>
                      {isOverweight ? '+' : ''}{overUnderPct}%
                    </span>
                  </div>

                  {/* Portfolio bar (right side, extends right from center) */}
                  <div className="flex-1 flex items-center">
                    <div className="flex items-center gap-2 w-full">
                      <div className="flex-1 max-w-[300px] h-7 flex">
                        <div
                          className="h-full bg-blue-500 dark:bg-blue-600 rounded-r transition-all duration-300"
                          style={{ width: `${portfolioBarWidth}%` }}
                        />
                      </div>
                      <span className={`text-xs font-medium min-w-[40px] transition-colors duration-300 ${
                        theme === 'dark' ? 'text-blue-400' : 'text-blue-600'
                      }`}>
                        {portfolioPct}%
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}

          {/* ETFs bar (if present) */}
          {hasETFs && (() => {
            const portfolioWeight = portfolio_weights['ETFs'] || 0
            const benchmarkWeight = 0 // Benchmark has no ETFs
            const overUnder = over_underweight['ETFs'] || portfolioWeight
            const portfolioPct = (portfolioWeight * 100).toFixed(1)
            const benchmarkPct = '0.0'
            const overUnderPct = (overUnder * 100).toFixed(1)

            // Calculate bar width
            const maxWeight = Math.max(
              ...Object.values(benchmark_weights),
              ...Object.values(portfolio_weights)
            )
            const portfolioBarWidth = (portfolioWeight / maxWeight) * 100

            return (
              <div key="etfs" className="flex items-center gap-2 pt-2 mt-2 border-t"
                style={{
                  borderColor: theme === 'dark' ? 'rgb(51 65 85 / 0.5)' : 'rgb(229 231 235 / 0.5)'
                }}
              >
                {/* Benchmark bar (left side - empty for ETFs) */}
                <div className="flex-1 flex justify-end items-center">
                  <div className="flex items-center gap-2 w-full justify-end">
                    <span className={`text-xs font-medium min-w-[40px] text-right transition-colors duration-300 ${
                      theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      {benchmarkPct}%
                    </span>
                    <div className="flex-1 max-w-[300px] h-7 flex justify-end">
                      {/* No bar for benchmark */}
                    </div>
                  </div>
                </div>

                {/* Center label with delta badge */}
                <div className="flex flex-col items-center min-w-[180px]">
                  <span className={`text-sm font-medium transition-colors duration-300 ${
                    theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
                  }`}>
                    ETFs / Index Funds
                  </span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded mt-0.5 transition-colors duration-300 ${
                    theme === 'dark'
                      ? 'bg-purple-900/30 text-purple-400'
                      : 'bg-purple-100 text-purple-700'
                  }`}>
                    +{overUnderPct}%
                  </span>
                </div>

                {/* Portfolio bar (right side - purple color) */}
                <div className="flex-1 flex items-center">
                  <div className="flex items-center gap-2 w-full">
                    <div className="flex-1 max-w-[300px] h-7 flex">
                      <div
                        className="h-full bg-purple-500 dark:bg-purple-600 rounded-r transition-all duration-300"
                        style={{ width: `${portfolioBarWidth}%` }}
                      />
                    </div>
                    <span className={`text-xs font-medium min-w-[40px] transition-colors duration-300 ${
                      theme === 'dark' ? 'text-purple-400' : 'text-purple-600'
                    }`}>
                      {portfolioPct}%
                    </span>
                  </div>
                </div>
              </div>
            )
          })()}

          {/* Unclassified bar (if present) */}
          {hasUnclassified && (() => {
            const portfolioWeight = portfolio_weights['Unclassified'] || 0
            const benchmarkWeight = 0 // Benchmark has no unclassified
            const overUnder = over_underweight['Unclassified'] || portfolioWeight
            const portfolioPct = (portfolioWeight * 100).toFixed(1)
            const benchmarkPct = '0.0'
            const overUnderPct = (overUnder * 100).toFixed(1)

            // Calculate bar width
            const maxWeight = Math.max(
              ...Object.values(benchmark_weights),
              ...Object.values(portfolio_weights)
            )
            const portfolioBarWidth = (portfolioWeight / maxWeight) * 100

            return (
              <div key="unclassified" className="flex items-center gap-2 pt-2 mt-2 border-t"
                style={{
                  borderColor: theme === 'dark' ? 'rgb(51 65 85 / 0.5)' : 'rgb(229 231 235 / 0.5)'
                }}
              >
                {/* Benchmark bar (left side - empty for unclassified) */}
                <div className="flex-1 flex justify-end items-center">
                  <div className="flex items-center gap-2 w-full justify-end">
                    <span className={`text-xs font-medium min-w-[40px] text-right transition-colors duration-300 ${
                      theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      {benchmarkPct}%
                    </span>
                    <div className="flex-1 max-w-[300px] h-7 flex justify-end">
                      {/* No bar for benchmark */}
                    </div>
                  </div>
                </div>

                {/* Center label with delta badge */}
                <div className="flex flex-col items-center min-w-[180px]">
                  <span className={`text-sm font-medium transition-colors duration-300 ${
                    theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
                  }`}>
                    Unclassified
                  </span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded mt-0.5 transition-colors duration-300 ${
                    theme === 'dark'
                      ? 'bg-amber-900/30 text-amber-400'
                      : 'bg-amber-100 text-amber-700'
                  }`}>
                    +{overUnderPct}%
                  </span>
                </div>

                {/* Portfolio bar (right side - amber color) */}
                <div className="flex-1 flex items-center">
                  <div className="flex items-center gap-2 w-full">
                    <div className="flex-1 max-w-[300px] h-7 flex">
                      <div
                        className="h-full bg-amber-500 dark:bg-amber-600 rounded-r transition-all duration-300"
                        style={{ width: `${portfolioBarWidth}%` }}
                      />
                    </div>
                    <span className={`text-xs font-medium min-w-[40px] transition-colors duration-300 ${
                      theme === 'dark' ? 'text-amber-400' : 'text-amber-600'
                    }`}>
                      {portfolioPct}%
                    </span>
                  </div>
                </div>
              </div>
            )
          })()}
        </div>

        {/* Legend */}
        <div className="mt-6 pt-4 border-t flex justify-center gap-8 text-xs"
          style={{
            borderColor: theme === 'dark' ? 'rgb(51 65 85)' : 'rgb(229 231 235)'
          }}
        >
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-gray-400 dark:bg-gray-500 rounded"></div>
            <span className={`transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              {benchmarkCode}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-500 dark:bg-blue-600 rounded"></div>
            <span className={`transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Portfolio
            </span>
          </div>
          {hasETFs && (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-purple-500 dark:bg-purple-600 rounded"></div>
              <span className={`transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>
                ETFs / Index Funds
              </span>
            </div>
          )}
          {hasUnclassified && (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-amber-500 dark:bg-amber-600 rounded"></div>
              <span className={`transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>
                Unclassified
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
