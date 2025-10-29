"""
Debug October 21 correlation hang with timeout
"""
import asyncio
import logging
from datetime import date

from app.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3 as batch_orchestrator

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = get_logger(__name__)


async def run_with_timeout():
    """Run Oct 21 batch with 5-minute timeout"""
    calculation_date = date(2025, 10, 21)

    print("\n" + "="*80)
    print("DEBUG: October 21, 2025 with 5-minute timeout")
    print("="*80)
    print("\nWatch for last debug message before timeout...")
    print("="*80 + "\n")

    try:
        # 5-minute timeout
        result = await asyncio.wait_for(
            batch_orchestrator.run_daily_batch_sequence(
                calculation_date=calculation_date
            ),
            timeout=300
        )

        print("\n✅ COMPLETED without hanging!")

    except asyncio.TimeoutError:
        print("\n⏱️ TIMEOUT after 5 minutes")
        print("Check logs above for LAST debug message before hang")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_with_timeout())
