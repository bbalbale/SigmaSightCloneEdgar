"""
Pydantic schemas for Position Tag API endpoints.

These schemas handle request/response validation for the position tagging system.
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AssignTagsToPositionRequest(BaseModel):
    """Request to assign one or more tags to a position."""
    tag_ids: List[UUID] = Field(..., description="List of tag IDs to assign to the position")
    replace_existing: bool = Field(default=False, description="If true, replace all existing tags")


class RemoveTagsFromPositionRequest(BaseModel):
    """Request to remove tags from a position."""
    tag_ids: List[UUID] = Field(..., description="List of tag IDs to remove from the position")


class PositionTagResponse(BaseModel):
    """Response model for a position-tag association."""
    id: UUID
    position_id: UUID
    tag_id: UUID
    assigned_at: datetime
    assigned_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class TagSummary(BaseModel):
    """Lightweight tag summary for position responses."""
    id: UUID
    name: str
    color: str
    description: Optional[str] = None


class PositionWithTagsResponse(BaseModel):
    """Position information with associated tags."""
    position_id: UUID
    symbol: str
    tags: List[TagSummary]


class PositionsByTagResponse(BaseModel):
    """Response for getting all positions with a specific tag."""
    tag_id: UUID
    tag_name: str
    positions: List[dict]  # Position data from positions/details endpoint
    total: int


class BulkAssignResponse(BaseModel):
    """Response for bulk tag assignment operations."""
    message: str
    assigned_count: int
    tag_ids: List[UUID]
