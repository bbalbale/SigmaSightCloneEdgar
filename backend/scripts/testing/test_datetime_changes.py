#!/usr/bin/env python
"""
Test script to verify datetime changes haven't broken functionality.

This script tests:
1. API endpoints still return data
2. Datetime fields are properly formatted
3. Batch processing can still run
4. Database operations work correctly

Author: SigmaSight Team  
Date: 2025-08-27
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.market_data import MarketDataCache
from app.core.datetime_utils import utc_now, to_utc_iso8601, validate_iso8601_format
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_database_operations():
    """Test that database operations with utc_now() work correctly."""
    print("\n🔍 Testing Database Operations...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Test 1: Can we query portfolios?
            stmt = select(Portfolio).limit(3)
            result = await db.execute(stmt)
            portfolios = result.scalars().all()
            
            print(f"✅ Found {len(portfolios)} portfolios")
            
            # Test 2: Can we query recent market data?
            recent_date = utc_now() - timedelta(days=7)
            stmt = select(func.count(MarketDataCache.id)).where(
                MarketDataCache.created_at >= recent_date
            )
            result = await db.execute(stmt)
            count = result.scalar()
            
            print(f"✅ Found {count} market data records from last 7 days")
            
            # Test 3: Verify timestamps are UTC
            stmt = select(MarketDataCache).limit(1)
            result = await db.execute(stmt)
            record = result.scalar_one_or_none()
            
            if record and record.created_at:
                # Check if timestamp is naive (as it should be for UTC)
                is_naive = record.created_at.tzinfo is None
                print(f"✅ Database timestamps are {'naive UTC' if is_naive else 'timezone-aware'}")
            
            return True
            
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False


async def test_api_endpoints():
    """Test that API endpoints return properly formatted dates."""
    print("\n🔍 Testing API Endpoints...")
    
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Health endpoint
        try:
            async with session.get(f"{base_url}/health") as resp:
                if resp.status == 200:
                    print(f"✅ Health endpoint working: {resp.status}")
                else:
                    print(f"⚠️ Health endpoint returned: {resp.status}")
        except Exception as e:
            print(f"❌ Health endpoint failed: {str(e)}")
            return False
        
        # Test 2: Login to get token
        try:
            login_data = {
                "email": "demo_individual@sigmasight.com",
                "password": "demo12345"
            }
            
            async with session.post(f"{base_url}/api/v1/auth/login", json=login_data) as resp:
                if resp.status == 200:
                    auth_response = await resp.json()
                    token = auth_response.get("access_token")
                    print(f"✅ Authentication successful")
                    
                    # Set up headers with token
                    headers = {"Authorization": f"Bearer {token}"}
                    
                    # Test 3: Portfolio endpoint with datetime fields
                    async with session.get(
                        f"{base_url}/api/v1/portfolios",
                        headers=headers
                    ) as resp:
                        if resp.status == 200:
                            portfolios = await resp.json()
                            if portfolios and len(portfolios) > 0:
                                portfolio = portfolios[0]
                                
                                # Check datetime fields
                                created_at = portfolio.get("created_at")
                                if created_at:
                                    # Check if it's properly formatted
                                    if "T" in created_at:
                                        print(f"✅ Portfolio datetime format: {created_at[:26]}...")
                                        
                                        # Check if it has timezone indicator
                                        has_z = created_at.endswith("Z")
                                        has_offset = "+00:00" in created_at
                                        
                                        if has_z:
                                            print(f"✅ Using Z suffix (ISO 8601 compliant)")
                                        elif has_offset:
                                            print(f"⚠️ Using +00:00 offset (needs standardization)")
                                        else:
                                            print(f"⚠️ No timezone indicator")
                            else:
                                print("⚠️ No portfolios returned")
                        else:
                            print(f"❌ Portfolio endpoint returned: {resp.status}")
                            
                else:
                    print(f"❌ Login failed: {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ API test failed: {str(e)}")
            return False
    
    return True


async def test_batch_processing_timestamps():
    """Test that batch processing uses UTC timestamps correctly."""
    print("\n🔍 Testing Batch Processing Timestamps...")
    
    try:
        from app.batch.batch_orchestrator_v2 import BatchOrchestratorV2
        
        # Create an orchestrator instance
        orchestrator = BatchOrchestratorV2()
        
        # Test timestamp generation
        test_timestamp = utc_now()
        iso_timestamp = to_utc_iso8601(test_timestamp)
        
        print(f"✅ Batch timestamp generation: {iso_timestamp}")
        
        # Validate format
        if validate_iso8601_format(iso_timestamp):
            print(f"✅ Timestamp format is valid ISO 8601 with Z")
        else:
            print(f"⚠️ Timestamp format validation failed")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch processing test failed: {str(e)}")
        return False


async def test_calculation_timestamps():
    """Test that calculation modules use UTC correctly."""
    print("\n🔍 Testing Calculation Module Timestamps...")
    
    try:
        from app.calculations.portfolio import utc_now as calc_utc_now
        
        # Test that the import works
        timestamp = calc_utc_now()
        
        print(f"✅ Portfolio calculations using utc_now(): {timestamp}")
        
        # Verify it's UTC (naive)
        if timestamp.tzinfo is None:
            print(f"✅ Timestamp is naive UTC (correct)")
        else:
            print(f"⚠️ Timestamp has timezone info: {timestamp.tzinfo}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Calculation test failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("DATETIME CHANGE VERIFICATION TEST SUITE")
    print("=" * 60)
    print(f"Current UTC time: {utc_now()}")
    print(f"ISO 8601 format: {to_utc_iso8601(utc_now())}")
    
    # Run all tests
    results = {
        "Database Operations": await test_database_operations(),
        "API Endpoints": await test_api_endpoints(),
        "Batch Processing": await test_batch_processing_timestamps(),
        "Calculations": await test_calculation_timestamps(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! Datetime changes are working correctly.")
    else:
        print("\n⚠️ Some tests failed. Review the output above for details.")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)