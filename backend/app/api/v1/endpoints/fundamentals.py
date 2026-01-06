"""
Fundamentals API Endpoints

Provides access to fundamental financial data (income statements, balance sheets,
cash flow statements, analyst estimates, and price targets).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from app.services.fundamentals_service import FundamentalsService
from app.schemas.fundamentals import (
    IncomeStatementResponse,
    BalanceSheetResponse,
    CashFlowResponse,
    AllStatementsResponse,
)
from app.core.clerk_auth import get_current_user_clerk
from app.models.users import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])


@router.get(
    "/income-statement/{symbol}",
    response_model=IncomeStatementResponse,
    summary="Get income statement",
    description="""
    Get historical income statement data for a symbol.

    **Frequency options:**
    - `q` - Quarterly (default, ~12 quarters available)
    - `a` - Annual (~4 years available)

    **Data includes:**
    - Revenue, COGS, Gross Profit
    - Operating expenses (R&D, SG&A)
    - EBIT, EBITDA
    - Net income, EPS
    - Calculated margins (gross, operating, net)

    **Source:** Yahoo Finance via YahooQuery
    """,
)
async def get_income_statement(
    symbol: str,
    frequency: str = Query("q", regex="^[qa]$", description="q=quarterly, a=annual"),
    periods: int = Query(12, ge=1, le=16, description="Number of periods to return"),
    current_user: User = Depends(get_current_user_clerk),
):
    """
    Get income statement data for a symbol

    Args:
        symbol: Stock symbol (e.g., AAPL, MSFT)
        frequency: 'q' (quarterly) or 'a' (annual)
        periods: Number of periods to return (1-16)
        current_user: Authenticated user

    Returns:
        IncomeStatementResponse with historical data

    Raises:
        404: Symbol not found or no data available
        500: Error fetching data from Yahoo Finance
    """
    try:
        symbol = symbol.upper()
        logger.info(f"Fetching income statement for {symbol} (frequency={frequency}, periods={periods})")

        service = FundamentalsService()
        result = await service.get_income_statement(symbol, frequency, periods)
        await service.close()

        # Check if we got any data
        if not result.periods:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No income statement data available for {symbol}"
            )

        logger.info(f"Successfully retrieved {len(result.periods)} periods for {symbol}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching income statement for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching income statement data: {str(e)}"
        )


@router.get(
    "/balance-sheet/{symbol}",
    response_model=BalanceSheetResponse,
    summary="Get balance sheet",
    description="""
    Get historical balance sheet data for a symbol.

    **Frequency options:**
    - `q` - Quarterly (default, ~12 quarters available)
    - `a` - Annual (~4 years available)

    **Data includes:**
    - **Assets:** Cash, receivables, inventory, PP&E, intangibles
    - **Liabilities:** Payables, short/long-term debt, deferred revenue
    - **Equity:** Common stock, retained earnings, treasury stock
    - **Calculated metrics:** Working capital, net debt, book value
    - **Ratios:** Current ratio, quick ratio, debt-to-equity, etc.

    **Source:** Yahoo Finance via YahooQuery (180+ fields available)
    """,
)
async def get_balance_sheet(
    symbol: str,
    frequency: str = Query("q", regex="^[qa]$", description="q=quarterly, a=annual"),
    periods: int = Query(12, ge=1, le=16, description="Number of periods to return"),
    current_user: User = Depends(get_current_user_clerk),
):
    """
    Get balance sheet data for a symbol

    Args:
        symbol: Stock symbol (e.g., AAPL, MSFT)
        frequency: 'q' (quarterly) or 'a' (annual)
        periods: Number of periods to return (1-16)
        current_user: Authenticated user

    Returns:
        BalanceSheetResponse with historical data and calculated ratios

    Raises:
        404: Symbol not found or no data available
        500: Error fetching data from Yahoo Finance
    """
    try:
        symbol = symbol.upper()
        logger.info(f"Fetching balance sheet for {symbol} (frequency={frequency}, periods={periods})")

        service = FundamentalsService()
        result = await service.get_balance_sheet(symbol, frequency, periods)
        await service.close()

        # Check if we got any data
        if not result.periods:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No balance sheet data available for {symbol}"
            )

        logger.info(f"Successfully retrieved {len(result.periods)} periods for {symbol}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching balance sheet for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching balance sheet data: {str(e)}"
        )


@router.get(
    "/cash-flow/{symbol}",
    response_model=CashFlowResponse,
    summary="Get cash flow statement",
    description="""
    Get historical cash flow statement data for a symbol.

    **Frequency options:**
    - `q` - Quarterly (default, ~12 quarters available)
    - `a` - Annual (~4 years available)

    **Data includes:**
    - **Operating activities:** Operating cash flow, depreciation, working capital changes
    - **Investing activities:** CapEx, acquisitions, investment purchases/sales
    - **Financing activities:** Dividends, stock repurchases, debt issuance/repayment
    - **Calculated metrics:** Free cash flow (OCF - CapEx)

    **Source:** Yahoo Finance via YahooQuery
    """,
)
async def get_cash_flow(
    symbol: str,
    frequency: str = Query("q", regex="^[qa]$", description="q=quarterly, a=annual"),
    periods: int = Query(12, ge=1, le=16, description="Number of periods to return"),
    current_user: User = Depends(get_current_user_clerk),
):
    """
    Get cash flow statement data for a symbol

    Args:
        symbol: Stock symbol (e.g., AAPL, MSFT)
        frequency: 'q' (quarterly) or 'a' (annual)
        periods: Number of periods to return (1-16)
        current_user: Authenticated user

    Returns:
        CashFlowResponse with historical cash flow data

    Raises:
        404: Symbol not found or no data available
        500: Error fetching data from Yahoo Finance
    """
    try:
        symbol = symbol.upper()
        logger.info(f"Fetching cash flow for {symbol} (frequency={frequency}, periods={periods})")

        service = FundamentalsService()
        result = await service.get_cash_flow(symbol, frequency, periods)
        await service.close()

        # Check if we got any data
        if not result.periods:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No cash flow data available for {symbol}"
            )

        logger.info(f"Successfully retrieved {len(result.periods)} periods for {symbol}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cash flow for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching cash flow data: {str(e)}"
        )


@router.get(
    "/all-statements/{symbol}",
    response_model=AllStatementsResponse,
    summary="Get all financial statements",
    description="""
    Get all three financial statements (income statement, balance sheet, cash flow) in one call.

    **Frequency options:**
    - `q` - Quarterly (default, ~12 quarters available)
    - `a` - Annual (~4 years available)

    **Returns:**
    - Complete income statement with margins and EPS
    - Complete balance sheet with calculated ratios
    - Complete cash flow with free cash flow calculation
    - All statements share the same time periods

    **Source:** Yahoo Finance via YahooQuery

    **Note:** This is more efficient than calling each endpoint separately.
    """,
)
async def get_all_statements(
    symbol: str,
    frequency: str = Query("q", regex="^[qa]$", description="q=quarterly, a=annual"),
    periods: int = Query(12, ge=1, le=16, description="Number of periods to return"),
    current_user: User = Depends(get_current_user_clerk),
):
    """
    Get all three financial statements in one call

    Args:
        symbol: Stock symbol (e.g., AAPL, MSFT)
        frequency: 'q' (quarterly) or 'a' (annual)
        periods: Number of periods to return (1-16)
        current_user: Authenticated user

    Returns:
        AllStatementsResponse with all three financial statements

    Raises:
        404: Symbol not found or no data available
        500: Error fetching data from Yahoo Finance
    """
    try:
        symbol = symbol.upper()
        logger.info(f"Fetching all statements for {symbol} (frequency={frequency}, periods={periods})")

        service = FundamentalsService()
        result = await service.get_all_statements(symbol, frequency, periods)
        await service.close()

        # Check if we got any data
        if (not result.income_statement.periods and
            not result.balance_sheet.periods and
            not result.cash_flow.periods):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No financial statement data available for {symbol}"
            )

        logger.info(f"Successfully retrieved all statements for {symbol}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching all statements for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching financial statements: {str(e)}"
        )


# TODO: Phase 2 endpoints (forward-looking data)
# @router.get("/analyst-estimates/{symbol}", response_model=AnalystEstimatesResponse)
# @router.get("/price-targets/{symbol}", response_model=PriceTargetsResponse)
# @router.get("/next-earnings/{symbol}", response_model=NextEarningsResponse)


# TODO: Phase 3 endpoints (calculated metrics)
# @router.get("/financial-ratios/{symbol}", response_model=FinancialRatiosResponse)
# @router.get("/growth-metrics/{symbol}", response_model=GrowthMetricsResponse)
