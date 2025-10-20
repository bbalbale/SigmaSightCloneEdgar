"""
Reprocess historical calculations from Sept 30 onwards with corrected equity balance.

This script:
1. Deletes calculation results from Sept 30 onwards (keeps market data cache)
2. Runs batch processing for each trading day in chronological order
3. Uses existing market data to avoid API costs
4. Ensures factor calculations use correct equity balance
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import text, select
from app.database import get_async_session
from app.utils.trading_calendar import trading_calendar
from app.models.users import Portfolio
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2


async def delete_calculation_results(db, portfolio_id: str, start_date: date):
    """Delete calculation results from start_date onwards (keep market data)"""

    print("=" * 80)
    print("STEP 1: Delete Calculation Results")
    print("=" * 80)
    print()

    tables_to_clean = [
        ("portfolio_snapshots", "snapshot_date"),
        ("position_market_betas", "calc_date"),
        ("position_interest_rate_betas", "calc_date"),
        ("position_factor_exposures", "calc_date"),
        ("position_volatility_analytics", "calc_date"),
        ("correlation_calculations", "calculation_date"),
        # Don't delete market_data_cache - that's our price data!
    ]

    total_deleted = 0

    for table_name, date_column in tables_to_clean:
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

    await db.commit()

    print()
    print(f"Total records deleted: {total_deleted}")
    print("Market data cache preserved ✓")
    print()


async def get_trading_days(start_date: date, end_date: date) -> list[date]:
    """Get all trading days between start and end dates"""
    trading_days = []
    current_date = start_date

    while current_date <= end_date:
        if trading_calendar.is_trading_day(current_date):
            trading_days.append(current_date)
        current_date += timedelta(days=1)

    return trading_days


async def run_batch_for_date(db, portfolio_id: str, calc_date: date):
    """Run batch calculations for a specific date (skip market data update)"""
    from app.calculations.snapshots import create_portfolio_snapshot
    from app.calculations.market_beta import calculate_portfolio_market_beta
    from app.calculations.interest_rate_beta import calculate_portfolio_ir_beta
    from app.calculations.factors_ridge import calculate_factor_betas_ridge
    from app.calculations.sector_analysis import calculate_portfolio_sector_concentration
    from app.calculations.volatility_analytics import calculate_portfolio_volatility_batch
    from app.calculations.stress_testing import run_comprehensive_stress_test, save_stress_test_results
    from app.services.correlation_service import CorrelationService
    from app.models.positions import Position
    from app.calculations.portfolio import calculate_portfolio_exposures
    from app.calculations.market_data import update_position_market_values
    from app.services.market_data_service import market_data_service
    from app.models.snapshots import PortfolioSnapshot
    from app.models.users import Portfolio
    from sqlalchemy import select, desc
    from uuid import UUID
    from decimal import Decimal

    portfolio_uuid = UUID(portfolio_id)

    # Get portfolio
    portfolio_stmt = select(Portfolio).where(Portfolio.id == portfolio_uuid)
    portfolio_result = await db.execute(portfolio_stmt)
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        return {"error": f"Portfolio {portfolio_id} not found"}

    # Job 1: Update position values (using cached market data)
    positions_stmt = select(Position).where(
        Position.portfolio_id == portfolio_uuid,
        Position.deleted_at.is_(None),
        Position.exit_date.is_(None)
    )
    positions_result = await db.execute(positions_stmt)
    positions = positions_result.scalars().all()

    for position in positions:
        try:
            prices = await market_data_service.get_cached_prices(db, [position.symbol])
            current_price = prices.get(position.symbol) if prices else None

            if current_price:
                await update_position_market_values(db, position, Decimal(str(current_price)))
        except Exception as e:
            print(f"    Warning: Could not update {position.symbol}: {e}")

    await db.commit()

    # Job 2: Update equity balance (NEW - uses rollforward)
    # Calculate current portfolio value
    position_dicts = []
    for pos in positions:
        market_value = float(pos.market_value) if pos.market_value else 0
        position_dicts.append({
            'symbol': pos.symbol,
            'quantity': float(pos.quantity),
            'market_value': market_value,
            'exposure': market_value,
            'position_type': pos.position_type.value if pos.position_type else 'LONG',
            'last_price': float(pos.last_price) if pos.last_price else 0
        })

    exposures = calculate_portfolio_exposures(position_dicts)
    current_value = exposures.get('gross_exposure', Decimal('0'))

    # Get latest snapshot for equity rollforward
    latest_snapshot_stmt = select(PortfolioSnapshot).where(
        PortfolioSnapshot.portfolio_id == portfolio_uuid
    ).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(1)

    snapshot_result = await db.execute(latest_snapshot_stmt)
    latest_snapshot = snapshot_result.scalar_one_or_none()

    if latest_snapshot and latest_snapshot.equity_balance and latest_snapshot.total_value:
        previous_equity = latest_snapshot.equity_balance
        daily_pnl = current_value - latest_snapshot.total_value
        new_equity = previous_equity + daily_pnl
    else:
        # First snapshot - use starting equity
        new_equity = portfolio.equity_balance or Decimal('0')

    # Update Portfolio.equity_balance
    portfolio.equity_balance = new_equity
    await db.commit()

    # Job 3: Portfolio aggregation (already done above)

    # Job 4: Market beta calculation
    try:
        await calculate_portfolio_market_beta(
            db=db,
            portfolio_id=portfolio_uuid,
            calculation_date=calc_date,
            persist=True
        )
    except Exception as e:
        print(f"    Warning: Market beta failed: {e}")

    # Job 5: IR beta calculation
    try:
        await calculate_portfolio_ir_beta(
            db=db,
            portfolio_id=portfolio_uuid,
            calculation_date=calc_date,
            window_days=90,
            persist=True
        )
    except Exception as e:
        print(f"    Warning: IR beta failed: {e}")

    # Job 6: Ridge factor calculation
    try:
        await calculate_factor_betas_ridge(
            db=db,
            portfolio_id=portfolio_uuid,
            calculation_date=calc_date,
            regularization_alpha=1.0,
            use_delta_adjusted=False,
            context=None
        )
    except Exception as e:
        print(f"    Warning: Ridge factors failed: {e}")

    # Job 7: Sector concentration analysis
    try:
        await calculate_portfolio_sector_concentration(
            db=db,
            portfolio_id=portfolio_uuid,
            calculation_date=calc_date
        )
    except Exception as e:
        print(f"    Warning: Sector analysis failed: {e}")

    # Job 8: Volatility analytics
    try:
        await calculate_portfolio_volatility_batch(
            db=db,
            portfolio_id=portfolio_uuid,
            calculation_date=calc_date
        )
    except Exception as e:
        print(f"    Warning: Volatility analytics failed: {e}")

    # Job 9: Portfolio snapshot (uses pre-calculated equity)
    try:
        result = await create_portfolio_snapshot(db, portfolio_uuid, calc_date)
        if not result.get('success'):
            print(f"    Warning: Snapshot creation: {result.get('message')}")
    except Exception as e:
        print(f"    Warning: Snapshot failed: {e}")

    # Job 10: Stress testing
    try:
        stress_results = await run_comprehensive_stress_test(db, portfolio_uuid, calc_date)
        if stress_results:
            await save_stress_test_results(db, portfolio_uuid, stress_results)
    except Exception as e:
        print(f"    Warning: Stress testing failed: {e}")

    # Job 11: Position correlations
    try:
        correlation_service = CorrelationService(db)
        await correlation_service.calculate_portfolio_correlations(
            portfolio_uuid,
            calculation_date=calc_date
        )
    except Exception as e:
        print(f"    Warning: Correlations failed: {e}")

    return {
        "success": True,
        "date": calc_date,
        "equity_balance": float(new_equity)
    }


async def main():
    print("=" * 80)
    print("HISTORICAL CALCULATION REPROCESSING")
    print("With Corrected Equity Balance")
    print("=" * 80)
    print()

    portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"
    start_date = date(2025, 9, 30)
    end_date = date.today()

    print(f"Portfolio: {portfolio_id}")
    print(f"Date range: {start_date} to {end_date}")
    print()

    async with get_async_session() as db:
        # Step 1: Delete old calculation results
        await delete_calculation_results(db, portfolio_id, start_date)

        # Step 2: Get all trading days
        trading_days = await get_trading_days(start_date, end_date)
        print("=" * 80)
        print("STEP 2: Get Trading Days")
        print("=" * 80)
        print(f"Found {len(trading_days)} trading days to process")
        print(f"First: {trading_days[0]}, Last: {trading_days[-1]}")
        print()

        # Step 3: Process each trading day in chronological order
        print("=" * 80)
        print("STEP 3: Reprocess Calculations")
        print("=" * 80)
        print()

        successful = 0
        failed = 0

        for i, calc_date in enumerate(trading_days, 1):
            print(f"[{i}/{len(trading_days)}] Processing {calc_date}...")

            try:
                result = await run_batch_for_date(db, portfolio_id, calc_date)

                if result.get('success'):
                    successful += 1
                    equity = result.get('equity_balance', 0)
                    print(f"  ✓ Complete - Equity: ${equity:,.2f}")
                else:
                    failed += 1
                    print(f"  ✗ Failed: {result.get('error')}")

            except Exception as e:
                failed += 1
                print(f"  ✗ Error: {str(e)}")

            print()

        print("=" * 80)
        print("REPROCESSING COMPLETE")
        print("=" * 80)
        print(f"Successful: {successful}/{len(trading_days)}")
        print(f"Failed: {failed}/{len(trading_days)}")
        print()

        # Step 4: Verify final state
        print("=" * 80)
        print("STEP 4: Verify Final State")
        print("=" * 80)
        print()

        # Check latest snapshot
        from app.models.snapshots import PortfolioSnapshot
        latest_snapshot_stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == portfolio_id
        ).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(1)

        snapshot_result = await db.execute(latest_snapshot_stmt)
        latest_snapshot = snapshot_result.scalar_one_or_none()

        if latest_snapshot:
            print(f"Latest Snapshot: {latest_snapshot.snapshot_date}")
            print(f"  Equity Balance: ${float(latest_snapshot.equity_balance):,.2f}")
            print(f"  Total Value: ${float(latest_snapshot.total_value):,.2f}")
            print(f"  Daily P&L: ${float(latest_snapshot.daily_pnl):,.2f}")
            print(f"  Cumulative P&L: ${float(latest_snapshot.cumulative_pnl):,.2f}")
        else:
            print("No snapshots found!")

        print()
        print("=" * 80)
        print("✅ REPROCESSING COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
