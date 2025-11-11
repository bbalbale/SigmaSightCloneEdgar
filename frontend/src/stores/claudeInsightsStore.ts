/**
 * Claude Insights Store - State management for Claude chat on SigmaSight AI page
 *
 * Handles:
 * - Conversation state
 * - Message history
 * - Streaming state
 * - SSE event processing
 */

import { create } from 'zustand'

export interface ClaudeMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  tool_calls_count?: number
  error?: string
}

interface ClaudeInsightsStore {
  // Conversation state
  conversationId: string | null
  messages: ClaudeMessage[]

  // Streaming state
  isStreaming: boolean
  streamingText: string
  currentRunId: string | null

  // Error state
  error: string | null

  // Actions
  setConversationId: (id: string) => void
  addMessage: (message: ClaudeMessage) => void
  updateStreamingText: (text: string) => void
  appendStreamingText: (chunk: string) => void
  startStreaming: (runId: string) => void
  stopStreaming: (finalMessage?: ClaudeMessage) => void
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

export const useClaudeInsightsStore = create<ClaudeInsightsStore>((set, get) => ({
  ...initialState,

  // Set conversation ID
  setConversationId: (id: string) => {
    set({ conversationId: id })
  },

  // Add a message to history
  addMessage: (message: ClaudeMessage) => {
    set(state => ({
      messages: [...state.messages, message]
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
  stopStreaming: (finalMessage?: ClaudeMessage) => {
    const state = get()

    const updates: Partial<ClaudeInsightsStore> = {
      isStreaming: false,
      currentRunId: null,
      streamingText: ''
    }

    // If final message provided, add it
    if (finalMessage) {
      updates.messages = [...state.messages, finalMessage]
    } else if (state.streamingText) {
      // Or create message from streaming text
      const assistantMessage: ClaudeMessage = {
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
export type { ClaudeInsightsStore }
