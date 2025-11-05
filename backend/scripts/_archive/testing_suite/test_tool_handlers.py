#!/usr/bin/env python3
"""
Test script for Phase 3 tool handlers.
Tests the provider-agnostic tools and OpenAI adapter with real API.
"""
import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.tools.handlers import PortfolioTools
from app.agent.tools.tool_registry import ToolRegistry
from app.agent.adapters.openai_adapter import OpenAIToolAdapter


async def test_tool_registry():
    """Test the tool registry with dispatch and uniform envelope."""
    print("\n🔧 Testing Tool Registry with Uniform Envelope")
    print("=" * 60)
    
    # Get auth token (you should login first to get this)
    auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NTcwMGMyMS0wN2E3LTQ1N2MtYmQ3Zi1kNTBjZjIwMTRhMzgiLCJlbWFpbCI6ImRlbW9faW5kaXZpZHVhbEBzaWdtYXNpZ2h0LmNvbSIsImV4cCI6MTc1NjQ4NzQzMH0.mLm3kV1VqAdp1l7EkzlVIHUOvuTo6_i6kq0s4ccqCKg"
    portfolio_id = "51134ffd-2f13-49bd-b1f5-0c327e801b69"  # Demo portfolio
    
    # Initialize registry
    registry = ToolRegistry(auth_token=auth_token)
    
    # Test 1: Get portfolio complete
    print("\n1️⃣ Testing get_portfolio_complete with registry...")
    result = await registry.dispatch_tool_call(
        tool_name="get_portfolio_complete",
        payload={
            "portfolio_id": portfolio_id,
            "include_holdings": True,
            "include_timeseries": False,
            "include_attrib": False
        }
    )
    
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Success! Meta: {result['meta']['requested']}")
        print(f"   Truncated: {result['meta']['truncated']}")
        print(f"   Data keys: {list(result['data'].keys()) if result['data'] else 'None'}")
    
    # Test 2: Get top positions
    print("\n2️⃣ Testing positions/top endpoint via registry...")
    result = await registry.dispatch_tool_call(
        tool_name="get_prices_historical",
        payload={
            "portfolio_id": portfolio_id,
            "lookback_days": 30,
            "max_symbols": 3
        }
    )
    
    if result.get("error"):
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Success! Applied params: {result['meta']['applied']}")
        if result['data'] and 'meta' in result['data']:
            print(f"   Symbols selected: {result['data']['meta'].get('symbols_selected', [])}")
    
    # Test 3: Test error handling with invalid portfolio
    print("\n3️⃣ Testing error handling with invalid portfolio...")
    result = await registry.dispatch_tool_call(
        tool_name="get_portfolio_complete",
        payload={"portfolio_id": "invalid-uuid"}
    )
    
    if result.get("error"):
        print(f"✅ Error properly handled: {result['error']['message']}")
        print(f"   Retryable: {result['meta']['retryable']}")
    else:
        print("❌ Expected error but got success")
    
    # Test 4: Unknown tool
    print("\n4️⃣ Testing unknown tool handling...")
    result = await registry.dispatch_tool_call(
        tool_name="unknown_tool",
        payload={}
    )
    
    if result.get("error"):
        print(f"✅ Unknown tool handled: {result['error']['message']}")
        print(f"   Error type: {result['error']['type']}")


