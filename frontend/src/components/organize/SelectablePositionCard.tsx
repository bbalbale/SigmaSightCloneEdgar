import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { TagItem } from '@/services/tagsApi'
import { TagBadge } from './TagBadge'

interface SelectablePositionCardProps {
  children: React.ReactNode
  positionId: string
  symbol: string
  isSelected: boolean
  onToggleSelection: () => void
  tags?: TagItem[]
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
  const { theme } = useTheme()

  // Drag start handler - make position draggable
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('positionId', positionId)
    e.dataTransfer.setData('symbol', symbol)
    e.dataTransfer.effectAllowed = 'move'

    // Add visual feedback
    e.currentTarget.classList.add('opacity-50')
  }

  const handleDragEnd = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('opacity-50')
  }

  // Drag & drop handlers for tag application AND position combination
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()

    // Check if we're dragging a position or a tag
    const draggedPositionId = e.dataTransfer.types.includes('positionid') ? 'position' : 'tag'

    if (draggedPositionId === 'position') {
      // Position drag - green highlight for combination
      e.currentTarget.classList.add(
        theme === 'dark' ? 'bg-green-900/20' : 'bg-green-50'
      )
    } else {
      // Tag drag - blue highlight
      e.currentTarget.classList.add(
        theme === 'dark' ? 'bg-blue-900/20' : 'bg-blue-50'
      )
    }
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20', 'bg-green-50', 'bg-green-900/20')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20', 'bg-green-50', 'bg-green-900/20')

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

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={`relative transition-all rounded-lg cursor-move ${
        isSelected
          ? theme === 'dark'
            ? 'ring-2 ring-blue-500 ring-offset-2 ring-offset-slate-900'
            : 'ring-2 ring-blue-500 ring-offset-2'
          : ''
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
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
