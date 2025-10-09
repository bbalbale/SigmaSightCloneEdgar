# AI Chat Portfolio Data Debugging Plan

**Date**: October 9, 2025
**Issue**: Chat interface may not be sending portfolio holdings/details properly
**Status**: ✅ RESOLVED - October 9, 2025

---

## 🎉 RESOLUTION SUMMARY

**Issue**: Agent was not referencing actual portfolio holdings in responses
**Root Cause #1**: System prompt didn't explicitly instruct agent to USE portfolio_context data
**Root Cause #2**: Stale conversation IDs in localStorage caused 404 errors

**Fixes Applied**:
1. ✅ Enhanced system prompt with explicit portfolio data usage instructions
2. ✅ Added detailed logging to verify portfolio context structure
3. ✅ Implemented automatic stale conversation ID cleanup

**Result**: Agent now provides SPECIFIC responses with:
- Actual position symbols
- Equity values and percentages
- Position counts
- Real portfolio data

**Verified**: October 9, 2025 - Agent successfully references portfolio holdings

---

## ✅ FIXES IMPLEMENTED (October 9, 2025)

### Fix #1: Enhanced System Prompt ✅ COMPLETED
**File**: `backend/app/agent/prompts/common_instructions.md`

Added explicit instructions (lines 85-108) instructing the agent to:
- Reference actual holdings from portfolio_context
- Be specific with symbols and values
- Never give generic advice when data is available
- Examples of GOOD vs BAD responses
- Instructions for handling missing data

**Key Addition**:
```markdown
### CRITICAL: Using Portfolio Data in Responses

**YOU HAVE DIRECT ACCESS TO THE USER'S PORTFOLIO DATA ABOVE.**

When answering questions about the portfolio, you MUST:
1. Reference actual holdings - Mention specific symbols, quantities, values
2. Be specific - Use exact numbers from the holdings
3. Never give generic advice - You have real data, don't say "check your dashboard"
4. Cite the data - Always base answers on the holdings listed above
```

### Fix #2: Enhanced Logging ✅ COMPLETED
**File**: `backend/app/api/v1/chat/send.py` (lines 154-173)

Added detailed logging to verify portfolio context structure:
- Portfolio summary (ID, name, value, holdings count)
- Sample holding for verification
- Warning if holdings list is empty

**Benefits**:
- Can now verify exact data being passed to agent
- Can diagnose if holdings are empty or malformed
- Clear visibility into portfolio context flow

---

## Investigation Summary

After thorough code review, I've identified that **portfolio data IS being sent to the agent**, but there may be issues in HOW it's being used or presented. Here's what I found:

---

## Current Data Flow (CONFIRMED WORKING)

### 1. Frontend: Portfolio ID Capture ✅
**File**: `frontend/src/containers/AIChatContainer.tsx`
- Line 15: `const portfolioId = usePortfolioStore((state) => state.portfolioId)`
- Portfolio ID is retrieved from Zustand store
- Passed to conversation creation

### 2. Frontend: Conversation Creation ✅
**File**: `frontend/src/services/chatService.ts`
- Lines 146-153: `createConversation()` method
- Portfolio ID is added to request payload as `portfolio_id`
- Sent to backend: `POST /api/proxy/api/v1/chat/conversations`

### 3. Backend: Portfolio ID Storage ✅
**File**: `backend/app/api/v1/chat/conversations.py`
- Lines 46-73: Conversation creation endpoint
- Portfolio ID is stored in conversation `meta_data` field
- Auto-resolves portfolio ID if not provided
- **Logs**: `[TRACE] TRACE-1 Conversation Created` (line 90)

### 4. Backend: Portfolio Data Fetching ✅
**File**: `backend/app/api/v1/chat/send.py`
- Lines 125-159: Portfolio context loading
- Retrieves `portfolio_id` from conversation metadata (line 127)
- Calls `get_portfolio_complete_endpoint()` to fetch full snapshot (lines 135-144)
- Creates `portfolio_context` object with:
  - Portfolio ID
  - Portfolio name
  - Total value
  - Position count
  - Holdings (top 50 positions)
- **Logs**: `[TRACE] TRACE-2 Send Context` (line 162)

