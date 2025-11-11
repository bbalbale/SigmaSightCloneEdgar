// TypeScript definitions matching SigmaSight database schema

export interface User {
  id: string // UUID
  email: string
  full_name: string
  is_active: boolean
  is_admin?: boolean
  created_at: string
  updated_at: string
}

export interface Portfolio {
  id: string // UUID
  user_id: string // FK to users.id
  name: string
  description?: string
  currency: string // default 'USD'
  cash_balance?: number
  equity_balance?: number
  created_at: string
  updated_at: string
  deleted_at?: string

  // Additional fields from API responses
  net_asset_value?: number
  total_value?: number
  total_pnl?: number
  positions_count?: number
}

export interface Position {
  id: string // UUID
  portfolio_id: string // FK to portfolios.id
  symbol: string
  position_type: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP' // Enum
  quantity: number
  cost_basis?: number
  entry_price?: number
  exit_price?: number
  entry_date?: string
  exit_date?: string
  last_price?: number
  market_value?: number
  unrealized_pnl?: number
  realized_pnl?: number
  investment_class?: 'PUBLIC' | 'OPTIONS' | 'PRIVATE' // Computed field

  // Options-specific fields
  underlying_symbol?: string
  strike_price?: number
  expiration_date?: string

  // Additional fields from API
  name?: string
  sector?: string

  created_at: string
  updated_at: string
  deleted_at?: string
}

export interface FactorExposure {
  id: string
  portfolio_id: string
  factor_name: string
  factor_id?: string
  exposure_value: number
  exposure_dollar?: number
  calculation_date?: string
}

export interface PortfolioAnalytics {
  portfolio_id: string
  long_exposure: number
  short_exposure: number
  gross_exposure: number
  net_exposure: number
  cash_balance: number
  net_asset_value: number
  total_value: number
  total_pnl?: number
  positions_count: number

  // Percentages
  long_exposure_pct?: number
  short_exposure_pct?: number
  gross_exposure_pct?: number
  net_exposure_pct?: number
  cash_balance_pct?: number
}

export interface TargetPrice {
  id: string
  portfolio_id: string
  position_id: string
  symbol: string
  position_type: string
  target_price_eoy?: number
  target_price_next_year?: number
  downside_target_price?: number
  current_price?: number
  expected_return_eoy?: number
  expected_return_next_year?: number
  downside_return?: number
  position_weight?: number
  contribution_to_portfolio?: number
  contribution_to_risk?: number
  price_updated_at?: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface Strategy {
  id: string
  portfolio_id: string
  strategy_type: string
  name: string
  description?: string
  is_synthetic: boolean
  net_exposure?: number
  total_cost_basis?: number
  created_at: string
  updated_at: string
  closed_at?: string
  created_by: string

  // Related data
  legs?: StrategyLeg[]
  tags?: Tag[]
}

export interface StrategyLeg {
  id: string
  strategy_id: string
  position_id: string
  created_at: string
}

export interface Tag {
  id: string
  user_id: string
  name: string
  color: string
  description?: string
  display_order: number
  usage_count: number
  is_archived: boolean
  archived_at?: string
  archived_by?: string
  created_at: string
  updated_at: string
}

// API Response types
export interface ApiResponse<T> {
  data: T
  message?: string
  status: number
}

// Form types
export interface LoginCredentials {
  email: string
  password: string
}

// Session types
export interface Session {
  user: User
  token: string
}

// Navigation types
export interface NavItem {
  href: string
  label: string
  icon?: string
}

// Dashboard Summary types
export interface PositionSummary {
  type: 'LONG' | 'SHORT' | 'OPTIONS' | 'PRIVATE'
  count: number
  totalValue: number
  totalPnL: number
  positions: Position[]
}
