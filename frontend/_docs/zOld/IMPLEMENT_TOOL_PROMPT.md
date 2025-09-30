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

## End-to-End Testing with Playwright & Monitoring

### Setup Test Environment

1. **Start Monitoring System**:
```bash
# Terminal 1: Backend with monitoring
cd backend
uv run python run.py

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Chrome with debugging
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug &

# Terminal 4: Monitoring
cd backend
uv run python app/monitoring/chat_monitor.py
```

2. **Initialize Playwright Test Session**:
```python
# Start Playwright browser
mcp__playwright__browser_navigate(url="http://localhost:3005")

# Login to demo account
mcp__playwright__browser_type(
    element="Email input",
    ref="[name='email']",
    text="demo_hnw@sigmasight.com"
)
mcp__playwright__browser_type(
    element="Password input", 
    ref="[name='password']",
    text="demo12345"
)
mcp__playwright__browser_click(
    element="Login button",
    ref="button:has-text('Sign In')"
)

# Navigate to portfolio
mcp__playwright__browser_navigate(
    url="http://localhost:3005/portfolio?type=high-net-worth"
)

# Open chat interface
mcp__playwright__browser_click(
    element="Chat button",
    ref="button[aria-label='Open chat']"
)
```

### Tool-Specific Test Cases

For the tool being implemented (e.g., `get_prices_historical`), create these test scenarios:

#### Test Case 1: Basic Tool Discovery
```python
# Query to discover the tool
test_query = "What tools do you have for historical price data?"

# Type in chat
mcp__playwright__browser_type(
    element="Chat input",
    ref="textarea[placeholder*='Ask']",
    text=test_query
)

# Submit
mcp__playwright__browser_click(
    element="Send button",
    ref="button[aria-label='Send message']"
)

# Wait for response
mcp__playwright__browser_wait_for(text="historical", time=5)

# Capture response
mcp__playwright__browser_take_screenshot(
    filename=f"test-{TOOL_NAME}-discovery.png"
)

# Check monitoring
monitoring_data = json.load(open("backend/chat_monitoring_report.json"))
assert TOOL_NAME in str(monitoring_data["available_tools"])
```

#### Test Case 2: Tool Execution with Valid Parameters
```python
# Query using the specific tool
test_query = "[SPECIFIC QUERY FOR YOUR TOOL]"
# Example: "Show me historical prices for my portfolio for the last 30 days"

# Submit query
mcp__playwright__browser_type(
    element="Chat input",
    ref="textarea[placeholder*='Ask']",
    text=test_query
)
mcp__playwright__browser_click(
    element="Send button",
    ref="button[aria-label='Send message']"
)

# Wait for tool execution
mcp__playwright__browser_wait_for(text="[EXPECTED_RESPONSE_TEXT]", time=10)

# Verify in monitoring
monitoring_data = json.load(open("backend/chat_monitoring_report.json"))
last_conversation = monitoring_data["conversations"][-1]

# Check tool was called
assert any(msg["tool_calls"] for msg in last_conversation["messages"] 
          if "tool_calls" in msg and TOOL_NAME in str(msg["tool_calls"]))

# Verify response structure
tool_response = next(
    msg for msg in last_conversation["messages"]
    if msg.get("role") == "tool" and TOOL_NAME in msg.get("name", "")
)
assert "data" in json.loads(tool_response["content"])
assert not tool_response["content"].startswith("Error")

# Screenshot evidence
mcp__playwright__browser_take_screenshot(
    filename=f"test-{TOOL_NAME}-success.png"
)
```

#### Test Case 3: Error Handling
```python
# Test with invalid parameters
invalid_query = "[QUERY WITH INVALID PARAMS]"
# Example: "Show historical prices for invalid_portfolio_id"

mcp__playwright__browser_type(
    element="Chat input",
    ref="textarea[placeholder*='Ask']",
    text=invalid_query
)
mcp__playwright__browser_click(
    element="Send button",
    ref="button[aria-label='Send message']"
)

# Wait for error handling
mcp__playwright__browser_wait_for(text="unable", time=5)

# Verify graceful error in monitoring
monitoring_data = json.load(open("backend/chat_monitoring_report.json"))
last_message = monitoring_data["conversations"][-1]["messages"][-1]

# Should have error but be gracefully handled
assert "error" in last_message["content"].lower() or \
       "unable" in last_message["content"].lower()

mcp__playwright__browser_take_screenshot(
    filename=f"test-{TOOL_NAME}-error-handling.png"
)
```