### 5. Backend: Context Passed to Agent ✅
**File**: `backend/app/api/v1/chat/send.py`
- Lines 310-318: OpenAI service call
- `portfolio_context` is passed to `openai_service.stream_responses()`
- Also passes:
  - `conversation_id`
  - `conversation_mode`
  - `message_text`
  - `message_history`
  - `auth_context`
  - `run_id`
  - `model_override`

---

## Potential Issues Identified

### Issue #1: Agent May Not Be USING the Portfolio Context
**Problem**: The agent receives portfolio context, but may not be instructed to use it in responses.

**Evidence**:
- Portfolio context is passed to `openai_service.stream_responses()`
- But we don't see explicit instructions telling the agent to reference this data

**Impact**: Agent may respond to questions without consulting the provided portfolio holdings.

**Root Cause**: System prompt may not explicitly instruct the agent to use the portfolio_context parameter.

---

### Issue #2: Portfolio Context May Be Too Large
**Problem**: Top 50 positions might still exceed token limits for some portfolios.

**Evidence**:
- Line 151: `"holdings": portfolio_snapshot.get("holdings", [])[:50]`
- Each holding includes full details (symbol, quantity, cost basis, P&L, etc.)

**Impact**: Context may be truncated or omitted by OpenAI if too large.

**Root Cause**: No token budget management for portfolio context.

---

### Issue #3: No Fallback for Missing Holdings
**Problem**: If portfolio snapshot fetch fails, only portfolio_id is included.

**Evidence**:
- Lines 154-159: Exception handler sets minimal context on error
- No indication to agent that data is incomplete

**Impact**: Agent may give incomplete responses without knowing data is missing.

**Root Cause**: Error handling doesn't communicate data availability to agent.

---

### Issue #4: Tool Functions May Not Be Configured
**Problem**: The 6 custom portfolio tools may not be available to the agent.

**Evidence**:
- `openai_service.stream_responses()` is called but we haven't verified tool availability
- The agent has tools like:
  - `get_portfolio_complete`
  - `get_portfolio_data_quality`
  - `get_positions_details`
  - `get_prices_historical`
  - `get_current_quotes`
  - `get_factor_etf_prices`

**Impact**: Agent can't fetch additional data even if prompted.

**Root Cause**: Tool configuration not verified in this investigation.

---

## Debugging Steps (Recommended Order)

### Step 1: Verify Portfolio Context is Reaching Agent
**Action**: Add detailed logging to confirm portfolio_context structure

**File**: `backend/app/api/v1/chat/send.py`

**Changes**:
```python
# After line 159, add:
if portfolio_context:
    holdings_count = len(portfolio_context.get("holdings", []))
    logger.info(
        f"[DEBUG] Portfolio Context Summary: "
        f"portfolio_id={portfolio_context['portfolio_id']}, "
        f"name={portfolio_context.get('portfolio_name')}, "
        f"total_value={portfolio_context.get('total_value')}, "
        f"holdings_count={holdings_count}"
    )
    # Log first holding for verification
    if holdings_count > 0:
        first_holding = portfolio_context["holdings"][0]
        logger.info(f"[DEBUG] Sample holding: {first_holding}")
else:
    logger.warning("[DEBUG] No portfolio context available for this conversation")
```

**Expected Output**: Should see portfolio details in logs when message is sent.

---

### Step 2: Check OpenAI Service Configuration
**Action**: Verify system prompt includes instructions to use portfolio_context

**File**: `backend/app/agent/services/openai_service.py`

**Investigation**:
1. Locate where system prompt is constructed
2. Verify it mentions portfolio_context parameter
3. Check if agent is instructed to reference holdings data
4. Confirm tools are registered and available

**Look for**:
```python
system_prompt = f"""
You are a portfolio analysis assistant.

You have access to the user's portfolio context:
{portfolio_context}

When answering questions, reference the specific positions and values from this data.
...
"""
```

---

### Step 3: Verify Tool Function Availability
**Action**: Check that all 6 portfolio tools are registered

**File**: `backend/app/agent/services/openai_service.py`

**Verification**:
- Confirm tools array includes all 6 functions
- Check tool signatures match API expectations
- Verify auth_context is passed to tools
- Test that tools can actually fetch data

---

