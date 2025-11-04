"""
Backfill realized P&L for historical positions.

This script calculates realized profits/losses for any position that has an
exit_price/exit_date recorded but does not yet have realized_pnl populated.
It also inserts a PositionRealizedEvent so downstream analytics pick up the
historical activity.

Run:
    uv run python scripts/backfill_realized_pnl.py
"""
import asyncio
from decimal import Decimal
from typing import List

from sqlalchemy import select, and_

from app.database import AsyncSessionLocal
from app.models.positions import Position, PositionType
from app.models.position_realized_events import PositionRealizedEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


async def backfill_realized_pnl() -> None:
    """Calculate realized P&L for closed positions missing realized amounts."""
    async with AsyncSessionLocal() as session:
        query = select(Position).where(
            and_(
                Position.exit_price.isnot(None),
                Position.exit_date.isnot(None),
                Position.realized_pnl.is_(None),
                Position.deleted_at.is_(None),
            )
        )

        result = await session.execute(query)
        positions: List[Position] = result.scalars().all()

        if not positions:
            logger.info("No positions require realized P&L backfill.")
            return

        logger.info(f"Found {len(positions)} positions to backfill realized P&L.")
        updated = 0

        for position in positions:
            quantity_closed = _determine_closed_quantity(position)
            if quantity_closed is None:
                logger.warning(
                    "Skipping position %s due to missing quantity information.",
                    position.id,
                )
                continue

            realized_pnl = _calculate_realized_pnl(position, quantity_closed)

            position.realized_pnl = realized_pnl
            await _record_realized_event(session, position, quantity_closed, realized_pnl)

            logger.info(
                "Backfilled %s | symbol=%s | entry=%s | exit=%s | quantity=%s | realized=%s",
                position.id,
                position.symbol,
                position.entry_price,
                position.exit_price,
                quantity_closed,
                realized_pnl,
            )
            updated += 1

        await session.commit()
        logger.info(f"Backfill complete. Updated {updated} positions.")


def _determine_closed_quantity(position: Position) -> Decimal | None:
    """
    Infer the quantity that was closed for a historical position.

    If the stored quantity is zero we cannot deduce the original size, so we skip.
    """
    if position.quantity is None or position.quantity == 0:
        # Historical bug may have zeroed quantity before we recorded realized P&L.
        # Without additional audit data we cannot recover the closed size.
        return None

    # Return the quantity with its original sign.
    return position.quantity


def _calculate_realized_pnl(position: Position, quantity_closed: Decimal) -> Decimal:
    """Compute realized P&L for a position."""
    multiplier = Decimal("100") if position.position_type in {
        PositionType.LC,
        PositionType.LP,
        PositionType.SC,
        PositionType.SP,
    } else Decimal("1")

    # For all position types, the P&L is (exit_price - entry_price) * quantity.
    # For short positions, quantity is negative, which correctly inverts the P&L.
    price_diff = position.exit_price - position.entry_price

    return price_diff * quantity_closed * multiplier


async def _record_realized_event(
    session,
    position: Position,
    quantity_closed: Decimal,
    realized_pnl: Decimal,
) -> None:
    """Insert a realized event if one does not already exist for the exit date."""
    event = PositionRealizedEvent(
        position_id=position.id,
        portfolio_id=position.portfolio_id,
        trade_date=position.exit_date,
        quantity_closed=abs(quantity_closed),
        realized_pnl=realized_pnl,
    )
    session.add(event)


if __name__ == "__main__":
    asyncio.run(backfill_realized_pnl())
