"""
Test Symbol Factor Calculation Timing

Runs the symbol factor and metrics calculations for a historical date
to measure performance with the new optimizations.

Usage:
    # From backend directory with Railway DATABASE_URL:
    uv run python scripts/test_factor_timing.py --db-url "postgresql+asyncpg://..."

    # Or specify a date:
    uv run python scripts/test_factor_timing.py --date 2025-12-18 --db-url "postgresql+asyncpg://..."
"""
import asyncio
import argparse
import os
import time
from datetime import date, datetime, timedelta

# Setup path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Note: app imports are done inside run_timing_test() AFTER DATABASE_URL is set


async def run_timing_test(calculation_date: date):
    """Run factor and metrics calculations and time each phase."""

    # Import app modules AFTER DATABASE_URL is set
    from app.database import AsyncSessionLocal
    from app.cache.price_cache import PriceCache
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    print(f"\n{'='*70}")
    print(f"SYMBOL FACTOR TIMING TEST - {calculation_date}")
    print(f"{'='*70}\n")

    results = {
        'calculation_date': calculation_date.isoformat(),
        'phases': {}
    }

    total_start = time.time()

    # =========================================================================
    # STEP 1: Load Price Cache (simulates batch orchestrator behavior)
    # =========================================================================
    print("STEP 1: Loading price cache for full universe...")
    step1_start = time.time()

    price_cache = None
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select, and_, distinct
        from app.models.positions import Position
        from app.models.market_data import MarketDataCache

        # Get position symbols
        pos_stmt = select(distinct(Position.symbol)).where(
            and_(
                Position.deleted_at.is_(None),
                Position.symbol.isnot(None),
                Position.symbol != '',
                Position.investment_class.in_(['PUBLIC', 'OPTIONS'])
            )
        )
        pos_result = await db.execute(pos_stmt)
        position_symbols = {row[0] for row in pos_result.all()}

        # Get universe symbols from market_data_cache
        cache_stmt = select(distinct(MarketDataCache.symbol)).where(
            and_(
                MarketDataCache.symbol.isnot(None),
                MarketDataCache.symbol != ''
            )
        )
        cache_result = await db.execute(cache_stmt)
        universe_symbols = {row[0] for row in cache_result.all()}

        # Factor ETFs
        factor_etf_symbols = {'VUG', 'VTV', 'MTUM', 'QUAL', 'IWM', 'SPY', 'USMV', 'TLT'}

        # Union all
        all_symbols = position_symbols.union(universe_symbols).union(factor_etf_symbols)

        print(f"   Symbols to load: {len(all_symbols)} (positions: {len(position_symbols)}, universe: {len(universe_symbols)})")

        # Load price cache
        price_cache = PriceCache()
        cache_start = calculation_date - timedelta(days=400)  # Extra buffer for regression
        loaded_count = await price_cache.load_date_range(
            db=db,
            symbols=all_symbols,
            start_date=cache_start,
            end_date=calculation_date
        )

        print(f"   Prices loaded: {loaded_count:,}")
        print(f"   Cache stats: {price_cache.get_stats()}")

    step1_duration = time.time() - step1_start
    results['phases']['price_cache_load'] = {
        'duration_seconds': round(step1_duration, 2),
        'symbols': len(all_symbols),
        'prices_loaded': loaded_count
    }
    print(f"   ⏱️  Duration: {step1_duration:.1f}s\n")

    # =========================================================================
    # STEP 2: Run Symbol Factor Calculations (Phase 1.5)
    # =========================================================================
    print("STEP 2: Running Symbol Factor Calculations (Phase 1.5)...")
    print(f"   Parameters: BATCH_SIZE=50, MAX_CONCURRENT_BATCHES=8")
    step2_start = time.time()

    from app.calculations.symbol_factors import calculate_universe_factors

    factor_result = await calculate_universe_factors(
        calculation_date=calculation_date,
        regularization_alpha=1.0,
        calculate_ridge=True,
        calculate_spread=True,
        price_cache=price_cache
    )

    step2_duration = time.time() - step2_start
    results['phases']['symbol_factors'] = {
        'duration_seconds': round(step2_duration, 2),
        'symbols_processed': factor_result.get('symbols_processed', 0),
        'ridge': factor_result.get('ridge_results', {}),
        'spread': factor_result.get('spread_results', {}),
        'errors': len(factor_result.get('errors', []))
    }

    print(f"   Symbols processed: {factor_result.get('symbols_processed', 0)}")
    print(f"   Ridge: {factor_result.get('ridge_results', {})}")
    print(f"   Spread: {factor_result.get('spread_results', {})}")
    if factor_result.get('errors'):
        print(f"   Errors: {len(factor_result['errors'])} (first 3: {factor_result['errors'][:3]})")
    print(f"   ⏱️  Duration: {step2_duration:.1f}s\n")

    # =========================================================================
    # STEP 3: Run Symbol Metrics Calculations (Phase 1.75)
    # =========================================================================
    print("STEP 3: Running Symbol Metrics Calculations (Phase 1.75)...")
    step3_start = time.time()

    from app.services.symbol_metrics_service import calculate_all_symbol_metrics

    async with AsyncSessionLocal() as db:
        metrics_result = await calculate_all_symbol_metrics(
            db=db,
            calculation_date=calculation_date,
            price_cache=price_cache
        )

    step3_duration = time.time() - step3_start
    results['phases']['symbol_metrics'] = {
        'duration_seconds': round(step3_duration, 2),
        'symbols_processed': metrics_result.get('symbols_processed', 0),
        'records_upserted': metrics_result.get('records_upserted', 0),
        'errors': len(metrics_result.get('errors', []))
    }

    print(f"   Symbols processed: {metrics_result.get('symbols_processed', 0)}")
    print(f"   Records upserted: {metrics_result.get('records_upserted', 0)}")
    if metrics_result.get('errors'):
        print(f"   Errors: {len(metrics_result['errors'])}")
    print(f"   ⏱️  Duration: {step3_duration:.1f}s\n")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    total_duration = time.time() - total_start
    results['total_duration_seconds'] = round(total_duration, 2)

    print(f"{'='*70}")
    print("TIMING SUMMARY")
    print(f"{'='*70}")
    print(f"   Price Cache Load:    {step1_duration:6.1f}s")
    print(f"   Symbol Factors:      {step2_duration:6.1f}s")
    print(f"   Symbol Metrics:      {step3_duration:6.1f}s")
    print(f"   {'─'*30}")
    print(f"   TOTAL:               {total_duration:6.1f}s ({total_duration/60:.1f} minutes)")
    print(f"{'='*70}\n")

    return results


def main():
    parser = argparse.ArgumentParser(description='Test symbol factor calculation timing')
    parser.add_argument(
        '--date',
        type=str,
        default='2025-12-18',
        help='Calculation date (YYYY-MM-DD format, default: 2025-12-18)'
    )
    parser.add_argument(
        '--db-url',
        type=str,
        default=None,
        help='Database URL (overrides DATABASE_URL env var)'
    )
    args = parser.parse_args()

    # Set DATABASE_URL if provided via argument
    if args.db_url:
        os.environ['DATABASE_URL'] = args.db_url
        print(f"Using provided DATABASE_URL")
    elif not os.environ.get('DATABASE_URL'):
        print("Error: DATABASE_URL not set. Use --db-url or set DATABASE_URL env var.")
        sys.exit(1)

    # Parse date
    try:
        calc_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    except ValueError:
        print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
        sys.exit(1)

    # Run the test
    results = asyncio.run(run_timing_test(calc_date))

    # Output JSON results for parsing
    import json
    print("\nJSON Results:")
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
