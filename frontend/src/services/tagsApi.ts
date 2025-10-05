import { requestManager } from './requestManager';
import { authManager } from './authManager';
import { API_ENDPOINTS } from '@/config/api';
import type {
  TagItem,
  UpdateTagRequest,
  BatchTagUpdate,
} from '@/types/strategies';

/**
 * Tags API Service - Tag Management + Position Tagging
 *
 * This service handles TWO logical groups of operations (intentional design):
 *
 * 1. TAG MANAGEMENT (lines 16-62):
 *    - Create, read, update, delete tags
 *    - Archive/restore tags
 *    - Default tag creation
 *    - Backend: /api/v1/tags/ (tags.py)
 *
 * 2. POSITION TAGGING (lines 69-130):
 *    - Add/remove tags from positions
 *    - Get position's tags
 *    - Get positions by tag (reverse lookup)
 *    - Backend: /api/v1/positions/{id}/tags (position_tags.py)
 *
 * Architecture Context:
 * - This ONE service aligns with TWO backend routers (intentional 3-tier design)
 * - Backend separates concerns: tag management vs position-tag relationships
 * - Frontend combines them in one service for convenience
 *
 * Related Files:
 * - Backend: backend/app/api/v1/tags.py (tag management)
 * - Backend: backend/app/api/v1/position_tags.py (position tagging)
 * - Hook: src/hooks/useTags.ts (tag management)
 * - Hook: src/hooks/usePositionTags.ts (position tagging)
 * - Docs: backend/TAGGING_ARCHITECTURE.md
 */
export class TagsApi {
  // ===== TAG MANAGEMENT METHODS =====
  // Create, update, delete, and manage tags
  async list(includeArchived = false): Promise<TagItem[]> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.LIST}?include_archived=${includeArchived}`;
    const token = authManager.getAccessToken() || '';
    console.log('[TagsApi.list] Token exists:', !!token, 'Length:', token?.length);
    console.log('[TagsApi.list] Fetching:', url);
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'GET' });
    console.log('[TagsApi.list] Response status:', resp.status);
    const data = await resp.json();
    console.log('[TagsApi.list] Response data:', data);
    return (data.tags as TagItem[]) || [];
  }

  async create(name: string, color = '#4A90E2', description?: string): Promise<TagItem> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.CREATE}`;
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, color, description })
    });
    const data = await resp.json();
    return data.data as TagItem;
  }

  async get(tagId: string): Promise<TagItem> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.GET(tagId)}`;
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'GET' });
    const data = await resp.json();
    return data.data as TagItem;
  }

  async update(tagId: string, request: UpdateTagRequest): Promise<TagItem> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.UPDATE(tagId)}`;
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    const data = await resp.json();
    return data.data as TagItem;
  }

  async delete(tagId: string): Promise<void> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.ARCHIVE(tagId)}`;
    const token = authManager.getAccessToken() || '';
    await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
  }

  async restore(tagId: string): Promise<TagItem> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.RESTORE(tagId)}`;
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await resp.json();
    return data.data as TagItem;
  }

  async getStrategies(tagId: string): Promise<Array<{ id: string; name: string; strategy_type: string }>> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.STRATEGIES_BY_TAG(tagId)}`;
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'GET' });
    const data = await resp.json();
    return (data.data?.strategies || []) as Array<{ id: string; name: string; strategy_type: string }>;
  }

  async defaults(): Promise<TagItem[]> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.DEFAULTS}`;
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await resp.json();
    return (data.data?.tags || []) as TagItem[];
  }

  async reorder(tagIds: string[]): Promise<void> {
    const url = '/api/proxy/api/v1/tags/reorder';
    const token = authManager.getAccessToken() || '';
    await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag_ids: tagIds })
    });
  }

  async batchUpdate(updates: BatchTagUpdate[]): Promise<TagItem[]> {
    const url = '/api/proxy/api/v1/tags/batch-update';
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates })
    });
    const data = await resp.json();
    return (data.data?.tags || []) as TagItem[];
  }

  // ===== POSITION TAGGING METHODS (NEW SYSTEM - PREFERRED) =====
  // Add/remove tags from positions, get positions by tag

  /**
   * Get all tags assigned to a position
   * Backend: GET /api/v1/positions/{id}/tags (position_tags.py)
   */
  async getPositionTags(positionId: string): Promise<TagItem[]> {
    const url = `/api/proxy${API_ENDPOINTS.POSITION_TAGS.GET(positionId)}`;
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'GET' });
    const data = await resp.json();
    return (Array.isArray(data.data) ? data.data : []) as TagItem[];
  }

  /**
   * Add tags to a position
   * Backend: POST /api/v1/positions/{id}/tags (position_tags.py)
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to add
   * @param replaceExisting - If true, replace all existing tags. If false, add to existing tags
   */
  async addPositionTags(positionId: string, tagIds: string[], replaceExisting = false): Promise<void> {
    const url = `/api/proxy${API_ENDPOINTS.POSITION_TAGS.ADD(positionId)}`;
    const token = authManager.getAccessToken() || '';
    await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag_ids: tagIds, replace_existing: replaceExisting })
    });
  }

  /**
   * Remove tags from a position
   * Backend: POST /api/v1/positions/{id}/tags/remove (position_tags.py)
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to remove
   */
  async removePositionTags(positionId: string, tagIds: string[]): Promise<void> {
    const url = `/api/proxy${API_ENDPOINTS.POSITION_TAGS.REMOVE(positionId)}/remove`;
    const token = authManager.getAccessToken() || '';
    await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag_ids: tagIds })
    });
  }

  /**
   * Replace all tags for a position (convenience method)
   * Backend: PATCH /api/v1/positions/{id}/tags (position_tags.py)
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to set (replaces all existing tags)
   */
  async replacePositionTags(positionId: string, tagIds: string[]): Promise<void> {
    const url = `/api/proxy${API_ENDPOINTS.POSITION_TAGS.REPLACE(positionId)}`;
    const token = authManager.getAccessToken() || '';
    await requestManager.authenticatedFetch(url, token, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag_ids: tagIds })
    });
  }

  /**
   * Get all positions with a specific tag (REVERSE LOOKUP)
   * Backend: GET /api/v1/tags/{id}/positions (tags.py - tag-centric endpoint)
   * Note: This reverse lookup is in tags.py because it's tag-centric:
   *       "What positions have THIS tag?" vs "What tags does THIS position have?"
   * @param tagId - Tag ID
   * @returns Array of positions with this tag
   */
  async getPositionsByTag(tagId: string): Promise<Array<{
    id: string;
    symbol: string;
    position_type: string;
    quantity: number;
    portfolio_id: string;
    investment_class: string;
  }>> {
    const url = `/api/proxy${API_ENDPOINTS.TAGS.POSITIONS_BY_TAG(tagId)}`;
    const token = authManager.getAccessToken() || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'GET' });
    const data = await resp.json();
    return (data.data?.positions || []) as Array<{
      id: string;
      symbol: string;
      position_type: string;
      quantity: number;
      portfolio_id: string;
      investment_class: string;
    }>;
  }
}

export default new TagsApi();

