"""
Tag Service - Business Logic for Tag Management (Service Layer)

This service owns the lifecycle for user-defined tags and supports
position-based tagging metrics (usage counts, archiving, restoration).

**Architecture Context** (3-tier separation of concerns):
- API Layer: app/api/v1/tags.py (FastAPI endpoints)
- THIS FILE (Service Layer): Tag management business logic
- Data Layer: app/models/tags_v2.py (TagV2)

**Tag Management Methods**:
- create_tag(): Create new tag
- get_tag(): Get tag by ID (with optional position usage details)
- get_user_tags(): List user's tags with usage counts
- update_tag(): Update tag properties
- archive_tag(): Soft delete tag and detach from positions
- restore_tag(): Restore archived tag
- create_default_tags(): Create starter tags for new users

**Related Services**:
- PositionTagService: Position-tag relationship management

**Frontend Integration**:
- Service: src/services/tagsApi.ts (lines 10-62 - tag management methods)
- Hook: src/hooks/useTags.ts

**Documentation**: backend/TAGGING_ARCHITECTURE.md
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models import TagV2, PositionTag
from app.core.logging import get_logger

logger = get_logger(__name__)


class TagService:
    """Service for managing user-scoped tags"""

    def __init__(self, db: AsyncSession):
        """Initialize with database session"""
        self.db = db

    async def create_tag(
        self,
        user_id: UUID,
        name: str,
        color: Optional[str] = None,
        description: Optional[str] = None,
        display_order: Optional[int] = None
    ) -> TagV2:
        """
        Create a new tag for a user

        Args:
            user_id: User who owns this tag
            name: Name of the tag
            color: Hex color code (e.g., #4A90E2)
            description: Optional description
            display_order: Display order for UI

        Returns:
            Created TagV2 object

        Raises:
            ValueError: If tag with same name already exists for user
        """
        try:
            # Check if active tag with same name exists for user
            existing = await self.db.execute(
                select(TagV2).where(
                    and_(
                        TagV2.user_id == user_id,
                        TagV2.name == name,
                        TagV2.is_archived == False
                    )
                )
            )
            if existing.scalar():
                raise ValueError(f"Tag '{name}' already exists for this user")

            # If no display_order provided, get the next available order
            if display_order is None:
                max_order = await self.db.execute(
                    select(func.max(TagV2.display_order)).where(TagV2.user_id == user_id)
                )
                display_order = (max_order.scalar() or 0) + 1

            # Create the tag
            tag = TagV2(
                id=uuid4(),
                user_id=user_id,
                name=name,
                color=color or "#4A90E2",  # Default blue
                description=description,
                display_order=display_order
            )

            self.db.add(tag)
            await self.db.commit()
            await self.db.refresh(tag)

            logger.info(f"Created tag {tag.id} ({tag.name}) for user {user_id}")
            return tag

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create tag: {e}")
            raise ValueError(f"Failed to create tag: {e}")

    async def get_tag(
        self,
        tag_id: UUID,
        include_positions: bool = False
    ) -> Optional[TagV2]:
        """
        Get a tag by ID

        Args:
            tag_id: Tag ID
            include_positions: Include associated position-tag relationships

        Returns:
            TagV2 object or None
        """
        query = select(TagV2).where(TagV2.id == tag_id)

        if include_positions:
            query = query.options(
                selectinload(TagV2.position_tags).selectinload(PositionTag.position)
            )

        result = await self.db.execute(query)
        tag = result.scalars().first()

        if tag and include_positions:
            tag.position_count = len(tag.position_tags or [])
            tag.usage_count = tag.position_count

        return tag

    async def get_user_tags(
        self,
        user_id: UUID,
        include_archived: bool = False,
        include_usage_stats: bool = True
    ) -> List[TagV2]:
        """
        Get all tags for a user

        Args:
            user_id: User ID
            include_archived: Include archived tags
            include_usage_stats: Include usage statistics

        Returns:
            List of TagV2 objects
        """
        query = select(TagV2).where(TagV2.user_id == user_id)

        if not include_archived:
            query = query.where(TagV2.is_archived == False)

        # Order by display_order
        query = query.order_by(TagV2.display_order)

        if include_usage_stats:
            query = query.options(selectinload(TagV2.position_tags))

        result = await self.db.execute(query)
        tags = result.scalars().all()

        # Update usage counts if requested - count BOTH sources
        if include_usage_stats:
            for tag in tags:
                position_count = len(tag.position_tags) if tag.position_tags else 0
                tag.position_count = position_count
                tag.usage_count = position_count

        return tags

    async def update_tag(
        self,
        tag_id: UUID,
        name: Optional[str] = None,
        color: Optional[str] = None,
        description: Optional[str] = None,
        display_order: Optional[int] = None
    ) -> Optional[TagV2]:
        """
        Update a tag

        Args:
            tag_id: Tag to update
            name: New name (optional)
            color: New color (optional)
            description: New description (optional)
            display_order: New display order (optional)

        Returns:
            Updated TagV2 or None if not found
        """
        tag = await self.get_tag(tag_id)
        if not tag:
            return None

        if name is not None:
            # Check if name already exists for user
            existing = await self.db.execute(
                select(TagV2).where(
                    and_(
                        TagV2.user_id == tag.user_id,
                        TagV2.name == name,
                        TagV2.id != tag_id,
                        TagV2.is_archived == False
                    )
                )
            )
            if existing.scalar():
                raise ValueError(f"Tag '{name}' already exists for this user")
            tag.name = name

        if color is not None:
            tag.color = color
        if description is not None:
            tag.description = description
        if display_order is not None:
            tag.display_order = display_order

        tag.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(tag)

        logger.info(f"Updated tag {tag_id}")
        return tag

    async def archive_tag(
        self,
        tag_id: UUID,
        archived_by: Optional[UUID] = None
    ) -> bool:
        """
        Archive a tag (soft delete)

        This will also remove all position tag associations so archived tags
        no longer appear on positions.

        Args:
            tag_id: Tag to archive
            archived_by: User who archived it

        Returns:
            True if archived, False if not found
        """
        tag = await self.get_tag(tag_id)
        if not tag:
            return False

        if tag.is_archived:
            logger.warning(f"Tag {tag_id} is already archived")
            return True

        # Remove all position tag associations so archived tags no longer surface
        await self.db.execute(
            delete(PositionTag).where(PositionTag.tag_id == tag_id)
        )
        logger.info(f"Removed all position_tags for archived tag {tag_id}")

        # Archive the tag
        tag.is_archived = True
        tag.archived_at = datetime.utcnow()
        tag.archived_by = archived_by

        await self.db.commit()
        logger.info(f"Archived tag {tag_id}")
        return True

    async def restore_tag(
        self,
        tag_id: UUID
    ) -> bool:
        """
        Restore an archived tag

        Args:
            tag_id: Tag to restore

        Returns:
            True if restored, False if not found
        """
        tag = await self.get_tag(tag_id)
        if not tag:
            return False

        if not tag.is_archived:
            logger.warning(f"Tag {tag_id} is not archived")
            return True

        tag.is_archived = False
        tag.archived_at = None
        tag.archived_by = None

        await self.db.commit()
        logger.info(f"Restored tag {tag_id}")
        return True

    async def create_default_tags(
        self,
        user_id: UUID
    ) -> List[TagV2]:
        """
        Create default tag set for a new user

        Args:
            user_id: User to create tags for

        Returns:
            List of created tags
        """
        default_tags = TagV2.default_tags()  # Get default tag definitions
        created = []

        for i, tag_def in enumerate(default_tags):
            try:
                tag = await self.create_tag(
                    user_id=user_id,
                    name=tag_def['name'],
                    color=tag_def['color'],
                    description=tag_def.get('description'),
                    display_order=i
                )
                created.append(tag)
            except ValueError as e:
                logger.warning(f"Skipping default tag {tag_def['name']}: {e}")
                continue

        logger.info(f"Created {len(created)} default tags for user {user_id}")
        return created
