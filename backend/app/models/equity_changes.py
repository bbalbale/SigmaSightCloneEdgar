"""
Equity Change Model

Tracks capital contributions and withdrawals at the portfolio level.
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EquityChangeType(str, Enum):
    """Type of equity change recorded for a portfolio."""

    CONTRIBUTION = "CONTRIBUTION"
    WITHDRAWAL = "WITHDRAWAL"


class EquityChange(Base):
    """Represents a capital contribution or withdrawal for a portfolio."""

    __tablename__ = "equity_changes"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id"),
        nullable=False,
        index=True,
    )
    change_type: Mapped[EquityChangeType] = mapped_column(
        SqlEnum(EquityChangeType, name="equity_change_type"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    change_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Soft delete marker",
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="equity_changes")
    created_by_user: Mapped["User"] = relationship("User", back_populates="equity_changes")

    __table_args__ = (
        Index("ix_equity_changes_portfolio_date", "portfolio_id", "change_date"),
    )


__all__ = ["EquityChange", "EquityChangeType"]
