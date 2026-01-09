"""
Batch Orchestrator - Production-Ready 9-Phase Architecture with Automatic Backfill

Architecture (Updated 2025-12-20 to add Phases 1.5 and 1.75):
- Phase 0: Company Profile Sync (beta values, sector, industry) - RUNS FIRST on final date only
- Phase 1: Market Data Collection (1-year lookback)
- Phase 1.5: Symbol Factor Calculation (universe-level ridge/spread factors)
- Phase 1.75: Symbol Metrics Calculation (returns, valuations, denormalized factors)
- Phase 2: Fundamental Data Collection (earnings-driven updates)
- Phase 3: P&L Calculation & Snapshots (equity rollforward)
- Phase 4: Position Market Value Updates (for analytics accuracy)
- Phase 5: Sector Tag Restoration (auto-tag from company profiles)
- Phase 6: Risk Analytics (betas, factors, volatility, correlations)

Phase 1.5 (Symbol Factor Calculation) Key Insight:
- Factor betas are intrinsic to the symbol (AAPL's momentum beta is the same in every portfolio)
- Pre-compute once per symbol, then aggregate via position weights at portfolio level
- Eliminates redundant regression calculations (O(symbols) instead of O(positions))
- Stored in symbol_factor_exposures table for fast lookup during Phase 6

Features:
- Automatic backfill detection
- Phase isolation (failures don't cascade)
- Performance tracking
- Data coverage reporting
- Automatic sector tagging from company profiles
- Smart fundamentals fetching (3+ days after earnings)
- Company profiles synced BEFORE calculations on final date only for fresh beta values
- Symbol factor pre-computation before portfolio analytics
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
from app.models.snapshots import PortfolioSnapshot
from app.utils.trading_calendar import trading_calendar
from app.batch.market_data_collector import market_data_collector
from app.batch.fundamentals_collector import fundamentals_collector
from app.batch.pnl_calculator import pnl_calculator
from app.batch.analytics_runner import analytics_runner
from app.calculations.market_data import get_previous_trading_day_price
from app.services.symbol_utils import should_skip_symbol
from app.telemetry.metrics import record_metric
from app.cache.price_cache import PriceCache
from app.services.batch_history_service import record_batch_start, record_batch_complete

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
        portfolio_ids: Optional[List[str]] = None,
        portfolio_id: Optional[str] = None,  # NEW: Single portfolio mode
        source: Optional[str] = None,        # NEW: Entry point tracking (None = auto-detect)
    ) -> Dict[str, Any]:
        """
        Main entry point - automatically detects and fills missing dates.

        This is the UNIFIED batch function that handles all use cases:
        1. Cron mode (portfolio_id=None): Process entire symbol universe
        2. Single-portfolio mode (portfolio_id=X): Process only that portfolio's symbols

        If start_date is provided, it is used as the beginning of the backfill period.
        If not, the last successful run date is detected automatically.

        Args:
            start_date: Optional date to begin the backfill from.
            end_date: Date to process up to (defaults to today).
            portfolio_ids: Specific portfolios to process (defaults to all).
            portfolio_id: Single portfolio ID for onboarding/settings mode.
                         When provided, enables scoped mode (~40x faster).
            source: Entry point for tracking ("cron", "onboarding", "settings", "admin").
                   If None, auto-detects based on RAILWAY_ENVIRONMENT ("cron" vs "manual").

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

        # =============================================================================
        # SINGLE-PORTFOLIO MODE DETECTION
        # When portfolio_id is provided, enable scoped mode for ~40x faster processing
        # =============================================================================
        is_single_portfolio_mode = portfolio_id is not None
        scoped_only = is_single_portfolio_mode

        if is_single_portfolio_mode:
            logger.info(f"Single-portfolio mode: processing portfolio {portfolio_id}")
            logger.info(f"Entry point: {source}")
            # Convert single portfolio_id to list format for internal use
            portfolio_ids = [portfolio_id]
        else:
            logger.info(f"Universe mode: processing all portfolios")

        logger.info(f"Batch Orchestrator - Backfill to {target_date}")

        start_time = asyncio.get_event_loop().time()
        analytics_runner.reset_caches()

        # Determine triggered_by for batch history (used after confirming work exists)
        triggered_by = source if source else ("cron" if os.environ.get("RAILWAY_ENVIRONMENT") else "manual")

        # Step 1: Determine the date range to process
        async with AsyncSessionLocal() as db:
            if is_single_portfolio_mode and not start_date:
                # SINGLE-PORTFOLIO MODE: Use portfolio's earliest entry_date
                earliest_query = select(Position.entry_date).where(
                    and_(
                        Position.portfolio_id == UUID(portfolio_id) if isinstance(portfolio_id, str) else portfolio_id,
                        Position.deleted_at.is_(None),
                        Position.entry_date.isnot(None)
                    )
                ).order_by(Position.entry_date).limit(1)
                result = await db.execute(earliest_query)
                earliest_date = result.scalar_one_or_none()

                if earliest_date:
                    last_run_date = earliest_date - timedelta(days=1)
                    logger.info(f"Single-portfolio backfill from earliest entry_date: {earliest_date}")
                else:
                    logger.warning(f"Portfolio {portfolio_id} has no positions with entry dates")
                    return {
                        'success': True,
                        'message': 'No positions with entry dates found',
                        'dates_processed': 0,
                        'portfolio_id': portfolio_id
                    }
            elif start_date:
                last_run_date = start_date - timedelta(days=1)
                logger.debug(f"Manual start_date: {start_date}")
            else:
                last_run_date = await self._get_last_batch_run_date(db)
                if last_run_date:
                    logger.debug(f"Last run: {last_run_date}")
                else:
                    # First run ever - get earliest position date
                    last_run_date = await self._get_earliest_position_date(db)
                    if last_run_date:
                        # Start from day before earliest position
                        last_run_date = last_run_date - timedelta(days=1)
                        logger.debug(f"First run from {last_run_date}")
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

        # NOW record batch start - only after confirming there's work to do
        # This prevents orphaned "running" entries in batch_run_history
        batch_run_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        record_batch_start(
            batch_run_id=batch_run_id,
            triggered_by=triggered_by,
            total_jobs=len(missing_dates),
        )

        # =============================================================================
        # PHASE 6 HARDENING: Wrap all processing in try/except to ensure record_batch_complete()
        # is ALWAYS called, even on crashes/timeouts/OOM. This prevents batch_run_history
        # rows from getting stuck in "running" status forever.
        #
        # Progress tracker: Mutable dict updated by _execute_batch_phases() so the
        # exception handler knows how many dates completed before the crash.
        # =============================================================================
        progress = {"completed": 0, "failed": 0}

        try:
            return await self._execute_batch_phases(
                missing_dates=missing_dates,
                target_date=target_date,
                portfolio_ids=portfolio_ids,
                scoped_only=scoped_only,
                batch_run_id=batch_run_id,
                progress=progress,  # Track progress for accurate crash reporting
            )
        except (Exception, asyncio.CancelledError) as e:
            # Record batch failure in database history before re-raising
            # NOTE: asyncio.CancelledError inherits from BaseException (not Exception)
            # in Python 3.8+, so we explicitly catch it to handle SIGTERM/deployment restarts
            logger.error(f"Batch failed with exception: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            duration = int(asyncio.get_event_loop().time() - start_time)
            # Use actual progress - crash may have happened after some dates succeeded
            completed = progress["completed"]
            failed = len(missing_dates) - completed  # Remaining dates count as failed
            record_batch_complete(
                batch_run_id=batch_run_id,
                status="failed",
                completed_jobs=completed,
                failed_jobs=failed,
                phase_durations={"total_duration": duration},
                error_summary={
                    "exception": str(e),
                    "type": type(e).__name__,
                    "crashed_after_dates": completed,
                },
            )
            raise  # Re-raise so caller knows batch failed

    async def _execute_batch_phases(
        self,
        missing_dates: List[date],
        target_date: date,
        portfolio_ids: Optional[List[str]],
        scoped_only: bool,
        batch_run_id: str,
        progress: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Execute all batch phases (1, 1.5, 1.75, 2-6) for the given date range.

        This is extracted from run_daily_batch_with_backfill() to enable proper
        try/except handling for Phase 6 hardening. Any exception here will be
        caught by the caller and recorded as a failed batch in batch_run_history.

        Args:
            missing_dates: Trading days to process
            target_date: Final target date
            portfolio_ids: Portfolio IDs to process (None = all)
            scoped_only: If True, only process portfolio symbols + factor ETFs
            batch_run_id: Batch run ID for history tracking
            progress: Mutable dict {"completed": N, "failed": N} updated as dates
                     are processed. Allows exception handler to report accurate
                     progress if batch crashes midway.

        Returns:
            Summary of batch operation
        """
        start_time = asyncio.get_event_loop().time()

        # =============================================================================
        # STEP 1: Run Phase 1 (Market Data) for ALL dates FIRST
        # This ensures market_data_cache has all prices before we load the price cache
        # =============================================================================
        logger.info(f"Phase 1: Collecting market data for {len(missing_dates)} dates")
        if scoped_only:
            logger.info(f"  Scoped mode: only fetching portfolio symbols + factor ETFs (~30 symbols)")
        for i, calc_date in enumerate(missing_dates, 1):
            logger.debug(f"Phase 1: {calc_date} ({i}/{len(missing_dates)})")
            async with AsyncSessionLocal() as db:
                try:
                    phase1_result = await market_data_collector.collect_daily_market_data(
                        calculation_date=calc_date,
                        lookback_days=365,
                        db=db,
                        portfolio_ids=portfolio_ids,
                        skip_company_profiles=True,  # Company profiles handled in Phase 0
                        scoped_only=scoped_only,     # NEW: Only portfolio symbols in single-portfolio mode
                    )
                    if not phase1_result.get('success'):
                        logger.warning(f"Phase 1 issues: {calc_date}")
                except Exception as e:
                    logger.error(f"Phase 1 error {calc_date}: {e}")
                    # Continue to next date - we'll try to process what we have

        # =============================================================================
        # STEP 2: Load price cache AFTER all market data is collected
        # Now the cache will include today's prices from Phase 1
        # NOTE: In scoped mode, only load portfolio symbols + factor ETFs
        # =============================================================================
        price_cache = None
        symbols: set = set()  # Initialize to prevent undefined variable if exception occurs
        logger.debug(f"Loading price cache...")
        async with AsyncSessionLocal() as cache_db:
            # Get all symbols from active PUBLIC/OPTIONS positions
            # Skip PRIVATE positions - they don't have market prices
            # In scoped_only mode, filter to single portfolio
            symbols_stmt = select(Position.symbol).where(
                and_(
                    Position.deleted_at.is_(None),
                    Position.symbol.isnot(None),
                    Position.symbol != '',
                    Position.investment_class.in_(['PUBLIC', 'OPTIONS'])  # Exclude PRIVATE
                )
            ).distinct()
            # Scope to portfolio_ids if provided
            if portfolio_ids:
                from uuid import UUID as UUID_type
                portfolio_uuids = [
                    UUID_type(pid) if isinstance(pid, str) else pid
                    for pid in portfolio_ids
                ]
                symbols_stmt = symbols_stmt.where(Position.portfolio_id.in_(portfolio_uuids))
            symbols_result = await cache_db.execute(symbols_stmt)
            position_symbols = {row[0] for row in symbols_result.all()}

            # Get symbols from market_data_cache
            # SCOPED MODE: Skip universe symbols to avoid loading 1,193 symbols
            from app.models.market_data import MarketDataCache
            if scoped_only:
                universe_symbols: set = set()
                logger.info(f"  Scoped mode: skipping universe symbols for price cache")
            else:
                # Get ALL symbols from market_data_cache (full universe for Phase 1.5)
                # This includes S&P 500, Nasdaq 100, Russell 2000, etc.
                cache_symbols_stmt = select(MarketDataCache.symbol).where(
                    and_(
                        MarketDataCache.symbol.isnot(None),
                        MarketDataCache.symbol != ''
                    )
                ).distinct()
                cache_symbols_result = await cache_db.execute(cache_symbols_stmt)
                universe_symbols = {row[0] for row in cache_symbols_result.all()}

            # Add factor ETF symbols for spread factor calculations + IR Beta
            # These are required by app/calculations/factors_spread.py and interest_rate_beta.py
            factor_etf_symbols = {'VUG', 'VTV', 'MTUM', 'QUAL', 'IWM', 'SPY', 'USMV', 'TLT'}

            # Union all symbol sources
            symbols = position_symbols.union(universe_symbols).union(factor_etf_symbols)
            logger.info(f"Price cache: loading {len(symbols)} symbols (positions: {len(position_symbols)}, universe: {len(universe_symbols)})")

            if symbols:
                # Load 366 days of price history for regression windows
                # Covers 1-year lookback for all calculations (beta, correlation, volatility)
                price_cache = PriceCache()
                cache_start = missing_dates[0] - timedelta(days=366)
                loaded_count = await price_cache.load_date_range(
                    db=cache_db,
                    symbols=symbols,
                    start_date=cache_start,
                    end_date=missing_dates[-1]
                )
                logger.debug(f"Price cache: {loaded_count} prices loaded")
                logger.debug(f"   Cache stats: {price_cache.get_stats()}")

        # =============================================================================
        # STEP 2.5: Calculate Symbol Factors ONCE for all symbols (Phase 1.5)
        # This pre-computes factor betas for the entire universe before portfolio processing.
        # Symbol betas are intrinsic to the symbol (not position-specific), so we calculate
        # them once and reuse during portfolio aggregation in Phase 6.
        # NOTE: In scoped mode, only calculate for portfolio symbols + factor ETFs
        # =============================================================================
        # Use the last trading day for symbol-level calculations
        # Both Phase 1.5 and Phase 1.75 use this same date to ensure factor lookups work
        final_date = missing_dates[-1]

        symbol_factor_result = None
        try:
            from app.calculations.symbol_factors import calculate_universe_factors

            if scoped_only:
                logger.info(f"Phase 1.5: Calculating symbol factors for {len(symbols)} scoped symbols (date={final_date})")
            else:
                logger.info(f"Phase 1.5: Calculating symbol factors for universe (date={final_date})")

            symbol_factor_result = await calculate_universe_factors(
                calculation_date=final_date,
                regularization_alpha=1.0,
                calculate_ridge=True,
                calculate_spread=True,
                price_cache=price_cache,
                symbols=list(symbols) if scoped_only else None,  # Pass symbols in scoped mode
            )

            logger.info(
                f"Phase 1.5 complete: {symbol_factor_result['symbols_processed']} symbols, "
                f"Ridge: {symbol_factor_result['ridge_results']['calculated']} calc / "
                f"{symbol_factor_result['ridge_results']['cached']} cached, "
                f"Spread: {symbol_factor_result['spread_results']['calculated']} calc / "
                f"{symbol_factor_result['spread_results']['cached']} cached"
            )

            if symbol_factor_result.get('errors'):
                logger.warning(f"Phase 1.5 had {len(symbol_factor_result['errors'])} errors")

        except Exception as e:
            logger.error(f"Phase 1.5 (Symbol Factors) error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Continue to Phase 2-6 even if symbol factors fail
            # Portfolio-level analytics will fall back to position-level calculations

        # =============================================================================
        # STEP 2.75: Calculate Symbol Metrics (returns, valuations) (Phase 1.75)
        # Pre-calculates returns and metrics for all symbols before P&L calculation.
        # P&L calculator can then lookup returns instead of recalculating per position.
        # Also populates symbol_daily_metrics for the Symbol Dashboard.
        # Uses same final_date as Phase 1.5 to ensure factor lookups work correctly.
        # NOTE: In scoped mode, only calculate for portfolio symbols + factor ETFs
        # =============================================================================
        symbol_metrics_result = None
        try:
            from app.services.symbol_metrics_service import calculate_symbol_metrics

            # Use same final_date as Phase 1.5 (already set above)
            if scoped_only:
                logger.info(f"Phase 1.75: Calculating symbol metrics for {len(symbols)} scoped symbols (date={final_date})")
            else:
                logger.info(f"Phase 1.75: Calculating symbol metrics (date={final_date})")

            symbol_metrics_result = await calculate_symbol_metrics(
                calculation_date=final_date,
                price_cache=price_cache,
                symbols_override=list(symbols) if scoped_only else None,  # Pass symbols in scoped mode
            )

            logger.info(
                f"Phase 1.75 complete: {symbol_metrics_result['symbols_updated']}/{symbol_metrics_result['symbols_total']} symbols updated"
            )

            if symbol_metrics_result.get('errors'):
                logger.warning(f"Phase 1.75 had {len(symbol_metrics_result['errors'])} errors")

        except Exception as e:
            logger.error(f"Phase 1.75 (Symbol Metrics) error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Store error info for result reporting
            symbol_metrics_result = {
                'success': False,
                'error': str(e),
                'symbols_updated': 0,
                'symbols_total': 0
            }
            # Continue to Phase 2-6 even if symbol metrics fail
            # P&L calculator will calculate returns directly from prices as fallback

        # =============================================================================
        # STEP 3: Run Phases 0, 2-6 for each date (using populated price cache)
        # Phase 1 already completed above, so we skip it in run_daily_batch_sequence
        # =============================================================================
        results = []
        for i, calc_date in enumerate(missing_dates, 1):
            logger.debug(f"Phases 2-6: {calc_date} ({i}/{len(missing_dates)})")

            # Create fresh session for this date
            async with AsyncSessionLocal() as db:
                result = await self._run_phases_2_through_6(
                    db=db,
                    calculation_date=calc_date,
                    portfolio_ids=portfolio_ids,
                    run_sector_analysis=(calc_date == target_date),
                    price_cache=price_cache
                )

                results.append(result)

                # Mark as complete in tracking table
                if result['success']:
                    await self._mark_batch_run_complete(db, calc_date, result)

                # Final commit to ensure all Phase 6 analytics are persisted
                # (analytics_runner commits internally, but we need final commit before context exits)
                await db.commit()
                logger.debug(f"Final commit completed for {calc_date}")

                # Update progress tracker AFTER commit succeeds
                # This ensures crash reporting is accurate - if commit fails,
                # we don't incorrectly count this date as completed
                if result['success']:
                    progress["completed"] += 1
                else:
                    progress["failed"] += 1

        duration = int(asyncio.get_event_loop().time() - start_time)

        success_count = sum(1 for r in results if r['success'])
        failed_count = len(results) - success_count
        logger.info(f"Backfill complete: {success_count}/{len(results)} dates in {duration}s")
        self._sector_analysis_target_date = None

        # Record batch completion (Phase 5 Admin Dashboard)
        overall_success = all(r['success'] for r in results)
        status = "completed" if overall_success else ("partial" if success_count > 0 else "failed")

        # Calculate phase durations from results
        phase_durations = {}
        if symbol_factor_result:
            phase_durations["phase_1_5_symbol_factors"] = symbol_factor_result.get('duration_seconds', 0)
        if symbol_metrics_result:
            phase_durations["phase_1_75_symbol_metrics"] = symbol_metrics_result.get('duration_seconds', 0)
        phase_durations["total_duration"] = duration

        # Collect error summary if any failures
        error_summary = None
        if not overall_success:
            errors = []
            for r in results:
                if not r.get('success') and r.get('errors'):
                    errors.extend(r['errors'])
            if errors:
                error_summary = {
                    "count": len(errors),
                    "types": list(set(e.split(':')[0] for e in errors if ':' in e))[:5],
                    "details": errors[:10]  # First 10 errors only
                }

        record_batch_complete(
            batch_run_id=batch_run_id,
            status=status,
            completed_jobs=success_count,
            failed_jobs=failed_count,
            phase_durations=phase_durations,
            error_summary=error_summary,
        )

        return {
            'success': overall_success,
            'dates_processed': len(missing_dates),
            'duration_seconds': duration,
            'phase_1_5': symbol_factor_result or {'success': False, 'skipped': True},
            'phase_1_75': symbol_metrics_result or {'success': False, 'skipped': True},
            'results': results
        }

    async def run_portfolio_onboarding_backfill(
        self,
        portfolio_id: str,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        DEPRECATED: This is now a wrapper for the unified run_daily_batch_with_backfill().

        Run full backfill for a SINGLE newly onboarded portfolio.

        This method now delegates to run_daily_batch_with_backfill() with:
        - portfolio_id parameter for single-portfolio scoped mode (~40x faster)
        - source="onboarding" for entry point tracking

        The unified function automatically:
        1. Finds the earliest position entry_date for THIS portfolio
        2. Runs Phase 1 (market data) for ONLY portfolio symbols + factor ETFs
        3. Runs Phase 1.5 and 1.75 for ONLY portfolio symbols (scoped mode)
        4. Runs Phases 2-6 for the portfolio

        This is ~40x faster than the old implementation which fetched market data
        for the entire 1,193 symbol universe.

        IMPORTANT: This wrapper handles batch_run_tracker.complete() in a finally
        block to ensure the tracker is always cleared, even on exceptions.
        The caller (portfolios.py) calls batch_run_tracker.start(), so we must
        ensure complete() is called to avoid stuck "running" status.

        Args:
            portfolio_id: UUID string of the portfolio to backfill
            end_date: Date to process up to (defaults to most recent trading day)

        Returns:
            Summary of backfill operation including dates processed and any errors
        """
        from app.batch.batch_run_tracker import batch_run_tracker

        logger.info(f"Portfolio Onboarding Backfill: Delegating to unified function for {portfolio_id}")

        try:
            # Delegate to unified function with single-portfolio mode enabled
            result = await self.run_daily_batch_with_backfill(
                end_date=end_date,
                portfolio_id=portfolio_id,
                source="onboarding",
            )
            return result
        finally:
            # CRITICAL: Always clear batch_run_tracker, even on exception
            # The caller (portfolios.py) calls batch_run_tracker.start()
            # We must call complete() to avoid stuck "running" status in UI
            batch_run_tracker.complete()
            logger.debug("Batch run tracker cleared (onboarding wrapper)")

    async def run_daily_batch_sequence(
        self,
        calculation_date: date,
        portfolio_ids: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
        run_sector_analysis: Optional[bool] = None,
        price_cache: Optional[PriceCache] = None,
        force_onboarding: bool = False,
    ) -> Dict[str, Any]:
        """
        Run 3-phase batch sequence for a single date

        Args:
            calculation_date: Date to process
            portfolio_ids: Specific portfolios (None = all)
            db: Optional database session
            run_sector_analysis: Whether to run sector analysis
            price_cache: Optional price cache
            force_onboarding: If True, run all phases even on historical dates (for onboarding)

        Returns:
            Summary of batch run
        """
        normalized_portfolio_ids = self._normalize_portfolio_ids(portfolio_ids)
        if run_sector_analysis is None:
            if self._sector_analysis_target_date:
                run_sector_analysis = calculation_date == self._sector_analysis_target_date
            else:
                run_sector_analysis = True

        # Generate batch_run_id and record start for history tracking
        batch_run_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        triggered_by = os.environ.get("BATCH_TRIGGERED_BY", "admin")
        record_batch_start(
            batch_run_id=batch_run_id,
            triggered_by=triggered_by,
            total_jobs=1,  # Single-date run = 1 job
        )
        start_time = asyncio.get_event_loop().time()
        result: Dict[str, Any] = {}

        try:
            if db is None:
                analytics_runner.reset_caches()
                self._sector_analysis_target_date = calculation_date
                async with AsyncSessionLocal() as session:
                    result = await self._run_sequence_with_session(
                        session,
                        calculation_date,
                        normalized_portfolio_ids,
                        bool(run_sector_analysis),
                        price_cache,
                        force_onboarding,
                    )
            else:
                result = await self._run_sequence_with_session(
                    db,
                    calculation_date,
                    normalized_portfolio_ids,
                    bool(run_sector_analysis),
                    price_cache,
                    force_onboarding,
                )
            return result
        finally:
            # Clear batch run tracker when batch completes (success or failure)
            from app.batch.batch_run_tracker import batch_run_tracker
            batch_run_tracker.complete()
            if db is None:
                self._sector_analysis_target_date = None

            # Record batch completion to history
            duration = asyncio.get_event_loop().time() - start_time
            status = "completed" if result.get('success') else "failed"
            phase_durations = {"total_duration": round(duration)}
            record_batch_complete(
                batch_run_id=batch_run_id,
                status=status,
                completed_jobs=1 if result.get('success') else 0,
                failed_jobs=0 if result.get('success') else 1,
                phase_durations=phase_durations,
                error_summary={"errors": result.get('errors', [])} if result.get('errors') else None,
            )

    async def _run_sequence_with_session(
        self,
        db: AsyncSession,
        calculation_date: date,
        portfolio_ids: Optional[List[UUID]],
        run_sector_analysis: bool,
        price_cache: Optional[PriceCache] = None,
        force_onboarding: bool = False,
    ) -> Dict[str, Any]:
        """
        Run 9-phase sequence with provided session and optional price cache

        Phases:
            0: Company Profile Sync
            1: Market Data Collection
            1.5: Symbol Factors (NEW - ensures symbols in universe)
            1.75: Symbol Metrics (NEW - pre-calculates returns)
            2: Fundamental Data Collection
            2.5: Cleanup incomplete snapshots
            3: P&L & Snapshots
            4: Position Market Values
            5: Risk Analytics
            6: Factor Analysis

        Args:
            db: Database session
            calculation_date: Date to process
            portfolio_ids: Specific portfolios (None = all)
            run_sector_analysis: Whether to run sector analysis
            price_cache: Optional price cache
            force_onboarding: If True, run all phases even on historical dates
        """

        result: Dict[str, Any] = {
            'success': False,
            'calculation_date': calculation_date,
            'phase_0': {},
            'phase_1': {},
            'phase_1_5': {},
            'phase_1_75': {},
            'phase_2': {},
            'phase_3': {},
            'phase_4': {},
            'phase_5': {},
            'phase_6': {},
            'errors': []
        }
        phase4_result: Dict[str, Any] = {}

        # OPTIMIZATION: Company profiles and fundamentals only needed on current/final date
        # Override for onboarding: force_onboarding=True ensures Phases 0 & 2 run even on weekends
        is_historical = calculation_date < date.today() and not force_onboarding

        # Phase 0: Company Profile Sync (BEFORE all calculations)
        # Only run on final/current date to get fresh beta values, sector, industry
        if not is_historical:
            try:
                self._log_phase_start("phase_0", calculation_date, portfolio_ids)
                phase0_result = await self._sync_company_profiles(
                    db=db,
                    portfolio_ids=portfolio_ids
                )
                result['phase_0'] = phase0_result
                self._log_phase_result("phase_0", phase0_result)

                if not phase0_result.get('success'):
                    logger.warning("Phase 0 (Company Profiles) had errors, continuing to Phase 1")
                    # Continue even if profile sync fails - not critical for calculations

            except Exception as e:
                logger.error(f"Phase 0 (Company Profiles) error: {e}")
                result['errors'].append(f"Phase 0 (Company Profiles) error: {str(e)}")
                # Continue to Phase 1 even if company profiles fail
        else:
            logger.debug(f"Skipping Phase 0 (Company Profiles) for historical date ({calculation_date})")
            result['phase_0'] = {'success': True, 'skipped': True, 'reason': 'historical_date'}

        # Phase 1: Market Data Collection
        try:
            self._log_phase_start("phase_1", calculation_date, portfolio_ids)
            phase1_result = await market_data_collector.collect_daily_market_data(
                calculation_date=calculation_date,
                lookback_days=365,
                db=db,
                portfolio_ids=portfolio_ids,
                skip_company_profiles=True  # Always skip - handled in Phase 0
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

        # =============================================================================
        # Phase 1.5: Calculate Symbol Factors for all symbols
        # This ensures symbols are added to symbol_universe and have factor exposures
        # calculated. Critical for new portfolios onboarded via admin/onboarding flow.
        # =============================================================================
        try:
            from app.calculations.symbol_factors import calculate_universe_factors

            logger.info(f"Phase 1.5: Calculating symbol factors for universe (date={calculation_date})")

            symbol_factor_result = await calculate_universe_factors(
                calculation_date=calculation_date,
                regularization_alpha=1.0,
                calculate_ridge=True,
                calculate_spread=True,
                price_cache=price_cache
            )

            result['phase_1_5'] = symbol_factor_result

            logger.info(
                f"Phase 1.5 complete: {symbol_factor_result['symbols_processed']} symbols, "
                f"Ridge: {symbol_factor_result['ridge_results']['calculated']} calc / "
                f"{symbol_factor_result['ridge_results']['cached']} cached, "
                f"Spread: {symbol_factor_result['spread_results']['calculated']} calc / "
                f"{symbol_factor_result['spread_results']['cached']} cached"
            )

            if symbol_factor_result.get('errors'):
                logger.warning(f"Phase 1.5 had {len(symbol_factor_result['errors'])} errors")

        except Exception as e:
            logger.error(f"Phase 1.5 (Symbol Factors) error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            result['phase_1_5'] = {'success': False, 'error': str(e)}
            # Continue to Phase 1.75 even if symbol factors fail

        # =============================================================================
        # Phase 1.75: Calculate Symbol Metrics (returns, valuations)
        # Pre-calculates returns and metrics for all symbols before P&L calculation.
        # P&L calculator can then lookup returns instead of recalculating per position.
        # =============================================================================
        try:
            from app.services.symbol_metrics_service import calculate_symbol_metrics

            logger.info(f"Phase 1.75: Calculating symbol metrics (date={calculation_date})")

            symbol_metrics_result = await calculate_symbol_metrics(
                calculation_date=calculation_date,
                price_cache=price_cache
            )

            result['phase_1_75'] = symbol_metrics_result

            logger.info(
                f"Phase 1.75 complete: {symbol_metrics_result['symbols_updated']}/{symbol_metrics_result['symbols_total']} symbols updated"
            )

            if symbol_metrics_result.get('errors'):
                logger.warning(f"Phase 1.75 had {len(symbol_metrics_result['errors'])} errors")

        except Exception as e:
            logger.error(f"Phase 1.75 (Symbol Metrics) error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            result['phase_1_75'] = {
                'success': False,
                'error': str(e),
                'symbols_updated': 0,
                'symbols_total': 0
            }
            # Continue to Phase 2 even if symbol metrics fail

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

        # Phase 2.5: Cleanup incomplete snapshots (Phase 2.10 idempotency)
        # Remove stale placeholder snapshots from crashed runs to allow retries
        try:
            from app.calculations.snapshots import cleanup_incomplete_snapshots

            cleaned = await cleanup_incomplete_snapshots(
                db=db,
                age_threshold_hours=1,  # Only delete snapshots older than 1 hour
                portfolio_id=None  # Clean up all portfolios
            )

            if cleaned['incomplete_deleted'] > 0:
                logger.warning(
                    f"[IDEMPOTENCY] Cleaned up {cleaned['incomplete_deleted']} incomplete snapshots "
                    f"before Phase 3 (from crashed batch runs)"
                )
                # Record metric for monitoring
                if hasattr(self, '_record_metric'):
                    self._record_metric("batch_incomplete_snapshots_cleaned", {
                        "count": cleaned['incomplete_deleted']
                    })
        except Exception as e:
            logger.error(f"Phase 2.5 (Cleanup) error: {e}")
            # Non-fatal - continue to Phase 3
            # Incomplete snapshots will block duplicate runs (by design)

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
                if total_positions > 0:
                    missing_ratio = positions_skipped / total_positions
                    missing_ratio_rounded = round(missing_ratio, 4)
                    phase4_result['missing_ratio'] = missing_ratio_rounded

                    if missing_ratio > 0.05:
                        warning_msg = (
                            f"Phase 4 insufficient price coverage: "
                            f"{positions_skipped}/{total_positions} positions missing ({missing_ratio:.1%})"
                        )
                        logger.warning(warning_msg)
                        metric_payload = {
                            'calculation_date': calculation_date.isoformat(),
                            'portfolio_scope': len(portfolio_ids) if portfolio_ids else "all",
                            'total_positions': total_positions,
                            'positions_skipped': positions_skipped,
                            'positions_ignored': positions_ignored,
                            'missing_ratio': missing_ratio_rounded,
                        }
                        record_metric("phase_4_insufficient_coverage", metric_payload)

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

        # Final visibility into missing symbols (if any) once the run is complete
        if phase4_result and phase4_result.get('missing_price_symbols'):
            unique_missing_symbols = sorted(set(phase4_result.get('missing_price_symbols', [])))
            missing_ratio = phase4_result.get('missing_ratio')
            ratio_text = ""
            if isinstance(missing_ratio, (int, float)):
                ratio_text = f" (~{missing_ratio * 100:.2f}% of eligible positions)"
            logger.warning(
                "Final coverage check for %s%s: missing market data for %d symbols: %s",
                calculation_date,
                ratio_text,
                len(unique_missing_symbols),
                ", ".join(unique_missing_symbols),
            )

        # Determine overall success
        # CRITICAL FIX (2025-11-14): Phase 6 (analytics) failures should NOT fail the batch!
        # Phase 3 already committed snapshots and equity - those are the critical operations.
        # Phase 6 is "best effort" analytics that can be re-run later.
        # If we mark the batch as failed, _mark_batch_run_complete() won't be called,
        # causing batch_run_tracking to get out of sync with actual snapshots.
        critical_errors = [e for e in result['errors'] if not e.startswith('Phase 6')]
        result['success'] = len(critical_errors) == 0

        if not result['success']:
            logger.error(f"Batch failed with critical errors: {critical_errors}")
        elif result['errors']:
            logger.warning(f"Batch succeeded with non-critical errors: {result['errors']}")

        return result

    async def _run_phases_2_through_6(
        self,
        db: AsyncSession,
        calculation_date: date,
        portfolio_ids: Optional[List[str]] = None,
        run_sector_analysis: bool = True,
        price_cache: Optional[PriceCache] = None,
    ) -> Dict[str, Any]:
        """
        Run Phases 0, 2-6 for a single date (Phase 1 already completed).

        This is called after all Phase 1 (market data) runs have completed,
        so the price cache is fully populated with all dates including today.

        Args:
            db: Database session
            calculation_date: Date to process
            portfolio_ids: Specific portfolios (None = all)
            run_sector_analysis: Whether to run sector analysis
            price_cache: Populated price cache

        Returns:
            Summary of batch run
        """
        normalized_portfolio_ids = self._normalize_portfolio_ids(portfolio_ids)

        result: Dict[str, Any] = {
            'success': False,
            'calculation_date': calculation_date,
            'phase_0': {},
            'phase_1': {'success': True, 'skipped': False, 'note': 'completed_in_first_pass'},
            'phase_2': {},
            'phase_3': {},
            'phase_4': {},
            'phase_5': {},
            'phase_6': {},
            'errors': []
        }
        phase4_result: Dict[str, Any] = {}

        # OPTIMIZATION: Company profiles and fundamentals only needed on current/final date
        is_historical = calculation_date < date.today()

        # Phase 0: Company Profile Sync (BEFORE all calculations)
        # Only run on final/current date to get fresh beta values, sector, industry
        if not is_historical:
            try:
                self._log_phase_start("phase_0", calculation_date, normalized_portfolio_ids)
                phase0_result = await self._sync_company_profiles(
                    db=db,
                    portfolio_ids=normalized_portfolio_ids
                )
                result['phase_0'] = phase0_result
                self._log_phase_result("phase_0", phase0_result)

                if not phase0_result.get('success'):
                    logger.warning("Phase 0 (Company Profiles) had errors, continuing to Phase 2")

            except Exception as e:
                logger.error(f"Phase 0 (Company Profiles) error: {e}")
                result['errors'].append(f"Phase 0 (Company Profiles) error: {str(e)}")
        else:
            logger.debug(f"Skipping Phase 0 (Company Profiles) for historical date ({calculation_date})")
            result['phase_0'] = {'success': True, 'skipped': True, 'reason': 'historical_date'}

        # Phase 1: SKIPPED - already completed in first pass
        # (result['phase_1'] already set above)

        # Phase 2: Fundamental Data Collection
        # OPTIMIZATION: Only run on current/final date (fundamentals don't change historically)
        if not is_historical:
            try:
                self._log_phase_start("phase_2", calculation_date, normalized_portfolio_ids)
                phase2_fundamentals_result = await fundamentals_collector.collect_fundamentals_data(
                    db=db,
                    portfolio_ids=normalized_portfolio_ids
                )
                result['phase_2'] = phase2_fundamentals_result
                self._log_phase_result("phase_2", phase2_fundamentals_result)

                if not phase2_fundamentals_result.get('success'):
                    logger.warning("Phase 2 (Fundamentals) had errors, continuing to Phase 3")

            except Exception as e:
                logger.error(f"Phase 2 (Fundamentals) error: {e}")
                result['errors'].append(f"Phase 2 (Fundamentals) error: {str(e)}")
        else:
            logger.debug(f"Skipping Phase 2 (Fundamentals) for historical date ({calculation_date})")
            result['phase_2'] = {'success': True, 'skipped': True, 'reason': 'historical_date'}

        # Phase 2.5: Cleanup incomplete snapshots
        try:
            from app.calculations.snapshots import cleanup_incomplete_snapshots

            cleaned = await cleanup_incomplete_snapshots(
                db=db,
                age_threshold_hours=1,
                portfolio_id=None
            )

            if cleaned['incomplete_deleted'] > 0:
                logger.warning(
                    f"[IDEMPOTENCY] Cleaned up {cleaned['incomplete_deleted']} incomplete snapshots "
                    f"before Phase 3 (from crashed batch runs)"
                )
        except Exception as e:
            logger.error(f"Phase 2.5 (Cleanup) error: {e}")

        # Phase 3: P&L & Snapshots
        try:
            self._log_phase_start("phase_3", calculation_date, normalized_portfolio_ids)
            phase3_result = await pnl_calculator.calculate_all_portfolios_pnl(
                calculation_date=calculation_date,
                db=db,
                portfolio_ids=normalized_portfolio_ids,
                price_cache=price_cache
            )
            result['phase_3'] = phase3_result
            self._log_phase_result("phase_3", phase3_result)

            if not phase3_result.get('success'):
                result['errors'].append("Phase 3 (P&L) had errors")

        except Exception as e:
            logger.error(f"Phase 3 (P&L) error: {e}")
            result['errors'].append(f"Phase 3 (P&L) error: {str(e)}")

        # Phase 4: Update Position Market Values
        try:
            self._log_phase_start("phase_4", calculation_date, normalized_portfolio_ids)
            phase4_result = await self._update_all_position_market_values(
                calculation_date=calculation_date,
                db=db,
                portfolio_ids=normalized_portfolio_ids
            )
            result['phase_4'] = phase4_result
            self._log_phase_result("phase_4", phase4_result)

            if not phase4_result.get('success'):
                logger.warning("Phase 4 (Position Updates) had errors, continuing to Phase 5")

        except Exception as e:
            logger.error(f"Phase 4 (Position Updates) error: {e}")
            result['errors'].append(f"Phase 4 (Position Updates) error: {str(e)}")

        # Phase 5: Restore Sector Tags from Company Profiles
        if not is_historical:
            try:
                self._log_phase_start("phase_5", calculation_date, normalized_portfolio_ids)
                phase5_result = await self._restore_all_sector_tags(
                    db=db,
                    portfolio_ids=normalized_portfolio_ids
                )
                result['phase_5'] = phase5_result
                self._log_phase_result("phase_5", phase5_result)

                if not phase5_result.get('success'):
                    logger.warning("Phase 5 (Sector Tags) had errors, continuing to Phase 6")

            except Exception as e:
                logger.error(f"Phase 5 (Sector Tags) error: {e}")
                result['errors'].append(f"Phase 5 (Sector Tags) error: {str(e)}")
        else:
            logger.debug(f"Skipping Phase 5 (Sector Tags) for historical date ({calculation_date})")
            result['phase_5'] = {'success': True, 'skipped': True, 'reason': 'historical_date'}

        # Phase 6: Risk Analytics
        try:
            self._log_phase_start("phase_6", calculation_date, normalized_portfolio_ids)
            phase6_result = await analytics_runner.run_all_portfolios_analytics(
                calculation_date=calculation_date,
                db=db,
                portfolio_ids=normalized_portfolio_ids,
                run_sector_analysis=run_sector_analysis,
                price_cache=price_cache,
            )
            result['phase_6'] = phase6_result
            self._log_phase_result("phase_6", phase6_result)

            if not phase6_result.get('success'):
                result['errors'].append("Phase 6 (Analytics) had errors")

        except Exception as e:
            logger.error(f"Phase 6 (Analytics) error: {e}")
            result['errors'].append(f"Phase 6 (Analytics) error: {str(e)}")

        # Final visibility into missing symbols
        if phase4_result and phase4_result.get('missing_price_symbols'):
            unique_missing_symbols = sorted(set(phase4_result.get('missing_price_symbols', [])))
            logger.warning(
                f"Final coverage check for {calculation_date}: missing market data for "
                f"{len(unique_missing_symbols)} symbols: {', '.join(unique_missing_symbols)}"
            )

        # Determine overall success (Phase 6 failures don't fail the batch)
        critical_errors = [e for e in result['errors'] if not e.startswith('Phase 6')]
        result['success'] = len(critical_errors) == 0

        if not result['success']:
            logger.error(f"Batch failed with critical errors: {critical_errors}")
        elif result['errors']:
            logger.warning(f"Batch succeeded with non-critical errors: {result['errors']}")

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

    async def _sync_company_profiles(
        self,
        db: AsyncSession,
        portfolio_ids: Optional[List[UUID]] = None
    ) -> Dict[str, Any]:
        """
        Sync company profiles for all position symbols (Phase 0).

        This fetches fresh company profile data including beta values, sector, and industry
        from yfinance. Runs BEFORE all calculations to ensure analytics use current data.

        Args:
            db: Database session
            portfolio_ids: Optional list of portfolio IDs to scope positions

        Returns:
            Summary of company profile sync
        """
        from app.services.market_data_service import MarketDataService

        logger.info("Phase 0: Syncing company profiles for all positions")

        try:
            # Get all unique symbols from active positions
            symbols_query = (
                select(Position.symbol)
                .distinct()
                .where(Position.deleted_at.is_(None))
            )
            if portfolio_ids is not None:
                symbols_query = symbols_query.where(Position.portfolio_id.in_(portfolio_ids))

            symbols_result = await db.execute(symbols_query)
            symbols = [row[0] for row in symbols_result.all()]

            logger.info(f"Found {len(symbols)} unique symbols to sync")

            if not symbols:
                return {
                    'success': True,
                    'symbols_attempted': 0,
                    'symbols_successful': 0,
                    'symbols_failed': 0
                }

            # Use market data service to fetch and cache company profiles
            market_data_service = MarketDataService()
            result = await market_data_service.fetch_and_cache_company_profiles(
                db=db,
                symbols=symbols
            )

            logger.info(
                f"Company profile sync complete: "
                f"{result['symbols_successful']}/{result['symbols_attempted']} successful"
            )

            return {
                'success': result['symbols_failed'] < result['symbols_attempted'],
                'symbols_attempted': result['symbols_attempted'],
                'symbols_successful': result['symbols_successful'],
                'symbols_failed': result['symbols_failed'],
                'failed_symbols': result.get('failed_symbols', [])[:10]  # First 10 only
            }

        except Exception as e:
            logger.error(f"Error syncing company profiles: {e}")
            return {
                'success': False,
                'error': str(e),
                'symbols_attempted': 0,
                'symbols_successful': 0,
                'symbols_failed': 0
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
        """
        Get the date of the last successful batch run.

        CRITICAL FIX (2025-11-14): Use the latest SNAPSHOT date, not batch_run_tracking.

        Why: batch_run_tracking records when a batch STARTED, but if run before market
        close (e.g., manually at midnight), no snapshots are created (non-trading hours).
        This causes backfill to skip dates that weren't actually processed.

        Example bug scenario:
        - Manual batch run at midnight Nov 13 → batch_run_tracking.run_date = Nov 13
        - But market hasn't opened → NO snapshots created
        - Next cron run thinks Nov 13 is done → skips to Nov 14
        - Nov 14 snapshot uses Nov 10 equity → corruption!

        Solution: Use the LATEST snapshot date across all portfolios as the true
        "last processed date" since snapshots are only created on actual trading days.
        """
        query = select(PortfolioSnapshot.snapshot_date).order_by(
            desc(PortfolioSnapshot.snapshot_date)
        ).limit(1)

        result = await db.execute(query)
        last_snapshot_date = result.scalar_one_or_none()

        if last_snapshot_date:
            logger.info(f"Last snapshot date found: {last_snapshot_date}")
            return last_snapshot_date

        # Fallback to batch tracking if no snapshots exist (first run ever)
        query_tracking = select(BatchRunTracking).where(
            BatchRunTracking.phase_1_status == 'success'
        ).order_by(desc(BatchRunTracking.run_date)).limit(1)

        result_tracking = await db.execute(query_tracking)
        last_run = result_tracking.scalar_one_or_none()

        if last_run:
            logger.info(f"No snapshots found, using batch tracking: {last_run.run_date}")
            return last_run.run_date

        logger.info("No snapshots or batch tracking found (first run ever)")
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
