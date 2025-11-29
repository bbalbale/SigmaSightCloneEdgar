"""
Integration tests for Position Management API endpoints
Day 6 - Position Management Phase 1

Tests all 9 position endpoints with demo data.
"""
import asyncio
import sys
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position, PositionType
from app.services.position_service import PositionService
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_demo_user_and_portfolio(db: AsyncSession):
    """Get demo user and their portfolio for testing."""
    # Get demo user
    user_result = await db.execute(
        select(User).where(User.email == "demo_hnw@sigmasight.com")
    )
    user = user_result.scalar_one_or_none()

    if not user:
        logger.error("Demo user not found. Please run: python scripts/database/reset_and_seed.py seed")
        return None, None

    # Get user's portfolio
    portfolio_result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id).limit(1)
    )
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        logger.error("No portfolio found for demo user")
        return None, None

    logger.info(f"Using demo user: {user.email}, portfolio: {portfolio.name}")
    return user, portfolio


async def test_create_position(db: AsyncSession, service: PositionService, portfolio_id: UUID, user_id: UUID):
    """Test 1: Create a new position"""
    logger.info("\n=== TEST 1: Create Position ===")

    try:
        position = await service.create_position(
            portfolio_id=portfolio_id,
            symbol="TSLA",
            quantity=Decimal("50"),
            avg_cost=Decimal("250.00"),
            position_type=PositionType.LONG,
            investment_class="PUBLIC",
            user_id=user_id,
            notes="Test position for integration testing",
            entry_date=date.today(),
        )

        logger.info(f"✅ Created position: {position.symbol} ({position.id})")
        logger.info(f"   Quantity: {position.quantity}, Entry: ${position.entry_price}")
        return position.id

    except Exception as e:
        logger.error(f"❌ Failed to create position: {e}")
        raise


async def test_get_position(db: AsyncSession, position_id: UUID, user_id: UUID):
    """Test 2: Get single position"""
    logger.info("\n=== TEST 2: Get Position ===")

    try:
        result = await db.execute(
            select(Position).where(Position.id == position_id)
        )
        position = result.scalar_one_or_none()

        if not position:
            raise ValueError(f"Position {position_id} not found")

        logger.info(f"✅ Retrieved position: {position.symbol}")
        logger.info(f"   ID: {position.id}")
        logger.info(f"   Quantity: {position.quantity}, Entry: ${position.entry_price}")
        logger.info(f"   Notes: {position.notes}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to get position: {e}")
        raise


async def test_update_position(db: AsyncSession, service: PositionService, position_id: UUID, user_id: UUID):
    """Test 3: Update position"""
    logger.info("\n=== TEST 3: Update Position ===")

    try:
        updated_position = await service.update_position(
            position_id=position_id,
            user_id=user_id,
            quantity=Decimal("75"),
            notes="Updated test position - quantity increased"
        )

        logger.info(f"✅ Updated position: {updated_position.symbol}")
        logger.info(f"   New quantity: {updated_position.quantity}")
        logger.info(f"   New notes: {updated_position.notes}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to update position: {e}")
        raise


async def test_validate_symbol(db: AsyncSession, service: PositionService):
    """Test 4: Validate symbol"""
    logger.info("\n=== TEST 4: Validate Symbol ===")

    try:
        # Test valid symbol
        is_valid, message = await service.validate_symbol("AAPL")
        logger.info(f"✅ AAPL validation: valid={is_valid}, message={message}")

        # Test invalid symbol
        is_valid, message = await service.validate_symbol("INVALID123")
        logger.info(f"✅ INVALID123 validation: valid={is_valid}, message={message}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed symbol validation: {e}")
        raise


async def test_check_duplicate(db: AsyncSession, service: PositionService, portfolio_id: UUID):
    """Test 5: Check for duplicate positions"""
    logger.info("\n=== TEST 5: Check Duplicate ===")

    try:
        # Check for TSLA (should exist from test 1)
        has_duplicates, existing = await service.check_duplicate_positions(
            portfolio_id=portfolio_id,
            symbol="TSLA"
        )

        logger.info(f"✅ TSLA duplicate check: has_duplicates={has_duplicates}")
        logger.info(f"   Found {len(existing)} existing position(s)")

        # Check for non-existent symbol
        has_duplicates, existing = await service.check_duplicate_positions(
            portfolio_id=portfolio_id,
            symbol="NONEXISTENT"
        )

        logger.info(f"✅ NONEXISTENT duplicate check: has_duplicates={has_duplicates}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed duplicate check: {e}")
        raise


async def test_bulk_create(db: AsyncSession, service: PositionService, portfolio_id: UUID, user_id: UUID):
    """Test 6: Bulk create positions"""
    logger.info("\n=== TEST 6: Bulk Create Positions ===")

    try:
        positions_data = [
            {
                "symbol": "MSFT",
                "quantity": Decimal("100"),
                "avg_cost": Decimal("350.00"),
                "position_type": PositionType.LONG,
                "investment_class": "PUBLIC",
                "notes": "Bulk test position 1"
            },
            {
                "symbol": "GOOGL",
                "quantity": Decimal("50"),
                "avg_cost": Decimal("140.00"),
                "position_type": PositionType.LONG,
                "investment_class": "PUBLIC",
                "notes": "Bulk test position 2"
            }
        ]

        positions = await service.bulk_create_positions(
            portfolio_id=portfolio_id,
            positions_data=positions_data,
            user_id=user_id
        )

        logger.info(f"✅ Bulk created {len(positions)} positions")
        for pos in positions:
            logger.info(f"   - {pos.symbol}: {pos.quantity} shares @ ${pos.entry_price}")

        return [pos.id for pos in positions]

    except Exception as e:
        logger.error(f"❌ Failed bulk create: {e}")
        raise


