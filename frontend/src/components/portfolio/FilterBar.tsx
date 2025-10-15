'use client'

import React, { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/contexts/ThemeContext'
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
  const { theme } = useTheme()
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
        <div className={`flex items-center justify-between text-sm transition-colors duration-300 ${
          theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
        }`}>
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
                className={`transition-colors duration-300 ${
                  selectedTagId
                    ? theme === 'dark'
                      ? 'text-white border-blue-500 bg-blue-600 hover:bg-blue-700'
                      : 'text-white border-blue-500 bg-blue-500 hover:bg-blue-600'
                    : theme === 'dark'
                      ? 'text-slate-400 border-slate-600 bg-slate-800 hover:bg-slate-700'
                      : 'text-gray-600 border-gray-300 bg-white hover:bg-gray-50'
                }`}
              >
                {selectedTag ? selectedTag.name : 'Tags'}
                {showTagMenu ? ' ▲' : ' ▼'}
              </Button>

              {showTagMenu && (
                <div className={`absolute right-0 top-full mt-2 w-48 rounded-lg shadow-lg border z-50 ${
                  theme === 'dark'
                    ? 'bg-slate-800 border-slate-700'
                    : 'bg-white border-gray-200'
                }`}>
                  <div className="p-2 max-h-64 overflow-y-auto">
                    <button
                      onClick={() => {
                        onTagFilterChange?.(null)
                        setShowTagMenu(false)
                      }}
                      className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                        !selectedTagId
                          ? theme === 'dark'
                            ? 'bg-slate-700 text-white'
                            : 'bg-gray-100 text-gray-900'
                          : theme === 'dark'
                            ? 'text-slate-300 hover:bg-slate-700'
                            : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      All (No Filter)
                    </button>
                    {tags.length === 0 ? (
                      <div className={`px-3 py-2 text-sm ${
                        theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                      }`}>
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
                          className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                            selectedTagId === tag.id
                              ? theme === 'dark'
                                ? 'bg-slate-700 text-white'
                                : 'bg-gray-100 text-gray-900'
                              : theme === 'dark'
                                ? 'text-slate-300 hover:bg-slate-700'
                                : 'text-gray-700 hover:bg-gray-50'
                          }`}
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
                className={`transition-colors duration-300 ${
                  selectedFactorName
                    ? theme === 'dark'
                      ? 'text-white border-blue-500 bg-blue-600 hover:bg-blue-700'
                      : 'text-white border-blue-500 bg-blue-500 hover:bg-blue-600'
                    : theme === 'dark'
                      ? 'text-slate-400 border-slate-600 bg-slate-800 hover:bg-slate-700'
                      : 'text-gray-600 border-gray-300 bg-white hover:bg-gray-50'
                }`}
              >
                {selectedFactorName || 'Exposure'}
                {showFactorMenu ? ' ▲' : ' ▼'}
              </Button>

              {showFactorMenu && (
                <div className={`absolute right-0 top-full mt-2 w-48 rounded-lg shadow-lg border z-50 ${
                  theme === 'dark'
                    ? 'bg-slate-800 border-slate-700'
                    : 'bg-white border-gray-200'
                }`}>
                  <div className="p-2 max-h-64 overflow-y-auto">
                    <button
                      onClick={() => {
                        onFactorFilterChange?.(null)
                        setShowFactorMenu(false)
                      }}
                      className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                        !selectedFactorName
                          ? theme === 'dark'
                            ? 'bg-slate-700 text-white'
                            : 'bg-gray-100 text-gray-900'
                          : theme === 'dark'
                            ? 'text-slate-300 hover:bg-slate-700'
                            : 'text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      All (No Filter)
                    </button>
                    {factorExposures.length === 0 ? (
                      <div className={`px-3 py-2 text-sm ${
                        theme === 'dark' ? 'text-slate-400' : 'text-gray-500'
                      }`}>
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
                          className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                            selectedFactorName === factor.name
                              ? theme === 'dark'
                                ? 'bg-slate-700 text-white'
                                : 'bg-gray-100 text-gray-900'
                              : theme === 'dark'
                                ? 'text-slate-300 hover:bg-slate-700'
                                : 'text-gray-700 hover:bg-gray-50'
                          }`}
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
                className={`transition-colors duration-300 ${
                  theme === 'dark'
                    ? 'text-red-400 border-red-600 bg-slate-800 hover:bg-red-900/20'
                    : 'text-red-600 border-red-300 bg-white hover:bg-red-50'
                }`}
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