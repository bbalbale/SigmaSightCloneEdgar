'use client'

import { useState, useEffect, useCallback } from 'react'
import tagsApi from '@/services/tagsApi'
import type { TagItem } from '@/types/strategies'

interface UseTagsOptions {
  includeArchived?: boolean
  autoRefresh?: boolean
}

interface UseTagsReturn {
  tags: TagItem[]
  loading: boolean
  error: Error | null
  refresh: () => Promise<void>
  createTag: (name: string, color?: string) => Promise<TagItem>
  updateTag: (tagId: string, updates: Partial<TagItem>) => Promise<void>
  deleteTag: (tagId: string) => Promise<void>
  archiveTag: (tagId: string) => Promise<void>
}

export function useTags(options: UseTagsOptions = {}): UseTagsReturn {
  const { includeArchived = false, autoRefresh = true } = options

  const [tags, setTags] = useState<TagItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchTags = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        throw new Error('Not authenticated')
      }

      const fetchedTags = await tagsApi.list(includeArchived)
      setTags(fetchedTags || [])
    } catch (err) {
      console.error('Failed to fetch tags:', err)
      setError(err instanceof Error ? err : new Error('Failed to fetch tags'))
      setTags([])
    } finally {
      setLoading(false)
    }
  }, [includeArchived])

  // Fetch tags on mount and when dependencies change
  useEffect(() => {
    if (autoRefresh) {
      fetchTags()
    }
  }, [fetchTags, autoRefresh])

  // Create a new tag
  const createTag = useCallback(async (name: string, color: string = '#4A90E2'): Promise<TagItem> => {
    try {
      const newTag = await tagsApi.create(name, color)
      // Refresh tags list to include the new tag
      await fetchTags()
      return newTag
    } catch (err) {
      console.error('Failed to create tag:', err)
      throw err
    }
  }, [fetchTags])

  // Update an existing tag (placeholder - API doesn't have update endpoint yet)
  const updateTag = useCallback(async (tagId: string, updates: Partial<TagItem>) => {
    try {
      // TODO: Call update API when available
      // For now, just update local state optimistically
      setTags(prev => prev.map(tag =>
        tag.id === tagId ? { ...tag, ...updates } : tag
      ))

      // Would normally call:
      // await tagsApi.update(tagId, updates)
      // await fetchTags()
    } catch (err) {
      console.error('Failed to update tag:', err)
      throw err
    }
  }, [])

  // Delete a tag
  const deleteTag = useCallback(async (tagId: string) => {
    try {
      await tagsApi.delete(tagId)
      // Refresh tags list after deletion
      await fetchTags()
    } catch (err) {
      console.error('Failed to delete tag:', err)
      throw err
    }
  }, [fetchTags])

  // Archive a tag (soft delete)
  const archiveTag = useCallback(async (tagId: string) => {
    try {
      // Update tag to be archived
      await updateTag(tagId, { is_archived: true })

      // If not including archived tags, remove from list
      if (!includeArchived) {
        setTags(prev => prev.filter(tag => tag.id !== tagId))
      }
    } catch (err) {
      console.error('Failed to archive tag:', err)
      throw err
    }
  }, [updateTag, includeArchived])

  return {
    tags,
    loading,
    error,
    refresh: fetchTags,
    createTag,
    updateTag,
    deleteTag,
    archiveTag
  }
}

// Helper hook for tag statistics and utilities
export function useTagUtils(tags: TagItem[]) {
  const activeTags = tags.filter(t => !t.is_archived)
  const archivedTags = tags.filter(t => t.is_archived)

  // Group tags by color
  const tagsByColor = tags.reduce((acc, tag) => {
    const color = tag.color || '#4A90E2'
    if (!acc[color]) {
      acc[color] = []
    }
    acc[color].push(tag)
    return acc
  }, {} as Record<string, TagItem[]>)

  // Find tag by name (case-insensitive)
  const findTagByName = (name: string) => {
    return tags.find(t => t.name.toLowerCase() === name.toLowerCase())
  }

  // Check if tag name exists (for validation)
  const tagNameExists = (name: string, excludeId?: string) => {
    return tags.some(t =>
      t.name.toLowerCase() === name.toLowerCase() &&
      t.id !== excludeId
    )
  }

  // Generate a unique color that's not heavily used
  const suggestColor = () => {
    const defaultColors = [
      '#4A90E2', // Blue
      '#50C878', // Green
      '#FFB347', // Orange
      '#FF6B6B', // Red
      '#9B59B6', // Purple
      '#F39C12', // Yellow
      '#1ABC9C', // Teal
      '#E74C3C', // Dark Red
      '#3498DB', // Light Blue
      '#2ECC71'  // Light Green
    ]

    // Find the least used color
    const colorCounts = defaultColors.map(color => ({
      color,
      count: tagsByColor[color]?.length || 0
    }))

    colorCounts.sort((a, b) => a.count - b.count)
    return colorCounts[0].color
  }

  return {
    totalTags: tags.length,
    activeTags: activeTags.length,
    archivedTags: archivedTags.length,
    tagsByColor,
    findTagByName,
    tagNameExists,
    suggestColor
  }
}