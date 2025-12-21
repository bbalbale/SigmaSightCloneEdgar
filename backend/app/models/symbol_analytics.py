"""
Symbol-level analytics models for factor exposures and metrics.

Part of the Symbol Factor Universe architecture:
- symbol_universe: Tracks all symbols in the system
- symbol_factor_exposures: Stores per-symbol factor betas (Ridge + Spread)
- symbol_daily_metrics: Denormalized dashboard data (returns, valuations, factors)

Created: 2025-12-20
"""
from datetime import datetime, date, timezone
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Date, UniqueConstraint, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database import Base


class SymbolUniverse(Base):
    """
    Symbol universe - tracks all symbols in the system.

    Used as the master list for:
    - Factor calculations (which symbols to process)
    - Dashboard queries (foreign key reference)
    - Symbol lifecycle tracking (first/last seen)
    """
    __tablename__ = "symbol_universe"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    asset_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'equity', 'etf', 'option_underlying'
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_seen_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_seen_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    factor_exposures: Mapped[list["SymbolFactorExposure"]] = relationship(
        "SymbolFactorExposure",
        back_populates="symbol_ref",
        cascade="all, delete-orphan"
    )
    daily_metrics: Mapped[Optional["SymbolDailyMetrics"]] = relationship(
        "SymbolDailyMetrics",
        back_populates="symbol_ref",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_symbol_universe_active', 'is_active'),
        Index('idx_symbol_universe_sector', 'sector'),
        Index('idx_symbol_universe_asset_type', 'asset_type'),
    )


class SymbolFactorExposure(Base):
    """
    Symbol factor exposures - stores per-symbol factor betas.

    Supports both calculation methods:
    - Ridge regression: 6 factors (Value, Growth, Momentum, Quality, Size, Low Vol)
    - Spread regression: 4 factors (Growth-Value, Momentum, Size, Quality spreads)

    Key insight: Factor beta is intrinsic to the symbol, not the position.
    AAPL's momentum beta is the same regardless of which portfolio holds it.
    """
    __tablename__ = "symbol_factor_exposures"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("symbol_universe.symbol", ondelete="CASCADE"),
        nullable=False
    )
    factor_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("factor_definitions.id"),
        nullable=False
    )
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Regression results
    beta_value: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    r_squared: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    observations: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_flag: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'full_history', 'limited_history'

    # Calculation metadata
    calculation_method: Mapped[str] = mapped_column(String(50), nullable=False)  # 'ridge_regression', 'spread_regression'
    regularization_alpha: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)  # Only for ridge
    regression_window_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 365 for ridge, 180 for spread

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    symbol_ref: Mapped["SymbolUniverse"] = relationship("SymbolUniverse", back_populates="factor_exposures")
    factor: Mapped["FactorDefinition"] = relationship("FactorDefinition")

    __table_args__ = (
        # Unique constraint for upsert pattern
        UniqueConstraint('symbol', 'factor_id', 'calculation_date', name='uq_symbol_factor_date'),
        # Primary lookup pattern (symbol + date)
        Index('idx_symbol_factor_lookup', 'symbol', 'calculation_date'),
        # Batch processing (find uncached symbols for a date)
        Index('idx_symbol_factor_calc_date', 'calculation_date'),
        # Factor type filtering
        Index('idx_symbol_factor_method', 'calculation_method', 'calculation_date'),
    )


class SymbolDailyMetrics(Base):
    """
    Symbol daily metrics - denormalized dashboard data.

    Consolidates data from multiple sources for fast dashboard queries:
    - Price & returns: from market_data_cache
    - Valuations: from company_profiles
    - Factor exposures: from symbol_factor_exposures

    Single-table design enables:
    - Sort by any column (market cap, P/E, momentum factor, etc.)
    - Filter by sector
    - <50ms API response for full universe

    Updated daily in batch Phase 1.5 (after market data, before P&L).
    """
    __tablename__ = "symbol_daily_metrics"

    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("symbol_universe.symbol", ondelete="CASCADE"),
        primary_key=True
    )
    metrics_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Price & Returns (calculated from market_data)
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    return_1d: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)  # Daily return
    return_mtd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)  # Month-to-date
    return_ytd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)  # Year-to-date
    return_1m: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)  # Rolling 1 month
    return_3m: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)  # Rolling 3 months
    return_1y: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)  # Rolling 1 year

    # Valuation (from company_profiles/fundamentals)
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    enterprise_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    ps_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    pb_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)

    # Company Info (from company_profiles)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Ridge Factors (denormalized from symbol_factor_exposures)
    factor_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    factor_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    factor_momentum: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    factor_quality: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    factor_size: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    factor_low_vol: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)

    # Spread Factors (denormalized from symbol_factor_exposures)
    factor_growth_value_spread: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    factor_momentum_spread: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    factor_size_spread: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    factor_quality_spread: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)

    # Data quality metadata
    data_quality_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    symbol_ref: Mapped["SymbolUniverse"] = relationship("SymbolUniverse", back_populates="daily_metrics")

    __table_args__ = (
        # Dashboard sorts by key columns
        Index('idx_metrics_date', 'metrics_date'),
        Index('idx_metrics_sector', 'sector'),
        Index('idx_metrics_market_cap', 'market_cap'),
        Index('idx_metrics_return_ytd', 'return_ytd'),
        Index('idx_metrics_pe', 'pe_ratio'),
        # Factor exposure sorts
        Index('idx_metrics_factor_momentum', 'factor_momentum'),
        Index('idx_metrics_factor_value', 'factor_value'),
        # Composite for common query pattern
        Index('idx_metrics_sector_cap', 'sector', 'market_cap'),
    )
