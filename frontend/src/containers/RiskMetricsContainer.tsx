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
import { FactorExposureCards } from '@/components/risk-metrics/FactorExposureCards'
import { AccountFilter } from '@/components/portfolio/AccountFilter'
import { usePortfolioStore, type PortfolioListItem } from '@/stores/portfolioStore'
import { AlertTriangle, Info, TrendingUp } from 'lucide-react'

/**
 * RiskMetricsContainer
 *
 * Container component for the Risk Metrics page.
 * Follows standard architecture: thin page → container → hooks → services
 *
 * Updated December 2025: True aggregate view support
 * - Default view is "All Accounts" with equity-weighted aggregate metrics
 * - Hooks automatically call aggregate endpoints when selectedPortfolioId is null
 * - Shows portfolio selector for switching between aggregate and individual portfolios
 * - Shows warning for private portfolios (no public market data)
 *
 * Responsibilities:
 * - Fetch all risk metrics data via custom hooks (hooks auto-detect aggregate mode)
 * - Orchestrate layout and component composition
 * - Pass data down to presentation components
 *
 * All API calls go through:
 * hooks → analyticsApi service → apiClient → backend
 */

export function RiskMetricsContainer() {
  // Get current portfolio info from store
  const portfolios = usePortfolioStore((state) => state.portfolios)
  const selectedPortfolioId = usePortfolioStore((state) => state.selectedPortfolioId)
  const portfolioId = usePortfolioStore((state) => state.portfolioId)

  // For aggregate view, filter to only active portfolios
  const activePortfolios = portfolios.filter((p) => p.is_active)

  // Separate public and private portfolios for aggregate view
  const publicPortfolios = activePortfolios.filter(
    (p) => !p.account_name?.toLowerCase().includes('private')
  )
  const privatePortfolios = activePortfolios.filter(
    (p) => p.account_name?.toLowerCase().includes('private')
  )

  const isMultiPortfolio = portfolios.length > 1
  const isAggregateView = selectedPortfolioId === null

  // Get current portfolio details
  const currentPortfolio = portfolios.find((p) => p.id === portfolioId)

  // Check if current portfolio is private (no public market analytics available)
  const isPrivatePortfolio = currentPortfolio?.account_name?.toLowerCase().includes('private') ?? false

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

  // Calculate total NAV for aggregate view
  const totalNAV = activePortfolios.reduce((sum, p) => sum + (p.net_asset_value ?? p.total_value ?? 0), 0)
  const totalPositions = activePortfolios.reduce((sum, p) => sum + (p.position_count ?? 0), 0)

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  // In aggregate view with multiple portfolios, show TRUE aggregate metrics (equity-weighted)
  if (isAggregateView && isMultiPortfolio) {
    return (
      <div className="min-h-screen transition-colors duration-300 bg-primary">
        {/* Page Description with Account Filter */}
        <div className="px-4 pt-4 pb-2">
          <div className="container mx-auto flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-4 flex-1">
              <p className="text-sm text-muted-foreground">
                Portfolio risk analytics, scenario testing, and benchmark comparisons
              </p>
              {/* Account Filter - Multi-Portfolio Feature */}
              <AccountFilter className="ml-auto" showForSinglePortfolio={false} />
            </div>
          </div>
        </div>

        {/* Aggregate View Header with Total NAV */}
        <div className="px-4 pb-4">
          <div className="container mx-auto">
            <div className="flex items-center gap-3">
              <TrendingUp className="h-6 w-6 text-emerald-500" />
              <div>
                <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                  All Accounts
                </h2>
                <p className="text-sm text-muted-foreground">
                  {formatCurrency(totalNAV)} across {activePortfolios.length} portfolios • {totalPositions} total positions
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Info Banner about Equity-Weighted Aggregate View */}
        <div className="px-4 pb-4">
          <div className="container mx-auto">
            <div className="flex items-center gap-3 p-4 rounded-lg border border-blue-500/30 bg-blue-500/10">
              <Info className="h-5 w-5 text-blue-500 flex-shrink-0" />
              <div>
                <p className="text-sm text-muted-foreground">
                  <span className="font-medium text-blue-600 dark:text-blue-400">Equity-Weighted Aggregate View</span>
                  {' — '}All risk metrics are calculated as weighted averages based on each portfolio&apos;s NAV.
                  {privatePortfolios.length > 0 && (
                    <> Note: {privatePortfolios.length} private portfolio{privatePortfolios.length !== 1 ? 's' : ''} excluded from public market analytics.</>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Show aggregate metrics (hooks automatically fetch aggregate data) */}
        <FactorExposureCards
          ridgeFactors={factorExposures.factors}
          spreadFactors={spreadFactors.spreadFactors}
          ridgeLoading={factorExposures.loading}
          spreadLoading={spreadFactors.loading}
          ridgeError={factorErrorMessage}
          spreadError={spreadErrorMessage}
          ridgeCalculationDate={factorExposures.calculationDate}
          spreadCalculationDate={spreadFactors.calculationDate ?? null}
          onRefetchRidge={factorExposures.refetch}
          onRefetchSpread={spreadFactors.refetch}
        />

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

        <section className="px-4 py-8">
          <div className="container mx-auto">
            <MarketBetaComparison />
          </div>
        </section>
      </div>
    )
  }

  // Single portfolio view (or single portfolio user)
  return (
    <div className="min-h-screen transition-colors duration-300 bg-primary">
      {/* Page Description with Account Filter */}
      <div className="px-4 pt-4 pb-2">
        <div className="container mx-auto flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4 flex-1">
            <p className="text-sm text-muted-foreground">
              Portfolio risk analytics, scenario testing, and benchmark comparisons
            </p>
            {/* Account Filter - Multi-Portfolio Feature */}
            <AccountFilter className="ml-auto" showForSinglePortfolio={false} />
          </div>
        </div>
      </div>

      {/* Portfolio Header - Shows which portfolio data is displayed */}
      {currentPortfolio && (
        <div className="px-4 pb-4">
          <div className="container mx-auto">
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              {currentPortfolio.account_name}
            </h2>
            <p className="text-sm text-muted-foreground">
              Portfolio-specific risk analytics and scenario testing
            </p>
          </div>
        </div>
      )}

      {/* Private Portfolio Warning */}
      {isPrivatePortfolio && (
        <div className="px-4 pb-4">
          <div className="container mx-auto">
            <div className="flex items-center gap-3 p-4 rounded-lg border border-yellow-500/30 bg-yellow-500/10">
              <AlertTriangle className="h-5 w-5 text-yellow-500 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                  Limited Analytics for Private Holdings
                </p>
                <p className="text-sm text-muted-foreground">
                  Risk metrics require public market data. Private investments don&apos;t have standard market analytics.
                  {isMultiPortfolio && ' Select a public portfolio to view full risk metrics.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Factor & Spread Analysis Cards */}
      <FactorExposureCards
        ridgeFactors={factorExposures.factors}
        spreadFactors={spreadFactors.spreadFactors}
        ridgeLoading={factorExposures.loading}
        spreadLoading={spreadFactors.loading}
        ridgeError={factorErrorMessage}
        spreadError={spreadErrorMessage}
        ridgeCalculationDate={factorExposures.calculationDate}
        spreadCalculationDate={spreadFactors.calculationDate ?? null}
        onRefetchRidge={factorExposures.refetch}
        onRefetchSpread={spreadFactors.refetch}
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
