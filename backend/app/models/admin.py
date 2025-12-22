"""
Admin user and session models for SigmaSight Admin Dashboard

Completely separate from regular user authentication.
Admin users have their own table, JWT claims, and session tracking.

Also includes UserActivityEvent for onboarding funnel tracking.
"""
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, Index, Text, Boolean, Date, Numeric, UniqueConstraint
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


class AIRequestMetrics(Base):
    """
    AI request metrics for performance monitoring and analytics.

    Tracks metrics for each AI chat request:
    - Token usage (prompt, completion, total)
    - Latency (time to first token, total response time)
    - Tool usage (count and details)
    - Errors (type and message)

    Data retention: 30 days rolling (aggregated to daily_metrics)

    Created: December 22, 2025 (Phase 4 Admin Dashboard)
    """
    __tablename__ = "ai_request_metrics"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Request identification
    conversation_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    message_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Model information
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Token usage
    input_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)   # Prompt/input tokens
    output_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)  # Completion/output tokens
    total_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)   # input + output

    # Latency metrics (milliseconds)
    first_token_ms: Mapped[Optional[int]] = mapped_column(nullable=True)  # Time to first token
    total_latency_ms: Mapped[Optional[int]] = mapped_column(nullable=True)  # Total response time

    # Tool usage
    tool_calls_count: Mapped[int] = mapped_column(nullable=False, default=0)
    tool_calls: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # Tool names and durations

    # Error tracking
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_ai_request_metrics_conversation_id', 'conversation_id'),
        Index('ix_ai_request_metrics_message_id', 'message_id'),
        Index('ix_ai_request_metrics_user_id', 'user_id'),
        Index('ix_ai_request_metrics_model', 'model'),
        Index('ix_ai_request_metrics_error_type', 'error_type'),
        Index('ix_ai_request_metrics_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<AIRequestMetrics {self.id} conv={self.conversation_id} latency={self.total_latency_ms}ms>"


class BatchRunHistory(Base):
    """
    Historical batch processing runs for monitoring and analytics.

    Tracks each batch orchestrator run:
    - Status (running, completed, failed)
    - Job counts (total, completed, failed)
    - Phase durations for performance analysis
    - Error summaries for debugging

    Data retention: 30 days rolling

    Created: December 22, 2025 (Phase 5 Admin Dashboard)
    """
    __tablename__ = "batch_run_history"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Run identification
    batch_run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    triggered_by: Mapped[str] = mapped_column(String(255), nullable=False)  # "cron", "manual", "admin:email"

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # running, completed, failed, partial

    # Job tracking
    total_jobs: Mapped[int] = mapped_column(nullable=False, default=0)
    completed_jobs: Mapped[int] = mapped_column(nullable=False, default=0)
    failed_jobs: Mapped[int] = mapped_column(nullable=False, default=0)

    # Performance metrics
    phase_durations: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Example: {"phase_1_market_data": 45.2, "phase_2_pnl": 12.1, "phase_3_analytics": 30.5}

    # Error details
    error_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # Example: {"count": 3, "types": ["timeout", "api_error"], "details": [...]}

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_batch_run_history_batch_run_id', 'batch_run_id'),
        Index('ix_batch_run_history_status', 'status'),
        Index('ix_batch_run_history_started_at', 'started_at'),
        Index('ix_batch_run_history_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<BatchRunHistory {self.batch_run_id} status={self.status}>"


class DailyMetrics(Base):
    """
    Pre-aggregated daily metrics for efficient dashboard queries.

    Stores aggregated metrics from raw event tables:
    - User activity aggregations (registrations, logins, etc.)
    - AI metrics aggregations (token usage, latency percentiles, etc.)
    - Batch processing aggregations (run counts, success rates, etc.)

    Data retention: Permanent (small data volume)

    Created: December 22, 2025 (Phase 5 Admin Dashboard)
    """
    __tablename__ = "daily_metrics"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Metric identification
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Examples: "user_registrations", "ai_requests", "batch_runs", "avg_latency_p50"

    # Metric value
    metric_value: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)

    # Dimensions for drill-down (optional grouping)
    dimensions: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Examples: {"model": "gpt-4o"}, {"error_code": "AUTH_001"}, {}

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('date', 'metric_type', 'dimensions', name='uq_daily_metrics_date_type_dims'),
        Index('ix_daily_metrics_date', 'date'),
        Index('ix_daily_metrics_metric_type', 'metric_type'),
        Index('ix_daily_metrics_date_type', 'date', 'metric_type'),
    )

    def __repr__(self):
        return f"<DailyMetrics {self.date} {self.metric_type}={self.metric_value}>"
