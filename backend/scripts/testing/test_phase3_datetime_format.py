#!/usr/bin/env python
"""
Test script to verify Phase 3 datetime format changes.

This script tests that API responses now use properly formatted
UTC ISO 8601 dates with Z suffix.

Author: SigmaSight Team
Date: 2025-08-27
"""

import asyncio
import json
import re
from typing import Dict, Any

import aiohttp
from app.core.datetime_utils import validate_iso8601_format
from app.core.logging import get_logger

logger = get_logger(__name__)


def check_datetime_format(value: str) -> Dict[str, Any]:
    """Check if a datetime string is properly formatted."""
    result = {
        "value": value,
        "has_z_suffix": value.endswith("Z") if value else False,
        "has_timezone_offset": "+00:00" in value if value else False,
        "is_valid_iso8601": validate_iso8601_format(value) if value else False,
        "has_t_separator": "T" in value if value else False,
    }
    
    # Determine overall status
    if result["is_valid_iso8601"]:
        result["status"] = "✅ CORRECT"
    elif result["has_timezone_offset"]:
        result["status"] = "⚠️ OLD FORMAT (+00:00)"
    elif result["has_t_separator"] and not result["has_z_suffix"]:
        result["status"] = "⚠️ MISSING Z"
    else:
        result["status"] = "❌ INVALID"
    
    return result


def find_datetime_fields(obj: Any, path: str = "") -> list:
    """Recursively find all datetime-like fields in an object."""
    datetime_fields = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            
            # Check if this looks like a datetime field
            if any(pattern in key.lower() for pattern in ['_at', 'date', 'time', 'stamp']):
                if isinstance(value, str) and ("T" in value or "-" in value):
                    datetime_fields.append((new_path, value))
            
            # Recurse
            datetime_fields.extend(find_datetime_fields(value, new_path))
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            datetime_fields.extend(find_datetime_fields(item, new_path))
    
    return datetime_fields


async def test_api_datetime_formats():
    """Test various API endpoints for proper datetime formatting."""
    print("\n🔍 Testing API Datetime Formats...")
    
    base_url = "http://localhost:8000"
    test_results = []
    
    async with aiohttp.ClientSession() as session:
        # First, get an auth token
        try:
            login_data = {
                "email": "demo_individual@sigmasight.com",
                "password": "demo12345"
            }
            
            async with session.post(f"{base_url}/api/v1/auth/login", json=login_data) as resp:
                if resp.status == 200:
                    auth_response = await resp.json()
                    token = auth_response.get("access_token")
                    headers = {"Authorization": f"Bearer {token}"}
                    print("✅ Authentication successful\n")
                else:
                    print(f"❌ Login failed: {resp.status}")
                    return
        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            return
        
        # Test endpoints
        test_endpoints = [
            ("/api/v1/portfolios", "Portfolios"),
            ("/api/v1/data/portfolio/demo-individual-investor-portfolio/data-quality", "Data Quality"),
            ("/api/v1/data/positions/details?portfolio_id=demo-individual-investor-portfolio", "Position Details"),
        ]
        
        for endpoint, name in test_endpoints:
            print(f"Testing {name} endpoint...")
            try:
                async with session.get(f"{base_url}{endpoint}", headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Find all datetime fields
                        datetime_fields = find_datetime_fields(data)
                        
                        if datetime_fields:
                            print(f"  Found {len(datetime_fields)} datetime fields:")
                            for field_path, value in datetime_fields[:5]:  # Show first 5
                                result = check_datetime_format(value)
                                print(f"    {field_path}: {result['status']}")
                                if result['status'] == "✅ CORRECT":
                                    print(f"      Value: {value[:26]}...Z")
                                else:
                                    print(f"      Value: {value[:30]}...")
                                
                                test_results.append({
                                    "endpoint": endpoint,
                                    "field": field_path,
                                    "format_check": result
                                })
                        else:
                            print(f"  No datetime fields found")
                    else:
                        print(f"  ⚠️ Endpoint returned: {resp.status}")
                        
            except Exception as e:
                print(f"  ❌ Error testing endpoint: {str(e)}")
            
            print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if test_results:
        correct_count = sum(1 for r in test_results if r['format_check']['status'] == "✅ CORRECT")
        old_format_count = sum(1 for r in test_results if r['format_check']['status'] == "⚠️ OLD FORMAT (+00:00)")
        invalid_count = sum(1 for r in test_results if "❌" in r['format_check']['status'])
        
        print(f"Total datetime fields tested: {len(test_results)}")
        print(f"✅ Correct format (Z suffix): {correct_count}")
        print(f"⚠️ Old format (+00:00): {old_format_count}")
        print(f"❌ Invalid format: {invalid_count}")
        
        if correct_count == len(test_results):
            print("\n🎉 All datetime fields are correctly formatted!")
        elif old_format_count > 0:
            print(f"\n⚠️ {old_format_count} fields still using old format (+00:00)")
            print("These may be coming from database serialization")
        
    else:
        print("No datetime fields were found to test")


async def test_direct_datetime_utils():
    """Test the datetime utilities directly."""
    print("\n🔍 Testing Datetime Utilities Directly...")
    
    from datetime import datetime
    from app.core.datetime_utils import utc_now, to_utc_iso8601, validate_iso8601_format
    
    # Test current time formatting
    now = utc_now()
    formatted = to_utc_iso8601(now)
    
    print(f"Current UTC time: {now}")
    print(f"Formatted: {formatted}")
    print(f"Valid ISO 8601: {validate_iso8601_format(formatted)}")
    
    # Test that Pydantic schemas use the new format
    from app.schemas.base import BaseSchema
    from datetime import datetime
    
    class TestModel(BaseSchema):
        created_at: datetime
    
    test_obj = TestModel(created_at=now)
    json_output = test_obj.model_dump_json()
    json_data = json.loads(json_output)
    
    print(f"\nPydantic serialization test:")
    print(f"  Input: {now}")
    print(f"  Output: {json_data['created_at']}")
    print(f"  Has Z suffix: {json_data['created_at'].endswith('Z')}")
    print(f"  Valid format: {validate_iso8601_format(json_data['created_at'])}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 3 DATETIME FORMAT VERIFICATION")
    print("=" * 60)
    
    # Test utilities
    await test_direct_datetime_utils()
    
    # Test API endpoints
    await test_api_datetime_formats()
    
    print("\n✅ Phase 3 testing complete!")


if __name__ == "__main__":
    asyncio.run(main())