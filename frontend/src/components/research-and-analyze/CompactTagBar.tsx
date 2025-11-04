'use client'

import React, { useState, useRef, useEffect } from 'react'
import { TagBadge } from '@/components/organize/TagBadge'
import { Button } from '@/components/ui/button'
import type { PositionTag } from '@/types/tags'

interface CompactTagBarProps {
  tags: PositionTag[]
  onViewAll: () => void
  onCreate: () => void
}

export function CompactTagBar({ tags, onViewAll, onCreate }: CompactTagBarProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [visibleCount, setVisibleCount] = useState(tags.length)

  // Calculate how many tags can fit dynamically
  useEffect(() => {
    const calculateVisibleTags = () => {
      if (!containerRef.current || tags.length === 0) return

      const container = containerRef.current
      const containerWidth = container.offsetWidth

      // Reserve space for buttons (View All + New + gaps)
      const buttonSpace = 200 // ~100px per button + gaps
      const countBadgeSpace = 60 // Space for "+N" badge
      const availableWidth = containerWidth - buttonSpace - countBadgeSpace

      // Estimate tag width (rough estimate: ~80-120px per tag including gaps)
      const estimatedTagWidth = 100
      const maxTags = Math.floor(availableWidth / estimatedTagWidth)

      setVisibleCount(Math.max(1, Math.min(maxTags, tags.length)))
    }

    calculateVisibleTags()
    window.addEventListener('resize', calculateVisibleTags)
    return () => window.removeEventListener('resize', calculateVisibleTags)
  }, [tags.length])

  const visibleTags = tags.slice(0, visibleCount)
  const hiddenCount = tags.length - visibleCount

  return (
    <div
      ref={containerRef}
      className="flex items-center gap-2 h-full"
    >
      {/* Action Buttons - moved to left */}
      <div className="flex gap-2 flex-shrink-0">
        <Button
          size="sm"
          variant="outline"
          onClick={onViewAll}
          className="text-xs h-8"
        >
          View All
        </Button>
        <Button
          size="sm"
          variant="default"
          onClick={onCreate}
          className="text-xs h-8"
        >
          + New
        </Button>
      </div>

      {/* Visible Tags */}
      <div className="flex gap-2 items-center flex-1 min-w-0">
        {visibleTags.length > 0 ? (
          <>
            {visibleTags.map(tag => (
              <TagBadge
                key={tag.id}
                tag={tag}
                draggable={true}
                size="sm"
              />
            ))}
            {hiddenCount > 0 && (
              <span
                className="text-xs px-2 py-1 rounded transition-colors duration-300 flex-shrink-0"
                style={{
                  backgroundColor: 'var(--bg-tertiary)',
                  color: 'var(--text-secondary)',
                  fontWeight: 500
                }}
              >
                +{hiddenCount}
              </span>
            )}
          </>
        ) : (
          <span
            className="text-sm transition-colors duration-300"
            style={{ color: 'var(--text-tertiary)' }}
          >
            No tags yet
          </span>
        )}
      </div>
    </div>
  )
}
