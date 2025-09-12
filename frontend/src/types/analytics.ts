// Analytics API response types (aligned with backend API_SPECIFICATIONS_V1.4.5.md)

export interface PortfolioOverviewResponse {
  portfolio_id: string;
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

export interface FactorExposuresResponse {
  available: boolean;
  portfolio_id: string;
  calculation_date: string;
  factors: FactorExposure[];
  metadata: FactorExposuresMetadata;
}

export interface FactorExposuresApiResponse {
  data: FactorExposuresResponse;
}

export interface PositionFactorExposureItem {
  position_id: string;
  symbol: string;
  exposures: Record<string, number>; // factor name → exposure value
}

export interface PositionFactorExposuresResponse {
  available: boolean;
  data?: PositionFactorExposureItem[];
  metadata?: {
    count: number;
    limit: number;
    offset: number;
  };
  reason?: string;
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

