#!/usr/bin/env python3
"""
Deep Analysis: Why Calculation Engines Aren't Populating Demo Portfolio Data
"""
import sys
from pathlib import Path
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.models.users import Portfolio, User
from app.models.positions import Position
from app.models.market_data import PositionGreeks, PositionFactorExposure, MarketDataCache
from app.models.correlations import CorrelationCalculation
from app.models.snapshots import PortfolioSnapshot
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload


async def analyze_demo_portfolios():
    """Analyze why calculation engines aren't working for demo portfolios"""
    
    async with get_async_session() as db:
        print('🔍 ANALYZING WHY CALCULATION ENGINES FAIL FOR DEMO PORTFOLIOS')
        print('=' * 80)
        
        # Get our 3 demo portfolios
        demo_emails = [
            'demo_individual@sigmasight.com',
            'demo_hnw@sigmasight.com', 
            'demo_hedgefundstyle@sigmasight.com'
        ]
        
        for email in demo_emails:
            print(f'\n📊 PORTFOLIO: {email}')
            print('-' * 50)
            
            # Get portfolio with user and positions
            stmt = select(Portfolio).join(User).options(
                selectinload(Portfolio.positions)
            ).where(User.email == email)
            result = await db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                print(f'❌ Portfolio not found')
                continue
            
            portfolio_id = str(portfolio.id)
            positions_count = len(portfolio.positions)
            
            print(f'   ID: {portfolio_id}')
            print(f'   Positions: {positions_count}')
            
            # Check if any calculation engine data exists for this portfolio
            print(f'\n🔧 CALCULATION ENGINE DATA:')
            
            # 1. Greeks data (via position joins)
            stmt = select(PositionGreeks).join(Position).where(Position.portfolio_id == portfolio_id)
            result = await db.execute(stmt)
            greeks_records = result.scalars().all()
            print(f'   Greeks Records: {len(greeks_records)}')
            
            # 2. Factor exposures (via position joins)
            stmt = select(PositionFactorExposure).join(Position).where(Position.portfolio_id == portfolio_id)
            result = await db.execute(stmt)
            factor_records = result.scalars().all()
            print(f'   Factor Records: {len(factor_records)}')
            
            # 3. Correlations
            stmt = select(CorrelationCalculation).where(CorrelationCalculation.portfolio_id == portfolio_id)
            result = await db.execute(stmt)
            correlation_records = result.scalars().all()
            print(f'   Correlation Records: {len(correlation_records)}')
            
            # 4. Snapshots
            stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio_id)
            result = await db.execute(stmt)
            snapshot_records = result.scalars().all()
            print(f'   Snapshot Records: {len(snapshot_records)}')
            
            # Look at individual positions for clues
            print(f'\n📈 SAMPLE POSITIONS (first 3):')
            for i, pos in enumerate(portfolio.positions[:3], 1):
                print(f'   {i}. {pos.symbol}: qty={pos.quantity}, type={pos.position_type}, last_price={pos.last_price}')
                
                # Check if this position has ANY calculation data
                stmt = select(PositionGreeks).where(PositionGreeks.position_id == pos.id)
                result = await db.execute(stmt)
                pos_greeks = result.scalar_one_or_none()
                
                stmt = select(PositionFactorExposure).where(PositionFactorExposure.position_id == pos.id)
                result = await db.execute(stmt)
                pos_factors = result.scalars().all()
                
                # Check market data for this symbol
                stmt = select(MarketDataCache).where(MarketDataCache.symbol == pos.symbol.upper()).limit(1)
                result = await db.execute(stmt)
                market_data = result.scalar_one_or_none()
                
                greeks_status = 'YES' if pos_greeks else 'NO'
                factors_status = f'{len(pos_factors)} records' if pos_factors else 'NO'
                market_status = 'YES' if market_data else 'NO'
                
                print(f'      Greeks: {greeks_status}, Factors: {factors_status}, Market Data: {market_status}')
        
        print(f'\n🔍 ROOT CAUSE ANALYSIS:')
        print('-' * 50)
        
        # Check all portfolios in the database
        stmt = select(Portfolio.id, Portfolio.name, func.count(Position.id).label('position_count')).outerjoin(Position).group_by(Portfolio.id, Portfolio.name)
        result = await db.execute(stmt)
        all_portfolios = result.all()
        
        print(f'📊 ALL PORTFOLIOS IN DATABASE:')
        for port in all_portfolios:
            port_id_str = str(port.id)
            
            # Check if this portfolio has calculation data
            stmt = select(func.count(PositionGreeks.id)).join(Position).where(Position.portfolio_id == port.id)
            result = await db.execute(stmt)
            greeks_count = result.scalar() or 0
            
            stmt = select(func.count(PositionFactorExposure.id)).join(Position).where(Position.portfolio_id == port.id)
            result = await db.execute(stmt)
            factors_count = result.scalar() or 0
            
            is_demo = 'DEMO' if port.name and 'Demo' in port.name else 'other'
            print(f'   {is_demo:5s} | {port_id_str[:8]}... | {port.position_count:2d} pos | {greeks_count:2d} greeks | {factors_count:3d} factors | {port.name}')
        
        # Check for any successful calculation data anywhere
        print(f'\n🔢 TOTAL CALCULATION DATA IN DATABASE:')
        stmt = select(func.count(PositionGreeks.id))
        result = await db.execute(stmt)
        total_greeks = result.scalar() or 0
        
        stmt = select(func.count(PositionFactorExposure.id))
        result = await db.execute(stmt)
        total_factors = result.scalar() or 0
        
        stmt = select(func.count(CorrelationCalculation.id))
        result = await db.execute(stmt)
        total_correlations = result.scalar() or 0
        
        print(f'   Total Greeks: {total_greeks}')
        print(f'   Total Factors: {total_factors}')
        print(f'   Total Correlations: {total_correlations}')
        
        if total_greeks == 0 and total_factors == 0 and total_correlations == 0:
            print(f'\n❌ CONCLUSION: NO CALCULATION ENGINE DATA EXISTS FOR ANY PORTFOLIO')
            print(f'   This means the batch calculation engines are failing to create/save data')
            print(f'   The 85.7% success rate is likely for other job types (market data, portfolio aggregation)')
        else:
            print(f'\n⚠️ CONCLUSION: CALCULATION DATA EXISTS BUT NOT FOR DEMO PORTFOLIOS')
            print(f'   This suggests demo portfolios have specific issues preventing calculations')


if __name__ == "__main__":
    asyncio.run(analyze_demo_portfolios())