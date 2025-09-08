"""
Tests for Market Data Service
"""
import pytest
import pytest_asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.market_data_service import MarketDataService, market_data_service
from app.models.market_data import MarketDataCache


class TestMarketDataService:
    """Test suite for MarketDataService"""

    @pytest.fixture
    def service(self):
        """Create a fresh MarketDataService instance for testing"""
        return MarketDataService()

    @pytest.fixture
    def mock_polygon_data(self):
        """Mock Polygon.io API response data"""
        mock_bar = Mock()
        mock_bar.timestamp = 1640995200000  # 2022-01-01
        mock_bar.open = 100.0
        mock_bar.high = 105.0
        mock_bar.low = 99.0
        mock_bar.close = 104.0
        mock_bar.volume = 1000000
        return [mock_bar]

    @pytest.fixture
    def mock_yfinance_data(self):
        """Mock YFinance ticker info response"""
        return {
            'sector': 'Technology',
            'industry': 'Software—Infrastructure'
        }

    @pytest.mark.asyncio
    async def test_fetch_stock_prices_success(self, service, mock_polygon_data):
        """Test successful stock price fetching"""
        with patch.object(service.polygon_client, 'get_aggs', return_value=mock_polygon_data):
            result = await service.fetch_stock_prices(['AAPL'])
            
            assert 'AAPL' in result
            assert len(result['AAPL']) == 1
            
            price_data = result['AAPL'][0]
            assert price_data['symbol'] == 'AAPL'
            assert price_data['close'] == Decimal('104.0')
            assert price_data['volume'] == 1000000
            assert price_data['data_source'] == 'polygon'

    @pytest.mark.asyncio
    async def test_fetch_stock_prices_api_error(self, service):
        """Test stock price fetching with API error"""
        with patch.object(service.polygon_client, 'get_aggs', side_effect=Exception("API Error")):
            result = await service.fetch_stock_prices(['AAPL'])
            
            assert 'AAPL' in result
            assert result['AAPL'] == []

    @pytest.mark.asyncio
    async def test_fetch_current_prices_success(self, service):
        """Test successful current price fetching"""
        mock_trade = Mock()
        mock_trade.price = 105.50
        
        with patch.object(service.polygon_client, 'get_last_trade', return_value=mock_trade):
            result = await service.fetch_current_prices(['AAPL'])
            
            assert 'AAPL' in result
            assert result['AAPL'] == Decimal('105.50')

    @pytest.mark.asyncio
    async def test_fetch_gics_data_success(self, service, mock_yfinance_data):
        """Test successful GICS data fetching"""
        pytest.skip("GICS data temporarily disabled; yfinance not used in current implementation.")

    @pytest.mark.asyncio
    async def test_fetch_options_chain_success(self, service):
        """Test successful options chain fetching"""
        mock_contract = Mock()
        mock_contract.ticker = 'AAPL220121C00150000'
        mock_contract.underlying_ticker = 'AAPL'
        mock_contract.expiration_date = '2022-01-21'
        mock_contract.strike_price = 150.0
        mock_contract.contract_type = 'call'
        
        with patch.object(service.polygon_client, 'list_options_contracts', return_value=[mock_contract]):
            result = await service.fetch_options_chain('AAPL')
            
            assert len(result) == 1
            option = result[0]
            assert option['ticker'] == 'AAPL220121C00150000'
            assert option['underlying_ticker'] == 'AAPL'
            assert option['contract_type'] == 'call'
            assert option['strike_price'] == Decimal('150.0')

    @pytest.mark.asyncio
    async def test_get_cached_prices(self, service):
        """Test getting cached prices from database"""
        # Mock database session and query results
        mock_db = AsyncMock(spec=AsyncSession)
        mock_record = Mock()
        mock_record.symbol = 'AAPL'
        mock_record.close = Decimal('104.0')
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        mock_db.execute.return_value = mock_result
        
        result = await service.get_cached_prices(mock_db, ['AAPL'])
        
        assert 'AAPL' in result
        assert result['AAPL'] == Decimal('104.0')


@pytest.mark.integration
class TestMarketDataServiceIntegration:
    """Integration tests requiring real API keys and database"""
    
    @pytest.mark.asyncio
    async def test_real_polygon_api_call(self):
        """Test real Polygon.io API call (requires API key)"""
        # Skip if no API key
        from app.config import settings
        if not settings.POLYGON_API_KEY or settings.POLYGON_API_KEY == 'your_polygon_api_key_here':
            pytest.skip("No Polygon API key configured")
        
        service = MarketDataService()
        result = await service.fetch_stock_prices(['AAPL'], 
                                                start_date=date.today() - timedelta(days=2),
                                                end_date=date.today())
        
        assert 'AAPL' in result
        assert len(result['AAPL']) >= 0  # May be 0 on weekends/holidays

    @pytest.mark.asyncio
    async def test_real_yfinance_api_call(self):
        """Test real YFinance API call"""
        pytest.skip("GICS data temporarily disabled; yfinance not used in current implementation.")


class TestMarketDataEndpoints:
    """Test market data API endpoints"""
    
    @pytest.mark.skip(reason="/api/v1/market-data routes unregistered in v1.2")
    def test_price_data_endpoint_unauthorized(self):
        """Test price data endpoint without authentication"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/market-data/prices/AAPL")
        
        # Should require authentication
        assert response.status_code == 401

    @pytest.mark.skip(reason="/api/v1/market-data routes unregistered in v1.2")
    def test_current_prices_endpoint_unauthorized(self):
        """Test current prices endpoint without authentication"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/api/v1/market-data/current-prices?symbols=AAPL&symbols=MSFT")
        
        # Should require authentication
        assert response.status_code == 401


# Manual testing helpers for development
class ManualTestHelpers:
    """Helper functions for manual testing during development"""
    
    @staticmethod
    async def test_service_manually():
        """Manual test function for development debugging"""
        print("Testing MarketDataService manually...")
        
        service = MarketDataService()
        
        # Test current prices
        print("\n1. Testing current prices...")
        try:
            prices = await service.fetch_current_prices(['AAPL', 'MSFT'])
            print(f"Current prices: {prices}")
        except Exception as e:
            print(f"Current prices error: {e}")
        
        # Test GICS data
        print("\n2. Testing GICS data...")
        try:
            gics = await service.fetch_gics_data(['AAPL'])
            print(f"GICS data: {gics}")
        except Exception as e:
            print(f"GICS error: {e}")
        
        # Test historical data
        print("\n3. Testing historical data...")
        try:
            historical = await service.fetch_stock_prices(
                ['AAPL'], 
                start_date=date.today() - timedelta(days=5)
            )
            print(f"Historical data points: {len(historical.get('AAPL', []))}")
        except Exception as e:
            print(f"Historical data error: {e}")

    @staticmethod
    async def test_batch_sync_manually():
        """Manual test for batch sync functionality"""
        print("Testing batch sync manually...")
        
        from app.batch.market_data_sync import sync_market_data
        
        try:
            result = await sync_market_data()
            print(f"Batch sync result: {result}")
        except Exception as e:
            print(f"Batch sync error: {e}")


if __name__ == "__main__":
    # Run manual tests for development
    import asyncio
    
    async def run_manual_tests():
        await ManualTestHelpers.test_service_manually()
        print("\n" + "="*50)
        await ManualTestHelpers.test_batch_sync_manually()
    
    asyncio.run(run_manual_tests())
