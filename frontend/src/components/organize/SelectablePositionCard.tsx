import React, { useState } from 'react'
import { TagBadge } from './TagBadge'

// Simple tag interface for display - matches Position tags from API
interface TagDisplay {
  id: string
  name: string
  color: string
  description?: string
}

interface SelectablePositionCardProps {
  children: React.ReactNode
  positionId: string
  symbol: string
  isSelected: boolean
  onToggleSelection: () => void
  tags?: TagDisplay[]
  onDropTag?: (tagId: string) => void
  onDropPosition?: (droppedPositionId: string, targetPositionId: string) => void
}

export function SelectablePositionCard({
  children,
  positionId,
  symbol,
  isSelected,
  onToggleSelection,
  tags = [],
  onDropTag,
  onDropPosition
}: SelectablePositionCardProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [dragType, setDragType] = useState<'tag' | 'position' | null>(null)

  // Drag start handler - make position draggable
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('positionId', positionId)
    e.dataTransfer.setData('symbol', symbol)
    e.dataTransfer.effectAllowed = 'move'
    setIsDragging(true)
  }

  const handleDragEnd = (e: React.DragEvent) => {
    setIsDragging(false)
  }

  // Drag & drop handlers for tag application AND position combination
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()

    // Check if we're dragging a position or a tag
    const draggedPositionId = e.dataTransfer.types.includes('positionid') ? 'position' : 'tag'
    setDragType(draggedPositionId)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    setDragType(null)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragType(null)

    // Check what was dropped
    const tagId = e.dataTransfer.getData('tagId')
    const droppedPositionId = e.dataTransfer.getData('positionId')

    if (tagId && onDropTag) {
      // Tag was dropped
      onDropTag(tagId)
    } else if (droppedPositionId && onDropPosition && droppedPositionId !== positionId) {
      // Position was dropped (and it's not the same position)
      onDropPosition(droppedPositionId, positionId)
    }
  }

  // Dynamic styles based on drag state
  const getDragOverlayStyle = () => {
    if (dragType === 'position') {
      return {
        backgroundColor: 'rgba(34, 197, 94, 0.1)', // green overlay
        pointerEvents: 'none' as const,
        position: 'absolute' as const,
        inset: 0,
        borderRadius: '0.5rem'
      }
    } else if (dragType === 'tag') {
      return {
        backgroundColor: 'rgba(59, 130, 246, 0.1)', // blue overlay
        pointerEvents: 'none' as const,
        position: 'absolute' as const,
        inset: 0,
        borderRadius: '0.5rem'
      }
    }
    return null
  }

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className="relative transition-all rounded-lg cursor-move"
      style={{
        opacity: isDragging ? 0.5 : 1,
        ...(isSelected ? {
          boxShadow: '0 0 0 2px rgb(59 130 246), 0 0 0 4px var(--bg-primary)'
        } : {})
      }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {dragType && <div style={getDragOverlayStyle()} />}

      {/* Checkbox + Card Layout */}
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelection}
          className="mt-4 h-4 w-4 cursor-pointer rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />

        {/* Card Content + Tags */}
        <div className="flex-1 min-w-0">
          {/* Position Card */}
          {children}

          {/* Tags Display */}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2 ml-1">
              {tags.map(tag => (
                <TagBadge key={tag.id} tag={tag} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
