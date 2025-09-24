"""
Position and Tag models
"""
from datetime import datetime, date
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Date, Enum as SQLEnum, Table, Column
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


# Many-to-many association table for positions and tags
position_tags = Table(
    'position_tags',
    Base.metadata,
    Column('position_id', UUID(as_uuid=True), ForeignKey('positions.id'), primary_key=True),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id'), primary_key=True),
    Column('created_at', DateTime(timezone=True), default=datetime.utcnow),
    Index('ix_position_tags_position_id_tag_id', 'position_id', 'tag_id')
)


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

    # Strategy relationship (added for tagging system)
    strategy_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
    tags: Mapped[List["Tag"]] = relationship("Tag", secondary=position_tags, back_populates="positions")
    # strategy: Mapped[Optional["Strategy"]] = relationship("Strategy", back_populates="positions", foreign_keys=[strategy_id])
    # strategy_legs: Mapped[List["StrategyLeg"]] = relationship("StrategyLeg", back_populates="position")
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
    """Tag model - stores user-defined tags for positions"""
    __tablename__ = "tags"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_type: Mapped[TagType] = mapped_column(SQLEnum(TagType), nullable=False, default=TagType.REGULAR)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color code
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="tags")
    positions: Mapped[List["Position"]] = relationship("Position", secondary=position_tags, back_populates="tags")
    
    __table_args__ = (
        Index('ix_tags_user_id_name', 'user_id', 'name', unique=True),
        Index('ix_tags_tag_type', 'tag_type'),
    )
