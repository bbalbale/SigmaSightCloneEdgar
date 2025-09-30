/**
 * Portfolio Resolver Service
 * Dynamically resolves portfolio IDs from the backend
 * Replaces hardcoded portfolio ID mappings
 *
 * Note: The backend uses a one-portfolio-per-user model.
 * Portfolio IDs are discovered by fetching the user's portfolios list.
 */

import { requestManager } from './requestManager'
import { authManager } from './authManager'

interface PortfolioInfo {
  id: string
  name: string
  totalValue?: number
  positionCount?: number
}

class PortfolioResolver {
  private portfolioCache: Map<string, PortfolioInfo> = new Map()
  private cacheExpiry: Map<string, number> = new Map()
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes

  private buildCacheKey(token: string, email?: string | null): string {
    if (email) {
      return `portfolio_${email}`
    }
    return `portfolio_${token.substring(0, 10)}`
  }

  /**
   * Get the current user's portfolio ID
   * Since each user has only one portfolio, we discover it by:
   * 1. First checking cache
   * 2. Fetching the user's portfolios list from the backend
   */
  async getUserPortfolioId(forceRefresh = false): Promise<string | null> {
    const token = authManager.getAccessToken()
    if (!token) {
      console.error('No authentication token found')
      return null
    }

    const cachedUser = authManager.getCachedUser()
    const email = cachedUser?.email || (typeof window !== 'undefined' ? localStorage.getItem('user_email') : null)
    const cacheKey = this.buildCacheKey(token, email || undefined)

    if (!forceRefresh && this.portfolioCache.has(cacheKey)) {
      const expiry = this.cacheExpiry.get(cacheKey) || 0
      if (Date.now() < expiry) {
        const cached = this.portfolioCache.get(cacheKey)
        if (cached) {
          return cached.id
        }
      }
    }

    try {
      const response = await requestManager.authenticatedFetch(
        '/api/proxy/api/v1/data/portfolios',
        token,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          maxRetries: 1,
          timeout: 5000,
          dedupe: true
        }
      )

      if (response.ok) {
        const portfolios = await response.json()

        if (Array.isArray(portfolios) && portfolios.length > 0) {
          const portfolio = portfolios[0]
          const portfolioInfo: PortfolioInfo = {
            id: portfolio.id,
            name: portfolio.name,
            totalValue: portfolio.total_value || 0,
            positionCount: portfolio.position_count || 0
          }

          this.portfolioCache.set(cacheKey, portfolioInfo)
          this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)

          authManager.setPortfolioId(portfolio.id)

          console.log('Portfolio discovered from backend:', {
            id: portfolio.id,
            name: portfolio.name,
            totalValue: portfolio.total_value,
            positionCount: portfolio.position_count
          })
          return portfolio.id
        }

        console.warn('No portfolios found for user in backend response')
        return null
      }

      // Fallback: deterministic mapping (development only)
      if (email) {
        const portfolioMap: Record<string, string> = {
          'demo_individual@sigmasight.com': '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe',
          'demo_hnw@sigmasight.com': 'e23ab931-a033-edfe-ed4f-9d02474780b4',
          'demo_hedgefundstyle@sigmasight.com': 'fcd71196-e93e-f000-5a74-31a9eead3118'
        }
        const mappedId = portfolioMap[email]
        if (mappedId) {
          const portfolioInfo: PortfolioInfo = {
            id: mappedId,
            name: `Portfolio for ${email}`,
            totalValue: 0,
            positionCount: 0
          }
          this.portfolioCache.set(cacheKey, portfolioInfo)
          this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)
          authManager.setPortfolioId(mappedId)
          console.warn('Backend portfolios endpoint unavailable; using fallback mapping for development:', portfolioInfo)
          return mappedId
        }
      }
      return null
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Error fetching portfolios:', error)
      }
      return null
    }
  }

  /**
   * Validate that a portfolio ID belongs to the current user
   */
  async validatePortfolioOwnership(portfolioId: string): Promise<boolean> {
    const token = authManager.getAccessToken()
    if (!token) {
      return false
    }

    try {
      const response = await requestManager.authenticatedFetch(
        `/api/proxy/api/v1/data/portfolio/${portfolioId}/complete`,
        token,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          maxRetries: 1,
          timeout: 5000
        }
      )

      return response.ok
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to validate portfolio ownership:', error)
      }
      return false
    }
  }

  /**
   * Clear the cache (useful when switching users)
   */
  clearCache(): void {
    this.portfolioCache.clear()
    this.cacheExpiry.clear()
  }

  /**
   * Clear cache and force refresh of portfolio information
   * Useful after login or when switching accounts
   */
  async refreshPortfolioInfo(): Promise<string | null> {
    this.clearCache()
    return this.getUserPortfolioId(true)
  }

  /**
   * Set user portfolio ID with email association (for backward compatibility)
   */
  setUserPortfolioId(portfolioId: string, email?: string | null): void {
    const token = authManager.getAccessToken()
    if (!token) {
      return
    }

    const cacheKey = this.buildCacheKey(token, email ?? authManager.getCachedUser()?.email)
    const portfolioInfo: PortfolioInfo = {
      id: portfolioId,
      name: email ? `Portfolio for ${email}` : 'Portfolio'
    }

    this.portfolioCache.set(cacheKey, portfolioInfo)
    this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)
    authManager.setPortfolioId(portfolioId)
  }
}

// Export singleton instance
export const portfolioResolver = new PortfolioResolver()
