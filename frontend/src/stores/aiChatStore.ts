/**
 * AI Chat Store - State management for AI chat on SigmaSight AI page
 *
 * Renamed from claudeInsightsStore.ts to reflect provider-agnostic design.
 * Currently uses OpenAI as the default LLM provider.
 *
 * Per SIGMASIGHT_AGENT_EXECUTION_PLAN.md:
 * - OpenAI is the default provider
 * - Store is provider-agnostic for future flexibility
 *
 * Handles:
 * - Conversation state
 * - Message history
 * - Streaming state
 * - SSE event processing
 */

import { create } from 'zustand'

export interface AIChatMessage {
  id: string
  backendMessageId?: string  // Backend-generated UUID for feedback
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  tool_calls_count?: number
  error?: string
  feedback?: 'up' | 'down' | null  // User feedback rating
}

interface AIChatStore {
  // Conversation state
  conversationId: string | null
  messages: AIChatMessage[]

  // Streaming state
  isStreaming: boolean
  streamingText: string
  currentRunId: string | null

  // Error state
  error: string | null

  // Actions
  setConversationId: (id: string) => void
  addMessage: (message: AIChatMessage) => void
  updateMessage: (messageId: string, updates: Partial<AIChatMessage>) => void
  updateStreamingText: (text: string) => void
  appendStreamingText: (chunk: string) => void
  startStreaming: (runId: string) => void
  stopStreaming: (finalMessage?: AIChatMessage) => void
  setError: (error: string | null) => void
  clearMessages: () => void
  reset: () => void
}

const initialState = {
  conversationId: null,
  messages: [],
  isStreaming: false,
  streamingText: '',
  currentRunId: null,
  error: null,
}

export const useAIChatStore = create<AIChatStore>((set, get) => ({
  ...initialState,

  // Set conversation ID
  setConversationId: (id: string) => {
    set({ conversationId: id })
  },

  // Add a message to history
  addMessage: (message: AIChatMessage) => {
    set(state => ({
      messages: [...state.messages, message]
    }))
  },

  // Update an existing message (for feedback, etc.)
  updateMessage: (messageId: string, updates: Partial<AIChatMessage>) => {
    set(state => ({
      messages: state.messages.map(msg =>
        msg.id === messageId ? { ...msg, ...updates } : msg
      )
    }))
  },

  // Update streaming text (replace entirely)
  updateStreamingText: (text: string) => {
    set({ streamingText: text })
  },

  // Append to streaming text
  appendStreamingText: (chunk: string) => {
    set(state => ({
      streamingText: state.streamingText + chunk
    }))
  },

  // Start streaming
  startStreaming: (runId: string) => {
    set({
      isStreaming: true,
      currentRunId: runId,
      streamingText: '',
      error: null
    })
  },

  // Stop streaming and optionally save final message
  stopStreaming: (finalMessage?: AIChatMessage) => {
    const state = get()

    const updates: Partial<AIChatStore> = {
      isStreaming: false,
      currentRunId: null,
      streamingText: ''
    }

    // If final message provided, add it
    if (finalMessage) {
      updates.messages = [...state.messages, finalMessage]
    } else if (state.streamingText) {
      // Or create message from streaming text
      const assistantMessage: AIChatMessage = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: state.streamingText,
        timestamp: new Date()
      }
      updates.messages = [...state.messages, assistantMessage]
    }

    set(updates)
  },

  // Set error
  setError: (error: string | null) => {
    set({ error })
  },

  // Clear messages
  clearMessages: () => {
    set({ messages: [] })
  },

  // Reset entire store
  reset: () => {
    set(initialState)
  }
}))

// Export types
export type { AIChatStore }
