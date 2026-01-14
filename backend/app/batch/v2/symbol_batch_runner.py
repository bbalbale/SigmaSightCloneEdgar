"""
V2 Symbol Batch Runner

Nightly job that processes ALL symbols in the universe:
1. Phase 0: Daily valuation metrics (PE, beta, 52w range, market cap) - batch via yahooquery
2. Phase 1: Market data collection (prices from YFinance)
3. Phase 2: SKIPPED - Fundamentals (see NextSteps.md Section 6)
4. Phase 3: Factor calculations (betas, exposures)

Key Design Decisions:
- Runs at 9:00 PM ET after market close
- Backfill mode by default (catches up missed dates)
- Writes to BOTH cache AND DB tables (hybrid approach)
- Uses BatchJobType.SYMBOL_BATCH for tracking

Reference: PlanningDocs/V2BatchArchitecture/04-SYMBOL-BATCH-RUNNER.md
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now
from app.core.trading_calendar import (
    get_trading_days_between,
    get_most_recent_trading_day,
    get_most_recent_completed_trading_day,
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
    import sys
    start_time = datetime.now()
    job_id = str(uuid4())

    # Determine target date (use completed trading day to respect market hours)
    if target_date is None:
        target_date = get_most_recent_completed_trading_day()

    print(f"{V2_LOG_PREFIX} Starting symbol batch (job_id={job_id[:8]}, target={target_date}, backfill={backfill})")
    sys.stdout.flush()
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
        print(f"{V2_LOG_PREFIX} Symbol batch already running, aborting")
        sys.stdout.flush()
        logger.warning(f"{V2_LOG_PREFIX} Symbol batch already running, aborting")
        return {
            "success": False,
            "error": "symbol_batch_already_running",
            "message": "Another symbol batch is already in progress",
        }

    try:
        # Ensure factor definitions exist before calculating
        print(f"{V2_LOG_PREFIX} Ensuring factor definitions...")
        sys.stdout.flush()
        await ensure_factor_definitions()
        print(f"{V2_LOG_PREFIX} Factor definitions ready")
        sys.stdout.flush()

        if backfill:
            print(f"{V2_LOG_PREFIX} Running with backfill...")
            sys.stdout.flush()
            result = await _run_with_backfill(target_date, job_id)
        else:
            # Single date mode
            print(f"{V2_LOG_PREFIX} Running single date mode for {target_date}...")
            sys.stdout.flush()
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
    Run symbol batch using DATA-DRIVEN approach.

    Instead of checking batch_run_history, we check actual data:
    - Which symbols are missing prices for target_date?
    - If none missing, we're caught up
    - If some missing, process them

    This is more resilient than date-based backfill because:
    - Self-healing: If a batch fails halfway, next run catches what's missing
    - Timezone-proof: No UTC vs ET confusion
    - More accurate: Checks actual data, not batch history records

    Args:
        target_date: Date to check and process
        job_id: Job ID for tracking

    Returns:
        BackfillResult with processing results
    """
    import sys
    from app.batch.v2.data_checks import get_symbols_missing_prices

    start_time = datetime.now()

    print(f"{V2_LOG_PREFIX} DATA-DRIVEN CHECK: Checking if symbols have prices for {target_date}...")
    sys.stdout.flush()

    # Check actual data - which symbols are missing prices?
    symbols_missing, all_symbols = await get_symbols_missing_prices(target_date)

    if not symbols_missing:
        print(f"{V2_LOG_PREFIX} All {len(all_symbols)} symbols have prices for {target_date} - nothing to do")
        sys.stdout.flush()
        logger.info(f"{V2_LOG_PREFIX} All symbols have prices for {target_date}, skipping")
        return BackfillResult(
            success=True,
            dates_processed=0,
            dates_failed=0,
            total_duration_seconds=(datetime.now() - start_time).total_seconds(),
        )

    # Some symbols are missing prices - need to process
    print(f"{V2_LOG_PREFIX} {len(symbols_missing)}/{len(all_symbols)} symbols missing prices for {target_date}")
    print(f"{V2_LOG_PREFIX} Missing symbols (first 10): {symbols_missing[:10]}")
    sys.stdout.flush()
    logger.info(
        f"{V2_LOG_PREFIX} {len(symbols_missing)} symbols missing prices for {target_date}, processing..."
    )

    # Process the target date (this will fetch prices for all symbols)
    # TODO: Future optimization - only fetch missing symbols
    results = []
    dates_failed = 0

    try:
        print(f"{V2_LOG_PREFIX} Processing {target_date}...")
        sys.stdout.flush()

        result = await _run_symbol_batch_for_date(target_date)
        results.append(result)

        # Record completion for this date
        await record_symbol_batch_completion(target_date, result, job_id)

        if not result.success:
            dates_failed += 1

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} Failed to process {target_date}: {e}", exc_info=True)
        dates_failed += 1
        results.append(SymbolBatchResult(
            success=False,
            target_date=target_date,
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
    import sys
    start_time = datetime.now()
    phases = {}
    errors = []
    symbols_processed = 0
    prices_fetched = 0
    factors_calculated = 0

    try:
        # Get symbols to process
        print(f"{V2_LOG_PREFIX} Getting symbols to process...")
        sys.stdout.flush()
        symbols = await _get_symbols_to_process(calc_date)
        symbols_processed = len(symbols)
        print(f"{V2_LOG_PREFIX} Found {symbols_processed} symbols to process for {calc_date}")
        sys.stdout.flush()
        logger.info(f"{V2_LOG_PREFIX} Found {symbols_processed} symbols to process for {calc_date}")

        # Phase 0: Daily valuations (PE, beta, 52w range, market cap)
        # Can be skipped via SKIP_PHASE0_VALUATIONS env var when yahooquery is slow/unreliable
        if settings.SKIP_PHASE0_VALUATIONS:
            print(f"{V2_LOG_PREFIX}   Phase 0: Daily valuations... SKIPPED (SKIP_PHASE0_VALUATIONS=true)")
            sys.stdout.flush()
            phases["phase_0_daily_valuations"] = {
                "success": True,
                "skipped": True,
                "reason": "SKIP_PHASE0_VALUATIONS=true",
            }
        else:
            print(f"{V2_LOG_PREFIX}   Phase 0: Daily valuations...")
            sys.stdout.flush()
            phase_start = datetime.now()
            try:
                phase_0_result = await _run_phase_0_company_profiles(symbols, calc_date)
                print(f"{V2_LOG_PREFIX}   Phase 0 complete: {phase_0_result.get('synced', 0)} valuations updated")
                sys.stdout.flush()
                phases["phase_0_daily_valuations"] = {
                    "success": True,
                    "duration_seconds": (datetime.now() - phase_start).total_seconds(),
                    "valuations_updated": phase_0_result.get("synced", 0),
                    "updated": phase_0_result.get("updated", 0),
                    "created": phase_0_result.get("created", 0),
                }
            except Exception as e:
                logger.warning(f"{V2_LOG_PREFIX} Phase 0 error (non-fatal): {e}")
                phases["phase_0_daily_valuations"] = {
                    "success": False,
                    "error": str(e),
                    "duration_seconds": (datetime.now() - phase_start).total_seconds(),
                }

        # Phase 1: Market data
        print(f"{V2_LOG_PREFIX}   Phase 1: Market data...")
        sys.stdout.flush()
        phase_start = datetime.now()
        try:
            phase_1_result = await _run_phase_1_market_data(symbols, calc_date)
            prices_fetched = phase_1_result.get("prices_fetched", 0)
            print(f"{V2_LOG_PREFIX}   Phase 1 complete: {prices_fetched} prices fetched")
            sys.stdout.flush()
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

        # Phase 2: Fundamentals - SKIPPED for now
        # See PlanningDocs/V2BatchArchitecture/NextSteps.md Section 6
        # Fundamentals collection has numeric overflow issues and needs optimization
        print(f"{V2_LOG_PREFIX}   Phase 2: Fundamentals... SKIPPED (see NextSteps.md)")
        sys.stdout.flush()
        phases["phase_2_fundamentals"] = {
            "success": True,
            "skipped": True,
            "reason": "Moved to NextSteps - needs optimization",
        }

        # Initialize unified cache after Phase 1 (loads prices from market_data_cache)
        # This provides 300x speedup for Phase 3 factor calculations
        print(f"{V2_LOG_PREFIX}   Initializing price cache (200 days)...")
        sys.stdout.flush()
        from app.cache.symbol_cache import symbol_cache
        await symbol_cache.initialize_async(target_date=calc_date)
        print(f"{V2_LOG_PREFIX}   Cache ready: {len(symbol_cache._symbols_loaded)} symbols")
        sys.stdout.flush()

        # Phase 3: Factor calculations
        print(f"{V2_LOG_PREFIX}   Phase 3: Factor calculations...")
        sys.stdout.flush()
        phase_start = datetime.now()
        try:
            phase_3_result = await _run_phase_3_factors(symbols, calc_date, symbol_cache._price_cache)
            factors_calculated = phase_3_result.get("calculated", 0)
            print(f"{V2_LOG_PREFIX}   Phase 3 complete: {factors_calculated} calculated")
            sys.stdout.flush()

            # Refresh factor cache with newly calculated factors
            # This ensures Phase 5 aggregation and user onboarding use fresh data
            print(f"{V2_LOG_PREFIX}   Refreshing factor cache...")
            sys.stdout.flush()
            await symbol_cache.refresh_factors(calc_date)
            print(f"{V2_LOG_PREFIX}   Factor cache refreshed")
            sys.stdout.flush()

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
# HELPER FUNCTIONS
# =============================================================================

import re

# OCC Option Symbol Pattern: SYMBOL + YYMMDD + C/P + STRIKE (8 digits with implied decimal)
# Examples: SPY250919C00460000, AAPL250815P00200000
OPTION_TICKER_PATTERN = re.compile(r'^([A-Z]+)(\d{6})([CP])(\d{8})$')

# Internal/Private asset ID pattern (e.g., EQ5D6A2D8F - generated identifiers)
INTERNAL_ID_PATTERN = re.compile(r'^EQ[A-F0-9]{8,}$', re.IGNORECASE)


def parse_option_expiry(symbol: str) -> Optional[date]:
    """
    Parse option ticker to extract expiration date.

    OCC format: SYMBOL + YYMMDD + C/P + STRIKE
    Example: SPY250919C00460000 -> expires 2025-09-19

    Returns:
        Expiration date if valid option ticker, None otherwise
    """
    match = OPTION_TICKER_PATTERN.match(symbol.upper())
    if not match:
        return None

    date_str = match.group(2)  # YYMMDD
    try:
        year = 2000 + int(date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def is_expired_option(symbol: str, as_of_date: date) -> bool:
    """
    Check if a symbol is an expired option.

    Args:
        symbol: Ticker symbol to check
        as_of_date: Date to check expiry against (typically today)

    Returns:
        True if symbol is an option that has expired, False otherwise
    """
    expiry = parse_option_expiry(symbol)
    if expiry is None:
        return False  # Not an option ticker
    return expiry < as_of_date


def filter_expired_options(symbols: List[str], as_of_date: date) -> tuple[List[str], List[str]]:
    """
    Filter out expired options from a list of symbols.

    Returns:
        Tuple of (valid_symbols, expired_symbols)
    """
    valid = []
    expired = []
    for symbol in symbols:
        if is_expired_option(symbol, as_of_date):
            expired.append(symbol)
        else:
            valid.append(symbol)
    return valid, expired


def is_private_asset_symbol(symbol: str) -> bool:
    """
    Detect if a symbol represents a private/alternative asset.

    Private assets don't have market data and can't be processed for factor analysis.
    Detection heuristics:
    1. Contains underscore (standard equity tickers don't have underscores)
       - Examples: HOME_EQUITY, FO_PRIVATE_CREDIT, BX_PRIVATE_EQUITY, MONEY_MARKET
    2. Matches internal ID pattern (EQ + hex digits)
       - Examples: EQ5D6A2D8F
    3. Known private asset prefixes

    Args:
        symbol: Ticker symbol to check

    Returns:
        True if symbol appears to be a private/alternative asset
    """
    symbol_upper = symbol.upper()

    # Rule 1: Contains underscore - standard equity tickers don't have underscores
    # This catches: HOME_EQUITY, RENTAL_SFH, FO_PRIVATE_CREDIT, BX_PRIVATE_EQUITY,
    #               MONEY_MARKET, TWO_SIGMA_FUND, A16Z_VC_FUND, TREASURY_BILLS, etc.
    if '_' in symbol:
        return True

    # Rule 2: Internal ID pattern (EQ + hex digits)
    # This catches generated identifiers like EQ5D6A2D8F
    if INTERNAL_ID_PATTERN.match(symbol_upper):
        return True

    return False


def filter_private_assets(symbols: List[str]) -> tuple[List[str], List[str]]:
    """
    Filter out private/alternative asset symbols from a list.

    Returns:
        Tuple of (public_symbols, private_symbols)
    """
    public = []
    private = []
    for symbol in symbols:
        if is_private_asset_symbol(symbol):
            private.append(symbol)
        else:
            public.append(symbol)
    return public, private


# =============================================================================
# PHASE IMPLEMENTATIONS (Step 6-7 will fill these in)
# =============================================================================

async def _get_symbols_to_process(calc_date: date = None) -> List[str]:
    """
    Get all symbols that need processing for factor calculations.

    Sources:
    1. All symbols from active positions (PUBLIC only)
    2. Symbols in symbol_universe
    3. Factor ETF symbols (SPY, TLT, etc.)

    Excludes:
    - PRIVATE positions (no market data - see NextSteps.md #7)
    - OPTIONS positions (need Greeks not factor calcs, expire)
    - Expired options (detected by parsing ticker)
    - Private asset symbols (detected by underscore pattern)
    - Inactive symbols from symbol_universe

    Returns:
        Deduplicated list of uppercase symbols
    """
    from app.models.positions import Position
    from app.models.users import Portfolio
    from app.models.symbol_analytics import SymbolUniverse

    if calc_date is None:
        calc_date = date.today()

    symbols = set()
    inactive_symbols = set()

    async with get_async_session() as db:
        # First, get inactive symbols to exclude (delisted, renamed, etc.)
        result = await db.execute(
            select(SymbolUniverse.symbol).where(SymbolUniverse.is_active == False)
        )
        inactive_symbols = {row[0].upper() for row in result.fetchall() if row[0]}
        if inactive_symbols:
            logger.info(f"{V2_LOG_PREFIX} Excluding {len(inactive_symbols)} inactive symbols: {inactive_symbols}")

        # Get symbols from active positions - PUBLIC investment class only
        # PRIVATE: No market data (custom identifiers like BX_PRIVATE_EQUITY)
        # OPTIONS: Need Greeks calculations, not factor regressions
        # NULL: Treat as unknown, will be filtered by pattern detection below
        result = await db.execute(
            select(Position.symbol)
            .join(Portfolio, Portfolio.id == Position.portfolio_id)
            .where(
                and_(
                    Portfolio.deleted_at.is_(None),
                    Position.exit_date.is_(None),
                    # Only include PUBLIC positions explicitly
                    # NULL and other classes will be filtered by pattern detection
                    or_(
                        Position.investment_class == "PUBLIC",
                        Position.investment_class.is_(None),  # Check pattern later
                    ),
                )
            )
            .distinct()
        )
        position_symbols = [row[0].upper() for row in result.fetchall() if row[0]]
        symbols.update(position_symbols)
        logger.info(f"{V2_LOG_PREFIX} Collected {len(position_symbols)} symbols from positions")

        # Get symbols from symbol_universe (active only)
        result = await db.execute(
            select(SymbolUniverse.symbol).where(SymbolUniverse.is_active == True)
        )
        universe_symbols = [row[0].upper() for row in result.fetchall() if row[0]]
        symbols.update(universe_symbols)

    # Remove inactive symbols from the set
    symbols -= inactive_symbols

    # Add factor ETF symbols
    factor_etfs = ["SPY", "TLT", "GLD", "USO", "UUP"]
    symbols.update(factor_etfs)

    # Filter out private/alternative asset symbols by pattern
    # This catches symbols with underscores (HOME_EQUITY, FO_PRIVATE_CREDIT, etc.)
    # and internal IDs (EQ5D6A2D8F) that slipped through due to NULL investment_class
    symbol_list = list(symbols)
    public_symbols, private_symbols = filter_private_assets(symbol_list)
    if private_symbols:
        logger.info(
            f"{V2_LOG_PREFIX} Filtered out {len(private_symbols)} private/alternative symbols: "
            f"{private_symbols[:5]}{'...' if len(private_symbols) > 5 else ''}"
        )

    # Filter out any expired options that slipped through
    valid_symbols, expired = filter_expired_options(public_symbols, calc_date)
    if expired:
        logger.info(f"{V2_LOG_PREFIX} Filtered out {len(expired)} expired options: {expired[:5]}{'...' if len(expired) > 5 else ''}")

    logger.info(f"{V2_LOG_PREFIX} Found {len(valid_symbols)} unique public symbols to process")
    return valid_symbols


async def _run_phase_0_company_profiles(symbols: List[str], calc_date: date) -> Dict[str, Any]:
    """
    Phase 0: Fetch daily valuation metrics for all symbols.

    Uses yahooquery batch API to efficiently fetch:
    - pe_ratio, forward_pe, beta
    - week_52_high, week_52_low
    - market_cap, dividend_yield

    Performance: ~5 minutes for 1250 symbols (vs 30+ min with individual calls)

    Optimization: Skips symbols that already have fresh data (updated today).
    This makes historical recalculations nearly instant.

    Note: Full company profile sync (sector, industry, etc.) is handled separately
    as documented in PlanningDocs/V2BatchArchitecture/NextSteps.md

    Args:
        symbols: List of symbols to sync
        calc_date: Calculation date

    Returns:
        Dict with sync results
    """
    from app.services.valuation_batch_service import valuation_batch_service
    from app.models.market_data import CompanyProfile
    from sqlalchemy import select, and_, func
    from datetime import datetime, timedelta

    logger.info(f"{V2_LOG_PREFIX} Phase 0: Daily valuation metrics for {len(symbols)} symbols")

    try:
        # Check which symbols already have fresh data (updated within last 24 hours)
        # This makes historical recalculations nearly instant
        async with get_async_session() as db:
            freshness_threshold = datetime.utcnow() - timedelta(hours=24)
            stmt = select(CompanyProfile.symbol).where(
                and_(
                    CompanyProfile.symbol.in_(symbols),
                    CompanyProfile.last_updated >= freshness_threshold,
                    CompanyProfile.beta.isnot(None)  # Has valuation data
                )
            )
            result = await db.execute(stmt)
            fresh_symbols = {row[0] for row in result.fetchall()}

        # Only fetch stale symbols
        stale_symbols = [s for s in symbols if s not in fresh_symbols]

        if not stale_symbols:
            logger.info(f"{V2_LOG_PREFIX} Phase 0: All {len(symbols)} symbols have fresh data, skipping fetch")
            return {
                "synced": len(symbols),
                "updated": 0,
                "created": 0,
                "failed": 0,
                "skipped_fresh": len(fresh_symbols),
            }

        logger.info(f"{V2_LOG_PREFIX} Phase 0: {len(fresh_symbols)} fresh, fetching {len(stale_symbols)} stale symbols")

        # Fetch valuation metrics in batch (efficient - ~5 min for 1250 symbols)
        valuations = await valuation_batch_service.fetch_daily_valuations(stale_symbols)

        # Update company_profiles table with valuation data
        async with get_async_session() as db:
            update_result = await valuation_batch_service.update_company_profiles(
                db=db,
                valuations=valuations,
            )

        synced = update_result.get("total_processed", 0) + len(fresh_symbols)
        failed = update_result.get("failed", 0)
        updated = update_result.get("updated", 0)
        created = update_result.get("created", 0)

        logger.info(
            f"{V2_LOG_PREFIX} Phase 0 complete: synced={synced} (updated={updated}, created={created}, fresh={len(fresh_symbols)}), failed={failed}"
        )

        return {
            "synced": synced,
            "updated": updated,
            "created": created,
            "failed": failed,
            "skipped_fresh": len(fresh_symbols),
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
    import sys
    from app.batch.market_data_collector import market_data_collector
    from app.config import settings

    print(f"[PHASE1] Starting market data collection for {len(symbols)} symbols...")
    print(f"[PHASE1] Lookback: 365 days, Date: {calc_date}")
    sys.stdout.flush()
    logger.info(f"{V2_LOG_PREFIX} Phase 1: Market data collection for {len(symbols)} symbols")

    try:
        # Use existing market_data_collector with 365-day lookback for vol analysis
        # Skip company profiles since Phase 0 handles that
        print(f"[PHASE1] Calling market_data_collector.collect_daily_market_data()...")
        sys.stdout.flush()

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
        provider_breakdown = result.get("provider_breakdown", {})

        print(f"[PHASE1] Complete: {prices_fetched} fetched, {symbols_with_data} with data")
        print(f"[PHASE1] Coverage: {coverage_pct}%, Mode: {fetch_mode}")
        if provider_breakdown:
            print(f"[PHASE1] Providers: {provider_breakdown}")
        sys.stdout.flush()

        logger.info(
            f"{V2_LOG_PREFIX} Phase 1 complete: fetched={prices_fetched}, "
            f"total_with_data={symbols_with_data}, coverage={coverage_pct}%, mode={fetch_mode}"
        )

        return {
            "prices_fetched": prices_fetched,
            "symbols_with_data": symbols_with_data,
            "coverage_pct": float(coverage_pct),
            "fetch_mode": fetch_mode,
            "provider_breakdown": provider_breakdown,
            "missing_symbols": result.get("missing_symbols", []),
        }

    except Exception as e:
        print(f"[PHASE1] ERROR: {e}")
        sys.stdout.flush()
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


async def _run_phase_3_factors(symbols: List[str], calc_date: date, price_cache=None) -> Dict[str, Any]:
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
        price_cache: Optional PriceCache for 300x faster price lookups

    Returns:
        Dict with calculation results
    """
    from app.calculations.symbol_factors import calculate_universe_factors

    logger.info(f"{V2_LOG_PREFIX} Phase 3: Factor calculations for {len(symbols)} symbols")

    # Print logging for Railway visibility
    print(f"[PHASE3] Starting factor calculations for {len(symbols)} symbols...")
    print(f"[PHASE3] Date: {calc_date}, Ridge=True, Spread=True, cache={'enabled' if price_cache else 'disabled'}")
    sys.stdout.flush()

    try:
        print(f"[PHASE3] Calling calculate_universe_factors()...")
        sys.stdout.flush()

        # Use existing universe factor calculation
        # Pass symbols for scoped mode (V2 symbol batch knows which symbols to process)
        result = await calculate_universe_factors(
            calculation_date=calc_date,
            regularization_alpha=1.0,  # Default L2 penalty for Ridge
            calculate_ridge=True,
            calculate_spread=True,
            price_cache=price_cache,  # V2: Use unified cache for 300x speedup
            symbols=symbols,  # Use our pre-computed symbol list
        )

        # Extract results
        ridge_results = result.get("ridge_results", {})
        spread_results = result.get("spread_results", {})
        market_beta_results = result.get("market_beta_results", {})
        ir_beta_results = result.get("ir_beta_results", {})
        provider_beta_results = result.get("provider_beta_results", {})

        ridge_calculated = ridge_results.get("calculated", 0)
        ridge_cached = ridge_results.get("cached", 0)
        ridge_failed = ridge_results.get("failed", 0)

        spread_calculated = spread_results.get("calculated", 0)
        spread_cached = spread_results.get("cached", 0)
        spread_failed = spread_results.get("failed", 0)

        market_beta_calculated = market_beta_results.get("calculated", 0)
        market_beta_cached = market_beta_results.get("cached", 0)
        market_beta_failed = market_beta_results.get("failed", 0)

        ir_beta_calculated = ir_beta_results.get("calculated", 0)
        ir_beta_cached = ir_beta_results.get("cached", 0)
        ir_beta_failed = ir_beta_results.get("failed", 0)

        provider_beta_calculated = provider_beta_results.get("calculated", 0)
        provider_beta_cached = provider_beta_results.get("cached", 0)
        provider_beta_failed = provider_beta_results.get("failed", 0)

        total_calculated = ridge_calculated + spread_calculated + market_beta_calculated + ir_beta_calculated + provider_beta_calculated
        total_cached = ridge_cached + spread_cached + market_beta_cached + ir_beta_cached + provider_beta_cached
        total_failed = ridge_failed + spread_failed + market_beta_failed + ir_beta_failed + provider_beta_failed

        # Print logging for Railway visibility
        print(f"[PHASE3] Complete: calculated={total_calculated}, cached={total_cached}, failed={total_failed}")
        print(f"[PHASE3] Ridge: calc={ridge_calculated}, cached={ridge_cached}, fail={ridge_failed}")
        print(f"[PHASE3] Spread: calc={spread_calculated}, cached={spread_cached}, fail={spread_failed}")
        print(f"[PHASE3] Market Beta: calc={market_beta_calculated}, cached={market_beta_cached}, fail={market_beta_failed}")
        print(f"[PHASE3] IR Beta: calc={ir_beta_calculated}, cached={ir_beta_cached}, fail={ir_beta_failed}")
        print(f"[PHASE3] Provider Beta: calc={provider_beta_calculated}, cached={provider_beta_cached}, fail={provider_beta_failed}")
        sys.stdout.flush()

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
        logger.info(
            f"{V2_LOG_PREFIX}   Market Beta: calc={market_beta_calculated}, cached={market_beta_cached}, fail={market_beta_failed}"
        )
        logger.info(
            f"{V2_LOG_PREFIX}   IR Beta: calc={ir_beta_calculated}, cached={ir_beta_cached}, fail={ir_beta_failed}"
        )
        logger.info(
            f"{V2_LOG_PREFIX}   Provider Beta: calc={provider_beta_calculated}, cached={provider_beta_cached}, fail={provider_beta_failed}"
        )

        errors = result.get("errors", [])
        if errors:
            print(f"[PHASE3] Errors ({len(errors)} total): {errors[:3]}")  # Show first 3
            sys.stdout.flush()
            logger.warning(f"{V2_LOG_PREFIX} Phase 3 errors: {errors[:5]}")  # Log first 5

        return {
            "calculated": total_calculated,
            "cached": total_cached,
            "failed": total_failed,
            "ridge_results": ridge_results,
            "spread_results": spread_results,
            "market_beta_results": market_beta_results,
            "ir_beta_results": ir_beta_results,
            "provider_beta_results": provider_beta_results,
            "errors": errors,
        }

    except Exception as e:
        print(f"[PHASE3] ERROR: {e}")
        sys.stdout.flush()
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

    IMPORTANT: Uses calc_date from error_summary (US Eastern date that was processed),
    NOT completed_at.date() which is a UTC date. This prevents timezone issues where
    a batch completing at 9 PM ET on Jan 13 shows as Jan 14 in UTC.

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

        if last_run:
            # Use calc_date from error_summary (US Eastern date that was processed)
            # This avoids UTC vs ET timezone issues
            error_summary = last_run.error_summary or {}
            calc_date_str = error_summary.get("calc_date")
            if calc_date_str:
                return date.fromisoformat(calc_date_str)

            # Fallback to completed_at.date() for backwards compatibility
            # (old runs without calc_date in error_summary)
            if last_run.completed_at:
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


# =============================================================================
# SCOPED SYMBOL PROCESSING (FOR ONBOARDING)
# =============================================================================

async def run_symbol_batch_for_symbols(
    symbols: List[str],
    target_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Run symbol batch phases for specific symbols only.

    Used during onboarding when portfolio contains unknown symbols.
    Runs Phase 0 (valuations), Phase 1 (prices), Phase 3 (factors).

    This is a SCOPED version of the nightly batch - processes only
    the provided symbols instead of the full universe.

    Args:
        symbols: List of symbols to process
        target_date: Calculation date (defaults to most recent trading day)

    Returns:
        Dict with processing results per phase
    """
    import time
    start_time = time.time()

    if target_date is None:
        target_date = get_most_recent_completed_trading_day()

    logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Processing {len(symbols)} symbols for {target_date}")

    result = {
        "success": True,
        "symbols_requested": len(symbols),
        "symbols_processed": 0,
        "target_date": target_date.isoformat(),
        "phases": {},
        "errors": [],
    }

    if not symbols:
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] No symbols to process")
        return result

    # Filter out private assets (HOME_EQUITY, FO_*, etc.)
    public_symbols, private_symbols = filter_private_assets(symbols)

    if private_symbols:
        logger.info(
            f"{V2_LOG_PREFIX} [ONBOARDING] Filtered {len(private_symbols)} private assets: "
            f"{private_symbols[:5]}{'...' if len(private_symbols) > 5 else ''}"
        )

    if not public_symbols:
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] No public symbols after filtering")
        result["symbols_processed"] = 0
        return result

    # Filter out expired options
    valid_symbols, expired_symbols = filter_expired_options(public_symbols, target_date)
    if expired_symbols:
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Filtered {len(expired_symbols)} expired options")

    if not valid_symbols:
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] No valid symbols after filtering")
        result["symbols_processed"] = 0
        return result

    try:
        # Phase 0: Daily valuations (PE, beta, 52w range, market cap)
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 0: Daily valuations for {len(valid_symbols)} symbols...")
        phase_start = time.time()
        try:
            phase_0_result = await _run_phase_0_for_symbols(valid_symbols, target_date)
            result["phases"]["phase_0_valuations"] = {
                "success": True,
                "duration_seconds": round(time.time() - phase_start, 2),
                **phase_0_result,
            }
            logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 0 complete: {phase_0_result.get('synced', 0)} valuations")
        except Exception as e:
            logger.warning(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 0 error (non-fatal): {e}")
            result["phases"]["phase_0_valuations"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": round(time.time() - phase_start, 2),
            }

        # Phase 1: Market data collection (365-day lookback for factor calculations)
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 1: Market data for {len(valid_symbols)} symbols...")
        phase_start = time.time()
        try:
            phase_1_result = await _run_phase_1_for_symbols(valid_symbols, target_date)
            result["phases"]["phase_1_market_data"] = {
                "success": True,
                "duration_seconds": round(time.time() - phase_start, 2),
                **phase_1_result,
            }
            logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 1 complete: {phase_1_result.get('prices_fetched', 0)} prices")
        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 1 error: {e}", exc_info=True)
            result["phases"]["phase_1_market_data"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": round(time.time() - phase_start, 2),
            }
            result["errors"].append(f"Phase 1: {e}")

        # Initialize cache after Phase 1 (needed for Phase 3)
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Initializing price cache...")
        from app.cache.symbol_cache import symbol_cache
        await symbol_cache.initialize_async(target_date=target_date)

        # Phase 3: Factor calculations
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 3: Factor calculations for {len(valid_symbols)} symbols...")
        phase_start = time.time()
        try:
            phase_3_result = await _run_phase_3_factors(valid_symbols, target_date, symbol_cache._price_cache)
            result["phases"]["phase_3_factors"] = {
                "success": True,
                "duration_seconds": round(time.time() - phase_start, 2),
                **phase_3_result,
            }
            logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 3 complete: {phase_3_result.get('calculated', 0)} factors")
        except Exception as e:
            logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 3 error: {e}", exc_info=True)
            result["phases"]["phase_3_factors"] = {
                "success": False,
                "error": str(e),
                "duration_seconds": round(time.time() - phase_start, 2),
            }
            result["errors"].append(f"Phase 3: {e}")

        # Add symbols to symbol_universe (so they're "known" for future onboarding)
        await _add_symbols_to_universe(valid_symbols)

        # Refresh factor cache (so Phase 5 aggregation uses fresh data)
        logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Refreshing factor cache...")
        await symbol_cache.refresh_factors(target_date)

        # Determine overall success
        phase_1_ok = result["phases"].get("phase_1_market_data", {}).get("success", False)
        phase_3_ok = result["phases"].get("phase_3_factors", {}).get("success", False)
        result["success"] = phase_1_ok and phase_3_ok
        result["symbols_processed"] = len(valid_symbols)

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Unexpected error: {e}", exc_info=True)
        result["success"] = False
        result["errors"].append(str(e))

    result["duration_seconds"] = round(time.time() - start_time, 2)
    logger.info(
        f"{V2_LOG_PREFIX} [ONBOARDING] Complete: success={result['success']}, "
        f"symbols={result['symbols_processed']}, duration={result['duration_seconds']}s"
    )

    return result


async def _run_phase_0_for_symbols(symbols: List[str], calc_date: date) -> Dict[str, Any]:
    """
    Phase 0: Fetch daily valuation metrics for specific symbols.

    Uses existing valuation_batch_service.fetch_daily_valuations().

    Args:
        symbols: List of symbols to process
        calc_date: Calculation date

    Returns:
        Dict with sync results
    """
    from app.services.valuation_batch_service import valuation_batch_service

    logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 0: Valuations for {len(symbols)} symbols")

    try:
        # Fetch valuation metrics in batch
        valuations = await valuation_batch_service.fetch_daily_valuations(symbols)

        # Update company_profiles table with valuation data
        async with get_async_session() as db:
            update_result = await valuation_batch_service.update_company_profiles(
                db=db,
                valuations=valuations,
            )

        return {
            "synced": update_result.get("total_processed", 0),
            "updated": update_result.get("updated", 0),
            "created": update_result.get("created", 0),
            "failed": update_result.get("failed", 0),
        }

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 0 error: {e}", exc_info=True)
        raise


async def _run_phase_1_for_symbols(symbols: List[str], calc_date: date) -> Dict[str, Any]:
    """
    Phase 1: Fetch market data (prices) for specific symbols.

    Uses existing market_data_service.fetch_historical_data_hybrid().

    Args:
        symbols: List of symbols to process
        calc_date: Calculation date

    Returns:
        Dict with fetch results
    """
    from app.services.market_data_service import MarketDataService
    from app.models.market_data import MarketDataCache
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from datetime import timedelta

    logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 1: Market data for {len(symbols)} symbols")

    market_data_service = MarketDataService()

    # 365-day lookback for factor calculations
    start_date = calc_date - timedelta(days=365)
    end_date = calc_date

    try:
        # Fetch prices using existing provider chain (YFinance → YahooQuery → Polygon → FMP)
        fetched_data = await market_data_service.fetch_historical_data_hybrid(
            symbols, start_date, end_date
        )

        prices_fetched = len(fetched_data)
        records_stored = 0

        # Store in market_data_cache using batch upsert
        if fetched_data:
            async with get_async_session() as db:
                for symbol, price_data in fetched_data.items():
                    if not price_data:
                        continue

                    # Prepare records for upsert
                    records = []
                    for row in price_data:
                        records.append({
                            "symbol": symbol,
                            "date": row.get("date"),
                            "open": row.get("open"),
                            "high": row.get("high"),
                            "low": row.get("low"),
                            "close": row.get("close"),
                            "volume": row.get("volume"),
                            "adjusted_close": row.get("adjusted_close") or row.get("close"),
                        })

                    if records:
                        # Batch upsert
                        stmt = pg_insert(MarketDataCache).values(records)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["symbol", "date"],
                            set_={
                                "open": stmt.excluded.open,
                                "high": stmt.excluded.high,
                                "low": stmt.excluded.low,
                                "close": stmt.excluded.close,
                                "volume": stmt.excluded.volume,
                                "adjusted_close": stmt.excluded.adjusted_close,
                            }
                        )
                        await db.execute(stmt)
                        records_stored += len(records)

                await db.commit()

        logger.info(
            f"{V2_LOG_PREFIX} [ONBOARDING] Phase 1 complete: "
            f"fetched={prices_fetched}, stored={records_stored}"
        )

        return {
            "prices_fetched": prices_fetched,
            "records_stored": records_stored,
        }

    except Exception as e:
        logger.error(f"{V2_LOG_PREFIX} [ONBOARDING] Phase 1 error: {e}", exc_info=True)
        raise


async def _add_symbols_to_universe(symbols: List[str]) -> None:
    """
    Add symbols to symbol_universe table.

    Uses upsert to handle existing symbols gracefully.

    Args:
        symbols: List of symbols to add
    """
    from app.models.symbol_analytics import SymbolUniverse
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    if not symbols:
        return

    logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Adding {len(symbols)} symbols to universe")

    async with get_async_session() as db:
        records = [
            {
                "symbol": symbol.upper(),
                "asset_type": "equity",
                "is_active": True,
                "first_seen_date": date.today(),
                "last_seen_date": date.today(),
            }
            for symbol in symbols
        ]

        stmt = pg_insert(SymbolUniverse).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "last_seen_date": date.today(),
                "is_active": True,
            }
        )
        await db.execute(stmt)
        await db.commit()

    logger.info(f"{V2_LOG_PREFIX} [ONBOARDING] Added/updated {len(symbols)} symbols in universe")
