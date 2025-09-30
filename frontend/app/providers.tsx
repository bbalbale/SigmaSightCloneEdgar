'use client'

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { authManager } from '@/services/authManager'
import { portfolioResolver } from '@/services/portfolioResolver'
import { setPortfolioState, clearPortfolioState } from '@/stores/portfolioStore'

interface User {
  id: string
  email: string
  fullName: string
  isAdmin: boolean
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

const publicPaths = ['/', '/landing', '/login']

export function Providers({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  // Initialize portfolio ID when user is authenticated
  const initializePortfolio = useCallback(async () => {
    try {
      const portfolioId = await portfolioResolver.getUserPortfolioId()
      if (portfolioId) {
        // Fetch portfolio details if needed
        // For now, just set the ID
        setPortfolioState(portfolioId)
      }
    } catch (error) {
      console.error('Failed to initialize portfolio:', error)
    }
  }, [])

  // Check authentication status on mount and token changes
  const checkAuth = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token')

      if (!token) {
        setUser(null)
        clearPortfolioState()
        setLoading(false)

        // Redirect to login if on protected route
        if (!publicPaths.includes(pathname)) {
          router.push('/login')
        }
        return
      }

      // Validate token and get user info
      const isValid = await authManager.validateToken(token)
      if (isValid) {
        const userInfo = await authManager.getCurrentUser()
        setUser(userInfo)

        // Initialize portfolio after successful auth
        await initializePortfolio()
      } else {
        // Token invalid, clear everything
        localStorage.removeItem('access_token')
        setUser(null)
        clearPortfolioState()

        if (!publicPaths.includes(pathname)) {
          router.push('/login')
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      setUser(null)
      clearPortfolioState()
    } finally {
      setLoading(false)
    }
  }, [pathname, router, initializePortfolio])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = async (email: string, password: string) => {
    try {
      const response = await authManager.login(email, password)

      if (response.user) {
        setUser(response.user)
        await initializePortfolio()
        router.push('/portfolio')
      }
    } catch (error) {
      // Let the login form handle the error
      throw error
    }
  }

  const logout = async () => {
    try {
      await authManager.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // Clear everything regardless of API response
      localStorage.removeItem('access_token')
      setUser(null)
      clearPortfolioState()
      portfolioResolver.clearCache()
      router.push('/login')
    }
  }

  const refreshAuth = async () => {
    await checkAuth()
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
        refreshAuth
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}