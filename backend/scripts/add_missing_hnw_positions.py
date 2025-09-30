"""
Add Missing Positions to HNW Portfolio
Inserts 7 missing positions (Real Estate, Crypto, Art, Cash) without affecting existing data
"""
import asyncio
from datetime import date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.positions import Position, PositionType
from app.core.logging import get_logger

logger = get_logger(__name__)

# HNW Portfolio ID (from seed data)
HNW_PORTFOLIO_ID = 'e23ab931-a033-edfe-ed4f-9d02474780b4'

# Missing positions based on Ben Mock Portfolios.md
MISSING_POSITIONS = [
    # Real Estate (20% allocation - $570K)
    {
        "symbol": "HOME_EQUITY",
        "quantity": Decimal("1"),
        "entry_price": Decimal("285000.00"),
        "entry_date": date(2023, 1, 15),
        "investment_class": "PRIVATE",
        "investment_subtype": "Real Estate",
        "position_type": PositionType.LONG,
    },
    {
        "symbol": "RENTAL_CONDO",
        "quantity": Decimal("1"),
        "entry_price": Decimal("142500.00"),
        "entry_date": date(2022, 6, 1),
        "investment_class": "PRIVATE",
        "investment_subtype": "Real Estate",
        "position_type": PositionType.LONG,
    },
    {
        "symbol": "RENTAL_SFH",
        "quantity": Decimal("1"),
        "entry_price": Decimal("142500.00"),
        "entry_date": date(2021, 9, 1),
        "investment_class": "PRIVATE",
        "investment_subtype": "Real Estate",
        "position_type": PositionType.LONG,
    },
    # Cryptocurrency (1.5% allocation - $42.75K)
    {
        "symbol": "CRYPTO_BTC_ETH",
        "quantity": Decimal("1"),
        "entry_price": Decimal("42750.00"),
        "entry_date": date(2023, 3, 1),
        "investment_class": "PRIVATE",
        "investment_subtype": "Cryptocurrency",
        "position_type": PositionType.LONG,
    },
    # Art/Collectibles (1% allocation - $28.5K)
    {
        "symbol": "ART_COLLECTIBLES",
        "quantity": Decimal("1"),
        "entry_price": Decimal("28500.00"),
        "entry_date": date(2022, 11, 1),
        "investment_class": "PRIVATE",
        "investment_subtype": "Art",
        "position_type": PositionType.LONG,
    },
    # Cash & Fixed Income (3% allocation - $85.5K)
    {
        "symbol": "MONEY_MARKET",
        "quantity": Decimal("1"),
        "entry_price": Decimal("57000.00"),
        "entry_date": date(2024, 1, 1),
        "investment_class": "PRIVATE",
        "investment_subtype": "Cash",
        "position_type": PositionType.LONG,
    },
    {
        "symbol": "TREASURY_BILLS",
        "quantity": Decimal("1"),
        "entry_price": Decimal("28500.00"),
        "entry_date": date(2024, 1, 1),
        "investment_class": "PRIVATE",
        "investment_subtype": "Fixed Income",
        "position_type": PositionType.LONG,
    },
]


async def add_missing_positions():
    """Add missing positions to HNW portfolio"""
    async with AsyncSessionLocal() as db:
        logger.info(f"Adding missing positions to HNW portfolio {HNW_PORTFOLIO_ID}")

        # Check existing positions
        stmt = select(Position).where(Position.portfolio_id == HNW_PORTFOLIO_ID)
        result = await db.execute(stmt)
        existing_positions = result.scalars().all()
        existing_symbols = {p.symbol for p in existing_positions}

        logger.info(f"Found {len(existing_positions)} existing positions")
        logger.info(f"Existing symbols: {sorted(existing_symbols)}")

        # Add missing positions
        added_count = 0
        skipped_count = 0
        total_value_added = Decimal("0")

        for pos_data in MISSING_POSITIONS:
            symbol = pos_data["symbol"]

            if symbol in existing_symbols:
                logger.info(f"⏭️  Skipping {symbol} - already exists")
                skipped_count += 1
                continue

            # Create new position
            position = Position(
                id=uuid4(),
                portfolio_id=HNW_PORTFOLIO_ID,
                symbol=symbol,
                quantity=pos_data["quantity"],
                entry_price=pos_data["entry_price"],
                entry_date=pos_data["entry_date"],
                position_type=pos_data["position_type"],
                investment_class=pos_data["investment_class"],
                investment_subtype=pos_data["investment_subtype"],
                last_price=pos_data["entry_price"],  # Initialize with entry price
                market_value=pos_data["quantity"] * pos_data["entry_price"],
                unrealized_pnl=Decimal("0"),  # No P&L yet
            )

            db.add(position)
            added_count += 1
            total_value_added += position.market_value

            logger.info(f"✅ Added {symbol}: {pos_data['quantity']} @ ${pos_data['entry_price']:,.2f} = ${position.market_value:,.2f}")

        # Commit changes
        await db.commit()

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY: Add Missing HNW Positions")
        print("=" * 80)
        print(f"Positions added:   {added_count}")
        print(f"Positions skipped: {skipped_count}")
        print(f"Total value added: ${total_value_added:,.2f}")
        print(f"")
        print(f"HNW Portfolio now has {len(existing_positions) + added_count} positions")
        print("=" * 80)

        return added_count


if __name__ == "__main__":
    asyncio.run(add_missing_positions())
