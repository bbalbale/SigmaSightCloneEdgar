'use client'

import React from 'react'

export interface MetricCardProps {
  label: string
  value: string
  subValue?: string
  valueColor?: 'positive' | 'negative' | 'neutral'
  size?: 'default' | 'large'
}

function getValueColor(valueColor: MetricCardProps['valueColor']): string {
  if (valueColor === 'positive') {
    return 'text-emerald-400'
  }
  if (valueColor === 'negative') {
    return 'text-red-400'
  }
  return 'text-accent'
}

export function MetricCard({
  label,
  value,
  subValue,
  valueColor = 'neutral',
  size = 'default',
}: MetricCardProps) {
  const valueSize = size === 'large' ? 'text-3xl' : 'text-2xl'

  return (
    <div className="themed-border-r p-3 transition-all duration-200 bg-secondary hover:bg-tertiary">
      {/* Label */}
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-secondary">
        {label}
      </div>

      {/* Primary Value */}
      <div className={`${valueSize} font-bold tabular-nums mb-0.5 ${getValueColor(valueColor)}`}>
        {value}
      </div>

      {/* Secondary Context */}
      {subValue && (
        <div className="text-xs font-medium tabular-nums text-secondary">{subValue}</div>
      )}
    </div>
  )
}

export function LoadingCard() {
  return (
    <div className="themed-card p-4 animate-pulse transition-colors duration-300">
      <div className="h-3 rounded w-24 mb-2 bg-tertiary"></div>
      <div className="h-8 rounded w-32 mb-1 bg-tertiary"></div>
      <div className="h-4 rounded w-20 bg-tertiary"></div>
    </div>
  )
}

// Utility formatters
export function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(0)}`
}

export function formatPercentage(value: number | null): string {
  if (value === null || value === undefined) return '--'
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}

export function formatVolatility(value: number | null): string {
  if (value === null || value === undefined) return '--'
  return `${value.toFixed(1)}%`
}

export function getColorForValue(value: number | null): 'positive' | 'negative' | 'neutral' {
  if (value === null) return 'neutral'
  if (value > 0) return 'positive'
  if (value < 0) return 'negative'
  return 'neutral'
}
