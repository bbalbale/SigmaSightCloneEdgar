"""
V2 Symbol Batch Runner

Nightly job that processes ALL symbols in the universe:
1. Phase 0: Company profile sync (sector, industry data)
2. Phase 1: Market data collection (prices from YFinance)
3. Phase 2: Fundamental data (earnings-driven)
4. Phase 3: Factor calculations (betas, exposures)

Key Design Decisions:
- Runs at 9:00 PM ET after market close
- Backfill mode by default (catches up missed dates)
- Writes to BOTH cache AND DB tables (hybrid approach)
- Uses BatchJobType.SYMBOL_BATCH for tracking

Reference: PlanningDocs/V2BatchArchitecture/04-SYMBOL-BATCH-RUNNER.md
"""

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now
from app.core.trading_calendar import (
    get_trading_days_between,
    get_most_recent_trading_day,
    is_trading_day,
)
from app.database import get_async_session, AsyncSessionLocal
from app.models.admin import BatchRunHistory
from app.batch.batch_run_tracker import (
    batch_run_tracker,
    BatchJobType,
    BatchJob,
)

logger = get_logger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# V2 Batch step logging prefix for observability
V2_LOG_PREFIX = "[V2_SYMBOL_BATCH]"

# Maximum dates to backfill in one run (safety limit)
MAX_BACKFILL_DATES = 30


# =============================================================================
# RESULT DATACLASSES
# =============================================================================

@dataclass
class SymbolBatchResult:
    """Result of a single-date symbol batch run."""
    success: bool
    target_date: date
    symbols_processed: int = 0
    prices_fetched: int = 0
    factors_calculated: int = 0
    errors: List[str] = None
    duration_seconds: float = 0.0
    phases: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.phases is None:
            self.phases = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "target_date": self.target_date.isoformat(),
            "symbols_processed": self.symbols_processed,
            "prices_fetched": self.prices_fetched,
            "factors_calculated": self.factors_calculated,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "phases": self.phases,
        }


@dataclass
class BackfillResult:
    """Result of a multi-date backfill run."""
    success: bool
    dates_processed: int
    dates_failed: int
    results: List[SymbolBatchResult] = None
    total_duration_seconds: float = 0.0

    def __post_init__(self):
        if self.results is None:
            self.results = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "dates_processed": self.dates_processed,
            "dates_failed": self.dates_failed,
            "results": [r.to_dict() for r in self.results],
            "total_duration_seconds": self.total_duration_seconds,
        }


# =============================================================================
# MAIN ENTRY POINTS
# =============================================================================

