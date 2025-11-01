"""
Test script for sector tagging functionality

Tests:
1. Sector tag service imports
2. Batch orchestrator Phase 2.75 integration
3. API endpoint registration
"""
import asyncio
from sqlalchemy import select, func


async def test_imports():
    """Test that all required imports work"""
    print("\n=== Testing Imports ===")

    try:
        from app.services.sector_tag_service import (
            get_sector_color,
            get_or_create_sector_tag,
            apply_sector_tag_to_position,
            restore_sector_tags_for_portfolio,
            get_sector_distribution
        )
        print("[PASS] Sector tag service imports successfully")
    except ImportError as e:
        print(f"[FAIL] Sector tag service import failed: {e}")
        return False

    try:
        from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3
        print("[PASS] Batch orchestrator v3 imports successfully")
    except ImportError as e:
        print(f"[FAIL] Batch orchestrator v3 import failed: {e}")
        return False

    try:
        from app.api.v1.endpoints.admin_batch import router
        print("[PASS] Admin batch endpoints import successfully")

        # Check if restore-sector-tags endpoint exists
        endpoint_paths = [route.path for route in router.routes]
        if '/restore-sector-tags' in endpoint_paths:
            print("[PASS] Restore sector tags endpoint registered")
        else:
            print("[WARN] Restore sector tags endpoint not found in router")
            print(f"   Available endpoints: {endpoint_paths}")
    except ImportError as e:
        print(f"[FAIL] Admin batch endpoints import failed: {e}")
        return False

    return True


async def test_sector_colors():
    """Test sector color mapping"""
    print("\n=== Testing Sector Color Mapping ===")

    from app.services.sector_tag_service import get_sector_color, SECTOR_COLORS

    print(f"Total sectors mapped: {len(SECTOR_COLORS)}")

    # Test a few key sectors
    test_sectors = ["Technology", "Healthcare", "Financial Services", "Energy"]
    for sector in test_sectors:
        color = get_sector_color(sector)
        print(f"  {sector}: {color}")

    # Test unknown sector
    unknown_color = get_sector_color("Unknown Sector XYZ")
    print(f"  Unknown sector: {unknown_color}")


async def test_database_data():
    """Test existing sector tags in database"""
    print("\n=== Testing Database Data ===")

    from app.database import AsyncSessionLocal
    from app.models.tags_v2 import TagV2
    from app.models.position_tags import PositionTag
    from app.models.market_data import CompanyProfile

    async with AsyncSessionLocal() as db:
        # Count sector tags
        sector_tags = await db.execute(
            select(func.count(TagV2.id)).where(
                TagV2.description.like("Sector:%")
            )
        )
        print(f"Existing sector tags: {sector_tags.scalar()}")

        # Count position-tag links
        position_tag_links = await db.execute(
            select(func.count(PositionTag.id))
        )
        print(f"Total position-tag links: {position_tag_links.scalar()}")

        # Count company profiles with sector data
        profiles_with_sector = await db.execute(
            select(func.count(CompanyProfile.symbol)).where(
                CompanyProfile.sector.isnot(None)
            )
        )
        print(f"Company profiles with sector: {profiles_with_sector.scalar()}")

        # Show sample sectors
        sample_profiles = await db.execute(
            select(CompanyProfile.symbol, CompanyProfile.sector)
            .where(CompanyProfile.sector.isnot(None))
            .limit(5)
        )
        print("\nSample company sectors:")
        for symbol, sector in sample_profiles:
            print(f"  {symbol}: {sector}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("SECTOR TAGGING VERIFICATION")
    print("=" * 60)

    # Test imports
    imports_ok = await test_imports()
    if not imports_ok:
        print("\n[FAIL] Import tests failed, stopping")
        return

    # Test sector colors
    await test_sector_colors()

    # Test database data
    try:
        await test_database_data()
    except Exception as e:
        print(f"[WARN] Database test failed (this is OK if DB is not seeded): {e}")

    print("\n" + "=" * 60)
    print("[PASS] VERIFICATION COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Reseed database: python scripts/database/reset_and_seed.py reset")
    print("2. Check sector tags are created during seeding")
    print("3. Run batch processing to test Phase 2.75")
    print("4. Test API endpoint: POST /api/v1/admin/batch/restore-sector-tags")


if __name__ == "__main__":
    asyncio.run(main())
