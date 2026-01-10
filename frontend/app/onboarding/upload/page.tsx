'use client'

import { useEffect, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { usePortfolioUpload } from '@/hooks/usePortfolioUpload'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { PortfolioUploadForm } from '@/components/onboarding/PortfolioUploadForm'
import { ValidationErrors } from '@/components/onboarding/ValidationErrors'
import { Loader2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function OnboardingUploadPage() {
  const searchParams = useSearchParams()
  const isFromSettings = searchParams?.get('context') === 'settings'

  // Get session cleanup function directly from store for unmount
  const clearOnboardingSession = usePortfolioStore((state) => state.clearOnboardingSession)

  const {
    uploadState,
    error,
    validationErrors,
    handleUpload,
    handleRetry,
    handleChooseDifferentFile,
    startSession,
  } = usePortfolioUpload()

  // Memoize startSession call to prevent effect re-runs
  const initSession = useCallback(() => {
    if (!isFromSettings) {
      startSession()
    }
  }, [isFromSettings, startSession])

  // Start onboarding session on mount (only for normal onboarding, not from Settings)
  useEffect(() => {
    initSession()

    // Cleanup: clear entire session on unmount to prevent stale data
    return () => {
      clearOnboardingSession()
    }
  }, [initSession, clearOnboardingSession])

  // Show validation errors (CSV format issues)
  if (uploadState === 'validation_error' || (validationErrors && validationErrors.length > 0)) {
    return <ValidationErrors errors={validationErrors || []} onTryAgain={handleChooseDifferentFile} />
  }

  // Show brief uploading state (before redirect to progress page)
  if (uploadState === 'uploading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800 p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardHeader>
            <div className="flex items-center gap-4">
              <div className="rounded-full p-3 bg-blue-100 dark:bg-blue-900/20">
                <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
              </div>
              <div>
                <CardTitle>Uploading Portfolio...</CardTitle>
                <CardDescription>Validating your CSV file</CardDescription>
              </div>
            </div>
          </CardHeader>
        </Card>
      </div>
    )
  }

  // Show error state with retry option
  if (uploadState === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800 p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardHeader>
            <CardTitle className="text-red-600">Upload Failed</CardTitle>
            <CardDescription>{error || 'An unexpected error occurred'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleChooseDifferentFile} className="w-full">
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Show upload form (idle state)
  return (
    <PortfolioUploadForm
      onUpload={handleUpload}
      disabled={false}
      error={null}
      onRetry={handleRetry}
      isFromSettings={isFromSettings}
    />
  )
}
