import { apiClient } from './apiClient';
import { authManager } from './authManager';
import { API_ENDPOINTS, REQUEST_CONFIGS } from '@/config/api';

/**
 * Equity Search API Service
 *
 * Provides search, filtering, and sorting capabilities for equities
 * across the entire symbol universe.
 *
 * Features:
 * - Full-text search on symbol and company name
 * - Filter by sector, industry, market cap range, P/E range
 * - Sort by any metric column (market cap, P/E, factors, etc.)
 * - Period selector for fundamental data (TTM, last year, forward, last quarter)
 *
 * Backend Implementation:
 * - File: backend/app/api/v1/equity_search.py
 * - Service: backend/app/services/equity_search_service.py
 * - Tables: symbol_daily_metrics, income_statements, cash_flows, balance_sheets
 */

// ===== TYPE DEFINITIONS =====

export type PeriodType = 'ttm' | 'last_year' | 'forward' | 'last_quarter';
export type SortOrder = 'asc' | 'desc';

export interface EquitySearchParams {
  query?: string;
  sectors?: string[];
  industries?: string[];
  min_market_cap?: number;
  max_market_cap?: number;
  min_pe_ratio?: number;
  max_pe_ratio?: number;
  period?: PeriodType;
  sort_by?: string;
  sort_order?: SortOrder;
  limit?: number;
  offset?: number;
}

export interface EquitySearchItem {
  symbol: string;
  company_name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  enterprise_value: number | null;
  ps_ratio: number | null;
  pe_ratio: number | null;
  revenue: number | null;
  ebit: number | null;
  fcf: number | null;
  period_label: string;
  factor_value: number | null;
  factor_growth: number | null;
  factor_momentum: number | null;
  factor_quality: number | null;
  factor_size: number | null;
  factor_low_vol: number | null;
}

export interface EquitySearchResponse {
  items: EquitySearchItem[];
  total_count: number;
  filters_applied: Record<string, unknown>;
  period: string;
  sort_by: string;
  sort_order: string;
  metrics_date: string | null;
}

export interface MarketCapRange {
  label: string;
  min_value: number | null;
  max_value: number | null;
}

export interface EquitySearchFiltersResponse {
  sectors: string[];
  industries: string[];
  market_cap_ranges: MarketCapRange[];
}

// ===== SERVICE CLASS =====

export class EquitySearchApi {
  private getAuthHeaders() {
    const token = authManager.getAccessToken();
    if (!token) {
      throw new Error('Not authenticated');
    }

    return {
      Authorization: `Bearer ${token}`,
    };
  }

  /**
   * Search equities with filters and sorting
   *
   * @param params - Search parameters
   * @returns Search results with pagination
   *
   * @example
   * ```typescript
   * // Search for tech stocks
   * const results = await equitySearchApi.search({
   *   query: 'AAPL',
   *   sectors: ['Technology'],
   *   sort_by: 'market_cap',
   *   sort_order: 'desc',
   * });
   * console.log(results.items[0].market_cap); // 3200000000000
   * ```
   */
  async search(params: EquitySearchParams = {}): Promise<EquitySearchResponse> {
    const queryParams = new URLSearchParams();

    if (params.query) {
      queryParams.set('query', params.query);
    }
    if (params.sectors?.length) {
      queryParams.set('sectors', params.sectors.join(','));
    }
    if (params.industries?.length) {
      queryParams.set('industries', params.industries.join(','));
    }
    if (params.min_market_cap !== undefined) {
      queryParams.set('min_market_cap', String(params.min_market_cap));
    }
    if (params.max_market_cap !== undefined) {
      queryParams.set('max_market_cap', String(params.max_market_cap));
    }
    if (params.min_pe_ratio !== undefined) {
      queryParams.set('min_pe_ratio', String(params.min_pe_ratio));
    }
    if (params.max_pe_ratio !== undefined) {
      queryParams.set('max_pe_ratio', String(params.max_pe_ratio));
    }
    if (params.period) {
      queryParams.set('period', params.period);
    }
    if (params.sort_by) {
      queryParams.set('sort_by', params.sort_by);
    }
    if (params.sort_order) {
      queryParams.set('sort_order', params.sort_order);
    }
    if (params.limit !== undefined) {
      queryParams.set('limit', String(params.limit));
    }
    if (params.offset !== undefined) {
      queryParams.set('offset', String(params.offset));
    }

    const queryString = queryParams.toString();
    const url = queryString
      ? `${API_ENDPOINTS.EQUITY_SEARCH.SEARCH}?${queryString}`
      : API_ENDPOINTS.EQUITY_SEARCH.SEARCH;

    const resp = await apiClient.get(url, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: this.getAuthHeaders(),
    });

    return resp as EquitySearchResponse;
  }

  /**
   * Get available filter options
   *
   * Returns sectors, industries, and market cap ranges for the filter UI.
   *
   * @returns Filter options
   *
   * @example
   * ```typescript
   * const filters = await equitySearchApi.getFilterOptions();
   * console.log(filters.sectors); // ['Technology', 'Healthcare', ...]
   * ```
   */
  async getFilterOptions(): Promise<EquitySearchFiltersResponse> {
    const resp = await apiClient.get(API_ENDPOINTS.EQUITY_SEARCH.FILTERS, {
      ...REQUEST_CONFIGS.STANDARD,
      headers: this.getAuthHeaders(),
    });

    return resp as EquitySearchFiltersResponse;
  }
}

// Export singleton instance
const equitySearchApi = new EquitySearchApi();
export default equitySearchApi;
