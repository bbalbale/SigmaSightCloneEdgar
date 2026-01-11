'use client'

import { useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useOnboardingStatus } from '@/hooks/useOnboardingStatus'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { onboardingService } from '@/services/onboardingService'
import { OnboardingProgress } from '@/components/onboarding/OnboardingProgress'
import { OnboardingStatusUnavailable } from '@/components/onboarding/OnboardingStatusUnavailable'
import { Loader2 } from 'lucide-react'

/**
 * Onboarding Progress Page (Phase 7.6 - Unified Progress/Completion)
 *
 * Route: /onboarding/progress?portfolioId=xxx
 *
 * Shows real-time batch processing status during portfolio setup.
 * Polls the status endpoint every 2 seconds and displays:
 * - Phase-by-phase progress with completion percentages
 * - Activity log with per-symbol/per-date granularity
 * - Same screen transitions to completion/error state without page change
 *
 * Phase 7.6: OnboardingProgress now handles all states (running, completed, partial, failed)
 * in a unified view that preserves context during state transitions.
 */
export default function OnboardingProgressPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const portfolioIdFromUrl = searchParams?.get('portfolioId')

  // Get portfolio info from store as fallback
  const storePortfolioId = usePortfolioStore((state) => state.portfolioId)
  const getSelectedPortfolio = usePortfolioStore((state) => state.getSelectedPortfolio)
  const onboardingSession = usePortfolioStore((state) => state.onboardingSession)

  // Use URL param first, then fall back to store
  const portfolioId = portfolioIdFromUrl || storePortfolioId

  // Get portfolio name from store or onboarding session
  const portfolioName =
    getSelectedPortfolio()?.account_name ||
    getSelectedPortfolio()?.name ||
    onboardingSession?.portfoliosAdded?.[0]?.portfolioName ||
    'Your Portfolio'

  // Hook for polling status
  const { status, isLoading, error, refetch, shouldShowUnavailable } = useOnboardingStatus({
    portfolioId: portfolioId || '',
    pollInterval: 2000,
    enabled: !!portfolioId,
  })

  // Navigation handlers
  const handleRetry = useCallback(() => {
    // Navigate back to upload page to retry
    router.push('/onboarding/upload')
  }, [router])

  const handleRefreshStatus = useCallback(() => {
    refetch()
  }, [refetch])

  const handleViewPortfolio = useCallback(() => {
    router.push('/command-center')
  }, [router])

  // Retry calculations - calls triggerCalculations for existing portfolio
  const handleRetryCalculations = useCallback(async () => {
    if (!portfolioId) return
    await onboardingService.triggerCalculations(portfolioId)
  }, [portfolioId])

  // Redirect if no portfolio ID
  useEffect(() => {
    if (!portfolioId) {
      router.push('/onboarding/upload')
    }
  }, [portfolioId, router])

  // No portfolio ID - redirect in progress
  if (!portfolioId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Initial loading
  if (isLoading && !status) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-muted-foreground">Loading status...</p>
        </div>
      </div>
    )
  }

  // Show unavailable screen after grace period with no running status
  // Grace period: 10+ seconds AND 5+ not_found responses AND never saw "running"
  if (shouldShowUnavailable) {
    return (
      <OnboardingStatusUnavailable
        onRefresh={handleRefreshStatus}
        onViewPortfolio={handleViewPortfolio}
        onRetryCalculations={handleRetryCalculations}
      />
    )
  }

  // Phase 7.6: Unified OnboardingProgress handles all states
  // (running, completed, partial, failed)
  return (
    <OnboardingProgress
      status={status}
      isLoading={isLoading}
      portfolioName={portfolioName}
      onRetry={handleRetry}
    />
  )
}
