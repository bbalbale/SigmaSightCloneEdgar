"""
Reset starting equity and reprocess calculations from Sept 30 onwards.

This ensures proper equity rollforward chain.
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
    """Delete calculation results from start_date onwards (keep market data)"""

    # Tables with direct portfolio_id column
    tables_with_portfolio_id = [
        ("portfolio_snapshots", "snapshot_date"),
        ("position_market_betas", "calc_date"),
        ("position_interest_rate_betas", "calculation_date"),
        ("correlation_calculations", "calculation_date"),
    ]

    # Tables without portfolio_id - need to delete via positions table JOIN
    tables_via_position_join = [
        ("position_factor_exposures", "calculation_date"),
        ("position_volatility", "calculation_date"),
    ]

    total_deleted = 0

    # Delete from tables with portfolio_id
    for table_name, date_column in tables_with_portfolio_id:
        try:
            result = await db.execute(text(f"""
                DELETE FROM {table_name}
                WHERE portfolio_id = :portfolio_id
                AND {date_column} >= :start_date
            """), {"portfolio_id": portfolio_id, "start_date": start_date})

            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"  {table_name}: deleted {deleted_count} records")

        except Exception as e:
            print(f"  {table_name}: {str(e)}")

    # Delete from tables via position JOIN
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

            deleted_count = result.rowcount
            total_deleted += deleted_count
            print(f"  {table_name}: deleted {deleted_count} records (via position JOIN)")

        except Exception as e:
            print(f"  {table_name}: {str(e)}")

    await db.commit()

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
    """Run ALL batch jobs for a single date using the batch orchestrator pattern"""
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
        await batch_orchestrator_v2._update_position_values(db, portfolio_id)

        # Run equity balance update (NEW - critical for correct factor calcs)
        result = await batch_orchestrator_v2._update_equity_balance(db, portfolio_id)
        equity = result.get('new_equity', 0)

        # Run portfolio aggregation
        await batch_orchestrator_v2._calculate_portfolio_aggregation(db, portfolio_id)

        # Run market beta
        await batch_orchestrator_v2._calculate_market_beta(db, portfolio_id)

        # Run IR beta
        await batch_orchestrator_v2._calculate_ir_beta(db, portfolio_id)

        # Run ridge factors
        await batch_orchestrator_v2._calculate_ridge_factors(db, portfolio_id)

        # Run sector analysis
        await batch_orchestrator_v2._calculate_sector_analysis(db, portfolio_id)

        # Run volatility analytics
        await batch_orchestrator_v2._calculate_volatility_analytics(db, portfolio_id)

        # Run factors (legacy)
        await batch_orchestrator_v2._calculate_factors(db, portfolio_id)

        # Run market risk
        await batch_orchestrator_v2._calculate_market_risk(db, portfolio_id)

        # Create snapshot
        await batch_orchestrator_v2._create_snapshot(db, portfolio_id)

        # Run stress testing
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
    print("=" * 80)
    print()

    portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"
    starting_equity = Decimal('2850000.00')  # Original starting equity from Sept 30
    start_date = date(2025, 9, 30)
    end_date = date.today()

    print(f"Portfolio: {portfolio_id}")
    print(f"Starting Equity: ${float(starting_equity):,.2f}")
    print(f"Date range: {start_date} to {end_date}")
    print()

    async with get_async_session() as db:
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

        # Step 3: Get trading days
        trading_days = await get_trading_days(start_date, end_date)
        print("=" * 80)
        print("STEP 3: Get Trading Days")
        print("=" * 80)
        print(f"Found {len(trading_days)} trading days to process")
        print(f"First: {trading_days[0]}, Last: {trading_days[-1]}")
        print()

        # Step 4: Process each trading day
        print("=" * 80)
        print("STEP 4: Reprocess Calculations")
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
        print("REPROCESSING COMPLETE")
        print("=" * 80)
        print(f"Successful: {successful}/{len(trading_days)}")
        print(f"Failed: {failed}/{len(trading_days)}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
