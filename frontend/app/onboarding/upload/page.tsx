'use client'

import { useSearchParams } from 'next/navigation'
import { usePortfolioUpload } from '@/hooks/usePortfolioUpload'
import { PortfolioUploadForm } from '@/components/onboarding/PortfolioUploadForm'
import { UploadProcessing } from '@/components/onboarding/UploadProcessing'
import { UploadSuccess } from '@/components/onboarding/UploadSuccess'
import { ValidationErrors } from '@/components/onboarding/ValidationErrors'

export default function OnboardingUploadPage() {
  const searchParams = useSearchParams()
  const isFromSettings = searchParams?.get('context') === 'settings'
  
  const {
    uploadState,
    batchStatus,
    currentSpinnerItem,
    checklist,
    result,
    error,
    validationErrors,
    handleUpload,
    handleContinueToDashboard,
    handleRetry,
    handleChooseDifferentFile,
  } = usePortfolioUpload()

  // Show validation errors FIRST (CSV format issues)
  if (uploadState === 'validation_error' || (validationErrors && validationErrors.length > 0)) {
    return <ValidationErrors errors={validationErrors || []} onTryAgain={handleChooseDifferentFile} />
  }

  // Show success screen
  if (uploadState === 'success' && result) {
    return (
      <UploadSuccess
        portfolioName={result.portfolio_name}
        positionsImported={result.positions_imported}
        positionsFailed={result.positions_failed}
        checklist={checklist}
        onContinue={handleContinueToDashboard}
        isFromSettings={isFromSettings}
      />
    )
  }

  // Show processing screen for uploading, processing, OR processing errors
  // Note: validation_error is handled above, so this only shows for batch processing errors
  if (uploadState === 'uploading' || uploadState === 'processing' || uploadState === 'error') {
    const processingState: 'uploading' | 'processing' =
      uploadState === 'error' ? 'processing' : uploadState

    return (
      <UploadProcessing
        uploadState={processingState}
        currentSpinnerItem={currentSpinnerItem}
        checklist={checklist}
        error={uploadState === 'error' ? (error ?? undefined) : undefined}
        onTryAgain={uploadState === 'error' ? handleChooseDifferentFile : undefined}
      />
    )
  }

  // Show upload form only for idle state
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
