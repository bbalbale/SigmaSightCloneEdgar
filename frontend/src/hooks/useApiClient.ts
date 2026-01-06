/**
 * useApiClient - Hook for making authenticated API calls with Clerk tokens
 *
 * This hook provides a fetch wrapper that automatically includes Clerk JWT tokens
 * in API requests. Use this hook in React components for all authenticated API calls.
 *
 * IMPORTANT: This hook can only be used inside React components, not in utility functions.
 * See PRD Section 6.2 for the correct pattern.
 *
 * Usage:
 * ```tsx
 * function MyComponent() {
 *   const { authFetch, getAuthHeaders } = useApiClient()
 *
 *   const loadData = async () => {
 *     const response = await authFetch('/api/v1/portfolios')
 *     return response.json()
 *   }
 *
 *   // For SSE connections
 *   const startStream = async () => {
 *     const headers = await getAuthHeaders()
 *     // Use headers for SSE connection...
 *   }
 * }
 * ```
 */

import { useAuth } from '@clerk/nextjs'
import { useCallback } from 'react'

interface UseApiClientReturn {
  /**
   * Authenticated fetch wrapper - adds Authorization header automatically
   */
  authFetch: (url: string, options?: RequestInit) => Promise<Response>

  /**
   * Get authentication headers for manual use (e.g., SSE connections)
   */
  getAuthHeaders: () => Promise<HeadersInit>

  /**
   * Get the current Clerk token directly
   */
  getToken: () => Promise<string | null>

  /**
   * Check if user is authenticated
   */
  isAuthenticated: boolean

  /**
   * Check if auth is still loading
   */
  isLoading: boolean
}

export function useApiClient(): UseApiClientReturn {
  const { getToken, isSignedIn, isLoaded } = useAuth()

  /**
   * Fetch wrapper with automatic Bearer token
   */
  const authFetch = useCallback(
    async (url: string, options?: RequestInit): Promise<Response> => {
      const token = await getToken()

      const headers: HeadersInit = {
        ...options?.headers,
        'Content-Type': 'application/json',
      }

      if (token) {
        ;(headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
      }

      return fetch(url, {
        ...options,
        headers,
      })
    },
    [getToken]
  )

  /**
   * Get headers for manual use (SSE, file uploads, etc.)
   */
  const getAuthHeaders = useCallback(async (): Promise<HeadersInit> => {
    const token = await getToken()
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }
    if (token) {
      ;(headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
    }
    return headers
  }, [getToken])

  /**
   * Get token directly
   */
  const getTokenDirect = useCallback(async (): Promise<string | null> => {
    return await getToken()
  }, [getToken])

  return {
    authFetch,
    getAuthHeaders,
    getToken: getTokenDirect,
    isAuthenticated: isSignedIn ?? false,
    isLoading: !isLoaded,
  }
}

/**
 * Type for components that need auth context
 */
export type ApiClientContext = ReturnType<typeof useApiClient>
