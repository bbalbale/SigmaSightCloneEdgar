/**
 * CopilotButton Component - Floating action button for AI copilot
 *
 * A floating button that opens the CopilotSheet when clicked.
 * Shows an unread indicator when the agent has responded.
 * Can be placed on any page to provide quick access to the copilot.
 */

'use client'

import React, { useState, useEffect } from 'react'
import { CopilotSheet } from './CopilotSheet'
import { useAIChatStore } from '@/stores/aiChatStore'
import { PageHint } from '@/hooks/useCopilot'
import { Sparkles, X } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface CopilotButtonProps {
  /**
   * Page hint for context-aware behavior
   */
  pageHint?: PageHint

  /**
   * Callback when an insight is ready
   */
  onInsightReady?: (insight: string) => void

  /**
   * Position of the button
   * @default 'bottom-right'
   */
  position?: 'bottom-right' | 'bottom-left'

  /**
   * Custom class name for the button container
   */
  className?: string
}

/**
 * CopilotButton - Floating action button that opens the copilot sheet
 *
 * Features:
 * - Fixed position in corner of screen
 * - Shows unread indicator when new messages arrive
 * - Opens CopilotSheet on click
 *
 * @example
 * ```tsx
 * // In your page or layout
 * function MyPage() {
 *   return (
 *     <>
 *       <YourPageContent />
 *       <CopilotButton pageHint="portfolio" />
 *     </>
 *   )
 * }
 * ```
 */
export function CopilotButton({
  pageHint,
  onInsightReady,
  position = 'bottom-right',
  className = ''
}: CopilotButtonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [hasUnread, setHasUnread] = useState(false)
  const [lastSeenCount, setLastSeenCount] = useState(0)

  const { messages, isStreaming } = useAIChatStore()

  // Track unread messages
  useEffect(() => {
    if (isOpen) {
      // Reset unread when sheet is open
      setHasUnread(false)
      setLastSeenCount(messages.length)
    } else {
      // Check for new assistant messages when sheet is closed
      const assistantMessages = messages.filter((m) => m.role === 'assistant')
      const newAssistantMessages = assistantMessages.length > lastSeenCount
      if (newAssistantMessages && !isStreaming) {
        setHasUnread(true)
      }
    }
  }, [isOpen, messages, isStreaming, lastSeenCount])

  // When sheet opens, update last seen count
  useEffect(() => {
    if (isOpen) {
      setLastSeenCount(messages.filter((m) => m.role === 'assistant').length)
    }
  }, [isOpen, messages])

  // Position classes
  const positionClasses =
    position === 'bottom-right' ? 'right-6 bottom-6' : 'left-6 bottom-6'

  return (
    <>
      {/* Floating Button */}
      <div className={`fixed ${positionClasses} z-40 ${className}`}>
        <Button
          onClick={() => setIsOpen(!isOpen)}
          className="relative h-14 w-14 rounded-full shadow-lg hover:shadow-xl transition-all duration-300"
          style={{
            backgroundColor: 'var(--color-accent)',
            color: 'white'
          }}
        >
          {isOpen ? (
            <X className="h-6 w-6" />
          ) : (
            <Sparkles className="h-6 w-6" />
          )}

          {/* Unread indicator */}
          {hasUnread && !isOpen && (
            <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-red-500 animate-pulse" />
          )}
        </Button>

        {/* Tooltip */}
        {!isOpen && (
          <div
            className="absolute bottom-full mb-2 right-0 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap opacity-0 hover:opacity-100 transition-opacity pointer-events-none"
            style={{
              backgroundColor: 'var(--bg-primary)',
              border: '1px solid var(--border-primary)',
              color: 'var(--text-primary)',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
            }}
          >
            Chat with SigmaSight AI
          </div>
        )}
      </div>

      {/* Copilot Sheet */}
      <CopilotSheet
        open={isOpen}
        onOpenChange={setIsOpen}
        pageHint={pageHint}
        onInsightReady={onInsightReady}
      />
    </>
  )
}

export default CopilotButton
