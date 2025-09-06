#!/usr/bin/env python
"""Test get_factor_etf_prices tool handler directly"""
import asyncio
import json
from app.agent.tools.handlers import PortfolioTools
from app.agent.tools.tool_registry import ToolRegistry

async def test_tool_handler():
    """Test the tool handler directly"""
    print("Testing get_factor_etf_prices tool handler...")
    
    # Auth token from demo_hnw@sigmasight.com
    auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5ZGFjZmIwZi0yMTIzLTdhOTQtZGViYy0wZjk4MmI5MGQ4NDUiLCJlbWFpbCI6ImRlbW9faG53QHNpZ21hc2lnaHQuY29tIiwicG9ydGZvbGlvX2lkIjoiZTIzYWI5MzEtYTAzMy1lZGZlLWVkNGYtOWQwMjQ3NDc4MGI0IiwiZXhwIjoxNzU3MjIxOTIwfQ.v0l4wHti9_yzji8ek2SCEKkZY3j0eselcn6A2t3c4gY"
    
    # Test via handler directly
    print("\n1. Testing handler directly with auth:")
    tools = PortfolioTools(base_url="http://localhost:8000", auth_token=auth_token)
    result = await tools.get_factor_etf_prices(lookback_days=30)
    print(json.dumps(result, indent=2, default=str))
    
    # Test via registry (doesn't support auth_token in constructor)
    print("\n2. Testing via tool registry (will fail without auth):")
    registry = ToolRegistry()
    registry.portfolio_tools = PortfolioTools(base_url="http://localhost:8000", auth_token=auth_token)
    result2 = await registry.dispatch_tool_call(
        'get_factor_etf_prices',
        {'lookback_days': 30}
    )
    print(json.dumps(result2, indent=2, default=str))
    
    return result, result2

if __name__ == "__main__":
    result1, result2 = asyncio.run(test_tool_handler())
    
    # Check if we got actual data
    if "data" in result1:
        print(f"\n✅ Handler returned actual data with {len(result1['data'])} factor ETFs")
    else:
        print(f"\n❌ Handler did not return expected data structure")
        
    if "error" in result1:
        print(f"❌ Handler returned error: {result1['error']}")