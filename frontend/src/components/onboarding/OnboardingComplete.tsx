'use client'

import { CheckCircle, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DownloadLogButton } from './DownloadLogButton'
import { OnboardingStatusResponse } from '@/services/onboardingService'

/**
 * Format elapsed seconds to human-readable duration
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`
  }
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`
  }
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`
}

export interface OnboardingCompleteProps {
  status: OnboardingStatusResponse
  portfolioName?: string
  onContinue: () => void
}

/**
 * Completion screen shown after batch processing finishes successfully
 */
export function OnboardingComplete({
  status,
  portfolioName = 'Your Portfolio',
  onContinue,
}: OnboardingCompleteProps) {
  const elapsedSeconds = status.elapsed_seconds ?? 0
  const phasesCompleted = status.overall_progress?.phases_completed ?? 0
  const phasesTotal = status.overall_progress?.phases_total ?? 0

  // Count warnings from activity log
  const warningCount = status.activity_log.filter(
    (entry) => entry.level === 'warning'
  ).length

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-emerald-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-lg">
        <Card className="shadow-lg">
          <CardHeader className="text-center">
            <div className="mx-auto rounded-full p-4 bg-green-100 dark:bg-green-900/20 w-fit mb-4">
              <CheckCircle className="h-12 w-12 text-green-600" />
            </div>
            <CardTitle className="text-2xl">Portfolio Setup Complete!</CardTitle>
            <CardDescription className="text-base">
              Your portfolio &quot;{portfolioName}&quot; is ready.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Summary Section */}
            <div className="bg-muted/30 rounded-lg p-4 space-y-2">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
                Summary
              </h3>
              <ul className="space-y-1 text-sm">
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span>{phasesCompleted}/{phasesTotal} phases completed</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span>Risk metrics and factor exposures ready</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span>Correlation matrix computed</span>
                </li>
                {warningCount > 0 && (
                  <li className="flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
                    <span>{warningCount} warning(s) during processing</span>
                  </li>
                )}
              </ul>
              <div className="pt-2 border-t mt-3">
                <p className="text-sm text-muted-foreground">
                  Total time: <span className="font-medium">{formatDuration(elapsedSeconds)}</span>
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <DownloadLogButton
                portfolioId={status.portfolio_id}
                variant="outline"
              />
              <Button onClick={onContinue} className="gap-2">
                View Portfolio Dashboard
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default OnboardingComplete
