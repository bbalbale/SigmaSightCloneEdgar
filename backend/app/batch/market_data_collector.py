"""
Phase 1: Market Data Collection
Smart incremental/gap-fill fetching with automatic backfill detection

Fetch Modes:
- Incremental: 1 day (when yesterday's data exists)
- Gap Fill: 2-30 days (when missing a few days)
- Backfill: 365 days (initial load or gaps >30 days)

Provider Priority: YFinance → YahooQuery → Polygon → FMP
"""
import asyncio
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from typing import Dict, List, Set, Tuple, Any, Optional
from uuid import UUID

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.core.trading_calendar import is_trading_day, get_most_recent_trading_day
from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache
from app.models.positions import Position
from app.services.yahooquery_service import yahooquery_service
from app.services.market_data_service import MarketDataService
from app.services.symbol_utils import normalize_symbol, should_skip_symbol
from app.services.symbol_validator import validate_symbols

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

# Symbols to skip when fetching company profiles
# ETFs, indexes, mutual funds, and closed-end funds don't have meaningful company profiles
SKIP_COMPANY_PROFILES = {
    # Factor ETFs (from above)
    'SPY', 'QQQ', 'IWM', 'VTI', 'TLT', 'IEF', 'SHY',
    'HYG', 'LQD', 'VTV', 'VUG', 'MTUM', 'QUAL', 'USMV',
    'DJP', 'VNQ', 'GLD',
    # Major broad market ETFs
    'VOO', 'VT', 'VEA', 'VWO', 'IEFA', 'IEMG', 'DIA',
    # Bond ETFs
    'BND', 'AGG', 'VCIT', 'VCSH', 'BSV', 'BIV', 'BLV',
    # Sector ETFs
    'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLP', 'XLY', 'XLU', 'XLRE', 'XLB', 'XLC',
    # Dividend/Income ETFs
    'VIG', 'SCHD', 'DGRO', 'VYM', 'DVY', 'SDY',
    # International ETFs
    'EFA', 'EEM', 'VEU', 'VXUS', 'ACWI', 'IXUS',
    # Industry-specific ETFs
    'SMH', 'XBI', 'IBB', 'SOXX', 'KRE', 'KBE', 'XRT',
    # Leveraged/Inverse (should never have company profiles)
    'TQQQ', 'SQQQ', 'SPXL', 'SPXS', 'TMF', 'TMV', 'UPRO', 'SPXU',
}


