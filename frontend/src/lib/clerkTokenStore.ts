/**
 * Clerk Token Store
 *
 * This module provides a way to share Clerk tokens with non-React code (like apiClient).
 * The token is updated by the ClerkTokenSync component in providers.tsx.
 *
 * Pattern explained:
 * - Clerk's useAuth() hook can only be used in React components
 * - apiClient interceptors run outside React context
 * - This store bridges the gap by having React components update it
 *
 * Usage in React components:
 * - Use the useApiClient() hook directly (preferred)
 * - Or call setClerkToken() to update the global store
 *
 * Usage in non-React code:
 * - The apiClient will automatically use getClerkToken()
 */

let _clerkToken: string | null = null
let _tokenExpiresAt: number | null = null

/**
 * Set the current Clerk token (called from React components)
 * @param token The JWT token from Clerk, or null to clear
 * @param expiresAt Optional expiry timestamp in milliseconds
 */
export function setClerkToken(token: string | null, expiresAt?: number): void {
  _clerkToken = token
  _tokenExpiresAt = expiresAt ?? null
}

/**
 * Get the current Clerk token (used by apiClient interceptor)
 * Returns null if token is expired or not set
 */
export function getClerkToken(): string | null {
  // Check if token is expired
  if (_tokenExpiresAt && Date.now() > _tokenExpiresAt) {
    _clerkToken = null
    _tokenExpiresAt = null
    return null
  }
  return _clerkToken
}

/**
 * Clear the token store (called on logout)
 */
export function clearClerkToken(): void {
  _clerkToken = null
  _tokenExpiresAt = null
}

/**
 * Check if we have a valid token
 */
export function hasValidToken(): boolean {
  const token = getClerkToken()
  return token !== null && token.length > 0
}
