"""
Analyze beta distributions before and after redesign
Compare univariate vs multivariate regression results
"""
import asyncio
import numpy as np
import pandas as pd
from datetime import date
from uuid import UUID
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.market_data import PositionFactorExposure, FactorDefinition, FactorExposure
from app.calculations.factors import calculate_factor_betas_hybrid
from app.core.logging import get_logger
from typing import Dict, Any
import json

logger = get_logger(__name__)

# Demo portfolio IDs
DEMO_PORTFOLIOS = {
    'Demo Individual': UUID('51134ffd-2f13-49bd-b1f5-0c327e801b69'),
    'Demo HNW': UUID('c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e'),
    'Demo Hedge Fund': UUID('2ee7435f-379f-4606-bdb7-dadce587a182')
}


async def fetch_existing_betas(db, calculation_date: date) -> Dict[str, Any]:
    """Fetch existing betas from database (before redesign)"""
    
    # Get position-level betas
    stmt = select(
        PositionFactorExposure,
        FactorDefinition.name
    ).join(
        FactorDefinition,
        PositionFactorExposure.factor_id == FactorDefinition.id
    ).where(
        PositionFactorExposure.calculation_date == calculation_date
    )
    
    result = await db.execute(stmt)
    position_exposures = result.all()
    
    # Get portfolio-level betas
    portfolio_stmt = select(
        FactorExposure,
        FactorDefinition.name
    ).join(
        FactorDefinition,
        FactorExposure.factor_id == FactorDefinition.id
    ).where(
        FactorExposure.calculation_date == calculation_date
    )
    
    portfolio_result = await db.execute(portfolio_stmt)
    portfolio_exposures = portfolio_result.all()
    
    return {
        'position_level': position_exposures,
        'portfolio_level': portfolio_exposures
    }


async def calculate_new_betas(db, portfolio_id: UUID, calculation_date: date) -> Dict[str, Any]:
    """Calculate betas with new multivariate approach"""
    
    try:
        results = await calculate_factor_betas_hybrid(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            use_delta_adjusted=True  # New default
        )
        return results
    except Exception as e:
        logger.error(f"Error calculating new betas: {e}")
        return None


def analyze_beta_distribution(betas_data: Dict[str, Any], label: str):
    """Analyze and report on beta distribution"""
    
    print(f"\n{'=' * 80}")
    print(f"BETA DISTRIBUTION ANALYSIS: {label}")
    print('=' * 80)
    
    if not betas_data:
        print("No data available")
        return
    
    # For position-level betas
    if 'position_betas' in betas_data:
        all_betas = []
        factor_stats = {}
        
        for pos_id, factor_betas in betas_data['position_betas'].items():
            for factor_name, beta in factor_betas.items():
                all_betas.append(beta)
                
                if factor_name not in factor_stats:
                    factor_stats[factor_name] = []
                factor_stats[factor_name].append(beta)
        
        if all_betas:
            all_betas = np.array(all_betas)
            
            print(f"\n1. OVERALL STATISTICS ({len(all_betas)} betas)")
            print("-" * 40)
            print(f"Mean:     {np.mean(all_betas):8.4f}")
            print(f"Median:   {np.median(all_betas):8.4f}")
            print(f"Std Dev:  {np.std(all_betas):8.4f}")
            print(f"Min:      {np.min(all_betas):8.4f}")
            print(f"Max:      {np.max(all_betas):8.4f}")
            
            # Check extreme values
            extreme_count = np.sum(np.abs(all_betas) > 3)
            high_count = np.sum(np.abs(all_betas) > 2)
            
            print(f"\nExtreme values:")
            print(f"  |β| > 3:  {extreme_count} ({100*extreme_count/len(all_betas):.1f}%)")
            print(f"  |β| > 2:  {high_count} ({100*high_count/len(all_betas):.1f}%)")
            
            # Percentiles
            percentiles = [1, 5, 25, 50, 75, 95, 99]
            print(f"\nPercentiles:")
            for p in percentiles:
                val = np.percentile(all_betas, p)
                print(f"  {p:3d}%:    {val:8.4f}")
        
        # Per-factor analysis
        print(f"\n2. PER-FACTOR STATISTICS")
        print("-" * 40)
        print(f"{'Factor':<20} {'Count':<6} {'Mean':<10} {'Std':<10} {'Min':<10} {'Max':<10}")
        print("-" * 76)
        
        for factor_name in sorted(factor_stats.keys()):
            betas = np.array(factor_stats[factor_name])
            print(f"{factor_name:<20} {len(betas):<6} {np.mean(betas):<10.4f} "
                  f"{np.std(betas):<10.4f} {np.min(betas):<10.4f} {np.max(betas):<10.4f}")
    
    # For regression statistics
    if 'regression_stats' in betas_data:
        r2_values = []
        p_values = []
        quality_flags = {}
        
        for pos_id, factor_stats in betas_data['regression_stats'].items():
            for factor_name, stats in factor_stats.items():
                if 'r_squared' in stats:
                    r2_values.append(stats['r_squared'])
                if 'p_value' in stats:
                    p_values.append(stats['p_value'])
                if 'quality_flag' in stats:
                    flag = stats['quality_flag']
                    quality_flags[flag] = quality_flags.get(flag, 0) + 1
        
        print(f"\n3. REGRESSION QUALITY METRICS")
        print("-" * 40)
        
        if r2_values:
            print(f"R-squared distribution:")
            print(f"  Mean:   {np.mean(r2_values):.4f}")
            print(f"  Median: {np.median(r2_values):.4f}")
            print(f"  Min:    {np.min(r2_values):.4f}")
            print(f"  Max:    {np.max(r2_values):.4f}")
            
            good_fit = sum(1 for r2 in r2_values if r2 > 0.3)
            print(f"  R² > 0.3: {good_fit}/{len(r2_values)} ({100*good_fit/len(r2_values):.1f}%)")
        
        if p_values:
            significant = sum(1 for p in p_values if p < 0.05)
            print(f"\nP-values:")
            print(f"  Significant (p < 0.05): {significant}/{len(p_values)} ({100*significant/len(p_values):.1f}%)")
        
        if quality_flags:
            print(f"\nQuality flags:")
            for flag, count in sorted(quality_flags.items()):
                print(f"  {flag}: {count}")


