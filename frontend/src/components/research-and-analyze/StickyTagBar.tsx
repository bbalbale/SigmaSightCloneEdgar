'use client'

import React from 'react'
import { StickyTagBarDesktop } from './StickyTagBarDesktop'
import { StickyTagBarMobile } from './StickyTagBarMobile'
import { Tag } from '@/stores/researchStore'

export interface StickyTagBarProps {
  tags: Tag[]
  onCreateTag: () => void
  onRestoreSectorTags: () => void
}

/**
 * StickyTagBar - Responsive Wrapper
 *
 * Desktop: Auto-hide sticky bar with horizontal tags
 * Mobile: Collapsible bar (collapsed by default)
 */
export function StickyTagBar({
  tags,
  onCreateTag,
  onRestoreSectorTags
}: StickyTagBarProps) {
  return (
    <>
      {/* Desktop: Auto-hide sticky bar (hidden on mobile) */}
      <div className="hidden md:block">
        <StickyTagBarDesktop
          tags={tags}
          onCreateTag={onCreateTag}
          onRestoreSectorTags={onRestoreSectorTags}
        />
      </div>

      {/* Mobile: Collapsible bar (hidden on desktop) */}
      <div className="md:hidden">
        <StickyTagBarMobile
          tags={tags}
          onCreateTag={onCreateTag}
          onRestoreSectorTags={onRestoreSectorTags}
        />
      </div>
    </>
  )
}
