"""
Sector Tag Service - Automatic sector-based tagging for positions

This service handles:
1. Sector-to-color mapping for consistent tag appearance
2. Auto-creation of sector tags when positions are created
3. Batch restoration of sector tags for portfolios
4. Integration with company profile data to determine sectors
"""
from typing import Optional, Dict, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.models.tags_v2 import TagV2
from app.models.position_tags import PositionTag
from app.models.positions import Position
from app.models.market_data import CompanyProfile
from app.core.logging import get_logger

logger = get_logger(__name__)


# Predefined sector-to-color mapping
# Using Material Design colors for visual consistency
SECTOR_COLORS = {
    "Technology": "#2196F3",              # Blue
    "Healthcare": "#4CAF50",              # Green
    "Financial Services": "#FF9800",      # Orange
    "Financials": "#FF9800",              # Orange (alternative name)
    "Energy": "#FFC107",                  # Amber
    "Consumer Discretionary": "#9C27B0",  # Purple
    "Consumer Cyclical": "#9C27B0",       # Purple (alternative name)
    "Consumer Defensive": "#E91E63",      # Pink
    "Consumer Staples": "#E91E63",        # Pink (alternative name)
    "Industrials": "#795548",             # Brown
    "Materials": "#607D8B",               # Blue Grey
    "Basic Materials": "#607D8B",         # Blue Grey (alternative name)
    "Real Estate": "#00BCD4",             # Cyan
    "Utilities": "#8BC34A",               # Light Green
    "Communication Services": "#3F51B5",  # Indigo
    "Telecommunication Services": "#3F51B5",  # Indigo (alternative name)
    "Uncategorized": "#9E9E9E",           # Grey
    "Unknown": "#9E9E9E",                 # Grey (alternative)
}

# Default color for any sector not in the mapping
DEFAULT_SECTOR_COLOR = "#78909C"  # Blue Grey 400


def get_sector_color(sector_name: Optional[str]) -> str:
    """
    Get the predefined color for a sector.

    Args:
        sector_name: Name of the sector (e.g., "Technology", "Healthcare")

    Returns:
        Hex color code for the sector
    """
    if not sector_name:
        return SECTOR_COLORS["Uncategorized"]

    # Normalize sector name (title case, strip whitespace)
    normalized_sector = sector_name.strip().title()

    # Return mapped color or default
    return SECTOR_COLORS.get(normalized_sector, DEFAULT_SECTOR_COLOR)


async def get_or_create_sector_tag(
    db: AsyncSession,
    user_id: UUID,
    sector_name: Optional[str]
) -> TagV2:
    """
    Get existing sector tag or create a new one.

    This function ensures that each user has exactly one tag per sector,
    maintaining consistency across the portfolio.

    Args:
        db: Database session
        user_id: UUID of the user
        sector_name: Name of the sector (or None for "Uncategorized")

    Returns:
        TagV2 instance for the sector
    """
    # Normalize sector name
    tag_name = sector_name.strip().title() if sector_name else "Uncategorized"

    # Check if tag already exists for this user
    stmt = select(TagV2).where(
        and_(
            TagV2.user_id == user_id,
            TagV2.name == tag_name,
            TagV2.is_archived == False
        )
    )
    result = await db.execute(stmt)
    existing_tag = result.scalar_one_or_none()

    if existing_tag:
        logger.debug(f"Using existing sector tag '{tag_name}' for user {user_id}")
        return existing_tag

    # Create new sector tag
    color = get_sector_color(tag_name)
    description = f"Sector: {tag_name}" if tag_name != "Uncategorized" else "Positions without sector classification"

    new_tag = TagV2(
        user_id=user_id,
        name=tag_name,
        color=color,
        description=description,
        display_order=0  # Sector tags don't have special ordering
    )

    db.add(new_tag)
    await db.flush()  # Flush to get the ID without committing

    logger.info(f"Created new sector tag '{tag_name}' (color: {color}) for user {user_id}")
    return new_tag


async def apply_sector_tag_to_position(
    db: AsyncSession,
    position_id: UUID,
    user_id: UUID
) -> Dict[str, any]:
    """
    Apply sector tag to a specific position based on its company profile.

    Args:
        db: Database session
        position_id: UUID of the position
        user_id: UUID of the user (for tag ownership)

    Returns:
        Dict with status and tag information:
        {
            "success": bool,
            "tag_created": bool,
            "tag_name": str,
            "sector": str | None,
            "message": str
        }
    """
    # Get the position
    position_stmt = select(Position).where(Position.id == position_id)
    position_result = await db.execute(position_stmt)
    position = position_result.scalar_one_or_none()

    if not position:
        return {
            "success": False,
            "tag_created": False,
            "message": f"Position {position_id} not found"
        }

    # Get company profile for the position's symbol
    profile_stmt = select(CompanyProfile).where(
        CompanyProfile.symbol == position.symbol
    )
    profile_result = await db.execute(profile_stmt)
    company_profile = profile_result.scalar_one_or_none()

    # Determine sector (or use "Uncategorized" if not available)
    sector = company_profile.sector if company_profile and company_profile.sector else None

    # Get or create the sector tag
    sector_tag = await get_or_create_sector_tag(db, user_id, sector)
    tag_was_new = sector_tag.id is None  # Check if tag was just created

    # Check if position already has this tag
    existing_link_stmt = select(PositionTag).where(
        and_(
            PositionTag.position_id == position_id,
            PositionTag.tag_id == sector_tag.id
        )
    )
    existing_link_result = await db.execute(existing_link_stmt)
    existing_link = existing_link_result.scalar_one_or_none()

    if existing_link:
        return {
            "success": True,
            "tag_created": False,
            "tag_name": sector_tag.name,
            "sector": sector,
            "message": f"Position already has sector tag '{sector_tag.name}'"
        }

    # Create the position-tag link
    position_tag = PositionTag(
        position_id=position_id,
        tag_id=sector_tag.id,
        assigned_by=user_id
    )
    db.add(position_tag)
    await db.flush()

    # Update tag usage count
    sector_tag.usage_count = (sector_tag.usage_count or 0) + 1

    logger.info(
        f"Applied sector tag '{sector_tag.name}' to position {position.symbol} "
        f"(sector: {sector or 'Uncategorized'})"
    )

    return {
        "success": True,
        "tag_created": tag_was_new,
        "tag_name": sector_tag.name,
        "sector": sector,
        "message": f"Successfully tagged position with '{sector_tag.name}'"
    }


