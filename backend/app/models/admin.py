"""
Admin user and session models for SigmaSight Admin Dashboard

Completely separate from regular user authentication.
Admin users have their own table, JWT claims, and session tracking.

Also includes UserActivityEvent for onboarding funnel tracking.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, Index, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any
from app.database import Base


class AdminUser(Base):
    """
    Admin user model - completely separate from regular users.

    Roles:
    - admin: Standard admin access
    - super_admin: Full access including sensitive operations
    """
    __tablename__ = "admin_users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    sessions: Mapped[List["AdminSession"]] = relationship("AdminSession", back_populates="admin_user", cascade="all, delete-orphan")


class AdminSession(Base):
    """
    Admin session tracking for token invalidation.

    Stores a hash of the JWT token to enable:
    - Token invalidation on logout
    - Tracking active sessions per admin
    - IP/User-Agent logging for security audit
    """
    __tablename__ = "admin_sessions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    admin_user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    admin_user: Mapped["AdminUser"] = relationship("AdminUser", back_populates="sessions")

    __table_args__ = (
        Index('ix_admin_sessions_admin_user_id', 'admin_user_id'),
        Index('ix_admin_sessions_expires_at', 'expires_at'),
        Index('ix_admin_sessions_token_hash', 'token_hash'),
    )


class UserActivityEvent(Base):
    """
    User activity events for onboarding funnel tracking and analytics.

    Tracks events across the user journey:
    - onboarding.* : Registration and portfolio creation events
    - auth.* : Login/logout events
    - chat.* : Conversation and message events
    - portfolio.* : Portfolio interaction events

    Data retention: 30 days rolling (aggregated to daily_metrics)

    Created: December 22, 2025 (Phase 3 Admin Dashboard)
    """
    __tablename__ = "user_activity_events"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User reference (nullable for anonymous/pre-auth events)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Session tracking (for correlating events before/after auth)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Event classification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Flexible event data (varies by event type)
    event_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Error tracking (for error events)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Client context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_user_activity_events_user_id', 'user_id'),
        Index('ix_user_activity_events_event_type', 'event_type'),
        Index('ix_user_activity_events_event_category', 'event_category'),
        Index('ix_user_activity_events_error_code', 'error_code'),
        Index('ix_user_activity_events_created_at', 'created_at'),
        Index('ix_user_activity_events_session_id', 'session_id'),
    )

    def __repr__(self):
        return f"<UserActivityEvent {self.id} type={self.event_type} user={self.user_id}>"