async def run_symbol_batch(
    target_date: Optional[date] = None,
    backfill: bool = True,
) -> Dict[str, Any]:
    """
    Run symbol batch with optional backfill for missed dates.

    This is the main entry point for the V2 symbol batch cron job.

    Args:
        target_date: End date to process (defaults to most recent trading day)
        backfill: If True, find and process all missed dates since last run

    Returns:
        Dict with batch results including dates processed and any errors

    Example:
        # Normal cron run (backfills if needed)
        result = await run_symbol_batch()

        # Manual run for specific date
        result = await run_symbol_batch(date(2026, 1, 10), backfill=False)
    """
    start_time = datetime.now()
    job_id = str(uuid4())

    # Determine target date
    if target_date is None:
        target_date = get_most_recent_trading_day()

    logger.info(f"{V2_LOG_PREFIX} Starting symbol batch (job_id={job_id}, target={target_date}, backfill={backfill})")

    # Register job with tracker
    job = BatchJob(
        job_id=job_id,
        job_type=BatchJobType.SYMBOL_BATCH,
        started_at=utc_now(),
        triggered_by="v2_cron",
        target_date=target_date.isoformat(),
    )

    if not batch_run_tracker.start_job_sync(job):
        logger.warning(f"{V2_LOG_PREFIX} Symbol batch already running, aborting")
        return {
            "success": False,
            "error": "symbol_batch_already_running",
            "message": "Another symbol batch is already in progress",
        }

    try:
        # Ensure factor definitions exist before calculating
        await ensure_factor_definitions()

        if backfill:
            result = await _run_with_backfill(target_date, job_id)
        else:
            # Single date mode
            single_result = await _run_symbol_batch_for_date(target_date)
            await record_symbol_batch_completion(target_date, single_result, job_id)
            result = BackfillResult(
                success=single_result.success,
                dates_processed=1 if single_result.success else 0,
                dates_failed=0 if single_result.success else 1,
                results=[single_result],
                total_duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        # Mark job complete
        status = "completed" if result.success else "failed"
        batch_run_tracker.complete_job_sync(BatchJobType.SYMBOL_BATCH, status)

        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"{V2_LOG_PREFIX} Symbol batch complete: "
            f"dates={result.dates_processed}, failed={result.dates_failed}, "
            f"duration={total_duration:.1f}s"
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Symbol batch failed: {e}", exc_info=True)
        batch_run_tracker.complete_job_sync(
            BatchJobType.SYMBOL_BATCH,
            status="failed",
            error_message=str(e)
        )
        return {
            "success": False,
            "error": "symbol_batch_exception",
            "message": str(e),
        }


async def _run_with_backfill(target_date: date, job_id: str) -> BackfillResult:
    """
    Run symbol batch with automatic backfill for missed dates.

    Args:
        target_date: End date to process
        job_id: Job ID for tracking

    Returns:
        BackfillResult with all processed dates
    """
    start_time = datetime.now()

    # Find last successful symbol batch date
    last_run = await get_last_symbol_batch_date()

    if last_run:
        # Get all trading days between last_run + 1 and target_date
        start_date = last_run + timedelta(days=1)
        missing_dates = get_trading_days_between(start_date, target_date)
        logger.info(
            f"{V2_LOG_PREFIX} Backfill mode: last_run={last_run}, "
            f"missing_dates={len(missing_dates)}"
        )
    else:
        # First run ever - just process target_date
        missing_dates = [target_date] if is_trading_day(target_date) else []
        logger.info(f"{V2_LOG_PREFIX} First run ever, processing target_date only")

    # Safety limit
    if len(missing_dates) > MAX_BACKFILL_DATES:
        logger.warning(
            f"{V2_LOG_PREFIX} Limiting backfill from {len(missing_dates)} to {MAX_BACKFILL_DATES} dates"
        )
        missing_dates = missing_dates[-MAX_BACKFILL_DATES:]

    if not missing_dates:
        logger.info(f"{V2_LOG_PREFIX} No dates to process, already caught up")
        return BackfillResult(
            success=True,
            dates_processed=0,
            dates_failed=0,
            total_duration_seconds=0.0,
        )

    # Process each missing date
    results = []
    dates_failed = 0

    for calc_date in missing_dates:
        logger.info(f"{V2_LOG_PREFIX} Processing date {calc_date} ({len(results)+1}/{len(missing_dates)})")

        try:
            result = await _run_symbol_batch_for_date(calc_date)
            results.append(result)

            # Record completion for this date
            await record_symbol_batch_completion(calc_date, result, job_id)

            if not result.success:
                dates_failed += 1

        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} Failed to process {calc_date}: {e}", exc_info=True)
            dates_failed += 1
            results.append(SymbolBatchResult(
                success=False,
                target_date=calc_date,
                errors=[str(e)],
            ))

    total_duration = (datetime.now() - start_time).total_seconds()

    return BackfillResult(
        success=dates_failed == 0,
        dates_processed=len(results) - dates_failed,
        dates_failed=dates_failed,
        results=results,
        total_duration_seconds=total_duration,
    )


# =============================================================================
# SINGLE DATE PROCESSING
# =============================================================================

