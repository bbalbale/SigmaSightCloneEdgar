/**
 * Portfolio Resolver Service
 * Dynamically resolves portfolio IDs from the backend
 * Replaces hardcoded portfolio ID mappings
 * 
 * Note: The backend uses a one-portfolio-per-user model.
 * Portfolio IDs are discovered by making an authenticated request
 * and extracting the ID from the response.
 */

export type PortfolioType = 'individual' | 'high-net-worth' | 'hedge-fund'

interface PortfolioInfo {
  id: string
  name: string
  userId: string
}

class PortfolioResolver {
  private portfolioCache: Map<string, PortfolioInfo> = new Map()
  private cacheExpiry: Map<string, number> = new Map()
  private readonly CACHE_DURATION = 5 * 60 * 1000 // 5 minutes
  
  // Temporary mapping for demo users until we have a better discovery mechanism
  // These will be validated against actual API responses
  private readonly DEMO_HINTS: Record<string, string> = {
    'demo_hnw@sigmasight.com': 'c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e',
    'demo_individual@sigmasight.com': '51134ffd-2f13-49bd-b1f5-0c327e801b69',
    'demo_hedgefundstyle@sigmasight.com': '2ee7435f-379f-4606-bdb7-dadce587a182'
  }

  /**
   * Get the current user's portfolio ID
   * Since each user has only one portfolio, we discover it by:
   * 1. First checking cache
   * 2. Using hint if available (for demo users)
   * 3. Making a test API call to discover the ID from the response
   */
  async getUserPortfolioId(forceRefresh = false): Promise<string | null> {
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('No authentication token found')
      return null
    }

    const userEmail = localStorage.getItem('user_email') || ''
    const cacheKey = `portfolio_${token.substring(0, 10)}` // Use token prefix as cache key
    
    // Check cache
    if (!forceRefresh && this.portfolioCache.has(cacheKey)) {
      const expiry = this.cacheExpiry.get(cacheKey) || 0
      if (Date.now() < expiry) {
        const cached = this.portfolioCache.get(cacheKey)
        return cached ? cached.id : null
      }
    }

    // Try using hint for demo users
    const hintId = this.DEMO_HINTS[userEmail]
    if (hintId) {
      // Validate the hint by trying to fetch the portfolio
      try {
        const response = await fetch(`/api/proxy/api/v1/data/portfolio/${hintId}/complete`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        })

        if (response.ok) {
          const data = await response.json()
          const portfolioInfo: PortfolioInfo = {
            id: hintId,
            name: data.portfolio?.name || 'Portfolio',
            userId: data.portfolio?.user_id || ''
          }
          
          // Cache the validated result
          this.portfolioCache.set(cacheKey, portfolioInfo)
          this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)
          
          return hintId
        }
      } catch (error) {
        console.warn('Hint validation failed, will try discovery:', error)
      }
    }

    // No hint or hint failed - we need a discovery mechanism
    // For now, return null and let the calling code handle it
    console.warn('Portfolio ID discovery not implemented - no list endpoint available')
    return null
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
   * Try to discover portfolio ID by making test API calls
   * This is a fallback when we don't have hints
   */
  async discoverPortfolioId(): Promise<string | null> {
    // Since there's no list endpoint, we would need to either:
    // 1. Add a list endpoint to the backend
    // 2. Store the portfolio ID when the user logs in
    // 3. Use a known pattern for portfolio IDs
    
    // For now, this returns null - the calling code should handle this
    console.error('Portfolio discovery not available - backend needs a list endpoint')
    return null
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
      const response = await fetch(`/api/proxy/api/v1/data/portfolio/${portfolioId}/complete`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      })

      return response.ok
    } catch (error) {
      console.error('Failed to validate portfolio ownership:', error)
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
   * Store portfolio ID after successful login
   * This should be called by the auth service after login
   */
  setUserPortfolioId(portfolioId: string, userEmail?: string): void {
    const token = localStorage.getItem('access_token')
    if (!token) return
    
    const cacheKey = `portfolio_${token.substring(0, 10)}`
    const portfolioInfo: PortfolioInfo = {
      id: portfolioId,
      name: 'User Portfolio',
      userId: ''
    }
    
    this.portfolioCache.set(cacheKey, portfolioInfo)
    this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)
    
    // Store email for hint lookup
    if (userEmail) {
      localStorage.setItem('user_email', userEmail)
    }
  }
}

// Export singleton instance
export const portfolioResolver = new PortfolioResolver()