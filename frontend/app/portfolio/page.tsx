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
      />

      <BottomNavigation />
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

// Bottom Navigation Component (could be extracted later)
function BottomNavigation() {
  const { theme } = useTheme()

  return (
    <footer className={`border-t px-4 py-3 transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-800 border-slate-700' : 'bg-white border-gray-200'
    }`}>
      <div className="container mx-auto">
        <div className="flex items-center justify-center gap-8">
          <NavButton icon="home" label="Home" theme={theme} />
          <NavButton icon="history" label="History" theme={theme} />
          <NavButton icon="risk" label="Risk Analytics" theme={theme} />
          <NavButton icon="performance" label="Performance" theme={theme} />
          <NavButton icon="tags" label="Tags" theme={theme} />
        </div>
      </div>
    </footer>
  )
}

// Navigation Button Component
function NavButton({ icon, label, theme }: { icon: string; label: string; theme: string }) {
  const icons: Record<string, React.ReactNode> = {
    home: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/>
      </svg>
    ),
    history: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path d="M9 2a1 1 0 000 2v2a1 1 0 001 1h2a1 1 0 100-2V2a1 1 0 00-1-1H9z"/>
        <path fillRule="evenodd" d="M4 5a2 2 0 012-2 1 1 0 000 2H4v10a2 2 0 002 2h8a2 2 0 002-2V5h-2a1 1 0 100-2 2 2 0 012 2v10a4 4 0 01-4 4H6a4 4 0 01-4-4V5z" clipRule="evenodd"/>
      </svg>
    ),
    risk: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
      </svg>
    ),
    performance: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/>
      </svg>
    ),
    tags: (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M17.707 9.293a1 1 0 010 1.414l-7 7a1 1 0 01-1.414 0l-7-7A.997.997 0 012 10V5a3 3 0 013-3h5c.256 0 .512.098.707.293l7 7zM5 6a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd"/>
      </svg>
    )
  }

  return (
    <Button variant="ghost" size="sm" className={`flex flex-col items-center gap-1 transition-colors duration-300 ${
      theme === 'dark'
        ? 'text-slate-400 hover:text-white'
        : 'text-gray-600 hover:text-gray-900'
    }`}>
      {icons[icon]}
      <span className="text-xs">{label}</span>
    </Button>
  )
}

export default function Portfolio() {
  return (
    <ThemeProvider>
      <PortfolioPageContent />
    </ThemeProvider>
  )
}