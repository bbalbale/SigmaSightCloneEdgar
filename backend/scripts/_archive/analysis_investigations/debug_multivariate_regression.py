"""
Debug multivariate regression issues - check for multicollinearity
"""
import asyncio
import numpy as np
import pandas as pd
from datetime import date, timedelta
from uuid import UUID
from app.database import get_async_session
from app.models.positions import Position
from app.calculations.factors import fetch_factor_returns, calculate_position_returns
from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS
import statsmodels.api as sm
from sqlalchemy import select, and_

async def debug_multivariate():
    """Debug why multivariate regression produces extreme betas"""
    
    print("=" * 80)
    print("MULTIVARIATE REGRESSION DEBUGGING")
    print("=" * 80)
    
    portfolio_id = UUID('51134ffd-2f13-49bd-b1f5-0c327e801b69')  # Demo Individual
    calculation_date = date.today()
    end_date = calculation_date
    start_date = end_date - timedelta(days=REGRESSION_WINDOW_DAYS + 30)
    
    async with get_async_session() as db:
        # Get factor returns
        factor_symbols = list(FACTOR_ETFS.values())
        factor_returns = await fetch_factor_returns(
            db=db,
            symbols=factor_symbols,
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"\n1. FACTOR RETURNS ANALYSIS")
        print("-" * 40)
        print(f"Shape: {factor_returns.shape}")
        print(f"Factors: {list(factor_returns.columns)}")
        
        # Check factor correlation
        factor_corr = factor_returns.corr()
        print(f"\n2. FACTOR CORRELATION MATRIX")
        print("-" * 40)
        print(factor_corr.round(3))
        
        # Check for high correlations
        high_corr = []
        for i in range(len(factor_corr.columns)):
            for j in range(i+1, len(factor_corr.columns)):
                corr_val = factor_corr.iloc[i, j]
                if abs(corr_val) > 0.7:
                    high_corr.append((
                        factor_corr.columns[i],
                        factor_corr.columns[j],
                        corr_val
                    ))
        
        if high_corr:
            print(f"\n⚠️ HIGH CORRELATIONS DETECTED (|r| > 0.7):")
            for f1, f2, corr in high_corr:
                print(f"  {f1} <-> {f2}: {corr:.3f}")
        
        # Get position returns
        position_returns = await calculate_position_returns(
            db=db,
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date,
            use_delta_adjusted=True
        )
        
        if position_returns.empty:
            print("No position returns available")
            return
        
        # Test with first position
        first_pos_id = position_returns.columns[0]
        
        # Get the position details
        pos_stmt = select(Position).where(Position.id == UUID(first_pos_id))
        pos_result = await db.execute(pos_stmt)
        position = pos_result.scalar_one_or_none()
        
        print(f"\n3. TEST POSITION: {position.symbol if position else 'Unknown'}")
        print("-" * 40)
        
        # Align data
        y_series = position_returns[first_pos_id]
        combined_df = pd.concat([
            y_series.rename('y'),
            factor_returns
        ], axis=1).dropna()
        
        print(f"Aligned data points: {len(combined_df)}")
        
        if len(combined_df) < MIN_REGRESSION_DAYS:
            print(f"Insufficient data ({MIN_REGRESSION_DAYS} required)")
            return
        
        y = combined_df['y'].values
        X_multi = combined_df.drop('y', axis=1).values
        
        # Check condition number
        X_with_const = sm.add_constant(X_multi)
        
        print(f"\n4. MATRIX CONDITIONING")
        print("-" * 40)
        
        # Calculate condition number
        cond_number = np.linalg.cond(X_with_const)
        print(f"Condition number: {cond_number:.2f}")
        
        if cond_number > 1000:
            print("⚠️ SEVERE multicollinearity detected (condition number > 1000)")
            print("This causes numerical instability and extreme betas")
        elif cond_number > 100:
            print("⚠️ Moderate multicollinearity detected (condition number > 100)")
        else:
            print("✅ Matrix is well-conditioned")
        
        # Check Variance Inflation Factors (VIF)
        print(f"\n5. VARIANCE INFLATION FACTORS (VIF)")
        print("-" * 40)
        
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        
        vif_data = pd.DataFrame()
        vif_data["Factor"] = combined_df.drop('y', axis=1).columns
        vif_data["VIF"] = [variance_inflation_factor(X_multi, i) 
                          for i in range(X_multi.shape[1])]
        
        print(vif_data)
        print("\nVIF Interpretation:")
        print("  VIF = 1: No correlation")
        print("  VIF < 5: Low multicollinearity")
        print("  VIF 5-10: Moderate multicollinearity")
        print("  VIF > 10: High multicollinearity (problematic)")
        
        # Run both univariate and multivariate for comparison
        print(f"\n6. REGRESSION COMPARISON")
        print("-" * 40)
        
        # Multivariate
        try:
            model_multi = sm.OLS(y, X_with_const).fit()
            print(f"\nMultivariate OLS:")
            print(f"  R-squared: {model_multi.rsquared:.4f}")
            print(f"  Condition number: {model_multi.condition_number:.2f}")
            print(f"  Betas:")
            for i, factor_name in enumerate(combined_df.drop('y', axis=1).columns):
                beta = model_multi.params[i+1] if len(model_multi.params) > i+1 else 0
                p_val = model_multi.pvalues[i+1] if len(model_multi.pvalues) > i+1 else 1
                print(f"    {factor_name:<15}: {beta:8.4f} (p={p_val:.4f})")
        except Exception as e:
            print(f"Multivariate failed: {e}")
        
        # Univariate comparison for Market factor
        print(f"\nUnivariate OLS (Market only):")
        if 'Market' in combined_df.columns:
            X_single = combined_df['Market'].values
            X_single_const = sm.add_constant(X_single)
            model_uni = sm.OLS(y, X_single_const).fit()
            print(f"  R-squared: {model_uni.rsquared:.4f}")
            print(f"  Market beta: {model_uni.params[1]:.4f} (p={model_uni.pvalues[1]:.4f})")
        
        # Try Ridge regression as alternative
        print(f"\n7. RIDGE REGRESSION (L2 Regularization)")
        print("-" * 40)
        
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_multi)
        
        # Try different alpha values
        alphas = [0.01, 0.1, 1.0, 10.0]
        for alpha in alphas:
            ridge = Ridge(alpha=alpha)
            ridge.fit(X_scaled, y)
            
            print(f"\nAlpha = {alpha}:")
            print(f"  R-squared: {ridge.score(X_scaled, y):.4f}")
            print(f"  Betas:")
            for i, factor_name in enumerate(combined_df.drop('y', axis=1).columns):
                # Unstandardize beta
                beta = ridge.coef_[i] / scaler.scale_[i]
                print(f"    {factor_name:<15}: {beta:8.4f}")
        
        print("\n" + "=" * 80)
        print("DIAGNOSIS SUMMARY")
        print("=" * 80)
        
        if cond_number > 100:
            print("\n🔴 PROBLEM: Multicollinearity is causing extreme betas")
            print("\nRECOMMENDATIONS:")
            print("1. Use Ridge regression (L2 regularization) instead of OLS")
            print("2. Consider dropping highly correlated factors")
            print("3. Use Principal Component Regression (PCR)")
            print("4. Implement stepwise selection to reduce factors")
        else:
            print("\n✅ Matrix conditioning is acceptable")
            print("Check for other issues: outliers, data quality, etc.")


if __name__ == "__main__":
    asyncio.run(debug_multivariate())