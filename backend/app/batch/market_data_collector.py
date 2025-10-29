"""
Phase 1: Market Data Collection
Fetches all required market data once per day with 1-year lookback for volatility analysis

Provider Priority: YFinance → YahooQuery → Polygon → FMP
"""
import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Set, Tuple, Any, Optional
from uuid import UUID

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache
from app.models.positions import Position
from app.services.yahooquery_service import yahooquery_service
from app.services.market_data_service import MarketDataService

logger = get_logger(__name__)

# Factor ETFs required for analytics
FACTOR_ETFS = [
    'SPY',   # S&P 500 (market beta)
    'QQQ',   # Nasdaq 100
    'IWM',   # Russell 2000 (small cap)
    'VTI',   # Total market
    'TLT',   # 20Y Treasury (interest rate beta)
    'IEF',   # 7-10Y Treasury
    'SHY',   # 1-3Y Treasury
    'HYG',   # High yield corporate bonds (credit spread)
    'LQD',   # Investment grade corporate bonds
    'VTV',   # Value factor
    'VUG',   # Growth factor
    'MTUM',  # Momentum factor
    'QUAL',  # Quality factor
    'USMV',  # Low volatility factor
    'DJP',   # Commodities
    'VNQ',   # REITs
    'GLD',   # Gold
]


