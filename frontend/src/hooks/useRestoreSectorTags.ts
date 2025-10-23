import { useState } from 'react'
import { restoreSectorTags, RestoreSectorTagsResponse } from '@/services/portfolioService'

interface UseRestoreSectorTagsReturn {
  /**
   * Restore sector tags for a portfolio
   * @param portfolioId - UUID of the portfolio
   * @returns Promise with restoration results
   */
  restoreTags: (portfolioId: string) => Promise<RestoreSectorTagsResponse>

  /**
   * Loading state - true while restoration is in progress
   */
  loading: boolean

  /**
   * Error message if restoration failed
   */
  error: string | null

  /**
   * Results from the last successful restoration
   */
  lastResult: RestoreSectorTagsResponse | null
}

/**
 * Hook for restoring sector tags to all positions in a portfolio
 *
 * This hook manages the state for the sector tag restoration operation,
 * including loading states, errors, and results.
 *
 * Example usage:
 * ```tsx
 * const { restoreTags, loading, error, lastResult } = useRestoreSectorTags()
 *
 * const handleRestore = async () => {
 *   try {
 *     const result = await restoreTags(portfolioId)
 *     console.log(`Tagged ${result.positions_tagged} positions`)
 *     // Refresh UI to show new tags
 *     refreshPositions()
 *   } catch (err) {
 *     console.error('Failed to restore tags:', err)
 *   }
 * }
 * ```
 */
export function useRestoreSectorTags(): UseRestoreSectorTagsReturn {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<RestoreSectorTagsResponse | null>(null)

  const restoreTags = async (portfolioId: string): Promise<RestoreSectorTagsResponse> => {
    setLoading(true)
    setError(null)

    try {
      const result = await restoreSectorTags(portfolioId)
      setLastResult(result)
      setLoading(false)
      return result
    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to restore sector tags'
      setError(errorMessage)
      setLoading(false)
      throw err
    }
  }

  return {
    restoreTags,
    loading,
    error,
    lastResult
  }
}
