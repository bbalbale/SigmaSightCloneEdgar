/**
 * Chat Service
 * Handles conversation management with the backend API
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

class ChatService {
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
}

export const chatService = new ChatService()