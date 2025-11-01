'use client'

import React, { useState } from 'react'
import { Position, Tag } from '@/stores/researchStore'

export interface SimplifiedPositionCardProps {
  position: Position
  onClick: () => void
  onDrop: (tagId: string) => void
  theme: 'dark' | 'light'
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  return `$${value.toFixed(0)}`
}

function formatPercentage(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`
}

export function SimplifiedPositionCard({
  position,
  onClick,
  onDrop,
  theme
}: SimplifiedPositionCardProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = () => {
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    const tagId = e.dataTransfer.getData('tagId')
    if (tagId) {
      onDrop(tagId)
    }
  }

  // Support both camelCase and snake_case field names from API
  // Try multiple sources: direct fields, snapshot fields, calculated fields
  const marketValue = (position as any).marketValue ||
                      (position as any).current_market_value ||
                      (position as any).market_value ||
                      ((position as any).shares || (position as any).quantity || 0) * ((position as any).current_price || (position as any).price || 0)

  const pnlPercent = (position as any).pnlPercent ||
                     (position as any).unrealized_pnl_percent ||
                     (position as any).pnl_percent || 0

  const quantity = position.quantity || (position as any).shares || 0
  const positionType = position.positionType || (position as any).position_type || ''
  const sector = position.sector || ''

  const pnlColor = pnlPercent >= 0
    ? (theme === 'dark' ? 'text-emerald-400' : 'text-emerald-600')
    : (theme === 'dark' ? 'text-red-400' : 'text-red-600')

  return (
    <div
      className={`border rounded p-3 cursor-pointer transition-all duration-200 ${
        theme === 'dark'
          ? 'bg-primary/50 border-primary/50 hover:bg-slate-800/50'
          : 'bg-white border-slate-300 hover:bg-slate-50'
      } ${isDragOver ? 'ring-2 ring-blue-400 border-blue-400' : ''}`}
      onClick={onClick}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Top Row: Symbol + P&L */}
      <div className="flex items-center justify-between mb-2">
        <span className={`text-lg font-bold ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        }`}>
          {position.symbol}
        </span>
        <span className={`text-sm font-semibold tabular-nums ${pnlColor}`}>
          {formatPercentage(pnlPercent)}
        </span>
      </div>

      {/* Market Value */}
      <div className={`text-xl font-bold tabular-nums mb-1 ${
        theme === 'dark' ? 'text-orange-400' : 'text-slate-900'
      }`}>
        {formatCurrency(marketValue)}
      </div>

      {/* Details */}
      <div className="text-xs text-tertiary">
        {quantity} {quantity === 1 ? 'share' : 'shares'} | {positionType}
        {sector && ` | ${sector}`}
      </div>

      {/* Tags */}
      {position.tags && position.tags.length > 0 && (
        <div className="flex gap-1 mt-2 flex-wrap">
          {position.tags.slice(0, 3).map((tag) => (
            <span
              key={tag.id}
              className="text-[10px] px-2 py-0.5 rounded"
              style={{
                backgroundColor: `${tag.color}20`,
                color: tag.color,
                border: `1px solid ${tag.color}40`
              }}
            >
              {tag.name}
            </span>
          ))}
          {position.tags.length > 3 && (
            <span className="text-[10px] px-2 py-0.5 rounded text-tertiary">
              +{position.tags.length - 3} more
            </span>
          )}
        </div>
      )}
    </div>
  )
}
