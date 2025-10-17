"""
Test Sector Analysis Module
Tests sector exposure and concentration calculations on demo portfolios.

Usage:
    uv run python scripts/test_sector_analysis.py
"""
import asyncio
from datetime import date

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.calculations.sector_analysis import (
    calculate_portfolio_sector_concentration,
    calculate_sector_exposure,
    calculate_concentration_metrics
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_sector_analysis():
    """Test sector analysis on all demo portfolios"""
    logger.info("=" * 60)
    logger.info("Testing Sector Analysis Module")
    logger.info("=" * 60)

    async with AsyncSessionLocal() as db:
        # Get all portfolios
        result = await db.execute(select(Portfolio))
        portfolios = result.scalars().all()

        logger.info(f"\nFound {len(portfolios)} portfolios to analyze\n")

        for portfolio in portfolios:
            logger.info("=" * 60)
            logger.info(f"Portfolio: {portfolio.name}")
            logger.info(f"ID: {portfolio.id}")
            logger.info("=" * 60)

            # Test complete analysis
            result = await calculate_portfolio_sector_concentration(
                db,
                portfolio.id,
                date.today()
            )

            if result['success']:
                logger.info("\n✅ Analysis SUCCESSFUL")

                # Sector exposure
                if result['sector_exposure']:
                    se = result['sector_exposure']
                    logger.info("\n--- SECTOR EXPOSURE ---")
                    logger.info(f"Total Portfolio Value: ${se['total_portfolio_value']:,.2f}")
                    logger.info(f"Classified Positions: {sum(se['positions_by_sector'].values())}")
                    logger.info(f"Unclassified Positions: {se['unclassified_count']}")

                    logger.info("\nPortfolio vs S&P 500:")
                    logger.info(f"{'Sector':<30} {'Portfolio':<12} {'S&P 500':<12} {'Over/Under':<12}")
                    logger.info("-" * 70)

                    for sector in sorted(se['portfolio_weights'].keys(), key=lambda s: se['portfolio_weights'][s], reverse=True):
                        port_wt = se['portfolio_weights'][sector]
                        bench_wt = se['benchmark_weights'].get(sector, 0.0)
                        diff = se['over_underweight'][sector]

                        logger.info(
                            f"{sector:<30} {port_wt*100:>10.2f}%  {bench_wt*100:>10.2f}%  "
                            f"{diff*100:>+10.2f}%"
                        )

                    logger.info(f"\nLargest Overweight: {se['largest_overweight']}")
                    logger.info(f"Largest Underweight: {se['largest_underweight']}")

                # Concentration metrics
                if result['concentration']:
                    conc = result['concentration']
                    logger.info("\n--- CONCENTRATION METRICS ---")
                    logger.info(f"Total Positions: {conc['total_positions']}")
                    logger.info(f"HHI: {conc['hhi']:.2f}")
                    logger.info(f"Effective # of Positions: {conc['effective_num_positions']:.2f}")
                    logger.info(f"Top 3 Concentration: {conc['top_3_concentration']*100:.2f}%")
                    logger.info(f"Top 10 Concentration: {conc['top_10_concentration']*100:.2f}%")

                    # Interpretation
                    if conc['hhi'] > 2500:
                        logger.info("⚠️  HIGH CONCENTRATION - Portfolio is concentrated")
                    elif conc['hhi'] > 1500:
                        logger.info("⚡ MODERATE CONCENTRATION")
                    else:
                        logger.info("✅ WELL DIVERSIFIED")

            else:
                logger.error(f"\n❌ Analysis FAILED: {result.get('error', 'Unknown error')}")

            logger.info("")

    logger.info("=" * 60)
    logger.info("Sector Analysis Test Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_sector_analysis())
