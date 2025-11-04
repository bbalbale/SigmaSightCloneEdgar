'use client'

import React, { useState } from 'react'
import { useCommandCenterData } from '@/hooks/useCommandCenterData'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { HeroMetricsRow } from '@/components/command-center/HeroMetricsRow'
import { PerformanceMetricsRow } from '@/components/command-center/PerformanceMetricsRow'
import { HoldingsTable } from '@/components/command-center/HoldingsTable'
import { ManagePositionsSidePanel } from '@/components/portfolio/ManagePositionsSidePanel'
import { Button } from '@/components/ui/button'

export function CommandCenterContainer() {
  const { portfolioId } = usePortfolioStore()
  const [sidePanelOpen, setSidePanelOpen] = useState(false)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const { heroMetrics, performanceMetrics, holdings, riskMetrics, loading, error } = useCommandCenterData(refreshTrigger)

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

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      {/* Page Description with Manage Positions Button */}
      <div className="px-4 pt-4 pb-2">
        <div className="container mx-auto flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Portfolio overview, holdings, and risk metrics
          </p>
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

      {/* Hero Metrics Row 1 - Exposures (6 cards) */}
      <section className="pt-4">
        <HeroMetricsRow metrics={heroMetrics} loading={loading} />
      </section>

      {/* Hero Metrics Row 2 - Performance & Risk (5 cards) */}
      <section className="pt-0">
        <PerformanceMetricsRow metrics={performanceMetrics} loading={loading} />
      </section>

      {/* Holdings Table - 11 columns */}
      <HoldingsTable holdings={holdings} loading={loading} onRefresh={handleRefresh} />

      {/* Manage Positions Side Panel */}
      {portfolioId && (
        <ManagePositionsSidePanel
          portfolioId={portfolioId}
          open={sidePanelOpen}
          onOpenChange={setSidePanelOpen}
          onComplete={handleSidePanelComplete}
        />
      )}
    </div>
  )
}