class MarketDataCollector:
    """
    Phase 1 of batch processing - collect all market data for the day

    Features:
    - Smart incremental/gap-fill fetching (1 day, 2-30 days, or 365 days)
    - Automatic detection of missed days with intelligent backfill
    - Provider priority chain: YFinance → YahooQuery → Polygon → FMP
    - Bulk fetching for efficiency (2 queries vs 108 per run)
    - Smart caching (don't re-fetch existing data)
    - Data coverage reporting
    """

    def __init__(self):
        self.market_data_service = MarketDataService()

    async def collect_daily_market_data(
        self,
        calculation_date: date,
        lookback_days: int = 365,
        db: Optional[AsyncSession] = None,
        portfolio_ids: Optional[List[UUID]] = None,
        skip_company_profiles: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point - collect all market data for a calculation date

        Args:
            calculation_date: Date to collect data for
            lookback_days: Number of days of historical data (default: 365 for vol analysis)
            db: Optional database session (creates one if not provided)
            portfolio_ids: Optional list of portfolios to scope symbol universe
            skip_company_profiles: If True, skip company profile fetch (for historical backfills)

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
                    session, calculation_date, lookback_days, portfolio_ids, skip_company_profiles
                )
        else:
            result = await self._collect_with_session(
                db, calculation_date, lookback_days, portfolio_ids, skip_company_profiles
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
        lookback_days: int,
        portfolio_ids: Optional[List[UUID]] = None,
        skip_company_profiles: bool = False
    ) -> Dict[str, Any]:
        """Internal collection with provided DB session"""

        # Step 1: Get symbol universe
        symbols = await self._get_symbol_universe(db, calculation_date, portfolio_ids)
        logger.info(f"Symbol universe: {len(symbols)} symbols")

        # Step 2: TWO-PHASE DATE RANGE DETERMINATION
        # Phase A: Check if we have HISTORICAL lookback data (calculation_date - lookback_days)
        # Phase B: Check if we have CURRENT day data (calculation_date)

        required_start = calculation_date - timedelta(days=lookback_days)
        required_end = calculation_date

        # OPTIMIZATION: Use fast aggregate query to check if we have complete coverage
        # Instead of checking day-by-day, check if ALL symbols have data for the calculation_date
        # and for the required historical lookback period
        from sqlalchemy import func, and_
        from app.models.market_data import MarketDataCache

        # Fast check: Do we have data for calculation_date for all symbols?
        has_current_data_query = select(func.count(MarketDataCache.symbol.distinct())).where(
            and_(
                MarketDataCache.symbol.in_(list(symbols)),
                MarketDataCache.date == calculation_date,
                MarketDataCache.close > 0
            )
        )
        current_result = await db.execute(has_current_data_query)
        symbols_with_current_data = current_result.scalar()

        # Fast check: What's the earliest date we have data for 80%+ of symbols?
        # Use a single query with GROUP BY date and HAVING count
        coverage_threshold = int(len(symbols) * 0.8)
        earliest_good_date_query = select(MarketDataCache.date).where(
            and_(
                MarketDataCache.symbol.in_(list(symbols)),
                MarketDataCache.date >= required_start,
                MarketDataCache.date <= calculation_date,
                MarketDataCache.close > 0
            )
        ).group_by(MarketDataCache.date).having(
            func.count(MarketDataCache.symbol.distinct()) >= coverage_threshold
        ).order_by(MarketDataCache.date.asc()).limit(1)

        earliest_result = await db.execute(earliest_good_date_query)
        earliest_date = earliest_result.scalar()

        # Fast check: What's the most recent date we have data for 80%+ of symbols?
        most_recent_good_date_query = select(MarketDataCache.date).where(
            and_(
                MarketDataCache.symbol.in_(list(symbols)),
                MarketDataCache.date >= required_start,
                MarketDataCache.date <= calculation_date,
                MarketDataCache.close > 0
            )
        ).group_by(MarketDataCache.date).having(
            func.count(MarketDataCache.symbol.distinct()) >= coverage_threshold
        ).order_by(MarketDataCache.date.desc()).limit(1)

        most_recent_result = await db.execute(most_recent_good_date_query)
        most_recent_date = most_recent_result.scalar()

        logger.info(f"Fast coverage check: {symbols_with_current_data}/{len(symbols)} symbols have data for {calculation_date}")
        if earliest_date:
            logger.info(f"Earliest good coverage: {earliest_date}")
        if most_recent_date:
            logger.info(f"Most recent good coverage: {most_recent_date}")

        # Determine what needs to be fetched
        fetch_ranges = []

        # PHASE A: Check historical lookback gap
        if earliest_date is None or earliest_date > required_start:
            # Missing historical data before earliest_date
            historical_start = required_start
            historical_end = earliest_date - timedelta(days=1) if earliest_date else required_start
            fetch_ranges.append(("historical", historical_start, historical_end))
            logger.info(f"Historical gap: Need data from {historical_start} to {historical_end}")

        # PHASE B: Check current day gap
        if most_recent_date is None or most_recent_date < calculation_date:
            # Missing current data after most_recent_date
            current_start = most_recent_date + timedelta(days=1) if most_recent_date else calculation_date
            current_end = calculation_date
            fetch_ranges.append(("current", current_start, current_end))
            logger.info(f"Current gap: Need data from {current_start} to {current_end}")

        # Determine overall fetch mode and date range
        if not fetch_ranges:
            # No gaps - all data exists
            start_date = calculation_date
            end_date = calculation_date
            fetch_mode = "cached"
            logger.info(f"All data cached: {required_start} to {required_end}")
        elif len(fetch_ranges) == 2:
            # Both historical and current gaps
            start_date = fetch_ranges[0][1]  # historical_start
            end_date = fetch_ranges[1][2]    # current_end
            fetch_mode = "full_backfill"
            logger.info(f"Full backfill: Historical + Current gaps = {start_date} to {end_date}")
        elif fetch_ranges[0][0] == "historical":
            # Only historical gap
            start_date = fetch_ranges[0][1]
            end_date = fetch_ranges[0][2]
            fetch_mode = "historical_backfill"
            logger.info(f"Historical backfill: {start_date} to {end_date}")
        else:
            # Only current gap
            start_date = fetch_ranges[0][1]
            end_date = fetch_ranges[0][2]
            fetch_mode = "incremental"
            logger.info(f"Incremental: {start_date} to {end_date}")

        # TRADING CALENDAR CHECK: Adjust end_date to most recent trading day
        if not is_trading_day(end_date):
            original_end = end_date
            end_date = get_most_recent_trading_day(end_date)
            logger.info(f"Trading Calendar: {original_end} is not a trading day (weekend/holiday)")
            logger.info(f"Trading Calendar: Using most recent trading day {end_date} instead")

            # If start_date is now after adjusted end_date, skip fetching
            if start_date > end_date:
                logger.info(f"Trading Calendar: No trading days in range {start_date} to {original_end}, skipping fetch")

                # Return early with cached data stats
                return {
                    'success': True,
                    'calculation_date': calculation_date,
                    'start_date': end_date,
                    'end_date': end_date,
                    'fetch_mode': 'skipped_non_trading_day',
                    'symbols_requested': len(symbols),
                    'symbols_fetched': 0,
                    'symbols_with_data': len(symbols),  # Assume cached
                    'data_coverage_pct': Decimal('100.00'),
                    'provider_breakdown': {'skipped': len(symbols)},
                    'missing_symbols': [],
                    'profiles_fetched': 0,
                    'profiles_failed': 0
                }

        # OPTIMIZATION: If fetch_mode is "cached", skip fetching entirely
        if fetch_mode == "cached":
            logger.info("All required data is cached - skipping fetch")
            return {
                'success': True,
                'calculation_date': calculation_date,
                'start_date': required_start,
                'end_date': required_end,
                'fetch_mode': 'cached',
                'symbols_requested': len(symbols),
                'symbols_fetched': 0,
                'symbols_with_data': len(symbols),
                'data_coverage_pct': Decimal('100.00'),
                'provider_breakdown': {'cached': len(symbols)},
                'missing_symbols': [],
                'profiles_fetched': 0,
                'profiles_failed': 0
            }

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
        # OPTIMIZATION: Skip for historical backfills (only needed on current/final date)
        if not skip_company_profiles:
            profile_results = await self._fetch_company_profiles(db, symbols)
        else:
            logger.debug(f"Skipping company profile fetch for historical date ({calculation_date})")
            profile_results = {'symbols_successful': 0, 'symbols_failed': 0}

        # Step 7: Calculate coverage metrics
        total_symbols = len(symbols)
        symbols_with_data = len(cached_symbols) + len(fetched_data)
        coverage_pct = (symbols_with_data / total_symbols * 100) if total_symbols > 0 else 0

        return {
            'success': True,
            'calculation_date': calculation_date,
            'start_date': start_date,
            'end_date': end_date,
            'fetch_mode': fetch_mode,  # 'incremental' or 'backfill'
            'symbols_requested': total_symbols,
            'symbols_fetched': len(fetched_data),
            'symbols_with_data': symbols_with_data,
            'data_coverage_pct': Decimal(str(coverage_pct)).quantize(Decimal('0.01')),
            'provider_breakdown': provider_counts,
            'missing_symbols': list(missing_symbols - set(fetched_data.keys())),
            'profiles_fetched': profile_results['symbols_successful'],
            'profiles_failed': profile_results['symbols_failed']
        }

    async def _get_symbol_universe(
        self,
        db: AsyncSession,
        calculation_date: date,
        portfolio_ids: Optional[List[UUID]] = None
    ) -> Set[str]:
        """
        Get all unique symbols from active positions + factor ETFs

        Returns:
            Set of symbols that need market data
        """
        # Get all position symbols
        query = (
            select(Position.symbol)
            .distinct()
            .where(
                Position.symbol.is_not(None),
                Position.symbol != '',
                Position.deleted_at.is_(None),
                (Position.investment_class.notin_(['PRIVATE', 'OPTIONS'])) | (Position.investment_class.is_(None)),
                (Position.exit_date.is_(None)) | (Position.exit_date >= calculation_date),
                (Position.expiration_date.is_(None)) | (Position.expiration_date >= calculation_date),
            )
        )
        if portfolio_ids is not None:
            query = query.where(Position.portfolio_id.in_(portfolio_ids))

        result = await db.execute(query)
        position_symbols = {
            normalize_symbol(symbol)
            for symbol in result.scalars().all()
        }

        # Add factor ETFs
        factor_symbols = {normalize_symbol(symbol) for symbol in FACTOR_ETFS}
        all_symbols = {symbol for symbol in (position_symbols | factor_symbols) if symbol}

        filtered_symbols: Set[str] = set()
        skipped_symbols: list[str] = []
        for symbol in all_symbols:
            skip, reason = should_skip_symbol(symbol)
            if skip:
                skipped_symbols.append(f"{symbol} ({reason})")
                continue
            filtered_symbols.add(symbol)

        if not filtered_symbols:
            logger.info("No tradable symbols found for market data collection")
            return set()

        logger.info(f"  Position symbols: {len(position_symbols)}")
        logger.info(f"  Factor ETFs: {len(FACTOR_ETFS)}")
        logger.info(f"  Filtered (real symbols): {len(filtered_symbols)}")
        if skipped_symbols:
            logger.info(
                "  Skipped synthetic/option symbols: %d",
                len(skipped_symbols),
            )

        existing_query = (
            select(MarketDataCache.symbol)
            .where(MarketDataCache.symbol.in_(list(filtered_symbols)))
            .distinct()
        )
        existing_result = await db.execute(existing_query)
        symbols_with_cached_data = {
            normalize_symbol(symbol)
            for symbol in existing_result.scalars().all()
        }

        symbols_to_validate = filtered_symbols - symbols_with_cached_data
        additional_valid: Set[str] = set()
        if symbols_to_validate:
            valid_symbols, invalid_symbols = await validate_symbols(symbols_to_validate)
            additional_valid = valid_symbols
            if invalid_symbols:
                logger.warning(
                    "Skipping %d symbols failing validation: %s",
                    len(invalid_symbols),
                    list(invalid_symbols)[:10],
                )

        real_symbols = symbols_with_cached_data | additional_valid
        return real_symbols

    async def _get_earliest_data_date(
        self,
        db: AsyncSession,
        symbols: Set[str]
    ) -> Optional[date]:
        """
        Find the earliest date that has market data for >= 80% of symbols

        Returns:
            Earliest date with sufficient data coverage, or None if no data exists
        """
        from sqlalchemy import func, and_
        from app.models.market_data import MarketDataCache

        # Get the earliest date with data for at least 80% of symbols
        # Strategy: Get the min date overall, then work forwards checking coverage
        min_date_query = select(func.min(MarketDataCache.date)).where(
            MarketDataCache.symbol.in_(list(symbols))
        )
        result = await db.execute(min_date_query)
        min_date = result.scalar()

        if not min_date:
            logger.info("No market data found in cache")
            return None

        # Check forwards from min_date to find a date with good coverage
        threshold = len(symbols) * 0.8
        check_date = min_date

        for _ in range(30):  # Check up to 30 days forward
            count_query = select(func.count(MarketDataCache.symbol.distinct())).where(
                and_(
                    MarketDataCache.symbol.in_(list(symbols)),
                    MarketDataCache.date == check_date,
                    MarketDataCache.close > 0
                )
            )
            count_result = await db.execute(count_query)
            symbols_with_data = count_result.scalar()

            if symbols_with_data >= threshold:
                logger.info(f"Earliest data: {check_date} ({symbols_with_data}/{len(symbols)} symbols)")
                return check_date

            check_date = check_date + timedelta(days=1)

        logger.warning(f"No early date found with >80% coverage (checked forward to {check_date})")
        return None

    async def _get_most_recent_data_date(
        self,
        db: AsyncSession,
        symbols: Set[str]
    ) -> Optional[date]:
        """
        Find the most recent date that has market data for >= 80% of symbols

        Returns:
            Most recent date with sufficient data coverage, or None if no data exists
        """
        from sqlalchemy import func, and_, desc
        from app.models.market_data import MarketDataCache

        # Get the most recent date with data for at least 80% of symbols
        # Strategy: Get the max date overall, then work backwards checking coverage
        max_date_query = select(func.max(MarketDataCache.date)).where(
            MarketDataCache.symbol.in_(list(symbols))
        )
        result = await db.execute(max_date_query)
        max_date = result.scalar()

        if not max_date:
            logger.info("No market data found in cache")
            return None

        # Check backwards from max_date to find a date with good coverage
        threshold = len(symbols) * 0.8
        check_date = max_date

        for _ in range(30):  # Check up to 30 days back
            count_query = select(func.count(MarketDataCache.symbol.distinct())).where(
                and_(
                    MarketDataCache.symbol.in_(list(symbols)),
                    MarketDataCache.date == check_date,
                    MarketDataCache.close > 0
                )
            )
            count_result = await db.execute(count_query)
            symbols_with_data = count_result.scalar()

            if symbols_with_data >= threshold:
                logger.info(f"Most recent data: {check_date} ({symbols_with_data}/{len(symbols)} symbols)")
                return check_date

            check_date = check_date - timedelta(days=1)

        logger.warning(f"No recent date found with >80% coverage (checked back to {check_date})")
        return None

    async def _has_data_for_date(
        self,
        db: AsyncSession,
        symbols: Set[str],
        check_date: date
    ) -> bool:
        """
        Quick check if we have market data for a specific date

        Returns True if we have data for >= 80% of symbols on this date
        (indicates this is an incremental run, not initial backfill)
        """
        from sqlalchemy import func, and_
        from app.models.market_data import MarketDataCache

        # Count how many symbols have data for this date
        query = select(func.count(MarketDataCache.symbol.distinct())).where(
            and_(
                MarketDataCache.symbol.in_(list(symbols)),
                MarketDataCache.date == check_date,
                MarketDataCache.close > 0
            )
        )
        result = await db.execute(query)
        symbols_with_data = result.scalar()

        # If we have data for >= 80% of symbols, consider it an incremental run
        threshold = len(symbols) * 0.8
        has_data = symbols_with_data >= threshold

        logger.debug(f"Date {check_date}: {symbols_with_data}/{len(symbols)} symbols ({symbols_with_data/len(symbols)*100:.1f}%)")

        return has_data

    async def _get_cached_symbols(
        self,
        db: AsyncSession,
        symbols: Set[str],
        start_date: date,
        end_date: date
    ) -> Set[str]:
        """
        Check which symbols already have sufficient data in cache (OPTIMIZED)

        A symbol is considered "fully cached" if it has data for the
        calculation_date (end_date) AND has at least 250 days of history.

        PERFORMANCE: Uses 2 bulk queries instead of 2*N queries (was 108 queries, now 2)
        """
        from sqlalchemy import func, and_

        cached = set()
        min_required_days = 250  # ~1 year of trading days

        # OPTIMIZATION 1: Bulk check for symbols with data on calculation_date
        # Single query replaces N queries (54 -> 1)
        recent_query = select(MarketDataCache.symbol).where(
            and_(
                MarketDataCache.symbol.in_(list(symbols)),
                MarketDataCache.date == end_date,
                MarketDataCache.close > 0
            )
        ).distinct()
        recent_result = await db.execute(recent_query)
        symbols_with_recent_data = {row[0] for row in recent_result.fetchall()}

        if not symbols_with_recent_data:
            logger.info("No symbols have data for calculation date, fetching all")
            return cached

        # OPTIMIZATION 2: Bulk count historical records using SQL COUNT + GROUP BY
        # Single query replaces N queries + data loads (54 -> 1)
        history_query = select(
            MarketDataCache.symbol,
            func.count(MarketDataCache.id).label('record_count')
        ).where(
            and_(
                MarketDataCache.symbol.in_(list(symbols_with_recent_data)),
                MarketDataCache.date >= start_date,
                MarketDataCache.date <= end_date,
                MarketDataCache.close > 0
            )
        ).group_by(MarketDataCache.symbol)

        history_result = await db.execute(history_query)
        symbol_counts = {row[0]: row[1] for row in history_result.fetchall()}

        # Determine which symbols are fully cached
        for symbol in symbols_with_recent_data:
            record_count = symbol_counts.get(symbol, 0)
            if record_count >= min_required_days:
                cached.add(symbol)
                logger.debug(f"  {symbol}: Fully cached ({record_count} days)")
            else:
                logger.debug(f"  {symbol}: Need more data ({record_count}/{min_required_days} days)")

        logger.info(f"Cache check: 2 bulk queries instead of {len(symbols)*2} individual queries")
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

        eligible_symbols: Set[str] = set()
        skipped_symbols: Set[str] = set()
        etf_symbols: Set[str] = set()

        for symbol in symbols:
            skip_symbol, _ = should_skip_symbol(symbol)
            if skip_symbol:
                skipped_symbols.add(symbol)
            elif symbol in SKIP_COMPANY_PROFILES:
                etf_symbols.add(symbol)
            else:
                eligible_symbols.add(symbol)

        if skipped_symbols:
            logger.debug(
                "Skipping %s synthetic/option symbols for company profiles: %s",
                len(skipped_symbols),
                list(skipped_symbols)[:10],
            )

        if etf_symbols:
            logger.debug(
                "Skipping %s ETF/fund symbols for company profiles: %s",
                len(etf_symbols),
                list(sorted(etf_symbols))[:10],
            )

        if not eligible_symbols:
            logger.info(
                "No eligible symbols found for company profiles (%s synthetic, %s ETF/funds).",
                len(skipped_symbols),
                len(etf_symbols),
            )
            return {
                'symbols_successful': 0,
                'symbols_failed': 0,
                'symbols_skipped': len(skipped_symbols),
                'symbols_etf_skipped': len(etf_symbols),
                'symbols_missing': 0,
                'symbols_stale': 0,
            }

        # Check which symbols already have profiles
        existing_query = select(CompanyProfile.symbol, CompanyProfile.last_updated).where(
            CompanyProfile.symbol.in_(list(eligible_symbols))
        )
        result = await db.execute(existing_query)
        rows = result.fetchall()

        existing_symbols = set()
        stale_symbols = set()
        freshness_cutoff = datetime.now(timezone.utc) - timedelta(days=3)

        for symbol, last_updated in rows:
            existing_symbols.add(symbol)
            if last_updated is None or last_updated < freshness_cutoff:
                stale_symbols.add(symbol)

        missing_symbols = eligible_symbols - existing_symbols

        symbols_to_fetch = sorted(missing_symbols | stale_symbols)

        if not symbols_to_fetch:
            logger.info(
                "All %s eligible symbols already have fresh company profiles (<=3 days old, %s ETF/funds skipped)",
                len(eligible_symbols),
                len(etf_symbols),
            )
            return {
                'symbols_successful': 0,
                'symbols_failed': 0,
                'symbols_skipped': len(skipped_symbols),
                'symbols_etf_skipped': len(etf_symbols),
                'symbols_stale': 0,
                'symbols_missing': 0,
            }

        logger.info(
            "Fetching company profiles for %s symbols (%s missing, %s stale, %s synthetic skipped, %s ETF/funds skipped)...",
            len(symbols_to_fetch),
            len(missing_symbols),
            len(stale_symbols),
            len(skipped_symbols),
            len(etf_symbols),
        )
        logger.debug("Profile fetch symbol list: %s", symbols_to_fetch)

        # Fetch profiles using market_data_service
        results = await self.market_data_service.fetch_and_cache_company_profiles(
            db, symbols_to_fetch
        )

        logger.info(
            "  Profiles fetched: %s/%s (missing=%s, stale=%s)",
            results['symbols_successful'],
            len(symbols_to_fetch),
            len(missing_symbols),
            len(stale_symbols),
        )
        if results['symbols_failed'] > 0:
            logger.warning(f"  Failed to fetch {results['symbols_failed']} profiles")

        results['symbols_missing'] = len(missing_symbols)
        results['symbols_stale'] = len(stale_symbols)
        results['symbols_skipped'] = len(skipped_symbols)
        results['symbols_etf_skipped'] = len(etf_symbols)
        return results


# Global instance
market_data_collector = MarketDataCollector()
