import asyncio
from uuid import UUID
from datetime import date
from sqlalchemy import select, and_, func
from app.database import AsyncSessionLocal
from app.models.positions import Position

async def check_holdings():
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')

    async with AsyncSessionLocal() as db:
        print('=' * 80)
        print('HNW PORTFOLIO HOLDINGS ANALYSIS')
        print('=' * 80)

        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        ).order_by(Position.market_value.desc())

        result = await db.execute(stmt)
        positions = result.scalars().all()

        print(f'\nTotal Positions: {len(positions)}')
        print(f'\n{"Symbol":10s} | {"Type":6s} | {"Quantity":>12s} | {"Last Price":>12s} | {"Market Value":>15s} | {"% of Portfolio":>12s}')
        print('-' * 100)

        total_value = sum(float(p.market_value) for p in positions if p.market_value)

        for pos in positions:
            mv = float(pos.market_value) if pos.market_value else 0
            pct = (mv / total_value * 100) if total_value else 0
            qty = float(pos.quantity)
            price = float(pos.last_price) if pos.last_price else 0

            print(f'{pos.symbol:10s} | {pos.position_type.value:6s} | {qty:>12,.2f} | ${price:>11,.2f} | ${mv:>14,.0f} | {pct:>11.2f}%')

        print('-' * 100)
        print(f'{"TOTAL":10s} | {"":6s} | {"":>12s} | {"":>12s} | ${total_value:>14,.0f} | {100.00:>11.2f}%')

        # Analyze by symbol type
        print(f'\n\nSymbol Analysis:')
        print(f'  Looking for patterns that might explain negative Quality Spread beta...')

        # Count by type
        options = [p for p in positions if p.position_type.value in ['LC', 'LP', 'SC', 'SP']]
        stocks = [p for p in positions if p.position_type.value in ['LONG', 'SHORT']]

        print(f'\n  Position Types:')
        print(f'    Stocks: {len(stocks)} positions')
        print(f'    Options: {len(options)} positions')

        # Check for speculative/growth stocks
        growth_symbols = ['TSLA', 'NVDA', 'AMZN', 'GOOGL', 'META', 'NFLX', 'AAPL']
        value_symbols = ['BRK', 'JPM', 'BAC', 'WFC', 'XOM', 'CVX', 'PG', 'JNJ', 'KO']

        growth_positions = [p for p in positions if any(g in p.symbol for g in growth_symbols)]
        value_positions = [p for p in positions if any(v in p.symbol for v in value_symbols)]

        growth_value = sum(float(p.market_value) for p in growth_positions if p.market_value)
        value_value = sum(float(p.market_value) for p in value_positions if p.market_value)

        print(f'\n  Growth vs Value Tilt:')
        print(f'    Growth stocks: {len(growth_positions)} positions, ${growth_value:,.0f} ({growth_value/total_value*100:.1f}%)')
        print(f'    Value stocks: {len(value_positions)} positions, ${value_value:,.0f} ({value_value/total_value*100:.1f}%)')

        # Check concentration
        top_5_value = sum(float(p.market_value) for p in positions[:5] if p.market_value)
        print(f'\n  Concentration:')
        print(f'    Top 5 positions: ${top_5_value:,.0f} ({top_5_value/total_value*100:.1f}%)')

        # Hypothesis check
        print(f'\n\nHYPOTHESIS TESTING:')
        print(f'  Quality Spread Beta: -1.0815 (very negative)')
        print(f'  This means: When QUAL outperforms SPY, portfolio underperforms')
        print(f'\n  Possible explanations:')

        if len(growth_positions) > len(value_positions) and growth_value > value_value:
            print(f'    [✓] Portfolio is GROWTH-TILTED ({growth_value/total_value*100:.1f}% growth vs {value_value/total_value*100:.1f}% value)')
            print(f'        Growth stocks often have LOWER quality metrics (lower ROE, higher debt)')
            print(f'        This would explain negative Quality Spread beta!')
        elif len(options) > 5:
            print(f'    [✓] Portfolio contains {len(options)} OPTIONS positions')
            print(f'        Options are speculative and have low quality characteristics')
            print(f'        This could explain negative Quality Spread beta')
        else:
            print(f'    [?] Portfolio composition doesn\'t obviously explain the negative beta')

        # Check if the dollar amount makes sense
        print(f'\n\nDOLLAR EXPOSURE SANITY CHECK:')
        print(f'  Quality Spread Beta: -1.0815')
        print(f'  Portfolio Equity: $4,295,815')
        print(f'  Calculated Dollar Exposure: -1.0815 × $4,295,815 = ${-1.0815 * 4295815:,.0f}')
        print(f'  Stored Dollar Exposure: $-4,645,786')
        print(f'  Difference: ${abs(-1.0815 * 4295815 - (-4645786)):,.0f}')

        expected = -1.0815 * 4295815
        actual = -4645786
        if abs(expected - actual) < 10000:
            print(f'\n  [✓] Dollar exposure calculation is CORRECT (beta × equity)')
        else:
            print(f'\n  [!] Dollar exposure doesn\'t match beta × equity')
            print(f'      This suggests exposure_dollar might be calculated differently')

asyncio.run(check_holdings())
