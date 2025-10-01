import React from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { TagItem } from '@/services/tagsApi'
import { TagBadge } from './TagBadge'

interface SelectablePositionCardProps {
  children: React.ReactNode
  isSelected: boolean
  onToggleSelection: () => void
  tags?: TagItem[]
  onDropTag?: (tagId: string) => void
}

export function SelectablePositionCard({
  children,
  isSelected,
  onToggleSelection,
  tags = [],
  onDropTag
}: SelectablePositionCardProps) {
  const { theme } = useTheme()

  // Drag & drop handlers for tag application
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.add(
      theme === 'dark' ? 'bg-blue-900/20' : 'bg-blue-50'
    )
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20')
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.currentTarget.classList.remove('bg-blue-50', 'bg-blue-900/20')

    const tagId = e.dataTransfer.getData('tagId')
    if (tagId && onDropTag) {
      onDropTag(tagId)
    }
  }

  return (
    <div
      className={`relative transition-all rounded-lg ${
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
