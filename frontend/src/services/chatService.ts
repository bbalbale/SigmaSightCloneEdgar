/**
 * Chat Service
 * Handles conversation management with the backend API
 * Includes conversation CRUD, message history, and error handling
 */

import { apiClient } from './apiClient'

interface CreateConversationRequest {
  mode: 'green' | 'blue' | 'indigo' | 'violet'
  portfolio_id?: string
}

interface Conversation {
  id: string
  mode: string
  created_at: string
  updated_at: string
  user_id: string
  meta_data?: Record<string, any>
}

interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  tool_calls?: any[]
}


// Error types for retry policies
export enum ErrorType {
  AUTH_EXPIRED = 'AUTH_EXPIRED',
  RATE_LIMITED = 'RATE_LIMITED',
  NETWORK_ERROR = 'NETWORK_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  FATAL_ERROR = 'FATAL_ERROR'
}

interface ErrorPolicy {
  action: 'redirect' | 'cooldown' | 'retry' | 'fail'
  maxAttempts?: number
  delay?: number | number[]
  target?: string
  duration?: number
  showToast?: boolean
}

const ERROR_POLICIES: Record<ErrorType, ErrorPolicy> = {
  AUTH_EXPIRED: { 
    action: 'redirect', 
    target: '/login',
    showToast: true 
  },
  RATE_LIMITED: { 
    action: 'cooldown', 
    duration: 30000,
    showToast: true 
  },
  NETWORK_ERROR: { 
    action: 'retry', 
    maxAttempts: 3, 
    delay: [1000, 2000, 4000],
    showToast: false
  },
  SERVER_ERROR: { 
    action: 'retry', 
    maxAttempts: 1, 
    delay: 1000,
    showToast: true 
  },
  FATAL_ERROR: { 
    action: 'fail', 
    showToast: true 
  }
}

class ChatService {
  private retryTimeouts: Map<string, NodeJS.Timeout> = new Map()
  
  /**
   * Classify error type based on response or error object
   */
  private classifyError(error: any): ErrorType {
    if (error.status === 401) return ErrorType.AUTH_EXPIRED
    if (error.status === 429) return ErrorType.RATE_LIMITED
    if (error.status >= 500) return ErrorType.SERVER_ERROR
    if (error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT') return ErrorType.NETWORK_ERROR
    if (!navigator.onLine) return ErrorType.NETWORK_ERROR
    return ErrorType.FATAL_ERROR
  }
  
  /**
   * Execute retry policy for a given error
   */
  private async executeRetryPolicy<T>(
    errorType: ErrorType,
    operation: () => Promise<T>,
    attempt = 0
  ): Promise<T> {
    const policy = ERROR_POLICIES[errorType]
    
    switch (policy.action) {
      case 'redirect':
        if (typeof window !== 'undefined' && policy.target) {
          window.location.href = policy.target
        }
        throw new Error('Authentication required')
        
      case 'cooldown':
        if (policy.duration) {
          await new Promise(resolve => setTimeout(resolve, policy.duration))
        }
        return operation()
        
      case 'retry':
        const maxAttempts = policy.maxAttempts || 1
        if (attempt >= maxAttempts) {
          throw new Error(`Max retry attempts (${maxAttempts}) exceeded`)
        }
        
        const delay = Array.isArray(policy.delay) 
          ? policy.delay[attempt] || policy.delay[policy.delay.length - 1]
          : policy.delay || 1000
          
        await new Promise(resolve => setTimeout(resolve, delay))
        
        try {
          return await operation()
        } catch (retryError) {
          const retryErrorType = this.classifyError(retryError)
          return this.executeRetryPolicy(retryErrorType, operation, attempt + 1)
        }
        
      case 'fail':
      default:
        throw new Error(`Operation failed: ${errorType}`)
    }
  }
  /**
   * Create a new conversation on the backend
   */
  async createConversation(mode: 'green' | 'blue' | 'indigo' | 'violet', portfolioId?: string): Promise<Conversation> {
    try {
      const payload: CreateConversationRequest = { mode }
      
      // Add portfolio_id to metadata if provided
      if (portfolioId) {
        payload.portfolio_id = portfolioId
      }
      
      const response = await fetch('/api/proxy/api/v1/chat/conversations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        credentials: 'include',
        body: JSON.stringify(payload),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create conversation')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Failed to create conversation:', error)
      throw error
    }
  }
  
  /**
   * List user's conversations
   */
  async listConversations(limit = 10): Promise<Conversation[]> {
    try {
      const response = await fetch(`/api/proxy/api/v1/chat/conversations?limit=${limit}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        credentials: 'include',
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to list conversations')
      }
      
      return await response.json()
    } catch (error) {
      console.error('Failed to list conversations:', error)
      throw error
    }
  }
  
  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId: string): Promise<void> {
    try {
      const response = await fetch(`/api/proxy/api/v1/chat/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        credentials: 'include',
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to delete conversation')
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      throw error
    }
  }
  
  
  /**
   * Send a non-streaming message (for system messages or fallback)
   */
  async sendMessage(
    conversationId: string,
    text: string,
    metadata?: Record<string, any>
  ): Promise<Message> {
    const operation = async () => {
      const response = await fetch('/api/proxy/api/v1/chat/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        credentials: 'include',
        body: JSON.stringify({
          conversation_id: conversationId,
          text,
          ...(metadata && { metadata })
        }),
      })
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw { status: response.status, ...error }
      }
      
      // For non-streaming, we'd need to handle the response differently
      // This is a placeholder - actual implementation depends on backend
      return await response.json()
    }
    
    try {
      return await operation()
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorType = this.classifyError(error)
      return this.executeRetryPolicy(errorType, operation)
    }
  }
  
  /**
   * Update conversation mode
   */
  async updateConversationMode(
    conversationId: string,
    mode: 'green' | 'blue' | 'indigo' | 'violet'
  ): Promise<Conversation> {
    const operation = async () => {
      const response = await fetch(
        `/api/proxy/api/v1/chat/conversations/${conversationId}/mode`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
          credentials: 'include',
          body: JSON.stringify({ mode }),
        }
      )
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}))
        throw { status: response.status, ...error }
      }
      
      return await response.json()
    }
    
    try {
      return await operation()
    } catch (error) {
      console.error('Failed to update conversation mode:', error)
      const errorType = this.classifyError(error)
      return this.executeRetryPolicy(errorType, operation)
    }
  }
  
  /**
   * Clear all retry timeouts
   */
  clearRetryTimeouts(): void {
    this.retryTimeouts.forEach(timeout => clearTimeout(timeout))
    this.retryTimeouts.clear()
  }
}

export const chatService = new ChatService()

// Export types for use in other components
export type { Conversation, Message, ErrorPolicy }