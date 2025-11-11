import React from 'react'

export type DataSourceStatus = 'live' | 'cached' | 'error' | 'mock'

interface DataSourceIndicatorProps {
  status: DataSourceStatus
  className?: string
  timestamp?: Date | string
}

const statusConfig = {
  live: {
    color: 'bg-emerald-500',
    tooltip: 'Live data from API',
    pulseAnimation: false, // No pulsing per user request
  },
  cached: {
    color: 'bg-yellow-500',
    tooltip: 'Using cached data',
    pulseAnimation: false,
  },
  error: {
    color: 'bg-red-500',
    tooltip: 'API error - displaying fallback data',
    pulseAnimation: false,
  },
  mock: {
    color: 'bg-primary0',
    tooltip: 'Mock data for demonstration',
    pulseAnimation: false,
  },
}

export function DataSourceIndicator({ status, className = '', timestamp }: DataSourceIndicatorProps) {
  const config = statusConfig[status]
  
  const tooltipText = timestamp 
    ? `${config.tooltip} (${new Date(timestamp).toLocaleTimeString()})`
    : config.tooltip

  return (
    <div 
      className={`inline-flex items-center ${className}`}
      title={tooltipText}
    >
      <div className="relative">
        <div 
          className={`w-2.5 h-2.5 rounded-full ${config.color} cursor-help`}
        />
        {config.pulseAnimation && status === 'live' && (
          <div 
            className={`absolute inset-0 w-2.5 h-2.5 rounded-full ${config.color} animate-ping opacity-75`}
          />
        )}
      </div>
    </div>
  )
}