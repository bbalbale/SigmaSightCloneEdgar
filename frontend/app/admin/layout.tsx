'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAdminStore } from '@/stores/adminStore'
import { adminAuthService } from '@/services/adminAuthService'
import { Loader2 } from 'lucide-react'

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const { admin, isAuthenticated, setAdmin, clearAdmin } = useAdminStore()
  const [isChecking, setIsChecking] = useState(true)

  // Public admin routes that don't require auth
  const isPublicRoute = pathname === '/admin/login'

  useEffect(() => {
    const checkAuth = async () => {
      // Skip auth check for login page
      if (isPublicRoute) {
        setIsChecking(false)
        return
      }

      // Check if we have a valid session
      if (!adminAuthService.isAuthenticated()) {
        clearAdmin()
        router.replace('/admin/login')
        return
      }

      // Validate token with backend if we have cached auth but want to verify
      if (isAuthenticated && !admin) {
        try {
          const adminData = await adminAuthService.getMe()
          if (adminData) {
            setAdmin(adminData)
          } else {
            clearAdmin()
            router.replace('/admin/login')
            return
          }
        } catch (error) {
          clearAdmin()
          router.replace('/admin/login')
          return
        }
      }

      setIsChecking(false)
    }

    checkAuth()
  }, [pathname, isPublicRoute, isAuthenticated, admin, setAdmin, clearAdmin, router])

  // Show loading while checking auth
  if (isChecking && !isPublicRoute) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-slate-400 text-sm">Verifying admin access...</p>
        </div>
      </div>
    )
  }

  // For login page, just render children without sidebar
  if (isPublicRoute) {
    return <>{children}</>
  }

  // For authenticated pages, render with admin sidebar/layout
  return (
    <div className="min-h-screen bg-slate-900">
      {children}
    </div>
  )
}
