#!/usr/bin/env python3
"""
Demo Portfolio Verification Script - Phase 2.0.1
Verifies that 3 demo portfolios exist and have complete calculation engine data
"""
import sys
from pathlib import Path
from datetime import datetime
import asyncio
from typing import Dict, Any, List
from uuid import UUID

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.models.users import Portfolio, User
from app.models.positions import Position
from app.models.market_data import PositionGreeks, PositionFactorExposure, MarketDataCache
from app.models.correlations import CorrelationCalculation
from app.models.snapshots import PortfolioSnapshot
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import selectinload
from app.core.logging import get_logger

logger = get_logger(__name__)

# Expected demo portfolio configuration
EXPECTED_DEMO_PORTFOLIOS = {
    "demo_individual@sigmasight.com": {
        "name": "Demo Individual Investor Portfolio",
        "expected_positions": 16,
        "description": "Conservative individual investor profile"
    },
    "demo_hnw@sigmasight.com": {
        "name": "Demo High Net Worth Investor Portfolio", 
        "expected_positions": 17,
        "description": "Affluent investor with diversified holdings"
    },
    "demo_hedgefundstyle@sigmasight.com": {
        "name": "Demo Hedge Fund Style Investor Portfolio",
        "expected_positions": 30,
        "description": "Sophisticated hedge fund style portfolio"
    }
}

CALCULATION_ENGINES = [
    "portfolio_exposures",
    "greeks_calculations", 
    "factor_analysis",
    "correlation_analysis",
    "market_risk_metrics",
    "portfolio_snapshots",
    "market_data_cache",
    "stress_testing"
]


