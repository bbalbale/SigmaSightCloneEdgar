"""
V2 Data-Driven Batch Checks

Instead of relying on batch_run_history to determine what needs processing,
these functions check the actual data to see what's missing.

Benefits:
- Self-healing: If a batch fails halfway, next run catches what's missing
- Timezone-proof: No UTC vs ET confusion - just "do we have data for this date?"
- More resilient: Doesn't depend on batch history records being accurate

Usage:
    from app.batch.v2.data_checks import (
        get_symbols_missing_prices,
        get_portfolios_missing_snapshots,
        get_target_date_if_market_closed,
    )
"""

import sys
from datetime import date, datetime, timedelta
from typing import List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.trading_calendar import (
    is_trading_day,
    get_most_recent_trading_day,
    US_EASTERN,
    MARKET_CLOSE_HOUR,
)
from app.database import get_async_session
from app.models.market_data import MarketDataCache
from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position
from app.models.users import Portfolio

logger = get_logger(__name__)

V2_LOG_PREFIX = "[V2_DATA_CHECK]"

# Market close time with buffer (4:30 PM ET to ensure data is available)
MARKET_CLOSE_BUFFER_MINUTES = 30


def get_target_date_if_market_closed() -> Optional[date]:
    """
    Get today's date if market has closed, otherwise None.

    Returns the date to process if:
    1. Today is a trading day AND
    2. It's after 4:30 PM ET (market closed + 30 min buffer)

    Returns:
        date if market has closed and we should process, None otherwise
    """
    now_et = datetime.now(US_EASTERN)
    today = now_et.date()

    # Check if today is a trading day
    if not is_trading_day(today):
        # Not a trading day, check if we should process the most recent trading day
        most_recent = get_most_recent_trading_day(today)
        # Only return it if we haven't already processed it (caller should check data)
        return most_recent

    # Today is a trading day - check if market has closed
    market_close_with_buffer = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_BUFFER_MINUTES
    current_minutes = now_et.hour * 60 + now_et.minute

    if current_minutes >= market_close_with_buffer:
        # Market has closed, process today
        return today
    else:
        # Market still open or just closed, don't process yet
        # Return the previous trading day instead
        return get_most_recent_trading_day(today - timedelta(days=1))


async def get_all_portfolio_symbols() -> Set[str]:
    """
    Get all unique symbols from all active portfolios.

    Only includes PUBLIC positions (stocks/ETFs), not OPTIONS or PRIVATE.

    Returns:
        Set of symbol strings
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(Position.symbol)
            .distinct()
            .join(Portfolio, Position.portfolio_id == Portfolio.id)
            .where(
                and_(
                    Portfolio.deleted_at.is_(None),
                    Position.investment_class == "PUBLIC",
                    Position.symbol.isnot(None),
                )
            )
        )
        symbols = {row[0] for row in result.fetchall() if row[0]}
        return symbols


async def get_symbols_missing_prices(target_date: date) -> Tuple[List[str], List[str]]:
    """
    Check which symbols are missing price data for the target date.

    Args:
        target_date: Date to check for missing prices

    Returns:
        Tuple of (symbols_missing_prices, all_symbols)
    """
    print(f"{V2_LOG_PREFIX} Checking symbols missing prices for {target_date}...")
    sys.stdout.flush()

    # Get all symbols we need
    all_symbols = await get_all_portfolio_symbols()

    if not all_symbols:
        print(f"{V2_LOG_PREFIX} No symbols found in portfolios")
        sys.stdout.flush()
        return [], []

    async with get_async_session() as db:
        # Get symbols that HAVE prices for target_date
        result = await db.execute(
            select(MarketDataCache.symbol)
            .distinct()
            .where(
                and_(
                    MarketDataCache.date == target_date,
                    MarketDataCache.close.isnot(None),
                    MarketDataCache.symbol.in_(all_symbols),
                )
            )
        )
        symbols_with_prices = {row[0] for row in result.fetchall()}

    # Calculate missing
    symbols_missing = list(all_symbols - symbols_with_prices)

    print(f"{V2_LOG_PREFIX} Symbols: {len(all_symbols)} total, {len(symbols_with_prices)} have prices, {len(symbols_missing)} missing")
    sys.stdout.flush()

    return symbols_missing, list(all_symbols)


async def get_portfolios_missing_snapshots(target_date: date) -> Tuple[List[UUID], List[UUID]]:
    """
    Check which portfolios are missing snapshots for the target date.

    Args:
        target_date: Date to check for missing snapshots

    Returns:
        Tuple of (portfolios_missing_snapshots, all_portfolio_ids)
    """
    print(f"{V2_LOG_PREFIX} Checking portfolios missing snapshots for {target_date}...")
    sys.stdout.flush()

    async with get_async_session() as db:
        # Get all active portfolio IDs
        result = await db.execute(
            select(Portfolio.id)
            .where(Portfolio.deleted_at.is_(None))
        )
        all_portfolio_ids = [row[0] for row in result.fetchall()]

        if not all_portfolio_ids:
            print(f"{V2_LOG_PREFIX} No active portfolios found")
            sys.stdout.flush()
            return [], []

        # Get portfolios that HAVE snapshots for target_date
        result = await db.execute(
            select(PortfolioSnapshot.portfolio_id)
            .distinct()
            .where(
                and_(
                    PortfolioSnapshot.snapshot_date == target_date,
                    PortfolioSnapshot.portfolio_id.in_(all_portfolio_ids),
                )
            )
        )
        portfolios_with_snapshots = {row[0] for row in result.fetchall()}

    # Calculate missing
    all_portfolio_set = set(all_portfolio_ids)
    portfolios_missing = list(all_portfolio_set - portfolios_with_snapshots)

    print(f"{V2_LOG_PREFIX} Portfolios: {len(all_portfolio_ids)} total, {len(portfolios_with_snapshots)} have snapshots, {len(portfolios_missing)} missing")
    sys.stdout.flush()

    return portfolios_missing, all_portfolio_ids


async def check_batch_status(target_date: date) -> dict:
    """
    Check overall batch status for a target date.

    Returns a summary of what data exists and what's missing.

    Args:
        target_date: Date to check

    Returns:
        Dict with status information
    """
    symbols_missing, all_symbols = await get_symbols_missing_prices(target_date)
    portfolios_missing, all_portfolios = await get_portfolios_missing_snapshots(target_date)

    return {
        "target_date": target_date.isoformat(),
        "symbols": {
            "total": len(all_symbols),
            "have_prices": len(all_symbols) - len(symbols_missing),
            "missing_prices": len(symbols_missing),
            "missing_list": symbols_missing[:20],  # First 20 for debugging
        },
        "portfolios": {
            "total": len(all_portfolios),
            "have_snapshots": len(all_portfolios) - len(portfolios_missing),
            "missing_snapshots": len(portfolios_missing),
            "missing_list": [str(p) for p in portfolios_missing],
        },
        "needs_symbol_batch": len(symbols_missing) > 0,
        "needs_portfolio_refresh": len(portfolios_missing) > 0,
    }
