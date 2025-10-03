"""
Position-Tag junction table for direct position tagging.

This model enables many-to-many relationships between positions and tags,
replacing the previous strategy-based tagging system.
"""
from typing import TYPE_CHECKING
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.positions import Position
    from app.models.tags_v2 import TagV2
    from app.models.users import User


class PositionTag(Base):
    """
    Junction table for position-tag relationships.

    Enables users to tag individual positions for organization and filtering.
    """
    __tablename__ = "position_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id = Column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False
    )
    tag_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tags_v2.id", ondelete="CASCADE"),
        nullable=False
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    position = relationship("Position", back_populates="position_tags")
    tag = relationship("TagV2", back_populates="position_tags")
    assignor = relationship("User", foreign_keys=[assigned_by])

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('position_id', 'tag_id', name='unique_position_tag'),
        Index('ix_position_tags_position_id', 'position_id'),
        Index('ix_position_tags_tag_id', 'tag_id'),
        Index('ix_position_tags_assigned_at', 'assigned_at'),
    )

    def __repr__(self):
        return f"<PositionTag(position_id={self.position_id}, tag_id={self.tag_id})>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "position_id": str(self.position_id),
            "tag_id": str(self.tag_id),
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by": str(self.assigned_by) if self.assigned_by else None,
        }
