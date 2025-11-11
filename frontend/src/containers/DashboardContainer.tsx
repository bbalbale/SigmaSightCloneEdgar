'use client'

import React from 'react'

// Custom hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'
import { useSpreadFactors } from '@/hooks/useSpreadFactors'

// Portfolio components
import { PortfolioHeader } from '@/components/portfolio/PortfolioHeader'
import { PortfolioMetrics } from '@/components/portfolio/PortfolioMetrics'
import { PortfolioError, PortfolioErrorState } from '@/components/portfolio/PortfolioError'
import { FactorExposureCards } from '@/components/portfolio/FactorExposureCards'
import { SpreadFactorCards } from '@/components/portfolio/SpreadFactorCards'

export function DashboardContainer() {

  const {
    loading,
    error,
    apiErrors,
    portfolioName,
    portfolioSummaryMetrics,
    positions,
    shortPositions,
    factorExposures,
    factorDataQuality,
    dataLoaded,
    handleRetry
  } = usePortfolioData()

  // Fetch spread factor exposures
  const {
    spreadFactors,
    loading: spreadLoading,
    error: spreadError,
    calculationDate
  } = useSpreadFactors()

  if (loading && !dataLoaded) {
    return (
      <div className="min-h-screen transition-colors duration-300 bg-primary">
        <section className="px-4 py-12">
          <div className="container mx-auto text-center">
            <p className="text-lg text-secondary">
              Loading portfolio data...
            </p>
          </div>
        </section>
      </div>
    )
  }

  if (error && !dataLoaded) {
    return (
      <div className="min-h-screen transition-colors duration-300 bg-primary">
        <PortfolioErrorState error={error} onRetry={handleRetry} />
      </div>
    )
  }

  return (
    <div className="min-h-screen transition-colors duration-300 bg-primary">

      <PortfolioError
        error={error}
        apiErrors={apiErrors}
        dataLoaded={dataLoaded}
        loading={loading}
        onRetry={handleRetry}
      />

      <PortfolioHeader
        portfolioName={portfolioName}
        loading={loading}
        dataLoaded={dataLoaded}
        positionsCount={positions.length + shortPositions.length}
      />

      <PortfolioMetrics
        metrics={portfolioSummaryMetrics}
        loading={loading}
        error={error}
      />

      {/* Factor Exposures Section */}
      {factorExposures ? (
        <FactorExposureCards factors={factorExposures} dataQuality={factorDataQuality} />
      ) : apiErrors?.factorExposures ? (
        <section className="px-4 pb-8">
          <div className="container mx-auto">
            <div className="themed-card p-6 text-center transition-colors duration-300">
              <p className="mb-2 text-secondary">Factor exposures temporarily unavailable</p>
              <button
                onClick={handleRetry}
                className="btn-accent px-4 py-2 rounded-md text-sm transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </section>
      ) : loading ? (
        <section className="px-4 pb-8">
          <div className="container mx-auto">
            <div className="themed-card p-6 text-center transition-colors duration-300">
              <p className="text-secondary">Loading factor exposures...</p>
              <p className="text-sm mt-2 opacity-70 text-tertiary">(This may take up to 60 seconds)</p>
            </div>
          </div>
        </section>
      ) : null}

      {/* Spread Factor Exposures Section */}
      <SpreadFactorCards
        factors={spreadFactors}
        loading={spreadLoading}
        error={spreadError}
        calculationDate={calculationDate}
      />
    </div>
  )
}
