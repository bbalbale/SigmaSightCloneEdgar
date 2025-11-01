# Claude Insights with Tool Access - Planning Document

**Date**: October 31, 2025
**Goal**: Give SigmaSight AI (Claude-based insights) access to portfolio analysis tools for deeper, data-driven investigation
**Status**: Planning Phase

---

## Context

### What We Have

**Two Separate AI Systems**:

1. **AI Chat** (`/ai-chat` page)
   - Uses **OpenAI Responses API**
   - Has **tool access** (6 tools available)
   - Conversational, streaming SSE
   - Database-backed conversation history
   - Located: `backend/app/agent/services/openai_service.py`
   - **Status**: ✅ Working, **DO NOT TOUCH**

2. **SigmaSight AI** (`/sigmasight-ai` page)
   - Uses **Claude Sonnet 4** (Anthropic Messages API)
   - Currently **NO tool access** (just generates text)
   - Generates insights from pre-aggregated context
   - Located: `backend/app/services/anthropic_provider.py`
   - **Status**: ✅ Working, but limited - **ENHANCE THIS**

### Available Tools (Already Built)

The `tool_registry` (`backend/app/agent/tools/tool_registry.py`) provides **6 tools**:

1. **`get_portfolio_complete`**
   - Get comprehensive portfolio snapshot
   - Includes positions, values, optional timeseries/attribution
   - Parameters: `portfolio_id`, `include_holdings`, `include_timeseries`, `include_attrib`

2. **`get_positions_details`**
   - Get detailed position information with P&L calculations
   - Parameters: `portfolio_id`, `position_ids`, `include_closed`

3. **`get_prices_historical`**
   - Retrieve historical price data for portfolio symbols
   - Parameters: `portfolio_id`, `lookback_days` (max 180), `include_factor_etfs`

4. **`get_current_quotes`**
   - Get real-time market quotes for symbols
   - Parameters: `symbols` (comma-separated, max 5), `include_options`

5. **`get_portfolio_data_quality`**
   - Assess portfolio data completeness and quality metrics
   - Parameters: `portfolio_id`, `check_factors`, `check_correlations`

6. **`get_factor_etf_prices`**
   - Get current and historical prices for factor ETFs
   - Factors: SPY (Market), VTV (Value), VUG (Growth), MTUM (Momentum), QUAL (Quality), SLY (Size), USMV (Low Vol)
   - Parameters: `lookback_days` (max 180), `factors` (comma-separated)

**Tool Handler**: `backend/app/agent/tools/handlers.py` → `PortfolioTools` class

---

## The Vision: Conversational Partner with Data Access

### Problem Statement

Current SigmaSight AI (Claude) generates insights from **pre-aggregated context** only:
- Context builder fetches ALL data upfront (hybrid_context_builder.py)
- Claude receives a massive context dump (positions, snapshot, Greeks, factors, correlations)
- Claude can only reason about what's in the initial context
- **No ability to dig deeper** or fetch additional data mid-conversation

**Example where this fails**:

User asks: "Why is my portfolio volatility spiking?"

**Current behavior**:
- Claude sees: "21d volatility is 0.21 (vs 0.15 last week)"
- Claude responds: "Your volatility increased due to market conditions"
- **Can't dig deeper**: Which positions are driving it? What changed in the correlation structure?

**With tool access**:
- Claude sees the volatility spike
- Claude uses `get_positions_details` to see which positions are most volatile
- Claude uses `get_prices_historical` to check recent price swings
- Claude uses `get_factor_etf_prices` to compare against market factors
- Claude responds: "Your volatility spiked because NVDA (+30% weight) had 5% daily swings this week, correlated with broader tech selloff. Here's the detailed breakdown..."

### Desired Behavior: Investigative Partner

SigmaSight AI should behave like a **curious analyst** who:
1. **Sees something interesting** in the initial context
2. **Asks for more data** using tools
3. **Digs deeper** to find root causes
4. **Explains findings** conversationally with specific evidence

**Example workflow**:

