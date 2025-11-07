#!/usr/bin/env python
"""
Trace Individual Investor portfolio values from July 1 onward
Shows positions, quantities, prices, and portfolio values for manual verification
"""
import asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import MarketDataCache

async def trace_portfolio_exposure():
    """Show detailed portfolio breakdown from July 1 onward"""

    async with get_async_session() as db:
        # Get Individual Investor portfolio
        user_result = await db.execute(
            select(User).where(User.email == 'demo_individual@sigmasight.com')
        )
        user = user_result.scalar_one()

        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = portfolio_result.scalar_one()

        print(f"\nPortfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print("=" * 120)

        # Get all snapshots from July 1 onward
        snapshots_result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .where(PortfolioSnapshot.snapshot_date >= date(2025, 7, 1))
            .order_by(PortfolioSnapshot.snapshot_date)
        )
        snapshots = snapshots_result.scalars().all()

        if not snapshots:
            print("No snapshots found from July 1 onward")
            return

        print(f"\nFound {len(snapshots)} snapshots from July 1 onward\n")

        # For each snapshot date, show positions and calculations
        for snapshot in snapshots:
            calc_date = snapshot.snapshot_date

            print("\n" + "=" * 120)
            print(f"DATE: {calc_date}")
            print("=" * 120)

            # Get all positions active on this date
            positions_result = await db.execute(
                select(Position)
                .where(Position.portfolio_id == portfolio.id)
                .where(Position.entry_date <= calc_date)
                .where(
                    (Position.exit_date.is_(None)) | (Position.exit_date > calc_date)
                )
                .where(Position.deleted_at.is_(None))
                .order_by(Position.symbol)
            )
            positions = positions_result.scalars().all()

            print(f"\nActive Positions: {len(positions)}")
            print("-" * 120)
            print(f"{'Symbol':<10} {'Type':<6} {'Quantity':>12} {'Price':>12} {'Market Value':>15} {'Notes':<30}")
            print("-" * 120)

            total_market_value = Decimal('0')
            position_details = []

            for pos in positions:
                # Get historical price for this date
                price_result = await db.execute(
                    select(MarketDataCache)
                    .where(MarketDataCache.symbol == pos.symbol)
                    .where(MarketDataCache.date == calc_date)
                )
                price_record = price_result.scalar_one_or_none()

                if price_record:
                    price = price_record.close

                    # Calculate market value
                    quantity = pos.quantity
                    multiplier = 100 if pos.position_type.value in ['LC', 'LP', 'SC', 'SP'] else 1
                    market_value = abs(quantity * price * multiplier)

                    total_market_value += market_value

                    position_details.append({
                        'symbol': pos.symbol,
                        'type': pos.position_type.value,
                        'quantity': quantity,
                        'price': price,
                        'market_value': market_value,
                        'has_price': True
                    })

                    print(f"{pos.symbol:<10} {pos.position_type.value:<6} {float(quantity):>12.2f} ${float(price):>11.2f} ${float(market_value):>14.2f}")
                else:
                    position_details.append({
                        'symbol': pos.symbol,
                        'type': pos.position_type.value,
                        'quantity': pos.quantity,
                        'price': None,
                        'market_value': Decimal('0'),
                        'has_price': False
                    })
                    print(f"{pos.symbol:<10} {pos.position_type.value:<6} {float(pos.quantity):>12.2f} {'NO PRICE':>12} ${0:>14.2f} {'*** MISSING PRICE ***':<30}")

            print("-" * 120)
            print(f"{'CALCULATED TOTAL':<10} {'':<6} {'':<12} {'':<12} ${float(total_market_value):>14.2f}")
            print("-" * 120)

            # Show snapshot values
            print(f"\nSnapshot Values (from database):")
            print(f"  Gross Exposure:     ${float(snapshot.gross_exposure):>14.2f}")
            print(f"  Net Exposure:       ${float(snapshot.net_exposure):>14.2f}")
            print(f"  Long Value:         ${float(snapshot.long_value):>14.2f}")
            print(f"  Short Value:        ${float(snapshot.short_value):>14.2f}")
            print(f"  Total Value:        ${float(snapshot.total_value):>14.2f}")
            print(f"  Equity Balance:     ${float(snapshot.equity_balance):>14.2f}")
            print(f"  Daily P&L:          ${float(snapshot.daily_pnl):>14.2f}")
            print(f"  Cumulative P&L:     ${float(snapshot.cumulative_pnl):>14.2f}")

            # Show discrepancy
            discrepancy = total_market_value - snapshot.gross_exposure
            print(f"\nDISCREPANCY:")
            print(f"  Calculated Sum:     ${float(total_market_value):>14.2f}")
            print(f"  Snapshot Gross:     ${float(snapshot.gross_exposure):>14.2f}")
            print(f"  Difference:         ${float(discrepancy):>14.2f}")

            if abs(discrepancy) > Decimal('0.01'):
                print(f"  *** MISMATCH! *** Difference = ${float(discrepancy):,.2f}")
            else:
                print(f"  OK - Values match")

        # Summary table
        print("\n\n" + "=" * 120)
        print("SUMMARY TABLE - All Dates")
        print("=" * 120)
        print(f"{'Date':<12} {'Positions':>10} {'Calc Total':>15} {'Snap Gross':>15} {'Equity':>15} {'Daily P&L':>15} {'Cum P&L':>15} {'Discrepancy':>15}")
        print("-" * 120)

        for snapshot in snapshots:
            calc_date = snapshot.snapshot_date

            # Recalculate total for this date
            positions_result = await db.execute(
                select(Position)
                .where(Position.portfolio_id == portfolio.id)
                .where(Position.entry_date <= calc_date)
                .where(
                    (Position.exit_date.is_(None)) | (Position.exit_date > calc_date)
                )
                .where(Position.deleted_at.is_(None))
            )
            positions = positions_result.scalars().all()

            total = Decimal('0')
            for pos in positions:
                price_result = await db.execute(
                    select(MarketDataCache.close)
                    .where(MarketDataCache.symbol == pos.symbol)
                    .where(MarketDataCache.date == calc_date)
                )
                price = price_result.scalar_one_or_none()
                if price:
                    multiplier = 100 if pos.position_type.value in ['LC', 'LP', 'SC', 'SP'] else 1
                    total += abs(pos.quantity * price * multiplier)

            discrepancy = total - snapshot.gross_exposure

            print(
                f"{calc_date} "
                f"{len(positions):>10} "
                f"${float(total):>14.2f} "
                f"${float(snapshot.gross_exposure):>14.2f} "
                f"${float(snapshot.equity_balance):>14.2f} "
                f"${float(snapshot.daily_pnl):>14.2f} "
                f"${float(snapshot.cumulative_pnl):>14.2f} "
                f"${float(discrepancy):>14.2f}"
            )

if __name__ == '__main__':
    asyncio.run(trace_portfolio_exposure())
