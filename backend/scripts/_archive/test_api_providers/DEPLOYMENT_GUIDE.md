# Section 1.4.9 Market Data Migration - Deployment Guide

## Overview
This guide covers the deployment of the hybrid market data provider system implemented in Section 1.4.9, which adds support for mutual fund holdings data through FMP (Financial Modeling Prep) and TradeFeeds providers.

## Architecture Summary
- **Primary Provider**: Financial Modeling Prep (FMP) - $139/month, unlimited API calls
- **Backup Provider**: TradeFeeds - $149/month, 22,000 credits (with 20X multiplier for fund/ETF calls)
- **Options Provider**: Polygon.io - $29/month, existing integration maintained
- **Database**: New `FundHoldings` model for mutual fund and ETF holdings data

## Pre-Deployment Checklist

### 1. API Provider Setup
1. **Sign up for Financial Modeling Prep Ultimate Plan**
   - Visit: https://financialmodelingprep.com/developer/docs
   - Plan: Ultimate ($139/month) - provides unlimited API calls
   - Required endpoints: `stock/real-time-price`, `v3/mutual-fund-holdings/{symbol}`
   - Test API key with sample requests

2. **Sign up for TradeFeeds (Backup Provider)**
   - Visit: https://tradefeeds.com
   - Plan: Professional ($149/month) - provides 22,000 credits
   - Note: Fund/ETF calls cost 20 credits each (expensive for high volume)
   - Required for fallback scenarios and testing

### 2. Environment Configuration
Add the following environment variables to your `.env` file:

```bash
# Financial Modeling Prep Configuration
FMP_API_KEY=your_fmp_api_key_here
FMP_TIMEOUT_SECONDS=30
FMP_MAX_RETRIES=3

# TradeFeeds Configuration (Backup)
TRADEFEEDS_API_KEY=your_tradefeeds_api_key_here
TRADEFEEDS_TIMEOUT_SECONDS=30
TRADEFEEDS_MAX_RETRIES=3
TRADEFEEDS_RATE_LIMIT=30

# Existing Polygon configuration (unchanged)
POLYGON_API_KEY=your_existing_polygon_key
```

### 3. Database Migration
The `FundHoldings` model is already integrated into the main database initialization:

```bash
# Initialize database with new FundHoldings table
uv run python scripts/init_database.py
```

Verify the table was created:
```sql
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'fund_holdings';
```

### 4. Dependency Installation
Ensure `aiohttp` dependency is installed (already added to `pyproject.toml`):

```bash
uv sync
```

## Deployment Steps

### 1. Code Deployment
All implementation files are already in place:
- `app/config.py` - Provider API configurations
- `app/clients/` - Complete client implementation directory
- `app/services/market_data_service.py` - Hybrid routing methods
- `app/models/market_data.py` - FundHoldings model
- `scripts/test_api_providers/` - Testing and validation scripts

### 2. Validation Testing
Run the integration test suite to verify deployment:

```bash
# Test all components
uv run python scripts/test_api_providers/integration_test.py

# Test client imports and basic functionality
uv run python scripts/test_api_providers/test_client_imports.py

# Run scenario testing (requires API keys)
uv run python scripts/test_api_providers/test_scenarios.py
```

Expected output for successful deployment:
```
🎯 Section 1.4.9 Integration: ✅ READY
Total Tests: 5
Passed: ✅ 5
Success Rate: 100.0%
```

### 3. Production Verification
Test with sample mutual fund symbols:
```bash
# Test FMP provider
curl -X GET "https://financialmodelingprep.com/api/v3/mutual-fund-holdings/FXNAX?apikey=YOUR_FMP_KEY"

# Verify holdings data format matches expected schema
```

## Usage Examples

### API Integration
The hybrid providers are integrated into the existing market data service:

```python
from app.services.market_data_service import market_data_service

# Fetch mutual fund holdings (uses FMP as primary)
holdings = await market_data_service.fetch_mutual_fund_holdings("FXNAX")

# Fetch ETF holdings  
etf_holdings = await market_data_service.fetch_etf_holdings("VTI")

# Hybrid stock prices (uses FMP → TradeFeeds → Polygon fallback)
prices = await market_data_service.fetch_stock_prices_hybrid(["AAPL", "MSFT"])
```

### Direct Client Usage
```python
from app.clients import market_data_factory

# Create FMP client
fmp_client = market_data_factory.create_client('FMP', api_key=settings.FMP_API_KEY)

# Fetch fund holdings
holdings = await fmp_client.get_fund_holdings("FXNAX")

# Always close clients when done
await fmp_client.close()
```

## Monitoring & Maintenance

### 1. Cost Monitoring
- **FMP**: $99/month flat rate, unlimited calls
- **TradeFeeds**: $149/month, monitor credit usage (20X for funds)
- **Total Expected Cost**: $128/month (FMP + Polygon only)

### 2. API Monitoring
Monitor these key metrics:
- FMP API response times and error rates
- TradeFeeds credit usage and rate limiting
- Fund holdings data freshness (daily updates)
- Fallback provider activation frequency

### 3. Data Quality Checks
- Verify fund holdings weights sum to 90-100% per fund
- Monitor for missing or stale holdings data
- Track provider data quality scores

## Troubleshooting

### Common Issues

**1. API Key Configuration Errors**
```
Error: FMP_API_KEY not configured
```
Solution: Verify environment variables are set and restart the application.

**2. Rate Limiting**
```
Error: Rate limit exceeded for TradeFeeds
```
Solution: The client automatically handles rate limiting with exponential backoff.

**3. Missing Dependencies**
```
ModuleNotFoundError: No module named 'aiohttp'
```
Solution: Run `uv sync` to install all dependencies.

**4. Database Migration Issues**
```
Error: relation "fund_holdings" does not exist
```
Solution: Run `uv run python scripts/init_database.py` to create missing tables.

### Rollback Plan
If issues occur, the system gracefully degrades:
1. Remove API keys from environment to disable new providers
2. System automatically falls back to existing Polygon integration
3. No changes required to existing functionality

## Performance Optimization

### 1. Caching Strategy
- Fund holdings data cached for 24 hours (daily refresh)
- Stock prices cached according to existing market data cache settings
- Provider response caching handled automatically

### 2. Request Optimization
- Batch stock price requests when possible
- Rate limiting built into clients prevents API quota exhaustion
- Automatic retry with exponential backoff for failed requests

## Security Considerations

### API Key Management
- Store API keys in secure environment variables only
- Never commit API keys to version control
- Use separate keys for development/staging/production environments
- Regularly rotate API keys following provider recommendations

### Request Validation
- All API responses validated against expected schemas
- Input sanitization for symbol parameters
- Error handling prevents sensitive information leakage

## Next Steps

### 1. Provider Trial Setup
- Activate FMP and TradeFeeds trial accounts
- Configure API keys in production environment
- Run validation tests with real API keys

### 2. Performance Monitoring
- Set up monitoring dashboards for API performance
- Configure alerts for provider failures
- Track cost metrics and usage patterns

### 3. Future Enhancements
- Add additional provider support if needed
- Implement advanced caching strategies
- Add automated provider performance comparison reports

## Support & Documentation

- **Implementation Code**: `app/clients/` directory
- **Testing Scripts**: `scripts/test_api_providers/` directory  
- **Configuration**: `app/config.py` for all provider settings
- **Database Models**: `app/models/market_data.py` for FundHoldings schema

For technical support, run the integration test suite and check the generated error logs for specific troubleshooting guidance.