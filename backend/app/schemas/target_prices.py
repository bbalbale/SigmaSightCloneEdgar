"""
Pydantic schemas for Target Prices
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator


class TargetPriceBase(BaseModel):
    """Base schema for target prices"""
    symbol: str = Field(..., max_length=20, description="Security symbol")
    position_type: Optional[str] = Field(None, description="Position type: LONG, SHORT, LC, LP, SC, SP")

    target_price_eoy: Optional[Decimal] = Field(None, ge=0, description="End-of-year target price")
    target_price_next_year: Optional[Decimal] = Field(None, ge=0, description="Next year target price")
    downside_target_price: Optional[Decimal] = Field(None, ge=0, description="Downside scenario target price")

    current_price: Decimal = Field(..., gt=0, description="Current market price")

    @validator('position_type')
    def validate_position_type(cls, v):
        if v and v not in ['LONG', 'SHORT', 'LC', 'LP', 'SC', 'SP']:
            raise ValueError('Invalid position type')
        return v


class TargetPriceCreate(TargetPriceBase):
    """Schema for creating target prices"""
    position_id: Optional[UUID] = Field(None, description="Optional link to specific position")


class TargetPriceUpdate(BaseModel):
    """Schema for updating target prices"""
    target_price_eoy: Optional[Decimal] = Field(None, ge=0)
    target_price_next_year: Optional[Decimal] = Field(None, ge=0)
    downside_target_price: Optional[Decimal] = Field(None, ge=0)

    current_price: Optional[Decimal] = Field(None, gt=0)


class TargetPriceResponse(TargetPriceBase):
    """Schema for target price responses"""
    id: UUID
    portfolio_id: UUID
    position_id: Optional[UUID]

    # Calculated returns
    expected_return_eoy: Optional[Decimal] = Field(None, description="Expected return to EOY target (%)")
    expected_return_next_year: Optional[Decimal] = Field(None, description="Expected return to next year target (%)")
    downside_return: Optional[Decimal] = Field(None, description="Downside scenario return (%)")

    # Risk metrics
    position_weight: Optional[Decimal] = Field(None, description="Position weight in portfolio (%)")
    contribution_to_portfolio_return: Optional[Decimal] = Field(None, description="Contribution to portfolio return (%)")
    contribution_to_portfolio_risk: Optional[Decimal] = Field(None, description="Contribution to portfolio risk (%)")

    # Metadata
    price_updated_at: Optional[datetime]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }


class TargetPriceBulkCreate(BaseModel):
    """Schema for bulk creating target prices"""
    target_prices: List[TargetPriceCreate]


class TargetPriceBulkUpdate(BaseModel):
    """Schema for bulk updating target prices"""
    updates: List[dict] = Field(..., description="List of {symbol: str, position_type: str, ...updates}")


class PortfolioTargetPriceSummary(BaseModel):
    """Summary of all target prices for a portfolio"""
    portfolio_id: UUID
    portfolio_name: str

    total_positions: int
    positions_with_targets: int
    coverage_percentage: Decimal

    # Weighted averages
    weighted_expected_return_eoy: Optional[Decimal] = Field(None, description="Portfolio-weighted EOY return (%)")
    weighted_expected_return_next_year: Optional[Decimal] = Field(None, description="Portfolio-weighted next year return (%)")
    weighted_downside_return: Optional[Decimal] = Field(None, description="Portfolio-weighted downside return (%)")

    # Risk metrics
    expected_sharpe_ratio: Optional[Decimal] = Field(None, description="Expected Sharpe ratio")
    expected_sortino_ratio: Optional[Decimal] = Field(None, description="Expected Sortino ratio")

    # Position details
    target_prices: List[TargetPriceResponse]

    # Metadata
    last_updated: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None
        }


class TargetPriceImportCSV(BaseModel):
    """Schema for importing target prices from CSV"""
    csv_content: str = Field(..., description="CSV content with headers: symbol,position_type,target_eoy,target_next_year,downside")
    update_existing: bool = Field(False, description="Update existing target prices if found")


class TargetPriceExportRequest(BaseModel):
    """Schema for exporting target prices"""
    format: str = Field("csv", description="Export format: csv, json")
    include_metadata: bool = Field(False, description="Include metadata fields")