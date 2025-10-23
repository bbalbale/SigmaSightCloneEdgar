'use client'

import { Badge } from '@/components/ui/badge'

// Simple tag interface for display - only requires what's actually used
interface TagDisplay {
  id: string
  name: string
  color?: string
}

interface TagBadgeProps {
  tag: TagDisplay
  draggable?: boolean
  onDelete?: (tagId: string) => void
  className?: string
}

export function TagBadge({
  tag,
  draggable = false,
  onDelete,
  className = ''
}: TagBadgeProps) {
  const handleDragStart = (e: React.DragEvent) => {
    if (draggable) {
      console.log('Starting drag of tag:', tag.name, tag.id)
      // Use text/plain format for better compatibility
      e.dataTransfer.setData('text/plain', tag.id)
      e.dataTransfer.effectAllowed = 'copy'
      console.log('Set dataTransfer with tag.id:', tag.id)
    }
  }

  const handleDragEnd = (e: React.DragEvent) => {
    if (draggable) {
      console.log('Drag ended for tag:', tag.name)
      // Dispatch custom event to stop auto-scroll
      window.dispatchEvent(new CustomEvent('tagDragEnd'))
    }
  }

  return (
    <Badge
      variant="secondary"
      draggable={draggable}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={`
        text-xs px-2 py-1
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
          onClick={(e) => {
            e.stopPropagation()
            onDelete(tag.id)
          }}
          className="ml-2 hover:text-gray-200"
        >
          ×
        </button>
      )}
    </Badge>
  )
}