async def restore_sector_tags_for_portfolio(
    db: AsyncSession,
    portfolio_id: UUID,
    user_id: UUID
) -> Dict[str, any]:
    """
    Restore sector tags for all positions in a portfolio.

    This function:
    1. Gets all positions in the portfolio
    2. Removes existing sector tags (tags with "Sector:" in description)
    3. Re-applies sector tags based on current company profile data

    Args:
        db: Database session
        portfolio_id: UUID of the portfolio
        user_id: UUID of the user

    Returns:
        Dict with restoration statistics:
        {
            "positions_tagged": int,
            "positions_skipped": int,
            "tags_created": int,
            "tags_applied": [{"tag_name": str, "position_count": int}]
        }
    """
    # Get all positions in the portfolio
    positions_stmt = select(Position).where(Position.portfolio_id == portfolio_id)
    positions_result = await db.execute(positions_stmt)
    positions = positions_result.scalars().all()

    if not positions:
        return {
            "positions_tagged": 0,
            "positions_skipped": 0,
            "tags_created": 0,
            "tags_applied": []
        }

    # Get all sector tags for this user (tags with "Sector:" in description)
    sector_tags_stmt = select(TagV2).where(
        and_(
            TagV2.user_id == user_id,
            TagV2.description.like("Sector:%"),
            TagV2.is_archived == False
        )
    )
    sector_tags_result = await db.execute(sector_tags_stmt)
    sector_tags = {tag.id for tag in sector_tags_result.scalars().all()}

    # Remove existing sector tags from all positions
    if sector_tags:
        position_ids = [p.id for p in positions]
        delete_stmt = select(PositionTag).where(
            and_(
                PositionTag.position_id.in_(position_ids),
                PositionTag.tag_id.in_(sector_tags)
            )
        )
        delete_result = await db.execute(delete_stmt)
        tags_to_delete = delete_result.scalars().all()

        for tag_link in tags_to_delete:
            await db.delete(tag_link)

        logger.info(f"Removed {len(tags_to_delete)} existing sector tag links")

    # Apply sector tags to all positions
    positions_tagged = 0
    positions_skipped = 0
    tags_created_count = 0
    tag_usage = {}  # Track which tags were applied and how many times

    for position in positions:
        result = await apply_sector_tag_to_position(db, position.id, user_id)

        if result["success"]:
            positions_tagged += 1
            if result["tag_created"]:
                tags_created_count += 1

            # Track tag usage
            tag_name = result["tag_name"]
            tag_usage[tag_name] = tag_usage.get(tag_name, 0) + 1
        else:
            positions_skipped += 1

    # Format tag usage for response
    tags_applied = [
        {"tag_name": name, "position_count": count}
        for name, count in sorted(tag_usage.items(), key=lambda x: x[1], reverse=True)
    ]

    await db.commit()

    logger.info(
        f"Restored sector tags for portfolio {portfolio_id}: "
        f"{positions_tagged} tagged, {positions_skipped} skipped, "
        f"{tags_created_count} tags created"
    )

    return {
        "positions_tagged": positions_tagged,
        "positions_skipped": positions_skipped,
        "tags_created": tags_created_count,
        "tags_applied": tags_applied
    }


async def get_sector_distribution(
    db: AsyncSession,
    portfolio_id: UUID
) -> Dict[str, int]:
    """
    Get the distribution of sectors across portfolio positions.

    Useful for analytics and visualization.

    Args:
        db: Database session
        portfolio_id: UUID of the portfolio

    Returns:
        Dict mapping sector names to position counts
    """
    # Get all positions with their company profiles
    stmt = (
        select(CompanyProfile.sector, func.count(Position.id).label('count'))
        .select_from(Position)
        .outerjoin(CompanyProfile, Position.symbol == CompanyProfile.symbol)
        .where(Position.portfolio_id == portfolio_id)
        .group_by(CompanyProfile.sector)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Build distribution dict
    distribution = {}
    for sector, count in rows:
        sector_name = sector if sector else "Uncategorized"
        distribution[sector_name] = count

    return distribution
