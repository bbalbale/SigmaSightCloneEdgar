'use client'

import React from 'react'
import { Position } from '@/stores/researchStore'
import { usePositionCorrelations, getCorrelationStrength } from '@/hooks/usePositionCorrelations'
import { AlertCircle } from 'lucide-react'

export interface CorrelationsSectionProps {
  position: Position
  theme?: 'dark' | 'light' // Make optional since we're not using it
}

export function CorrelationsSection({ position }: CorrelationsSectionProps) {
  const {
    correlations,
    hasConcentrationRisk,
    riskMessage,
    loading,
    error
  } = usePositionCorrelations(position.symbol)

  if (loading) {
    return (
      <p className="transition-colors duration-300" style={{
        fontSize: 'var(--text-sm)',
        color: 'var(--text-tertiary)'
      }}>
        Loading correlations...
      </p>
    )
  }

  if (error) {
    return (
      <p className="transition-colors duration-300" style={{
        fontSize: 'var(--text-sm)',
        color: 'var(--color-error)'
      }}>
        {error}
      </p>
    )
  }

  if (correlations.length === 0) {
    return (
      <p className="transition-colors duration-300" style={{
        fontSize: 'var(--text-sm)',
        color: 'var(--text-tertiary)'
      }}>
        No correlation data available
      </p>
    )
  }

  return (
    <div className="space-y-4">
      {/* Risk Warning */}
      {hasConcentrationRisk && riskMessage && (
        <div className="flex items-start gap-2 p-3 rounded border transition-colors duration-300" style={{
          backgroundColor: 'rgba(249, 115, 22, 0.1)',
          borderColor: 'rgba(249, 115, 22, 0.2)'
        }}>
          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" style={{
            color: 'rgb(249, 115, 22)'
          }} />
          <p className="transition-colors duration-300" style={{
            fontSize: 'var(--text-xs)',
            color: 'rgb(249, 115, 22)'
          }}>
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
              <span className="transition-colors duration-300" style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-secondary)'
              }}>
                {corr.symbol}:
              </span>
              <span className="font-medium transition-colors duration-300" style={{
                fontSize: 'var(--text-sm)',
                color: 'var(--text-primary)'
              }}>
                {corr.correlation.toFixed(2)} {showStrength && <span className="transition-colors duration-300" style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-tertiary)'
                }}>({strength})</span>}
              </span>
            </div>
          )
        })}
      </div>

    </div>
  )
}
