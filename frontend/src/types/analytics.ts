// Analytics API response types (aligned with backend API_SPECIFICATIONS_V1.4.5.md)

export interface PortfolioOverviewResponse {
  portfolio_id: string;
  net_asset_value: number;
  total_value: number;
  cash_balance: number;
  exposures: {
    long_exposure: number;
    short_exposure: number;
    gross_exposure: number;
    net_exposure: number;
    long_percentage: number;
    short_percentage: number;
    gross_percentage: number;
    net_percentage: number;
  };
  pnl: {
    total_pnl: number;
    unrealized_pnl: number;
    realized_pnl: number;
  };
  position_count: {
    total_positions: number;
    long_count: number;
    short_count: number;
    option_count: number;
  };
  last_updated: string; // ISO
}

export interface CorrelationMatrixResponse {
  available: boolean;
  data?: {
    matrix: Record<string, Record<string, number>>;
    average_correlation: number;
  };
  metadata?: {
    calculation_date: string; // ISO
    lookback_days: number;
    positions_included: number;
  };
  reason?: string;
}

// Legacy factor exposures format
export interface PortfolioFactorExposuresResponse {
  available: boolean;
  data?: Array<{
    factor: string;
    exposure: number;
  }>;
  metadata?: {
    calculation_date: string; // ISO
  };
  reason?: string;
}

// New detailed factor exposures format
export interface FactorExposure {
  name: string;
  beta: number;
  exposure_dollar: number;
}

export interface FactorExposuresMetadata {
  factor_model: string;
  calculation_method: string;
  completeness: string;
  total_active_factors: number;
  factors_calculated: number;
  has_market_beta: number;
}

// Data staleness information for latest-available pattern
export interface DataStalenessInfo {
  snapshot_date?: string;
  calculation_date?: string;
  age_hours?: number;
  is_stale: boolean;
  is_current: boolean;
  should_recalculate?: boolean;
}

// Data quality information for calculation issues
export interface DataQualityInfo {
  flag: string;
  message: string;
  positions_analyzed: number;
  positions_total: number;
  positions_skipped: number;
  data_days: number;
}

export interface FactorExposuresResponse {
  available: boolean;
  portfolio_id: string;
  calculation_date: string;
  factors: FactorExposure[];
  metadata: FactorExposuresMetadata;
  data_quality?: DataStalenessInfo | DataQualityInfo | null;
}

export interface FactorExposuresApiResponse {
  data: FactorExposuresResponse;
}

export interface PositionFactorExposureItem {
  position_id: string;
  symbol: string;
  exposures: Record<string, number>; // factor name → exposure value (beta)
}

// Updated to match backend API response structure
export interface PositionFactorExposuresResponse {
  available: boolean;
  portfolio_id: string;
  calculation_date: string | null;
  total: number | null;
  limit: number | null;
  offset: number | null;
  positions: PositionFactorExposureItem[] | null;
  data_quality?: {
    flag: string;
    message: string;
    positions_analyzed: number;
    positions_total: number;
    positions_skipped: number;
    data_days: number;
  } | null;
  metadata?: {
    reason?: string;
  };
}

// Helper type for factor beta display
export interface PositionFactorData {
  factorExposures: Map<string, Record<string, number>>; // symbol → { factor_name → beta }
  companyBetas: Map<string, number>; // symbol → company market beta
  loading: boolean;
  error: string | null;
  calculationDate: string | null;
}

export interface StressTestScenarioImpact {
  dollar_impact: number;
  percentage_impact: number; // percentage points
  new_portfolio_value: number;
}

export interface StressTestScenario {
  id: string;
  name: string;
  description?: string;
  category?: string;
  impact_type?: string;
  impact: StressTestScenarioImpact;
  severity?: string;
}

export interface StressTestResponse {
  available: boolean;
  data?: {
    scenarios: StressTestScenario[];
    portfolio_value: number;
    calculation_date: string; // YYYY-MM-DD
  };
  metadata?: {
    scenarios_requested?: string[];
  };
  reason?: string;
}

export interface DiversificationScoreResponse {
  available: boolean;
  data?: {
    overall_score: number; // 0-100
    category_scores: {
      asset_class: number;
      sector: number;
      geography: number;
      position_size: number;
    };
    recommendations?: string[];
  };
  metadata?: {
    calculation_date: string; // ISO
    position_count: number;
  };
  reason?: string;
}

export interface VolatilityMetricsData {
  realized_volatility_21d: number;
  realized_volatility_63d: number;
  expected_volatility_21d: number | null;
  volatility_trend: string | null; // 'increasing', 'decreasing', 'stable'
  volatility_percentile: number | null; // 0-1 scale
}

export interface VolatilityMetricsResponse {
  available: boolean;
  portfolio_id: string;
  calculation_date: string | null;
  data: VolatilityMetricsData | null;
  metadata?: {
    forecast_model?: string;
    trading_day_windows?: string;
    error?: string;
  };
}

export interface SectorExposureData {
  portfolio_weights: Record<string, number>; // sector name -> weight (0-1)
  benchmark_weights: Record<string, number>; // sector name -> weight (0-1)
  over_underweight: Record<string, number>; // sector name -> difference
  largest_overweight: string | null;
  largest_underweight: string | null;
  total_portfolio_value: number;
  positions_by_sector: Record<string, number>;
  unclassified_value: number;
  unclassified_count: number;
}

export interface SectorExposureResponse {
  available: boolean;
  portfolio_id: string;
  calculation_date: string | null;
  data: SectorExposureData | null;
  metadata?: {
    benchmark?: string;
    error?: string;
  };
}

export interface ConcentrationMetricsData {
  hhi: number; // Herfindahl-Hirschman Index (0-10000)
  effective_num_positions: number;
  top_3_concentration: number; // 0-1 scale
  top_10_concentration: number; // 0-1 scale
  total_positions: number;
  position_weights: Record<string, number> | null;
}

export interface ConcentrationMetricsResponse {
  available: boolean;
  portfolio_id: string;
  calculation_date: string | null;
  data: ConcentrationMetricsData | null;
  metadata?: {
    calculation_method?: string;
    interpretation?: string;
    error?: string;
  };
}

