'use client'

import React from 'react'
import { useCorrelationMatrix } from '@/hooks/useCorrelationMatrix'
import { useStressTest } from '@/hooks/useStressTest'
import { useVolatility } from '@/hooks/useVolatility'
import { useSectorExposure } from '@/hooks/useSectorExposure'
import { useFactorExposures } from '@/hooks/useFactorExposures'
import { useSpreadFactors } from '@/hooks/useSpreadFactors'
import { CorrelationMatrix } from '@/components/risk/CorrelationMatrix'
import { StressTest } from '@/components/risk/StressTest'
import { VolatilityMetrics } from '@/components/risk/VolatilityMetrics'
import { MarketBetaComparison } from '@/components/risk-metrics/MarketBetaComparison'
import { SectorExposure } from '@/components/risk-metrics/SectorExposure'
import { FactorExposureHeroRow } from '@/components/risk-metrics/FactorExposureHeroRow'
import { SpreadFactorCards } from '@/components/portfolio/SpreadFactorCards'

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
  // Fetch all risk metrics data via custom hooks
  // Each hook uses analyticsApi service (no direct fetch calls)
  const factorExposures = useFactorExposures()
  const spreadFactors = useSpreadFactors()
  const correlationMatrix = useCorrelationMatrix()
  const stressTest = useStressTest()
  const volatility = useVolatility()
  const sectorExposure = useSectorExposure()

  const spreadErrorMessage = (() => {
    const { error } = spreadFactors
    if (!error) return null
    if (typeof error === 'string') return error
    if (error instanceof Error) return error.message
    if (typeof error === 'object' && 'message' in error) {
      return String((error as { message?: unknown }).message ?? 'Unable to load spread factors')
    }
    return 'Unable to load spread factors'
  })()

  const factorErrorMessage = factorExposures.error ?? factorExposures.reason ?? null

  return (
    <div className="min-h-screen transition-colors duration-300 bg-primary">
      {/* Page Description */}
      <div className="px-4 pt-4 pb-2">
        <div className="container mx-auto">
          <p className="text-sm text-muted-foreground">
            Portfolio risk analytics, scenario testing, and benchmark comparisons
          </p>
        </div>
      </div>

      {/* Hero Cards: Factor & Spread tilts */}
      <FactorExposureHeroRow
        factorExposures={factorExposures.factors}
        factorAvailable={factorExposures.available}
        factorLoading={factorExposures.loading}
        factorError={factorErrorMessage}
        factorCalculationDate={factorExposures.calculationDate}
        spreadFactors={spreadFactors.spreadFactors}
        spreadAvailable={spreadFactors.available}
        spreadLoading={spreadFactors.loading}
        spreadError={spreadErrorMessage}
        spreadCalculationDate={spreadFactors.calculationDate ?? null}
        onRefetchFactors={factorExposures.refetch}
        onRefetchSpreads={spreadFactors.refetch}
      />

      {/* Spread Factor Details */}
      <SpreadFactorCards
        factors={spreadFactors.spreadFactors}
        loading={spreadFactors.loading}
        error={spreadErrorMessage}
        calculationDate={spreadFactors.calculationDate ?? null}
      />

      {/* Stress Test Section */}
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <StressTest
            data={stressTest.data}
            loading={stressTest.loading}
            error={stressTest.error}
            onRetry={stressTest.refetch}
          />
        </div>
      </section>

      {/* Correlation Matrix Section */}
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <CorrelationMatrix
            data={correlationMatrix.data}
            loading={correlationMatrix.loading}
            error={correlationMatrix.error}
            onRetry={correlationMatrix.refetch}
          />
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

      {/* S&P Sector Allocation */}
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

      {/* Market Beta Comparison Section - relocated to bottom */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <MarketBetaComparison />
        </div>
      </section>
    </div>
  )
}
