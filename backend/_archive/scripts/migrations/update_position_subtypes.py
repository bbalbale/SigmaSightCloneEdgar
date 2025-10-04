#!/usr/bin/env python
"""
Update investment_subtype to be more accurate:
- ETFs should be marked as ETF, not STOCK
- Individual stocks should be STOCK
- Mutual funds should be MUTUAL_FUND
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.positions import Position, PositionType
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger(__name__)


# Known ETFs
ETFS = ['SPY', 'QQQ', 'VTI', 'BND', 'VNQ', 'VTIAX', 'GLD', 'DJP', 'IWM', 'EEM', 'TLT', 'XLE', 'XLF']

# Known mutual funds
MUTUAL_FUNDS = ['FXNAX', 'FCNTX', 'FMAGX', 'VTSAX', 'VTIAX', 'VFIAX']


async def update_subtypes():
    """Update investment_subtype to be more accurate."""
    async with AsyncSessionLocal() as db:
        # Get all PUBLIC positions
        result = await db.execute(
            select(Position).where(Position.investment_class == 'PUBLIC')
        )
        public_positions = result.scalars().all()

        logger.info(f"Found {len(public_positions)} PUBLIC positions to review")

        etf_count = 0
        stock_count = 0
        mutual_fund_count = 0

        for pos in public_positions:
            symbol_upper = pos.symbol.upper()

            # Determine correct subtype
            if symbol_upper in ETFS or 'ETF' in symbol_upper:
                if pos.investment_subtype != 'ETF':
                    pos.investment_subtype = 'ETF'
                    etf_count += 1
            elif symbol_upper in MUTUAL_FUNDS or len(symbol_upper) == 5:  # Most mutual funds have 5-letter tickers
                if pos.investment_subtype != 'MUTUAL_FUND':
                    pos.investment_subtype = 'MUTUAL_FUND'
                    mutual_fund_count += 1
            else:
                if pos.investment_subtype != 'STOCK':
                    pos.investment_subtype = 'STOCK'
                    stock_count += 1

        await db.commit()

        logger.info(f"\n✅ Updated subtypes:")
        logger.info(f"  ETFs: {etf_count}")
        logger.info(f"  Stocks: {stock_count}")
        logger.info(f"  Mutual Funds: {mutual_fund_count}")

        # Show final breakdown
        result = await db.execute(
            select(
                Position.investment_class,
                Position.investment_subtype,
            ).distinct()
            .order_by(Position.investment_class, Position.investment_subtype)
        )
        types = result.all()

        logger.info("\n" + "="*60)
        logger.info("FINAL INVESTMENT TYPES:")
        for row in types:
            # Count how many of each
            count_result = await db.execute(
                select(Position).where(
                    Position.investment_class == row.investment_class,
                    Position.investment_subtype == row.investment_subtype
                )
            )
            count = len(count_result.scalars().all())
            logger.info(f"  {row.investment_class}/{row.investment_subtype}: {count} positions")


async def main():
    """Main function."""
    await update_subtypes()


if __name__ == "__main__":
    asyncio.run(main())