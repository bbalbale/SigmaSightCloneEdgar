"""
Price Cache Service

Provides price cache bootstrap functionality extracted from seed_initial_prices.py.
This service is transaction-agnostic - it does NOT commit/rollback transactions.

Key responsibilities:
- Bootstrap historical prices for symbols
- Handle YFinance network failures gracefully
- Support both full historical loads and quick bootstraps

Can be used from:
- CLI seeding scripts (which manage their own transactions)
- Request handlers (which manage request-scoped transactions)
- Onboarding flows (30-day quick bootstrap)
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.positions import Position
from app.db.fetch_historical_data import (
    fetch_and_store_historical_data,
    filter_stock_symbols
)

logger = get_logger(__name__)


class PriceCacheService:
    """Service for bootstrapping price cache data"""

    @staticmethod
    async def bootstrap_prices(
        db: AsyncSession,
        symbols: List[str],
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Bootstrap historical prices for symbols.

        IMPORTANT: Does NOT commit - caller manages transaction.

        Args:
            db: Database session
            symbols: List of symbols to bootstrap
            days: Number of days of historical data (default: 30)

        Returns:
            Dictionary with bootstrap metrics:
            {
                "total_symbols": int,
                "successful_symbols": int,
                "failed_symbols": int,
                "total_records": int,
                "records_per_symbol": Dict[str, int],
                "network_failure": bool,
                "error_message": Optional[str]
            }
        """
        metrics = {
            "total_symbols": len(symbols),
            "successful_symbols": 0,
            "failed_symbols": 0,
            "total_records": 0,
            "records_per_symbol": {},
            "network_failure": False,
            "error_message": None
        }

        try:
            # Filter to stocks/ETFs only (exclude options)
            stock_symbols = await filter_stock_symbols(symbols)

            if not stock_symbols:
                logger.warning("No stock symbols to bootstrap")
                return metrics

            logger.info(f"Bootstrapping {days} days of prices for {len(stock_symbols)} symbols")

            # Fetch and store historical data
            records_per_symbol = await fetch_and_store_historical_data(
                db=db,
                symbols=stock_symbols,
                days=days,
                batch_size=10  # Process 10 at a time
            )

            # Calculate metrics
            metrics["records_per_symbol"] = records_per_symbol
            metrics["successful_symbols"] = sum(1 for count in records_per_symbol.values() if count > 0)
            metrics["failed_symbols"] = len(stock_symbols) - metrics["successful_symbols"]
            metrics["total_records"] = sum(records_per_symbol.values())

            logger.info(
                f"Price bootstrap complete: "
                f"{metrics['successful_symbols']}/{len(stock_symbols)} symbols, "
                f"{metrics['total_records']} records"
            )

        except ConnectionError as e:
            # Network failure - graceful degradation
            logger.warning(f"Network failure during price bootstrap: {str(e)}")
            metrics["network_failure"] = True
            metrics["error_message"] = "Network unavailable - prices will be fetched later"

        except Exception as e:
            # Other errors
            logger.error(f"Price bootstrap error: {str(e)}", exc_info=True)
            metrics["error_message"] = str(e)

        return metrics

    @staticmethod
    async def get_price_coverage(
        db: AsyncSession,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Check price cache coverage for symbols.

        Args:
            db: Database session
            symbols: List of symbols to check

        Returns:
            Dictionary with coverage metrics:
            {
                "total_symbols": int,
                "symbols_with_prices": int,
                "symbols_without_prices": int,
                "coverage_percentage": float,
                "missing_symbols": List[str]
            }
        """
        from app.models.market_data import MarketDataCache

        metrics = {
            "total_symbols": len(symbols),
            "symbols_with_prices": 0,
            "symbols_without_prices": 0,
            "coverage_percentage": 0.0,
            "missing_symbols": []
        }

        for symbol in symbols:
            result = await db.execute(
                select(MarketDataCache).where(
                    MarketDataCache.symbol == symbol
                ).limit(1)
            )
            has_price = result.scalar_one_or_none() is not None

            if has_price:
                metrics["symbols_with_prices"] += 1
            else:
                metrics["symbols_without_prices"] += 1
                metrics["missing_symbols"].append(symbol)

        if metrics["total_symbols"] > 0:
            metrics["coverage_percentage"] = (
                metrics["symbols_with_prices"] / metrics["total_symbols"]
            ) * 100

        return metrics


# Convenience instance
price_cache_service = PriceCacheService()
