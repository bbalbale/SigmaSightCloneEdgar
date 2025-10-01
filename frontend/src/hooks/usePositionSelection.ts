'use client'

import { useState, useCallback } from 'react'

const MAX_SELECTIONS = 10

interface UsePositionSelectionReturn {
  selectedIds: string[]
  selectedCount: number
  isSelected: (id: string) => boolean
  toggleSelection: (id: string) => void
  clearSelection: () => void
  canSelectMore: boolean
}

/**
 * Hook to manage position selection state for combining positions
 * Enforces maximum of 10 selections at once
 */
export function usePositionSelection(): UsePositionSelectionReturn {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  const isSelected = useCallback((id: string) => {
    return selectedIds.has(id)
  }, [selectedIds])

  const toggleSelection = useCallback((id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)

      if (newSet.has(id)) {
        // Deselect
        newSet.delete(id)
      } else {
        // Select - check limit
        if (newSet.size >= MAX_SELECTIONS) {
          alert(`Maximum ${MAX_SELECTIONS} positions can be selected at once`)
          return prev
        }
        newSet.add(id)
      }

      return newSet
    })
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  const canSelectMore = selectedIds.size < MAX_SELECTIONS

  return {
    selectedIds: Array.from(selectedIds),
    selectedCount: selectedIds.size,
    isSelected,
    toggleSelection,
    clearSelection,
    canSelectMore
  }
}
