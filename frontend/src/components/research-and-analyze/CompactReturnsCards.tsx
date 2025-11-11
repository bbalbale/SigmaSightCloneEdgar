'use client'

import React from 'react'

interface CompactReturnsCardsProps {
  eoyReturn: number
  nextYearReturn: number
}

export function CompactReturnsCards({ eoyReturn, nextYearReturn }: CompactReturnsCardsProps) {
  return (
    <div className="flex gap-3 h-full">
      {/* EOY Return Card */}
      <div
        className="flex-1 rounded-lg px-4 py-3 transition-all duration-300"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
          border: '1px solid'
        }}
      >
        <div className="flex flex-col items-center justify-center h-full">
          <div
            className="text-xs font-medium mb-1 transition-colors duration-300"
            style={{ color: 'var(--text-secondary)' }}
          >
            EOY Return
          </div>
          <div
            className="text-xl font-bold tabular-nums transition-colors duration-300"
            style={{
              color: eoyReturn >= 0 ? 'var(--color-success)' : 'var(--color-error)'
            }}
          >
            {eoyReturn >= 0 ? '+' : ''}{eoyReturn.toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Next Year Return Card */}
      <div
        className="flex-1 rounded-lg px-4 py-3 transition-all duration-300"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-primary)',
          border: '1px solid'
        }}
      >
        <div className="flex flex-col items-center justify-center h-full">
          <div
            className="text-xs font-medium mb-1 transition-colors duration-300"
            style={{ color: 'var(--text-secondary)' }}
          >
            Next Year Return
          </div>
          <div
            className="text-xl font-bold tabular-nums transition-colors duration-300"
            style={{
              color: nextYearReturn >= 0 ? 'var(--color-success)' : 'var(--color-error)'
            }}
          >
            {nextYearReturn >= 0 ? '+' : ''}{nextYearReturn.toFixed(1)}%
          </div>
        </div>
      </div>
    </div>
  )
}