### Step 4: Add Frontend Logging
**Action**: Log portfolio context being sent

**File**: `frontend/src/components/chat/ChatConversationPane.tsx`

**Changes** (around line 166):
```typescript
// After conversation is created, log portfolio context
console.log('[ChatConversationPane] Conversation created with:', {
  conversationId,
  portfolioId,
  mode: currentMode
});
```

---

### Step 5: Test with Specific Questions
**Action**: Ask questions that REQUIRE portfolio data

**Test Cases**:
1. "What is my largest position?" - Should name a specific symbol
2. "How many positions do I have?" - Should give exact count
3. "What is my total portfolio value?" - Should give dollar amount
4. "Show me my top 5 holdings" - Should list actual symbols
5. "What's my portfolio's diversification?" - Should reference actual holdings

**Expected Behavior**: Agent should give SPECIFIC answers based on actual portfolio data, not generic responses.

**Failure Indicators**:
- Generic responses ("You can check...")
- No specific symbols or values mentioned
- Asks follow-up questions it shouldn't need to ask
- Says it doesn't have access to portfolio data

---

### Step 6: Check Token Usage
**Action**: Monitor if portfolio context fits within token limits

**File**: `backend/app/api/v1/chat/send.py`

**Changes** (after line 152):
```python
# Estimate token count for portfolio context
import json
context_str = json.dumps(portfolio_context)
estimated_tokens = len(context_str) // 4  # Rough estimate: 4 chars per token
logger.info(
    f"[DEBUG] Portfolio context size: "
    f"{len(context_str)} chars, "
    f"~{estimated_tokens} tokens"
)
if estimated_tokens > 4000:
    logger.warning(
        f"[DEBUG] Portfolio context may be too large: {estimated_tokens} tokens"
    )
```

---

## Recommended Fixes (Based on Root Cause)

### Fix #1: Enhance System Prompt (Most Likely Issue)
**Problem**: Agent not instructed to use portfolio context

**Solution**: Update system prompt in `openai_service.py`

```python
system_prompt = f"""You are SigmaSight, an expert portfolio analysis assistant.

IMPORTANT: You have direct access to the user's portfolio data in the portfolio_context parameter.
This includes:
- Portfolio value: {portfolio_context.get('total_value')}
- Number of positions: {portfolio_context.get('position_count')}
- Actual holdings with symbols, quantities, and P&L

When answering questions about the portfolio:
1. ALWAYS reference the specific data from portfolio_context
2. Mention actual symbols, values, and metrics
3. Be specific - don't give generic advice
4. If data is missing, say so explicitly

Example:
- User: "What's my largest position?"
- You: "Your largest position is [SYMBOL] worth $X,XXX (Y.Y% of portfolio)."

DO NOT respond with generic advice like "check your dashboard" - you have the data right here.
"""
```

---

### Fix #2: Reduce Portfolio Context Size
**Problem**: Too much data causing truncation

**Solution**: Send summary instead of full holdings

```python
# Instead of full holdings (line 151)
portfolio_context = {
    "portfolio_id": str(portfolio_id),
    "portfolio_name": portfolio_snapshot["portfolio"]["name"],
    "total_value": portfolio_snapshot["portfolio"]["total_value"],
    "position_count": len(portfolio_snapshot.get("holdings", [])),
    # Send top 10 holdings with key info only
    "top_holdings": [
        {
            "symbol": h["symbol"],
            "value": h["total_value"],
            "percent": h["percent_of_portfolio"],
            "unrealized_pnl": h["unrealized_pnl"]
        }
        for h in portfolio_snapshot.get("holdings", [])[:10]
    ]
}
```

**Benefit**: Reduces token usage while preserving key information.

---

### Fix #3: Add Data Availability Flag
**Problem**: Agent doesn't know if data is incomplete

**Solution**: Add metadata about data completeness

```python
portfolio_context = {
    "portfolio_id": str(portfolio_id),
    "data_complete": True,  # Set to False if fetch failed
    "data_timestamp": datetime.now().isoformat(),
    # ... rest of context
}

# In exception handler (line 155):
portfolio_context = {
    "portfolio_id": str(portfolio_id),
    "data_complete": False,
    "data_error": str(e)
}
```

