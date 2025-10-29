"""Check analytics and snapshot data status"""
import asyncio
from sqlalchemy import select, func, text
from app.database import AsyncSessionLocal
from app.models.market_data import (
    PositionMarketBeta, PositionInterestRateBeta,
    PositionFactorExposure, PositionVolatility
)
from app.models.correlations import CorrelationCalculation

async def check_analytics_data():
    async with AsyncSessionLocal() as db:
        # Market betas
        market_beta_count = await db.execute(select(func.count(PositionMarketBeta.id)))

        # IR betas
        ir_beta_count = await db.execute(select(func.count(PositionInterestRateBeta.id)))

        # Factor exposures
        factor_exp_count = await db.execute(select(func.count(PositionFactorExposure.id)))

        # Volatility
        volatility_count = await db.execute(select(func.count(PositionVolatility.id)))

        # Correlations
        correlation_count = await db.execute(select(func.count(CorrelationCalculation.id)))

        print('=' * 80)
        print('ANALYTICS/CALCULATION DATA')
        print('=' * 80)
        print()
        print('RISK ANALYTICS:')
        print(f'  Market Betas:         {market_beta_count.scalar()}')
        print(f'  IR Betas:             {ir_beta_count.scalar()}')
        print(f'  Factor Exposures:     {factor_exp_count.scalar()}')
        print(f'  Volatility Metrics:   {volatility_count.scalar()}')
        print(f'  Correlation Calcs:    {correlation_count.scalar()}')
        print()

        # Check snapshots by date and portfolio
        snapshots_detail = await db.execute(
            text('''
                SELECT
                    ps.snapshot_date,
                    p.name,
                    ps.total_value,
                    ps.daily_pnl,
                    ps.cumulative_pnl,
                    ps.num_positions
                FROM portfolio_snapshots ps
                JOIN portfolios p ON ps.portfolio_id = p.id
                ORDER BY ps.snapshot_date, p.name
            ''')
        )

        print('PORTFOLIO SNAPSHOTS DETAIL:')
        header = f'  {"Date":<12} {"Portfolio":<40} {"Value":<15} {"Daily P&L":<15} {"Cumul P&L":<15} {"Positions":<10}'
        print(header)
        print('  ' + '-' * 110)
        for row in snapshots_detail.fetchall():
            date, name, value, daily_pnl, cumul_pnl, num_pos = row
            value_str = f'${float(value):,.2f}' if value else 'N/A'
            daily_pnl_str = f'${float(daily_pnl):,.2f}' if daily_pnl else 'N/A'
            cumul_pnl_str = f'${float(cumul_pnl):,.2f}' if cumul_pnl else 'N/A'
            print(f'  {str(date):<12} {name[:40]:<40} {value_str:<15} {daily_pnl_str:<15} {cumul_pnl_str:<15} {num_pos or 0:<10}')

        print()
        print('=' * 80)

if __name__ == "__main__":
    asyncio.run(check_analytics_data())
