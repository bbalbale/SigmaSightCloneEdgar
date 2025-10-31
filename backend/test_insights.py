"""
Test script for AI Insights functionality.

Tests:
1. Anthropic library import
2. AnthropicProvider initialization
3. AnalyticalReasoningService functionality
4. Insights endpoint availability
"""
import asyncio
import sys
from uuid import UUID

async def test_imports():
    """Test that all required imports work."""
    print("=" * 60)
    print("TEST 1: Testing imports...")
    print("=" * 60)

    try:
        import anthropic
        print(f"[PASS] anthropic library imported successfully (v{anthropic.__version__})")
    except ImportError as e:
        print(f"[FAIL] Failed to import anthropic: {e}")
        return False

    try:
        from app.services.anthropic_provider import anthropic_provider
        print("[PASS] anthropic_provider imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import anthropic_provider: {e}")
        return False

    try:
        from app.services.analytical_reasoning_service import analytical_reasoning_service
        print("[PASS] analytical_reasoning_service imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import analytical_reasoning_service: {e}")
        return False

    try:
        from app.api.v1.insights import router
        print("[PASS] insights router imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import insights router: {e}")
        return False

    print()
    return True


async def test_provider_initialization():
    """Test that AnthropicProvider initializes correctly."""
    print("=" * 60)
    print("TEST 2: Testing AnthropicProvider initialization...")
    print("=" * 60)

    try:
        from app.services.anthropic_provider import AnthropicProvider
        from app.config import settings

        if not settings.ANTHROPIC_API_KEY:
            print("[FAIL] ANTHROPIC_API_KEY not set in .env file")
            return False

        print(f"[PASS] ANTHROPIC_API_KEY is set (length: {len(settings.ANTHROPIC_API_KEY)})")

        provider = AnthropicProvider()
        print(f"[PASS] AnthropicProvider initialized successfully")
        print(f"  - Model: {provider.model}")
        print(f"  - Max tokens: {provider.max_tokens}")
        print(f"  - Temperature: {provider.temperature}")
        print()
        return True

    except Exception as e:
        print(f"[FAIL] Failed to initialize AnthropicProvider: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_context_builder():
    """Test that HybridContextBuilder works."""
    print("=" * 60)
    print("TEST 3: Testing HybridContextBuilder...")
    print("=" * 60)

    try:
        from app.services.hybrid_context_builder import hybrid_context_builder
        print("[PASS] hybrid_context_builder imported successfully")
        print()
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import hybrid_context_builder: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_database_tables():
    """Test that ai_insights table exists."""
    print("=" * 60)
    print("TEST 4: Testing database tables...")
    print("=" * 60)

    try:
        from sqlalchemy import text
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            # Check ai_insights table
            result = await db.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ai_insights')"
            ))
            exists = result.scalar()

            if exists:
                print("[PASS] ai_insights table exists")

                # Check table structure
                result = await db.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'ai_insights'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                print(f"  - Columns: {len(columns)}")
                for col_name, col_type in columns[:5]:  # Show first 5
                    print(f"    • {col_name} ({col_type})")
                if len(columns) > 5:
                    print(f"    ... and {len(columns) - 5} more columns")

                # Check record count
                result = await db.execute(text("SELECT COUNT(*) FROM ai_insights"))
                count = result.scalar()
                print(f"  - Records: {count}")
            else:
                print("[FAIL] ai_insights table does not exist")
                print("  → Run: uv run alembic upgrade head")
                return False

        print()
        return True

    except Exception as e:
        print(f"[FAIL] Database check failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_insight_models():
    """Test that insight models can be imported and used."""
    print("=" * 60)
    print("TEST 5: Testing AI Insight models...")
    print("=" * 60)

    try:
        from app.models.ai_insights import AIInsight, InsightType, InsightSeverity
        print("[PASS] AI Insight models imported successfully")

        # Show available insight types
        print(f"  - Insight types: {[t.value for t in InsightType]}")
        print(f"  - Severity levels: {[s.value for s in InsightSeverity]}")
        print()
        return True

    except Exception as e:
        print(f"[FAIL] Failed to import AI Insight models: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("=" * 60)
    print("  AI INSIGHTS DIAGNOSTIC TEST SUITE".center(60))
    print("=" * 60)
    print()

    results = []

    # Run tests
    results.append(("Imports", await test_imports()))
    results.append(("Provider Initialization", await test_provider_initialization()))
    results.append(("Context Builder", await test_context_builder()))
    results.append(("Database Tables", await test_database_tables()))
    results.append(("Insight Models", await test_insight_models()))

    # Summary
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[PASS]" if result else "[FAIL]"
        print(f"{symbol} {test_name}: {status}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print()
        print("[PASS] All tests passed! AI Insights system is ready.")
        print()
        print("Next steps:")
        print("1. Restart the backend server to load the anthropic library:")
        print("   cd backend && uv run python run.py")
        print()
        print("2. Test the insights endpoint via API:")
        print("   POST /api/v1/insights/generate")
        print()
        return 0
    else:
        print()
        print("[FAIL] Some tests failed. Please fix the issues above.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
