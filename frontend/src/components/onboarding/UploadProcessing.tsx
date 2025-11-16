'use client'

import { Loader2, Check, Hourglass, XCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChecklistState } from '@/hooks/usePortfolioUpload'

interface UploadProcessingProps {
  uploadState: 'uploading' | 'processing'
  currentSpinnerItem: string | null
  checklist: ChecklistState
  error?: string
  onTryAgain?: () => void
}

const checklistLabels: Record<string, string> = {
  portfolio_created: 'Portfolio created',
  positions_imported: 'Positions imported',
  symbol_extraction: 'Extracting symbols',
  security_enrichment: 'Enriching security data',
  price_bootstrap: 'Bootstrapping price cache',
  market_data_collection: 'Collecting market data',
  pnl_calculation: 'Calculating P&L',
  position_values: 'Computing position values',
  market_beta: 'Analyzing market beta',
  ir_beta: 'Analyzing interest rate beta',
  factor_spread: 'Computing spread factors',
  factor_ridge: 'Computing ridge factors',
  sector_analysis: 'Running sector analysis',
  volatility: 'Calculating volatility',
  correlations: 'Computing correlations',
}

export function UploadProcessing({
  uploadState,
  currentSpinnerItem,
  checklist,
  error,
  onTryAgain
}: UploadProcessingProps) {
  const getIcon = (key: string) => {
    // If item is completed, show checkmark
    if (checklist[key as keyof ChecklistState]) {
      return <Check className="h-4 w-4 text-green-600" />
    }

    // If this is the current item being processed (during batch), show rotating arrow
    if (uploadState === 'processing' && currentSpinnerItem === key) {
      return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
    }

    // Otherwise show hourglass for waiting items
    return <Hourglass className="h-4 w-4 text-gray-400" />
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-2xl">
        <Card className="shadow-lg">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div className={`rounded-full p-3 ${error ? 'bg-red-100 dark:bg-red-900/20' : 'bg-blue-100 dark:bg-blue-900/20'}`}>
                {error ? (
                  <XCircle className="h-6 w-6 text-red-600" />
                ) : (
                  <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
                )}
              </div>
              <div className="flex-1">
                <CardTitle>
                  {error
                    ? 'An Error Occurred'
                    : uploadState === 'uploading'
                    ? 'Uploading Your Portfolio...'
                    : 'Analyzing Your Portfolio...'}
                </CardTitle>
                <CardDescription>
                  {error
                    ? 'Something went wrong during the upload process'
                    : uploadState === 'uploading'
                    ? 'Validating your CSV file and importing positions'
                    : 'Running risk analytics and calculations'}
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {/* Show error if present */}
            {error && (
              <div className="mb-4 p-4 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
                <div className="flex items-start gap-3">
                  <XCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-900 dark:text-red-100 mb-1">
                      An error occurred
                    </p>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      {error}
                    </p>
                  </div>
                </div>
                {onTryAgain && (
                  <Button
                    onClick={onTryAgain}
                    variant="outline"
                    className="mt-3 w-full"
                  >
                    Try Again
                  </Button>
                )}
              </div>
            )}

            {/* Show normal processing UI when no error */}
            {!error && uploadState === 'uploading' && (
              // Simple loading state for upload phase
              <div className="space-y-4">
                <div className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
                  <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
                  <span className="text-sm font-medium">Validating CSV and importing positions...</span>
                </div>
                <p className="text-xs text-muted-foreground text-center">
                  This usually takes 10-30 seconds
                </p>
              </div>
            )}

            {/* Detailed checklist for processing phase (when no error) */}
            {!error && uploadState === 'processing' && (
              <div className="space-y-2">
                {Object.entries(checklistLabels).map(([key, label]) => (
                  <div
                    key={key}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                      checklist[key as keyof ChecklistState]
                        ? 'bg-green-50 dark:bg-green-950'
                        : currentSpinnerItem === key
                        ? 'bg-blue-50 dark:bg-blue-950'
                        : 'bg-gray-50 dark:bg-gray-900'
                    }`}
                  >
                    {getIcon(key)}
                    <span
                      className={`text-sm ${
                        checklist[key as keyof ChecklistState]
                          ? 'font-medium text-green-900 dark:text-green-100'
                          : currentSpinnerItem === key
                          ? 'font-medium text-blue-900 dark:text-blue-100'
                          : 'text-muted-foreground'
                      }`}
                    >
                      {label}
                    </span>
                  </div>
                ))}

                <p className="text-xs text-muted-foreground text-center pt-4">
                  This usually takes 30-60 seconds. Hang tight!
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
