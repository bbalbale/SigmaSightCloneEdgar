/**
 * useCopilot Hook - Reusable hook for AI copilot functionality
 *
 * Wraps aiChatStore and provides a clean API for any component
 * to interact with the AI copilot.
 *
 * Per SIGMASIGHT_AGENT_EXECUTION_PLAN.md:
 * - Uses OpenAI as the default LLM provider
 * - Provider-agnostic design for future flexibility
 *
 * Features:
 * - Message sending with SSE streaming
 * - Conversation management
 * - Optional page hints for future prefill logic
 * - Feedback integration
 */

import { useCallback, useMemo } from 'react'
import { useAIChatStore, AIChatMessage } from '@/stores/aiChatStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { sendMessage as sendAIMessage, createNewConversation } from '@/services/aiChatService'
import { submitFeedback } from '@/services/feedbackService'

export type PageHint =
  | 'portfolio'
  | 'public-positions'
  | 'private-positions'
  | 'organize'
  | 'ai-chat'
  | 'settings'
  | string

export interface CopilotOptions {
  /**
   * Page hint for context-aware suggestions
   * Can be used for future prefill/commentary logic
   */
  pageHint?: PageHint

  /**
   * Route path for finer context scoping
   */
  route?: string

  /**
   * Current selection on the page (symbol, tag, etc.)
   */
  selection?: Record<string, unknown>

  /**
   * Callback when an insight is ready (for prefill/commentary)
   */
  onInsightReady?: (insight: string) => void
}

export interface UseCopilotReturn {
  // State
  messages: AIChatMessage[]
  isStreaming: boolean
  streamingText: string
  error: string | null
  conversationId: string | null
  hasMessages: boolean

  // Actions
  sendMessage: (message: string) => Promise<void>
  resetConversation: () => void
  submitMessageFeedback: (message: AIChatMessage, rating: 'up' | 'down') => Promise<void>
  clearError: () => void

  // Page context
  pageHint?: PageHint
}

/**
 * Hook for interacting with the AI copilot
 *
 * @param options - Optional configuration for the copilot
 * @returns Copilot state and actions
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const {
 *     messages,
 *     isStreaming,
 *     sendMessage,
 *     resetConversation
 *   } = useCopilot({ pageHint: 'portfolio' })
 *
 *   return (
 *     <div>
 *       {messages.map(msg => <Message key={msg.id} {...msg} />)}
 *       <button onClick={() => sendMessage('Hello!')}>Send</button>
 *     </div>
 *   )
 * }
 * ```
 */
export function useCopilot(options?: CopilotOptions): UseCopilotReturn {
  const {
    messages,
    isStreaming,
    streamingText,
    error,
    conversationId,
    setError,
    updateMessage
  } = useAIChatStore()

  const portfolioId = usePortfolioStore(state => state.portfolioId)
  const portfolios = usePortfolioStore(state => state.portfolios)
  const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)

  const portfolioIds = useMemo(() => {
    // If aggregate view (selectedPortfolioId null) include all; else include selected/effective
    if (selectedPortfolioId === null && portfolios.length > 0) {
      return portfolios.map(p => p.id)
    }
    const effective = selectedPortfolioId || portfolioId
    return effective ? [effective] : []
  }, [selectedPortfolioId, portfolioId, portfolios])

  const { pageHint, route, selection, onInsightReady } = options || {}

  /**
   * Send a message to the AI copilot
   */
  const sendMessage = useCallback(async (message: string) => {
    if (!message.trim()) return

    try {
      await sendAIMessage(message, {
        pageHint,
        route,
        selection,
        portfolioId: portfolioId || undefined,
        portfolioIds,
      })

      // If callback provided, notify when response is ready
      if (onInsightReady) {
        // Get the latest assistant message after streaming completes
        const store = useAIChatStore.getState()
        const lastMessage = store.messages[store.messages.length - 1]
        if (lastMessage?.role === 'assistant') {
          onInsightReady(lastMessage.content)
        }
      }
    } catch (err) {
      console.error('Failed to send message:', err)
      // Error is already handled by the service and stored in the store
    }
  }, [onInsightReady])

  /**
   * Reset the conversation and start fresh
   */
  const resetConversation = useCallback(() => {
    createNewConversation()
  }, [])

  /**
   * Submit feedback for a message
   */
  const submitMessageFeedback = useCallback(async (
    message: AIChatMessage,
    rating: 'up' | 'down'
  ) => {
    // Only allow feedback on assistant messages with backend IDs
    if (!message.backendMessageId || message.role !== 'assistant') {
      console.warn('Cannot submit feedback: no backend message ID or not assistant message')
      return
    }

    // Toggle off if same rating clicked again
    const newRating = message.feedback === rating ? null : rating
    const previousRating = message.feedback

    // Optimistic update
    updateMessage(message.id, { feedback: newRating || undefined })

    try {
      if (newRating) {
        await submitFeedback(message.backendMessageId, { rating: newRating })
      }
      // Note: If clearing feedback (newRating is null), we could call deleteFeedback
      // For now, we just update the UI
    } catch (err) {
      console.error('Failed to submit feedback:', err)
      // Revert on error
      updateMessage(message.id, { feedback: previousRating })
    }
  }, [updateMessage])

  /**
   * Clear any error state
   */
  const clearError = useCallback(() => {
    setError(null)
  }, [setError])

  /**
   * Whether there are any messages in the conversation
   */
  const hasMessages = useMemo(() => messages.length > 0, [messages])

  return {
    // State
    messages,
    isStreaming,
    streamingText,
    error,
    conversationId,
    hasMessages,

    // Actions
    sendMessage,
    resetConversation,
    submitMessageFeedback,
    clearError,

    // Page context
    pageHint
  }
}

export default useCopilot
