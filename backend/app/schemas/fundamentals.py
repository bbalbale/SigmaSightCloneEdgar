"""
Pydantic schemas for fundamental financial data
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal


# ============================================================================
# Base Schemas
# ============================================================================

class FinancialPeriod(BaseModel):
    """Single period of financial data"""
    period_date: date
    period_type: str  # "3M", "12M", "TTM"
    fiscal_year: int
    fiscal_quarter: Optional[str] = None  # "Q1", "Q2", "Q3", "Q4"


class Metadata(BaseModel):
    """Metadata for financial data responses"""
    data_source: str = "yahooquery"
    last_updated: datetime
    periods_returned: int


# ============================================================================
# Income Statement Schemas
# ============================================================================

class IncomeStatementMetrics(BaseModel):
    """Income statement line items for one period"""
    revenue: Optional[Decimal] = None
    cost_of_revenue: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None
    research_and_development: Optional[Decimal] = None
    selling_general_administrative: Optional[Decimal] = None
    total_operating_expenses: Optional[Decimal] = None
    operating_income: Optional[Decimal] = None
    operating_margin: Optional[Decimal] = None
    ebit: Optional[Decimal] = None
    interest_expense: Optional[Decimal] = None
    other_income_expense: Optional[Decimal] = None
    pretax_income: Optional[Decimal] = None
    tax_provision: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    net_margin: Optional[Decimal] = None
    ebitda: Optional[Decimal] = None
    depreciation_amortization: Optional[Decimal] = None
    basic_eps: Optional[Decimal] = None
    diluted_eps: Optional[Decimal] = None
    basic_shares: Optional[int] = None
    diluted_shares: Optional[int] = None


class IncomeStatementPeriod(FinancialPeriod):
    """Income statement for one period"""
    metrics: IncomeStatementMetrics


class IncomeStatementResponse(BaseModel):
    """Full income statement response"""
    symbol: str
    frequency: str  # "q", "a", "ttm"
    currency: str
    periods: List[IncomeStatementPeriod]
    metadata: Metadata


# ============================================================================
# Balance Sheet Schemas
# ============================================================================

class CurrentAssets(BaseModel):
    """Current assets breakdown"""
    cash_and_equivalents: Optional[Decimal] = None
    short_term_investments: Optional[Decimal] = None
    cash_and_short_term_investments: Optional[Decimal] = None
    accounts_receivable: Optional[Decimal] = None
    inventory: Optional[Decimal] = None
    other_current_assets: Optional[Decimal] = None
    total_current_assets: Optional[Decimal] = None


class NonCurrentAssets(BaseModel):
    """Non-current assets breakdown"""
    net_ppe: Optional[Decimal] = None
    goodwill: Optional[Decimal] = None
    intangible_assets: Optional[Decimal] = None
    long_term_investments: Optional[Decimal] = None
    other_non_current_assets: Optional[Decimal] = None
    total_non_current_assets: Optional[Decimal] = None


class Assets(BaseModel):
    """All assets"""
    current_assets: CurrentAssets
    non_current_assets: NonCurrentAssets
    total_assets: Optional[Decimal] = None


class CurrentLiabilities(BaseModel):
    """Current liabilities breakdown"""
    accounts_payable: Optional[Decimal] = None
    short_term_debt: Optional[Decimal] = None
    current_portion_long_term_debt: Optional[Decimal] = None
    accrued_liabilities: Optional[Decimal] = None
    deferred_revenue: Optional[Decimal] = None
    other_current_liabilities: Optional[Decimal] = None
    total_current_liabilities: Optional[Decimal] = None


class NonCurrentLiabilities(BaseModel):
    """Non-current liabilities breakdown"""
    long_term_debt: Optional[Decimal] = None
    deferred_tax_liabilities: Optional[Decimal] = None
    other_non_current_liabilities: Optional[Decimal] = None
    total_non_current_liabilities: Optional[Decimal] = None


class Liabilities(BaseModel):
    """All liabilities"""
    current_liabilities: CurrentLiabilities
    non_current_liabilities: NonCurrentLiabilities
    total_liabilities: Optional[Decimal] = None


class Equity(BaseModel):
    """Shareholders' equity"""
    common_stock: Optional[Decimal] = None
    retained_earnings: Optional[Decimal] = None
    accumulated_other_comprehensive_income: Optional[Decimal] = None
    treasury_stock: Optional[Decimal] = None
    total_stockholders_equity: Optional[Decimal] = None
    minority_interest: Optional[Decimal] = None


