/**
 * Portfolio Resolver Service
 * Dynamically resolves portfolio IDs from the backend
 * Replaces hardcoded portfolio ID mappings
 * 
 * Note: The backend uses a one-portfolio-per-user model.
 * Portfolio IDs are discovered by fetching the user's portfolios list.
 */

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

    // Fetch portfolios from the backend
    try {
      const response = await fetch('/api/proxy/api/v1/data/portfolios', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      })

      if (response.ok) {
        const portfolios = await response.json()
        
        // Users typically have one portfolio, but take the first if multiple
        if (portfolios && portfolios.length > 0) {
          const portfolio = portfolios[0]
          const portfolioInfo: PortfolioInfo = {
            id: portfolio.id,
            name: portfolio.name,
            totalValue: portfolio.total_value,
            positionCount: portfolio.position_count
          }
          
          // Cache the result
          this.portfolioCache.set(cacheKey, portfolioInfo)
          this.cacheExpiry.set(cacheKey, Date.now() + this.CACHE_DURATION)
          
          console.log('Portfolio discovered:', portfolioInfo)
          return portfolio.id
        } else {
          console.warn('No portfolios found for user')
          return null
        }
      } else {
        console.error('Failed to fetch portfolios:', response.status, response.statusText)
        return null
      }
    } catch (error) {
      console.error('Error fetching portfolios:', error)
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
   * Clear cache and force refresh of portfolio information
   * Useful after login or when switching accounts
   */
  async refreshPortfolioInfo(): Promise<string | null> {
    this.clearCache()
    return this.getUserPortfolioId(true)
  }
}

// Export singleton instance
export const portfolioResolver = new PortfolioResolver()