"""
Portfolio CRUD Endpoints

Handles creation, update, and deletion of portfolios.
Supports multi-portfolio functionality.

Created: 2025-11-01
"""
from typing import List
from uuid import UUID, uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user
from app.core.uuid_strategy import generate_portfolio_uuid
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot
from app.schemas.portfolios import (
    PortfolioCreateRequest,
    PortfolioUpdateRequest,
    PortfolioResponse,
    PortfolioListResponse,
    PortfolioDeleteResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])

# Type alias for current user dependency
CurrentUser = User


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_data: PortfolioCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create a new portfolio for the authenticated user.

    Users can have multiple portfolios representing different accounts
    (e.g., taxable brokerage, IRA, 401k, etc.).

    Args:
        portfolio_data: Portfolio creation data
        current_user: Authenticated user
        db: Database session

    Returns:
        Created portfolio with metadata

    Raises:
        400: Invalid portfolio data
    """
    try:
        # Generate UUID using shared UUIDStrategy (respects DETERMINISTIC_UUIDS setting)
        portfolio_uuid = generate_portfolio_uuid(
            user_id=current_user.id,
            account_name=portfolio_data.account_name
        )

        # Create new portfolio
        new_portfolio = Portfolio(
            id=portfolio_uuid,
            user_id=current_user.id,
            name=portfolio_data.name,
            account_name=portfolio_data.account_name,
            account_type=portfolio_data.account_type,
            description=portfolio_data.description,
            currency=portfolio_data.currency,
            equity_balance=portfolio_data.equity_balance,
            is_active=portfolio_data.is_active
        )

        db.add(new_portfolio)
        await db.commit()
        await db.refresh(new_portfolio)

        logger.info(
            f"Created portfolio {new_portfolio.id} for user {current_user.id}: "
            f"{portfolio_data.account_name} ({portfolio_data.account_type})"
        )

        # Build response
        response = PortfolioResponse(
            id=new_portfolio.id,
            user_id=new_portfolio.user_id,
            name=new_portfolio.name,
            account_name=new_portfolio.account_name,
            account_type=new_portfolio.account_type,
            description=new_portfolio.description,
            currency=new_portfolio.currency,
            equity_balance=new_portfolio.equity_balance,
            is_active=new_portfolio.is_active,
            created_at=new_portfolio.created_at,
            updated_at=new_portfolio.updated_at,
            deleted_at=new_portfolio.deleted_at,
            position_count=0,
            net_asset_value=new_portfolio.equity_balance or Decimal('0'),
            total_value=new_portfolio.equity_balance or Decimal('0')
        )

        return response

    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating portfolio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create portfolio: {str(e)}"
        )


@router.get("", response_model=PortfolioListResponse)
async def list_portfolios(
    include_inactive: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get all portfolios for the authenticated user.

    Args:
        include_inactive: Whether to include inactive portfolios
        current_user: Authenticated user
        db: Database session

    Returns:
        List of portfolios with metadata and aggregate totals
    """
    try:
        # Build query
        query = select(Portfolio).where(Portfolio.user_id == current_user.id)

        if not include_inactive:
            query = query.where(Portfolio.is_active == True)

        # Eager load positions for position count
        query = query.options(selectinload(Portfolio.positions))

        result = await db.execute(query)
        portfolios = result.scalars().all()

        # Build response for each portfolio
        portfolio_responses = []
        net_asset_value_sum = Decimal('0')
        active_count = 0

        for portfolio in portfolios:
            # Get latest snapshot for total value
            snapshot_result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()

            net_asset_value = snapshot.net_asset_value if snapshot and snapshot.net_asset_value else portfolio.equity_balance or Decimal('0')
            position_count = len(portfolio.positions) if portfolio.positions else 0

            if portfolio.is_active:
                active_count += 1
                net_asset_value_sum += net_asset_value

            portfolio_responses.append(
                PortfolioResponse(
                    id=portfolio.id,
                    user_id=portfolio.user_id,
                    name=portfolio.name,
                    account_name=portfolio.account_name,
                    account_type=portfolio.account_type,
                    description=portfolio.description,
                    currency=portfolio.currency,
                    equity_balance=portfolio.equity_balance,
                    is_active=portfolio.is_active,
                    created_at=portfolio.created_at,
                    updated_at=portfolio.updated_at,
                    deleted_at=portfolio.deleted_at,
                    position_count=position_count,
                    net_asset_value=net_asset_value,
                    total_value=net_asset_value
                )
            )

        logger.info(
            f"Retrieved {len(portfolios)} portfolios for user {current_user.id} "
            f"({active_count} active, total NAV: ${net_asset_value_sum:,.2f})"
        )

        return PortfolioListResponse(
            portfolios=portfolio_responses,
            total_count=len(portfolios),
            active_count=active_count,
            net_asset_value=net_asset_value_sum,
            total_value=net_asset_value_sum
        )

    except Exception as e:
        logger.error(f"Error listing portfolios: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve portfolios: {str(e)}"
        )


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get a specific portfolio by ID.

    Args:
        portfolio_id: Portfolio UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Portfolio details with metadata

    Raises:
        404: Portfolio not found or user doesn't have access
    """
    try:
        # Get portfolio with positions
        result = await db.execute(
            select(Portfolio)
            .options(selectinload(Portfolio.positions))
            .where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id
            )
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found"
            )

        # Get latest snapshot
        snapshot_result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snapshot = snapshot_result.scalar_one_or_none()

        net_asset_value = snapshot.net_asset_value if snapshot and snapshot.net_asset_value else portfolio.equity_balance or Decimal('0')
        position_count = len(portfolio.positions) if portfolio.positions else 0

        return PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            account_name=portfolio.account_name,
            account_type=portfolio.account_type,
            description=portfolio.description,
            currency=portfolio.currency,
            equity_balance=portfolio.equity_balance,
            is_active=portfolio.is_active,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
            deleted_at=portfolio.deleted_at,
            position_count=position_count,
            net_asset_value=net_asset_value,
            total_value=net_asset_value
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving portfolio {portfolio_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve portfolio: {str(e)}"
        )


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: UUID,
    portfolio_data: PortfolioUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update an existing portfolio.

    Only the portfolio owner can update it.
    All fields are optional - only provided fields will be updated.

    Args:
        portfolio_id: Portfolio UUID
        portfolio_data: Portfolio update data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated portfolio with metadata

    Raises:
        404: Portfolio not found or user doesn't have access
        400: Invalid update data
    """
    try:
        # Get portfolio
        result = await db.execute(
            select(Portfolio)
            .where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id
            )
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found"
            )

        # Update fields (only if provided)
        update_data = portfolio_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(portfolio, field, value)

        # Update timestamp
        portfolio.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(portfolio)

        logger.info(f"Updated portfolio {portfolio_id}: {update_data.keys()}")

        # Get latest snapshot for response
        snapshot_result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snapshot = snapshot_result.scalar_one_or_none()

        # Get position count
        position_count_result = await db.execute(
            select(func.count(Position.id))
            .where(Position.portfolio_id == portfolio.id)
        )
        position_count = position_count_result.scalar() or 0

        net_asset_value = snapshot.net_asset_value if snapshot and snapshot.net_asset_value else portfolio.equity_balance or Decimal('0')

        return PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            account_name=portfolio.account_name,
            account_type=portfolio.account_type,
            description=portfolio.description,
            currency=portfolio.currency,
            equity_balance=portfolio.equity_balance,
            is_active=portfolio.is_active,
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
            deleted_at=portfolio.deleted_at,
            position_count=position_count,
            net_asset_value=net_asset_value,
            total_value=net_asset_value
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating portfolio {portfolio_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update portfolio: {str(e)}"
        )


