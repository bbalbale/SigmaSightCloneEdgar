/**
 * Chat Authentication Service
 * Handles cookie-based authentication for chat streaming
 * Uses HttpOnly cookies with credentials:'include'
 */

import { portfolioResolver } from './portfolioResolver';
import { authManager } from './authManager';
import { setPortfolioState, clearPortfolioState } from '@/stores/portfolioStore';

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  portfolio_id?: string | null;
  user?: {
    id: string;
    email: string;
    name?: string;
  } | null;
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
    // Always use proxy for now (both dev and Docker)
    // TODO: Update for production deployment with proper API URL
    this.baseUrl = '/api/proxy';
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

      this.isAuthenticated = true;
      this.currentUser = data.user ?? null;

      if (typeof window !== 'undefined') {
        const previousUser = localStorage.getItem('user_email');
        const isDifferentUser = previousUser && previousUser !== email;

        if (isDifferentUser) {
          console.log('[Auth] Different user detected, clearing all user-specific data');
          const keepItems = ['cache_version'];
          const saved: [string, string][] = keepItems
            .map(k => [k, localStorage.getItem(k)] as [string, string | null])
            .filter((item): item is [string, string] => item[1] !== null);

          const keysToRemove: string[] = [];
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && !keepItems.includes(key)) {
              keysToRemove.push(key);
            }
          }
          keysToRemove.forEach(key => localStorage.removeItem(key));

          sessionStorage.clear();
          localStorage.removeItem('chat-storage');
          saved.forEach(([k, v]) => localStorage.setItem(k, v));

          clearPortfolioState();
        }

        authManager.setSession({
          token: data.access_token,
          email,
          tokenType: data.token_type,
          expiresIn: data.expires_in,
          portfolioId: data.portfolio_id ?? null,
          user: data.user ?? null,
        });

        localStorage.removeItem('conversationId');
        localStorage.removeItem('chatHistory');
        localStorage.removeItem('currentConversationId');
        sessionStorage.removeItem('conversationId');
        sessionStorage.removeItem('chatHistory');
        console.log('[Auth] Cleared stale conversation state on login');
      }

      let resolvedPortfolioId = data.portfolio_id ?? null;
      try {
        const discoveredId = await portfolioResolver.getUserPortfolioId(true);
        if (discoveredId) {
          resolvedPortfolioId = discoveredId;
        }
      } catch (error) {
        console.warn('Could not discover portfolio ID after login:', error);
      }

      if (resolvedPortfolioId) {
        authManager.setPortfolioId(resolvedPortfolioId);
        setPortfolioState(resolvedPortfolioId);
      }

      try {
        const conversationId = await this.initializeConversation();
        console.log('[Auth] Initialized new conversation:', conversationId);
      } catch (error) {
        console.warn('[Auth] Could not initialize conversation on login:', error);
      }

      return data;
    } catch (error) {
      console.error('Login error:', error);
      this.isAuthenticated = false;
      this.currentUser = null;
      throw error;
    }
  }

  /**
   * Initialize a new conversation after login
   * Creates a fresh conversation to avoid stale conversation ID issues
   */
  async initializeConversation(): Promise<string | null> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/chat/conversations`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          title: `Chat Session - ${new Date().toLocaleDateString()}`,
          mode: 'green', // Default mode
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        console.error('[Auth] Failed to create conversation:', error);
        return null;
      }

      const data = await response.json();
      const conversationId = data.conversation_id || data.id;
      
      // Store the new conversation ID
      if (conversationId && typeof window !== 'undefined') {
        localStorage.setItem('conversationId', conversationId);
        localStorage.setItem('currentConversationId', conversationId);
        console.log('[Auth] Stored new conversation ID:', conversationId);
        
        // FIX 6.49: Also update chat store directly
        try {
          // Import dynamically to avoid circular dependency
          const { useChatStore } = await import('@/stores/chatStore');
          const store = useChatStore.getState();
          store.loadConversation(conversationId);
          console.log('[Auth] Updated chat store with new conversation ID');
        } catch (error) {
          console.warn('[Auth] Could not update chat store:', error);
        }
      }
      
      return conversationId;
    } catch (error) {
      console.error('[Auth] Error initializing conversation:', error);
      return null;
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
      authManager.clearSession();
      clearPortfolioState();
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('auth_user');
        // Also clear conversation state on logout
        localStorage.removeItem('conversationId');
        localStorage.removeItem('chatHistory');
        localStorage.removeItem('currentConversationId');
        sessionStorage.removeItem('conversationId');
        sessionStorage.removeItem('chatHistory');
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
        authManager.setCachedUser(user);
        return user;
      }
    } catch (error) {
      console.error('Auth check error:', error);
    }

    // Not authenticated
    this.isAuthenticated = false;
    this.currentUser = null;
    authManager.clearSession();
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
      if (stored && stored !== 'undefined') {
        try {
          this.currentUser = JSON.parse(stored);
        } catch (error) {
          console.warn('Failed to parse stored auth user:', error);
          sessionStorage.removeItem('auth_user'); // Clean up bad data
        }
      }
    }

    // Verify auth is still valid
    const user = await this.checkAuth();
    return user !== null;
  }

  /**
   * Make authenticated fetch request
   * Automatically includes credentials and Bearer token
   */
  async authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
    // Ensure we're authenticated
    const isValid = await this.refreshIfNeeded();
    if (!isValid) {
      throw new Error('Not authenticated');
    }

    // Get Bearer token from localStorage
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;

    return fetch(url, {
      ...options,
      credentials: 'include', // Always include cookies
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
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