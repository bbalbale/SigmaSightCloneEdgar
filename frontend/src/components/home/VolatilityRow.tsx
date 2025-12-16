'use client'

import React from 'react'
import { VolatilityMetricGroup } from './BenchmarkMetricGroup'
import type { VolatilityData } from '@/hooks/useHomePageData'

interface VolatilityRowProps {
  volatility: VolatilityData
}

export function VolatilityRow({ volatility }: VolatilityRowProps) {
  return (
    <div className="themed-border overflow-hidden bg-secondary">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
        {/* Portfolio Volatility */}
        <VolatilityMetricGroup label="Portfolio Volatility" data={volatility.portfolio} />

        {/* SPY Volatility */}
        <VolatilityMetricGroup label="SPY Volatility" data={volatility.SPY} />

        {/* QQQ Volatility */}
        <VolatilityMetricGroup label="QQQ Volatility" data={volatility.QQQ} />

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
