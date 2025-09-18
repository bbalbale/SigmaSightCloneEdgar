"""
Target Price model for portfolio-specific price targets
"""
from datetime import datetime
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database import Base


class TargetPrice(Base):
    """
    Portfolio-specific target prices for positions.
    Allows different portfolios to have different targets for the same symbol.
    """
    __tablename__ = "portfolio_target_prices"

    # Primary key
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    portfolio_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False
    )
    position_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=True  # Optional link to specific position
    )

    # Symbol and position type
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    position_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # LONG, SHORT, LC, LP, SC, SP

    # Target Prices
    target_price_eoy: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    target_price_next_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    downside_target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)

    # Current Market Data (for calculation context)
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    current_implied_vol: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)  # For options

    # Calculated Returns (auto-calculated by service)
    expected_return_eoy: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    expected_return_next_year: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    downside_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)

    # Risk Metrics
    position_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    contribution_to_portfolio_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    contribution_to_portfolio_risk: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)

    # Metadata
    price_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    analyst_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # USER_INPUT, ANALYST_CONSENSUS, MODEL
    created_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="target_prices")
    position: Mapped[Optional["Position"]] = relationship("Position", back_populates="target_price")

    # Table constraints and indexes
    __table_args__ = (
        # Allow same symbol with different position types
        UniqueConstraint('portfolio_id', 'symbol', 'position_type', name='uq_portfolio_symbol_type'),

        # Performance indexes
        Index('ix_target_prices_portfolio_id', 'portfolio_id'),
        Index('ix_target_prices_symbol', 'symbol'),
        Index('ix_target_prices_position_id', 'position_id'),
        Index('ix_target_prices_updated_at', 'updated_at'),
    )

    def calculate_expected_returns(self) -> None:
        """
        Calculate expected returns based on current price and target prices.
        This is a simple percentage calculation for now.
        """
        if self.current_price and self.current_price != 0:
            # EOY return calculation
            if self.target_price_eoy:
                if self.position_type in ['SHORT', 'SC', 'SP']:
                    # For short positions, profit when price goes down
                    self.expected_return_eoy = (
                        (self.current_price - self.target_price_eoy) / self.current_price
                    ) * 100
                else:
                    # For long positions, profit when price goes up
                    self.expected_return_eoy = (
                        (self.target_price_eoy - self.current_price) / self.current_price
                    ) * 100

            # Next year return calculation
            if self.target_price_next_year:
                if self.position_type in ['SHORT', 'SC', 'SP']:
                    self.expected_return_next_year = (
                        (self.current_price - self.target_price_next_year) / self.current_price
                    ) * 100
                else:
                    self.expected_return_next_year = (
                        (self.target_price_next_year - self.current_price) / self.current_price
                    ) * 100

            # Downside return calculation
            if self.downside_target_price:
                if self.position_type in ['SHORT', 'SC', 'SP']:
                    # For shorts, downside is when price goes up
                    self.downside_return = (
                        (self.current_price - self.downside_target_price) / self.current_price
                    ) * 100
                else:
                    # For longs, downside is when price goes down
                    self.downside_return = (
                        (self.downside_target_price - self.current_price) / self.current_price
                    ) * 100

    def __repr__(self):
        return (
            f"<TargetPrice(portfolio={self.portfolio_id}, symbol={self.symbol}, "
            f"eoy={self.target_price_eoy}, next_year={self.target_price_next_year})>"
        )