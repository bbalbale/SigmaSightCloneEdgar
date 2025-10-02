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
    return (resp.data?.tags as TagItem[]) || [];
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
    await apiClient.delete(url, REQUEST_CONFIGS.STANDARD);
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
}

export default new TagsApi();

