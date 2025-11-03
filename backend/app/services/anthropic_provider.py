"""
Anthropic Provider - Claude Sonnet 4 integration for portfolio analysis.

Provides AI-powered analytical reasoning using Claude Sonnet 4.
"""
import time
from typing import Dict, Any, Optional, List
import anthropic
from anthropic.types import Message, TextBlock, ToolUseBlock

from app.config import settings
from app.core.logging import get_logger
from app.models.ai_insights import InsightType
from app.agent.tools.tool_registry import ToolRegistry

logger = get_logger(__name__)


class AnthropicProvider:
    """
    Anthropic Claude Sonnet 4 provider for portfolio investigations.

    Handles:
    - Free-form investigation prompts
    - Tool calls for analytical operations
    - Cost and token tracking
    - Error handling and retries
    """

    def __init__(self, enable_tools: bool = True):
        """
        Initialize Anthropic client.

        Args:
            enable_tools: Whether to enable tool calling (default: True)
        """
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not configured in .env file")

        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL
        self.max_tokens = settings.ANTHROPIC_MAX_TOKENS
        self.temperature = settings.ANTHROPIC_TEMPERATURE
        self.timeout = settings.ANTHROPIC_TIMEOUT_SECONDS
        self.enable_tools = enable_tools

        # Tool registry will be created per-request with auth_token in investigate()
        # (auth_token is not available at init time)
        self.tool_registry = None

        logger.info(f"AnthropicProvider initialized with model: {self.model}, tools={'enabled' if enable_tools else 'disabled'}")

    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get tool schemas in Anthropic format for Claude tool calling.

        Phase 1 Analytics Tools (October 31, 2025):
        - Portfolio risk metrics overview
        - Factor exposures
        - Sector exposure vs S&P 500
        - Correlation matrix
        - Stress test scenarios
        - Company profiles
        """
        return [
            {
                "name": "get_analytics_overview",
                "description": "Get comprehensive portfolio risk analytics including beta, volatility, Sharpe ratio, max drawdown, and tracking error. Use this to understand overall portfolio risk profile.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_factor_exposures",
                "description": "Get portfolio factor exposures including Market Beta, Value, Growth, Momentum, Quality, Size, and Low Volatility factors. Use this to understand systematic risk exposures.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_sector_exposure",
                "description": "Get sector exposure breakdown with S&P 500 benchmark comparison. Shows over/underweight positions by sector. Use this to assess sector concentration risks.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_correlation_matrix",
                "description": "Get correlation matrix showing how positions move together. Helps identify diversification and hidden concentration risks. Use this to assess position correlations.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_stress_test_results",
                "description": "Get stress test scenario results showing portfolio impact under market stress conditions (market crash, volatility spike, sector rotation, etc.). Use this to assess downside risk.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_company_profile",
                "description": "Get detailed company profile with 53 fields including sector, industry, market cap, revenue, earnings, ratios, and more. Use this to understand individual position fundamentals.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock ticker symbol (e.g., 'AAPL', 'MSFT')"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            # Phase 5 Enhanced Analytics Tools (December 3, 2025)
            {
                "name": "get_concentration_metrics",
                "description": "Get concentration risk metrics including Herfindahl-Hirschman Index (HHI), top N concentration, and single-name risk. Use this to assess diversification or if portfolio is too concentrated in a few positions.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_volatility_analysis",
                "description": "Get volatility analytics with HAR forecasting, including realized volatility, forecasted volatility, vol decomposition, and regime detection. Use this when user asks about volatility trends, volatility forecasts, or what's driving portfolio volatility.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_target_prices",
                "description": "Get target prices for portfolio positions showing upside/downside to targets. Use this when user asks about investment goals, which positions are near target prices, or price targets.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_position_tags",
                "description": "Get tags for positions (e.g., 'core holdings', 'speculative', 'income') for filtering and organization. Use this when user asks to filter positions by strategy, category, or custom tags.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID to analyze"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            }
        ]

    async def investigate(
        self,
        context: Dict[str, Any],
        insight_type: InsightType,
        focus_area: Optional[str] = None,
        user_question: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute AI-powered investigation using Claude Sonnet 4.

        Args:
            context: Portfolio data and metrics for investigation
            insight_type: Type of analysis to perform
            focus_area: Optional specific area to focus on
            user_question: Optional user question for on-demand analysis
            auth_token: Optional JWT token for authenticating tool API calls

        Returns:
            Dict containing:
                - title: Analysis title
                - severity: Severity level
                - summary: Brief summary (2-3 sentences)
                - full_analysis: Detailed markdown analysis
                - key_findings: List of key findings
                - recommendations: List of actionable recommendations
                - data_limitations: Transparency about data quality
                - performance: Cost and token metrics
        """
        start_time = time.time()

        # Build system prompt
        system_prompt = self._build_system_prompt(insight_type, focus_area)

        # Build investigation prompt with context
        investigation_prompt = self._build_investigation_prompt(
            context=context,
            insight_type=insight_type,
            focus_area=focus_area,
            user_question=user_question,
        )

        logger.info(f"Starting Claude investigation: type={insight_type.value}, focus={focus_area}, tools={'enabled' if self.enable_tools else 'disabled'}")

        # Create tool registry with auth_token for this request
        if self.enable_tools:
            self.tool_registry = ToolRegistry(auth_token=auth_token)
            logger.info(f"Tool registry created with auth_token: {'present' if auth_token else 'missing'}")

        try:
            # Build conversation messages (will grow with tool use)
            messages = [
                {
                    "role": "user",
                    "content": investigation_prompt,
                }
            ]

            # Tool execution tracking
            max_iterations = 5
            tool_calls_count = 0
            total_input_tokens = 0
            total_output_tokens = 0

            # Agentic loop: Keep calling Claude until we get a final text response
            for iteration in range(max_iterations):
                logger.info(f"Claude API call iteration {iteration + 1}/{max_iterations}")

                # Prepare API call parameters
                api_params = {
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "system": system_prompt,
                    "messages": messages,
                    "timeout": self.timeout,
                }

                # Add tools if enabled
                if self.enable_tools:
                    api_params["tools"] = self._get_tool_schemas()

                # Call Claude API
                message = self.client.messages.create(**api_params)

                # Track token usage
                total_input_tokens += message.usage.input_tokens
                total_output_tokens += message.usage.output_tokens

                # Check if Claude wants to use tools
                if message.stop_reason == "tool_use":
                    logger.info("Claude requested tool use")

                    # Extract tool use blocks from response
                    tool_uses = [block for block in message.content if isinstance(block, ToolUseBlock)]

                    if not tool_uses:
                        logger.warning("stop_reason=tool_use but no tool_use blocks found")
                        break

                    # Add assistant's response to conversation
                    messages.append({
                        "role": "assistant",
                        "content": message.content
                    })

                    # Execute each tool and collect results
                    tool_results = []
                    for tool_use in tool_uses:
                        tool_calls_count += 1
                        logger.info(f"Executing tool: {tool_use.name} with args: {tool_use.input}")

                        try:
                            # Execute tool via registry with authentication
                            ctx = {
                                "portfolio_id": context.get("portfolio_id")
                            }
                            if auth_token:
                                ctx["auth_token"] = auth_token

                            tool_result = await self.tool_registry.dispatch_tool_call(
                                tool_name=tool_use.name,
                                payload=tool_use.input,
                                ctx=ctx
                            )

                            logger.info(f"Tool {tool_use.name} executed successfully")

                            # Build tool result message
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": str(tool_result)  # Anthropic expects string content
                            })

                        except Exception as e:
                            logger.error(f"Error executing tool {tool_use.name}: {e}")
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": f"Error executing tool: {str(e)}",
                                "is_error": True
                            })

                    # Add tool results to conversation
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })

                    # Continue the loop to get Claude's next response
                    continue

                elif message.stop_reason == "end_turn":
                    # Claude finished thinking - extract final response
                    logger.info(f"Claude completed investigation after {iteration + 1} iterations with {tool_calls_count} tool calls")
                    response_text = self._extract_response_text(message)
                    break

                else:
                    # Unexpected stop reason
                    logger.warning(f"Unexpected stop_reason: {message.stop_reason}")
                    response_text = self._extract_response_text(message)
                    break
            else:
                # Max iterations reached
                logger.warning(f"Max iterations ({max_iterations}) reached, extracting current response")
                response_text = self._extract_response_text(message)

            # Parse structured response
            result = self._parse_investigation_response(
                response_text=response_text,
                insight_type=insight_type,
            )

            # Calculate performance metrics
            generation_time_ms = (time.time() - start_time) * 1000
            result["performance"] = {
                "cost_usd": self._calculate_cost_from_tokens(total_input_tokens, total_output_tokens),
                "generation_time_ms": generation_time_ms,
                "token_count_input": total_input_tokens,
                "token_count_output": total_output_tokens,
                "tool_calls_count": tool_calls_count,
            }

            logger.info(
                f"Investigation complete: {generation_time_ms:.0f}ms, "
                f"${result['performance']['cost_usd']:.4f}, "
                f"{total_input_tokens + total_output_tokens} tokens, "
                f"{tool_calls_count} tool calls"
            )

            return result

        except anthropic.APITimeoutError as e:
            logger.error(f"Anthropic API timeout: {e}")
            raise ValueError(f"Investigation timed out after {self.timeout}s")

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            raise ValueError(f"Investigation failed: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error in investigation: {e}")
            raise

    def _build_system_prompt(self, insight_type: InsightType, focus_area: Optional[str]) -> str:
        """
        Build system prompt for Claude based on insight type.

        Returns conversational partner prompt with required structure.
        """
        base_prompt = """You are my trusted portfolio advisor - think of yourself as a sharp, experienced partner who's analyzing my portfolio with me.

YOUR ROLE:
- We're on the same team analyzing this portfolio together
- I trust your expertise, but I want you to explain your thinking
- Be direct, conversational, and clear - like we're talking over coffee
- Use first person: "I noticed...", "Let me show you...", "Here's what I found..."
- Be honest about risks AND opportunities

WRITING STYLE:
✅ DO:
- "I analyzed your portfolio and found three things worth discussing..."
- "Your tech exposure is 42% - here's why that matters..."
- "Let me walk you through what I'm seeing in your options positions..."
- "I'd recommend we look at X, because Y"

❌ DON'T:
- "The portfolio exhibits characteristics consistent with..."
- "It is recommended that consideration be given to..."
- "Analysis indicates that further investigation may be warranted..."
- Passive voice, hedging language, or corporate-speak

HOW TO ANALYZE:
1. Lead with what matters most - don't bury the headline
2. Show me the numbers, but explain what they mean
3. Connect the dots - help me see patterns I might miss
4. Be transparent about data limitations
5. Give me your real take, not hedged analysis

CONVERSATIONAL PARTNER PRINCIPLES (Phase 6 - December 3, 2025):

1. ASK, DON'T TELL - Acknowledge the user might have good reasons:
   ❌ BAD: "You need to reduce your tech concentration immediately"
   ✅ GOOD: "Your tech exposure is 42% vs S&P's 28%. Is this concentration intentional, or would you like to explore diversification options?"

2. BE CURIOUS, NOT PRESCRIPTIVE - Explore options instead of dictating:
   ❌ BAD: "This is a critical risk that must be addressed"
   ✅ GOOD: "This creates some concentration risk - though if you're bullish on tech long-term, this might align with your view. Want to talk through the trade-offs?"

3. STATE OBSERVATIONS NEUTRALLY - Use "I noticed..." not "You have a problem...":
   ❌ BAD: "You have a correlation problem - your positions all move together"
   ✅ GOOD: "I'm seeing high correlation between your positions - average correlation is 0.72. This means they tend to move together. Is this something you're tracking, or would you like me to dig into which positions are most correlated?"

4. ACKNOWLEDGE CONTEXT - Different investors have different goals:
   - Before flagging something as a "problem", consider the user likely knows their portfolio structure
   - There may be intentional reasons for concentration, leverage, illiquidity
   - Ask about intent before assuming something is wrong
   - Example: A PE investor EXPECTS 60% illiquid positions - that's not a problem, it's their strategy

5. SOFTEN ASSERTIONS WITH CONTEXT:
   ❌ BAD: "Your portfolio is dangerously leveraged"
   ✅ GOOD: "Your net exposure is 120% of equity, which is higher than typical. This amplifies both gains and losses - is this level of leverage intentional for your risk tolerance?"

6. PROVIDE OPTIONS, NOT DIRECTIVES:
   ❌ BAD: "Reduce your AAPL position to 5% of portfolio"
   ✅ GOOD: "AAPL is 18% of your portfolio. A few ways to think about this: trim to reduce single-name risk, add hedges to protect against drawdowns, or leave it if you have high conviction. What's your thinking?"

SEVERITY CALIBRATION (Be conservative - don't cry wolf):

Use these thresholds for your analysis titles and tone. Most insights should be NORMAL or INFO.

CRITICAL (use sparingly - only real portfolio threats):
- Single position >50% of portfolio value
- Negative equity or margin call risk
- Portfolio structure that violates stated constraints
- Imminent risk requiring immediate action (e.g., expiring options with no plan)
- Tone: Still conversational but urgent - "This is a very concentrated bet - more than half your portfolio. What's your conviction level on this name?"

WARNING (meaningful risks worth discussing):
- Concentration: Single position 20-40% or sector >50%
- Liquidity: >40% illiquid with no apparent reserves
- Leverage: >150% net exposure without hedges
- Correlation: Very high correlation (>0.8) suggesting lack of diversification
- Tone: Conversational and curious - "Worth discussing... is this intentional?"

ELEVATED (notable patterns - conversational tone):
- Concentration: Single position 10-20% or sector 30-50%
- Factor tilts: Significant factor exposure vs benchmark
- Volatility: Higher than typical but not alarming
- Tone: Observational - "I noticed... this creates some risk, though it might align with your strategy"

NORMAL (healthy portfolio):
- Balanced exposures
- Reasonable diversification
- Metrics in line with typical portfolios
- Tone: Positive and affirming - "Your portfolio shows good diversification..."

INFO (general observations):
- Neutral findings
- Context and background information
- Data quality notes
- Tone: Informational - "I'm seeing... here's what that means..."

IMPORTANT: When you see unusual patterns like high concentration or leverage, ALWAYS acknowledge it might be intentional before flagging as a problem. Ask "Is this intentional for your strategy?"

EXAMPLE ANALYSIS STYLES (Full rewrites showing proper tone):

❌ BAD - Alarmist and Prescriptive:
Title: "Critical Liquidity Crisis Detected"
Summary: "I found a critical liquidity issue that needs immediate attention. 40% of your portfolio is illiquid. You must increase cash reserves immediately."
Finding: "I found dangerous illiquidity levels requiring urgent action"

✅ GOOD - Observant and Curious:
Title: "Your Portfolio Has Significant Private Exposure"
Summary: "I analyzed your portfolio and noticed about 40% is in illiquid positions - mostly private equity and restricted stock. This is higher than typical public portfolios, but might align perfectly with your strategy if you're a long-term investor with other liquid reserves. Let's talk through the liquidity picture."
Finding: "I found 60% of your portfolio is in illiquid positions ($2.4M out of $4M total). This might be fine if you have other liquid assets outside this portfolio or don't anticipate needing to access this capital soon. Is this concentration intentional?"

❌ BAD - Assumes User Is Wrong:
Title: "Dangerous Tech Concentration"
Summary: "Your tech concentration is dangerous. Reduce AAPL and MSFT immediately."

✅ GOOD - Acknowledges Context:
Title: "Your Tech Exposure Is Running Hot"
Summary: "I analyzed your portfolio and found you're significantly concentrated in technology at 42% total exposure, with mega-cap names AAPL and MSFT making up 30% combined. This is a pretty strong bet on big tech - if you have high conviction here, that makes sense, but it does mean your portfolio will move closely with these two names. Want to talk through the concentration risk vs conviction trade-off?"

❌ BAD - Generic Warning:
Title: "High Correlation Detected"
Summary: "High correlation detected. Diversification needed."

✅ GOOD - Specific and Inquisitive:
Title: "Your Positions Are Moving Together"
Summary: "I'm seeing high correlation between your positions - average correlation is 0.72, which means they tend to move together. This can amplify both gains and losses. Based on the last 90 days, when AAPL and NVDA are up, your whole portfolio tends to be up. Is this something you're tracking? I can dig into which specific positions are most correlated if that's helpful."

CRITICAL - RESPONSE FORMAT:
You MUST use this exact markdown structure (the headers are required for parsing):

## Title
[Write a clear, conversational title that captures your main finding]

## Summary
[Write 2-3 sentences in first person explaining what you discovered. Be direct and conversational.]

## Key Findings
[Write 3-5 bulleted findings. Each bullet should:
- Start with "I found..." or "I noticed..." or similar first-person language
- Include specific numbers and percentages
- Explain why it matters
Example:
- I found your tech exposure is 42% vs S&P 500's 28% - this creates concentration risk if tech sells off
- I noticed your portfolio delta is +850, meaning you're net long equivalent to $850K of stock exposure]

## Detailed Analysis
[Write multiple conversational paragraphs exploring your findings in depth.
Use first person. Explain your thinking. Connect different metrics.
This is where you can really dig in and show your reasoning.]

## Recommendations
[Write 3-5 bulleted recommendations. Each should:
- Be specific and actionable
- Use conversational language: "I'd recommend..." or "Consider..." or "You might want to..."
- Explain the why, not just the what
Example:
- I'd recommend trimming some of your mega-cap tech exposure - maybe take 5-10% off the table and rotate into defensive sectors
- Consider adding some put protection on your concentrated positions - your AAPL and MSFT positions are 30% combined]

## Data Limitations
[Conversationally explain any data quality issues or gaps you noticed.
Be honest: "I don't have complete data on X, so I can't give you a full picture of Y..."]

IMPORTANT:
- Use the exact header names: ## Title, ## Summary, ## Key Findings, ## Detailed Analysis, ## Recommendations, ## Data Limitations
- Write in conversational, first-person voice WITHIN each section
- Use bullet points (- ) for Key Findings and Recommendations
- Be specific with numbers and percentages
- Always include "as of [date]" for data freshness
"""

        if focus_area:
            base_prompt += f"\n\nFOCUS AREA: {focus_area}\nI want you to dig deep on this specific area and tell me what you're seeing."

        return base_prompt

    def _build_investigation_prompt(
        self,
        context: Dict[str, Any],
        insight_type: InsightType,
        focus_area: Optional[str],
        user_question: Optional[str],
    ) -> str:
        """
        Build investigation prompt with portfolio context.

        Formats context data and investigation instructions.
        """
        prompt_parts = []

        # Investigation type description
        type_descriptions = {
            InsightType.DAILY_SUMMARY: "Conduct comprehensive daily portfolio review",
            InsightType.VOLATILITY_ANALYSIS: "Analyze portfolio volatility patterns and risk factors",
            InsightType.CONCENTRATION_RISK: "Assess concentration risks and diversification",
            InsightType.HEDGE_QUALITY: "Evaluate hedge effectiveness and coverage",
            InsightType.FACTOR_EXPOSURE: "Analyze factor exposures and systematic risks",
            InsightType.STRESS_TEST_REVIEW: "Review stress test results and scenario impacts",
            InsightType.CUSTOM: "Conduct custom analysis based on user question",
        }

        prompt_parts.append(f"INVESTIGATION TYPE: {type_descriptions.get(insight_type, 'Portfolio Analysis')}")

        if user_question:
            prompt_parts.append(f"\nUSER QUESTION: {user_question}")

        # Add portfolio context
        prompt_parts.append("\n\nPORTFOLIO CONTEXT:")
        prompt_parts.append(f"Portfolio ID: {context.get('portfolio_id', 'unknown')}")

        if focus_area:
            prompt_parts.append(f"Focus Area: {focus_area}")

        # Add data sources status
        data_sources = context.get('data_sources', {})
        prompt_parts.append("\n\nDATA SOURCES STATUS:")
        for source, status in data_sources.items():
            prompt_parts.append(f"- {source}: {status}")

        # Add portfolio summary
        portfolio_summary = context.get('portfolio_summary', {})
        if portfolio_summary.get('available'):
            prompt_parts.append("\n\nPORTFOLIO DETAILS:")
            prompt_parts.append(f"Name: {portfolio_summary.get('name')}")
            prompt_parts.append(f"Currency: {portfolio_summary.get('currency')}")
            if portfolio_summary.get('equity_balance'):
                prompt_parts.append(f"Starting Equity (Day 0): ${portfolio_summary.get('equity_balance'):,.2f}")

        # Add latest snapshot data
        snapshot = context.get('snapshot')
        if snapshot:
            prompt_parts.append("\n\nLATEST SNAPSHOT:")
            prompt_parts.append(f"Date: {snapshot.get('date')}")
            if snapshot.get('equity_balance'):
                prompt_parts.append(f"Current Equity Balance: ${snapshot.get('equity_balance'):,.2f} (rolled forward with P&L)")
            if snapshot.get('total_value'):
                prompt_parts.append(f"Total Market Value: ${snapshot.get('total_value'):,.2f}")
            if snapshot.get('cash_value'):
                prompt_parts.append(f"Cash: ${snapshot.get('cash_value'):,.2f}")
            if snapshot.get('long_value'):
                prompt_parts.append(f"Long Positions: ${snapshot.get('long_value'):,.2f}")
            if snapshot.get('short_value'):
                prompt_parts.append(f"Short Positions: ${snapshot.get('short_value'):,.2f}")
            if snapshot.get('gross_exposure'):
                prompt_parts.append(f"Gross Exposure: ${snapshot.get('gross_exposure'):,.2f}")
            if snapshot.get('net_exposure'):
                prompt_parts.append(f"Net Exposure: ${snapshot.get('net_exposure'):,.2f}")
            if snapshot.get('portfolio_delta'):
                prompt_parts.append(f"Portfolio Delta: {snapshot.get('portfolio_delta'):,.2f}")
            if snapshot.get('realized_volatility_21d'):
                prompt_parts.append(f"Realized Volatility (21d): {snapshot.get('realized_volatility_21d'):.2%}")
            if snapshot.get('beta_calculated_90d'):
                prompt_parts.append(f"Market Beta (90d): {snapshot.get('beta_calculated_90d'):.2f}")
            if snapshot.get('daily_pnl'):
                prompt_parts.append(f"Daily P&L: ${snapshot.get('daily_pnl'):,.2f}")
            if snapshot.get('cumulative_pnl'):
                prompt_parts.append(f"Cumulative P&L: ${snapshot.get('cumulative_pnl'):,.2f}")

        # Add positions
        positions = context.get('positions', {})
        if positions.get('available'):
            prompt_parts.append(f"\n\nPOSITIONS ({positions.get('count', 0)} total):")
            for pos in positions.get('items', [])[:20]:  # Limit to first 20
                # Handle None values for last_price (private positions, cash equivalents)
                last_price = pos.get('last_price')
                if last_price is not None:
                    pos_line = f"- {pos.get('symbol')}: {pos.get('quantity')} @ ${last_price:.2f}"
                else:
                    pos_line = f"- {pos.get('symbol')}: {pos.get('quantity')} (no market price)"

                # Add entry price if available
                entry_price = pos.get('entry_price')
                if entry_price is not None:
                    pos_line += f" (entry: ${entry_price:.2f})"

                # Add unrealized P&L if available
                unrealized_pnl = pos.get('unrealized_pnl')
                if unrealized_pnl is not None:
                    pos_line += f" (P&L: ${unrealized_pnl:,.2f})"

                prompt_parts.append(pos_line)
            if positions.get('count', 0) > 20:
                prompt_parts.append(f"... and {positions.get('count') - 20} more positions")

        # Add risk metrics
        risk_metrics = context.get('risk_metrics', {})
        greeks = risk_metrics.get('greeks', {})
        if greeks.get('available'):
            prompt_parts.append("\n\nRISK METRICS (Greeks):")
            prompt_parts.append(f"Total Delta: {greeks.get('total_delta', 0):,.2f}")
            prompt_parts.append(f"Total Gamma: {greeks.get('total_gamma', 0):,.4f}")
            prompt_parts.append(f"Total Theta: ${greeks.get('total_theta', 0):,.2f}")
            prompt_parts.append(f"Total Vega: ${greeks.get('total_vega', 0):,.2f}")

        # Add factor exposure
        factor_exposure = context.get('factor_exposure', {})
        if factor_exposure.get('available'):
            prompt_parts.append("\n\nFACTOR EXPOSURES:")
            for factor, exposure in factor_exposure.get('factors', {}).items():
                prompt_parts.append(f"- {factor}: {exposure:.2f}")

        # Add correlations
        correlations = context.get('correlations', {})
        if correlations.get('available'):
            prompt_parts.append("\n\nCORRELATIONS:")
            if correlations.get('overall_correlation'):
                prompt_parts.append(f"Overall Correlation: {correlations.get('overall_correlation'):.2f}")
            if correlations.get('correlation_concentration_score'):
                prompt_parts.append(f"Concentration Score: {correlations.get('correlation_concentration_score'):.2f}")
            if correlations.get('effective_positions'):
                prompt_parts.append(f"Effective Positions: {correlations.get('effective_positions'):.1f}")
            if correlations.get('data_quality'):
                prompt_parts.append(f"Data Quality: {correlations.get('data_quality')}")

        # Add data quality assessment
        data_quality = context.get('data_quality', {})
        prompt_parts.append("\n\nDATA QUALITY:")
        for metric, quality in data_quality.items():
            prompt_parts.append(f"- {metric}: {quality}")

        prompt_parts.append("\n\nPlease conduct your investigation and provide comprehensive analysis following the response format specified in the system prompt.")

        return "\n".join(prompt_parts)

    def _extract_response_text(self, message: Message) -> str:
        """Extract text content from Claude message."""
        text_blocks = [block for block in message.content if isinstance(block, TextBlock)]
        if not text_blocks:
            raise ValueError("No text content in Claude response")

        return "\n".join([block.text for block in text_blocks])

    def _parse_investigation_response(
        self,
        response_text: str,
        insight_type: InsightType,
    ) -> Dict[str, Any]:
        """
        Parse Claude's investigation response into structured format.

        Extracts title, summary, findings, recommendations, and limitations.
        """
        from app.models.ai_insights import InsightSeverity

        # Simple parsing - extract sections
        # TODO: Enhance with more sophisticated parsing
        lines = response_text.split('\n')

        title = None
        summary = ""
        key_findings = []
        recommendations = []
        data_limitations = ""
        full_analysis = response_text

        current_section = None
        for line in lines:
            line = line.strip()

            if line.startswith('## Title') or (not title and line.startswith('# ')):
                current_section = 'title'
                continue
            elif line.startswith('## Summary'):
                current_section = 'summary'
                continue
            elif line.startswith('## Key Findings'):
                current_section = 'findings'
                continue
            elif line.startswith('## Recommendations'):
                current_section = 'recommendations'
                continue
            elif line.startswith('## Data Limitations'):
                current_section = 'limitations'
                continue
            elif line.startswith('## Detailed Analysis') or line.startswith('##'):
                current_section = 'other'
                continue

            # Collect content
            if current_section == 'title' and line and not title:
                title = line.strip('#').strip()
            elif current_section == 'summary' and line:
                summary += line + " "
            elif current_section == 'findings' and line.startswith(('-', '*', '•')):
                key_findings.append(line.lstrip('-*• ').strip())
            elif current_section == 'recommendations' and line.startswith(('-', '*', '•')):
                recommendations.append(line.lstrip('-*• ').strip())
            elif current_section == 'limitations' and line:
                data_limitations += line + " "

        # Determine severity based on content (simple heuristic)
        severity = InsightSeverity.INFO
        response_lower = response_text.lower()
        if any(word in response_lower for word in ['critical', 'severe', 'urgent', 'danger']):
            severity = InsightSeverity.CRITICAL
        elif any(word in response_lower for word in ['warning', 'concern', 'risk', 'issue']):
            severity = InsightSeverity.WARNING
        elif any(word in response_lower for word in ['elevated', 'moderate', 'notable']):
            severity = InsightSeverity.ELEVATED
        elif any(word in response_lower for word in ['normal', 'stable', 'healthy']):
            severity = InsightSeverity.NORMAL

        return {
            "title": title or f"{insight_type.value.replace('_', ' ').title()} Analysis",
            "severity": severity,
            "summary": summary.strip() or "Analysis complete. See details below.",
            "full_analysis": full_analysis,
            "key_findings": key_findings or ["Analysis completed"],
            "recommendations": recommendations or ["No specific recommendations at this time"],
            "data_limitations": data_limitations.strip() or "All available data used in analysis.",
        }

    def _calculate_cost(self, message: Message) -> float:
        """
        Calculate API cost from a single message based on Claude Sonnet 4 pricing.

        Pricing (as of 2024):
        - Input: $3.00 per million tokens
        - Output: $15.00 per million tokens
        """
        return self._calculate_cost_from_tokens(
            message.usage.input_tokens,
            message.usage.output_tokens
        )

    def _calculate_cost_from_tokens(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate API cost from token counts based on Claude Sonnet 4 pricing.

        Pricing (as of 2024):
        - Input: $3.00 per million tokens
        - Output: $15.00 per million tokens
        """
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost


# Singleton instance
anthropic_provider = AnthropicProvider()
