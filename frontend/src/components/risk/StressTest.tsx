"use client"

import React from 'react'
import type { StressTestResponse, StressTestScenario } from '@/types/analytics'

interface StressTestProps {
  data: StressTestResponse | null
  loading: boolean
  error: Error | null
  onRetry?: () => void
}

export function StressTest({ data, loading, error, onRetry }: StressTestProps) {
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

  // Get color based on impact severity - using Tailwind classes
  const getImpactColor = (percentage: number): string => {
    if (percentage >= 0) return 'text-green-400'
    if (percentage > -5) return 'text-yellow-400'
    if (percentage > -10) return 'text-orange-400'
    return 'text-red-400'
  }

  const getSeverityBadge = (severity?: string) => {
    if (!severity) return null

    const colors: Record<string, string> = {
      low: 'bg-green-900/30 text-green-300',
      medium: 'bg-yellow-900/30 text-yellow-300',
      high: 'bg-orange-900/30 text-orange-300',
      severe: 'bg-red-900/30 text-red-300',
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
      <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
        <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Stress Test Scenarios
        </h2>
        <div className="flex items-center justify-center py-12">
          <div className="text-center text-secondary">
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
      <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
        <h2 className="text-2xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Stress Test Scenarios
        </h2>
        <div className="rounded-lg border p-6 text-center bg-red-900/20 border-red-800 text-red-300">
          <p className="mb-4">Error loading stress test: {error.message}</p>
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
          Stress Test Scenarios
        </h2>
        <div className="rounded-lg border p-6 text-center transition-colors duration-300" style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
          color: 'var(--text-primary)'
        }}>
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
    <div className="rounded-lg border p-8 transition-colors duration-300 themed-card">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold mb-2 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Stress Test Scenarios
        </h2>
        <div className="flex flex-wrap gap-4 text-sm text-secondary">
          <span>
            Portfolio Value: <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
              {formatCurrency(portfolio_value)}
            </strong>
          </span>
          <span>
            Scenarios: <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
              {scenarios.length}
            </strong>
          </span>
          <span>
            Date: <strong className="transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
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
            className="rounded-lg border p-4 transition-colors duration-300 hover:opacity-80"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border-primary)'
            }}
          >
            {/* Scenario Header */}
            <div className="mb-3">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-sm transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  {scenario.name}
                </h3>
                {getSeverityBadge(scenario.severity)}
              </div>
              {scenario.description && (
                <p className="text-xs text-secondary">
                  {scenario.description}
                </p>
              )}
              {scenario.category && (
                <div className="mt-2 text-xs text-tertiary">
                  Category: {scenario.category}
                </div>
              )}
            </div>

            {/* Impact Metrics */}
            <div className="space-y-2 pt-3 border-t transition-colors duration-300" style={{ borderColor: 'var(--border-primary)' }}>
              <div className="flex justify-between items-center">
                <span className="text-xs text-secondary">
                  Dollar Impact
                </span>
                <span className={`text-sm font-semibold ${getImpactColor(scenario.impact.percentage_impact)}`}>
                  {formatCurrency(scenario.impact.dollar_impact)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-secondary">
                  % Impact
                </span>
                <span className={`text-sm font-semibold ${getImpactColor(scenario.impact.percentage_impact)}`}>
                  {formatPercentage(scenario.impact.percentage_impact)}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-secondary">
                  New Value
                </span>
                <span className="text-sm font-semibold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                  {formatCurrency(scenario.impact.new_portfolio_value)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Summary Statistics */}
      {scenarios.length > 0 && (
        <div className="mt-6 p-4 rounded-lg transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
          <h3 className="text-sm font-semibold mb-3 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
            Summary
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <div className="text-secondary">
                Worst Case
              </div>
              <div className="font-semibold mt-1 text-red-400">
                {formatPercentage(Math.min(...scenarios.map(s => s.impact.percentage_impact)))}
              </div>
            </div>
            <div>
              <div className="text-secondary">
                Best Case
              </div>
              <div className="font-semibold mt-1 text-green-400">
                {formatPercentage(Math.max(...scenarios.map(s => s.impact.percentage_impact)))}
              </div>
            </div>
            <div>
              <div className="text-secondary">
                Average Impact
              </div>
              <div className="font-semibold mt-1 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                {formatPercentage(
                  scenarios.reduce((sum, s) => sum + s.impact.percentage_impact, 0) / scenarios.length
                )}
              </div>
            </div>
            <div>
              <div className="text-secondary">
                Scenarios Tested
              </div>
              <div className="font-semibold mt-1 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
                {scenarios.length}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
