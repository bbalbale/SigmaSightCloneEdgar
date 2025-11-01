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
)
from app.core.dependencies import get_current_user, CurrentUser

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
    current_user: CurrentUser = Depends(get_current_user),
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
    current_user: CurrentUser = Depends(get_current_user),
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


# TODO: Add cash flow endpoint
# @router.get("/cash-flow/{symbol}", response_model=CashFlowResponse)
# async def get_cash_flow(...):
#     """Get cash flow statement data"""
#     pass


# TODO: Add all-statements endpoint
# @router.get("/all-statements/{symbol}", response_model=AllStatementsResponse)
# async def get_all_statements(...):
#     """Get all three financial statements in one call"""
#     pass


# TODO: Phase 2 endpoints (forward-looking data)
# @router.get("/analyst-estimates/{symbol}", response_model=AnalystEstimatesResponse)
# @router.get("/price-targets/{symbol}", response_model=PriceTargetsResponse)
# @router.get("/next-earnings/{symbol}", response_model=NextEarningsResponse)


# TODO: Phase 3 endpoints (calculated metrics)
# @router.get("/financial-ratios/{symbol}", response_model=FinancialRatiosResponse)
# @router.get("/growth-metrics/{symbol}", response_model=GrowthMetricsResponse)
