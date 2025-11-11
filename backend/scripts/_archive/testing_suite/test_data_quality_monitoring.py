#!/usr/bin/env python3
"""
Test Data Quality Monitoring System - Section 4.7
Validates the new pre-flight data quality validation functionality
"""
import sys
from pathlib import Path
from datetime import datetime
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.batch.data_quality import pre_flight_validation, DataQualityValidator
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_data_quality_system():
    """Test the complete data quality monitoring system"""
    print("\n" + "="*80)
    print("Data Quality Monitoring System Test")
    print("="*80)
    
    async with get_async_session() as db:
        print("\n📊 1. Testing Data Quality Validation (All Portfolios)")
        print("-" * 50)
        
        # Test 1: Validate all portfolios
        try:
            validation_results = await pre_flight_validation(db, portfolio_id=None)
            
            print(f"✅ Validation Status: {validation_results.get('status', 'unknown').upper()}")
            print(f"📈 Quality Score: {validation_results.get('quality_score', 0):.1%}")
            print(f"🎯 Total Symbols: {validation_results.get('total_symbols', 0)}")
            
            # Coverage details
            coverage = validation_results.get('coverage_details', {})
            if coverage:
                current = coverage.get('current_prices', {})
                historical = coverage.get('historical_data', {})
                freshness = coverage.get('data_freshness', {})
                
                print(f"💰 Current Price Coverage: {current.get('coverage_percentage', 0):.1%}")
                print(f"📚 Historical Data Coverage: {historical.get('coverage_percentage', 0):.1%}")
                print(f"🕐 Data Freshness: {freshness.get('freshness_percentage', 0):.1%}")
            
            # Show recommendations
            recommendations = validation_results.get('recommendations', [])
            if recommendations:
                print(f"💡 Recommendations ({len(recommendations)}):")
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"   {i}. {rec}")
            
        except Exception as e:
            print(f"❌ Validation failed: {str(e)}")
        
        print("\n📊 2. Testing Data Quality Validator Class")
        print("-" * 50)
        
        # Test 2: Direct validator class usage
        try:
            validator = DataQualityValidator()
            
            # Test threshold access
            print(f"📋 Quality Thresholds:")
            for key, value in validator.quality_thresholds.items():
                if key.endswith('_hours'):
                    print(f"   {key}: {value} hours")
                elif key.endswith('_days'):
                    print(f"   {key}: {value} days")
                else:
                    print(f"   {key}: {value:.0%}")
            
            # Test validation for first portfolio only
            class_results = await validator.validate_data_coverage(db, portfolio_id=None)
            print(f"✅ Direct validator test: {class_results.get('status', 'unknown').upper()}")
            
        except Exception as e:
            print(f"❌ Validator class test failed: {str(e)}")
        
        print("\n📊 3. Testing Symbol-Level Coverage Details")
        print("-" * 50)
        
        # Test 3: Detailed symbol analysis
        try:
            validation_results = await pre_flight_validation(db, portfolio_id=None)
            coverage = validation_results.get('coverage_details', {})
            
            if coverage:
                # Current prices
                current = coverage.get('current_prices', {})
                missing_symbols = current.get('missing_symbols', [])
                if missing_symbols:
                    print(f"❌ Missing Current Prices ({len(missing_symbols)}):")
                    for symbol in missing_symbols[:5]:
                        print(f"   • {symbol}")
                    if len(missing_symbols) > 5:
                        print(f"   • ... and {len(missing_symbols) - 5} more")
                else:
                    print("✅ All symbols have current price data")
                
                # Historical data
                historical = coverage.get('historical_data', {})
                insufficient_symbols = historical.get('insufficient_symbols', [])
                if insufficient_symbols:
                    print(f"⚠️ Insufficient Historical Data ({len(insufficient_symbols)}):")
                    for symbol in insufficient_symbols[:5]:
                        print(f"   • {symbol}")
                    if len(insufficient_symbols) > 5:
                        print(f"   • ... and {len(insufficient_symbols) - 5} more")
                else:
                    print("✅ All symbols have sufficient historical data")
                
                # Freshness
                freshness = coverage.get('data_freshness', {})
                stale_symbols = freshness.get('stale_symbols', [])
                if stale_symbols:
                    print(f"🕐 Stale Data ({len(stale_symbols)}):")
                    for symbol in stale_symbols[:5]:
                        print(f"   • {symbol}")
                    if len(stale_symbols) > 5:
                        print(f"   • ... and {len(stale_symbols) - 5} more")
                else:
                    print("✅ All symbols have fresh data")
            
        except Exception as e:
            print(f"❌ Symbol analysis failed: {str(e)}")
        
        print("\n📊 4. Testing Performance")
        print("-" * 50)
        
        # Test 4: Performance measurement
        try:
            start_time = datetime.now()
            validation_results = await pre_flight_validation(db, portfolio_id=None)
            duration = (datetime.now() - start_time).total_seconds()
            
            print(f"⚡ Validation Duration: {duration:.2f} seconds")
            print(f"🎯 Symbols per Second: {validation_results.get('total_symbols', 0) / duration:.1f}")
            
            if duration > 5.0:
                print("⚠️ Warning: Validation taking longer than 5 seconds")
            else:
                print("✅ Performance: Within acceptable limits")
                
        except Exception as e:
            print(f"❌ Performance test failed: {str(e)}")
    
    print("\n" + "="*80)
    print("📊 Data Quality Monitoring Test Summary")
    print("="*80)
    
    print("✅ Features Tested:")
    print("   1. Pre-flight validation function")
    print("   2. DataQualityValidator class")
    print("   3. Symbol-level coverage analysis")
    print("   4. Performance measurement")
    
    print("\n📋 Integration Points:")
    print("   • Batch orchestrator pre-flight validation")
    print("   • Admin API endpoints for quality monitoring")
    print("   • Quality score integration in batch results")
    print("   • Recommendation engine for data improvements")
    
    print("\n🎯 Next Steps:")
    print("   • Run batch processing to see integrated validation")
    print("   • Test admin API endpoints via FastAPI")
    print("   • Monitor batch logs for quality scores")
    print("   • Review recommendations for data refresh needs")


if __name__ == "__main__":
    asyncio.run(test_data_quality_system())