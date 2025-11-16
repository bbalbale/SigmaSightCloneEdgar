'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { onboardingService } from '@/services/onboardingService'
import { setPortfolioState } from '@/stores/portfolioStore'

export type UploadState = 'idle' | 'uploading' | 'processing' | 'success' | 'error'

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
  handleRetry: () => void
  handleChooseDifferentFile: () => void
}

/**
 * Hook for handling portfolio CSV upload and batch processing
 */
export function usePortfolioUpload(): UsePortfolioUploadReturn {
  const router = useRouter()
  const [uploadState, setUploadState] = useState<UploadState>('idle')
  const [batchStatus, setBatchStatus] = useState<string>('idle')
  const [currentSpinnerItem, setCurrentSpinnerItem] = useState<string | null>(null)
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

  // Refs for cleanup
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const currentFileRef = useRef<File | null>(null)
  const currentPortfolioNameRef = useRef<string>('')
  const currentAccountNameRef = useRef<string>('')
  const currentAccountTypeRef = useRef<string>('')
  const currentEquityBalanceRef = useRef<number>(0)

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

    try {
      // PHASE 2A: CSV Upload (10-30 seconds)
      const formData = new FormData()
      formData.append('portfolio_name', portfolioName)
      formData.append('account_name', accountName)
      formData.append('account_type', accountType)
      formData.append('equity_balance', equityBalance.toString())
      formData.append('csv_file', file)  // Backend expects 'csv_file', not 'file'

      const uploadResponse = await onboardingService.createPortfolio(formData)

      // Store portfolio ID in Zustand
      setPortfolioState(uploadResponse.portfolio_id, uploadResponse.portfolio_name)
      setResult({
        portfolio_id: uploadResponse.portfolio_id,
        portfolio_name: uploadResponse.portfolio_name,
        positions_imported: uploadResponse.positions_imported,
        positions_failed: uploadResponse.positions_failed,
        total_positions: uploadResponse.total_positions,
      })

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
            // DO NOT auto-navigate - wait for user to click "Continue to Dashboard" button
          }
        } catch (error) {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current)
          }
          setUploadState('error')
          setError(getErrorMessage(error))
        }
      }, 3000) // Poll every 3 seconds
    } catch (err: any) {
      setUploadState('error')

      // Check if it's a validation error
      if (err?.data?.detail?.errors || err?.data?.error?.details?.errors) {
        const rawErrors = err.data?.detail?.errors || err.data?.error?.details?.errors || []

        // Flatten nested errors: each row may have multiple errors
        const flattenedErrors: ValidationError[] = []
        rawErrors.forEach((rowError: any) => {
          if (rowError.errors && Array.isArray(rowError.errors)) {
            // Backend format: { row, symbol, errors: [{code, message, field}] }
            rowError.errors.forEach((err: any) => {
              flattenedErrors.push({
                row: rowError.row,
                symbol: rowError.symbol,
                error_code: err.code || err.error_code || 'UNKNOWN',
                message: err.message,
                field: err.field,
              })
            })
          } else {
            // Already flat format: { row, symbol, code, message, field }
            flattenedErrors.push({
              row: rowError.row,
              symbol: rowError.symbol,
              error_code: rowError.code || rowError.error_code || 'UNKNOWN',
              message: rowError.message,
              field: rowError.field,
            })
          }
        })

        setValidationErrors(flattenedErrors)
        setError('CSV validation failed. Please fix the errors below.')
      } else {
        setError(getErrorMessage(err))
      }
    }
  }

  const handleContinueToDashboard = () => {
    router.push('/portfolio')
  }

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
    handleRetry,
    handleChooseDifferentFile,
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
