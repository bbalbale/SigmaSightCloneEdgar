#!/usr/bin/env python3
"""
Debug Date Alignment between Treasury and Position Data
Figure out why regression_days = 0 when we have data for both
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta
from fredapi import Fred
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.calculations.factors import calculate_position_returns, fetch_historical_prices
from app.config import settings
from app.constants.factors import REGRESSION_WINDOW_DAYS
from sqlalchemy import select, and_
from app.models.users import Portfolio
from app.models.positions import Position

async def debug_date_alignment():
    """Debug why Treasury and position data don't overlap"""
    print("\n" + "="*80)
    print("Date Alignment Debug - Treasury vs Position Data")
    print("="*80)
    
    # 1. Check Treasury data date range
    print("\n📊 1. Treasury Data (from FRED)")
    print("-" * 40)
    
    fred = Fred(api_key=settings.FRED_API_KEY)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=REGRESSION_WINDOW_DAYS + 30)  # 252 + 30 days
    
    print(f"Requesting Treasury data: {start_date} to {end_date}")
    print(f"Total days requested: {(end_date - start_date).days}")
    
    treasury_data = fred.get_series(
        'DGS10',  # 10-Year Treasury
        observation_start=start_date,
        observation_end=end_date
    )
    
    print(f"\nTreasury data received:")
    print(f"  Data points: {len(treasury_data)}")
    print(f"  Date range: {treasury_data.index[0].date()} to {treasury_data.index[-1].date()}")
    print(f"  First 5 dates: {[d.date() for d in treasury_data.index[:5]]}")
    print(f"  Last 5 dates: {[d.date() for d in treasury_data.index[-5:]]}")
    
    # Convert to daily changes
    treasury_changes = treasury_data.pct_change(fill_method=None).dropna() * 10000
    print(f"\nTreasury changes (for regression):")
    print(f"  Data points: {len(treasury_changes)}")
    print(f"  Date range: {treasury_changes.index[0].date()} to {treasury_changes.index[-1].date()}")
    
    # 2. Check position returns date range
    print("\n📊 2. Position Returns Data")
    print("-" * 40)
    
    async with AsyncSessionLocal() as db:
        # Get a demo portfolio
        stmt = select(Portfolio).where(
            Portfolio.name == 'Demo Growth Investor Portfolio'
        ).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("❌ Demo portfolio not found")
            return
        
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        
        # Calculate position returns (same as in market_risk.py)
        position_returns = await calculate_position_returns(
            db=db,
            portfolio_id=portfolio.id,
            start_date=start_date,
            end_date=end_date,
            use_delta_adjusted=False
        )
        
        if position_returns.empty:
            print("❌ No position returns data")
            
            # Let's check what's in fetch_historical_prices
            stmt = select(Position).where(
                and_(
                    Position.portfolio_id == portfolio.id,
                    Position.exit_date.is_(None)
                )
            )
            result = await db.execute(stmt)
            positions = result.scalars().all()
            
            if positions:
                symbols = list(set(p.symbol for p in positions))
                print(f"\nDirect price fetch for symbols: {symbols[:5]}")
                
                price_df = await fetch_historical_prices(
                    db=db,
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if price_df.empty:
                    print("❌ fetch_historical_prices returned empty DataFrame")
                else:
                    print(f"✅ Price data shape: {price_df.shape}")
                    print(f"   Date range: {price_df.index[0]} to {price_df.index[-1]}")
                    print(f"   Symbols: {list(price_df.columns)[:5]}")
        else:
            print(f"\nPosition returns received:")
            print(f"  Shape: {position_returns.shape}")
            print(f"  Date range: {position_returns.index[0]} to {position_returns.index[-1]}")
            print(f"  First 5 dates: {position_returns.index[:5].tolist()}")
            print(f"  Last 5 dates: {position_returns.index[-5:].tolist()}")
            
            # Check data types
            print(f"\nData type check:")
            print(f"  Treasury index type: {type(treasury_changes.index)}")
            print(f"  Position index type: {type(position_returns.index)}")
            
            # 3. Find overlapping dates
            print("\n📊 3. Date Overlap Analysis")
            print("-" * 40)
            
            # Convert to same date type for comparison
            treasury_dates = set(treasury_changes.index.date)
            position_dates = set(position_returns.index)
            
            if isinstance(position_returns.index[0], pd.Timestamp):
                position_dates = set(position_returns.index.date)
            
            common_dates = treasury_dates.intersection(position_dates)
            
            print(f"Treasury dates: {len(treasury_dates)}")
            print(f"Position dates: {len(position_dates)}")
            print(f"Common dates: {len(common_dates)}")
            
            if len(common_dates) > 0:
                common_dates_list = sorted(list(common_dates))
                print(f"  First common date: {common_dates_list[0]}")
                print(f"  Last common date: {common_dates_list[-1]}")
            else:
                print("  ❌ No overlapping dates!")
                
                # Find the gap
                latest_position = max(position_dates) if position_dates else None
                earliest_treasury = min(treasury_dates) if treasury_dates else None
                
                if latest_position and earliest_treasury:
                    gap_days = (earliest_treasury - latest_position).days
                    print(f"\n  Gap analysis:")
                    print(f"    Latest position date: {latest_position}")
                    print(f"    Earliest treasury date: {earliest_treasury}")
                    print(f"    Gap: {gap_days} days")
                    
                    if gap_days > 0:
                        print(f"    ⚠️ Position data ends {gap_days} days before Treasury data starts!")
            
            # 4. Check actual alignment code
            print("\n📊 4. Alignment Code Check")
            print("-" * 40)
            
            # This mimics what happens in calculate_position_interest_rate_betas
            common_dates_intersect = treasury_changes.index.intersection(position_returns.index)
            print(f"Using pandas intersection: {len(common_dates_intersect)} common dates")
            
            if len(common_dates_intersect) == 0:
                print("\n⚠️ PROBLEM IDENTIFIED:")
                print("  The pandas intersection is returning 0 dates")
                print("  This explains why regression_days = 0")
                
                # Check index types
                print(f"\n  Index type mismatch?")
                print(f"    Treasury: {treasury_changes.index.dtype}")
                print(f"    Position: {position_returns.index.dtype}")
                
                # Try to find the issue
                if hasattr(treasury_changes.index[0], 'date'):
                    print(f"    Treasury sample: {treasury_changes.index[0]} (has time component)")
                if hasattr(position_returns.index[0], 'date'):
                    print(f"    Position sample: {position_returns.index[0]} (has time component)")


if __name__ == "__main__":
    asyncio.run(debug_date_alignment())