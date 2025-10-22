"""
Apply sector tags to all existing positions across all portfolios.

This script:
1. Gets all portfolios in the database
2. For each portfolio, applies sector tags to all positions
3. Uses the sector_tag_service to ensure consistency
4. Reports on the tagging results

Usage:
    uv run python scripts/apply_sector_tags_to_all.py
"""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.services.sector_tag_service import restore_sector_tags_for_portfolio
from app.core.logging import get_logger

logger = get_logger(__name__)


async def apply_sector_tags_to_all_portfolios():
    """Apply sector tags to all positions in all portfolios."""

    async with get_async_session() as db:
        # Get all portfolios
        stmt = select(Portfolio)
        result = await db.execute(stmt)
        portfolios = result.scalars().all()

        if not portfolios:
            logger.warning("No portfolios found in database")
            print("No portfolios found in database")
            return

        logger.info(f"Found {len(portfolios)} portfolios to process")
        print(f"\nFound {len(portfolios)} portfolios to process\n")

        total_positions_tagged = 0
        total_tags_created = 0

        # Process each portfolio
        for i, portfolio in enumerate(portfolios, 1):
            print(f"[{i}/{len(portfolios)}] Processing portfolio: {portfolio.name}")
            print(f"    User ID: {portfolio.user_id}")

            try:
                # Apply sector tags using the service
                result = await restore_sector_tags_for_portfolio(
                    db=db,
                    portfolio_id=portfolio.id,
                    user_id=portfolio.user_id
                )

                # Update totals
                total_positions_tagged += result["positions_tagged"]
                total_tags_created += result["tags_created"]

                # Display results for this portfolio
                print(f"    Tagged: {result['positions_tagged']} positions")
                print(f"    Created: {result['tags_created']} new tags")
                print(f"    Skipped: {result['positions_skipped']} positions")

                if result["tags_applied"]:
                    print(f"    Tag distribution:")
                    for tag_info in result["tags_applied"]:
                        print(f"       - {tag_info['tag_name']}: {tag_info['position_count']} positions")

                print()  # Blank line between portfolios

            except Exception as e:
                logger.error(f"Error processing portfolio {portfolio.id}: {e}", exc_info=True)
                print(f"    Error: {e}\n")
                continue

        # Final summary
        print("=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        print(f"Total positions tagged: {total_positions_tagged}")
        print(f"Total tags created: {total_tags_created}")
        print(f"Portfolios processed: {len(portfolios)}")
        print("=" * 60)

        logger.info(
            f"Sector tagging complete: {total_positions_tagged} positions tagged, "
            f"{total_tags_created} tags created across {len(portfolios)} portfolios"
        )


if __name__ == "__main__":
    asyncio.run(apply_sector_tags_to_all_portfolios())
