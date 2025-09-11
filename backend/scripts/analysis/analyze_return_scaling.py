"""
Deep dive into the return scaling issue
"""
import asyncio
import numpy as np
import pandas as pd
from datetime import date, timedelta
from uuid import UUID
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.constants.factors import FACTOR_ETFS
import statsmodels.api as sm

async def analyze_return_scaling():
    """
    Analyze why position returns don't match factor returns scale
    """
    print("=" * 80)
    print("RETURN SCALING ANALYSIS")
    print("=" * 80)
    
    portfolio_id = UUID('51134ffd-2f13-49bd-b1f5-0c327e801b69')  # Demo Individual
    
    async with get_async_session() as db:
        # Get a specific position to analyze
        pos_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.symbol == 'AAPL',  # Use a well-known stock
                Position.deleted_at.is_(None)
            )
        )
        pos_result = await db.execute(pos_stmt)
        aapl_position = pos_result.scalar_one_or_none()
        
        if not aapl_position:
            # Try another symbol
            pos_stmt = select(Position).where(
                and_(
                    Position.portfolio_id == portfolio_id,
                    Position.deleted_at.is_(None)
                )
            ).limit(1)
            pos_result = await db.execute(pos_stmt)
            aapl_position = pos_result.scalar_one_or_none()
        
        if aapl_position:
            print(f"\n1. ANALYZING POSITION: {aapl_position.symbol}")
            print("-" * 40)
            print(f"Position ID: {aapl_position.id}")
            print(f"Quantity: {aapl_position.quantity}")
            print(f"Entry Price: {aapl_position.entry_price}")
            print(f"Last Price: {aapl_position.last_price}")
            
            # Get price history
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            price_stmt = select(MarketDataCache).where(
                and_(
                    MarketDataCache.symbol == aapl_position.symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= end_date
                )
            ).order_by(MarketDataCache.date)
            
            price_result = await db.execute(price_stmt)
            prices = price_result.scalars().all()
            
            if prices:
                print(f"\n2. PRICE DATA ANALYSIS")
                print("-" * 40)
                price_data = [(p.date, float(p.close)) for p in prices]
                df = pd.DataFrame(price_data, columns=['date', 'price'])
                df.set_index('date', inplace=True)
                
                print(f"Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
                print(f"Data points: {len(df)}")
                
                # Calculate returns different ways
                print(f"\n3. RETURN CALCULATIONS COMPARISON")
                print("-" * 40)
                
                # Method 1: Simple percentage change
                simple_returns = df['price'].pct_change().dropna()
                print(f"Simple pct_change():")
                print(f"  Mean: {simple_returns.mean():.6f}")
                print(f"  Std:  {simple_returns.std():.6f}")
                print(f"  Min:  {simple_returns.min():.6f}")
                print(f"  Max:  {simple_returns.max():.6f}")
                
                # Method 2: Log returns
                log_returns = np.log(df['price'] / df['price'].shift(1)).dropna()
                print(f"\nLog returns:")
                print(f"  Mean: {log_returns.mean():.6f}")
                print(f"  Std:  {log_returns.std():.6f}")
                print(f"  Min:  {log_returns.min():.6f}")
                print(f"  Max:  {log_returns.max():.6f}")
                
                # Method 3: Dollar-weighted returns (considering position size)
                position_value = df['price'] * float(aapl_position.quantity)
                dollar_returns = position_value.pct_change().dropna()
                print(f"\nDollar-weighted returns (position level):")
                print(f"  Mean: {dollar_returns.mean():.6f}")
                print(f"  Std:  {dollar_returns.std():.6f}")
                print(f"  Min:  {dollar_returns.min():.6f}")
                print(f"  Max:  {dollar_returns.max():.6f}")
                
                # Check if any look unusual
                if simple_returns.max() > 0.2 or simple_returns.min() < -0.2:
                    print("\n⚠️  WARNING: Returns > 20% detected - possible data issue")
        
        # Now check how factor returns are calculated
        print(f"\n4. FACTOR RETURN CALCULATION CHECK")
        print("-" * 40)
        
        # Get SPY (market factor) data
        spy_stmt = select(MarketDataCache).where(
            and_(
                MarketDataCache.symbol == 'SPY',
                MarketDataCache.date >= start_date,
                MarketDataCache.date <= end_date
            )
        ).order_by(MarketDataCache.date)
        
        spy_result = await db.execute(spy_stmt)
        spy_prices = spy_result.scalars().all()
        
        if spy_prices:
            spy_data = [(p.date, float(p.close)) for p in spy_prices]
            spy_df = pd.DataFrame(spy_data, columns=['date', 'price'])
            spy_df.set_index('date', inplace=True)
            
            spy_returns = spy_df['price'].pct_change().dropna()
            print(f"SPY (Market Factor) Returns:")
            print(f"  Mean: {spy_returns.mean():.6f}")
            print(f"  Std:  {spy_returns.std():.6f}")
            print(f"  Min:  {spy_returns.min():.6f}")
            print(f"  Max:  {spy_returns.max():.6f}")
        
        # Compare returns from calculate_position_returns
        print(f"\n5. CHECKING calculate_position_returns() OUTPUT")
        print("-" * 40)
        
        from app.calculations.factors import calculate_position_returns
        
        calc_end_date = date.today()
        calc_start_date = calc_end_date - timedelta(days=30)
        
        position_returns = await calculate_position_returns(
            db=db,
            portfolio_id=portfolio_id,
            start_date=calc_start_date,
            end_date=calc_end_date,
            use_delta_adjusted=False
        )
        
        if not position_returns.empty:
            # Check first position
            first_col = position_returns.columns[0]
            first_returns = position_returns[first_col].dropna()
            
            print(f"Position {str(first_col)[:8]}... returns from function:")
            print(f"  Mean: {first_returns.mean():.6f}")
            print(f"  Std:  {first_returns.std():.6f}")
            print(f"  Min:  {first_returns.min():.6f}")
            print(f"  Max:  {first_returns.max():.6f}")
            print(f"  Shape: {position_returns.shape}")
            
            # Check for scaling issues
            if first_returns.max() > 1:
                print("\n⚠️  ISSUE FOUND: Returns > 1.0 detected!")
                print("  This suggests returns are being calculated on DOLLAR VALUES")
                print("  not on PRICES, causing inflated betas")
        
        # Test regression with properly scaled returns
        print(f"\n6. TEST REGRESSION WITH CORRECT SCALING")
        print("-" * 40)
        
        if aapl_position and spy_prices and prices:
            # Align dates
            aapl_dates = set(p.date for p in prices)
            spy_dates = set(p.date for p in spy_prices)
            common_dates = sorted(aapl_dates & spy_dates)
            
            if len(common_dates) > 10:
                # Build aligned series
                aapl_prices = {p.date: float(p.close) for p in prices}
                spy_prices_dict = {p.date: float(p.close) for p in spy_prices}
                
                aapl_series = [aapl_prices[d] for d in common_dates]
                spy_series = [spy_prices_dict[d] for d in common_dates]
                
                # Calculate returns
                aapl_ret = pd.Series(aapl_series).pct_change().dropna().values
                spy_ret = pd.Series(spy_series).pct_change().dropna().values
                
                # Ensure same length
                min_len = min(len(aapl_ret), len(spy_ret))
                aapl_ret = aapl_ret[:min_len]
                spy_ret = spy_ret[:min_len]
                
                # Run regression
                X = sm.add_constant(spy_ret)
                model = sm.OLS(aapl_ret, X).fit()
                
                beta = model.params[1] if len(model.params) > 1 else 0
                
                print(f"Regression: {aapl_position.symbol} vs SPY")
                print(f"  Beta (correctly scaled): {beta:.4f}")
                print(f"  R-squared: {model.rsquared:.4f}")
                print(f"  Data points: {min_len}")
                
                if abs(beta) > 2:
                    print(f"\n⚠️  Beta still high even with correct scaling!")
                    print(f"  Possible reasons:")
                    print(f"  1. {aapl_position.symbol} is a leveraged ETF")
                    print(f"  2. Data quality issues")
                    print(f"  3. Short time period")
                else:
                    print(f"\n✅ Beta looks reasonable with correct scaling")
        
        print("\n" + "=" * 80)
        print("CONCLUSION")
        print("=" * 80)
        print("\nThe issue appears to be in calculate_position_returns():")
        print("It's calculating returns on POSITION VALUES (quantity × price)")
        print("instead of just PRICE returns.")
        print("\nThis causes inflated returns when positions are large,")
        print("leading to inflated betas in the regression.")

if __name__ == "__main__":
    asyncio.run(analyze_return_scaling())