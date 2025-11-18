'use client'

import React, { useEffect, useMemo, useState } from 'react'
import { useCommandCenterData } from '@/hooks/useCommandCenterData'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { HeroMetricsRow } from '@/components/command-center/HeroMetricsRow'
import { PerformanceMetricsRow } from '@/components/command-center/PerformanceMetricsRow'
import { HoldingsTable } from '@/components/command-center/HoldingsTable'
import { ManagePositionsSidePanel } from '@/components/portfolio/ManagePositionsSidePanel'
import { ManageEquitySidePanel } from '@/components/portfolio/ManageEquitySidePanel'
import { Button } from '@/components/ui/button'
import { AccountFilter } from '@/components/portfolio/AccountFilter'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { UploadPortfolioBanner } from '@/components/command-center/UploadPortfolioBanner'

type PortfolioSectionShape = ReturnType<typeof useCommandCenterData>['portfolios'][number]

export function CommandCenterContainer() {
  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
  const totalPortfolios = usePortfolioStore(state => state.portfolios.length)
  const [sidePanelOpen, setSidePanelOpen] = useState(false)
  const [equityPanelOpen, setEquityPanelOpen] = useState(false)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [equityActionMessage, setEquityActionMessage] = useState<string | null>(null)

  const { aggregate, portfolios, loading, error } = useCommandCenterData(refreshTrigger)

  useEffect(() => {
    if (!equityActionMessage) {
      return
    }
    const timer = setTimeout(() => setEquityActionMessage(null), 5000)
    return () => clearTimeout(timer)
  }, [equityActionMessage])

  const isAggregateView = selectedPortfolioId === null
  const filteredSections = selectedPortfolioId
    ? portfolios.filter(section => section.portfolioId === selectedPortfolioId)
    : portfolios
  const sectionsToRender = filteredSections.length > 0 ? filteredSections : portfolios

  const aggregatePortfolioCount = useMemo(() => {
    if (!aggregate) {
      return 0
    }
    const ids = new Set<string>()
    aggregate.holdings.forEach(holding => {
      if (holding.portfolio_id) {
        ids.add(holding.portfolio_id)
      }
    })
    return ids.size
  }, [aggregate])

  const multiPortfolioActive = aggregatePortfolioCount > 1 || totalPortfolios > 1
  const showAggregateSection = Boolean(
    isAggregateView && aggregate && multiPortfolioActive
  )
  const showPortfolioBadge = isAggregateView && multiPortfolioActive && sectionsToRender.length > 1

  const emptyHeroMetrics = {
    equityBalance: 0,
    targetReturnEOY: 0,
    grossExposure: 0,
    netExposure: 0,
    longExposure: 0,
    shortExposure: 0,
    totalCapitalFlow: 0,
    netCapitalFlow30d: 0,
    lastCapitalChange: null,
  }

  const emptyPerformanceMetrics = {
    ytdPnl: 0,
    mtdPnl: 0,
    cashBalance: 0,
    portfolioBeta90d: null,
    portfolioBeta1y: null,
    stressTest: null,
    volatility: {
      current21d: null,
      historical63d: null,
      forward21d: null
    }
  }

  const emptyRiskMetrics = {
    portfolioBeta90d: null,
    portfolioBeta1y: null,
    topSector: null,
    largestPosition: null,
    spCorrelation: null,
    stressTest: null
  }

  const placeholderSection: PortfolioSectionShape | undefined = loading
    ? {
        portfolioId: selectedPortfolioId ?? 'loading',
        accountName: 'Loading...',
        heroMetrics: emptyHeroMetrics,
        performanceMetrics: emptyPerformanceMetrics,
        riskMetrics: emptyRiskMetrics,
        holdings: [],
        equitySummary: {
          portfolioId: selectedPortfolioId ?? 'loading',
          totalContributions: 0,
          totalWithdrawals: 0,
          netFlow: 0,
          periods: {},
        },
        equityChanges: [],
      }
    : undefined

  const sectionsForRendering =
    sectionsToRender.length > 0
      ? sectionsToRender
      : placeholderSection
        ? [placeholderSection]
        : []

  // Phase 2.4: Show CTA banner for users without portfolios
  if (!loading && portfolios.length === 0 && !error) {
    return (
      <div
        className="min-h-screen transition-colors duration-300"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        <UploadPortfolioBanner />
      </div>
    )
  }

  if (error && !loading) {
    return (
      <div
        className="min-h-screen transition-colors duration-300"
        style={{ backgroundColor: 'var(--bg-primary)' }}
      >
        <section className="px-4 py-12">
          <div className="container mx-auto">
            <div
              className="text-center transition-colors duration-300"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-primary)',
                borderRadius: 'var(--border-radius)',
                padding: 'var(--card-padding)'
              }}
            >
              <h2
                className="font-semibold mb-2"
                style={{
                  fontSize: 'var(--text-xl)',
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-body)'
                }}
              >
                Error Loading Data
              </h2>
              <p
                style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-body)'
                }}
              >
                {error}
              </p>
            </div>
          </div>
        </section>
      </div>
    )
  }

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1)
  }

  const handleSidePanelComplete = () => {
    setSidePanelOpen(false)
    handleRefresh()
  }

  const handleEquityPanelComplete = (result?: { message?: string }) => {
    if (result?.message) {
      setEquityActionMessage(result.message)
    }
    setEquityPanelOpen(false)
    handleRefresh()
  }

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      {/* Page Description with Manage Positions Button and Account Filter */}
      <div className="px-4 pt-4 pb-2">
        <div className="container mx-auto flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4 flex-1">
            <p className="text-sm text-muted-foreground">
              Portfolio overview, holdings, and risk metrics
            </p>
            {/* Account Filter - Multi-Portfolio Feature (November 3, 2025) */}
            <AccountFilter className="ml-auto" showForSinglePortfolio={true} />
      </div>
      <div className="flex items-center gap-2">
        <Button
          onClick={() => setEquityPanelOpen(true)}
          size="sm"
          variant="secondary"
          disabled={isAggregateView || !portfolioId}
        >
          Manage Equity
        </Button>
        <Button
          onClick={() => setSidePanelOpen(true)}
          size="sm"
          className="flex items-center gap-2"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          Manage Positions
        </Button>
      </div>
    </div>
  </div>

  {equityActionMessage && (
    <div className="px-4">
      <div className="container mx-auto">
        <Alert>
          <AlertDescription>{equityActionMessage}</AlertDescription>
        </Alert>
      </div>
    </div>
  )}

      {showAggregateSection && aggregate && (
        <>
          <section className="px-4 pt-6">
            <div className="container mx-auto">
              <h2
                className="text-lg font-semibold"
                style={{ color: 'var(--color-accent)' }}
              >
                All Accounts Overview
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                Combined exposure, performance, and risk across every portfolio.
              </p>
            </div>
          </section>
          <HeroMetricsRow metrics={aggregate.heroMetrics} loading={loading} />
          <PerformanceMetricsRow metrics={aggregate.performanceMetrics} loading={loading} />
          <HoldingsTable
            holdings={aggregate.holdings}
            loading={loading}
            onRefresh={handleRefresh}
          />
        </>
      )}

      {sectionsForRendering.map(section => {
        const holdingsForSection = section.holdings.map(({ account_name, portfolio_id, ...rest }) => rest)
        return (
          <React.Fragment key={section.portfolioId}>
            <section className="px-4 pt-8">
              <div className="container mx-auto">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                  <div>
                    <h3
                      className="text-lg font-semibold"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {section.accountName}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Portfolio-specific exposure, performance, and risk.
                    </p>
                  </div>
                  {showPortfolioBadge && (
                    <span className="text-xs text-muted-foreground uppercase tracking-wide">
                      Individual Account
                    </span>
                  )}
                </div>
              </div>
            </section>
            <HeroMetricsRow metrics={section.heroMetrics} loading={loading} />
            <PerformanceMetricsRow metrics={section.performanceMetrics} loading={loading} />
            <HoldingsTable
              holdings={holdingsForSection}
              loading={loading}
              onRefresh={handleRefresh}
            />
          </React.Fragment>
        )
      })}

      {/* Manage Positions Side Panel */}
      {portfolioId && (
        <ManagePositionsSidePanel
          portfolioId={portfolioId}
          open={sidePanelOpen}
          onOpenChange={setSidePanelOpen}
          onComplete={handleSidePanelComplete}
        />
      )}
      {portfolioId && (
        <ManageEquitySidePanel
          portfolioId={portfolioId}
          open={equityPanelOpen}
          onOpenChange={setEquityPanelOpen}
          onComplete={handleEquityPanelComplete}
        />
      )}
    </div>
  )
}