#### Test Case 4: Performance & Response Time
```python
import time

# Measure response time
start_time = time.time()

mcp__playwright__browser_type(
    element="Chat input",
    ref="textarea[placeholder*='Ask']",
    text="[STANDARD QUERY FOR TOOL]"
)
mcp__playwright__browser_click(
    element="Send button",
    ref="button[aria-label='Send message']"
)

# Wait for complete response
mcp__playwright__browser_wait_for(text="[EXPECTED_TEXT]", time=10)

response_time = time.time() - start_time

# Check performance
assert response_time < 5.0, f"Tool took {response_time}s, expected <5s"

# Check monitoring for detailed timing
monitoring_data = json.load(open("backend/chat_monitoring_report.json"))
last_conv = monitoring_data["conversations"][-1]
print(f"Tool execution time: {last_conv.get('response_time', 'N/A')}s")
```

### Monitoring Validation

After running tests, validate using the monitoring report:

```python
# Load and analyze monitoring data
with open("backend/chat_monitoring_report.json", "r") as f:
    monitoring = json.load(f)

# Validate tool registration
assert TOOL_NAME in [t["name"] for t in monitoring["available_tools"]]

# Check tool execution in conversations
tool_executions = []
for conv in monitoring["conversations"]:
    for msg in conv["messages"]:
        if msg.get("tool_calls"):
            for call in msg["tool_calls"]:
                if call["function"]["name"] == TOOL_NAME:
                    tool_executions.append(call)

assert len(tool_executions) > 0, f"No executions of {TOOL_NAME} found"

# Validate tool responses
for execution in tool_executions:
    # Check parameters were passed correctly
    args = json.loads(execution["function"]["arguments"])
    assert all(param in args for param in REQUIRED_PARAMS)
    
    # Find corresponding tool response
    tool_response = next(
        msg for msg in conv["messages"]
        if msg["role"] == "tool" and msg["tool_call_id"] == execution["id"]
    )
    
    # Validate response format
    content = json.loads(tool_response["content"])
    if "error" not in content:
        assert "data" in content or "results" in content
        assert content != {}
```

### Test Report Generation

Generate a comprehensive test report:

```python
# Generate test report
test_report = f"""
# Tool Implementation Test Report: {TOOL_NAME}
**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Tool**: {TOOL_NAME}
**API Endpoint**: {API_ENDPOINT}

## Test Results Summary

| Test Case | Status | Response Time | Notes |
|-----------|--------|---------------|-------|
| Tool Discovery | {'✅' if discovery_passed else '❌'} | {discovery_time}s | {discovery_notes} |
| Valid Parameters | {'✅' if valid_passed else '❌'} | {valid_time}s | {valid_notes} |
| Error Handling | {'✅' if error_passed else '❌'} | {error_time}s | {error_notes} |
| Performance | {'✅' if perf_passed else '❌'} | {perf_time}s | {perf_notes} |

## Tool Execution Details

### Successful Execution
- **Query**: "{successful_query}"
- **Parameters Used**: {params_used}
- **Response Size**: {response_size} characters
- **Data Points Returned**: {data_points}

### Error Handling
- **Invalid Query**: "{error_query}"
- **Error Message**: "{error_message}"
- **Graceful Recovery**: {'Yes' if graceful else 'No'}

## Monitoring Insights
- **Total Tool Calls**: {total_calls}
- **Success Rate**: {success_rate}%
- **Average Response Time**: {avg_time}s
- **Character Count Range**: {min_chars} - {max_chars}

## Evidence
- Screenshots: `.playwright-mcp/test-{TOOL_NAME}-*.png`
- Monitoring Log: `backend/chat_monitoring_report.json`
- API Logs: Check backend console output

## Recommendations
{recommendations}

## Status
{'✅ READY FOR PRODUCTION' if all_passed else '❌ NEEDS FIXES'}
"""

# Save report
with open(f"test-report-{TOOL_NAME}-{timestamp}.md", "w") as f:
    f.write(test_report)
```

### Quick Test Command

Add this bash script for quick testing:

```bash
#!/bin/bash
# test_tool.sh - Quick test for specific tool

TOOL_NAME=$1
QUERY=$2

# Test via curl first
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo_hnw@sigmasight.com","password":"demo12345"}' | jq -r '.access_token')

# Test chat with tool
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"${QUERY}\",\"portfolio_id\":\"e23ab931-a033-edfe-ed4f-9d02474780b4\"}"

# Check monitoring
python -c "
import json
with open('chat_monitoring_report.json') as f:
    data = json.load(f)
    tools = [t['name'] for t in data.get('available_tools', [])]
    print(f'Tool {TOOL_NAME} registered: {'✅' if TOOL_NAME in tools else '❌'}')
"
```

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