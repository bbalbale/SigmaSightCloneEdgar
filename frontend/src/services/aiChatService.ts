/**
 * AI Chat Service - SSE streaming service for AI chat
 *
 * Renamed from claudeInsightsService.ts to reflect provider-agnostic design.
 * Uses OpenAI Responses API via /chat/send endpoint.
 *
 * Per SIGMASIGHT_AGENT_EXECUTION_PLAN.md:
 * - OpenAI is the default provider
 * - Uses Responses API (NOT Chat Completions API)
 *
 * Handles:
 * - SSE connection to /api/v1/chat/conversations/{id}/send
 * - Automatic conversation creation with portfolio context
 * - Event processing (start, token, tool_call, tool_result, done, error)
 * - Store updates
 * - Authentication
 */

import { useAIChatStore } from '@/stores/aiChatStore'
import type { AIChatMessage } from '@/stores/aiChatStore'
import { usePortfolioStore } from '@/stores/portfolioStore'

const BACKEND_API_URL = process.env.NEXT_PUBLIC_BACKEND_API_URL || 'http://localhost:8000/api/v1'

interface SendMessageOptions {
  message: string
  conversationId?: string
  portfolioId?: string
  onStart?: (data: any) => void
  onMessage?: (chunk: string) => void
  onToolCall?: (data: any) => void
  onToolResult?: (data: any) => void
  onDone?: (data: any) => void
  onError?: (error: string) => void
}

interface CreateConversationResponse {
  id: string
  mode: string
  created_at: string
  provider: string
}

/**
 * Create a new conversation with portfolio context
 */
async function createConversation(portfolioId?: string): Promise<CreateConversationResponse> {
  const token = localStorage.getItem('access_token')
  if (!token) {
    throw new Error('Not authenticated')
  }

  const payload: any = { mode: 'green' }
  if (portfolioId) {
    payload.portfolio_id = portfolioId
  }

  const response = await fetch(`${BACKEND_API_URL}/chat/conversations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload)
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`Failed to create conversation: HTTP ${response.status}: ${errorText}`)
  }

  return await response.json()
}

/**
 * Send a message to the AI and stream the response via SSE
 * Uses OpenAI Responses API backend endpoint
 */
export async function sendAIMessage(options: SendMessageOptions): Promise<void> {
  const { message, onStart, onMessage, onToolCall, onToolResult, onDone, onError } = options
  let { conversationId, portfolioId } = options

  // Get auth token from localStorage
  const token = localStorage.getItem('access_token')
  if (!token) {
    const error = 'Not authenticated'
    onError?.(error)
    throw new Error(error)
  }

  // Get portfolio ID from store if not provided
  if (!portfolioId) {
    portfolioId = usePortfolioStore.getState().portfolioId || undefined
  }

  // Get conversation ID from store if not provided
  if (!conversationId) {
    conversationId = useAIChatStore.getState().conversationId || undefined
  }

  // Create conversation if needed
  if (!conversationId) {
    try {
      console.log('[AI] Creating new conversation with portfolio:', portfolioId)
      const conversation = await createConversation(portfolioId)
      conversationId = conversation.id

      // Store the conversation ID
      useAIChatStore.getState().setConversationId(conversationId)
      console.log('[AI] Created conversation:', conversationId)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create conversation'
      console.error('[AI] Failed to create conversation:', errorMessage)
      onError?.(errorMessage)
      throw error
    }
  }

  // Prepare request body for /chat/send endpoint
  const body = {
    conversation_id: conversationId,
    text: message
  }

  // Make fetch request with SSE streaming to /chat/send
  try {
    const response = await fetch(`${BACKEND_API_URL}/chat/send`, {
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
          handleSSEEvent(eventType, data, { onStart, onMessage, onToolCall, onToolResult, onDone, onError })
        }
      }
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    console.error('AI chat error:', errorMessage)
    onError?.(errorMessage)
    throw error
  }
}

// Store pending assistant message ID from message_created event
let pendingAssistantMessageId: string | null = null

/**
 * Handle SSE events and update store
 */
function handleSSEEvent(
  eventType: string,
  data: any,
  callbacks: Pick<SendMessageOptions, 'onStart' | 'onMessage' | 'onToolCall' | 'onToolResult' | 'onDone' | 'onError'>
) {
  const store = useAIChatStore.getState()
  const { onStart, onMessage, onToolCall, onToolResult, onDone, onError } = callbacks

  switch (eventType) {
    case 'start':
      console.log('[AI] Stream started:', data)

      // Set conversation ID if new
      if (data.data?.conversation_id && !store.conversationId) {
        store.setConversationId(data.data.conversation_id)
      }

      // Start streaming
      store.startStreaming(data.run_id)
      onStart?.(data)
      break

    case 'message_created':
      // Capture the backend-generated assistant message ID for feedback
      console.log('[AI] Message created:', data)
      if (data.assistant_message_id) {
        pendingAssistantMessageId = data.assistant_message_id
      }
      break

    case 'response_id':
      // Track OpenAI response ID for debugging
      console.log('[AI] Response ID:', data.data?.response_id)
      break

    case 'message':
      // Legacy message format - append text chunk
      if (data.delta) {
        store.appendStreamingText(data.delta)
        onMessage?.(data.delta)
      }
      break

    case 'token':
      // Handle token events from OpenAI Responses API
      if (data.data?.delta) {
        store.appendStreamingText(data.data.delta)
        onMessage?.(data.data.delta)
      }
      break

    case 'tool_call':
      // Tool call started
      console.log('[AI] Tool call:', data.data?.tool_name, data.data?.tool_args)
      onToolCall?.(data)
      break

    case 'tool_result':
      // Tool call completed with result
      console.log('[AI] Tool result:', data.data?.tool_name, 'duration:', data.data?.duration_ms, 'ms')
      onToolResult?.(data)
      break

    case 'done':
      console.log('[AI] Stream complete:', data)

      // Create final assistant message with backend ID
      const finalMessage: AIChatMessage = {
        id: `msg_${Date.now()}`,
        backendMessageId: pendingAssistantMessageId || undefined,
        role: 'assistant',
        content: data.data?.final_text || store.streamingText,
        timestamp: new Date(),
        tool_calls_count: data.data?.tool_calls_count || 0
      }

      // Clear pending ID
      pendingAssistantMessageId = null

      // Stop streaming and save message
      store.stopStreaming(finalMessage)
      onDone?.(data)
      break

    case 'error':
      console.error('[AI] Stream error:', data)

      const errorMessage = data.error || data.data?.error || 'Unknown error'
      store.setError(errorMessage)
      store.stopStreaming()
      pendingAssistantMessageId = null
      onError?.(errorMessage)
      break

    case 'heartbeat':
      // Heartbeat to keep connection alive
      break

    case 'info':
      // Info events (retry info, model switch, etc.)
      console.log('[AI] Info:', data.data?.info_type, data)
      break

    default:
      console.warn('[AI] Unknown event type:', eventType, data)
  }
}

/**
 * Create a new conversation
 */
export function createNewConversation(): void {
  const store = useAIChatStore.getState()
  store.reset()
}

/**
 * Send a message with store integration
 */
export async function sendMessage(message: string): Promise<void> {
  const store = useAIChatStore.getState()

  // Add user message to store
  const userMessage: AIChatMessage = {
    id: `msg_${Date.now()}`,
    role: 'user',
    content: message,
    timestamp: new Date()
  }
  store.addMessage(userMessage)

  // Send to AI
  await sendAIMessage({
    message,
    conversationId: store.conversationId || undefined
  })
}
