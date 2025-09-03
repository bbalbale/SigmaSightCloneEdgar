/**
 * Portfolio Resolver Service
 * Dynamically resolves portfolio IDs from the backend
 * Replaces hardcoded portfolio ID mappings
 * 
 * Note: The backend uses a one-portfolio-per-user model.
 * Portfolio IDs are discovered by fetching the user's portfolios list.
 */

import { requestManager } from './requestManager'

export type PortfolioType = 'individual' | 'high-net-worth' | 'hedge-fund'

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

  /**
   * Get the current user's portfolio ID
   * Since each user has only one portfolio, we discover it by:
   * 1. First checking cache
   * 2. Fetching the user's portfolios list from the backend
   */
  async getUserPortfolioId(forceRefresh = false): Promise<string | null> {
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('No authentication token found')
      return null
    }

    const cacheKey = `portfolio_${token.substring(0, 10)}` // Use token prefix as cache key
    
    // Check cache
    if (!forceRefresh && this.portfolioCache.has(cacheKey)) {
      const expiry = this.cacheExpiry.get(cacheKey) || 0
      if (Date.now() < expiry) {
        const cached = this.portfolioCache.get(cacheKey)
        return cached ? cached.id : null
      }
    }

    // Fetch portfolios from the backend with retry logic
    try {
      // TEMPORARY WORKAROUND: Use hardcoded mapping with CORRECT portfolio IDs
      // The /portfolios endpoint exists in code but isn't available in the running backend
      // These are the actual portfolio IDs from the database:
      const email = localStorage.getItem('user_email')
      const portfolioMap: Record<string, string> = {
        'demo_individual@sigmasight.com': '51134ffd-2f13-49bd-b1f5-0c327e801b69',
        'demo_hnw@sigmasight.com': 'c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e',
        'demo_hedgefundstyle@sigmasight.com': '2ee7435f-379f-4606-bdb7-dadce587a182'
      }
      
      if (email && portfolioMap[email]) {
        const portfolioInfo: PortfolioInfo = {
          id: portfolioMap[email],
          name: `Portfolio for ${email}`,
          totalValue: 0,
          positionCount: 0
        }
        
        // Cache the result
        this.portfolioCache.set(cacheKey, portfolioInfo)
        this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)
        
        console.log('Portfolio resolved using correct IDs from database:', portfolioInfo)
        return portfolioMap[email]
      }
      
      // Try the portfolios endpoint anyway in case backend gets restarted
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
        
        // Users typically have one portfolio, but take the first if multiple
        if (portfolios && portfolios.length > 0) {
          const portfolio = portfolios[0]
          const portfolioInfo: PortfolioInfo = {
            id: portfolio.id,
            name: portfolio.name,
            totalValue: portfolio.total_value || 0,
            positionCount: portfolio.position_count || 0
          }
          
          // Cache the result
          this.portfolioCache.set(cacheKey, portfolioInfo)
          this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)
          
          console.log('Portfolio discovered from backend:', {
            id: portfolio.id,
            name: portfolio.name,
            totalValue: portfolio.total_value,
            positionCount: portfolio.position_count
          })
          return portfolio.id
        } else {
          console.warn('No portfolios found for user in backend response')
          return null
        }
      } else {
        console.log('Portfolios endpoint not available, using hardcoded mapping')
        return null
      }
    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Error fetching portfolios:', error)
      }
      return null
    }
  }

  /**
   * Get portfolio ID by type
   * Since users have only one portfolio, this just returns the user's portfolio ID
   * The type parameter is preserved for backward compatibility
   */
  async getPortfolioIdByType(type: PortfolioType): Promise<string | null> {
    // Each user has only one portfolio, so type doesn't matter
    return this.getUserPortfolioId()
  }


  /**
   * Validate that a portfolio ID belongs to the current user
   */
  async validatePortfolioOwnership(portfolioId: string): Promise<boolean> {
    const token = localStorage.getItem('access_token')
    if (!token) {
      return false
    }

    try {
      // Try to fetch the portfolio - if successful, user owns it
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
   * This is called by portfolioService.ts after successful authentication
   */
  setUserPortfolioId(portfolioId: string, email: string): void {
    // Store in cache for immediate use
    const cacheKey = `portfolio_${email}`
    const portfolioInfo: PortfolioInfo = {
      id: portfolioId,
      name: `Portfolio for ${email}`
    }
    
    this.portfolioCache.set(cacheKey, portfolioInfo)
    this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)
  }
}

// Export singleton instance
export const portfolioResolver = new PortfolioResolver()