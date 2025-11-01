# Backend Implementation Plan: Multi-Account Aggregation

**Feature:** Multi-Account Portfolio Aggregation
**Created:** 2025-11-01
**Status:** Planning Phase
**Estimated Effort:** 3-4 weeks (backend only)

---

## Overview

This document details the backend implementation plan for enabling users to manage multiple portfolios (accounts) and view aggregated analytics across all accounts.

**Core Approach:** Portfolio-as-Asset Aggregation
- Calculate risk metrics per portfolio (existing logic, unchanged)
- Aggregate using weighted averages (new service layer)
- No changes to existing calculation engines

---

## Phase 1: Database Schema Migration

### Current Schema
```python
# app/models/users.py

class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    # ONE-TO-ONE relationship (enforced)
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="user",
        uselist=False  # Enforces single portfolio
    )

class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    # UNIQUE constraint prevents multiple portfolios per user
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        unique=True  # ← REMOVE THIS
    )

    # Existing constraint
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_portfolios_user_id'),  # ← DROP THIS
        Index('ix_portfolios_deleted_at', 'deleted_at'),
    )
```

### Target Schema
```python
# app/models/users.py

class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    # ONE-TO-MANY relationship
    portfolios: Mapped[List["Portfolio"]] = relationship(
        "Portfolio",
        back_populates="user",
        uselist=True  # Allow multiple portfolios
    )

class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    # NO unique constraint
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )

    # Existing fields
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]]
    total_value: Mapped[Decimal]

    # NEW fields
    account_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="User-friendly account name (e.g., 'Fidelity', 'Schwab IRA')"
    )
    account_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="taxable",
        comment="Account type: taxable, ira, roth_ira, 401k, etc."
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Can hide accounts without deleting"
    )

    # Updated constraint (remove unique constraint on user_id)
    __table_args__ = (
        Index('ix_portfolios_deleted_at', 'deleted_at'),
        Index('ix_portfolios_user_id', 'user_id'),  # Add index for performance
    )
```

### Alembic Migration

**File:** `backend/alembic/versions/XXXX_add_multi_portfolio_support.py`

```python
"""Add multi-portfolio support

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-11-XX XX:XX:XX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'XXXX'
down_revision = 'YYYY'
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns
    op.add_column('portfolios', sa.Column('account_name', sa.String(), nullable=True))
    op.add_column('portfolios', sa.Column('account_type', sa.String(), nullable=True))
    op.add_column('portfolios', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))

    # Set default values for existing portfolios
    # Use existing 'name' as account_name
    op.execute("UPDATE portfolios SET account_name = name WHERE account_name IS NULL")
    op.execute("UPDATE portfolios SET account_type = 'taxable' WHERE account_type IS NULL")

    # Make account_name and account_type non-nullable
    op.alter_column('portfolios', 'account_name', nullable=False)
    op.alter_column('portfolios', 'account_type', nullable=False)

    # Drop unique constraint on user_id
    op.drop_constraint('uq_portfolios_user_id', 'portfolios', type_='unique')

    # Drop unique constraint from user_id column if it exists
    # (Some databases create implicit unique constraint)
    try:
        op.drop_index('ix_portfolios_user_id', table_name='portfolios')
    except:
        pass  # Index might not exist

    # Add performance index on user_id (non-unique)
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'], unique=False)

def downgrade():
    # Remove index
    op.drop_index('ix_portfolios_user_id', table_name='portfolios')

    # Re-add unique constraint
    op.create_unique_constraint('uq_portfolios_user_id', 'portfolios', ['user_id'])

    # Remove new columns
    op.drop_column('portfolios', 'is_active')
    op.drop_column('portfolios', 'account_type')
    op.drop_column('portfolios', 'account_name')
```

### Migration Testing

**Test Plan:**
1. **Backup database:** Create snapshot before migration
2. **Test in dev environment:**
   ```bash
   cd backend
   uv run alembic upgrade head
   ```
3. **Verify schema changes:**
   ```sql
   -- Check columns added
   SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_name = 'portfolios';

   -- Check constraints removed
   SELECT constraint_name, constraint_type
   FROM information_schema.table_constraints
   WHERE table_name = 'portfolios';
   ```
