# Testing Scripts

Comprehensive test scripts for all system components.

> **Note**: 14 completed version-specific test scripts have been archived to `../../_archive/scripts/tests/`

## Test Categories

### Authentication & Security
- **test_auth.py** - Full authentication flow testing
- **test_openai_integration.py** - OpenAI API integration tests
- **test_openai_non_streaming.py** - Non-streaming OpenAI tests

### Calculations
- **test_calculations.py** - General calculation engine tests
- **test_equity_calculations.py** - Equity-specific calculations
- **test_factor_calculations.py** - Factor analysis calculations
- **test_greeks.py** - Options Greeks calculations
- **test_correlation_analysis.py** - Correlation matrix tests
- **test_market_risk.py** - Market risk calculations

### Data & APIs
- **test_raw_data_apis.py** - Raw data API endpoints
- **test_historical_data.py** - Historical data retrieval
- **test_historical_prices.py** - Price history tests
- **test_market_data.py** - Market data service tests

### Providers
- **test_fmp_*.py** - FMP provider tests (5 files)
- **test_polygon_*.py** - Polygon provider tests (3 files)
- **test_treasury_fred_integration.py** - FRED integration tests

### System Components
- **test_database_regression.py** - Database regression tests
- **test_data_quality_monitoring.py** - Data quality checks
- **test_rate_limiting.py** - Rate limiting tests
- **test_stress_testing.py** - Stress test scenarios

### Additional Test Files (Moved from Backend Root)
- **test_correlation_api.py** - Direct correlation service API testing
- **test_correlation_debug.py** - Correlation calculation debugging
- **test_endpoints.py** - General API endpoint tests
- **test_factor_etf_tool.py** - Factor ETF tool testing
- **test_portfolio_all_info.py** - Complete portfolio information tests
- **test_stress_test_1_3_1_14.py** - Stress test scenario 1.3.1.14
- **test_stress_test_3_0_3_14.py** - Stress test scenario 3.0.3.14
- **test_stress_test_api.py** - Stress test API endpoints
- **test_stress_test_load.py** - Load stress testing
- **test_stress_test_service.py** - Stress test service layer
- **test_treasury_rates.py** - Treasury rate data tests
- **test_treasury_rates_debug.py** - Treasury rate debugging
- **test_yields_api.py** - Yield data API tests
- **testagent.py** - Agent testing utilities

## Running Tests

### Run all tests:
```bash
cd backend
for test in scripts/testing/test_*.py; do
    echo "Running $test"
    uv run python "$test"
done
```

### Run specific test:
```bash
uv run python scripts/testing/test_auth.py
```