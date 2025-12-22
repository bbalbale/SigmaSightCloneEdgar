"""
Activity Tracking Service for User Journey Analytics

Provides non-blocking event recording for:
- Onboarding funnel (registration, login, portfolio creation)
- Chat interactions (sessions, messages, feedback)
- Portfolio operations (views, updates)

Data flows to user_activity_events table for admin dashboard analytics.
Implements fire-and-forget pattern to avoid impacting user-facing latency.

Created: December 22, 2025 (Admin Dashboard Phase 3)
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_async_session
from app.models.admin import UserActivityEvent

logger = logging.getLogger(__name__)


class ActivityTrackingService:
    """
    Service for tracking user activity events.

    Uses fire-and-forget pattern to avoid blocking the main request.
    Events are recorded to user_activity_events table for analytics.
    """

    # Event type constants for type safety and consistency
    # Onboarding events
    EVENT_REGISTER_START = "onboarding.register_start"
    EVENT_REGISTER_COMPLETE = "onboarding.register_complete"
    EVENT_REGISTER_ERROR = "onboarding.register_error"
    EVENT_LOGIN_SUCCESS = "onboarding.login_success"
    EVENT_LOGIN_ERROR = "onboarding.login_error"
    EVENT_PORTFOLIO_START = "onboarding.portfolio_start"
    EVENT_PORTFOLIO_COMPLETE = "onboarding.portfolio_complete"
    EVENT_PORTFOLIO_ERROR = "onboarding.portfolio_error"

    # Chat events
    EVENT_CHAT_SESSION_START = "chat.session_start"
    EVENT_CHAT_MESSAGE_SENT = "chat.message_sent"
    EVENT_CHAT_FEEDBACK_GIVEN = "chat.feedback_given"

    # Auth events
    EVENT_AUTH_LOGOUT = "auth.logout"
    EVENT_AUTH_TOKEN_REFRESH = "auth.token_refresh"

    # Category mappings
    CATEGORY_ONBOARDING = "onboarding"
    CATEGORY_AUTH = "auth"
    CATEGORY_CHAT = "chat"
    CATEGORY_PORTFOLIO = "portfolio"

    @staticmethod
    def _get_category(event_type: str) -> str:
        """Extract category from event type (first part before dot)."""
        if "." in event_type:
            return event_type.split(".")[0]
        return "unknown"

    @staticmethod
    async def _record_event(
        event_type: str,
        event_category: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Internal method to record an event to the database.

        Should be called via track_event() for fire-and-forget behavior.
        """
        try:
            async with get_async_session() as db:
                event = UserActivityEvent(
                    user_id=user_id,
                    session_id=session_id,
                    event_type=event_type,
                    event_category=event_category,
                    event_data=event_data or {},
                    error_code=error_code,
                    error_message=error_message,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                db.add(event)
                await db.commit()
                logger.debug(f"Recorded activity event: {event_type} for user={user_id}")
        except Exception as e:
            # Never let tracking errors affect the user
            logger.warning(f"Failed to record activity event {event_type}: {e}")

    @classmethod
    def track_event(
        cls,
        event_type: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Fire-and-forget event tracking.

        This method schedules the event recording as a background task,
        allowing the main request to continue without waiting.

        Args:
            event_type: The event type (e.g., 'onboarding.register_complete')
            user_id: The user's UUID (if authenticated)
            session_id: Browser session ID (for pre/post auth correlation)
            event_data: Additional event-specific data (stored as JSONB)
            error_code: Error code for error events
            error_message: Human-readable error message
            ip_address: Client IP address
            user_agent: Client user agent string
        """
        event_category = cls._get_category(event_type)

        # Schedule as background task - fire and forget
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create task
                asyncio.create_task(
                    cls._record_event(
                        event_type=event_type,
                        event_category=event_category,
                        user_id=user_id,
                        session_id=session_id,
                        event_data=event_data,
                        error_code=error_code,
                        error_message=error_message,
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                )
            else:
                # Fallback for sync contexts (shouldn't happen often)
                loop.run_until_complete(
                    cls._record_event(
                        event_type=event_type,
                        event_category=event_category,
                        user_id=user_id,
                        session_id=session_id,
                        event_data=event_data,
                        error_code=error_code,
                        error_message=error_message,
                        ip_address=ip_address,
                        user_agent=user_agent,
                    )
                )
        except Exception as e:
            # Never let tracking errors affect the user
            logger.warning(f"Failed to schedule activity tracking: {e}")

    @classmethod
    async def track_event_async(
        cls,
        event_type: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Async version for when you want to await the recording.

        Use this when you need to ensure the event is recorded before continuing.
        For most cases, use track_event() for fire-and-forget behavior.
        """
        event_category = cls._get_category(event_type)
        await cls._record_event(
            event_type=event_type,
            event_category=event_category,
            user_id=user_id,
            session_id=session_id,
            event_data=event_data,
            error_code=error_code,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )


# Convenience functions for common events
def track_login_success(
    user_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track successful login event."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_LOGIN_SUCCESS,
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_login_error(
    error_code: str,
    error_message: str,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track failed login attempt."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_LOGIN_ERROR,
        session_id=session_id,
        event_data={"email": email} if email else None,
        error_code=error_code,
        error_message=error_message,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_register_start(
    email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track registration start."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_REGISTER_START,
        session_id=session_id,
        event_data={"email": email},
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_register_complete(
    user_id: UUID,
    email: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track successful registration."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_REGISTER_COMPLETE,
        user_id=user_id,
        session_id=session_id,
        event_data={"email": email},
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_register_error(
    error_code: str,
    error_message: str,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track registration error."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_REGISTER_ERROR,
        session_id=session_id,
        event_data={"email": email} if email else None,
        error_code=error_code,
        error_message=error_message,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_portfolio_start(
    user_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track portfolio creation start."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_PORTFOLIO_START,
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_portfolio_complete(
    user_id: UUID,
    portfolio_id: UUID,
    portfolio_name: str,
    position_count: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track successful portfolio creation."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_PORTFOLIO_COMPLETE,
        user_id=user_id,
        session_id=session_id,
        event_data={
            "portfolio_id": str(portfolio_id),
            "portfolio_name": portfolio_name,
            "position_count": position_count,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_portfolio_error(
    user_id: UUID,
    error_code: str,
    error_message: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track portfolio creation error."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_PORTFOLIO_ERROR,
        user_id=user_id,
        session_id=session_id,
        error_code=error_code,
        error_message=error_message,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_chat_session_start(
    user_id: UUID,
    conversation_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Track new chat session/conversation."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_CHAT_SESSION_START,
        user_id=user_id,
        event_data={"conversation_id": str(conversation_id)},
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_chat_message(
    user_id: UUID,
    conversation_id: UUID,
    message_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Track message sent in chat."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_CHAT_MESSAGE_SENT,
        user_id=user_id,
        event_data={
            "conversation_id": str(conversation_id),
            "message_id": str(message_id),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_chat_feedback(
    user_id: UUID,
    message_id: UUID,
    rating: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Track feedback given on AI response."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_CHAT_FEEDBACK_GIVEN,
        user_id=user_id,
        event_data={
            "message_id": str(message_id),
            "rating": rating,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )


def track_logout(
    user_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Track user logout."""
    ActivityTrackingService.track_event(
        event_type=ActivityTrackingService.EVENT_AUTH_LOGOUT,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )


# Module-level singleton for convenience
activity_tracker = ActivityTrackingService()
