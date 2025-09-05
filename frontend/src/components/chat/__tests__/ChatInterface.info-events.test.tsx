import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import { ChatInterface } from '@/components/chat/ChatInterface'
import { useChatStore } from '@/stores/chatStore'
import { useStreamStore } from '@/stores/streamStore'

// Mock streaming hook to emit message_created and info events
vi.mock('@/hooks/useFetchStreaming', () => {
  return {
    useFetchStreaming: () => ({
      streamMessage: vi.fn(async (
        conversationId: string,
        text: string,
        options: any
      ) => {
        // Provide backend IDs
        options?.onMessageCreated?.({
          user_message_id: 'user_msg_1',
          assistant_message_id: 'asst_msg_1',
          conversation_id: conversationId,
          run_id: 'run_test_1',
        })

        // Emit info events
        options?.onInfo?.({
          info_type: 'retry_scheduled',
          attempt: 2,
          max_attempts: 3,
          retry_in_ms: 1400, // should render ~1.4s
        })

        options?.onInfo?.({
          info_type: 'model_switch',
          from: 'primary',
          to: 'fallback',
          attempt: 2,
        })

        // Finish stream
        options?.onDone?.('Answer complete.')
        return 'run_test_1'
      }),
      abortStream: vi.fn(),
    }),
  }
})

// Mock auth to always succeed
vi.mock('@/services/chatAuthService', () => ({
  chatAuthService: {
    refreshIfNeeded: vi.fn().mockResolvedValue(true),
  },
}))

// Optional: mock chatService to avoid any accidental calls
vi.mock('@/services/chatService', () => ({
  chatService: {
    createConversation: vi.fn(async (mode: string) => ({ id: 'conv_test' })),
    updateConversationMode: vi.fn(async () => ({ ok: true })),
  },
}))

// Helpers to reset stores and localStorage between tests
const resetAllStores = () => {
  try {
    localStorage.clear()
  } catch {}
  const chat = useChatStore.getState()
  chat.reset()
  const stream = useStreamStore.getState()
  stream.reset()
}

describe('ChatInterface - info events integration', () => {
  beforeEach(() => {
    resetAllStores()
    // Open chat sheet and ensure a conversation exists
    const chat = useChatStore.getState()
    chat.setOpen(true)
    chat.createConversation('green', 'conv_test')
  })

  it('renders system messages for retry and model switch info events', async () => {
    render(<ChatInterface />)

    const input = await screen.findByPlaceholderText(/Type your message/i)
    fireEvent.change(input, { target: { value: 'Hello there' } })

    const sendBtn = screen.getByRole('button', { name: /Send/i })
    fireEvent.click(sendBtn)

    // User message should appear (added after onMessageCreated)
    await screen.findByText('Hello there')

    // System info: retry_scheduled
    await screen.findByText(
      /Temporary issue detected\. Retrying 2\/3 in 1\.4s\.\.\./i,
      {},
      { timeout: 5000 }
    )

    // System info: model_switch
    await screen.findByText(
      /Switching model from primary to fallback \(attempt 2\)\./i,
      {},
      { timeout: 5000 }
    )
  })
})
