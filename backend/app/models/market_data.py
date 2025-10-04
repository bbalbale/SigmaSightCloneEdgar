"""
Market data and analytics models
"""
from datetime import datetime, date
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Index, Numeric, Date, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Dict, List
from app.database import Base


class MarketDataCache(Base):
    """Market data cache - stores historical price data"""
    __tablename__ = "market_data_cache"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Sector/Industry data from FMP Company Profile API
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Additional company metadata from FMP
    exchange: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    
    data_source: Mapped[str] = mapped_column(String(50), nullable=False, default='polygon')  # Updated for Section 1.4.9: supports 'polygon', 'fmp', 'tradefeeds', 'yfinance'
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uq_market_data_cache_symbol_date'),
        Index('ix_market_data_cache_symbol', 'symbol'),
        Index('ix_market_data_cache_date', 'date'),
    )


class CompanyProfile(Base):
    """Company profile information - comprehensive company metadata from yahooquery"""
    __tablename__ = "company_profiles"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)

    # Basic company info
    company_name: Mapped[Optional[str]] = mapped_column(String(200))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    exchange: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[Optional[str]] = mapped_column(String(10))
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    description: Mapped[Optional[str]] = mapped_column(String(1000))

    # Company type flags
    is_etf: Mapped[Optional[bool]] = mapped_column(default=False)
    is_fund: Mapped[Optional[bool]] = mapped_column(default=False)

    # Company details
    ceo: Mapped[Optional[str]] = mapped_column(String(100))
    employees: Mapped[Optional[int]]
    website: Mapped[Optional[str]] = mapped_column(String(200))

    # Valuation metrics (updated periodically)
    pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    forward_pe: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    dividend_yield: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    beta: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    week_52_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    week_52_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Analyst estimates and targets
    target_mean_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    target_high_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    target_low_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    number_of_analyst_opinions: Mapped[Optional[int]]
    recommendation_mean: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))  # 1-5 scale
    recommendation_key: Mapped[Optional[str]] = mapped_column(String(20))  # "buy", "hold", "sell"

    # Forward estimates
    forward_eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    earnings_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))  # As decimal
    revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))  # As decimal
    earnings_quarterly_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))

    # Profitability metrics
    profit_margins: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    operating_margins: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    gross_margins: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    return_on_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    return_on_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    total_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))  # TTM

    # Current year estimates (0y period) - from yahooquery earnings_trend
    current_year_revenue_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    current_year_revenue_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    current_year_revenue_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    current_year_revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    current_year_earnings_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    current_year_earnings_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    current_year_earnings_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    current_year_end_date: Mapped[Optional[date]] = mapped_column(Date)

    # Next year estimates (+1y period) - from yahooquery earnings_trend
    next_year_revenue_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    next_year_revenue_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    next_year_revenue_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    next_year_revenue_growth: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))
    next_year_earnings_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    next_year_earnings_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    next_year_earnings_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    next_year_end_date: Mapped[Optional[date]] = mapped_column(Date)

    # Data tracking
    data_source: Mapped[str] = mapped_column(String(50), default='yahooquery')
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_company_profiles_symbol', 'symbol'),
    )


class PositionGreeks(Base):
    """Position Greeks - stores calculated Greeks for options positions"""
    __tablename__ = "position_greeks"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False, unique=True)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Greeks values - increased precision to handle large option deltas (migration 99219061f7b0)
    delta: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6), nullable=True)  # Allows up to 999,999.999999
    gamma: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6), nullable=True)  # Allows up to 999,999.999999
    theta: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    vega: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    rho: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    
    # Position-adjusted values
    delta_dollars: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    gamma_dollars: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    position: Mapped["Position"] = relationship("Position", back_populates="greeks")
    
    __table_args__ = (
        Index('ix_position_greeks_position_id', 'position_id'),
        Index('ix_position_greeks_calculation_date', 'calculation_date'),
    )


