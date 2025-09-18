"""
User and Portfolio models
"""
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index, Numeric
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
    
    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="user", uselist=False)
    tags: Mapped[List["Tag"]] = relationship("Tag", back_populates="user")
    modeling_sessions: Mapped[List["ModelingSessionSnapshot"]] = relationship("ModelingSessionSnapshot", back_populates="user")


class Portfolio(Base):
    """Portfolio model - each user has exactly one portfolio"""
    __tablename__ = "portfolios"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default='USD')
    equity_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)  # User-provided NAV
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="portfolio")
    positions: Mapped[List["Position"]] = relationship("Position", back_populates="portfolio")
    snapshots: Mapped[List["PortfolioSnapshot"]] = relationship("PortfolioSnapshot", back_populates="portfolio")
    factor_exposures: Mapped[List["FactorExposure"]] = relationship("FactorExposure", back_populates="portfolio")
    market_risk_scenarios: Mapped[List["MarketRiskScenario"]] = relationship("MarketRiskScenario", back_populates="portfolio")
    stress_test_results: Mapped[List["StressTestResult"]] = relationship("StressTestResult", back_populates="portfolio")
    correlation_calculations: Mapped[List["CorrelationCalculation"]] = relationship("CorrelationCalculation", back_populates="portfolio")
    target_prices: Mapped[List["TargetPrice"]] = relationship("TargetPrice", back_populates="portfolio")

    __table_args__ = (
        UniqueConstraint('user_id', name='uq_portfolios_user_id'),
        Index('ix_portfolios_deleted_at', 'deleted_at'),
    )
