"""
Pydantic schemas for equity change endpoints.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import Field, computed_field, field_validator

from app.models.equity_changes import EquityChangeType
from app.schemas.base import BaseSchema


class EquityChangeBase(BaseSchema):
    """Shared fields for creating/updating equity changes."""

    change_type: EquityChangeType = Field(..., description="CONTRIBUTION or WITHDRAWAL")
    amount: Decimal = Field(..., gt=0, description="Amount of the contribution/withdrawal")
    change_date: date = Field(..., description="Effective date of the change (no future dates)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional description")

    @field_validator("change_date")
    @classmethod
    def validate_change_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Change date cannot be in the future")
        return value


class EquityChangeCreateRequest(EquityChangeBase):
    """Request payload for creating an equity change."""
    pass


class EquityChangeUpdateRequest(BaseSchema):
    """Request payload for updating an equity change (within edit window)."""

    amount: Optional[Decimal] = Field(None, gt=0)
    change_date: Optional[date] = None
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("change_date")
    @classmethod
    def validate_change_date(cls, value: Optional[date]) -> Optional[date]:
        if value and value > date.today():
            raise ValueError("Change date cannot be in the future")
        return value


class EquityChangeResponse(EquityChangeBase):
    """Response payload for an equity change."""

    id: UUID
    portfolio_id: UUID
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    @computed_field(return_type=datetime)
    def editable_until(self) -> datetime:
        """Timestamp when editing is no longer allowed (7-day window)."""
        return self.created_at + timedelta(days=7)

    @computed_field(return_type=datetime)
    def deletable_until(self) -> datetime:
        """Timestamp when deletion is no longer allowed (30-day window)."""
        return self.created_at + timedelta(days=30)

    @computed_field(return_type=bool)
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class EquityChangeListResponse(BaseSchema):
    """Paginated list of equity changes."""

    items: List[EquityChangeResponse]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class EquityChangeSummaryPeriod(BaseSchema):
    """Aggregated flow metrics for a given period."""

    contributions: Decimal
    withdrawals: Decimal
    net_flow: Decimal


class EquityChangeSummaryResponse(BaseSchema):
    """Summary data for hero metrics and quick stats."""

    portfolio_id: UUID
    total_contributions: Decimal
    total_withdrawals: Decimal
    net_flow: Decimal
    last_change: Optional[EquityChangeResponse] = None
    periods: dict = Field(default_factory=dict)


class EquityChangeExportRequest(BaseSchema):
    """Query parameters for export endpoint."""

    format: str = Field(default="csv", description="Export format (currently only CSV is supported)")
    start_date: Optional[date] = Field(None, description="Filter start date")
    end_date: Optional[date] = Field(None, description="Filter end date")

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        allowed = {"csv"}
        if value.lower() not in allowed:
            raise ValueError(f"Export format must be one of: {', '.join(sorted(allowed))}")
        return value.lower()
