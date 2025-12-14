'use client'

import { useEffect } from 'react'
import { Check, ArrowRight, Plus, AlertCircle, Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { ChecklistState } from '@/hooks/usePortfolioUpload'
import {
  useOnboardingPortfolios,
  useCanAddAnotherPortfolio,
  useIsInOnboardingSession,
  type OnboardingSessionPortfolio
} from '@/stores/portfolioStore'

interface UploadSuccessProps {
  portfolioName: string
  positionsImported: number
  positionsFailed?: number
  checklist: ChecklistState
  onContinue: () => void
  onAddAnother?: () => void
  onRetryFailed?: (portfolioId: string) => void
  isFromSettings?: boolean
}

const checklistLabels: Record<string, string> = {
  portfolio_created: 'Portfolio created',
  positions_imported: 'Positions imported',
  symbol_extraction: 'Symbols extracted',
  security_enrichment: 'Securities enriched',
  price_bootstrap: 'Price cache ready',
  market_data_collection: 'Market data collected',
  pnl_calculation: 'P&L calculated',
  position_values: 'Position values computed',
  market_beta: 'Market beta analyzed',
  ir_beta: 'Interest rate beta analyzed',
  factor_spread: 'Spread factors computed',
  factor_ridge: 'Ridge factors computed',
  sector_analysis: 'Sector analysis complete',
  volatility: 'Volatility calculated',
  correlations: 'Correlations computed',
}

// Status indicator component for session portfolios
function PortfolioStatusIndicator({ status }: { status: OnboardingSessionPortfolio['status'] }) {
  switch (status) {
    case 'success':
      return <Check className="h-4 w-4 text-green-600" />
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />
    case 'processing':
      return <Loader2 className="h-4 w-4 text-amber-500 animate-spin" />
  }
}

// Session portfolio list item
function SessionPortfolioItem({
  portfolio,
  onRetry
}: {
  portfolio: OnboardingSessionPortfolio
  onRetry?: (portfolioId: string) => void
}) {
  return (
    <div className={`flex items-center justify-between p-3 rounded-lg ${
      portfolio.status === 'success'
        ? 'bg-green-50 dark:bg-green-950'
        : portfolio.status === 'failed'
        ? 'bg-red-50 dark:bg-red-950'
        : 'bg-amber-50 dark:bg-amber-950'
    }`}>
      <div className="flex items-center gap-3">
        <PortfolioStatusIndicator status={portfolio.status} />
        <div>
          <p className="text-sm font-medium">{portfolio.portfolioName}</p>
          <p className="text-xs text-muted-foreground">
            {portfolio.status === 'success' && portfolio.positionsCount !== undefined
              ? `${portfolio.positionsCount} positions imported`
              : portfolio.status === 'failed'
              ? portfolio.error || 'Upload failed'
              : 'Processing...'}
          </p>
        </div>
      </div>
      {portfolio.status === 'failed' && onRetry && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onRetry(portfolio.portfolioId)}
        >
          <RefreshCw className="h-4 w-4 mr-1" />
          Retry
        </Button>
      )}
    </div>
  )
}

