/**
 * CopilotPanel Component - Reusable chat panel for AI copilot
 *
 * A flexible chat UI that can be used inline on pages or inside sheets/modals.
 * Uses the useCopilot hook for all state management.
 *
 * Variants:
 * - 'inline': Full-featured panel for dedicated AI pages
 * - 'compact': Smaller panel for slide-out sheets
 */

'use client'

import React, { useState, useRef, useEffect } from 'react'
import { useCopilot, PageHint } from '@/hooks/useCopilot'
import { AIChatMessage } from '@/stores/aiChatStore'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Sparkles, Send, Loader2, RefreshCw, ThumbsUp, ThumbsDown } from 'lucide-react'

export type CopilotVariant = 'inline' | 'compact'

export interface CopilotPanelProps {
  /**
   * Visual variant of the panel
   * - 'inline': Full-featured for dedicated pages (default)
   * - 'compact': Smaller for sheets/modals
   */
  variant?: CopilotVariant

  /**
   * Custom height for the messages area
   * Defaults to '700px' for inline, '400px' for compact
   */
  height?: string

  /**
   * Whether to show the header with title and new chat button
   * Defaults to true
   */
  showHeader?: boolean

  /**
   * Page hint for context-aware behavior
   */
  pageHint?: PageHint

  /**
   * Optional route for finer-grained context
   */
  route?: string

  /**
   * Custom class name for the container
   */
  className?: string

  /**
   * Callback when an insight is ready
   */
  onInsightReady?: (insight: string) => void

  /**
   * Prefill the input with an externally provided message
   */
  prefillMessage?: string

  /**
   * Notify caller when the prefill has been consumed
   */
  onPrefillConsumed?: () => void

  /**
   * Optional quick prompts to render above the input
   */
  quickPrompts?: string[]
}

/**
 * Message component for displaying chat messages
 */
