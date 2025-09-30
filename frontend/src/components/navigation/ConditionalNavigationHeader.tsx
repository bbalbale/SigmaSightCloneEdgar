'use client'

import { usePathname } from 'next/navigation'
import { NavigationHeader } from './NavigationHeader'
import { useAuth } from '../../../app/providers'

// Pages where the navigation header should NOT appear
const publicPages = ['/', '/landing', '/login']

export function ConditionalNavigationHeader() {
  const pathname = usePathname() ?? ''
  const { user, loading } = useAuth()

  // Don't show header on public pages
  if (publicPages.includes(pathname)) {
    return null
  }

  // Don't show header if user is not logged in (and not loading)
  if (!loading && !user) {
    return null
  }

  // Show header for authenticated users on protected pages
  return <NavigationHeader />
}
