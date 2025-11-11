#!/usr/bin/env python
"""Test the correlation matrix API endpoint"""

import asyncio
import json
from app.services.correlation_service import CorrelationService
from app.database import get_async_session
from uuid import UUID

async def test_correlation_api():
    """Test the correlation service directly"""
    
    # Portfolio with known correlation data
    portfolio_id = UUID("fcd71196-e93e-f000-5a74-31a9eead3118")
    
    async with get_async_session() as db:
        service = CorrelationService(db)
        
        print("Testing correlation matrix retrieval...")
        result = await service.get_matrix(
            portfolio_id=portfolio_id,
            lookback_days=90,
            min_overlap=30
        )
        
        # Pretty print the result
        print(json.dumps(result, indent=2, default=str))
        
        if "data" in result and result["data"].get("matrix"):
            matrix = result["data"]["matrix"]
            symbols = list(matrix.keys())
            print(f"\nFound correlations for {len(symbols)} symbols")
            print(f"Symbols: {', '.join(symbols[:5])}...")
            print(f"Average correlation: {result['data'].get('average_correlation')}")
        elif result.get("available") is False:
            print(f"\nNo data available: {result.get('metadata', {}).get('message')}")

if __name__ == "__main__":
    asyncio.run(test_correlation_api())