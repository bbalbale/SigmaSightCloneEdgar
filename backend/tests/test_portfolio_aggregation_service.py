"""
Unit tests for PortfolioAggregationService

Tests the portfolio-as-asset weighted average aggregation logic.
"""
import pytest
from decimal import Decimal
from uuid import uuid4, UUID
from datetime import datetime, timezone

from app.services.portfolio_aggregation_service import PortfolioAggregationService
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import PositionFactorExposure


@pytest.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test_aggregation@example.com",
        hashed_password="hashed",
        full_name="Test User",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
async def test_portfolios(db_session, test_user):
    """Create multiple test portfolios with different values."""
    portfolio_a = Portfolio(
        id=uuid4(),
        user_id=test_user.id,
        name="Portfolio A",
        account_name="Schwab Taxable",
        account_type="taxable",
        is_active=True,
        equity_balance=Decimal('500000')  # $500k
    )

    portfolio_b = Portfolio(
        id=uuid4(),
        user_id=test_user.id,
        name="Portfolio B",
        account_name="Fidelity IRA",
        account_type="ira",
        is_active=True,
        equity_balance=Decimal('300000')  # $300k
    )

    portfolio_c = Portfolio(
        id=uuid4(),
        user_id=test_user.id,
        name="Portfolio C",
        account_name="Vanguard 401k",
        account_type="401k",
        is_active=True,
        equity_balance=Decimal('200000')  # $200k
    )

    db_session.add_all([portfolio_a, portfolio_b, portfolio_c])
    await db_session.commit()

    return {
        'a': portfolio_a,
        'b': portfolio_b,
        'c': portfolio_c
    }


@pytest.fixture
async def portfolio_snapshots(db_session, test_portfolios):
    """Create portfolio snapshots with market values."""
    snapshot_a = PortfolioSnapshot(
        id=uuid4(),
        portfolio_id=test_portfolios['a'].id,
        snapshot_date=datetime.now(timezone.utc).date(),
        total_value=Decimal('520000'),  # Grown to $520k
        equity_balance=Decimal('500000')
    )

    snapshot_b = PortfolioSnapshot(
        id=uuid4(),
        portfolio_id=test_portfolios['b'].id,
        snapshot_date=datetime.now(timezone.utc).date(),
        total_value=Decimal('310000'),  # Grown to $310k
        equity_balance=Decimal('300000')
    )

    snapshot_c = PortfolioSnapshot(
        id=uuid4(),
        portfolio_id=test_portfolios['c'].id,
        snapshot_date=datetime.now(timezone.utc).date(),
        total_value=Decimal('190000'),  # Down to $190k
        equity_balance=Decimal('200000')
    )

    db_session.add_all([snapshot_a, snapshot_b, snapshot_c])
    await db_session.commit()

    return {
        'a': snapshot_a,
        'b': snapshot_b,
        'c': snapshot_c
    }