class BalanceSheetCalculatedMetrics(BaseModel):
    """Calculated balance sheet metrics"""
    working_capital: Optional[Decimal] = None
    net_debt: Optional[Decimal] = None
    total_debt: Optional[Decimal] = None
    book_value: Optional[Decimal] = None
    book_value_per_share: Optional[Decimal] = None
    tangible_book_value: Optional[Decimal] = None
    tangible_book_value_per_share: Optional[Decimal] = None


class BalanceSheetRatios(BaseModel):
    """Balance sheet ratios"""
    current_ratio: Optional[Decimal] = None
    quick_ratio: Optional[Decimal] = None
    cash_ratio: Optional[Decimal] = None
    debt_to_equity: Optional[Decimal] = None
    debt_to_assets: Optional[Decimal] = None
    equity_to_assets: Optional[Decimal] = None


class BalanceSheetMetrics(BaseModel):
    """Balance sheet metrics for one period"""
    assets: Assets
    liabilities: Liabilities
    equity: Equity
    calculated_metrics: BalanceSheetCalculatedMetrics
    ratios: BalanceSheetRatios


class BalanceSheetPeriod(FinancialPeriod):
    """Balance sheet for one period"""
    metrics: BalanceSheetMetrics


class BalanceSheetResponse(BaseModel):
    """Full balance sheet response"""
    symbol: str
    frequency: str  # "q", "a"
    currency: str
    periods: List[BalanceSheetPeriod]
    metadata: Metadata


# ============================================================================
# Cash Flow Schemas
# ============================================================================

class OperatingActivities(BaseModel):
    """Operating cash flow activities"""
    operating_cash_flow: Optional[Decimal] = None
    depreciation_amortization: Optional[Decimal] = None
    change_in_working_capital: Optional[Decimal] = None
    stock_based_compensation: Optional[Decimal] = None
    deferred_income_tax: Optional[Decimal] = None
    other_operating_activities: Optional[Decimal] = None


class InvestingActivities(BaseModel):
    """Investing cash flow activities"""
    capital_expenditures: Optional[Decimal] = None
    acquisitions: Optional[Decimal] = None
    purchases_of_investments: Optional[Decimal] = None
    sales_of_investments: Optional[Decimal] = None
    other_investing_activities: Optional[Decimal] = None
    net_investing_cash_flow: Optional[Decimal] = None


class FinancingActivities(BaseModel):
    """Financing cash flow activities"""
    dividends_paid: Optional[Decimal] = None
    stock_repurchases: Optional[Decimal] = None
    debt_issuance: Optional[Decimal] = None
    debt_repayment: Optional[Decimal] = None
    common_stock_issuance: Optional[Decimal] = None
    other_financing_activities: Optional[Decimal] = None
    net_financing_cash_flow: Optional[Decimal] = None


class CashFlowCalculatedMetrics(BaseModel):
    """Calculated cash flow metrics"""
    free_cash_flow: Optional[Decimal] = None
    fcf_margin: Optional[Decimal] = None
    fcf_per_share: Optional[Decimal] = None


class CashFlowMetrics(BaseModel):
    """Cash flow metrics for one period"""
    operating_activities: OperatingActivities
    investing_activities: InvestingActivities
    financing_activities: FinancingActivities
    calculated_metrics: CashFlowCalculatedMetrics
    net_change_in_cash: Optional[Decimal] = None
    beginning_cash: Optional[Decimal] = None
    ending_cash: Optional[Decimal] = None


class CashFlowPeriod(FinancialPeriod):
    """Cash flow for one period"""
    metrics: CashFlowMetrics


