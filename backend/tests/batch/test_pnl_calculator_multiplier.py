import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import delete, select

from app.batch.pnl_calculator import PnLCalculator
from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache
from app.models.positions import Position, PositionType
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio, User


@pytest.mark.asyncio
async def test_pnl_calculator_respects_security_type():
    calc_date = date(2024, 5, 6)  # Monday
    prev_date = date(2024, 5, 3)  # Previous trading day (Friday)
    symbol = f"OPT{uuid4().hex[:8]}"

    async with AsyncSessionLocal() as db:
        user = User(
            id=uuid4(),
            email=f"{uuid4().hex[:8]}@example.com",
            hashed_password="test",
            full_name="Test User"
        )
        db.add(user)

        portfolio = Portfolio(
            id=uuid4(),
            user_id=user.id,
            name="Option Test",
            account_name="Option Account",
            account_type="taxable",
            equity_balance=Decimal("100000.00")
        )
        db.add(portfolio)

        position = Position(
            id=uuid4(),
            portfolio_id=portfolio.id,
            symbol=symbol,
            position_type=PositionType.LC,
            quantity=Decimal("2"),
            entry_price=Decimal("3.00"),
            entry_date=prev_date
        )
        db.add(position)

        db.add_all([
            MarketDataCache(
                symbol=symbol,
                date=prev_date,
                close=Decimal("4.00")
            ),
            MarketDataCache(
                symbol=symbol,
                date=calc_date,
                close=Decimal("5.00")
            )
        ])

        await db.flush()
        await db.refresh(position)

        calculator = PnLCalculator()
        pnl = await calculator._calculate_position_pnl(
            db=db,
            position=position,
            calculation_date=calc_date,
            previous_snapshot=None
        )

        assert pnl == Decimal("200"), "Should apply 100x contract multiplier for options"

    # Separate scenario for equities (no multiplier)
    equity_calc_date = date(2024, 6, 4)  # Tuesday
    equity_prev_date = date(2024, 6, 3)  # Monday
    equity_symbol = f"EQ{uuid4().hex[:8]}"

    async with AsyncSessionLocal() as db:
        equity_user = User(
            id=uuid4(),
            email=f"{uuid4().hex[:8]}@example.com",
            hashed_password="test",
            full_name="Equity User"
        )
        db.add(equity_user)

        equity_portfolio = Portfolio(
            id=uuid4(),
            user_id=equity_user.id,
            name="Equity Test",
            account_name="Equity Account",
            account_type="taxable",
            equity_balance=Decimal("50000.00")
        )
        db.add(equity_portfolio)

        equity_position = Position(
            id=uuid4(),
            portfolio_id=equity_portfolio.id,
            symbol=equity_symbol,
            position_type=PositionType.LONG,
            quantity=Decimal("10"),
            entry_price=Decimal("20.00"),
            entry_date=equity_prev_date
        )
        db.add(equity_position)

        db.add_all([
            MarketDataCache(
                symbol=equity_symbol,
                date=equity_prev_date,
                close=Decimal("20.00")
            ),
            MarketDataCache(
                symbol=equity_symbol,
                date=equity_calc_date,
                close=Decimal("21.00")
            )
        ])

        await db.flush()
        await db.refresh(equity_position)

        calculator = PnLCalculator()
        equity_pnl = await calculator._calculate_position_pnl(
            db=db,
            position=equity_position,
            calculation_date=equity_calc_date,
            previous_snapshot=None
        )

        assert equity_pnl == Decimal("10"), "Stocks should not be scaled by option multiplier"

    # Verify calculate_portfolio_pnl updates portfolio.equity_balance
    calc_date = date(2024, 5, 6)  # Monday
    prev_date = date(2024, 5, 3)  # Previous trading day
    symbol = f"EQ{uuid4().hex[:8]}"

    async with AsyncSessionLocal() as db:
        user = User(
            id=uuid4(),
            email=f"{uuid4().hex[:8]}@example.com",
            hashed_password="test",
            full_name="Equity Balance User"
        )
        db.add(user)

        portfolio = Portfolio(
            id=uuid4(),
            user_id=user.id,
            name="Equity Balance Portfolio",
            account_name="Equity Account",
            account_type="taxable",
            equity_balance=Decimal("100000.00")
        )
        db.add(portfolio)

        position = Position(
            id=uuid4(),
            portfolio_id=portfolio.id,
            symbol=symbol,
            position_type=PositionType.LONG,
            quantity=Decimal("100"),
            entry_price=Decimal("100.00"),
            entry_date=prev_date
        )
        db.add(position)

        db.add_all([
            MarketDataCache(
                symbol=symbol,
                date=prev_date,
                close=Decimal("100.00")
            ),
            MarketDataCache(
                symbol=symbol,
                date=calc_date,
                close=Decimal("105.00")
            )
        ])

        await db.flush()

        calculator = PnLCalculator()
        success = await calculator.calculate_portfolio_pnl(
            portfolio_id=portfolio.id,
            calculation_date=calc_date,
            db=db
        )

        assert success, "P&L calculation should succeed"

        refreshed_portfolio = (await db.execute(
            select(Portfolio).where(Portfolio.id == portfolio.id)
        )).scalar_one()

        expected_equity = Decimal("100000.00") + Decimal("500.00")
        assert refreshed_portfolio.equity_balance == expected_equity

        await db.execute(
            delete(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio.id)
        )
        await db.execute(delete(Position).where(Position.portfolio_id == portfolio.id))
        await db.execute(delete(Portfolio).where(Portfolio.id == portfolio.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.execute(delete(MarketDataCache).where(MarketDataCache.symbol == symbol))
        await db.commit()
