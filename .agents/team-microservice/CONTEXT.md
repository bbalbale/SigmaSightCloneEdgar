# Team Context - Shared Knowledge

## Architecture Decisions

### Communication Pattern
- **Decision**: HTTP via Railway private networking
- **Rationale**: Simple, debuggable, no need for message queues between services
- **URL Pattern**: `http://stockfund-api.railway.internal:8000`

### Authentication
- **Decision**: Shared API key in header
- **Header**: `Authorization: Bearer {STOCKFUND_API_KEY}`
- **Key Storage**: Railway shared variables

### Error Handling Strategy
- **Decision**: Graceful degradation
- **When StockFundamentals is down**: Return error to client, don't crash
- **Future**: Fall back to Yahoo Finance (not implemented yet)

## Code Patterns to Follow

### Service Client Pattern (from existing SigmaSight code)
```python
# Services should be async, use httpx
class EdgarClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
    
    async def get_financials(self, ticker: str) -> EdgarFinancials:
        # implementation
```

### API Endpoint Pattern
```python
# Endpoints use dependency injection for services
@router.get("/edgar/financials/{ticker}")
async def get_edgar_financials(
    ticker: str,
    edgar_client: EdgarClient = Depends(get_edgar_client)
):
    return await edgar_client.get_financials(ticker)
```

## Open Questions
- Should we cache EDGAR responses in SigmaSight, or rely on StockFundamentals caching?
- How long before we make EDGAR the default over Yahoo?

## Useful Commands

### Test StockFundamentals locally
```bash
curl http://localhost:8001/health
curl http://localhost:8001/api/v1/financials/AAPL/periods
```

### Test via Railway
```bash
railway run curl http://stockfund-api.railway.internal:8000/health
```
