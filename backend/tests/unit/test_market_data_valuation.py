from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.batch.pnl_calculator import PnLCalculator
from app.calculations.market_data import get_position_valuation, calculate_daily_pnl
from app.models.positions import Position, PositionType
from app.services.portfolio_analytics_service import PortfolioAnalyticsService


def _build_position(
    *,
    symbol: str,
    quantity: Decimal,
    position_type: PositionType,
    entry_price: Decimal,
    last_price: Decimal,
) -> Position:
    """Helper to construct Position objects for unit tests without DB persistence."""
    return Position(
        id=uuid4(),
        portfolio_id=uuid4(),
        symbol=symbol,
        position_type=position_type,
        quantity=quantity,
        entry_price=entry_price,
        entry_date=date(2024, 1, 1),
        last_price=last_price,
    )


def test_get_position_valuation_applies_option_multiplier():
    """Ensure option valuations honour the 100x contract multiplier."""
    position = _build_position(
        symbol="OPT1",
        quantity=Decimal("2"),
        position_type=PositionType.LC,
        entry_price=Decimal("4"),
        last_price=Decimal("5"),
    )

    valuation = get_position_valuation(position)

    assert valuation.multiplier == Decimal("100")
    assert valuation.market_value == Decimal("1000")  # 2 * 5 * 100
    assert valuation.cost_basis == Decimal("800")  # 2 * 4 * 100
    assert valuation.unrealized_pnl == Decimal("200")


@pytest.mark.asyncio
async def test_calculate_position_pnl_uses_lookback(monkeypatch):
    """
    When the immediate previous trading day price is missing, the calculator should
    use the latest available prior close within the lookback window.
    """
    calculator = PnLCalculator()
    calculation_date = date(2024, 1, 10)
    position = _build_position(
        symbol="ABC",
        quantity=Decimal("3"),
        position_type=PositionType.LONG,
        entry_price=Decimal("90"),
        last_price=Decimal("100"),
    )

    price_map = {
        (position.symbol, calculation_date): Decimal("100"),
    }

    async def fake_get_cached_price(self, db, symbol, price_date):
        return price_map.get((symbol, price_date))

    async def fake_get_previous_price(db, symbol, current_date, max_lookback_days):
        assert symbol == position.symbol
        assert current_date == calculation_date
        # Simulate finding a price three days back
        return Decimal("95"), current_date - timedelta(days=3)

    monkeypatch.setattr(
        PnLCalculator,
        "_get_cached_price",
        fake_get_cached_price,
    )
    monkeypatch.setattr(
        "app.batch.pnl_calculator.get_previous_trading_day_price",
        fake_get_previous_price,
    )

    pnl = await calculator._calculate_position_pnl(
        db=None,
        position=position,
        calculation_date=calculation_date,
        previous_snapshot=None,
    )

    # (100 - 95) * 3 shares
    assert pnl == Decimal("15")


@pytest.mark.asyncio
async def test_portfolio_analytics_uses_option_multiplier(monkeypatch):
    """Portfolio analytics should respect option multipliers when aggregating exposures."""
    service = PortfolioAnalyticsService()

    async def fake_target_returns(*args, **kwargs):
        return None

    async def fake_period_pnl(*args, **kwargs):
        return {"ytd_pnl": 0.0, "mtd_pnl": 0.0}

    monkeypatch.setattr(service, "_get_target_returns", fake_target_returns)
    monkeypatch.setattr(service, "_calculate_period_pnl", fake_period_pnl)

    option_position = _build_position(
        symbol="OPTX",
        quantity=Decimal("1"),
        position_type=PositionType.LC,
        entry_price=Decimal("4"),
        last_price=Decimal("5"),
    )

    metrics = await service._calculate_portfolio_metrics(
        db=None,
        portfolio_id=uuid4(),
        positions=[option_position],
        equity_balance=1000.0,
        snapshot=None,
    )

    assert metrics["exposures"]["long_exposure"] == 500.0  # 1 * 5 * 100
    assert metrics["pnl"]["unrealized_pnl"] == 100.0  # (5 - 4) * 1 * 100


@pytest.mark.asyncio
async def test_daily_return_aligned_for_short_positions(monkeypatch):
    """Daily return should be positive when a short position profits."""
    position = _build_position(
        symbol="SHORT1",
        quantity=Decimal("-10"),
        position_type=PositionType.SHORT,
        entry_price=Decimal("50"),
        last_price=Decimal("48"),
    )

    async def fake_get_previous_price(db, symbol, current_date, max_lookback_days):
        return Decimal("50"), current_date - timedelta(days=1)

    monkeypatch.setattr(
        "app.calculations.market_data.get_previous_trading_day_price",
        fake_get_previous_price,
    )

    result = await calculate_daily_pnl(
        db=None,
        position=position,
        current_price=Decimal("48"),
    )

    assert result["daily_pnl"] == Decimal("20")  # (-10 * 48) - (-10 * 50)
    assert result["daily_return"] == Decimal("0.04")
