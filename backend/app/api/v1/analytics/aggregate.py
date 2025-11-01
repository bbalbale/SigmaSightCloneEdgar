"""
Aggregate Analytics Endpoints

Provides portfolio-level analytics aggregated across multiple portfolios.
Uses portfolio-as-asset weighted average approach.

Created: 2025-11-01
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_async_session
from app.models.users import User
from app.services.portfolio_aggregation_service import PortfolioAggregationService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/aggregate", tags=["aggregate-analytics"])

# Type alias
CurrentUser = User


@router.get("/overview")
async def get_aggregate_overview(
    portfolio_ids: Optional[List[UUID]] = Query(None, description="Specific portfolio IDs to aggregate. If None, aggregates all active portfolios."),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get aggregate portfolio overview across multiple portfolios.

    Provides:
    - Total portfolio value
    - Portfolio count
    - Individual portfolio breakdown with weights
    - Aggregate metrics summary

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs to aggregate
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate overview with portfolio breakdown and weights
    """
    try:
        service = PortfolioAggregationService(db)

        # Get aggregate metrics
        result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        logger.info(
            f"Aggregate overview for user {current_user.id}: "
            f"{result['portfolio_count']} portfolios, ${result['total_value']:,.2f}"
        )

        return result

    except Exception as e:
        logger.error(f"Error getting aggregate overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve aggregate overview: {str(e)}"
        )


