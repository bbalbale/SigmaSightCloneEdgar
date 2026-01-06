'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Legacy login page - redirects to Clerk sign-in
 *
 * This page is kept for backward compatibility.
 * Users going to /login are redirected to /sign-in (Clerk).
 */
export default function LoginPage() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to Clerk sign-in page
    router.replace('/sign-in')
  }, [router])

  // Show brief loading state while redirecting
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
        <p className="text-muted-foreground">Redirecting to sign in...</p>
      </div>
    </div>
  )
}
