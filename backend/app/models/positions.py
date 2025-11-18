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

    # User notes (Position Management Phase 1 - Nov 3, 2025)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
    # Direct position tagging (new system)
    position_tags: Mapped[List["PositionTag"]] = relationship("PositionTag", back_populates="position", cascade="all, delete-orphan")
    greeks: Mapped[Optional["PositionGreeks"]] = relationship("PositionGreeks", back_populates="position", uselist=False, cascade="all, delete-orphan")
    factor_exposures: Mapped[List["PositionFactorExposure"]] = relationship("PositionFactorExposure", back_populates="position", cascade="all, delete-orphan")
    market_betas: Mapped[List["PositionMarketBeta"]] = relationship("PositionMarketBeta", back_populates="position", cascade="all, delete-orphan")
    interest_rate_betas: Mapped[List["PositionInterestRateBeta"]] = relationship("PositionInterestRateBeta", back_populates="position", cascade="all, delete-orphan")
    volatility: Mapped[List["PositionVolatility"]] = relationship("PositionVolatility", back_populates="position", cascade="all, delete-orphan")
    target_price: Mapped[Optional["TargetPrice"]] = relationship("TargetPrice", back_populates="position", uselist=False, cascade="all, delete-orphan")
    realized_events: Mapped[List["PositionRealizedEvent"]] = relationship(
        "PositionRealizedEvent",
        back_populates="position",
        cascade="all, delete-orphan",
    )
    
    __table_args__ = (
        Index('ix_positions_portfolio_id', 'portfolio_id'),
        Index('ix_positions_symbol', 'symbol'),
        Index('ix_positions_deleted_at', 'deleted_at'),
        Index('ix_positions_exit_date', 'exit_date'),
        Index('ix_positions_investment_class', 'investment_class'),
        Index('ix_positions_inv_class_subtype', 'investment_class', 'investment_subtype'),
        Index('idx_position_portfolio_active', 'portfolio_id', 'deleted_at'),  # Performance index for active positions
    )

    # Helper methods (Position Management Phase 1 - Nov 3, 2025)
    def is_deleted(self) -> bool:
        """Check if position is soft deleted"""
        return self.deleted_at is not None

    def can_edit_symbol(self) -> bool:
        """
        Check if symbol can be edited.

        Symbol editing only allowed if:
        - Position was created less than 5 minutes ago, AND
        - Position has no snapshots (checked separately in service layer)

        Returns:
            bool: True if < 5 minutes old, False otherwise
        """
        age = datetime.utcnow() - self.created_at
        return age.total_seconds() < 300  # 5 minutes = 300 seconds

    def soft_delete(self):
        """Soft delete this position by setting deleted_at timestamp"""
        self.deleted_at = datetime.utcnow()


class Tag(Base):
    """Deprecated legacy Tag model retained only for migrations."""
    __tablename__ = "tags"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
