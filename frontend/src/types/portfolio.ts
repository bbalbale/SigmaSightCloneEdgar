/**
 * TypeScript interfaces for Portfolio API responses
 * Based on backend JSON structure from /backend/reports/demo-*-portfolio_2025-08-23/portfolio_report.json
 */

// Base Portfolio Information
export interface PortfolioInfo {
  id: string;
  name: string;
  created_at: string;
  position_count: number;
}

// Report Metadata
export interface PortfolioMetadata {
  portfolio_id: string;
  portfolio_name: string;
  report_date: string;
  anchor_date: string;
  generated_at: string;
  precision_policy: {
    monetary_values: string;
    greeks: string;
    correlations: string;
    factor_exposures: string;
  };
}

// Portfolio Snapshot Data
export interface PortfolioSnapshotData {
  date: string;
  net_asset_value?: string;
  total_value: string;
  daily_pnl: string;
  daily_return: string;
}

export interface PortfolioSnapshot {
  available: boolean;
  data: PortfolioSnapshotData | null;
  description: string;
}

// Position Exposures Data
export interface PositionExposuresMetadata {
  calculated_at: string;
  position_count: number;
  warnings: string[];
}

export interface PositionExposuresData {
  gross_exposure: string;
  net_exposure: string;
  long_exposure: string;
  short_exposure: string;
  long_count: number;
  short_count: number;
  options_exposure: string;
  stock_exposure: string;
  notional: string;
  metadata: PositionExposuresMetadata;
}

export interface PositionExposures {
  available: boolean;
  data: PositionExposuresData | null;
  description: string;
}

// Greeks Aggregation
export interface GreeksAggregationMetadata {
  calculated_at: string;
  positions_with_greeks: number;
  positions_without_greeks: number;
  warnings: string[];
}

export interface GreeksAggregationData {
  delta: string;
  gamma: string;
  theta: string;
  vega: string;
  rho: string;
  metadata: GreeksAggregationMetadata;
}

export interface GreeksAggregation {
  available: boolean;
  data: GreeksAggregationData | null;
  description: string;
}

// Factor Analysis
export interface FactorExposure {
  factor_name: string;
  category: string;
  exposure_value: string;
  exposure_dollar: string | null;
  calculation_date: string;
}

export interface FactorAnalysis {
  available: boolean;
  count: number;
  data: FactorExposure[] | null;
  description: string;
}

// Correlation Analysis
export interface CorrelationAnalysis {
  available: boolean;
  data: any | null; // Structure TBD when backend implements this
  description: string;
}

// Market Data
export interface MarketData {
  available: boolean;
  position_count: number;
  description: string;
}

// Stress Testing
export interface StressTesting {
  available: boolean;
  scenario_count: number;
  data: any | null; // Structure TBD when backend implements this
  description: string;
}

// Interest Rate Betas
export interface InterestRateBetas {
  available: boolean;
  data: any | null; // Structure TBD when backend implements this
  description: string;
}

// Calculation Engines Container
export interface CalculationEngines {
  portfolio_snapshot: PortfolioSnapshot;
  position_exposures: PositionExposures;
  greeks_aggregation: GreeksAggregation;
  factor_analysis: FactorAnalysis;
  correlation_analysis: CorrelationAnalysis;
  market_data: MarketData;
  stress_testing: StressTesting;
  interest_rate_betas: InterestRateBetas;
}

// Positions Summary
export interface PositionsSummary {
  count: number;
  long_count: number;
  short_count: number;
  options_count: number;
  stock_count: number;
}

// Main Portfolio Report Structure
export interface PortfolioReport {
  version: string;
  metadata: PortfolioMetadata;
  portfolio_info: PortfolioInfo;
  calculation_engines: CalculationEngines;
  positions_summary: PositionsSummary;
}

// Individual Position Data (from /api/v1/data/positions/details)
export interface Position {
  id: string;
  portfolio_id: string;
  symbol: string;
  quantity: number;
  position_type: 'long' | 'short' | 'option';
  current_price?: number;
  market_value?: number;
  cost_basis?: number;
  unrealized_pnl?: number;
  percent_change?: number;
  last_updated?: string;
}

// Portfolio List (from /api/v1/data/portfolios)
export interface PortfolioListItem {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  position_count: number;
  net_asset_value?: number;
  total_value?: number;
}

// Market Quote Data (from /api/v1/data/prices/quotes)
export interface MarketQuote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
  market_cap?: number;
  pe_ratio?: number;
}

// Historical Price Data (from /api/v1/data/prices/historical/{id})
export interface HistoricalPrice {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoricalPriceResponse {
  symbol: string;
  data: HistoricalPrice[];
  total_days: number;
  start_date: string;
  end_date: string;
}

// Factor ETF Prices (from /api/v1/data/factors/etf-prices)
export interface FactorETFPrice {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  factor_category: string;
}

// Data Quality Assessment (from /api/v1/data/portfolio/{id}/data-quality)
export interface DataQualityMetric {
  metric_name: string;
  status: 'good' | 'warning' | 'error';
  value: number;
  threshold: number;
  description: string;
}

export interface DataQualityResponse {
  portfolio_id: string;
  assessment_date: string;
  overall_score: number;
  overall_status: 'good' | 'warning' | 'error';
  metrics: DataQualityMetric[];
  recommendations: string[];
}

// UI-specific derived types for frontend components
export interface PortfolioSummaryMetric {
  title: string;
  value: string;
  subValue: string;
  description: string;
  positive: boolean;
  loading?: boolean;
}

export interface PositionTableRow {
  symbol: string;
  quantity: number;
  price: number;
  marketValue: number;
  pnl: number;
  percentChange?: number;
  positive: boolean;
}

// API Response wrappers
export interface ApiListResponse<T> {
  data: T[];
  total: number;
  page?: number;
  limit?: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  timestamp: string;
}

// Error types for API responses
export interface ApiErrorResponse {
  error: string;
  message: string;
  details?: any;
  timestamp: string;
  path: string;
}

// Loading states
export interface LoadingState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastUpdated?: string;
}

// Configuration types
export interface PortfolioConfig {
  refreshInterval: number;
  enableRealTimeData: boolean;
  defaultPortfolioId?: string;
  maxRetries: number;
  timeout: number;
}

// Utility types for data transformations
export type NumericString = string; // Represents numeric values as strings from backend
export type ISODateString = string; // ISO date format
export type UUIDString = string; // UUID format
export type PercentageString = string; // Percentage as string (e.g., "0.05" for 5%)
export type CurrencyString = string; // Currency as string (e.g., "12345.67")

export default PortfolioReport;
