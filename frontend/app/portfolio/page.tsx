"use client"

import React, { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'

// Custom hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'
import { useStrategies } from '@/hooks/useStrategies'

// Portfolio components
import { PortfolioHeader } from '@/components/portfolio/PortfolioHeader'
import { PortfolioMetrics } from '@/components/portfolio/PortfolioMetrics'
import { PortfolioPositions } from '@/components/portfolio/PortfolioPositions'
import { PortfolioStrategiesView } from '@/components/portfolio/PortfolioStrategiesView'
import { PortfolioError, PortfolioErrorState } from '@/components/portfolio/PortfolioError'
import { FilterBar } from '@/components/portfolio/FilterBar'
import { FactorExposureCards } from '@/components/portfolio/FactorExposureCards'
import { Button } from '@/components/ui/button'

function PortfolioPageContent() {
  const { theme } = useTheme()
  const [viewMode, setViewMode] = useState<'positions' | 'strategies'>('positions')

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
    handleRetry
  } = usePortfolioData()

  // Fetch strategies data
  const {
    strategies,
    loading: strategiesLoading,
    error: strategiesError
  } = useStrategies({
    includePositions: true,
    includeTags: true
  })

  if (loading && !dataLoaded) {
    return (
      <div className={`min-h-screen transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
      }`}>
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

      {factorExposures && (
        <FactorExposureCards factors={factorExposures} />
      )}

      <FilterBar />

      {/* View Toggle */}
      <section className="px-4 py-4">
        <div className="container mx-auto">
          <div className="flex gap-2 mb-4">
            <Button
              variant={viewMode === 'positions' ? 'outline' : 'default'}
              onClick={() => setViewMode('positions')}
            >
              Position View
            </Button>
            <Button
              variant={viewMode === 'strategies' ? 'outline' : 'default'}
              onClick={() => setViewMode('strategies')}
            >
              Combination View
            </Button>
          </div>
        </div>
      </section>

      {/* Conditional Rendering */}
      {viewMode === 'positions' ? (
        <PortfolioPositions
          longPositions={positions}
          shortPositions={shortPositions}
          publicPositions={publicPositions}
          optionsPositions={optionsPositions}
          privatePositions={privatePositions}
        />
      ) : (
        <PortfolioStrategiesView
          strategies={strategies}
        />
      )}
    </div>
  )
}

export default function Portfolio() {
  return <PortfolioPageContent />
}
