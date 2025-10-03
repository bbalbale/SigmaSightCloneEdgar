import { apiClient } from './apiClient';
import { API_ENDPOINTS, REQUEST_CONFIGS } from '@/config/api';
import type {
  TagItem,
  UpdateTagRequest,
  BatchTagUpdate,
} from '@/types/strategies';

export class TagsApi {
  async list(includeArchived = false): Promise<TagItem[]> {
    const url = `${API_ENDPOINTS.TAGS.LIST}?include_archived=${includeArchived}`;
    const resp = await apiClient.get(url, REQUEST_CONFIGS.STANDARD);
    return (resp.tags as TagItem[]) || [];
  }

  async create(name: string, color = '#4A90E2', description?: string): Promise<TagItem> {
    const resp = await apiClient.post(API_ENDPOINTS.TAGS.CREATE, { name, color, description }, REQUEST_CONFIGS.STANDARD);
    return resp.data as TagItem;
  }

  async get(tagId: string): Promise<TagItem> {
    const url = API_ENDPOINTS.TAGS.GET(tagId);
    const resp = await apiClient.get(url, REQUEST_CONFIGS.STANDARD);
    return resp.data as TagItem;
  }

  async update(tagId: string, request: UpdateTagRequest): Promise<TagItem> {
    const url = API_ENDPOINTS.TAGS.UPDATE(tagId);
    const resp = await apiClient.patch(url, request, REQUEST_CONFIGS.STANDARD);
    return resp.data as TagItem;
  }

  async delete(tagId: string): Promise<void> {
    const url = API_ENDPOINTS.TAGS.ARCHIVE(tagId);
    await apiClient.post(url, {}, REQUEST_CONFIGS.STANDARD);
  }

  async restore(tagId: string): Promise<TagItem> {
    const url = API_ENDPOINTS.TAGS.RESTORE(tagId);
    const resp = await apiClient.post(url, {}, REQUEST_CONFIGS.STANDARD);
    return resp.data as TagItem;
  }

  async getStrategies(tagId: string): Promise<Array<{ id: string; name: string; strategy_type: string }>> {
    const url = API_ENDPOINTS.TAGS.STRATEGIES_BY_TAG(tagId);
    const resp = await apiClient.get(url, REQUEST_CONFIGS.STANDARD);
    return (resp.data?.strategies || []) as Array<{ id: string; name: string; strategy_type: string }>;
  }

  async defaults(): Promise<TagItem[]> {
    const resp = await apiClient.post(API_ENDPOINTS.TAGS.DEFAULTS, {}, REQUEST_CONFIGS.STANDARD);
    return (resp.data?.tags || []) as TagItem[];
  }

  async reorder(tagIds: string[]): Promise<void> {
    await apiClient.post('/api/v1/tags/reorder', { tag_ids: tagIds }, REQUEST_CONFIGS.STANDARD);
  }

  async batchUpdate(updates: BatchTagUpdate[]): Promise<TagItem[]> {
    const resp = await apiClient.post('/api/v1/tags/batch-update', { updates }, REQUEST_CONFIGS.STANDARD);
    return (resp.data?.tags || []) as TagItem[];
  }

  // ===== Position Tagging Methods (New System) =====

  /**
   * Get all tags assigned to a position
   */
  async getPositionTags(positionId: string): Promise<TagItem[]> {
    const url = API_ENDPOINTS.POSITION_TAGS.GET(positionId);
    const resp = await apiClient.get(url, REQUEST_CONFIGS.STANDARD);
    return (Array.isArray(resp.data) ? resp.data : []) as TagItem[];
  }

  /**
   * Add tags to a position
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to add
   * @param replaceExisting - If true, replace all existing tags. If false, add to existing tags
   */
  async addPositionTags(positionId: string, tagIds: string[], replaceExisting = false): Promise<void> {
    const url = API_ENDPOINTS.POSITION_TAGS.ADD(positionId);
    await apiClient.post(url, { tag_ids: tagIds, replace_existing: replaceExisting }, REQUEST_CONFIGS.STANDARD);
  }

  /**
   * Remove tags from a position
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to remove
   */
  async removePositionTags(positionId: string, tagIds: string[]): Promise<void> {
    const url = API_ENDPOINTS.POSITION_TAGS.REMOVE(positionId);
    // Send as query parameters for DELETE request
    const queryParams = tagIds.map(id => `tag_ids=${id}`).join('&');
    await apiClient.delete(`${url}?${queryParams}`, REQUEST_CONFIGS.STANDARD);
  }

  /**
   * Replace all tags for a position (convenience method)
   * @param positionId - Position ID
   * @param tagIds - Array of tag IDs to set (replaces all existing tags)
   */
  async replacePositionTags(positionId: string, tagIds: string[]): Promise<void> {
    const url = API_ENDPOINTS.POSITION_TAGS.REPLACE(positionId);
    await apiClient.patch(url, { tag_ids: tagIds }, REQUEST_CONFIGS.STANDARD);
  }

  /**
   * Get all positions with a specific tag
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
    const url = API_ENDPOINTS.TAGS.POSITIONS_BY_TAG(tagId);
    const resp = await apiClient.get(url, REQUEST_CONFIGS.STANDARD);
    return (resp.data?.positions || []) as Array<{
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

