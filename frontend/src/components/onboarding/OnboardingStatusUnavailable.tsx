'use client'

import { useState } from 'react'
import { AlertTriangle, RefreshCw, ArrowRight, RotateCcw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export interface OnboardingStatusUnavailableProps {
  onRefresh: () => void
  onViewPortfolio: () => void
  onRetryCalculations?: () => Promise<void>  // Optional: retry trigger calculations
}

/**
 * Screen shown when status endpoint returns not_found mid-run
 *
 * This can happen due to server restart, network issues, or if triggerCalculations
 * failed after portfolio creation. Shown after grace period with no running status.
 */
export function OnboardingStatusUnavailable({
  onRefresh,
  onViewPortfolio,
  onRetryCalculations,
}: OnboardingStatusUnavailableProps) {
  const [isRetrying, setIsRetrying] = useState(false)
  const [retryError, setRetryError] = useState<string | null>(null)

  const handleRetryCalculations = async () => {
    if (!onRetryCalculations) return

    setIsRetrying(true)
    setRetryError(null)
    try {
      await onRetryCalculations()
      // After successful trigger, refresh status to start polling
      onRefresh()
    } catch (err) {
      setRetryError('Failed to restart calculations. Please try again.')
      console.error('Retry calculations failed:', err)
    } finally {
      setIsRetrying(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-slate-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-md">
        <Card className="shadow-lg">
          <CardHeader className="text-center">
            <div className="mx-auto rounded-full p-4 bg-gray-100 dark:bg-gray-800 w-fit mb-4">
              <AlertTriangle className="h-10 w-10 text-gray-500" />
            </div>
            <CardTitle className="text-xl">Status Unavailable</CardTitle>
            <CardDescription className="text-base">
              Unable to fetch status updates.
              <br />
              Your portfolio may need to be set up again.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {retryError && (
              <p className="text-sm text-red-600 text-center">{retryError}</p>
            )}

            <div className="flex flex-col gap-3">
              {/* Primary action: Retry calculations if available */}
              {onRetryCalculations && (
                <Button
                  onClick={handleRetryCalculations}
                  disabled={isRetrying}
                  className="gap-2 w-full"
                >
                  <RotateCcw className={`h-4 w-4 ${isRetrying ? 'animate-spin' : ''}`} />
                  {isRetrying ? 'Restarting...' : 'Retry Setup'}
                </Button>
              )}

              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button onClick={onRefresh} variant="outline" className="gap-2">
                  <RefreshCw className="h-4 w-4" />
                  Refresh Status
                </Button>
                <Button onClick={onViewPortfolio} variant="outline" className="gap-2">
                  View Portfolio
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default OnboardingStatusUnavailable
