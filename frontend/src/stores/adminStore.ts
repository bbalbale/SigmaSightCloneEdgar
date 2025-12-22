/**
 * Admin Store - Admin Dashboard State Management
 * Handles admin authentication state using Zustand with persistence
 *
 * Completely separate from regular user authentication (portfolioStore, authManager)
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Admin user interface
export interface AdminUser {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'super_admin'
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

interface AdminStore {
  // State
  admin: AdminUser | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Actions
  setAdmin: (admin: AdminUser | null) => void
  setAuthenticated: (authenticated: boolean) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearAdmin: () => void

  // Computed
  isSuperAdmin: () => boolean
  hasAdmin: () => boolean
}

export const useAdminStore = create<AdminStore>()(
  persist(
    (set, get) => ({
      // Initial state
      admin: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Set admin user after login
      setAdmin: (admin) => {
        set({
          admin,
          isAuthenticated: admin !== null,
          error: null
        })
      },

      // Set authentication status
      setAuthenticated: (authenticated) => {
        set({ isAuthenticated: authenticated })
        if (!authenticated) {
          set({ admin: null })
        }
      },

      // Set loading state
      setLoading: (loading) => {
        set({ isLoading: loading })
      },

      // Set error message
      setError: (error) => {
        set({ error })
      },

      // Clear admin data (logout)
      clearAdmin: () => {
        set({
          admin: null,
          isAuthenticated: false,
          isLoading: false,
          error: null
        })
      },

      // Check if admin has super_admin role
      isSuperAdmin: () => {
        const admin = get().admin
        return admin?.role === 'super_admin'
      },

      // Check if admin is set
      hasAdmin: () => {
        return get().admin !== null
      }
    }),
    {
      name: 'admin-storage', // localStorage key
      version: 1,
      // Only persist admin data, not loading/error states
      partialize: (state) => ({
        admin: state.admin,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)

// Selector hooks for common use cases
export const useAdmin = () => useAdminStore((state) => state.admin)
export const useIsAdminAuthenticated = () => useAdminStore((state) => state.isAuthenticated)
export const useAdminLoading = () => useAdminStore((state) => state.isLoading)
export const useAdminError = () => useAdminStore((state) => state.error)
export const useIsSuperAdmin = () => useAdminStore((state) => state.admin?.role === 'super_admin')

// Helper functions for use outside React components
export const getAdmin = () => useAdminStore.getState().admin
export const isAdminAuthenticated = () => useAdminStore.getState().isAuthenticated
export const clearAdminState = () => useAdminStore.getState().clearAdmin()