class CashFlowResponse(BaseModel):
    """Full cash flow response"""
    symbol: str
    frequency: str  # "q", "a"
    currency: str
    periods: List[CashFlowPeriod]
    metadata: Metadata


# ============================================================================
# Combined Financial Statements
# ============================================================================

class AllStatementsResponse(BaseModel):
    """Response containing all three financial statements"""
    symbol: str
    frequency: str
    currency: str
    income_statement: IncomeStatementResponse
    balance_sheet: BalanceSheetResponse
    cash_flow: CashFlowResponse
    metadata: Metadata


# ============================================================================
# Analyst Estimates Schemas
# ============================================================================

class RevenueEstimate(BaseModel):
    """Revenue estimate data"""
    average: Optional[Decimal] = None
    low: Optional[Decimal] = None
    high: Optional[Decimal] = None
    num_analysts: Optional[int] = None
    year_ago: Optional[Decimal] = None
    growth: Optional[Decimal] = None  # YoY growth rate


class EPSEstimate(BaseModel):
    """EPS estimate data"""
    average: Optional[Decimal] = None
    low: Optional[Decimal] = None
    high: Optional[Decimal] = None
    num_analysts: Optional[int] = None
    year_ago: Optional[Decimal] = None
    growth: Optional[Decimal] = None  # YoY growth rate


class EPSRevisions(BaseModel):
    """EPS estimate revisions"""
    up_last_7_days: Optional[int] = None
    up_last_30_days: Optional[int] = None
    down_last_7_days: Optional[int] = None
    down_last_30_days: Optional[int] = None
    down_last_90_days: Optional[int] = None


class EPSTrend(BaseModel):
    """EPS estimate trend over time"""
    current: Optional[Decimal] = None
    seven_days_ago: Optional[Decimal] = Field(None, alias="7_days_ago")
    thirty_days_ago: Optional[Decimal] = Field(None, alias="30_days_ago")
    sixty_days_ago: Optional[Decimal] = Field(None, alias="60_days_ago")
    ninety_days_ago: Optional[Decimal] = Field(None, alias="90_days_ago")


class EstimatePeriod(BaseModel):
    """Estimates for one period"""
    period: str  # "Q1 2025", "FY 2025"
    end_date: date
    revenue: RevenueEstimate
    eps: EPSEstimate
    eps_revisions: EPSRevisions
    eps_trend: EPSTrend


class AnalystEstimatesResponse(BaseModel):
    """Analyst estimates response"""
    symbol: str
    current_quarter: Optional[EstimatePeriod] = None
    next_quarter: Optional[EstimatePeriod] = None
    current_year: Optional[EstimatePeriod] = None
    next_year: Optional[EstimatePeriod] = None
    metadata: Metadata


# ============================================================================
# Price Targets Schemas
# ============================================================================

class PriceTargets(BaseModel):
    """Analyst price targets"""
    low: Optional[Decimal] = None
    mean: Optional[Decimal] = None
    high: Optional[Decimal] = None
    median: Optional[Decimal] = None


class Upside(BaseModel):
    """Upside calculations to price targets"""
    to_mean: Optional[Decimal] = None  # Percentage upside to mean target
    to_high: Optional[Decimal] = None  # Percentage upside to high target


class RecommendationDistribution(BaseModel):
    """Distribution of analyst recommendations"""
    strong_buy: Optional[int] = None
    buy: Optional[int] = None
    hold: Optional[int] = None
    sell: Optional[int] = None
    strong_sell: Optional[int] = None


class Recommendations(BaseModel):
    """Analyst recommendations"""
    mean: Optional[Decimal] = None  # 1=Strong Buy, 5=Sell
    distribution: RecommendationDistribution
    num_analysts: Optional[int] = None


class PriceTargetsResponse(BaseModel):
    """Price targets response"""
    symbol: str
    current_price: Optional[Decimal] = None
    targets: PriceTargets
    upside: Upside
    recommendations: Recommendations
    metadata: Metadata


