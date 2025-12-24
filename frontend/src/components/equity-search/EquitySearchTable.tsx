'use client';

import React from 'react';
import { EquitySearchItem, SortOrder } from '@/services/equitySearchApi';
import { ChevronUp, ChevronDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

type SortColumn =
  | 'symbol'
  | 'company_name'
  | 'sector'
  | 'market_cap'
  | 'enterprise_value'
  | 'ps_ratio'
  | 'pe_ratio'
  | 'revenue'
  | 'ebit'
  | 'fcf'
  | 'factor_value'
  | 'factor_growth'
  | 'factor_momentum'
  | 'factor_quality'
  | 'factor_size'
  | 'factor_low_vol';

interface EquitySearchTableProps {
  data: EquitySearchItem[];
  loading: boolean;
  error: string | null;
  totalCount: number;
  hasMore: boolean;
  sortConfig: { column: string; direction: SortOrder };
  onSort: (column: SortColumn) => void;
  onLoadMore: () => void;
  periodLabel?: string;
}

// Format large numbers with abbreviations
function formatNumber(value: number | null, decimals: number = 1): string {
  if (value === null || value === undefined) return '-';

  const absValue = Math.abs(value);
  if (absValue >= 1_000_000_000_000) {
    return `$${(value / 1_000_000_000_000).toFixed(decimals)}T`;
  }
  if (absValue >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(decimals)}B`;
  }
  if (absValue >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(decimals)}M`;
  }
  if (absValue >= 1_000) {
    return `$${(value / 1_000).toFixed(decimals)}K`;
  }
  return `$${value.toFixed(decimals)}`;
}

// Format ratio (P/E, P/S)
function formatRatio(value: number | null): string {
  if (value === null || value === undefined) return '-';
  if (value < 0) return 'N/A';
  return value.toFixed(1) + 'x';
}

// Format factor beta
function formatFactor(value: number | null): string {
  if (value === null || value === undefined) return '-';
  const sign = value >= 0 ? '+' : '';
  return sign + value.toFixed(2);
}

