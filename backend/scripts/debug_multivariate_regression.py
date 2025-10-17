"""
Comprehensive diagnostic for multivariate factor regression.
Replicates EXACT calculation from factors.py to debug beta issues.
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import date, timedelta
from sqlalchemy import select
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache
from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS
from app.core.logging import get_logger

logger = get_logger(__name__)


async def fetch_prices(session, symbols: list, start_date: date, end_date: date) -> pd.DataFrame:
    """Fetch historical prices and convert to DataFrame."""
    stmt = (
        select(MarketDataCache.symbol, MarketDataCache.date, MarketDataCache.close)
        .where(
            MarketDataCache.symbol.in_(symbols),
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
        .order_by(MarketDataCache.date, MarketDataCache.symbol)
    )

    result = await session.execute(stmt)
    records = result.all()

    if not records:
        return pd.DataFrame()

    # Convert to DataFrame
    data = []
    for record in records:
        data.append({
            'symbol': record.symbol,
            'date': record.date,
            'close': float(record.close)
        })

    df = pd.DataFrame(data)

    # Pivot to have dates as index and symbols as columns
    price_df = df.pivot(index='date', columns='symbol', values='close')
    price_df.index = pd.to_datetime(price_df.index)

    return price_df


def calculate_vif(X: pd.DataFrame) -> dict:
    """Calculate VIF for each factor to check multicollinearity."""
    vif_data = {}
    for i, col in enumerate(X.columns):
        try:
            vif = variance_inflation_factor(X.values, i)
            vif_data[col] = float(vif) if np.isfinite(vif) else 999.9
        except:
            vif_data[col] = 999.9
    return vif_data


async def debug_multivariate_regression():
    """
    Run EXACT multivariate regression as factors.py does.
    Shows all diagnostics to understand why betas might be wrong.
    """
    async with AsyncSessionLocal() as session:
        try:
            print("\n" + "="*120)
            print("MULTIVARIATE FACTOR REGRESSION DIAGNOSTIC")
            print("="*120)

            # Use same date range as factor calculation would
            calculation_date = date.today()
            end_date = calculation_date
            start_date = end_date - timedelta(days=REGRESSION_WINDOW_DAYS + 30)

            print(f"\nDate Range: {start_date} to {end_date}")
            print(f"Regression Window: {REGRESSION_WINDOW_DAYS} days")

            # Get factor ETF symbols (same as factors.py uses)
            print(f"\nFactor ETFs:")
            for factor_name, etf_symbol in FACTOR_ETFS.items():
                print(f"  {factor_name:<15} -> {etf_symbol}")

            factor_symbols = list(FACTOR_ETFS.values())

            # Fetch factor ETF prices
            print(f"\nFetching factor ETF prices...")
            factor_prices = await fetch_prices(session, factor_symbols, start_date, end_date)

            if factor_prices.empty:
                print("[ERROR] No factor price data found")
                return

            print(f"[OK] Retrieved {len(factor_prices)} days of factor prices")

            # Align dates (drop any missing)
            factor_prices_aligned = factor_prices.dropna()
            print(f"[OK] Aligned: {len(factor_prices_aligned)} common trading days")

            # Calculate factor returns (EXACT same as factors.py line 115)
            factor_returns = factor_prices_aligned.pct_change(fill_method=None).dropna()
            print(f"[OK] Calculated {len(factor_returns)} days of factor returns")

            # Map ETF symbols to factor names
            symbol_to_factor = {v: k for k, v in FACTOR_ETFS.items()}
            factor_returns = factor_returns.rename(columns=symbol_to_factor)

            # Fetch NVDA prices
            print(f"\nFetching NVDA prices...")
            nvda_prices = await fetch_prices(session, ["NVDA"], start_date, end_date)

            if nvda_prices.empty:
                print("[ERROR] No NVDA price data found")
                return

            # Calculate NVDA returns
            nvda_returns = nvda_prices.pct_change(fill_method=None).dropna()
            nvda_returns.columns = ['NVDA']
            print(f"[OK] Calculated {len(nvda_returns)} days of NVDA returns")

            # Align NVDA returns with factor returns (same dates)
            common_dates = factor_returns.index.intersection(nvda_returns.index)
            print(f"[OK] Common dates: {len(common_dates)} days")

            factor_returns_aligned = factor_returns.loc[common_dates]
            nvda_returns_aligned = nvda_returns.loc[common_dates]

            # Display factor correlation matrix
            print("\n" + "="*120)
            print("FACTOR CORRELATION MATRIX")
            print("="*120)
            corr_matrix = factor_returns_aligned.corr()
            print(corr_matrix.to_string())

            # Check for high correlations
            print("\n" + "="*120)
            print("HIGH CORRELATIONS (> 0.7)")
            print("="*120)
            high_corrs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    corr = corr_matrix.iloc[i, j]
                    if abs(corr) > 0.7:
                        factor1 = corr_matrix.columns[i]
                        factor2 = corr_matrix.columns[j]
                        high_corrs.append((factor1, factor2, corr))
                        print(f"  {factor1:<15} vs {factor2:<15}: {corr:>7.4f}")

            if not high_corrs:
                print("  None found")

            # Prepare regression data (EXACT same as factors.py lines 449-465)
            print("\n" + "="*120)
            print("MULTIVARIATE REGRESSION: NVDA vs ALL 7 FACTORS")
            print("="*120)

            y_series = nvda_returns_aligned['NVDA']
            model_input = pd.concat([y_series, factor_returns_aligned], axis=1)
            model_input = model_input.dropna()

            print(f"Observations: {len(model_input)}")
            print(f"Factors: {len(factor_returns_aligned.columns)}")

            # Extract y and X (same as factors.py lines 464-465)
            y = model_input.iloc[:, 0].values  # NVDA returns
            X = model_input.iloc[:, 1:]         # All 7 factor returns

            # Check multicollinearity BEFORE regression
            print("\n" + "="*120)
            print("MULTICOLLINEARITY DIAGNOSTICS")
            print("="*120)

            vif_values = calculate_vif(X)
            print(f"\nVariance Inflation Factors (VIF):")
            print(f"  VIF > 10 = SEVERE multicollinearity")
            print(f"  VIF > 5 = MODERATE multicollinearity")
            print(f"  VIF < 5 = OK\n")

            for factor, vif in sorted(vif_values.items(), key=lambda x: x[1], reverse=True):
                status = "[SEVERE]" if vif > 10 else "[MODERATE]" if vif > 5 else "[OK]"
                print(f"  {factor:<15} VIF = {vif:>8.2f} {status}")

            # Condition number
            try:
                condition_number = np.linalg.cond(X.values)
                print(f"\nCondition Number: {condition_number:.2f}")
                print(f"  > 100 indicates multicollinearity")
                print(f"  Status: {'[PROBLEM]' if condition_number > 100 else '[OK]'}")
            except:
                print(f"\nCondition Number: [CALCULATION FAILED]")

            # Run OLS regression (EXACT same as factors.py line 488)
            print("\n" + "="*120)
            print("RUNNING OLS REGRESSION")
            print("="*120)

            X_with_const = sm.add_constant(X, has_constant='add')
            model = sm.OLS(y, X_with_const).fit()

            print(f"\nRegression Complete!")
            print(f"R-squared: {model.rsquared:.4f}")
            print(f"Adjusted R-squared: {model.rsquared_adj:.4f}")

            # Display all factor betas with statistics
            print("\n" + "="*120)
            print("FACTOR BETAS (Position-Level)")
            print("="*120)
            print(f"{'Factor':<15} {'Beta':>10} {'Std Err':>10} {'t-stat':>10} {'p-value':>10} {'Signif':<10}")
            print("-"*120)

            factor_columns = list(X.columns)
            for factor_name in factor_columns:
                beta = float(model.params.get(factor_name, 0.0))
                std_err = float(model.bse.get(factor_name, 0.0))
                t_stat = abs(beta / std_err) if std_err > 0 else 0.0
                p_value = float(model.pvalues.get(factor_name, 1.0))

                # Significance levels
                if p_value < 0.01:
                    signif = "***"
                elif p_value < 0.05:
                    signif = "**"
                elif p_value < 0.10:
                    signif = "*"
                else:
                    signif = "ns"

                print(f"{factor_name:<15} {beta:>10.4f} {std_err:>10.4f} {t_stat:>10.2f} {p_value:>10.4f} {signif:<10}")

            # Expected values for comparison
            print("\n" + "="*120)
            print("EXPECTED VS ACTUAL")
            print("="*120)
            print(f"\nMarket Beta (from regression): {model.params.get('Market', 0.0):.4f}")
            print(f"Expected Market Beta for NVDA: ~2.12")
            print(f"Simple univariate beta (from previous script): ~1.73")
            print(f"\nMatch: {'[PROBLEM - SIGN WRONG]' if model.params.get('Market', 0.0) < 0 else '[CHECK MAGNITUDE]'}")

            # Show full regression summary
            print("\n" + "="*120)
            print("FULL REGRESSION SUMMARY")
            print("="*120)
            print(model.summary())

            # Correlation of NVDA with each factor (simple pairwise)
            print("\n" + "="*120)
            print("SIMPLE PAIRWISE CORRELATIONS (NVDA vs Each Factor)")
            print("="*120)
            print(f"{'Factor':<15} {'Correlation':>12}")
            print("-"*40)

            for factor_name in factor_columns:
                corr = nvda_returns_aligned['NVDA'].corr(factor_returns_aligned[factor_name])
                print(f"{factor_name:<15} {corr:>12.4f}")

            print("\n" + "="*120)
            print("DIAGNOSTIC COMPLETE")
            print("="*120)
            print("\nNext Steps:")
            print("1. Check if VIF > 10 for any factors (severe multicollinearity)")
            print("2. Check if condition number > 100 (matrix is ill-conditioned)")
            print("3. Look at simple correlations vs multivariate betas")
            print("4. If Market beta is negative but correlation is positive -> MULTICOLLINEARITY PROBLEM")
            print("="*120 + "\n")

        except Exception as e:
            logger.error(f"Error in diagnostic: {e}")
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(debug_multivariate_regression())
