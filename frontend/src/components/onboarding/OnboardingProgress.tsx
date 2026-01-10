'use client'

import { Loader2, Rocket } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PhaseList } from './PhaseList'
import { ActivityLog } from './ActivityLog'
import { OnboardingStatusResponse } from '@/services/onboardingService'

/**
 * Format elapsed seconds to human-readable duration
 */
function formatElapsed(seconds: number): string {
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
  return `${hours}h ${remainingMinutes}m`
}

export interface OnboardingProgressProps {
  status: OnboardingStatusResponse | null
  isLoading?: boolean
}

/**
 * Main progress screen during batch processing
 *
 * Shows real-time phase progress and activity log while batch is running.
 * Note: Download button is intentionally NOT shown here - only on completion/error screens.
 */
export function OnboardingProgress({ status, isLoading = false }: OnboardingProgressProps) {
  const overallProgress = status?.overall_progress
  const percentComplete = overallProgress?.percent_complete ?? 0
  const elapsedSeconds = status?.elapsed_seconds ?? 0

  // Build header message
  let headerMessage = 'Setting up your portfolio...'
  if (overallProgress?.phases_total) {
    headerMessage = `Analyzing your portfolio with ${overallProgress.phases_total} processing phases.`
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-2xl">
        <Card className="shadow-lg">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div className="rounded-full p-3 bg-blue-100 dark:bg-blue-900/20">
                {isLoading ? (
                  <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
                ) : (
                  <Rocket className="h-6 w-6 text-blue-600" />
                )}
              </div>
              <div className="flex-1">
                <CardTitle>Setting Up Your Portfolio</CardTitle>
                <CardDescription>{headerMessage}</CardDescription>
                <CardDescription className="mt-1">
                  This typically takes 15-20 minutes.
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Phase Progress Section */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wide">
                Phase Progress
              </h3>
              <PhaseList
                phases={status?.phases ?? null}
                currentPhase={overallProgress?.current_phase}
              />
            </div>

            {/* Divider */}
            <div className="border-t" />

            {/* Activity Log Section */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wide">
                Activity Log
              </h3>
              <ActivityLog entries={status?.activity_log ?? []} maxHeight="200px" />
            </div>

            {/* Divider */}
            <div className="border-t" />

            {/* Footer Stats */}
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Elapsed:</span>
                <span className="font-medium">{formatElapsed(elapsedSeconds)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Overall:</span>
                <span className="font-medium">{percentComplete}% complete</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default OnboardingProgress
