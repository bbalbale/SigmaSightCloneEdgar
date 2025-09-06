# TODO 9.18 Debug Report: get_factor_etf_prices Tool

**Date**: 2025-09-06 22:18:00 PST
**Issue**: Tool returns educational content instead of actual data

## Investigation Summary

### 1. API Endpoint Status ✅
- **Endpoint**: `/api/v1/data/factors/etf-prices`
- **Direct Test**: Returns actual data correctly
```json
{
  "data": {
    "SPY": {
      "factor_name": "Market Beta",
      "current_price": 530.0,
      ...
    }
  }
}
```

### 2. Tool Handler Status ✅
- **Handler Implementation**: EXISTS at `handlers.py:415-466`
- **Auth Test**: Works correctly with authentication token
- **Returns**: Actual data when called directly
```python
async def get_factor_etf_prices(
    self,
    lookback_days: int = 90,
    factors: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
```

### 3. Tool Registration Status ✅
- **Registry**: Tool is registered in `tool_registry.py:71`
- **OpenAI Service**: Tool definition exists in `openai_service.py:128-151`
```python
{
    "name": "get_factor_etf_prices",
    "type": "function",
    "description": "Get ETF prices for factor analysis and correlations",
    "parameters": {
        "type": "object",
        "properties": {
            "lookback_days": {
                "type": "integer",
                "description": "Days of history (max 180)",
                "default": 90
            },
            "factors": {
                "type": "string",
                "description": "Comma-separated factor names"
            }
        },
        "required": []
    }
}
```

### 4. LLM Behavior Issue ❌
**PROBLEM IDENTIFIED**: The LLM is not calling the tool when prompted

**Test Query**: "Show me factor ETF prices"

**Expected Behavior**: LLM should call `get_factor_etf_prices` tool

**Actual Behavior**: LLM responds with:
> "Could you please tell me which factor ETFs you're interested in? Common factors include value, growth, momentum, volatility, and more. Let me know so I can get the right data for you!"

## Root Cause Analysis

The issue is NOT with the tool implementation but with the LLM's decision-making:

1. **Tool Description Ambiguity**: The tool description "Get ETF prices for factor analysis and correlations" may not be clear enough for the LLM to understand it should be called for general factor ETF price requests

2. **Optional Parameters**: Both parameters are optional, but the LLM seems to think it needs user input for the `factors` parameter before calling the tool

3. **Prompt Engineering Issue**: The LLM may need clearer guidance about when to call this tool

## Recommended Fixes

### Option 1: Improve Tool Description (Recommended)
Update the tool description in `openai_service.py` to be more explicit:
```python
"description": "Get current and historical prices for factor ETFs. Call this tool when users ask about factor ETF prices, factor investing, or factor analysis. Returns market beta (SPY) by default, or specific factors if requested."
```

### Option 2: Make Tool More Directive
Add examples to the description:
```python
"description": "Get factor ETF prices. Use when: user asks 'show me factor ETF prices', 'what are factor ETFs trading at', 'factor analysis prices', etc. No parameters required - returns default factors if not specified."
```

### Option 3: Adjust System Prompt
Add guidance in the system prompt about proactively calling tools when appropriate rather than asking for clarification.

## Test Evidence

### Direct Tool Test (Working)
```bash
# With authentication
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/data/factors/etf-prices?lookback_days=30"
# Returns: Actual SPY data
```

### Handler Test (Working)
```python
tools = PortfolioTools(auth_token=token)
result = await tools.get_factor_etf_prices(lookback_days=30)
# Returns: {'data': {'SPY': {...}}, 'metadata': {...}}
```

### Chat Test (Not Working)
- User: "Show me factor ETF prices"
- LLM: Asks for clarification instead of calling tool
- No tool invocation in backend logs

## Conclusion

The `get_factor_etf_prices` tool is fully implemented and functional. The issue is that the LLM (GPT-5-mini) is not recognizing when to call the tool based on user queries. This is a prompt engineering / tool description issue, not a technical implementation problem.

## Next Steps

1. Update tool description to be more directive
2. Test with different phrasings
3. Consider adding few-shot examples to system prompt
4. Monitor if GPT-5-mini has different tool-calling behavior than GPT-4

---

*Debug session completed successfully - tool works, LLM behavior needs adjustment*