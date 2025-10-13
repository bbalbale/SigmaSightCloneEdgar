'use client'

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { authManager } from '@/services/authManager'
import { portfolioResolver } from '@/services/portfolioResolver'
import { chatAuthService } from '@/services/chatAuthService'
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

const publicPaths = ['/', '/landing', '/login', '/test-user-creation']

const isPublicRoute = (path: string | null) => {
  if (!path) {
    return false
  }
  return publicPaths.includes(path)
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  const initializePortfolio = useCallback(async () => {
    try {
      const portfolioId = await portfolioResolver.getUserPortfolioId()
      if (portfolioId) {
        setPortfolioState(portfolioId)
      }
    } catch (error) {
      console.error('Failed to initialize portfolio:', error)
    }
  }, [])

  const mapUser = useCallback((authUser: { id: string; email: string; name?: string } | null): User | null => {
    if (!authUser) {
      return null
    }
    return {
      id: authUser.id,
      email: authUser.email,
      fullName: authUser.name || authUser.email,
      isAdmin: false
    }
  }, [])

  const checkAuth = useCallback(async () => {
    try {
      const token = authManager.getAccessToken()

      if (!token) {
        setUser(null)
        clearPortfolioState()
        setLoading(false)
        if (!isPublicRoute(pathname)) {
          router.push('/login')
        }
        return
      }

      const isValid = await authManager.validateToken(token)
      if (isValid) {
        const currentUser = await authManager.getCurrentUser()
        setUser(mapUser(currentUser))
        await initializePortfolio()
      } else {
        authManager.clearSession()
        setUser(null)
        clearPortfolioState()
        if (!isPublicRoute(pathname)) {
          router.push('/login')
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      authManager.clearSession()
      setUser(null)
      clearPortfolioState()
    } finally {
      setLoading(false)
    }
  }, [initializePortfolio, mapUser, pathname, router])

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const login = useCallback(async (email: string, password: string) => {
    const response = await chatAuthService.login(email, password)
    setUser(mapUser(response.user || null))
    await initializePortfolio()
    router.push('/portfolio')
  }, [initializePortfolio, mapUser, router])

  const logout = useCallback(async () => {
    try {
      await chatAuthService.logout()
    } finally {
      authManager.clearSession()
      setUser(null)
      clearPortfolioState()
      portfolioResolver.clearCache()
      router.push('/login')
    }
  }, [router])

  const refreshAuth = useCallback(async () => {
    await checkAuth()
  }, [checkAuth])

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

