/**
 * Data transformation utilities
 * Converts backend portfolio data to frontend-compatible formats
 */

import { format } from 'date-fns';
import type {
  PortfolioReport,
  PortfolioSummaryMetric,
  PositionTableRow,
  Position,
  MarketQuote,
  HistoricalPrice,
} from '@/types/portfolio';

/**
 * Transform backend portfolio report to UI summary metrics
 */
export function transformToSummaryMetrics(
  portfolioReport: PortfolioReport
): PortfolioSummaryMetric[] {
  const { calculation_engines } = portfolioReport;
  
  const metrics: PortfolioSummaryMetric[] = [];

  // Portfolio Snapshot Metrics
  if (calculation_engines.portfolio_snapshot.available && calculation_engines.portfolio_snapshot.data) {
    const snapshot = calculation_engines.portfolio_snapshot.data;
    
    metrics.push({
      title: 'Total Value',
      value: formatCurrency(snapshot.total_value),
      subValue: `as of ${formatDate(snapshot.date)}`,
      description: 'Current total portfolio market value',
      positive: true,
      loading: false,
    });

    if (snapshot.daily_pnl && snapshot.daily_pnl !== '0.000000') {
      metrics.push({
        title: 'Daily P&L',
        value: formatCurrency(snapshot.daily_pnl),
        subValue: `${formatPercentage(snapshot.daily_return)} daily return`,
        description: 'Profit/Loss for the current trading day',
        positive: parseFloat(snapshot.daily_pnl) >= 0,
        loading: false,
      });
    }
  }

  // Position Exposures
  if (calculation_engines.position_exposures.available && calculation_engines.position_exposures.data) {
    const exposures = calculation_engines.position_exposures.data;
    
    metrics.push({
      title: 'Long Exposure',
      value: formatCurrency(exposures.long_exposure),
      subValue: `${exposures.long_count} long positions`,
      description: 'Total exposure in long positions',
      positive: true,
      loading: false,
    });

    metrics.push({
      title: 'Gross Exposure',
      value: formatCurrency(exposures.gross_exposure),
      subValue: `${exposures.gross_exposure !== exposures.net_exposure ? 'Net: ' + formatCurrency(exposures.net_exposure) : ''}`,
      description: 'Total absolute exposure (long + short)',
      positive: true,
      loading: false,
    });

    if (parseFloat(exposures.short_exposure) > 0) {
      metrics.push({
        title: 'Short Exposure',
        value: formatCurrency(exposures.short_exposure),
        subValue: `${exposures.short_count} short positions`,
        description: 'Total exposure in short positions',
        positive: false,
        loading: false,
      });
    }
  }

  // Greeks Aggregation
  if (calculation_engines.greeks_aggregation.available && calculation_engines.greeks_aggregation.data) {
    const greeks = calculation_engines.greeks_aggregation.data;
    
    if (parseFloat(greeks.delta) !== 0) {
      metrics.push({
        title: 'Portfolio Delta',
        value: formatNumber(greeks.delta),
        subValue: `${greeks.metadata.positions_with_greeks} positions with Greeks`,
        description: 'Sensitivity to underlying price changes',
        positive: parseFloat(greeks.delta) >= 0,
        loading: false,
      });
    }
  }

  // If no metrics available, show loading states
  if (metrics.length === 0) {
    return [
      {
        title: 'Total Value',
        value: 'Calculating...',
        subValue: 'Loading portfolio data',
        description: 'Current total portfolio market value',
        positive: true,
        loading: true,
      },
      {
        title: 'Exposures',
        value: 'Calculating...',
        subValue: 'Analyzing positions',
        description: 'Portfolio exposure analysis',
        positive: true,
        loading: true,
      },
    ];
  }

  return metrics;
}

/**
 * Transform positions to table rows for UI display
 */
export function transformPositionsToTableRows(
  positions: Position[],
  quotes?: MarketQuote[]
): { longPositions: PositionTableRow[]; shortPositions: PositionTableRow[] } {
  const quoteMap = new Map(quotes?.map(q => [q.symbol, q]) || []);
  
  const longPositions: PositionTableRow[] = [];
  const shortPositions: PositionTableRow[] = [];

  positions.forEach(position => {
    const quote = quoteMap.get(position.symbol);
    const currentPrice = position.current_price || quote?.price || 0;
    const marketValue = position.market_value || (position.quantity * currentPrice);
    const pnl = position.unrealized_pnl || 0;
    const percentChange = position.percent_change || quote?.change_percent || 0;

    const tableRow: PositionTableRow = {
      symbol: position.symbol,
      quantity: position.quantity,
      price: currentPrice,
      marketValue,
      pnl,
      percentChange,
      positive: pnl >= 0,
    };

    if (position.position_type === 'short' || position.quantity < 0) {
      shortPositions.push(tableRow);
    } else {
      longPositions.push(tableRow);
    }
  });

  // Sort by market value (descending)
  longPositions.sort((a, b) => b.marketValue - a.marketValue);
  shortPositions.sort((a, b) => Math.abs(b.marketValue) - Math.abs(a.marketValue));

  return { longPositions, shortPositions };
}

