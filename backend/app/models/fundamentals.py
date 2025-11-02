"""
Fundamental financial data models for income statements, balance sheets, and cash flows.

These models store historical fundamental data (quarterly and annual) for securities.
UPSERT strategy with UNIQUE constraints prevents duplicate periods.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IncomeStatement(Base):
    """
    Income statement data for a security (quarterly or annual).

    Stores revenue, expenses, and profitability metrics.
    Unique constraint on (symbol, period_date, frequency) prevents duplicates.
    """

    __tablename__ = "income_statements"

    # Primary key
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer)
    frequency: Mapped[str] = mapped_column(String(1), nullable=False)

    # Revenue & Costs (4 fields)
    total_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    cost_of_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    gross_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    gross_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))  # calculated

    # Operating Expenses (2 fields)
    research_and_development: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    selling_general_and_administrative: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Operating Results (4 fields)
    operating_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    operating_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))  # calculated
    ebit: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    ebitda: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Net Income (6 fields)
    net_income: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    net_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))  # calculated
    diluted_eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    basic_eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    basic_average_shares: Mapped[Optional[int]] = mapped_column(Integer)
    diluted_average_shares: Mapped[Optional[int]] = mapped_column(Integer)

    # Tax & Interest (3 fields)
    tax_provision: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    interest_expense: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    depreciation_and_amortization: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Metadata
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint('symbol', 'period_date', 'frequency', name='uq_income_symbol_period_freq'),
    )


class BalanceSheet(Base):
    """
    Balance sheet data for a security (quarterly or annual).

    Stores assets, liabilities, and equity.
    Unique constraint on (symbol, period_date, frequency) prevents duplicates.
    """

    __tablename__ = "balance_sheets"

    # Primary key
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer)
    frequency: Mapped[str] = mapped_column(String(1), nullable=False)

    # Assets (8 fields)
    total_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    current_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    cash_and_cash_equivalents: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    short_term_investments: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    accounts_receivable: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    inventory: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    property_plant_equipment: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    intangible_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Liabilities (6 fields)
    total_liabilities: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    current_liabilities: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    accounts_payable: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    short_term_debt: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    long_term_debt: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    total_debt: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Equity (3 fields)
    total_stockholders_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    retained_earnings: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    common_stock: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Calculated metrics (5 fields)
    working_capital: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))  # Current Assets - Current Liabilities
    net_debt: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))  # Total Debt - Cash
    current_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # Current Assets / Current Liabilities
    debt_to_equity: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))  # Total Debt / Total Equity
    book_value_per_share: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Metadata
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint('symbol', 'period_date', 'frequency', name='uq_balance_symbol_period_freq'),
    )


class CashFlow(Base):
    """
    Cash flow statement data for a security (quarterly or annual).

    Stores operating, investing, and financing cash flows.
    Unique constraint on (symbol, period_date, frequency) prevents duplicates.
    """

    __tablename__ = "cash_flows"

    # Primary key
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    period_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer)
    frequency: Mapped[str] = mapped_column(String(1), nullable=False)

    # Operating Activities (4 fields)
    operating_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    depreciation_and_amortization: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    stock_based_compensation: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    change_in_working_capital: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Investing Activities (4 fields)
    investing_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    capital_expenditures: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    acquisitions: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    purchases_of_investments: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Financing Activities (4 fields)
    financing_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    dividends_paid: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    stock_repurchases: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    debt_issuance_repayment: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Summary (2 fields)
    net_change_in_cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    beginning_cash_position: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Calculated metrics (2 fields)
    free_cash_flow: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))  # Operating Cash Flow - CapEx
    fcf_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 6))  # Free Cash Flow / Revenue

    # Metadata
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint('symbol', 'period_date', 'frequency', name='uq_cashflow_symbol_period_freq'),
    )
