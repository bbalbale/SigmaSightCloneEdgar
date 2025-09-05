/**
 * Chat Store - Persistent data management
 * Handles conversations, messages, and UI state
 * Streaming state moved to streamStore.ts
 * Based on Technical Specifications Section 2
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Types from Technical Specifications
interface Message {
  id: string
  conversationId: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  toolCalls?: any[]
  runId?: string // Reference to streaming run if applicable
  error?: {
    message: string
    error_type?: 'AUTH_EXPIRED' | 'RATE_LIMITED' | 'NETWORK_ERROR' | 'SERVER_ERROR' | 'FATAL_ERROR'
  }
}

interface Conversation {
  id: string
  title: string
  mode: 'green' | 'blue' | 'indigo' | 'violet'
  createdAt: Date
  updatedAt: Date
  messageCount: number
  lastMessage?: string
}

interface ChatStore {
  // Persistent State
  conversations: Map<string, Conversation>
  messages: Map<string, Message[]> // Messages by conversationId
  currentConversationId: string | null
  currentMode: 'green' | 'blue' | 'indigo' | 'violet'
  isOpen: boolean
  
  // Actions for Conversations
  createConversation: (mode?: 'green' | 'blue' | 'indigo' | 'violet', backendId?: string) => string
  loadConversation: (conversationId: string) => void
  deleteConversation: (conversationId: string) => void
  updateConversationTitle: (conversationId: string, title: string) => void
  
  // Actions for Messages
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>, backendId?: string) => void
  updateMessage: (messageId: string, updates: Partial<Message>) => void
  getMessage: (messageId: string) => Message | undefined
  getMessages: (conversationId?: string) => Message[]
  clearMessages: (conversationId?: string) => void
  
  // Backend ID coordination
  handleMessageCreated: (event: {
    user_message_id: string
    assistant_message_id: string
    conversation_id: string
    run_id: string
  }) => void
  
  // UI Actions
  setOpen: (open: boolean) => void
  setMode: (mode: 'green' | 'blue' | 'indigo' | 'violet') => void
  
  // Utility Actions
  reset: () => void
  hydrateFromStorage: () => void
}

const initialState = {
  conversations: new Map(),
  messages: new Map(),
  currentConversationId: null,
  currentMode: 'green' as const,
  isOpen: false,
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      // Initial state
      ...initialState,
      
      // Create new conversation
      createConversation: (mode = 'green', backendId?: string) => {
        // Use backend ID if provided, otherwise generate valid UUID
        // FIX 6.50: Use crypto.randomUUID() for valid UUID format
        const conversationId = backendId || crypto.randomUUID()
        const conversation: Conversation = {
          id: conversationId,
          title: 'New Conversation',
          mode,
          createdAt: new Date(),
          updatedAt: new Date(),
          messageCount: 0,
        }
        
        set((state) => {
          const conversations = new Map(state.conversations)
          conversations.set(conversationId, conversation)
          return {
            conversations,
            currentConversationId: conversationId,
            currentMode: mode,
          }
        })
        
        return conversationId
      },
      
      // Load existing conversation
      loadConversation: (conversationId: string) => {
        const state = get()
        const conversation = state.conversations.get(conversationId)
        
        if (conversation) {
          set({
            currentConversationId: conversationId,
            currentMode: conversation.mode,
          })
        }
      },
      
      // Delete conversation
      deleteConversation: (conversationId: string) => {
        set((state) => {
          const conversations = new Map(state.conversations)
          const messages = new Map(state.messages)
          
          conversations.delete(conversationId)
          messages.delete(conversationId)
          
          // If deleting current conversation, clear it
          const newState: any = { conversations, messages }
          if (state.currentConversationId === conversationId) {
            newState.currentConversationId = null
          }
          
          return newState
        })
      },
      
      // Update conversation title
      updateConversationTitle: (conversationId: string, title: string) => {
        set((state) => {
          const conversations = new Map(state.conversations)
          const conversation = conversations.get(conversationId)
          
          if (conversation) {
            conversation.title = title
            conversation.updatedAt = new Date()
            conversations.set(conversationId, conversation)
          }
          
          return { conversations }
        })
      },
      
      // Add message to conversation (requires backend ID)
      addMessage: (messageData, backendId?: string) => {
        const state = get()
        let conversationId = messageData.conversationId || state.currentConversationId
        
        // Create conversation if none exists
        if (!conversationId) {
          conversationId = state.createConversation(state.currentMode)
        }
        
        // CRITICAL: Require backend ID - no frontend generation
        if (!backendId) {
          console.error('[chatStore] Cannot add message without backend ID')
          return
        }
        
        const message: Message = {
          ...messageData,
          id: backendId, // Use backend-provided ID
          conversationId,
          timestamp: new Date(),
        }
        
        set((state) => {
          // Update messages
          const messages = new Map(state.messages)
          const conversationMessages = messages.get(conversationId) || []
          messages.set(conversationId, [...conversationMessages, message])
          
          // Update conversation metadata
          const conversations = new Map(state.conversations)
          const conversation = conversations.get(conversationId)
          
          if (conversation) {
            conversation.messageCount = conversationMessages.length + 1
            conversation.updatedAt = new Date()
            if (message.role === 'user') {
              conversation.lastMessage = message.content.slice(0, 100)
            }
            conversations.set(conversationId, conversation)
          }
          
          return { messages, conversations }
        })
      },
      
      // Update existing message
      updateMessage: (messageId: string, updates: Partial<Message>) => {
        set((state) => {
          const messages = new Map(state.messages)
          
          // Find and update the message
          for (const [convId, convMessages] of messages.entries()) {
            const messageIndex = convMessages.findIndex(m => m.id === messageId)
            if (messageIndex !== -1) {
              convMessages[messageIndex] = {
                ...convMessages[messageIndex],
                ...updates,
              }
              messages.set(convId, [...convMessages])
              break
            }
          }
          
          return { messages }
        })
      },
      
      // Get single message by ID
      getMessage: (messageId: string) => {
        const state = get()
        // Search through all conversations for the message
        for (const [, messages] of state.messages.entries()) {
          const message = messages.find(m => m.id === messageId)
          if (message) return message
        }
        return undefined
      },
      
      // Get messages for current or specific conversation
      getMessages: (conversationId?: string) => {
        const state = get()
        const targetId = conversationId || state.currentConversationId
        if (!targetId) return []
        return state.messages.get(targetId) || []
      },
      
      // Clear messages
      clearMessages: (conversationId?: string) => {
        set((state) => {
          const messages = new Map(state.messages)
          const targetId = conversationId || state.currentConversationId
          
          if (targetId) {
            messages.set(targetId, [])
            
            // Update conversation metadata
            const conversations = new Map(state.conversations)
            const conversation = conversations.get(targetId)
            if (conversation) {
              conversation.messageCount = 0
              conversation.lastMessage = undefined
              conversation.updatedAt = new Date()
              conversations.set(targetId, conversation)
            }
            
            return { messages, conversations }
          }
          
          return state
        })
      },
      
      // Handle message_created event from backend SSE
      handleMessageCreated: (event) => {
        const state = get()
        const { user_message_id, assistant_message_id, conversation_id, run_id } = event
        
        // Check if messages already exist (avoid duplicates)
        const existingUser = state.getMessage(user_message_id)
        const existingAssistant = state.getMessage(assistant_message_id)
        
        if (existingUser && existingAssistant) {
          console.log('[chatStore] Messages already exist, skipping creation')
          return
        }
        
        // If messages don't exist, they should be created via addMessage
        // This handler is primarily for coordinating with streamStore
        console.log('[chatStore] Message IDs received from backend:', {
          user_message_id,
          assistant_message_id,
          conversation_id,
          run_id
        })
        
        // Store the run_id reference if needed
        if (assistant_message_id && run_id) {
          // Update assistant message with run_id
          state.updateMessage(assistant_message_id, { runId: run_id })
        }
      },
      
      // UI Actions
      setOpen: (open: boolean) => set({ isOpen: open }),
      
      setMode: (mode: 'green' | 'blue' | 'indigo' | 'violet') => {
        set((state) => {
          const newState: any = { currentMode: mode }
          
          // Update current conversation's mode if exists
          if (state.currentConversationId) {
            const conversations = new Map(state.conversations)
            const conversation = conversations.get(state.currentConversationId)
            if (conversation) {
              conversation.mode = mode
              conversation.updatedAt = new Date()
              conversations.set(state.currentConversationId, conversation)
              newState.conversations = conversations
            }
          }
          
          return newState
        })
      },
      
      // Reset store
      reset: () => set(initialState),
      
      // Hydrate from storage (for persist middleware)
      hydrateFromStorage: () => {
        // FIX 6.49: Sync with localStorage conversation ID
        const storedConversationId = localStorage.getItem('conversationId')
        const currentStoredId = localStorage.getItem('currentConversationId')
        
        // Prioritize localStorage over persisted store state
        if (storedConversationId || currentStoredId) {
          const validId = storedConversationId || currentStoredId
          
          // Validate UUID format (FIX 6.50)
          const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
          if (validId && uuidRegex.test(validId)) {
            set({ currentConversationId: validId })
            console.log('[ChatStore] Synced conversation ID from localStorage:', validId)
          } else {
            console.warn('[ChatStore] Invalid conversation ID format in localStorage:', validId)
            // Clear invalid ID
            localStorage.removeItem('conversationId')
            localStorage.removeItem('currentConversationId')
          }
        }
      },
    }),
    {
      name: 'chat-storage',
      // Custom storage serialization for Maps
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name)
          if (!str) return null
          
          const { state } = JSON.parse(str)
          return {
            state: {
              ...state,
              conversations: new Map(state.conversations || []),
              messages: new Map(state.messages || []),
            },
          }
        },
        setItem: (name, value) => {
          const toStore = {
            state: {
              ...value.state,
              conversations: Array.from(value.state.conversations.entries()),
              messages: Array.from(value.state.messages.entries()),
            },
          }
          localStorage.setItem(name, JSON.stringify(toStore))
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
    }
  )
)

// Export types
export type { Message, Conversation }