```
Initial Context → AI sees high concentration

AI thinks: "42% tech exposure is high, but WHY? Let me check the positions..."

AI calls: get_positions_details(portfolio_id)

AI receives: AAPL 20%, MSFT 10%, NVDA 8%, META 4%

AI thinks: "AAPL is 20% alone - that's concentrated. Has this changed recently?"

AI calls: get_prices_historical(portfolio_id, lookback_days=30)

AI receives: AAPL up 18% in last 30 days (portfolio rebalanced by appreciation)

AI responds: "Your tech concentration at 42% is driven primarily by AAPL (20% of portfolio).
This happened because AAPL is up 18% in the last month while other positions stayed flat,
so the position grew from ~14% to 20% through appreciation. This is classic 'winner concentration' -
your best performer is now your biggest risk. Want to discuss whether to trim or let it run?"
```

---

## Architecture: Adding Tools to Claude

### Current Claude Flow (No Tools)

```
Frontend: Click "Generate Insight"
    ↓
Backend: POST /api/v1/insights/generate
    ↓
analytical_reasoning_service.py
    ↓
hybrid_context_builder.py (aggregates ALL data)
    ↓
anthropic_provider.py → investigate()
    ↓
Claude Messages API (single request/response)
    ↓
Parse response → Save to database
    ↓
Return to frontend
```

**Limitations**:
- Single request/response (no back-and-forth)
- All context must be gathered upfront
- Claude can't request additional data
- No iterative investigation

### Proposed Claude Flow (With Tools)

```
Frontend: Click "Generate Insight"
    ↓
Backend: POST /api/v1/insights/generate
    ↓
analytical_reasoning_service.py
    ↓
hybrid_context_builder.py (gathers INITIAL context only)
    ↓
anthropic_provider.py → investigate_with_tools()
    ↓
Claude Messages API (tool-enabled)
    ↓
[LOOP] Claude requests tool → Execute → Return result → Claude reasons → Next tool or final answer
    ↓
Parse final response → Save to database
    ↓
Return to frontend
```

**Benefits**:
- Claude can dig deeper as needed
- Fetch only relevant data (not everything upfront)
- Iterative investigation process
- Better insights from targeted data fetching

---

## Implementation Plan

### Phase 1: Enable Tools in Anthropic Provider ✅

**File**: `backend/app/services/anthropic_provider.py`

**Changes needed**:

1. **Add tool definitions** (Anthropic format, similar to OpenAI tools)
```python
def _get_tool_definitions(self) -> List[Dict[str, Any]]:
    """
    Convert tool registry to Anthropic tool format.
    Anthropic uses same JSON schema as OpenAI.
    """
    return [
        {
            "name": "get_portfolio_complete",
            "description": "Get comprehensive portfolio snapshot with positions, values, and optional data",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "string",
                        "description": "Portfolio UUID"
                    },
                    "include_holdings": {
                        "type": "boolean",
                        "description": "Include position details",
                        "default": True
                    }
                },
                "required": ["portfolio_id"]
            }
        },
        # ... other tools
    ]
```

2. **Enable tool use in API call**
```python
message = self.client.messages.create(
    model=self.model,
    max_tokens=self.max_tokens,
    temperature=self.temperature,
    system=system_prompt,
    tools=self._get_tool_definitions(),  # ← Add this
    messages=[{"role": "user", "content": investigation_prompt}],
    timeout=self.timeout,
)
```

3. **Implement tool execution loop**
```python
async def investigate_with_tools(self, context, insight_type, focus_area, user_question):
    """
    Execute investigation with tool access (agentic loop).
    """
    messages = self._build_messages(context, insight_type, focus_area, user_question)

    max_iterations = 5  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        # Call Claude
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self._build_system_prompt(insight_type, focus_area),
            tools=self._get_tool_definitions(),
            messages=messages
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Claude is done, extract final answer
            return self._parse_investigation_response(response.content[0].text, insight_type)

        elif response.stop_reason == "tool_use":
            # Claude wants to use a tool
            tool_calls = [block for block in response.content if block.type == "tool_use"]

            # Execute each tool call
            tool_results = []
            for tool_call in tool_calls:
                result = await self._execute_tool(
                    tool_name=tool_call.name,
                    tool_input=tool_call.input,
                    portfolio_id=context.get("portfolio_id")
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result)
                })

            # Add assistant response + tool results to message history
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            iteration += 1

        else:
            # Unexpected stop reason
            logger.warning(f"Unexpected stop reason: {response.stop_reason}")
            break

    # Max iterations reached
    logger.warning(f"Max iterations ({max_iterations}) reached in tool loop")
    return self._parse_investigation_response("Analysis incomplete due to iteration limit", insight_type)
```

