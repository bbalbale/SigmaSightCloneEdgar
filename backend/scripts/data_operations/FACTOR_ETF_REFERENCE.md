# Factor ETF Reference

> **Last Updated**: 2025-09-11  
> **Important Change**: SIZE factor switched from SLY to IWM due to data availability

## Available Factor ETFs in SigmaSight

The system currently tracks the following factor ETFs for factor analysis and portfolio risk decomposition:

| Ticker | Factor Name | Description |
|--------|-------------|-------------|
| **SPY** | Market Beta | S&P 500 Index - Market factor/systematic risk |
| **VTV** | Value Factor | Vanguard Value ETF - Exposure to value stocks |
| **VUG** | Growth Factor | Vanguard Growth ETF - Exposure to growth stocks |
| **MTUM** | Momentum Factor | iShares Momentum Factor ETF - High momentum stocks |
| **QUAL** | Quality Factor | iShares Quality Factor ETF - High quality fundamentals |
| **IWM** | Size Factor | iShares Russell 2000 ETF - Small cap exposure (Changed from SLY) |
| **USMV** | Low Volatility | iShares Min Vol USA ETF - Low volatility stocks |

## Implementation Details

### Tool Update (2025-09-06)
- **Issue**: LLM was not calling `get_factor_etf_prices` tool when prompted
- **Root Cause**: Tool description was too vague
- **Fix**: Updated tool description in `openai_service.py` to be more directive and include available factors

### API Endpoint
- **Path**: `/api/v1/data/factors/etf-prices`
- **Authentication**: Required (Bearer token)
- **Parameters**:
  - `lookback_days`: Number of days of historical data (max 180, default 90)
  - `factors`: Comma-separated list of factor names (optional)

### Tool Handler
- **Location**: `app/agent/tools/handlers.py:415-466`
- **Method**: `get_factor_etf_prices()`
- **Returns**: Price data with metadata including factor names

### Current Data Status
- Currently returns seed/mock data for development
- SPY is the primary factor ETF with available data
- Other factors may have limited or mock data

## Usage Examples

### Chat Queries That Should Trigger Tool
- "Show me factor ETF prices"
- "What are the factor ETFs trading at?"
- "Get factor analysis prices"
- "Show me SPY and VTV prices"
- "What's the current price of momentum factor ETF?"
- "Factor investing prices"

### Expected Response
When the tool is called correctly, it returns:
```json
{
  "data": {
    "SPY": {
      "factor_name": "Market Beta",
      "symbol": "SPY",
      "current_price": 530.0,
      "open": 527.35,
      "high": 532.65,
      "low": 524.7,
      "volume": 1000000,
      "date": "2025-09-05"
    }
  },
  "metadata": {
    "factor_model": "7-factor",
    "etf_count": 1,
    "lookback_days": 30
  }
}
```

## SIZE Factor Change History (2025-09-11)

### Why We Switched from SLY to IWM
- **Problem**: SLY (SPDR S&P 600 Small Cap) had stale data - last update was 820+ days old (2022-2023)
- **Solution**: Switched to IWM (iShares Russell 2000) which has current, reliable data
- **Benefits**: 
  - IWM has 180+ days of fresh historical data
  - Better liquidity and data coverage from providers
  - More widely used small-cap benchmark (Russell 2000 vs S&P 600)
  - Successfully tested with all 3 demo portfolios

### Implementation Files Updated
- `app/constants/factors.py` - Changed FACTOR_ETFS mapping
- `app/services/market_data_sync.py` - Updated ETF list
- `scripts/data_operations/fetch_factor_etf_data.py` - Unified fetching script

## Notes
- IWM is now the primary SIZE factor ETF (replaced SLY)
- BRK.B/BRK-B issue: Different format requirements across data providers
- All factor ETFs are validated for FMP (Financial Modeling Prep) API coverage
- 7 active factors working (Short Interest factor disabled - no ETF proxy)