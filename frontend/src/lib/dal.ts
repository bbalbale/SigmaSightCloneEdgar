// Data Access Layer for server-side data fetching
// This file should only be imported in Server Components

import 'server-only'
import { cache } from 'react'
import { cookies } from 'next/headers'
import {
  User,
  Portfolio,
  Position,
  FactorExposure,
  PortfolioAnalytics,
  TargetPrice,
  Strategy,
  Tag,
  Session
} from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://sigmasight-be-production.up.railway.app'

// Helper function to get auth token from cookies
async function getAuthToken(): Promise<string | null> {
  const cookieStore = await cookies()
  // Check both possible cookie names for backward compatibility
  return cookieStore.get('access_token')?.value ||
         cookieStore.get('sigmasight_session')?.value ||
         null
}

// Cache the session verification to avoid multiple calls
export const verifySession = cache(async (): Promise<Session | null> => {
  const token = await getAuthToken()

  if (!token) {
    return null
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      cache: 'no-store'
    })

    if (!response.ok) {
      console.error('Session verification failed:', response.status)
      return null
    }

    const user = await response.json()
    return { user, token }
  } catch (error) {
    console.error('Session verification error:', error)
    return null
  }
})

// Authenticated fetch helper
async function authenticatedFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const session = await verifySession()

  if (!session) {
    throw new Error('Unauthorized - Please log in')
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.token}`,
      ...options.headers,
    },
    cache: options.cache || 'no-store'
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || errorData.error || `API Error: ${response.status}`)
  }

  return response.json()
}

// Portfolio fetching functions
export async function fetchUserPortfolios(): Promise<Portfolio[]> {
  try {
    const response = await authenticatedFetch<Portfolio[]>('/api/v1/data/portfolios')
    return Array.isArray(response) ? response : []
  } catch (error) {
    console.error('Failed to fetch portfolios:', error)
    // Return empty array instead of throwing to allow page to render
    return []
  }
}

export async function fetchPortfolioComplete(portfolioId: string): Promise<Portfolio | null> {
  try {
    const response = await authenticatedFetch<any>(
      `/api/v1/data/portfolio/${portfolioId}/complete`
    )
    return response
  } catch (error) {
    console.error('Failed to fetch complete portfolio:', error)
    return null
  }
}

// Position fetching functions
export async function fetchPositionDetails(portfolioId?: string): Promise<Position[]> {
  try {
    const endpoint = portfolioId
      ? `/api/v1/data/positions/details?portfolio_id=${portfolioId}`
      : '/api/v1/data/positions/details'

    const response = await authenticatedFetch<any>(endpoint)

    // Handle both array response and object with positions array
    if (Array.isArray(response)) {
      return response
    } else if (response.positions && Array.isArray(response.positions)) {
      return response.positions
    }
    return []
  } catch (error) {
    console.error('Failed to fetch position details:', error)
    return []
  }
}

export async function fetchPublicPositions(portfolioId?: string): Promise<Position[]> {
  try {
    const positions = await fetchPositionDetails(portfolioId)
    // Filter for public positions (non-options)
    return positions.filter(position =>
      position.position_type === 'LONG' || position.position_type === 'SHORT'
    )
  } catch (error) {
    console.error('Failed to fetch public positions:', error)
    return []
  }
}

export async function fetchPrivatePositions(portfolioId?: string): Promise<Position[]> {
  try {
    const positions = await fetchPositionDetails(portfolioId)
    // Filter for private positions (assuming these are marked differently or in a separate field)
    // For now, return empty array as private positions need specific identification
    return positions.filter(position =>
      position.investment_class === 'PRIVATE'
    )
  } catch (error) {
    console.error('Failed to fetch private positions:', error)
    return []
  }
}

export async function fetchOptionsPositions(portfolioId?: string): Promise<Position[]> {
  try {
    const positions = await fetchPositionDetails(portfolioId)
    // Filter for options positions
    return positions.filter(position =>
      ['LC', 'LP', 'SC', 'SP'].includes(position.position_type)
    )
  } catch (error) {
    console.error('Failed to fetch options positions:', error)
    return []
  }
}

// Analytics fetching functions
export async function fetchPortfolioAnalytics(portfolioId: string): Promise<PortfolioAnalytics | null> {
  try {
    const response = await authenticatedFetch<any>(
      `/api/v1/analytics/portfolio/${portfolioId}/overview`
    )
    return response
  } catch (error) {
    console.error('Failed to fetch portfolio analytics:', error)
    return null
  }
}

export async function fetchFactorExposures(portfolioId: string): Promise<FactorExposure[]> {
  try {
    const response = await authenticatedFetch<any>(
      `/api/v1/analytics/portfolio/${portfolioId}/factor-exposures`
    )

    if (response.available && response.exposures) {
      return response.exposures
    }
    return []
  } catch (error) {
    console.error('Failed to fetch factor exposures:', error)
    return []
  }
}

// Target Prices fetching functions
export async function fetchTargetPrices(portfolioId: string): Promise<TargetPrice[]> {
  try {
    const response = await authenticatedFetch<TargetPrice[]>(
      `/api/v1/target-prices/${portfolioId}`
    )
    return Array.isArray(response) ? response : []
  } catch (error) {
    console.error('Failed to fetch target prices:', error)
    return []
  }
}

// Strategy fetching functions
export async function fetchStrategies(): Promise<Strategy[]> {
  try {
    const response = await authenticatedFetch<Strategy[]>('/api/v1/strategies/')
    return Array.isArray(response) ? response : []
  } catch (error) {
    console.error('Failed to fetch strategies:', error)
    return []
  }
}

// Tags fetching functions
export async function fetchTags(): Promise<Tag[]> {
  try {
    const response = await authenticatedFetch<Tag[]>(
      '/api/v1/tags/?include_archived=false'
    )
    return Array.isArray(response) ? response : []
  } catch (error) {
    console.error('Failed to fetch tags:', error)
    return []
  }
}

// Summary function for dashboard
export async function fetchDashboardSummary(portfolioId: string) {
  try {
    const [analytics, positions, factorExposures] = await Promise.all([
      fetchPortfolioAnalytics(portfolioId),
      fetchPositionDetails(portfolioId),
      fetchFactorExposures(portfolioId)
    ])

    // Group positions by type
    const longPositions = positions.filter(p => p.position_type === 'LONG')
    const shortPositions = positions.filter(p => p.position_type === 'SHORT')
    const optionsPositions = positions.filter(p => ['LC', 'LP', 'SC', 'SP'].includes(p.position_type))
    const privatePositions = positions.filter(p => p.investment_class === 'PRIVATE')

    return {
      analytics,
      positions: {
        all: positions,
        long: longPositions,
        short: shortPositions,
        options: optionsPositions,
        private: privatePositions
      },
      factorExposures,
      summary: {
        totalPositions: positions.length,
        longCount: longPositions.length,
        shortCount: shortPositions.length,
        optionsCount: optionsPositions.length,
        privateCount: privatePositions.length
      }
    }
  } catch (error) {
    console.error('Failed to fetch dashboard summary:', error)
    return {
      analytics: null,
      positions: {
        all: [],
        long: [],
        short: [],
        options: [],
        private: []
      },
      factorExposures: [],
      summary: {
        totalPositions: 0,
        longCount: 0,
        shortCount: 0,
        optionsCount: 0,
        privateCount: 0
      }
    }
  }
}
