"""
Analytics API Response Schemas

Pydantic models for portfolio analytics endpoints including portfolio overview,
risk metrics, and performance data.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Union, List
from datetime import datetime


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
    total_value: float = Field(..., description="Total portfolio value including cash")
    cash_balance: float = Field(..., description="Available cash balance")
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
    metadata: Optional[Dict[str, Union[str, List[str]]]] = Field(None, description="Additional metadata, including scenarios_requested if provided")
        }


class PortfolioFactorItem(BaseModel):
    name: str = Field(..., description="Factor name")
    beta: float = Field(..., description="Portfolio beta to the factor")
    exposure_dollar: Optional[float] = Field(None, description="Dollar exposure to the factor, if available")


class PortfolioFactorExposuresResponse(BaseModel):
    available: bool = Field(..., description="Whether factor exposures are available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    calculation_date: Optional[str] = Field(None, description="ISO date of the factor exposure calculation")
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
