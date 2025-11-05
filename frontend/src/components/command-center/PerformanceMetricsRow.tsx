'use client'

import React from 'react'

interface PerformanceMetricsRowProps {
  metrics: {
    ytdPnl: number
    mtdPnl: number
    cashBalance: number
    portfolioBeta90d: number | null
    portfolioBeta1y: number | null
    stressTest: { up: number; down: number } | null
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
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-secondary">
        {label}
      </div>

      {/* Primary Value */}
      <div className={`text-2xl font-bold tabular-nums mb-0.5 ${getValueColor()}`}>
        {value}
      </div>

      {/* Secondary Context */}
      <div className="text-xs font-medium tabular-nums text-secondary">
        {subValue}
      </div>
    </div>
  )
}

interface BetaCardProps {
  label: string
  beta90d: number | null
  beta1y: number | null
}

function BetaCard({ label, beta90d, beta1y }: BetaCardProps) {
  return (
    <div className="themed-border-r p-3 transition-all duration-200 bg-secondary hover:bg-tertiary">
      {/* Label */}
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-secondary">
        {label}
      </div>

      {beta1y !== null || beta90d !== null ? (
        <div className="space-y-1">
          <div className="flex items-baseline gap-3">
            <div className="flex flex-col">
              <span className="text-2xl font-bold tabular-nums text-accent leading-tight">
                {beta1y !== null ? beta1y.toFixed(2) : '—'}
              </span>
              <span className="text-[11px] uppercase text-secondary tracking-wide">
                1 Year
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-bold tabular-nums text-primary leading-tight">
                {beta90d !== null ? beta90d.toFixed(2) : '—'}
              </span>
              <span className="text-[11px] uppercase text-secondary tracking-wide">
                90 Days
              </span>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="text-2xl font-bold tabular-nums mb-0.5 text-accent">
            —
          </div>
          <div className="text-xs font-medium text-secondary">
            N/A
          </div>
        </>
      )}
    </div>
  )
}

interface StressTestCardProps {
  label: string
  stressTest: { up: number; down: number } | null
}

function StressTestCard({ label, stressTest }: StressTestCardProps) {
  return (
    <div className="themed-border-r p-3 transition-all duration-200 bg-secondary hover:bg-tertiary">
      {/* Label */}
      <div className="text-[10px] font-semibold uppercase tracking-wider mb-1.5 text-secondary">
        {label}
      </div>

      <div className="text-xs font-medium mb-1 text-secondary">
        ±1% Market:
      </div>

      {stressTest ? (
        <div className="flex items-baseline gap-1.5">
          <span className="text-lg font-bold tabular-nums text-emerald-400">
            {formatCurrency(stressTest.up)}
          </span>
          <span className="text-xs text-secondary">
            /
          </span>
          <span className="text-lg font-bold tabular-nums text-red-400">
            {formatCurrency(stressTest.down)}
          </span>
        </div>
      ) : (
        <div className="text-xs font-medium text-secondary">
          No data
        </div>
      )}
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

export function PerformanceMetricsRow({ metrics, loading }: PerformanceMetricsRowProps) {
  if (loading) {
    return (
      <section className="px-4 pb-4">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <LoadingCard key={i} />
            ))}
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        <div className="themed-border overflow-hidden bg-secondary">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5">
            {/* YTD P&L */}
            <MetricCard
              label="YTD P&L"
              value={formatCurrency(metrics.ytdPnl)}
              subValue="Year to Date"
              valueColor={metrics.ytdPnl >= 0 ? 'positive' : 'negative'}
            />

            {/* MTD P&L */}
            <MetricCard
              label="MTD P&L"
              value={formatCurrency(metrics.mtdPnl)}
              subValue="Month to Date"
              valueColor={metrics.mtdPnl >= 0 ? 'positive' : 'negative'}
            />

            {/* Cash/Margin */}
            <MetricCard
              label="Uninvested Cash/Margin"
              value={formatCurrency(metrics.cashBalance)}
              subValue={metrics.cashBalance >= 0 ? 'Available' : 'Margin Used'}
              valueColor={metrics.cashBalance >= 0 ? 'neutral' : 'negative'}
            />

            {/* Portfolio Beta */}
            <BetaCard
              label="Portfolio Beta"
              beta90d={metrics.portfolioBeta90d}
              beta1y={metrics.portfolioBeta1y}
            />

            {/* Stress Test */}
            <StressTestCard
              label="Stress Test"
              stressTest={metrics.stressTest}
            />
          </div>
        </div>
      </div>
    </section>
  )
}
