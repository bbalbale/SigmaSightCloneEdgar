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
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <section className="px-4 py-12">
          <div className="container mx-auto">
            <div className={`rounded-lg border p-8 text-center transition-colors duration-300 ${
              theme === 'dark'
                ? 'bg-slate-900 border-slate-700'
                : 'bg-white border-slate-200'
            }`}>
              <h2 className={`text-xl font-semibold mb-2 ${
                theme === 'dark' ? 'text-slate-50' : 'text-slate-900'
              }`}>
                Error Loading Data
              </h2>
              <p className={`text-sm ${
                theme === 'dark' ? 'text-slate-400' : 'text-slate-600'
              }`}>
                {error}
              </p>
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Page Header */}
      <section className={`px-4 py-8 border-b transition-colors duration-300 ${
        theme === 'dark' ? 'border-slate-700' : 'border-slate-200'
      }`}>
        <div className="container mx-auto">
          <div className="flex items-start justify-between">
            <div>
              <h1 className={`text-3xl font-bold ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                Command Center
              </h1>
              <p className={`mt-2 text-lg ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>
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
