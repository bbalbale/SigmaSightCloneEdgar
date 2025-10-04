'use client'

import React, { useState } from 'react'
import { useTheme } from '@/contexts/ThemeContext'
import { usePortfolioData } from '@/hooks/usePortfolioData'
import { useTags } from '@/hooks/useTags'
import { usePositionTags } from '@/hooks/usePositionTags'
import { TagList } from '@/components/organize/TagList'
import { PositionList } from '@/components/common/PositionList'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'
import { Badge } from '@/components/ui/badge'

export function OrganizeContainer() {
  const { theme } = useTheme()

  // Auto-scroll state for drag-drop
  const [autoScrollInterval, setAutoScrollInterval] = useState<NodeJS.Timeout | null>(null)

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

  // Filter state
  const [selectedTagFilter, setSelectedTagFilter] = useState<string | null>(null)

  // Auto-scroll helper function
  const handleAutoScroll = React.useCallback((e: React.DragEvent) => {
    const SCROLL_THRESHOLD = 100 // pixels from edge to trigger scroll
    const SCROLL_SPEED = 10 // pixels per interval

    const { clientY } = e
    const viewportHeight = window.innerHeight

    // Clear any existing interval
    if (autoScrollInterval) {
      clearInterval(autoScrollInterval)
      setAutoScrollInterval(null)
    }

    // Check if near top edge
    if (clientY < SCROLL_THRESHOLD) {
      const interval = setInterval(() => {
        window.scrollBy(0, -SCROLL_SPEED)
      }, 20)
      setAutoScrollInterval(interval)
    }
    // Check if near bottom edge
    else if (clientY > viewportHeight - SCROLL_THRESHOLD) {
      const interval = setInterval(() => {
        window.scrollBy(0, SCROLL_SPEED)
      }, 20)
      setAutoScrollInterval(interval)
    }
  }, [autoScrollInterval])

  // Stop auto-scroll when drag ends or leaves
  const stopAutoScroll = React.useCallback(() => {
    if (autoScrollInterval) {
      clearInterval(autoScrollInterval)
      setAutoScrollInterval(null)
    }
  }, [autoScrollInterval])

  // Cleanup auto-scroll on unmount
  React.useEffect(() => {
    return () => {
      if (autoScrollInterval) {
        clearInterval(autoScrollInterval)
      }
    }
  }, [autoScrollInterval])

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
      </section>

      {/* Tag Management */}
      <section className="px-4 pb-6">
        <div className="container mx-auto">
          <TagList
            tags={tags}
            onCreate={handleCreateTag}
            onDelete={handleDeleteTag}
          />
        </div>
      </section>

      {/* Filter by Tag (Optional) */}
      {tags.length > 0 && (
        <section className="px-4 pb-4">
          <div className="container mx-auto">
            <div className="flex items-center gap-2">
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
