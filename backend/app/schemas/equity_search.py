"""
Equity Search schemas for request/response validation.

Supports search, filtering, sorting, and period-aware fundamental data.
"""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PeriodType(str, Enum):
    """Period type for fundamental data."""
    TTM = "ttm"  # Trailing twelve months
    LAST_YEAR = "last_year"  # Most recent fiscal year
    FORWARD = "forward"  # Forward estimates
    LAST_QUARTER = "last_quarter"  # Most recent quarter


class SortOrder(str, Enum):
    """Sort order."""
    ASC = "asc"
    DESC = "desc"


# Valid sort columns
VALID_SORT_COLUMNS = {
    "symbol",
    "company_name",
    "sector",
    "market_cap",
    "enterprise_value",
    "ps_ratio",
    "pe_ratio",
    "revenue",
    "ebit",
    "fcf",
    "factor_value",
    "factor_growth",
    "factor_momentum",
    "factor_quality",
    "factor_size",
    "factor_low_vol",
}


class EquitySearchItem(BaseModel):
    """Individual equity search result."""

    # Identity
    symbol: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    # Valuation metrics
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    ps_ratio: Optional[float] = None
    pe_ratio: Optional[float] = None

    # Fundamentals (period-dependent)
    revenue: Optional[float] = None
    ebit: Optional[float] = None
    fcf: Optional[float] = None
    period_label: str = "TTM"  # "TTM", "FY2024", "FY2025E", "Q3 2024"

    # Factor betas
    factor_value: Optional[float] = None
    factor_growth: Optional[float] = None
    factor_momentum: Optional[float] = None
    factor_quality: Optional[float] = None
    factor_size: Optional[float] = None
    factor_low_vol: Optional[float] = None

    class Config:
        from_attributes = True


class MarketCapRange(BaseModel):
    """Market cap range option for filters."""
    label: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class EquitySearchFiltersResponse(BaseModel):
    """Available filter options for the equity search UI."""
    sectors: List[str] = []
    industries: List[str] = []
    market_cap_ranges: List[MarketCapRange] = [
        MarketCapRange(label="Mega Cap (>$200B)", min_value=200_000_000_000),
        MarketCapRange(label="Large Cap ($10B-$200B)", min_value=10_000_000_000, max_value=200_000_000_000),
        MarketCapRange(label="Mid Cap ($2B-$10B)", min_value=2_000_000_000, max_value=10_000_000_000),
        MarketCapRange(label="Small Cap ($300M-$2B)", min_value=300_000_000, max_value=2_000_000_000),
        MarketCapRange(label="Micro Cap (<$300M)", max_value=300_000_000),
    ]


class EquitySearchResponse(BaseModel):
    """Response for equity search endpoint."""
    items: List[EquitySearchItem] = []
    total_count: int = 0

    # Query metadata
    filters_applied: Dict[str, Any] = {}
    period: str = "ttm"
    sort_by: str = "market_cap"
    sort_order: str = "desc"

    # Data freshness
    metrics_date: Optional[date] = None

    class Config:
        from_attributes = True
