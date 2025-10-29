"""
Batch Run Tracking Model - Tracks daily batch processing runs for automatic backfill detection
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Date, Integer, Numeric, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BatchRunTracking(Base):
    """
    Tracks batch processing runs for automatic backfill and monitoring

    Used by BatchOrchestratorV3 to:
    - Detect gaps in processing (automatic backfill)
    - Monitor performance metrics per phase
    - Debug failed runs
    - Report data coverage
    """
    __tablename__ = "batch_run_tracking"

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Run date (unique - one record per day)
    run_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)

    # Phase statuses ('success', 'failed', 'skipped', 'in_progress')
    phase_1_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phase_2_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    phase_3_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Performance metrics (seconds)
    phase_1_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    phase_2_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    phase_3_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Processing metrics
    portfolios_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    symbols_fetched: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data_coverage_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default="now()",
        nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<BatchRunTracking("
            f"run_date={self.run_date}, "
            f"phase_1={self.phase_1_status}, "
            f"phase_2={self.phase_2_status}, "
            f"phase_3={self.phase_3_status}, "
            f"portfolios={self.portfolios_processed}"
            f")>"
        )
