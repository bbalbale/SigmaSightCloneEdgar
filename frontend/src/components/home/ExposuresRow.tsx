'use client'

import React from 'react'
import { MetricCard, formatCurrency, getColorForValue } from './MetricCard'
import type { ExposuresData } from '@/hooks/useHomePageData'

interface ExposuresRowProps {
  exposures: ExposuresData
}

export function ExposuresRow({ exposures }: ExposuresRowProps) {
  return (
    <div className="themed-border overflow-hidden bg-secondary">
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6">
        {/* Equity Balance */}
        <MetricCard
          label="Equity Balance"
          value={formatCurrency(exposures.equityBalance)}
          subValue="Total Value"
          valueColor="neutral"
        />

        {/* Long Exposure */}
        <MetricCard
          label="Long Exposure"
          value={formatCurrency(exposures.longExposure)}
          subValue={`${exposures.longPct.toFixed(0)}% NAV`}
          valueColor="neutral"
        />

        {/* Short Exposure */}
        <MetricCard
          label="Short Exposure"
          value={
            exposures.shortExposure < 0
              ? `(${formatCurrency(Math.abs(exposures.shortExposure))})`
              : formatCurrency(exposures.shortExposure)
          }
          subValue={`${exposures.shortPct.toFixed(0)}% NAV`}
          valueColor="neutral"
        />

        {/* Gross Exposure */}
        <MetricCard
          label="Gross Exposure"
          value={formatCurrency(exposures.grossExposure)}
          subValue={`${exposures.grossPct.toFixed(0)}% NAV`}
          valueColor="neutral"
        />

        {/* Net Exposure */}
        <MetricCard
          label="Net Exposure"
          value={formatCurrency(exposures.netExposure)}
          subValue={`${exposures.netPct >= 0 ? '+' : ''}${exposures.netPct.toFixed(0)}% NAV`}
          valueColor={getColorForValue(exposures.netExposure)}
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
