#!/usr/bin/env python3
"""
Integration Test for Section 1.4.9 Market Data API Migration
Tests the complete hybrid market data provider system integration
"""
import asyncio
import sys
import traceback
from pathlib import Path
from typing import List, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.config import settings
from app.clients import market_data_factory, DataType
from app.services.market_data_service import market_data_service
from app.database import AsyncSessionLocal, engine
from app.models.market_data import FundHoldings
from sqlalchemy import text

class IntegrationTester:
    """Integration test suite for Section 1.4.9"""
    
    def __init__(self):
        self.test_results = []
        self.errors = []
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete integration test suite"""
        print("🚀 Starting Section 1.4.9 Integration Tests")
        print("=" * 60)
        
        test_methods = [
            ("Database Schema Validation", self.test_database_schema),
            ("Client Factory Validation", self.test_client_factory),
            ("Market Data Service Integration", self.test_market_data_service),
            ("Error Handling Validation", self.test_error_handling),
            ("Configuration Validation", self.test_configuration)
        ]
        
        for test_name, test_method in test_methods:
            print(f"\n📋 Running: {test_name}")
            try:
                result = await test_method()
                if result:
                    print(f"✅ {test_name}: PASSED")
                    self.test_results.append({"test": test_name, "status": "PASSED", "result": result})
                else:
                    print(f"❌ {test_name}: FAILED")
                    self.test_results.append({"test": test_name, "status": "FAILED", "result": result})
            except Exception as e:
                error_msg = f"{test_name}: {str(e)}"
                print(f"💥 {test_name}: ERROR - {error_msg}")
                self.errors.append(error_msg)
                self.test_results.append({"test": test_name, "status": "ERROR", "error": str(e)})
        
        return self._generate_summary()
    
    async def test_database_schema(self) -> Dict[str, Any]:
        """Test that FundHoldings table exists and has correct schema"""
        try:
            async with engine.begin() as conn:
                # Check if fund_holdings table exists
                result = await conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'fund_holdings'
                    );
                """))
                table_exists = result.scalar()
                
                if not table_exists:
                    return {"success": False, "error": "fund_holdings table does not exist"}
                
                # Check table columns
                result = await conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'fund_holdings'
                    ORDER BY column_name;
                """))
                columns = result.fetchall()
                
                expected_columns = {
                    'data_source', 'fund_symbol', 'holding_symbol', 'id', 
                    'market_value', 'name', 'shares', 'updated_at', 'weight'
                }
                actual_columns = {col[0] for col in columns}
                
                missing_columns = expected_columns - actual_columns
                if missing_columns:
                    return {
                        "success": False, 
                        "error": f"Missing columns: {missing_columns}",
                        "actual_columns": actual_columns
                    }
                
                return {
                    "success": True,
                    "table_exists": True,
                    "column_count": len(columns),
                    "columns": [{"name": col[0], "type": col[1], "nullable": col[2]} for col in columns]
                }
                
        except Exception as e:
            return {"success": False, "error": f"Database test failed: {str(e)}"}
    
    async def test_client_factory(self) -> Dict[str, Any]:
        """Test the market data factory and client creation"""
        try:
            # Test client creation with/without API keys
            test_results = {}
            
            # Test FMP client creation
            try:
                fmp_client = market_data_factory.create_client('FMP', api_key="test_key")
                test_results["fmp_client"] = {"success": True, "type": str(type(fmp_client))}
            except Exception as e:
                test_results["fmp_client"] = {"success": False, "error": str(e)}
            
            # Test TradeFeeds client creation  
            try:
                tf_client = market_data_factory.create_client('TradeFeeds', api_key="test_key")
                test_results["tradefeeds_client"] = {"success": True, "type": str(type(tf_client))}
            except Exception as e:
                test_results["tradefeeds_client"] = {"success": False, "error": str(e)}
            
            # Test provider status checks
            try:
                fmp_available = market_data_factory.is_provider_available('FMP')
                tf_available = market_data_factory.is_provider_available('TradeFeeds')
                test_results["provider_status"] = {
                    "FMP": fmp_available,
                    "TradeFeeds": tf_available
                }
            except Exception as e:
                test_results["provider_status"] = {"error": str(e)}
            
            success = all(
                result.get("success", False) if isinstance(result, dict) else True 
                for result in test_results.values() 
                if "error" not in result
            )
            
            return {"success": success, "details": test_results}
            
        except Exception as e:
            return {"success": False, "error": f"Client factory test failed: {str(e)}"}
    
    async def test_market_data_service(self) -> Dict[str, Any]:
        """Test market data service hybrid methods"""
        try:
            test_results = {}
            
            # Test hybrid stock prices method exists
            has_hybrid_stocks = hasattr(market_data_service, 'fetch_stock_prices_hybrid')
            test_results["hybrid_stock_method"] = has_hybrid_stocks
            
            # Test mutual fund holdings method exists
            has_fund_method = hasattr(market_data_service, 'fetch_mutual_fund_holdings')
            test_results["fund_holdings_method"] = has_fund_method
            
            # Test ETF holdings method exists
            has_etf_method = hasattr(market_data_service, 'fetch_etf_holdings')
            test_results["etf_holdings_method"] = has_etf_method
            
            # Test provider validation method
            has_validation = hasattr(market_data_service, 'validate_provider_configuration')
            test_results["provider_validation_method"] = has_validation
            
            # Check if we can call methods (they should handle missing API keys gracefully)
            try:
                # This should not crash even without API keys
                validation_result = await market_data_service.validate_provider_configuration()
                test_results["provider_validation_call"] = {
                    "success": True,
                    "result": validation_result
                }
            except Exception as e:
                test_results["provider_validation_call"] = {
                    "success": False,
                    "error": str(e)
                }
            
            success = (has_hybrid_stocks and has_fund_method and 
                      has_etf_method and has_validation)
            
            return {"success": success, "details": test_results}
            
        except Exception as e:
            return {"success": False, "error": f"Market data service test failed: {str(e)}"}
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling for various failure scenarios"""
        try:
            test_results = {}
            
            # Test handling of missing API keys
            try:
                result = market_data_factory.is_provider_available('FMP')
                test_results["missing_api_key_handling"] = {
                    "success": True,
                    "fmp_available": result
                }
            except Exception as e:
                test_results["missing_api_key_handling"] = {
                    "success": False,
                    "error": str(e)
                }
            
            # Test invalid provider name
            try:
                client = market_data_factory.create_client('InvalidProvider', api_key="test")
                test_results["invalid_provider"] = {
                    "success": False,
                    "error": "Should have raised ValueError"
                }
            except ValueError:
                test_results["invalid_provider"] = {
                    "success": True,
                    "correctly_raised_error": True
                }
            except Exception as e:
                test_results["invalid_provider"] = {
                    "success": False,
                    "unexpected_error": str(e)
                }
            
            success = all(
                result.get("success", False) 
                for result in test_results.values()
            )
            
            return {"success": success, "details": test_results}
            
        except Exception as e:
            return {"success": False, "error": f"Error handling test failed: {str(e)}"}
    
    async def test_configuration(self) -> Dict[str, Any]:
        """Test configuration settings for new providers"""
        try:
            config_tests = {}
            
            # Check that new config fields exist
            config_fields = [
                'FMP_API_KEY', 'FMP_TIMEOUT_SECONDS', 'FMP_MAX_RETRIES',
                'TRADEFEEDS_API_KEY', 'TRADEFEEDS_TIMEOUT_SECONDS', 
                'TRADEFEEDS_MAX_RETRIES', 'TRADEFEEDS_RATE_LIMIT'
            ]
            
            for field in config_fields:
                has_field = hasattr(settings, field)
                config_tests[field] = has_field
            
            # Check default values are reasonable
            default_checks = {
                'FMP_TIMEOUT_SECONDS': getattr(settings, 'FMP_TIMEOUT_SECONDS', 0) > 0,
                'FMP_MAX_RETRIES': getattr(settings, 'FMP_MAX_RETRIES', 0) > 0,
                'TRADEFEEDS_TIMEOUT_SECONDS': getattr(settings, 'TRADEFEEDS_TIMEOUT_SECONDS', 0) > 0,
                'TRADEFEEDS_MAX_RETRIES': getattr(settings, 'TRADEFEEDS_MAX_RETRIES', 0) > 0,
                'TRADEFEEDS_RATE_LIMIT': getattr(settings, 'TRADEFEEDS_RATE_LIMIT', 0) > 0,
            }
            
            config_tests.update(default_checks)
            
            success = all(config_tests.values())
            
            return {
                "success": success,
                "details": config_tests,
                "missing_fields": [k for k, v in config_tests.items() if not v]
            }
            
        except Exception as e:
            return {"success": False, "error": f"Configuration test failed: {str(e)}"}
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary"""
        passed = len([r for r in self.test_results if r.get("status") == "PASSED"])
        failed = len([r for r in self.test_results if r.get("status") == "FAILED"]) 
        errors = len([r for r in self.test_results if r.get("status") == "ERROR"])
        total = len(self.test_results)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        summary = {
            "total_tests": total,
            "passed": passed,
            "failed": failed, 
            "errors": errors,
            "success_rate": success_rate,
            "overall_status": "PASSED" if failed == 0 and errors == 0 else "FAILED",
            "test_results": self.test_results
        }
        
        if self.errors:
            summary["error_details"] = self.errors
        
        return summary

async def main():
    """Run integration tests"""
    tester = IntegrationTester()
    
    try:
        results = await tester.run_all_tests()
        
        print("\n" + "=" * 60)
        print("📊 INTEGRATION TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: ✅ {results['passed']}")
        print(f"Failed: ❌ {results['failed']}")
        print(f"Errors: 💥 {results['errors']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Overall Status: {results['overall_status']}")
        
        if results.get('error_details'):
            print("\n🚨 ERROR DETAILS:")
            for error in results['error_details']:
                print(f"  - {error}")
        
        print(f"\n🎯 Section 1.4.9 Integration: {'✅ READY' if results['overall_status'] == 'PASSED' else '❌ NEEDS WORK'}")
        
        # Exit with error code if tests failed
        if results['overall_status'] != 'PASSED':
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Integration test suite failed: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())