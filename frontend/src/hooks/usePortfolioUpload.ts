'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { onboardingService } from '@/services/onboardingService'
import { setPortfolioState, usePortfolioStore } from '@/stores/portfolioStore'

export type UploadState = 'idle' | 'uploading' | 'processing' | 'success' | 'validation_error' | 'error'

export interface ValidationError {
  row: number
  symbol?: string
  error_code: string
  message: string
  field?: string
}

export interface UploadResult {
  portfolio_id: string
  portfolio_name: string
  positions_imported: number
  positions_failed: number
  total_positions: number
}

export interface ChecklistState {
  portfolio_created: boolean
  positions_imported: boolean
  symbol_extraction: boolean
  security_enrichment: boolean
  price_bootstrap: boolean
  market_data_collection: boolean
  pnl_calculation: boolean
  position_values: boolean
  market_beta: boolean
  ir_beta: boolean
  factor_spread: boolean
  factor_ridge: boolean
  sector_analysis: boolean
  volatility: boolean
  correlations: boolean
}

interface UsePortfolioUploadReturn {
  uploadState: UploadState
  batchStatus: string
  currentSpinnerItem: string | null
  checklist: ChecklistState
  result: UploadResult | null
  error: string | null
  validationErrors: ValidationError[] | null
  handleUpload: (portfolioName: string, accountName: string, accountType: string, equityBalance: number, file: File) => Promise<void>
  handleContinueToDashboard: () => void
  handleAddAnother: () => void
  handleRetry: () => void
  handleChooseDifferentFile: () => void
  // Session management
  startSession: () => void
  isInSession: boolean
}

/**
 * Hook for handling portfolio CSV upload and batch processing
 * Now with session management for multi-portfolio onboarding
 */
