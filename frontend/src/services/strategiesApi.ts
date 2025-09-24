import { API_ENDPOINTS } from '@/config/api';
import { requestManager } from './requestManager';

export interface StrategyListItem {
  id: string;
  name: string;
  type: string;
  is_synthetic: boolean;
  position_count?: number | null;
  tags?: { id: string; name: string; color: string }[] | null;
}

export class StrategiesApi {
  async listByPortfolio(options: {
    portfolioId: string;
    tagIds?: string[];
    tagMode?: 'any' | 'all';
    strategyType?: string;
    includePositions?: boolean;
    includeTags?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ strategies: StrategyListItem[]; total: number; limit: number; offset: number }>{
    const { portfolioId, tagIds, tagMode = 'any', strategyType, includePositions = false, includeTags = true, limit = 200, offset = 0 } = options;
    const params = new URLSearchParams();
    if (tagIds?.length) params.set('tag_ids', tagIds.join(','));
    if (tagMode) params.set('tag_mode', tagMode);
    if (strategyType) params.set('strategy_type', strategyType);
    params.set('include_positions', String(includePositions));
    params.set('include_tags', String(includeTags));
    params.set('limit', String(limit));
    params.set('offset', String(offset));

    const url = `/api/proxy${API_ENDPOINTS.PORTFOLIOS.STRATEGIES(portfolioId)}?${params.toString()}`;
    const token = localStorage.getItem('access_token') || '';
    const data = await requestManager.authenticatedFetch(url, token, { method: 'GET', timeout: 10000, dedupe: true })
      .then(async (r) => {
        if (!r.ok) {
          const text = await r.text().catch(() => '');
          throw new Error(`HTTP ${r.status}: ${text || r.statusText}`);
        }
        return r.json();
      });
    if (!data || !Array.isArray(data.strategies)) {
      return { strategies: [], total: 0, limit, offset };
    }
    return data as { strategies: StrategyListItem[]; total: number; limit: number; offset: number };
  }

  async getStrategyTags(strategyId: string) {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.TAGS.GET(strategyId)}`;
    const token = localStorage.getItem('access_token') || '';
    const data = await requestManager.authenticatedFetch(url, token, { method: 'GET', timeout: 10000 }).then(r => r.json());
    return data;
  }

  async replaceStrategyTags(strategyId: string, tagIds: string[]) {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.TAGS.REPLACE(strategyId)}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tag_ids: tagIds }), timeout: 10000 });
    return resp.json();
  }

  async addStrategyTags(strategyId: string, tagIds: string[]) {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.TAGS.ADD(strategyId)}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tag_ids: tagIds }), timeout: 10000 });
    return resp.json();
  }

  async removeStrategyTags(strategyId: string, tagIds: string[]) {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.TAGS.REMOVE(strategyId)}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tag_ids: tagIds }), timeout: 10000 });
    return resp.json();
  }
}

export default new StrategiesApi();
