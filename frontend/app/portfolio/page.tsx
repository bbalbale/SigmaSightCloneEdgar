"use client"

import React, { useState, useMemo } from 'react'
import { useTheme } from '@/contexts/ThemeContext'

// Custom hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'
import { useTags } from '@/hooks/useTags'

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
    handleRetry
  } = usePortfolioData()

  // Fetch tags for filtering
  const { tags } = useTags()

  // Filter state
  const [selectedTagId, setSelectedTagId] = useState<string | null>(null)
  const [selectedFactorName, setSelectedFactorName] = useState<string | null>(null)

  // Filter positions based on selected tag
  const filterPositionsByTag = useMemo(() => {
    return (positionsList: any[]) => {
      if (!selectedTagId) return positionsList
      return positionsList.filter(p =>
        p.tags?.some((tag: any) => tag.id === selectedTagId)
      )
    }
  }, [selectedTagId])

  // Filter positions based on selected factor exposure
  const filterPositionsByFactor = useMemo(() => {
    return (positionsList: any[]) => {
      if (!selectedFactorName) return positionsList
      return positionsList.filter(p =>
        p.factor_exposures?.some((exp: any) => exp.factor_name === selectedFactorName)
      )
    }
  }, [selectedFactorName])

  // Apply both filters
  const applyFilters = (positionsList: any[]) => {
    let filtered = positionsList
    if (selectedTagId) {
      filtered = filterPositionsByTag(filtered)
    }
    if (selectedFactorName) {
      filtered = filterPositionsByFactor(filtered)
    }
    return filtered
  }

  // Filtered positions
  const filteredPublicPositions = useMemo(() => applyFilters(publicPositions), [publicPositions, selectedTagId, selectedFactorName])
  const filteredOptionsPositions = useMemo(() => applyFilters(optionsPositions), [optionsPositions, selectedTagId, selectedFactorName])
  const filteredPrivatePositions = useMemo(() => applyFilters(privatePositions), [privatePositions, selectedTagId, selectedFactorName])

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

      <FilterBar
        tags={tags}
        factorExposures={factorExposures || []}
        selectedTagId={selectedTagId}
        selectedFactorName={selectedFactorName}
        onTagFilterChange={setSelectedTagId}
        onFactorFilterChange={setSelectedFactorName}
      />

      <PortfolioPositions
        longPositions={positions}
        shortPositions={shortPositions}
        publicPositions={filteredPublicPositions}
        optionsPositions={filteredOptionsPositions}
        privatePositions={filteredPrivatePositions}
      />
    </div>
  )
}

export default function Portfolio() {
  return <PortfolioPageContent />
}