**Benefit**: Agent can inform user if data is unavailable.

---

### Fix #4: Verify Tool Configuration
**Problem**: Tools may not be registered correctly

**Solution**: Ensure all 6 tools are available and working

**Check**:
1. Tools are defined in `openai_service.py`
2. Tools have correct signatures
3. Tools can authenticate with `auth_context`
4. Tools return data in expected format

---

## Testing Plan

### Phase 1: Logging Verification (No Code Changes)
1. Start backend with DEBUG logging
2. Login to frontend
3. Go to `/ai-chat` page
4. Send message: "What's my portfolio worth?"
5. Check backend logs for:
   - `[TRACE] TRACE-1 Conversation Created` - Verify portfolio_id in metadata
   - `[TRACE] TRACE-2 Send Context` - Verify portfolio_context structure
   - OpenAI API call logs - Verify context is included

**Expected**: Should see portfolio data in logs at each step.

---

### Phase 2: Response Quality Check (No Code Changes)
1. Ask specific questions that require portfolio data
2. Evaluate responses:
   - ✅ GOOD: "Your portfolio is worth $2.9M with 30 positions"
   - ❌ BAD: "You can check your portfolio value in the dashboard"
   - ✅ GOOD: "Your largest position is AAPL at $102K"
   - ❌ BAD: "Your largest position depends on your holdings"

**If responses are generic**: System prompt needs updating (Fix #1).

---

### Phase 3: Tool Function Verification
1. Ask question that requires fetching additional data
2. Example: "Show me historical prices for my top position"
3. Check logs for tool_call events
4. Verify tool actually fetches data

**Expected**: Should see `tool_call` and `tool_result` events in SSE stream.

---

### Phase 4: Implement Fixes
1. Start with Fix #1 (system prompt)
2. Test thoroughly
3. If still issues, add Fix #2 (context size)
4. Verify with test cases

---

## Quick Diagnostic Command

Run this to check current behavior:

```bash
# Backend: Enable detailed logging
cd backend
export LOG_LEVEL=DEBUG

# Start backend
uv run python run.py

# In another terminal, watch logs
tail -f logs/sigmasight.log | grep -E "\[TRACE\]|\[DEBUG\]"
```

Then in frontend:
1. Login
2. Go to `/ai-chat`
3. Ask: "What positions do I have in my portfolio?"
4. Watch backend logs for portfolio context being passed

---

## Success Criteria

The issue is RESOLVED when:

✅ Backend logs show portfolio_context with holdings
✅ Agent responses include SPECIFIC portfolio data (symbols, values)
✅ Agent can answer questions like "What's my largest position?" with actual symbol
✅ No generic responses like "check your dashboard"
✅ Tool calls work when additional data is needed

---

## Next Steps

1. **Run Phase 1 Testing** (logging verification)
2. **Identify which issue** is causing the problem
3. **Implement corresponding fix**
4. **Verify with test cases**
5. **Document solution** in this file

---

## Additional Notes

### Conversation Metadata Structure
```json
{
  "portfolio_id": "uuid-string"
}
```

### Portfolio Context Structure (Current)
```json
{
  "portfolio_id": "uuid-string",
  "portfolio_name": "Portfolio Name",
  "total_value": 2900000,
  "position_count": 30,
  "holdings": [
    {
      "symbol": "AAPL",
      "quantity": 1200,
      "cost_basis": 90.00,
      "current_price": 85.00,
      "total_value": 102000,
      "unrealized_pnl": -6000,
      // ... more fields
    }
    // ... up to 50 positions
  ]
}
```

### OpenAI Service Call Signature
```python
async for sse_event in openai_service.stream_responses(
    conversation_id=str(conversation.id),
    conversation_mode=conversation.mode,
    message_text=message_text,
    message_history=message_history,
    portfolio_context=portfolio_context,  # ← Data is HERE
    auth_context=auth_context,
    run_id=run_id,
    model_override=model_for_attempt
):
```

---

## Conclusion

The portfolio data IS being fetched and passed to the agent. The most likely issue is that the agent's system prompt doesn't explicitly instruct it to USE this data in responses.

**Recommended first action**: Verify system prompt in `openai_service.py` and update it to explicitly reference portfolio_context.