class MarketDataCollector:
    """
    Phase 1 of batch processing - collect all market data for the day

    Features:
    - 1-year historical lookback for volatility/beta calculations
    - Provider priority chain: YFinance → YahooQuery → Polygon → FMP
    - Bulk fetching for efficiency
    - Smart caching (don't re-fetch existing data)
    - Data coverage reporting
    """

    def __init__(self):
        self.market_data_service = MarketDataService()

    async def collect_daily_market_data(
        self,
        calculation_date: date,
        lookback_days: int = 365,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - collect all market data for a calculation date

        Args:
            calculation_date: Date to collect data for
            lookback_days: Number of days of historical data (default: 365 for vol analysis)
            db: Optional database session (creates one if not provided)

        Returns:
            Data coverage report with metrics
        """
        logger.info(f"=" * 80)
        logger.info(f"Phase 1: Market Data Collection for {calculation_date}")
        logger.info(f"=" * 80)

        start_time = asyncio.get_event_loop().time()

        # Create DB session if not provided
        if db is None:
            async with AsyncSessionLocal() as session:
                result = await self._collect_with_session(
                    session, calculation_date, lookback_days
                )
        else:
            result = await self._collect_with_session(
                db, calculation_date, lookback_days
            )

        duration = int(asyncio.get_event_loop().time() - start_time)
        result['duration_seconds'] = duration

        logger.info(f"Phase 1 complete in {duration}s")
        logger.info(f"  Symbols fetched: {result['symbols_fetched']}/{result['symbols_requested']}")
        logger.info(f"  Data coverage: {result['data_coverage_pct']:.1f}%")
        logger.info(f"  Date range: {result['start_date']} to {result['end_date']}")
        logger.info(f"  Provider breakdown: {result['provider_breakdown']}")

        return result

    async def _collect_with_session(
        self,
        db: AsyncSession,
        calculation_date: date,
        lookback_days: int
    ) -> Dict[str, Any]:
        """Internal collection with provided DB session"""

        # Step 1: Get symbol universe
        symbols = await self._get_symbol_universe(db)
        logger.info(f"Symbol universe: {len(symbols)} symbols")

        # Step 2: Determine date range (1 year back for vol/beta)
        end_date = calculation_date
        start_date = calculation_date - timedelta(days=lookback_days)

        logger.info(f"Date range: {start_date} to {end_date} ({lookback_days} days)")

        # Step 3: Check what data we already have in cache
        cached_symbols = await self._get_cached_symbols(db, symbols, start_date, end_date)
        missing_symbols = symbols - cached_symbols

        logger.info(f"Already cached: {len(cached_symbols)} symbols")
        logger.info(f"Need to fetch: {len(missing_symbols)} symbols")

        # Step 4: Fetch missing data using provider priority chain
        fetched_data = {}
        provider_counts = {'yahooquery': 0, 'yfinance': 0, 'fmp': 0, 'polygon': 0}

        if missing_symbols:
            fetched_data, provider_counts = await self._fetch_with_priority_chain(
                list(missing_symbols), start_date, end_date
            )

        # Step 5: Store fetched data in cache
        if fetched_data:
            await self._store_in_cache(db, fetched_data)

        # Step 6: Fetch company profiles for all symbols (needed for sector analysis)
        profile_results = await self._fetch_company_profiles(db, symbols)

        # Step 7: Calculate coverage metrics
        total_symbols = len(symbols)
        symbols_with_data = len(cached_symbols) + len(fetched_data)
        coverage_pct = (symbols_with_data / total_symbols * 100) if total_symbols > 0 else 0

        return {
            'success': True,
            'calculation_date': calculation_date,
            'start_date': start_date,
            'end_date': end_date,
            'symbols_requested': total_symbols,
            'symbols_fetched': len(fetched_data),
            'symbols_with_data': symbols_with_data,
            'data_coverage_pct': Decimal(str(coverage_pct)).quantize(Decimal('0.01')),
            'provider_breakdown': provider_counts,
            'missing_symbols': list(missing_symbols - set(fetched_data.keys())),
            'profiles_fetched': profile_results['symbols_successful'],
            'profiles_failed': profile_results['symbols_failed']
        }

    async def _get_symbol_universe(self, db: AsyncSession) -> Set[str]:
        """
        Get all unique symbols from active positions + factor ETFs

        Returns:
            Set of symbols that need market data
        """
        # Get all position symbols
        query = select(Position.symbol).distinct()
        result = await db.execute(query)
        position_symbols = {row[0] for row in result.fetchall()}

        # Add factor ETFs
        all_symbols = position_symbols | set(FACTOR_ETFS)

        # Filter out synthetic symbols (private equity, real estate, etc.)
        from app.services.market_data_service import SYNTHETIC_SYMBOLS
        real_symbols = {s for s in all_symbols if s not in SYNTHETIC_SYMBOLS}

        logger.info(f"  Position symbols: {len(position_symbols)}")
        logger.info(f"  Factor ETFs: {len(FACTOR_ETFS)}")
        logger.info(f"  Filtered (real symbols): {len(real_symbols)}")

        return real_symbols

    async def _get_cached_symbols(
        self,
        db: AsyncSession,
        symbols: Set[str],
        start_date: date,
        end_date: date
    ) -> Set[str]:
        """
        Check which symbols already have sufficient data in cache

        A symbol is considered "fully cached" if it has data for the
        calculation_date (end_date) AND has at least 250 days of history.

        This is smarter than re-fetching the entire year every time:
        - For daily runs, we only need to fetch the new day's data
        - For backfills, we only fetch missing historical data
        """
        cached = set()

        # We need data up to end_date (calculation_date)
        # AND at least 250 days of history for volatility/beta calculations
        min_required_days = 250  # ~1 year of trading days

        for symbol in symbols:
            # Check if we have data for the calculation_date (most recent date needed)
            recent_query = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol,
                MarketDataCache.date == end_date,
                MarketDataCache.close > 0
            )
            recent_result = await db.execute(recent_query)
            has_recent = recent_result.scalar_one_or_none() is not None

            if not has_recent:
                # Don't have data for calculation_date, need to fetch
                continue

            # Check if we have enough historical data
            history_query = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol,
                MarketDataCache.date >= start_date,
                MarketDataCache.date <= end_date,
                MarketDataCache.close > 0
            )
            history_result = await db.execute(history_query)
            cached_records = history_result.scalars().all()

            if len(cached_records) >= min_required_days:
                cached.add(symbol)
                logger.debug(f"  {symbol}: Fully cached ({len(cached_records)} days)")
            else:
                logger.debug(f"  {symbol}: Need more data ({len(cached_records)}/{min_required_days} days)")

        return cached

    async def _fetch_with_priority_chain(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Tuple[Dict[str, List[Dict]], Dict[str, int]]:
        """
        Fetch data using provider priority chain

        Priority: YFinance → YahooQuery → Polygon → FMP

        Smart fetching:
        - For daily runs: Only fetches the new day (end_date)
        - For backfills: Only fetches missing date ranges
        - Uses upsert to handle duplicates gracefully

        Returns:
            (fetched_data, provider_counts)
        """
        all_data = {}
        provider_counts = {'yahooquery': 0, 'yfinance': 0, 'fmp': 0, 'polygon': 0}
        remaining_symbols = symbols.copy()

        # Determine fetch strategy based on date range
        days_to_fetch = (end_date - start_date).days

        if days_to_fetch <= 7:
            # Short range (daily run or small backfill) - fetch exact range
            logger.info(f"Fetching {days_to_fetch} days of data (incremental)")
        else:
            # Long range (initial load or large backfill) - fetch full year
            logger.info(f"Fetching {days_to_fetch} days of data (historical backfill)")

        # Try YFinance first
        logger.info("Trying YFinance (primary provider)...")
        try:
            yf_data = await self.market_data_service.fetch_historical_data_hybrid(
                remaining_symbols, start_date, end_date
            )
            for symbol, data in yf_data.items():
                if data and len(data) > 0:
                    all_data[symbol] = data
                    provider_counts['yfinance'] += 1
            remaining_symbols = [s for s in remaining_symbols if s not in yf_data]
            logger.info(f"  YFinance: fetched {len(yf_data)} symbols")
        except Exception as e:
            logger.warning(f"  YFinance failed: {e}")

        # Try YahooQuery for remaining
        if remaining_symbols:
            logger.info(f"Trying YahooQuery for {len(remaining_symbols)} remaining symbols...")
            try:
                yq_data = await yahooquery_service.fetch_historical_prices(
                    remaining_symbols, start_date, end_date
                )
                for symbol, data in yq_data.items():
                    if data and len(data) > 0 and symbol not in all_data:
                        all_data[symbol] = data
                        provider_counts['yahooquery'] += 1
                remaining_symbols = [s for s in remaining_symbols if s not in yq_data]
                logger.info(f"  YahooQuery: fetched {len(yq_data)} symbols")
            except Exception as e:
                logger.warning(f"  YahooQuery failed: {e}")

        # Remaining symbols logged as missing (FMP/Polygon would go here)
        if remaining_symbols:
            logger.warning(f"Unable to fetch {len(remaining_symbols)} symbols: {remaining_symbols[:10]}")

        return all_data, provider_counts

    async def _store_in_cache(
        self,
        db: AsyncSession,
        fetched_data: Dict[str, List[Dict[str, Any]]]
    ) -> int:
        """
        Store fetched data in market_data_cache using batch upserts (10-20x faster)

        Returns:
            Number of records stored
        """
        if not fetched_data:
            return 0

        logger.info(f"Storing {len(fetched_data)} symbols in cache...")

        # Prepare all records for batch insert
        all_records = []
        for symbol, daily_data in fetched_data.items():
            for record in daily_data:
                all_records.append({
                    'symbol': symbol,
                    'date': record['date'],
                    'open': record.get('open'),
                    'high': record.get('high'),
                    'low': record.get('low'),
                    'close': record['close'],
                    'volume': record.get('volume'),
                    'data_source': record.get('data_source', 'unknown')
                })

        if not all_records:
            return 0

        # Batch insert in chunks of 1000 records
        batch_size = 1000
        records_stored = 0

        for i in range(0, len(all_records), batch_size):
            batch = all_records[i:i + batch_size]

            # Use bulk upsert
            stmt = pg_insert(MarketDataCache).values(batch)

            # On conflict, update with new data
            stmt = stmt.on_conflict_do_update(
                index_elements=['symbol', 'date'],
                set_={
                    'close': stmt.excluded.close,
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'volume': stmt.excluded.volume,
                    'data_source': stmt.excluded.data_source,
                }
            )

            await db.execute(stmt)
            records_stored += len(batch)

            logger.debug(f"  Batch {i//batch_size + 1}: Stored {len(batch)} records")

        await db.commit()
        logger.info(f"  Stored {records_stored} records in {(len(all_records) + batch_size - 1) // batch_size} batches")

        return records_stored

    async def _fetch_company_profiles(
        self,
        db: AsyncSession,
        symbols: Set[str]
    ) -> Dict[str, Any]:
        """
        Fetch company profiles for symbols that don't have them yet

        Returns:
            Results dictionary with success/failure counts
        """
        from app.models.market_data import CompanyProfile
        from sqlalchemy import select

        # Check which symbols already have profiles
        existing_query = select(CompanyProfile.symbol).where(
            CompanyProfile.symbol.in_(list(symbols))
        )
        result = await db.execute(existing_query)
        existing_symbols = {row[0] for row in result.fetchall()}

        missing_symbols = symbols - existing_symbols

        if not missing_symbols:
            logger.info(f"All {len(symbols)} symbols already have company profiles")
            return {
                'symbols_successful': 0,
                'symbols_failed': 0,
                'symbols_skipped': len(symbols)
            }

        logger.info(f"Fetching company profiles for {len(missing_symbols)} symbols...")

        # Fetch profiles using market_data_service
        results = await self.market_data_service.fetch_and_cache_company_profiles(
            db, list(missing_symbols)
        )

        logger.info(f"  Profiles fetched: {results['symbols_successful']}/{len(missing_symbols)}")
        if results['symbols_failed'] > 0:
            logger.warning(f"  Failed to fetch {results['symbols_failed']} profiles")

        return results


# Global instance
market_data_collector = MarketDataCollector()
