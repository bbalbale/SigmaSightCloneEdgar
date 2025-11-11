"""
Position realized P&L event model.

Captures each realized trade (full or partial) so we can build accurate
portfolio-level realized P&L timelines and audit trails.
"""
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PositionRealizedEvent(Base):
    """Individual realized P&L events for a position (supports partial closes)."""

    __tablename__ = "position_realized_events"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    position_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    portfolio_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_closed: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships for eager loading / backrefs
    position = relationship("Position", back_populates="realized_events")
    portfolio = relationship("Portfolio", back_populates="position_realized_events")

    __table_args__ = (
        Index("ix_position_realized_events_portfolio_date", "portfolio_id", "trade_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<PositionRealizedEvent position_id={self.position_id} trade_date={self.trade_date} "
            f"quantity_closed={self.quantity_closed} realized_pnl={self.realized_pnl}>"
        )
