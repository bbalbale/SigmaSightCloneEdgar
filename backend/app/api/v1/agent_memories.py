"""
API endpoints for managing user memories.

These endpoints allow users to view and manage what the AI remembers about them.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.auth import CurrentUser
from app.agent.services.memory_service import (
    get_user_memories,
    save_memory,
    delete_memory,
    delete_all_user_memories,
    count_user_memories,
    SCOPE_USER,
    SCOPE_PORTFOLIO,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agent/memories", tags=["Agent Memories"])


# ==================== Schemas ====================

class MemoryResponse(BaseModel):
    """Response model for a single memory"""
    id: str
    scope: str
    content: str
    tags: dict = Field(default_factory=dict)
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """Response model for listing memories"""
    memories: List[MemoryResponse]
    total: int


class MemoryCreateRequest(BaseModel):
    """Request model for creating a memory"""
    content: str = Field(..., min_length=1, max_length=500, description="Memory content")
    scope: str = Field(default=SCOPE_USER, description="Memory scope: 'user' or 'portfolio'")
    portfolio_id: Optional[str] = Field(default=None, description="Portfolio ID for portfolio-scoped memories")
    tags: Optional[dict] = Field(default=None, description="Optional metadata tags")


class MemoryCreateResponse(BaseModel):
    """Response model for creating a memory"""
    id: str
    message: str


class MemoryDeleteResponse(BaseModel):
    """Response model for deleting a memory"""
    success: bool
    message: str


class MemoryCountResponse(BaseModel):
    """Response model for counting memories"""
    count: int


# ==================== Endpoints ====================

@router.get("", response_model=MemoryListResponse)
async def list_memories(
    scope: Optional[str] = Query(None, description="Filter by scope: 'user' or 'portfolio'"),
    portfolio_id: Optional[str] = Query(None, description="Filter by portfolio ID"),
    limit: int = Query(20, ge=1, le=50, description="Maximum memories to return"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List the current user's memories.

    Memories are what the AI remembers about the user across conversations,
    such as preferences, corrections, and context.
    """
    try:
        portfolio_uuid = UUID(portfolio_id) if portfolio_id else None

        memories = await get_user_memories(
            db,
            current_user.id,
            scope=scope,
            portfolio_id=portfolio_uuid,
            limit=limit,
        )

        total = await count_user_memories(db, current_user.id)

        return MemoryListResponse(
            memories=[MemoryResponse(**m) for m in memories],
            total=total,
        )

    except Exception as e:
        import traceback
        logger.error(f"Error listing memories: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to list memories: {str(e)}")


@router.post("", response_model=MemoryCreateResponse)
async def create_memory(
    request: MemoryCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new memory for the current user.

    This allows users to explicitly tell the AI something to remember.
    """
    try:
        portfolio_uuid = UUID(request.portfolio_id) if request.portfolio_id else None

        memory_id = await save_memory(
            db,
            user_id=current_user.id,
            content=request.content,
            scope=request.scope,
            tags=request.tags,
            portfolio_id=portfolio_uuid,
        )

        return MemoryCreateResponse(
            id=memory_id,
            message="Memory saved successfully",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to save memory")


@router.delete("/{memory_id}", response_model=MemoryDeleteResponse)
async def delete_single_memory(
    memory_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a specific memory by ID.

    Only the memory owner can delete their memories.
    """
    try:
        deleted = await delete_memory(db, memory_id, current_user.id)

        if deleted:
            return MemoryDeleteResponse(
                success=True,
                message="Memory deleted successfully",
            )
        else:
            raise HTTPException(status_code=404, detail="Memory not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete memory")


@router.delete("", response_model=MemoryDeleteResponse)
async def delete_all_memories(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete ALL memories for the current user.

    This is a destructive operation that cannot be undone.
    """
    try:
        deleted_count = await delete_all_user_memories(db, current_user.id)

        return MemoryDeleteResponse(
            success=True,
            message=f"Deleted {deleted_count} memories",
        )

    except Exception as e:
        logger.error(f"Error deleting all memories: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete memories")


@router.get("/count", response_model=MemoryCountResponse)
async def get_memory_count(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the count of memories for the current user.
    """
    try:
        print(f"[DEBUG] get_memory_count called for user {current_user.id}")
        print(f"[DEBUG] db session: {db}")
        count = await count_user_memories(db, current_user.id)
        print(f"[DEBUG] count result: {count}")
        return MemoryCountResponse(count=count)

    except Exception as e:
        import traceback
        error_msg = f"Error counting memories: {e}"
        tb = traceback.format_exc()
        print(f"[DEBUG ERROR] {error_msg}")
        print(f"[DEBUG TRACEBACK] {tb}")
        logger.error(error_msg)
        logger.error(f"Traceback: {tb}")
        raise HTTPException(status_code=500, detail=f"Failed to count memories: {str(e)}")
