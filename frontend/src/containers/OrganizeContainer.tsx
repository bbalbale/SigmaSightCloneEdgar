'use client'

import React, { useState, useRef } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { usePortfolioData } from '@/hooks/usePortfolioData'
import { useTags } from '@/hooks/useTags'
import { usePositionTags } from '@/hooks/usePositionTags'
import { useRestoreSectorTags } from '@/hooks/useRestoreSectorTags'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { TagList } from '@/components/organize/TagList'
import { PositionList } from '@/components/common/PositionList'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

export function OrganizeContainer() {
  const { theme } = useTheme()
  const { portfolioId } = usePortfolioStore()

  // Auto-scroll ref for drag-drop (using ref to avoid stale closures)
  const autoScrollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Fetch positions (includes tags array automatically from backend)
  const {
    loading,
    positions,
    publicPositions,
    optionsPositions,
    privatePositions,
    handleRetry: refreshPositions
  } = usePortfolioData()

  // Debug logging
  console.log('[OrganizeContainer] All positions:', positions)
  console.log('[OrganizeContainer] Public positions:', publicPositions)
  console.log('[OrganizeContainer] Positions with tags:', positions?.filter((p: any) => p.tags && p.tags.length > 0).length || 0)

  // Tag management
  const {
    tags,
    createTag,
    deleteTag,
    loading: tagsLoading
  } = useTags()

  // Position tagging operations
  const {
    addTagsToPosition,
    removeTagsFromPosition,
    loading: positionTagsLoading
  } = usePositionTags()

  // Sector tag restoration
  const {
    restoreTags,
    loading: restoringTags
  } = useRestoreSectorTags()

  // Filter state
  const [selectedTagFilter, setSelectedTagFilter] = useState<string | null>(null)

  // Auto-scroll helper function - improved for better UX
  const handleAutoScroll = React.useCallback((e: React.DragEvent) => {
    const SCROLL_THRESHOLD = 150 // pixels from edge to trigger scroll (increased for easier triggering)
    const SCROLL_SPEED = 15 // pixels per interval (increased for faster scrolling)

    const { clientY } = e
    const viewportHeight = window.innerHeight

    // Clear any existing interval
    if (autoScrollIntervalRef.current) {
      clearInterval(autoScrollIntervalRef.current)
      autoScrollIntervalRef.current = null
    }

    // Calculate distance from edge for variable scroll speed
    const distanceFromTop = clientY
    const distanceFromBottom = viewportHeight - clientY

    // Check if near top edge - scroll up
    if (distanceFromTop < SCROLL_THRESHOLD && distanceFromTop > 0) {
      // Variable speed based on proximity to edge
      const speedMultiplier = 1 + (SCROLL_THRESHOLD - distanceFromTop) / SCROLL_THRESHOLD
      const interval = setInterval(() => {
        window.scrollBy(0, -SCROLL_SPEED * speedMultiplier)
      }, 16) // ~60fps
      autoScrollIntervalRef.current = interval
    }
    // Check if near bottom edge - scroll down
    else if (distanceFromBottom < SCROLL_THRESHOLD && distanceFromBottom > 0) {
      // Variable speed based on proximity to edge
      const speedMultiplier = 1 + (SCROLL_THRESHOLD - distanceFromBottom) / SCROLL_THRESHOLD
      const interval = setInterval(() => {
        window.scrollBy(0, SCROLL_SPEED * speedMultiplier)
      }, 16) // ~60fps
      autoScrollIntervalRef.current = interval
    }
  }, [])

  // Stop auto-scroll when drag ends or leaves
  const stopAutoScroll = React.useCallback(() => {
    if (autoScrollIntervalRef.current) {
      clearInterval(autoScrollIntervalRef.current)
      autoScrollIntervalRef.current = null
    }
  }, [])

  // Cleanup auto-scroll on unmount
  React.useEffect(() => {
    return () => {
      if (autoScrollIntervalRef.current) {
        clearInterval(autoScrollIntervalRef.current)
        autoScrollIntervalRef.current = null
      }
    }
  }, [])

  // Add global dragend listener as fallback to catch all drag end events
  React.useEffect(() => {
    const handleGlobalDragEnd = () => {
      console.log('[OrganizeContainer] Global drag end detected, stopping auto-scroll')
      stopAutoScroll()
    }

    // Listen for custom event from TagBadge
    window.addEventListener('tagDragEnd', handleGlobalDragEnd)
    // Listen for native dragend event as fallback
    document.addEventListener('dragend', handleGlobalDragEnd)

    return () => {
      window.removeEventListener('tagDragEnd', handleGlobalDragEnd)
      document.removeEventListener('dragend', handleGlobalDragEnd)
      stopAutoScroll()  // Always cleanup on unmount
    }
  }, [stopAutoScroll])

  // Handle tag drop on position
  const handleTagDrop = async (positionId: string, tagId: string) => {
    console.log('handleTagDrop called:', { positionId, tagId })
    stopAutoScroll() // Stop auto-scrolling

    if (!positionId || !tagId) {
      console.error('Missing positionId or tagId:', { positionId, tagId })
      return
    }
    try {
      await addTagsToPosition(positionId, [tagId], false) // false = don't replace existing
      console.log(`Tag ${tagId} added to position ${positionId}`)
      // Refresh positions to show updated tags
      refreshPositions()
    } catch (error) {
      console.error('Failed to add tag to position:', error)
      // Optionally show error toast
    }
  }

  // Handle tag removal from position
  const handleRemoveTag = async (positionId: string, tagId: string) => {
    console.log('handleRemoveTag called:', { positionId, tagId })
    if (!positionId || !tagId) {
      console.error('Missing positionId or tagId:', { positionId, tagId })
      return
    }
    try {
      await removeTagsFromPosition(positionId, [tagId])
      console.log(`Tag ${tagId} removed from position ${positionId}`)
      // Refresh positions to show updated tags
      refreshPositions()
    } catch (error) {
      console.error('Failed to remove tag from position:', error)
      // Optionally show error toast
    }
  }

  // Handle tag creation
  const handleCreateTag = async (name: string, color: string) => {
    try {
      await createTag(name, color)
      console.log(`Tag "${name}" created`)
    } catch (error) {
      console.error('Failed to create tag:', error)
      throw error
    }
  }

  // Handle tag deletion
  const handleDeleteTag = async (tagId: string) => {
    try {
      await deleteTag(tagId)
      console.log(`Tag ${tagId} deleted`)
      // Refresh positions to remove deleted tag from display
      refreshPositions()
    } catch (error) {
      console.error('Failed to delete tag:', error)
      throw error
    }
  }

  // Handle restore sector tags
  const handleRestoreSectorTags = async () => {
    if (!portfolioId) {
      console.error('No portfolio ID available')
      alert('Error: Portfolio ID not found. Please refresh the page.')
      return
    }

    try {
      const result = await restoreTags(portfolioId)
      console.log('Sector tags restored:', result)

      // Show success message
      alert(
        `✅ Sector tags restored!\n\n` +
        `• ${result.positions_tagged} positions tagged\n` +
        `• ${result.tags_created} new tags created\n` +
        `• ${result.positions_skipped} positions skipped\n\n` +
        `Sectors applied: ${result.tags_applied.map(t => t.tag_name).join(', ')}`
      )

      // Refresh positions to show updated tags
      refreshPositions()
    } catch (error: any) {
      console.error('Failed to restore sector tags:', error)
      alert(`❌ Failed to restore sector tags: ${error?.message || 'Unknown error'}`)
    }
  }

  // Split positions by type
  const publicLongs = publicPositions.filter(p => p.type === 'LONG' || !p.type)
  const publicShorts = publicPositions.filter(p => p.type === 'SHORT')
  const optionLongs = optionsPositions.filter(p => p.type === 'LC' || p.type === 'LP')
  const optionShorts = optionsPositions.filter(p => p.type === 'SC' || p.type === 'SP')

  // Filter positions by selected tag (if any)
  const filterByTag = (positionsList: any[]) => {
    if (!selectedTagFilter) return positionsList
    return positionsList.filter(p =>
      p.tags?.some((tag: any) => tag.id === selectedTagFilter)
    )
  }

  const filteredPublicLongs = filterByTag(publicLongs)
  const filteredPublicShorts = filterByTag(publicShorts)
  const filteredOptionLongs = filterByTag(optionLongs)
  const filteredOptionShorts = filterByTag(optionShorts)
  const filteredPrivate = filterByTag(privatePositions)

  return (
    <div className={`min-h-screen transition-colors duration-300 ${
      theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50'
    }`}>
      {/* Header */}
      <section className="px-4 py-8">
        <div className="container mx-auto">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className={`text-3xl font-bold mb-2 transition-colors duration-300 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                Organize & Tag Positions
              </h1>
              <p className={`transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
              }`}>
                Create tags and drag them onto positions to organize your portfolio
              </p>
            </div>

            {/* Restore Sector Tags Button */}
            <Button
              onClick={handleRestoreSectorTags}
              disabled={restoringTags || loading}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-md font-medium
                transition-all duration-200
                ${theme === 'dark'
                  ? 'bg-blue-600 hover:bg-blue-700 text-white disabled:bg-slate-700 disabled:text-slate-500'
                  : 'bg-blue-500 hover:bg-blue-600 text-white disabled:bg-gray-300 disabled:text-gray-500'
                }
                disabled:cursor-not-allowed
              `}
              title="Automatically create and apply sector tags to all positions based on company profiles"
            >
              {restoringTags ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Restoring...</span>
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>Restore Sector Tags</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </section>

      {/* Tag Management - STICKY */}
      <section className={`sticky top-0 z-40 px-4 pb-6 pt-4 transition-colors duration-300 ${
        theme === 'dark' ? 'bg-slate-900 border-b border-slate-700' : 'bg-gray-50 border-b border-gray-200'
      } shadow-sm`}>
        <div className="container mx-auto">
          <TagList
            tags={tags}
            onCreate={handleCreateTag}
            onDelete={handleDeleteTag}
          />
        </div>
      </section>

      {/* Filter by Tag (Optional) - STICKY BELOW TAGS */}
      {tags.length > 0 && (
        <section className={`sticky z-30 px-4 pb-4 pt-2 transition-colors duration-300 ${
          theme === 'dark' ? 'bg-slate-900 border-b border-slate-700' : 'bg-gray-50 border-b border-gray-200'
        } shadow-sm`} style={{ top: '180px' }}>
          <div className="container mx-auto">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`text-sm font-medium transition-colors duration-300 ${
                theme === 'dark' ? 'text-slate-300' : 'text-gray-700'
              }`}>
                Filter by tag:
              </span>
              <button
                onClick={() => setSelectedTagFilter(null)}
                className={`px-3 py-1 rounded-md text-sm transition-colors ${
                  selectedTagFilter === null
                    ? theme === 'dark'
                      ? 'bg-blue-600 text-white'
                      : 'bg-blue-500 text-white'
                    : theme === 'dark'
                      ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                All
              </button>
              {tags.map(tag => (
                <button
                  key={tag.id}
                  onClick={() => setSelectedTagFilter(tag.id)}
                  className={`px-3 py-1 rounded-md text-sm transition-colors`}
                  style={{
                    backgroundColor: selectedTagFilter === tag.id ? tag.color : undefined,
                    color: selectedTagFilter === tag.id ? '#fff' : undefined
                  }}
                >
                  {tag.name}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Loading State */}
      {loading && !positions.length ? (
        <section className="px-4 py-8">
          <div className="container mx-auto text-center">
            <p className={`text-lg transition-colors duration-300 ${
              theme === 'dark' ? 'text-slate-400' : 'text-gray-600'
            }`}>
              Loading positions...
            </p>
          </div>
        </section>
      ) : (
        <>
          {/* Positions Grid - Row 1: Public Longs/Shorts + Private */}
          <section className="px-4 pb-8">
            <div className="container mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Long Positions */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                      theme === 'dark' ? 'text-white' : 'text-gray-900'
                    }`}>
                      Long Stocks
                    </h3>
                    <Badge variant="secondary" className={`transition-colors duration-300 ${
                      theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {filteredPublicLongs.length}
                    </Badge>
                  </div>
                  <PositionList
                    items={filteredPublicLongs}
                    renderItem={(position, index) => {
                      // Debug: Check if position has ID
                      if (!position.id) {
                        console.warn(`Position ${position.symbol} missing ID at index ${index}`)
                      }

                      return (
                        <div
                          key={position.id || `position-${index}`}
                          className="relative"
                          onDragOver={(e) => {
                            e.preventDefault()
                            e.dataTransfer.dropEffect = 'copy'
                            handleAutoScroll(e) // Enable auto-scroll
                          }}
                          onDrop={(e) => {
                            e.preventDefault()
                            stopAutoScroll() // Stop auto-scroll on drop
                            const tagId = e.dataTransfer.getData('text/plain')
                            console.log('Position DROP:', position.symbol, 'Tag:', tagId)
                            if (tagId && position.id) {
                              handleTagDrop(position.id, tagId)
                            }
                          }}
                          onDragLeave={stopAutoScroll} // Stop auto-scroll when leaving
                        >
                          <div
                            className="border-2 border-transparent hover:border-gray-300 transition-all duration-200 rounded-lg p-1"
                            onDragEnter={(e) => {
                              e.currentTarget.style.borderColor = '#3B82F6'
                              e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.05)'
                            }}
                            onDragLeave={(e) => {
                              e.currentTarget.style.borderColor = 'transparent'
                              e.currentTarget.style.backgroundColor = 'transparent'
                            }}
                          >
                            <OrganizePositionCard position={position} onRemoveTag={handleRemoveTag} />
                          </div>
                        </div>
                      )
                    }}
                    emptyMessage="No long positions"
                  />
                </div>

                {/* Short Positions */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                      theme === 'dark' ? 'text-white' : 'text-gray-900'
                    }`}>
                      Short Stocks
                    </h3>
                    <Badge variant="secondary" className={`transition-colors duration-300 ${
                      theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {filteredPublicShorts.length}
                    </Badge>
                  </div>
                  <PositionList
                    items={filteredPublicShorts}
                    renderItem={(position) => (
                      <div
                        key={position.id}
                        className="relative"
                        onDragOver={(e) => {
                          e.preventDefault()
                          e.dataTransfer.dropEffect = 'copy'
                          handleAutoScroll(e)
                        }}
                        onDrop={(e) => {
                          e.preventDefault()
                          stopAutoScroll()
                          const tagId = e.dataTransfer.getData('text/plain')
                          if (tagId && position.id) {
                            handleTagDrop(position.id, tagId)
                          }
                        }}
                        onDragLeave={stopAutoScroll}
                      >
                        <div
                          className="border-2 border-transparent hover:border-gray-300 transition-all duration-200 rounded-lg p-1"
                          onDragEnter={(e) => {
                            e.currentTarget.style.borderColor = '#3B82F6'
                            e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.05)'
                          }}
                          onDragLeave={(e) => {
                            e.currentTarget.style.borderColor = 'transparent'
                            e.currentTarget.style.backgroundColor = 'transparent'
                          }}
                        >
                          <OrganizePositionCard position={position} onRemoveTag={handleRemoveTag} />
                        </div>
                      </div>
                    )}
                    emptyMessage="No short positions"
                  />
                </div>

                {/* Private Investments */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                      theme === 'dark' ? 'text-white' : 'text-gray-900'
                    }`}>
                      Private Investments
                    </h3>
                    <Badge variant="secondary" className={`transition-colors duration-300 ${
                      theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {filteredPrivate.length}
                    </Badge>
                  </div>
                  <PositionList
                    items={filteredPrivate}
                    renderItem={(position) => (
                      <div
                        key={position.id}
                        onDragOver={(e) => {
                          e.preventDefault()
                          handleAutoScroll(e)
                        }}
                        onDrop={(e) => {
                          e.preventDefault()
                          stopAutoScroll()
                          const tagId = e.dataTransfer.getData('text/plain')
                          if (tagId) handleTagDrop(position.id, tagId)
                        }}
                        onDragLeave={stopAutoScroll}
                      >
                        <OrganizePositionCard position={position} onRemoveTag={handleRemoveTag} />
                      </div>
                    )}
                    emptyMessage="No private investments"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Positions Grid - Row 2: Options Long/Short */}
          <section className="px-4 pb-8">
            <div className="container mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Long Options */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                      theme === 'dark' ? 'text-white' : 'text-gray-900'
                    }`}>
                      Long Options
                    </h3>
                    <Badge variant="secondary" className={`transition-colors duration-300 ${
                      theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {filteredOptionLongs.length}
                    </Badge>
                  </div>
                  <PositionList
                    items={filteredOptionLongs}
                    renderItem={(position) => (
                      <div
                        key={position.id}
                        onDragOver={(e) => {
                          e.preventDefault()
                          handleAutoScroll(e)
                        }}
                        onDrop={(e) => {
                          e.preventDefault()
                          stopAutoScroll()
                          const tagId = e.dataTransfer.getData('text/plain')
                          if (tagId) handleTagDrop(position.id, tagId)
                        }}
                        onDragLeave={stopAutoScroll}
                      >
                        <OrganizePositionCard position={position} onRemoveTag={handleRemoveTag} />
                      </div>
                    )}
                    emptyMessage="No long options"
                  />
                </div>

                {/* Short Options */}
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <h3 className={`text-lg font-semibold transition-colors duration-300 ${
                      theme === 'dark' ? 'text-white' : 'text-gray-900'
                    }`}>
                      Short Options
                    </h3>
                    <Badge variant="secondary" className={`transition-colors duration-300 ${
                      theme === 'dark' ? 'bg-slate-700 text-slate-300' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {filteredOptionShorts.length}
                    </Badge>
                  </div>
                  <PositionList
                    items={filteredOptionShorts}
                    renderItem={(position) => (
                      <div
                        key={position.id}
                        onDragOver={(e) => {
                          e.preventDefault()
                          handleAutoScroll(e)
                        }}
                        onDrop={(e) => {
                          e.preventDefault()
                          stopAutoScroll()
                          const tagId = e.dataTransfer.getData('text/plain')
                          if (tagId) handleTagDrop(position.id, tagId)
                        }}
                        onDragLeave={stopAutoScroll}
                      >
                        <OrganizePositionCard position={position} onRemoveTag={handleRemoveTag} />
                      </div>
                    )}
                    emptyMessage="No short options"
                  />
                </div>

                {/* Empty column for layout */}
                <div></div>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