function MessageBubble({
  message,
  onFeedback,
  feedbackLoading
}: {
  message: AIChatMessage
  onFeedback: (rating: 'up' | 'down') => void
  feedbackLoading: boolean
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span
          className="text-xs font-semibold transition-colors duration-300"
          style={{
            color: 'var(--color-accent)'
          }}
        >
          {message.role === 'user' ? 'You' : 'SigmaSight AI'}
        </span>
      </div>
      <div
        className="rounded-lg p-3 transition-colors duration-300"
        style={{
          backgroundColor: 'var(--bg-primary)',
          border: '1px solid var(--border-primary)',
          color: 'var(--text-primary)'
        }}
      >
        <div
          className={`text-sm whitespace-pre-wrap ${
            message.role === 'assistant'
              ? 'prose prose-sm max-w-none dark:prose-invert'
              : ''
          }`}
        >
          {message.content}
        </div>
        {/* Tool calls info and feedback buttons */}
        <div
          className="flex items-center justify-between mt-2 pt-2 border-t transition-colors duration-300"
          style={{
            borderColor: 'var(--border-primary)'
          }}
        >
          {/* Tool calls count */}
          <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
            {message.tool_calls_count && message.tool_calls_count > 0 && (
              <span>
                Used {message.tool_calls_count} analytics tool
                {message.tool_calls_count > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Feedback buttons - only for assistant messages with backend ID */}
          {message.role === 'assistant' && message.backendMessageId && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => onFeedback('up')}
                disabled={feedbackLoading}
                className={`p-1 rounded hover:bg-opacity-20 transition-colors ${
                  message.feedback === 'up' ? 'text-green-500' : ''
                }`}
                style={{
                  color:
                    message.feedback === 'up'
                      ? 'var(--color-success, #10b981)'
                      : 'var(--text-tertiary)'
                }}
                title="Helpful response"
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => onFeedback('down')}
                disabled={feedbackLoading}
                className={`p-1 rounded hover:bg-opacity-20 transition-colors ${
                  message.feedback === 'down' ? 'text-red-500' : ''
                }`}
                style={{
                  color:
                    message.feedback === 'down'
                      ? 'var(--color-error, #ef4444)'
                      : 'var(--text-tertiary)'
                }}
                title="Not helpful"
              >
                <ThumbsDown className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Streaming message indicator
 */
function StreamingMessage({ text }: { text: string }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span
          className="text-xs font-semibold transition-colors duration-300"
          style={{
            color: 'var(--color-accent)'
          }}
        >
          SigmaSight AI
        </span>
      </div>
      <div
        className="rounded-lg p-3 transition-colors duration-300"
        style={{
          backgroundColor: 'var(--bg-primary)',
          border: '1px solid var(--border-primary)',
          color: 'var(--text-primary)'
        }}
      >
        <div className="text-sm whitespace-pre-wrap prose prose-sm max-w-none dark:prose-invert">
          {text}
        </div>
        <div className="flex items-center gap-2 mt-2">
          <Loader2
            className="h-3 w-3 animate-spin"
            style={{ color: 'var(--color-accent)' }}
          />
          <span
            className="text-xs transition-colors duration-300"
            style={{ color: 'var(--text-tertiary)' }}
          >
            SigmaSight AI is thinking... (~15-30 sec)
          </span>
        </div>
      </div>
    </div>
  )
}

/**
 * Empty state placeholder
 */
function EmptyState({ variant }: { variant: CopilotVariant }) {
  const isCompact = variant === 'compact'

  return (
    <div className={`text-center ${isCompact ? 'py-8' : 'py-16'}`}>
      <Sparkles
        className={`${isCompact ? 'h-12 w-12' : 'h-16 w-16'} mx-auto mb-4`}
        style={{ color: 'var(--color-accent)' }}
      />
      <h3
        className={`${isCompact ? 'text-base' : 'text-lg'} font-semibold mb-2 transition-colors duration-300`}
        style={{
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-display)'
        }}
      >
        Start a Conversation
      </h3>
      <p
        className="text-sm mb-4 transition-colors duration-300"
        style={{ color: 'var(--text-secondary)' }}
      >
        Ask SigmaSight AI about your portfolio risks, exposures, or get recommendations
      </p>
      <div
        className="text-xs transition-colors duration-300 space-y-1"
        style={{ color: 'var(--text-tertiary)' }}
      >
        <div>Try: &quot;What are my biggest risks?&quot;</div>
        <div>Or: &quot;How concentrated is my portfolio?&quot;</div>
      </div>
    </div>
  )
}

/**
 * CopilotPanel - Main component
 */
export function CopilotPanel({
  variant = 'inline',
  height,
  showHeader = true,
  pageHint,
  route,
  className = '',
  onInsightReady,
  prefillMessage,
  onPrefillConsumed,
  quickPrompts
}: CopilotPanelProps) {
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [feedbackLoading, setFeedbackLoading] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    isStreaming,
    streamingText,
    error,
    hasMessages,
    sendMessage,
    resetConversation,
    submitMessageFeedback
  } = useCopilot({ pageHint, route, onInsightReady })

  // Determine height based on variant
  const messagesHeight = height || (variant === 'compact' ? '400px' : '700px')
  const isCompact = variant === 'compact'

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])

  const handleSend = async () => {
    if (!input.trim() || isSending || isStreaming) return

    setIsSending(true)
    try {
      await sendMessage(input.trim())
      setInput('')
    } catch (err) {
      console.error('Failed to send message:', err)
    } finally {
      setIsSending(false)
    }
  }

  useEffect(() => {
    if (prefillMessage) {
      setInput(prefillMessage)
      onPrefillConsumed?.()
    }
  }, [prefillMessage, onPrefillConsumed])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewConversation = () => {
    if (confirm('Start a new conversation? Current history will be cleared.')) {
      resetConversation()
    }
  }

  const handleFeedback = async (message: AIChatMessage, rating: 'up' | 'down') => {
    setFeedbackLoading(message.id)
    try {
      await submitMessageFeedback(message, rating)
    } finally {
      setFeedbackLoading(null)
    }
  }

  const derivedQuickPrompts = quickPrompts || (
    pageHint === 'ai-chat'
      ? [
          "Summarize today's top risk drivers in my portfolio.",
          'What are the biggest concentration risks I should watch?',
          'Run a quick factor exposure check and explain any extremes.'
        ]
      : []
  )

  return (
    <div
      className={`rounded-lg border transition-colors duration-300 ${className}`}
      style={{
        backgroundColor: 'var(--bg-primary)',
        borderColor: 'var(--border-primary)'
      }}
    >
      {/* Header */}
      {showHeader && (
        <div
          className="p-4 border-b flex items-center justify-between transition-colors duration-300"
          style={{
            borderColor: 'var(--border-primary)'
          }}
        >
          <div className="flex items-center gap-2">
            <Sparkles
              className={`${isCompact ? 'h-4 w-4' : 'h-5 w-5'}`}
              style={{ color: 'var(--color-accent)' }}
            />
            <h3
              className={`font-semibold ${isCompact ? 'text-sm' : ''}`}
              style={{
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-display)'
              }}
            >
              Chat with SigmaSight AI
            </h3>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleNewConversation}
            disabled={isStreaming || isSending}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            {!isCompact && 'New Chat'}
          </Button>
        </div>
      )}

      {/* Messages */}
      <div
        className="p-4 space-y-4 overflow-y-auto transition-colors duration-300"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          minHeight: messagesHeight,
          maxHeight: variant === 'inline' ? '900px' : messagesHeight
        }}
      >
        {!hasMessages && !streamingText && <EmptyState variant={variant} />}

        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onFeedback={(rating) => handleFeedback(message, rating)}
            feedbackLoading={feedbackLoading === message.id}
          />
        ))}

        {/* Streaming message */}
        {(isStreaming || streamingText) && <StreamingMessage text={streamingText} />}

        {/* Error message */}
        {error && (
          <div
            className="rounded-lg p-3 transition-colors duration-300"
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid var(--color-error)',
              color: 'var(--color-error)'
            }}
          >
            <p className="text-sm font-medium">Error</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        className="p-4 transition-colors duration-300"
        style={{
          boxShadow: '0 -2px 8px rgba(0, 0, 0, 0.1)'
        }}
      >
        {derivedQuickPrompts.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {derivedQuickPrompts.map((prompt) => (
              <Button
                key={prompt}
                variant="outline"
                size="sm"
                disabled={isStreaming || isSending}
                onClick={() => setInput(prompt)}
              >
                {prompt}
              </Button>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask SigmaSight AI about your portfolio..."
            disabled={isStreaming || isSending}
            rows={isCompact ? 2 : 3}
            className="flex-1 resize-none transition-colors duration-300"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border-primary)',
              color: 'var(--text-primary)'
            }}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming || isSending}
            className="self-end"
          >
            {isSending || isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>
          SigmaSight AI can analyze your portfolio using real-time analytics tools
        </p>
      </div>
    </div>
  )
}

export default CopilotPanel
