"""
Position Tag API endpoints - Direct position tagging system.

Replaces the legacy strategy-based tagging with direct position tags.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user, validate_portfolio_ownership
from app.models import User, Position
from app.services.position_tag_service import PositionTagService
from app.services.tag_service import TagService
from app.schemas.position_tag_schemas import (
    AssignTagsToPositionRequest,
    RemoveTagsFromPositionRequest,
    PositionTagResponse,
    TagSummary,
    PositionsByTagResponse,
    BulkAssignResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["position-tags"])


@router.post("/{position_id}/tags", response_model=BulkAssignResponse)
async def assign_tags_to_position(
    position_id: UUID,
    request: AssignTagsToPositionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign one or more tags to a position.

    If replace_existing is True, all existing tags will be removed first.
    """
    service = PositionTagService(db)
    tag_service = TagService(db)

    # Verify position exists and user has access
    from sqlalchemy import select
    position_result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    position = position_result.scalar()

    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    # Verify user owns the portfolio containing this position
    try:
        await validate_portfolio_ownership(db, position.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # Verify all tags belong to user
    for tag_id in request.tag_ids:
        tag = await tag_service.get_tag(tag_id)
        if not tag or tag.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied or tag not found: {tag_id}"
            )

    try:
        created_tags = await service.bulk_assign_tags(
            position_id=position_id,
            tag_ids=request.tag_ids,
            assigned_by=current_user.id,
            replace_existing=request.replace_existing
        )

        return BulkAssignResponse(
            message=f"Assigned {len(created_tags)} tags to position",
            assigned_count=len(created_tags),
            tag_ids=[pt.tag_id for pt in created_tags]
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{position_id}/tags")
async def remove_tags_from_position(
    position_id: UUID,
    tag_ids: List[UUID] = Query(..., description="Tag IDs to remove"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove one or more tags from a position.
    """
    service = PositionTagService(db)

    # Verify position exists and user has access
    from sqlalchemy import select
    position_result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    position = position_result.scalar()

    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    # Verify user owns the portfolio containing this position
    try:
        await validate_portfolio_ownership(db, position.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    removed_count = await service.bulk_remove_tags(
        position_id=position_id,
        tag_ids=tag_ids
    )

    return {
        "message": f"Removed {removed_count} tags from position",
        "removed_count": removed_count
    }


@router.get("/{position_id}/tags", response_model=List[TagSummary])
async def get_position_tags(
    position_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all tags assigned to a position.
    """
    service = PositionTagService(db)

    # Verify position exists and user has access
    from sqlalchemy import select
    position_result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    position = position_result.scalar()

    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    # Verify user owns the portfolio containing this position
    try:
        await validate_portfolio_ownership(db, position.portfolio_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    tags = await service.get_tags_for_position(position_id)

    return [
        TagSummary(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            description=tag.description
        )
        for tag in tags
    ]


@router.patch("/{position_id}/tags", response_model=BulkAssignResponse)
async def update_position_tags(
    position_id: UUID,
    request: AssignTagsToPositionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update all tags for a position (replaces existing tags).

    This is a convenience endpoint equivalent to POST with replace_existing=True.
    """
    # Force replace_existing to True for PATCH
    request.replace_existing = True

    return await assign_tags_to_position(
        position_id=position_id,
        request=request,
        db=db,
        current_user=current_user
    )


# This endpoint is registered under /tags router but included here for completeness
# It will be added to the tags.py file instead
# @router.get("/tags/{tag_id}/positions", response_model=PositionsByTagResponse)
# async def get_positions_by_tag(...)
