'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { onboardingService, OnboardingStatusResponse } from '@/services/onboardingService'

/**
 * Options for the useOnboardingStatus hook
 */
export interface UseOnboardingStatusOptions {
  portfolioId: string
  pollInterval?: number  // Default: 2000ms
  enabled?: boolean      // Enable/disable polling
}

/**
 * Return type for the useOnboardingStatus hook
 */
export interface UseOnboardingStatusReturn {
  status: OnboardingStatusResponse | null
  isLoading: boolean
  error: Error | null
  refetch: () => void
  notFoundCount: number  // Track consecutive not_found responses
}

/**
 * Hook for polling onboarding batch processing status
 *
 * Polls the status endpoint every 2 seconds during active processing.
 * Automatically stops polling when status is "completed" or "failed".
 * Tracks consecutive "not_found" responses for UI handling.
 */
export function useOnboardingStatus(options: UseOnboardingStatusOptions): UseOnboardingStatusReturn {
  const { portfolioId, pollInterval = 2000, enabled = true } = options

  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<Error | null>(null)
  const [notFoundCount, setNotFoundCount] = useState<number>(0)

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef<boolean>(true)

  const fetchStatus = useCallback(async () => {
    if (!portfolioId || !enabled) return

    try {
      const response = await onboardingService.getOnboardingStatus(portfolioId)

      if (!isMountedRef.current) return

      setStatus(response)
      setError(null)

      // Track not_found responses
      if (response.status === 'not_found') {
        setNotFoundCount((prev) => prev + 1)
      } else {
        setNotFoundCount(0)
      }

      setIsLoading(false)

      // Stop polling if completed or failed
      if (response.status === 'completed' || response.status === 'failed') {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
      }
    } catch (err) {
      if (!isMountedRef.current) return

      setError(err instanceof Error ? err : new Error('Failed to fetch status'))
      setIsLoading(false)
    }
  }, [portfolioId, enabled])

  const refetch = useCallback(() => {
    setIsLoading(true)
    setNotFoundCount(0)
    fetchStatus()

    // Restart polling if it was stopped (e.g., after completed/failed status)
    if (!pollIntervalRef.current && enabled && portfolioId) {
      pollIntervalRef.current = setInterval(fetchStatus, pollInterval)
    }
  }, [fetchStatus, enabled, portfolioId, pollInterval])

  // Set up polling
  useEffect(() => {
    isMountedRef.current = true

    if (!portfolioId || !enabled) {
      setIsLoading(false)
      return
    }

    // Initial fetch
    fetchStatus()

    // Set up polling interval
    pollIntervalRef.current = setInterval(fetchStatus, pollInterval)

    return () => {
      isMountedRef.current = false
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
  }, [portfolioId, pollInterval, enabled, fetchStatus])

  return {
    status,
    isLoading,
    error,
    refetch,
    notFoundCount,
  }
}

export default useOnboardingStatus
