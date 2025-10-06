"""
Position and Tag models
"""
from datetime import datetime, date
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Date, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
import enum
from app.database import Base


# Position type enum
class PositionType(enum.Enum):
    LC = "LC"      # Long Call
    LP = "LP"      # Long Put
    SC = "SC"      # Short Call
    SP = "SP"      # Short Put
    LONG = "LONG"  # Long Stock
    SHORT = "SHORT" # Short Stock


# Tag type enum
class TagType(enum.Enum):
    REGULAR = "REGULAR"
    STRATEGY = "STRATEGY"


# Legacy position_tags removed in favor of position_tags junction table


class Position(Base):
    """Position model - stores individual positions within portfolios"""
    __tablename__ = "positions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    position_type: Mapped[PositionType] = mapped_column(SQLEnum(PositionType), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    exit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Option-specific fields
    underlying_symbol: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    strike_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Investment classification (new fields for categorization)
    investment_class: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # PUBLIC, OPTIONS, PRIVATE
    investment_subtype: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # STOCK, ETF, HEDGE_FUND, etc.

    # Current market data
    last_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    market_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    unrealized_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    realized_pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
    # Direct position tagging (new system)
    position_tags: Mapped[List["PositionTag"]] = relationship("PositionTag", back_populates="position", cascade="all, delete-orphan")
    greeks: Mapped[Optional["PositionGreeks"]] = relationship("PositionGreeks", back_populates="position", uselist=False)
    factor_exposures: Mapped[List["PositionFactorExposure"]] = relationship("PositionFactorExposure", back_populates="position")
    interest_rate_betas: Mapped[List["PositionInterestRateBeta"]] = relationship("PositionInterestRateBeta", back_populates="position")
    target_price: Mapped[Optional["TargetPrice"]] = relationship("TargetPrice", back_populates="position", uselist=False)
    
    __table_args__ = (
        Index('ix_positions_portfolio_id', 'portfolio_id'),
        Index('ix_positions_symbol', 'symbol'),
        Index('ix_positions_deleted_at', 'deleted_at'),
        Index('ix_positions_exit_date', 'exit_date'),
        Index('ix_positions_investment_class', 'investment_class'),
        Index('ix_positions_inv_class_subtype', 'investment_class', 'investment_subtype'),
    )


class Tag(Base):
    """Deprecated legacy Tag model retained only for migrations."""
    __tablename__ = "tags"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
