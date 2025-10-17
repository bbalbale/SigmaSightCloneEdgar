"""
Analytics API Response Schemas

Pydantic models for portfolio analytics endpoints including portfolio overview,
risk metrics, and performance data.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Union, List
from datetime import datetime


class DataQualityInfo(BaseModel):
    """
    Data quality information for analytics calculations

    Provides transparency about why calculations were skipped or partially completed,
    including position filtering details and data availability metrics.

    Added in Phase 8.1 Task 13 to expose internal quality metrics from graceful degradation.
    """
    flag: str = Field(..., description="Quality flag constant (e.g., QUALITY_FLAG_NO_PUBLIC_POSITIONS)")
    message: str = Field(..., description="Human-readable explanation of quality status")
    positions_analyzed: int = Field(..., description="Number of positions included in calculation")
    positions_total: int = Field(..., description="Total number of positions in portfolio")
    positions_skipped: int = Field(..., description="Number of positions excluded (PRIVATE + insufficient data)")
    data_days: int = Field(..., description="Number of days of historical data used in calculation")

    class Config:
        schema_extra = {
            "example": {
                "flag": "QUALITY_FLAG_NO_PUBLIC_POSITIONS",
                "message": "Portfolio contains no public positions for factor analysis",
                "positions_analyzed": 0,
                "positions_total": 8,
                "positions_skipped": 8,
                "data_days": 0
            }
        }


class PortfolioExposures(BaseModel):
    """Portfolio exposure metrics"""
    long_exposure: float = Field(..., description="Total long exposure in dollars")
    short_exposure: float = Field(..., description="Total short exposure in dollars")
    gross_exposure: float = Field(..., description="Total gross exposure (long + short)")
    net_exposure: float = Field(..., description="Net exposure (long - short)")
    long_percentage: float = Field(..., description="Long exposure as percentage of total")
    short_percentage: float = Field(..., description="Short exposure as percentage of total")
    gross_percentage: float = Field(..., description="Gross exposure as percentage of total")
    net_percentage: float = Field(..., description="Net exposure as percentage of total")


class PortfolioPnL(BaseModel):
    """Portfolio P&L metrics"""
    total_pnl: float = Field(..., description="Total P&L (realized + unrealized)")
    unrealized_pnl: float = Field(..., description="Unrealized P&L from current positions")
    realized_pnl: float = Field(..., description="Realized P&L from closed positions")


class PositionCount(BaseModel):
    """Portfolio position count breakdown"""
    total_positions: int = Field(..., description="Total number of positions")
    long_count: int = Field(..., description="Number of long positions")
    short_count: int = Field(..., description="Number of short positions")
    option_count: int = Field(..., description="Number of option positions")


class PortfolioOverviewResponse(BaseModel):
    """
    Portfolio overview response matching API_SPECIFICATIONS_V1.4.5.md
    
    Comprehensive portfolio metrics for dashboard consumption including
    exposures, P&L, and position counts.
    """
    portfolio_id: str = Field(..., description="Portfolio UUID")
    equity_balance: Optional[float] = Field(None, description="User-provided equity balance (NAV)")
    total_value: float = Field(..., description="Total portfolio value including cash")
    cash_balance: float = Field(..., description="Available cash balance")
    leverage: float = Field(..., description="Leverage ratio (gross exposure / equity)")
    exposures: PortfolioExposures = Field(..., description="Portfolio exposure metrics")
    pnl: PortfolioPnL = Field(..., description="Portfolio P&L metrics")
    position_count: PositionCount = Field(..., description="Position count breakdown")
    last_updated: str = Field(..., description="ISO 8601 timestamp of last calculation")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v else None
        }
        schema_extra = {
            "example": {
                "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
                "total_value": 1250000.00,
                "cash_balance": 62500.00,
                "exposures": {
                    "long_exposure": 1187500.00,
                    "short_exposure": 0.00,
                    "gross_exposure": 1187500.00,
                    "net_exposure": 1187500.00,
                    "long_percentage": 95.0,
                    "short_percentage": 0.0,
                    "gross_percentage": 95.0,
                    "net_percentage": 95.0
                },
                "pnl": {
                    "total_pnl": 125432.18,
                    "unrealized_pnl": 98765.43,
                    "realized_pnl": 26666.75
                },
                "position_count": {
                    "total_positions": 21,
                    "long_count": 18,
                    "short_count": 0,
                    "option_count": 3
                },
                "last_updated": "2025-01-15T10:30:00Z"
            }
        }


class CorrelationMatrixData(BaseModel):
    """Correlation matrix data"""
    matrix: Dict[str, Dict[str, float]] = Field(..., description="Nested dictionary of symbol correlations")
    average_correlation: Optional[float] = Field(None, description="Average portfolio correlation")


class CorrelationMatrixResponse(BaseModel):
    """
    Correlation matrix response for portfolio positions

    Returns pre-calculated pairwise correlations between portfolio positions
    ordered by position weight (gross market value).
    """
    data: Optional[CorrelationMatrixData] = Field(None, description="Correlation data when available")
    available: Optional[bool] = Field(None, description="Whether correlation data is available")
    data_quality: Optional[DataQualityInfo] = Field(None, description="Data quality metrics when calculation is skipped or partial")
    metadata: Optional[Dict[str, Union[str, int]]] = Field(None, description="Error or status metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "data": {
                    "matrix": {
                        "AAPL": {"AAPL": 1.0, "MSFT": 0.82, "NVDA": 0.75},
                        "MSFT": {"AAPL": 0.82, "MSFT": 1.0, "NVDA": 0.68},
                        "NVDA": {"AAPL": 0.75, "MSFT": 0.68, "NVDA": 1.0}
                    },
                    "average_correlation": 0.75
                }
            }
        }


class DiversificationScoreResponse(BaseModel):
    """
    Weighted absolute portfolio correlation (0–1) over the full calculation symbol set.
    Returns a light payload suitable for dashboards and summaries.
    """
    available: bool = Field(..., description="Whether correlation data is available for this portfolio/lookback")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    portfolio_correlation: Optional[float] = Field(None, description="Weighted absolute average pairwise correlation (0–1)")
    duration_days: Optional[int] = Field(None, description="Lookback window in days used by the calculation")
    calculation_date: Optional[str] = Field(None, description="ISO date of the correlation calculation")
    symbols_included: Optional[int] = Field(None, description="Number of symbols in the full calculation set")
    metadata: Optional[Dict[str, Union[str, int, float]]] = Field(None, description="Additional parameters and notes")

    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
                "portfolio_correlation": 0.73,
                "duration_days": 90,
                "calculation_date": "2025-09-05",
                "symbols_included": 23,
                "metadata": {
                    "lookback_days": 90,
                    "min_overlap": 30,
                    "selection_method": "full_calculation_set"
                }
            }
        }


class StressImpact(BaseModel):
    dollar_impact: float = Field(..., description="Dollar P&L impact from scenario (correlated)")
    percentage_impact: float = Field(..., description="Impact as percentage points of portfolio value (e.g., -10.0 means -10%)")
    new_portfolio_value: float = Field(..., description="Baseline portfolio value plus dollar_impact")


class StressScenarioItem(BaseModel):
    id: str = Field(..., description="Scenario identifier string")
    name: str = Field(..., description="Scenario display name")
    description: Optional[str] = Field(None, description="Scenario description")
    category: Optional[str] = Field(None, description="Scenario category")
    impact_type: str = Field("correlated", description="Impact type used (correlated)")
    impact: StressImpact
    severity: Optional[str] = Field(None, description="Scenario severity")


class StressTestPayload(BaseModel):
    scenarios: List[StressScenarioItem]
    portfolio_value: float
    calculation_date: str


class StressTestResponse(BaseModel):
    available: bool = Field(..., description="Whether stress test results are available")
    data: Optional[StressTestPayload] = Field(None, description="Stress test payload when available")
    data_quality: Optional[DataQualityInfo] = Field(None, description="Data quality metrics when calculation is skipped or partial")
    metadata: Optional[Dict[str, Union[str, List[str]]]] = Field(None, description="Additional metadata, including scenarios_requested if provided")


class RiskDateRange(BaseModel):
    start: str = Field(..., description="ISO date start of lookback window")
    end: str = Field(..., description="ISO date end of lookback window")


class PortfolioRiskMetrics(BaseModel):
    portfolio_beta: Optional[float] = Field(None, description="Portfolio beta (factor exposure 'Market Beta' in v1)")
    annualized_volatility: Optional[float] = Field(None, description="Annualized volatility of portfolio daily returns (sample stddev × sqrt(252))")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown over lookback window (negative percentage)")


class PortfolioRiskMetricsResponse(BaseModel):
    available: bool = Field(..., description="Whether risk metrics are available for this window")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    risk_metrics: Optional[PortfolioRiskMetrics] = Field(None, description="Risk metrics payload when available")
    metadata: Optional[Dict[str, Union[str, int, float, List[str], Dict[str, str]]]] = Field(
        None,
        description=(
            "Additional context: lookback_days, date_range, observations, calculation_timestamp, "
            "beta_source, beta_calculation_date, beta_window_days, warnings[]"
        ),
    )


class PortfolioFactorItem(BaseModel):
    name: str = Field(..., description="Factor name")
    beta: float = Field(..., description="Portfolio beta to the factor")
    exposure_dollar: Optional[float] = Field(None, description="Dollar exposure to the factor, if available")


class PortfolioFactorExposuresResponse(BaseModel):
    available: bool = Field(..., description="Whether factor exposures are available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    calculation_date: Optional[str] = Field(None, description="ISO date of the factor exposure calculation")
    data_quality: Optional[DataQualityInfo] = Field(None, description="Data quality metrics when calculation is skipped or partial")
    factors: Optional[List[PortfolioFactorItem]] = Field(None, description="List of factor exposures")
    metadata: Optional[Dict[str, Union[str, int]]] = Field(None, description="Additional metadata such as factor model details")

    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
                "calculation_date": "2025-09-05",
                "factors": [
                    {"name": "Growth", "beta": 0.67, "exposure_dollar": 837500.0},
                    {"name": "Value", "beta": -0.15, "exposure_dollar": -187500.0}
                ],
                "metadata": {
                    "factor_model": "7-factor",
                    "calculation_method": "ETF-proxy regression"
                }
            }
        }


class PositionFactorItem(BaseModel):
    position_id: str = Field(..., description="Position UUID")
    symbol: str = Field(..., description="Position symbol")
    exposures: Dict[str, float] = Field(..., description="Map of factor name to beta")


class PositionFactorExposuresResponse(BaseModel):
    available: bool = Field(..., description="Whether position factor exposures are available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    calculation_date: Optional[str] = Field(None, description="ISO date used for exposures")
    data_quality: Optional[DataQualityInfo] = Field(None, description="Data quality metrics when calculation is skipped or partial")
    total: Optional[int] = Field(None, description="Total positions matched")
    limit: Optional[int] = Field(None, description="Page size")
    offset: Optional[int] = Field(None, description="Pagination offset")
    positions: Optional[List[PositionFactorItem]] = Field(None, description="List of positions with factor exposures")

    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
                "calculation_date": "2025-09-05",
                "total": 120,
                "limit": 50,
                "offset": 0,
                "positions": [
                    {
                        "position_id": "e5e29f33-ac9f-411b-9494-bff119f435b2",
                        "symbol": "AAPL",
                        "exposures": {"Market Beta": 0.95, "Value": -0.12, "Momentum": 0.18}
                    }
                ]
            }
        }


class SectorExposureData(BaseModel):
    """Sector exposure data comparing portfolio to S&P 500 benchmark"""
    portfolio_weights: Dict[str, float] = Field(..., description="Portfolio sector weights (decimals summing to 1.0)")
    benchmark_weights: Dict[str, float] = Field(..., description="S&P 500 sector weights (decimals summing to 1.0)")
    over_underweight: Dict[str, float] = Field(..., description="Over/underweight vs benchmark (positive = overweight)")
    largest_overweight: Optional[str] = Field(None, description="Sector with largest overweight")
    largest_underweight: Optional[str] = Field(None, description="Sector with largest underweight")
    total_portfolio_value: float = Field(..., description="Total portfolio value used for calculation")
    positions_by_sector: Dict[str, int] = Field(..., description="Number of positions per sector")
    unclassified_value: float = Field(..., description="Value of positions without sector classification")
    unclassified_count: int = Field(..., description="Number of positions without sector classification")


class SectorExposureResponse(BaseModel):
    """
    Portfolio sector exposure response (Phase 1: Risk Metrics)

    Returns portfolio sector exposure vs S&P 500 benchmark with over/underweight analysis.
    Uses GICS sector classifications from market_data_cache table.
    """
    available: bool = Field(..., description="Whether sector exposure data is available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    calculation_date: Optional[str] = Field(None, description="ISO date of calculation")
    data: Optional[SectorExposureData] = Field(None, description="Sector exposure data when available")
    metadata: Optional[Dict[str, Union[str, int]]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
                "calculation_date": "2025-10-17",
                "data": {
                    "portfolio_weights": {
                        "Technology": 0.45,
                        "Healthcare": 0.20,
                        "Financials": 0.15,
                        "Consumer Discretionary": 0.10,
                        "Industrials": 0.10
                    },
                    "benchmark_weights": {
                        "Technology": 0.28,
                        "Healthcare": 0.13,
                        "Financials": 0.11,
                        "Consumer Discretionary": 0.10,
                        "Industrials": 0.08
                    },
                    "over_underweight": {
                        "Technology": 0.17,
                        "Healthcare": 0.07,
                        "Financials": 0.04,
                        "Consumer Discretionary": 0.0,
                        "Industrials": 0.02
                    },
                    "largest_overweight": "Technology",
                    "largest_underweight": "Energy",
                    "total_portfolio_value": 1250000.00,
                    "positions_by_sector": {
                        "Technology": 8,
                        "Healthcare": 4,
                        "Financials": 3,
                        "Consumer Discretionary": 2,
                        "Industrials": 2
                    },
                    "unclassified_value": 0.0,
                    "unclassified_count": 0
                },
                "metadata": {
                    "benchmark": "SP500",
                    "benchmark_date": "2025-10-17"
                }
            }
        }


class ConcentrationMetricsData(BaseModel):
    """Portfolio concentration metrics"""
    hhi: float = Field(..., description="Herfindahl-Hirschman Index (0-10000, higher = more concentrated)")
    effective_num_positions: float = Field(..., description="Effective number of positions (10000 / HHI)")
    top_3_concentration: float = Field(..., description="Sum of top 3 position weights (0-1)")
    top_10_concentration: float = Field(..., description="Sum of top 10 position weights (0-1)")
    total_positions: int = Field(..., description="Total number of active positions")
    position_weights: Optional[Dict[str, float]] = Field(None, description="Individual position weights (optional)")


class ConcentrationMetricsResponse(BaseModel):
    """
    Portfolio concentration metrics response (Phase 1: Risk Metrics)

    Returns HHI, effective positions, and top-N concentration metrics.
    Measures portfolio diversification and concentration risk.
    """
    available: bool = Field(..., description="Whether concentration metrics are available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    calculation_date: Optional[str] = Field(None, description="ISO date of calculation")
    data: Optional[ConcentrationMetricsData] = Field(None, description="Concentration metrics when available")
    metadata: Optional[Dict[str, Union[str, int]]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
                "calculation_date": "2025-10-17",
                "data": {
                    "hhi": 625.0,
                    "effective_num_positions": 16.0,
                    "top_3_concentration": 0.35,
                    "top_10_concentration": 0.75,
                    "total_positions": 21,
                    "position_weights": None
                },
                "metadata": {
                    "calculation_method": "market_value_weighted",
                    "interpretation": "Well diversified (HHI < 1500)"
                }
            }
        }


class VolatilityMetricsData(BaseModel):
    """Portfolio volatility metrics with HAR forecasting"""
    realized_volatility_21d: float = Field(..., description="21-day (~1 month) realized volatility")
    realized_volatility_63d: float = Field(..., description="63-day (~3 months) realized volatility")
    expected_volatility_21d: Optional[float] = Field(None, description="HAR model forecast for next 21 trading days")
    volatility_trend: Optional[str] = Field(None, description="Volatility direction: increasing, decreasing, or stable")
    volatility_percentile: Optional[float] = Field(None, description="Current volatility percentile vs 1-year history (0-1)")


class VolatilityMetricsResponse(BaseModel):
    """
    Portfolio volatility metrics response (Phase 2: Risk Metrics)

    Returns realized and expected volatility with trend analysis.
    Uses HAR (Heterogeneous Autoregressive) model for forecasting.
    """
    available: bool = Field(..., description="Whether volatility metrics are available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    calculation_date: Optional[str] = Field(None, description="ISO date of calculation")
    data: Optional[VolatilityMetricsData] = Field(None, description="Volatility metrics when available")
    metadata: Optional[Dict[str, Union[str, int]]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
                "calculation_date": "2025-10-17",
                "data": {
                    "realized_volatility_21d": 0.28,
                    "realized_volatility_63d": 0.32,
                    "expected_volatility_21d": 0.30,
                    "volatility_trend": "decreasing",
                    "volatility_percentile": 0.65
                },
                "metadata": {
                    "forecast_model": "HAR",
                    "trading_day_windows": "21d, 63d"
                }
            }
        }


class PositionBetaComparison(BaseModel):
    """Beta comparison for a single position"""
    symbol: str = Field(..., description="Position symbol")
    position_id: str = Field(..., description="Position UUID")
    market_beta: Optional[float] = Field(None, description="Market beta from company profile (data provider)")
    calculated_beta: Optional[float] = Field(None, description="Our calculated beta from OLS regression")
    beta_r_squared: Optional[float] = Field(None, description="R-squared for calculated beta")
    calculation_date: Optional[str] = Field(None, description="Date of beta calculation")
    observations: Optional[int] = Field(None, description="Number of data points in regression")
    beta_difference: Optional[float] = Field(None, description="Difference between calculated and market beta")


class MarketBetaComparisonResponse(BaseModel):
    """
    Market beta comparison response (Phase 0: Risk Metrics)

    Returns comparison between market betas (from data provider) and our calculated betas
    for each position in the portfolio.
    """
    available: bool = Field(..., description="Whether beta comparison data is available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    positions: Optional[List[PositionBetaComparison]] = Field(None, description="Beta comparison for each position")
    metadata: Optional[Dict[str, Union[str, int]]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "available": True,
                "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
                "positions": [
                    {
                        "symbol": "AAPL",
                        "position_id": "e5e29f33-ac9f-411b-9494-bff119f435b2",
                        "market_beta": 1.25,
                        "calculated_beta": 1.18,
                        "beta_r_squared": 0.85,
                        "calculation_date": "2025-10-17",
                        "observations": 90,
                        "beta_difference": -0.07
                    },
                    {
                        "symbol": "MSFT",
                        "position_id": "f6f39044-bd0f-522c-a5a5-c00229g546c3",
                        "market_beta": 0.95,
                        "calculated_beta": 0.92,
                        "beta_r_squared": 0.88,
                        "calculation_date": "2025-10-17",
                        "observations": 90,
                        "beta_difference": -0.03
                    }
                ],
                "metadata": {
                    "total_positions": 18,
                    "positions_with_data": 15
                }
            }
        }