@router.get("/breakdown")
async def get_portfolio_breakdown(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get detailed breakdown of portfolios with individual metrics.

    Returns each portfolio's contribution to the aggregate, including:
    - Account name and type
    - Current value
    - Weight (% of total)
    - Position count
    - Individual metrics (if available)

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Detailed breakdown of all portfolios
    """
    try:
        service = PortfolioAggregationService(db)

        # Get base aggregate data
        result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        # Enhance with additional details
        enhanced_portfolios = []
        for portfolio in result['portfolios']:
            enhanced_portfolios.append({
                **portfolio,
                "weight_pct": round(portfolio['weight'] * 100, 2),
                "contribution_dollars": round(portfolio['value'], 2)
            })

        response = {
            "total_value": result['total_value'],
            "portfolio_count": result['portfolio_count'],
            "portfolios": enhanced_portfolios,
            "summary": {
                "total_weight": sum(p['weight'] for p in result['portfolios']),
                "average_value": result['total_value'] / result['portfolio_count'] if result['portfolio_count'] > 0 else 0
            }
        }

        return response

    except Exception as e:
        logger.error(f"Error getting portfolio breakdown: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve portfolio breakdown: {str(e)}"
        )


@router.get("/beta")
async def get_aggregate_beta(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get aggregate portfolio beta across multiple portfolios.

    Uses weighted average based on portfolio values:
    Aggregate Beta = Σ(Beta_i × Weight_i)

    Where Weight_i = Portfolio_Value_i / Total_Value

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate beta with individual portfolio contributions
    """
    try:
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select

        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "aggregate_beta": None,
                "portfolios": [],
                "message": "No portfolios found"
            }

        # Get beta for each portfolio from snapshots
        portfolio_betas: Dict[UUID, Dict[str, Any]] = {}

        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])

            # Get latest snapshot with beta
            snapshot_result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()

            beta = None
            if snapshot:
                # Prefer calculated 90d beta, fall back to provider 1y
                if snapshot.beta_calculated_90d is not None:
                    beta = float(snapshot.beta_calculated_90d)
                elif snapshot.beta_provider_1y is not None:
                    beta = float(snapshot.beta_provider_1y)

            portfolio_betas[portfolio_id] = {
                'beta': beta,
                'weight': portfolio_data['weight']
            }

        # Calculate aggregate beta
        aggregate_beta = await service.aggregate_beta(portfolio_betas)

        # Build response
        portfolio_contributions = []
        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])
            beta_data = portfolio_betas.get(portfolio_id, {})

            portfolio_contributions.append({
                "portfolio_id": str(portfolio_id),
                "account_name": portfolio_data['account_name'],
                "account_type": portfolio_data['account_type'],
                "value": portfolio_data['value'],
                "weight": portfolio_data['weight'],
                "beta": beta_data.get('beta'),
                "contribution": (beta_data.get('beta', 0) * portfolio_data['weight']) if beta_data.get('beta') is not None else None
            })

        response = {
            "aggregate_beta": aggregate_beta,
            "total_value": portfolios_result['total_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "portfolios": portfolio_contributions,
            "calculation_method": "weighted_average",
            "formula": "Σ(Beta_i × Weight_i) where Weight_i = Value_i / Total_Value"
        }

        logger.info(
            f"Aggregate beta for user {current_user.id}: {aggregate_beta:.4f if aggregate_beta else 'N/A'} "
            f"({portfolios_result['portfolio_count']} portfolios)"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate beta: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate beta: {str(e)}"
        )


@router.get("/volatility")
async def get_aggregate_volatility(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get aggregate portfolio volatility across multiple portfolios.

    Uses weighted average (approximation):
    Aggregate Volatility ≈ Σ(Volatility_i × Weight_i)

    Note: This is a simplified approximation. True portfolio volatility
    should account for correlations between portfolios.

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate volatility with individual portfolio contributions
    """
    try:
        from app.models.snapshots import PortfolioSnapshot
        from sqlalchemy import select

        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "aggregate_volatility": None,
                "portfolios": [],
                "message": "No portfolios found"
            }

        # Get volatility for each portfolio from snapshots
        portfolio_volatilities: Dict[UUID, Dict[str, Any]] = {}

        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])

            # Get latest snapshot with volatility
            snapshot_result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio_id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )
            snapshot = snapshot_result.scalar_one_or_none()

            volatility = None
            if snapshot and snapshot.realized_volatility_21d is not None:
                volatility = float(snapshot.realized_volatility_21d)

            portfolio_volatilities[portfolio_id] = {
                'volatility': volatility,
                'weight': portfolio_data['weight']
            }

        # Calculate aggregate volatility
        aggregate_volatility = await service.aggregate_volatility(portfolio_volatilities)

        # Build response
        portfolio_contributions = []
        for portfolio_data in portfolios_result['portfolios']:
            portfolio_id = UUID(portfolio_data['id'])
            vol_data = portfolio_volatilities.get(portfolio_id, {})

            portfolio_contributions.append({
                "portfolio_id": str(portfolio_id),
                "account_name": portfolio_data['account_name'],
                "account_type": portfolio_data['account_type'],
                "value": portfolio_data['value'],
                "weight": portfolio_data['weight'],
                "volatility": vol_data.get('volatility'),
                "contribution": (vol_data.get('volatility', 0) * portfolio_data['weight']) if vol_data.get('volatility') is not None else None
            })

        response = {
            "aggregate_volatility": aggregate_volatility,
            "total_value": portfolios_result['total_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "portfolios": portfolio_contributions,
            "calculation_method": "weighted_average",
            "note": "Simplified approximation. True volatility should account for correlations.",
            "formula": "Σ(Volatility_i × Weight_i) where Weight_i = Value_i / Total_Value"
        }

        logger.info(
            f"Aggregate volatility for user {current_user.id}: {aggregate_volatility:.4f if aggregate_volatility else 'N/A'} "
            f"({portfolios_result['portfolio_count']} portfolios)"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate volatility: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate volatility: {str(e)}"
        )


@router.get("/factor-exposures")
async def get_aggregate_factor_exposures(
    portfolio_ids: Optional[List[UUID]] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Get aggregate factor exposures across multiple portfolios.

    Calculates weighted average exposure for each factor:
    - Market (SPY)
    - Size (IWM)
    - Value (IVE)
    - Momentum (MTUM)
    - Quality (QUAL)

    Args:
        portfolio_ids: Optional list of specific portfolio UUIDs
        current_user: Authenticated user
        db: Database session

    Returns:
        Aggregate factor exposures with portfolio contributions
    """
    try:
        service = PortfolioAggregationService(db)

        # Get portfolios and weights
        portfolios_result = await service.aggregate_portfolio_metrics(
            user_id=current_user.id,
            portfolio_ids=portfolio_ids
        )

        if portfolios_result['portfolio_count'] == 0:
            return {
                "aggregate_factors": {},
                "portfolios": [],
                "message": "No portfolios found"
            }

        # Extract portfolio IDs and weights
        portfolio_ids_list = [UUID(p['id']) for p in portfolios_result['portfolios']]
        weights = {UUID(p['id']): p['weight'] for p in portfolios_result['portfolios']}

        # Calculate aggregate factor exposures
        aggregate_factors = await service.aggregate_factor_exposures(
            portfolio_ids=portfolio_ids_list,
            weights=weights
        )

        # Build response
        response = {
            "aggregate_factors": aggregate_factors,
            "total_value": portfolios_result['total_value'],
            "portfolio_count": portfolios_result['portfolio_count'],
            "calculation_method": "weighted_average",
            "factors": {
                "market": "SPY - S&P 500",
                "size": "IWM - Russell 2000",
                "value": "IVE - S&P 500 Value",
                "momentum": "MTUM - Momentum",
                "quality": "QUAL - Quality"
            },
            "formula": "For each factor: Σ(Exposure_i × Weight_i)"
        }

        logger.info(
            f"Aggregate factor exposures for user {current_user.id}: "
            f"{len(aggregate_factors)} factors calculated"
        )

        return response

    except Exception as e:
        logger.error(f"Error calculating aggregate factor exposures: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate aggregate factor exposures: {str(e)}"
        )
