"""
Pydantic schemas for Tag API requests and responses
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import re

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TagBase(BaseModel):
    """Base tag schema"""
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field("#4A90E2", pattern=r"^#[0-9A-Fa-f]{6}$")
    description: Optional[str] = None

    @field_validator('color')
    @classmethod
    def validate_hex_color(cls, v):
        """Validate hex color format"""
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color code (e.g., #4A90E2)')
        return v.upper()


class CreateTagRequest(TagBase):
    """Request schema for creating a tag"""
    display_order: Optional[int] = None


class UpdateTagRequest(BaseModel):
    """Request schema for updating a tag"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    description: Optional[str] = None
    display_order: Optional[int] = None

    @field_validator('color')
    @classmethod
    def validate_hex_color(cls, v):
        """Validate hex color format if provided"""
        if v and not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color code (e.g., #4A90E2)')
        return v.upper() if v else v


class AssignTagRequest(BaseModel):
    """Request schema for assigning a tag to a strategy"""
    strategy_id: UUID
    tag_id: UUID


class BulkAssignTagsRequest(BaseModel):
    """Request schema for bulk tag assignment"""
    strategy_id: UUID
    tag_ids: List[UUID]
    replace_existing: bool = False


class StrategyTagsReplaceRequest(BaseModel):
    """Replace a strategy's tags with the provided list"""
    tag_ids: List[UUID]


class StrategyTagsModifyRequest(BaseModel):
    """Modify a strategy's tags by adding/removing specific tag IDs"""
    tag_ids: List[UUID]


class TagResponse(TagBase):
    """Response schema for a tag"""
    id: UUID
    user_id: UUID
    display_order: int
    usage_count: int
    is_archived: bool
    archived_at: Optional[datetime] = None
    archived_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    strategy_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    """Response for listing tags"""
    tags: List[TagResponse]
    total: int
    active_count: int
    archived_count: int


class StrategyTagResponse(BaseModel):
    """Response for a strategy-tag association"""
    id: UUID
    strategy_id: UUID
    tag_id: UUID
    tag_name: str
    tag_color: str
    assigned_at: datetime
    assigned_by: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class TaggedStrategyResponse(BaseModel):
    """Response for strategies with tags"""
    strategy_id: UUID
    strategy_name: str
    strategy_type: str
    tags: List[TagResponse]

    model_config = ConfigDict(from_attributes=True)


class TagStatistics(BaseModel):
    """Tag usage statistics"""
    tag_id: UUID
    tag_name: str
    strategy_count: int
    portfolio_count: int
    last_used: Optional[datetime] = None
    most_common_strategy_type: Optional[str] = None


class TagStatisticsResponse(BaseModel):
    """Response for tag statistics"""
    user_id: UUID
    total_tags: int
    active_tags: int
    archived_tags: int
    most_used_tags: List[TagStatistics]
    least_used_tags: List[TagStatistics]
