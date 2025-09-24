import { apiClient } from './apiClient';
import { API_ENDPOINTS, REQUEST_CONFIGS } from '@/config/api';

export interface TagItem {
  id: string;
  name: string;
  color: string;
  description?: string | null;
  is_archived?: boolean;
}

export class TagsApi {
  async list(includeArchived = false): Promise<TagItem[]> {
    const url = `${API_ENDPOINTS.TAGS.LIST}?include_archived=${includeArchived}`;
    const resp = await apiClient.get(url, REQUEST_CONFIGS.STANDARD);
    return (resp.data?.tags as TagItem[]) || [];
  }

  async create(name: string, color = '#4A90E2'): Promise<TagItem> {
    const resp = await apiClient.post(API_ENDPOINTS.TAGS.CREATE, { name, color }, REQUEST_CONFIGS.STANDARD);
    return resp.data as TagItem;
  }
}

export default new TagsApi();

