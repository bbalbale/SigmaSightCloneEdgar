'use client'

import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'

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
  const { theme } = useTheme()

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
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <PortfolioErrorState error={error} onRetry={handleRetry} />
      </div>
    )
  }

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>

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
            <div className={`rounded-lg border p-6 text-center transition-colors duration-300 ${
              theme === 'dark'
                ? 'bg-slate-800 border-slate-700 text-slate-400'
                : 'bg-white border-gray-200 text-gray-600'
            }`}>
              <p className="mb-2">Factor exposures temporarily unavailable</p>
              <button
                onClick={handleRetry}
                className={`px-4 py-2 rounded-md text-sm transition-colors ${
                  theme === 'dark'
                    ? 'bg-blue-600 hover:bg-blue-700 text-white'
                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                }`}
              >
                Retry
              </button>
            </div>
          </div>
        </section>
      ) : loading ? (
        <section className="px-4 pb-8">
          <div className="container mx-auto">
            <div className={`rounded-lg border p-6 text-center transition-colors duration-300 ${
              theme === 'dark'
                ? 'bg-slate-800 border-slate-700 text-slate-400'
                : 'bg-white border-gray-200 text-gray-600'
            }`}>
              <p>Loading factor exposures...</p>
              <p className="text-sm mt-2 opacity-70">(This may take up to 60 seconds)</p>
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
