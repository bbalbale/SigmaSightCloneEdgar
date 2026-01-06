/**
 * Centralized Authentication Manager
 * Maintains a single shared session for portfolio + chat features
 * Works alongside chatAuthService, which handles cookie-based chat auth
 *
 * CLERK MIGRATION NOTE:
 * With Clerk auth, tokens are now stored in clerkTokenStore (synced by ClerkTokenSync component).
 * getAccessToken() checks clerkTokenStore first, then falls back to localStorage for legacy tokens.
 * This ensures all existing services work with Clerk auth without individual updates.
 */

import { getClerkToken } from '@/lib/clerkTokenStore'

interface AuthUser {
  id: string
  email: string
  name?: string
}

interface AuthSession {
  token: string
  email: string
  expiresAt: number
  portfolioId: string | null
  user: AuthUser | null
}

interface SessionPayload {
  token: string
  email: string
  tokenType?: string
  expiresIn?: number
  portfolioId?: string | null
  user?: AuthUser | null
}

class AuthManager {
  private session: AuthSession | null = null
  private readonly TOKEN_EXPIRY_BUFFER = 60 * 1000 // Refresh 1 minute early
  private readonly DEFAULT_TOKEN_LIFETIME = 30 * 60 * 1000 // 30 minutes

  /**
   * Store the authenticated session in memory + localStorage
   */
  setSession(payload: SessionPayload): void {
    if (typeof window === 'undefined') {
      return
    }

    const expiresInMs = (payload.expiresIn ?? this.DEFAULT_TOKEN_LIFETIME / 1000) * 1000
    const expiresAt = Date.now() + Math.max(expiresInMs - this.TOKEN_EXPIRY_BUFFER, this.DEFAULT_TOKEN_LIFETIME / 2)

    this.session = {
      token: payload.token,
      email: payload.email,
      expiresAt,
      portfolioId: payload.portfolioId ?? null,
      user: payload.user ?? null
    }

    localStorage.setItem('access_token', payload.token)
    localStorage.setItem('user_email', payload.email)
    localStorage.setItem('token_expires_at', `${expiresAt}`)

    if (payload.portfolioId) {
      localStorage.setItem('portfolio_id', payload.portfolioId)
    } else {
      localStorage.removeItem('portfolio_id')
    }

    if (payload.user) {
      sessionStorage.setItem('auth_user', JSON.stringify(payload.user))
    } else {
      sessionStorage.removeItem('auth_user')
    }
  }

  /**
   * Clear all session data
   */
  clearSession(): void {
    this.session = null
    if (typeof window === 'undefined') {
      return
    }

    localStorage.removeItem('access_token')
    localStorage.removeItem('user_email')
    localStorage.removeItem('token_expires_at')
    localStorage.removeItem('portfolio_id')
    sessionStorage.removeItem('auth_user')
  }

  /**
   * Ensure in-memory session is hydrated from storage
   */
  private hydrateSession(): void {
    if (this.session || typeof window === 'undefined') {
      return
    }

    const token = localStorage.getItem('access_token')
    if (!token) {
      this.session = null
      return
    }

    const email = localStorage.getItem('user_email') || ''
    const expiresRaw = localStorage.getItem('token_expires_at')
    const expiresAt = expiresRaw ? Number(expiresRaw) : Date.now() + this.DEFAULT_TOKEN_LIFETIME
    const portfolioId = localStorage.getItem('portfolio_id') || null

    let user: AuthUser | null = null
    const storedUser = sessionStorage.getItem('auth_user') ?? localStorage.getItem('auth_user')
    if (storedUser && storedUser !== 'undefined') {
      try {
        user = JSON.parse(storedUser)
      } catch {
        user = null
      }
    }

    this.session = {
      token,
      email,
      expiresAt,
      portfolioId,
      user
    }
  }

  /**
   * Retrieve the current access token
   * Checks Clerk token store first (new auth), then falls back to localStorage (legacy)
   */
  getAccessToken(): string | null {
    // First, check for Clerk token (new auth path)
    const clerkToken = getClerkToken()
    if (clerkToken) {
      return clerkToken
    }

    // Fall back to legacy localStorage token
    if (!this.session) {
      this.hydrateSession()
    }
    return this.session?.token ?? null
  }

  /**
   * Update portfolio ID in session + storage
   */
  setPortfolioId(portfolioId: string | null): void {
    if (typeof window === 'undefined') {
      return
    }

    if (!this.session) {
      this.hydrateSession()
    }

    if (this.session) {
      this.session.portfolioId = portfolioId
    }

    if (portfolioId) {
      localStorage.setItem('portfolio_id', portfolioId)
    } else {
      localStorage.removeItem('portfolio_id')
    }
  }

  /**
   * Get cached portfolio ID from session/storage
   */
  getPortfolioId(): string | null {
    if (!this.session) {
      this.hydrateSession()
    }
    return this.session?.portfolioId ?? null
  }

  /**
   * Cache user info locally to avoid redundant requests
   */
  setCachedUser(user: AuthUser | null): void {
    if (typeof window === 'undefined') {
      return
    }

    if (!this.session) {
      this.hydrateSession()
    }

    if (this.session) {
      this.session.user = user
    }

    if (user) {
      sessionStorage.setItem('auth_user', JSON.stringify(user))
    } else {
      sessionStorage.removeItem('auth_user')
    }
  }

  /**
   * Return cached user if available
   */
  getCachedUser(): AuthUser | null {
    if (!this.session) {
      this.hydrateSession()
    }
    return this.session?.user ?? null
  }

  /**
   * Fetch the current user from the backend using the stored token
   */
  async getCurrentUser(): Promise<AuthUser | null> {
    const token = this.getAccessToken()
    if (!token) {
      return null
    }

    try {
      const response = await fetch('/api/proxy/api/v1/auth/me', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        signal: AbortSignal.timeout(5000)
      })

      if (!response.ok) {
        return null
      }

      const data = await response.json()
      const user: AuthUser = {
        id: data.id ?? data.user_id ?? '',
        email: data.email ?? '',
        name: data.name ?? data.full_name ?? undefined
      }

      this.setCachedUser(user)

      if (data.portfolio_id) {
        this.setPortfolioId(data.portfolio_id)
      }

      return user
    } catch (error) {
      console.error('Failed to fetch current user:', error)
      return null
    }
  }

  /**
   * Validate that a token is still usable
   */
  async validateToken(token?: string): Promise<boolean> {
    const accessToken = token ?? this.getAccessToken()
    if (!accessToken) {
      return false
    }

    try {
      const response = await fetch('/api/proxy/api/v1/auth/me', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        signal: AbortSignal.timeout(5000)
      })

      return response.ok
    } catch {
      return false
    }
  }
}

export const authManager = new AuthManager()
export type { AuthUser, SessionPayload }
