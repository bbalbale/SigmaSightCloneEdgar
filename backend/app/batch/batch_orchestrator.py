"""
Batch Orchestrator - Production-Ready 6-Phase Architecture with Automatic Backfill

Architecture (Renumbered 2025-11-06 for clarity):
- Phase 1: Market Data Collection (1-year lookback)
- Phase 2: Fundamental Data Collection (earnings-driven updates)
- Phase 3: P&L Calculation & Snapshots (equity rollforward)
- Phase 4: Position Market Value Updates (for analytics accuracy)
- Phase 5: Sector Tag Restoration (auto-tag from company profiles)
- Phase 6: Risk Analytics (betas, factors, volatility, correlations)

Features:
- Automatic backfill detection
- Phase isolation (failures don't cascade)
- Performance tracking
- Data coverage reporting
- Automatic sector tagging from company profiles
- Smart fundamentals fetching (3+ days after earnings)
"""
import asyncio
import json
from datetime import date, timedelta, datetime, time, timezone
from zoneinfo import ZoneInfo
from dateutil import tz
from decimal import Decimal
from typing import Dict, List, Any, Optional
from uuid import UUID, uuid4
import os

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import AsyncSessionLocal
from app.models.batch_tracking import BatchRunTracking
from app.models.positions import Position
from app.models.users import Portfolio
from app.utils.trading_calendar import trading_calendar
from app.batch.market_data_collector import market_data_collector
from app.batch.fundamentals_collector import fundamentals_collector
from app.batch.pnl_calculator import pnl_calculator
from app.batch.analytics_runner import analytics_runner
from app.calculations.market_data import get_previous_trading_day_price
from app.services.symbol_utils import should_skip_symbol
from app.telemetry.metrics import record_metric
from app.cache.price_cache import PriceCache

logger = get_logger(__name__)


