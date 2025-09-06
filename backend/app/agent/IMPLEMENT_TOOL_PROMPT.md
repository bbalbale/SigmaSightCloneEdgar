# Tool Implementation Prompt Template

Use this prompt template when implementing a new tool handler for an existing API endpoint. This standardized approach ensures consistent tool implementation across the agent system.

## Prerequisites Checklist
Before using this prompt, ensure you have:
- [ ] API endpoint path and method (e.g., GET /api/v1/data/prices/historical/{portfolio_id})
- [ ] API documentation or specification
- [ ] Required parameters and their types
- [ ] Expected response structure
- [ ] Authentication requirements (JWT, portfolio context, etc.)
- [ ] Any business logic or data transformation needs

## Prompt Template

---

### Task: Implement Tool Handler for [TOOL_NAME]

I need to implement a tool handler that provides access to an existing API endpoint. Please create a complete, production-ready implementation following the established patterns in this codebase.

**Tool Details:**
- **Tool Name**: `[TOOL_NAME]` (e.g., get_prices_historical)
- **Description**: [Brief description of what the tool does]
- **API Endpoint**: `[METHOD] [ENDPOINT_PATH]` 
- **Purpose**: [Business purpose and use cases]

**API Specification:**
```
Endpoint: [FULL_ENDPOINT_PATH]
Method: [HTTP_METHOD]
Authentication: [Bearer JWT / Portfolio Context / etc.]

Parameters:
- [param_name]: [type] - [required/optional] - [description]
- [param_name]: [type] - [required/optional] - [description]

Example Request:
[EXAMPLE_API_REQUEST]

Example Response:
[EXAMPLE_API_RESPONSE_JSON]
```

**Implementation Requirements:**

1. **Verify API First** - Before implementing, verify the API works:
```bash
# Test the API endpoint directly
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' | jq -r '.access_token')

curl -X [METHOD] "http://localhost:8000[ENDPOINT_PATH]" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"
```

2. **Add Tool Handler Method** in `app/agent/tools/handlers.py`:
- Follow the existing async pattern
- Include proper error handling and retry logic
- Add parameter validation
- Include business logic for data transformation
- Log important operations

3. **Register Tool** in `app/agent/tools/tool_registry.py`:
- Add to the tools list with proper schema
- Include all required and optional parameters
- Add clear descriptions for LLM understanding

4. **Update OpenAI Service** in `app/agent/services/openai_service.py`:
- Add to `_get_tool_definitions_responses()` method
- Include complete parameter schema
- Ensure tool name matches registration

5. **Add Tests** in `tests/test_tool_handlers.py`:
- Unit test for the handler method
- Integration test with mock API response
- Error handling test cases
- Parameter validation tests

**Specific Implementation Constraints:**
- [Any specific business rules]
- [Data transformation requirements]
- [Performance considerations]
- [Error handling requirements]

**Context from Existing Codebase:**

Current tool implementation pattern from `handlers.py`:
```python
async def get_portfolio_complete(
    self,
    portfolio_id: str,
    include_holdings: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """[Implementation pattern example]"""
    try:
        params = {...}
        endpoint = f"/api/v1/data/portfolio/{portfolio_id}/complete"
        response = await self._make_request("GET", endpoint, params)
        # Business logic here
        return response
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e), "retryable": isinstance(e, ...)}
```

Please provide:
1. Complete handler method implementation
2. Tool registry entry
3. OpenAI service tool definition
4. Basic test cases
5. Any necessary imports or dependencies

---

## Usage Instructions

1. **Fill in the template** with specific details for your tool
2. **Verify the API** works using the curl commands
3. **Submit to Claude** with the filled template
4. **Review implementation** for:
   - Consistency with existing patterns
   - Proper error handling
   - Complete parameter validation
   - Appropriate logging
5. **Test thoroughly** before committing

## Common Tool Patterns

### Pattern 1: Data Retrieval Tool
```python
async def get_[resource]_[action](
    self,
    portfolio_id: str,
    [other_params],
    **kwargs
) -> Dict[str, Any]:
    """Get [resource] with [action]"""
    # Validate parameters
    # Build request
    # Make API call
    # Transform data if needed
    # Return standardized response
```

### Pattern 2: Calculation Tool
```python
async def calculate_[metric](
    self,
    portfolio_id: str,
    [calculation_params],
    **kwargs
) -> Dict[str, Any]:
    """Calculate [metric] for portfolio"""
    # Fetch required data
    # Perform calculations
    # Format results
    # Return with metadata
```

### Pattern 3: Action Tool
```python
async def [action]_[resource](
    self,
    [resource_id]: str,
    [action_params],
    **kwargs
) -> Dict[str, Any]:
    """Perform [action] on [resource]"""
    # Validate permissions
    # Prepare action data
    # Execute action
    # Return confirmation/results
```

## Response Format Standards

All tools should return consistent response structures:

### Success Response
```python
{
    "data": {...},  # Actual response data
    "meta": {
        "as_of": "2025-09-06T12:00:00Z",
        "rows_returned": 10,
        "truncated": False,
        "parameters_used": {...}
    }
}
```

### Error Response
```python
{
    "error": "Error message",
    "error_type": "validation|api|network|data",
    "retryable": True/False,
    "details": {...}  # Optional additional context
}
```

## Testing Checklist

After implementation, verify:
- [ ] API endpoint is accessible
- [ ] Tool appears in available tools list
- [ ] LLM can discover and call the tool
- [ ] Parameters are validated correctly
- [ ] Errors are handled gracefully
- [ ] Response format matches specification
- [ ] Performance is acceptable (<1s for most operations)
- [ ] Logging provides debugging information

## Example TODO Entry

When documenting in TODO files, use this format:
```markdown
### TODO 9.17: Implement get_prices_historical Tool Handler
**Status**: 🔄 In Progress
**API**: GET /api/v1/data/prices/historical/{portfolio_id}
**Purpose**: Retrieve historical price data for portfolio positions
**Implementation**: Use IMPLEMENT_TOOL_PROMPT.md with:
- Tool name: get_prices_historical
- Parameters: portfolio_id, lookback_days, max_symbols
- Returns: Historical OHLCV data for positions
**Priority**: High - Blocks historical analysis features
```

## Notes

- Always verify the API works before implementing the tool
- Follow existing patterns for consistency
- Include comprehensive error handling
- Test with actual demo data
- Document any deviations from standard patterns
- Update this template with new patterns discovered