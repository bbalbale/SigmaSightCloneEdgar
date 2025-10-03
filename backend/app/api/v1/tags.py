"""
Tag API endpoints
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.models import User
from app.services.tag_service import TagService
from app.services.strategy_service import StrategyService
from app.schemas.tag_schemas import (
    CreateTagRequest,
    UpdateTagRequest,
    AssignTagRequest,
    BulkAssignTagsRequest,
    TagResponse,
    TagListResponse,
    StrategyTagResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", response_model=TagResponse)
async def create_tag(
    request: CreateTagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new tag for the current user"""
    service = TagService(db)

    try:
        tag = await service.create_tag(
            user_id=current_user.id,
            name=request.name,
            color=request.color,
            description=request.description,
            display_order=request.display_order
        )

        return TagResponse.model_validate(tag)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create tag: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create tag")


@router.get("/", response_model=TagListResponse)
async def list_tags(
    include_archived: bool = Query(False, description="Include archived tags"),
    include_usage_stats: bool = Query(True, description="Include usage statistics"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tags for the current user"""
    service = TagService(db)

    tags = await service.get_user_tags(
        user_id=current_user.id,
        include_archived=include_archived,
        include_usage_stats=include_usage_stats
    )

    # Convert to response models
    tag_responses = [TagResponse.model_validate(t) for t in tags]

    # Count active vs archived
    active_count = sum(1 for t in tags if not t.is_archived)
    archived_count = len(tags) - active_count

    return TagListResponse(
        tags=tag_responses,
        total=len(tags),
        active_count=active_count,
        archived_count=archived_count
    )


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: UUID,
    include_strategies: bool = Query(False, description="Include associated strategies"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific tag by ID"""
    service = TagService(db)

    tag = await service.get_tag(tag_id, include_strategies=include_strategies)

    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    # Verify user owns this tag
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return TagResponse.model_validate(tag)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID,
    request: UpdateTagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a tag"""
    service = TagService(db)

    # Verify ownership first
    tag = await service.get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        updated_tag = await service.update_tag(
            tag_id=tag_id,
            name=request.name,
            color=request.color,
            description=request.description,
            display_order=request.display_order
        )

        return TagResponse.model_validate(updated_tag)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{tag_id}/archive")
async def archive_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive a tag (soft delete)"""
    service = TagService(db)

    # Verify ownership
    tag = await service.get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    success = await service.archive_tag(tag_id, archived_by=current_user.id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to archive tag")

    return {"message": "Tag archived successfully"}


@router.post("/{tag_id}/restore")
async def restore_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restore an archived tag"""
    service = TagService(db)

    # Verify ownership
    tag = await service.get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    success = await service.restore_tag(tag_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to restore tag")

    return {"message": "Tag restored successfully"}


@router.post("/assign")
async def assign_tag_to_strategy(
    request: AssignTagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a tag to a strategy"""
    service = TagService(db)
    strategy_service = StrategyService(db)

    # Verify tag ownership
    tag = await service.get_tag(request.tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Verify strategy ownership via portfolio
    strategy = await strategy_service.get_strategy(request.strategy_id, include_positions=False)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, strategy.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    try:
        strategy_tag = await service.assign_tag_to_strategy(
            tag_id=request.tag_id,
            strategy_id=request.strategy_id,
            assigned_by=current_user.id
        )

        return {"message": "Tag assigned successfully", "id": strategy_tag.id}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/assign")
async def remove_tag_from_strategy(
    tag_id: UUID = Query(..., description="Tag to remove"),
    strategy_id: UUID = Query(..., description="Strategy to remove from"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a tag from a strategy"""
    service = TagService(db)
    strategy_service = StrategyService(db)

    # Verify tag ownership
    tag = await service.get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Authorize strategy ownership via portfolio
    strategy = await strategy_service.get_strategy(strategy_id, include_positions=False)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, strategy.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    success = await service.remove_tag_from_strategy(tag_id, strategy_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag assignment not found")

    return {"message": "Tag removed successfully"}


@router.post("/bulk-assign")
async def bulk_assign_tags(
    request: BulkAssignTagsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign multiple tags to a strategy at once"""
    service = TagService(db)
    strategy_service = StrategyService(db)

    # Verify all tags belong to user
    for tag_id in request.tag_ids:
        tag = await service.get_tag(tag_id)
        if not tag or tag.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied or tag not found: {tag_id}"
            )

    # Authorize strategy ownership via portfolio
    strategy = await strategy_service.get_strategy(request.strategy_id, include_positions=False)
    if not strategy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    try:
        await validate_portfolio_ownership(db, strategy.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    created_tags = await service.bulk_assign_tags(
        strategy_id=request.strategy_id,
        tag_ids=request.tag_ids,
        assigned_by=current_user.id,
        replace_existing=request.replace_existing
    )

    return {
        "message": f"Assigned {len(created_tags)} tags to strategy",
        "assigned_count": len(created_tags)
    }


@router.get("/{tag_id}/strategies")
async def get_strategies_by_tag(
    tag_id: UUID,
    portfolio_id: Optional[UUID] = Query(None, description="Filter by portfolio"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all strategies with a specific tag"""
    service = TagService(db)

    # Verify tag ownership
    tag = await service.get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Default to current user's portfolio, and authorize
    effective_portfolio_id = portfolio_id or getattr(current_user, "portfolio_id", None)
    if not effective_portfolio_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No portfolio context available")
    try:
        await validate_portfolio_ownership(db, effective_portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    strategies = await service.get_strategies_by_tag(tag_id, effective_portfolio_id)

    return {
        "tag_id": tag_id,
        "tag_name": tag.name,
        "strategies": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.strategy_type,
                "portfolio_id": s.portfolio_id
            }
            for s in strategies
        ],
        "total": len(strategies)
    }


@router.post("/defaults")
async def create_default_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get or create default tag set for the current user - idempotent operation"""
    service = TagService(db)

    # Check if user already has tags
    existing_tags = await service.get_user_tags(current_user.id)
    if existing_tags:
        # Return existing tags instead of error - idempotent behavior
        return {
            "message": f"User has {len(existing_tags)} existing tags",
            "tags": [TagResponse.model_validate(t) for t in existing_tags]
        }

    # No tags exist, create defaults
    created_tags = await service.create_default_tags(current_user.id)

    return {
        "message": f"Created {len(created_tags)} default tags",
        "tags": [TagResponse.model_validate(t) for t in created_tags]
    }


@router.get("/{tag_id}/positions")
async def get_positions_by_tag(
    tag_id: UUID,
    portfolio_id: Optional[UUID] = Query(None, description="Filter by portfolio"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all positions with a specific tag (new position tagging system).

    This replaces the /tags/{tag_id}/strategies endpoint for the new
    position-based tagging system.
    """
    from app.services.position_tag_service import PositionTagService

    tag_service = TagService(db)
    position_tag_service = PositionTagService(db)

    # Verify tag ownership
    tag = await tag_service.get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    if tag.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Default to current user's portfolio, and authorize
    effective_portfolio_id = portfolio_id or getattr(current_user, "portfolio_id", None)
    if not effective_portfolio_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No portfolio context available")
    try:
        await validate_portfolio_ownership(db, effective_portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    positions = await position_tag_service.get_positions_by_tag(tag_id, effective_portfolio_id)

    return {
        "tag_id": tag_id,
        "tag_name": tag.name,
        "positions": [
            {
                "id": p.id,
                "symbol": p.symbol,
                "position_type": p.position_type.value if hasattr(p.position_type, 'value') else str(p.position_type),
                "quantity": float(p.quantity),
                "portfolio_id": p.portfolio_id,
                "investment_class": p.investment_class
            }
            for p in positions
        ],
        "total": len(positions)
    }