export function usePortfolioUpload(): UsePortfolioUploadReturn {
  const router = useRouter()
  const [uploadState, setUploadState] = useState<UploadState>('idle')
  const [batchStatus, setBatchStatus] = useState<string>('idle')
  const [currentSpinnerItem, setCurrentSpinnerItem] = useState<string | null>(null)

  // Session management from store
  const {
    onboardingSession,
    startOnboardingSession,
    addToOnboardingSession,
    updateSessionPortfolioStatus,
    completeOnboardingSession,
    resetForNextUpload,
    setBatchRunning,
    isInOnboardingSession
  } = usePortfolioStore()
  const [checklist, setChecklist] = useState<ChecklistState>({
    portfolio_created: false,
    positions_imported: false,
    symbol_extraction: false,
    security_enrichment: false,
    price_bootstrap: false,
    market_data_collection: false,
    pnl_calculation: false,
    position_values: false,
    market_beta: false,
    ir_beta: false,
    factor_spread: false,
    factor_ridge: false,
    sector_analysis: false,
    volatility: false,
    correlations: false,
  })
  const [result, setResult] = useState<UploadResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<ValidationError[] | null>(null)

  // Refs for cleanup and tracking
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const currentFileRef = useRef<File | null>(null)
  const currentPortfolioNameRef = useRef<string>('')
  const currentAccountNameRef = useRef<string>('')
  const currentAccountTypeRef = useRef<string>('')
  const currentEquityBalanceRef = useRef<number>(0)
  const currentUploadPortfolioIdRef = useRef<string | null>(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

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

    // Mark batch as running in session (blocks "Add Another" button)
    if (isInOnboardingSession()) {
      setBatchRunning(true)
    }

    try {
      // PHASE 2A: CSV Upload (10-30 seconds)
      const formData = new FormData()
      formData.append('portfolio_name', portfolioName)
      formData.append('account_name', accountName)
      formData.append('account_type', accountType)
      formData.append('equity_balance', equityBalance.toString())
      formData.append('csv_file', file)  // Backend expects 'csv_file', not 'file'

      const uploadResponse = await onboardingService.createPortfolio(formData)

      // Track current upload for error handling
      currentUploadPortfolioIdRef.current = uploadResponse.portfolio_id

      // Store portfolio ID in Zustand
      setPortfolioState(uploadResponse.portfolio_id, uploadResponse.portfolio_name)
      setResult({
        portfolio_id: uploadResponse.portfolio_id,
        portfolio_name: uploadResponse.portfolio_name,
        positions_imported: uploadResponse.positions_imported,
        positions_failed: uploadResponse.positions_failed,
        total_positions: uploadResponse.total_positions,
      })

      // Add to onboarding session with 'processing' status
      if (isInOnboardingSession()) {
        addToOnboardingSession({
          portfolioId: uploadResponse.portfolio_id,
          portfolioName: uploadResponse.portfolio_name,
          accountName: accountName,
          positionsCount: uploadResponse.positions_imported,
        }, 'processing')
      }

      // Mark first two items complete
      setChecklist((prev) => ({
        ...prev,
        portfolio_created: true,
        positions_imported: true,
      }))

      // PHASE 2B: Batch Processing (30-60 seconds)
      setUploadState('processing')

      const calcResponse = await onboardingService.triggerCalculations(uploadResponse.portfolio_id)
      setBatchStatus(calcResponse.status)

      // Start polling for batch status
      pollIntervalRef.current = setInterval(async () => {
        try {
          const status = await onboardingService.getBatchStatus(
            uploadResponse.portfolio_id,
            calcResponse.batch_run_id
          )

          setBatchStatus(status.status)

          // Rotate spinner through items to show activity
          // Don't flip items to ✅ until entire batch completes
          const elapsed = status.elapsed_seconds || 0
          const checklistItems = [
            'symbol_extraction',
            'security_enrichment',
            'price_bootstrap',
            'market_data_collection',
            'pnl_calculation',
            'position_values',
            'market_beta',
            'ir_beta',
            'factor_spread',
            'factor_ridge',
            'sector_analysis',
            'volatility',
            'correlations',
          ]
          // Rotate through items every 3 seconds
          const currentItemIndex = Math.floor(elapsed / 3) % checklistItems.length
          setCurrentSpinnerItem(checklistItems[currentItemIndex])

          // Check if complete
          if (status.status === 'completed') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
            }
            // NOW flip all items to ✅
            setChecklist({
              portfolio_created: true,
              positions_imported: true,
              symbol_extraction: true,
              security_enrichment: true,
              price_bootstrap: true,
              market_data_collection: true,
              pnl_calculation: true,
              position_values: true,
              market_beta: true,
              ir_beta: true,
              factor_spread: true,
              factor_ridge: true,
              sector_analysis: true,
              volatility: true,
              correlations: true,
            })
            setUploadState('success')

            // Update session status to success and unblock "Add Another"
            if (isInOnboardingSession()) {
              updateSessionPortfolioStatus(uploadResponse.portfolio_id, 'success', {
                positionsCount: uploadResponse.positions_imported
              })
              setBatchRunning(false)
            }
            // Clear current upload tracking on success
            currentUploadPortfolioIdRef.current = null
            // DO NOT auto-navigate - wait for user to click "Continue to Dashboard" button
          }
        } catch (error) {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
          }
          setUploadState('error')
          setError(getErrorMessage(error))

          // Update session status to failed and unblock "Add Another"
          if (isInOnboardingSession()) {
            updateSessionPortfolioStatus(uploadResponse.portfolio_id, 'failed', {
              error: getErrorMessage(error)
            })
            setBatchRunning(false)
          }
        }
      }, 3000) // Poll every 3 seconds
    } catch (err: any) {
      // Check if it's a validation error (CSV format issues)
      // Try multiple paths for backward compatibility with different FastAPI response structures
      const nestedErrors = err?.data?.error?.details?.error?.details?.errors  // Current onboarding endpoint
      const detailErrors = err?.data?.detail?.errors  // FastAPI default validation errors
      const shallowErrors = err?.data?.error?.details?.errors  // Older onboarding format

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
        // Backend now returns errors in flat format: { row, symbol, code, message, field }
        const validationErrors: ValidationError[] = rawErrors.map((error: any) => ({
          row: error.row,
          symbol: error.symbol,
          error_code: error.code || error.error_code || 'UNKNOWN',
          message: error.message,
          field: error.field,
        }))

        setValidationErrors(validationErrors)
        setError('CSV validation failed. Please fix the errors below.')
        setUploadState('validation_error')  // Set validation_error state for CSV issues
      } else {
        // Processing or network errors
        setError(errorMessage)
        setUploadState('error')  // Set error state for processing/network issues
      }

      // Update session: mark portfolio as failed if it was added, unblock session
      if (isInOnboardingSession()) {
        // If portfolio was created but triggerCalculations failed, update status
        if (currentUploadPortfolioIdRef.current) {
          updateSessionPortfolioStatus(currentUploadPortfolioIdRef.current, 'failed', {
            error: errorMessage
          })
        }
        setBatchRunning(false)
      }
      // Clear current upload tracking
      currentUploadPortfolioIdRef.current = null
    }
  }

  const handleContinueToDashboard = () => {
    // Complete the onboarding session if active
    if (isInOnboardingSession()) {
      completeOnboardingSession()
    }
    router.push('/command-center')
  }

  const handleAddAnother = () => {
    // Reset local state for next upload
    setUploadState('idle')
    setError(null)
    setValidationErrors(null)
    setResult(null)
    setCurrentSpinnerItem(null)
    setChecklist({
      portfolio_created: false,
      positions_imported: false,
      symbol_extraction: false,
      security_enrichment: false,
      price_bootstrap: false,
      market_data_collection: false,
      pnl_calculation: false,
      position_values: false,
      market_beta: false,
      ir_beta: false,
      factor_spread: false,
      factor_ridge: false,
      sector_analysis: false,
      volatility: false,
      correlations: false,
    })
    currentFileRef.current = null

    // Reset session state for next upload (keeps session active)
    if (isInOnboardingSession()) {
      resetForNextUpload()
    }
  }

  // Start a new onboarding session (memoized for stable reference)
  const startSession = useCallback(() => {
    if (!isInOnboardingSession()) {
      startOnboardingSession()
    }
  }, [isInOnboardingSession, startOnboardingSession])

  const handleRetry = () => {
    // Reset all state before retry
    setUploadState('idle')
    setError(null)
    setValidationErrors(null)
    setResult(null)
    setCurrentSpinnerItem(null)
    setChecklist({
      portfolio_created: false,
      positions_imported: false,
      symbol_extraction: false,
      security_enrichment: false,
      price_bootstrap: false,
      market_data_collection: false,
      pnl_calculation: false,
      position_values: false,
      market_beta: false,
      ir_beta: false,
      factor_spread: false,
      factor_ridge: false,
      sector_analysis: false,
      volatility: false,
      correlations: false,
    })

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
    // Reset all state when choosing different file
    setUploadState('idle')
    setError(null)
    setValidationErrors(null)
    setResult(null)
    setCurrentSpinnerItem(null)
    setChecklist({
      portfolio_created: false,
      positions_imported: false,
      symbol_extraction: false,
      security_enrichment: false,
      price_bootstrap: false,
      market_data_collection: false,
      pnl_calculation: false,
      position_values: false,
      market_beta: false,
      ir_beta: false,
      factor_spread: false,
      factor_ridge: false,
      sector_analysis: false,
      volatility: false,
      correlations: false,
    })
    currentFileRef.current = null
  }

  return {
    uploadState,
    batchStatus,
    currentSpinnerItem,
    checklist,
    result,
    error,
    validationErrors,
    handleUpload,
    handleContinueToDashboard,
    handleAddAnother,
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
