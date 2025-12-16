'use client'

import React from 'react'
import { MetricCard, formatPercentage, getColorForValue } from './MetricCard'
import { BenchmarkMetricGroup } from './BenchmarkMetricGroup'
import type { ReturnsData } from '@/hooks/useHomePageData'

interface ReturnsRowProps {
  returns: ReturnsData
}

export function ReturnsRow({ returns }: ReturnsRowProps) {
  return (
    <div className="themed-border overflow-hidden bg-secondary">
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5">
        {/* Target Return EOY */}
        <MetricCard
          label="Target Return EOY"
          value={formatPercentage(returns.portfolio.targetReturnEOY)}
          subValue="Weighted Avg"
          valueColor={getColorForValue(returns.portfolio.targetReturnEOY)}
        />

        {/* Target Return Next Year */}
        <MetricCard
          label="Target Return Next Year"
          value={formatPercentage(returns.portfolio.targetReturnNextYear)}
          subValue="Weighted Avg"
          valueColor={getColorForValue(returns.portfolio.targetReturnNextYear)}
        />

        {/* SPY Returns */}
        <BenchmarkMetricGroup
          label="SPY Returns"
          data={returns.benchmarks.SPY}
        />

        {/* QQQ Returns */}
        <BenchmarkMetricGroup
          label="QQQ Returns"
          data={returns.benchmarks.QQQ}
        />

        {/* AI Insight Placeholder */}
        <div className="themed-border-r p-3 transition-all duration-200 bg-tertiary flex items-center justify-center">
          <div className="text-center">
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-1 text-secondary">
              AI Insight
            </div>
            <div className="text-xs text-secondary">Coming soon</div>
          </div>
        </div>
      </div>
    </div>
  )
}
