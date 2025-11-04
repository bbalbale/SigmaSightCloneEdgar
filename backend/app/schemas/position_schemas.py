"""
Pydantic schemas for Position API requests and responses.

Position Management Phase 1 - Nov 3, 2025
"""
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.models.positions import PositionType


class PositionBase(BaseModel):
    """Base position schema shared across requests and responses."""

    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    quantity: Decimal = Field(..., description="Number of shares/contracts")
    avg_cost: Decimal = Field(..., gt=0, description="Average cost per share")
    position_type: PositionType = Field(..., description="Position type (LONG, SHORT, LC, LP, SC, SP)")
    investment_class: str = Field(..., description="Investment class (PUBLIC, OPTIONS, PRIVATE)")
    notes: Optional[str] = Field(None, description="User notes")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        """Ensure symbol is uppercase and trimmed."""
        return value.upper().strip()


class CreatePositionRequest(PositionBase):
    """Payload for creating a single position."""

    investment_subtype: Optional[str] = Field(None, description="Investment subtype (STOCK, ETF, etc.)")
    entry_date: Optional[date] = Field(None, description="Entry date (defaults to today)")

    # Option-specific fields
    underlying_symbol: Optional[str] = Field(None, description="Underlying symbol for options")
    strike_price: Optional[Decimal] = Field(None, description="Strike price for options")
    expiration_date: Optional[date] = Field(None, description="Expiration date for options")


class BulkCreatePositionsRequest(BaseModel):
    """Payload for bulk creating positions."""

    portfolio_id: UUID = Field(..., description="Portfolio to add positions to")
    positions: List[CreatePositionRequest] = Field(..., min_length=1, description="List of positions to create")


class UpdatePositionRequest(BaseModel):
    """Payload for updating position fields."""

    quantity: Optional[Decimal] = Field(None, description="New quantity")
    avg_cost: Optional[Decimal] = Field(None, gt=0, description="New average cost")
    position_type: Optional[PositionType] = Field(None, description="New position type")
    notes: Optional[str] = Field(None, description="New notes")
    symbol: Optional[str] = Field(None, min_length=1, max_length=20, description="New symbol (restricted)")
    exit_price: Optional[Decimal] = Field(None, gt=0, description="Exit price when closing position")
    exit_date: Optional[date] = Field(None, description="Exit date when closing position")
    entry_price: Optional[Decimal] = Field(None, gt=0, description="Corrected entry price")
    close_quantity: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Quantity being closed (required for partial/full exits)"
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: Optional[str]) -> Optional[str]:
        """Ensure symbol is uppercase and trimmed if provided."""
        return value.upper().strip() if value else None

    @field_validator("exit_date")
    @classmethod
    def validate_exit_date(cls, value: Optional[date]) -> Optional[date]:
        """Ensure exit date is not in the future."""
        if value and value > date.today():
            raise ValueError("Exit date cannot be in the future")
        return value

    @field_validator("close_quantity")
    @classmethod
    def validate_close_quantity(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure partial-close quantities are positive."""
        if value is not None and value <= 0:
            raise ValueError("close_quantity must be greater than zero")
        return value


class BulkDeletePositionsRequest(BaseModel):
    """Payload for bulk deleting positions."""

    position_ids: List[UUID] = Field(..., min_length=1, description="List of position IDs to delete")
    force_hard_delete: bool = Field(False, description="Force hard delete (Reverse Addition)")


class PositionResponse(BaseModel):
    """Position representation returned from the API."""

    id: UUID
    portfolio_id: UUID
    symbol: str
    quantity: Decimal
    entry_price: Decimal  # Maps to avg_cost
    entry_date: date
    position_type: PositionType
    investment_class: str
    investment_subtype: Optional[str] = None
    notes: Optional[str] = None

    # Option-specific fields
    underlying_symbol: Optional[str] = None
    strike_price: Optional[Decimal] = None
    expiration_date: Optional[date] = None

    # Market data (may be None if not yet calculated)
    last_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None

    # Exit data (for closed positions)
    exit_price: Optional[Decimal] = None
    exit_date: Optional[date] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BulkPositionsResponse(BaseModel):
    """Response for bulk create operation."""

    success: bool
    count: int
    positions: List[PositionResponse]


class DeletePositionResponse(BaseModel):
    """Response for delete operation."""

    deleted: bool
    position_id: UUID
    symbol: str
    type: str  # "soft_delete" or "hard_delete"
    deleted_at: Optional[datetime] = None
    reason: Optional[str] = None


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operation."""

    deleted: bool
    count: int
    positions: List[str]  # List of symbols deleted


class DuplicateCheckResponse(BaseModel):
    """Response for duplicate check."""

    has_duplicates: bool
    existing_positions: List[PositionResponse]
    tags_to_inherit: List[UUID] = []


class SymbolValidationResponse(BaseModel):
    """Response for symbol validation."""

    valid: bool
    symbol: str
    message: Optional[str] = None
