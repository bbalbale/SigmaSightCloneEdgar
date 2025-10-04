"""
Test script for YFinance integration with Polygon and FMP fallbacks
Tests the provider prioritization and rate limiting
"""
import asyncio
import logging
from datetime import date, timedelta
from app.services.market_data_service import market_data_service
from app.clients.factory import market_data_factory, DataType
from app.services.rate_limiter import polygon_rate_limiter, fmp_quota_tracker
from app.core.logging import get_logger
from app.database import AsyncSessionLocal

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)


async def test_yfinance_provider():
    """Test YFinance client directly"""
    print("\n" + "="*50)
    print("Testing YFinance Provider")
    print("="*50)

    try:
        # Get YFinance provider
        provider = market_data_factory.get_provider_for_data_type(DataType.STOCKS)

        if provider and provider.provider_name == "YFinance":
            print("[OK] YFinance provider initialized")

            # Test current prices
            print("\n1. Testing current stock prices...")
            symbols = ['AAPL', 'MSFT', 'GOOGL']
            prices = await provider.get_stock_prices(symbols)

            for symbol, data in prices.items():
                if data:
                    print(f"  {symbol}: ${data['price']:.2f} (change: {data['change_percent']:.2f}%)")
                else:
                    print(f"  {symbol}: No data")

            # Test historical prices
            print("\n2. Testing historical prices...")
            hist_data = await provider.get_historical_prices('AAPL', days=5)
            print(f"  Retrieved {len(hist_data)} days of historical data for AAPL")
            if hist_data and len(hist_data) > 0:
                latest = hist_data[-1]
                print(f"  Latest: {latest['date']} - Close: ${latest['close']:.2f}")

            # Test company profile
            print("\n3. Testing company profiles...")
            profiles = await provider.get_company_profile(['AAPL', 'MSFT'])
            for symbol, profile in profiles.items():
                if profile:
                    print(f"  {symbol}: {profile.get('sector')} / {profile.get('industry')}")
                else:
                    print(f"  {symbol}: No profile data")

        else:
            print("[ERROR] YFinance provider not available")

    except Exception as e:
        logger.error(f"YFinance test failed: {str(e)}")
        print(f"[ERROR] Error: {str(e)}")


async def test_provider_fallback():
    """Test provider fallback mechanism"""
    print("\n" + "="*50)
    print("Testing Provider Fallback")
    print("="*50)

    try:
        # Test with various symbol types
        symbols = [
            'AAPL',    # Regular stock - should use YFinance
            'MSFT',    # Regular stock - should use YFinance
            'SPY',     # ETF - should use YFinance
            'QQQ',     # ETF - should use YFinance
            'AAPL250117C00150000',  # Option - should use Polygon
        ]

        print("\n1. Testing fetch_historical_data_hybrid...")
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        results = await market_data_service.fetch_historical_data_hybrid(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )

        for symbol, data in results.items():
            if data:
                source = data[0].get('data_source', 'unknown') if data else 'no data'
                print(f"  {symbol}: {len(data)} records from {source}")
            else:
                print(f"  {symbol}: No data retrieved")

        print("\n2. Testing current prices fallback...")
        current_prices = await market_data_service.fetch_stock_prices_hybrid(symbols[:4])

        for symbol, price_data in current_prices.items():
            if price_data:
                provider = price_data.get('provider', 'unknown')
                print(f"  {symbol}: ${price_data['price']:.2f} from {provider}")
            else:
                print(f"  {symbol}: No price data")

    except Exception as e:
        logger.error(f"Provider fallback test failed: {str(e)}")
        print(f"[ERROR] Error: {str(e)}")


async def test_rate_limiting():
    """Test rate limiting for all providers"""
    print("\n" + "="*50)
    print("Testing Rate Limiting")
    print("="*50)

    try:
        # Test YFinance rate limiting (1 req/sec)
        print("\n1. YFinance rate limiting (1 req/sec)...")
        provider = market_data_factory.get_client('YFinance')
        if provider:
            import time
            start_time = time.time()

            # Make 3 rapid requests
            for i in range(3):
                await provider.get_stock_prices(['AAPL'])
                elapsed = time.time() - start_time
                print(f"  Request {i+1} completed at {elapsed:.2f}s")

            total_time = time.time() - start_time
            print(f"  Total time for 3 requests: {total_time:.2f}s (expected ~2s with rate limiting)")

        # Test Polygon rate limiting (5 req/min)
        print("\n2. Polygon rate limiting stats:")
        stats = polygon_rate_limiter.stats
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Average rate: {stats['average_rate']:.2f} req/s")
        print(f"  Current tokens: {stats['current_tokens']:.1f}/{polygon_rate_limiter.requests_per_minute}")

        # Test FMP quota tracking
        print("\n3. FMP quota tracking:")
        quota_stats = fmp_quota_tracker.stats
        print(f"  Calls today: {quota_stats['calls_today']}/{quota_stats['daily_limit']}")
        print(f"  Remaining: {quota_stats['remaining']}")
        print(f"  Usage: {quota_stats['quota_used_percent']:.1f}%")

    except Exception as e:
        logger.error(f"Rate limiting test failed: {str(e)}")
        print(f"[ERROR] Error: {str(e)}")


async def test_provider_status():
    """Test provider status and availability"""
    print("\n" + "="*50)
    print("Provider Status")
    print("="*50)

    try:
        # Get provider status
        status = await market_data_service.get_provider_status()

        print(f"\nProviders configured: {status['providers_configured']}")
        print(f"Providers active: {status['providers_active']}")

        print("\nProvider details:")
        for name, info in status['provider_details'].items():
            active = "[OK]" if info.get('api_key_valid') else "[ERROR]"
            print(f"  {active} {name}: {info['status']}")

        print("\nConfiguration:")
        config = status['configuration']
        print(f"  USE_YFINANCE: {config.get('use_yfinance', False)}")
        print(f"  USE_FMP_FOR_STOCKS: {config['use_fmp_for_stocks']}")
        print(f"  USE_FMP_FOR_FUNDS: {config['use_fmp_for_funds']}")
        print(f"  Polygon available: {config['polygon_available']}")
        print(f"  FMP configured: {config['fmp_configured']}")

    except Exception as e:
        logger.error(f"Provider status test failed: {str(e)}")
        print(f"[ERROR] Error: {str(e)}")


async def main():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("YFinance Integration Test Suite")
    print("="*60)

    try:
        # Initialize the factory
        market_data_factory.initialize()

        # Run tests
        await test_yfinance_provider()
        await test_provider_fallback()
        await test_rate_limiting()
        await test_provider_status()

        print("\n" + "="*60)
        print("[OK] Integration tests completed")
        print("="*60)

        print("\nSummary:")
        print("1. YFinance is now the primary provider for stocks and ETFs")
        print("2. Polygon is limited to 5 calls/minute (free tier)")
        print("3. FMP is limited to 250 calls/day")
        print("4. Fallback chain: YFinance -> Polygon -> FMP")

    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")
        print(f"\n[ERROR] Test suite failed: {str(e)}")

    finally:
        # Close all sessions
        await market_data_factory.close_all()
        await market_data_service.close()


if __name__ == "__main__":
    asyncio.run(main())