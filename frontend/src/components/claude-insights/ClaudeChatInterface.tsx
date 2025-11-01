/**
 * Claude Chat Interface Component
 *
 * Chat UI for Claude Insights on SigmaSight AI page
 */

'use client'

import React, { useState, useRef, useEffect } from 'react'
import { useClaudeInsightsStore } from '@/stores/claudeInsightsStore'
import { sendMessage, createNewConversation } from '@/services/claudeInsightsService'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Sparkles, Send, Loader2, RefreshCw } from 'lucide-react'

export function ClaudeChatInterface() {
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    messages,
    isStreaming,
    streamingText,
    error
  } = useClaudeInsightsStore()

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
    } catch (error) {
      console.error('Failed to send message:', error)
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewConversation = () => {
    if (confirm('Start a new conversation? Current history will be cleared.')) {
      createNewConversation()
    }
  }

  return (
    <div className="rounded-lg border transition-colors duration-300" style={{
      backgroundColor: 'var(--bg-primary)',
      borderColor: 'var(--border-primary)'
    }}>
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between transition-colors duration-300" style={{
        borderColor: 'var(--border-primary)'
      }}>
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" style={{ color: 'var(--color-accent)' }} />
          <h3 className="font-semibold" style={{
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-display)'
          }}>
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
          New Chat
        </Button>
      </div>

      {/* Messages */}
      <div className="p-4 space-y-4 min-h-[400px] max-h-[600px] overflow-y-auto transition-colors duration-300" style={{
        backgroundColor: 'var(--bg-secondary)'
      }}>
        {messages.length === 0 && !streamingText && (
          <div className="text-center py-12">
            <Sparkles className="h-12 w-12 mx-auto mb-4" style={{ color: 'var(--color-accent)' }} />
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Ask SigmaSight AI about your portfolio risks, exposures, or recommendations
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className="max-w-[80%] rounded-lg p-3 transition-colors duration-300"
              style={{
                backgroundColor: message.role === 'user' ? 'rgba(251, 146, 60, 0.2)' : 'var(--bg-primary)',
                color: 'var(--text-primary)',
                ...(message.role === 'assistant' ? {
                  border: '1px solid var(--border-primary)'
                } : {})
              }}
            >
              <div className={`text-sm whitespace-pre-wrap ${
                message.role === 'assistant'
                  ? 'prose prose-sm max-w-none dark:prose-invert'
                  : ''
              }`}>
                {message.content}
              </div>
              {message.tool_calls_count && message.tool_calls_count > 0 && (
                <div className="text-xs mt-2 pt-2 border-t transition-colors duration-300" style={{
                  borderColor: 'var(--border-primary)',
                  color: 'var(--text-tertiary)'
                }}>
                  Used {message.tool_calls_count} analytics tool{message.tool_calls_count > 1 ? 's' : ''}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {(isStreaming || streamingText) && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg p-3 transition-colors duration-300" style={{
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)',
              color: 'var(--text-primary)'
            }}>
              <div className="text-sm whitespace-pre-wrap prose prose-sm max-w-none dark:prose-invert">
                {streamingText}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <Loader2 className="h-3 w-3 animate-spin" style={{ color: 'var(--color-accent)' }} />
                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  SigmaSight AI is thinking...
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="rounded-lg p-3 transition-colors duration-300" style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid var(--color-error)',
            color: 'var(--color-error)'
          }}>
            <p className="text-sm font-medium">Error</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t transition-colors duration-300" style={{
        borderColor: 'var(--border-primary)'
      }}>
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask SigmaSight AI about your portfolio..."
            disabled={isStreaming || isSending}
            rows={2}
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