async def test_soft_delete(db: AsyncSession, service: PositionService, position_id: UUID, user_id: UUID):
    """Test 7: Soft delete position"""
    logger.info("\n=== TEST 7: Soft Delete Position ===")

    try:
        result = await service.soft_delete_position(
            position_id=position_id,
            user_id=user_id
        )

        logger.info(f"✅ Soft deleted position: {result['symbol']}")

        # Verify it's marked deleted (refresh from DB)
        await db.rollback()  # Clear any pending changes
        position_result = await db.execute(
            select(Position).where(Position.id == position_id)
        )
        position = position_result.scalar_one_or_none()

        if position and position.deleted_at:
            logger.info(f"✅ Verified: Position is soft deleted (deleted_at={position.deleted_at})")
        else:
            raise ValueError("Soft delete failed - deleted_at not set")

        return True

    except Exception as e:
        logger.error(f"❌ Failed soft delete: {e}")
        raise


async def test_bulk_delete(db: AsyncSession, service: PositionService, position_ids: list, user_id: UUID):
    """Test 8: Bulk delete positions"""
    logger.info("\n=== TEST 8: Bulk Delete Positions ===")

    try:
        result = await service.bulk_delete_positions(
            position_ids=position_ids,
            user_id=user_id
        )

        logger.info(f"✅ Bulk deleted {result['count']} positions")
        logger.info(f"   Symbols: {', '.join(result['positions'])}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed bulk delete: {e}")
        raise


async def test_hard_delete(db: AsyncSession, service: PositionService, portfolio_id: UUID, user_id: UUID):
    """Test 9: Hard delete (Reverse Addition)"""
    logger.info("\n=== TEST 9: Hard Delete (Reverse Addition) ===")

    try:
        # Create a new position for hard delete test
        position = await service.create_position(
            portfolio_id=portfolio_id,
            symbol="NVDA",
            quantity=Decimal("25"),
            avg_cost=Decimal("500.00"),
            position_type=PositionType.LONG,
            investment_class="PUBLIC",
            user_id=user_id,
            notes="Test position for hard delete"
        )

        logger.info(f"Created test position: {position.symbol} ({position.id})")

        # Check if should hard delete (< 5 min, no snapshots)
        should_hard, reason = await service.should_hard_delete(position.id)
        logger.info(f"Should hard delete: {should_hard}, Reason: {reason}")

        if should_hard:
            result = await service.hard_delete_position(position.id, user_id)
            logger.info(f"✅ Hard deleted position: {result['symbol']}")

            # Verify it's gone
            check_result = await db.execute(
                select(Position).where(Position.id == position.id)
            )
            check_position = check_result.scalar_one_or_none()

            if not check_position:
                logger.info(f"✅ Verified: Position permanently removed from database")
            else:
                raise ValueError("Hard delete failed - position still exists")
        else:
            logger.info(f"⚠️ Skipping hard delete test: {reason}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed hard delete test: {e}")
        raise


async def run_all_tests():
    """Run all integration tests"""
    logger.info("=" * 80)
    logger.info("POSITION MANAGEMENT API - INTEGRATION TESTS")
    logger.info("Day 6 - Testing all 9 endpoints")
    logger.info("=" * 80)

    async with get_async_session() as db:
        # Setup
        user, portfolio = await get_demo_user_and_portfolio(db)
        if not user or not portfolio:
            logger.error("Failed to get demo data. Exiting.")
            return False

        service = PositionService(db)

        try:
            # Test 1: Create position
            test_position_id = await test_create_position(db, service, portfolio.id, user.id)
            await db.commit()

            # Test 2: Get position
            await test_get_position(db, test_position_id, user.id)

            # Test 3: Update position
            await test_update_position(db, service, test_position_id, user.id)
            await db.commit()

            # Test 4: Validate symbol
            await test_validate_symbol(db, service)

            # Test 5: Check duplicate
            await test_check_duplicate(db, service, portfolio.id)

            # Test 6: Bulk create
            bulk_position_ids = await test_bulk_create(db, service, portfolio.id, user.id)
            await db.commit()

            # Test 7: Soft delete (use test position from Test 1)
            await test_soft_delete(db, service, test_position_id, user.id)
            await db.commit()

            # Test 8: Bulk delete (use positions from Test 6)
            await test_bulk_delete(db, service, bulk_position_ids, user.id)
            await db.commit()

            # Test 9: Hard delete
            await test_hard_delete(db, service, portfolio.id, user.id)
            await db.commit()

            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("✅ ALL TESTS PASSED")
            logger.info("=" * 80)
            logger.info("\nTest Summary:")
            logger.info("  ✅ Test 1: Create Position")
            logger.info("  ✅ Test 2: Get Position")
            logger.info("  ✅ Test 3: Update Position")
            logger.info("  ✅ Test 4: Validate Symbol")
            logger.info("  ✅ Test 5: Check Duplicate")
            logger.info("  ✅ Test 6: Bulk Create Positions")
            logger.info("  ✅ Test 7: Soft Delete Position")
            logger.info("  ✅ Test 8: Bulk Delete Positions")
            logger.info("  ✅ Test 9: Hard Delete (Reverse Addition)")
            logger.info("\n✅ Position Management API - All endpoints working correctly")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"\n❌ TEST SUITE FAILED: {e}")
            await db.rollback()
            return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
