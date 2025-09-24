"""Enhanced tag models for user-scoped organizational metadata.

Tags are user-level organizational tools that can be applied to strategies
for filtering and grouping purposes.
"""
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

if TYPE_CHECKING:
    from app.models.users import User
    from app.models.strategies import StrategyTag


class TagV2(Base):
    """Enhanced tag model for user-scoped organizational metadata."""

    __tablename__ = "tags_v2"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    color = Column(String(7), default="#4A90E2", nullable=True)
    description = Column(Text, nullable=True)

    # Display and usage
    display_order = Column(Integer, default=0, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)

    # Archiving support
    is_archived = Column(Boolean, default=False, nullable=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'name', 'is_archived', name='unique_active_tag_name_v2'),
        CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name='valid_hex_color'),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    archiver = relationship("User", foreign_keys=[archived_by])
    strategy_tags = relationship("StrategyTag", cascade="all, delete-orphan", back_populates="tag")

    def __repr__(self):
        return f"<TagV2(id={self.id}, name={self.name}, user={self.user_id})>"

    @property
    def is_active(self) -> bool:
        """Check if tag is active (not archived)."""
        return not self.is_archived

    @property
    def strategy_count(self) -> int:
        """Get the number of strategies using this tag."""
        try:
            return len(self.strategy_tags) if self.strategy_tags is not None else 0
        except Exception:
            return 0

    def archive(self, archived_by_user_id: Optional[UUID] = None):
        """Archive this tag."""
        self.is_archived = True
        self.archived_at = datetime.utcnow()
        self.archived_by = archived_by_user_id

    def restore(self):
        """Restore this tag from archive."""
        self.is_archived = False
        self.archived_at = None
        self.archived_by = None

    def to_dict(self) -> dict:
        """Convert tag to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "color": self.color,
            "description": self.description,
            "display_order": self.display_order,
            "usage_count": self.usage_count,
            "is_archived": self.is_archived,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "strategy_count": self.strategy_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def default_tags(cls) -> list[dict]:
        """Get default tag suggestions for new users."""
        return [
            {"name": "income", "color": "#4CAF50", "description": "Income generating strategies"},
            {"name": "growth", "color": "#2196F3", "description": "Growth-focused positions"},
            {"name": "defensive", "color": "#FF9800", "description": "Defensive/hedging positions"},
            {"name": "speculative", "color": "#F44336", "description": "High-risk speculative trades"},
            {"name": "tech", "color": "#9C27B0", "description": "Technology sector"},
            {"name": "finance", "color": "#00BCD4", "description": "Financial sector"},
            {"name": "healthcare", "color": "#8BC34A", "description": "Healthcare sector"},
            {"name": "energy", "color": "#FFC107", "description": "Energy sector"},
            {"name": "options", "color": "#795548", "description": "Options strategies"},
            {"name": "long-term", "color": "#607D8B", "description": "Long-term holdings"},
        ]
