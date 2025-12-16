'use client'

import React from 'react'
import { formatPercentage, getColorForValue } from './MetricCard'

interface BenchmarkData {
  m1: number | null
  m3: number | null
  ytd: number | null
  y1: number | null
  daily?: number | null
}

interface BenchmarkMetricGroupProps {
  label: string
  data: BenchmarkData | null
}

export function BenchmarkMetricGroup({ label, data }: BenchmarkMetricGroupProps) {
  const periods = [
    { key: 'm1' as const, label: '1M' },
    { key: 'm3' as const, label: '3M' },
    { key: 'ytd' as const, label: 'YTD' },
    { key: 'y1' as const, label: '1Y' },
  ]

  return (
    <div className="themed-border-r p-3 transition-all duration-200 bg-secondary hover:bg-tertiary">
      {/* Label */}
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-secondary">
        {label}
      </div>

      {/* Values Grid */}
      <div className="grid grid-cols-4 gap-1">
        {periods.map((period) => {
          const value = data ? data[period.key] : null
          const colorClass =
            value === null
              ? 'text-secondary'
              : value > 0
                ? 'text-emerald-400'
                : value < 0
                  ? 'text-red-400'
                  : 'text-accent'

          return (
            <div key={period.key} className="text-center">
              <div className="text-[9px] font-medium uppercase text-tertiary mb-0.5">
                {period.label}
              </div>
              <div className={`text-sm font-bold tabular-nums ${colorClass}`}>
                {value !== null ? `${value >= 0 ? '+' : ''}${value.toFixed(1)}%` : '--'}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface VolatilityGroupData {
  y1: number | null
  d90: number | null
  forward: number | null
}

interface VolatilityMetricGroupProps {
  label: string
  data: VolatilityGroupData | null
}

export function VolatilityMetricGroup({ label, data }: VolatilityMetricGroupProps) {
  const periods = [
    { key: 'y1' as const, label: '1Y' },
    { key: 'd90' as const, label: '90D' },
    { key: 'forward' as const, label: 'Fwd' },
  ]

  return (
    <div className="themed-border-r p-3 transition-all duration-200 bg-secondary hover:bg-tertiary">
      {/* Label */}
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-secondary">
        {label}
      </div>

      {/* Values Grid */}
      <div className="grid grid-cols-3 gap-2">
        {periods.map((period) => {
          const value = data ? data[period.key] : null

          return (
            <div key={period.key} className="text-center">
              <div className="text-[9px] font-medium uppercase text-tertiary mb-0.5">
                {period.label}
              </div>
              <div className="text-lg font-bold tabular-nums text-accent">
                {value !== null ? `${value.toFixed(1)}%` : '--'}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
