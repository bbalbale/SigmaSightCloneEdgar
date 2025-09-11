#!/usr/bin/env python3
"""
Export all factor ETF historical data to CSV files for data quality analysis.
This script helps identify whether we have data ingestion or quality problems.

Critical Discovery (from FACTOR_BETA_REDESIGN.md):
- Factor correlations up to 0.96 (Size vs Value)  
- VIF values: Quality (52.5), Growth (41.8), Value (23.9), Size (22.0)
- Condition number: 640+ indicating numerical instability
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import sys
import os
from pathlib import Path
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS
from app.models.market_data import MarketDataCache
from app.database import get_async_session
from app.core.logging import get_logger

logger = get_logger(__name__)

async def fetch_etf_data_from_db(
    db: AsyncSession,
    symbol: str,
    start_date: date,
    end_date: date
) -> pd.Series:
    """
    Fetch historical prices for a single ETF from the database.
    """
    stmt = select(
        MarketDataCache.date,
        MarketDataCache.close
    ).where(
        and_(
            MarketDataCache.symbol == symbol.upper(),
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date)
    
    result = await db.execute(stmt)
    records = result.all()
    
    if not records:
        return pd.Series()
    
    # Convert to Series with date as index
    data = {record.date: float(record.close) for record in records}
    series = pd.Series(data)
    series.index = pd.to_datetime(series.index)
    return series

async def export_factor_etf_data():
    """
    Export all factor ETF data to CSV files for analysis.
    Creates individual CSV files and a combined CSV for correlation analysis.
    """
    # Create exports directory
    export_dir = Path("factor_etf_exports")
    export_dir.mkdir(exist_ok=True)
    
    logger.info(f"Exporting factor ETF data to {export_dir}")
    logger.info(f"Factor ETFs to export: {FACTOR_ETFS}")
    
    # Date range for historical data
    end_date = date.today()
    start_date = end_date - timedelta(days=REGRESSION_WINDOW_DAYS * 2)  # Get extra data for analysis
    
    logger.info(f"Date range: {start_date} to {end_date}")
    
    # Get database session
    async with get_async_session() as db:
        # Check what data we have in the database first
        stmt = select(
            MarketDataCache.symbol,
            func.count(MarketDataCache.id).label('count'),
            func.min(MarketDataCache.date).label('min_date'),
            func.max(MarketDataCache.date).label('max_date')
        ).where(
            MarketDataCache.symbol.in_(list(FACTOR_ETFS.values()))
        ).group_by(MarketDataCache.symbol)
        
        result = await db.execute(stmt)
        db_summary = result.all()
        
        logger.info("\nDatabase Summary for Factor ETFs:")
        for row in db_summary:
            logger.info(f"  {row.symbol}: {row.count} records, from {row.min_date} to {row.max_date}")
        
        # Collect all data
        price_dataframes = {}
        
        for factor_name, etf_symbol in FACTOR_ETFS.items():
            logger.info(f"Fetching data for {factor_name} ({etf_symbol})...")
            
            try:
                # Fetch historical prices from database
                prices = await fetch_etf_data_from_db(db, etf_symbol, start_date, end_date)
                
                if not prices.empty:
                    # Save individual ETF data
                    individual_file = export_dir / f"{factor_name}_{etf_symbol}_prices.csv"
                    prices.to_csv(individual_file, header=['close'])
                    logger.info(f"✅ Exported {len(prices)} records to {individual_file}")
                    
                    # Store for combined analysis
                    price_dataframes[f"{factor_name}_{etf_symbol}"] = prices
                    
                    # Calculate returns for analysis
                    returns = prices.pct_change()
                    returns_file = export_dir / f"{factor_name}_{etf_symbol}_returns.csv"
                    returns.to_csv(returns_file, header=['return'])
                    logger.info(f"✅ Exported returns to {returns_file}")
                    
                else:
                    logger.warning(f"❌ No data available for {factor_name} ({etf_symbol})")
                    
            except Exception as e:
                logger.error(f"❌ Error fetching {factor_name} ({etf_symbol}): {e}")
    
    # Create combined dataset for correlation analysis
    if price_dataframes:
        logger.info("\nCreating combined dataset for correlation analysis...")
        
        # Align all price series on dates
        combined_prices = pd.DataFrame(price_dataframes)
        combined_returns = combined_prices.pct_change()
        
        # Save combined data
        combined_prices_file = export_dir / "combined_factor_etf_prices.csv"
        combined_prices.to_csv(combined_prices_file)
        logger.info(f"✅ Exported combined prices to {combined_prices_file}")
        
        combined_returns_file = export_dir / "combined_factor_etf_returns.csv"
        combined_returns.to_csv(combined_returns_file)
        logger.info(f"✅ Exported combined returns to {combined_returns_file}")
        
        # Calculate and export correlation matrix
        correlation_matrix = combined_returns.corr()
        correlation_file = export_dir / "factor_correlation_matrix.csv"
        correlation_matrix.to_csv(correlation_file)
        logger.info(f"✅ Exported correlation matrix to {correlation_file}")
        
        # Print correlation summary
        logger.info("\n" + "="*60)
        logger.info("CORRELATION MATRIX SUMMARY")
        logger.info("="*60)
        print("\nCorrelation Matrix:")
        print(correlation_matrix.round(3))
        
        # Find high correlations (excluding diagonal)
        high_corr_pairs = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:
                    high_corr_pairs.append((
                        correlation_matrix.columns[i],
                        correlation_matrix.columns[j],
                        corr_value
                    ))
        
        if high_corr_pairs:
            logger.info("\nHigh Correlation Pairs (|r| > 0.7):")
            for col1, col2, corr in sorted(high_corr_pairs, key=lambda x: abs(x[2]), reverse=True):
                print(f"  {col1} <-> {col2}: {corr:.3f}")
        
        # Data quality summary
        logger.info("\n" + "="*60)
        logger.info("DATA QUALITY SUMMARY")
        logger.info("="*60)
        
        for col_name in combined_prices.columns:
            prices = combined_prices[col_name]
            returns = combined_returns[col_name]
            
            print(f"\n{col_name}:")
            print(f"  Total days: {len(prices)}")
            print(f"  Non-null prices: {prices.notna().sum()} ({prices.notna().sum()/len(prices)*100:.1f}%)")
            print(f"  Non-null returns: {returns.notna().sum()} ({returns.notna().sum()/len(returns)*100:.1f}%)")
            
            if prices.notna().any():
                print(f"  Price range: ${prices.min():.2f} - ${prices.max():.2f}")
                print(f"  Mean return: {returns.mean():.4f} ({returns.mean()*100:.2f}%)")
                print(f"  Std dev: {returns.std():.4f} ({returns.std()*100:.2f}%)")
                print(f"  Min return: {returns.min():.4f} ({returns.min()*100:.2f}%)")
                print(f"  Max return: {returns.max():.4f} ({returns.max()*100:.2f}%)")
        
        # Calculate VIF (Variance Inflation Factor) to check multicollinearity
        try:
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            
            # Prepare data for VIF calculation (drop NaN rows)
            returns_clean = combined_returns.dropna()
            
            if len(returns_clean) > 10:  # Need sufficient data
                vif_data = pd.DataFrame()
                vif_data["Factor"] = returns_clean.columns
                vif_data["VIF"] = [variance_inflation_factor(returns_clean.values, i) 
                                  for i in range(returns_clean.shape[1])]
                
                vif_file = export_dir / "factor_vif_analysis.csv"
                vif_data.to_csv(vif_file, index=False)
                
                logger.info("\n" + "="*60)
                logger.info("MULTICOLLINEARITY ANALYSIS (VIF)")
                logger.info("="*60)
                print("\nVariance Inflation Factors:")
                print(vif_data.to_string(index=False))
                print("\nInterpretation:")
                print("  VIF < 5: Low multicollinearity")
                print("  VIF 5-10: Moderate multicollinearity")
                print("  VIF > 10: High multicollinearity (problematic)")
                
                # Calculate condition number
                from numpy.linalg import cond
                
                # Add constant for proper condition number calculation
                X = returns_clean.values
                X_with_const = np.column_stack([np.ones(len(X)), X])
                condition_num = cond(X_with_const)
                
                print(f"\nCondition Number: {condition_num:.2f}")
                print("Interpretation:")
                print("  < 30: No multicollinearity")
                print("  30-100: Moderate multicollinearity")
                print("  > 100: Severe multicollinearity")
                
        except ImportError:
            logger.warning("statsmodels not available for VIF calculation")
        except Exception as e:
            logger.error(f"Error calculating VIF: {e}")
        
        # Check for data alignment issues
        logger.info("\n" + "="*60)
        logger.info("DATA ALIGNMENT ANALYSIS")
        logger.info("="*60)
        
        # Count days where each ETF has data
        data_availability = combined_prices.notna().sum(axis=1)
        print(f"\nDays with data for N ETFs:")
        for n_etfs in range(len(FACTOR_ETFS) + 1):
            n_days = (data_availability == n_etfs).sum()
            if n_days > 0:
                print(f"  {n_etfs} ETFs: {n_days} days")
        
        # Check for suspicious patterns (e.g., all ETFs having same values)
        if len(combined_prices) > 0:
            # Check if any rows have all identical values (excluding NaN)
            for idx, row in combined_prices.iterrows():
                non_nan_values = row.dropna()
                if len(non_nan_values) > 1 and non_nan_values.nunique() == 1:
                    logger.warning(f"Suspicious: All ETFs have same price ({non_nan_values.iloc[0]:.2f}) on {idx}")
    
    logger.info("\n" + "="*60)
    logger.info(f"✅ Export complete! Files saved to: {export_dir.absolute()}")
    logger.info("="*60)
    
    # Summary recommendations
    logger.info("\n" + "="*60)
    logger.info("ANALYSIS RECOMMENDATIONS")
    logger.info("="*60)
    print("\n1. Check the correlation matrix for unexpected patterns")
    print("2. Review VIF values - high values indicate multicollinearity")
    print("3. Examine individual ETF returns for data quality issues")
    print("4. Look for gaps in data coverage that might affect calculations")
    print("5. Consider whether the high correlations are market reality or data problems")
    
    return export_dir

def main():
    """Main entry point."""
    asyncio.run(export_factor_etf_data())

if __name__ == "__main__":
    main()