/**
 * Calculate portfolio summary statistics
 */
export function calculatePortfolioStats(positions: Position[]) {
  const stats = {
    totalPositions: positions.length,
    longCount: 0,
    shortCount: 0,
    optionsCount: 0,
    stockCount: 0,
    totalValue: 0,
    totalPnL: 0,
  };

  positions.forEach(position => {
    const marketValue = position.market_value || 0;
    const pnl = position.unrealized_pnl || 0;

    stats.totalValue += marketValue;
    stats.totalPnL += pnl;

    if (position.position_type === 'option') {
      stats.optionsCount++;
    } else {
      stats.stockCount++;
    }

    if (position.position_type === 'short' || position.quantity < 0) {
      stats.shortCount++;
    } else {
      stats.longCount++;
    }
  });

  return stats;
}

/**
 * Validate and clean portfolio data
 */
export function validatePortfolioData(data: any): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check required fields
  if (!data?.metadata?.portfolio_id) {
    errors.push('Missing portfolio ID');
  }

  if (!data?.portfolio_info?.name) {
    warnings.push('Missing portfolio name');
  }

  // Check calculation engines availability
  const engines = data?.calculation_engines;
  if (!engines) {
    errors.push('Missing calculation engines data');
  } else {
    if (!engines.portfolio_snapshot?.available) {
      warnings.push('Portfolio snapshot data unavailable');
    }
    
    if (!engines.position_exposures?.available) {
      warnings.push('Position exposures data unavailable');
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Format currency values for display
 */
export function formatCurrency(
  value: string | number,
  options: { compact?: boolean; showCents?: boolean } = {}
): string {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) {
    return '$0.00';
  }

  const { compact = false, showCents = true } = options;

  if (compact && Math.abs(numValue) >= 1000000) {
    return `$${(numValue / 1000000).toFixed(1)}M`;
  } else if (compact && Math.abs(numValue) >= 1000) {
    return `$${(numValue / 1000).toFixed(1)}K`;
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: showCents ? 2 : 0,
    maximumFractionDigits: showCents ? 2 : 0,
  }).format(numValue);
}

/**
 * Format percentage values for display
 */
export function formatPercentage(
  value: string | number,
  options: { decimals?: number; showSign?: boolean } = {}
): string {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) {
    return '0.00%';
  }

  const { decimals = 2, showSign = true } = options;
  const percentage = numValue * 100; // Convert decimal to percentage
  
  const formatted = percentage.toFixed(decimals);
  const sign = showSign && percentage > 0 ? '+' : '';
  
  return `${sign}${formatted}%`;
}

/**
 * Format numeric values for display
 */
export function formatNumber(
  value: string | number,
  options: { decimals?: number; compact?: boolean } = {}
): string {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) {
    return '0';
  }

  const { decimals = 2, compact = false } = options;

  if (compact && Math.abs(numValue) >= 1000000) {
    return `${(numValue / 1000000).toFixed(1)}M`;
  } else if (compact && Math.abs(numValue) >= 1000) {
    return `${(numValue / 1000).toFixed(1)}K`;
  }

  return numValue.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format date strings for display
 */
export function formatDate(
  dateString: string,
  formatString: string = 'MMM d, yyyy'
): string {
  try {
    const date = new Date(dateString);
    return format(date, formatString);
  } catch {
    return dateString; // Return original if parsing fails
  }
}

/**
 * Format date with relative time (e.g., "2 hours ago")
 */
export function formatRelativeDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return formatDate(dateString, 'MMM d');
  } catch {
    return dateString;
  }
}

/**
 * Safe string to number conversion
 */
export function safeParseFloat(value: string | number | null | undefined): number {
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? 0 : parsed;
  }
  return 0;
}

/**
 * Determine if a value represents a positive change/performance
 */
export function isPositiveValue(value: string | number): boolean {
  const numValue = safeParseFloat(value);
  return numValue >= 0;
}

/**
 * Generate color class based on positive/negative value
 */
export function getValueColorClass(value: string | number): string {
  return isPositiveValue(value) ? 'text-green-600' : 'text-red-600';
}

/**
 * Deep merge utility for configuration objects
 */
export function deepMerge<T extends Record<string, any>>(target: T, source: Partial<T>): T {
  const result = { ...target };
  
  for (const key in source) {
    if (source.hasOwnProperty(key)) {
      const sourceValue = source[key];
      if (sourceValue && typeof sourceValue === 'object' && !Array.isArray(sourceValue)) {
        result[key] = deepMerge(result[key] || {}, sourceValue);
      } else {
        result[key] = sourceValue as T[Extract<keyof T, string>];
      }
    }
  }
  
  return result;
}