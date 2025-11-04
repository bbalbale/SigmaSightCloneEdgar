'use client'

import type { DragEvent } from 'react'
import React from 'react'
import { Badge } from '@/components/ui/badge'
import type { PositionTag, TagSize } from '@/types/tags'

interface TagBadgeProps {
  tag: PositionTag
  draggable?: boolean
  onDelete?: (tagId: string) => void
  className?: string
  size?: TagSize
  onDragStart?: (event: DragEvent<HTMLSpanElement>, tag: PositionTag) => void
  onDragEnd?: (event: DragEvent<HTMLSpanElement>, tag: PositionTag) => void
}

export function TagBadge({
  tag,
  draggable = false,
  onDelete,
  className = '',
  size = 'md',
  onDragStart,
  onDragEnd
}: TagBadgeProps) {
  const handleDragStart = (event: DragEvent<HTMLSpanElement>) => {
    if (!draggable) return

    if (onDragStart) {
      onDragStart(event, tag)
      return
    }

    event.dataTransfer.setData('text/plain', tag.id)
    event.dataTransfer.effectAllowed = 'copy'
  }

  const handleDragEnd = (event: DragEvent<HTMLSpanElement>) => {
    if (!draggable) return

    if (onDragEnd) {
      onDragEnd(event, tag)
      return
    }

    window.dispatchEvent(new CustomEvent('tagDragEnd'))
  }

  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-1' : 'text-sm px-3 py-1'

  return (
    <Badge
      variant="secondary"
      draggable={draggable}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={`
        ${sizeClasses}
        ${draggable ? 'cursor-move' : ''}
        ${className}
      `}
      style={{
        backgroundColor: tag.color || '#3B82F6',
        color: 'white'
      }}
    >
      <span>{tag.name}</span>
      {onDelete && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation()
            onDelete(tag.id)
          }}
          className="ml-2 text-xs leading-none hover:text-gray-200 focus:outline-none"
          aria-label={`Remove ${tag.name}`}
        >
          ×
        </button>
      )}
    </Badge>
  )
}
