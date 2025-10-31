'use client'

import React from 'react'
import { Position } from '@/stores/researchStore'
import { SimplifiedPositionCard } from './SimplifiedPositionCard'

export interface TabContentProps {
  positions: Position[]
  onPositionClick: (position: Position) => void
  onTagDrop: (positionId: string, tagId: string) => void
  theme: 'dark' | 'light'
}

export function TabContent({ positions, onPositionClick, onTagDrop, theme }: TabContentProps) {
  if (positions.length === 0) {
    return (
      <div className="py-8 text-center text-slate-400">
        No positions found matching your filters
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 py-4">
      {positions.map((position) => (
        <SimplifiedPositionCard
          key={position.id}
          position={position}
          onClick={() => onPositionClick(position)}
          onDrop={(tagId) => onTagDrop(position.id, tagId)}
          theme={theme}
        />
      ))}
    </div>
  )
}
