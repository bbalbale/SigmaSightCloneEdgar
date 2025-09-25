"""
Strategy API endpoints
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.models import User, StrategyType
from app.services.strategy_service import StrategyService
from app.schemas.strategy_schemas import (
    CreateStrategyRequest,
    UpdateStrategyRequest,
    CombinePositionsRequest,
    StrategyResponse,
    StrategyMetricsResponse,
    StrategyListResponse,
    DetectedStrategiesResponse,
    DetectedStrategyPattern
)
from app.core.logging import get_logger
from app.schemas.tag_schemas import (
    TagResponse,
    StrategyTagsReplaceRequest,
    StrategyTagsModifyRequest,
)
from app.services.tag_service import TagService

logger = get_logger(__name__)
router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/", response_model=StrategyResponse)
async def create_strategy(
    request: CreateStrategyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new strategy"""
    service = StrategyService(db)

    # Authorization: ensure portfolio belongs to current user
    try:
        await validate_portfolio_ownership(db, request.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    try:
        strategy = await service.create_strategy(
            portfolio_id=request.portfolio_id,
            name=request.name,
            strategy_type=request.strategy_type,
            description=request.description,
            position_ids=request.position_ids,
            created_by=current_user.id
        )

        # Convert to response model
        return StrategyResponse.model_validate(strategy)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create strategy: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create strategy")


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    include_positions: bool = Query(True, description="Include positions in response"),
    include_metrics: bool = Query(False, description="Include metrics in response"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a strategy by ID"""
    service = StrategyService(db)

    strategy = await service.get_strategy(
        strategy_id=strategy_id,
        include_positions=include_positions,
        include_metrics=include_metrics
    )

    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    # Authorization: ensure strategy's portfolio belongs to current user
    try:
        await validate_portfolio_ownership(db, strategy.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    response = StrategyResponse.model_validate(strategy)
    response.position_count = len(strategy.positions) if strategy.positions else 0

    # Normalize metrics: return only the latest metrics entry if requested
    if include_metrics and getattr(strategy, "metrics", None):
        try:
            latest = max(strategy.metrics, key=lambda m: m.calculation_date or datetime.min)
            response.metrics = StrategyMetricsResponse.model_validate(latest)
        except Exception:
            response.metrics = None

    return response


@router.get("/", response_model=StrategyListResponse)
async def list_strategies(
    portfolio_id: Optional[UUID] = Query(None, description="Filter by portfolio"),
    strategy_type: Optional[StrategyType] = Query(None, description="Filter by strategy type"),
    is_synthetic: Optional[bool] = Query(None, description="Filter by synthetic status"),
    include_positions: bool = Query(False, description="Include positions in response"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List strategies with optional filters"""
    service = StrategyService(db)

    # Default to current user's portfolio to avoid data leakage
    effective_portfolio_id = portfolio_id or getattr(current_user, "portfolio_id", None)
    if not effective_portfolio_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No portfolio context available")
    try:
        await validate_portfolio_ownership(db, effective_portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # Always include positions for now to avoid lazy loading issues
    strategies = await service.list_strategies(
        portfolio_id=effective_portfolio_id,
        strategy_type=strategy_type,
        is_synthetic=is_synthetic,
        include_positions=True,  # Always load to avoid lazy loading issues
        limit=limit,
        offset=offset
    )

    # Convert to response models - build dicts manually to avoid lazy loading
    strategy_responses = []
    for s in strategies:
        # Build response dict manually to control what's accessed
        strategy_dict = {
            "id": s.id,
            "portfolio_id": s.portfolio_id,
            "name": s.name,
            "description": s.description,
            "strategy_type": s.strategy_type,
            "is_synthetic": s.is_synthetic,
            "net_exposure": s.net_exposure,
            "total_cost_basis": s.total_cost_basis,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "closed_at": s.closed_at,
            "created_by": s.created_by,
            "position_count": len(s.positions) if hasattr(s, 'positions') and s.positions is not None else 0
        }

        # Only include positions if requested
        if include_positions and hasattr(s, 'positions') and s.positions is not None:
            strategy_dict["positions"] = [
                {
                    "id": p.id,
                    "symbol": p.symbol,
                    "position_type": p.position_type,
                    "quantity": p.quantity,
                    "entry_price": p.entry_price,
                    "market_value": p.market_value,
                    "unrealized_pnl": p.unrealized_pnl
                }
                for p in s.positions
            ]

        strategy_responses.append(StrategyResponse(**strategy_dict))

    return StrategyListResponse(
        strategies=strategy_responses,
        total=len(strategies),
        limit=limit,
        offset=offset
    )


@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    request: UpdateStrategyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a strategy"""
    service = StrategyService(db)

    # Load and authorize
    existing = await service.get_strategy(strategy_id, include_positions=False)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, existing.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    strategy = await service.update_strategy(
        strategy_id=strategy_id,
        name=request.name,
        description=request.description,
        strategy_type=request.strategy_type
    )

    return StrategyResponse.model_validate(strategy)


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: UUID,
    reassign_positions: bool = Query(True, description="Create standalone strategies for orphaned positions"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (close) a strategy"""
    service = StrategyService(db)

    # Load and authorize
    existing = await service.get_strategy(strategy_id, include_positions=True)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, existing.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    success = await service.delete_strategy(
        strategy_id=strategy_id,
        reassign_positions=reassign_positions
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    return {"message": "Strategy closed successfully"}


@router.post("/combine", response_model=StrategyResponse)
async def combine_positions(
    request: CombinePositionsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Combine multiple positions into a multi-leg strategy"""
    service = StrategyService(db)

    # Authorization: ensure portfolio belongs to current user
    try:
        await validate_portfolio_ownership(db, request.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    try:
        strategy = await service.combine_into_strategy(
            position_ids=request.position_ids,
            strategy_name=request.strategy_name,
            strategy_type=request.strategy_type,
            portfolio_id=request.portfolio_id,
            description=request.description,
            created_by=current_user.id
        )

        return StrategyResponse.model_validate(strategy)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to combine positions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to combine positions")


@router.get("/detect/{portfolio_id}", response_model=DetectedStrategiesResponse)
async def detect_strategies(
    portfolio_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detect potential multi-leg strategies in a portfolio"""
    service = StrategyService(db)

    # Authorization
    try:
        await validate_portfolio_ownership(db, portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    detected = await service.detect_strategies(portfolio_id)

    # Convert to response model
    patterns = [
        DetectedStrategyPattern(
            type=d['type'],
            positions=d['positions'],
            confidence=d['confidence'],
            description=d['description']
        )
        for d in detected
    ]

    return DetectedStrategiesResponse(
        portfolio_id=portfolio_id,
        detected_patterns=patterns,
        total_patterns=len(patterns)
    )


@router.get("/{strategy_id}/tags", response_model=List[TagResponse])
async def get_strategy_tags(
    strategy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return tags assigned to a strategy (auth by portfolio ownership)"""
    s_service = StrategyService(db)
    t_service = TagService(db)

    strategy = await s_service.get_strategy(strategy_id, include_positions=False)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, strategy.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    tags = await t_service.get_tags_for_strategy(strategy_id)
    return [TagResponse.model_validate(t) for t in tags]


@router.put("/{strategy_id}/tags")
async def replace_strategy_tags(
    strategy_id: UUID,
    request: StrategyTagsReplaceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Replace all tags on a strategy with provided tag_ids"""
    s_service = StrategyService(db)
    t_service = TagService(db)

    strategy = await s_service.get_strategy(strategy_id, include_positions=False)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, strategy.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    created = await t_service.replace_tags_for_strategy(strategy_id, request.tag_ids, assigned_by=current_user.id)
    return {"message": f"Replaced, now {len(created)} tags assigned"}


@router.post("/{strategy_id}/tags")
async def add_strategy_tags(
    strategy_id: UUID,
    request: StrategyTagsModifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add specific tag_ids to a strategy (no replace)"""
    s_service = StrategyService(db)
    t_service = TagService(db)

    strategy = await s_service.get_strategy(strategy_id, include_positions=False)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, strategy.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    created = await t_service.bulk_assign_tags(strategy_id, request.tag_ids, assigned_by=current_user.id, replace_existing=False)
    return {"message": f"Added {len(created)} tag assignments"}


@router.delete("/{strategy_id}/tags")
async def remove_strategy_tags(
    strategy_id: UUID,
    request: StrategyTagsModifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove provided tag_ids from a strategy"""
    s_service = StrategyService(db)
    t_service = TagService(db)

    strategy = await s_service.get_strategy(strategy_id, include_positions=False)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, strategy.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    await t_service.remove_tags_from_strategy(strategy_id, request.tag_ids)
    return {"message": "Tags removed"}
