'use client'

import React, { useState, useEffect } from 'react'
import { Tag } from '@/stores/researchStore'
import { Button } from '@/components/ui/button'

export interface StickyTagBarProps {
  tags: Tag[]
  onCreateTag: () => void
  onRestoreSectorTags: () => void
}

export function StickyTagBarDesktop({
  tags,
  onCreateTag,
  onRestoreSectorTags
}: StickyTagBarProps) {
  const [isVisible, setIsVisible] = useState(true)
  const [lastScrollY, setLastScrollY] = useState(0)

  // Auto-hide on scroll down, show on scroll up
  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false) // Scrolling down
      } else {
        setIsVisible(true) // Scrolling up
      }
      setLastScrollY(currentScrollY)
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [lastScrollY])

  const handleDragStart = (e: React.DragEvent, tagId: string) => {
    e.dataTransfer.setData('tagId', tagId)
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      className={`sticky top-0 z-40 transition-all duration-300 border-b ${
        isVisible ? 'translate-y-0' : '-translate-y-full'
      }`}
      style={{
        backgroundColor: 'var(--bg-primary)',
        borderColor: 'var(--border-primary)'
      }}
    >
      <div className="container mx-auto py-3">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Tag Label */}
          <span className="font-semibold uppercase tracking-wider mr-2 transition-colors duration-300" style={{
            fontSize: '10px',
            color: 'var(--text-tertiary)'
          }}>
            TAGS
          </span>

          {/* Draggable Tags or Placeholder */}
          {tags.length > 0 ? (
            tags.map(tag => (
              <div
                key={tag.id}
                draggable
                onDragStart={(e) => handleDragStart(e, tag.id)}
                className="px-3 py-1.5 rounded font-medium cursor-move transition-all hover:scale-105"
                style={{
                  backgroundColor: `${tag.color}20`,
                  color: tag.color,
                  border: `1px solid ${tag.color}40`,
                  fontSize: 'var(--text-xs)'
                }}
              >
                {tag.name}
              </div>
            ))
          ) : (
            <span className="transition-colors duration-300" style={{
              fontSize: 'var(--text-sm)',
              color: 'var(--text-tertiary)'
            }}>
              No tags yet
            </span>
          )}

          {/* Buttons */}
          <Button
            size="sm"
            variant="outline"
            onClick={onCreateTag}
            className={tags.length > 0 ? 'ml-auto text-xs' : 'text-xs'}
          >
            + New Tag
          </Button>

          <Button
            size="sm"
            variant="default"
            onClick={onRestoreSectorTags}
            className="text-xs"
          >
            Restore Sector Tags
          </Button>
        </div>
      </div>
    </div>
  )
}
