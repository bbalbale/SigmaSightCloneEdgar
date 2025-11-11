'use client'

import React from 'react'
import type { DataStalenessInfo, DataQualityInfo } from '@/types/analytics'

interface DataQualityIndicatorProps {
  dataQuality?: DataStalenessInfo | DataQualityInfo | null
  className?: string
}

// Type guard to check if it's staleness info
function isStalenessInfo(quality: any): quality is DataStalenessInfo {
  return quality && typeof quality.is_stale === 'boolean'
}

// Type guard to check if it's quality info
function isQualityInfo(quality: any): quality is DataQualityInfo {
  return quality && typeof quality.flag === 'string'
}

export function DataQualityIndicator({ dataQuality, className = '' }: DataQualityIndicatorProps) {
  if (!dataQuality) {
    return null
  }

  // Handle staleness information (data available but may be old)
  if (isStalenessInfo(dataQuality)) {
    const { age_hours, is_stale, is_current, snapshot_date, calculation_date } = dataQuality

    // Determine color and status
    let colorClass = 'bg-emerald-500' // Current (green)
    let statusText = 'Current'
    let tooltipText = 'Data is current'

    if (is_stale) {
      colorClass = 'bg-amber-500' // Stale (yellow/amber)
      statusText = 'Stale Data'
      tooltipText = `Data is ${age_hours || 0} hours old (>72 hours). Recalculation in progress.`
    } else if (!is_current && age_hours) {
      if (age_hours < 48) {
        colorClass = 'bg-emerald-500' // Fresh (green)
        statusText = 'Recent'
        tooltipText = `Data from ${age_hours} hours ago`
      } else {
        colorClass = 'bg-yellow-500' // Aging (yellow)
        statusText = 'Aging'
        tooltipText = `Data from ${age_hours} hours ago (${Math.floor(age_hours / 24)} days)`
      }
    }

    // Format the date for display
    const displayDate = calculation_date || snapshot_date
    const dateStr = displayDate ? new Date(displayDate).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    }) : ''

    return (
      <div className={`inline-flex items-center gap-2 ${className}`} title={tooltipText}>
        <div className="relative">
          <div className={`w-2.5 h-2.5 rounded-full ${colorClass} cursor-help`} />
        </div>
        <span className="text-xs text-secondary">
          {dateStr && `As of ${dateStr}`}
          {age_hours && age_hours > 24 && ` (${Math.floor(age_hours / 24)}d ago)`}
        </span>
      </div>
    )
  }

  // Handle quality information (data unavailable or incomplete)
  if (isQualityInfo(dataQuality)) {
    const { message, positions_analyzed, positions_total } = dataQuality

    return (
      <div className={`inline-flex items-center gap-2 ${className}`} title={message}>
        <div className="relative">
          <div className="w-2.5 h-2.5 rounded-full bg-gray-400 cursor-help" />
        </div>
        <span className="text-xs text-secondary">
          {positions_analyzed}/{positions_total} positions analyzed
        </span>
      </div>
    )
  }

  return null
}

export default DataQualityIndicator
