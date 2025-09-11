#!/usr/bin/env python3
"""
Check factor exposures data in the database for a specific portfolio.
"""

import asyncio
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.market_data import FactorExposure, PositionFactorExposure
from app.models.users import Portfolio
from app.models.positions import Position
import json
from datetime import datetime

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


PORTFOLIO_ID = "e23ab931-a033-edfe-ed4f-9d02474780b4"

async def check_factor_exposures():
    """Check what factor exposure data exists for the portfolio."""
    
    async with AsyncSessionLocal() as session:
        portfolio_uuid = UUID(PORTFOLIO_ID)
        
        print(f"\n{'='*80}")
        print(f"Factor Exposures Analysis for Portfolio: {PORTFOLIO_ID}")
        print(f"{'='*80}\n")
        
        # 1. Check if portfolio exists
        portfolio = await session.get(Portfolio, portfolio_uuid)
        if not portfolio:
            print(f"❌ Portfolio not found!")
            return
        
        print(f"✅ Portfolio found: {portfolio.name}")
        print(f"   User ID: {portfolio.user_id}")
        print(f"   Created: {portfolio.created_at}")
        
        # 2. Check portfolio-level factor exposures
        print(f"\n📊 PORTFOLIO-LEVEL FACTOR EXPOSURES:")
        print("-" * 40)
        
        query = select(FactorExposure).options(
            selectinload(FactorExposure.factor)
        ).where(
            FactorExposure.portfolio_id == portfolio_uuid
        ).order_by(FactorExposure.calculation_date.desc())
        
        result = await session.execute(query)
        portfolio_exposures = result.scalars().all()
        
        if not portfolio_exposures:
            print("❌ No portfolio-level factor exposures found")
        else:
            print(f"✅ Found {len(portfolio_exposures)} portfolio factor exposure records")
            
            # Group by calculation date
            dates = {}
            for exp in portfolio_exposures:
                date_str = exp.calculation_date.strftime("%Y-%m-%d") if exp.calculation_date else "None"
                if date_str not in dates:
                    dates[date_str] = []
                dates[date_str].append(exp)
            
            for date_str, exps in sorted(dates.items(), reverse=True)[:3]:  # Show last 3 dates
                print(f"\n   📅 Date: {date_str}")
                print(f"   Factors ({len(exps)}):")
                for exp in exps[:10]:  # Show first 10 factors
                    contribution = getattr(exp, 'contribution', None)
                    print(f"      • {exp.factor.name}: {exp.exposure_value:.4f} (dollar: {exp.exposure_dollar or 0:.2f})")
                if len(exps) > 10:
                    print(f"      ... and {len(exps) - 10} more factors")
        
        # 3. Check position-level factor exposures
        print(f"\n📊 POSITION-LEVEL FACTOR EXPOSURES:")
        print("-" * 40)
        
        # Get positions for this portfolio
        positions_query = select(Position).where(Position.portfolio_id == portfolio_uuid)
        positions_result = await session.execute(positions_query)
        positions = positions_result.scalars().all()
        
        print(f"Portfolio has {len(positions)} positions")
        
        # Check position factor exposures
        pos_exp_query = select(PositionFactorExposure).options(
            selectinload(PositionFactorExposure.factor)
        ).join(
            Position, PositionFactorExposure.position_id == Position.id
        ).where(
            Position.portfolio_id == portfolio_uuid
        ).order_by(PositionFactorExposure.calculation_date.desc())
        
        pos_exp_result = await session.execute(pos_exp_query)
        position_exposures = pos_exp_result.scalars().all()
        
        if not position_exposures:
            print("❌ No position-level factor exposures found")
        else:
            print(f"✅ Found {len(position_exposures)} position factor exposure records")
            
            # Group by calculation date
            pos_dates = {}
            for exp in position_exposures:
                date_str = exp.calculation_date.strftime("%Y-%m-%d") if exp.calculation_date else "None"
                if date_str not in pos_dates:
                    pos_dates[date_str] = {}
                pos_id = str(exp.position_id)
                if pos_id not in pos_dates[date_str]:
                    pos_dates[date_str][pos_id] = []
                pos_dates[date_str][pos_id].append(exp)
            
            for date_str in sorted(pos_dates.keys(), reverse=True)[:2]:  # Show last 2 dates
                print(f"\n   📅 Date: {date_str}")
                positions_on_date = pos_dates[date_str]
                print(f"   Positions with exposures: {len(positions_on_date)}")
                
                # Show first 3 positions
                for i, (pos_id, exps) in enumerate(list(positions_on_date.items())[:3]):
                    # Get position details
                    position = await session.get(Position, UUID(pos_id))
                    if position:
                        print(f"\n      Position: {position.symbol} (ID: {pos_id[:8]}...)")
                        print(f"      Factors ({len(exps)}):")
                        for exp in exps[:5]:  # Show first 5 factors per position
                            print(f"         • {exp.factor.name}: {exp.exposure_value:.4f}")
                        if len(exps) > 5:
                            print(f"         ... and {len(exps) - 5} more factors")
        
        # 4. Check for calculation date consistency
        print(f"\n📅 CALCULATION DATE ANALYSIS:")
        print("-" * 40)
        
        # Get unique calculation dates for portfolio exposures
        portfolio_dates_query = select(
            func.distinct(FactorExposure.calculation_date)
        ).where(
            FactorExposure.portfolio_id == portfolio_uuid
        ).order_by(FactorExposure.calculation_date.desc())
        
        portfolio_dates_result = await session.execute(portfolio_dates_query)
        portfolio_dates = [d[0] for d in portfolio_dates_result.all() if d[0]]
        
        print(f"Portfolio-level calculation dates: {len(portfolio_dates)}")
        for date in portfolio_dates[:5]:
            print(f"   • {date.strftime('%Y-%m-%d')}")
        
        # Get unique calculation dates for position exposures
        position_dates_query = select(
            func.distinct(PositionFactorExposure.calculation_date)
        ).join(
            Position, PositionFactorExposure.position_id == Position.id
        ).where(
            Position.portfolio_id == portfolio_uuid
        ).order_by(PositionFactorExposure.calculation_date.desc())
        
        position_dates_result = await session.execute(position_dates_query)
        position_dates = [d[0] for d in position_dates_result.all() if d[0]]
        
        print(f"\nPosition-level calculation dates: {len(position_dates)}")
        for date in position_dates[:5]:
            print(f"   • {date.strftime('%Y-%m-%d')}")
        
        # 5. Check for complete factor sets
        print(f"\n✅ COMPLETE FACTOR SET CHECK:")
        print("-" * 40)
        
        # Expected factors (from your factor model)
        expected_factors = [
            "Market Beta",
            "Size",
            "Value",
            "Momentum",
            "Quality",
            "Low Volatility",
            "Growth"
        ]
        
        for date in portfolio_dates[:3]:
            date_str = date.strftime("%Y-%m-%d")
            
            # Count factors for this date
            factor_count_query = select(
                func.count(func.distinct(FactorExposure.factor_id))
            ).where(
                FactorExposure.portfolio_id == portfolio_uuid,
                FactorExposure.calculation_date == date
            )
            
            factor_count_result = await session.execute(factor_count_query)
            factor_count = factor_count_result.scalar()
            
            # Get actual factor names
            factor_names_query = select(FactorExposure).options(
                selectinload(FactorExposure.factor)
            ).where(
                FactorExposure.portfolio_id == portfolio_uuid,
                FactorExposure.calculation_date == date
            ).distinct(FactorExposure.factor_id)
            
            factor_names_result = await session.execute(factor_names_query)
            factor_exposures = factor_names_result.scalars().all()
            factor_names = [exp.factor.name for exp in factor_exposures]
            
            print(f"\n   Date: {date_str}")
            print(f"   Factor count: {factor_count}/{len(expected_factors)}")
            print(f"   Factors present: {', '.join(factor_names)}")
            
            missing = set(expected_factors) - set(factor_names)
            if missing:
                print(f"   ❌ Missing factors: {', '.join(missing)}")
            else:
                print(f"   ✅ All expected factors present!")
        
        print(f"\n{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(check_factor_exposures())