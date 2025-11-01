'use client'

import React from 'react'
import { Position } from '@/stores/researchStore'
import { usePositionCorrelations, getCorrelationStrength } from '@/hooks/usePositionCorrelations'
import { AlertCircle } from 'lucide-react'

export interface CorrelationsSectionProps {
  position: Position
  theme: 'dark' | 'light'
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
      <p className={`text-sm ${theme === 'dark' ? 'text-tertiary' : 'text-slate-600'}`}>
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
      <p className={`text-sm ${theme === 'dark' ? 'text-tertiary' : 'text-slate-600'}`}>
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

      {/* Correlation List - Simplified to match spec */}
      <div className="space-y-2">
        {correlations.map((corr) => {
          const strength = getCorrelationStrength(corr.correlation)
          const showStrength = Math.abs(corr.correlation) > 0.7 // Only show strength label for high correlations

          return (
            <div
              key={corr.symbol}
              className="flex items-center justify-between"
            >
              <span className={`text-sm ${theme === 'dark' ? 'text-primary' : 'text-slate-700'}`}>
                {corr.symbol}:
              </span>
              <span className={`text-sm font-medium ${theme === 'dark' ? 'text-slate-200' : 'text-slate-900'}`}>
                {corr.correlation.toFixed(2)} {showStrength && <span className={`text-xs ${theme === 'dark' ? 'text-tertiary' : 'text-slate-600'}`}>({strength})</span>}
              </span>
            </div>
          )
        })}
      </div>

    </div>
  )
}
