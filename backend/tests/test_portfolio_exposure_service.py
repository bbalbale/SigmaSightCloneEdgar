"""
Test suite for portfolio_exposure_service.py
Tests snapshot caching, fallback logic, and exposure calculations

Created: 2025-10-20 (Calculation Consolidation Refactor - Phase 1.2)
Follows: TDD approach - tests written before implementation
"""
import pytest
import pytest_asyncio
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.portfolio_exposure_service import (
    get_portfolio_exposures,
    prepare_positions_for_aggregation
)
from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position, PositionType
from app.models.users import User, Portfolio


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user"""
    user = User(
        id=uuid4(),
        email="test_exposure@test.com",
        full_name="Test User",
        hashed_password="fake_hash"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_portfolio(db_session, test_user):
    """Create a test portfolio"""
    portfolio = Portfolio(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Exposure Portfolio",
        equity_balance=Decimal('1000000.00')
    )
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)
    return portfolio


@pytest_asyncio.fixture
async def sample_positions(db_session, test_portfolio):
    """Create sample positions for testing"""
    positions = [
        # Long stock
        Position(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            symbol='AAPL',
            quantity=Decimal('100'),
            position_type=PositionType.LONG,
            entry_price=Decimal('150.00'),
            last_price=Decimal('150.00'),
            market_value=Decimal('15000.00')
        ),
        # Another long stock
        Position(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            symbol='GOOGL',
            quantity=Decimal('50'),
            position_type=PositionType.LONG,
            entry_price=Decimal('140.00'),
            last_price=Decimal('140.00'),
            market_value=Decimal('7000.00')
        ),
        # Short stock
        Position(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            symbol='TSLA',
            quantity=Decimal('-100'),
            position_type=PositionType.SHORT,
            entry_price=Decimal('200.00'),
            last_price=Decimal('200.00'),
            market_value=Decimal('-20000.00')
        ),
    ]

    for pos in positions:
        db_session.add(pos)
    await db_session.commit()

    return positions


# ============================================================================
# SECTION 1: Test get_portfolio_exposures() - Snapshot Caching
# ============================================================================

@pytest.mark.asyncio
class TestSnapshotCaching:
    """Test snapshot cache hit/miss logic"""

    async def test_uses_recent_snapshot(self, db_session, test_portfolio):
        """Should use snapshot if within staleness limit"""
        # Create a recent snapshot (today)
        snapshot = PortfolioSnapshot(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            snapshot_date=date.today(),
            net_exposure=Decimal('2500000.00'),
            gross_exposure=Decimal('6500000.00'),
            long_exposure=Decimal('4500000.00'),
            short_exposure=Decimal('2000000.00'),
            position_count=30,
            total_value=Decimal('3000000.00')
        )
        db_session.add(snapshot)
        await db_session.commit()

        # Call service
        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Assertions
        assert result['source'] == 'snapshot'
        assert result['net_exposure'] == 2500000.00
        assert result['gross_exposure'] == 6500000.00
        assert result['long_exposure'] == 4500000.00
        assert result['short_exposure'] == 2000000.00
        assert result['position_count'] == 30
        assert result['snapshot_date'] == date.today()

    async def test_ignores_stale_snapshot(self, db_session, test_portfolio, sample_positions):
        """Should recalculate if snapshot too old"""
        # Create a stale snapshot (5 days old)
        old_date = date.today() - timedelta(days=5)
        snapshot = PortfolioSnapshot(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            snapshot_date=old_date,
            net_exposure=Decimal('2500000.00'),
            gross_exposure=Decimal('6500000.00'),
            long_exposure=Decimal('4500000.00'),
            short_exposure=Decimal('2000000.00'),
            position_count=30,
            total_value=Decimal('3000000.00')
        )
        db_session.add(snapshot)
        await db_session.commit()

        # Call service with max_staleness_days=3
        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today(),
            max_staleness_days=3
        )

        # Should calculate real-time (not use stale snapshot)
        assert result['source'] == 'real_time'
        assert result['snapshot_date'] is None
        # Should have calculated from sample_positions
        assert result['net_exposure'] != 2500000.00  # Different from stale snapshot

    async def test_calculates_when_no_snapshot(self, db_session, test_portfolio, sample_positions):
        """Should calculate real-time when no snapshot exists"""
        # No snapshot created

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        assert result['source'] == 'real_time'
        assert result['snapshot_date'] is None
        assert 'net_exposure' in result
        assert 'gross_exposure' in result
        assert result['position_count'] == 3  # From sample_positions

    async def test_staleness_boundary(self, db_session, test_portfolio):
        """Test exact staleness threshold boundary"""
        # Create snapshot exactly at threshold (3 days old)
        boundary_date = date.today() - timedelta(days=3)
        snapshot = PortfolioSnapshot(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            snapshot_date=boundary_date,
            net_exposure=Decimal('1000000.00'),
            gross_exposure=Decimal('2000000.00'),
            long_exposure=Decimal('1500000.00'),
            short_exposure=Decimal('500000.00'),
            position_count=10,
            total_value=Decimal('1200000.00')
        )
        db_session.add(snapshot)
        await db_session.commit()

        # Should still use it (at boundary)
        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today(),
            max_staleness_days=3
        )

        assert result['source'] == 'snapshot'

    async def test_uses_most_recent_snapshot(self, db_session, test_portfolio):
        """Should use the most recent snapshot when multiple exist"""
        # Create multiple snapshots
        old_snapshot = PortfolioSnapshot(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            snapshot_date=date.today() - timedelta(days=2),
            net_exposure=Decimal('1000000.00'),
            gross_exposure=Decimal('2000000.00'),
            long_exposure=Decimal('1500000.00'),
            short_exposure=Decimal('500000.00'),
            position_count=10,
            total_value=Decimal('1200000.00')
        )

        recent_snapshot = PortfolioSnapshot(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            snapshot_date=date.today() - timedelta(days=1),
            net_exposure=Decimal('1500000.00'),  # Different
            gross_exposure=Decimal('2500000.00'),
            long_exposure=Decimal('2000000.00'),
            short_exposure=Decimal('500000.00'),
            position_count=12,
            total_value=Decimal('1800000.00')
        )

        db_session.add(old_snapshot)
        db_session.add(recent_snapshot)
        await db_session.commit()

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Should use the recent snapshot
        assert result['net_exposure'] == 1500000.00  # From recent_snapshot
        assert result['snapshot_date'] == date.today() - timedelta(days=1)


# ============================================================================
# SECTION 2: Test Exposure Calculations
# ============================================================================

@pytest.mark.asyncio
class TestExposureCalculations:
    """Test signed exposure calculations"""

    async def test_signed_exposure_with_longs_and_shorts(self, db_session, test_portfolio, sample_positions):
        """Should calculate signed exposures correctly with mixed positions"""
        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # sample_positions has:
        # AAPL: +15000, GOOGL: +7000, TSLA: -20000
        # Net = 15000 + 7000 - 20000 = 2000
        # Gross = |15000| + |7000| + |-20000| = 42000
        # Long = 15000 + 7000 = 22000
        # Short = |-20000| = 20000

        assert result['net_exposure'] == pytest.approx(2000.00, abs=1)
        assert result['gross_exposure'] == pytest.approx(42000.00, abs=1)
        assert result['long_exposure'] == pytest.approx(22000.00, abs=1)
        assert result['short_exposure'] == pytest.approx(20000.00, abs=1)

    async def test_all_long_positions(self, db_session, test_portfolio):
        """Should calculate correctly with all long positions"""
        positions = [
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='AAPL',
                quantity=Decimal('100'),
                position_type=PositionType.LONG,
                entry_price=Decimal('150.00'),
                last_price=Decimal('150.00'),
                market_value=Decimal('15000.00')
            ),
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='MSFT',
                quantity=Decimal('50'),
                position_type=PositionType.LONG,
                entry_price=Decimal('300.00'),
                last_price=Decimal('300.00'),
                market_value=Decimal('15000.00')
            ),
        ]

        for pos in positions:
            db_session.add(pos)
        await db_session.commit()

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Net = Gross = Long (all positive)
        # Short = 0
        assert result['net_exposure'] == pytest.approx(30000.00, abs=1)
        assert result['gross_exposure'] == pytest.approx(30000.00, abs=1)
        assert result['long_exposure'] == pytest.approx(30000.00, abs=1)
        assert result['short_exposure'] == pytest.approx(0.00, abs=1)

    async def test_all_short_positions(self, db_session, test_portfolio):
        """Should calculate correctly with all short positions"""
        positions = [
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='TSLA',
                quantity=Decimal('-100'),
                position_type=PositionType.SHORT,
                entry_price=Decimal('200.00'),
                last_price=Decimal('200.00'),
                market_value=Decimal('-20000.00')
            ),
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='NVDA',
                quantity=Decimal('-50'),
                position_type=PositionType.SHORT,
                entry_price=Decimal('400.00'),
                last_price=Decimal('400.00'),
                market_value=Decimal('-20000.00')
            ),
        ]

        for pos in positions:
            db_session.add(pos)
        await db_session.commit()

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Net = -40000 (all negative)
        # Gross = 40000 (absolute)
        # Long = 0
        # Short = 40000
        assert result['net_exposure'] == pytest.approx(-40000.00, abs=1)
        assert result['gross_exposure'] == pytest.approx(40000.00, abs=1)
        assert result['long_exposure'] == pytest.approx(0.00, abs=1)
        assert result['short_exposure'] == pytest.approx(40000.00, abs=1)

    async def test_options_multiplier_long_call(self, db_session, test_portfolio):
        """Should apply 100x multiplier for long call options"""
        position = Position(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            symbol='SPY',
            quantity=Decimal('10'),  # 10 contracts
            position_type=PositionType.LC,  # Long Call
            entry_price=Decimal('5.00'),
            last_price=Decimal('5.00'),
            market_value=Decimal('5000.00')  # 10 × 5 × 100
        )
        db_session.add(position)
        await db_session.commit()

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Should be 10 contracts × $5 × 100 multiplier = $5000
        assert result['gross_exposure'] == pytest.approx(5000.00, abs=1)
        assert result['net_exposure'] == pytest.approx(5000.00, abs=1)

    async def test_options_multiplier_short_put(self, db_session, test_portfolio):
        """Should apply 100x multiplier and negative sign for short put"""
        position = Position(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            symbol='QQQ',
            quantity=Decimal('-5'),  # Short 5 contracts
            position_type=PositionType.SP,  # Short Put
            entry_price=Decimal('3.00'),
            last_price=Decimal('3.00'),
            market_value=Decimal('-1500.00')  # -5 × 3 × 100
        )
        db_session.add(position)
        await db_session.commit()

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Should be -5 contracts × $3 × 100 = -$1500
        assert result['net_exposure'] == pytest.approx(-1500.00, abs=1)
        assert result['gross_exposure'] == pytest.approx(1500.00, abs=1)
        assert result['short_exposure'] == pytest.approx(1500.00, abs=1)


# ============================================================================
# SECTION 3: Test Edge Cases
# ============================================================================

@pytest.mark.asyncio
class TestEdgeCases:
    """Test edge cases and error handling"""

    async def test_empty_portfolio_no_positions(self, db_session, test_portfolio):
        """Should handle portfolio with no positions"""
        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        assert result['source'] == 'real_time'
        assert result['net_exposure'] == 0.0
        assert result['gross_exposure'] == 0.0
        assert result['long_exposure'] == 0.0
        assert result['short_exposure'] == 0.0
        assert result['position_count'] == 0

    async def test_all_exited_positions(self, db_session, test_portfolio):
        """Should ignore exited positions"""
        positions = [
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='AAPL',
                quantity=Decimal('100'),
                position_type=PositionType.LONG,
                entry_price=Decimal('150.00'),
                last_price=Decimal('150.00'),
                market_value=Decimal('15000.00'),
                exit_date=date.today() - timedelta(days=10)  # Exited
            ),
        ]

        for pos in positions:
            db_session.add(pos)
        await db_session.commit()

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Should return zero exposures (all positions exited)
        assert result['net_exposure'] == 0.0
        assert result['position_count'] == 0

    async def test_position_with_no_price_data(self, db_session, test_portfolio):
        """Should skip positions without price data"""
        positions = [
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='AAPL',
                quantity=Decimal('100'),
                position_type=PositionType.LONG,
                entry_price=Decimal('150.00'),
                last_price=Decimal('150.00'),
                market_value=Decimal('15000.00')
            ),
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='NODATA',
                quantity=Decimal('50'),
                position_type=PositionType.LONG,
                entry_price=None,  # No price
                last_price=None,  # No price
                market_value=None  # No market value
            ),
        ]

        for pos in positions:
            db_session.add(pos)
        await db_session.commit()

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Should only count AAPL (skip NODATA)
        assert result['position_count'] == 1
        assert result['gross_exposure'] == pytest.approx(15000.00, abs=1)

    async def test_zero_quantity_position(self, db_session, test_portfolio):
        """Should handle positions with zero quantity"""
        position = Position(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            symbol='AAPL',
            quantity=Decimal('0'),  # Zero quantity
            position_type=PositionType.LONG,
            entry_price=Decimal('150.00'),
            last_price=Decimal('150.00'),
            market_value=Decimal('0.00')
        )
        db_session.add(position)
        await db_session.commit()

        result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        assert result['net_exposure'] == 0.0
        assert result['gross_exposure'] == 0.0

    async def test_nonexistent_portfolio(self, db_session):
        """Should handle nonexistent portfolio gracefully"""
        fake_id = uuid4()

        result = await get_portfolio_exposures(
            db_session,
            fake_id,
            date.today()
        )

        # Should return zero exposures for nonexistent portfolio
        assert result['net_exposure'] == 0.0
        assert result['gross_exposure'] == 0.0
        assert result['position_count'] == 0


# ============================================================================
# SECTION 4: Test prepare_positions_for_aggregation()
# ============================================================================

@pytest.mark.asyncio
class TestPreparePositionsForAggregation:
    """Test position data preparation helper"""

    async def test_prepares_position_data_structure(self, db_session, sample_positions):
        """Should prepare correct data structure for aggregation"""
        result = await prepare_positions_for_aggregation(db_session, sample_positions)

        # Should return list of dicts
        assert isinstance(result, list)
        assert len(result) == 3  # All 3 positions

        # Check structure of first item
        first_item = result[0]
        assert 'exposure' in first_item
        assert 'market_value' in first_item
        assert 'position_type' in first_item

        # Exposure should be Decimal
        assert isinstance(first_item['exposure'], Decimal)
        assert isinstance(first_item['market_value'], Decimal)

    async def test_handles_positions_without_price(self, db_session, test_portfolio):
        """Should skip positions without price data"""
        positions = [
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='AAPL',
                quantity=Decimal('100'),
                position_type=PositionType.LONG,
                last_price=Decimal('150.00'),
                market_value=Decimal('15000.00')
            ),
            Position(
                id=uuid4(),
                portfolio_id=test_portfolio.id,
                symbol='NODATA',
                quantity=Decimal('50'),
                position_type=PositionType.LONG,
                last_price=None,  # No price
                market_value=None
            ),
        ]

        result = await prepare_positions_for_aggregation(db_session, positions)

        # Should only include AAPL (skip NODATA)
        assert len(result) == 1

    async def test_empty_position_list(self, db_session):
        """Should handle empty position list"""
        result = await prepare_positions_for_aggregation(db_session, [])

        assert result == []


# ============================================================================
# SECTION 5: Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestIntegration:
    """Integration tests comparing snapshot vs real-time"""

    async def test_snapshot_and_realtime_match(self, db_session, test_portfolio, sample_positions):
        """Snapshot and real-time calculations should match"""
        # First, calculate real-time
        realtime_result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Create snapshot with same values
        snapshot = PortfolioSnapshot(
            id=uuid4(),
            portfolio_id=test_portfolio.id,
            snapshot_date=date.today(),
            net_exposure=Decimal(str(realtime_result['net_exposure'])),
            gross_exposure=Decimal(str(realtime_result['gross_exposure'])),
            long_exposure=Decimal(str(realtime_result['long_exposure'])),
            short_exposure=Decimal(str(realtime_result['short_exposure'])),
            position_count=realtime_result['position_count'],
            total_value=Decimal('100000.00')
        )
        db_session.add(snapshot)
        await db_session.commit()

        # Now retrieve using snapshot
        snapshot_result = await get_portfolio_exposures(
            db_session,
            test_portfolio.id,
            date.today()
        )

        # Results should match
        assert snapshot_result['source'] == 'snapshot'
        assert snapshot_result['net_exposure'] == pytest.approx(realtime_result['net_exposure'], abs=1)
        assert snapshot_result['gross_exposure'] == pytest.approx(realtime_result['gross_exposure'], abs=1)