4. **Test data migration:**
   ```python
   # Verify existing portfolios have account_name set
   async with get_async_session() as db:
       stmt = select(Portfolio)
       result = await db.execute(stmt)
       portfolios = result.scalars().all()

       for p in portfolios:
           assert p.account_name is not None
           assert p.account_type is not None
           assert p.is_active is True
   ```
5. **Test creating multiple portfolios:**
   ```python
   # Should now work (previously would fail)
   user_id = UUID("...")

   portfolio_1 = Portfolio(
       id=uuid4(),
       user_id=user_id,
       name="Main Portfolio",
       account_name="Fidelity",
       account_type="taxable"
   )
   db.add(portfolio_1)

   portfolio_2 = Portfolio(
       id=uuid4(),
       user_id=user_id,  # Same user_id - now allowed!
       name="Retirement",
       account_name="Schwab IRA",
       account_type="ira"
   )
   db.add(portfolio_2)

   await db.commit()
   ```

---

## Phase 2: Service Layer - Aggregation Logic

### New Service: Portfolio Aggregation

**File:** `backend/app/services/portfolio_aggregation_service.py`

```python
"""
Portfolio Aggregation Service

Aggregates analytics across multiple portfolios using portfolio-as-asset approach.
Each portfolio is treated as a conceptual investment with its own risk metrics.
Aggregate metrics are calculated as weighted averages based on portfolio value.
"""
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import Portfolio
from app.services.portfolio_analytics_service import PortfolioAnalyticsService
from app.core.logging import get_logger

logger = get_logger(__name__)


class AggregateAnalytics:
    """Container for aggregate analytics across multiple portfolios"""

    def __init__(
        self,
        total_value: Decimal,
        total_positions: int,
        portfolio_count: int,
        weighted_beta: Optional[float] = None,
        weighted_volatility: Optional[float] = None,
        weighted_sharpe: Optional[float] = None,
        portfolio_breakdown: Optional[List[dict]] = None
    ):
        self.total_value = total_value
        self.total_positions = total_positions
        self.portfolio_count = portfolio_count
        self.weighted_beta = weighted_beta
        self.weighted_volatility = weighted_volatility
        self.weighted_sharpe = weighted_sharpe
        self.portfolio_breakdown = portfolio_breakdown or []


class PortfolioAggregationService:
    """Service for aggregating analytics across multiple portfolios"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics_service = PortfolioAnalyticsService(db)

    async def get_user_portfolios(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[Portfolio]:
        """
        Get all portfolios for a user.

        Args:
            user_id: User UUID
            active_only: Only return active portfolios (default True)

        Returns:
            List of Portfolio objects
        """
        stmt = select(Portfolio).where(Portfolio.user_id == user_id)

        if active_only:
            stmt = stmt.where(Portfolio.is_active == True)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_aggregate_analytics(
        self,
        user_id: UUID
    ) -> AggregateAnalytics:
        """
        Calculate aggregate analytics across all user's portfolios.

        Uses portfolio-as-asset approach:
        1. Get analytics for each portfolio (existing calculations)
        2. Calculate weighted averages based on portfolio values

        Args:
            user_id: User UUID

        Returns:
            AggregateAnalytics object with combined metrics
        """
        # Get all active portfolios
        portfolios = await self.get_user_portfolios(user_id, active_only=True)

        if not portfolios:
            logger.warning(f"No portfolios found for user {user_id}")
            return AggregateAnalytics(
                total_value=Decimal(0),
                total_positions=0,
                portfolio_count=0
            )

        # Calculate total value across all portfolios
        total_value = sum(p.total_value or Decimal(0) for p in portfolios)

        if total_value == 0:
            logger.warning(f"Total portfolio value is 0 for user {user_id}")
            return AggregateAnalytics(
                total_value=Decimal(0),
                total_positions=sum(len(p.positions) for p in portfolios),
                portfolio_count=len(portfolios)
            )

        # Get analytics for each portfolio
        portfolio_analytics = []
        total_positions = 0

        for portfolio in portfolios:
            # Get portfolio analytics (existing service)
            analytics = await self.analytics_service.get_portfolio_overview(
                portfolio.id
            )

            portfolio_analytics.append({
                'portfolio_id': portfolio.id,
                'account_name': portfolio.account_name,
                'account_type': portfolio.account_type,
                'value': portfolio.total_value,
                'weight': float(portfolio.total_value / total_value),
                'position_count': len(portfolio.positions),
                'beta': analytics.get('beta'),
                'volatility': analytics.get('volatility'),
                'sharpe_ratio': analytics.get('sharpe_ratio')
            })

            total_positions += len(portfolio.positions)

        # Calculate weighted averages
        weighted_beta = self._calculate_weighted_average(
            portfolio_analytics,
            'beta'
        )

        weighted_volatility = self._calculate_weighted_average(
            portfolio_analytics,
            'volatility'
        )

        weighted_sharpe = self._calculate_weighted_average(
            portfolio_analytics,
            'sharpe_ratio'
        )

        return AggregateAnalytics(
            total_value=total_value,
            total_positions=total_positions,
            portfolio_count=len(portfolios),
            weighted_beta=weighted_beta,
            weighted_volatility=weighted_volatility,
            weighted_sharpe=weighted_sharpe,
            portfolio_breakdown=portfolio_analytics
        )

    def _calculate_weighted_average(
        self,
        portfolio_analytics: List[dict],
        metric_key: str
    ) -> Optional[float]:
        """
        Calculate weighted average of a metric across portfolios.

        Formula: Σ(metric_i × weight_i)

        Args:
            portfolio_analytics: List of portfolio analytics dicts
            metric_key: Key of metric to average (e.g., 'beta', 'volatility')

        Returns:
            Weighted average or None if no data available
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for portfolio in portfolio_analytics:
            metric_value = portfolio.get(metric_key)
            weight = portfolio.get('weight', 0.0)

            if metric_value is not None and weight > 0:
                weighted_sum += metric_value * weight
                total_weight += weight

        if total_weight == 0:
            return None

        return weighted_sum / total_weight

    async def get_portfolio_breakdown(
        self,
        user_id: UUID
    ) -> List[dict]:
        """
        Get summary breakdown of all portfolios.

        Useful for displaying account breakdown in UI.

        Args:
            user_id: User UUID

        Returns:
            List of portfolio summaries with value, percentage, metrics
        """
        portfolios = await self.get_user_portfolios(user_id, active_only=True)

        if not portfolios:
            return []

        total_value = sum(p.total_value or Decimal(0) for p in portfolios)

        breakdown = []
        for portfolio in portfolios:
            value = portfolio.total_value or Decimal(0)
            percentage = float(value / total_value * 100) if total_value > 0 else 0.0

            breakdown.append({
                'portfolio_id': str(portfolio.id),
                'account_name': portfolio.account_name,
                'account_type': portfolio.account_type,
                'value': float(value),
                'percentage': percentage,
                'position_count': len(portfolio.positions),
                'is_active': portfolio.is_active
            })

        # Sort by value (largest first)
        breakdown.sort(key=lambda x: x['value'], reverse=True)

        return breakdown
```