4. **Add tool execution handler**
```python
async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any], portfolio_id: str) -> Dict[str, Any]:
    """
    Execute a tool call using the tool registry.
    """
    from app.agent.tools.tool_registry import tool_registry

    try:
        # Add portfolio_id to context for authentication
        context = {
            "portfolio_id": portfolio_id,
            "request_id": str(uuid.uuid4())
        }

        # Dispatch tool call
        result = await tool_registry.dispatch_tool_call(
            tool_name=tool_name,
            payload=tool_input,
            ctx=context
        )

        return result

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        return {
            "error": str(e),
            "tool_name": tool_name
        }
```

### Phase 2: Update System Prompt for Tool Use

**File**: `backend/app/services/anthropic_provider.py` → `_build_system_prompt()`

**Add tool usage guidance**:

```python
base_prompt = """You are my trusted portfolio advisor with access to analysis tools.

YOUR ROLE:
- Analyze portfolio data conversationally (first-person, direct language)
- Use tools to dig deeper when needed
- Be curious - if you see something interesting, investigate it
- Explain your thought process as you analyze

AVAILABLE TOOLS:
You have access to 6 tools for deeper analysis:
1. get_portfolio_complete - Get full portfolio snapshot
2. get_positions_details - Get specific position details
3. get_prices_historical - Check price history
4. get_current_quotes - Get real-time quotes
5. get_portfolio_data_quality - Assess data completeness
6. get_factor_etf_prices - Get factor ETF data

WHEN TO USE TOOLS:
✅ Use tools when:
- You see something interesting and want more detail
- You need to verify a hypothesis (e.g., "Is AAPL concentration from appreciation or intent?")
- You want to compare current vs historical data
- You need to check data quality before making claims

❌ Don't use tools when:
- The initial context has enough information
- You're just summarizing what you already know
- It would be redundant (tool would return same data as context)

TOOL USAGE EXAMPLES:

Example 1: Investigating Concentration
Initial context shows: "Tech exposure 42%"
Your thought: "That's high, but which specific positions? Let me check..."
Action: Call get_positions_details() to see position breakdown
Result: AAPL 20%, MSFT 10%, NVDA 8%, META 4%
Response: "Your 42% tech exposure is driven by AAPL at 20% alone..."

Example 2: Understanding Volatility Spike
Initial context shows: "21d volatility increased from 0.15 to 0.21"
Your thought: "What changed? Let me look at recent price movements..."
Action: Call get_prices_historical(lookback_days=30)
Result: NVDA had 5% daily swings, AAPL stable
Response: "The volatility spike is from NVDA, which had 5% daily swings this week..."

Example 3: When NOT to use tools
Initial context shows: "Portfolio value $500K, 15 positions, diversified sectors"
Your thought: "I have enough info to provide overview - no need for more data"
Action: None (answer directly from context)
Response: "Your portfolio looks well-balanced at $500K across 15 positions..."

CRITICAL - RESPONSE FORMAT:
[Same as before - conversational tone with required markdown headers]

REMEMBER:
- Tools are for INVESTIGATION, not just data fetching
- Think like an analyst - be curious, dig deeper
- But don't over-fetch - use tools when they add insight
- Always explain WHY you used a tool in your analysis
"""
```

### Phase 3: Update Insight Generation Endpoint

**File**: `backend/app/api/v1/insights.py`

**Minimal changes needed** - the endpoint just calls `analytical_reasoning_service`, which calls `anthropic_provider`:

```python
# In analytical_reasoning_service.py
insight = await analytical_reasoning_service.investigate_portfolio(
    db=db,
    portfolio_id=portfolio_id,
    insight_type=insight_type_enum,
    focus_area=request.focus_area,
    user_question=request.user_question
)

# In analytical_reasoning_service.py → investigate_portfolio()
# Change from investigate() to investigate_with_tools()
result = await self.anthropic_provider.investigate_with_tools(
    context=context,
    insight_type=insight_type,
    focus_area=focus_area,
    user_question=user_question,
)
```