class TestPortfolioAggregationService:
    """Test suite for PortfolioAggregationService."""

    async def test_get_user_portfolios(self, db_session, test_user, test_portfolios):
        """Test retrieving user's portfolios."""
        service = PortfolioAggregationService(db_session)

        portfolios = await service.get_user_portfolios(test_user.id)

        assert len(portfolios) == 3
        assert all(p.user_id == test_user.id for p in portfolios)
        assert all(p.is_active for p in portfolios)

    async def test_get_user_portfolios_include_inactive(self, db_session, test_user, test_portfolios):
        """Test retrieving portfolios including inactive ones."""
        # Mark one portfolio inactive
        test_portfolios['c'].is_active = False
        await db_session.commit()

        service = PortfolioAggregationService(db_session)

        # Without inactive
        active_portfolios = await service.get_user_portfolios(test_user.id, include_inactive=False)
        assert len(active_portfolios) == 2

        # With inactive
        all_portfolios = await service.get_user_portfolios(test_user.id, include_inactive=True)
        assert len(all_portfolios) == 3

    async def test_get_portfolio_values_with_snapshots(
        self,
        db_session,
        test_portfolios,
        portfolio_snapshots
    ):
        """Test getting portfolio values when snapshots exist."""
        service = PortfolioAggregationService(db_session)

        portfolio_ids = [p.id for p in test_portfolios.values()]
        values = await service.get_portfolio_values(portfolio_ids)

        # Should use snapshot values, not equity_balance
        assert values[test_portfolios['a'].id] == Decimal('520000')
        assert values[test_portfolios['b'].id] == Decimal('310000')
        assert values[test_portfolios['c'].id] == Decimal('190000')

    async def test_get_portfolio_values_fallback_to_equity_balance(
        self,
        db_session,
        test_portfolios
    ):
        """Test getting portfolio values when no snapshots exist."""
        service = PortfolioAggregationService(db_session)

        portfolio_ids = [p.id for p in test_portfolios.values()]
        values = await service.get_portfolio_values(portfolio_ids)

        # Should use equity_balance as fallback
        assert values[test_portfolios['a'].id] == Decimal('500000')
        assert values[test_portfolios['b'].id] == Decimal('300000')
        assert values[test_portfolios['c'].id] == Decimal('200000')

    async def test_calculate_weights(self, db_session):
        """Test weight calculation based on portfolio values."""
        service = PortfolioAggregationService(db_session)

        portfolio_values = {
            uuid4(): Decimal('500000'),  # 50%
            uuid4(): Decimal('300000'),  # 30%
            uuid4(): Decimal('200000'),  # 20%
        }

        weights = service.calculate_weights(portfolio_values)

        assert len(weights) == 3
        assert abs(sum(weights.values()) - 1.0) < 0.0001  # Should sum to 1.0

        # Check individual weights
        values_list = list(portfolio_values.values())
        weights_list = list(weights.values())

        assert abs(weights_list[0] - 0.50) < 0.0001
        assert abs(weights_list[1] - 0.30) < 0.0001
        assert abs(weights_list[2] - 0.20) < 0.0001

    async def test_calculate_weights_zero_total(self, db_session):
        """Test weight calculation when total value is zero."""
        service = PortfolioAggregationService(db_session)

        portfolio_values = {
            uuid4(): Decimal('0'),
            uuid4(): Decimal('0'),
            uuid4(): Decimal('0'),
        }

        weights = service.calculate_weights(portfolio_values)

        # Should return equal weights
        assert len(weights) == 3
        assert all(abs(w - 0.333333) < 0.001 for w in weights.values())

    async def test_aggregate_portfolio_metrics(
        self,
        db_session,
        test_user,
        test_portfolios,
        portfolio_snapshots
    ):
        """Test aggregating portfolio-level metrics."""
        service = PortfolioAggregationService(db_session)

        result = await service.aggregate_portfolio_metrics(test_user.id)

        # Check structure
        assert 'total_value' in result
        assert 'portfolio_count' in result
        assert 'portfolios' in result
        assert 'aggregate_metrics' in result

        # Check values
        assert result['portfolio_count'] == 3
        assert result['total_value'] == 1020000  # 520k + 310k + 190k

        # Check portfolio summaries
        portfolios = result['portfolios']
        assert len(portfolios) == 3

        # Check each portfolio has required fields
        for portfolio in portfolios:
            assert 'id' in portfolio
            assert 'account_name' in portfolio
            assert 'account_type' in portfolio
            assert 'value' in portfolio
            assert 'weight' in portfolio

        # Check weights sum to 1.0
        total_weight = sum(p['weight'] for p in portfolios)
        assert abs(total_weight - 1.0) < 0.0001

    async def test_aggregate_portfolio_metrics_specific_portfolios(
        self,
        db_session,
        test_user,
        test_portfolios,
        portfolio_snapshots
    ):
        """Test aggregating only specific portfolios."""
        service = PortfolioAggregationService(db_session)

        # Only aggregate portfolios A and B
        portfolio_ids = [test_portfolios['a'].id, test_portfolios['b'].id]
        result = await service.aggregate_portfolio_metrics(
            test_user.id,
            portfolio_ids=portfolio_ids
        )

        assert result['portfolio_count'] == 2
        assert result['total_value'] == 830000  # 520k + 310k

    async def test_aggregate_portfolio_metrics_no_portfolios(
        self,
        db_session
    ):
        """Test aggregating when user has no portfolios."""
        service = PortfolioAggregationService(db_session)

        result = await service.aggregate_portfolio_metrics(uuid4())  # Non-existent user

        assert result['total_value'] == 0
        assert result['portfolio_count'] == 0
        assert result['portfolios'] == []

    async def test_aggregate_beta(self, db_session):
        """Test weighted average beta calculation."""
        service = PortfolioAggregationService(db_session)

        portfolio_metrics = {
            uuid4(): {'beta': 1.2, 'weight': 0.50},  # Weight 50%
            uuid4(): {'beta': 0.8, 'weight': 0.30},  # Weight 30%
            uuid4(): {'beta': 1.0, 'weight': 0.20},  # Weight 20%
        }

        aggregate_beta = await service.aggregate_beta(portfolio_metrics)

        # Expected: (1.2 * 0.50) + (0.8 * 0.30) + (1.0 * 0.20) = 1.04
        expected = 1.04
        assert abs(aggregate_beta - expected) < 0.001

    async def test_aggregate_beta_missing_data(self, db_session):
        """Test beta aggregation with some missing data."""
        service = PortfolioAggregationService(db_session)

        portfolio_metrics = {
            uuid4(): {'beta': 1.2, 'weight': 0.50},
            uuid4(): {'beta': None, 'weight': 0.30},  # Missing beta
            uuid4(): {'beta': 1.0, 'weight': 0.20},
        }

        aggregate_beta = await service.aggregate_beta(portfolio_metrics)

        # Should only use portfolios with beta data
        # Renormalized weights: 0.50/(0.50+0.20) = 0.714, 0.20/(0.50+0.20) = 0.286
        # Expected: (1.2 * 0.714) + (1.0 * 0.286) = 1.143
        expected = 1.143
        assert abs(aggregate_beta - expected) < 0.01

    async def test_aggregate_volatility(self, db_session):
        """Test weighted average volatility calculation."""
        service = PortfolioAggregationService(db_session)

        portfolio_metrics = {
            uuid4(): {'volatility': 0.20, 'weight': 0.50},  # 20% volatility, 50% weight
            uuid4(): {'volatility': 0.15, 'weight': 0.30},  # 15% volatility, 30% weight
            uuid4(): {'volatility': 0.18, 'weight': 0.20},  # 18% volatility, 20% weight
        }

        aggregate_vol = await service.aggregate_volatility(portfolio_metrics)

        # Expected: (0.20 * 0.50) + (0.15 * 0.30) + (0.18 * 0.20) = 0.181
        expected = 0.181
        assert abs(aggregate_vol - expected) < 0.001

    async def test_aggregate_volatility_no_data(self, db_session):
        """Test volatility aggregation with no data."""
        service = PortfolioAggregationService(db_session)

        portfolio_metrics = {}
        aggregate_vol = await service.aggregate_volatility(portfolio_metrics)

        assert aggregate_vol is None

    async def test_single_portfolio_identity(
        self,
        db_session,
        test_user
    ):
        """Test that single portfolio aggregation returns identity (same value)."""
        # Create single portfolio
        single_portfolio = Portfolio(
            id=uuid4(),
            user_id=test_user.id,
            name="Single Portfolio",
            account_name="Single Account",
            account_type="taxable",
            is_active=True,
            equity_balance=Decimal('1000000')
        )
        db_session.add(single_portfolio)

        # Create snapshot
        snapshot = PortfolioSnapshot(
            id=uuid4(),
            portfolio_id=single_portfolio.id,
            snapshot_date=datetime.now(timezone.utc).date(),
            total_value=Decimal('1100000'),
            equity_balance=Decimal('1000000')
        )
        db_session.add(snapshot)
        await db_session.commit()

        service = PortfolioAggregationService(db_session)
        result = await service.aggregate_portfolio_metrics(test_user.id)

        # Single portfolio should have 100% weight
        assert result['portfolio_count'] == 1
        assert result['portfolios'][0]['weight'] == 1.0
        assert result['portfolios'][0]['value'] == 1100000


