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
import { AlertTriangle, Info } from 'lucide-react'

/**
 * RiskMetricsContainer
 *
 * Container component for the Risk Metrics page.
 * Follows standard architecture: thin page → container → hooks → services
 *
 * Updated December 2025: Added multi-portfolio support with AccountFilter
 * - Shows portfolio selector for users with multiple portfolios
 * - Displays current portfolio name in header
 * - Shows warning for private portfolios (no public market data)
 * - In aggregate view, shows metrics for each portfolio separately
 *
 * Responsibilities:
 * - Fetch all risk metrics data via custom hooks
 * - Orchestrate layout and component composition
 * - Pass data down to presentation components
 *
 * All API calls go through:
 * hooks → analyticsApi service → apiClient → backend
 */

/**
 * Single Portfolio Risk Metrics Section
 * Renders all risk metrics for a single portfolio
 */
function PortfolioRiskMetricsSection({
  portfolio,
  showHeader = true
}: {
  portfolio: PortfolioListItem
  showHeader?: boolean
}) {
  // Temporarily set the portfolioId in store to fetch this portfolio's data
  const setSelectedPortfolio = usePortfolioStore((state) => state.setSelectedPortfolio)

  // Check if this portfolio is private
  const isPrivatePortfolio = portfolio.account_name?.toLowerCase().includes('private') ?? false

  // We need the hooks to use this specific portfolio
  // The hooks read from portfolioId in the store
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
    <div className="mb-8">
      {/* Portfolio Header */}
      {showHeader && (
        <div className="px-4 pb-4">
          <div className="container mx-auto">
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              {portfolio.account_name}
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

      {/* Market Beta Comparison Section */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <MarketBetaComparison />
        </div>
      </section>
    </div>
  )
}

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

  // For Risk Metrics in aggregate view, use first PUBLIC portfolio for data fetching
  // This ensures we show analytics data even when store defaults to a private portfolio
  const effectivePortfolioId = React.useMemo(() => {
    if (!isAggregateView) {
      return portfolioId
    }
    // In aggregate view, prefer first public portfolio that has analytics
    if (publicPortfolios.length > 0) {
      return publicPortfolios[0].id
    }
    // Fall back to store default
    return portfolioId
  }, [isAggregateView, portfolioId, publicPortfolios])

  // Temporarily override the store's portfolioId for hooks when in aggregate view
  // This effect ensures hooks fetch data for the public portfolio
  React.useEffect(() => {
    if (isAggregateView && publicPortfolios.length > 0 && portfolioId !== publicPortfolios[0].id) {
      // We need to update the portfolioId in store for hooks to work correctly
      // But we don't want to change selectedPortfolioId (keep aggregate view)
      usePortfolioStore.setState({ portfolioId: publicPortfolios[0].id })
    }
  }, [isAggregateView, publicPortfolios, portfolioId])

  // Get current portfolio details
  const currentPortfolio = portfolios.find((p) => p.id === effectivePortfolioId)

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

  // In aggregate view with multiple portfolios, show each portfolio's metrics separately
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

        {/* Aggregate View Header */}
        <div className="px-4 pb-4">
          <div className="container mx-auto">
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              All Accounts
            </h2>
            <p className="text-sm text-muted-foreground">
              Combined risk analytics across {activePortfolios.length} portfolios
            </p>
          </div>
        </div>

        {/* Info Banner about Aggregate View */}
        <div className="px-4 pb-4">
          <div className="container mx-auto">
            <div className="flex items-center gap-3 p-4 rounded-lg border border-blue-500/30 bg-blue-500/10">
              <Info className="h-5 w-5 text-blue-500 flex-shrink-0" />
              <div>
                <p className="text-sm text-muted-foreground">
                  Viewing risk metrics for {activePortfolios.length} portfolio{activePortfolios.length !== 1 ? 's' : ''}.
                  {publicPortfolios.length > 0 && privatePortfolios.length > 0 && (
                    <> Public portfolios ({publicPortfolios.length}) show full analytics.
                    Private portfolios ({privatePortfolios.length}) have limited market data.</>
                  )}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Render each public portfolio's metrics first */}
        {publicPortfolios.map((portfolio) => (
          <div key={portfolio.id} className="border-t border-border/50 pt-6 mt-6">
            <div className="px-4 pb-4">
              <div className="container mx-auto">
                <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {portfolio.account_name}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {portfolio.position_count} positions • Public market analytics available
                </p>
              </div>
            </div>

            {/* Show metrics for this portfolio using the current hook data
                (hooks use portfolioId which we've set to first public portfolio in aggregate view) */}
            {portfolio.id === effectivePortfolioId && (
              <>
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
              </>
            )}

            {/* For other public portfolios, show a message to select them */}
            {portfolio.id !== effectivePortfolioId && (
              <div className="px-4 pb-6">
                <div className="container mx-auto">
                  <div className="p-6 rounded-lg border border-border/50 bg-muted/30 text-center">
                    <p className="text-sm text-muted-foreground">
                      Select &quot;{portfolio.account_name}&quot; from the dropdown above to view detailed risk metrics.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Show private portfolios with limited analytics message */}
        {privatePortfolios.map((portfolio) => (
          <div key={portfolio.id} className="border-t border-border/50 pt-6 mt-6">
            <div className="px-4 pb-4">
              <div className="container mx-auto">
                <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {portfolio.account_name}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {portfolio.position_count} positions • Private holdings
                </p>
              </div>
            </div>
            <div className="px-4 pb-6">
              <div className="container mx-auto">
                <div className="flex items-center gap-3 p-4 rounded-lg border border-yellow-500/30 bg-yellow-500/10">
                  <AlertTriangle className="h-5 w-5 text-yellow-500 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                      Limited Analytics Available
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Risk metrics require public market data. Private investments don&apos;t have standard market analytics like volatility, beta, or factor exposures.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
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