### Phase 4: Handle Cost and Performance

**Considerations**:

1. **Cost Increase**:
   - Current: ~$0.02 per insight (single Claude call)
   - With tools: ~$0.04-0.08 per insight (multiple roundtrips)
   - **Mitigation**: Set `max_iterations=5` to cap tool use

2. **Time Increase**:
   - Current: ~25-30 seconds
   - With tools: ~40-60 seconds (3-5 tool calls)
   - **Mitigation**: Show progress in frontend ("AI is analyzing positions...")

3. **Token Limits**:
   - Anthropic Sonnet 4: 200K context window
   - Each tool result adds tokens
   - **Mitigation**: Limit tool results (e.g., top 10 positions only)

---

## Example: Insight with Tool Access

### User Request
"Generate daily summary for my portfolio"

### Initial Context (from hybrid_context_builder)
```
Portfolio: $500K
Positions: 15 total
Tech exposure: 42%
Volatility (21d): 0.21 (was 0.15 last week)
Beta: 1.15
```

### Claude's Investigation (with tools)

**Iteration 1**: Claude sees high tech concentration
```
Claude: "I notice 42% tech exposure (vs S&P's 28%). Let me see which specific positions..."
Tool call: get_positions_details(portfolio_id)
Result: AAPL $100K (20%), MSFT $50K (10%), NVDA $40K (8%), META $20K (4%)
```

**Iteration 2**: Claude notices AAPL is very large
```
Claude: "AAPL at 20% is high. Has this grown recently through appreciation?"
Tool call: get_prices_historical(portfolio_id, lookback_days=90)
Result: AAPL up 22% in 90 days, portfolio average up 8%
```

**Iteration 3**: Claude checks correlation
```
Claude: "AAPL and MSFT together are 30%. Are they correlated?"
Tool call: get_portfolio_complete(portfolio_id, include_correlations=true)
Result: AAPL-MSFT correlation: 0.78 (high)
```

**Final Response**:
```markdown
## Title
Your Portfolio Has Classic "Winner Concentration"

## Summary
I analyzed your portfolio and found you're 42% tech, with AAPL alone at 20%. This concentration happened naturally - AAPL is up 22% in the last 90 days while the rest of your portfolio averaged 8%, so it grew from about 14% to 20% through appreciation. This is classic "winner concentration" where your best performer becomes your biggest risk.

## Key Findings
- I found AAPL is 20% of your portfolio ($100K out of $500K) after appreciating 22% in 90 days
- I noticed AAPL and MSFT together are 30%, and they're correlated at 0.78 (meaning they tend to move together)
- I saw your overall tech exposure at 42% vs S&P 500's 28% - that's a +14% overweight creating sector concentration

## Detailed Analysis
Let me walk you through what happened here. You started with AAPL around 14% of the portfolio 90 days ago. AAPL then rallied 22% while your other positions averaged 8% gains. Without any buying or selling, AAPL mathematically grew to 20% of the portfolio through price appreciation alone.

This is what I call "winner concentration" - your best performer naturally becomes your largest position. It's a good problem to have (congrats on the AAPL gains!), but it does create concentration risk. With MSFT also at 10%, your top two positions are 30% of the portfolio and correlated at 0.78.

The correlation is important because it means AAPL and MSFT tend to move together (both are mega-cap tech with similar market drivers). So while you have two names, you don't have 2x the diversification.

## Recommendations
- I'd suggest thinking about whether 20% in AAPL still aligns with your conviction level - if you added it at 14% originally, this might be more than you intended
- Consider the trade-off: letting winners run (momentum continuation) vs locking in gains and reducing risk (rebalancing)
- If you want to keep the position size, you could add some downside protection (e.g., put options on AAPL) to reduce tail risk without selling

## Data Limitations
I have 90 days of price history, so I can see the recent appreciation story. I don't have your original purchase dates or cost basis, so I can't calculate exact tax impacts if you were to trim. Worth checking your cost basis before making any decisions.
```

**Tools used**: 3 total
**Cost**: ~$0.045 (vs $0.02 without tools)
**Time**: ~45 seconds (vs 30 seconds)
**Value**: Much richer insight with specific evidence

