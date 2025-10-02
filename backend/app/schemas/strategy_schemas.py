"""
Pydantic schemas for Strategy API requests and responses
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models import StrategyType


class StrategyBase(BaseModel):
    """Base strategy schema"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    strategy_type: StrategyType = StrategyType.STANDALONE


class CreateStrategyRequest(StrategyBase):
    """Request schema for creating a strategy"""
    portfolio_id: UUID
    position_ids: Optional[List[UUID]] = None


class UpdateStrategyRequest(BaseModel):
    """Request schema for updating a strategy"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    strategy_type: Optional[StrategyType] = None


class CombinePositionsRequest(BaseModel):
    """Request schema for combining positions into a strategy"""
    position_ids: List[UUID] = Field(..., min_length=2)
    strategy_name: str = Field(..., min_length=1, max_length=200)
    strategy_type: StrategyType
    portfolio_id: UUID
    description: Optional[str] = None


class PositionInStrategy(BaseModel):
    """Position information within a strategy"""
    id: UUID
    symbol: str
    position_type: str
    quantity: Decimal
    entry_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class StrategyMetricsResponse(BaseModel):
    """Strategy metrics response"""
    id: UUID
    strategy_id: UUID
    calculation_date: datetime
    net_delta: Optional[float] = None
    net_gamma: Optional[float] = None
    net_theta: Optional[float] = None
    net_vega: Optional[float] = None
    total_pnl: Optional[float] = None
    max_profit: Optional[float] = None
    max_loss: Optional[float] = None
    break_even_points: Optional[List[float]] = None

    model_config = ConfigDict(from_attributes=True)


class StrategyResponse(StrategyBase):
    """Response schema for a strategy"""
    id: UUID
    portfolio_id: UUID
    is_synthetic: bool
    net_exposure: Optional[float] = None
    total_cost_basis: Optional[float] = None
    total_market_value: Optional[float] = None  # Sum of all position market values
    direction: Optional[str] = None  # LONG, SHORT, LC, LP, SC, SP, NEUTRAL
    primary_investment_class: Optional[str] = None  # PUBLIC, OPTIONS, PRIVATE
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    positions: Optional[List[PositionInStrategy]] = None
    position_count: int = 0
    metrics: Optional[StrategyMetricsResponse] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('position_count', mode='before')
    @classmethod
    def calculate_position_count(cls, v, values):
        """Calculate position count from positions if available"""
        if 'positions' in values.data and values.data['positions']:
            return len(values.data['positions'])
        return v


class StrategyListResponse(BaseModel):
    """Response for listing strategies"""
    strategies: List[StrategyResponse]
    total: int
    limit: int
    offset: int


class DetectedStrategyPattern(BaseModel):
    """A detected strategy pattern"""
    type: StrategyType
    positions: List[UUID]
    confidence: float = Field(..., ge=0, le=1)
    description: str


class DetectedStrategiesResponse(BaseModel):
    """Response for strategy detection"""
    portfolio_id: UUID
    detected_patterns: List[DetectedStrategyPattern]
    total_patterns: int