async def _run_symbol_batch_for_date(calc_date: date) -> SymbolBatchResult:
    """
    Run symbol batch for a single date.

    Phases:
    1. Phase 0: Company profile sync
    2. Phase 1: Market data collection (prices)
    3. Phase 2: Fundamental data (if earnings window)
    4. Phase 3: Factor calculations

    Args:
        calc_date: Date to process

    Returns:
        SymbolBatchResult with phase details
    """
    start_time = datetime.now()
    phases = {}
    errors = []
    symbols_processed = 0
    prices_fetched = 0
    factors_calculated = 0

    try:
        # Get symbols to process
        symbols = await _get_symbols_to_process()
        symbols_processed = len(symbols)
        logger.info(f"{V2_LOG_PREFIX} Found {symbols_processed} symbols to process for {calc_date}")

        # Phase 0: Company profiles (only on final date of backfill)
        phase_start = datetime.now()
        try:
            phase_0_result = await _run_phase_0_company_profiles(symbols, calc_date)
            phases["phase_0_company_profiles"] = {
                "success": True,
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
                "profiles_synced": phase_0_result.get("synced", 0),
            }
        except Exception as e:
            logger.warning(f"{V2_LOG_PREFIX} Phase 0 error (non-fatal): {e}")
            phases["phase_0_company_profiles"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
            }

        # Phase 1: Market data
        phase_start = datetime.now()
        try:
            phase_1_result = await _run_phase_1_market_data(symbols, calc_date)
            prices_fetched = phase_1_result.get("prices_fetched", 0)
            phases["phase_1_market_data"] = {
                "success": True,
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
                "prices_fetched": prices_fetched,
            }
        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} Phase 1 error: {e}", exc_info=True)
            errors.append(f"Phase 1 market data: {e}")
            phases["phase_1_market_data"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
            }

        # Phase 2: Fundamentals (earnings-driven)
        phase_start = datetime.now()
        try:
            phase_2_result = await _run_phase_2_fundamentals(symbols, calc_date)
            phases["phase_2_fundamentals"] = {
                "success": True,
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
                "symbols_updated": phase_2_result.get("updated", 0),
            }
        except Exception as e:
            logger.warning(f"{V2_LOG_PREFIX} Phase 2 error (non-fatal): {e}")
            phases["phase_2_fundamentals"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
            }

        # Phase 3: Factor calculations
        phase_start = datetime.now()
        try:
            phase_3_result = await _run_phase_3_factors(symbols, calc_date)
            factors_calculated = phase_3_result.get("calculated", 0)
            phases["phase_3_factors"] = {
                "success": True,
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
                "factors_calculated": factors_calculated,
            }
        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} Phase 3 error: {e}", exc_info=True)
            errors.append(f"Phase 3 factors: {e}")
            phases["phase_3_factors"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now() - phase_start).total_seconds(),
            }

        # Determine overall success
        critical_phases_ok = (
            phases.get("phase_1_market_data", {}).get("success", False) and
            phases.get("phase_3_factors", {}).get("success", False)
        )

        return SymbolBatchResult(
            success=critical_phases_ok,
            target_date=calc_date,
            symbols_processed=symbols_processed,
            prices_fetched=prices_fetched,
            factors_calculated=factors_calculated,
            errors=errors,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            phases=phases,
        )

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Unexpected error for {calc_date}: {e}", exc_info=True)
        return SymbolBatchResult(
            success=False,
            target_date=calc_date,
            errors=[str(e)],
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            phases=phases,
        )


# =============================================================================
# PHASE IMPLEMENTATIONS (Step 6-7 will fill these in)
# =============================================================================

