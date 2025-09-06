# Tool Response Truncation Configuration

## Overview
The SigmaSight chat system now includes configurable limits for tool response data sent to the LLM. This prevents token overflow while ensuring the LLM receives sufficient data for portfolio analysis.

## Configuration Options

### Environment Variables

Add these to your `.env` file to customize tool response handling:

```bash
# Tool Response Truncation Settings
# Default: 10000 chars (~2500 tokens, supports ~50 positions)
TOOL_RESPONSE_MAX_CHARS=10000

# Portfolio-specific tools get higher limits
# Default: 15000 chars (~3750 tokens, supports complex portfolios)
TOOL_RESPONSE_PORTFOLIO_MAX_CHARS=15000

# Disable all truncation (use with caution - may exceed token limits)
TOOL_RESPONSE_TRUNCATE_ENABLED=true
```

### Configuration Location
- **Config Definition**: `backend/app/config.py` (lines 70-76)
- **Implementation**: `backend/app/agent/services/openai_service.py` (lines 718-743)

## Default Values

| Setting | Default | Description |
|---------|---------|-------------|
| `TOOL_RESPONSE_MAX_CHARS` | 10,000 | Standard tools (market data, quotes, etc.) |
| `TOOL_RESPONSE_PORTFOLIO_MAX_CHARS` | 15,000 | Portfolio tools (complete data, positions) |
| `TOOL_RESPONSE_TRUNCATE_ENABLED` | true | Set to false to disable all truncation |

## Portfolio Tools (Higher Limits)
These tools automatically use `TOOL_RESPONSE_PORTFOLIO_MAX_CHARS`:
- `get_portfolio_complete`
- `get_positions_details`
- `get_portfolio_data_quality`

## Size Guidelines

### Character to Token Estimates
- 1,000 chars ≈ 250 tokens (old limit - insufficient)
- 5,000 chars ≈ 1,250 tokens (minimal portfolio support)
- 10,000 chars ≈ 2,500 tokens (standard portfolios)
- 15,000 chars ≈ 3,750 tokens (complex portfolios)

### Portfolio Size Support
- **10,000 chars**: Supports portfolios with ~50 positions
- **15,000 chars**: Supports portfolios with ~75 positions
- **20,000 chars**: Supports portfolios with ~100 positions

## Token Budget Considerations

### GPT-4 Models
- **Context Window**: 128,000 tokens
- **Safe Usage**: 15,000 chars uses only ~3% of context

### GPT-3.5 Models
- **Context Window**: 16,000 tokens  
- **Safe Usage**: 15,000 chars uses ~23% of context

## Debugging

When truncation occurs, the system logs:
```
Tool response truncated: get_portfolio_complete - 5209 chars -> 15000 chars
```

Monitor logs with:
```bash
grep "Tool response truncated" backend/logs/app.log
```

## Testing Different Limits

### Quick Test
```bash
# Test with smaller limit
export TOOL_RESPONSE_MAX_CHARS=5000
uv run python run.py

# Test with no truncation
export TOOL_RESPONSE_TRUNCATE_ENABLED=false
uv run python run.py
```

### Verify Configuration
```python
from app.config import settings
print(f"Max chars: {settings.TOOL_RESPONSE_MAX_CHARS}")
print(f"Portfolio max: {settings.TOOL_RESPONSE_PORTFOLIO_MAX_CHARS}")
print(f"Truncation enabled: {settings.TOOL_RESPONSE_TRUNCATE_ENABLED}")
```

## Common Issues and Solutions

### Issue: "Portfolio list incomplete"
**Cause**: Truncation limit too low
**Solution**: Increase `TOOL_RESPONSE_PORTFOLIO_MAX_CHARS` to 20000+

### Issue: "Token limit exceeded" errors
**Cause**: Truncation disabled or limit too high
**Solution**: Enable truncation or reduce limits

### Issue: "Missing position details"
**Cause**: Default 1000 char limit (old version)
**Solution**: Update to latest version with 10000+ default

## Migration from Old Version

If upgrading from the hardcoded 1000-char limit:

1. No action required - new defaults (10000/15000) are set automatically
2. Optionally customize via environment variables
3. Monitor logs to verify proper data flow

## Performance Impact

- **Minimal**: Character truncation is negligible (<1ms)
- **Network**: Slightly larger SSE payloads (~10-15KB vs 1KB)
- **LLM Cost**: Higher token usage but within reasonable bounds
- **Quality**: Significantly improved response accuracy with full data

## Recommendations

### For Development
```bash
TOOL_RESPONSE_MAX_CHARS=10000
TOOL_RESPONSE_PORTFOLIO_MAX_CHARS=15000
TOOL_RESPONSE_TRUNCATE_ENABLED=true
```

### For Production
```bash
TOOL_RESPONSE_MAX_CHARS=10000
TOOL_RESPONSE_PORTFOLIO_MAX_CHARS=20000  # Support larger portfolios
TOOL_RESPONSE_TRUNCATE_ENABLED=true
```

### For Testing/Debugging
```bash
TOOL_RESPONSE_TRUNCATE_ENABLED=false  # See full responses
```

## Future Enhancements

Potential improvements for consideration:
1. Smart truncation that preserves all position symbols/IDs
2. Per-tool configuration in a config file
3. Dynamic limits based on model context window
4. Compression strategies for very large portfolios
5. Pagination support for massive datasets