'use client'

import { useRouter } from 'next/navigation'
import { usePortfolioUpload } from '@/hooks/usePortfolioUpload'
import { PortfolioUploadForm } from '@/components/onboarding/PortfolioUploadForm'
import { UploadProcessing } from '@/components/onboarding/UploadProcessing'
import { UploadSuccess } from '@/components/onboarding/UploadSuccess'
import { ValidationErrors } from '@/components/onboarding/ValidationErrors'

export default function OnboardingUploadPage() {
  const router = useRouter()
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

  // Show validation errors if present
  if (validationErrors && validationErrors.length > 0) {
    return <ValidationErrors errors={validationErrors} onTryAgain={handleChooseDifferentFile} />
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
      />
    )
  }

  // Show processing screen for uploading, processing, OR error
  if (uploadState === 'uploading' || uploadState === 'processing' || uploadState === 'error') {
    const processingState: 'uploading' | 'processing' =
      uploadState === 'error' ? 'processing' : uploadState

    return (
      <UploadProcessing
        uploadState={processingState}
        currentSpinnerItem={currentSpinnerItem}
        checklist={checklist}
        error={uploadState === 'error' ? error : undefined}
        onTryAgain={uploadState === 'error' ? () => router.push('/onboarding/upload') : undefined}
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
    />
  )
}
