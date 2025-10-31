'use client'

import React from 'react'
import { Position } from '@/stores/researchStore'
import { usePositionCorrelations, getCorrelationStrength } from '@/hooks/usePositionCorrelations'
import { AlertCircle } from 'lucide-react'

export interface CorrelationsSectionProps {
  position: Position
  theme: 'dark' | 'light'
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(2)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(2)}`
}

function getCorrelationColor(correlation: number, theme: 'dark' | 'light'): string {
  const abs = Math.abs(correlation)
  if (abs > 0.85) {
    return theme === 'dark' ? 'text-red-400' : 'text-red-600'
  }
  if (abs > 0.7) {
    return theme === 'dark' ? 'text-orange-400' : 'text-orange-600'
  }
  if (abs > 0.5) {
    return theme === 'dark' ? 'text-yellow-400' : 'text-yellow-600'
  }
  return theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
}

export function CorrelationsSection({ position, theme }: CorrelationsSectionProps) {
  const {
    correlations,
    hasConcentrationRisk,
    riskMessage,
    loading,
    error
  } = usePositionCorrelations(position.symbol)

  if (loading) {
    return (
      <p className={`text-sm ${theme === 'dark' ? 'text-slate-500' : 'text-slate-600'}`}>
        Loading correlations...
      </p>
    )
  }

  if (error) {
    return (
      <p className={`text-sm ${theme === 'dark' ? 'text-red-400' : 'text-red-600'}`}>
        {error}
      </p>
    )
  }

  if (correlations.length === 0) {
    return (
      <p className={`text-sm ${theme === 'dark' ? 'text-slate-500' : 'text-slate-600'}`}>
        No correlation data available
      </p>
    )
  }

  return (
    <div className="space-y-4">
      {/* Risk Warning */}
      {hasConcentrationRisk && riskMessage && (
        <div className={`flex items-start gap-2 p-3 rounded ${
          theme === 'dark' ? 'bg-orange-500/10 border border-orange-500/20' : 'bg-orange-50 border border-orange-200'
        }`}>
          <AlertCircle className={`h-4 w-4 mt-0.5 flex-shrink-0 ${
            theme === 'dark' ? 'text-orange-400' : 'text-orange-600'
          }`} />
          <p className={`text-xs ${theme === 'dark' ? 'text-orange-300' : 'text-orange-800'}`}>
            {riskMessage}
          </p>
        </div>
      )}

      {/* Correlation List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between mb-2">
          <span className={`text-[10px] font-semibold uppercase tracking-wider ${theme === 'dark' ? 'text-slate-500' : 'text-slate-600'}`}>
            TOP 5 CORRELATIONS
          </span>
        </div>

        {correlations.map((corr, index) => {
          const correlationColor = getCorrelationColor(corr.correlation, theme)
          const strength = getCorrelationStrength(corr.correlation)
          const isPositive = corr.correlation >= 0

          return (
            <div
              key={corr.symbol}
              className={`flex items-center justify-between p-2 rounded ${
                theme === 'dark' ? 'bg-slate-800/50' : 'bg-slate-50'
              }`}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-medium ${theme === 'dark' ? 'text-slate-200' : 'text-slate-900'}`}>
                    {index + 1}. {corr.symbol}
                  </span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                    theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {strength}
                  </span>
                </div>
                <span className={`text-xs ${theme === 'dark' ? 'text-slate-500' : 'text-slate-600'}`}>
                  {formatCurrency(corr.marketValue)}
                </span>
              </div>

              <div className="text-right">
                <div className={`text-sm font-bold tabular-nums ${correlationColor}`}>
                  {isPositive ? '+' : ''}{(corr.correlation * 100).toFixed(1)}%
                </div>
                <div className={`text-[10px] ${theme === 'dark' ? 'text-slate-600' : 'text-slate-500'}`}>
                  correlation
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Interpretation Guide */}
      <div className={`text-xs p-2 rounded ${
        theme === 'dark' ? 'bg-slate-800/30 text-slate-500' : 'bg-slate-50 text-slate-600'
      }`}>
        <p className="font-medium mb-1">Correlation Guide:</p>
        <p>+100% = Perfect positive correlation (moves together)</p>
        <p>0% = No correlation</p>
        <p>-100% = Perfect negative correlation (moves opposite)</p>
      </div>
    </div>
  )
}