### Unit Tests

**File:** `backend/tests/test_portfolio_aggregation_service.py`

```python
import pytest
from decimal import Decimal
from uuid import uuid4

from app.services.portfolio_aggregation_service import (
    PortfolioAggregationService,
    AggregateAnalytics
)
from app.models.users import User, Portfolio


@pytest.mark.asyncio
async def test_aggregate_analytics_calculation(db_session):
    """Test weighted average calculation for aggregate analytics"""

    # Create user with 3 portfolios
    user = User(id=uuid4(), email="test@example.com", ...)
    db_session.add(user)

    portfolio_a = Portfolio(
        id=uuid4(),
        user_id=user.id,
        name="Portfolio A",
        account_name="Fidelity",
        account_type="taxable",
        total_value=Decimal("500000")  # 50% weight
    )
    db_session.add(portfolio_a)

    portfolio_b = Portfolio(
        id=uuid4(),
        user_id=user.id,
        name="Portfolio B",
        account_name="Schwab IRA",
        account_type="ira",
        total_value=Decimal("300000")  # 30% weight
    )
    db_session.add(portfolio_b)

    portfolio_c = Portfolio(
        id=uuid4(),
        user_id=user.id,
        name="Portfolio C",
        account_name="401k",
        account_type="401k",
        total_value=Decimal("200000")  # 20% weight
    )
    db_session.add(portfolio_c)

    await db_session.commit()

    # Mock portfolio analytics
    # Portfolio A: Beta 1.2, Vol 20%
    # Portfolio B: Beta 0.8, Vol 15%
    # Portfolio C: Beta 1.0, Vol 18%

    service = PortfolioAggregationService(db_session)
    aggregate = await service.get_aggregate_analytics(user.id)

    # Verify total value
    assert aggregate.total_value == Decimal("1000000")
    assert aggregate.portfolio_count == 3

    # Verify weighted beta
    # (1.2 * 0.5) + (0.8 * 0.3) + (1.0 * 0.2) = 1.04
    expected_beta = (1.2 * 0.5) + (0.8 * 0.3) + (1.0 * 0.2)
    assert abs(aggregate.weighted_beta - expected_beta) < 0.001

    # Verify weighted volatility
    # (20% * 0.5) + (15% * 0.3) + (18% * 0.2) = 18.1%
    expected_vol = (20 * 0.5) + (15 * 0.3) + (18 * 0.2)
    assert abs(aggregate.weighted_volatility - expected_vol) < 0.1


@pytest.mark.asyncio
async def test_portfolio_breakdown(db_session):
    """Test portfolio breakdown summary"""

    user = User(id=uuid4(), email="test@example.com", ...)
    db_session.add(user)

    # Create portfolios with different values
    portfolios_data = [
        ("Fidelity", "taxable", 500000),
        ("Schwab IRA", "ira", 300000),
        ("401k", "401k", 200000)
    ]

    for account_name, account_type, value in portfolios_data:
        portfolio = Portfolio(
            id=uuid4(),
            user_id=user.id,
            name=account_name,
            account_name=account_name,
            account_type=account_type,
            total_value=Decimal(value)
        )
        db_session.add(portfolio)

    await db_session.commit()

    service = PortfolioAggregationService(db_session)
    breakdown = await service.get_portfolio_breakdown(user.id)

    assert len(breakdown) == 3

    # Check sorted by value (largest first)
    assert breakdown[0]['account_name'] == 'Fidelity'
    assert breakdown[0]['percentage'] == 50.0
    assert breakdown[1]['account_name'] == 'Schwab IRA'
    assert breakdown[1]['percentage'] == 30.0
    assert breakdown[2]['account_name'] == '401k'
    assert breakdown[2]['percentage'] == 20.0
```

