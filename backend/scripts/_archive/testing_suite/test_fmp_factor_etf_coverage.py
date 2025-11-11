#!/usr/bin/env python3
"""
Test FMP Coverage for Factor ETFs
Validates that FMP can provide data for all factor ETFs before removing YFinance
"""
import asyncio
import os
from datetime import date, timedelta
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.market_data_service import market_data_service
from app.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)

# Factor ETFs we need to validate
FACTOR_ETFS = {
    "SPY": "Market Factor (S&P 500)",
    "VTV": "Value Factor", 
    "VUG": "Growth Factor",
    "MTUM": "Momentum Factor",
    "QUAL": "Quality Factor", 
    "SLY": "Size Factor (Small Cap)",
    "SIZE": "Size Factor (Alternative)",  # Alternative SIZE symbol
    "USMV": "Low Volatility Factor"
}

# Additional symbols to test (mentioned in BRK.B issue)
ADDITIONAL_TEST_SYMBOLS = {
    "BRK.B": "Berkshire Hathaway Class B (problematic symbol)",
    "BRK-B": "Berkshire Hathaway Class B (alternative format)"
}

async def test_fmp_historical_data(symbols: List[str], days_back: int = 90) -> Dict[str, Dict[str, Any]]:
    """
    Test FMP historical data availability for given symbols
    
    Args:
        symbols: List of symbols to test
        days_back: Days of historical data to request
        
    Returns:
        Dict mapping symbol to test results
    """
    results = {}
    start_date = date.today() - timedelta(days=days_back)
    end_date = date.today()
    
    async with AsyncSessionLocal() as db:
        for symbol in symbols:
            logger.info(f"Testing FMP coverage for {symbol}...")
            
            try:
                # Test current price using hybrid approach (FMP primary)
                hybrid_price_result = await market_data_service.fetch_stock_prices_hybrid([symbol])
                hybrid_price_data = hybrid_price_result.get(symbol, {})
                current_price = hybrid_price_data.get('price') if hybrid_price_data else None
                
                # Also test legacy method for comparison
                legacy_price_result = await market_data_service.fetch_current_prices([symbol])
                legacy_price = legacy_price_result.get(symbol)
                
                # Test historical data 
                historical_result = await market_data_service.bulk_fetch_and_cache(
                    db=db,
                    symbols=[symbol],
                    days_back=days_back
                )
                
                # Analyze results
                historical_records = historical_result.get('total_records', 0)
                errors = historical_result.get('errors', [])
                symbol_errors = [e for e in errors if symbol in str(e)]
                
                results[symbol] = {
                    'current_price': current_price,
                    'current_price_available': current_price is not None,
                    'historical_records': historical_records,
                    'historical_available': historical_records > 0,
                    'errors': symbol_errors,
                    'expected_records': days_back,  # Rough estimate
                    'coverage_ratio': historical_records / max(days_back, 1) if historical_records else 0,
                    'test_passed': current_price is not None and historical_records > 0 and len(symbol_errors) == 0
                }
                
                logger.info(f"✅ {symbol}: Current=${current_price}, Historical={historical_records} records")
                
            except Exception as e:
                logger.error(f"❌ {symbol}: Error during testing - {str(e)}")
                results[symbol] = {
                    'current_price': None,
                    'current_price_available': False,
                    'historical_records': 0,
                    'historical_available': False,
                    'errors': [str(e)],
                    'expected_records': days_back,
                    'coverage_ratio': 0,
                    'test_passed': False,
                    'exception': str(e)
                }
    
    return results

