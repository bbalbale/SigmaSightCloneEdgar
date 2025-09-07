"""
Analytics API Response Schemas

Pydantic models for portfolio analytics endpoints including portfolio overview,
risk metrics, and performance data.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Union
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
                        "NVDA": {"AAPL": 0.75, "NVDA": 0.68, "NVDA": 1.0}
                    },
                    "average_correlation": 0.75
                }
            }
        }