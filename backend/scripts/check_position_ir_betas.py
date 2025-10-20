"""
Check Position-Level IR Beta Values
"""
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.market_data import PositionInterestRateBeta
from app.models.positions import Position


async def check_ir_betas():
    async with get_async_session() as db:
        stmt = select(
            Position.symbol,
            PositionInterestRateBeta.ir_beta,
            PositionInterestRateBeta.r_squared,
            Position.market_value
        ).join(
            Position, PositionInterestRateBeta.position_id == Position.id
        ).order_by(
            PositionInterestRateBeta.ir_beta.desc()
        ).limit(20)

        result = await db.execute(stmt)
        rows = result.all()

        print('Position-Level IR Betas (Top 20 by absolute beta):')
        print('=' * 80)
        print(f"{'Symbol':<10} {'IR Beta':>12} {'R-Squared':>12} {'Market Value':>15}")
        print('-' * 80)

        for symbol, ir_beta, r_sq, mkt_val in rows:
            print(f"{symbol:<10} {float(ir_beta):>12.6f} {float(r_sq) if r_sq else 0:>12.3f} ${float(mkt_val) if mkt_val else 0:>14,.0f}")

        print('=' * 80)

        # Get stats
        stats_stmt = select(
            func.avg(PositionInterestRateBeta.ir_beta),
            func.min(PositionInterestRateBeta.ir_beta),
            func.max(PositionInterestRateBeta.ir_beta),
            func.count(PositionInterestRateBeta.id)
        )
        stats_result = await db.execute(stats_stmt)
        avg_beta, min_beta, max_beta, count = stats_result.one()

        print(f'\nStatistics across all {count} position IR betas:')
        print(f'  Average IR Beta: {float(avg_beta):.6f}')
        print(f'  Min IR Beta: {float(min_beta):.6f}')
        print(f'  Max IR Beta: {float(max_beta):.6f}')


if __name__ == "__main__":
    asyncio.run(check_ir_betas())
