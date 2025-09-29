"use client"

import React from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext'
import { ThemeToggle } from '@/components/app/ThemeToggle'

// Custom hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'

// Portfolio components
import { PortfolioHeader } from '@/components/portfolio/PortfolioHeader'
import { PortfolioMetrics } from '@/components/portfolio/PortfolioMetrics'
import { PortfolioPositions } from '@/components/portfolio/PortfolioPositions'
import { PortfolioError, PortfolioErrorState } from '@/components/portfolio/PortfolioError'
import { FilterBar } from '@/components/portfolio/FilterBar'
import { FactorExposureCards } from '@/components/portfolio/FactorExposureCards'

function PortfolioPageContent() {
  const { theme } = useTheme()

  const {
    loading,
    error,
    apiErrors,
    portfolioName,
    portfolioSummaryMetrics,
    positions,
    shortPositions,
    publicPositions,
    optionsPositions,
    privatePositions,
    factorExposures,
    dataLoaded,
    portfolioType,
    handleRetry
  } = usePortfolioData()

  // Loading state (only show if no data loaded yet)
  if (loading && !dataLoaded && portfolioType) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <AppHeader />
        <section className="px-4 py-12">
          <div className="container mx-auto text-center">
            <p className={`text-lg ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
              Loading portfolio data...
            </p>
          </div>
        </section>
      </div>
    )
  }

  // Error state (only show if no data loaded)
  if (error && !dataLoaded) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <AppHeader />
        <PortfolioErrorState error={error} onRetry={handleRetry} />
      </div>
    )
  }

  // No portfolio selected
  if (!portfolioType) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
        <AppHeader />
        <section className="px-4 py-12">
          <div className="container mx-auto text-center">
            <p className={`text-lg mb-4 ${theme === 'dark' ? 'text-slate-400' : 'text-gray-600'}`}>
              Please select a portfolio type to continue
            </p>
            <div className="flex gap-4 justify-center">
              <Link href="/portfolio?type=high-net-worth">
                <Button variant="outline">High Net Worth</Button>
              </Link>
              <Link href="/portfolio?type=individual">
                <Button variant="outline">Individual</Button>
              </Link>
              <Link href="/portfolio?type=hedge-fund">
                <Button variant="outline">Hedge Fund</Button>
              </Link>
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
      <AppHeader />

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

      {factorExposures && (
        <FactorExposureCards factors={factorExposures} />
      )}

      <FilterBar />

      <PortfolioPositions
        longPositions={positions}
        shortPositions={shortPositions}
        publicPositions={publicPositions}
        optionsPositions={optionsPositions}
        privatePositions={privatePositions}
      />
    </div>
  )
}

// App Header Component (could be extracted to its own file later)
function AppHeader() {
  const { theme } = useTheme()

  return (
    <header className={`border-b transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
    }`}>
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <Link href="/landing" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="text-emerald-400 text-xl font-bold">$</div>
            <h1 className={`text-xl font-semibold transition-colors duration-300 ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>SigmaSight</h1>
          </Link>
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}

export default function Portfolio() {
  return (
    <ThemeProvider>
      <PortfolioPageContent />
    </ThemeProvider>
  )
}