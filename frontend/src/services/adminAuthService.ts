/**
 * Admin Authentication Service
 * Handles admin login, logout, and session management
 * Separate from regular user authentication (authManager)
 */

import { apiClient } from './apiClient'

interface AdminUser {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'super_admin'
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

interface AdminLoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  admin_id: string
  email: string
  role: string
  full_name: string
}

interface AdminSession {
  token: string
  email: string
  expiresAt: number
  admin: AdminUser | null
}

interface AdminLoginCredentials {
  email: string
  password: string
}

class AdminAuthService {
  private session: AdminSession | null = null
  private readonly STORAGE_KEY = 'admin_session'
  private readonly TOKEN_EXPIRY_BUFFER = 60 * 1000 // Refresh 1 minute early

  /**
   * Login admin user
   */
  async login(credentials: AdminLoginCredentials): Promise<AdminLoginResponse> {
    const response = await fetch('/api/proxy/api/v1/admin/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(credentials),
      credentials: 'include' // Include cookies
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(error.detail || 'Invalid email or password')
    }

    const data: AdminLoginResponse = await response.json()

    // Store session
    this.setSession({
      token: data.access_token,
      email: data.email,
      expiresAt: Date.now() + (data.expires_in * 1000) - this.TOKEN_EXPIRY_BUFFER,
      admin: {
        id: data.admin_id,
        email: data.email,
        full_name: data.full_name,
        role: data.role as 'admin' | 'super_admin',
        is_active: true,
        created_at: new Date().toISOString(),
        last_login_at: new Date().toISOString()
      }
    })

    return data
  }

  /**
   * Logout admin user
   */
  async logout(): Promise<void> {
    const token = this.getAccessToken()

    if (token) {
      try {
        await fetch('/api/proxy/api/v1/admin/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        })
      } catch (error) {
        console.warn('Admin logout request failed:', error)
      }
    }

    this.clearSession()
  }

  /**
   * Get current admin info from backend
   */
  async getMe(): Promise<AdminUser | null> {
    const token = this.getAccessToken()
    if (!token) return null

    try {
      const response = await fetch('/api/proxy/api/v1/admin/auth/me', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        signal: AbortSignal.timeout(5000)
      })

      if (!response.ok) {
        if (response.status === 401) {
          this.clearSession()
        }
        return null
      }

      const data = await response.json()
      const admin: AdminUser = {
        id: data.id,
        email: data.email,
        full_name: data.full_name,
        role: data.role,
        is_active: data.is_active,
        created_at: data.created_at,
        last_login_at: data.last_login_at
      }

      // Update cached admin in session
      if (this.session) {
        this.session.admin = admin
        this.persistSession()
      }

      return admin
    } catch (error) {
      console.error('Failed to fetch admin info:', error)
      return null
    }
  }

  /**
   * Refresh admin token
   */
  async refreshToken(): Promise<boolean> {
    const token = this.getAccessToken()
    if (!token) return false

    try {
      const response = await fetch('/api/proxy/api/v1/admin/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        credentials: 'include'
      })

      if (!response.ok) {
        this.clearSession()
        return false
      }

      const data: AdminLoginResponse = await response.json()

      // Update session with new token
      this.setSession({
        token: data.access_token,
        email: data.email,
        expiresAt: Date.now() + (data.expires_in * 1000) - this.TOKEN_EXPIRY_BUFFER,
        admin: this.session?.admin || null
      })

      return true
    } catch (error) {
      console.error('Failed to refresh admin token:', error)
      return false
    }
  }

  /**
   * Check if admin is authenticated
   */
  isAuthenticated(): boolean {
    this.hydrateSession()
    if (!this.session?.token) return false
    return Date.now() < this.session.expiresAt
  }

  /**
   * Check if token is expired or about to expire
   */
  isTokenExpired(): boolean {
    this.hydrateSession()
    if (!this.session) return true
    return Date.now() >= this.session.expiresAt
  }

  /**
   * Get current access token
   */
  getAccessToken(): string | null {
    this.hydrateSession()
    return this.session?.token || null
  }

  /**
   * Get cached admin user
   */
  getCachedAdmin(): AdminUser | null {
    this.hydrateSession()
    return this.session?.admin || null
  }

  /**
   * Check if admin has super_admin role
   */
  isSuperAdmin(): boolean {
    const admin = this.getCachedAdmin()
    return admin?.role === 'super_admin'
  }

  /**
   * Store session in memory and localStorage
   */
  private setSession(session: AdminSession): void {
    this.session = session
    this.persistSession()
  }

  /**
   * Persist session to localStorage
   */
  private persistSession(): void {
    if (typeof window === 'undefined' || !this.session) return

    localStorage.setItem(this.STORAGE_KEY, JSON.stringify({
      token: this.session.token,
      email: this.session.email,
      expiresAt: this.session.expiresAt,
      admin: this.session.admin
    }))
  }

  /**
   * Clear session from memory and localStorage
   */
  clearSession(): void {
    this.session = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem(this.STORAGE_KEY)
    }
  }

  /**
   * Hydrate session from localStorage
   */
  private hydrateSession(): void {
    if (this.session || typeof window === 'undefined') return

    const stored = localStorage.getItem(this.STORAGE_KEY)
    if (!stored) return

    try {
      const parsed = JSON.parse(stored)
      this.session = {
        token: parsed.token,
        email: parsed.email,
        expiresAt: parsed.expiresAt,
        admin: parsed.admin
      }
    } catch (error) {
      console.warn('Failed to parse admin session:', error)
      this.clearSession()
    }
  }

  /**
   * Validate token with backend
   */
  async validateToken(): Promise<boolean> {
    const admin = await this.getMe()
    return admin !== null
  }
}

export const adminAuthService = new AdminAuthService()
export type { AdminUser, AdminLoginResponse, AdminLoginCredentials }