# ============================================================================
# Next Earnings Schemas
# ============================================================================

class EarningsEstimate(BaseModel):
    """Earnings estimate"""
    average: Optional[Decimal] = None
    low: Optional[Decimal] = None
    high: Optional[Decimal] = None


class NextEarnings(BaseModel):
    """Next earnings event"""
    date: Optional[datetime] = None
    fiscal_quarter: Optional[str] = None
    revenue_estimate: Optional[EarningsEstimate] = None
    eps_estimate: Optional[EarningsEstimate] = None


class LastEarnings(BaseModel):
    """Last earnings results"""
    date: Optional[date] = None
    revenue_actual: Optional[Decimal] = None
    revenue_estimate: Optional[Decimal] = None
    revenue_surprise: Optional[Decimal] = None  # % beat/miss
    eps_actual: Optional[Decimal] = None
    eps_estimate: Optional[Decimal] = None
    eps_surprise: Optional[Decimal] = None  # % beat/miss


class NextEarningsResponse(BaseModel):
    """Next earnings response"""
    symbol: str
    next_earnings: Optional[NextEarnings] = None
    last_earnings: Optional[LastEarnings] = None
    metadata: Metadata


# ============================================================================
# Simplified Response Schemas (Direct Database Mapping)
# ============================================================================

class SimpleIncomeStatementPeriod(BaseModel):
    """Simplified income statement for one period - direct DB mapping"""
    period_date: date
    frequency: str  # 'q' or 'a'
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None

    # Revenue & Costs
    total_revenue: Optional[Decimal] = None
    cost_of_revenue: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None

    # Operating Expenses
    research_and_development: Optional[Decimal] = None
    selling_general_and_administrative: Optional[Decimal] = None

    # Operating Results
    operating_income: Optional[Decimal] = None
    operating_margin: Optional[Decimal] = None
    ebit: Optional[Decimal] = None
    ebitda: Optional[Decimal] = None

    # Net Income
    net_income: Optional[Decimal] = None
    net_margin: Optional[Decimal] = None

    # Per Share
    diluted_eps: Optional[Decimal] = None
    basic_eps: Optional[Decimal] = None
    basic_average_shares: Optional[int] = None
    diluted_average_shares: Optional[int] = None

    # Tax & Interest
    tax_provision: Optional[Decimal] = None
    interest_expense: Optional[Decimal] = None
    depreciation_and_amortization: Optional[Decimal] = None

    class Config:
        from_attributes = True


class SimpleBalanceSheetPeriod(BaseModel):
    """Simplified balance sheet for one period - direct DB mapping"""
    period_date: date
    frequency: str  # 'q' or 'a'
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None

    # Assets
    total_assets: Optional[Decimal] = None
    current_assets: Optional[Decimal] = None
    cash_and_cash_equivalents: Optional[Decimal] = None
    short_term_investments: Optional[Decimal] = None
    accounts_receivable: Optional[Decimal] = None
    inventory: Optional[Decimal] = None
    property_plant_equipment: Optional[Decimal] = None
    intangible_assets: Optional[Decimal] = None

    # Liabilities
    total_liabilities: Optional[Decimal] = None
    current_liabilities: Optional[Decimal] = None
    accounts_payable: Optional[Decimal] = None
    short_term_debt: Optional[Decimal] = None
    long_term_debt: Optional[Decimal] = None
    total_debt: Optional[Decimal] = None

    # Equity
    total_stockholders_equity: Optional[Decimal] = None
    retained_earnings: Optional[Decimal] = None
    common_stock: Optional[Decimal] = None

    # Calculated Metrics
    working_capital: Optional[Decimal] = None
    net_debt: Optional[Decimal] = None
    current_ratio: Optional[Decimal] = None
    debt_to_equity: Optional[Decimal] = None
    book_value_per_share: Optional[Decimal] = None

    class Config:
        from_attributes = True


