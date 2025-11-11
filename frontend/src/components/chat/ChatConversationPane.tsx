"use client"

import React, { useEffect, useRef, useCallback } from 'react'
import { ChatInput } from '@/components/app/ChatInput'
import { MessageSquare, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/stores/chatStore'
import { useStreamStore } from '@/stores/streamStore'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useFetchStreaming } from '@/hooks/useFetchStreaming'
import type { StreamingOptions } from '@/hooks/useFetchStreaming'
import { chatAuthService } from '@/services/chatAuthService'
import { chatService } from '@/services/chatService'

interface ChatConversationPaneProps {
  className?: string
  isActive?: boolean
  variant?: 'sheet' | 'inline'
  title?: string
  subtitle?: string
  onConversationReset?: () => void
  initialMessage?: string
}

export function ChatConversationPane({
  className,
  isActive = true,
  variant = 'inline',
  title = 'SigmaSight AI Assistant',
  subtitle = 'Ask questions about your portfolio',
  onConversationReset,
  initialMessage,
}: ChatConversationPaneProps) {
  // Log when component receives initialMessage prop
  console.log('[ChatConversationPane] Component rendered with:', {
    isActive,
    variant,
    hasInitialMessage: !!initialMessage,
    initialMessage
  })

  const {
    currentMode,
    currentConversationId,
    setMode,
    addMessage,
    updateMessage,
    getMessages,
    createConversation,
    handleMessageCreated,
  } = useChatStore()

  const {
    isStreaming,
    currentRunId,
    streamBuffers,
    messageQueue,
    queueMessage,
    processQueue,
    setAssistantMessageId,
    reset: resetStreamState,
  } = useStreamStore()

  const { portfolioId } = usePortfolioStore()

  const { streamMessage, abortStream } = useFetchStreaming()

  const messages = getMessages()
  const streamBuffersSize = streamBuffers.size

  const currentAssistantMessageIdRef = useRef<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const infoMessageCounterRef = useRef(0)
  const [isInitialized, setIsInitialized] = React.useState(false)
  const handleSendMessageRef = useRef<((text: string) => Promise<void>) | null>(null)

  useEffect(() => {
    if (!isActive || isInitialized) {
      return
    }

    const syncConversation = () => {
      console.log('[ChatConversationPane] Starting initialization...')

      // Only clear stream state, not conversation state
      // Conversation state is managed by chat store and should persist
      console.log('[ChatConversationPane] Resetting stream state only')
      resetStreamState()

      console.log('[ChatConversationPane] Initialization complete')
      setIsInitialized(true)
    }

    try {
      syncConversation()
    } catch (error) {
      console.warn('[ChatConversationPane] Failed to sync conversation state', error)
      setIsInitialized(true) // Still mark as initialized to prevent blocking
    }
  }, [isActive, isInitialized, resetStreamState])

  const modeColors: Record<typeof currentMode, string> = {
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    indigo: 'bg-indigo-500',
    violet: 'bg-violet-500',
  }

  const modeDescriptions: Record<typeof currentMode, string> = {
    green: 'Educational & Detailed',
    blue: 'Concise & Quantitative',
    indigo: 'Strategic & Narrative',
    violet: 'Conservative & Risk-Focused',
  }

  const handleConversationReset = useCallback(() => {
    if (onConversationReset) {
      onConversationReset()
      return
    }

    useChatStore.getState().reset()
    resetStreamState()
  }, [onConversationReset, resetStreamState])

  const handleSendMessage = useCallback(async (text: string) => {
    const streamState = useStreamStore.getState()
    if (streamState.isStreaming && streamState.activeRuns.size === 0) {
      console.warn('[ChatConversationPane] Detected stuck streaming state, resetting...')
      streamState.stopStreaming()
    }

    const modeSwitchMatch = text.match(/^\/mode\s+(green|blue|indigo|violet)$/i)
    if (modeSwitchMatch) {
      const newMode = modeSwitchMatch[1].toLowerCase() as typeof currentMode
      setMode(newMode)

      if (currentConversationId) {
        try {
          await chatService.updateConversationMode(currentConversationId, newMode)
        } catch (error) {
          console.error('Failed to update mode on backend:', error)
        }
      }

      addMessage(
        {
          conversationId: currentConversationId || 'temp',
          role: 'system',
          content: `Mode switched to ${newMode} (${modeDescriptions[newMode]})`,
        },
        `system-mode-${Date.now()}`
      )
      return
    }

    if (isStreaming && currentConversationId) {
      queueMessage(currentConversationId, text)
      return
    }

    let conversationId = currentConversationId

    if (!conversationId) {
      try {
        const backendConversation = await chatService.createConversation(currentMode, portfolioId || undefined)
        conversationId = backendConversation.id
        createConversation(currentMode, conversationId)
      } catch (error) {
        console.error('Failed to create conversation:', error)
        addMessage(
          {
            conversationId: 'temp',
            role: 'system',
            content: 'Failed to create conversation. Please check your connection and try again.',
          },
          `error-conv-${Date.now()}`
        )
        return
      }
    }

    const tempUserMessage = {
      conversationId,
      role: 'user' as const,
      content: text,
    }

    try {
      const isAuthenticated = await chatAuthService.refreshIfNeeded()
      if (!isAuthenticated) {
        addMessage(
          {
            conversationId,
            role: 'assistant',
            content: 'Please log in to use the chat assistant.',
            error: {
              message: 'Authentication required',
              error_type: 'AUTH_EXPIRED',
            },
          },
          `error-auth-${Date.now()}`
        )
        return
      }

      let runId: string | null | undefined = null
      runId = await streamMessage(conversationId, text, {
        onMessageCreated: (event) => {
          addMessage(tempUserMessage, event.user_message_id)
          addMessage(
            {
              conversationId,
              role: 'assistant',
              content: '',
            },
            event.assistant_message_id
          )
          setAssistantMessageId(event.assistant_message_id)
          currentAssistantMessageIdRef.current = event.assistant_message_id
          handleMessageCreated(event)
        },
        onToken: (token: string, runIdFromEvent?: string) => {
          const actualRunId = runIdFromEvent || runId || ''
          const { streamBuffers: currentStreamBuffers } = useStreamStore.getState()
          const buffer = currentStreamBuffers.get(actualRunId)

          if (buffer && currentAssistantMessageIdRef.current) {
            updateMessage(currentAssistantMessageIdRef.current, {
              content: buffer.text,
            })
          }
        },
        onInfo: (info: Parameters<NonNullable<StreamingOptions['onInfo']>>[0]) => {
          try {
            let content = ''
            if (info.info_type === 'retry_scheduled') {
              const attempt = info.attempt
              const maxAttempts = info.max_attempts
              const retryMs = info.retry_in_ms
              const secs = typeof retryMs === 'number' ? Math.round(retryMs / 100) / 10 : undefined
              content = `Temporary issue detected. Retrying ${attempt}/${maxAttempts}${secs !== undefined ? ` in ${secs}s` : ''}...`
            } else if (info.info_type === 'model_switch') {
              const from = info.from || 'primary'
              const to = info.to || 'fallback'
              const attempt = info.attempt ?? '?'
              content = `Switching model from ${from} to ${to} (attempt ${attempt}).`
            } else if (info.info_type) {
              content = `[Info: ${info.info_type}]`
            }

            if (content) {
              const uniqueSuffix = `${(info as any).run_id ?? 'run'}-${(info as any).seq ?? 'n'}`
              const uniqueId = `system-info-${Date.now()}-${infoMessageCounterRef.current++}-${uniqueSuffix}`
              addMessage(
                {
                  conversationId: conversationId!,
                  role: 'system',
                  content,
                },
                uniqueId
              )
            }
          } catch (error) {
            console.warn('Failed to handle info event', error, info)
          }
        },
        onError: (error: any) => {
          console.error('Streaming error:', error)
          if (currentAssistantMessageIdRef.current) {
            const currentMessages = getMessages()
            const currentMessage = currentMessages.find((m) => m.id === currentAssistantMessageIdRef.current)
            const currentContent = currentMessage?.content || ''
            const shouldAppend = currentContent && currentContent !== 'Thinking...'
            const errorText = error.message || 'An error occurred while processing your request.'
            const finalContent = shouldAppend ? `${currentContent}\n\n[Error: ${errorText}]` : `Error: ${errorText}`

            updateMessage(currentAssistantMessageIdRef.current, {
              content: finalContent,
              error: {
                message: error.message,
                error_type: error.error_type,
              },
            })
          }
        },
        onDone: (finalText: string) => {
          if (currentAssistantMessageIdRef.current) {
            updateMessage(currentAssistantMessageIdRef.current, {
              content: finalText || 'No response received.',
              runId: runId || undefined,
            })
          }
          currentAssistantMessageIdRef.current = null
          const streamStateAfter = useStreamStore.getState()
          if (streamStateAfter.isStreaming && streamStateAfter.currentRunId === runId) {
            streamStateAfter.stopStreaming()
          }
        },
      })
    } catch (error: any) {
      console.error('Failed to send message:', error)
      const streamState = useStreamStore.getState()
      if (streamState.isStreaming) {
        console.log('[ChatConversationPane] Resetting streaming state due to error')
        streamState.stopStreaming()
      }

      // Handle stale conversation ID (404 - Conversation not found)
      if (error?.detail && typeof error.detail === 'string' && error.detail.includes('Conversation not found')) {
        console.warn('[ChatConversationPane] Stale conversation detected, resetting...')
        handleConversationReset()
        addMessage(
          {
            conversationId: 'temp',
            role: 'system',
            content: 'Your conversation expired. Starting a new one. Please send your message again.',
          },
          `error-stale-${Date.now()}`
        )
        return
      }

      // Legacy error handling for old conversation ID format
      if (error?.detail && conversationId && conversationId.startsWith('conv_')) {
        handleConversationReset()
        return
      }

      if (currentAssistantMessageIdRef.current) {
        updateMessage(currentAssistantMessageIdRef.current, {
          content: 'Failed to send message. Please try again.',
          error: {
            message: error.message || 'Unknown error',
            error_type: 'NETWORK_ERROR',
          },
        })
      }
    }
  }, [
    addMessage,
    createConversation,
    currentConversationId,
    currentMode,
    getMessages,
    handleMessageCreated,
    handleConversationReset,
    isStreaming,
    modeDescriptions,
    queueMessage,
    setAssistantMessageId,
    setMode,
    streamMessage,
    updateMessage,
  ])

  // Update the ref whenever handleSendMessage changes
  useEffect(() => {
    handleSendMessageRef.current = handleSendMessage
  }, [handleSendMessage])

  const hasSentInitialRef = useRef(false)

  useEffect(() => {
    // Send initial message from URL parameter if provided
    if (!isActive || !isInitialized || hasSentInitialRef.current || !initialMessage) {
      console.log('[ChatConversationPane] Initial message effect - conditions not met:', {
        isActive,
        isInitialized,
        hasSentInitial: hasSentInitialRef.current,
        hasInitialMessage: !!initialMessage
      })
      return
    }

    console.log('[ChatConversationPane] Conditions met, checking handleSendMessageRef...')
    if (handleSendMessageRef.current) {
      console.log('[ChatConversationPane] Sending initial message:', initialMessage)
      handleSendMessageRef.current(initialMessage)
      hasSentInitialRef.current = true
    } else {
      console.warn('[ChatConversationPane] handleSendMessageRef.current is null, cannot send message')
    }
  }, [isActive, isInitialized, initialMessage])
  // Note: Removed handleSendMessage from dependencies to prevent constant re-runs

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamBuffersSize])

  const isProcessingQueueRef = useRef(false)

  useEffect(() => {
    if (!isStreaming && messageQueue && !isProcessingQueueRef.current && handleSendMessageRef.current) {
      isProcessingQueueRef.current = true
      const queued = processQueue()
      if (queued) {
        handleSendMessageRef.current(queued.message).finally(() => {
          isProcessingQueueRef.current = false
        })
      } else {
        isProcessingQueueRef.current = false
      }
    }
  }, [isStreaming, messageQueue, processQueue])

  useEffect(() => {
    if (!isActive || !isStreaming) {
      return
    }

    const timeoutId = setTimeout(() => {
      const state = useStreamStore.getState()
      if (state.isStreaming && state.activeRuns.size === 0) {
        console.warn('[ChatConversationPane] Streaming timeout - forcing reset after 30s')
        state.stopStreaming()
      }
    }, 30000)

    return () => clearTimeout(timeoutId)
  }, [isActive, isStreaming])

  const handleAbort = useCallback(() => {
    abortStream()
    currentAssistantMessageIdRef.current = null
  }, [abortStream])

  return (
    <div
      className={cn(
        'flex h-full flex-col bg-white',
        variant === 'inline' ? 'border border-primary rounded-xl shadow-sm min-h-[560px]' : '',
        className
      )}
    >
      <div
        className={cn(
          'px-6 py-4 border-b',
          variant === 'inline' ? 'rounded-t-xl bg-white' : ''
        )}
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
            {subtitle ? <p className="text-sm text-tertiary mt-1">{subtitle}</p> : null}
          </div>
          <div className="flex items-center gap-2">
            <div className={cn('w-2 h-2 rounded-full', modeColors[currentMode])} />
            <span className="text-xs text-tertiary">{modeDescriptions[currentMode]}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {messages.length === 0 ? (
          <div className="text-center text-tertiary mt-8">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p className="text-sm">Start a conversation about your portfolio</p>

            <div className="mt-6 space-y-2">
              <p className="text-xs text-gray-400 mb-3">Try asking:</p>
              {[
                "What's my largest position?",
                'Show me my portfolio performance',
                'What are my risk exposures?',
              ].map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(suggestion)}
                  className="block w-full text-left px-4 py-2 text-sm bg-primary hover:bg-gray-100 rounded-lg transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={cn(
                    'max-w-[80%] rounded-lg px-4 py-2',
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  )}
                >
                  {message.error ? (
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm">{message.content || message.error.message}</p>
                        {message.error.error_type === 'AUTH_EXPIRED' && (
                          <button
                            onClick={() => {
                              if (typeof window !== 'undefined') {
                                window.location.href = '/login'
                              }
                            }}
                            className="text-xs underline mt-1"
                          >
                            Go to login
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  )}
                  <p className="text-xs mt-1 opacity-70">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}

            {isStreaming && currentRunId && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg px-4 py-2">
                  <div className="flex items-center gap-2">
                    <div className="flex space-x-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                    </div>
                    <button
                      onClick={handleAbort}
                      className="text-xs text-tertiary hover:text-primary"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            {messageQueue && (
              <div className="flex justify-center">
                <div className="text-xs text-tertiary bg-primary px-3 py-1 rounded-full">
                  Message queued...
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="border-t p-4 bg-white">
        <ChatInput
          placeholder={isStreaming ? 'Please wait...' : 'Type your message...'}
          onSubmit={handleSendMessage}
          className="w-full"
          disabled={isStreaming}
        />

        <div className="flex items-center gap-2 mt-3">
          <span className="text-xs text-tertiary">Mode:</span>
          <div className="flex gap-1">
            {(['green', 'blue', 'indigo', 'violet'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setMode(mode)}
                className={cn(
                  'w-6 h-6 rounded-full transition-all',
                  modeColors[mode],
                  currentMode === mode ? 'ring-2 ring-offset-2 ring-gray-400' : 'opacity-50 hover:opacity-75'
                )}
                aria-label={`Switch to ${modeDescriptions[mode]} mode`}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