async def test_fmp_gics_data(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Test FMP GICS sector/industry data for symbols
    
    Args:
        symbols: List of symbols to test
        
    Returns:
        Dict mapping symbol to GICS test results
    """
    results = {}
    
    async with AsyncSessionLocal() as db:
        try:
            gics_result = await market_data_service.fetch_gics_data(symbols)
            
            for symbol in symbols:
                gics_data = gics_result.get(symbol, {})
                sector = gics_data.get('sector')
                industry = gics_data.get('industry')
                
                results[symbol] = {
                    'sector': sector,
                    'industry': industry,
                    'sector_available': sector is not None,
                    'industry_available': industry is not None,
                    'gics_complete': sector is not None and industry is not None
                }
                
        except Exception as e:
            logger.error(f"GICS data test failed: {str(e)}")
            for symbol in symbols:
                results[symbol] = {
                    'sector': None,
                    'industry': None, 
                    'sector_available': False,
                    'industry_available': False,
                    'gics_complete': False,
                    'exception': str(e)
                }
    
    return results

def print_coverage_report(
    factor_results: Dict[str, Dict[str, Any]], 
    additional_results: Dict[str, Dict[str, Any]],
    gics_results: Dict[str, Dict[str, Any]]
):
    """Print comprehensive coverage report"""
    
    print("\n" + "="*80)
    print("🔍 FMP COVERAGE VALIDATION REPORT")
    print("="*80)
    
    # Factor ETFs Report
    print("\n📊 FACTOR ETFs COVERAGE:")
    print("-"*50)
    
    total_factor_etfs = len(FACTOR_ETFS)
    passed_factor_etfs = 0
    
    for symbol, description in FACTOR_ETFS.items():
        result = factor_results.get(symbol, {})
        status = "✅ PASS" if result.get('test_passed', False) else "❌ FAIL"
        
        if result.get('test_passed', False):
            passed_factor_etfs += 1
            
        current_price = result.get('current_price', 'N/A')
        historical_count = result.get('historical_records', 0)
        coverage = result.get('coverage_ratio', 0)
        
        print(f"{status} {symbol:5} - {description}")
        print(f"      Current Price: ${current_price}")
        print(f"      Historical: {historical_count} records ({coverage:.1%} coverage)")
        
        errors = result.get('errors', [])
        if errors:
            print(f"      Errors: {errors}")
        print()
    
    # Additional Symbols Report  
    print("\n📈 ADDITIONAL TEST SYMBOLS:")
    print("-"*50)
    
    for symbol, description in ADDITIONAL_TEST_SYMBOLS.items():
        result = additional_results.get(symbol, {})
        status = "✅ PASS" if result.get('test_passed', False) else "❌ FAIL"
        
        current_price = result.get('current_price', 'N/A')
        historical_count = result.get('historical_records', 0)
        coverage = result.get('coverage_ratio', 0)
        
        print(f"{status} {symbol:6} - {description}")
        print(f"      Current Price: ${current_price}")
        print(f"      Historical: {historical_count} records ({coverage:.1%} coverage)")
        
        errors = result.get('errors', [])
        if errors:
            print(f"      Errors: {errors}")
        print()
    
    # GICS Data Report
    print("\n🏢 GICS SECTOR/INDUSTRY DATA:")
    print("-"*50)
    
    all_symbols = list(FACTOR_ETFS.keys()) + list(ADDITIONAL_TEST_SYMBOLS.keys())
    gics_complete_count = 0
    
    for symbol in all_symbols:
        gics_result = gics_results.get(symbol, {})
        complete = gics_result.get('gics_complete', False)
        status = "✅ COMPLETE" if complete else "⚠️ PARTIAL"
        
        if complete:
            gics_complete_count += 1
            
        sector = gics_result.get('sector', 'N/A')
        industry = gics_result.get('industry', 'N/A')
        
        print(f"{status} {symbol:6} - Sector: {sector}, Industry: {industry}")
    
    # Summary Report
    print("\n" + "="*80)
    print("📋 SUMMARY REPORT")
    print("="*80)
    
    factor_pass_rate = passed_factor_etfs / total_factor_etfs if total_factor_etfs > 0 else 0
    total_symbols = len(all_symbols)
    gics_completion_rate = gics_complete_count / total_symbols if total_symbols > 0 else 0
    
    print(f"Factor ETF Coverage: {passed_factor_etfs}/{total_factor_etfs} ({factor_pass_rate:.1%})")
    print(f"GICS Data Completion: {gics_complete_count}/{total_symbols} ({gics_completion_rate:.1%})")
    
    # Recommendation
    print("\n🎯 RECOMMENDATION:")
    if factor_pass_rate >= 0.9:  # 90% or better
        print("✅ FMP shows excellent coverage for factor ETFs")
        print("✅ Safe to proceed with YFinance removal")
        print("✅ BRK.B/BRK-B testing provides symbol variant guidance")
    elif factor_pass_rate >= 0.7:  # 70-89%
        print("⚠️ FMP shows good but incomplete coverage") 
        print("⚠️ Review failing symbols before YFinance removal")
        print("⚠️ Consider keeping YFinance as fallback for missing symbols")
    else:
        print("❌ FMP coverage insufficient for factor ETFs")
        print("❌ Do NOT remove YFinance until coverage improves")
        print("❌ Consider alternative data provider or FMP account upgrade")
    
    print("\n" + "="*80)

async def main():
    """Main test function"""
    print("🚀 Starting FMP Coverage Validation for Factor ETFs...")
    print(f"Testing {len(FACTOR_ETFS)} factor ETFs and {len(ADDITIONAL_TEST_SYMBOLS)} additional symbols")
    
    # Test historical data coverage
    print("\n1️⃣ Testing Factor ETF Historical Data...")
    factor_symbols = list(FACTOR_ETFS.keys())
    factor_results = await test_fmp_historical_data(factor_symbols, days_back=90)
    
    print("\n2️⃣ Testing Additional Symbols (BRK.B variants)...")
    additional_symbols = list(ADDITIONAL_TEST_SYMBOLS.keys()) 
    additional_results = await test_fmp_historical_data(additional_symbols, days_back=90)
    
    print("\n3️⃣ Testing GICS Sector/Industry Data...")
    all_symbols = factor_symbols + additional_symbols
    gics_results = await test_fmp_gics_data(all_symbols)
    
    # Generate comprehensive report
    print_coverage_report(factor_results, additional_results, gics_results)

if __name__ == "__main__":
    asyncio.run(main())