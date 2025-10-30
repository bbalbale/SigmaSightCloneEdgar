'use client'

import { usePortfolioUpload } from '@/hooks/usePortfolioUpload'
import { PortfolioUploadForm } from '@/components/onboarding/PortfolioUploadForm'
import { UploadProcessing } from '@/components/onboarding/UploadProcessing'
import { UploadSuccess } from '@/components/onboarding/UploadSuccess'
import { ValidationErrors } from '@/components/onboarding/ValidationErrors'

export default function OnboardingUploadPage() {
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
        positionsCount={result.positions_count}
        checklist={checklist}
        onContinue={handleContinueToDashboard}
      />
    )
  }

  // Show processing screen (uploading or batch processing)
  if (uploadState === 'uploading' || uploadState === 'processing') {
    return (
      <UploadProcessing
        uploadState={uploadState}
        currentSpinnerItem={currentSpinnerItem}
        checklist={checklist}
      />
    )
  }

  // Show upload form (idle state)
  return (
    <PortfolioUploadForm
      onUpload={handleUpload}
      disabled={uploadState !== 'idle'}
    />
  )
}
