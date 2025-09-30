"""
Portfolio snapshots and batch job models
"""
from datetime import datetime, date
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Date, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, Any
from app.database import Base


class PortfolioSnapshot(Base):
    """Portfolio snapshots - daily portfolio state for historical tracking"""
    __tablename__ = "portfolio_snapshots"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Portfolio values
    total_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    cash_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    long_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    short_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    
    # Exposures
    gross_exposure: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    net_exposure: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    
    # P&L
    daily_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    daily_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6), nullable=True)
    cumulative_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    
    # Aggregated Greeks
    portfolio_delta: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    portfolio_gamma: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    portfolio_theta: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    portfolio_vega: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    
    # Position counts
    num_positions: Mapped[int] = mapped_column(nullable=False)
    num_long_positions: Mapped[int] = mapped_column(nullable=False)
    num_short_positions: Mapped[int] = mapped_column(nullable=False)

    # Equity balance (starting capital + realized P&L)
    equity_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="snapshots")
    
    __table_args__ = (
        UniqueConstraint('portfolio_id', 'snapshot_date', name='uq_portfolio_snapshots_portfolio_date'),
        Index('ix_portfolio_snapshots_portfolio_id', 'portfolio_id'),
        Index('ix_portfolio_snapshots_snapshot_date', 'snapshot_date'),
    )


class BatchJob(Base):
    """Batch jobs - tracks batch job execution history"""
    __tablename__ = "batch_jobs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_name: Mapped[str] = mapped_column(String(100), nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'market_data', 'risk_metrics', 'snapshots'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending')  # 'pending', 'running', 'success', 'failed'
    
    # Execution details
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Results
    records_processed: Mapped[Optional[int]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    job_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_batch_jobs_job_type', 'job_type'),
        Index('ix_batch_jobs_status', 'status'),
        Index('ix_batch_jobs_started_at', 'started_at'),
    )


class BatchJobSchedule(Base):
    """Batch job schedules - defines when batch jobs should run"""
    __tablename__ = "batch_job_schedules"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., '0 16 * * 1-5' for 4 PM weekdays
    is_active: Mapped[bool] = mapped_column(default=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Job configuration
    timeout_seconds: Mapped[int] = mapped_column(nullable=False, default=300)
    retry_count: Mapped[int] = mapped_column(nullable=False, default=3)
    retry_delay_seconds: Mapped[int] = mapped_column(nullable=False, default=60)
    
    # Tracking
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_batch_job_schedules_is_active', 'is_active'),
        Index('ix_batch_job_schedules_next_run_at', 'next_run_at'),
    )
