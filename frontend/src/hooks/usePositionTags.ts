/**
 * usePositionTags Hook
 *
 * React hook for managing position tags - provides functionality for:
 * - Fetching tags for positions
 * - Adding/removing tags from positions
 * - Filtering positions by tags
 * - Tag assignment state management
 */

import { useState, useCallback } from 'react';
import tagsApi from '@/services/tagsApi';
import type { TagItem } from '@/types/strategies';

interface UsePositionTagsReturn {
  // State
  loading: boolean;
  error: string | null;

  // Methods
  getPositionTags: (positionId: string) => Promise<TagItem[]>;
  addTagsToPosition: (positionId: string, tagIds: string[], replaceExisting?: boolean) => Promise<void>;
  removeTagsFromPosition: (positionId: string, tagIds: string[]) => Promise<void>;
  replacePositionTags: (positionId: string, tagIds: string[]) => Promise<void>;
  getPositionsByTag: (tagId: string) => Promise<Array<{
    id: string;
    symbol: string;
    position_type: string;
    quantity: number;
    portfolio_id: string;
    investment_class: string;
  }>>;
}

export function usePositionTags(): UsePositionTagsReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Get all tags assigned to a position
   */
  const getPositionTags = useCallback(async (positionId: string): Promise<TagItem[]> => {
    setLoading(true);
    setError(null);

    try {
      const tags = await tagsApi.getPositionTags(positionId);
      return tags;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch position tags';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Add tags to a position
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to add
   * @param replaceExisting - If true, replace all existing tags. If false, add to existing tags
   */
  const addTagsToPosition = useCallback(async (
    positionId: string,
    tagIds: string[],
    replaceExisting = false
  ): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      await tagsApi.addPositionTags(positionId, tagIds, replaceExisting);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add tags to position';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Remove tags from a position
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to remove
   */
  const removeTagsFromPosition = useCallback(async (
    positionId: string,
    tagIds: string[]
  ): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      await tagsApi.removePositionTags(positionId, tagIds);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to remove tags from position';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Replace all tags for a position
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to set (replaces all existing tags)
   */
  const replacePositionTags = useCallback(async (
    positionId: string,
    tagIds: string[]
  ): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      await tagsApi.replacePositionTags(positionId, tagIds);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to replace position tags';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Get all positions with a specific tag
   * @param tagId - Tag ID
   */
  const getPositionsByTag = useCallback(async (tagId: string) => {
    setLoading(true);
    setError(null);

    try {
      const positions = await tagsApi.getPositionsByTag(tagId);
      return positions;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch positions by tag';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    // State
    loading,
    error,

    // Methods
    getPositionTags,
    addTagsToPosition,
    removeTagsFromPosition,
    replacePositionTags,
    getPositionsByTag,
  };
}

export default usePositionTags;
