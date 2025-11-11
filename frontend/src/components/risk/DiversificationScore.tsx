"use client"

import React from 'react'
import type { DiversificationScoreResponse } from '@/types/analytics'

interface DiversificationScoreProps {
  data: DiversificationScoreResponse | null
  loading: boolean
  error: Error | null
  onRetry?: () => void
}

export function DiversificationScore({ data, loading, error, onRetry }: DiversificationScoreProps) {
  // Get color based on score (0-100) - using Tailwind classes for color coding
  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    if (score >= 40) return 'text-orange-400'
    return 'text-red-400'
  }

  const getScoreLabel = (score: number): string => {
    if (score >= 80) return 'Excellent'
    if (score >= 60) return 'Good'
    if (score >= 40) return 'Fair'
    return 'Needs Improvement'
  }

  // Loading state
  if (loading) {
    return (
      <div className="rounded-lg border p-6 transition-colors duration-300 themed-card">
        <h3 className="text-xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
          Diversification Score
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
          Diversification Score
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
          Diversification Score
        </h3>
        <div className="rounded-lg border p-4 text-center transition-colors duration-300" style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
          color: 'var(--text-primary)'
        }}>
          <p className="text-sm">Diversification score is not available</p>
          {data?.reason && (
            <p className="mt-2 text-xs opacity-70">Reason: {data.reason}</p>
          )}
        </div>
      </div>
    )
  }

  const { overall_score, category_scores, recommendations } = data.data

  return (
    <div className="rounded-lg border p-6 transition-colors duration-300 themed-card">
      <h3 className="text-xl font-bold mb-4 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
        Diversification Score
      </h3>

      {/* Overall Score Display */}
      <div className="text-center mb-6">
        <div className={`text-5xl font-bold mb-2 ${getScoreColor(overall_score)}`}>
          {overall_score.toFixed(0)}
        </div>
        <div className="text-lg font-medium text-primary">
          {getScoreLabel(overall_score)}
        </div>
        {data.metadata && (
          <div className="text-xs mt-2 text-tertiary">
            {data.metadata.position_count} positions analyzed
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 rounded-full mb-6 transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${overall_score}%`,
            backgroundColor: overall_score >= 80 ? '#10b981' : overall_score >= 60 ? '#f59e0b' : overall_score >= 40 ? '#f97316' : '#ef4444'
          }}
        />
      </div>

      {/* Category Scores */}
      <div className="space-y-3 mb-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-secondary">
            Asset Class
          </span>
          <span className="text-sm font-semibold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
            {category_scores.asset_class.toFixed(0)}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-secondary">
            Sector
          </span>
          <span className="text-sm font-semibold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
            {category_scores.sector.toFixed(0)}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-secondary">
            Geography
          </span>
          <span className="text-sm font-semibold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
            {category_scores.geography.toFixed(0)}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-secondary">
            Position Size
          </span>
          <span className="text-sm font-semibold transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
            {category_scores.position_size.toFixed(0)}
          </span>
        </div>
      </div>

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <div className="mt-4 p-4 rounded-lg transition-colors duration-300" style={{ backgroundColor: 'var(--bg-secondary)' }}>
          <h4 className="text-sm font-semibold mb-2 transition-colors duration-300" style={{ color: 'var(--text-primary)' }}>
            Recommendations
          </h4>
          <ul className="space-y-1 text-xs text-secondary">
            {recommendations.map((rec, index) => (
              <li key={index} className="flex items-start">
                <span className="mr-2">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metadata */}
      {data.metadata?.calculation_date && (
        <div className="mt-4 text-xs text-center text-tertiary">
          Updated: {new Date(data.metadata.calculation_date).toLocaleDateString()}
        </div>
      )}
    </div>
  )
}
