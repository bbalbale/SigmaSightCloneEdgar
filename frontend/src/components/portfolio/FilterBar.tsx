'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { TagBadge } from '@/components/organize/TagBadge'
import type { TagItem } from '@/types/strategies'
import type { FactorExposure } from '@/types/analytics'

interface FilterBarProps {
  tags?: TagItem[]
  factorExposures?: FactorExposure[]
  selectedTagId?: string | null
  selectedFactorName?: string | null
  onTagFilterChange?: (tagId: string | null) => void
  onFactorFilterChange?: (factorName: string | null) => void
}

export function FilterBar({
  tags = [],
  factorExposures = [],
  selectedTagId,
  selectedFactorName,
  onTagFilterChange,
  onFactorFilterChange
}: FilterBarProps) {
  const [showTagMenu, setShowTagMenu] = useState(false)
  const [showFactorMenu, setShowFactorMenu] = useState(false)
  const tagMenuRef = useRef<HTMLDivElement>(null)
  const factorMenuRef = useRef<HTMLDivElement>(null)

  // Close menus when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (tagMenuRef.current && !tagMenuRef.current.contains(event.target as Node)) {
        setShowTagMenu(false)
      }
      if (factorMenuRef.current && !factorMenuRef.current.contains(event.target as Node)) {
        setShowFactorMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const selectedTag = tags.find(t => t.id === selectedTagId)
  const hasActiveFilter = selectedTagId || selectedFactorName

  return (
    <section className="px-4 pb-4">
      <div className="container mx-auto">
        <div className="flex items-center justify-between text-sm transition-colors duration-300 text-secondary">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h6a1 1 0 110 2H4a1 1 0 01-1-1zM3 16a1 1 0 011-1h4a1 1 0 110 2H4a1 1 0 01-1-1z"/>
            </svg>
            <span>Filter by:</span>
          </div>
          <div className="flex items-center gap-3">
            {/* Tags Filter */}
            <div className="relative" ref={tagMenuRef}>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowTagMenu(!showTagMenu)
                  setShowFactorMenu(false)
                }}
                className="transition-colors duration-300"
                style={{
                  ...(selectedTagId ? {
                    color: 'white',
                    borderColor: '#3b82f6',
                    backgroundColor: '#2563eb'
                  } : {
                    color: 'var(--text-secondary)',
                    borderColor: 'var(--border-primary)',
                    backgroundColor: 'var(--bg-primary)'
                  })
                }}
              >
                {selectedTag ? selectedTag.name : 'Tags'}
                {showTagMenu ? ' ▲' : ' ▼'}
              </Button>

              {showTagMenu && (
                <div className="absolute right-0 top-full mt-2 w-48 rounded-lg shadow-lg border z-50 themed-card">
                  <div className="p-2 max-h-64 overflow-y-auto">
                    <button
                      onClick={() => {
                        onTagFilterChange?.(null)
                        setShowTagMenu(false)
                      }}
                      className="w-full text-left px-3 py-2 rounded text-sm transition-colors"
                      style={{
                        backgroundColor: !selectedTagId ? 'var(--bg-secondary)' : 'transparent',
                        color: 'var(--text-primary)'
                      }}
                    >
                      All (No Filter)
                    </button>
                    {tags.length === 0 ? (
                      <div className="px-3 py-2 text-sm text-secondary">
                        No tags available
                      </div>
                    ) : (
                      tags.map(tag => (
                        <button
                          key={tag.id}
                          onClick={() => {
                            onTagFilterChange?.(tag.id)
                            setShowTagMenu(false)
                          }}
                          className="w-full text-left px-3 py-2 rounded text-sm transition-colors hover:opacity-80"
                          style={{
                            backgroundColor: selectedTagId === tag.id ? 'var(--bg-secondary)' : 'transparent',
                            color: 'var(--text-primary)'
                          }}
                        >
                          <div className="flex items-center gap-2">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: tag.color }}
                            />
                            {tag.name}
                          </div>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Factor Exposure Filter */}
            <div className="relative" ref={factorMenuRef}>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowFactorMenu(!showFactorMenu)
                  setShowTagMenu(false)
                }}
                className="transition-colors duration-300"
                style={{
                  ...(selectedFactorName ? {
                    color: 'white',
                    borderColor: '#3b82f6',
                    backgroundColor: '#2563eb'
                  } : {
                    color: 'var(--text-secondary)',
                    borderColor: 'var(--border-primary)',
                    backgroundColor: 'var(--bg-primary)'
                  })
                }}
              >
                {selectedFactorName || 'Exposure'}
                {showFactorMenu ? ' ▲' : ' ▼'}
              </Button>

              {showFactorMenu && (
                <div className="absolute right-0 top-full mt-2 w-48 rounded-lg shadow-lg border z-50 themed-card">
                  <div className="p-2 max-h-64 overflow-y-auto">
                    <button
                      onClick={() => {
                        onFactorFilterChange?.(null)
                        setShowFactorMenu(false)
                      }}
                      className="w-full text-left px-3 py-2 rounded text-sm transition-colors"
                      style={{
                        backgroundColor: !selectedFactorName ? 'var(--bg-secondary)' : 'transparent',
                        color: 'var(--text-primary)'
                      }}
                    >
                      All (No Filter)
                    </button>
                    {factorExposures.length === 0 ? (
                      <div className="px-3 py-2 text-sm text-secondary">
                        No exposures available
                      </div>
                    ) : (
                      factorExposures.map(factor => (
                        <button
                          key={factor.name}
                          onClick={() => {
                            onFactorFilterChange?.(factor.name)
                            setShowFactorMenu(false)
                          }}
                          className="w-full text-left px-3 py-2 rounded text-sm transition-colors hover:opacity-80"
                          style={{
                            backgroundColor: selectedFactorName === factor.name ? 'var(--bg-secondary)' : 'transparent',
                            color: 'var(--text-primary)'
                          }}
                        >
                          {factor.name}
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Clear Filters Button */}
            {hasActiveFilter && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onTagFilterChange?.(null)
                  onFactorFilterChange?.(null)
                }}
                className="transition-colors duration-300 text-red-400 border-red-600 hover:bg-red-900/20"
                style={{
                  borderColor: '#dc2626'
                }}
              >
                Clear
              </Button>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
