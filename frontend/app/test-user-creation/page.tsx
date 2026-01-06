'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Legacy test user creation page - redirects to Clerk sign-up
 *
 * With Clerk auth, user registration is handled by Clerk's SignUp component.
 * This page is kept for backward compatibility with existing links.
 */
export default function TestUserCreationPage() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to Clerk sign-up page
    router.replace('/sign-up')
  }, [router])

  // Show brief loading state while redirecting
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4" />
        <p className="text-muted-foreground">Redirecting to sign up...</p>
      </div>
    </div>
  )
}
