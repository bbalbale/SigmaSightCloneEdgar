'use client'

import { useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { onboardingService } from '@/services/onboardingService'
import { setPortfolioState, usePortfolioStore } from '@/stores/portfolioStore'

export type UploadState = 'idle' | 'uploading' | 'validation_error' | 'error'

export interface ValidationError {
  row: number
  symbol?: string
  error_code: string
  message: string
  field?: string
}

interface UsePortfolioUploadReturn {
  uploadState: UploadState
  error: string | null
  validationErrors: ValidationError[] | null
  handleUpload: (portfolioName: string, accountName: string, accountType: string, equityBalance: number, file: File) => Promise<void>
  handleRetry: () => void
  handleChooseDifferentFile: () => void
  // Session management
  startSession: () => void
  isInSession: boolean
}

/**
 * Hook for handling portfolio CSV upload
 * After successful upload and triggering calculations, redirects to /onboarding/progress
 * for real-time status tracking (Phase 7.3)
 */
export function usePortfolioUpload(): UsePortfolioUploadReturn {
  const router = useRouter()
  const [uploadState, setUploadState] = useState<UploadState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<ValidationError[] | null>(null)

  // Session management from store
  const {
    startOnboardingSession,
    addToOnboardingSession,
    setBatchRunning,
    isInOnboardingSession
  } = usePortfolioStore()

  // Refs for retry functionality
  const currentFileRef = useRef<File | null>(null)
  const currentPortfolioNameRef = useRef<string>('')
  const currentAccountNameRef = useRef<string>('')
  const currentAccountTypeRef = useRef<string>('')
  const currentEquityBalanceRef = useRef<number>(0)

  const handleUpload = async (portfolioName: string, accountName: string, accountType: string, equityBalance: number, file: File) => {
    // Store for retry
    currentFileRef.current = file
    currentPortfolioNameRef.current = portfolioName
    currentAccountNameRef.current = accountName
    currentAccountTypeRef.current = accountType
    currentEquityBalanceRef.current = equityBalance

    setUploadState('uploading')
    setError(null)
    setValidationErrors(null)

    // Mark batch as running in session
    if (isInOnboardingSession()) {
      setBatchRunning(true)
    }

    // Track if portfolio was created (for error handling)
    let createdPortfolioId: string | null = null

    try {
      // PHASE 1: CSV Upload and Portfolio Creation
      const formData = new FormData()
      formData.append('portfolio_name', portfolioName)
      formData.append('account_name', accountName)
      formData.append('account_type', accountType)
      formData.append('equity_balance', equityBalance.toString())
      formData.append('csv_file', file)

      const uploadResponse = await onboardingService.createPortfolio(formData)
      createdPortfolioId = uploadResponse.portfolio_id

      // Store portfolio ID in Zustand
      setPortfolioState(uploadResponse.portfolio_id, uploadResponse.portfolio_name)

      // Add to onboarding session with 'processing' status
      if (isInOnboardingSession()) {
        addToOnboardingSession({
          portfolioId: uploadResponse.portfolio_id,
          portfolioName: uploadResponse.portfolio_name,
          accountName: accountName,
          positionsCount: uploadResponse.positions_imported,
        }, 'processing')
      }

      // PHASE 2: Trigger batch calculations
      await onboardingService.triggerCalculations(uploadResponse.portfolio_id)

      // PHASE 3: Redirect to new progress page for real-time status tracking
      // The progress page handles polling, completion, errors, and log downloads
      router.push(`/onboarding/progress?portfolioId=${uploadResponse.portfolio_id}`)

    } catch (err: unknown) {
      // P0 FIX: If portfolio was created but triggerCalculations failed,
      // redirect to progress page anyway - it will show error/retry options.
      // This prevents the 409 "portfolio already exists" loop on retry.
      if (createdPortfolioId) {
        console.warn('Portfolio created but triggerCalculations failed, redirecting to progress page')
        router.push(`/onboarding/progress?portfolioId=${createdPortfolioId}`)
        return
      }

      // Unblock session on error (only if we're NOT redirecting)
      if (isInOnboardingSession()) {
        setBatchRunning(false)
      }

      // Check if it's a validation error (CSV format issues)
      const errorObj = err as { data?: { error?: { details?: { error?: { details?: { errors?: unknown[] } }, errors?: unknown[] } }, detail?: { errors?: unknown[] } } }
      const nestedErrors = errorObj?.data?.error?.details?.error?.details?.errors
      const detailErrors = errorObj?.data?.detail?.errors
      const shallowErrors = errorObj?.data?.error?.details?.errors

      // Pick the first non-empty error array we find
      const rawErrors = (nestedErrors && Array.isArray(nestedErrors) && nestedErrors.length > 0)
        ? nestedErrors
        : (detailErrors && Array.isArray(detailErrors) && detailErrors.length > 0)
        ? detailErrors
        : (shallowErrors && Array.isArray(shallowErrors) && shallowErrors.length > 0)
        ? shallowErrors
        : null

      const errorMessage = getErrorMessage(err)

      if (rawErrors) {
        // Backend returns errors in format: { row, symbol, code, message, field }
        const parsedErrors: ValidationError[] = rawErrors.map((error: unknown) => {
          const e = error as { row?: number; symbol?: string; code?: string; error_code?: string; message?: string; field?: string }
          return {
            row: e.row ?? 0,
            symbol: e.symbol,
            error_code: e.code || e.error_code || 'UNKNOWN',
            message: e.message ?? 'Unknown error',
            field: e.field,
          }
        })

        setValidationErrors(parsedErrors)
        setError('CSV validation failed. Please fix the errors below.')
        setUploadState('validation_error')
      } else {
        setError(errorMessage)
        setUploadState('error')
      }
    }
  }

  // Start a new onboarding session (memoized for stable reference)
  const startSession = useCallback(() => {
    if (!isInOnboardingSession()) {
      startOnboardingSession()
    }
  }, [isInOnboardingSession, startOnboardingSession])

  const handleRetry = () => {
    // Reset state and retry with stored values
    setUploadState('idle')
    setError(null)
    setValidationErrors(null)

    if (currentFileRef.current) {
      handleUpload(
        currentPortfolioNameRef.current,
        currentAccountNameRef.current,
        currentAccountTypeRef.current,
        currentEquityBalanceRef.current,
        currentFileRef.current
      )
    }
  }

  const handleChooseDifferentFile = () => {
    // Reset state to show upload form again
    setUploadState('idle')
    setError(null)
    setValidationErrors(null)
    currentFileRef.current = null
  }

  return {
    uploadState,
    error,
    validationErrors,
    handleUpload,
    handleRetry,
    handleChooseDifferentFile,
    // Session management
    startSession,
    isInSession: isInOnboardingSession(),
  }
}

/**
 * Extract user-friendly error message from API error
 */
function getErrorMessage(error: any): string {
  // Handle structured error responses from backend
  if (error?.data?.detail) {
    const detail = error.data.detail

    // If detail has a message property (structured error)
    if (typeof detail === 'object' && detail.message) {
      return detail.message
    }

    // If detail is a string
    if (typeof detail === 'string') {
      return detail
    }
  }

  // Handle status codes with friendly messages
  if (error?.status) {
    switch (error.status) {
      case 400:
        return 'There was a problem with your CSV file. Please check the errors below.'
      case 409:
        return 'You already have a portfolio. Please contact support if you need help.'
      case 500:
        return "We couldn't prepare your portfolio for analysis. This usually means a network issue fetching market data."
      default:
        return `Upload failed (${error.status}). Please try again.`
    }
  }

  // Network errors
  if (error?.name === 'NetworkError') {
    return "Couldn't connect to server. Please check your internet connection and try again."
  }

  // Default fallback
  return 'Upload failed. Please try again.'
}