class FactorDefinition(Base):
    """Factor definitions - defines available risk factors"""
    __tablename__ = "factor_definitions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    factor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'style', 'sector', 'macro'
    calculation_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    etf_proxy: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # ETF ticker for factor proxy
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Display order in UI
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    exposures: Mapped[list["FactorExposure"]] = relationship("FactorExposure", back_populates="factor")
    position_exposures: Mapped[list["PositionFactorExposure"]] = relationship("PositionFactorExposure", back_populates="factor")
    correlations_as_factor_1: Mapped[List["FactorCorrelation"]] = relationship("FactorCorrelation", foreign_keys="FactorCorrelation.factor_1_id", back_populates="factor_1")
    correlations_as_factor_2: Mapped[List["FactorCorrelation"]] = relationship("FactorCorrelation", foreign_keys="FactorCorrelation.factor_2_id", back_populates="factor_2")


class FactorExposure(Base):
    """Factor exposures - stores portfolio factor exposures"""
    __tablename__ = "factor_exposures"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    factor_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("factor_definitions.id"), nullable=False)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    exposure_value: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    exposure_dollar: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="factor_exposures")
    factor: Mapped["FactorDefinition"] = relationship("FactorDefinition", back_populates="exposures")
    
    __table_args__ = (
        UniqueConstraint('portfolio_id', 'factor_id', 'calculation_date', 
                        name='uq_factor_exposures_portfolio_factor_date'),
        Index('ix_factor_exposures_portfolio_id_factor_id', 'portfolio_id', 'factor_id'),
        Index('ix_factor_exposures_calculation_date', 'calculation_date'),
    )


class PositionFactorExposure(Base):
    """Position factor exposures - stores position-level factor exposures"""
    __tablename__ = "position_factor_exposures"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False)
    factor_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("factor_definitions.id"), nullable=False)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    exposure_value: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    quality_flag: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'full_history', 'limited_history'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    position: Mapped["Position"] = relationship("Position", back_populates="factor_exposures")
    factor: Mapped["FactorDefinition"] = relationship("FactorDefinition", back_populates="position_exposures")
    
    __table_args__ = (
        UniqueConstraint('position_id', 'factor_id', 'calculation_date', 
                        name='uq_position_factor_date'),
        Index('idx_pfe_factor_date', 'factor_id', 'calculation_date'),
        Index('idx_pfe_position_date', 'position_id', 'calculation_date'),
        Index('idx_pfe_calculation_date', 'calculation_date'),
    )


class MarketRiskScenario(Base):
    """Market risk scenarios - stores portfolio scenario results"""
    __tablename__ = "market_risk_scenarios"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'market_up_5', 'market_down_10', etc.
    scenario_value: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)  # The scenario change (e.g., 0.05 for +5%)
    predicted_pnl: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)  # Predicted P&L for this scenario
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="market_risk_scenarios")
    
    __table_args__ = (
        Index('idx_market_risk_portfolio_date', 'portfolio_id', 'calculation_date'),
        Index('idx_market_risk_scenario_type', 'scenario_type'),
    )


class PositionInterestRateBeta(Base):
    """Position interest rate betas - stores position-level interest rate sensitivities"""
    __tablename__ = "position_interest_rate_betas"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    position_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id"), nullable=False)
    ir_beta: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)  # Interest rate beta
    r_squared: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)  # Regression R²
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    position: Mapped["Position"] = relationship("Position", back_populates="interest_rate_betas")
    
    __table_args__ = (
        Index('idx_ir_betas_position_date', 'position_id', 'calculation_date'),
    )


class StressTestScenario(Base):
    """Stress test scenarios - stores scenario definitions and configurations"""
    __tablename__ = "stress_test_scenarios"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    scenario_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # market, rates, rotation, volatility, historical
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # mild, moderate, severe, extreme
    shock_config: Mapped[Dict] = mapped_column(JSONB, nullable=False)  # JSON config for shocked factors
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stress_test_results: Mapped[List["StressTestResult"]] = relationship("StressTestResult", back_populates="scenario")
    
    __table_args__ = (
        Index('idx_stress_scenarios_category', 'category'),
        Index('idx_stress_scenarios_severity', 'severity'),
        Index('idx_stress_scenarios_active', 'active'),
    )


