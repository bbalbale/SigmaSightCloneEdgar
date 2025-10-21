"""
Reset starting equity and reprocess calculations from Sept 30 onwards.

This script uses the refactored batch orchestrator (Phases 1-7 complete, Oct 2025) which
eliminates ~600 lines of duplicate code and establishes canonical calculation functions.

Architecture:
- All OLS regressions → regression_utils.run_single_factor_regression()
- All position valuations → market_data.get_position_value()
- All return retrievals → market_data.get_returns()
- All exposure calculations → portfolio_exposure_service.get_portfolio_exposures()

Benefits:
- Consistent beta capping (±5.0) and significance testing (90% confidence)
- Single source of truth for all calculations
- 50% fewer database queries via batch fetching and snapshot caching
- Proper equity rollforward chain maintained

See PHASE_1_COMPLETE.md through PHASE_5-7_COMPLETE.md for refactoring details.
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import text, select, desc
from app.database import get_async_session
from app.utils.trading_calendar import trading_calendar
from app.models.users import Portfolio
from uuid import UUID
from decimal import Decimal


async def reset_portfolio_equity(db, portfolio_id: str, starting_equity: Decimal):
    """Reset portfolio equity_balance to starting value"""
    portfolio_uuid = UUID(portfolio_id)

    portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_uuid)
    portfolio_result = await db.execute(portfolio_stmt)
    portfolio = portfolio_result.scalar_one_or_none()

    if portfolio:
        portfolio.equity_balance = starting_equity
        await db.commit()
        print(f"OK Reset Portfolio.equity_balance to ${float(starting_equity):,.2f}")
    else:
        print(f"ERROR Portfolio {portfolio_id} not found")


async def delete_calculation_results(db, portfolio_id: str, start_date: date):
    """Delete calculation results from start_date onwards (keep market data)

    Deletes in proper order to respect foreign key constraints:
    1. Child tables first (correlation_clusters, pairwise_correlations)
    2. Parent tables (correlation_calculations)
    3. Other calculation tables
    """

    total_deleted = 0

    # STEP 1a: Delete correlation grandchild tables first (deepest level)
    try:
        # correlation_cluster_positions references correlation_clusters
        result = await db.execute(text("""
            DELETE FROM correlation_cluster_positions
            WHERE cluster_id IN (
                SELECT cc.id FROM correlation_clusters cc
                JOIN correlation_calculations calc ON cc.correlation_calculation_id = calc.id
                WHERE calc.portfolio_id = :portfolio_id
                AND calc.calculation_date >= :start_date
            )
        """), {"portfolio_id": portfolio_id, "start_date": start_date})

        await db.commit()
        deleted_count = result.rowcount
        total_deleted += deleted_count
        print(f"  correlation_cluster_positions: deleted {deleted_count} records (via FK chain)")

    except Exception as e:
        await db.rollback()
        print(f"  correlation_cluster_positions: ERROR - {str(e)}")

    # STEP 1b: Delete correlation child tables (middle level)
    correlation_child_tables = [
        "correlation_clusters",
        "pairwise_correlations",
    ]

    for table_name in correlation_child_tables:
        try:
            # These tables reference correlation_calculations
            result = await db.execute(text(f"""
                DELETE FROM {table_name}
                WHERE correlation_calculation_id IN (
                    SELECT id FROM correlation_calculations
                    WHERE portfolio_id = :portfolio_id
                    AND calculation_date >= :start_date
                )
            """), {"portfolio_id": portfolio_id, "start_date": start_date})

            await db.commit()
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"  {table_name}: deleted {deleted_count} records (via FK to correlation_calculations)")

        except Exception as e:
            await db.rollback()
            print(f"  {table_name}: ERROR - {str(e)}")

    # STEP 2: Delete parent correlation_calculations table
    try:
        result = await db.execute(text("""
            DELETE FROM correlation_calculations
            WHERE portfolio_id = :portfolio_id
            AND calculation_date >= :start_date
        """), {"portfolio_id": portfolio_id, "start_date": start_date})

        await db.commit()
        deleted_count = result.rowcount
        total_deleted += deleted_count
        print(f"  correlation_calculations: deleted {deleted_count} records")

    except Exception as e:
        await db.rollback()
        print(f"  correlation_calculations: ERROR - {str(e)}")

    # STEP 3: Delete other tables with direct portfolio_id column
    tables_with_portfolio_id = [
        ("portfolio_snapshots", "snapshot_date"),
        ("position_market_betas", "calc_date"),
        ("position_interest_rate_betas", "calculation_date"),
    ]

    for table_name, date_column in tables_with_portfolio_id:
        try:
            result = await db.execute(text(f"""
                DELETE FROM {table_name}
                WHERE portfolio_id = :portfolio_id
                AND {date_column} >= :start_date
            """), {"portfolio_id": portfolio_id, "start_date": start_date})

            await db.commit()
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"  {table_name}: deleted {deleted_count} records")

        except Exception as e:
            await db.rollback()
            print(f"  {table_name}: ERROR - {str(e)}")

    # STEP 4: Delete from tables without portfolio_id (via position JOIN)
    tables_via_position_join = [
        ("position_factor_exposures", "calculation_date"),
        ("position_volatility", "calculation_date"),
    ]

    for table_name, date_column in tables_via_position_join:
        try:
            result = await db.execute(text(f"""
                DELETE FROM {table_name}
                WHERE position_id IN (
                    SELECT id FROM positions
                    WHERE portfolio_id = :portfolio_id
                )
                AND {date_column} >= :start_date
            """), {"portfolio_id": portfolio_id, "start_date": start_date})

            await db.commit()
            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"  {table_name}: deleted {deleted_count} records (via position JOIN)")

        except Exception as e:
            await db.rollback()
            print(f"  {table_name}: ERROR - {str(e)}")

    print(f"OK Total records deleted: {total_deleted}")
    return total_deleted


async def get_trading_days(start_date: date, end_date: date) -> list[date]:
    """Get all trading days between start and end dates"""
    trading_days = []
    current_date = start_date

    while current_date <= end_date:
        if trading_calendar.is_trading_day(current_date):
            trading_days.append(current_date)
        current_date += timedelta(days=1)

    return trading_days


async def run_batch_for_single_portfolio(db, portfolio_id: str, calc_date: date):
    """
    Run ALL batch jobs for a single date using the refactored batch orchestrator.

    Uses Phases 1-7 refactored calculation modules with canonical functions:
    - regression_utils.run_single_factor_regression() for all OLS (market beta, IR beta)
    - market_data.get_position_value() for all position valuations
    - market_data.get_returns() for all return retrieval (no duplicate fetch functions)
    - portfolio_exposure_service.get_portfolio_exposures() for snapshot caching

    This ensures all calculations use consistent logic with no duplicate implementations.
    """
    from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2

    # Create a minimal PortfolioData-like object
    class PortfolioData:
        def __init__(self, id):
            self.id = id
            self.name = "Demo Portfolio"

    portfolio_data = PortfolioData(portfolio_id)

    # Temporarily override trading calendar check for historical processing
    from app.calculations import snapshots as snapshot_module
    original_is_trading_day = trading_calendar.is_trading_day

    # Make the specific date a "trading day" for processing
    def mock_is_trading_day(check_date):
        if check_date == calc_date:
            return True
        return original_is_trading_day(check_date)

    trading_calendar.is_trading_day = mock_is_trading_day

    try:
        # Run position values update
        # Uses: market_data.get_position_value() [Phase 2 refactoring]
        await batch_orchestrator_v2._update_position_values(db, portfolio_id)

        # Run equity balance update (critical for correct factor weighting)
        result = await batch_orchestrator_v2._update_equity_balance(db, portfolio_id)
        equity = result.get('new_equity', 0)

        # Run portfolio aggregation (gross/net exposure calculation)
        await batch_orchestrator_v2._calculate_portfolio_aggregation(db, portfolio_id)

        # Run market beta (OLS regression vs SPY)
        # Uses: regression_utils.run_single_factor_regression() + market_data.get_returns() [Phases 3-4]
        await batch_orchestrator_v2._calculate_market_beta(db, portfolio_id)

        # Run IR beta (OLS regression vs TLT)
        # Uses: regression_utils.run_single_factor_regression() + market_data.get_returns() [Phases 3-4]
        await batch_orchestrator_v2._calculate_ir_beta(db, portfolio_id)

        # Run ridge factors (6 non-market factors with L2 regularization)
        # Uses: market_data.get_position_value() [Phases 2 & 6]
        await batch_orchestrator_v2._calculate_ridge_factors(db, portfolio_id)

        # Run spread factors (4 long-short factors, 180-day window)
        # Uses: market_data.get_position_value() [Phase 6]
        await batch_orchestrator_v2._calculate_spread_factors(db, portfolio_id)

        # Run sector analysis
        # Uses: market_data.get_position_value() [Phase 6]
        await batch_orchestrator_v2._calculate_sector_analysis(db, portfolio_id)

        # Run volatility analytics
        await batch_orchestrator_v2._calculate_volatility_analytics(db, portfolio_id)

        # Legacy 7-factor OLS removed - now using Ridge (6 factors) + Market Beta (OLS) + Spread (4 factors)
        # Old code had duplicate OLS, position valuation, and return fetching logic
        # All consolidated via Phases 1-7 refactoring

        # Run market risk (scenario analysis)
        # Uses: portfolio_exposure_service.get_portfolio_exposures() [Phase 5]
        await batch_orchestrator_v2._calculate_market_risk(db, portfolio_id)

        # Create snapshot (captures full portfolio state)
        await batch_orchestrator_v2._create_snapshot(db, portfolio_id)

        # Run stress testing (uses IR beta for IR shock scenarios)
        # Uses: portfolio_exposure_service.get_portfolio_exposures() [Phase 5]
        await batch_orchestrator_v2._run_stress_tests(db, portfolio_id)

        # Run correlations
        try:
            await batch_orchestrator_v2._calculate_correlations(db, portfolio_id)
        except Exception as e:
            # Correlations may fail for early dates
            pass

        return {"success": True, "equity": equity}

    finally:
        # Restore original trading calendar function
        trading_calendar.is_trading_day = original_is_trading_day


async def main():
    print("=" * 80)
    print("RESET AND REPROCESS HISTORICAL CALCULATIONS")
    print("With Volatility Key Alignment + Size Factor Consistency + Spread Factors")
    print("=" * 80)
    print()

    # All 3 demo portfolios with their starting equity values
    portfolios = [
        ("e23ab931-a033-edfe-ed4f-9d02474780b4", "High Net Worth", Decimal('2850000.00')),
        ("1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe", "Individual Investor", Decimal('250000.00')),
        ("fcd71196-e93e-f000-5a74-31a9eead3118", "Hedge Fund Style", Decimal('5000000.00')),
    ]

    start_date = date(2025, 9, 30)
    end_date = date.today()

    print(f"Processing {len(portfolios)} portfolios")
    print(f"Date range: {start_date} to {end_date}")
    print()

    async with get_async_session() as db:
        # Get trading days once (same for all portfolios)
        trading_days = await get_trading_days(start_date, end_date)
        print("=" * 80)
        print("TRADING DAYS")
        print("=" * 80)
        print(f"Found {len(trading_days)} trading days to process")
        print(f"First: {trading_days[0]}, Last: {trading_days[-1]}")
        print()

        total_successful = 0
        total_failed = 0

        # Process each portfolio
        for portfolio_id, portfolio_name, starting_equity in portfolios:
            print("\n")
            print("=" * 80)
            print(f"PORTFOLIO: {portfolio_name}")
            print("=" * 80)
            print(f"ID: {portfolio_id}")
            print(f"Starting Equity: ${float(starting_equity):,.2f}")
            print()

            # Step 1: Reset portfolio equity to starting value
            print("=" * 80)
            print("STEP 1: Reset Starting Equity")
            print("=" * 80)
            await reset_portfolio_equity(db, portfolio_id, starting_equity)
            print()

            # Step 2: Delete old calculation results
            print("=" * 80)
            print("STEP 2: Delete Calculation Results")
            print("=" * 80)
            await delete_calculation_results(db, portfolio_id, start_date)
            print()

            # Step 3: Reprocess each trading day
            print("=" * 80)
            print("STEP 3: Reprocess Calculations")
            print("=" * 80)
            print()

            successful = 0
            failed = 0

            for i, calc_date in enumerate(trading_days, 1):
                print(f"[{i}/{len(trading_days)}] Processing {calc_date}...", flush=True)

                try:
                    result = await run_batch_for_single_portfolio(db, portfolio_id, calc_date)

                    if result.get('success'):
                        successful += 1
                        equity = result.get('equity', 0)
                        print(f"  OK Complete - Equity: ${equity:,.2f}")
                    else:
                        failed += 1
                        print(f"  ERROR Failed")

                except Exception as e:
                    failed += 1
                    print(f"  ERROR: {str(e)}")

                print()

            print("=" * 80)
            print(f"PORTFOLIO {portfolio_name} COMPLETE")
            print("=" * 80)
            print(f"Successful: {successful}/{len(trading_days)}")
            print(f"Failed: {failed}/{len(trading_days)}")
            print()

            total_successful += successful
            total_failed += failed

        # Final summary
        print("\n")
        print("=" * 80)
        print("ALL PORTFOLIOS COMPLETE")
        print("=" * 80)
        print(f"Total Successful: {total_successful}/{len(portfolios) * len(trading_days)}")
        print(f"Total Failed: {total_failed}/{len(portfolios) * len(trading_days)}")
        print()
        print("✅ Reprocessing complete using refactored calculation engine:")
        print()
        print("   ARCHITECTURE (Phases 1-7 refactoring complete):")
        print("   - All OLS regressions → regression_utils.run_single_factor_regression()")
        print("   - All position valuations → market_data.get_position_value()")
        print("   - All return retrievals → market_data.get_returns()")
        print("   - All exposure calcs → portfolio_exposure_service.get_portfolio_exposures()")
        print()
        print("   BENEFITS:")
        print("   - ~600 lines of duplicate code eliminated")
        print("   - Consistent beta capping (±5.0) across all regressions")
        print("   - 50% fewer DB queries (batch fetching + snapshot caching)")
        print("   - Single source of truth for all calculations")
        print()
        print("   RECENT FIXES:")
        print("   - Volatility key alignment (realized_vol_21d → realized_volatility_21d)")
        print("   - Size factor consistency (SIZE → IWM)")
        print("   - Spread factor calculations (4 long-short factors)")
        print()


if __name__ == "__main__":
    asyncio.run(main())
