import { useState, useEffect, useCallback, useRef } from 'react';
import equitySearchApi, {
  EquitySearchParams,
  EquitySearchItem,
  EquitySearchResponse,
  EquitySearchFiltersResponse,
  PeriodType,
  SortOrder,
} from '@/services/equitySearchApi';

export interface UseEquitySearchOptions {
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
  pageSize?: number;
}

export interface UseEquitySearchResult {
  data: EquitySearchItem[];
  loading: boolean;
  error: string | null;
  totalCount: number;
  hasMore: boolean;
  metricsDate: string | null;
  loadMore: () => void;
  refresh: () => void;
}

/**
 * Custom hook for equity search functionality
 *
 * Provides debounced search, pagination, and state management
 * for the equity search page.
 *
 * @param options - Search options
 * @returns Search state and actions
 *
 * @example
 * ```tsx
 * const { data, loading, loadMore, hasMore } = useEquitySearch({
 *   query: 'tech',
 *   sort_by: 'market_cap',
 *   sort_order: 'desc',
 * });
 * ```
 */
export function useEquitySearch(options: UseEquitySearchOptions): UseEquitySearchResult {
  const [data, setData] = useState<EquitySearchItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [metricsDate, setMetricsDate] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  const pageSize = options.pageSize || 50;
  const hasMore = data.length < totalCount;

  // Track if this is the initial load
  const isInitialLoad = useRef(true);

  // Build search params from options
  const buildParams = useCallback(
    (currentOffset: number): EquitySearchParams => ({
      query: options.query,
      sectors: options.sectors,
      industries: options.industries,
      min_market_cap: options.min_market_cap,
      max_market_cap: options.max_market_cap,
      min_pe_ratio: options.min_pe_ratio,
      max_pe_ratio: options.max_pe_ratio,
      period: options.period,
      sort_by: options.sort_by,
      sort_order: options.sort_order,
      limit: pageSize,
      offset: currentOffset,
    }),
    [
      options.query,
      options.sectors,
      options.industries,
      options.min_market_cap,
      options.max_market_cap,
      options.min_pe_ratio,
      options.max_pe_ratio,
      options.period,
      options.sort_by,
      options.sort_order,
      pageSize,
    ]
  );

  // Fetch data from API
  const fetchData = useCallback(
    async (isLoadMore: boolean = false) => {
      setLoading(true);
      setError(null);

      const currentOffset = isLoadMore ? offset : 0;

      try {
        const params = buildParams(currentOffset);
        const response = await equitySearchApi.search(params);

        if (isLoadMore) {
          setData((prev) => [...prev, ...response.items]);
        } else {
          setData(response.items);
        }

        setTotalCount(response.total_count);
        setMetricsDate(response.metrics_date);

        if (isLoadMore) {
          setOffset(currentOffset + response.items.length);
        } else {
          setOffset(response.items.length);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to search equities';
        setError(message);
        console.error('Equity search error:', err);
      } finally {
        setLoading(false);
      }
    },
    [buildParams, offset]
  );

  // Effect to fetch data when options change
  useEffect(() => {
    // Skip the initial load if we want to wait for explicit trigger
    // For now, we auto-fetch on mount and when options change
    fetchData(false);

    // Mark initial load complete
    isInitialLoad.current = false;
  }, [
    options.query,
    options.sectors,
    options.industries,
    options.min_market_cap,
    options.max_market_cap,
    options.min_pe_ratio,
    options.max_pe_ratio,
    options.period,
    options.sort_by,
    options.sort_order,
  ]);

  // Load more function for pagination
  const loadMore = useCallback(() => {
    if (!loading && hasMore) {
      fetchData(true);
    }
  }, [loading, hasMore, fetchData]);

  // Refresh function to reload from beginning
  const refresh = useCallback(() => {
    setOffset(0);
    fetchData(false);
  }, [fetchData]);

  return {
    data,
    loading,
    error,
    totalCount,
    hasMore,
    metricsDate,
    loadMore,
    refresh,
  };
}

/**
 * Custom hook for fetching filter options
 *
 * Fetches available sectors, industries, and market cap ranges
 * for the filter UI.
 *
 * @returns Filter options and loading state
 */
export function useEquitySearchFilters() {
  const [filters, setFilters] = useState<EquitySearchFiltersResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFilters = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await equitySearchApi.getFilterOptions();
        setFilters(response);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load filters';
        setError(message);
        console.error('Filter options error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchFilters();
  }, []);

  return { filters, loading, error };
}

export default useEquitySearch;
