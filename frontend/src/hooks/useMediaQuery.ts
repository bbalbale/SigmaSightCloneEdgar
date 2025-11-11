'use client'

import { useState, useEffect } from 'react'

/**
 * useMediaQuery Hook
 *
 * Custom hook for responsive design that listens to media query changes.
 * Returns true if the media query matches, false otherwise.
 *
 * @param query - CSS media query string (e.g., "(max-width: 767px)")
 * @returns boolean indicating if the media query matches
 *
 * @example
 * const isMobile = useMediaQuery('(max-width: 767px)')
 *
 * if (isMobile) {
 *   return <MobileView />
 * }
 * return <DesktopView />
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    // Create media query list
    const media = window.matchMedia(query)

    // Set initial value
    setMatches(media.matches)

    // Create listener for changes
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches)

    // Add event listener
    media.addEventListener('change', listener)

    // Cleanup
    return () => media.removeEventListener('change', listener)
  }, [query])

  return matches
}

/**
 * useIsMobile Hook
 *
 * Convenience hook to check if viewport is mobile size (<768px).
 * Uses Tailwind's md breakpoint as the cutoff.
 *
 * @returns true if viewport width < 768px
 *
 * @example
 * const isMobile = useIsMobile()
 *
 * return (
 *   <div className={isMobile ? 'mobile-layout' : 'desktop-layout'}>
 *     {isMobile ? <MobileNav /> : <DesktopNav />}
 *   </div>
 * )
 */
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)')
}

/**
 * useIsDesktop Hook
 *
 * Convenience hook to check if viewport is desktop size (≥768px).
 * Uses Tailwind's md breakpoint.
 *
 * @returns true if viewport width ≥ 768px
 *
 * @example
 * const isDesktop = useIsDesktop()
 *
 * if (isDesktop) {
 *   return <FullDataTable />
 * }
 * return <CompactCards />
 */
export function useIsDesktop(): boolean {
  return useMediaQuery('(min-width: 768px)')
}

/**
 * useIsTablet Hook
 *
 * Convenience hook to check if viewport is tablet size (768px-1023px).
 * Uses Tailwind's md and lg breakpoints.
 *
 * @returns true if viewport width is between 768px and 1023px
 *
 * @example
 * const isTablet = useIsTablet()
 *
 * if (isTablet) {
 *   return <TwoColumnLayout />
 * }
 */
export function useIsTablet(): boolean {
  return useMediaQuery('(min-width: 768px) and (max-width: 1023px)')
}

/**
 * useIsWideDesktop Hook
 *
 * Convenience hook to check if viewport is wide desktop size (≥1440px).
 * Uses Tailwind's xl breakpoint.
 *
 * @returns true if viewport width ≥ 1440px
 *
 * @example
 * const isWideDesktop = useIsWideDesktop()
 *
 * if (isWideDesktop) {
 *   return <ThreeColumnLayout />
 * }
 */
export function useIsWideDesktop(): boolean {
  return useMediaQuery('(min-width: 1440px)')
}
