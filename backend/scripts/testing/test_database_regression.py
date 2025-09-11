#!/usr/bin/env python3
"""
Database Module Regression Testing Script
Tests all critical components after database module unification
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Test imports from unified database module
from app.database import AsyncSessionLocal, get_async_session, Base, get_db
from app.models import User, Portfolio, Position, PortfolioSnapshot
from app.core.dependencies import get_current_user

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class DatabaseRegressionTester:
    def __init__(self):
        self.results: Dict[str, bool] = {}
        self.errors: Dict[str, str] = {}
        
    def log_test(self, test_name: str, passed: bool, error: str = None):
        """Log test result with color coding"""
        self.results[test_name] = passed
        if error:
            self.errors[test_name] = error
            
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"{status} {test_name}")
        if error and not passed:
            print(f"  {RED}Error: {error}{RESET}")
    
    async def test_direct_session_creation(self):
        """Test direct AsyncSessionLocal usage"""
        test_name = "Direct Session Creation"
        try:
            async with AsyncSessionLocal() as db:
                # Test basic query
                result = await db.execute(text("SELECT 1"))
                assert result.scalar() == 1
                
                # Test model query
                users = await db.execute(select(User).limit(1))
                user_count = len(users.scalars().all())
                
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def test_context_manager_session(self):
        """Test get_async_session context manager"""
        test_name = "Context Manager Session"
        try:
            async with get_async_session() as db:
                # Test transaction
                result = await db.execute(text("SELECT COUNT(*) FROM users"))
                count = result.scalar()
                
                # Test model operations
                portfolios = await db.execute(
                    select(Portfolio).limit(5)
                )
                portfolio_list = portfolios.scalars().all()
                
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def test_batch_processing_imports(self):
        """Test batch processing module imports"""
        test_name = "Batch Processing Imports"
        try:
            # Import all batch modules
            from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
            from app.batch.market_data_sync import sync_market_data
            from app.batch.daily_calculations import run_daily_calculations
            
            # Verify they can access database
            orchestrator = batch_orchestrator_v2
            
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def test_calculation_engine_imports(self):
        """Test calculation engine imports and database access"""
        test_name = "Calculation Engine Imports"
        try:
            # Import calculation modules (just verify they exist)
            import app.calculations.portfolio
            import app.calculations.greeks
            import app.calculations.factors
            import app.calculations.snapshots
            
            # Test a simple database operation in calculation context
            async with AsyncSessionLocal() as db:
                # Get a test portfolio
                result = await db.execute(
                    select(Portfolio).limit(1)
                )
                portfolio = result.scalar_one_or_none()
                
                if portfolio:
                    # Just verify we can access the portfolio
                    assert portfolio.id is not None
            
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def test_api_endpoint_imports(self):
        """Test API endpoint imports"""
        test_name = "API Endpoint Imports"
        try:
            # Import actual API modules that exist in v1 subdirectory
            import app.api.v1.auth
            import app.api.v1.portfolio  # Note: singular, not plural
            import app.api.v1.positions
            import app.api.v1.market_data
            import app.api.v1.risk
            import app.api.v1.modeling
            import app.api.v1.router
            
            from app.main import app
            
            # Verify FastAPI app exists
            assert app is not None
            
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def test_service_layer_imports(self):
        """Test service layer imports"""
        test_name = "Service Layer Imports"
        try:
            # Import service modules that exist
            from app.services.market_data_service import MarketDataService
            from app.services.correlation_service import CorrelationService
            # Note: stress_testing_service and factor_service may not exist yet
            
            # Create service instances (they should handle database internally)
            market_service = MarketDataService()
            
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def test_database_operations(self):
        """Test various database operations"""
        test_name = "Database Operations"
        try:
            async with AsyncSessionLocal() as db:
                # Test SELECT
                users = await db.execute(select(User).limit(3))
                user_list = users.scalars().all()
                
                # Test JOIN
                query = select(Portfolio).join(User).limit(5)
                portfolios = await db.execute(query)
                portfolio_list = portfolios.scalars().all()
                
                # Test COUNT
                count_query = select(Position).where(Position.quantity > 0)
                positions = await db.execute(count_query)
                position_count = len(positions.scalars().all())
                
                # Test transaction rollback
                await db.rollback()
                
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def test_concurrent_sessions(self):
        """Test multiple concurrent database sessions"""
        test_name = "Concurrent Sessions"
        try:
            async def query_task(task_id: int):
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        text(f"SELECT {task_id} as task_id, COUNT(*) FROM portfolios")
                    )
                    return result.first()
            
            # Run 5 concurrent queries
            tasks = [query_task(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Verify all completed
            assert len(results) == 5
            assert all(r is not None for r in results)
            
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def test_session_cleanup(self):
        """Test that sessions are properly cleaned up"""
        test_name = "Session Cleanup"
        try:
            # Create and close multiple sessions
            for i in range(10):
                async with AsyncSessionLocal() as db:
                    await db.execute(text("SELECT 1"))
                # Session should be closed here
            
            # Create sessions with context manager
            for i in range(10):
                async with get_async_session() as db:
                    await db.execute(text("SELECT 1"))
                # Session should be closed here
            
            self.log_test(test_name, True)
            return True
        except Exception as e:
            self.log_test(test_name, False, str(e))
            return False
    
    async def run_all_tests(self):
        """Run all regression tests"""
        print(f"\n{BLUE}=== Database Module Regression Testing ==={RESET}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Define test suite
        tests = [
            self.test_direct_session_creation,
            self.test_context_manager_session,
            self.test_batch_processing_imports,
            self.test_calculation_engine_imports,
            self.test_api_endpoint_imports,
            self.test_service_layer_imports,
            self.test_database_operations,
            self.test_concurrent_sessions,
            self.test_session_cleanup,
        ]
        
        # Run all tests
        for test in tests:
            await test()
            await asyncio.sleep(0.1)  # Small delay between tests
        
        # Summary
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        failed = total - passed
        
        print(f"\n{BLUE}=== Test Summary ==={RESET}")
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {failed}{RESET}")
        
        if failed > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for test_name, passed in self.results.items():
                if not passed:
                    print(f"  - {test_name}")
                    if test_name in self.errors:
                        print(f"    Error: {self.errors[test_name]}")
        
        success_rate = (passed / total) * 100 if total > 0 else 0
        print(f"\n{YELLOW}Success Rate: {success_rate:.1f}%{RESET}")
        
        return failed == 0


async def main():
    """Main test runner"""
    tester = DatabaseRegressionTester()
    success = await tester.run_all_tests()
    
    if success:
        print(f"\n{GREEN}✅ All regression tests passed!{RESET}")
        print("The database module unification is working correctly.")
        return 0
    else:
        print(f"\n{RED}❌ Some tests failed!{RESET}")
        print("Please review the errors above and fix any issues.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