---

## Success Criteria

### Insight Quality Improvements
- ✅ Insights include **specific evidence** from tool calls
- ✅ Claude explains **thought process** (why tools were used)
- ✅ Deeper analysis with **root cause investigation**
- ✅ More credible because claims are **data-backed**

### Performance Metrics
- Time to generate: <60 seconds (vs 30s baseline)
- Cost per insight: <$0.10 (vs $0.02 baseline)
- Tool calls per insight: Average 2-4, max 5
- User rating: >4.5/5.0 (higher than current)

### User Experience
- Frontend shows progress: "AI is analyzing positions..." (tool execution feedback)
- Insights feel investigative, not just summarizing
- Users see Claude's "thinking process"
- More trust because insights cite specific data points

---

## Risks & Mitigations

### Risk 1: Cost Explosion
**Risk**: Claude makes too many tool calls, costs spiral
**Mitigation**:
- Set `max_iterations=5` hard limit
- Track tool call counts and costs in logs
- Add rate limiting if needed (e.g., max 20 tool calls per day per user)

### Risk 2: Slow Performance
**Risk**: Multiple tool calls make insights too slow
**Mitigation**:
- Show progress indicator in frontend
- Set 60s timeout
- Optimize tool responses (return only needed data)

### Risk 3: Tool Call Errors
**Risk**: Tool fails, Claude gets stuck or generates bad insights
**Mitigation**:
- Wrap tool execution in try/catch
- Return error messages to Claude so it can adapt
- Fallback to non-tool analysis if tools fail

### Risk 4: Redundant Tool Calls
**Risk**: Claude calls same tool multiple times with same args
**Mitigation**:
- Add tool call deduplication
- Include recent tool results in context so Claude doesn't re-fetch

---

## Comparison: OpenAI Chat vs Claude Insights

| Feature | OpenAI Chat (/ai-chat) | Claude Insights (/sigmasight-ai) |
|---------|------------------------|----------------------------------|
| **Purpose** | Conversational Q&A | Deep portfolio analysis |
| **AI Model** | OpenAI Responses API | Claude Sonnet 4 |
| **Tool Access** | ✅ Yes (6 tools) | ⚠️ Not yet (adding) |
| **Streaming** | ✅ SSE streaming | ❌ No (single response) |
| **Conversation History** | ✅ Database-backed | ❌ No (one-shot) |
| **Use Case** | "What's my tech exposure?" | "Generate daily summary" |
| **Response Time** | <5s (streaming) | 30-60s (batch generation) |
| **Status** | ✅ Working, don't touch | 🚧 Enhancing with tools |

**Key Difference**:
- **Chat**: Interactive back-and-forth, conversational, real-time
- **Insights**: Deep analysis, investigative, generated on-demand

**Both use tools**, but for different purposes:
- Chat uses tools to answer specific questions
- Insights use tools to conduct investigation and generate comprehensive analysis

---

## Implementation Checklist

### Phase 1: Tool Infrastructure
- [ ] Add tool definitions to `anthropic_provider.py`
- [ ] Implement `_get_tool_definitions()` in Anthropic format
- [ ] Test tool definitions match registry

### Phase 2: Agentic Loop
- [ ] Implement `investigate_with_tools()` method
- [ ] Add tool execution logic
- [ ] Add iteration limit (max 5)
- [ ] Handle `stop_reason="tool_use"`

### Phase 3: Tool Execution
- [ ] Implement `_execute_tool()` method
- [ ] Integrate with `tool_registry`
- [ ] Add error handling
- [ ] Test each tool individually

### Phase 4: System Prompt Updates
- [ ] Add tool usage guidance to system prompt
- [ ] Add examples of when to use tools
- [ ] Add examples of when NOT to use tools
- [ ] Test prompt with various scenarios

### Phase 5: Testing
- [ ] Test with "winner concentration" scenario (AAPL appreciation)
- [ ] Test with volatility spike scenario
- [ ] Test with missing data scenario (graceful degradation)
- [ ] Test cost tracking (total tokens + cost per insight)

### Phase 6: Frontend Updates
- [ ] Add progress indicator ("AI is analyzing...")
- [ ] Show tool calls in insight detail (optional: "AI called 3 tools")
- [ ] Test with real portfolios
- [ ] Collect user feedback