async def _get_symbols_to_process() -> List[str]:
    """
    Get all symbols that need processing.

    Sources:
    1. All symbols from active positions
    2. Symbols in symbol_universe
    3. Factor ETF symbols (SPY, TLT, etc.)

    Returns:
        Deduplicated list of uppercase symbols
    """
    # TODO: Step 6 will implement this
    # For now, return empty list (placeholder)
    from app.models.positions import Position
    from app.models.users import Portfolio
    from app.models.symbol_analytics import SymbolUniverse

    symbols = set()

    async with get_async_session() as db:
        # Get symbols from active positions
        result = await db.execute(
            select(Position.symbol)
            .join(Portfolio, Portfolio.id == Position.portfolio_id)
            .where(
                and_(
                    Portfolio.deleted_at.is_(None),
                    Position.exit_date.is_(None),
                )
            )
            .distinct()
        )
        position_symbols = [row[0].upper() for row in result.fetchall() if row[0]]
        symbols.update(position_symbols)

        # Get symbols from symbol_universe
        result = await db.execute(
            select(SymbolUniverse.symbol).where(SymbolUniverse.is_active == True)
        )
        universe_symbols = [row[0].upper() for row in result.fetchall() if row[0]]
        symbols.update(universe_symbols)

    # Add factor ETF symbols
    factor_etfs = ["SPY", "TLT", "GLD", "USO", "UUP"]
    symbols.update(factor_etfs)

    logger.info(f"{V2_LOG_PREFIX} Found {len(symbols)} unique symbols to process")
    return list(symbols)


async def _run_phase_0_company_profiles(symbols: List[str], calc_date: date) -> Dict[str, Any]:
    """
    Phase 0: Sync company profiles for all symbols.

    Fetches sector, industry, market cap, etc. from YahooQuery/FMP APIs.
    Uses existing market_data_collector._fetch_company_profiles() method.

    Args:
        symbols: List of symbols to sync
        calc_date: Calculation date

    Returns:
        Dict with sync results
    """
    from app.batch.market_data_collector import market_data_collector

    logger.info(f"{V2_LOG_PREFIX} Phase 0: Company profile sync for {len(symbols)} symbols")

    try:
        async with get_async_session() as db:
            results = await market_data_collector._fetch_company_profiles(
                db=db,
                symbols=set(symbols)
            )

        synced = results.get("symbols_successful", 0)
        failed = results.get("symbols_failed", 0)
        skipped = results.get("symbols_skipped", 0) + results.get("symbols_etf_skipped", 0)

        logger.info(
            f"{V2_LOG_PREFIX} Phase 0 complete: synced={synced}, failed={failed}, skipped={skipped}"
        )

        return {
            "synced": synced,
            "failed": failed,
            "skipped": skipped,
            "details": results,
        }

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Phase 0 error: {e}", exc_info=True)
        raise


async def _run_phase_1_market_data(symbols: List[str], calc_date: date) -> Dict[str, Any]:
    """
    Phase 1: Fetch market data (prices) for all symbols.

    Uses existing market_data_collector.collect_daily_market_data() method.
    Provider priority: YFinance → YahooQuery → Polygon → FMP
    Writes to market_data_cache table.

    Args:
        symbols: List of symbols to fetch
        calc_date: Calculation date

    Returns:
        Dict with fetch results
    """
    from app.batch.market_data_collector import market_data_collector
    from app.config import settings

    logger.info(f"{V2_LOG_PREFIX} Phase 1: Market data collection for {len(symbols)} symbols")

    try:
        # Use existing market_data_collector with 365-day lookback for vol analysis
        # Skip company profiles since Phase 0 handles that
        result = await market_data_collector.collect_daily_market_data(
            calculation_date=calc_date,
            lookback_days=365,
            db=None,  # Let it create its own session
            portfolio_ids=None,  # Process all symbols
            skip_company_profiles=True,  # Phase 0 handles profiles
            scoped_only=False,  # Full universe for nightly batch
        )

        prices_fetched = result.get("symbols_fetched", 0)
        symbols_with_data = result.get("symbols_with_data", 0)
        coverage_pct = result.get("data_coverage_pct", 0)
        fetch_mode = result.get("fetch_mode", "unknown")

        logger.info(
            f"{V2_LOG_PREFIX} Phase 1 complete: fetched={prices_fetched}, "
            f"total_with_data={symbols_with_data}, coverage={coverage_pct}%, mode={fetch_mode}"
        )

        return {
            "prices_fetched": prices_fetched,
            "symbols_with_data": symbols_with_data,
            "coverage_pct": float(coverage_pct),
            "fetch_mode": fetch_mode,
            "provider_breakdown": result.get("provider_breakdown", {}),
            "missing_symbols": result.get("missing_symbols", []),
        }

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Phase 1 error: {e}", exc_info=True)
        raise


