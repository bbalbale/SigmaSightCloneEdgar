'use client'

import React from 'react'
import { FilterState } from '@/stores/researchStore'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export interface ResearchFilterBarProps {
  filters: FilterState
  onSearchChange: (search: string) => void
  onClearFilters: () => void
}

export function ResearchFilterBar({
  filters,
  onSearchChange,
  onClearFilters
}: ResearchFilterBarProps) {
  return (
    <div className="flex gap-2 items-center py-3">
      {/* Search */}
      <Input
        placeholder="Search symbol or name..."
        value={filters.search}
        onChange={(e) => onSearchChange(e.target.value)}
        className="max-w-xs"
      />

      {/* More filters will be added here */}

      {/* Clear Filters */}
      <Button
        variant="ghost"
        onClick={onClearFilters}
        className="text-xs"
      >
        Clear All
      </Button>
    </div>
  )
}