@router.delete("/{portfolio_id}", response_model=PortfolioDeleteResponse)
async def delete_portfolio(
    portfolio_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Soft delete a portfolio.

    Sets deleted_at timestamp and marks portfolio as inactive.
    Positions are not deleted, allowing for potential restoration.

    Note: Users cannot delete their last active portfolio.

    Args:
        portfolio_id: Portfolio UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Deletion confirmation with timestamp

    Raises:
        404: Portfolio not found or user doesn't have access
        400: Cannot delete last active portfolio
    """
    try:
        # Get portfolio
        result = await db.execute(
            select(Portfolio)
            .where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == current_user.id
            )
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio {portfolio_id} not found"
            )

        # Check if this is the last active portfolio
        active_count_result = await db.execute(
            select(func.count(Portfolio.id))
            .where(
                Portfolio.user_id == current_user.id,
                Portfolio.is_active == True,
                Portfolio.deleted_at.is_(None)
            )
        )
        active_count = active_count_result.scalar()

        if active_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last active portfolio. Create another portfolio first."
            )

        # Soft delete
        deleted_at = datetime.now(timezone.utc)
        portfolio.deleted_at = deleted_at
        portfolio.is_active = False
        portfolio.updated_at = deleted_at

        await db.commit()

        logger.info(f"Soft deleted portfolio {portfolio_id} for user {current_user.id}")

        return PortfolioDeleteResponse(
            success=True,
            message="Portfolio soft deleted successfully",
            portfolio_id=portfolio_id,
            deleted_at=deleted_at
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting portfolio {portfolio_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete portfolio: {str(e)}"
        )
