'use client';

import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { EquitySearchFiltersResponse, MarketCapRange } from '@/services/equitySearchApi';

export interface EquityFilters {
  sectors?: string[];
  min_market_cap?: number;
  max_market_cap?: number;
  min_pe_ratio?: number;
  max_pe_ratio?: number;
}

interface EquitySearchFiltersProps {
  filters: EquityFilters;
  onFiltersChange: (filters: EquityFilters) => void;
  filterOptions: EquitySearchFiltersResponse | null;
  loading?: boolean;
}

const defaultMarketCapRanges: MarketCapRange[] = [
  { label: 'Mega Cap (>$200B)', min_value: 200_000_000_000, max_value: null },
  { label: 'Large Cap ($10B-$200B)', min_value: 10_000_000_000, max_value: 200_000_000_000 },
  { label: 'Mid Cap ($2B-$10B)', min_value: 2_000_000_000, max_value: 10_000_000_000 },
  { label: 'Small Cap ($300M-$2B)', min_value: 300_000_000, max_value: 2_000_000_000 },
  { label: 'Micro Cap (<$300M)', min_value: null, max_value: 300_000_000 },
];

export function EquitySearchFilters({
  filters,
  onFiltersChange,
  filterOptions,
  loading,
}: EquitySearchFiltersProps) {
  const sectors = filterOptions?.sectors || [];
  const marketCapRanges = filterOptions?.market_cap_ranges || defaultMarketCapRanges;

  const handleSectorChange = (sector: string) => {
    if (sector === 'all') {
      onFiltersChange({ ...filters, sectors: undefined });
    } else {
      onFiltersChange({ ...filters, sectors: [sector] });
    }
  };

  const handleMarketCapChange = (rangeIndex: string) => {
    if (rangeIndex === 'all') {
      onFiltersChange({
        ...filters,
        min_market_cap: undefined,
        max_market_cap: undefined,
      });
    } else {
      const range = marketCapRanges[parseInt(rangeIndex)];
      onFiltersChange({
        ...filters,
        min_market_cap: range.min_value || undefined,
        max_market_cap: range.max_value || undefined,
      });
    }
  };

  const clearFilters = () => {
    onFiltersChange({});
  };

  const hasActiveFilters =
    filters.sectors?.length ||
    filters.min_market_cap !== undefined ||
    filters.max_market_cap !== undefined ||
    filters.min_pe_ratio !== undefined ||
    filters.max_pe_ratio !== undefined;

  // Find current market cap selection
  const currentMarketCapIndex = marketCapRanges.findIndex(
    (range) =>
      range.min_value === filters.min_market_cap && range.max_value === filters.max_market_cap
  );

  return (
    <div
      className="flex flex-wrap items-center gap-3 p-4 rounded-lg mb-4"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-primary)',
        border: '1px solid var(--border-primary)',
      }}
    >
      {/* Sector Filter */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Sector:</span>
        <Select
          value={filters.sectors?.[0] || 'all'}
          onValueChange={handleSectorChange}
          disabled={loading}
        >
          <SelectTrigger
            className="w-[160px]"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              borderColor: 'var(--border-primary)',
            }}
          >
            <SelectValue placeholder="All Sectors" />
          </SelectTrigger>
          <SelectContent
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border-primary)',
            }}
          >
            <SelectItem value="all">All Sectors</SelectItem>
            {sectors.map((sector) => (
              <SelectItem key={sector} value={sector}>
                {sector}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Market Cap Filter */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Market Cap:</span>
        <Select
          value={currentMarketCapIndex >= 0 ? String(currentMarketCapIndex) : 'all'}
          onValueChange={handleMarketCapChange}
          disabled={loading}
        >
          <SelectTrigger
            className="w-[180px]"
            style={{
              backgroundColor: 'var(--bg-tertiary)',
              borderColor: 'var(--border-primary)',
            }}
          >
            <SelectValue placeholder="All Sizes" />
          </SelectTrigger>
          <SelectContent
            style={{
              backgroundColor: 'var(--bg-secondary)',
              borderColor: 'var(--border-primary)',
            }}
          >
            <SelectItem value="all">All Sizes</SelectItem>
            {marketCapRanges.map((range, index) => (
              <SelectItem key={index} value={String(index)}>
                {range.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Clear Filters Button */}
      {hasActiveFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={clearFilters}
          className="ml-auto"
        >
          <X className="h-4 w-4 mr-1" />
          Clear Filters
        </Button>
      )}
    </div>
  );
}

export default EquitySearchFilters;
