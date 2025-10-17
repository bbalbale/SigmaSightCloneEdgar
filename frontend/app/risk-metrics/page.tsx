"use client"

import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { useCorrelationMatrix } from '@/hooks/useCorrelationMatrix'
import { useDiversificationScore } from '@/hooks/useDiversificationScore'
import { useStressTest } from '@/hooks/useStressTest'
import { useVolatility } from '@/hooks/useVolatility'
import { CorrelationMatrix } from '@/components/risk/CorrelationMatrix'
import { DiversificationScore } from '@/components/risk/DiversificationScore'
import { StressTest } from '@/components/risk/StressTest'
import { VolatilityMetrics } from '@/components/risk/VolatilityMetrics'

function RiskMetricsPageContent() {
  const { theme } = useTheme()

  // Fetch all risk metrics data
  const correlationMatrix = useCorrelationMatrix()
  const diversificationScore = useDiversificationScore()
  const stressTest = useStressTest()
  const volatility = useVolatility()

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Page Header */}
      <section className="px-4 py-8 border-b transition-colors duration-300"
        style={{
          borderColor: theme === 'dark' ? 'rgb(51 65 85)' : 'rgb(229 231 235)'
        }}
      >
        <div className="container mx-auto">
          <h1 className={`text-3xl font-bold ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>
            Risk Metrics
          </h1>
          <p className={`mt-2 text-lg ${
            theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
          }`}>
            Portfolio risk analysis and diversification metrics
          </p>
        </div>
      </section>

      {/* Volatility Analysis Section */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <VolatilityMetrics
            data={volatility.data}
            loading={volatility.loading}
            error={volatility.error}
            onRetry={volatility.refetch}
          />
        </div>
      </section>

      {/* Diversification Score Section */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <DiversificationScore
            data={diversificationScore.data}
            loading={diversificationScore.loading}
            error={diversificationScore.error}
            onRetry={diversificationScore.refetch}
          />
        </div>
      </section>

      {/* Correlation Matrix Section */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <CorrelationMatrix
            data={correlationMatrix.data}
            loading={correlationMatrix.loading}
            error={correlationMatrix.error}
            onRetry={correlationMatrix.refetch}
          />
        </div>
      </section>

      {/* Stress Test Section */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <StressTest
            data={stressTest.data}
            loading={stressTest.loading}
            error={stressTest.error}
            onRetry={stressTest.refetch}
          />
        </div>
      </section>
    </div>
  )
}

export default function RiskMetrics() {
  return <RiskMetricsPageContent />
}
