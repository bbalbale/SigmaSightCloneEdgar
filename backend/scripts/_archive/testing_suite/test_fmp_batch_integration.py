#!/usr/bin/env python3
"""
Test Complete FMP Integration with Batch Processing System
Tests that the FMP hybrid approach works end-to-end with batch processing
"""
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
from app.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)

# Use the Growth Investor portfolio for testing
TEST_PORTFOLIO_ID = "741c8741-0274-499f-b543-ce188ed47189"

async def test_fmp_batch_integration():
    """Test complete FMP integration with batch processing"""
    
    print("🧪 Testing Complete FMP Integration with Batch Processing...")
    print(f"Portfolio ID: {TEST_PORTFOLIO_ID}")
    
    try:
        # Test complete batch sequence
        print("\n1️⃣ Running complete batch sequence...")
        
        start_time = asyncio.get_event_loop().time()
        
        results = await batch_orchestrator_v2.run_daily_batch_sequence(TEST_PORTFOLIO_ID)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        print(f"⏱️ Total execution time: {duration:.2f} seconds")
        print(f"📊 Total jobs: {len(results)}")
        
        # Analyze results
        successful_jobs = [r for r in results if r['status'] == 'completed']
        failed_jobs = [r for r in results if r['status'] == 'failed']
        
        print(f"\n2️⃣ Results Analysis:")
        print(f"  ✅ Successful jobs: {len(successful_jobs)}/{len(results)}")
        print(f"  ❌ Failed jobs: {len(failed_jobs)}/{len(results)}")
        
        for result in results:
            status_emoji = "✅" if result['status'] == 'completed' else "❌"
            duration = result.get('duration_seconds', 0)
            job_name = result['job_name']
            print(f"    {status_emoji} {job_name}: {duration:.2f}s")
            
            if result['status'] == 'failed':
                error = result.get('error', 'Unknown error')
                print(f"        Error: {error}")
        
        # Check specifically for market data job
        market_data_jobs = [r for r in results if 'market_data' in r['job_name'].lower()]
        if market_data_jobs:
            market_job = market_data_jobs[0]
            print(f"\n3️⃣ Market Data Integration:")
            print(f"  Status: {market_job['status']}")
            print(f"  Duration: {market_job.get('duration_seconds', 0):.2f}s")
            
            if 'result' in market_job:
                market_result = market_job['result']
                if isinstance(market_result, dict):
                    symbols_updated = market_result.get('symbols_updated', 0)
                    total_records = market_result.get('total_records', 0)
                    print(f"  Symbols updated: {symbols_updated}")
                    print(f"  Records processed: {total_records}")
                    
                    if total_records > 0:
                        print("  ✅ FMP integration working in batch processing!")
                    else:
                        print("  ⚠️ No records processed - may be using cached data")
        
        # Overall assessment
        success_rate = len(successful_jobs) / len(results) if results else 0
        
        print(f"\n4️⃣ Overall Assessment:")
        print(f"  Success rate: {success_rate:.1%}")
        print(f"  Performance: {'✅ Excellent' if duration < 40 else '⚠️ Acceptable' if duration < 60 else '❌ Slow'} ({duration:.2f}s)")
        
        if success_rate >= 0.8:
            print("  ✅ FMP migration successful!")
            return True
        else:
            print("  ❌ Batch processing issues detected")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fmp_batch_integration())
    
    if success:
        print("\n🎉 FMP BATCH INTEGRATION TEST PASSED")
        print("🎉 Ready to remove YFinance dependencies")
    else:
        print("\n❌ FMP BATCH INTEGRATION TEST FAILED")
        print("❌ Fix issues before removing YFinance")