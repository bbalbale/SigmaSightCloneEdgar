'use client'

import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { TagBadge } from '@/components/organize/TagBadge'
import { Button } from '@/components/ui/button'
import type { Tag } from '@/lib/types'

interface StickyTagBarMobileProps {
  tags: Tag[]
  onCreateTag?: () => void
  onRestoreSectorTags?: () => void
}

/**
 * StickyTagBarMobile - Collapsible tag bar for mobile devices
 *
 * Mobile behavior:
 * - Collapsed by default showing tag count
 * - Tapping expands to show scrollable tags
 * - Action buttons in expanded section
 * - No auto-hide (different from desktop)
 */
export function StickyTagBarMobile({
  tags,
  onCreateTag,
  onRestoreSectorTags
}: StickyTagBarMobileProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="sticky top-0 z-40 transition-all duration-300" style={{
      backgroundColor: 'var(--bg-primary)',
      borderBottom: '1px solid var(--border-primary)'
    }}>
      {/* Collapsed Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between transition-colors duration-200"
        style={{
          backgroundColor: 'var(--bg-secondary)'
        }}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold transition-colors duration-300" style={{
            color: 'var(--text-primary)'
          }}>
            Tags
          </span>
          <span className="text-xs px-2 py-0.5 rounded transition-colors duration-300" style={{
            backgroundColor: 'var(--bg-tertiary)',
            color: 'var(--text-secondary)'
          }}>
            {tags.length}
          </span>
        </div>
        <div className="transition-colors duration-300" style={{ color: 'var(--text-secondary)' }}>
          {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 py-3 space-y-3 transition-colors duration-300" style={{
          backgroundColor: 'var(--bg-secondary)',
          borderTop: '1px solid var(--border-primary)'
        }}>
          {/* Action Buttons */}
          <div className="flex gap-2">
            {onCreateTag && (
              <Button
                onClick={onCreateTag}
                size="sm"
                className="flex-1 h-9 text-xs transition-colors duration-300"
                style={{
                  backgroundColor: 'var(--color-accent)',
                  color: 'var(--bg-primary)'
                }}
              >
                + New Tag
              </Button>
            )}
            {onRestoreSectorTags && (
              <Button
                onClick={onRestoreSectorTags}
                variant="outline"
                size="sm"
                className="flex-1 h-9 text-xs transition-colors duration-300"
                style={{
                  borderColor: 'var(--border-primary)',
                  color: 'var(--text-primary)'
                }}
              >
                Restore Sector Tags
              </Button>
            )}
          </div>

          {/* Tags - Horizontal Scroll */}
          {tags.length > 0 ? (
            <div className="overflow-x-auto pb-2">
              <div className="flex gap-2 min-w-min">
                {tags.map(tag => (
                  <div key={tag.id} className="flex-shrink-0">
                    <TagBadge
                      tag={tag}
                      draggable={true}
                      onDragStart={(e) => {
                        e.dataTransfer.setData('text/plain', tag.id)
                        e.dataTransfer.effectAllowed = 'copy'
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-sm text-center py-2 transition-colors duration-300" style={{
              color: 'var(--text-secondary)'
            }}>
              No tags yet. Create your first tag!
            </p>
          )}
        </div>
      )}
    </div>
  )
}
