'use client'

import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { useCorrelationMatrix } from '@/hooks/useCorrelationMatrix'
import { useDiversificationScore } from '@/hooks/useDiversificationScore'
import { useStressTest } from '@/hooks/useStressTest'
import { useVolatility } from '@/hooks/useVolatility'
import { useSectorExposure } from '@/hooks/useSectorExposure'
import { useConcentration } from '@/hooks/useConcentration'
import { CorrelationMatrix } from '@/components/risk/CorrelationMatrix'
import { DiversificationScore } from '@/components/risk/DiversificationScore'
import { StressTest } from '@/components/risk/StressTest'
import { VolatilityMetrics } from '@/components/risk/VolatilityMetrics'
import { MarketBetaComparison } from '@/components/risk-metrics/MarketBetaComparison'
import { SectorExposure } from '@/components/risk-metrics/SectorExposure'
import { ConcentrationMetrics } from '@/components/risk-metrics/ConcentrationMetrics'

/**
 * RiskMetricsContainer
 *
 * Container component for the Risk Metrics page.
 * Follows standard architecture: thin page → container → hooks → services
 *
 * Responsibilities:
 * - Fetch all risk metrics data via custom hooks
 * - Orchestrate layout and component composition
 * - Pass data down to presentation components
 *
 * All API calls go through:
 * hooks → analyticsApi service → apiClient → backend
 */
export function RiskMetricsContainer() {
  const { theme } = useTheme()

  // Fetch all risk metrics data via custom hooks
  // Each hook uses analyticsApi service (no direct fetch calls)
  const correlationMatrix = useCorrelationMatrix()
  const diversificationScore = useDiversificationScore()
  const stressTest = useStressTest()
  const volatility = useVolatility()
  const sectorExposure = useSectorExposure()
  const concentration = useConcentration()

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

      {/* Volatility Analysis Section - Phase 2 */}
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

      {/* Market Beta Comparison Section - Phase 0 */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <MarketBetaComparison />
        </div>
      </section>

      {/* Sector Exposure Section - Phase 1 */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <SectorExposure
            data={sectorExposure.data}
            loading={sectorExposure.loading}
            error={sectorExposure.error}
            onRetry={sectorExposure.refetch}
          />
        </div>
      </section>

      {/* Concentration Metrics Section - Phase 1 */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <ConcentrationMetrics
            data={concentration.data}
            loading={concentration.loading}
            error={concentration.error}
            onRetry={concentration.refetch}
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
