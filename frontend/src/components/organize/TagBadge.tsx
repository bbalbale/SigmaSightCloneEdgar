'use client'

import { TagItem } from '@/services/tagsApi'
import { Badge } from '@/components/ui/badge'

interface TagBadgeProps {
  tag: TagItem
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
      e.dataTransfer.setData('tagId', tag.id)
      e.dataTransfer.effectAllowed = 'copy'
    }
  }

  return (
    <Badge
      variant="secondary"
      draggable={draggable}
      onDragStart={handleDragStart}
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
