import os
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("POLYGON_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from app.models.positions import Position, PositionType
from app.models.users import Portfolio
from app.services.position_service import PositionService


class _FakeResult:
    """Lightweight wrapper mimicking SQLAlchemy scalar result."""

    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


def _build_position(
    portfolio: Portfolio,
    quantity: Decimal,
    entry_price: Decimal,
    position_type: PositionType,
) -> Position:
    position = Position(
        id=uuid4(),
        portfolio_id=portfolio.id,
        symbol="TEST",
        position_type=position_type,
        quantity=quantity,
        entry_price=entry_price,
        entry_date=date(2025, 1, 1),
        investment_class="PUBLIC",
        investment_subtype="STOCK",
        notes=None,
    )
    position.portfolio = portfolio
    position.created_at = datetime.utcnow()
    position.updated_at = datetime.utcnow()
    position.realized_pnl = None
    position.exit_price = None
    position.exit_date = None
    position.deleted_at = None
    return position


@pytest.mark.asyncio
async def test_partial_close_accumulates_realized_pnl_and_retains_position():
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Test",
        account_name="Primary",
    )

    position = _build_position(
        portfolio=portfolio,
        quantity=Decimal("100"),
        entry_price=Decimal("150"),
        position_type=PositionType.LONG,
    )

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_FakeResult(position))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    service = PositionService(db)

    exit_date = date(2025, 6, 1)
    updated = await service.update_position(
        position_id=position.id,
        user_id=portfolio.user_id,
        exit_price=Decimal("160"),
        close_quantity=Decimal("40"),
        quantity=Decimal("60"),
        exit_date=exit_date,
    )

    assert updated.quantity == Decimal("60")
    assert updated.realized_pnl == Decimal("400")
    assert updated.exit_price is None
    assert updated.exit_date is None

    db.add.assert_called_once()
    event = db.add.call_args.args[0]
    assert event.quantity_closed == Decimal("40")
    assert event.realized_pnl == Decimal("400")
    assert event.trade_date == exit_date


@pytest.mark.asyncio
async def test_full_close_short_position_sets_exit_fields():
    portfolio = Portfolio(
        id=uuid4(),
        user_id=uuid4(),
        name="Short",
        account_name="Margin",
    )

    position = _build_position(
        portfolio=portfolio,
        quantity=Decimal("-100"),
        entry_price=Decimal("200"),
        position_type=PositionType.SHORT,
    )

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_FakeResult(position))
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()

    service = PositionService(db)

    exit_date = date(2025, 7, 15)
    updated = await service.update_position(
        position_id=position.id,
        user_id=portfolio.user_id,
        exit_price=Decimal("180"),
        close_quantity=Decimal("100"),
        quantity=Decimal("0"),
        exit_date=exit_date,
    )

    assert updated.quantity == Decimal("0")
    assert updated.realized_pnl == Decimal("2000")
    assert updated.exit_price == Decimal("180")
    assert updated.exit_date == exit_date

    db.add.assert_called_once()
    event = db.add.call_args.args[0]
    assert event.quantity_closed == Decimal("100")
    assert event.realized_pnl == Decimal("2000")
    assert event.trade_date == exit_date