# Integration test with factor exposures
class TestFactorAggregation:
    """Test factor exposure aggregation."""

    async def test_aggregate_factor_exposures(
        self,
        db_session,
        test_user,
        test_portfolios
    ):
        """Test aggregating factor exposures across portfolios."""
        # Create positions for each portfolio
        position_a = Position(
            id=uuid4(),
            portfolio_id=test_portfolios['a'].id,
            symbol="AAPL",
            position_type=PositionType.LONG,
            quantity=Decimal('100')
        )
        position_b = Position(
            id=uuid4(),
            portfolio_id=test_portfolios['b'].id,
            symbol="MSFT",
            position_type=PositionType.LONG,
            quantity=Decimal('50')
        )
        db_session.add_all([position_a, position_b])
        await db_session.commit()

        # Create factor exposures
        factor_a = PositionFactorExposure(
            id=uuid4(),
            position_id=position_a.id,
            market_beta=Decimal('1.2'),
            size_beta=Decimal('-0.3'),
            value_beta=Decimal('0.1'),
            momentum_beta=Decimal('0.5'),
            quality_beta=Decimal('0.8')
        )
        factor_b = PositionFactorExposure(
            id=uuid4(),
            position_id=position_b.id,
            market_beta=Decimal('0.9'),
            size_beta=Decimal('-0.2'),
            value_beta=Decimal('0.2'),
            momentum_beta=Decimal('0.3'),
            quality_beta=Decimal('0.6')
        )
        db_session.add_all([factor_a, factor_b])
        await db_session.commit()

        # Test aggregation
        service = PortfolioAggregationService(db_session)

        # Portfolio A: $500k (50%), Portfolio B: $300k (30%), Portfolio C: $200k (20%)
        weights = {
            test_portfolios['a'].id: 0.50,
            test_portfolios['b'].id: 0.30,
            test_portfolios['c'].id: 0.20  # No positions, should not affect calculation
        }

        portfolio_ids = [p.id for p in test_portfolios.values()]
        aggregate_factors = await service.aggregate_factor_exposures(portfolio_ids, weights)

        # Should only include portfolios with factor data (A and B)
        # Renormalized weights: A=0.625, B=0.375
        assert 'market' in aggregate_factors
        assert 'size' in aggregate_factors
        assert 'value' in aggregate_factors

        # Market: (1.2 * 0.625) + (0.9 * 0.375) = 1.0875
        expected_market = 1.0875
        assert abs(aggregate_factors['market'] - expected_market) < 0.01
