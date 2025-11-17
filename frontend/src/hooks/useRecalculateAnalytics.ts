'use client'

import { useState } from 'react'
import { onboardingService } from '@/services/onboardingService'
import { usePortfolioStore } from '@/stores/portfolioStore'

export type RecalculateState = 'idle' | 'triggering' | 'polling' | 'success' | 'error'

interface UseRecalculateAnalyticsReturn {
  state: RecalculateState
  error: string | null
  batchRunId: string | null
  elapsedSeconds: number
  handleRecalculate: () => Promise<void>
  reset: () => void
}

/**
 * Hook for manually triggering batch recalculation of portfolio analytics
 *
 * Use case: Power users who want to refresh analytics after data changes
 * or when testing new features (e.g., Phase 2.7 weekend batch processing)
 */
export function useRecalculateAnalytics(): UseRecalculateAnalyticsReturn {
  const { portfolioId } = usePortfolioStore()
  const [state, setState] = useState<RecalculateState>('idle')
  const [error, setError] = useState<string | null>(null)
  const [batchRunId, setBatchRunId] = useState<string | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null)

  const cleanup = () => {
    if (pollInterval) {
      clearInterval(pollInterval)
      setPollInterval(null)
    }
  }

  const reset = () => {
    cleanup()
    setState('idle')
    setError(null)
    setBatchRunId(null)
    setElapsedSeconds(0)
  }

  const handleRecalculate = async () => {
    if (!portfolioId) {
      console.error('[Recalculate] No portfolio ID found in store')
      setError('No portfolio selected')
      setState('error')
      return
    }

    console.log('[Recalculate] Starting batch for portfolio:', portfolioId)
    setState('triggering')
    setError(null)
    setElapsedSeconds(0)
    cleanup()

    try {
      // Step 1: Trigger batch calculations
      console.log('[Recalculate] Calling triggerCalculations...')
      const response = await onboardingService.triggerCalculations(portfolioId)
      console.log('[Recalculate] Success! Batch run ID:', response.batch_run_id)
      setBatchRunId(response.batch_run_id)
      setState('polling')

      // Step 2: Poll for completion every 3 seconds
      const interval = setInterval(async () => {
        try {
          const status = await onboardingService.getBatchStatus(
            portfolioId,
            response.batch_run_id
          )

          setElapsedSeconds(status.elapsed_seconds || 0)

          if (status.status === 'completed') {
            cleanup()
            setState('success')
            // Auto-reset after 5 seconds
            setTimeout(() => {
              reset()
            }, 5000)
          } else if (status.status === 'failed') {
            cleanup()
            setState('error')
            setError('Batch processing failed. Please try again or contact support.')
          }
        } catch (err) {
          cleanup()
          setState('error')
          setError(getErrorMessage(err))
        }
      }, 3000)

      setPollInterval(interval)
    } catch (err) {
      console.error('[Recalculate] Error occurred:', err)
      console.error('[Recalculate] Error details:', {
        status: (err as any)?.status,
        data: (err as any)?.data,
        message: (err as any)?.message
      })
      setState('error')
      setError(getErrorMessage(err))
    }
  }

  return {
    state,
    error,
    batchRunId,
    elapsedSeconds,
    handleRecalculate,
    reset,
  }
}

/**
 * Extract user-friendly error message from API error
 */
function getErrorMessage(error: any): string {
  if (error?.data?.detail) {
    const detail = error.data.detail
    if (typeof detail === 'object' && detail.message) {
      return detail.message
    }
    if (typeof detail === 'string') {
      return detail
    }
  }

  if (error?.status === 409) {
    return 'Another batch is already running. Please wait for it to complete.'
  }

  if (error?.status === 403) {
    return 'You do not have permission to recalculate this portfolio.'
  }

  if (error?.status === 404) {
    return 'Portfolio not found.'
  }

  return 'Failed to trigger recalculation. Please try again.'
}