class SimpleCashFlowPeriod(BaseModel):
    """Simplified cash flow for one period - direct DB mapping"""
    period_date: date
    frequency: str  # 'q' or 'a'
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None

    # Operating Activities
    operating_cash_flow: Optional[Decimal] = None
    depreciation_and_amortization: Optional[Decimal] = None
    stock_based_compensation: Optional[Decimal] = None
    change_in_working_capital: Optional[Decimal] = None

    # Investing Activities
    investing_cash_flow: Optional[Decimal] = None
    capital_expenditures: Optional[Decimal] = None
    acquisitions: Optional[Decimal] = None
    purchases_of_investments: Optional[Decimal] = None

    # Financing Activities
    financing_cash_flow: Optional[Decimal] = None
    dividends_paid: Optional[Decimal] = None
    stock_repurchases: Optional[Decimal] = None
    debt_issuance_repayment: Optional[Decimal] = None

    # Summary
    net_change_in_cash: Optional[Decimal] = None
    beginning_cash_position: Optional[Decimal] = None

    # Calculated Metrics
    free_cash_flow: Optional[Decimal] = None
    fcf_margin: Optional[Decimal] = None

    class Config:
        from_attributes = True


class SimpleAnalystEstimates(BaseModel):
    """Simplified analyst estimates - direct from company_profiles"""

    # Current Quarter
    current_quarter_end_date: Optional[date] = None
    current_quarter_revenue_avg: Optional[Decimal] = None
    current_quarter_revenue_low: Optional[Decimal] = None
    current_quarter_revenue_high: Optional[Decimal] = None
    current_quarter_eps_avg: Optional[Decimal] = None
    current_quarter_eps_low: Optional[Decimal] = None
    current_quarter_eps_high: Optional[Decimal] = None
    current_quarter_analyst_count: Optional[int] = None

    # Next Quarter
    next_quarter_end_date: Optional[date] = None
    next_quarter_revenue_avg: Optional[Decimal] = None
    next_quarter_revenue_low: Optional[Decimal] = None
    next_quarter_revenue_high: Optional[Decimal] = None
    next_quarter_eps_avg: Optional[Decimal] = None
    next_quarter_eps_low: Optional[Decimal] = None
    next_quarter_eps_high: Optional[Decimal] = None
    next_quarter_analyst_count: Optional[int] = None

    # Current Year
    current_year_end_date: Optional[date] = None
    current_year_revenue_avg: Optional[Decimal] = None
    current_year_revenue_low: Optional[Decimal] = None
    current_year_revenue_high: Optional[Decimal] = None
    current_year_revenue_growth: Optional[Decimal] = None
    current_year_earnings_avg: Optional[Decimal] = None
    current_year_earnings_low: Optional[Decimal] = None
    current_year_earnings_high: Optional[Decimal] = None

    # Next Year
    next_year_end_date: Optional[date] = None
    next_year_revenue_avg: Optional[Decimal] = None
    next_year_revenue_low: Optional[Decimal] = None
    next_year_revenue_high: Optional[Decimal] = None
    next_year_revenue_growth: Optional[Decimal] = None
    next_year_earnings_avg: Optional[Decimal] = None
    next_year_earnings_low: Optional[Decimal] = None
    next_year_earnings_high: Optional[Decimal] = None

    class Config:
        from_attributes = True


# API Response Wrappers
class SimpleIncomeStatementResponse(BaseModel):
    """Income statement API response"""
    symbol: str
    frequency: str
    currency: str = "USD"
    periods: List[SimpleIncomeStatementPeriod]
    periods_returned: int


class SimpleBalanceSheetResponse(BaseModel):
    """Balance sheet API response"""
    symbol: str
    frequency: str
    currency: str = "USD"
    periods: List[SimpleBalanceSheetPeriod]
    periods_returned: int


class SimpleCashFlowResponse(BaseModel):
    """Cash flow API response"""
    symbol: str
    frequency: str
    currency: str = "USD"
    periods: List[SimpleCashFlowPeriod]
    periods_returned: int


class SimpleAnalystEstimatesResponse(BaseModel):
    """Analyst estimates API response"""
    symbol: str
    estimates: SimpleAnalystEstimates
