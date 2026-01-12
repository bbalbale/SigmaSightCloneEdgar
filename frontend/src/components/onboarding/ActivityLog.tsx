'use client'

import { useRef, useEffect, useState } from 'react'
import { ActivityLogEntry, ActivityLogEntryProps } from './ActivityLogEntry'
import { cn } from '@/lib/utils'

export interface ActivityLogProps {
  entries: Array<{
    timestamp: string
    message: string
    level: 'info' | 'warning' | 'error'
  }>
  maxHeight?: string
  className?: string
  /** Whether to auto-scroll to bottom when new entries arrive. Defaults to true. */
  autoScroll?: boolean
}

/**
 * Scrollable activity log display with smart auto-scroll
 *
 * Auto-scrolls to bottom when new entries are added, but pauses
 * auto-scroll if user manually scrolls up to read earlier entries.
 */
export function ActivityLog({
  entries,
  maxHeight = '250px',
  className,
  autoScroll = true,
}: ActivityLogProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isUserScrolled, setIsUserScrolled] = useState(false)
  const [showScrollIndicator, setShowScrollIndicator] = useState(false)

  // Handle scroll events to detect user interaction
  const handleScroll = () => {
    if (!containerRef.current) return

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 30

    setIsUserScrolled(!isAtBottom)
    setShowScrollIndicator(!isAtBottom)
  }

  // Auto-scroll to bottom when new entries arrive (if user hasn't scrolled up and autoScroll is enabled)
  useEffect(() => {
    if (!containerRef.current || isUserScrolled || !autoScroll) return

    containerRef.current.scrollTop = containerRef.current.scrollHeight
  }, [entries, isUserScrolled, autoScroll])

  // Scroll to bottom when indicator is clicked
  const scrollToBottom = () => {
    if (!containerRef.current) return

    containerRef.current.scrollTo({
      top: containerRef.current.scrollHeight,
      behavior: 'smooth',
    })
    setIsUserScrolled(false)
    setShowScrollIndicator(false)
  }

  if (entries.length === 0) {
    return (
      <div
        className={cn(
          'rounded-lg border bg-muted/30 p-4 text-center text-sm text-muted-foreground',
          className
        )}
      >
        Waiting for activity...
      </div>
    )
  }

  return (
    <div className={cn('relative', className)}>
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="rounded-lg border bg-muted/30 overflow-y-auto"
        style={{ maxHeight }}
      >
        <div className="py-2">
          {entries.map((entry, index) => (
            <ActivityLogEntry
              key={`${entry.timestamp}-${index}`}
              timestamp={entry.timestamp}
              message={entry.message}
              level={entry.level}
            />
          ))}
        </div>
      </div>

      {/* Scroll to bottom indicator - shown when user has scrolled up */}
      {showScrollIndicator && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-2 right-2 flex items-center gap-1 px-2 py-1 text-xs bg-blue-500 text-white rounded-full hover:bg-blue-600 transition-colors shadow-md"
        >
          <span>↓ Jump to latest</span>
        </button>
      )}
    </div>
  )
}

export default ActivityLog