async def compare_approaches():
    """Compare univariate (current) vs multivariate (new) approaches"""
    
    print("\n" + "=" * 80)
    print("FACTOR BETA REDESIGN: BEFORE/AFTER COMPARISON")
    print("=" * 80)
    
    calculation_date = date.today()
    
    async with get_async_session() as db:
        # Analyze existing betas (if any)
        print("\n📊 EXISTING BETAS (Univariate Approach)")
        existing = await fetch_existing_betas(db, calculation_date)
        
        if existing['position_level']:
            print(f"Found {len(existing['position_level'])} position-level exposures")
            
            # Convert to format for analysis
            position_betas = {}
            for pfe, factor_name in existing['position_level']:
                pos_id = str(pfe.position_id)
                if pos_id not in position_betas:
                    position_betas[pos_id] = {}
                position_betas[pos_id][factor_name] = float(pfe.exposure_value)
            
            analyze_beta_distribution({'position_betas': position_betas}, "EXISTING (Univariate)")
        else:
            print("No existing betas found in database")
        
        # Calculate new betas for each demo portfolio
        print("\n📊 NEW BETAS (Multivariate Approach)")
        
        for portfolio_name, portfolio_id in DEMO_PORTFOLIOS.items():
            print(f"\nCalculating for {portfolio_name}...")
            
            new_results = await calculate_new_betas(db, portfolio_id, calculation_date)
            
            if new_results:
                analyze_beta_distribution(new_results, f"NEW - {portfolio_name}")
                
                # Save detailed results for inspection
                output_file = f"beta_analysis_{portfolio_name.replace(' ', '_').lower()}.json"
                
                # Convert to JSON-serializable format
                json_results = {
                    'portfolio': portfolio_name,
                    'portfolio_id': str(portfolio_id),
                    'calculation_date': str(calculation_date),
                    'factor_betas': new_results.get('factor_betas', {}),
                    'data_quality': new_results.get('data_quality', {}),
                    'metadata': new_results.get('metadata', {})
                }
                
                # Extract key statistics
                if 'position_betas' in new_results:
                    all_betas = []
                    for pos_betas in new_results['position_betas'].values():
                        all_betas.extend(pos_betas.values())
                    
                    if all_betas:
                        json_results['summary_stats'] = {
                            'total_betas': len(all_betas),
                            'mean': float(np.mean(all_betas)),
                            'std': float(np.std(all_betas)),
                            'min': float(np.min(all_betas)),
                            'max': float(np.max(all_betas)),
                            'extreme_count': int(np.sum(np.abs(all_betas) > 3)),
                            'high_count': int(np.sum(np.abs(all_betas) > 2))
                        }
                
                with open(output_file, 'w') as f:
                    json.dump(json_results, f, indent=2, default=str)
                print(f"  Detailed results saved to: {output_file}")
            else:
                print(f"  Failed to calculate new betas")
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("\nExpected improvements with multivariate approach:")
        print("1. ✅ Reduced beta magnitudes (no omitted variable bias)")
        print("2. ✅ Fewer extreme values (better factor attribution)")
        print("3. ✅ Improved R² (factors work together)")
        print("4. ✅ More stable estimates (robust to factor correlations)")
        print("5. ✅ Winsorization instead of hard caps")


if __name__ == "__main__":
    asyncio.run(compare_approaches())