class StressTestResult(Base):
    """Stress test results - stores historical stress test results for tracking"""
    __tablename__ = "stress_test_results"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    scenario_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stress_test_scenarios.id"), nullable=False)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    direct_pnl: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)  # Direct impact P&L
    correlated_pnl: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)  # Correlated impact P&L
    correlation_effect: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)  # Difference between correlated and direct
    factor_impacts: Mapped[Dict] = mapped_column(JSONB, nullable=True)  # Detailed factor-level impacts
    calculation_metadata: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)  # Calculation details
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="stress_test_results")
    scenario: Mapped["StressTestScenario"] = relationship("StressTestScenario", back_populates="stress_test_results")
    
    __table_args__ = (
        Index('idx_stress_results_portfolio_date', 'portfolio_id', 'calculation_date'),
        Index('idx_stress_results_scenario', 'scenario_id'),
        Index('idx_stress_results_calculation_date', 'calculation_date'),
    )


class FactorCorrelation(Base):
    """Factor correlations - stores factor correlation matrix results"""
    __tablename__ = "factor_correlations"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    factor_1_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("factor_definitions.id"), nullable=False)
    factor_2_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("factor_definitions.id"), nullable=False)
    correlation: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)  # Correlation coefficient (-1 to 1)
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    lookback_days: Mapped[int] = mapped_column(nullable=False)  # Historical period used
    decay_factor: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)  # Exponential decay factor
    data_points: Mapped[int] = mapped_column(nullable=False)  # Number of data points used
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    factor_1: Mapped["FactorDefinition"] = relationship("FactorDefinition", foreign_keys=[factor_1_id], back_populates="correlations_as_factor_1")
    factor_2: Mapped["FactorDefinition"] = relationship("FactorDefinition", foreign_keys=[factor_2_id], back_populates="correlations_as_factor_2")
    
    __table_args__ = (
        UniqueConstraint('factor_1_id', 'factor_2_id', 'calculation_date', 
                        name='uq_factor_correlations_factors_date'),
        Index('idx_factor_correlations_date', 'calculation_date'),
        Index('idx_factor_correlations_factors', 'factor_1_id', 'factor_2_id'),
    )


class FundHoldings(Base):
    """Fund holdings - stores mutual fund and ETF holdings data (Section 1.4.9)"""
    __tablename__ = "fund_holdings"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    fund_symbol: Mapped[str] = mapped_column(String(20), nullable=False)  # Fund symbol (e.g., 'FXNAX', 'VTI')
    holding_symbol: Mapped[str] = mapped_column(String(20), nullable=False)  # Holding symbol (e.g., 'AAPL')
    holding_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Company/security name
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 6), nullable=False)  # Weight as decimal (0.0525 for 5.25%)
    shares: Mapped[Optional[int]] = mapped_column(nullable=True)  # Number of shares held
    market_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)  # Market value of holding
    
    # Data quality and tracking
    data_source: Mapped[str] = mapped_column(String(50), nullable=False)  # 'fmp', 'tradefeeds', etc.
    last_updated: Mapped[date] = mapped_column(Date, nullable=False)  # Date when holdings data was fetched
    data_quality: Mapped[str] = mapped_column(String(20), nullable=False, default='good')  # 'good', 'partial', 'incomplete'
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('fund_symbol', 'holding_symbol', 'last_updated', 
                        name='uq_fund_holdings_fund_holding_date'),
        Index('ix_fund_holdings_fund_symbol', 'fund_symbol'),
        Index('ix_fund_holdings_holding_symbol', 'holding_symbol'),
        Index('ix_fund_holdings_last_updated', 'last_updated'),
        Index('ix_fund_holdings_data_source', 'data_source'),
        Index('ix_fund_holdings_fund_date', 'fund_symbol', 'last_updated'),  # Composite index for queries
    )
