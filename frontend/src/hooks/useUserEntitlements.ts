/**
 * useUserEntitlements - Hook for fetching user entitlements and account status
 *
 * Fetches data from /api/v1/auth/me which includes:
 * - User profile info
 * - Tier (free/paid)
 * - Invite validation status
 * - Portfolio count and limits
 * - AI message usage and limits
 */

import { useState, useEffect, useCallback } from 'react'
import { useUser } from '@clerk/nextjs'
import { apiClient } from '@/services/apiClient'

export interface UserEntitlements {
  // Identity
  id: string
  email: string
  fullName: string | null

  // Account Status
  isActive: boolean
  inviteValidated: boolean
  createdAt: string

  // Subscription
  tier: 'free' | 'paid'

  // Portfolio Info
  portfolioId: string | null
  portfolioCount: number
  portfolioLimit: number
  canCreatePortfolio: boolean

  // AI Message Limits
  aiMessagesUsed: number
  aiMessagesLimit: number
  aiMessagesRemaining: number
  canSendAiMessage: boolean

  // Derived
  shouldShowUpgrade: boolean
}

interface UseUserEntitlementsReturn {
  entitlements: UserEntitlements | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export function useUserEntitlements(): UseUserEntitlementsReturn {
  const { isSignedIn, isLoaded } = useUser()
  const [entitlements, setEntitlements] = useState<UserEntitlements | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchEntitlements = useCallback(async () => {
    if (!isLoaded || !isSignedIn) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)

      // Response shape matches backend UserMeResponse schema
      const response = await apiClient.get<{
        id: string
        email: string
        full_name: string | null
        is_active: boolean
        created_at: string
        tier: 'free' | 'paid'
        invite_validated: boolean
        portfolio_id: string | null
        portfolio_count: number
        limits: {
          max_portfolios: number
          max_ai_messages: number
          ai_messages_used: number
          ai_messages_remaining: number
        }
      }>('/api/v1/auth/me')

      const { limits } = response

      setEntitlements({
        id: response.id,
        email: response.email,
        fullName: response.full_name,
        isActive: response.is_active,
        inviteValidated: response.invite_validated,
        createdAt: response.created_at,
        tier: response.tier,
        portfolioId: response.portfolio_id,
        portfolioCount: response.portfolio_count,
        portfolioLimit: limits.max_portfolios,
        canCreatePortfolio: response.portfolio_count < limits.max_portfolios,
        aiMessagesUsed: limits.ai_messages_used,
        aiMessagesLimit: limits.max_ai_messages,
        aiMessagesRemaining: limits.ai_messages_remaining,
        canSendAiMessage: limits.ai_messages_used < limits.max_ai_messages,
        shouldShowUpgrade: response.tier === 'free',
      })
    } catch (err) {
      console.error('Failed to fetch user entitlements:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch account info')
    } finally {
      setLoading(false)
    }
  }, [isLoaded, isSignedIn])

  useEffect(() => {
    fetchEntitlements()
  }, [fetchEntitlements])

  return {
    entitlements,
    loading,
    error,
    refetch: fetchEntitlements,
  }
}
