/**
 * Claude Insights Service - SSE streaming service for Claude chat
 *
 * Handles:
 * - SSE connection to /api/v1/insights/chat
 * - Event processing (start, message, done, error)
 * - Store updates
 * - Authentication
 */

import { useClaudeInsightsStore } from '@/stores/claudeInsightsStore'
import type { ClaudeMessage } from '@/stores/claudeInsightsStore'

const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000/api/v1'

interface SendMessageOptions {
  message: string
  conversationId?: string
  onStart?: (data: any) => void
  onMessage?: (chunk: string) => void
  onDone?: (data: any) => void
  onError?: (error: string) => void
}

/**
 * Send a message to Claude and stream the response
 */
export async function sendClaudeMessage(options: SendMessageOptions): Promise<void> {
  const { message, conversationId, onStart, onMessage, onDone, onError } = options

  // Get auth token from localStorage
  const token = localStorage.getItem('access_token')
  if (!token) {
    const error = 'Not authenticated'
    onError?.(error)
    throw new Error(error)
  }

  // Prepare request body
  const body: any = { message }
  if (conversationId) {
    body.conversation_id = conversationId
  }

  // Make fetch request with SSE streaming
  try {
    const response = await fetch(`${BACKEND_API_URL}/insights/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify(body)
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`HTTP ${response.status}: ${errorText}`)
    }

    // Process SSE stream
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true })

      // Process complete SSE messages (end with \n\n)
      const messages = buffer.split('\n\n')
      buffer = messages.pop() || '' // Keep incomplete message in buffer

      for (const msg of messages) {
        if (!msg.trim()) continue

        // Parse SSE format: "event: type\ndata: {...}"
        const lines = msg.split('\n')
        let eventType = 'message'
        let data: any = null

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.substring(6).trim()
          } else if (line.startsWith('data:')) {
            const dataStr = line.substring(5).trim()
            try {
              data = JSON.parse(dataStr)
            } catch (e) {
              console.warn('Failed to parse SSE data:', dataStr)
            }
          }
        }

        // Handle event
        if (data) {
          handleSSEEvent(eventType, data, { onStart, onMessage, onDone, onError })
        }
      }
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    console.error('Claude chat error:', errorMessage)
    onError?.(errorMessage)
    throw error
  }
}

/**
 * Handle SSE events and update store
 */
function handleSSEEvent(
  eventType: string,
  data: any,
  callbacks: Pick<SendMessageOptions, 'onStart' | 'onMessage' | 'onDone' | 'onError'>
) {
  const store = useClaudeInsightsStore.getState()
  const { onStart, onMessage, onDone, onError } = callbacks

  switch (eventType) {
    case 'start':
      console.log('[Claude] Stream started:', data)

      // Set conversation ID if new
      if (data.conversation_id && !store.conversationId) {
        store.setConversationId(data.conversation_id)
      }

      // Start streaming
      store.startStreaming(data.run_id)
      onStart?.(data)
      break

    case 'message':
      console.log('[Claude] Message chunk:', data)

      // Append text chunk
      if (data.delta) {
        store.appendStreamingText(data.delta)
        onMessage?.(data.delta)
      }
      break

    case 'done':
      console.log('[Claude] Stream complete:', data)

      // Create final assistant message
      const finalMessage: ClaudeMessage = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: data.data?.final_text || store.streamingText,
        timestamp: new Date(),
        tool_calls_count: data.data?.tool_calls_count || 0
      }

      // Stop streaming and save message
      store.stopStreaming(finalMessage)
      onDone?.(data)
      break

    case 'error':
      console.error('[Claude] Stream error:', data)

      const errorMessage = data.error || 'Unknown error'
      store.setError(errorMessage)
      store.stopStreaming()
      onError?.(errorMessage)
      break

    default:
      console.warn('[Claude] Unknown event type:', eventType, data)
  }
}

/**
 * Create a new conversation
 */
export function createNewConversation(): void {
  const store = useClaudeInsightsStore.getState()
  store.reset()
}

/**
 * Send a message with store integration
 */
export async function sendMessage(message: string): Promise<void> {
  const store = useClaudeInsightsStore.getState()

  // Add user message to store
  const userMessage: ClaudeMessage = {
    id: `msg_${Date.now()}`,
    role: 'user',
    content: message,
    timestamp: new Date()
  }
  store.addMessage(userMessage)

  // Send to Claude
  await sendClaudeMessage({
    message,
    conversationId: store.conversationId || undefined
  })
}
