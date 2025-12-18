"""
Memory API endpoints for managing user memories.

Memories store user preferences, corrections, and context that persists
across conversations to personalize the AI assistant's responses.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.core.logging import get_logger
from app.agent.services.memory_service import (
    save_memory,
    get_user_memories,
    delete_memory,
    delete_all_user_memories,
    count_user_memories,
    SCOPE_USER,
    SCOPE_PORTFOLIO,
    MAX_MEMORIES_PER_USER,
    MAX_MEMORY_LENGTH,
)

logger = get_logger(__name__)

router = APIRouter()


# Pydantic schemas
class MemoryCreate(BaseModel):
    """Schema for creating a new memory."""
    content: str = Field(..., min_length=1, max_length=MAX_MEMORY_LENGTH, description="Memory content (max 500 chars)")
    scope: str = Field(default=SCOPE_USER, description="Memory scope: 'user' or 'portfolio'")
    portfolio_id: Optional[UUID] = Field(default=None, description="Portfolio ID for portfolio-scoped memories")
    tags: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata tags")


class MemoryUpdate(BaseModel):
    """Schema for updating a memory."""
    content: str = Field(..., min_length=1, max_length=MAX_MEMORY_LENGTH, description="Updated memory content")


class MemoryResponse(BaseModel):
    """Schema for memory response."""
    id: str
    scope: str
    content: str
    tags: Dict[str, Any]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """Schema for listing memories."""
    memories: List[MemoryResponse]
    total: int
    limit: int


class MemoryCountResponse(BaseModel):
    """Schema for memory count."""
    count: int
    max_allowed: int = MAX_MEMORIES_PER_USER


@router.get("/memories", response_model=MemoryListResponse)
async def list_memories(
    scope: Optional[str] = Query(default=None, description="Filter by scope: 'user' or 'portfolio'"),
    portfolio_id: Optional[UUID] = Query(default=None, description="Filter by portfolio ID"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of memories to return"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> MemoryListResponse:
    """
    List all memories for the current user.

    Optionally filter by scope or portfolio_id.
    """
    try:
        memories = await get_user_memories(
            db,
            user_id=current_user.id,
            scope=scope,
            portfolio_id=portfolio_id,
            limit=limit,
        )

        total = await count_user_memories(db, current_user.id)

        return MemoryListResponse(
            memories=[MemoryResponse(**m) for m in memories],
            total=total,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memories",
        )


@router.post("/memories", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    memory: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> MemoryResponse:
    """
    Create a new memory for the current user.

    If the user has reached the maximum number of memories (50),
    the oldest memory will be automatically deleted.
    """
    try:
        # Validate scope
        if memory.scope not in [SCOPE_USER, SCOPE_PORTFOLIO]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scope. Must be '{SCOPE_USER}' or '{SCOPE_PORTFOLIO}'",
            )

        # Portfolio ID required for portfolio scope
        if memory.scope == SCOPE_PORTFOLIO and not memory.portfolio_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="portfolio_id is required for portfolio-scoped memories",
            )

        memory_id = await save_memory(
            db,
            user_id=current_user.id,
            content=memory.content,
            scope=memory.scope,
            portfolio_id=memory.portfolio_id,
            tags=memory.tags or {},
        )

        # Fetch the created memory to return
        memories = await get_user_memories(db, current_user.id, limit=1)
        if memories and memories[0]["id"] == memory_id:
            return MemoryResponse(**memories[0])

        # Fallback response
        return MemoryResponse(
            id=memory_id,
            scope=memory.scope,
            content=memory.content,
            tags=memory.tags or {},
            created_at=None,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create memory",
        )


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory_endpoint(
    memory_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Delete a specific memory by ID.

    Only the owner can delete their memories.
    """
    try:
        deleted = await delete_memory(db, memory_id, current_user.id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found or not owned by current user",
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory",
        )


@router.delete("/memories", status_code=status.HTTP_200_OK)
async def delete_all_memories(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, int]:
    """
    Delete all memories for the current user.

    Returns the number of memories deleted.
    """
    try:
        deleted_count = await delete_all_user_memories(db, current_user.id)

        return {"deleted": deleted_count}

    except Exception as e:
        logger.error(f"Failed to delete all memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memories",
        )


@router.get("/memories/count", response_model=MemoryCountResponse)
async def get_memory_count(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> MemoryCountResponse:
    """
    Get the count of memories for the current user.

    Also returns the maximum allowed memories per user.
    """
    try:
        count = await count_user_memories(db, current_user.id)

        return MemoryCountResponse(
            count=count,
            max_allowed=MAX_MEMORIES_PER_USER,
        )

    except Exception as e:
        logger.error(f"Failed to count memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to count memories",
        )
