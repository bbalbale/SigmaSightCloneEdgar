#!/usr/bin/env python
"""Test that all models can be imported without circular dependency errors."""

def test_model_imports():
    """Test importing all models."""
    print("Testing model imports...")
    print("-" * 50)

    try:
        # Test importing from __init__.py
        print("1. Testing import from app.models...")
        from app.models import (
            User, Portfolio, Position, Tag, PositionType, TagType,
            Strategy, StrategyLeg, StrategyMetrics, StrategyTag, StrategyType,
            TagV2
        )
        print("   OK All models imported from app.models")

        # Test direct imports
        print("\n2. Testing direct model imports...")
        from app.models.users import User, Portfolio
        print("   OK User and Portfolio imported")

        from app.models.positions import Position, Tag, PositionType, TagType
        print("   OK Position models imported")

        from app.models.strategies import Strategy, StrategyLeg, StrategyMetrics, StrategyTag, StrategyType
        print("   OK Strategy models imported")

        from app.models.tags_v2 import TagV2
        print("   OK TagV2 imported")

        # Test creating instances (without database)
        print("\n3. Testing model instantiation...")

        # Create a strategy instance
        strategy = Strategy(
            name="Test Strategy",
            strategy_type=StrategyType.STANDALONE.value
        )
        print(f"   OK Strategy created: {strategy}")

        # Create a tag instance
        tag = TagV2(
            name="test-tag",
            color="#4A90E2"
        )
        print(f"   OK TagV2 created: {tag}")

        print("\n" + "=" * 50)
        print("SUCCESS: All models imported without errors!")
        print("=" * 50)

        return True

    except ImportError as e:
        print(f"\nERROR: Import Error: {e}")
        return False
    except Exception as e:
        print(f"\nERROR: Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_relationships():
    """Test that relationships are properly configured."""
    print("\nTesting model relationships...")
    print("-" * 50)

    try:
        from app.models import Strategy, Position, Portfolio, User, TagV2, StrategyTag

        # Check Strategy relationships
        print("1. Checking Strategy relationships...")
        assert hasattr(Strategy, 'portfolio'), "Strategy missing 'portfolio' relationship"
        assert hasattr(Strategy, 'positions'), "Strategy missing 'positions' relationship"
        assert hasattr(Strategy, 'strategy_legs'), "Strategy missing 'strategy_legs' relationship"
        assert hasattr(Strategy, 'tags'), "Strategy missing 'tags' relationship"
        assert hasattr(Strategy, 'metrics'), "Strategy missing 'metrics' relationship"
        print("   OK Strategy relationships configured")

        # Check Position relationships
        print("\n2. Checking Position relationships...")
        assert hasattr(Position, 'strategy'), "Position missing 'strategy' relationship"
        assert hasattr(Position, 'strategy_legs'), "Position missing 'strategy_legs' relationship"
        assert hasattr(Position, 'portfolio'), "Position missing 'portfolio' relationship"
        print("   OK Position relationships configured")

        # Check Portfolio relationships
        print("\n3. Checking Portfolio relationships...")
        assert hasattr(Portfolio, 'strategies'), "Portfolio missing 'strategies' relationship"
        assert hasattr(Portfolio, 'positions'), "Portfolio missing 'positions' relationship"
        assert hasattr(Portfolio, 'user'), "Portfolio missing 'user' relationship"
        print("   OK Portfolio relationships configured")

        # Check User relationships
        print("\n4. Checking User relationships...")
        assert hasattr(User, 'tags_v2'), "User missing 'tags_v2' relationship"
        assert hasattr(User, 'portfolio'), "User missing 'portfolio' relationship"
        print("   OK User relationships configured")

        # Check TagV2 relationships
        print("\n5. Checking TagV2 relationships...")
        assert hasattr(TagV2, 'user'), "TagV2 missing 'user' relationship"
        assert hasattr(TagV2, 'strategy_tags'), "TagV2 missing 'strategy_tags' relationship"
        print("   OK TagV2 relationships configured")

        print("\n" + "=" * 50)
        print("SUCCESS: All relationships properly configured!")
        print("=" * 50)

        return True

    except AssertionError as e:
        print(f"\nERROR: Relationship Error: {e}")
        return False
    except Exception as e:
        print(f"\nERROR: Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys

    # Test imports
    if not test_model_imports():
        sys.exit(1)

    # Test relationships
    if not test_relationships():
        sys.exit(1)

    print("\nSUCCESS: All tests passed successfully!")
    sys.exit(0)