"""
User and Portfolio models
"""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index, Numeric, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from app.database import Base


class User(Base):
    """User model - stores user account information"""
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Clerk Authentication & Billing (Phase 2)
    clerk_user_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    tier: Mapped[str] = mapped_column(String(20), default='free', server_default='free')
    invite_validated: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    ai_messages_used: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    ai_messages_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default='now()')
    
    # Relationships
    portfolios: Mapped[List["Portfolio"]] = relationship("Portfolio", back_populates="user", uselist=True, cascade="all, delete-orphan")
    # Enhanced tag model (v2) - replaced the old tags relationship
    tags_v2: Mapped[List["TagV2"]] = relationship("TagV2", back_populates="user", foreign_keys="TagV2.user_id", cascade="all, delete-orphan")
    modeling_sessions: Mapped[List["ModelingSessionSnapshot"]] = relationship("ModelingSessionSnapshot", back_populates="user", cascade="all, delete-orphan")
    equity_changes: Mapped[List["EquityChange"]] = relationship("EquityChange", back_populates="created_by_user", cascade="all, delete-orphan")


class Portfolio(Base):
    """Portfolio model - users can have multiple portfolios (accounts)"""
    __tablename__ = "portfolios"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False, default='taxable')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default='USD')
    equity_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)  # User-provided NAV
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    positions: Mapped[List["Position"]] = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    snapshots: Mapped[List["PortfolioSnapshot"]] = relationship("PortfolioSnapshot", back_populates="portfolio", cascade="all, delete-orphan")
    factor_exposures: Mapped[List["FactorExposure"]] = relationship("FactorExposure", back_populates="portfolio", cascade="all, delete-orphan")
    position_market_betas: Mapped[List["PositionMarketBeta"]] = relationship("PositionMarketBeta", back_populates="portfolio", cascade="all, delete-orphan")
    position_interest_rate_betas: Mapped[List["PositionInterestRateBeta"]] = relationship("PositionInterestRateBeta", back_populates="portfolio", cascade="all, delete-orphan")
    market_risk_scenarios: Mapped[List["MarketRiskScenario"]] = relationship("MarketRiskScenario", back_populates="portfolio", cascade="all, delete-orphan")
    stress_test_results: Mapped[List["StressTestResult"]] = relationship("StressTestResult", back_populates="portfolio", cascade="all, delete-orphan")
    correlation_calculations: Mapped[List["CorrelationCalculation"]] = relationship("CorrelationCalculation", back_populates="portfolio", cascade="all, delete-orphan")
    target_prices: Mapped[List["TargetPrice"]] = relationship("TargetPrice", back_populates="portfolio", cascade="all, delete-orphan")
    ai_insights: Mapped[List["AIInsight"]] = relationship("AIInsight", back_populates="portfolio", cascade="all, delete-orphan")
    position_realized_events: Mapped[List["PositionRealizedEvent"]] = relationship("PositionRealizedEvent", back_populates="portfolio", cascade="all, delete-orphan")
    equity_changes: Mapped[List["EquityChange"]] = relationship("EquityChange", back_populates="portfolio", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_portfolios_deleted_at', 'deleted_at'),
        Index('ix_portfolios_user_id', 'user_id'),  # Non-unique index for performance
        UniqueConstraint('user_id', 'account_name', name='uq_portfolio_user_account_name'),  # Prevent duplicate account names per user
    )
