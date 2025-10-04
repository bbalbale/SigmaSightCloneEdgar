#!/usr/bin/env python
"""
Test script for Target Prices API endpoints.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import json

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.models.positions import Position
from app.models.target_prices import TargetPrice
from app.schemas.target_prices import TargetPriceCreate
from app.services.target_price_service import TargetPriceService
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_target_prices():
    """Test target price functionality."""
    async with AsyncSessionLocal() as db:
        logger.info("="*60)
        logger.info("TESTING TARGET PRICES API")
        logger.info("="*60)

        # Get first portfolio for testing
        result = await db.execute(
            select(Portfolio).limit(1)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            logger.error("No portfolios found for testing")
            return

        logger.info(f"\nUsing portfolio: {portfolio.name} (ID: {portfolio.id})")

        # Get user
        result = await db.execute(
            select(User).where(User.id == portfolio.user_id)
        )
        user = result.scalar_one_or_none()

        # Initialize service
        service = TargetPriceService()

        # Test 1: Create target prices for a few positions
        logger.info("\n1. Creating target prices...")

        # Get some positions from the portfolio
        result = await db.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
            .limit(5)
        )
        positions = result.scalars().all()

        created_count = 0
        for pos in positions[:3]:  # Create targets for first 3 positions
            try:
                target_data = TargetPriceCreate(
                    symbol=pos.symbol,
                    position_type=pos.position_type.value if hasattr(pos.position_type, 'value') else 'LONG',
                    position_id=pos.id,
                    target_price_eoy=Decimal(str(float(pos.last_price or 100) * 1.15)),  # 15% upside
                    target_price_next_year=Decimal(str(float(pos.last_price or 100) * 1.25)),  # 25% upside
                    downside_target_price=Decimal(str(float(pos.last_price or 100) * 0.85)),  # 15% downside
                    current_price=pos.last_price or Decimal('100')
                )

                target_price = await service.create_target_price(
                    db,
                    portfolio.id,
                    target_data,
                    user.id if user else None
                )

                logger.info(f"  ✅ Created target for {pos.symbol}:")
                logger.info(f"     EOY Return: {target_price.expected_return_eoy:.2f}%")
                created_count += 1

            except Exception as e:
                logger.warning(f"  ⚠️ Could not create target for {pos.symbol}: {e}")

        logger.info(f"\nCreated {created_count} target prices")

        # Test 2: Get portfolio target prices
        logger.info("\n2. Fetching portfolio target prices...")
        target_prices = await service.get_portfolio_target_prices(db, portfolio.id)
        logger.info(f"  Found {len(target_prices)} target prices")

        for tp in target_prices[:3]:
            logger.info(f"  - {tp.symbol}: EOY target=${tp.target_price_eoy}, Return={tp.expected_return_eoy:.2f}%")

        # Test 3: Get portfolio summary
        logger.info("\n3. Getting portfolio summary...")
        try:
            summary = await service.get_portfolio_summary(db, portfolio.id)
            logger.info(f"  Coverage: {summary.positions_with_targets}/{summary.total_positions} positions ({summary.coverage_percentage:.1f}%)")

            if summary.weighted_expected_return_eoy:
                logger.info(f"  Weighted EOY Return: {summary.weighted_expected_return_eoy:.2f}%")
            if summary.weighted_expected_return_next_year:
                logger.info(f"  Weighted Next Year Return: {summary.weighted_expected_return_next_year:.2f}%")

        except Exception as e:
            logger.error(f"  Error getting summary: {e}")

        # Test 4: Update a target price
        if target_prices:
            logger.info("\n4. Updating a target price...")
            first_target = target_prices[0]

            from app.schemas.target_prices import TargetPriceUpdate
            update_data = TargetPriceUpdate(
                target_price_eoy=Decimal(str(float(first_target.target_price_eoy or 100) * 1.1))
            )

            updated = await service.update_target_price(
                db,
                first_target.id,
                update_data
            )

            logger.info(f"  ✅ Updated {updated.symbol} EOY target to ${updated.target_price_eoy}")
            logger.info(f"     New EOY Return: {updated.expected_return_eoy:.2f}%")

        # Test 5: CSV Export simulation
        logger.info("\n5. Simulating CSV export...")
        if target_prices:
            csv_lines = ["symbol,position_type,target_eoy,target_next_year,downside,current_price"]
            for tp in target_prices:
                csv_lines.append(
                    f"{tp.symbol},{tp.position_type},"
                    f"{tp.target_price_eoy},{tp.target_price_next_year},"
                    f"{tp.downside_target_price},{tp.current_price}"
                )
            logger.info("  CSV Preview:")
            for line in csv_lines[:4]:
                logger.info(f"    {line}")

        # Test 6: Delete a target price
        if target_prices and len(target_prices) > 1:
            logger.info("\n6. Deleting a target price...")
            to_delete = target_prices[-1]
            deleted = await service.delete_target_price(db, to_delete.id)
            if deleted:
                logger.info(f"  ✅ Deleted target price for {to_delete.symbol}")

        logger.info("\n" + "="*60)
        logger.info("Target prices API testing complete!")
        logger.info("="*60)


async def main():
    """Main function."""
    await test_target_prices()


if __name__ == "__main__":
    asyncio.run(main())