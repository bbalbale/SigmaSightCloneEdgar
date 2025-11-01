'use client'

import React from 'react'

interface HeroMetricsRowProps {
  metrics: {
    equityBalance: number
    targetReturnEOY: number
    grossExposure: number
    netExposure: number
    longExposure: number
    shortExposure: number
  }
  loading: boolean
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(0)}`
}

function formatPercentage(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}

interface MetricCardProps {
  label: string
  value: string
  subValue: string
  valueColor?: 'positive' | 'negative' | 'neutral'
}

function MetricCard({ label, value, subValue, valueColor = 'neutral' }: MetricCardProps) {
  const getValueColor = () => {
    if (valueColor === 'positive') {
      return 'text-emerald-400'
    }
    if (valueColor === 'negative') {
      return 'text-red-400'
    }
    return 'text-accent'
  }

  return (
    <div className="themed-border-r p-3 transition-all duration-200 bg-secondary hover:bg-tertiary">
      {/* Label */}
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-tertiary">
        {label}
      </div>

      {/* Primary Value */}
      <div className={`text-2xl font-bold tabular-nums mb-0.5 ${getValueColor()}`}>
        {value}
      </div>

      {/* Secondary Context */}
      <div className="text-xs font-medium tabular-nums text-tertiary">
        {subValue}
      </div>
    </div>
  )
}

function LoadingCard() {
  return (
    <div className="themed-card p-4 animate-pulse transition-colors duration-300">
      <div className="h-3 rounded w-24 mb-2 bg-tertiary"></div>
      <div className="h-8 rounded w-32 mb-1 bg-tertiary"></div>
      <div className="h-4 rounded w-20 bg-tertiary"></div>
    </div>
  )
}

export function HeroMetricsRow({ metrics, loading }: HeroMetricsRowProps) {
  if (loading) {
    return (
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[...Array(6)].map((_, i) => (
              <LoadingCard key={i} />
            ))}
          </div>
        </div>
      </section>
    )
  }

  // Calculate NAV percentages (assuming equity balance is NAV)
  const nav = metrics.equityBalance
  const grossPct = nav > 0 ? (metrics.grossExposure / nav) * 100 : 0
  const netPct = nav > 0 ? (metrics.netExposure / nav) * 100 : 0
  const longPct = nav > 0 ? (metrics.longExposure / nav) * 100 : 0
  const shortPct = nav > 0 ? (Math.abs(metrics.shortExposure) / nav) * 100 : 0

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        <div className="themed-border overflow-hidden bg-secondary">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6">
            {/* Equity Balance */}
            <MetricCard
              label="Equity Balance"
              value={formatCurrency(metrics.equityBalance)}
              subValue="Total Value"
              valueColor="neutral"
            />

            {/* Target Return */}
            <MetricCard
              label="Target Return EOY"
              value={formatPercentage(metrics.targetReturnEOY)}
              subValue="Weighted Avg"
              valueColor={metrics.targetReturnEOY >= 0 ? 'positive' : 'negative'}
            />

            {/* Gross Exposure */}
            <MetricCard
              label="Gross Exposure"
              value={formatCurrency(metrics.grossExposure)}
              subValue={`${grossPct.toFixed(0)}% NAV`}
              valueColor="neutral"
            />

            {/* Net Exposure */}
            <MetricCard
              label="Net Exposure"
              value={formatCurrency(metrics.netExposure)}
              subValue={`${netPct >= 0 ? '+' : ''}${netPct.toFixed(0)}% NAV`}
              valueColor={metrics.netExposure >= 0 ? 'positive' : 'negative'}
            />

            {/* Long Exposure */}
            <MetricCard
              label="Long Exposure"
              value={formatCurrency(metrics.longExposure)}
              subValue={`${longPct.toFixed(0)}% NAV`}
              valueColor="neutral"
            />

            {/* Short Exposure */}
            <MetricCard
              label="Short Exposure"
              value={metrics.shortExposure < 0 ? `(${formatCurrency(Math.abs(metrics.shortExposure))})` : formatCurrency(metrics.shortExposure)}
              subValue={`${shortPct.toFixed(0)}% NAV`}
              valueColor="neutral"
            />
          </div>
        </div>
      </div>
    </section>
  )
}
