#!/usr/bin/env python
"""Debug the correlation service to find the exact error"""

import asyncio
from uuid import UUID
from app.services.correlation_service import CorrelationService
from app.database import get_async_session

async def test_correlation_service():
    """Test the correlation service directly"""
    portfolio_id = UUID("1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe")
    
    async with get_async_session() as db:
        service = CorrelationService(db)
        
        try:
            print(f"Testing get_matrix for portfolio {portfolio_id}")
            result = await service.get_matrix(
                portfolio_id=portfolio_id,
                lookback_days=90,
                min_overlap=30,
                max_symbols=25
            )
            
            if result.get("available"):
                data = result.get("data", {})
                matrix = data.get("matrix", {})
                print(f"✅ Success! Got matrix with {len(matrix)} symbols")
                if matrix:
                    symbols = list(matrix.keys())
                    print(f"Symbols: {', '.join(symbols[:5])}...")
            else:
                print(f"⚠️ No data available: {result.get('metadata', {})}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_correlation_service())