"""
Investigate why factor betas are unrealistically large
"""
import asyncio
import numpy as np
import pandas as pd
from datetime import date, timedelta
from uuid import UUID
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.positions import Position
from app.models.market_data import MarketDataCache, PositionFactorExposure, FactorDefinition
from app.calculations.factors import fetch_factor_returns, calculate_position_returns
from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS
import statsmodels.api as sm

async def investigate_betas():
    """
    Deep dive into beta calculation issues
    """
    print("=" * 80)
    print("FACTOR BETA INVESTIGATION")
    print("=" * 80)
    
    portfolio_id = UUID('51134ffd-2f13-49bd-b1f5-0c327e801b69')  # Demo Individual
    calculation_date = date.today()
    
    async with get_async_session() as db:
        # 1. Check stored betas distribution
        print("\n1. STORED BETA VALUES ANALYSIS")
        print("-" * 40)
        
        # Get all position factor exposures for today
        pfe_stmt = select(PositionFactorExposure, FactorDefinition).join(
            FactorDefinition, PositionFactorExposure.factor_id == FactorDefinition.id
        ).where(
            PositionFactorExposure.calculation_date == calculation_date
        ).limit(500)
        
        pfe_result = await db.execute(pfe_stmt)
        exposures = pfe_result.all()
        
        if exposures:
            # Analyze beta distribution by factor
            beta_by_factor = {}
            for pfe, fd in exposures:
                if fd.name not in beta_by_factor:
                    beta_by_factor[fd.name] = []
                beta_by_factor[fd.name].append(float(pfe.exposure_value))
            
            print(f"Total exposure records: {len(exposures)}")
            print("\nBeta Distribution by Factor:")
            print(f"{'Factor':<20} {'Count':<6} {'Min':<8} {'Max':<8} {'Mean':<8} {'Std':<8} {'# at ±3':<8}")
            print("-" * 80)
            
            for factor_name, betas in beta_by_factor.items():
                betas_array = np.array(betas)
                at_cap = np.sum(np.abs(betas_array) >= 2.99)
                print(f"{factor_name:<20} {len(betas):<6} {np.min(betas):<8.3f} {np.max(betas):<8.3f} "
                      f"{np.mean(betas):<8.3f} {np.std(betas):<8.3f} {at_cap:<8}")
            
            # Check for extreme values
            all_betas = [b for betas in beta_by_factor.values() for b in betas]
            extreme_betas = [b for b in all_betas if abs(b) > 2]
            print(f"\n⚠️  Extreme betas (|β| > 2): {len(extreme_betas)}/{len(all_betas)} "
                  f"({100*len(extreme_betas)/len(all_betas):.1f}%)")
        
        # 2. Analyze factor returns
        print("\n2. FACTOR ETF RETURNS ANALYSIS")
        print("-" * 40)
        
        end_date = calculation_date
        start_date = end_date - timedelta(days=REGRESSION_WINDOW_DAYS + 30)
        
        factor_symbols = list(FACTOR_ETFS.values())
        factor_returns = await fetch_factor_returns(
            db=db,
            symbols=factor_symbols,
            start_date=start_date,
            end_date=end_date
        )
        
        if not factor_returns.empty:
            print(f"Factor returns shape: {factor_returns.shape}")
            print(f"Date range: {factor_returns.index[0]} to {factor_returns.index[-1]}")
            print(f"Trading days: {len(factor_returns)}")
            
            print("\nFactor Returns Statistics:")
            print(f"{'Factor':<20} {'Mean':<10} {'Std':<10} {'Min':<10} {'Max':<10}")
            print("-" * 60)
            
            for col in factor_returns.columns:
                returns = factor_returns[col].dropna()
                print(f"{col:<20} {returns.mean():<10.6f} {returns.std():<10.6f} "
                      f"{returns.min():<10.6f} {returns.max():<10.6f}")
            
            # Check if returns look like percentages or decimals
            all_returns = factor_returns.values.flatten()
            all_returns = all_returns[~np.isnan(all_returns)]
            if np.max(np.abs(all_returns)) > 1:
                print("\n⚠️  WARNING: Factor returns appear to be in percentage form (>1)")
            else:
                print("\n✅ Factor returns appear to be in decimal form (<1)")
        
        # 3. Analyze position returns
        print("\n3. POSITION RETURNS ANALYSIS")
        print("-" * 40)
        
        position_returns = await calculate_position_returns(
            db=db,
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
            use_delta_adjusted=False
        )
        
        if not position_returns.empty:
            print(f"Position returns shape: {position_returns.shape}")
            print(f"Positions tracked: {len(position_returns.columns)}")
            
            # Sample a few positions
            sample_positions = position_returns.columns[:5]
            print("\nSample Position Returns Statistics:")
            print(f"{'Position ID':<40} {'Mean':<10} {'Std':<10} {'Min':<10} {'Max':<10}")
            print("-" * 80)
            
            for pos_id in sample_positions:
                returns = position_returns[pos_id].dropna()
                if len(returns) > 0:
                    print(f"{str(pos_id)[:38]:<40} {returns.mean():<10.6f} {returns.std():<10.6f} "
                          f"{returns.min():<10.6f} {returns.max():<10.6f}")
            
            # Check if returns look like percentages or decimals
            all_pos_returns = position_returns.values.flatten()
            all_pos_returns = all_pos_returns[~np.isnan(all_pos_returns)]
            if len(all_pos_returns) > 0:
                if np.max(np.abs(all_pos_returns)) > 1:
                    print("\n⚠️  WARNING: Position returns appear to be in percentage form (>1)")
                else:
                    print("\n✅ Position returns appear to be in decimal form (<1)")
        
        # 4. Test a simple regression
        print("\n4. TEST REGRESSION ANALYSIS")
        print("-" * 40)
        
        if not factor_returns.empty and not position_returns.empty:
            # Take first position and first factor
            sample_pos_id = position_returns.columns[0]
            sample_factor = factor_returns.columns[0]
            
            # Align data
            common_dates = factor_returns.index.intersection(position_returns.index)
            y = position_returns.loc[common_dates, sample_pos_id].values
            X = factor_returns.loc[common_dates, sample_factor].values
            
            # Remove NaN
            mask = ~(np.isnan(y) | np.isnan(X))
            y_clean = y[mask]
            X_clean = X[mask]
            
            if len(y_clean) > 30:
                # Run regression
                X_with_const = sm.add_constant(X_clean)
                model = sm.OLS(y_clean, X_with_const).fit()
                
                beta = model.params[1] if len(model.params) > 1 else 0
                
                print(f"Sample Regression: Position vs {sample_factor}")
                print(f"  Data points: {len(y_clean)}")
                print(f"  Beta: {beta:.4f}")
                print(f"  R-squared: {model.rsquared:.4f}")
                print(f"  P-value: {model.pvalues[1] if len(model.pvalues) > 1 else 'N/A':.4f}")
                
                # Check residuals
                residuals = model.resid
                print(f"  Residuals std: {np.std(residuals):.6f}")
                
                # Manual beta calculation for verification
                cov_xy = np.cov(X_clean, y_clean)[0, 1]
                var_x = np.var(X_clean)
                manual_beta = cov_xy / var_x if var_x > 0 else 0
                print(f"  Manual beta (cov/var): {manual_beta:.4f}")
                
                # Check if scaling issue
                if abs(beta) > 2:
                    print("\n⚠️  ISSUE: Beta > 2 detected!")
                    print("  Possible causes:")
                    print("  1. Returns are on different scales")
                    print("  2. Position has leverage")
                    print("  3. Data quality issues")
        
        # 5. Check for data quality issues
        print("\n5. DATA QUALITY CHECK")
        print("-" * 40)
        
        # Check for positions with extreme price changes
        pos_stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.deleted_at.is_(None)
            )
        )
        pos_result = await db.execute(pos_stmt)
        positions = pos_result.scalars().all()
        
        print(f"Checking {len(positions)} positions for data issues...")
        
        issues_found = []
        for pos in positions:
            # Get historical prices
            price_stmt = select(MarketDataCache).where(
                and_(
                    MarketDataCache.symbol == pos.symbol,
                    MarketDataCache.date >= start_date,
                    MarketDataCache.date <= end_date
                )
            ).order_by(MarketDataCache.date)
            
            price_result = await db.execute(price_stmt)
            prices = price_result.scalars().all()
            
            if len(prices) > 1:
                price_values = [float(p.close) for p in prices]
                price_series = pd.Series(price_values)
                returns = price_series.pct_change().dropna()
                
                if len(returns) > 0:
                    max_return = returns.max()
                    min_return = returns.min()
                    
                    # Check for extreme returns (>50% in a day is suspicious)
                    if abs(max_return) > 0.5 or abs(min_return) > 0.5:
                        issues_found.append({
                            'symbol': pos.symbol,
                            'max_return': max_return,
                            'min_return': min_return,
                            'price_count': len(prices)
                        })
        
        if issues_found:
            print(f"\n⚠️  Found {len(issues_found)} positions with extreme returns:")
            for issue in issues_found[:5]:
                print(f"  {issue['symbol']}: max={issue['max_return']:.2%}, min={issue['min_return']:.2%}")
        else:
            print("✅ No extreme price movements detected")
        
        # 6. Summary and recommendations
        print("\n" + "=" * 80)
        print("INVESTIGATION SUMMARY")
        print("=" * 80)
        
        print("\n📊 Key Findings:")
        if exposures and len(extreme_betas) > len(all_betas) * 0.2:
            print("1. ❌ Many betas are hitting the ±3 cap (>20% of values)")
        else:
            print("1. ⚠️  Some betas are extreme but not majority")
        
        if not factor_returns.empty and np.max(np.abs(all_returns)) > 1:
            print("2. ❌ Factor returns may be in wrong scale (percentage vs decimal)")
        else:
            print("2. ✅ Factor returns appear to be in correct scale")
        
        if not position_returns.empty and len(all_pos_returns) > 0:
            if np.max(np.abs(all_pos_returns)) > 1:
                print("3. ❌ Position returns may be in wrong scale")
            else:
                print("3. ✅ Position returns appear to be in correct scale")
        
        if issues_found:
            print(f"4. ⚠️  {len(issues_found)} positions have suspicious price data")
        else:
            print("4. ✅ Price data quality looks reasonable")
        
        print("\n🔧 Likely Root Causes:")
        print("1. Returns calculation mismatch between positions and factors")
        print("2. Insufficient data for reliable regression (especially options)")
        print("3. Beta cap at ±3 is masking even more extreme values")
        print("4. Possible leverage or volatility mismatch in positions")

if __name__ == "__main__":
    asyncio.run(investigate_betas())