"""
Test script for Anthropic tool execution in Claude Insights.

Tests the agentic loop with Phase 1 analytics tools.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.anthropic_provider import anthropic_provider
from app.models.ai_insights import InsightType
from app.database import get_async_session
from app.models.users import Portfolio
from sqlalchemy import select
from app.core.logging import get_logger
import httpx

logger = get_logger(__name__)


async def get_auth_token():
    """Get auth token by logging in as demo user."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={
                "email": "demo_hnw@sigmasight.com",
                "password": "demo12345"
            }
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def test_tool_execution():
    """
    Test Claude Insights with tool access.

    Steps:
    1. Get demo portfolio ID
    2. Build simple context (just portfolio ID)
    3. Call investigate() with tools enabled
    4. Verify tool calls were made and executed
    5. Verify final response is properly formatted
    """
    print("\n" + "="*80)
    print("Testing Anthropic Tool Execution (Phase 1)")
    print("="*80 + "\n")

    # Step 1: Get demo portfolio
    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.name.like("%High Net Worth%"))
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("[ERROR] No demo portfolio found - run seed script first")
            return

        print(f"[OK] Found demo portfolio: {portfolio.name}")
        print(f"   Portfolio ID: {portfolio.id}\n")

    # Step 2: Build minimal context for testing
    context = {
        "portfolio_id": str(portfolio.id),
        "data_sources": {
            "portfolio_complete": "available",
            "positions": "available",
            "risk_metrics": "available",
        },
        "portfolio_summary": {
            "available": True,
            "name": portfolio.name,
            "currency": "USD",
        }
    }

    # Step 3: Get authentication token for tool calls
    print("Getting authentication token for tool calls...")
    auth_token = await get_auth_token()
    print(f"[OK] Got auth token\n")

    # Step 4: Call investigate with FACTOR_EXPOSURE analysis
    # This type should trigger Claude to use get_factor_exposures tool
    print("Calling Claude Insights with FACTOR_EXPOSURE analysis type...")
    print("Claude should use get_factor_exposures and possibly other tools.\n")

    try:
        result = await anthropic_provider.investigate(
            context=context,
            insight_type=InsightType.FACTOR_EXPOSURE,
            focus_area="Factor exposures and systematic risks",
            auth_token=auth_token
        )

        # Step 4: Verify tool calls were made
        performance = result.get("performance", {})
        tool_calls_count = performance.get("tool_calls_count", 0)

        print("\n" + "="*80)
        print("RESULTS")
        print("="*80 + "\n")

        print(f"[OK] Investigation completed successfully!")
        print(f"\nPerformance Metrics:")
        print(f"   - Tool calls made: {tool_calls_count}")
        print(f"   - Input tokens: {performance.get('token_count_input', 0):,}")
        print(f"   - Output tokens: {performance.get('token_count_output', 0):,}")
        print(f"   - Generation time: {performance.get('generation_time_ms', 0):.0f}ms")
        print(f"   - Cost: ${performance.get('cost_usd', 0):.4f}")

        if tool_calls_count > 0:
            print(f"\n[SUCCESS] Claude made {tool_calls_count} tool calls!")
        else:
            print(f"\n[WARNING] Claude did not use any tools (expected at least 1)")

        # Step 5: Verify response structure
        print(f"\nResponse Structure:")
        print(f"   - Title: {result.get('title', 'N/A')}")
        print(f"   - Severity: {result.get('severity', 'N/A')}")
        print(f"   - Key findings: {len(result.get('key_findings', []))} items")
        print(f"   - Recommendations: {len(result.get('recommendations', []))} items")

        # Show first key finding
        key_findings = result.get('key_findings', [])
        if key_findings:
            print(f"\nFirst Key Finding:")
            print(f"   {key_findings[0][:150]}...")

        # Show summary (truncated)
        summary = result.get('summary', '')
        if summary:
            print(f"\nSummary (truncated):")
            print(f"   {summary[:200]}...")

        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80 + "\n")

        # Save full response to file for inspection
        import json
        output_file = Path(__file__).parent / "test_anthropic_tools_output.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"[SAVE] Full response saved to: {output_file}\n")

        return result

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise


async def test_tool_registry_directly():
    """
    Test tool registry directly without Claude.

    Verifies that each tool can be called and returns data.
    """
    print("\n" + "="*80)
    print("Testing Tool Registry Directly (No Claude)")
    print("="*80 + "\n")

    from app.agent.tools.tool_registry import ToolRegistry

    # Get demo portfolio
    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.name.like("%High Net Worth%"))
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("[ERROR] No demo portfolio found")
            return

    portfolio_id = str(portfolio.id)
    print(f"Testing with portfolio: {portfolio.name}")
    print(f"Portfolio ID: {portfolio_id}\n")

    # Get authentication token
    print("Getting authentication token...")
    auth_token = await get_auth_token()
    print(f"[OK] Got auth token: {auth_token[:20]}...\n")

    # Initialize tool registry with authentication
    registry = ToolRegistry(auth_token=auth_token)

    # Test each Phase 1 tool
    tools_to_test = [
        ("get_analytics_overview", {"portfolio_id": portfolio_id}),
        ("get_factor_exposures", {"portfolio_id": portfolio_id}),
        ("get_sector_exposure", {"portfolio_id": portfolio_id}),
        ("get_correlation_matrix", {"portfolio_id": portfolio_id}),
        ("get_stress_test_results", {"portfolio_id": portfolio_id}),
        ("get_company_profile", {"symbol": "AAPL"}),
    ]

    results = {}
    for tool_name, payload in tools_to_test:
        print(f"Testing {tool_name}...")
        try:
            result = await registry.dispatch_tool_call(
                tool_name=tool_name,
                payload=payload,
                ctx={"portfolio_id": portfolio_id, "auth_token": auth_token}
            )

            # Check if successful
            if result.get("error"):
                print(f"   [ERROR] {result['error']['message']}")
                results[tool_name] = "error"
            elif result.get("data"):
                print(f"   [OK] Success: Got data")
                results[tool_name] = "success"
            else:
                print(f"   [WARN] No data or error")
                results[tool_name] = "empty"

        except Exception as e:
            print(f"   [ERROR] Exception: {e}")
            results[tool_name] = "exception"

    # Summary
    print("\n" + "="*80)
    print("TOOL REGISTRY TEST SUMMARY")
    print("="*80 + "\n")

    success_count = sum(1 for v in results.values() if v == "success")
    total_count = len(results)

    print(f"Successful: {success_count}/{total_count}")
    print(f"\nResults:")
    for tool_name, status in results.items():
        status_marker = "[OK]" if status == "success" else "[FAIL]"
        print(f"   {status_marker} {tool_name}: {status}")

    print("\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Anthropic tool execution")
    parser.add_argument(
        "--mode",
        choices=["claude", "registry", "both"],
        default="both",
        help="Test mode: claude (with AI), registry (direct), or both"
    )

    args = parser.parse_args()

    if args.mode in ["registry", "both"]:
        print("\n[TOOL REGISTRY TEST] Testing Tool Registry Directly...")
        asyncio.run(test_tool_registry_directly())

    if args.mode in ["claude", "both"]:
        print("\n[CLAUDE TEST] Testing Claude with Tool Access...")
        asyncio.run(test_tool_execution())
