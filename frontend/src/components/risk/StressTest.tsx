"use client"

import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import type { StressTestResponse, StressTestScenario } from '@/types/analytics'

interface StressTestProps {
  data: StressTestResponse | null
  loading: boolean
  error: Error | null
  onRetry?: () => void
}

export function StressTest({ data, loading, error, onRetry }: StressTestProps) {
  const { theme } = useTheme()

  // Format currency
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  // Format percentage
  const formatPercentage = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  // Get color based on impact severity
  const getImpactColor = (percentage: number): string => {
    if (percentage >= 0) return theme === 'dark' ? 'text-green-400' : 'text-green-600'
    if (percentage > -5) return theme === 'dark' ? 'text-yellow-400' : 'text-yellow-600'
    if (percentage > -10) return theme === 'dark' ? 'text-orange-400' : 'text-orange-600'
    return theme === 'dark' ? 'text-red-400' : 'text-red-600'
  }

  const getSeverityBadge = (severity?: string) => {
    if (!severity) return null

    const colors: Record<string, string> = {
      low: theme === 'dark' ? 'bg-green-900/30 text-green-300' : 'bg-green-100 text-green-700',
      medium: theme === 'dark' ? 'bg-yellow-900/30 text-yellow-300' : 'bg-yellow-100 text-yellow-700',
      high: theme === 'dark' ? 'bg-orange-900/30 text-orange-300' : 'bg-orange-100 text-orange-700',
      severe: theme === 'dark' ? 'bg-red-900/30 text-red-300' : 'bg-red-100 text-red-700',
    }

    return (
      <span className={`text-xs px-2 py-1 rounded ${colors[severity.toLowerCase()] || colors.medium}`}>
        {severity}
      </span>
    )
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
          Stress Test Scenarios
        </h2>
        <div className="flex items-center justify-center py-12">
          <div className={`text-center ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-current mx-auto mb-4"></div>
            <p>Loading stress test scenarios...</p>
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
          Stress Test Scenarios
        </h2>
        <div className={`rounded-lg border p-6 text-center ${
          theme === 'dark'
            ? 'bg-red-900/20 border-red-800 text-red-300'
            : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          <p className="mb-4">Error loading stress test: {error.message}</p>
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
          Stress Test Scenarios
        </h2>
        <div className={`rounded-lg border p-6 text-center ${
          theme === 'dark'
            ? 'bg-slate-700/50 border-slate-600 text-slate-300'
            : 'bg-gray-50 border-gray-200 text-gray-600'
        }`}>
          <p>Stress test data is not available</p>
          {data?.reason && (
            <p className="mt-2 text-sm opacity-70">Reason: {data.reason}</p>
          )}
        </div>
      </div>
    )
  }

  const { scenarios, portfolio_value, calculation_date } = data.data

  return (
    <div className={`rounded-lg border p-8 transition-colors duration-300 ${
      theme === 'dark'
        ? 'bg-slate-800 border-slate-700'
        : 'bg-white border-gray-200'
    }`}>
      {/* Header */}
      <div className="mb-6">
        <h2 className={`text-2xl font-bold mb-2 ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>
          Stress Test Scenarios
        </h2>
        <div className={`flex flex-wrap gap-4 text-sm ${
          theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
        }`}>
          <span>
            Portfolio Value: <strong className={theme === 'dark' ? 'text-slate-200' : 'text-gray-800'}>
              {formatCurrency(portfolio_value)}
            </strong>
          </span>
          <span>
            Scenarios: <strong className={theme === 'dark' ? 'text-slate-200' : 'text-gray-800'}>
              {scenarios.length}
            </strong>
          </span>
          <span>
            Date: <strong className={theme === 'dark' ? 'text-slate-200' : 'text-gray-800'}>
              {new Date(calculation_date).toLocaleDateString()}
            </strong>
          </span>
        </div>
      </div>

      {/* Scenarios Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scenarios.map((scenario) => (
          <div
            key={scenario.id}
            className={`rounded-lg border p-4 transition-colors duration-300 ${
              theme === 'dark'
                ? 'bg-slate-700/50 border-slate-600 hover:bg-slate-700'
                : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
            }`}
          >
            {/* Scenario Header */}
            <div className="mb-3">
              <div className="flex items-start justify-between mb-2">
                <h3 className={`font-semibold text-sm ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {scenario.name}
                </h3>
                {getSeverityBadge(scenario.severity)}
              </div>
              {scenario.description && (
                <p className={`text-xs ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                }`}>
                  {scenario.description}
                </p>
              )}
              {scenario.category && (
                <div className={`mt-2 text-xs ${
                  theme === 'dark' ? 'text-slate-500' : 'text-gray-500'
                }`}>
                  Category: {scenario.category}
                </div>
              )}
            </div>

            {/* Impact Metrics */}
            <div className="space-y-2 pt-3 border-t"
              style={{
                borderColor: theme === 'dark' ? 'rgb(71 85 105)' : 'rgb(229 231 235)'
              }}
            >
              <div className="flex justify-between items-center">
                <span className={`text-xs ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                }`}>
                  Dollar Impact
                </span>
                <span className={`text-sm font-semibold ${
                  getImpactColor(scenario.impact.percentage_impact)
                }`}>
                  {formatCurrency(scenario.impact.dollar_impact)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-xs ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                }`}>
                  % Impact
                </span>
                <span className={`text-sm font-semibold ${
                  getImpactColor(scenario.impact.percentage_impact)
                }`}>
                  {formatPercentage(scenario.impact.percentage_impact)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className={`text-xs ${
                  theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
                }`}>
                  New Value
                </span>
                <span className={`text-sm font-semibold ${
                  theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
                }`}>
                  {formatCurrency(scenario.impact.new_portfolio_value)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Statistics */}
      {scenarios.length > 0 && (
        <div className={`mt-6 p-4 rounded-lg ${
          theme === 'dark' ? 'bg-slate-700/50' : 'bg-gray-50'
        }`}>
          <h3 className={`text-sm font-semibold mb-3 ${
            theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
          }`}>
            Summary
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <div className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
                Worst Case
              </div>
              <div className={`font-semibold mt-1 ${
                theme === 'dark' ? 'text-red-400' : 'text-red-600'
              }`}>
                {formatPercentage(Math.min(...scenarios.map(s => s.impact.percentage_impact)))}
              </div>
            </div>
            <div>
              <div className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
                Best Case
              </div>
              <div className={`font-semibold mt-1 ${
                theme === 'dark' ? 'text-green-400' : 'text-green-600'
              }`}>
                {formatPercentage(Math.max(...scenarios.map(s => s.impact.percentage_impact)))}
              </div>
            </div>
            <div>
              <div className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
                Average Impact
              </div>
              <div className={`font-semibold mt-1 ${
                theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
              }`}>
                {formatPercentage(
                  scenarios.reduce((sum, s) => sum + s.impact.percentage_impact, 0) / scenarios.length
                )}
              </div>
            </div>
            <div>
              <div className={theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}>
                Scenarios Tested
              </div>
              <div className={`font-semibold mt-1 ${
                theme === 'dark' ? 'text-slate-200' : 'text-gray-800'
              }`}>
                {scenarios.length}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
