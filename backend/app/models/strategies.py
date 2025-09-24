"""Strategy models for portfolio position management.

Strategies are containers for positions, enabling multi-leg trade management
and organizational tagging. Every position belongs to exactly one strategy.
"""
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Column, String, Boolean, Numeric, DateTime, ForeignKey, Integer, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base

if TYPE_CHECKING:
    from app.models.positions import Position
    from app.models.users import Portfolio, User


class StrategyType(str, Enum):
    """Types of trading strategies."""
    STANDALONE = "standalone"  # Single position (default)
    COVERED_CALL = "covered_call"  # Long stock + short call
    PROTECTIVE_PUT = "protective_put"  # Long stock + long put
    IRON_CONDOR = "iron_condor"  # 4 option legs
    STRADDLE = "straddle"  # Call + put same strike
    STRANGLE = "strangle"  # Call + put different strikes
    BUTTERFLY = "butterfly"  # 3 option legs
    PAIRS_TRADE = "pairs_trade"  # Long + short correlated assets
    CUSTOM = "custom"  # User-defined strategy


class Strategy(Base):
    """Strategy model representing a container for one or more positions."""

    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    strategy_type = Column(String(50), default=StrategyType.STANDALONE.value, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_synthetic = Column(Boolean, default=False, nullable=False)  # True for multi-leg strategies

    # Aggregated financials
    net_exposure = Column(Numeric(20, 2), nullable=True)
    total_cost_basis = Column(Numeric(20, 2), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # User tracking
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            f"strategy_type IN {tuple(t.value for t in StrategyType)}",
            name="valid_strategy_type"
        ),
    )

    # Relationships
    portfolio = relationship("Portfolio", back_populates="strategies")
    positions = relationship("Position", back_populates="strategy", foreign_keys="Position.strategy_id")
    strategy_legs = relationship("StrategyLeg", cascade="all, delete-orphan", back_populates="strategy")
    strategy_tags = relationship("StrategyTag", cascade="all, delete-orphan", back_populates="strategy")
    metrics = relationship("StrategyMetrics", cascade="all, delete-orphan", back_populates="strategy")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Strategy(id={self.id}, name={self.name}, type={self.strategy_type})>"

    @property
    def is_multi_leg(self) -> bool:
        """Check if this strategy contains multiple positions."""
        return self.is_synthetic or self.strategy_type != StrategyType.STANDALONE.value

    @property
    def leg_count(self) -> int:
        """Get the number of positions in this strategy."""
        return 1  # Default to 1 for standalone strategies

    def to_dict(self) -> dict:
        """Convert strategy to dictionary."""
        return {
            "id": str(self.id),
            "portfolio_id": str(self.portfolio_id),
            "strategy_type": self.strategy_type,
            "name": self.name,
            "description": self.description,
            "is_synthetic": self.is_synthetic,
            "net_exposure": float(self.net_exposure) if self.net_exposure else None,
            "total_cost_basis": float(self.total_cost_basis) if self.total_cost_basis else None,
            "leg_count": self.leg_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class StrategyLeg(Base):
    """Junction table linking strategies to their component positions."""

    __tablename__ = "strategy_legs"

    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), primary_key=True)
    position_id = Column(UUID(as_uuid=True), ForeignKey("positions.id", ondelete="CASCADE"), primary_key=True)
    leg_type = Column(String(50), default="single", nullable=False)  # single, long_leg, short_leg, protective, etc.
    leg_order = Column(Integer, default=0, nullable=False)  # Display ordering

    # Relationships
    strategy = relationship("Strategy", back_populates="strategy_legs")
    position = relationship("Position", back_populates="strategy_legs")

    def __repr__(self):
        return f"<StrategyLeg(strategy={self.strategy_id}, position={self.position_id}, type={self.leg_type})>"


class StrategyMetrics(Base):
    """Cached metrics for strategy performance and risk."""

    __tablename__ = "strategy_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    calculation_date = Column(DateTime(timezone=True), nullable=False)

    # Greeks (aggregated across all legs)
    net_delta = Column(Numeric(10, 4), nullable=True)
    net_gamma = Column(Numeric(10, 6), nullable=True)
    net_theta = Column(Numeric(20, 2), nullable=True)
    net_vega = Column(Numeric(20, 2), nullable=True)

    # P&L metrics
    total_pnl = Column(Numeric(20, 2), nullable=True)
    max_profit = Column(Numeric(20, 2), nullable=True)
    max_loss = Column(Numeric(20, 2), nullable=True)
    break_even_points = Column(JSONB, nullable=True)  # Array of price points

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('strategy_id', 'calculation_date', name='unique_strategy_date'),
    )

    # Relationships
    strategy = relationship("Strategy", back_populates="metrics")

    def __repr__(self):
        return f"<StrategyMetrics(strategy={self.strategy_id}, date={self.calculation_date})>"

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            "id": str(self.id),
            "strategy_id": str(self.strategy_id),
            "calculation_date": self.calculation_date.isoformat() if self.calculation_date else None,
            "net_delta": float(self.net_delta) if self.net_delta else None,
            "net_gamma": float(self.net_gamma) if self.net_gamma else None,
            "net_theta": float(self.net_theta) if self.net_theta else None,
            "net_vega": float(self.net_vega) if self.net_vega else None,
            "total_pnl": float(self.total_pnl) if self.total_pnl else None,
            "max_profit": float(self.max_profit) if self.max_profit else None,
            "max_loss": float(self.max_loss) if self.max_loss else None,
            "break_even_points": self.break_even_points,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StrategyTag(Base):
    """Junction table linking strategies to tags."""

    __tablename__ = "strategy_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags_v2.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('strategy_id', 'tag_id', name='unique_strategy_tag'),
    )

    # Relationships
    strategy = relationship("Strategy", back_populates="strategy_tags")
    tag = relationship("TagV2", back_populates="strategy_tags")
    assignor = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self):
        return f"<StrategyTag(strategy={self.strategy_id}, tag={self.tag_id})>"
