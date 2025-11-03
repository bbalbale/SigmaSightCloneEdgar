"""
Phase 1.5: Fundamental Data Collection
Smart fetching based on earnings dates to minimize API calls

Fetch Logic:
- Only fetch if 3+ days after earnings date
- Skip if data recently fetched
- Batch by symbol (all statements + analyst data in one API call)

Provider: YahooQuery for all fundamental data
"""
import asyncio
from datetime import date
from typing import Dict, List, Set, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.services.fundamentals_service import fundamentals_service

logger = get_logger(__name__)


class FundamentalsCollector:
    """
    Phase 1.5 of batch processing - collect fundamental data for portfolio symbols

    Features:
    - Smart fetching (only after earnings + 3 days)
    - Earnings-driven updates (reduces API calls by 80-90%)
    - Stores income statements, balance sheets, cash flows
    - Updates company profiles with analyst estimates
    - Handles fiscal calendar complexity
    """

    async def collect_fundamentals_data(
        self,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - collect fundamental data for all portfolio symbols

        Args:
            db: Optional database session

        Returns:
            Summary of fundamentals collection
        """
        if db is None:
            async with AsyncSessionLocal() as session:
                return await self._collect_with_session(session)
        else:
            return await self._collect_with_session(db)

    async def _collect_with_session(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Collect fundamentals with provided session"""

        result = {
            'success': True,
            'symbols_evaluated': 0,
            'symbols_fetched': 0,
            'symbols_skipped': 0,
            'errors': []
        }

        try:
            # Step 1: Get all unique symbols from positions (PUBLIC only)
            symbols = await self._get_portfolio_symbols(db)
            result['symbols_evaluated'] = len(symbols)

            if not symbols:
                logger.info("No PUBLIC symbols found, skipping fundamentals collection")
                return result

            logger.info(f"Evaluating fundamentals for {len(symbols)} symbols")

            # Step 2: Determine which symbols need fetching
            symbols_to_fetch = []
            for symbol in symbols:
                should_fetch, reason = await fundamentals_service.should_fetch_fundamentals(db, symbol)
                if should_fetch:
                    symbols_to_fetch.append(symbol)
                    logger.info(f"  {symbol}: FETCH ({reason})")
                else:
                    result['symbols_skipped'] += 1
                    logger.debug(f"  {symbol}: SKIP ({reason})")

            result['symbols_to_fetch'] = len(symbols_to_fetch)

            # Step 3: Fetch fundamentals for each symbol
            for symbol in symbols_to_fetch:
                try:
                    await self._fetch_symbol_fundamentals(db, symbol)
                    result['symbols_fetched'] += 1
                except Exception as e:
                    logger.error(f"Error fetching fundamentals for {symbol}: {e}")
                    result['errors'].append(f"{symbol}: {str(e)}")

            # Step 4: Summary
            logger.info(f"Fundamentals collection complete:")
            logger.info(f"  Evaluated: {result['symbols_evaluated']}")
            logger.info(f"  Fetched: {result['symbols_fetched']}")
            logger.info(f"  Skipped: {result['symbols_skipped']}")
            logger.info(f"  Errors: {len(result['errors'])}")

            result['success'] = len(result['errors']) == 0

            return result

        except Exception as e:
            logger.error(f"Error in fundamentals collection: {e}")
            result['success'] = False
            result['errors'].append(str(e))
            return result

    async def _get_portfolio_symbols(self, db: AsyncSession) -> List[str]:
        """Get unique PUBLIC symbols from all positions"""
        try:
            # Only fetch for PUBLIC positions (stocks/ETFs)
            # Options and PRIVATE don't have fundamental data
            stmt = select(Position.symbol).distinct().where(
                Position.investment_class == 'PUBLIC'
            )
            result = await db.execute(stmt)
            symbols = [row[0] for row in result.fetchall() if row[0]]

            return symbols

        except Exception as e:
            logger.error(f"Error getting portfolio symbols: {e}")
            return []

    async def _fetch_symbol_fundamentals(
        self,
        db: AsyncSession,
        symbol: str
    ) -> None:
        """
        Fetch all fundamental data for a single symbol

        Fetches:
        - Income statements (quarterly)
        - Balance sheets (quarterly)
        - Cash flows (quarterly)
        - Analyst estimates → company_profiles

        Note: We only fetch quarterly data for now (12 periods)
        Annual data can be added later if needed
        """
        try:
            logger.info(f"Fetching fundamentals for {symbol}...")

            # Use YahooQuery Ticker directly
            from yahooquery import Ticker

            # Run in thread pool to avoid blocking async
            loop = asyncio.get_event_loop()
            ticker_data = await loop.run_in_executor(
                None,
                self._fetch_ticker_data_sync,
                symbol
            )

            if not ticker_data:
                logger.warning(f"No fundamental data available for {symbol}")
                return

            # Extract data components
            income_statements_q = ticker_data.get('income_statement_q')
            balance_sheets_q = ticker_data.get('balance_sheet_q')
            cash_flows_q = ticker_data.get('cash_flow_q')
            earnings_estimates = ticker_data.get('earnings_estimates')
            earnings_calendar = ticker_data.get('earnings_calendar')

            # Track if we stored any fundamental data
            statements_stored = False

            # Store income statements (quarterly)
            if income_statements_q is not None and not income_statements_q.empty:
                periods = await fundamentals_service.store_income_statements(
                    db=db,
                    symbol=symbol,
                    data=income_statements_q,
                    frequency='q'
                )
                logger.info(f"  Stored {periods} quarterly income statements")
                if periods > 0:
                    statements_stored = True

            # Store balance sheets (quarterly)
            if balance_sheets_q is not None and not balance_sheets_q.empty:
                periods = await fundamentals_service.store_balance_sheets(
                    db=db,
                    symbol=symbol,
                    data=balance_sheets_q,
                    frequency='q'
                )
                logger.info(f"  Stored {periods} quarterly balance sheets")
                if periods > 0:
                    statements_stored = True

            # Store cash flows (quarterly)
            if cash_flows_q is not None and not cash_flows_q.empty:
                periods = await fundamentals_service.store_cash_flows(
                    db=db,
                    symbol=symbol,
                    data=cash_flows_q,
                    frequency='q',
                    revenue_data=income_statements_q  # For FCF margin calculation
                )
                logger.info(f"  Stored {periods} quarterly cash flows")
                if periods > 0:
                    statements_stored = True

            # Update company profile with analyst estimates
            if earnings_estimates is not None:
                success = await fundamentals_service.update_company_profile_analyst_data(
                    db=db,
                    symbol=symbol,
                    earnings_estimates=earnings_estimates,
                    earnings_calendar=earnings_calendar
                )
                if success:
                    logger.info(f"  Updated analyst estimates in company_profiles")
            elif statements_stored:
                # Even without earnings estimates, update the timestamp if we stored financial statements
                # This ensures smart fetching logic works correctly
                await fundamentals_service.update_fundamentals_timestamp(db=db, symbol=symbol)
                logger.info(f"  Updated fundamentals_last_fetched timestamp for {symbol}")

            logger.info(f"Completed fundamentals for {symbol}")

        except Exception as e:
            logger.error(f"Error fetching fundamentals for {symbol}: {e}")
            raise

    def _fetch_ticker_data_sync(self, symbol: str) -> Dict[str, Any]:
        """
        Synchronous fetch of ticker data (runs in thread pool)

        Returns dict with:
        - income_statement_q: Quarterly income statements
        - balance_sheet_q: Quarterly balance sheets
        - cash_flow_q: Quarterly cash flows
        - earnings_estimates: Analyst earnings estimates
        - earnings_calendar: Next earnings date info
        """
        try:
            from yahooquery import Ticker

            ticker = Ticker(symbol)

            # Fetch all fundamental data
            # These return DataFrames or dict with error messages
            income_q = ticker.income_statement(frequency='q')
            balance_q = ticker.balance_sheet(frequency='q')
            cashflow_q = ticker.cash_flow(frequency='q')

            # These return dicts
            earnings_est = ticker.earnings_estimate if hasattr(ticker, 'earnings_estimate') else None
            earnings_cal = ticker.earnings_calendar if hasattr(ticker, 'earnings_calendar') else None

            return {
                'income_statement_q': income_q if not isinstance(income_q, dict) else None,
                'balance_sheet_q': balance_q if not isinstance(balance_q, dict) else None,
                'cash_flow_q': cashflow_q if not isinstance(cashflow_q, dict) else None,
                'earnings_estimates': earnings_est,
                'earnings_calendar': earnings_cal
            }

        except Exception as e:
            logger.error(f"Error fetching ticker data for {symbol}: {e}")
            return {}


# Singleton instance
fundamentals_collector = FundamentalsCollector()
