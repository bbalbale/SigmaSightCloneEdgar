import asyncio
from app.services.correlation_service import get_correlation_matrix

async def test():
    portfolio_id = "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"  # Demo Individual

    result = await get_correlation_matrix(portfolio_id)

    print(f"Available: {result.get('available')}")
    print(f"Position Symbols: {len(result.get('position_symbols', []))}")
    print(f"Correlation Matrix Rows: {len(result.get('correlation_matrix', []))}")

    if result.get('position_symbols'):
        print(f"\nFirst 5 symbols: {result['position_symbols'][:5]}")

    if result.get('correlation_matrix'):
        print(f"First row length: {len(result['correlation_matrix'][0])}")

asyncio.run(test())
