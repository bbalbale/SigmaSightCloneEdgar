"""
Test script for Phase 5 Enhanced Analytics Tools

Tests the 4 new tools added on December 3, 2025:
1. get_concentration_metrics
2. get_volatility_analysis
3. get_target_prices
4. get_position_tags

Usage:
    cd backend
    uv run python scripts/test_phase5_tools.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.tools.tool_registry import ToolRegistry
from app.agent.tools.handlers import PortfolioTools
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
import json


async def get_demo_portfolio_id():
    """Get a demo portfolio ID for testing"""
    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.name.ilike("%high net worth%"))
        )
        portfolio = result.scalar_one_or_none()
        if portfolio:
            return str(portfolio.id)

        # Fallback to any portfolio
        result = await db.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()
        if portfolio:
            return str(portfolio.id)

        raise ValueError("No portfolios found in database. Please seed demo data first.")


async def test_tool(tool_name: str, tool_registry: ToolRegistry, portfolio_id: str):
    """Test a single tool"""
    print(f"\n{'='*80}")
    print(f"Testing: {tool_name}")
    print(f"{'='*80}")

    try:
        # Call the tool
        result = await tool_registry.dispatch_tool_call(
            tool_name=tool_name,
            payload={"portfolio_id": portfolio_id},
            ctx={}
        )

        # Check for errors
        if "error" in result:
            print(f"[FAIL] {result['error']}")
            return False

        # Print summary
        print(f"[PASS] SUCCESS")

        # Print data summary
        if "data" in result:
            data = result["data"]
            if isinstance(data, dict):
                print(f"\nData fields: {list(data.keys())}")

                # Tool-specific summaries
                if tool_name == "get_concentration_metrics":
                    if "hhi" in data:
                        print(f"  - HHI: {data['hhi']:.4f}")
                    if "top_5_concentration" in data:
                        print(f"  - Top 5 concentration: {data['top_5_concentration']:.2%}")

                elif tool_name == "get_volatility_analysis":
                    if "realized_volatility" in data:
                        print(f"  - Realized volatility: {data['realized_volatility']:.4f}")
                    if "forecasted_volatility" in data:
                        print(f"  - Forecasted volatility: {data['forecasted_volatility']:.4f}")

                elif tool_name == "get_target_prices":
                    if "target_prices" in data:
                        target_prices = data["target_prices"]
                        print(f"  - Number of target prices: {len(target_prices)}")
                        if target_prices:
                            print(f"  - Example: {target_prices[0]}")

                elif tool_name == "get_position_tags":
                    if "tags" in data:
                        tags = data["tags"]
                        print(f"  - Number of tags: {len(tags)}")
                        if tags:
                            print(f"  - Tag names: {[tag.get('name') for tag in tags[:5]]}")

        # Print metadata
        if "meta" in result:
            meta = result["meta"]
            if "as_of" in meta:
                print(f"\nTimestamp: {meta['as_of']}")
            if "request_id" in meta:
                print(f"Request ID: {meta['request_id']}")

        return True

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("Phase 5 Enhanced Analytics Tools - Test Suite")
    print("="*80)

    # Get demo portfolio
    print("\nFetching demo portfolio...")
    try:
        portfolio_id = await get_demo_portfolio_id()
        print(f"[OK] Using portfolio ID: {portfolio_id}")
    except Exception as e:
        print(f"[FAIL] Failed to get demo portfolio: {e}")
        return

    # Initialize tool registry
    print("\nInitializing tool registry...")
    tools = PortfolioTools(base_url="http://localhost:8000")
    tool_registry = ToolRegistry(tools=tools)
    print(f"[OK] Registry initialized with {len(tool_registry.registry)} tools")

    # Test each Phase 5 tool
    tools_to_test = [
        "get_concentration_metrics",
        "get_volatility_analysis",
        "get_target_prices",
        "get_position_tags",
    ]

    results = {}
    for tool_name in tools_to_test:
        success = await test_tool(tool_name, tool_registry, portfolio_id)
        results[tool_name] = success

    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    for tool_name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} - {tool_name}")

    total = len(results)
    passed = sum(results.values())
    print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n[SUCCESS] All Phase 5 tools are working!")
    else:
        print("\n[WARNING] Some tools failed. Check logs above for details.")


if __name__ == "__main__":
    asyncio.run(main())
