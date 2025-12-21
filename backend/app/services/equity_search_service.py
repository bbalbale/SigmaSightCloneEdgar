"""
Equity Search Service

Provides search, filtering, and sorting capabilities for equities.
Uses symbol_daily_metrics as the primary data source for fast queries,
with joins to fundamental tables for period-specific data.
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.symbol_analytics import SymbolDailyMetrics
from app.models.market_data import CompanyProfile
from app.models.fundamentals import IncomeStatement, BalanceSheet, CashFlow
from app.schemas.equity_search import (
    PeriodType,
    SortOrder,
    EquitySearchItem,
    EquitySearchResponse,
    EquitySearchFiltersResponse,
    VALID_SORT_COLUMNS,
)

logger = logging.getLogger(__name__)


class EquitySearchService:
    """Service for searching and filtering equities."""

    async def search(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        sectors: Optional[List[str]] = None,
        industries: Optional[List[str]] = None,
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
        min_pe_ratio: Optional[float] = None,
        max_pe_ratio: Optional[float] = None,
        period: PeriodType = PeriodType.TTM,
        sort_by: str = "market_cap",
        sort_order: SortOrder = SortOrder.DESC,
        limit: int = 50,
        offset: int = 0,
    ) -> EquitySearchResponse:
        """
        Search equities with filters and sorting.

        Args:
            db: Database session
            query: Text search on symbol + company_name
            sectors: Filter by sectors
            industries: Filter by industries
            min_market_cap: Minimum market cap
            max_market_cap: Maximum market cap
            min_pe_ratio: Minimum P/E ratio
            max_pe_ratio: Maximum P/E ratio
            period: Period for fundamental data (TTM, last_year, forward, last_quarter)
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            EquitySearchResponse with items and metadata
        """
        # Validate sort column
        if sort_by not in VALID_SORT_COLUMNS:
            sort_by = "market_cap"

        # Build base query from symbol_daily_metrics
        stmt = select(SymbolDailyMetrics)

        # Apply text search filter
        if query:
            search_pattern = f"%{query.upper()}%"
            stmt = stmt.where(
                or_(
                    SymbolDailyMetrics.symbol.ilike(search_pattern),
                    SymbolDailyMetrics.company_name.ilike(search_pattern),
                )
            )

        # Apply sector filter
        if sectors:
            stmt = stmt.where(SymbolDailyMetrics.sector.in_(sectors))

        # Apply industry filter
        if industries:
            stmt = stmt.where(SymbolDailyMetrics.industry.in_(industries))

        # Apply market cap filters
        if min_market_cap is not None:
            stmt = stmt.where(SymbolDailyMetrics.market_cap >= min_market_cap)
        if max_market_cap is not None:
            stmt = stmt.where(SymbolDailyMetrics.market_cap <= max_market_cap)

        # Apply P/E ratio filters
        if min_pe_ratio is not None:
            stmt = stmt.where(SymbolDailyMetrics.pe_ratio >= min_pe_ratio)
        if max_pe_ratio is not None:
            stmt = stmt.where(SymbolDailyMetrics.pe_ratio <= max_pe_ratio)

        # Get total count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar() or 0

        # Apply sorting for columns that exist in symbol_daily_metrics
        sort_column = self._get_sort_column(sort_by)
        if sort_column is not None:
            if sort_order == SortOrder.DESC:
                stmt = stmt.order_by(desc(sort_column).nulls_last())
            else:
                stmt = stmt.order_by(asc(sort_column).nulls_last())

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

        # Execute query
        result = await db.execute(stmt)
        metrics_rows = result.scalars().all()

        if not metrics_rows:
            return EquitySearchResponse(
                items=[],
                total_count=0,
                filters_applied=self._build_filters_applied(
                    query, sectors, industries, min_market_cap, max_market_cap, min_pe_ratio, max_pe_ratio
                ),
                period=period.value,
                sort_by=sort_by,
                sort_order=sort_order.value,
            )

        # Get symbols for fundamental data lookup
        symbols = [row.symbol for row in metrics_rows]

        # Fetch period-specific fundamentals
        fundamentals_map = await self._fetch_fundamentals(db, symbols, period)

        # Fetch balance sheet data for EV calculation (if not in metrics)
        balance_sheet_map = await self._fetch_balance_sheet_data(db, symbols)

        # Build response items
        items = []
        for row in metrics_rows:
            symbol = row.symbol
            fundamentals = fundamentals_map.get(symbol, {})
            balance_data = balance_sheet_map.get(symbol, {})

            # Calculate Enterprise Value if not already in metrics
            ev = row.enterprise_value
            if ev is None and row.market_cap is not None:
                total_debt = balance_data.get("total_debt") or 0
                cash = balance_data.get("cash") or 0
                ev = float(row.market_cap) + float(total_debt) - float(cash)

            item = EquitySearchItem(
                symbol=symbol,
                company_name=row.company_name,
                sector=row.sector,
                industry=row.industry,
                market_cap=float(row.market_cap) if row.market_cap else None,
                enterprise_value=float(ev) if ev else None,
                ps_ratio=float(row.ps_ratio) if row.ps_ratio else None,
                pe_ratio=float(row.pe_ratio) if row.pe_ratio else None,
                revenue=fundamentals.get("revenue"),
                ebit=fundamentals.get("ebit"),
                fcf=fundamentals.get("fcf"),
                period_label=fundamentals.get("period_label", self._get_period_label(period)),
                factor_value=float(row.factor_value) if row.factor_value else None,
                factor_growth=float(row.factor_growth) if row.factor_growth else None,
                factor_momentum=float(row.factor_momentum) if row.factor_momentum else None,
                factor_quality=float(row.factor_quality) if row.factor_quality else None,
                factor_size=float(row.factor_size) if row.factor_size else None,
                factor_low_vol=float(row.factor_low_vol) if row.factor_low_vol else None,
            )
            items.append(item)

        # If sorting by a fundamental column, sort in memory
        if sort_by in ["revenue", "ebit", "fcf", "enterprise_value"]:
            items = self._sort_items(items, sort_by, sort_order)

        # Get metrics date
        metrics_date = metrics_rows[0].metrics_date if metrics_rows else None

        return EquitySearchResponse(
            items=items,
            total_count=total_count,
            filters_applied=self._build_filters_applied(
                query, sectors, industries, min_market_cap, max_market_cap, min_pe_ratio, max_pe_ratio
            ),
            period=period.value,
            sort_by=sort_by,
            sort_order=sort_order.value,
            metrics_date=metrics_date,
        )

    async def get_filter_options(self, db: AsyncSession) -> EquitySearchFiltersResponse:
        """
        Get available filter options.

        Returns:
            EquitySearchFiltersResponse with sectors, industries, and market cap ranges
        """
        # Get unique sectors
        sectors_stmt = (
            select(SymbolDailyMetrics.sector)
            .where(SymbolDailyMetrics.sector.isnot(None))
            .distinct()
            .order_by(SymbolDailyMetrics.sector)
        )
        sectors_result = await db.execute(sectors_stmt)
        sectors = [row[0] for row in sectors_result.all()]

        # Get unique industries
        industries_stmt = (
            select(SymbolDailyMetrics.industry)
            .where(SymbolDailyMetrics.industry.isnot(None))
            .distinct()
            .order_by(SymbolDailyMetrics.industry)
        )
        industries_result = await db.execute(industries_stmt)
        industries = [row[0] for row in industries_result.all()]

        return EquitySearchFiltersResponse(
            sectors=sectors,
            industries=industries,
        )

    def _get_sort_column(self, sort_by: str):
        """Get the SQLAlchemy column for sorting."""
        column_map = {
            "symbol": SymbolDailyMetrics.symbol,
            "company_name": SymbolDailyMetrics.company_name,
            "sector": SymbolDailyMetrics.sector,
            "market_cap": SymbolDailyMetrics.market_cap,
            "enterprise_value": SymbolDailyMetrics.enterprise_value,
            "ps_ratio": SymbolDailyMetrics.ps_ratio,
            "pe_ratio": SymbolDailyMetrics.pe_ratio,
            "factor_value": SymbolDailyMetrics.factor_value,
            "factor_growth": SymbolDailyMetrics.factor_growth,
            "factor_momentum": SymbolDailyMetrics.factor_momentum,
            "factor_quality": SymbolDailyMetrics.factor_quality,
            "factor_size": SymbolDailyMetrics.factor_size,
            "factor_low_vol": SymbolDailyMetrics.factor_low_vol,
        }
        return column_map.get(sort_by)

    async def _fetch_fundamentals(
        self,
        db: AsyncSession,
        symbols: List[str],
        period: PeriodType,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch period-specific fundamental data for symbols.

        Returns dict mapping symbol -> {revenue, ebit, fcf, period_label}
        """
        if not symbols:
            return {}

        result = {}

        if period == PeriodType.TTM:
            # Sum of last 4 quarters
            result = await self._fetch_ttm_fundamentals(db, symbols)
        elif period == PeriodType.LAST_YEAR:
            # Most recent annual data
            result = await self._fetch_annual_fundamentals(db, symbols)
        elif period == PeriodType.LAST_QUARTER:
            # Most recent quarterly data
            result = await self._fetch_quarterly_fundamentals(db, symbols)
        elif period == PeriodType.FORWARD:
            # Forward estimates from company_profiles
            result = await self._fetch_forward_estimates(db, symbols)

        return result

    async def _fetch_ttm_fundamentals(
        self, db: AsyncSession, symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch TTM (trailing twelve months) fundamental data."""
        result = {}

        # Get last 4 quarters of income statements
        income_stmt = (
            select(
                IncomeStatement.symbol,
                func.sum(IncomeStatement.total_revenue).label("revenue"),
                func.sum(IncomeStatement.ebit).label("ebit"),
            )
            .where(
                and_(
                    IncomeStatement.symbol.in_(symbols),
                    IncomeStatement.frequency == "Q",
                )
            )
            .group_by(IncomeStatement.symbol)
        )

        # Subquery to get only the last 4 quarters per symbol
        # For simplicity, we'll use a window function approach
        subq = (
            select(
                IncomeStatement.symbol,
                IncomeStatement.total_revenue,
                IncomeStatement.ebit,
                func.row_number()
                .over(
                    partition_by=IncomeStatement.symbol,
                    order_by=IncomeStatement.period_date.desc(),
                )
                .label("rn"),
            )
            .where(
                and_(
                    IncomeStatement.symbol.in_(symbols),
                    IncomeStatement.frequency == "Q",
                )
            )
            .subquery()
        )

        ttm_income_stmt = (
            select(
                subq.c.symbol,
                func.sum(subq.c.total_revenue).label("revenue"),
                func.sum(subq.c.ebit).label("ebit"),
            )
            .where(subq.c.rn <= 4)
            .group_by(subq.c.symbol)
        )

        income_result = await db.execute(ttm_income_stmt)
        for row in income_result.all():
            result[row.symbol] = {
                "revenue": float(row.revenue) if row.revenue else None,
                "ebit": float(row.ebit) if row.ebit else None,
                "fcf": None,
                "period_label": "TTM",
            }

        # Get last 4 quarters of cash flows for FCF
        subq_cf = (
            select(
                CashFlow.symbol,
                CashFlow.free_cash_flow,
                func.row_number()
                .over(
                    partition_by=CashFlow.symbol,
                    order_by=CashFlow.period_date.desc(),
                )
                .label("rn"),
            )
            .where(
                and_(
                    CashFlow.symbol.in_(symbols),
                    CashFlow.frequency == "Q",
                )
            )
            .subquery()
        )

        ttm_cf_stmt = (
            select(
                subq_cf.c.symbol,
                func.sum(subq_cf.c.free_cash_flow).label("fcf"),
            )
            .where(subq_cf.c.rn <= 4)
            .group_by(subq_cf.c.symbol)
        )

        cf_result = await db.execute(ttm_cf_stmt)
        for row in cf_result.all():
            if row.symbol in result:
                result[row.symbol]["fcf"] = float(row.fcf) if row.fcf else None
            else:
                result[row.symbol] = {
                    "revenue": None,
                    "ebit": None,
                    "fcf": float(row.fcf) if row.fcf else None,
                    "period_label": "TTM",
                }

        return result

    async def _fetch_annual_fundamentals(
        self, db: AsyncSession, symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch most recent annual fundamental data."""
        result = {}

        # Subquery to get most recent annual period per symbol
        subq = (
            select(
                IncomeStatement.symbol,
                IncomeStatement.total_revenue,
                IncomeStatement.ebit,
                IncomeStatement.fiscal_year,
                func.row_number()
                .over(
                    partition_by=IncomeStatement.symbol,
                    order_by=IncomeStatement.period_date.desc(),
                )
                .label("rn"),
            )
            .where(
                and_(
                    IncomeStatement.symbol.in_(symbols),
                    IncomeStatement.frequency == "A",
                )
            )
            .subquery()
        )

        annual_stmt = select(subq).where(subq.c.rn == 1)
        income_result = await db.execute(annual_stmt)

        for row in income_result.all():
            fiscal_year = row.fiscal_year or datetime.now().year - 1
            result[row.symbol] = {
                "revenue": float(row.total_revenue) if row.total_revenue else None,
                "ebit": float(row.ebit) if row.ebit else None,
                "fcf": None,
                "period_label": f"FY{fiscal_year}",
            }

        # Get FCF from cash flows
        subq_cf = (
            select(
                CashFlow.symbol,
                CashFlow.free_cash_flow,
                func.row_number()
                .over(
                    partition_by=CashFlow.symbol,
                    order_by=CashFlow.period_date.desc(),
                )
                .label("rn"),
            )
            .where(
                and_(
                    CashFlow.symbol.in_(symbols),
                    CashFlow.frequency == "A",
                )
            )
            .subquery()
        )

        annual_cf_stmt = select(subq_cf).where(subq_cf.c.rn == 1)
        cf_result = await db.execute(annual_cf_stmt)

        for row in cf_result.all():
            if row.symbol in result:
                result[row.symbol]["fcf"] = float(row.free_cash_flow) if row.free_cash_flow else None

        return result

    async def _fetch_quarterly_fundamentals(
        self, db: AsyncSession, symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch most recent quarterly fundamental data."""
        result = {}

        # Subquery to get most recent quarterly period per symbol
        subq = (
            select(
                IncomeStatement.symbol,
                IncomeStatement.total_revenue,
                IncomeStatement.ebit,
                IncomeStatement.fiscal_year,
                IncomeStatement.fiscal_quarter,
                func.row_number()
                .over(
                    partition_by=IncomeStatement.symbol,
                    order_by=IncomeStatement.period_date.desc(),
                )
                .label("rn"),
            )
            .where(
                and_(
                    IncomeStatement.symbol.in_(symbols),
                    IncomeStatement.frequency == "Q",
                )
            )
            .subquery()
        )

        quarterly_stmt = select(subq).where(subq.c.rn == 1)
        income_result = await db.execute(quarterly_stmt)

        for row in income_result.all():
            year = row.fiscal_year or datetime.now().year
            quarter = row.fiscal_quarter or 1
            result[row.symbol] = {
                "revenue": float(row.total_revenue) if row.total_revenue else None,
                "ebit": float(row.ebit) if row.ebit else None,
                "fcf": None,
                "period_label": f"Q{quarter} {year}",
            }

        # Get FCF from cash flows
        subq_cf = (
            select(
                CashFlow.symbol,
                CashFlow.free_cash_flow,
                func.row_number()
                .over(
                    partition_by=CashFlow.symbol,
                    order_by=CashFlow.period_date.desc(),
                )
                .label("rn"),
            )
            .where(
                and_(
                    CashFlow.symbol.in_(symbols),
                    CashFlow.frequency == "Q",
                )
            )
            .subquery()
        )

        quarterly_cf_stmt = select(subq_cf).where(subq_cf.c.rn == 1)
        cf_result = await db.execute(quarterly_cf_stmt)

        for row in cf_result.all():
            if row.symbol in result:
                result[row.symbol]["fcf"] = float(row.free_cash_flow) if row.free_cash_flow else None

        return result

    async def _fetch_forward_estimates(
        self, db: AsyncSession, symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch forward estimates from company_profiles."""
        result = {}

        stmt = select(
            CompanyProfile.symbol,
            CompanyProfile.current_year_revenue_avg,
        ).where(CompanyProfile.symbol.in_(symbols))

        profile_result = await db.execute(stmt)
        current_year = datetime.now().year

        for row in profile_result.all():
            result[row.symbol] = {
                "revenue": float(row.current_year_revenue_avg) if row.current_year_revenue_avg else None,
                "ebit": None,  # Forward EBIT estimates not typically available
                "fcf": None,  # Forward FCF estimates not typically available
                "period_label": f"FY{current_year}E",
            }

        return result

    async def _fetch_balance_sheet_data(
        self, db: AsyncSession, symbols: List[str]
    ) -> Dict[str, Dict[str, float]]:
        """Fetch latest balance sheet data for EV calculation."""
        result = {}

        # Get most recent balance sheet per symbol
        subq = (
            select(
                BalanceSheet.symbol,
                BalanceSheet.total_debt,
                BalanceSheet.cash_and_cash_equivalents,
                func.row_number()
                .over(
                    partition_by=BalanceSheet.symbol,
                    order_by=BalanceSheet.period_date.desc(),
                )
                .label("rn"),
            )
            .where(BalanceSheet.symbol.in_(symbols))
            .subquery()
        )

        stmt = select(subq).where(subq.c.rn == 1)
        bs_result = await db.execute(stmt)

        for row in bs_result.all():
            result[row.symbol] = {
                "total_debt": float(row.total_debt) if row.total_debt else 0,
                "cash": float(row.cash_and_cash_equivalents) if row.cash_and_cash_equivalents else 0,
            }

        return result

    def _get_period_label(self, period: PeriodType) -> str:
        """Get default period label."""
        labels = {
            PeriodType.TTM: "TTM",
            PeriodType.LAST_YEAR: f"FY{datetime.now().year - 1}",
            PeriodType.LAST_QUARTER: f"Q{(datetime.now().month - 1) // 3} {datetime.now().year}",
            PeriodType.FORWARD: f"FY{datetime.now().year}E",
        }
        return labels.get(period, "TTM")

    def _sort_items(
        self, items: List[EquitySearchItem], sort_by: str, sort_order: SortOrder
    ) -> List[EquitySearchItem]:
        """Sort items in memory for columns not in the database."""
        reverse = sort_order == SortOrder.DESC

        def get_sort_value(item: EquitySearchItem):
            value = getattr(item, sort_by, None)
            if value is None:
                return float("-inf") if reverse else float("inf")
            return value

        return sorted(items, key=get_sort_value, reverse=reverse)

    def _build_filters_applied(
        self,
        query: Optional[str],
        sectors: Optional[List[str]],
        industries: Optional[List[str]],
        min_market_cap: Optional[float],
        max_market_cap: Optional[float],
        min_pe_ratio: Optional[float],
        max_pe_ratio: Optional[float],
    ) -> Dict[str, Any]:
        """Build filters_applied metadata."""
        filters = {}
        if query:
            filters["query"] = query
        if sectors:
            filters["sectors"] = sectors
        if industries:
            filters["industries"] = industries
        if min_market_cap is not None:
            filters["min_market_cap"] = min_market_cap
        if max_market_cap is not None:
            filters["max_market_cap"] = max_market_cap
        if min_pe_ratio is not None:
            filters["min_pe_ratio"] = min_pe_ratio
        if max_pe_ratio is not None:
            filters["max_pe_ratio"] = max_pe_ratio
        return filters


# Singleton instance
equity_search_service = EquitySearchService()