---

## Phase 3: API Endpoints

### New Endpoints

#### 1. Create Portfolio

**Endpoint:** `POST /api/v1/portfolios`

**File:** `backend/app/api/v1/portfolios.py` (NEW FILE)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID, uuid4

from app.core.dependencies import get_current_user, CurrentUser, get_async_session
from app.models.users import Portfolio
from app.services.portfolio_aggregation_service import PortfolioAggregationService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


class CreatePortfolioRequest(BaseModel):
    account_name: str = Field(..., min_length=1, max_length=100)
    account_type: str = Field(default="taxable")
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "account_name": "Schwab IRA",
                "account_type": "ira",
                "description": "Traditional IRA at Schwab"
            }
        }


class PortfolioResponse(BaseModel):
    id: str
    user_id: str
    name: str
    account_name: str
    account_type: str
    description: Optional[str]
    total_value: float
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    request: CreatePortfolioRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new portfolio (account) for the current user.

    Users can have multiple portfolios to track different brokerage accounts.
    Maximum 20 portfolios per user.

    Args:
        request: Portfolio creation data
        current_user: Authenticated user
        db: Database session

    Returns:
        Created portfolio

    Raises:
        400: If user has reached maximum portfolio limit
    """
    # Check portfolio limit
    service = PortfolioAggregationService(db)
    existing_portfolios = await service.get_user_portfolios(
        current_user.id,
        active_only=False
    )

    if len(existing_portfolios) >= 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 20 portfolios per user reached"
        )

    # Create portfolio
    portfolio = Portfolio(
        id=uuid4(),
        user_id=current_user.id,
        name=request.account_name,  # Use account_name as name for backward compat
        account_name=request.account_name,
        account_type=request.account_type,
        description=request.description,
        total_value=Decimal(0),
        equity_balance=Decimal(0),
        is_active=True
    )

    db.add(portfolio)
    await db.commit()
    await db.refresh(portfolio)

    return portfolio


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: UUID,
    request: CreatePortfolioRequest,  # Reuse same schema
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update portfolio account name, type, or description.

    Args:
        portfolio_id: Portfolio UUID
        request: Updated portfolio data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated portfolio

    Raises:
        404: Portfolio not found or not owned by user
    """
    # Validate ownership
    from app.core.dependencies import validate_portfolio_ownership
    await validate_portfolio_ownership(db, portfolio_id, current_user.id)

    # Get portfolio
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    result = await db.execute(stmt)
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found"
        )

    # Update fields
    portfolio.account_name = request.account_name
    portfolio.account_type = request.account_type
    portfolio.description = request.description
    portfolio.name = request.account_name  # Keep name in sync

    await db.commit()
    await db.refresh(portfolio)

    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete (deactivate) a portfolio.

    Soft delete - marks portfolio as inactive but preserves data.
    Positions remain in database for historical tracking.

    Args:
        portfolio_id: Portfolio UUID
        current_user: Authenticated user
        db: Database session

    Raises:
        404: Portfolio not found or not owned by user
        400: Cannot delete last active portfolio
    """
    # Validate ownership
    from app.core.dependencies import validate_portfolio_ownership
    await validate_portfolio_ownership(db, portfolio_id, current_user.id)

    # Check not deleting last portfolio
    service = PortfolioAggregationService(db)
    active_portfolios = await service.get_user_portfolios(
        current_user.id,
        active_only=True
    )

    if len(active_portfolios) == 1 and active_portfolios[0].id == portfolio_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your only active portfolio"
        )

    # Get portfolio
    stmt = select(Portfolio).where(Portfolio.id == portfolio_id)
    result = await db.execute(stmt)
    portfolio = result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} not found"
        )

    # Soft delete
    portfolio.is_active = False

    await db.commit()

    return None
```

#### 2. Get Aggregate Analytics

**Endpoint:** `GET /api/v1/analytics/aggregate`

**File:** `backend/app/api/v1/analytics.py` (ADD TO EXISTING FILE)

```python
@router.get("/aggregate")
async def get_aggregate_analytics(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get aggregate analytics across all user's portfolios.

    Calculates weighted averages of risk metrics treating each portfolio
    as a conceptual asset.

    Returns:
        {
            "total_value": 1000000.00,
            "total_positions": 50,
            "portfolio_count": 3,
            "weighted_beta": 1.04,
            "weighted_volatility": 18.1,
            "weighted_sharpe": 1.32,
            "portfolio_breakdown": [
                {
                    "portfolio_id": "...",
                    "account_name": "Fidelity",
                    "value": 500000.00,
                    "weight": 0.5,
                    "beta": 1.2,
                    "volatility": 20.0
                },
                ...
            ]
        }
    """
    service = PortfolioAggregationService(db)
    aggregate = await service.get_aggregate_analytics(current_user.id)

    return {
        "total_value": float(aggregate.total_value),
        "total_positions": aggregate.total_positions,
        "portfolio_count": aggregate.portfolio_count,
        "weighted_beta": aggregate.weighted_beta,
        "weighted_volatility": aggregate.weighted_volatility,
        "weighted_sharpe": aggregate.weighted_sharpe,
        "portfolio_breakdown": aggregate.portfolio_breakdown
    }


