"""
Pydantic schemas for Portfolio CRUD operations

Supports multi-portfolio functionality with account types and activation status.
Created: 2025-11-01
"""
from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, validator


class PortfolioCreateRequest(BaseModel):
    """Request schema for creating a new portfolio."""

    name: str = Field(..., min_length=1, max_length=255, description="Portfolio display name")
    account_name: str = Field(..., min_length=1, max_length=100, description="Account name (e.g., 'Fidelity IRA')")
    account_type: str = Field(
        default="taxable",
        description="Account type: taxable, ira, roth_ira, 401k, 529, hsa, trust, other"
    )
    description: Optional[str] = Field(None, max_length=1000, description="Portfolio description")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code")
    equity_balance: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Initial equity balance (NAV)"
    )
    is_active: bool = Field(default=True, description="Whether portfolio is active")

    @validator('account_type')
    def validate_account_type(cls, v):
        """Validate account type is one of the allowed values."""
        allowed_types = ['taxable', 'ira', 'roth_ira', '401k', '403b', '529', 'hsa', 'trust', 'other']
        if v.lower() not in allowed_types:
            raise ValueError(f"account_type must be one of: {', '.join(allowed_types)}")
        return v.lower()

    @validator('currency')
    def validate_currency(cls, v):
        """Ensure currency is uppercase."""
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Retirement Account",
                "account_name": "Fidelity IRA",
                "account_type": "ira",
                "description": "Traditional IRA at Fidelity",
                "currency": "USD",
                "equity_balance": 100000.00,
                "is_active": True
            }
        }


class PortfolioUpdateRequest(BaseModel):
    """Request schema for updating an existing portfolio."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    account_name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_type: Optional[str] = None
    description: Optional[str] = Field(None, max_length=1000)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    equity_balance: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @validator('account_type')
    def validate_account_type(cls, v):
        """Validate account type if provided."""
        if v is None:
            return v
        allowed_types = ['taxable', 'ira', 'roth_ira', '401k', '403b', '529', 'hsa', 'trust', 'other']
        if v.lower() not in allowed_types:
            raise ValueError(f"account_type must be one of: {', '.join(allowed_types)}")
        return v.lower()

    @validator('currency')
    def validate_currency(cls, v):
        """Ensure currency is uppercase if provided."""
        if v is None:
            return v
        return v.upper()

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Account Name",
                "account_name": "Schwab Taxable",
                "is_active": False
            }
        }


class PortfolioResponse(BaseModel):
    """Response schema for portfolio data."""

    id: UUID
    user_id: UUID
    name: str
    account_name: str
    account_type: str
    description: Optional[str]
    currency: str
    equity_balance: Optional[Decimal]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    # Calculated fields
    position_count: Optional[int] = 0
    net_asset_value: Optional[Decimal] = None
    total_value: Optional[Decimal] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "660e8400-e29b-41d4-a716-446655440000",
                "name": "My Retirement Account",
                "account_name": "Fidelity IRA",
                "account_type": "ira",
                "description": "Traditional IRA at Fidelity",
                "currency": "USD",
                "equity_balance": 100000.00,
                "is_active": True,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "deleted_at": None,
                "position_count": 15,
                "net_asset_value": 125000.00,
                "total_value": 125000.00
            }
        }


class PortfolioListResponse(BaseModel):
    """Response schema for portfolio list."""

    portfolios: list[PortfolioResponse]
    total_count: int
    active_count: int
    net_asset_value: Decimal
    total_value: Decimal

    class Config:
        json_schema_extra = {
            "example": {
                "portfolios": [],
                "total_count": 3,
                "active_count": 2,
                "net_asset_value": 1000000.00,
                "total_value": 1000000.00
            }
        }


class PortfolioDeleteResponse(BaseModel):
    """Response schema for portfolio deletion."""

    success: bool
    message: str
    portfolio_id: UUID
    deleted_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Portfolio soft deleted successfully",
                "portfolio_id": "550e8400-e29b-41d4-a716-446655440000",
                "deleted_at": "2025-01-01T00:00:00Z"
            }
        }


class TriggerCalculationsResponse(BaseModel):
    """Response schema for triggering portfolio batch calculations."""

    portfolio_id: str
    batch_run_id: str
    status: str
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "754e6704-6cad-5fbd-9881-e9c1ae917b5b",
                "batch_run_id": "ba5e8400-e29b-41d4-a716-446655440000",
                "status": "started",
                "message": "Batch calculations started successfully. Poll status at /api/v1/portfolios/{portfolio_id}/batch-status/{batch_run_id}"
            }
        }


class BatchStatusResponse(BaseModel):
    """Response schema for batch processing status."""

    status: str  # "idle", "running", "completed", "failed"
    batch_run_id: str
    portfolio_id: str
    started_at: str
    triggered_by: str
    elapsed_seconds: int

    class Config:
        json_schema_extra = {
            "example": {
                "status": "running",
                "batch_run_id": "ba5e8400-e29b-41d4-a716-446655440000",
                "portfolio_id": "754e6704-6cad-5fbd-9881-e9c1ae917b5b",
                "started_at": "2025-11-16T10:36:33Z",
                "triggered_by": "user@example.com",
                "elapsed_seconds": 15
            }
        }
