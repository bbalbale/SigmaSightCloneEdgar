'use client'

import React from 'react'
import { useAuth } from '../../app/providers'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { User, RefreshCw, Zap, AlertCircle, CheckCircle2 } from 'lucide-react'
import { PortfolioManagement } from '@/components/settings/PortfolioManagement'
import { AccountBillingSettings } from '@/components/settings/AccountBillingSettings'
import { MemoryPanel } from '@/components/ai/MemoryPanel'
import { BriefingSettings } from '@/components/settings/BriefingSettings'
import { useRecalculateAnalytics } from '@/hooks/useRecalculateAnalytics'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { usePortfolioStore } from '@/stores/portfolioStore'

export function SettingsContainer() {
  const { user } = useAuth()
  const { portfolioId } = usePortfolioStore()
  const {
    state,
    error,
    elapsedSeconds,
    handleRecalculate,
    reset
  } = useRecalculateAnalytics()

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground mt-2">Manage your account settings and preferences</p>
      </div>

      {/* Account & Billing Section (Clerk Integration) */}
      <AccountBillingSettings />

      {/* Portfolio Management - Multi-Portfolio Feature (November 3, 2025) */}
      {/* Always show for single portfolio users so they can add more portfolios */}
      <PortfolioManagement showForSinglePortfolio={true} />

      {/* Actions Section - Power User Features */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Actions
          </CardTitle>
          <CardDescription>
            Advanced portfolio operations (use with caution)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Recalculate Analytics */}
          <div className="space-y-3">
            <div>
              <h3 className="text-sm font-medium mb-1">Recalculate Portfolio Analytics</h3>
              <p className="text-sm text-muted-foreground">
                Trigger a full recalculation of risk metrics, factor exposures, correlations, and volatility.
                This process takes 30-60 seconds to complete.
              </p>
            </div>

            {/* Status Messages */}
            {state === 'success' && (
              <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
                <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                <AlertDescription className="text-green-800 dark:text-green-200">
                  Analytics recalculated successfully! Refresh the page to see updated data.
                </AlertDescription>
              </Alert>
            )}

            {state === 'error' && error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {(state === 'polling' || state === 'triggering') && (
              <Alert className="border-blue-500 bg-blue-50 dark:bg-blue-950">
                <RefreshCw className="h-4 w-4 text-blue-600 dark:text-blue-400 animate-spin" />
                <AlertDescription className="text-blue-800 dark:text-blue-200">
                  {state === 'triggering'
                    ? 'Starting batch recalculation...'
                    : `Processing... ${elapsedSeconds}s elapsed`
                  }
                </AlertDescription>
              </Alert>
            )}

            {/* Action Button */}
            <Button
              onClick={handleRecalculate}
              disabled={state === 'triggering' || state === 'polling'}
              variant={state === 'error' ? 'destructive' : 'default'}
              className="w-full sm:w-auto"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${(state === 'triggering' || state === 'polling') ? 'animate-spin' : ''}`} />
              {state === 'triggering' ? 'Starting...' :
               state === 'polling' ? `Processing (${elapsedSeconds}s)` :
               state === 'success' ? 'Recalculate Again' :
               'Recalculate Analytics'}
            </Button>

            {state === 'error' && (
              <Button
                onClick={reset}
                variant="outline"
                size="sm"
                className="ml-2"
              >
                Clear Error
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* AI Memory Management */}
      <MemoryPanel portfolioId={portfolioId || undefined} />

      {/* Morning Briefing Settings (Phase 2) */}
      <BriefingSettings />
    </div>
  )
}