---

## Next Steps

1. **Review this plan** - Does it align with the vision?
2. **Start with Phase 1** - Add tool definitions to Anthropic provider
3. **Test tool execution** - Verify tools work with Claude
4. **Implement agentic loop** - Allow multiple tool calls
5. **Update system prompt** - Guide Claude on when/how to use tools
6. **Test with real portfolios** - Generate insights and compare quality

**Question**: Should we proceed with implementation, or refine the plan first?

---

## Appendix: Tool Definitions in Anthropic Format

```python
def _get_tool_definitions_anthropic(self) -> List[Dict[str, Any]]:
    """
    Tool definitions in Anthropic format (same as OpenAI).
    """
    return [
        {
            "name": "get_portfolio_complete",
            "description": "Get comprehensive portfolio snapshot including positions, values, timeseries, and attribution. Use this when you need a full overview of the portfolio.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "string",
                        "description": "Portfolio UUID"
                    },
                    "include_holdings": {
                        "type": "boolean",
                        "description": "Include detailed position holdings",
                        "default": True
                    },
                    "include_timeseries": {
                        "type": "boolean",
                        "description": "Include historical timeseries data",
                        "default": False
                    },
                    "include_attrib": {
                        "type": "boolean",
                        "description": "Include attribution analysis",
                        "default": False
                    }
                },
                "required": ["portfolio_id"]
            }
        },
        {
            "name": "get_positions_details",
            "description": "Get detailed information about specific positions including P&L, market values, and position characteristics. Use this when you want to investigate specific holdings.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "string",
                        "description": "Portfolio UUID"
                    },
                    "position_ids": {
                        "type": "string",
                        "description": "Comma-separated position UUIDs (optional - omit for all positions)"
                    },
                    "include_closed": {
                        "type": "boolean",
                        "description": "Include closed positions in results",
                        "default": False
                    }
                },
                "required": ["portfolio_id"]
            }
        },
        {
            "name": "get_prices_historical",
            "description": "Retrieve historical price data for portfolio symbols over a specified lookback period. Use this to analyze price trends, volatility, or recent performance.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "string",
                        "description": "Portfolio UUID"
                    },
                    "lookback_days": {
                        "type": "integer",
                        "description": "Number of days of historical data (max 180)",
                        "default": 90
                    },
                    "include_factor_etfs": {
                        "type": "boolean",
                        "description": "Include factor ETF prices for comparison",
                        "default": False
                    }
                },
                "required": ["portfolio_id"]
            }
        },
        {
            "name": "get_current_quotes",
            "description": "Get real-time market quotes for specified symbols. Use this to check current prices, volumes, or market status.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "string",
                        "description": "Comma-separated ticker symbols (max 5 symbols)"
                    },
                    "include_options": {
                        "type": "boolean",
                        "description": "Include options chain data",
                        "default": False
                    }
                },
                "required": ["symbols"]
            }
        },
        {
            "name": "get_portfolio_data_quality",
            "description": "Assess completeness and quality of portfolio data including factor coverage, correlation data, and missing fields. Use this before making claims about data quality.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_id": {
                        "type": "string",
                        "description": "Portfolio UUID"
                    },
                    "check_factors": {
                        "type": "boolean",
                        "description": "Check factor data availability",
                        "default": True
                    },
                    "check_correlations": {
                        "type": "boolean",
                        "description": "Check correlation data quality",
                        "default": True
                    }
                },
                "required": ["portfolio_id"]
            }
        },
        {
            "name": "get_factor_etf_prices",
            "description": "Get current and historical prices for factor ETFs (Market/SPY, Value/VTV, Growth/VUG, Momentum/MTUM, Quality/QUAL, Size/SLY, Low Vol/USMV). Use this for factor analysis and comparisons.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "Number of days of historical data (max 180)",
                        "default": 90
                    },
                    "factors": {
                        "type": "string",
                        "description": "Comma-separated factor names (SPY, VTV, VUG, MTUM, QUAL, SLY, USMV). Omit for all factors."
                    }
                },
                "required": []
            }
        }
    ]
```

---

**End of Planning Document**
