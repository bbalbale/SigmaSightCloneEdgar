'use client'

import React, { useState } from 'react'
import { useCommandCenterData } from '@/hooks/useCommandCenterData'
import { HeroMetricsRow } from '@/components/command-center/HeroMetricsRow'
import { HoldingsTable } from '@/components/command-center/HoldingsTable'
import { RiskMetricsRow } from '@/components/command-center/RiskMetricsRow'
import { AIInsightsButton } from '@/components/command-center/AIInsightsButton'
import { PositionManagementContainer } from '@/containers/PositionManagementContainer'
import { Button } from '@/components/ui/button'

type ViewMode = 'analytics' | 'manage'

export function CommandCenterContainer() {
  const { heroMetrics, holdings, riskMetrics, loading, error } = useCommandCenterData()
  const [viewMode, setViewMode] = useState<ViewMode>('analytics')

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

  return (
    <div
      className="min-h-screen transition-colors duration-300"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      {/* Page Description & Mode Toggle */}
      <div className="px-4 pt-4 pb-2">
        <div className="container mx-auto">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Portfolio overview, holdings, and risk metrics
            </p>
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'analytics' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('analytics')}
              >
                Analytics View
              </Button>
              <Button
                variant={viewMode === 'manage' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('manage')}
              >
                Manage Positions
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Conditional Content Based on View Mode */}
      {viewMode === 'analytics' ? (
        <>
          {/* Hero Metrics - 6 cards */}
          <section className="pt-4">
            <HeroMetricsRow metrics={heroMetrics} loading={loading} />
          </section>

          {/* Holdings Table - 11 columns */}
          <HoldingsTable holdings={holdings} loading={loading} />

          {/* Risk Metrics - 5 cards */}
          <RiskMetricsRow metrics={riskMetrics} loading={loading} />
        </>
      ) : (
        <div className="px-4 pt-4">
          <div className="container mx-auto">
            <PositionManagementContainer />
          </div>
        </div>
      )}
    </div>
  )
}