async def test_openai_adapter():
    """Test the OpenAI adapter."""
    print("\n🤖 Testing OpenAI Adapter")
    print("=" * 60)
    
    auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NTcwMGMyMS0wN2E3LTQ1N2MtYmQ3Zi1kNTBjZjIwMTRhMzgiLCJlbWFpbCI6ImRlbW9faW5kaXZpZHVhbEBzaWdtYXNpZ2h0LmNvbSIsImV4cCI6MTc1NjQ4NzQzMH0.mLm3kV1VqAdp1l7EkzlVIHUOvuTo6_i6kq0s4ccqCKg"
    portfolio_id = "51134ffd-2f13-49bd-b1f5-0c327e801b69"
    
    # Initialize tools and adapter
    tools = PortfolioTools(auth_token=auth_token)
    adapter = OpenAIToolAdapter(tools)
    
    # Get function schemas
    print("\n1️⃣ Getting OpenAI function schemas...")
    schemas = adapter.get_function_schemas()
    print(f"✅ Found {len(schemas)} tool schemas:")
    for schema in schemas:
        print(f"   - {schema['name']}: {schema['description'][:60]}...")
    
    # Test tool execution
    print("\n2️⃣ Testing tool execution through adapter...")
    result_json = await adapter.execute_tool(
        name="get_portfolio_data_quality",
        arguments={"portfolio_id": portfolio_id}
    )
    
    result = json.loads(result_json)
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Success! Got data quality assessment")
        if "data_quality_score" in result:
            print(f"   Quality score: {result['data_quality_score']}")
        if "_tool_recommendation" in result:
            print(f"   Recommendation: {result['_tool_recommendation']}")
    
    # Test parsing tool call
    print("\n3️⃣ Testing tool call parsing...")
    mock_tool_call = {
        "function": {
            "name": "get_current_quotes",
            "arguments": '{"symbols": "AAPL,GOOGL,MSFT"}'
        }
    }
    
    name, args = adapter.parse_tool_call(mock_tool_call)
    print(f"✅ Parsed tool call:")
    print(f"   Name: {name}")
    print(f"   Arguments: {args}")
    
    # Test formatting response
    print("\n4️⃣ Testing response formatting...")
    formatted = adapter.format_tool_response(
        tool_call_id="call_123",
        response=result_json
    )
    print(f"✅ Formatted response:")
    print(f"   Role: {formatted['role']}")
    print(f"   Tool call ID: {formatted['tool_call_id']}")
    print(f"   Content length: {len(formatted['content'])} chars")


async def test_direct_tools():
    """Test the PortfolioTools directly."""
    print("\n🔨 Testing Direct Tool Handlers")
    print("=" * 60)
    
    auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2NTcwMGMyMS0wN2E3LTQ1N2MtYmQ3Zi1kNTBjZjIwMTRhMzgiLCJlbWFpbCI6ImRlbW9faW5kaXZpZHVhbEBzaWdtYXNpZ2h0LmNvbSIsImV4cCI6MTc1NjQ4NzQzMH0.mLm3kV1VqAdp1l7EkzlVIHUOvuTo6_i6kq0s4ccqCKg"
    portfolio_id = "51134ffd-2f13-49bd-b1f5-0c327e801b69"
    
    tools = PortfolioTools(auth_token=auth_token)
    
    # Test get_current_quotes
    print("\n1️⃣ Testing get_current_quotes...")
    result = await tools.get_current_quotes(
        symbols="AAPL,GOOGL,MSFT,AMZN,META,NVDA"  # More than 5 to test truncation
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Success!")
        if "meta" in result:
            print(f"   Requested: {result['meta'].get('requested_symbols', 'N/A')}")
            print(f"   Applied: {result['meta'].get('applied_symbols', 'N/A')}")
            print(f"   Truncated: {result['meta'].get('truncated', False)}")
    
    # Test get_factor_etf_prices
    print("\n2️⃣ Testing get_factor_etf_prices...")
    result = await tools.get_factor_etf_prices(
        lookback_days=30,
        factors="Market,Size,Value"
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Success!")
        if "meta" in result:
            print(f"   Lookback days: {result['meta'].get('lookback_days', 'N/A')}")
            print(f"   Requested factors: {result['meta'].get('requested_factors', 'N/A')}")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("🚀 PHASE 3: TOOL HANDLERS TEST SUITE")
    print("=" * 60)
    
    try:
        # Test registry first (most important)
        await test_tool_registry()
        
        # Test OpenAI adapter
        await test_openai_adapter()
        
        # Test direct tools
        await test_direct_tools()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())