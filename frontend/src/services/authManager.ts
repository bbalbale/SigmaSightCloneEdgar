/**
 * Centralized Authentication Manager
 * Prevents token race conditions and manages authentication state consistently
 * Ensures only one authentication request happens at a time
 */

import { PortfolioType } from './portfolioService'

interface AuthToken {
  access_token: string
  token_type: string
  expires_in?: number
  user?: {
    id: string
    email: string
    name?: string
  }
}

interface CachedToken {
  token: string
  email: string
  expiresAt: number
  user?: AuthToken['user']
}

// Demo user credentials for authentication
const DEMO_CREDENTIALS = {
  'individual': { email: 'demo_individual@sigmasight.com', password: 'demo12345' },
  'high-net-worth': { email: 'demo_hnw@sigmasight.com', password: 'demo12345' },
  'hedge-fund': { email: 'demo_hedgefundstyle@sigmasight.com', password: 'demo12345' }
}

class AuthManager {
  private tokenCache: Map<string, CachedToken> = new Map()
  private authInProgress: Map<string, Promise<string>> = new Map()
  private readonly TOKEN_EXPIRY_BUFFER = 60 * 1000 // Refresh 1 minute before expiry
  private readonly DEFAULT_TOKEN_LIFETIME = 30 * 60 * 1000 // 30 minutes default
  
  /**
   * Get authentication token for a portfolio type
   * Prevents concurrent authentication requests and caches valid tokens
   */
  async getToken(portfolioType: PortfolioType): Promise<string> {
    const credentials = DEMO_CREDENTIALS[portfolioType]
    if (!credentials) {
      throw new Error(`Invalid portfolio type: ${portfolioType}`)
    }

    const cacheKey = credentials.email

    // Check if we have a valid cached token
    const cached = this.tokenCache.get(cacheKey)
    if (cached && this.isTokenValid(cached)) {
      return cached.token
    }

    // Check if authentication is already in progress for this user
    const inProgress = this.authInProgress.get(cacheKey)
    if (inProgress) {
      return inProgress
    }

    // Start new authentication process
    const authPromise = this.authenticate(credentials.email, credentials.password, cacheKey)
    this.authInProgress.set(cacheKey, authPromise)

    try {
      const token = await authPromise
      return token
    } finally {
      // Clean up in-progress tracker
      this.authInProgress.delete(cacheKey)
    }
  }

  /**
   * Authenticate with the backend
   */
  private async authenticate(email: string, password: string, cacheKey: string): Promise<string> {
    try {
      const response = await fetch('/api/proxy/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
        signal: AbortSignal.timeout(10000) // 10 second timeout
      })

      if (!response.ok) {
        // Clear any stale cache on auth failure
        this.tokenCache.delete(cacheKey)
        localStorage.removeItem('access_token')
        
        const errorData = await response.json().catch(() => ({}))
        throw new Error(`Authentication failed: ${errorData.detail || response.status}`)
      }

      const data: AuthToken = await response.json()
      
      // Calculate expiration time
      const expiresIn = data.expires_in || (this.DEFAULT_TOKEN_LIFETIME / 1000)
      const expiresAt = Date.now() + (expiresIn * 1000) - this.TOKEN_EXPIRY_BUFFER

      // Cache the token
      const cachedToken: CachedToken = {
        token: data.access_token,
        email,
        expiresAt,
        user: data.user
      }
      
      this.tokenCache.set(cacheKey, cachedToken)
      
      // Also update localStorage for backward compatibility
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('user_email', email)
      if (data.user) {
        sessionStorage.setItem('auth_user', JSON.stringify(data.user))
      }

      return data.access_token
    } catch (error) {
      console.error(`Authentication failed for ${email}:`, error)
      throw error
    }
  }

  /**
   * Check if a cached token is still valid
   */
  private isTokenValid(cached: CachedToken): boolean {
    return Date.now() < cached.expiresAt
  }

  /**
   * Get token from localStorage (for backward compatibility)
   */
  getStoredToken(): string | null {
    return localStorage.getItem('access_token')
  }

  /**
   * Clear all cached tokens and stored auth data
   */
  clearAllTokens(): void {
    this.tokenCache.clear()
    this.authInProgress.clear()
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_email')
    sessionStorage.removeItem('auth_user')
  }

  /**
   * Clear token for specific portfolio type
   */
  clearTokenForType(portfolioType: PortfolioType): void {
    const credentials = DEMO_CREDENTIALS[portfolioType]
    if (credentials) {
      this.tokenCache.delete(credentials.email)
      this.authInProgress.delete(credentials.email)
    }
  }

  /**
   * Refresh token for a specific portfolio type
   */
  async refreshToken(portfolioType: PortfolioType): Promise<string> {
    this.clearTokenForType(portfolioType)
    return this.getToken(portfolioType)
  }

  /**
   * Validate that a token is still working by making a test request
   */
  async validateToken(token: string): Promise<boolean> {
    try {
      const response = await fetch('/api/proxy/api/v1/auth/me', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        signal: AbortSignal.timeout(5000) // 5 second timeout
      })
      return response.ok
    } catch {
      return false
    }
  }
}

// Export singleton instance
export const authManager = new AuthManager()

// Export types
export type { AuthToken, CachedToken }