@router.get("/portfolio-breakdown")
async def get_portfolio_breakdown(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get summary breakdown of all user's portfolios.

    Useful for displaying account breakdown in UI.

    Returns:
        [
            {
                "portfolio_id": "...",
                "account_name": "Fidelity",
                "account_type": "taxable",
                "value": 500000.00,
                "percentage": 50.0,
                "position_count": 25
            },
            ...
        ]
    """
    service = PortfolioAggregationService(db)
    breakdown = await service.get_portfolio_breakdown(current_user.id)

    return breakdown
```

### Modified Endpoints

#### Update Existing Analytics Endpoints

**Pattern:** All analytics endpoints support optional `portfolio_id` query parameter

**Example:** `GET /api/v1/analytics/overview`

```python
@router.get("/overview")
async def get_analytics_overview(
    portfolio_id: Optional[UUID] = None,  # NEW: Optional parameter
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get portfolio analytics overview.

    If portfolio_id provided: Returns analytics for that specific portfolio.
    If portfolio_id is None: Returns AGGREGATE analytics across all portfolios.

    Args:
        portfolio_id: Optional portfolio UUID (None = aggregate all)
        current_user: Authenticated user
        db: Database session

    Returns:
        Portfolio or aggregate analytics
    """
    if portfolio_id:
        # Single portfolio view (existing logic)
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        analytics_service = PortfolioAnalyticsService(db)
        return await analytics_service.get_portfolio_overview(portfolio_id)
    else:
        # Aggregate view (NEW)
        aggregation_service = PortfolioAggregationService(db)
        aggregate = await aggregation_service.get_aggregate_analytics(current_user.id)

        return {
            "portfolio_id": None,  # Indicates aggregate view
            "total_value": float(aggregate.total_value),
            "beta": aggregate.weighted_beta,
            "volatility": aggregate.weighted_volatility,
            "sharpe_ratio": aggregate.weighted_sharpe,
            "is_aggregate": True
        }
```

**Apply this pattern to ALL analytics endpoints:**
- `GET /api/v1/analytics/sector-exposure`
- `GET /api/v1/analytics/concentration`
- `GET /api/v1/analytics/volatility`
- `GET /api/v1/analytics/factor-exposures`
- etc.

---

## Phase 4: Update Authentication Flow

### Update `resolve_portfolio_id()`

**File:** `backend/app/core/dependencies.py`

```python
async def resolve_portfolio_id(
    portfolio_id: Optional[UUID],
    current_user: CurrentUser,
    db: AsyncSession
) -> Optional[UUID]:  # Now returns Optional (can be None)
    """
    Resolve portfolio ID for multi-portfolio support.

    NEW BEHAVIOR:
    - If portfolio_id provided: Validate ownership and return it
    - If portfolio_id is None: Return None (signals aggregate view)

    Args:
        portfolio_id: Optional portfolio UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        portfolio_id if provided, None for aggregate view

    Raises:
        ValueError: If portfolio not found or not owned by user
    """
    if portfolio_id:
        # Validate ownership
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
        return portfolio_id

    # None signals aggregate view across all portfolios
    return None
```

### Update `get_current_user()`

**File:** `backend/app/core/dependencies.py`

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_session)
) -> CurrentUser:
    """Get current authenticated user from JWT token"""

    # ... existing token validation ...

    # Load user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(...)

    # NEW: Load all user's portfolios (not just first)
    portfolios_stmt = select(Portfolio).where(
        and_(
            Portfolio.user_id == user.id,
            Portfolio.is_active == True
        )
    )
    portfolios_result = await db.execute(portfolios_stmt)
    portfolios = portfolios_result.scalars().all()

    # Create CurrentUser
    user_data = CurrentUser.model_validate(user)

    # NEW: Set portfolio_ids list instead of single portfolio_id
    user_data.portfolio_ids = [p.id for p in portfolios]
    user_data.default_portfolio_id = portfolios[0].id if portfolios else None

    return user_data
```

### Update `CurrentUser` Model

**File:** `backend/app/core/dependencies.py`

```python
class CurrentUser(BaseModel):
    id: UUID
    email: str
    full_name: str

    # NEW: List of all user's portfolio IDs
    portfolio_ids: List[UUID] = []

    # Keep for backward compatibility
    default_portfolio_id: Optional[UUID] = None

    # Deprecated (remove in future version)
    portfolio_id: Optional[UUID] = None

    class Config:
        from_attributes = True
```

---

## Phase 5: Testing

### Integration Tests

**File:** `backend/tests/integration/test_multi_portfolio_flow.py`

```python
"""Integration tests for multi-portfolio user flow"""

@pytest.mark.asyncio
async def test_create_multiple_portfolios(client, auth_headers):
    """Test creating multiple portfolios for one user"""

    # Create first portfolio
    response = await client.post(
        "/api/v1/portfolios",
        json={
            "account_name": "Fidelity Taxable",
            "account_type": "taxable"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    portfolio_1_id = response.json()["id"]

    # Create second portfolio
    response = await client.post(
        "/api/v1/portfolios",
        json={
            "account_name": "Schwab IRA",
            "account_type": "ira"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    portfolio_2_id = response.json()["id"]

    # List portfolios
    response = await client.get(
        "/api/v1/data/portfolios",
        headers=auth_headers
    )
    assert response.status_code == 200
    portfolios = response.json()
    assert len(portfolios) == 2


@pytest.mark.asyncio
async def test_aggregate_analytics_flow(client, auth_headers):
    """Test aggregate analytics across multiple portfolios"""

    # Create 2 portfolios with positions
    # ... setup code ...

    # Get aggregate analytics (no portfolio_id parameter)
    response = await client.get(
        "/api/v1/analytics/aggregate",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["portfolio_count"] == 2
    assert data["total_value"] > 0
    assert "weighted_beta" in data
    assert "portfolio_breakdown" in data
    assert len(data["portfolio_breakdown"]) == 2


@pytest.mark.asyncio
async def test_single_portfolio_view_still_works(client, auth_headers, portfolio_id):
    """Test that single portfolio view still works (backward compatibility)"""

    # Get analytics for specific portfolio
    response = await client.get(
        f"/api/v1/analytics/overview?portfolio_id={portfolio_id}",
        headers=auth_headers
    )
    assert response.status_code == 200

    data = response.json()
    assert data["portfolio_id"] == str(portfolio_id)
    assert "is_aggregate" not in data or data["is_aggregate"] == False
```

---

## Phase 6: Documentation

### API Documentation Updates

Update `backend/_docs/reference/API_REFERENCE.md`:

```markdown
## Portfolio Management (NEW)

### Create Portfolio
`POST /api/v1/portfolios`

Create a new portfolio (account) for the authenticated user.

**Request:**
```json
{
  "account_name": "Schwab IRA",
  "account_type": "ira",
  "description": "Traditional IRA at Schwab"
}
```

**Response:** `201 Created`
```json
{
  "id": "...",
  "account_name": "Schwab IRA",
  "account_type": "ira",
  ...
}
```

### Update Portfolio
`PUT /api/v1/portfolios/{portfolio_id}`

### Delete Portfolio
`DELETE /api/v1/portfolios/{portfolio_id}`

Soft delete - marks as inactive.

## Analytics (UPDATED)

All analytics endpoints now support optional `portfolio_id` parameter:

- No `portfolio_id`: Returns aggregate analytics across all portfolios
- With `portfolio_id`: Returns analytics for specific portfolio

### Get Aggregate Analytics
`GET /api/v1/analytics/aggregate`

Returns weighted average metrics across all user's portfolios.
```

---

## Rollout Plan

### Week 1: Migration
1. Create and test migration in dev
2. Deploy to staging
3. Run migration in staging
4. Verify existing data

### Week 2-3: Backend Development
1. Implement `PortfolioAggregationService`
2. Add new portfolio CRUD endpoints
3. Update analytics endpoints
4. Write unit tests
5. Write integration tests

### Week 3-4: Testing
1. QA testing in staging
2. Performance testing with multiple portfolios
3. Accuracy validation of weighted averages
4. Backward compatibility testing

### Week 4: Production Deployment
1. Deploy migration to production (low-traffic window)
2. Deploy backend API
3. Monitor for errors
4. Gradual rollout (feature flag if needed)

---

## Performance Considerations

### Database Queries
- Add index on `portfolios.user_id` for fast user portfolio lookups
- Use `selectinload()` for eager loading portfolio relationships
- Cache aggregate analytics (5-minute TTL)

### Scalability
- Most users: 2-5 portfolios (fast)
- Power users: 10-20 portfolios (still acceptable)
- Limit: 20 portfolios per user (enforced)

---

## Success Criteria

- ✅ Users can create multiple portfolios
- ✅ Aggregate analytics calculate correctly (validated against manual calculations)
- ✅ Single portfolio view still works (backward compatible)
- ✅ **Single-portfolio users see identical results** (weighted avg with n=1 = value)
- ✅ Performance acceptable (<200ms for aggregate analytics)
- ✅ All tests passing
- ✅ No breaking changes to existing API consumers

---

## Handling Single-Portfolio Users

### Mathematical Correctness

**Question:** What happens when user has only 1 portfolio?

**Answer:** Weighted averages work perfectly with n=1 (returns identical values).

```python
# User with 1 portfolio
Portfolio A:
  - Total Value: $500,000
  - Beta: 1.2
  - Volatility: 20%

# Aggregation calculation
Total Value = $500,000
Weight A = $500k / $500k = 1.0  # 100% weight

Aggregate Beta = 1.2 × 1.0 = 1.2  ✅ Identical!
Aggregate Volatility = 20% × 1.0 = 20%  ✅ Identical!
```

**Result:** Existing users (all have 1 portfolio) will see **identical analytics** after migration.

### Backend Implementation

**No Special Casing Required:**

```python
# PortfolioAggregationService handles n=1 automatically
async def get_aggregate_analytics(user_id: UUID):
    portfolios = await get_user_portfolios(user_id)

    # Works for any n >= 1
    # When n=1, weighted average returns portfolio value
    # When n>1, weighted average aggregates across portfolios

    total_value = sum(p.total_value for p in portfolios)

    weighted_beta = sum(
        p.beta * (p.total_value / total_value)
        for p in portfolios
    )
    # If n=1: weighted_beta = portfolio.beta × 1.0 = portfolio.beta ✅
```

**Backward Compatibility:**
- ✅ Existing endpoints return same results
- ✅ Existing users see no changes
- ✅ No migration of analytics data needed
- ✅ Zero breaking changes

### Testing Single-Portfolio Scenario

**Test Cases:**

```python
@pytest.mark.asyncio
async def test_aggregate_analytics_single_portfolio(db_session):
    """Verify aggregation works correctly with 1 portfolio"""

    # Create user with 1 portfolio
    user = User(id=uuid4(), email="test@example.com")
    portfolio = Portfolio(
        id=uuid4(),
        user_id=user.id,
        total_value=Decimal("500000"),
        beta=1.2,
        volatility=20.0
    )

    db_session.add(user)
    db_session.add(portfolio)
    await db_session.commit()

    # Get aggregate analytics
    service = PortfolioAggregationService(db_session)
    aggregate = await service.get_aggregate_analytics(user.id)

    # Verify results are identical to portfolio
    assert aggregate.total_value == portfolio.total_value
    assert aggregate.weighted_beta == portfolio.beta
    assert aggregate.weighted_volatility == portfolio.volatility
    assert aggregate.portfolio_count == 1


@pytest.mark.asyncio
async def test_backward_compatibility_single_portfolio(client, auth_headers):
    """Verify existing single-portfolio users see no changes"""

    # Get analytics before migration (baseline)
    # ... record baseline values ...

    # Apply migration
    # ... run migration ...

    # Get analytics after migration
    response = await client.get(
        "/api/v1/analytics/overview",  # No portfolio_id = aggregate
        headers=auth_headers
    )

    # Verify results identical to baseline
    assert response.json()["beta"] == baseline_beta
    assert response.json()["volatility"] == baseline_volatility
```

---

---

## Implementation Decisions Summary

**Migration Strategy:**
- Write comprehensive unit tests for migration
- Apply confidently to dev database (UIRefactor branch)
- Backup available if needed

**Timeline:**
- 3-4 weeks for complete backend implementation
- Week 1: Database migration + aggregation service
- Week 2: New CRUD endpoints + aggregate analytics
- Week 3: Update existing endpoints + E2E testing
- Week 4: Buffer, bug fixes, documentation

**Feature Flags:**
- None - backward compatible deployment
- All changes deployed at once
- Simpler code, less complexity

**Monitoring:**
- Basic structured logging to critical paths
- PortfolioAggregationService
- Portfolio CRUD endpoints
- Error handling paths

**Deployment:**
- Backend first (this phase)
- Validate backward compatibility with current frontend
- Frontend updates in separate phase

---

**Document Version:** 1.2
**Last Updated:** 2025-11-01
**Changes:**
- v1.1: Added single-portfolio handling section
- v1.2: Added implementation decisions summary
