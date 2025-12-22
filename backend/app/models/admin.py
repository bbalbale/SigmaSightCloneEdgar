"""
Admin user and session models for SigmaSight Admin Dashboard

Completely separate from regular user authentication.
Admin users have their own table, JWT claims, and session tracking.
"""
from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, Index, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
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