export function UploadSuccess({
  portfolioName,
  positionsImported,
  positionsFailed = 0,
  checklist,
  onContinue,
  onAddAnother,
  onRetryFailed,
  isFromSettings = false
}: UploadSuccessProps) {
  // Session state from store
  const sessionPortfolios = useOnboardingPortfolios()
  const canAddAnother = useCanAddAnotherPortfolio()
  const isInSession = useIsInOnboardingSession()

  // Check if we're in a multi-portfolio session with previous uploads
  const hasMultiplePortfolios = isInSession && sessionPortfolios.length > 0
  const successCount = sessionPortfolios.filter(p => p.status === 'success').length
  const failedCount = sessionPortfolios.filter(p => p.status === 'failed').length
  const processingCount = sessionPortfolios.filter(p => p.status === 'processing').length

  useEffect(() => {
    console.log('🎉 Portfolio upload successful!');
  }, [])

  // Determine title based on context
  const getTitle = () => {
    if (hasMultiplePortfolios && sessionPortfolios.length > 1) {
      return '🎉 Portfolio Session Summary'
    }
    return '🎉 Portfolio Ready!'
  }

  // Determine description based on context
  const getDescription = () => {
    if (hasMultiplePortfolios && sessionPortfolios.length > 1) {
      const parts = []
      if (successCount > 0) parts.push(`${successCount} successful`)
      if (failedCount > 0) parts.push(`${failedCount} failed`)
      if (processingCount > 0) parts.push(`${processingCount} processing`)
      return `${sessionPortfolios.length} portfolios: ${parts.join(', ')}`
    }
    return 'Your portfolio has been successfully uploaded and analyzed'
  }

  // Show "Add Another" button only in onboarding flow, not from settings
  const showAddAnotherButton = !isFromSettings && onAddAnother && canAddAnother

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-emerald-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-2xl">
        <Card className="shadow-lg border-green-200 dark:border-green-900">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div className="rounded-full bg-green-100 dark:bg-green-900/20 p-3">
                <Check className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-green-900 dark:text-green-100">
                  {getTitle()}
                </CardTitle>
                <CardDescription className="text-green-700 dark:text-green-300">
                  {getDescription()}
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Session Portfolio List (for multi-portfolio sessions) */}
            {hasMultiplePortfolios && sessionPortfolios.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">
                  Portfolios in this session:
                </p>
                <div className="space-y-2">
                  {sessionPortfolios.map((portfolio) => (
                    <SessionPortfolioItem
                      key={portfolio.portfolioId}
                      portfolio={portfolio}
                      onRetry={onRetryFailed}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Single Portfolio Summary (for individual upload or non-session) */}
            {!hasMultiplePortfolios && (
              <div className="bg-green-50 dark:bg-green-950 rounded-lg p-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-green-900 dark:text-green-100">
                    Portfolio Name:
                  </span>
                  <span className="text-sm text-green-700 dark:text-green-300">
                    {portfolioName}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-green-900 dark:text-green-100">
                    Positions Imported:
                  </span>
                  <span className="text-sm text-green-700 dark:text-green-300">
                    {positionsImported} {positionsFailed > 0 ? `(${positionsFailed} failed)` : ''}
                  </span>
                </div>
              </div>
            )}

            {/* Completed Checklist */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">
                Completed tasks:
              </p>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(checklistLabels).map(([key, label]) => (
                  <div
                    key={key}
                    className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300"
                  >
                    <Check className="h-3 w-3" />
                    <span>{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* What's Next */}
            <div className="border-t pt-4">
              <p className="text-sm font-medium mb-2">What's next?</p>
              <ul className="text-sm text-muted-foreground space-y-1 ml-4">
                <li>• View your portfolio dashboard</li>
                <li>• Explore risk metrics and factor exposures</li>
                <li>• Analyze position correlations</li>
                <li>• Review stress test scenarios</li>
              </ul>
            </div>
          </CardContent>

          <CardFooter className="flex flex-col gap-3">
            {/* Add Another Portfolio Button (only in onboarding flow) */}
            {showAddAnotherButton && (
              <Button
                className="w-full"
                variant="outline"
                size="lg"
                onClick={onAddAnother}
                disabled={!canAddAnother}
              >
                <Plus className="mr-2 h-4 w-4" />
                {canAddAnother ? 'Add Another Portfolio' : 'Processing...'}
              </Button>
            )}

            {/* Continue to Dashboard Button */}
            <Button
              className="w-full"
              size="lg"
              onClick={onContinue}
            >
              Continue to Dashboard
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>

            {/* Mixed results hint */}
            {failedCount > 0 && (
              <p className="text-xs text-muted-foreground text-center">
                You can continue to the dashboard even with failed uploads.
                Retry them later from Settings.
              </p>
            )}
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
