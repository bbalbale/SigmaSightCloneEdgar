/**
 * Chat Authentication Service
 * Handles cookie-based authentication for chat streaming
 * Uses HttpOnly cookies with credentials:'include'
 */

import { portfolioResolver } from './portfolioResolver';

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    name?: string;
  };
}

interface AuthUser {
  id: string;
  email: string;
  name?: string;
}

class ChatAuthService {
  private baseUrl: string;
  private isAuthenticated: boolean = false;
  private currentUser: AuthUser | null = null;

  constructor() {
    // Use proxy in development, direct URL in production
    this.baseUrl = process.env.NODE_ENV === 'development' 
      ? '/api/proxy' 
      : process.env.NEXT_PUBLIC_API_URL || '';
  }

  /**
   * Login with email and password
   * Sets HttpOnly cookie automatically via backend response
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Important: include cookies
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data: LoginResponse = await response.json();
      
      // Store user info (but not the token - that's in HttpOnly cookie)
      this.isAuthenticated = true;
      this.currentUser = data.user;
      
      // Store auth state in sessionStorage for persistence check
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('auth_user', JSON.stringify(data.user));
        // Store access token for portfolio API calls (not for chat)
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('user_email', email);
      }
      
      // Try to discover and cache the portfolio ID
      // This is a best-effort operation - don't fail login if it doesn't work
      try {
        await portfolioResolver.getUserPortfolioId(true); // Force refresh to discover ID
      } catch (error) {
        console.warn('Could not discover portfolio ID after login:', error);
      }

      return data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  /**
   * Logout - clears HttpOnly cookie via backend
   */
  async logout(): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/api/v1/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local state regardless
      this.isAuthenticated = false;
      this.currentUser = null;
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('auth_user');
      }
    }
  }

  /**
   * Check authentication status
   * Verifies cookie is still valid
   */
  async checkAuth(): Promise<AuthUser | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/auth/me`, {
        method: 'GET',
        credentials: 'include',
      });

      if (response.ok) {
        const user = await response.json();
        this.isAuthenticated = true;
        this.currentUser = user;
        return user;
      }
    } catch (error) {
      console.error('Auth check error:', error);
    }

    // Not authenticated
    this.isAuthenticated = false;
    this.currentUser = null;
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('auth_user');
    }
    return null;
  }

  /**
   * Refresh authentication if needed
   * Called before making authenticated requests
   */
  async refreshIfNeeded(): Promise<boolean> {
    // First check if we have a stored user
    if (!this.currentUser && typeof window !== 'undefined') {
      const stored = sessionStorage.getItem('auth_user');
      if (stored) {
        this.currentUser = JSON.parse(stored);
      }
    }

    // Verify auth is still valid
    const user = await this.checkAuth();
    return user !== null;
  }

  /**
   * Make authenticated fetch request
   * Automatically includes credentials
   */
  async authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
    // Ensure we're authenticated
    const isValid = await this.refreshIfNeeded();
    if (!isValid) {
      throw new Error('Not authenticated');
    }

    return fetch(url, {
      ...options,
      credentials: 'include', // Always include cookies
      headers: {
        ...options.headers,
      },
    });
  }

  /**
   * Send chat message with streaming response
   * Uses fetch() with manual SSE parsing
   */
  async sendChatMessage(
    message: string, 
    conversationId: string,
    onChunk: (chunk: string) => void,
    onError: (error: any) => void,
    onDone: () => void
  ): Promise<AbortController> {
    const abortController = new AbortController();

    try {
      const response = await this.authenticatedFetch(
        `${this.baseUrl}/api/v1/chat/send`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({
            message,
            conversation_id: conversationId,
          }),
          signal: abortController.signal,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        onError(error);
        return abortController;
      }

      // Parse SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        onError(new Error('No response body'));
        return abortController;
      }

      // Read stream
      const processStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              onDone();
              break;
            }

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                try {
                  const parsed = JSON.parse(data);
                  
                  // Handle different event types
                  if (parsed.delta) {
                    onChunk(parsed.delta);
                  } else if (parsed.type === 'heartbeat') {
                    // Ignore heartbeats
                    continue;
                  } else if (parsed.error_type) {
                    onError(parsed);
                  }
                } catch (e) {
                  // Not JSON, might be raw text
                  if (data.trim()) {
                    onChunk(data);
                  }
                }
              }
            }
          }
        } catch (error: any) {
          if (error.name !== 'AbortError') {
            onError(error);
          }
        }
      };

      processStream();

    } catch (error) {
      onError(error);
    }

    return abortController;
  }

  // Getters
  getIsAuthenticated(): boolean {
    return this.isAuthenticated;
  }

  getCurrentUser(): AuthUser | null {
    return this.currentUser;
  }
}

// Export singleton instance
export const chatAuthService = new ChatAuthService();

// Export types
export type { LoginResponse, AuthUser };