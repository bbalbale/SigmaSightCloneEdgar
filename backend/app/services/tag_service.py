"""
Tag Service - Business Logic for Tag Management (Service Layer)

This service handles tag lifecycle operations (create/update/delete) and includes
DEPRECATED strategy tagging methods kept for backward compatibility.

**Architecture Context** (3-tier separation of concerns):
- API Layer: app/api/v1/tags.py (FastAPI endpoints)
- THIS FILE (Service Layer): Tag management business logic
- Data Layer: app/models/tags_v2.py (TagV2, StrategyTag)

**Tag Management Methods** (Active - Use these):
- create_tag(): Create new tag
- get_tag(): Get tag by ID
- get_user_tags(): List user's tags
- update_tag(): Update tag properties
- archive_tag(): Soft delete tag
- restore_tag(): Restore archived tag
- create_default_tags(): Create starter tags for new users

**Strategy Tagging Methods** (DEPRECATED - Do not use for new features):
- assign_tag_to_strategy() ⚠️ Use PositionTagService.assign_tag_to_position() instead
- remove_tag_from_strategy() ⚠️ Use PositionTagService.remove_tag_from_position() instead
- get_strategies_by_tag() ⚠️ Use PositionTagService.get_positions_by_tag() instead
- bulk_assign_tags() ⚠️ Use PositionTagService.bulk_assign_tags() instead

**Used By**:
- app/api/v1/tags.py: Tag management endpoints
- app/api/v1/position_tags.py: For tag validation

**Related Services**:
- PositionTagService: Position-tag relationship management (PREFERRED)

**Frontend Integration**:
- Service: src/services/tagsApi.ts (lines 10-62 - tag management methods)
- Hook: src/hooks/useTags.ts

**Documentation**: backend/TAGGING_ARCHITECTURE.md
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models import TagV2, StrategyTag, Strategy, User
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
        include_strategies: bool = False
    ) -> Optional[TagV2]:
        """
        Get a tag by ID

        Args:
            tag_id: Tag ID
            include_strategies: Include associated strategies

        Returns:
            TagV2 object or None
        """
        query = select(TagV2).where(TagV2.id == tag_id)

        if include_strategies:
            query = query.options(selectinload(TagV2.strategy_tags))

        result = await self.db.execute(query)
        return result.scalars().first()

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
            # Load both strategy_tags (legacy) and position_tags (new preferred method)
            query = query.options(
                selectinload(TagV2.strategy_tags),
                selectinload(TagV2.position_tags)
            )

        result = await self.db.execute(query)
        tags = result.scalars().all()

        # Update usage counts if requested - count BOTH sources
        if include_usage_stats:
            for tag in tags:
                strategy_count = len(tag.strategy_tags) if tag.strategy_tags else 0
                position_count = len(tag.position_tags) if tag.position_tags else 0
                tag.usage_count = strategy_count + position_count

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

        This will also remove all position_tags and strategy_tags associations
        to prevent archived tags from appearing on positions/strategies.

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

        # Remove all position_tags associations (NEW - prevents archived tags from showing)
        from app.models.position_tags import PositionTag
        await self.db.execute(
            delete(PositionTag).where(PositionTag.tag_id == tag_id)
        )
        logger.info(f"Removed all position_tags for archived tag {tag_id}")

        # Remove all strategy_tags associations (DEPRECATED but still needed for backward compat)
        await self.db.execute(
            delete(StrategyTag).where(StrategyTag.tag_id == tag_id)
        )
        logger.info(f"Removed all strategy_tags for archived tag {tag_id}")

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

    async def assign_tag_to_strategy(
        self,
        tag_id: UUID,
        strategy_id: UUID,
        assigned_by: Optional[UUID] = None
    ) -> StrategyTag:
        """
        Assign a tag to a strategy

        Args:
            tag_id: Tag to assign
            strategy_id: Strategy to tag
            assigned_by: User who assigned it

        Returns:
            Created StrategyTag association

        Raises:
            ValueError: If tag or strategy not found, or already assigned
        """
        # Verify tag exists
        tag = await self.get_tag(tag_id)
        if not tag:
            raise ValueError(f"Tag {tag_id} not found")

        if tag.is_archived:
            raise ValueError(f"Cannot assign archived tag {tag_id}")

        # Verify strategy exists
        strategy_result = await self.db.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = strategy_result.scalar()
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        # Check if already assigned
        existing = await self.db.execute(
            select(StrategyTag).where(
                and_(
                    StrategyTag.strategy_id == strategy_id,
                    StrategyTag.tag_id == tag_id
                )
            )
        )
        if existing.scalar():
            raise ValueError(f"Tag already assigned to this strategy")

        # Create the association
        strategy_tag = StrategyTag(
            id=uuid4(),
            strategy_id=strategy_id,
            tag_id=tag_id,
            assigned_by=assigned_by
        )

        self.db.add(strategy_tag)

        # Increment usage count
        tag.usage_count = (tag.usage_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(strategy_tag)

        logger.info(f"Assigned tag {tag_id} to strategy {strategy_id}")
        return strategy_tag

    async def remove_tag_from_strategy(
        self,
        tag_id: UUID,
        strategy_id: UUID
    ) -> bool:
        """
        Remove a tag from a strategy

        Args:
            tag_id: Tag to remove
            strategy_id: Strategy to remove from

        Returns:
            True if removed, False if not found
        """
        # Find the association
        result = await self.db.execute(
            select(StrategyTag).where(
                and_(
                    StrategyTag.strategy_id == strategy_id,
                    StrategyTag.tag_id == tag_id
                )
            )
        )
        strategy_tag = result.scalar()

        if not strategy_tag:
            return False

        # Delete the association
        await self.db.delete(strategy_tag)

        # Decrement usage count
        tag = await self.get_tag(tag_id)
        if tag and tag.usage_count > 0:
            tag.usage_count -= 1

        await self.db.commit()
        logger.info(f"Removed tag {tag_id} from strategy {strategy_id}")
        return True

    async def get_strategies_by_tag(
        self,
        tag_id: UUID,
        portfolio_id: Optional[UUID] = None
    ) -> List[Strategy]:
        """
        Get all strategies with a specific tag

        Args:
            tag_id: Tag to filter by
            portfolio_id: Optional portfolio filter

        Returns:
            List of Strategy objects
        """
        query = (
            select(Strategy)
            .join(StrategyTag, Strategy.id == StrategyTag.strategy_id)
            .where(StrategyTag.tag_id == tag_id)
        )

        if portfolio_id:
            query = query.where(Strategy.portfolio_id == portfolio_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_tags_for_strategy(
        self,
        strategy_id: UUID
    ) -> List[TagV2]:
        """Return TagV2 objects assigned to a strategy"""
        query = (
            select(TagV2)
            .join(StrategyTag, TagV2.id == StrategyTag.tag_id)
            .where(StrategyTag.strategy_id == strategy_id)
            .order_by(TagV2.display_order)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def replace_tags_for_strategy(
        self,
        strategy_id: UUID,
        tag_ids: List[UUID],
        assigned_by: Optional[UUID] = None
    ) -> List[StrategyTag]:
        """Replace existing tags with provided list for a strategy"""
        # Remove existing tags
        await self.db.execute(
            delete(StrategyTag).where(StrategyTag.strategy_id == strategy_id)
        )

        created: List[StrategyTag] = []
        for tag_id in tag_ids:
            # Ensure tag exists
            tag = await self.get_tag(tag_id)
            if not tag or tag.is_archived:
                continue
            assoc = StrategyTag(strategy_id=strategy_id, tag_id=tag_id, assigned_by=assigned_by)
            self.db.add(assoc)
            created.append(assoc)

        await self.db.commit()
        return created

    async def remove_tags_from_strategy(
        self,
        strategy_id: UUID,
        tag_ids: List[UUID]
    ) -> int:
        """Remove a list of tags from a strategy; returns count removed"""
        result = await self.db.execute(
            delete(StrategyTag).where(
                and_(
                    StrategyTag.strategy_id == strategy_id,
                    StrategyTag.tag_id.in_(tag_ids)
                )
            )
        )
        # SQLAlchemy 2.0 async returns a CursorResult; rowcount may be -1 on some backends, ignore
        await self.db.commit()
        return 0

    async def bulk_assign_tags(
        self,
        strategy_id: UUID,
        tag_ids: List[UUID],
        assigned_by: Optional[UUID] = None,
        replace_existing: bool = False
    ) -> List[StrategyTag]:
        """
        Assign multiple tags to a strategy

        Args:
            strategy_id: Strategy to tag
            tag_ids: List of tag IDs to assign
            assigned_by: User who assigned them
            replace_existing: If True, remove existing tags first

        Returns:
            List of created StrategyTag associations
        """
        if replace_existing:
            # Remove all existing tags for this strategy
            await self.db.execute(
                delete(StrategyTag).where(StrategyTag.strategy_id == strategy_id)
            )

        created_tags = []
        for tag_id in tag_ids:
            try:
                strategy_tag = await self.assign_tag_to_strategy(
                    tag_id=tag_id,
                    strategy_id=strategy_id,
                    assigned_by=assigned_by
                )
                created_tags.append(strategy_tag)
            except ValueError as e:
                logger.warning(f"Skipping tag {tag_id}: {e}")
                continue

        return created_tags

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
