import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

// Routes that bypass Clerk entirely (have their own auth)
const isAdminRoute = createRouteMatcher(['/admin(.*)'])

// Public routes that don't require authentication
const isPublicRoute = createRouteMatcher([
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/landing(.*)',
  '/login(.*)',  // Legacy login redirects to sign-in
  '/',  // Root redirect page
])

// API routes that should pass through without route checking
const isApiRoute = createRouteMatcher(['/api(.*)'])

export default clerkMiddleware(async (auth, req) => {
  // Admin routes bypass Clerk entirely - admin layout handles its own auth
  if (isAdminRoute(req)) {
    return NextResponse.next()
  }

  // API routes pass through
  if (isApiRoute(req)) {
    return NextResponse.next()
  }

  // Public routes don't require authentication
  if (isPublicRoute(req)) {
    return NextResponse.next()
  }

  // Get auth state
  const { userId } = await auth()

  // If not authenticated, redirect to sign-in
  if (!userId) {
    const signInUrl = new URL('/sign-in', req.url)
    signInUrl.searchParams.set('redirect_url', req.url)
    return NextResponse.redirect(signInUrl)
  }

  // User is authenticated - allow access
  // Invite validation is handled at the component level (Settings page)
  // This avoids slow external API calls in middleware
  return NextResponse.next()
})

export const config = {
  // Match all routes except static files and _next
  matcher: [
    // Skip Next.js internals and static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}
