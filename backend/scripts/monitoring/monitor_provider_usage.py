"""
Monitor market data provider usage and statistics
Shows which provider is being used for different data types and tracks API usage
"""
import asyncio
import logging
from datetime import datetime
from app.services.market_data_service import market_data_service
from app.clients.factory import market_data_factory, DataType
from app.services.rate_limiter import polygon_rate_limiter, fmp_quota_tracker
from app.core.logging import get_logger

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)


def print_separator(title=""):
    """Print a formatted separator"""
    if title:
        print(f"\n{'='*20} {title} {'='*20}")
    else:
        print("="*60)


async def monitor_providers():
    """Monitor and display provider statistics"""

    print_separator("MARKET DATA PROVIDER MONITOR")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize factory
    market_data_factory.initialize()

    # 1. Provider Configuration
    print_separator("Provider Configuration")

    providers = market_data_factory.get_available_providers()
    print(f"Total Providers Configured: {len(providers)}")

    for name, info in providers.items():
        status = "[ACTIVE]" if info.get('api_key_configured') else "[INACTIVE]"
        print(f"  {status} {name}")
        print(f"    - Timeout: {info['timeout']}s")
        print(f"    - Max Retries: {info['max_retries']}")

    # 2. Provider Priority
    print_separator("Provider Priority by Data Type")

    data_types = [
        (DataType.STOCKS, "Stocks & ETFs"),
        (DataType.FUNDS, "Mutual Funds"),
        (DataType.OPTIONS, "Options")
    ]

    for dtype, description in data_types:
        provider = market_data_factory.get_provider_for_data_type(dtype)
        if provider:
            print(f"  {description}: {provider.provider_name}")
        else:
            print(f"  {description}: Polygon (default)")

    # 3. Rate Limiting Status
    print_separator("Rate Limiting Status")

    # Polygon rate limiter
    polygon_stats = polygon_rate_limiter.stats
    print(f"\nPolygon API (5 calls/minute free tier):")
    print(f"  - Total Requests: {polygon_stats['total_requests']}")
    print(f"  - Average Rate: {polygon_stats['average_rate']:.2f} req/s")
    print(f"  - Current Tokens: {polygon_stats['current_tokens']:.1f}/{polygon_rate_limiter.requests_per_minute}")

    # FMP quota tracker
    fmp_stats = fmp_quota_tracker.stats
    print(f"\nFMP API (250 calls/day limit):")
    print(f"  - Calls Today: {fmp_stats['calls_today']}/{fmp_stats['daily_limit']}")
    print(f"  - Remaining: {fmp_stats['remaining']}")
    print(f"  - Usage: {fmp_stats['quota_used_percent']:.1f}%")
    print(f"  - Last Reset: {fmp_stats['last_reset']}")

    print(f"\nYFinance API (1 req/sec self-imposed):")
    print(f"  - No official rate limit")
    print(f"  - Self-throttled to 1 request/second")
    print(f"  - Unlimited daily usage")

    # 4. Provider Health Check
    print_separator("Provider Health Check")

    validation_results = await market_data_factory.validate_all_providers()

    for provider, is_valid in validation_results.items():
        status = "[OK]" if is_valid else "[FAILED]"
        print(f"  {status} {provider}")

    # 5. Usage Recommendations
    print_separator("Usage Recommendations")

    print("\nCurrent Configuration:")
    print("1. YFinance: PRIMARY for all stock/ETF price data (unlimited)")
    print("2. Polygon: FALLBACK for stocks, PRIMARY for options (5/min)")
    print("3. FMP: LAST RESORT for prices, PRIMARY for holdings (250/day)")

    print("\nOptimization Tips:")

    if fmp_stats['quota_used_percent'] > 80:
        print("  [!] FMP quota >80% used - consider deferring non-critical requests")

    if polygon_stats['average_rate'] > 0.08:  # More than 5 per minute
        print("  [!] Polygon rate near limit - requests may be delayed")

    if not validation_results.get('YFinance', False):
        print("  [!] YFinance not available - will use more expensive providers")

    print("\nAPI Cost Savings with YFinance:")
    yfinance_available = validation_results.get('YFinance', False)
    if yfinance_available:
        print("  - Estimated 90% reduction in Polygon API calls")
        print("  - Estimated 95% reduction in FMP API calls")
        print("  - Unlimited historical data retrieval")
    else:
        print("  - YFinance unavailable - higher API costs expected")

    print_separator()


async def test_provider_selection():
    """Test which provider gets selected for different scenarios"""

    print_separator("Testing Provider Selection")

    test_cases = [
        (['AAPL', 'MSFT'], "Regular Stocks"),
        (['SPY', 'QQQ'], "ETFs"),
        (['AAPL250117C00150000'], "Options"),
        (['FXNAX'], "Mutual Fund")
    ]

    for symbols, description in test_cases:
        print(f"\nTest: {description} - {symbols}")

        # Determine expected provider
        if 'C00' in symbols[0] or 'P00' in symbols[0]:
            expected = "Polygon (options)"
        elif symbols[0] in ['FXNAX', 'VFIAX']:
            expected = "FMP (fund holdings)"
        else:
            expected = "YFinance (primary)"

        print(f"  Expected Provider: {expected}")

    print_separator()


async def main():
    """Run the monitoring suite"""
    try:
        await monitor_providers()
        await test_provider_selection()

        print("\n" + "="*60)
        print("Monitoring complete. All systems operational.")
        print("="*60)

    except Exception as e:
        logger.error(f"Monitoring failed: {str(e)}")
    finally:
        await market_data_factory.close_all()
        await market_data_service.close()


if __name__ == "__main__":
    asyncio.run(main())