class BatchOrchestrator:
    """
    Main orchestrator for 3-phase batch processing with automatic backfill

    Usage:
        # Run with automatic backfill
        await batch_orchestrator.run_daily_batch_with_backfill()

        # Run for specific date
        await batch_orchestrator.run_daily_batch_sequence(date(2025, 7, 1))

        # Run for specific portfolios
        await batch_orchestrator.run_daily_batch_sequence(
            calculation_date=date(2025, 7, 1),
            portfolio_ids=['uuid1', 'uuid2']
        )
    """

    def __init__(self) -> None:
        self._sector_analysis_target_date: Optional[date] = None

    async def run_daily_batch_with_backfill(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        portfolio_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - automatically detects and fills missing dates.

        If start_date is provided, it is used as the beginning of the backfill period.
        If not, the last successful run date is detected automatically.

        Args:
            start_date: Optional date to begin the backfill from.
            end_date: Date to process up to (defaults to today).
            portfolio_ids: Specific portfolios to process (defaults to all).

        Returns:
            Summary of backfill operation.
        """
        target_date = end_date if end_date is not None else date.today()

        # Step 2: Determine the effective target date based on NY time
        if end_date is None:
            force_time = os.environ.get("SIGMASIGHT_FORCE_NY_TIME")
            if force_time:
                try:
                    ny_now = datetime.fromisoformat(force_time)
                except ValueError:
                    ny_now = datetime.now(timezone.utc).astimezone(tz.gettz("America/New_York"))
            else:
                try:
                    ny_now = datetime.now(ZoneInfo("America/New_York"))
                except Exception:
                    eastern = tz.gettz("America/New_York")
                    if eastern is not None:
                        ny_now = datetime.now(timezone.utc).astimezone(eastern)
                    else:
                        ny_now = datetime.utcnow()

            ny_time_str = ny_now.strftime("%Y-%m-%d %H:%M:%S")
            logger.info("Current NY time: %s", ny_time_str)
            print(f"[batch] Current NY time: {ny_time_str}")

            effective_target_date = ny_now.date()
            logger.info("Initial effective target date: %s", effective_target_date)

            if not trading_calendar.is_trading_day(effective_target_date):
                previous_trading_day = trading_calendar.get_previous_trading_day(effective_target_date)
                if previous_trading_day:
                    effective_target_date = previous_trading_day
                    logger.info("Adjusted target date to previous trading day (non-trading day): %s", effective_target_date)
            elif ny_now.time() < time(16, 30):
                previous_trading_day = trading_calendar.get_previous_trading_day(ny_now.date())
                if previous_trading_day:
                    effective_target_date = previous_trading_day
                    logger.info("Adjusted target date to previous trading day (market open): %s", effective_target_date)
            
            target_date = effective_target_date
        else:
            target_date = end_date
            logger.info("Manual end_date provided: %s", target_date)

        logger.info(f"=" * 80)
        logger.info(f"Batch Orchestrator V3 - Backfill to {target_date}")
        logger.info(f"=" * 80)

        start_time = asyncio.get_event_loop().time()
        analytics_runner.reset_caches()

        # Step 1: Determine the date range to process
        async with AsyncSessionLocal() as db:
            if start_date:
                last_run_date = start_date - timedelta(days=1)
                logger.info(f"Manual start_date provided: {start_date}. Starting backfill from {last_run_date}.")
            else:
                last_run_date = await self._get_last_batch_run_date(db)
                if last_run_date:
                    logger.info(f"Last successful run detected: {last_run_date}")
                else:
                    # First run ever - get earliest position date
                    last_run_date = await self._get_earliest_position_date(db)
                    if last_run_date:
                        # Start from day before earliest position
                        last_run_date = last_run_date - timedelta(days=1)
                        logger.info(f"First run - starting from {last_run_date}")
                    else:
                        logger.warning("No positions found, nothing to process")
                        return {
                            'success': True,
                            'message': 'No positions to process',
                            'dates_processed': 0
                        }

        # Step 2: Calculate missing trading days
        missing_dates = trading_calendar.get_trading_days_between(
            start_date=last_run_date + timedelta(days=1),
            end_date=target_date
        )
        self._sector_analysis_target_date = target_date

        if not missing_dates:
            logger.info(f"Batch processing up to date as of {target_date}")
            return {
                'success': True,
                'message': f'Already up to date as of {target_date}',
                'dates_processed': 0
            }

        logger.info(f"Backfilling {len(missing_dates)} missing dates: {missing_dates[0]} to {missing_dates[-1]}")

        # OPTIMIZATION: Create multi-day price cache ONCE for entire backfill
        # This eliminates repeated price queries across all dates (10,000x speedup)
        price_cache = None
        if len(missing_dates) > 1:
            logger.info(f"🚀 OPTIMIZATION: Pre-loading multi-day price cache for {len(missing_dates)} dates")
            async with AsyncSessionLocal() as cache_db:
                # Get all symbols from active PUBLIC/OPTIONS positions
                # Skip PRIVATE positions - they don't have market prices
                symbols_stmt = select(Position.symbol).where(
                    and_(
                        Position.deleted_at.is_(None),
                        Position.symbol.isnot(None),
                        Position.symbol != '',
                        Position.investment_class.in_(['PUBLIC', 'OPTIONS'])  # Exclude PRIVATE
                    )
                ).distinct()
                symbols_result = await cache_db.execute(symbols_stmt)
                symbols = {row[0] for row in symbols_result.all()}

                if symbols:
                    # Load prices for entire date range (ONE bulk query)
                    price_cache = PriceCache()
                    loaded_count = await price_cache.load_date_range(
                        db=cache_db,
                        symbols=symbols,
                        start_date=missing_dates[0],
                        end_date=missing_dates[-1]
                    )
                    logger.info(f"✅ Price cache loaded: {loaded_count} prices across {len(missing_dates)} dates")
                    logger.info(f"   Cache stats: {price_cache.get_stats()}")

        # Step 3: Process each missing date with its own fresh session
        # CRITICAL FIX: Each date gets a fresh session to avoid greenlet errors
        # caused by expired objects after commits in analytics calculations
        results = []
        for i, calc_date in enumerate(missing_dates, 1):
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Processing {calc_date} ({i}/{len(missing_dates)})")
            logger.info(f"{'=' * 80}")

            # Create fresh session for this date
            async with AsyncSessionLocal() as db:
                result = await self.run_daily_batch_sequence(
                    calculation_date=calc_date,
                    portfolio_ids=portfolio_ids,
                    db=db,
                    run_sector_analysis=(calc_date == target_date),
                    price_cache=price_cache  # Pass shared cache
                )

                results.append(result)

                # Mark as complete in tracking table
                if result['success']:
                    await self._mark_batch_run_complete(db, calc_date, result)

        duration = int(asyncio.get_event_loop().time() - start_time)

        logger.info(f"\n{'=' * 80}")
        logger.info(f"Backfill Complete in {duration}s")
        logger.info(f"  Dates processed: {len(missing_dates)}")
        logger.info(f"  Success: {sum(1 for r in results if r['success'])}/{len(results)}")
        logger.info(f"={'=' * 80}\n")
        self._sector_analysis_target_date = None

        return {
            'success': all(r['success'] for r in results),
            'dates_processed': len(missing_dates),
            'duration_seconds': duration,
            'results': results
        }

    async def run_daily_batch_sequence(
        self,
        calculation_date: date,
        portfolio_ids: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
        run_sector_analysis: Optional[bool] = None,
        price_cache: Optional[PriceCache] = None,
    ) -> Dict[str, Any]:
        """
        Run 3-phase batch sequence for a single date

        Args:
            calculation_date: Date to process
            portfolio_ids: Specific portfolios (None = all)
            db: Optional database session

        Returns:
            Summary of batch run
        """
        normalized_portfolio_ids = self._normalize_portfolio_ids(portfolio_ids)
        if run_sector_analysis is None:
            if self._sector_analysis_target_date:
                run_sector_analysis = calculation_date == self._sector_analysis_target_date
            else:
                run_sector_analysis = True

        try:
            if db is None:
                analytics_runner.reset_caches()
                self._sector_analysis_target_date = calculation_date
                async with AsyncSessionLocal() as session:
                    return await self._run_sequence_with_session(
                        session,
                        calculation_date,
                        normalized_portfolio_ids,
                        bool(run_sector_analysis),
                        price_cache,
                    )
            else:
                return await self._run_sequence_with_session(
                    db,
                    calculation_date,
                    normalized_portfolio_ids,
                    bool(run_sector_analysis),
                    price_cache,
                )
        finally:
            # Clear batch run tracker when batch completes (success or failure)
            from app.batch.batch_run_tracker import batch_run_tracker
            batch_run_tracker.complete()
            if db is None:
                self._sector_analysis_target_date = None

    async def _run_sequence_with_session(
        self,
        db: AsyncSession,
        calculation_date: date,
        portfolio_ids: Optional[List[UUID]],
        run_sector_analysis: bool,
        price_cache: Optional[PriceCache] = None,
    ) -> Dict[str, Any]:
        """Run 6-phase sequence with provided session and optional price cache"""

        result = {
            'success': False,
            'calculation_date': calculation_date,
            'phase_1': {},
            'phase_2': {},
            'phase_3': {},
            'phase_4': {},
            'phase_5': {},
            'phase_6': {},
            'errors': []
        }
        insufficient_price_coverage = False
        coverage_details: Dict[str, Any] = {}

        # OPTIMIZATION: Skip company profiles for historical dates (only needed on current/final date)
        is_historical = calculation_date < date.today()

        # Phase 1: Market Data Collection
        try:
            self._log_phase_start("phase_1", calculation_date, portfolio_ids)
            phase1_result = await market_data_collector.collect_daily_market_data(
                calculation_date=calculation_date,
                lookback_days=365,
                db=db,
                portfolio_ids=portfolio_ids,
                skip_company_profiles=is_historical
            )
            result['phase_1'] = phase1_result
            self._log_phase_result("phase_1", phase1_result)

            if not phase1_result.get('success'):
                result['errors'].append("Phase 1 failed")
                return result

        except Exception as e:
            logger.error(f"Phase 1 error: {e}")
            result['errors'].append(f"Phase 1 error: {str(e)}")
            return result

        # Phase 2: Fundamental Data Collection
        # OPTIMIZATION: Only run on current/final date (fundamentals don't change historically)
        if not is_historical:
            try:
                self._log_phase_start("phase_2", calculation_date, portfolio_ids)
                phase2_fundamentals_result = await fundamentals_collector.collect_fundamentals_data(
                    db=db,
                    portfolio_ids=portfolio_ids
                )
                result['phase_2'] = phase2_fundamentals_result
                self._log_phase_result("phase_2", phase2_fundamentals_result)

                if not phase2_fundamentals_result.get('success'):
                    logger.warning("Phase 2 (Fundamentals) had errors, continuing to Phase 3")
                    # Continue even if fundamentals fail - not critical for P&L

            except Exception as e:
                logger.error(f"Phase 2 (Fundamentals) error: {e}")
                result['errors'].append(f"Phase 2 (Fundamentals) error: {str(e)}")
                # Continue to Phase 3 even if fundamentals fail
        else:
            logger.debug(f"Skipping Phase 2 (Fundamentals) for historical date ({calculation_date})")
            result['phase_2'] = {'success': True, 'skipped': True, 'reason': 'historical_date'}

        # Phase 3: P&L & Snapshots
        try:
            self._log_phase_start("phase_3", calculation_date, portfolio_ids)
            phase3_result = await pnl_calculator.calculate_all_portfolios_pnl(
                calculation_date=calculation_date,
                db=db,
                portfolio_ids=portfolio_ids,
                price_cache=price_cache  # Pass price cache for optimization
            )
            result['phase_3'] = phase3_result
            self._log_phase_result("phase_3", phase3_result)

            if not phase3_result.get('success'):
                result['errors'].append("Phase 3 (P&L) had errors")
                # Continue to Phase 4 even if Phase 3 has issues

        except Exception as e:
            logger.error(f"Phase 3 (P&L) error: {e}")
            result['errors'].append(f"Phase 3 (P&L) error: {str(e)}")
            # Continue to Phase 4

        # Phase 4: Update Position Market Values (CRITICAL for Phase 6 analytics)
        try:
            self._log_phase_start("phase_4", calculation_date, portfolio_ids)
            phase4_result = await self._update_all_position_market_values(
                calculation_date=calculation_date,
                db=db,
                portfolio_ids=portfolio_ids
            )
            result['phase_4'] = phase4_result
            self._log_phase_result("phase_4", phase4_result)

            if phase4_result:
                total_positions = phase4_result.get('total_positions') or 0
                positions_skipped = phase4_result.get('positions_skipped') or 0
                positions_ignored = phase4_result.get('positions_ignored', 0)
                coverage_details = {
                    'total_positions': total_positions,
                    'positions_skipped': positions_skipped,
                    'positions_ignored': positions_ignored,
                }

                if total_positions > 0:
                    missing_ratio = positions_skipped / total_positions
                    coverage_details['missing_ratio'] = round(missing_ratio, 4)

                    if missing_ratio > 0.05:
                        insufficient_price_coverage = True
                        message = (
                            f"Phase 4 insufficient price coverage: "
                            f"{positions_skipped}/{total_positions} positions missing ({missing_ratio:.1%})"
                        )
                        logger.error(message)
                        result['errors'].append(message)
                        record_metric(
                            "phase_4_insufficient_coverage",
                            {
                                'calculation_date': calculation_date.isoformat(),
                                'portfolio_scope': len(portfolio_ids) if portfolio_ids else "all",
                                **coverage_details,
                            },
                        )

            if not phase4_result.get('success'):
                logger.warning("Phase 4 (Position Updates) had errors, continuing to Phase 5")
                # Continue to Phase 5 even if position updates fail

        except Exception as e:
            logger.error(f"Phase 4 (Position Updates) error: {e}")
            result['errors'].append(f"Phase 4 (Position Updates) error: {str(e)}")
            # Continue to Phase 5

        # Phase 5: Restore Sector Tags from Company Profiles
        # OPTIMIZATION: Only run on current/final date (tags don't change historically)
        if not is_historical:
            try:
                self._log_phase_start("phase_5", calculation_date, portfolio_ids)
                phase5_result = await self._restore_all_sector_tags(
                    db=db,
                    portfolio_ids=portfolio_ids
                )
                result['phase_5'] = phase5_result
                self._log_phase_result("phase_5", phase5_result)

                if not phase5_result.get('success'):
                    logger.warning("Phase 5 (Sector Tags) had errors, continuing to Phase 6")
                    # Continue to Phase 6 even if sector tagging fails

            except Exception as e:
                logger.error(f"Phase 5 (Sector Tags) error: {e}")
                result['errors'].append(f"Phase 5 (Sector Tags) error: {str(e)}")
                # Continue to Phase 6
        else:
            logger.debug(f"Skipping Phase 5 (Sector Tags) for historical date ({calculation_date})")
            result['phase_5'] = {'success': True, 'skipped': True, 'reason': 'historical_date'}

        # Phase 6: Risk Analytics
        if insufficient_price_coverage:
            logger.error("Skipping Phase 6 due to insufficient price coverage in Phase 4")
            phase6_result = {
                'success': False,
                'skipped': True,
                'reason': 'insufficient_price_coverage',
                **coverage_details,
            }
            result['phase_6'] = phase6_result
            self._log_phase_result("phase_6", phase6_result)
            record_metric(
                "phase_6_skipped",
                {
                    'calculation_date': calculation_date.isoformat(),
                    'portfolio_scope': len(portfolio_ids) if portfolio_ids else "all",
                    **coverage_details,
                },
            )
        else:
            try:
                self._log_phase_start("phase_6", calculation_date, portfolio_ids)
                phase6_result = await analytics_runner.run_all_portfolios_analytics(
                    calculation_date=calculation_date,
                    db=db,
                    portfolio_ids=portfolio_ids,
                    run_sector_analysis=run_sector_analysis,
                    price_cache=price_cache,  # Pass price cache for optimization
                )
                result['phase_6'] = phase6_result
                self._log_phase_result("phase_6", phase6_result)

                if not phase6_result.get('success'):
                    result['errors'].append("Phase 6 (Analytics) had errors")

            except Exception as e:
                logger.error(f"Phase 6 (Analytics) error: {e}")
                result['errors'].append(f"Phase 6 (Analytics) error: {str(e)}")

        # Determine overall success
        result['success'] = len(result['errors']) == 0

        return result

    async def _update_all_position_market_values(
        self,
        calculation_date: date,
        db: AsyncSession,
        portfolio_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Update last_price and market_value for all active positions

        This is CRITICAL for Phase 3 analytics that rely on position.market_value
        (e.g., provider beta calculation)

        Args:
            calculation_date: Date to get prices for
            db: Database session

        Returns:
            Summary of positions updated
        """
        from app.models.market_data import MarketDataCache
        from decimal import Decimal

        logger.info(f"Updating position market values for {calculation_date}")

        try:
            # Get all active positions
            positions_query = select(Position).where(
                and_(
                    Position.exit_date.is_(None),
                    Position.deleted_at.is_(None)
                )
            )
            if portfolio_ids is not None:
                positions_query = positions_query.where(Position.portfolio_id.in_(portfolio_ids))

            positions_result = await db.execute(positions_query)
            positions = positions_result.scalars().all()

            total_positions_raw = len(positions)
            logger.info(f"Found {total_positions_raw} active positions to update")

            if not positions:
                return {
                    'success': True,
                    'positions_updated': 0,
                    'positions_skipped': 0,
                    'positions_ignored': 0,
                    'total_positions': 0
                }

            eligible_positions: List[Position] = []
            ignored_positions: List[Position] = []

            for position in positions:
                symbol = position.symbol or ""
                skip = True
                if symbol:
                    skip, _ = should_skip_symbol(symbol.upper())
                if skip:
                    ignored_positions.append(position)
                else:
                    eligible_positions.append(position)

            total_eligible = len(eligible_positions)

            if not eligible_positions:
                logger.info(
                    "No market-data eligible positions found; skipping price update and analytics coverage check."
                )
                return {
                    'success': True,
                    'positions_updated': 0,
                    'positions_skipped': 0,
                    'positions_ignored': total_positions_raw,
                    'price_fallbacks_used': 0,
                    'missing_price_symbols': [],
                    'total_positions': 0,
                }

            # Bulk-load market data for all symbols to avoid N+1 queries
            symbols = {position.symbol for position in eligible_positions if position.symbol}
            price_map: Dict[str, Decimal] = {}

            if symbols:
                price_query = select(MarketDataCache.symbol, MarketDataCache.close).where(
                    and_(
                        MarketDataCache.symbol.in_(symbols),
                        MarketDataCache.date == calculation_date
                    )
                )
                price_result = await db.execute(price_query)
                price_map = {
                    row[0]: row[1]
                    for row in price_result.fetchall()
                    if row[1] is not None
                }

            positions_updated = 0
            positions_skipped = 0
            fallback_prices_used = 0
            missing_price_symbols: List[str] = []

            for position in eligible_positions:
                # Get current price from market_data_cache
                current_price = price_map.get(position.symbol)

                price_date_used = calculation_date

                if current_price is None or current_price <= 0:
                    fallback_price = await get_previous_trading_day_price(
                        db=db,
                        symbol=position.symbol,
                        current_date=calculation_date,
                        max_lookback_days=5,
                    )
                    if fallback_price:
                        current_price, price_date_used = fallback_price
                        fallback_prices_used += 1
                        logger.debug(
                            "  %s: using fallback price from %s",
                            position.symbol,
                            price_date_used,
                        )
                    else:
                        positions_skipped += 1
                        missing_price_symbols.append(position.symbol)
                        logger.debug(f"  {position.symbol}: No price data available")
                        continue

                if current_price and current_price > 0:

                    # Calculate market value
                    # For stocks: quantity * price
                    # For options: quantity * price * 100 (contract multiplier)
                    multiplier = Decimal('100') if position.position_type.name in ['CALL', 'PUT', 'LC', 'LP', 'SC', 'SP'] else Decimal('1')
                    market_value = position.quantity * current_price * multiplier

                    # Update position
                    position.last_price = current_price
                    position.market_value = market_value

                    # CRITICAL FIX (2025-11-03): Recalculate unrealized_pnl to stay in sync with market_value
                    # Bug was: unrealized_pnl not updated when market_value changed, causing $104K+ errors
                    cost_basis = position.quantity * position.entry_price * multiplier
                    position.unrealized_pnl = market_value - cost_basis

                    positions_updated += 1
                    logger.debug(
                        "  %s: price=%s (as of %s), market_value=%s",
                        position.symbol,
                        current_price,
                        price_date_used,
                        market_value,
                    )

            # Commit all position updates
            await db.commit()

            logger.info(
                "Position market values updated: %s updated, %s skipped (eligible), %s fallback prices, %s ignored",
                positions_updated,
                positions_skipped,
                fallback_prices_used,
                len(ignored_positions),
            )

            return {
                'success': True,
                'positions_updated': positions_updated,
                'positions_skipped': positions_skipped,
                'positions_ignored': len(ignored_positions),
                'price_fallbacks_used': fallback_prices_used,
                'missing_price_symbols': missing_price_symbols,
                'total_positions': total_eligible
            }

        except Exception as e:
            logger.error(f"Error updating position market values: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'positions_updated': 0
            }

    async def _restore_all_sector_tags(
        self,
        db: AsyncSession,
        portfolio_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Restore sector tags for all portfolios based on company profile data.

        This updates sector tags to match current company profile sectors,
        ensuring tags stay in sync with the latest sector classifications.

        Args:
            db: Database session

        Returns:
            Summary of sector tag restoration
        """
        from app.services.sector_tag_service import restore_sector_tags_for_portfolio

        logger.info("Restoring sector tags for all portfolios")

        try:
            # Get all active portfolios
            portfolios_query = select(Portfolio).where(
                Portfolio.deleted_at.is_(None)
            )
            if portfolio_ids is not None:
                portfolios_query = portfolios_query.where(Portfolio.id.in_(portfolio_ids))

            portfolios_result = await db.execute(portfolios_query)
            portfolios = portfolios_result.scalars().all()

            logger.info(f"Found {len(portfolios)} active portfolios to update sector tags")

            total_positions_tagged = 0
            total_positions_skipped = 0
            total_tags_created = 0
            portfolios_processed = 0

            for portfolio in portfolios:
                try:
                    # Restore sector tags for this portfolio
                    result = await restore_sector_tags_for_portfolio(
                        db=db,
                        portfolio_id=portfolio.id,
                        user_id=portfolio.user_id
                    )

                    total_positions_tagged += result.get('positions_tagged', 0)
                    total_positions_skipped += result.get('positions_skipped', 0)
                    total_tags_created += result.get('tags_created', 0)
                    portfolios_processed += 1

                    logger.info(
                        f"  {portfolio.name}: {result.get('positions_tagged', 0)} positions tagged, "
                        f"{result.get('tags_created', 0)} tags created"
                    )

                except Exception as e:
                    logger.error(f"  Error restoring sector tags for portfolio {portfolio.name}: {e}")
                    # Continue to next portfolio

            logger.info(
                f"Sector tag restoration complete: "
                f"{portfolios_processed} portfolios, "
                f"{total_positions_tagged} positions tagged, "
                f"{total_tags_created} tags created"
            )

            return {
                'success': True,
                'portfolios_processed': portfolios_processed,
                'total_portfolios': len(portfolios),
                'positions_tagged': total_positions_tagged,
                'positions_skipped': total_positions_skipped,
                'tags_created': total_tags_created
            }

        except Exception as e:
            logger.error(f"Error restoring sector tags: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e),
                'portfolios_processed': 0
            }

    def _normalize_portfolio_ids(
        self,
        portfolio_ids: Optional[List[str]]
    ) -> Optional[List[UUID]]:
        """
        Convert incoming portfolio IDs (strings/UUIDs) into UUID objects.
        Returns None when no filter is provided, or an empty list when the
        caller explicitly provided IDs but none were valid.
        """
        if portfolio_ids is None:
            return None

        normalized: List[UUID] = []

        for portfolio_id in portfolio_ids:
            if isinstance(portfolio_id, UUID):
                normalized.append(portfolio_id)
                continue

            try:
                normalized.append(UUID(str(portfolio_id)))
            except (TypeError, ValueError):
                logger.warning(f"Invalid portfolio ID '{portfolio_id}', skipping")

        return normalized

    async def _get_last_batch_run_date(self, db: AsyncSession) -> Optional[date]:
        """Get the date of the last successful batch run"""
        query = select(BatchRunTracking).where(
            BatchRunTracking.phase_1_status == 'success'
        ).order_by(desc(BatchRunTracking.run_date)).limit(1)

        result = await db.execute(query)
        last_run = result.scalar_one_or_none()

        if last_run:
            return last_run.run_date

        return None

    async def _get_earliest_position_date(self, db: AsyncSession) -> Optional[date]:
        """Get the earliest position entry date across all portfolios"""
        query = select(Position.entry_date).order_by(Position.entry_date).limit(1)

        result = await db.execute(query)
        earliest_date = result.scalar_one_or_none()

        return earliest_date

    def _phase_status(self, phase_result: Dict[str, Any]) -> str:
        """Normalize phase success payload into a status label."""
        if not phase_result:
            return 'skipped'

        success = phase_result.get('success')
        if success is True:
            return 'success'
        if success is False:
            return 'failed'

        return 'unknown'

    def _log_phase_start(
        self,
        phase_name: str,
        calculation_date: date,
        portfolio_ids: Optional[List[UUID]],
    ) -> None:
        """Structured log when a phase begins."""
        payload = {
            "phase": phase_name,
            "calculation_date": str(calculation_date),
            "portfolio_scope": len(portfolio_ids) if portfolio_ids else "all",
        }
        record_metric("phase_start", payload)
        logger.info(
            "phase_start name=%s date=%s portfolios=%s",
            phase_name,
            calculation_date,
            len(portfolio_ids) if portfolio_ids else "all",
        )

    def _log_phase_result(self, phase_name: str, result: Dict[str, Any]) -> None:
        """Structured log summarizing a phase result."""
        if not result:
            logger.info("phase_result name=%s status=skipped", phase_name)
            return

        status = self._phase_status(result)
        duration = result.get('duration_seconds')
        extra_fields: Dict[str, Any] = {}

        if phase_name == "phase_2_5":
            extra_fields["positions_updated"] = result.get('positions_updated')
            extra_fields["positions_skipped"] = result.get('positions_skipped')
            extra_fields["positions_ignored"] = result.get('positions_ignored')
            extra_fields["price_fallbacks"] = result.get('price_fallbacks_used')
            extra_fields["missing_symbols"] = result.get('missing_price_symbols')
        elif phase_name == "phase_3":
            extra_fields["portfolio_count"] = result.get('portfolios_processed')
            extra_fields["analytics_completed"] = result.get('analytics_completed')
        elif phase_name == "phase_2":
            extra_fields["portfolios_processed"] = result.get('portfolios_processed')
            extra_fields["snapshots_created"] = result.get('snapshots_created')
        elif phase_name == "phase_1":
            extra_fields["symbols_requested"] = result.get('symbols_requested')
            extra_fields["symbols_fetched"] = result.get('symbols_fetched')
            extra_fields["coverage_pct"] = result.get('data_coverage_pct')

        payload = {
            "phase": phase_name,
            "status": status,
            "duration": duration,
            **{k: v for k, v in extra_fields.items() if v is not None},
        }
        record_metric("phase_result", payload)
        logger.info(
            "phase_result name=%s status=%s duration=%s extra=%s",
            phase_name,
            status,
            duration,
            extra_fields,
        )

    async def _mark_batch_run_complete(
        self,
        db: AsyncSession,
        run_date: date,
        batch_result: Dict[str, Any]
    ):
        """Mark a batch run as complete in tracking table (upsert if re-running same date)"""
        from datetime import datetime, timezone
        from sqlalchemy import select

        # Extract metrics from results
        phase1 = batch_result.get('phase_1', {})
        phase2 = batch_result.get('phase_2', {})
        phase3 = batch_result.get('phase_3', {})

        phase15 = batch_result.get('phase_1_5', {})
        phase25 = batch_result.get('phase_2_5', {})
        phase275 = batch_result.get('phase_2_75', {})

        extra_phase_status = {
            "phase_1_5": self._phase_status(phase15),
            "phase_2_5": self._phase_status(phase25),
            "phase_2_75": self._phase_status(phase275),
        }

        needs_metadata = batch_result.get('errors') or any(
            value not in ('success', 'skipped')
            for value in extra_phase_status.values()
        )

        # Check if tracking record already exists for this date (upsert logic)
        existing_stmt = select(BatchRunTracking).where(BatchRunTracking.run_date == run_date)
        existing_result = await db.execute(existing_stmt)
        tracking = existing_result.scalar_one_or_none()

        if tracking:
            # Update existing record
            logger.info(f"Updating existing batch run tracking for {run_date}")
            tracking.phase_1_status = 'success' if phase1.get('success') else 'failed'
            tracking.phase_2_status = 'success' if phase2.get('success') else 'failed'
            tracking.phase_3_status = 'success' if phase3.get('success') else 'failed'
            tracking.phase_1_duration_seconds = phase1.get('duration_seconds')
            tracking.phase_2_duration_seconds = phase2.get('duration_seconds')
            tracking.phase_3_duration_seconds = phase3.get('duration_seconds')
            tracking.portfolios_processed = phase2.get('portfolios_processed')
            tracking.symbols_fetched = phase1.get('symbols_fetched')
            tracking.data_coverage_pct = phase1.get('data_coverage_pct')
            tracking.error_message = json.dumps({
                'errors': batch_result.get('errors', []),
                'phase_status': extra_phase_status
            }) if needs_metadata else None
            tracking.completed_at = datetime.now(timezone.utc)
        else:
            # Create new record
            tracking = BatchRunTracking(
                id=uuid4(),
                run_date=run_date,
                phase_1_status='success' if phase1.get('success') else 'failed',
                phase_2_status='success' if phase2.get('success') else 'failed',
                phase_3_status='success' if phase3.get('success') else 'failed',
                phase_1_duration_seconds=phase1.get('duration_seconds'),
                phase_2_duration_seconds=phase2.get('duration_seconds'),
                phase_3_duration_seconds=phase3.get('duration_seconds'),
                portfolios_processed=phase2.get('portfolios_processed'),
                symbols_fetched=phase1.get('symbols_fetched'),
                data_coverage_pct=phase1.get('data_coverage_pct'),
                error_message=json.dumps({
                    'errors': batch_result.get('errors', []),
                    'phase_status': extra_phase_status
                }) if needs_metadata else None,
                completed_at=datetime.now(timezone.utc)
            )
            db.add(tracking)
            logger.debug(f"Created new batch run tracking for {run_date}")

        await db.commit()

        logger.debug(f"Batch run tracking record saved for {run_date}")


# Global instance
batch_orchestrator = BatchOrchestrator()
