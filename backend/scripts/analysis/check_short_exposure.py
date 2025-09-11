"""
Check short position exposures in Demo Hedge Fund portfolio
"""
import asyncio
from app.database import get_async_session
from app.models.positions import Position, PositionType
from sqlalchemy import select, and_
from uuid import UUID

async def check_shorts():
    portfolio_id = UUID('2ee7435f-379f-4606-bdb7-dadce587a182')  # Demo Hedge Fund
    
    async with get_async_session() as db:
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.deleted_at.is_(None)
            )
        ).order_by(Position.symbol)
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        print(f'Demo Hedge Fund positions ({len(positions)} total):')
        print('-' * 80)
        
        for pos in positions:
            if pos.position_type in [PositionType.SHORT, PositionType.SC, PositionType.SP]:
                print(f'  SHORT: {pos.symbol:10} qty={pos.quantity:8.0f} mkt_val=${pos.market_value:12,.2f} type={pos.position_type.value}')
            else:
                print(f'  LONG:  {pos.symbol:10} qty={pos.quantity:8.0f} mkt_val=${pos.market_value:12,.2f} type={pos.position_type.value}')
                
        # Summary
        shorts = [p for p in positions if p.position_type in [PositionType.SHORT, PositionType.SC, PositionType.SP]]
        longs = [p for p in positions if p.position_type not in [PositionType.SHORT, PositionType.SC, PositionType.SP]]
        
        short_exposure = sum(float(p.market_value) for p in shorts)
        long_exposure = sum(float(p.market_value) for p in longs)
        
        print('-' * 80)
        print(f'Summary:')
        print(f'  Long positions: {len(longs)}, exposure: ${long_exposure:,.2f}')
        print(f'  Short positions: {len(shorts)}, exposure: ${short_exposure:,.2f}')
        print(f'  Net exposure: ${long_exposure + short_exposure:,.2f}')
        print(f'  Gross exposure: ${abs(long_exposure) + abs(short_exposure):,.2f}')
            
if __name__ == "__main__":
    asyncio.run(check_shorts())