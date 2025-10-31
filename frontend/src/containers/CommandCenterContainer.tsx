'use client'

import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { useCommandCenterData } from '@/hooks/useCommandCenterData'
import { HeroMetricsRow } from '@/components/command-center/HeroMetricsRow'
import { HoldingsTable } from '@/components/command-center/HoldingsTable'
import { RiskMetricsRow } from '@/components/command-center/RiskMetricsRow'
import { AIInsightsButton } from '@/components/command-center/AIInsightsButton'

export function CommandCenterContainer() {
  const { theme } = useTheme()
  const { heroMetrics, holdings, riskMetrics, loading, error } = useCommandCenterData()

  if (error && !loading) {
    return (
      <div className="min-h-screen transition-colors duration-300 bg-primary">
        <section className="px-4 py-12">
          <div className="container mx-auto">
            <div className="themed-card text-center transition-colors duration-300">
              <h2 className="text-xl font-semibold mb-2 text-primary">
                Error Loading Data
              </h2>
              <p className="text-sm text-secondary">
                {error}
              </p>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="min-h-screen transition-colors duration-300 bg-primary">
      {/* Page Header */}
      <section className="px-4 py-8 themed-border-b transition-colors duration-300">
        <div className="container mx-auto">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-primary">
                Command Center
              </h1>
              <p className="mt-2 text-lg text-secondary">
                Portfolio overview, holdings, and risk metrics
              </p>
            </div>
            <AIInsightsButton />
          </div>
        </div>
      </section>

      {/* Hero Metrics - 6 cards */}
      <section className="pt-8">
        <HeroMetricsRow metrics={heroMetrics} loading={loading} />
      </section>

      {/* Holdings Table - 11 columns */}
      <HoldingsTable holdings={holdings} loading={loading} />

      {/* Risk Metrics - 5 cards */}
      <RiskMetricsRow metrics={riskMetrics} loading={loading} />
    </div>
  )
}
