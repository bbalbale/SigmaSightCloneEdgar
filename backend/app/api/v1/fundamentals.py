"""
API endpoints for Fundamental Financial Data
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.fundamentals import IncomeStatement, BalanceSheet, CashFlow
from app.models.market_data import CompanyProfile
from app.schemas.fundamentals import (
    SimpleIncomeStatementResponse,
    SimpleIncomeStatementPeriod,
    SimpleBalanceSheetResponse,
    SimpleBalanceSheetPeriod,
    SimpleCashFlowResponse,
    SimpleCashFlowPeriod,
    SimpleAnalystEstimatesResponse,
    SimpleAnalystEstimates,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/fundamentals", tags=["Fundamentals"])


@router.get(
    "/{symbol}/income-statement",
    response_model=SimpleIncomeStatementResponse,
    summary="Get income statements for a symbol",
    description="""Returns historical income statement data for a symbol.

    Features:
    - Quarterly and annual data available
    - Up to 20 historical periods
    - Includes revenue, expenses, margins, and EPS
    - Data filtered for completeness (100% data quality)
    """,
    responses={
        200: {"description": "Income statements retrieved successfully"},
        404: {"description": "No income statement data found for symbol"},
    }
)
async def get_income_statement(
    symbol: str,
    periods: int = Query(4, ge=1, le=20, description="Number of periods to return"),
    frequency: str = Query("q", regex="^(q|a)$", description="Frequency: 'q' for quarterly, 'a' for annual"),
    db: AsyncSession = Depends(get_db)
):
    """Get income statement data for a symbol"""

    # Query database
    stmt = select(IncomeStatement).where(
        IncomeStatement.symbol == symbol.upper(),
        IncomeStatement.frequency == frequency
    ).order_by(IncomeStatement.period_date.desc()).limit(periods)

    result = await db.execute(stmt)
    statements = result.scalars().all()

    if not statements:
        raise HTTPException(
            status_code=404,
            detail=f"No income statement data found for {symbol.upper()}"
        )

    # Convert to response schema
    periods_data = [SimpleIncomeStatementPeriod.from_orm(stmt) for stmt in statements]

    return SimpleIncomeStatementResponse(
        symbol=symbol.upper(),
        frequency=frequency,
        currency="USD",
        periods=periods_data,
        periods_returned=len(periods_data)
    )


@router.get(
    "/{symbol}/balance-sheet",
    response_model=SimpleBalanceSheetResponse,
    summary="Get balance sheets for a symbol",
    description="""Returns historical balance sheet data for a symbol.

    Features:
    - Quarterly and annual data available
    - Up to 20 historical periods
    - Includes assets, liabilities, equity, and financial ratios
    - Calculated metrics: current ratio, debt-to-equity, working capital
    """,
    responses={
        200: {"description": "Balance sheets retrieved successfully"},
        404: {"description": "No balance sheet data found for symbol"},
    }
)
async def get_balance_sheet(
    symbol: str,
    periods: int = Query(4, ge=1, le=20, description="Number of periods to return"),
    frequency: str = Query("q", regex="^(q|a)$", description="Frequency: 'q' for quarterly, 'a' for annual"),
    db: AsyncSession = Depends(get_db)
):
    """Get balance sheet data for a symbol"""

    # Query database
    stmt = select(BalanceSheet).where(
        BalanceSheet.symbol == symbol.upper(),
        BalanceSheet.frequency == frequency
    ).order_by(BalanceSheet.period_date.desc()).limit(periods)

    result = await db.execute(stmt)
    sheets = result.scalars().all()

    if not sheets:
        raise HTTPException(
            status_code=404,
            detail=f"No balance sheet data found for {symbol.upper()}"
        )

    # Convert to response schema
    periods_data = [SimpleBalanceSheetPeriod.from_orm(sheet) for sheet in sheets]

    return SimpleBalanceSheetResponse(
        symbol=symbol.upper(),
        frequency=frequency,
        currency="USD",
        periods=periods_data,
        periods_returned=len(periods_data)
    )


@router.get(
    "/{symbol}/cash-flow",
    response_model=SimpleCashFlowResponse,
    summary="Get cash flow statements for a symbol",
    description="""Returns historical cash flow data for a symbol.

    Features:
    - Quarterly and annual data available
    - Up to 20 historical periods
    - Operating, investing, and financing activities
    - Calculated metrics: free cash flow, FCF margin
    """,
    responses={
        200: {"description": "Cash flows retrieved successfully"},
        404: {"description": "No cash flow data found for symbol"},
    }
)
async def get_cash_flow(
    symbol: str,
    periods: int = Query(4, ge=1, le=20, description="Number of periods to return"),
    frequency: str = Query("q", regex="^(q|a)$", description="Frequency: 'q' for quarterly, 'a' for annual"),
    db: AsyncSession = Depends(get_db)
):
    """Get cash flow statement data for a symbol"""

    # Query database
    stmt = select(CashFlow).where(
        CashFlow.symbol == symbol.upper(),
        CashFlow.frequency == frequency
    ).order_by(CashFlow.period_date.desc()).limit(periods)

    result = await db.execute(stmt)
    flows = result.scalars().all()

    if not flows:
        raise HTTPException(
            status_code=404,
            detail=f"No cash flow data found for {symbol.upper()}"
        )

    # Convert to response schema
    periods_data = [SimpleCashFlowPeriod.from_orm(flow) for flow in flows]

    return SimpleCashFlowResponse(
        symbol=symbol.upper(),
        frequency=frequency,
        currency="USD",
        periods=periods_data,
        periods_returned=len(periods_data)
    )


@router.get(
    "/{symbol}/analyst-estimates",
    response_model=SimpleAnalystEstimatesResponse,
    summary="Get analyst estimates for a symbol",
    description="""Returns analyst consensus estimates for forward periods.

    Features:
    - Current quarter and next quarter estimates
    - Current fiscal year and next fiscal year estimates
    - Revenue and EPS estimates with ranges (low, average, high)
    - Number of analysts covering
    - Revenue growth estimates

    Data sourced from YahooQuery earnings_trend endpoint.
    """,
    responses={
        200: {"description": "Analyst estimates retrieved successfully"},
        404: {"description": "No analyst estimate data found for symbol"},
    }
)
async def get_analyst_estimates(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Get analyst estimate data for a symbol"""

    # Query company_profiles table
    stmt = select(CompanyProfile).where(CompanyProfile.symbol == symbol.upper())

    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No analyst estimate data found for {symbol.upper()}"
        )

    # Build analyst estimates response
    estimates = SimpleAnalystEstimates(
        # Current Quarter
        current_quarter_end_date=profile.current_quarter_target_period_date,
        current_quarter_revenue_avg=profile.current_quarter_revenue_avg,
        current_quarter_revenue_low=profile.current_quarter_revenue_low,
        current_quarter_revenue_high=profile.current_quarter_revenue_high,
        current_quarter_eps_avg=profile.current_quarter_eps_avg,
        current_quarter_eps_low=profile.current_quarter_eps_low,
        current_quarter_eps_high=profile.current_quarter_eps_high,
        current_quarter_analyst_count=profile.current_quarter_analyst_count,

        # Next Quarter
        next_quarter_end_date=profile.next_quarter_target_period_date,
        next_quarter_revenue_avg=profile.next_quarter_revenue_avg,
        next_quarter_revenue_low=profile.next_quarter_revenue_low,
        next_quarter_revenue_high=profile.next_quarter_revenue_high,
        next_quarter_eps_avg=profile.next_quarter_eps_avg,
        next_quarter_eps_low=profile.next_quarter_eps_low,
        next_quarter_eps_high=profile.next_quarter_eps_high,
        next_quarter_analyst_count=profile.next_quarter_analyst_count,

        # Current Year
        current_year_end_date=profile.current_year_end_date,
        current_year_revenue_avg=profile.current_year_revenue_avg,
        current_year_revenue_low=profile.current_year_revenue_low,
        current_year_revenue_high=profile.current_year_revenue_high,
        current_year_revenue_growth=profile.current_year_revenue_growth,
        current_year_earnings_avg=profile.current_year_earnings_avg,
        current_year_earnings_low=profile.current_year_earnings_low,
        current_year_earnings_high=profile.current_year_earnings_high,

        # Next Year
        next_year_end_date=profile.next_year_end_date,
        next_year_revenue_avg=profile.next_year_revenue_avg,
        next_year_revenue_low=profile.next_year_revenue_low,
        next_year_revenue_high=profile.next_year_revenue_high,
        next_year_revenue_growth=profile.next_year_revenue_growth,
        next_year_earnings_avg=profile.next_year_earnings_avg,
        next_year_earnings_low=profile.next_year_earnings_low,
        next_year_earnings_high=profile.next_year_earnings_high,
    )

    return SimpleAnalystEstimatesResponse(
        symbol=symbol.upper(),
        estimates=estimates
    )