class DemoPortfolioVerifier:
    """Comprehensive verification of demo portfolios and their calculation data"""
    
    def __init__(self):
        self.verification_results = {}
        self.summary_stats = {}
    
    async def verify_all_portfolios(self) -> Dict[str, Any]:
        """Main verification entry point"""
        print("\n" + "="*90)
        print("🎯 Demo Portfolio Verification - Phase 2.0.1")
        print("="*90)
        
        async with get_async_session() as db:
            # Step 1: Verify portfolio structure
            await self._verify_portfolio_structure(db)
            
            # Step 2: Verify calculation engine data
            await self._verify_calculation_engines(db)
            
            # Step 3: Verify data quality and completeness
            await self._verify_data_quality(db)
            
            # Step 4: Generate summary
            summary = await self._generate_verification_summary()
            
            return summary
    
    async def _verify_portfolio_structure(self, db):
        """Verify the 3 demo portfolios exist with expected positions"""
        print("\n📊 1. Portfolio Structure Verification")
        print("-" * 60)
        
        # Get all portfolios with users and positions
        stmt = select(Portfolio).options(
            selectinload(Portfolio.user),
            selectinload(Portfolio.positions)
        )
        result = await db.execute(stmt)
        portfolios = result.scalars().all()
        
        print(f"Found {len(portfolios)} total portfolios in database")
        
        # Check each expected demo portfolio
        demo_portfolios_found = {}
        
        for portfolio in portfolios:
            user_email = portfolio.user.email if portfolio.user else "NO_USER"
            
            if user_email in EXPECTED_DEMO_PORTFOLIOS:
                expected = EXPECTED_DEMO_PORTFOLIOS[user_email]
                actual_positions = len(portfolio.positions)
                
                demo_portfolios_found[user_email] = {
                    'portfolio_id': str(portfolio.id),
                    'name': portfolio.name,
                    'expected_name': expected['name'],
                    'actual_positions': actual_positions,
                    'expected_positions': expected['expected_positions'],
                    'positions_match': actual_positions == expected['expected_positions'],
                    'name_match': portfolio.name == expected['name'],
                    'created_at': portfolio.created_at,
                    'status': 'FOUND'
                }
                
                # Print detailed status
                status_icon = "✅" if actual_positions == expected['expected_positions'] else "⚠️"
                print(f"{status_icon} {user_email}:")
                print(f"   Portfolio: '{portfolio.name}'")
                print(f"   ID: {portfolio.id}")
                print(f"   Positions: {actual_positions}/{expected['expected_positions']}")
                
                if not demo_portfolios_found[user_email]['name_match']:
                    print(f"   ⚠️ Name mismatch: expected '{expected['name']}'")
                
        # Check for missing portfolios
        missing_portfolios = set(EXPECTED_DEMO_PORTFOLIOS.keys()) - set(demo_portfolios_found.keys())
        for missing_email in missing_portfolios:
            demo_portfolios_found[missing_email] = {
                'status': 'MISSING',
                'expected_name': EXPECTED_DEMO_PORTFOLIOS[missing_email]['name'],
                'expected_positions': EXPECTED_DEMO_PORTFOLIOS[missing_email]['expected_positions']
            }
            print(f"❌ {missing_email}: MISSING")
        
        # Summary stats
        total_positions = sum(p['actual_positions'] for p in demo_portfolios_found.values() if 'actual_positions' in p)
        expected_total = sum(EXPECTED_DEMO_PORTFOLIOS[email]['expected_positions'] for email in EXPECTED_DEMO_PORTFOLIOS)
        
        print(f"\n📈 Portfolio Summary:")
        print(f"   Demo Portfolios Found: {len([p for p in demo_portfolios_found.values() if p['status'] == 'FOUND'])}/3")
        print(f"   Total Positions: {total_positions}/{expected_total}")
        print(f"   Structure Status: {'✅ COMPLETE' if len(demo_portfolios_found) == 3 and total_positions == expected_total else '⚠️ INCOMPLETE'}")
        
        self.verification_results['portfolios'] = demo_portfolios_found
        self.summary_stats['total_portfolios'] = len(demo_portfolios_found)
        self.summary_stats['total_positions'] = total_positions
    
    async def _verify_calculation_engines(self, db):
        """Verify calculation engine data availability"""
        print("\n🔧 2. Calculation Engine Data Verification")
        print("-" * 60)
        
        engine_data = {}
        
        # Get demo portfolio IDs for filtering
        demo_portfolio_ids = []
        for email, data in self.verification_results.get('portfolios', {}).items():
            if data.get('portfolio_id'):
                demo_portfolio_ids.append(data['portfolio_id'])
        
        if not demo_portfolio_ids:
            print("❌ No demo portfolios found - skipping calculation engine verification")
            return
        
        print(f"Checking calculation data for {len(demo_portfolio_ids)} demo portfolios...")
        
        # 1. Position Greeks - join through positions table
        stmt = select(func.count(PositionGreeks.id)).join(
            Position, PositionGreeks.position_id == Position.id
        ).where(
            Position.portfolio_id.in_(demo_portfolio_ids)
        )
        result = await db.execute(stmt)
        greeks_count = result.scalar() or 0
        engine_data['greeks'] = {'count': greeks_count, 'table': 'PositionGreeks'}
        
        # 2. Factor Exposures - join through positions table
        stmt = select(func.count(PositionFactorExposure.id)).join(
            Position, PositionFactorExposure.position_id == Position.id
        ).where(
            Position.portfolio_id.in_(demo_portfolio_ids)
        )
        result = await db.execute(stmt)
        factors_count = result.scalar() or 0
        engine_data['factors'] = {'count': factors_count, 'table': 'PositionFactorExposure'}
        
        # 3. Correlation Calculations
        stmt = select(func.count(CorrelationCalculation.id)).where(
            CorrelationCalculation.portfolio_id.in_(demo_portfolio_ids)
        )
        result = await db.execute(stmt)
        correlations_count = result.scalar() or 0
        engine_data['correlations'] = {'count': correlations_count, 'table': 'CorrelationCalculation'}
        
        # 4. Portfolio Snapshots
        stmt = select(func.count(PortfolioSnapshot.id)).where(
            PortfolioSnapshot.portfolio_id.in_(demo_portfolio_ids)
        )
        result = await db.execute(stmt)
        snapshots_count = result.scalar() or 0
        engine_data['snapshots'] = {'count': snapshots_count, 'table': 'PortfolioSnapshot'}
        
        # 5. Market Data Cache (all symbols used by demo portfolios)
        stmt = select(func.count(distinct(MarketDataCache.symbol)))
        result = await db.execute(stmt)
        market_symbols_count = result.scalar() or 0
        engine_data['market_data'] = {'count': market_symbols_count, 'table': 'MarketDataCache'}
        
        # 6. Check positions table as baseline
        stmt = select(func.count(Position.id)).where(
            Position.portfolio_id.in_(demo_portfolio_ids)
        )
        result = await db.execute(stmt)
        positions_count = result.scalar() or 0
        engine_data['positions'] = {'count': positions_count, 'table': 'Position'}
        
        # Print results
        print("📊 Calculation Engine Data Status:")
        for engine_name, data in engine_data.items():
            status_icon = "✅" if data['count'] > 0 else "❌"
            print(f"   {status_icon} {engine_name.title()}: {data['count']} records ({data['table']})")
        
        # Calculate completeness ratio
        total_engines = len(engine_data)
        engines_with_data = len([d for d in engine_data.values() if d['count'] > 0])
        completeness_ratio = engines_with_data / total_engines
        
        print(f"\n📈 Calculation Engines Summary:")
        print(f"   Engines with Data: {engines_with_data}/{total_engines} ({completeness_ratio:.1%})")
        print(f"   Data Status: {'✅ COMPLETE' if completeness_ratio >= 0.8 else '⚠️ PARTIAL' if completeness_ratio > 0.5 else '❌ INSUFFICIENT'}")
        
        self.verification_results['calculation_engines'] = engine_data
        self.summary_stats['engines_completeness'] = completeness_ratio
    
    async def _verify_data_quality(self, db):
        """Verify data quality and recency"""
        print("\n📊 3. Data Quality Verification")
        print("-" * 60)
        
        quality_metrics = {}
        
        # Check market data freshness
        stmt = select(
            func.max(MarketDataCache.date).label('latest_date'),
            func.count(MarketDataCache.id).label('total_records')
        )
        result = await db.execute(stmt)
        market_data_info = result.one_or_none()
        
        if market_data_info:
            latest_date = market_data_info.latest_date
            days_old = (datetime.now().date() - latest_date).days if latest_date else float('inf')
            quality_metrics['market_data_freshness'] = {
                'latest_date': latest_date,
                'days_old': days_old,
                'total_records': market_data_info.total_records,
                'is_fresh': days_old <= 7
            }
            
            freshness_icon = "✅" if days_old <= 7 else "⚠️" if days_old <= 30 else "❌"
            print(f"{freshness_icon} Market Data Freshness: {days_old} days old (latest: {latest_date})")
        
        # Check position data completeness
        demo_portfolio_ids = []
        for email, data in self.verification_results.get('portfolios', {}).items():
            if data.get('portfolio_id'):
                demo_portfolio_ids.append(data['portfolio_id'])
        
        if demo_portfolio_ids:
            # Positions with prices
            stmt = select(func.count(Position.id)).where(
                Position.portfolio_id.in_(demo_portfolio_ids),
                Position.last_price.is_not(None)
            )
            result = await db.execute(stmt)
            positions_with_prices = result.scalar() or 0
            
            total_positions = self.summary_stats.get('total_positions', 0)
            price_coverage = positions_with_prices / total_positions if total_positions > 0 else 0
            
            quality_metrics['price_coverage'] = {
                'positions_with_prices': positions_with_prices,
                'total_positions': total_positions,
                'coverage_ratio': price_coverage
            }
            
            price_icon = "✅" if price_coverage >= 0.9 else "⚠️" if price_coverage >= 0.7 else "❌"
            print(f"{price_icon} Price Coverage: {positions_with_prices}/{total_positions} ({price_coverage:.1%})")
        
        self.verification_results['data_quality'] = quality_metrics
    
    async def _generate_verification_summary(self) -> Dict[str, Any]:
        """Generate comprehensive verification summary"""
        print("\n" + "="*90)
        print("📋 VERIFICATION SUMMARY")
        print("="*90)
        
        # Portfolio status
        portfolios = self.verification_results.get('portfolios', {})
        portfolios_found = len([p for p in portfolios.values() if p.get('status') == 'FOUND'])
        
        print(f"🎯 Demo Portfolios: {portfolios_found}/3 found")
        
        # Position status  
        total_positions = self.summary_stats.get('total_positions', 0)
        expected_positions = 63  # 16 + 17 + 30
        print(f"📊 Positions: {total_positions}/{expected_positions} ({total_positions/expected_positions:.1%})")
        
        # Calculation engine status
        engines_completeness = self.summary_stats.get('engines_completeness', 0)
        print(f"🔧 Calculation Engines: {engines_completeness:.1%} have data")
        
        # Data quality
        quality = self.verification_results.get('data_quality', {})
        market_fresh = quality.get('market_data_freshness', {}).get('is_fresh', False)
        price_coverage = quality.get('price_coverage', {}).get('coverage_ratio', 0)
        
        print(f"📈 Data Quality: Market data {'✅ Fresh' if market_fresh else '⚠️ Stale'}, Price coverage {price_coverage:.1%}")
        
        # Overall readiness assessment
        readiness_score = (
            (portfolios_found / 3) * 0.3 +
            (total_positions / expected_positions) * 0.2 +
            engines_completeness * 0.3 +
            (1 if market_fresh else 0.5) * 0.1 +
            price_coverage * 0.1
        )
        
        if readiness_score >= 0.9:
            readiness_status = "✅ READY"
            readiness_message = "All systems ready for Phase 2.0 Portfolio Report Generator"
        elif readiness_score >= 0.7:
            readiness_status = "⚠️ MOSTLY READY"
            readiness_message = "Minor issues identified, can proceed with caution"
        else:
            readiness_status = "❌ NOT READY"
            readiness_message = "Critical issues must be resolved before proceeding"
        
        print(f"\n🎯 OVERALL READINESS: {readiness_status} ({readiness_score:.1%})")
        print(f"💡 Assessment: {readiness_message}")
        
        # Recommendations
        recommendations = []
        
        if portfolios_found < 3:
            recommendations.append("Run demo data seeding to create missing portfolios")
        
        if engines_completeness < 0.8:
            recommendations.append("Run batch calculations to populate calculation engine data")
        
        if not market_fresh:
            recommendations.append("Update market data cache with recent prices")
        
        if price_coverage < 0.9:
            recommendations.append("Verify position pricing and market data alignment")
        
        if recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print(f"\n✅ No action required - system is ready!")
        
        return {
            'verification_timestamp': datetime.now(),
            'readiness_score': readiness_score,
            'readiness_status': readiness_status,
            'portfolios_found': portfolios_found,
            'total_positions': total_positions,
            'engines_completeness': engines_completeness,
            'data_quality': quality,
            'recommendations': recommendations,
            'detailed_results': self.verification_results,
            'ready_for_phase_2': readiness_score >= 0.7
        }


async def main():
    """Run the verification process"""
    verifier = DemoPortfolioVerifier()
    summary = await verifier.verify_all_portfolios()
    
    print(f"\n🏁 Verification completed at {summary['verification_timestamp']}")
    print(f"📁 Run this script anytime with: python scripts/verify_demo_portfolios.py")
    
    return summary


if __name__ == "__main__":
    asyncio.run(main())