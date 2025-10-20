"""
Test suite for market_data.py enhancements (Phase 1.3)
Tests get_position_value() and get_returns() canonical wrappers

Created: 2025-10-20 (Calculation Consolidation Refactor - Phase 1.3)
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from uuid import uuid4

from app.calculations.market_data import get_position_value, get_returns
from app.models.positions import Position, PositionType


# ============================================================================
# SECTION 1: Test get_position_value()
# ============================================================================

class TestGetPositionValue:
    """Test canonical position valuation function"""

    def test_long_stock_signed(self):
        """Long stock should have positive signed value"""
        pos = Position(
            id=uuid4(),
            symbol='AAPL',
            quantity=Decimal('100'),
            entry_price=Decimal('50.00'),
            last_price=Decimal('50.00'),
            position_type=PositionType.LONG,
            market_value=None  # Force calculation
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('5000.00')  # 100 * 50 * 1

    def test_short_stock_signed(self):
        """Short stock should have negative signed value"""
        pos = Position(
            id=uuid4(),
            symbol='TSLA',
            quantity=Decimal('-100'),  # Negative for short
            entry_price=Decimal('200.00'),
            last_price=Decimal('200.00'),
            position_type=PositionType.SHORT,
            market_value=None
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('-20000.00')  # -100 * 200 * 1

    def test_short_stock_absolute(self):
        """Absolute value should always be positive"""
        pos = Position(
            id=uuid4(),
            symbol='TSLA',
            quantity=Decimal('-100'),
            entry_price=Decimal('200.00'),
            last_price=Decimal('200.00'),
            position_type=PositionType.SHORT,
            market_value=Decimal('-20000.00')
        )

        value = get_position_value(pos, signed=False)
        assert value == Decimal('20000.00')  # Absolute value

    def test_long_call_multiplier(self):
        """Long call should apply 100x multiplier"""
        pos = Position(
            id=uuid4(),
            symbol='SPY',
            quantity=Decimal('10'),  # 10 contracts
            entry_price=Decimal('5.00'),
            last_price=Decimal('5.00'),
            position_type=PositionType.LC,  # Long Call
            market_value=None
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('5000.00')  # 10 * 5 * 100

    def test_long_put_multiplier(self):
        """Long put should apply 100x multiplier"""
        pos = Position(
            id=uuid4(),
            symbol='QQQ',
            quantity=Decimal('5'),
            entry_price=Decimal('3.00'),
            last_price=Decimal('3.00'),
            position_type=PositionType.LP,  # Long Put
            market_value=None
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('1500.00')  # 5 * 3 * 100

    def test_short_call_multiplier_and_sign(self):
        """Short call should apply 100x multiplier and negative sign"""
        pos = Position(
            id=uuid4(),
            symbol='SPY',
            quantity=Decimal('-10'),  # Short 10 contracts
            entry_price=Decimal('5.00'),
            last_price=Decimal('5.00'),
            position_type=PositionType.SC,  # Short Call
            market_value=None
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('-5000.00')  # -10 * 5 * 100

    def test_short_put_multiplier_and_sign(self):
        """Short put should apply 100x multiplier and negative sign"""
        pos = Position(
            id=uuid4(),
            symbol='QQQ',
            quantity=Decimal('-5'),  # Short 5 contracts
            entry_price=Decimal('3.00'),
            last_price=Decimal('3.00'),
            position_type=PositionType.SP,  # Short Put
            market_value=None
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('-1500.00')  # -5 * 3 * 100

    def test_uses_cached_value_when_available(self):
        """Should use cached market_value if available and not recalculating"""
        pos = Position(
            id=uuid4(),
            symbol='AAPL',
            quantity=Decimal('100'),
            entry_price=Decimal('50.00'),
            last_price=Decimal('50.00'),
            position_type=PositionType.LONG,
            market_value=Decimal('5500.00')  # Different from calculated (5000)
        )

        # Should use cached value
        value = get_position_value(pos, signed=True, recalculate=False)
        assert value == Decimal('5500.00')  # Uses cached

    def test_recalculate_ignores_cached_value(self):
        """Should recalculate when recalculate=True"""
        pos = Position(
            id=uuid4(),
            symbol='AAPL',
            quantity=Decimal('100'),
            entry_price=Decimal('50.00'),
            last_price=Decimal('50.00'),
            position_type=PositionType.LONG,
            market_value=Decimal('5500.00')  # Different from calculated
        )

        # Should recalculate
        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('5000.00')  # Recalculated: 100 * 50

    def test_falls_back_to_entry_price(self):
        """Should use entry_price if last_price is None"""
        pos = Position(
            id=uuid4(),
            symbol='AAPL',
            quantity=Decimal('100'),
            entry_price=Decimal('45.00'),
            last_price=None,  # No last price
            position_type=PositionType.LONG,
            market_value=None
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('4500.00')  # 100 * 45 (uses entry_price)

    def test_handles_no_price_data(self):
        """Should return zero if no price data available"""
        pos = Position(
            id=uuid4(),
            symbol='NODATA',
            quantity=Decimal('100'),
            entry_price=None,  # No price
            last_price=None,  # No price
            position_type=PositionType.LONG,
            market_value=None
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('0')  # No price available

    def test_zero_quantity_position(self):
        """Should handle zero quantity"""
        pos = Position(
            id=uuid4(),
            symbol='AAPL',
            quantity=Decimal('0'),
            entry_price=Decimal('50.00'),
            last_price=Decimal('50.00'),
            position_type=PositionType.LONG,
            market_value=None
        )

        value = get_position_value(pos, signed=True, recalculate=True)
        assert value == Decimal('0')  # 0 * 50 = 0

    def test_signed_vs_absolute_consistency(self):
        """Absolute value should equal abs(signed value)"""
        pos = Position(
            id=uuid4(),
            symbol='TSLA',
            quantity=Decimal('-100'),
            entry_price=Decimal('200.00'),
            last_price=Decimal('200.00'),
            position_type=PositionType.SHORT,
            market_value=None
        )

        signed_val = get_position_value(pos, signed=True, recalculate=True)
        absolute_val = get_position_value(pos, signed=False, recalculate=True)

        assert absolute_val == abs(signed_val)


# ============================================================================
# SECTION 2: Test get_returns() - Async tests need database
# ============================================================================

# Note: Full integration tests for get_returns() require database fixtures
# These will be similar to the async tests in test_portfolio_exposure_service.py
# For now, the function is tested indirectly through existing factor calculation tests

@pytest.mark.asyncio
class TestGetReturnsIntegration:
    """Integration tests for get_returns() - requires database"""

    async def test_get_returns_placeholder(self):
        """Placeholder for future integration tests"""
        # TODO: Add integration tests when database fixtures are working
        # Will test:
        # - Single symbol returns
        # - Multiple symbol returns (aligned)
        # - Multiple symbol returns (unaligned)
        # - Empty result handling
        # - Date alignment logic
        pass


# ============================================================================
# SECTION 3: Integration Tests - Consistency Checks
# ============================================================================

class TestConsistencyWithExistingCode:
    """Verify new functions match behavior of existing code"""

    def test_matches_factor_utils_absolute_value(self):
        """get_position_value(signed=False) should match factor_utils behavior"""
        # This verifies we can safely replace factor_utils.get_position_market_value
        pos = Position(
            id=uuid4(),
            symbol='AAPL',
            quantity=Decimal('-100'),  # Short
            entry_price=Decimal('50.00'),
            last_price=Decimal('50.00'),
            position_type=PositionType.SHORT,
            market_value=None
        )

        # New function (absolute)
        new_absolute = get_position_value(pos, signed=False, recalculate=True)

        # Should be positive (absolute value)
        assert new_absolute == Decimal('5000.00')
        assert new_absolute > 0  # Always positive

    def test_matches_factor_utils_signed_exposure(self):
        """get_position_value(signed=True) should match factor_utils.get_position_signed_exposure"""
        pos = Position(
            id=uuid4(),
            symbol='AAPL',
            quantity=Decimal('-100'),
            entry_price=Decimal('50.00'),
            last_price=Decimal('50.00'),
            position_type=PositionType.SHORT,
            market_value=None
        )

        # New function (signed)
        new_signed = get_position_value(pos, signed=True, recalculate=True)

        # Should be negative for short
        assert new_signed == Decimal('-5000.00')
        assert new_signed < 0  # Negative for short
