'use client'

import React from 'react'

export interface AggregateMetrics {
  totalValue: number
  totalPnl: number
  totalPnlPercent: number
  positionCount: number
}

export interface SummaryMetricsBarProps {
  metrics: AggregateMetrics
}

export function SummaryMetricsBar({ metrics }: SummaryMetricsBarProps) {
  return (
    <div className="py-2 text-sm text-slate-400">
      <span className="font-semibold">{metrics.positionCount}</span> positions
      {' | '}
      <span className="font-semibold tabular-nums">
        ${metrics.totalValue.toLocaleString()}
      </span> total
      {' | '}
      <span className={`font-semibold tabular-nums ${
        metrics.totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'
      }`}>
        {metrics.totalPnl >= 0 ? '+' : ''}${metrics.totalPnl.toLocaleString()}
        {' '}({metrics.totalPnl >= 0 ? '+' : ''}{metrics.totalPnlPercent.toFixed(1)}%)
      </span>
    </div>
  )
}
