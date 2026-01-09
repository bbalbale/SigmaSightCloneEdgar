#!/usr/bin/env python3
"""
Check test portfolio results for testalpha user.
Run on Railway: railway run python scripts/check_testalpha_results.py
"""

import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import PositionFactorExposure, PositionGreeks


async def check_test_portfolio():
    async with get_async_session() as db:
        # Find testalpha user
        user_result = await db.execute(
            select(User).where(User.email.ilike('%testalpha%'))
        )
        user = user_result.scalar_one_or_none()

        if not user:
            print('❌ User not found (testalpha)')
            return

        print(f'✅ User: {user.email}')
        print(f'   User ID: {user.id}')

        # Get portfolios
        portfolios_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolios = portfolios_result.scalars().all()

        if not portfolios:
            print('❌ No portfolios found')
            return

        for p in portfolios:
            print(f'\n{"="*60}')
            print(f'Portfolio: {p.name}')
            print(f'Portfolio ID: {p.id}')
            print(f'{"="*60}')

            # Count positions
            pos_result = await db.execute(
                select(Position).where(Position.portfolio_id == p.id)
            )
            positions = pos_result.scalars().all()
            print(f'\n📊 Positions: {len(positions)}')

            # List position symbols
            symbols = [pos.symbol for pos in positions]
            print(f'   Symbols: {", ".join(sorted(symbols))}')

            # Count snapshots
            snap_count = await db.execute(
                select(func.count(PortfolioSnapshot.id)).where(PortfolioSnapshot.portfolio_id == p.id)
            )
            snapshot_count = snap_count.scalar()
            print(f'\n📅 Snapshots: {snapshot_count}')

            if snapshot_count > 0:
                # Get date range
                latest_snap = await db.execute(
                    select(func.max(PortfolioSnapshot.snapshot_date)).where(PortfolioSnapshot.portfolio_id == p.id)
                )
                earliest_snap = await db.execute(
                    select(func.min(PortfolioSnapshot.snapshot_date)).where(PortfolioSnapshot.portfolio_id == p.id)
                )
                print(f'   Date range: {earliest_snap.scalar()} to {latest_snap.scalar()}')

            # Count factor exposures
            position_ids = [pos.id for pos in positions]
            if position_ids:
                factor_count = await db.execute(
                    select(func.count(PositionFactorExposure.id)).where(
                        PositionFactorExposure.position_id.in_(position_ids)
                    )
                )
                print(f'\n📈 Position Factor Exposures: {factor_count.scalar()}')

                # Count Greeks
                greeks_count = await db.execute(
                    select(func.count(PositionGreeks.id)).where(
                        PositionGreeks.position_id.in_(position_ids)
                    )
                )
                print(f'📊 Position Greeks: {greeks_count.scalar()}')

            # Check symbol_universe for portfolio symbols
            from sqlalchemy import text
            universe_result = await db.execute(
                text("""
                    SELECT symbol FROM symbol_universe
                    WHERE symbol = ANY(:symbols)
                """),
                {"symbols": symbols}
            )
            universe_symbols = [r[0] for r in universe_result.fetchall()]
            print(f'\n🌐 Symbols in Universe: {len(universe_symbols)}/{len(symbols)}')

            missing = set(symbols) - set(universe_symbols)
            if missing:
                print(f'   Missing from universe: {", ".join(sorted(missing))}')


if __name__ == "__main__":
    asyncio.run(check_test_portfolio())
