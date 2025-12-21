'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useEquitySearch, useEquitySearchFilters } from '@/hooks/useEquitySearch';
import { EquitySearchTable } from '@/components/equity-search/EquitySearchTable';
import { EquitySearchFilters, EquityFilters } from '@/components/equity-search/EquitySearchFilters';
import { PeriodSelector } from '@/components/equity-search/PeriodSelector';
import { PeriodType, SortOrder } from '@/services/equitySearchApi';

// Debounce utility
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = React.useState(value);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function EquitySearchContainer() {
  // Search state
  const [searchInput, setSearchInput] = useState('');
  const debouncedSearch = useDebounce(searchInput, 300);

  // Filter state
  const [filters, setFilters] = useState<EquityFilters>({});

  // Period state
  const [period, setPeriod] = useState<PeriodType>('ttm');

  // Sort state
  const [sortConfig, setSortConfig] = useState<{ column: string; direction: SortOrder }>({
    column: 'market_cap',
    direction: 'desc',
  });

  // Fetch filter options
  const { filters: filterOptions, loading: filtersLoading } = useEquitySearchFilters();

  // Build search options
  const searchOptions = useMemo(
    () => ({
      query: debouncedSearch || undefined,
      sectors: filters.sectors,
      min_market_cap: filters.min_market_cap,
      max_market_cap: filters.max_market_cap,
      min_pe_ratio: filters.min_pe_ratio,
      max_pe_ratio: filters.max_pe_ratio,
      period,
      sort_by: sortConfig.column,
      sort_order: sortConfig.direction,
    }),
    [debouncedSearch, filters, period, sortConfig]
  );

  // Fetch search results
  const { data, loading, error, totalCount, hasMore, metricsDate, loadMore, refresh } =
    useEquitySearch(searchOptions);

  // Handle sort column click
  const handleSort = useCallback((column: string) => {
    setSortConfig((prev) => ({
      column,
      direction: prev.column === column && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  }, []);

  // Get period label for display
  const getPeriodLabel = (p: PeriodType): string => {
    const labels: Record<PeriodType, string> = {
      ttm: 'TTM',
      last_year: 'Last Year',
      forward: 'Forward',
      last_quarter: 'Last Quarter',
    };
    return labels[p];
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-primary)' }}>
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <h1
            className="text-2xl font-semibold mb-1"
            style={{ color: 'var(--color-accent)' }}
          >
            Equity Search
          </h1>
          <p className="text-sm text-muted-foreground">
            Search and analyze equities by fundamentals and factor exposures
          </p>
        </div>

        {/* Search Bar and Period Selector */}
        <div className="flex flex-col sm:flex-row gap-4 mb-4">
          <div className="relative flex-1 max-w-md">
            <Search
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground"
              size={18}
            />
            <Input
              type="text"
              placeholder="Search by ticker or company name..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-10"
              style={{
                backgroundColor: 'var(--bg-secondary)',
                borderColor: 'var(--border-primary)',
              }}
            />
          </div>
          <PeriodSelector
            value={period}
            onChange={setPeriod}
            disabled={loading}
          />
        </div>

        {/* Filters */}
        <EquitySearchFilters
          filters={filters}
          onFiltersChange={setFilters}
          filterOptions={filterOptions}
          loading={filtersLoading}
        />

        {/* Results Table */}
        <EquitySearchTable
          data={data}
          loading={loading}
          error={error}
          totalCount={totalCount}
          hasMore={hasMore}
          sortConfig={sortConfig}
          onSort={handleSort}
          onLoadMore={loadMore}
          periodLabel={getPeriodLabel(period)}
        />

        {/* Metrics Date Footer */}
        {metricsDate && (
          <div className="mt-4 text-xs text-muted-foreground text-center">
            Data as of {new Date(metricsDate).toLocaleDateString()}
          </div>
        )}
      </div>
    </div>
  );
}

export default EquitySearchContainer;
