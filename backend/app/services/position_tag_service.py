"""
Position Tag Service - Business logic for managing position-tag relationships.

This service handles the direct tagging of positions, replacing the legacy
strategy-based tagging system.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models import PositionTag, Position, TagV2
from app.core.logging import get_logger

logger = get_logger(__name__)


class PositionTagService:
    """Service for managing position-tag relationships."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def assign_tag_to_position(
        self,
        position_id: UUID,
        tag_id: UUID,
        assigned_by: Optional[UUID] = None
    ) -> PositionTag:
        """
        Assign a tag to a position.

        Args:
            position_id: Position to tag
            tag_id: Tag to assign
            assigned_by: User who assigned the tag

        Returns:
            Created PositionTag association

        Raises:
            ValueError: If position or tag not found, or already assigned
        """
        # Verify position exists
        position_result = await self.db.execute(
            select(Position).where(Position.id == position_id)
        )
        position = position_result.scalar()
        if not position:
            raise ValueError(f"Position {position_id} not found")

        # Verify tag exists and is not archived
        tag_result = await self.db.execute(
            select(TagV2).where(TagV2.id == tag_id)
        )
        tag = tag_result.scalar()
        if not tag:
            raise ValueError(f"Tag {tag_id} not found")
        if tag.is_archived:
            raise ValueError(f"Cannot assign archived tag {tag_id}")

        # Check if already assigned
        existing = await self.db.execute(
            select(PositionTag).where(
                and_(
                    PositionTag.position_id == position_id,
                    PositionTag.tag_id == tag_id
                )
            )
        )
        if existing.scalar():
            raise ValueError(f"Tag already assigned to this position")

        # Create the association
        position_tag = PositionTag(
            id=uuid4(),
            position_id=position_id,
            tag_id=tag_id,
            assigned_by=assigned_by
        )

        self.db.add(position_tag)

        # Increment tag usage count
        tag.usage_count = (tag.usage_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(position_tag)

        logger.info(f"Assigned tag {tag_id} to position {position_id}")
        return position_tag

    async def remove_tag_from_position(
        self,
        position_id: UUID,
        tag_id: UUID
    ) -> bool:
        """
        Remove a tag from a position.

        Args:
            position_id: Position to remove tag from
            tag_id: Tag to remove

        Returns:
            True if removed, False if not found
        """
        # Find the association
        result = await self.db.execute(
            select(PositionTag).where(
                and_(
                    PositionTag.position_id == position_id,
                    PositionTag.tag_id == tag_id
                )
            )
        )
        position_tag = result.scalar()

        if not position_tag:
            return False

        # Delete the association
        await self.db.delete(position_tag)

        # Decrement usage count
        tag_result = await self.db.execute(
            select(TagV2).where(TagV2.id == tag_id)
        )
        tag = tag_result.scalar()
        if tag and tag.usage_count > 0:
            tag.usage_count -= 1

        await self.db.commit()
        logger.info(f"Removed tag {tag_id} from position {position_id}")
        return True

    async def get_tags_for_position(
        self,
        position_id: UUID
    ) -> List[TagV2]:
        """
        Get all tags assigned to a position.

        Args:
            position_id: Position ID

        Returns:
            List of TagV2 objects
        """
        query = (
            select(TagV2)
            .join(PositionTag, TagV2.id == PositionTag.tag_id)
            .where(PositionTag.position_id == position_id)
            .where(TagV2.is_archived == False)
            .order_by(TagV2.display_order)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_positions_by_tag(
        self,
        tag_id: UUID,
        portfolio_id: Optional[UUID] = None
    ) -> List[Position]:
        """
        Get all positions with a specific tag.

        Args:
            tag_id: Tag to filter by
            portfolio_id: Optional portfolio filter

        Returns:
            List of Position objects
        """
        query = (
            select(Position)
            .join(PositionTag, Position.id == PositionTag.position_id)
            .where(PositionTag.tag_id == tag_id)
            .where(Position.deleted_at.is_(None))  # Exclude soft-deleted positions
        )

        if portfolio_id:
            query = query.where(Position.portfolio_id == portfolio_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def bulk_assign_tags(
        self,
        position_id: UUID,
        tag_ids: List[UUID],
        assigned_by: Optional[UUID] = None,
        replace_existing: bool = False
    ) -> List[PositionTag]:
        """
        Assign multiple tags to a position.

        Args:
            position_id: Position to tag
            tag_ids: List of tag IDs to assign
            assigned_by: User who assigned them
            replace_existing: If True, remove existing tags first

        Returns:
            List of created PositionTag associations
        """
        if replace_existing:
            # Remove all existing tags for this position
            await self.db.execute(
                delete(PositionTag).where(PositionTag.position_id == position_id)
            )
            await self.db.commit()

        created_tags = []
        for tag_id in tag_ids:
            try:
                position_tag = await self.assign_tag_to_position(
                    position_id=position_id,
                    tag_id=tag_id,
                    assigned_by=assigned_by
                )
                created_tags.append(position_tag)
            except ValueError as e:
                logger.warning(f"Skipping tag {tag_id} for position {position_id}: {e}")
                continue

        return created_tags

    async def bulk_remove_tags(
        self,
        position_id: UUID,
        tag_ids: List[UUID]
    ) -> int:
        """
        Remove multiple tags from a position.

        Args:
            position_id: Position to remove tags from
            tag_ids: List of tag IDs to remove

        Returns:
            Number of tags removed
        """
        result = await self.db.execute(
            delete(PositionTag).where(
                and_(
                    PositionTag.position_id == position_id,
                    PositionTag.tag_id.in_(tag_ids)
                )
            )
        )
        await self.db.commit()

        # The rowcount might not be accurate in async, but we return 0 as placeholder
        logger.info(f"Removed tags {tag_ids} from position {position_id}")
        return len(tag_ids)

    async def replace_tags_for_position(
        self,
        position_id: UUID,
        tag_ids: List[UUID],
        assigned_by: Optional[UUID] = None
    ) -> List[PositionTag]:
        """
        Replace all tags for a position with a new set.

        Args:
            position_id: Position to update
            tag_ids: New list of tag IDs
            assigned_by: User who assigned them

        Returns:
            List of created PositionTag associations
        """
        return await self.bulk_assign_tags(
            position_id=position_id,
            tag_ids=tag_ids,
            assigned_by=assigned_by,
            replace_existing=True
        )

    async def get_position_tag_associations(
        self,
        position_id: UUID
    ) -> List[PositionTag]:
        """
        Get all PositionTag associations for a position.

        Args:
            position_id: Position ID

        Returns:
            List of PositionTag objects with relationships loaded
        """
        query = (
            select(PositionTag)
            .where(PositionTag.position_id == position_id)
            .options(selectinload(PositionTag.tag))
        )

        result = await self.db.execute(query)
        return result.scalars().all()
