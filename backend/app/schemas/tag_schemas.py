"""
Pydantic schemas for Tag API requests and responses.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import re

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TagBase(BaseModel):
    """Base tag schema shared across requests and responses."""

    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field("#4A90E2", pattern=r"^#[0-9A-Fa-f]{6}$")
    description: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        """Ensure the color uses the #RRGGBB hex format."""
        if not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValueError("Color must be a valid hex color code (e.g., #4A90E2)")
        return value.upper()


class CreateTagRequest(TagBase):
    """Payload for creating a tag."""

    display_order: Optional[int] = None


class UpdateTagRequest(BaseModel):
    """Payload for updating tag metadata."""

    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    description: Optional[str] = None
    display_order: Optional[int] = None

    @field_validator("color")
    @classmethod
    def validate_hex_color(cls, value: Optional[str]) -> Optional[str]:
        """Ensure optional color updates use the #RRGGBB hex format."""
        if value and not re.match(r"^#[0-9A-Fa-f]{6}$", value):
            raise ValueError("Color must be a valid hex color code (e.g., #4A90E2)")
        return value.upper() if value else value


class TagResponse(TagBase):
    """Tag representation returned from the API."""

    id: UUID
    user_id: UUID
    display_order: int
    usage_count: int
    position_count: int = 0
    strategy_count: int = 0  # Deprecated; kept for backward compatibility
    is_archived: bool
    archived_at: Optional[datetime] = None
    archived_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    """Envelope for listing tags."""

    tags: List[TagResponse]
    total: int
    active_count: int
    archived_count: int
