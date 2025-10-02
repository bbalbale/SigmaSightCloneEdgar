import { API_ENDPOINTS } from '@/config/api';
import { requestManager } from './requestManager';
import type {
  StrategyListItem,
  StrategyDetail,
  CreateStrategyRequest,
  UpdateStrategyRequest,
  CombineStrategyRequest,
  ListStrategiesResponse,
  StrategyDetection,
} from '@/types/strategies';

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
  }): Promise<ListStrategiesResponse> {
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

  async create(request: CreateStrategyRequest): Promise<StrategyDetail> {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.CREATE}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      timeout: 10000
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
    return resp.json();
  }

  async get(strategyId: string): Promise<StrategyDetail> {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.GET(strategyId)}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'GET', timeout: 10000 });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
    return resp.json();
  }

  async update(strategyId: string, request: UpdateStrategyRequest): Promise<StrategyDetail> {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.UPDATE(strategyId)}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      timeout: 10000
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
    return resp.json();
  }

  async delete(strategyId: string): Promise<void> {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.DELETE(strategyId)}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'DELETE', timeout: 10000 });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
  }

  async addPositions(strategyId: string, positionIds: string[]): Promise<StrategyDetail> {
    const url = `/api/proxy/api/v1/strategies/${strategyId}/positions`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position_ids: positionIds }),
      timeout: 10000
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
    return resp.json();
  }

  async removePositions(strategyId: string, positionIds: string[]): Promise<StrategyDetail> {
    const url = `/api/proxy/api/v1/strategies/${strategyId}/positions`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position_ids: positionIds }),
      timeout: 10000
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
    return resp.json();
  }

  async combine(request: CombineStrategyRequest): Promise<StrategyDetail> {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.COMBINE}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      timeout: 10000
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
    return resp.json();
  }

  async detect(portfolioId: string): Promise<StrategyDetection[]> {
    const url = `/api/proxy${API_ENDPOINTS.STRATEGIES.DETECT(portfolioId)}`;
    const token = localStorage.getItem('access_token') || '';
    const resp = await requestManager.authenticatedFetch(url, token, { method: 'GET', timeout: 10000 });
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
    return resp.json();
  }
}

export default new StrategiesApi();
