"""
Usage tracking service for SigmaSight.

Handles AI message counting and tier-based limits.

PRD Reference: Section 9.2.1
"""
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_tier_limit
from app.core.logging import get_logger
from app.models.users import User

logger = get_logger(__name__)


async def check_and_increment_ai_messages(
    db: AsyncSession, user: User
) -> Tuple[bool, int, int]:
    """
    Check AI message limit and increment usage counter.

    Implements monthly reset logic and tier-based limits.
    Simple counter approach (not atomic) - occasional 101st message
    is acceptable for MVP per PRD Section 9.2.1.

    Args:
        db: Database session
        user: User object with tier and usage fields

    Returns:
        Tuple of (allowed: bool, remaining: int, limit: int)
        - allowed: True if message is allowed, False if limit reached
        - remaining: Messages remaining after this one
        - limit: Total monthly limit for user's tier

    Example:
        allowed, remaining, limit = await check_and_increment_ai_messages(db, user)
        if not allowed:
            raise HTTPException(429, "Monthly AI message limit reached")
    """
    now = datetime.now(timezone.utc)

    # Get the user's tier limit
    limit = get_tier_limit(user.tier, "max_ai_messages")

    # Check if we need to reset the counter (new month)
    if user.ai_messages_reset_at:
        reset_date = user.ai_messages_reset_at
        # Ensure reset_date is timezone-aware for comparison
        if reset_date.tzinfo is None:
            reset_date = reset_date.replace(tzinfo=timezone.utc)

        # Reset if we're in a new month
        if (now.year > reset_date.year) or (
            now.year == reset_date.year and now.month > reset_date.month
        ):
            logger.info(
                f"Resetting AI message counter for user {user.email} "
                f"(was {user.ai_messages_used}, new month)"
            )
            user.ai_messages_used = 0
            user.ai_messages_reset_at = now
    else:
        # First time using AI messages, set reset date
        user.ai_messages_reset_at = now

    # Check if limit reached
    if user.ai_messages_used >= limit:
        logger.warning(
            f"User {user.email} reached AI message limit "
            f"({user.ai_messages_used}/{limit})"
        )
        return False, 0, limit

    # Increment counter
    user.ai_messages_used += 1
    await db.commit()

    remaining = limit - user.ai_messages_used

    logger.debug(
        f"User {user.email} AI message {user.ai_messages_used}/{limit} "
        f"({remaining} remaining)"
    )

    return True, remaining, limit


async def get_ai_message_usage(user: User) -> dict:
    """
    Get current AI message usage stats for a user.

    Args:
        user: User object

    Returns:
        dict with usage stats:
        {
            "used": int,
            "limit": int,
            "remaining": int,
            "reset_at": datetime or None,
            "tier": str
        }
    """
    limit = get_tier_limit(user.tier, "max_ai_messages")
    used = user.ai_messages_used or 0
    remaining = max(0, limit - used)

    return {
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "reset_at": user.ai_messages_reset_at,
        "tier": user.tier,
    }
