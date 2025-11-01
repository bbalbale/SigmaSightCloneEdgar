'use client'

import React from 'react'
import { ResearchTableViewDesktop } from './ResearchTableViewDesktop'
import { ResearchTableMobile } from './ResearchTableMobile'
import type { EnhancedPosition } from '@/services/positionResearchService'
import type { TargetPriceUpdate } from '@/services/targetPriceUpdateService'

interface ResearchTableViewProps {
  positions: EnhancedPosition[]
  title: string
  aggregateReturnEOY: number
  aggregateReturnNextYear: number
  onTargetPriceUpdate?: (update: TargetPriceUpdate) => Promise<void>
  onTagDrop?: (positionId: string, tagId: string) => Promise<void>
  onRemoveTag?: (positionId: string, tagId: string) => Promise<void>
}

/**
 * ResearchTableView - Responsive Wrapper
 *
 * Renders desktop table on ≥768px, mobile cards on <768px.
 * Uses CSS-based conditional rendering for better performance.
 *
 * Desktop: Full 9-column table with expandable rows
 * Mobile: Compact position cards with essential info
 */
export function ResearchTableView({
  positions,
  title,
  aggregateReturnEOY,
  aggregateReturnNextYear,
  onTargetPriceUpdate,
  onTagDrop,
  onRemoveTag
}: ResearchTableViewProps) {
  return (
    <>
      {/* Desktop: Table (hidden on mobile) */}
      <div className="hidden md:block">
        <ResearchTableViewDesktop
          positions={positions}
          title={title}
          aggregateReturnEOY={aggregateReturnEOY}
          aggregateReturnNextYear={aggregateReturnNextYear}
          onTargetPriceUpdate={onTargetPriceUpdate}
          onTagDrop={onTagDrop}
          onRemoveTag={onRemoveTag}
        />
      </div>

      {/* Mobile: Cards (hidden on desktop) */}
      <div className="md:hidden">
        <ResearchTableMobile
          positions={positions}
          title={title}
          aggregateReturnEOY={aggregateReturnEOY}
          aggregateReturnNextYear={aggregateReturnNextYear}
          onTargetPriceUpdate={onTargetPriceUpdate}
          onTagDrop={onTagDrop}
          onRemoveTag={onRemoveTag}
        />
      </div>
    </>
  )
}
