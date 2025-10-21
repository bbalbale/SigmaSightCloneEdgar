"""
Test spread factor calculation with debug logging
Run for HNW portfolio to see where position_betas gets lost
"""
import asyncio
from uuid import UUID
from datetime import date

from app.database import AsyncSessionLocal
from app.calculations.factors_spread import calculate_portfolio_spread_betas
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_spread_calculation():
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')
    calculation_date = date(2025, 10, 21)  # Today

    print('=' * 80)
    print('TESTING SPREAD FACTOR CALCULATION WITH DEBUG LOGGING')
    print('=' * 80)
    print(f'Portfolio: {portfolio_id}')
    print(f'Calculation Date: {calculation_date}')
    print('=' * 80)
    print()

    async with AsyncSessionLocal() as db:
        try:
            logger.info(f"Starting spread factor calculation for portfolio {portfolio_id}")

            result = await calculate_portfolio_spread_betas(
                db=db,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date,
                context=None  # Let it load context
            )

            logger.info(f"Calculation complete!")
            logger.info(f"Result keys: {result.keys()}")
            logger.info(f"Factor betas: {result.get('factor_betas', {})}")
            logger.info(f"Position betas count: {len(result.get('position_betas', {}))}")
            logger.info(f"Data quality: {result.get('data_quality', {})}")

            print()
            print('=' * 80)
            print('CALCULATION RESULT:')
            print('=' * 80)
            print(f"Position betas calculated: {len(result.get('position_betas', {}))}")
            print(f"Portfolio factors calculated: {len(result.get('factor_betas', {}))}")
            print(f"Storage results: {result.get('storage_results', {})}")
            print()

            # Commit the transaction
            await db.commit()
            logger.info("Transaction committed successfully")

        except Exception as e:
            logger.error(f"Error during calculation: {e}", exc_info=True)
            await db.rollback()
            raise


if __name__ == '__main__':
    asyncio.run(test_spread_calculation())
