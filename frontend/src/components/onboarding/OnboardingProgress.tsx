'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2, Rocket, CheckCircle, AlertTriangle, XCircle, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { PhaseList } from './PhaseList'
import { ActivityLog } from './ActivityLog'
import { DownloadLogButton } from './DownloadLogButton'
import { OnboardingStatusResponse } from '@/services/onboardingService'
import { usePortfolioStore } from '@/stores/portfolioStore'

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

/**
 * Phase 7.6: Derive UI state from backend status
 */
type UIState = 'running' | 'completed' | 'partial' | 'failed'

function getUIState(status: string | undefined): UIState {
  switch (status) {
    case 'completed':
      return 'completed'
    case 'partial':
      return 'partial'
    case 'failed':
      return 'failed'
    case 'running':
    case 'not_found':
    default:
      return 'running'
  }
}

/**
 * Check if status is terminal (polling should stop)
 */
function isTerminal(status: string | undefined): boolean {
  return ['completed', 'partial', 'failed'].includes(status ?? '')
}

/**
 * Get UI configuration based on state
 */
function getUIConfig(uiState: UIState, portfolioName: string) {
  switch (uiState) {
    case 'completed':
      return {
        icon: CheckCircle,
        iconColor: 'text-green-600',
        iconBg: 'bg-green-100 dark:bg-green-900/20',
        gradient: 'from-green-50 to-emerald-50 dark:from-gray-900 dark:to-gray-800',
        title: 'Portfolio Setup Complete!',
        subtitle: `Your portfolio "${portfolioName}" is ready.`,
        elapsedLabel: 'Total time:',
      }
    case 'partial':
      return {
        icon: AlertTriangle,
        iconColor: 'text-yellow-600',
        iconBg: 'bg-yellow-100 dark:bg-yellow-900/20',
        gradient: 'from-yellow-50 to-amber-50 dark:from-gray-900 dark:to-gray-800',
        title: 'Portfolio Setup Completed with Warnings',
        subtitle: 'Your portfolio is ready, but some data may be incomplete.',
        elapsedLabel: 'Total time:',
      }
    case 'failed':
      return {
        icon: XCircle,
        iconColor: 'text-red-600',
        iconBg: 'bg-red-100 dark:bg-red-900/20',
        gradient: 'from-red-50 to-rose-50 dark:from-gray-900 dark:to-gray-800',
        title: 'Setup Interrupted',
        subtitle: 'We encountered an issue. Some features may have limited data.',
        elapsedLabel: 'Completed in:',
      }
    default:
      return {
        icon: Rocket,
        iconColor: 'text-blue-600',
        iconBg: 'bg-blue-100 dark:bg-blue-900/20',
        gradient: 'from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800',
        title: 'Setting Up Your Portfolio',
        subtitle: 'Analyzing your portfolio in 9 processing phases.',
        elapsedLabel: 'Elapsed:',
      }
  }
}

export interface OnboardingProgressProps {
  status: OnboardingStatusResponse | null
  isLoading?: boolean
  portfolioName?: string
  onRetry?: () => void
}

/**
 * Phase 7.6: Unified progress/completion screen
 *
 * Shows real-time phase progress and activity log while batch is running.
 * When batch completes (or fails), shows the same layout with updated state,
 * preserving all phase information and activity log.
 *
 * Handles all terminal states: completed, partial, failed
 */
export function OnboardingProgress({
  status,
  isLoading = false,
  portfolioName = 'Your Portfolio',
  onRetry,
}: OnboardingProgressProps) {
  const router = useRouter()
  const clearOnboardingSession = usePortfolioStore((state) => state.clearOnboardingSession)
  const onboardingSession = usePortfolioStore((state) => state.onboardingSession)

  // Cache the portfolio name in local state before session is cleared
  // This prevents the name from being lost when clearOnboardingSession() runs
  const sessionPortfolioName = onboardingSession?.portfoliosAdded?.[0]?.portfolioName
  const [cachedPortfolioName, setCachedPortfolioName] = useState<string | null>(null)

  // Cache the portfolio name when we first have it
  useEffect(() => {
    if (sessionPortfolioName && !cachedPortfolioName) {
      setCachedPortfolioName(sessionPortfolioName)
    }
  }, [sessionPortfolioName, cachedPortfolioName])

  // Use cached name, then session name, then prop fallback
  const displayName = cachedPortfolioName || sessionPortfolioName || portfolioName

  const overallProgress = status?.overall_progress
  const percentComplete = overallProgress?.percent_complete ?? 0
  const elapsedSeconds = status?.elapsed_seconds ?? 0
  const phasesCompleted = overallProgress?.phases_completed ?? 0
  const phasesTotal = overallProgress?.phases_total ?? 9

  // Derive UI state from backend status
  const uiState = getUIState(status?.status)
  const terminal = isTerminal(status?.status)
  const config = getUIConfig(uiState, displayName)
  const IconComponent = config.icon

  // Clear onboarding session when reaching terminal state
  // Note: Portfolio name is cached in local state before this runs
  useEffect(() => {
    if (terminal) {
      clearOnboardingSession()
    }
  }, [terminal, clearOnboardingSession])

  // Navigation handler
  const handleContinueToDashboard = () => {
    router.push('/command-center')
  }

  return (
    <div className={`min-h-screen flex items-center justify-center bg-gradient-to-br ${config.gradient} p-4`}>
      <div className="w-full max-w-2xl">
        <Card className="shadow-lg">
          <CardHeader>
            <div className="flex items-start gap-4">
              <div className={`rounded-full p-3 ${config.iconBg}`}>
                {isLoading && !terminal ? (
                  <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
                ) : (
                  <IconComponent className={`h-6 w-6 ${config.iconColor}`} />
                )}
              </div>
              <div className="flex-1">
                <CardTitle>{config.title}</CardTitle>
                <CardDescription>{config.subtitle}</CardDescription>
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
                activityLog={status?.activity_log}
              />
            </div>

            {/* Divider */}
            <div className="border-t" />

            {/* Activity Log Section */}
            <div>
              <h3 className="text-sm font-semibold text-muted-foreground mb-3 uppercase tracking-wide">
                Activity Log
              </h3>
              <ActivityLog
                entries={status?.activity_log ?? []}
                maxHeight="200px"
                autoScroll={!terminal}
              />
            </div>

            {/* Divider */}
            <div className="border-t" />

            {/* Footer Stats */}
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">{config.elapsedLabel}</span>
                <span className="font-medium">{formatElapsed(elapsedSeconds)}</span>
              </div>
              <div className="flex items-center gap-2">
                {terminal ? (
                  <>
                    <span className="text-muted-foreground">Phases:</span>
                    <span className="font-medium">{phasesCompleted}/{phasesTotal} completed</span>
                  </>
                ) : (
                  <>
                    <span className="text-muted-foreground">Overall:</span>
                    <span className="font-medium">{percentComplete}% complete</span>
                  </>
                )}
              </div>
            </div>

            {/* Action Buttons - Only shown in terminal states */}
            {terminal && (
              <>
                <div className="border-t" />
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <DownloadLogButton
                    portfolioId={status?.portfolio_id ?? ''}
                    variant="outline"
                  />
                  {uiState === 'failed' && onRetry && (
                    <Button onClick={onRetry} variant="secondary">
                      Retry Setup
                    </Button>
                  )}
                  <Button onClick={handleContinueToDashboard} className="gap-2">
                    {uiState === 'failed' ? 'View Portfolio Anyway' : 'View Portfolio Dashboard'}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default OnboardingProgress
