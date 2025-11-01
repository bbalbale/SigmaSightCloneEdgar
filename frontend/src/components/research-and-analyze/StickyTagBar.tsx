'use client'

import React, { useState, useEffect } from 'react'
import { Tag } from '@/stores/researchStore'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/contexts/ThemeContext'

export interface StickyTagBarProps {
  tags: Tag[]
  onCreateTag: () => void
  onRestoreSectorTags: () => void
}

export function StickyTagBar({
  tags,
  onCreateTag,
  onRestoreSectorTags
}: StickyTagBarProps) {
  const { theme } = useTheme()
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
      className={`sticky top-0 z-40 transition-transform duration-300 ${
        isVisible ? 'translate-y-0' : '-translate-y-full'
      } ${
        theme === 'dark'
          ? 'bg-primary border-b border-primary'
          : 'bg-white border-b border-slate-200'
      }`}
    >
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Tag Label */}
          <span className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mr-2">
            TAGS
          </span>

          {/* Draggable Tags or Placeholder */}
          {tags.length > 0 ? (
            tags.map(tag => (
              <div
                key={tag.id}
                draggable
                onDragStart={(e) => handleDragStart(e, tag.id)}
                className="px-3 py-1.5 rounded text-xs font-medium cursor-move transition-all hover:scale-105"
                style={{
                  backgroundColor: `${tag.color}20`,
                  color: tag.color,
                  border: `1px solid ${tag.color}40`
                }}
              >
                {tag.name}
              </div>
            ))
          ) : (
            <span className={`text-sm ${theme === 'dark' ? 'text-tertiary' : 'text-slate-600'}`}>
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
