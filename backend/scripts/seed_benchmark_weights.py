"""
Seed Benchmark Sector Weights
Fetches S&P 500 constituents from FMP API and calculates sector weights.

Usage:
    uv run python scripts/seed_benchmark_weights.py
"""
import asyncio
from datetime import date
from decimal import Decimal
from typing import Dict, List
import uuid
import os

import httpx
from sqlalchemy import select, and_

from app.database import AsyncSessionLocal
from app.models.market_data import BenchmarkSectorWeight
from app.core.logging import get_logger

logger = get_logger(__name__)

FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE_URL = "https://financialmodelingprep.com/api/v3"

# Static S&P 500 sector weights (fallback if FMP API key not available)
# Source: SPDR Sector ETFs as of 2025
STATIC_SP500_SECTOR_WEIGHTS = {
    'Technology': {'weight': 0.28, 'num_constituents': 75, 'market_cap': 12_000_000_000_000},
    'Healthcare': {'weight': 0.13, 'num_constituents': 63, 'market_cap': 5_500_000_000_000},
    'Financials': {'weight': 0.13, 'num_constituents': 71, 'market_cap': 5_500_000_000_000},
    'Consumer Discretionary': {'weight': 0.10, 'num_constituents': 54, 'market_cap': 4_200_000_000_000},
    'Industrials': {'weight': 0.08, 'num_constituents': 72, 'market_cap': 3_400_000_000_000},
    'Communication Services': {'weight': 0.08, 'num_constituents': 25, 'market_cap': 3_400_000_000_000},
    'Consumer Staples': {'weight': 0.06, 'num_constituents': 32, 'market_cap': 2_500_000_000_000},
    'Energy': {'weight': 0.04, 'num_constituents': 23, 'market_cap': 1_700_000_000_000},
    'Utilities': {'weight': 0.03, 'num_constituents': 28, 'market_cap': 1_300_000_000_000},
    'Real Estate': {'weight': 0.02, 'num_constituents': 30, 'market_cap': 850_000_000_000},
    'Materials': {'weight': 0.02, 'num_constituents': 27, 'market_cap': 850_000_000_000},
    'Other': {'weight': 0.03, 'num_constituents': 5, 'market_cap': 1_300_000_000_000}
}


async def fetch_sp500_constituents() -> List[Dict]:
    """
    Fetch S&P 500 constituents from FMP API.

    Returns:
        List of dicts with keys: symbol, name, sector, subSector, marketCap, weight
    """
    url = f"{FMP_BASE_URL}/sp500_constituent"
    params = {"apikey": FMP_API_KEY}

    logger.info("Fetching S&P 500 constituents from FMP...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        constituents = response.json()

    logger.info(f"Fetched {len(constituents)} S&P 500 constituents")
    return constituents


def calculate_sector_weights(constituents: List[Dict]) -> Dict[str, Dict]:
    """
    Calculate sector weights from market caps.

    Args:
        constituents: List of constituent dicts with sector and marketCap

    Returns:
        Dict mapping sector -> {weight, market_cap, num_constituents}
    """
    # Group by sector
    sector_data = {}
    total_market_cap = 0

    for stock in constituents:
        sector = stock.get("sector", "Unknown")
        market_cap = float(stock.get("marketCap", 0))

        if sector not in sector_data:
            sector_data[sector] = {
                "market_cap": 0,
                "num_constituents": 0
            }

        sector_data[sector]["market_cap"] += market_cap
        sector_data[sector]["num_constituents"] += 1
        total_market_cap += market_cap

    # Calculate weights
    for sector in sector_data:
        sector_data[sector]["weight"] = sector_data[sector]["market_cap"] / total_market_cap

    logger.info(f"Calculated weights for {len(sector_data)} sectors")
    logger.info(f"Total market cap: ${total_market_cap:,.0f}")

    return sector_data


async def store_benchmark_weights(
    db,
    benchmark_code: str,
    asof_date: date,
    sector_weights: Dict[str, Dict]
) -> int:
    """
    Store benchmark sector weights in database.

    Returns:
        Number of records inserted/updated
    """
    count = 0

    for sector, data in sector_weights.items():
        # Check if record exists
        stmt = select(BenchmarkSectorWeight).where(
            and_(
                BenchmarkSectorWeight.benchmark_code == benchmark_code,
                BenchmarkSectorWeight.asof_date == asof_date,
                BenchmarkSectorWeight.sector == sector
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing record
            existing.weight = Decimal(str(data["weight"]))
            existing.market_cap = Decimal(str(data["market_cap"]))
            existing.num_constituents = data["num_constituents"]
            existing.data_source = "FMP"
            logger.info(f"Updated {sector}: {data['weight']:.4f}")
        else:
            # Insert new record
            new_weight = BenchmarkSectorWeight(
                id=uuid.uuid4(),
                benchmark_code=benchmark_code,
                asof_date=asof_date,
                sector=sector,
                weight=Decimal(str(data["weight"])),
                market_cap=Decimal(str(data["market_cap"])),
                num_constituents=data["num_constituents"],
                data_source="FMP"
            )
            db.add(new_weight)
            logger.info(f"Inserted {sector}: {data['weight']:.4f}")

        count += 1

    await db.commit()
    return count


async def main():
    """Main execution"""
    logger.info("=" * 60)
    logger.info("Starting S&P 500 Benchmark Weights Seed")
    logger.info("=" * 60)

    try:
        # Try to fetch from FMP API if key is available
        if FMP_API_KEY:
            logger.info("FMP API key found - fetching live data...")
            try:
                constituents = await fetch_sp500_constituents()
                sector_weights = calculate_sector_weights(constituents)
                data_source = "FMP"
            except Exception as e:
                logger.warning(f"FMP API fetch failed: {e}")
                logger.info("Falling back to static sector weights...")
                sector_weights = STATIC_SP500_SECTOR_WEIGHTS
                data_source = "static"
        else:
            logger.info("FMP API key not found - using static sector weights")
            sector_weights = STATIC_SP500_SECTOR_WEIGHTS
            data_source = "static"

        # Print sector breakdown
        logger.info(f"\nSector Breakdown (source: {data_source}):")
        for sector, data in sorted(sector_weights.items(), key=lambda x: x[1]["weight"], reverse=True):
            logger.info(f"  {sector:30s} {data['weight']*100:6.2f}% ({data['num_constituents']:3d} stocks)")

        # Store in database
        async with AsyncSessionLocal() as db:
            count = await store_benchmark_weights(
                db,
                benchmark_code="SP500",
                asof_date=date.today(),
                sector_weights=sector_weights
            )

        logger.info(f"\nSuccessfully seeded {count} sector weights for S&P 500")

    except Exception as e:
        logger.error(f"Error seeding benchmark weights: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
