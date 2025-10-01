// Client-side authentication utilities

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null
  }
  return localStorage.getItem('access_token')
}

export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') {
    return
  }
  localStorage.setItem('access_token', token)
}

export function clearAuthToken(): void {
  if (typeof window === 'undefined') {
    return
  }
  localStorage.removeItem('access_token')
}

export function isAuthenticated(): boolean {
  return getAuthToken() !== null
}

// Redirect to login if not authenticated
export function requireAuth(): void {
  if (!isAuthenticated() && typeof window !== 'undefined') {
    window.location.href = '/login'
  }
}

// Headers helper for API calls
export function getAuthHeaders(): HeadersInit {
  const token = getAuthToken()
  if (!token) {
    return {
      'Content-Type': 'application/json'
    }
  }
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
}