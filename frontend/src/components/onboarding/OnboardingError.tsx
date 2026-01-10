'use client'

import { AlertTriangle, CheckCircle, XCircle, ArrowRight, RotateCcw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DownloadLogButton } from './DownloadLogButton'
import { OnboardingStatusResponse } from '@/services/onboardingService'

export interface OnboardingErrorProps {
  status: OnboardingStatusResponse
  onRetry: () => void
  onContinue: () => void
}

/**
 * Error/failure screen shown when batch processing fails
 *
 * Shows what completed, what failed, and options to retry or continue anyway.
 */
export function OnboardingError({
  status,
  onRetry,
  onContinue,
}: OnboardingErrorProps) {
  const phases = status.phases ?? []

  // Find completed and failed phases
  const completedPhases = phases.filter((p) => p.status === 'completed')
  const failedPhase = phases.find((p) => p.status === 'failed')

  // Get last error from activity log
  const lastError = status.activity_log
    .filter((entry) => entry.level === 'error')
    .pop()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 to-amber-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-lg">
        <Card className="shadow-lg">
          <CardHeader className="text-center">
            <div className="mx-auto rounded-full p-4 bg-orange-100 dark:bg-orange-900/20 w-fit mb-4">
              <AlertTriangle className="h-12 w-12 text-orange-600" />
            </div>
            <CardTitle className="text-2xl">Setup Interrupted</CardTitle>
            <CardDescription className="text-base">
              We encountered an issue while setting up your portfolio.
              <br />
              Some features may have limited data.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Status Summary */}
            <div className="bg-muted/30 rounded-lg p-4 space-y-3">
              {/* Completed phases */}
              {completedPhases.length > 0 && (
                <div className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium">Completed:</p>
                    <p className="text-sm text-muted-foreground">
                      {completedPhases.map((p) => p.phase_name).join(', ')}
                    </p>
                  </div>
                </div>
              )}

              {/* Failed phase */}
              {failedPhase && (
                <div className="flex items-start gap-2">
                  <XCircle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium">Failed at:</p>
                    <p className="text-sm text-muted-foreground">
                      {failedPhase.phase_name}
                    </p>
                  </div>
                </div>
              )}

              {/* Error message */}
              {lastError && (
                <div className="pt-2 border-t">
                  <p className="text-sm font-medium text-red-700 dark:text-red-400">
                    Error: {lastError.message}
                  </p>
                </div>
              )}
            </div>

            {/* Reassurance message */}
            <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-4">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                Your portfolio is available with partial analytics.
                <br />
                Full analytics will be available after the next daily update.
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <DownloadLogButton
                portfolioId={status.portfolio_id}
                variant="outline"
              />
              <Button onClick={onRetry} variant="outline" className="gap-2">
                <RotateCcw className="h-4 w-4" />
                Retry Setup
              </Button>
              <Button onClick={onContinue} className="gap-2">
                View Portfolio Anyway
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default OnboardingError