async def _run_phase_2_fundamentals(symbols: List[str], calc_date: date) -> Dict[str, Any]:
    """
    Phase 2: Collect fundamental data if within earnings window.

    Uses existing fundamentals_collector with earnings-driven logic.
    Only fetches if 3+ days after earnings date to ensure data is available.
    Reduces API calls by 80-90% compared to fetching every day.

    Args:
        symbols: List of symbols to check
        calc_date: Calculation date

    Returns:
        Dict with collection results
    """
    from app.batch.fundamentals_collector import fundamentals_collector

    logger.info(f"{V2_LOG_PREFIX} Phase 2: Fundamentals collection (earnings-driven)")

    try:
        # Use existing fundamentals_collector
        # It handles smart fetching based on earnings dates
        result = await fundamentals_collector.collect_fundamentals_data(
            db=None,  # Let it create its own session
            portfolio_ids=None,  # Process all symbols
        )

        symbols_fetched = result.get("symbols_fetched", 0)
        symbols_skipped = result.get("symbols_skipped", 0)
        symbols_evaluated = result.get("symbols_evaluated", 0)
        errors = result.get("errors", [])

        logger.info(
            f"{V2_LOG_PREFIX} Phase 2 complete: fetched={symbols_fetched}, "
            f"skipped={symbols_skipped}, evaluated={symbols_evaluated}"
        )

        if errors:
            logger.warning(f"{V2_LOG_PREFIX} Phase 2 errors: {errors[:5]}")  # Log first 5 errors

        return {
            "updated": symbols_fetched,
            "skipped": symbols_skipped,
            "evaluated": symbols_evaluated,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Phase 2 error: {e}", exc_info=True)
        raise


async def _run_phase_3_factors(symbols: List[str], calc_date: date) -> Dict[str, Any]:
    """
    Phase 3: Calculate factor exposures for all equity symbols.

    Uses existing calculate_universe_factors() which:
    - Calculates Ridge factors (6 style factors) via regression
    - Calculates Spread factors (4 long-short factor spreads)
    - Uses smart caching (skips symbols already calculated for this date)
    - Writes results to symbol_factor_exposures table
    - Uses parallel batch processing for speed

    Args:
        symbols: List of symbols to calculate
        calc_date: Calculation date

    Returns:
        Dict with calculation results
    """
    from app.calculations.symbol_factors import calculate_universe_factors

    logger.info(f"{V2_LOG_PREFIX} Phase 3: Factor calculations for {len(symbols)} symbols")

    try:
        # Use existing universe factor calculation
        # Pass symbols for scoped mode (V2 symbol batch knows which symbols to process)
        result = await calculate_universe_factors(
            calculation_date=calc_date,
            regularization_alpha=1.0,  # Default L2 penalty for Ridge
            calculate_ridge=True,
            calculate_spread=True,
            price_cache=None,  # Will create its own if needed
            symbols=symbols,  # Use our pre-computed symbol list
        )

        # Extract results
        ridge_results = result.get("ridge_results", {})
        spread_results = result.get("spread_results", {})

        ridge_calculated = ridge_results.get("calculated", 0)
        ridge_cached = ridge_results.get("cached", 0)
        ridge_failed = ridge_results.get("failed", 0)

        spread_calculated = spread_results.get("calculated", 0)
        spread_cached = spread_results.get("cached", 0)
        spread_failed = spread_results.get("failed", 0)

        total_calculated = ridge_calculated + spread_calculated
        total_cached = ridge_cached + spread_cached
        total_failed = ridge_failed + spread_failed

        logger.info(
            f"{V2_LOG_PREFIX} Phase 3 complete: calculated={total_calculated}, "
            f"cached={total_cached}, failed={total_failed}"
        )
        logger.info(
            f"{V2_LOG_PREFIX}   Ridge: calc={ridge_calculated}, cached={ridge_cached}, fail={ridge_failed}"
        )
        logger.info(
            f"{V2_LOG_PREFIX}   Spread: calc={spread_calculated}, cached={spread_cached}, fail={spread_failed}"
        )

        errors = result.get("errors", [])
        if errors:
            logger.warning(f"{V2_LOG_PREFIX} Phase 3 errors: {errors[:5]}")  # Log first 5

        return {
            "calculated": total_calculated,
            "cached": total_cached,
            "failed": total_failed,
            "ridge_results": ridge_results,
            "spread_results": spread_results,
            "errors": errors,
        }

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Phase 3 error: {e}", exc_info=True)
        raise


# =============================================================================
# TRACKING AND UTILITIES
# =============================================================================

async def ensure_factor_definitions():
    """
    Ensure factor definitions exist before calculating exposures.

    This is critical because factor writes will fail if definitions don't exist.
    Uses existing seed_factors() which is idempotent.
    """
    from app.db.seed_factors import seed_factors

    logger.info(f"{V2_LOG_PREFIX} Verifying factor definitions...")
    async with AsyncSessionLocal() as db:
        await seed_factors(db)
        await db.commit()
    logger.info(f"{V2_LOG_PREFIX} Factor definitions verified/seeded")


async def get_last_symbol_batch_date() -> Optional[date]:
    """
    Get the most recent successful symbol batch date.

    Queries BatchRunHistory for SYMBOL_BATCH jobs with status='completed'.

    Returns:
        Date of last successful symbol batch, or None if never run
    """
    async with get_async_session() as db:
        # Look for completed symbol batch runs
        result = await db.execute(
            select(BatchRunHistory)
            .where(
                and_(
                    BatchRunHistory.status == "completed",
                    # Look for V2 symbol batch jobs by checking triggered_by or error_summary
                    # We store batch_type in error_summary.batch_type for V2 jobs
                    BatchRunHistory.triggered_by == "v2_cron",
                )
            )
            .order_by(desc(BatchRunHistory.completed_at))
            .limit(1)
        )
        last_run = result.scalar_one_or_none()

        if last_run and last_run.completed_at:
            return last_run.completed_at.date()

    return None


async def record_symbol_batch_completion(
    calc_date: date,
    result: SymbolBatchResult,
    job_id: str,
) -> None:
    """
    Record symbol batch completion to BatchRunHistory.

    Args:
        calc_date: Date that was processed
        result: SymbolBatchResult with phase details
        job_id: Job ID for correlation
    """
    async with get_async_session() as db:
        history = BatchRunHistory(
            batch_run_id=job_id,
            triggered_by="v2_cron",
            started_at=utc_now() - timedelta(seconds=result.duration_seconds),
            completed_at=utc_now(),
            status="completed" if result.success else "failed",
            total_jobs=result.symbols_processed,
            completed_jobs=result.prices_fetched,
            failed_jobs=len(result.errors),
            phase_durations={
                phase_name: phase_data.get("duration_seconds", 0)
                for phase_name, phase_data in result.phases.items()
            },
            error_summary={
                "batch_type": "symbol_batch",
                "calc_date": calc_date.isoformat(),
                "errors": result.errors,
            } if result.errors else {
                "batch_type": "symbol_batch",
                "calc_date": calc_date.isoformat(),
            },
        )
        db.add(history)
        await db.commit()

    logger.info(f"{V2_LOG_PREFIX} Recorded completion for {calc_date} (job_id={job_id})")
