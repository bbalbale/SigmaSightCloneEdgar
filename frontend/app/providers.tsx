'use client'

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth as useClerkAuth, useUser, useClerk } from '@clerk/nextjs'
import { portfolioResolver } from '@/services/portfolioResolver'
import { setPortfolioState, clearPortfolioState } from '@/stores/portfolioStore'
import { setClerkToken, clearClerkToken, setTokenRefreshFn } from '@/lib/clerkTokenStore'
import { ThemeProvider } from '@/contexts/ThemeContext'

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

// Public paths that don't require authentication
const publicPaths = ['/', '/landing', '/login', '/sign-in', '/sign-up', '/test-user-creation']

const isPublicRoute = (path: string | null) => {
  if (!path) {
    return false
  }
  // Admin routes have their own auth system in admin/layout.tsx
  if (path.startsWith('/admin')) {
    return true
  }
  // Clerk auth routes
  if (path.startsWith('/sign-in') || path.startsWith('/sign-up')) {
    return true
  }
  return publicPaths.includes(path)
}

/**
 * ClerkTokenSync - Syncs Clerk JWT tokens to the global token store
 * This allows non-React code (like apiClient) to access the current token
 */
function ClerkTokenSync() {
  const { getToken, isSignedIn } = useClerkAuth()

  // Register the token refresh function so non-React code can request fresh tokens
  useEffect(() => {
    if (isSignedIn) {
      setTokenRefreshFn(getToken)
    } else {
      setTokenRefreshFn(null)
    }
    return () => setTokenRefreshFn(null)
  }, [getToken, isSignedIn])

  useEffect(() => {
    let mounted = true
    let refreshInterval: ReturnType<typeof setInterval> | null = null

    const syncToken = async () => {
      if (!mounted) return

      if (isSignedIn) {
        try {
          const token = await getToken()
          if (mounted && token) {
            // Set token with 55 second expiry (Clerk tokens last 60 seconds)
            setClerkToken(token, Date.now() + 55000)
          }
        } catch (error) {
          console.warn('Failed to sync Clerk token:', error)
        }
      } else {
        clearClerkToken()
      }
    }

    // Initial sync
    syncToken()

    // Refresh token every 50 seconds (before the 60-second expiry)
    if (isSignedIn) {
      refreshInterval = setInterval(syncToken, 50000)
    }

    return () => {
      mounted = false
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    }
  }, [getToken, isSignedIn])

  return null
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  // Clerk hooks
  const { isLoaded: isClerkLoaded, isSignedIn } = useClerkAuth()
  const { user: clerkUser } = useUser()
  const { signOut } = useClerk()

  // Initialize portfolio when user is authenticated
  const initializePortfolio = useCallback(async () => {
    try {
      // Clear any stale portfolio data from previous sessions
      // This ensures we don't use wrong portfolio IDs after user change
      clearPortfolioState()
      portfolioResolver.clearCache()

      const portfolioId = await portfolioResolver.getUserPortfolioId(true) // force refresh
      if (portfolioId) {
        setPortfolioState(portfolioId)
      }
    } catch (error) {
      console.error('Failed to initialize portfolio:', error)
    }
  }, [])

  // Map Clerk user to our User interface
  const mapClerkUser = useCallback((clerkUserData: typeof clerkUser): User | null => {
    if (!clerkUserData) {
      return null
    }
    return {
      id: clerkUserData.id,
      email: clerkUserData.primaryEmailAddress?.emailAddress || '',
      fullName: clerkUserData.fullName || clerkUserData.firstName || clerkUserData.primaryEmailAddress?.emailAddress || '',
      isAdmin: false
    }
  }, [])

  // Main auth effect - driven by Clerk state
  useEffect(() => {
    // Wait for Clerk to load
    if (!isClerkLoaded) {
      return
    }

    const handleAuth = async () => {
      if (isSignedIn && clerkUser) {
        // User is signed in via Clerk
        setUser(mapClerkUser(clerkUser))
        await initializePortfolio()
        setLoading(false)
      } else {
        // Not signed in
        setUser(null)
        clearPortfolioState()
        setLoading(false)

        // Redirect to sign-in if on protected route
        if (!isPublicRoute(pathname)) {
          router.push('/sign-in')
        }
      }
    }

    handleAuth()
  }, [isClerkLoaded, isSignedIn, clerkUser, mapClerkUser, initializePortfolio, pathname, router])

  // Login function - redirects to Clerk sign-in
  // (Legacy email/password login is no longer used with Clerk)
  const login = useCallback(async (_email: string, _password: string) => {
    // With Clerk, login is handled by the SignIn component
    // This function is kept for interface compatibility but redirects to Clerk
    router.push('/sign-in')
  }, [router])

  // Logout function - uses Clerk sign-out
  const logout = useCallback(async () => {
    try {
      // Clear local state first
      setUser(null)
      clearPortfolioState()
      clearClerkToken()
      portfolioResolver.clearCache()

      // Sign out via Clerk
      await signOut()

      // Redirect to sign-in
      router.push('/sign-in')
    } catch (error) {
      console.error('Logout failed:', error)
      // Still redirect even if Clerk signOut fails
      router.push('/sign-in')
    }
  }, [signOut, router])

  // Refresh auth - re-checks Clerk state
  const refreshAuth = useCallback(async () => {
    if (isSignedIn && clerkUser) {
      setUser(mapClerkUser(clerkUser))
      await initializePortfolio()
    }
  }, [isSignedIn, clerkUser, mapClerkUser, initializePortfolio])

  return (
    <ThemeProvider>
      <ClerkTokenSync />
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
    </ThemeProvider>
  )
}
