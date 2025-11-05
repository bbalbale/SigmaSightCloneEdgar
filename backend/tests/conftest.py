"""
Pytest configuration and fixtures for test suite

Provides:
- Mock fixtures for external API services
- Pytest markers for test categorization

Note: All database tests use PostgreSQL (no SQLite).
Integration tests use the real database via AsyncSessionLocal from app.database.
"""
import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for async tests"""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================================================
# External API Mocks (YFinance, Polygon, FMP, FRED)
# ==============================================================================

@pytest.fixture
def mock_market_data_services(monkeypatch):
    """
    Mock external market data services to prevent network calls in tests.

    This fixture mocks:
    - PriceCacheService.bootstrap_prices (YFinance/FMP)
    - SecurityMasterService.enrich_symbols (FMP)

    Use this fixture in integration/E2E tests to avoid:
    - Network calls to external APIs
    - Flaky tests due to network issues
    - Slow tests
    - API rate limits

    Example usage:
        def test_portfolio_creation(client, mock_market_data_services):
            # Test runs with mocked external calls
            response = client.post("/api/v1/onboarding/create-portfolio", ...)
    """

    # Mock price cache service
    async def mock_bootstrap_prices(db, symbols, days=30):
        """Mock price cache bootstrap - returns success without API calls"""
        return {
            "symbols_fetched": len(symbols),
            "symbols_failed": 0,
            "prices_stored": len(symbols) * days,
            "date_range": {
                "start": "2024-01-01",
                "end": "2024-01-30"
            },
            "coverage_percentage": 100.0,
            "network_failure": False,
            "warnings": [],
            "recommendations": []
        }

    # Mock security master service
    async def mock_enrich_symbols(db, symbols):
        """Mock security master enrichment - returns success without API calls"""
        return {
            "symbols_enriched": len(symbols),
            "symbols_failed": 0,
            "symbols_updated": 0,
            "symbols_created": len(symbols),
            "enrichment_source": "mock",
            "warnings": [],
            "recommendations": []
        }

    # Apply mocks to singleton instances (not module-level attributes)
    from app.services.price_cache_service import price_cache_service
    from app.services.security_master_service import security_master_service

    # Mock methods on the singleton instances
    monkeypatch.setattr(
        price_cache_service,
        "bootstrap_prices",
        mock_bootstrap_prices
    )
    monkeypatch.setattr(
        security_master_service,
        "enrich_symbols",
        mock_enrich_symbols
    )

    return {
        "bootstrap_prices": mock_bootstrap_prices,
        "enrich_symbols": mock_enrich_symbols
    }


@pytest.fixture
def mock_preprocessing_service(monkeypatch):
    """
    Mock the entire preprocessing service for tests that don't need it.

    This is a higher-level mock that bypasses preprocessing entirely.
    Use when you want to test endpoints without any preprocessing logic.

    Example usage:
        def test_batch_trigger(client, mock_preprocessing_service):
            # Preprocessing is skipped entirely
            response = client.post("/api/v1/portfolio/{id}/calculate", ...)
    """

    async def mock_prepare_portfolio(portfolio_id, db):
        """Mock preprocessing - returns success immediately"""
        return {
            "symbols_count": 5,
            "security_master_enriched": 5,
            "prices_bootstrapped": 150,
            "price_coverage_percentage": 100.0,
            "ready_for_batch": True,
            "network_failure": False,
            "warnings": [],
            "recommendations": []
        }

    # Mock the singleton instance method (not module-level attribute)
    from app.services.preprocessing_service import preprocessing_service

    monkeypatch.setattr(
        preprocessing_service,
        "prepare_portfolio_for_batch",
        mock_prepare_portfolio
    )

    return mock_prepare_portfolio


@pytest.fixture
def mock_batch_orchestrator(monkeypatch):
    """
    Mock the batch orchestrator for tests that don't need batch processing.

    This prevents actual batch calculations from running in tests.
    Use when testing the trigger logic without running calculations.

    Example usage:
        def test_calculate_endpoint(client, mock_batch_orchestrator):
            # Batch doesn't actually run
            response = client.post("/api/v1/portfolio/{id}/calculate", ...)
    """

    async def mock_run_batch(calculation_date, portfolio_ids=None):
        """Mock batch run - returns success immediately"""
        return {
            "status": "completed",
            "portfolios_processed": len(portfolio_ids) if portfolio_ids else 1,
            "engines_run": 8,
            "duration_seconds": 0.1
        }

    try:
        from app.batch.batch_orchestrator import batch_orchestrator
        monkeypatch.setattr(
            batch_orchestrator,
            "run_daily_batch_sequence",
            mock_run_batch
        )
    except (ImportError, AttributeError):
        pass

    return mock_run_batch


# ==============================================================================
# Pytest Markers
# ==============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require external services (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "network: marks tests that require network access (deselect with '-m \"not network\"')"
    )
