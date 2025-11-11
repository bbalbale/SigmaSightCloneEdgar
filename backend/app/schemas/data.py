"""
Pydantic schemas for Agent-optimized data endpoints
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
from app.schemas.base import BaseSchema


class MetaInfo(BaseModel):
    """Common meta object for all agent responses"""
    as_of: datetime
    requested: Dict[str, Any]
    applied: Dict[str, Any]
    limits: Dict[str, int]
    rows_returned: int
    truncated: bool = False
    suggested_params: Optional[Dict[str, Any]] = None


class PositionSummary(BaseSchema):
    """Individual position data summary"""
    position_id: UUID
    symbol: str
    quantity: float
    market_value: float
    weight: float
    pnl_dollar: float
    pnl_percent: float
    position_type: str  # stock, option, etf, mutual_fund


class TopPositionsResponse(BaseSchema):
    """Response for top positions by value endpoint"""
    meta: MetaInfo
    positions: List[PositionSummary]
    portfolio_coverage: float  # % of portfolio value covered
    total_portfolio_value: float


class PortfolioSummaryResponse(BaseSchema):
    """Condensed portfolio overview response"""
    meta: MetaInfo
    portfolio_id: UUID
    portfolio_name: str
    net_asset_value: float
    total_value: float
    cash_balance: float
    positions_count: int
    top_holdings: List[PositionSummary]  # Top 5 by default
    asset_allocation: Dict[str, float]  # stock, option, etf, etc.


class HistoricalPricesRequest(BaseModel):
    """Request schema for historical prices with selection"""
    max_symbols: int = Field(default=5, le=5, ge=1, description="Maximum symbols to return")
    selection_method: str = Field(
        default="top_by_value",
        pattern="^(top_by_value|top_by_weight|all)$",
        description="Method for selecting symbols"
    )
    lookback_days: int = Field(default=180, le=180, ge=1, description="Days of history")
    include_factor_etfs: bool = Field(default=True, description="Include factor ETFs")
    date_format: str = Field(default="iso", pattern="^(iso|unix)$", description="Date format")


class PricePoint(BaseModel):
    """Single price point in historical data"""
    date: str  # ISO format or unix timestamp based on request
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int] = None


class HistoricalPricesResponse(BaseSchema):
    """Response for historical prices endpoint"""
    meta: MetaInfo
    symbols_included: List[str]
    symbols_excluded: List[str]  # If truncation occurred
    price_data: Dict[str, List[PricePoint]]
    factor_etfs: Optional[Dict[str, List[PricePoint]]] = None


class QuoteData(BaseModel):
    """Real-time quote data"""
    symbol: str
    last_price: float
    change: float
    change_percent: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    timestamp: datetime


class QuotesResponse(BaseSchema):
    """Response for real-time quotes endpoint"""
    meta: MetaInfo
    quotes: List[QuoteData]
    invalid_symbols: List[str]  # Symbols that couldn't be found


class DataQualityCheck(BaseModel):
    """Individual data quality check result"""
    check_name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class DataQualityResponse(BaseSchema):
    """Response for data quality assessment endpoint"""
    meta: MetaInfo
    portfolio_id: UUID
    overall_quality: str  # "excellent", "good", "fair", "poor"
    quality_score: float  # 0.0 to 1.0
    checks: List[DataQualityCheck]
    feasibility: Dict[str, bool]  # Which calculations are feasible
    recommendations: List[str]  # Suggestions for improving data quality
