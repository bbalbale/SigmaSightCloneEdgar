'use client'

import { Loader2, Check, Clock, AlertCircle, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface PhaseListItemProps {
  phaseId: string
  phaseName: string
  status: 'pending' | 'running' | 'completed' | 'warning' | 'failed'
  current?: number
  total?: number
  unit?: string
  durationSeconds?: number | null
}

/**
 * Format duration in seconds to human-readable string
 */
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`
  }
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`
  }
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`
}

/**
 * Get status icon for a phase
 */
function getStatusIcon(status: PhaseListItemProps['status']) {
  switch (status) {
    case 'completed':
      return <Check className="h-4 w-4 text-green-600" />
    case 'running':
      return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
    case 'warning':
      return <AlertTriangle className="h-4 w-4 text-yellow-600" />
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-600" />
    case 'pending':
    default:
      return <Clock className="h-4 w-4 text-gray-400" />
  }
}

/**
 * Get background color class for a phase status
 */
function getBackgroundClass(status: PhaseListItemProps['status']): string {
  switch (status) {
    case 'completed':
      return 'bg-green-50 dark:bg-green-950/30'
    case 'running':
      return 'bg-blue-50 dark:bg-blue-950/30'
    case 'warning':
      return 'bg-yellow-50 dark:bg-yellow-950/30'
    case 'failed':
      return 'bg-red-50 dark:bg-red-950/30'
    case 'pending':
    default:
      return 'bg-gray-50 dark:bg-gray-900/30'
  }
}

/**
 * Single phase item in the progress list
 */
export function PhaseListItem({
  phaseId,
  phaseName,
  status,
  current = 0,
  total = 0,
  unit = 'items',
  durationSeconds,
}: PhaseListItemProps) {
  const showProgressBar = status === 'running' && total > 0
  const progressPercent = total > 0 ? Math.round((current / total) * 100) : 0

  return (
    <div
      className={cn(
        'rounded-lg p-3 transition-colors',
        getBackgroundClass(status)
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getStatusIcon(status)}
          <span
            className={cn(
              'text-sm font-medium',
              status === 'completed' && 'text-green-900 dark:text-green-100',
              status === 'running' && 'text-blue-900 dark:text-blue-100',
              status === 'warning' && 'text-yellow-900 dark:text-yellow-100',
              status === 'failed' && 'text-red-900 dark:text-red-100',
              status === 'pending' && 'text-muted-foreground'
            )}
          >
            {phaseName}
          </span>
        </div>

        {/* Duration display */}
        {durationSeconds !== null && durationSeconds !== undefined && (
          <span className="text-xs text-muted-foreground">
            {formatDuration(durationSeconds)}
          </span>
        )}
      </div>

      {/* Progress bar for running phase */}
      {showProgressBar && (
        <div className="mt-2 space-y-1">
          <div className="h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>
              {current}/{total} {unit}
            </span>
            <span>{progressPercent}%</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default PhaseListItem