export function EquitySearchTable({
  data,
  loading,
  error,
  totalCount,
  hasMore,
  sortConfig,
  onSort,
  onLoadMore,
  periodLabel,
}: EquitySearchTableProps) {
  // Sortable header component
  const SortableHeader = ({
    column,
    children,
    align = 'left',
  }: {
    column: SortColumn;
    children: React.ReactNode;
    align?: 'left' | 'right';
  }) => {
    const isActive = sortConfig.column === column;

    return (
      <th
        className={`px-3 py-2 text-xs font-semibold uppercase tracking-wider cursor-pointer hover:bg-opacity-80 transition-colors whitespace-nowrap ${
          align === 'right' ? 'text-right' : 'text-left'
        }`}
        style={{ color: 'var(--text-secondary)' }}
        onClick={() => onSort(column)}
      >
        <div
          className={`flex items-center gap-1 ${
            align === 'right' ? 'justify-end' : 'justify-start'
          }`}
        >
          <span>{children}</span>
          {isActive && (
            <span className="ml-1">
              {sortConfig.direction === 'desc' ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronUp className="w-3 h-3" />
              )}
            </span>
          )}
        </div>
      </th>
    );
  };

  // Loading state
  if (loading && data.length === 0) {
    return (
      <div
        className="flex items-center justify-center p-12 rounded-lg"
        style={{ backgroundColor: 'var(--bg-secondary)' }}
      >
        <Loader2 className="w-6 h-6 animate-spin mr-2" />
        <span className="text-muted-foreground">Loading equities...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className="flex items-center justify-center p-12 rounded-lg"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--color-error)',
        }}
      >
        <span style={{ color: 'var(--color-error)' }}>{error}</span>
      </div>
    );
  }

  // Empty state
  if (data.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center p-12 rounded-lg"
        style={{ backgroundColor: 'var(--bg-secondary)' }}
      >
        <span className="text-muted-foreground mb-2">No equities found</span>
        <span className="text-xs text-muted-foreground">
          Try adjusting your search or filters
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Results count */}
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          Showing {data.length} of {totalCount.toLocaleString()} equities
        </span>
        {periodLabel && (
          <span className="text-xs text-muted-foreground">
            Fundamentals: {periodLabel}
          </span>
        )}
      </div>

      {/* Table */}
      <div
        className="rounded-lg overflow-hidden"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-primary)',
        }}
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead
              style={{
                backgroundColor: 'var(--bg-tertiary)',
                borderBottom: '1px solid var(--border-primary)',
              }}
            >
              <tr>
                <SortableHeader column="symbol">Symbol</SortableHeader>
                <SortableHeader column="sector">Sector</SortableHeader>
                <SortableHeader column="market_cap" align="right">
                  Market Cap
                </SortableHeader>
                <SortableHeader column="enterprise_value" align="right">
                  EV
                </SortableHeader>
                <SortableHeader column="pe_ratio" align="right">
                  P/E
                </SortableHeader>
                <SortableHeader column="ps_ratio" align="right">
                  P/S
                </SortableHeader>
                <SortableHeader column="revenue" align="right">
                  Revenue
                </SortableHeader>
                <SortableHeader column="ebit" align="right">
                  EBIT
                </SortableHeader>
                <SortableHeader column="fcf" align="right">
                  FCF
                </SortableHeader>
                <SortableHeader column="factor_momentum" align="right">
                  Mom
                </SortableHeader>
                <SortableHeader column="factor_value" align="right">
                  Val
                </SortableHeader>
                <SortableHeader column="factor_quality" align="right">
                  Qual
                </SortableHeader>
                <SortableHeader column="factor_growth" align="right">
                  Grwth
                </SortableHeader>
                <SortableHeader column="factor_size" align="right">
                  Size
                </SortableHeader>
                <SortableHeader column="factor_low_vol" align="right">
                  LowVol
                </SortableHeader>
              </tr>
            </thead>
            <tbody>
              {data.map((item, index) => (
                <tr
                  key={item.symbol}
                  style={{
                    borderBottom: '1px solid var(--border-primary)',
                    backgroundColor:
                      index % 2 === 0 ? 'transparent' : 'var(--bg-tertiary)',
                  }}
                  className="hover:bg-opacity-50 transition-colors"
                >
                  <td className="px-3 py-2">
                    <div className="flex flex-col">
                      <span className="font-medium" style={{ color: 'var(--color-accent)' }}>
                        {item.symbol}
                      </span>
                      <span className="text-xs text-muted-foreground truncate max-w-[150px]">
                        {item.company_name || '-'}
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-sm text-muted-foreground">
                    {item.sector || '-'}
                  </td>
                  <td className="px-3 py-2 text-sm text-right font-mono">
                    {formatNumber(item.market_cap)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right font-mono text-muted-foreground">
                    {formatNumber(item.enterprise_value)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right font-mono">
                    {formatRatio(item.pe_ratio)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right font-mono text-muted-foreground">
                    {formatRatio(item.ps_ratio)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right font-mono">
                    {formatNumber(item.revenue)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right font-mono text-muted-foreground">
                    {formatNumber(item.ebit)}
                  </td>
                  <td className="px-3 py-2 text-sm text-right font-mono">
                    {formatNumber(item.fcf)}
                  </td>
                  <td
                    className="px-3 py-2 text-sm text-right font-mono"
                    style={{
                      color:
                        item.factor_momentum !== null
                          ? item.factor_momentum > 0
                            ? 'var(--color-success)'
                            : item.factor_momentum < 0
                            ? 'var(--color-error)'
                            : 'var(--text-secondary)'
                          : 'var(--text-secondary)',
                    }}
                  >
                    {formatFactor(item.factor_momentum)}
                  </td>
                  <td
                    className="px-3 py-2 text-sm text-right font-mono"
                    style={{
                      color:
                        item.factor_value !== null
                          ? item.factor_value > 0
                            ? 'var(--color-success)'
                            : item.factor_value < 0
                            ? 'var(--color-error)'
                            : 'var(--text-secondary)'
                          : 'var(--text-secondary)',
                    }}
                  >
                    {formatFactor(item.factor_value)}
                  </td>
                  <td
                    className="px-3 py-2 text-sm text-right font-mono"
                    style={{
                      color:
                        item.factor_quality !== null
                          ? item.factor_quality > 0
                            ? 'var(--color-success)'
                            : item.factor_quality < 0
                            ? 'var(--color-error)'
                            : 'var(--text-secondary)'
                          : 'var(--text-secondary)',
                    }}
                  >
                    {formatFactor(item.factor_quality)}
                  </td>
                  <td
                    className="px-3 py-2 text-sm text-right font-mono"
                    style={{
                      color:
                        item.factor_growth !== null
                          ? item.factor_growth > 0
                            ? 'var(--color-success)'
                            : item.factor_growth < 0
                            ? 'var(--color-error)'
                            : 'var(--text-secondary)'
                          : 'var(--text-secondary)',
                    }}
                  >
                    {formatFactor(item.factor_growth)}
                  </td>
                  <td
                    className="px-3 py-2 text-sm text-right font-mono"
                    style={{
                      color:
                        item.factor_size !== null
                          ? item.factor_size > 0
                            ? 'var(--color-success)'
                            : item.factor_size < 0
                            ? 'var(--color-error)'
                            : 'var(--text-secondary)'
                          : 'var(--text-secondary)',
                    }}
                  >
                    {formatFactor(item.factor_size)}
                  </td>
                  <td
                    className="px-3 py-2 text-sm text-right font-mono"
                    style={{
                      color:
                        item.factor_low_vol !== null
                          ? item.factor_low_vol > 0
                            ? 'var(--color-success)'
                            : item.factor_low_vol < 0
                            ? 'var(--color-error)'
                            : 'var(--text-secondary)'
                          : 'var(--text-secondary)',
                    }}
                  >
                    {formatFactor(item.factor_low_vol)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Load More Button */}
      {hasMore && (
        <div className="flex justify-center pt-4">
          <Button
            variant="outline"
            onClick={onLoadMore}
            disabled={loading}
            style={{
              borderColor: 'var(--border-primary)',
            }}
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Loading...
              </>
            ) : (
              `Load More (${data.length} of ${totalCount.toLocaleString()})`
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

export default EquitySearchTable;
