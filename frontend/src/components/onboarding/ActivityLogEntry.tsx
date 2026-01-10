'use client'

import { cn } from '@/lib/utils'

export interface ActivityLogEntryProps {
  timestamp: string
  message: string
  level: 'info' | 'warning' | 'error'
}

/**
 * Format ISO timestamp to UTC time-only display (HH:MM:SS)
 * Per design doc Section 9.5: "UTC everywhere (UI and download)"
 */
function formatTimestamp(isoTimestamp: string): string {
  try {
    const date = new Date(isoTimestamp)
    // Use UTC to match downloaded log format per design doc
    return date.toISOString().slice(11, 19)
  } catch {
    return isoTimestamp
  }
}

/**
 * Get level indicator for log entry
 */
function getLevelIndicator(level: ActivityLogEntryProps['level']): string {
  switch (level) {
    case 'warning':
      return ''
    case 'error':
      return ''
    case 'info':
    default:
      return ''
  }
}

/**
 * Single activity log entry in the scrollable log display
 */
export function ActivityLogEntry({
  timestamp,
  message,
  level,
}: ActivityLogEntryProps) {
  const formattedTime = formatTimestamp(timestamp)
  const levelIndicator = getLevelIndicator(level)
  const displayMessage = levelIndicator ? `${levelIndicator} ${message}` : message

  return (
    <div
      className={cn(
        'flex items-start gap-2 py-1 px-2 text-xs font-mono',
        level === 'warning' && 'text-yellow-700 dark:text-yellow-400',
        level === 'error' && 'text-red-700 dark:text-red-400',
        level === 'info' && 'text-gray-700 dark:text-gray-300'
      )}
    >
      <span className="text-muted-foreground shrink-0">{formattedTime}</span>
      <span className="break-words">{displayMessage}</span>
    </div>
  )
}

export default ActivityLogEntry
