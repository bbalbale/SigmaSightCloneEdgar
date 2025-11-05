#!/usr/bin/env python3
"""
Manual testing script for position-to-position correlation analysis
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload

from app.models import Portfolio, Position, CorrelationCalculation, CorrelationCluster, PairwiseCorrelation
from app.services.correlation_service import CorrelationService
from app.config import settings

# Use environment variable or default connection string
DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)


async def test_correlation_analysis():
    """Test the correlation analysis functionality"""
    
    # Create async engine and session
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            print("\n=== Position-to-Position Correlation Analysis Test ===\n")
            
            # 1. Find a demo portfolio with positions
            result = await db.execute(
                select(Portfolio)
                .options(selectinload(Portfolio.positions))
                .join(Portfolio.positions)
                .group_by(Portfolio.id)
                .having(func.count(Position.id) >= 5)  # At least 5 positions
                .limit(1)
            )
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                print("❌ No portfolio found with at least 5 positions")
                return
            
            print(f"✅ Found portfolio: {portfolio.name} (ID: {portfolio.id})")
            print(f"   Total positions: {len(portfolio.positions)}")
            
            # Display portfolio composition
            total_value = Decimal("0")
            print("\n📊 Portfolio Composition:")
            for pos in sorted(portfolio.positions, key=lambda p: abs(p.quantity * p.last_price), reverse=True)[:10]:
                value = abs(pos.quantity * pos.last_price)
                total_value += value
                print(f"   - {pos.symbol}: ${value:,.2f} ({pos.position_type})")
            
            print(f"\n   Total Portfolio Value: ${total_value:,.2f}")
            
            # 2. Test correlation calculation with different filter modes
            correlation_service = CorrelationService(db)
            calculation_date = datetime.now()
            
            print("\n🔄 Testing Correlation Calculations with Different Filters...\n")
            
            # Test 1: Default filtering (both value and weight)
            print("Test 1: Default filtering (both value AND weight thresholds)")
            print("   Min value: $10,000, Min weight: 1%, Mode: both")
            
            try:
                calc1 = await correlation_service.calculate_portfolio_correlations(
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date,
                    min_position_value=Decimal("10000"),
                    min_portfolio_weight=Decimal("0.01"),
                    filter_mode="both",
                    correlation_threshold=Decimal("0.7"),
                    duration_days=90,
                    force_recalculate=True
                )
                
                print(f"   ✅ Calculation completed!")
                print(f"   - Positions included: {calc1.positions_included}")
                print(f"   - Positions excluded: {calc1.positions_excluded}")
                print(f"   - Overall correlation: {calc1.overall_correlation:.4f}")
                print(f"   - Concentration score: {calc1.correlation_concentration_score:.4f}")
                print(f"   - Effective positions: {calc1.effective_positions:.2f}")
                print(f"   - Data quality: {calc1.data_quality}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test 2: Value-only filtering
            print("\nTest 2: Value-only filtering")
            print("   Min value: $5,000, Mode: value_only")
            
            try:
                calc2 = await correlation_service.calculate_portfolio_correlations(
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date + timedelta(seconds=1),  # Different timestamp
                    min_position_value=Decimal("5000"),
                    min_portfolio_weight=None,
                    filter_mode="value_only",
                    correlation_threshold=Decimal("0.6"),  # Lower threshold
                    duration_days=90,
                    force_recalculate=True
                )
                
                print(f"   ✅ Calculation completed!")
                print(f"   - Positions included: {calc2.positions_included}")
                print(f"   - Positions excluded: {calc2.positions_excluded}")
                print(f"   - Overall correlation: {calc2.overall_correlation:.4f}")
                print(f"   - Clusters found: {len(await get_clusters(db, calc2.id))}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Test 3: Either filtering
            print("\nTest 3: Either filtering (value OR weight)")
            print("   Min value: $20,000, Min weight: 2%, Mode: either")
            
            try:
                calc3 = await correlation_service.calculate_portfolio_correlations(
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date + timedelta(seconds=2),
                    min_position_value=Decimal("20000"),
                    min_portfolio_weight=Decimal("0.02"),
                    filter_mode="either",
                    correlation_threshold=Decimal("0.7"),
                    duration_days=90,
                    force_recalculate=True
                )
                
                print(f"   ✅ Calculation completed!")
                print(f"   - Positions included: {calc3.positions_included}")
                print(f"   - Positions excluded: {calc3.positions_excluded}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # 3. Display correlation clusters from the first calculation
            if 'calc1' in locals():
                print("\n🔗 Correlation Clusters (from Test 1):")
                clusters = await get_clusters(db, calc1.id)
                
                for cluster in clusters:
                    print(f"\n   Cluster: {cluster.nickname}")
                    print(f"   - Average correlation: {cluster.avg_correlation:.4f}")
                    print(f"   - Total value: ${cluster.total_value:,.2f}")
                    print(f"   - Portfolio %: {cluster.portfolio_percentage*100:.2f}%")
                    
                    # Get cluster positions
                    await db.refresh(cluster, ['positions'])
                    print("   - Positions:")
                    for pos in cluster.positions[:5]:  # Show first 5
                        print(f"     • {pos.symbol}: ${pos.value:,.2f} (correlation: {pos.correlation_to_cluster:.3f})")
                
                # 4. Sample correlation matrix
                print("\n📊 Sample Pairwise Correlations (top 10):")
                correlations = await get_top_correlations(db, calc1.id, limit=10)
                
                for corr in correlations:
                    if corr.symbol_1 != corr.symbol_2:  # Skip self-correlations
                        print(f"   {corr.symbol_1} ↔ {corr.symbol_2}: {corr.correlation_value:.4f} "
                              f"(n={corr.data_points} days)")
            
            print("\n✅ Correlation analysis test completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await engine.dispose()


async def get_clusters(db: AsyncSession, calculation_id: UUID):
    """Get clusters for a calculation"""
    result = await db.execute(
        select(CorrelationCluster)
        .where(CorrelationCluster.correlation_calculation_id == calculation_id)
        .order_by(CorrelationCluster.total_value.desc())
    )
    return result.scalars().all()


async def get_top_correlations(db: AsyncSession, calculation_id: UUID, limit: int = 10):
    """Get top correlations by absolute value"""
    result = await db.execute(
        select(PairwiseCorrelation)
        .where(PairwiseCorrelation.correlation_calculation_id == calculation_id)
        .order_by(func.abs(PairwiseCorrelation.correlation_value).desc())
        .limit(limit)
    )
    return result.scalars().all()


if __name__ == "__main__":
    asyncio.run(test_correlation_analysis())