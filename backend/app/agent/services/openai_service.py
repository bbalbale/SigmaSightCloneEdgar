"""
OpenAI service for agent chat functionality
"""
import json
import time
from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.agent.tools.tool_registry import tool_registry
from app.agent.prompts.prompt_manager import PromptManager
from app.agent.schemas.sse import (
    SSEStartEvent,
    SSEMessageEvent,
    SSETokenEvent,
    SSEToolStartedEvent,
    SSEToolFinishedEvent,
    SSEDoneEvent,
    SSEErrorEvent
)
from app.agent.services.rag_service import (
    retrieve_relevant_docs,
    format_rag_docs_for_prompt,
)
from app.agent.services.memory_service import (
    get_user_memories,
    format_memories_for_prompt,
)

logger = get_logger(__name__)


class OpenAIService:
    """Service for handling OpenAI API interactions"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.prompt_manager = PromptManager()
        self.model = settings.MODEL_DEFAULT
        self.fallback_model = settings.MODEL_FALLBACK
        self.deep_reasoning_model = settings.MODEL_DEEP_REASONING
        # Track tool call IDs for correlation between OpenAI and our system
        self.tool_call_id_map: Dict[str, Dict[str, Any]] = {}
        # RAG configuration (from settings)
        self.rag_enabled = settings.RAG_ENABLED
        self.rag_doc_limit = settings.RAG_DOC_LIMIT
        self.rag_max_chars = settings.RAG_MAX_CHARS
        # Smart routing configuration
        self.smart_routing_enabled = settings.SMART_ROUTING_ENABLED
        self.default_reasoning_effort = settings.DEFAULT_REASONING_EFFORT
        self.default_text_verbosity = settings.DEFAULT_TEXT_VERBOSITY
        # Web search configuration
        self.web_search_enabled = settings.WEB_SEARCH_ENABLED

        # Keywords for smart routing classification
        self._deep_reasoning_keywords = [
            "deep dive", "investment thesis", "thesis", "compare scenarios",
            "root cause", "analysis of", "evaluate", "comprehensive",
            "multi-step", "strategic", "long-term", "scenario analysis",
            "risk assessment", "due diligence", "fundamental analysis",
            "valuation", "intrinsic value", "dcf", "discounted cash flow"
        ]
        self._web_search_keywords = [
            "today", "recent", "latest", "news", "current", "now",
            "this week", "this month", "yesterday", "what happened",
            "breaking", "update", "announcement", "earnings report",
            "market news", "fed", "interest rate", "inflation",
            "morning briefing", "morning brief", "morning update", "morning meeting"
        ]

    async def _get_rag_context(
        self,
        db: Optional[AsyncSession],
        query: str,
        portfolio_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Retrieve relevant RAG documents and format them for prompt injection.

        Args:
            db: Async database session (if None, RAG is skipped)
            query: The user's query to search for
            portfolio_context: Optional portfolio context for scope filtering

        Returns:
            Formatted RAG context string, or empty string if no docs found
        """
        if not self.rag_enabled or db is None:
            return ""

        try:
            # Build scopes for filtering
            scopes = ["global"]

            # Add portfolio-specific scope if available
            if portfolio_context and portfolio_context.get("portfolio_id"):
                scopes.append(f"portfolio:{portfolio_context['portfolio_id']}")
            if portfolio_context and portfolio_context.get("portfolio_ids"):
                for pid in portfolio_context.get("portfolio_ids"):
                    scopes.append(f"portfolio:{pid}")

            # Add page-specific scope if available
            if portfolio_context and portfolio_context.get("page_hint"):
                scopes.append(f"page:{portfolio_context['page_hint']}")
            # Add route-specific scope if available (more granular than page_hint)
            if portfolio_context and portfolio_context.get("route"):
                scopes.append(f"route:{portfolio_context['route']}")

            # Retrieve relevant documents
            docs = await retrieve_relevant_docs(
                db,
                query=query,
                scopes=scopes,
                limit=self.rag_doc_limit,
            )

            if not docs:
                logger.debug(f"[RAG] No relevant docs found for query")
                return ""

            # Format docs for prompt injection
            rag_context = format_rag_docs_for_prompt(docs, max_chars=self.rag_max_chars)
            logger.info(f"[RAG] Injecting {len(docs)} docs ({len(rag_context)} chars) into prompt")

            return rag_context

        except Exception as e:
            logger.warning(f"[RAG] Failed to retrieve context: {e}")
            return ""

    async def _get_user_memories_context(
        self,
        db: Optional[AsyncSession],
        auth_context: Optional[Dict[str, Any]] = None,
        portfolio_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Retrieve user memories and format them for prompt injection.

        Args:
            db: Async database session (if None, memories are skipped)
            auth_context: Authentication context with user_id
            portfolio_context: Optional portfolio context for portfolio-scoped memories

        Returns:
            Formatted memories context string, or empty string if no memories
        """
        if db is None or auth_context is None:
            return ""

        user_id = auth_context.get("user_id")
        if not user_id:
            return ""

        try:
            from uuid import UUID
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

            # Get user memories (general + portfolio-specific if available)
            memories = await get_user_memories(db, user_uuid, limit=10)

            # Also get portfolio-specific memories if we have a portfolio context
            if portfolio_context and portfolio_context.get("portfolio_id"):
                portfolio_id = portfolio_context["portfolio_id"]
                portfolio_uuid = UUID(portfolio_id) if isinstance(portfolio_id, str) else portfolio_id
                portfolio_memories = await get_user_memories(
                    db, user_uuid, portfolio_id=portfolio_uuid, limit=5
                )
                # Combine, avoiding duplicates
                existing_ids = {m["id"] for m in memories}
                for pm in portfolio_memories:
                    if pm["id"] not in existing_ids:
                        memories.append(pm)

            if not memories:
                logger.debug("[Memory] No memories found for user")
                return ""

            # Format memories for prompt injection
            memories_context = format_memories_for_prompt(memories, max_chars=1000)
            logger.info(f"[Memory] Injecting {len(memories)} memories ({len(memories_context)} chars) into prompt")

            return memories_context

        except Exception as e:
            logger.warning(f"[Memory] Failed to retrieve memories: {e}")
            return ""

    async def _get_portfolio_data_context(
        self,
        db: Optional[AsyncSession],
        portfolio_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Pre-fetch portfolio data to inject into chat context.

        Includes:
        - Portfolio holdings summary
        - Risk metrics (analytics overview)
        - Factor exposures
        - Most recent morning briefing

        Returns formatted context string for prompt injection.
        """
        if not portfolio_context:
            return ""

        portfolio_id = portfolio_context.get("portfolio_id")
        if not portfolio_id:
            return ""

        context_parts = []

        try:
            # Create a minimal tool context for calling handlers
            tool_context = {
                "portfolio_id": portfolio_id,
                "portfolio_ids": portfolio_context.get("portfolio_ids", [portfolio_id]),
            }

            # 1. Fetch portfolio holdings summary
            try:
                from app.agent.tools.tool_registry import tool_registry

                holdings_result = await tool_registry.dispatch_tool_call(
                    "get_portfolio_complete",
                    {"portfolio_id": portfolio_id},
                    tool_context
                )

                if holdings_result and not holdings_result.get("error"):
                    # Format holdings summary
                    holdings_summary = self._format_holdings_summary(holdings_result)
                    if holdings_summary:
                        context_parts.append(holdings_summary)
                        logger.debug(f"[PortfolioContext] Added holdings summary ({len(holdings_summary)} chars)")
            except Exception as e:
                logger.warning(f"[PortfolioContext] Failed to fetch holdings: {e}")

            # 2. Fetch analytics overview (risk metrics)
            try:
                analytics_result = await tool_registry.dispatch_tool_call(
                    "get_analytics_overview",
                    {"portfolio_id": portfolio_id},
                    tool_context
                )

                if analytics_result and not analytics_result.get("error"):
                    analytics_summary = self._format_analytics_summary(analytics_result)
                    if analytics_summary:
                        context_parts.append(analytics_summary)
                        logger.debug(f"[PortfolioContext] Added analytics summary ({len(analytics_summary)} chars)")
            except Exception as e:
                logger.warning(f"[PortfolioContext] Failed to fetch analytics: {e}")

            # 3. Fetch factor exposures
            try:
                factors_result = await tool_registry.dispatch_tool_call(
                    "get_factor_exposures",
                    {"portfolio_id": portfolio_id},
                    tool_context
                )

                if factors_result and not factors_result.get("error"):
                    factors_summary = self._format_factors_summary(factors_result)
                    if factors_summary:
                        context_parts.append(factors_summary)
                        logger.debug(f"[PortfolioContext] Added factors summary ({len(factors_summary)} chars)")
            except Exception as e:
                logger.warning(f"[PortfolioContext] Failed to fetch factor exposures: {e}")

            # 4. Fetch most recent morning briefing
            if db:
                try:
                    from sqlalchemy import select
                    from app.models.ai_insights import AIInsight, InsightType
                    from uuid import UUID as UUIDType

                    portfolio_uuid = UUIDType(portfolio_id) if isinstance(portfolio_id, str) else portfolio_id

                    result = await db.execute(
                        select(AIInsight)
                        .where(AIInsight.portfolio_id == portfolio_uuid)
                        .where(AIInsight.insight_type == InsightType.MORNING_BRIEFING)
                        .order_by(AIInsight.created_at.desc())
                        .limit(1)
                    )
                    latest_briefing = result.scalar_one_or_none()

                    if latest_briefing:
                        briefing_summary = self._format_briefing_summary(latest_briefing)
                        if briefing_summary:
                            context_parts.append(briefing_summary)
                            logger.debug(f"[PortfolioContext] Added morning briefing ({len(briefing_summary)} chars)")
                except Exception as e:
                    logger.warning(f"[PortfolioContext] Failed to fetch morning briefing: {e}")

            if not context_parts:
                return ""

            # Combine all context parts
            full_context = "\n\n".join(context_parts)
            logger.info(f"[PortfolioContext] Injecting portfolio context ({len(full_context)} chars)")
            return full_context

        except Exception as e:
            logger.warning(f"[PortfolioContext] Failed to build portfolio context: {e}")
            return ""

    def _format_holdings_summary(self, holdings_data: Dict[str, Any]) -> str:
        """Format portfolio holdings for context injection."""
        try:
            positions = holdings_data.get("positions", [])
            if not positions:
                return ""

            lines = ["### Current Portfolio Holdings"]
            lines.append(f"Total positions: {len(positions)}")

            # Summarize top positions by market value
            sorted_positions = sorted(
                [p for p in positions if p.get("market_value")],
                key=lambda x: abs(x.get("market_value", 0)),
                reverse=True
            )[:10]  # Top 10

            if sorted_positions:
                lines.append("\n**Top Holdings:**")
                for p in sorted_positions:
                    symbol = p.get("symbol", "N/A")
                    qty = p.get("quantity", 0)
                    mv = p.get("market_value", 0)
                    daily_pnl = p.get("daily_pnl_dollar", 0)
                    lines.append(f"- {symbol}: {qty:,.0f} shares, ${mv:,.0f} value, ${daily_pnl:+,.0f} today")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"[PortfolioContext] Error formatting holdings: {e}")
            return ""

    def _format_analytics_summary(self, analytics_data: Dict[str, Any]) -> str:
        """Format analytics/risk metrics for context injection."""
        try:
            lines = ["### Portfolio Risk Metrics"]

            # Portfolio-level metrics
            if analytics_data.get("portfolio_beta"):
                lines.append(f"- Portfolio Beta: {analytics_data['portfolio_beta']:.2f}")
            if analytics_data.get("total_value"):
                lines.append(f"- Total Market Value: ${analytics_data['total_value']:,.0f}")
            if analytics_data.get("daily_pnl"):
                lines.append(f"- Daily P&L: ${analytics_data['daily_pnl']:+,.0f}")
            if analytics_data.get("volatility"):
                lines.append(f"- Portfolio Volatility: {analytics_data['volatility']:.1%}")
            if analytics_data.get("sharpe_ratio"):
                lines.append(f"- Sharpe Ratio: {analytics_data['sharpe_ratio']:.2f}")

            # Sector exposure if available
            sectors = analytics_data.get("sector_exposure", {})
            if sectors:
                lines.append("\n**Sector Exposure:**")
                for sector, weight in sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:5]:
                    lines.append(f"- {sector}: {weight:.1%}")

            return "\n".join(lines) if len(lines) > 1 else ""
        except Exception as e:
            logger.warning(f"[PortfolioContext] Error formatting analytics: {e}")
            return ""

    def _format_factors_summary(self, factors_data: Dict[str, Any]) -> str:
        """Format factor exposures for context injection."""
        try:
            exposures = factors_data.get("exposures", factors_data.get("factor_exposures", {}))
            if not exposures:
                return ""

            lines = ["### Factor Exposures"]

            # Handle different data formats
            if isinstance(exposures, list):
                for factor in exposures[:5]:
                    name = factor.get("factor_name", factor.get("name", "Unknown"))
                    beta = factor.get("beta", factor.get("exposure", 0))
                    lines.append(f"- {name}: {beta:+.2f}")
            elif isinstance(exposures, dict):
                for name, beta in list(exposures.items())[:5]:
                    if isinstance(beta, (int, float)):
                        lines.append(f"- {name}: {beta:+.2f}")

            return "\n".join(lines) if len(lines) > 1 else ""
        except Exception as e:
            logger.warning(f"[PortfolioContext] Error formatting factors: {e}")
            return ""

    def _format_briefing_summary(self, briefing: Any) -> str:
        """Format the most recent morning briefing for context injection."""
        try:
            lines = ["### Latest Morning Briefing"]
            lines.append(f"*Generated: {briefing.created_at.strftime('%Y-%m-%d %H:%M')}*")

            if briefing.title:
                lines.append(f"\n**{briefing.title}**")

            if briefing.summary:
                lines.append(f"\n{briefing.summary}")

            # Add key findings if available
            if briefing.key_findings:
                findings = briefing.key_findings if isinstance(briefing.key_findings, list) else []
                if findings:
                    lines.append("\n**Key Findings:**")
                    for finding in findings[:5]:
                        if isinstance(finding, str):
                            lines.append(f"- {finding}")
                        elif isinstance(finding, dict):
                            lines.append(f"- {finding.get('text', finding.get('finding', str(finding)))}")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"[PortfolioContext] Error formatting briefing: {e}")
            return ""

    def _classify_query(self, query: str) -> Dict[str, Any]:
        """
        Classify a query to determine optimal routing parameters.

        Returns a dict with:
        - model: which model to use
        - reasoning_effort: none, low, medium, high, xhigh
        - text_verbosity: low, medium, high
        - use_web_search: whether to enable web_search tool
        """
        query_lower = query.lower()

        # Default routing parameters
        routing = {
            "model": self.model,
            "reasoning_effort": self.default_reasoning_effort,
            "text_verbosity": self.default_text_verbosity,
            "use_web_search": False,
        }

        if not self.smart_routing_enabled:
            return routing

        # Check for deep reasoning keywords
        needs_deep_reasoning = any(kw in query_lower for kw in self._deep_reasoning_keywords)

        # Check for web search keywords
        needs_web_search = any(kw in query_lower for kw in self._web_search_keywords)

        # Detect question complexity by length and structure
        word_count = len(query.split())
        has_multiple_questions = query.count("?") > 1
        is_complex = word_count > 50 or has_multiple_questions

        # Route based on classification
        if needs_deep_reasoning or is_complex:
            routing["model"] = self.deep_reasoning_model
            routing["reasoning_effort"] = "high"
            routing["text_verbosity"] = "high"
            logger.info(f"[ROUTING] Deep reasoning mode: {query[:50]}...")
        elif needs_web_search:
            routing["reasoning_effort"] = "medium"
            routing["use_web_search"] = self.web_search_enabled
            logger.info(f"[ROUTING] Web search mode: {query[:50]}...")
        else:
            # Default: balanced mode for typical portfolio questions
            routing["reasoning_effort"] = "medium"
            routing["text_verbosity"] = "medium"

        return routing

    async def _execute_tool_call(
        self,
        tool_call_id: str,
        function_name: str,
        function_args: Dict[str, Any],
        conversation_id: str,
        portfolio_context: Optional[Dict[str, Any]],
        auth_context: Optional[Dict[str, Any]],
        run_id: str,
        seq: int
    ) -> AsyncGenerator[str, None]:
        """
        Execute a single tool call and yield SSE events.

        This is extracted to allow reuse in both initial stream and continuation loops.

        Yields:
            SSE events for tool_call and tool_result
        """
        from app.agent.tools.tool_registry import tool_registry

        # Auto-inject portfolio context when missing
        portfolio_tools = {
            "get_portfolio_complete", "get_portfolio_snapshot", "get_portfolio_overview",
            "get_positions_details", "get_analytics_overview", "get_factor_exposures",
            "get_sector_exposure", "get_daily_movers", "get_concentration_metrics",
            "get_volatility_analysis", "get_correlation_matrix", "get_stress_test_results",
            "get_target_prices", "get_position_tags"
        }

        if function_name in portfolio_tools and portfolio_context:
            primary_pid = portfolio_context.get("portfolio_id")
            fallback_pids = portfolio_context.get("portfolio_ids") or []
            candidate_pids = []
            if primary_pid:
                candidate_pids.append(primary_pid)
            if fallback_pids:
                candidate_pids.extend([pid for pid in fallback_pids if pid not in candidate_pids])

            if len(candidate_pids) == 1:
                chosen = candidate_pids[0]
                if not function_args.get("portfolio_id") or function_args.get("portfolio_id") == "default":
                    function_args["portfolio_id"] = chosen
                    logger.info(f"[TOOL] Injected portfolio_id={chosen} for tool {function_name}")
            elif len(candidate_pids) > 1:
                if not function_args.get("portfolio_ids"):
                    function_args["portfolio_ids"] = candidate_pids
                if function_args.get("portfolio_id") == "default":
                    del function_args["portfolio_id"]

        # Emit tool_call event
        tool_call_payload = {
            "type": "tool_call",
            "run_id": run_id,
            "seq": seq,
            "data": {
                "tool_call_id": tool_call_id,
                "tool_name": function_name,
                "tool_args": function_args
            },
            "timestamp": int(time.time() * 1000)
        }
        yield f"event: tool_call\ndata: {json.dumps(tool_call_payload)}\n\n"

        # Execute tool
        logger.info(f"[TOOL] Executing tool call - ID: {tool_call_id}, Tool: {function_name}")
        start_time = time.time()

        try:
            # Build context for tool execution
            tool_context = {
                "conversation_id": conversation_id,
                "portfolio_context": portfolio_context,
                "request_id": f"{conversation_id}_{tool_call_id}"
            }

            if auth_context:
                tool_context.update(auth_context)

            result = await tool_registry.dispatch_tool_call(function_name, function_args, tool_context)
            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(f"[OK] Tool call completed - ID: {tool_call_id}, Tool: {function_name}, Duration: {duration_ms}ms")

            # Emit tool_result event
            tool_result_payload = {
                "type": "tool_result",
                "run_id": run_id,
                "seq": seq + 1,
                "data": {
                    "tool_call_id": tool_call_id,
                    "tool_name": function_name,
                    "tool_result": result,
                    "duration_ms": duration_ms
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: tool_result\ndata: {json.dumps(tool_result_payload)}\n\n"

            # Return result for accumulation (stored in result attribute)
            yield json.dumps({"_result": result, "_tool_call_id": tool_call_id})

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[ERROR] Tool call failed - ID: {tool_call_id}, Tool: {function_name}, Error: {e}")

            error_result = {
                "error": str(e),
                "tool_call_id": tool_call_id,
                "tool_name": function_name
            }

            tool_error_payload = {
                "type": "tool_result",
                "run_id": run_id,
                "seq": seq + 1,
                "data": {
                    "tool_call_id": tool_call_id,
                    "tool_name": function_name,
                    "tool_result": error_result,
                    "duration_ms": duration_ms
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: tool_result\ndata: {json.dumps(tool_error_payload)}\n\n"

            yield json.dumps({"_result": error_result, "_tool_call_id": tool_call_id})

    def _get_tool_definitions(self, include_web_search: bool = False) -> List[Dict[str, Any]]:
        """Default tool definitions method - delegates to Responses API format"""
        return self._get_tool_definitions_responses(include_web_search=include_web_search)

    def _get_tool_definitions_responses(self, include_web_search: bool = False) -> List[Dict[str, Any]]:
        """
        Convert our tool definitions to Responses API format (with full schemas).

        Args:
            include_web_search: If True, include OpenAI's built-in web_search tool
        """
        tools = [
            # ===== Multi-Portfolio Discovery Tool =====
            {
                "name": "list_user_portfolios",
                "type": "function",
                "description": "List ALL portfolios for the authenticated user. Returns portfolio names, IDs, descriptions, and position counts. USE THIS TOOL FIRST when: (1) user asks about 'all my portfolios' or 'my portfolios', (2) user wants to compare portfolios, (3) user asks about aggregate holdings across accounts, (4) user asks a question without specifying which portfolio. After getting the list, use the portfolio_id from the results to query specific portfolios with other tools.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            # ===== Core Portfolio Data Tools =====
            {
                "name": "get_portfolio_complete",
                "type": "function",
                "description": "Get comprehensive portfolio snapshot with ALL positions, their symbols, quantities, market values, and weights. Returns: portfolio total value, cash balance, and a list of all holdings with symbol, quantity, entry_price, current_price, market_value, weight_pct, sector, and P&L. USE THIS TOOL FIRST when asked about portfolio holdings, biggest positions, sector exposure, or portfolio composition.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        },
                        "include_holdings": {
                            "type": "boolean",
                            "description": "Include position details (always True for position questions)",
                            "default": True
                        },
                        "include_timeseries": {
                            "type": "boolean",
                            "description": "Include historical data",
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
                "type": "function",
                "description": "Get detailed position-level information with P&L calculations. Returns for each position: symbol, quantity, entry_price, current_price, market_value, cost_basis, unrealized_pnl, unrealized_pnl_pct, sector, industry. Use when asked about specific positions or detailed P&L breakdown.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        },
                        "position_ids": {
                            "type": "string",
                            "description": "Comma-separated position IDs (optional, gets all if omitted)"
                        },
                        "include_closed": {
                            "type": "boolean",
                            "description": "Include closed positions",
                            "default": False
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_portfolio_data_quality",
                "type": "function",
                "description": "Assess portfolio data completeness and quality metrics. Returns data quality score, available analyses, and any missing data warnings.",
                "parameters": {
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
                            "description": "Check correlation data",
                            "default": True
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            # ===== Market Data Tools =====
            {
                "name": "get_prices_historical",
                "type": "function",
                "description": "Retrieve historical price data for portfolio symbols. Returns daily OHLCV data for top holdings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        },
                        "lookback_days": {
                            "type": "integer",
                            "description": "Days of history (max 180)",
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
                "type": "function",
                "description": "Get real-time market quotes for specified symbols. Returns current price, change, change_pct, volume, bid, ask.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "string",
                            "description": "Comma-separated symbols (max 5)"
                        },
                        "include_options": {
                            "type": "boolean",
                            "description": "Include options data",
                            "default": False
                        }
                    },
                    "required": ["symbols"]
                }
            },
            {
                "name": "get_factor_etf_prices",
                "type": "function",
                "description": "Get historical prices for factor ETFs (SPY, VTV, VUG, MTUM, QUAL, SLY, USMV). Use for factor analysis and benchmark comparison.",
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
                            "description": "Comma-separated factor names (e.g., 'SPY,VTV,MTUM')"
                        }
                    },
                    "required": []
                }
            },
            # ===== Analytics Tools =====
            {
                "name": "get_analytics_overview",
                "type": "function",
                "description": "Get portfolio analytics overview including total value, returns, beta, volatility, Sharpe ratio, and sector breakdown.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_factor_exposures",
                "type": "function",
                "description": "Get portfolio factor exposures (Market, Size, Value, Momentum, Quality, Low Volatility). Returns factor betas and R-squared.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_sector_exposure",
                "type": "function",
                "description": "Get detailed sector exposure breakdown vs S&P 500 benchmark. Returns sector weights, over/underweights, and top holdings per sector.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_correlation_matrix",
                "type": "function",
                "description": "Get correlation matrix for portfolio positions. Shows how positions move relative to each other.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_stress_test_results",
                "type": "function",
                "description": "Get stress test results showing portfolio impact under various market scenarios (e.g., 2008 crisis, COVID crash, rate hikes).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_concentration_metrics",
                "type": "function",
                "description": "Get portfolio concentration metrics including HHI (Herfindahl-Hirschman Index), top position weights, and concentration risk scores.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_volatility_analysis",
                "type": "function",
                "description": "Get portfolio volatility analysis including historical volatility, VaR (Value at Risk), and HAR volatility forecasts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            # ===== Reference Data Tools =====
            {
                "name": "get_company_profile",
                "type": "function",
                "description": "Get company profile information including name, sector, industry, market cap, description, and key financials.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "Stock symbol (e.g., 'AAPL')"
                        }
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "get_target_prices",
                "type": "function",
                "description": "Get analyst target prices for positions in the portfolio.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_position_tags",
                "type": "function",
                "description": "Get tags/labels assigned to portfolio positions (e.g., 'growth', 'dividend', 'core holding').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            # ===== Daily Insight Tools (December 15, 2025) =====
            {
                "name": "get_daily_movers",
                "type": "function",
                "description": "Get today's biggest movers (gainers and losers) in the portfolio. Returns positions sorted by daily change percentage, portfolio daily P&L, biggest winner and loser. USE THIS FIRST for daily insights or when asked 'what moved today?' or 'how did my portfolio do today?'",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        },
                        "threshold_pct": {
                            "type": "number",
                            "description": "Minimum absolute % change to include (default 2.0)",
                            "default": 2.0
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_market_news",
                "type": "function",
                "description": "Get market news relevant to portfolio positions. Returns news headlines, sources, and sentiment for symbols. Use for daily insights or when asked about news affecting the portfolio.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "string",
                            "description": "Comma-separated symbols (e.g., 'AAPL,MSFT,GOOGL')"
                        },
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID (alternative to symbols - gets news for top holdings)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum news items (default 10, max 25)",
                            "default": 10
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_morning_briefing",
                "type": "function",
                "description": "Get the most recent morning briefing for the portfolio. Returns the AI-generated morning meeting analysis including: title, summary, key findings (top movers, news, watch items), and recommendations. Use when: (1) user asks 'what did the briefing say?' or 'what's in the morning briefing?', (2) you want to reference specific analysis from today's briefing, (3) user asks about recent performance summary.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            }
        ]

        # Add OpenAI's built-in web_search tool if requested
        if include_web_search and self.web_search_enabled:
            tools.append({
                "type": "web_search"
            })
            logger.info("[TOOLS] web_search tool enabled for this request")

        return tools

    def _validate_tool_call_format(self, tool_call: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate and fix tool call format to ensure OpenAI API compliance.
        
        Args:
            tool_call: Tool call dictionary from message history
            
        Returns:
            Fixed tool call dictionary or None if invalid
        """
        try:
            # Ensure required fields exist
            if not isinstance(tool_call, dict):
                logger.warning(f"Tool call is not a dictionary: {type(tool_call)}")
                return None
            
            # Generate ID if missing
            tool_call_id = tool_call.get("id")
            if not tool_call_id or not isinstance(tool_call_id, str):
                tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
                logger.warning(f"Generated missing tool call ID: {tool_call_id}")
            
            # Ensure type is 'function'
            tool_type = tool_call.get("type", "function")
            if tool_type != "function":
                logger.warning(f"Invalid tool call type: {tool_type}, setting to 'function'")
                tool_type = "function"
            
            # Validate function object
            function = tool_call.get("function", {})
            if not isinstance(function, dict):
                logger.warning(f"Tool call function is not a dictionary: {type(function)}")
                function = {}
            
            # CRITICAL: Ensure function.name is a string
            function_name = function.get("name")
            if not function_name or not isinstance(function_name, str):
                logger.warning(f"Invalid function name: {function_name} (type: {type(function_name)})")
                function_name = "unknown_tool"  # Fallback to valid string
            
            # Ensure arguments is a string (JSON-encoded)
            arguments = function.get("arguments")
            if arguments is None:
                arguments = "{}"
            elif not isinstance(arguments, str):
                # If arguments is a dict, JSON encode it
                if isinstance(arguments, dict):
                    arguments = json.dumps(arguments)
                else:
                    logger.warning(f"Invalid arguments type: {type(arguments)}, setting to empty dict")
                    arguments = "{}"
            
            # Return validated tool call
            return {
                "id": tool_call_id,
                "type": tool_type,
                "function": {
                    "name": function_name,
                    "arguments": arguments
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating tool call format: {e}")
            return None
    
    def _build_messages(
        self, 
        conversation_mode: str, 
        message_history: List[Dict[str, Any]], 
        user_message: str,
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> List[ChatCompletionMessageParam]:
        """Build message array for OpenAI API"""
        # Get system prompt for the mode
        system_prompt = self.prompt_manager.get_system_prompt(
            conversation_mode,
            user_context=portfolio_context
        )

        # Inject UI context explicitly so the model can tailor tools/RAG
        if portfolio_context:
            ui_context_lines = []
            page_hint = portfolio_context.get("page_hint")
            route = portfolio_context.get("route")
            portfolio_id = portfolio_context.get("portfolio_id")
            selection = portfolio_context.get("selection")

            if page_hint:
                ui_context_lines.append(f"Page: {page_hint}")
            if route:
                ui_context_lines.append(f"Route: {route}")
            if portfolio_id:
                ui_context_lines.append(f"Portfolio ID: {portfolio_id}")
            if portfolio_context and portfolio_context.get("portfolio_ids"):
                try:
                    portfolio_ids_str = ", ".join([str(pid) for pid in portfolio_context.get("portfolio_ids")])
                except Exception:
                    portfolio_ids_str = str(portfolio_context.get("portfolio_ids"))
                ui_context_lines.append(f"Portfolio IDs: {portfolio_ids_str}")
            if selection:
                try:
                    selection_str = json.dumps(selection, ensure_ascii=False)
                except Exception:
                    selection_str = str(selection)
                ui_context_lines.append(f"Selection: {selection_str}")

            if ui_context_lines:
                ui_context_section = "\n".join(ui_context_lines)
                system_prompt = system_prompt + "\n---\n\n## UI Context\n\n" + ui_context_section + "\n\n---\n"
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in message_history:
            if msg["role"] in ["user", "assistant"]:
                # Check if this assistant message has tool calls
                if msg["role"] == "assistant" and msg.get("tool_calls"):
                    logger.debug(f"Skipping assistant message with tool calls to avoid incomplete sequences")
                    # Only include the text content, skip tool calls entirely
                    if msg.get("content") and msg["content"].strip():
                        messages.append({
                            "role": "assistant",
                            "content": msg["content"]
                        })
                    # Skip messages that only have tool calls with no content
                    continue
                else:
                    # Regular user message or assistant message without tool calls
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _build_responses_input(
        self,
        conversation_mode: str,
        message_history: List[Dict[str, Any]],
        user_message: str,
        portfolio_context: Optional[Dict[str, Any]] = None,
        rag_context: Optional[str] = None,
        memories_context: Optional[str] = None,
        portfolio_data_context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Build input structure for OpenAI Responses API (array of messages)"""
        # Get system prompt for the mode
        system_prompt = self.prompt_manager.get_system_prompt(
            conversation_mode,
            user_context=portfolio_context
        )

        # Inject portfolio data context FIRST (highest priority - always available)
        if portfolio_data_context:
            portfolio_section = f"""
---

## Current Portfolio Context

The following is real-time data about the user's portfolio. Use this information to provide informed, contextual responses:

{portfolio_data_context}

---
"""
            system_prompt = system_prompt + "\n" + portfolio_section
            logger.debug(f"[PortfolioData] Added {len(portfolio_data_context)} chars of portfolio data to system prompt")

        # Inject user memories if available (before RAG for higher priority)
        if memories_context:
            memories_section = f"""
---

## User Preferences & Context

Things to remember about this user (apply these to your responses):

{memories_context}

---
"""
            system_prompt = system_prompt + "\n" + memories_section
            logger.debug(f"[Memory] Added {len(memories_context)} chars of memories to system prompt")

        # Inject RAG context if available
        if rag_context:
            rag_section = f"""
---

## Relevant Knowledge Base Context

The following documents may be relevant to the user's question. Use this information to provide more accurate and informed responses:

{rag_context}

---
"""
            # Insert RAG context after the system prompt header
            system_prompt = system_prompt + "\n" + rag_section
            logger.debug(f"[RAG] Added {len(rag_context)} chars of RAG context to system prompt")

        # [TRACE] PROMPT-CHECK System Prompt (Phase 9.12.1 investigation)
        logger.info(f"[TRACE] PROMPT-CHECK: {system_prompt[:200]}...")

        # Build message history for input (starting with system message)
        messages = []

        # Add system message first (Responses API format)
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # Add conversation history (user/assistant pairs)
        for msg in message_history:
            if msg["role"] in ["user", "assistant"]:
                # Check if this assistant message has tool calls
                if msg["role"] == "assistant" and msg.get("tool_calls"):
                    logger.debug(f"Skipping assistant message with tool calls in Responses API input")
                    # Only include the text content, skip tool calls entirely
                    if msg.get("content") and msg["content"].strip():
                        messages.append({
                            "role": "assistant",
                            "content": msg["content"]
                        })
                    # Skip messages that only have tool calls with no content
                    continue
                else:
                    # Regular user message or assistant message without tool calls
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                # Note: We skip tool_calls from history as Responses manages tools per-turn
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Return array of messages for Responses API
        return messages
    
    async def stream_responses(
        self,
        conversation_id: str,
        conversation_mode: str,
        message_text: str,
        message_history: List[Dict[str, Any]] = None,
        portfolio_context: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        auth_context: Optional[Dict[str, Any]] = None,
        model_override: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream responses using OpenAI Responses API with proper tool execution handshake

        Args:
            conversation_id: Conversation UUID
            conversation_mode: Mode for prompt selection (e.g., 'green', 'blue')
            message_text: User's message text
            message_history: Previous conversation messages
            portfolio_context: Portfolio context dict with portfolio_id, etc.
            run_id: Optional run ID for tracing
            auth_context: Authentication context
            model_override: Optional model override
            db: Optional database session for RAG context retrieval

        Yields SSE formatted events with standardized contract (type, run_id, seq fields)
        """
        run_id = run_id or str(uuid.uuid4())
        seq = 0
        final_content_parts = []
        token_count_initial = 0
        token_count_continuation = 0

        try:
            # Smart routing: classify query to determine model/reasoning/tools
            routing = self._classify_query(message_text)
            model_to_use = model_override or routing["model"]
            reasoning_effort = routing["reasoning_effort"]
            text_verbosity = routing["text_verbosity"]
            use_web_search = routing["use_web_search"]

            logger.info(
                f"[ROUTING] model={model_to_use} reasoning={reasoning_effort} "
                f"verbosity={text_verbosity} web_search={use_web_search}"
            )

            # Retrieve RAG context before building input
            rag_context = await self._get_rag_context(
                db=db,
                query=message_text,
                portfolio_context=portfolio_context,
            )

            # Retrieve user memories for personalization
            memories_context = await self._get_user_memories_context(
                db=db,
                auth_context=auth_context,
                portfolio_context=portfolio_context,
            )

            # Pre-fetch portfolio data (holdings, risk metrics, factor exposures, latest briefing)
            portfolio_data_context = await self._get_portfolio_data_context(
                db=db,
                portfolio_context=portfolio_context,
            )

            # Build Responses API input with RAG, memories, and portfolio data context
            input_data = self._build_responses_input(
                conversation_mode,
                message_history or [],
                message_text,
                portfolio_context,
                rag_context=rag_context,
                memories_context=memories_context,
                portfolio_data_context=portfolio_data_context,
            )

            logger.info(
                f"[TRACE] START-PAYLOAD ctx={portfolio_context} rag={'yes' if rag_context else 'no'} memories={'yes' if memories_context else 'no'} portfolio_data={'yes' if portfolio_data_context else 'no'}"
            )

            # Get tool definitions for Responses API (with optional web_search)
            tools = self._get_tool_definitions_responses(include_web_search=use_web_search)
            
            # Yield start event with standardized format (includes routing info)
            start_payload = {
                "type": "start",
                "run_id": run_id,
                "seq": seq,
                "data": {
                    "conversation_id": conversation_id,
                    "mode": conversation_mode,
                    "model": model_to_use,
                    "reasoning_effort": reasoning_effort,
                    "text_verbosity": text_verbosity,
                    "web_search_enabled": use_web_search,
                    "page_hint": portfolio_context.get("page_hint") if portfolio_context else None,
                    "route": portfolio_context.get("route") if portfolio_context else None,
                    "portfolio_id": portfolio_context.get("portfolio_id") if portfolio_context else None,
                    "portfolio_ids": portfolio_context.get("portfolio_ids") if portfolio_context else None,
                },
                "timestamp": int(time.time() * 1000)
            }
            logger.info(f"[TRACE] START-EVENT payload={start_payload}")
            yield f"event: start\ndata: {json.dumps(start_payload)}\n\n"
            seq += 1
            
            # Call OpenAI Responses API with streaming
            # Note: reasoning.effort is NOT supported by GPT-5 series (gpt-5, gpt-5-mini, etc.)
            # Only o-series models (o1, o3, o4-mini) support reasoning.effort parameter
            # See: https://github.com/sst/opencode/issues/1859
            reasoning_supported_models = ["o1", "o3", "o3-mini", "o4-mini"]
            supports_reasoning = any(model_to_use.startswith(m) for m in reasoning_supported_models)

            create_params = {
                "model": model_to_use,
                "input": input_data,
                "tools": tools if tools else None,
                "stream": True,
                "text": {"format": {"type": "text"}, "verbosity": text_verbosity},
            }
            if supports_reasoning:
                create_params["reasoning"] = {"effort": reasoning_effort}

            stream = await self.client.responses.create(**create_params)
            
            # Track state for streaming
            current_content = ""
            tool_call_chunks = {}
            accumulated_tool_calls = {}
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = settings.SSE_HEARTBEAT_INTERVAL_MS / 1000.0
            
            # Store response ID for tool output submission
            response_id = None
            
            async for event in stream:
                # Check if we need to send a heartbeat
                current_time = asyncio.get_event_loop().time()
                if current_time - last_heartbeat > heartbeat_interval:
                    heartbeat_payload = {
                        "type": "heartbeat",
                        "run_id": run_id,
                        "seq": 0,  # Heartbeats don't increment sequence
                        "data": {},
                        "timestamp": int(time.time() * 1000)
                    }
                    yield f"event: heartbeat\ndata: {json.dumps(heartbeat_payload)}\n\n"
                    last_heartbeat = current_time
                
                # Handle Responses API events based on actual SDK event names
                try:
                    if event.type == "response.created":
                        # Capture response ID for tool output submission
                        response_id = event.response.id
                        logger.info(f"Response started with ID: {response_id}")
                        
                        # Emit response_id event for traceability (Phase 5.8.2.1)
                        response_id_payload = {
                            "type": "response_id",
                            "run_id": run_id,
                            "seq": seq,
                            "data": {
                                "response_id": response_id,
                                "provider": "openai"
                            },
                            "timestamp": int(time.time() * 1000)
                        }
                        yield f"event: response_id\ndata: {json.dumps(response_id_payload)}\n\n"
                        seq += 1
                        
                    elif event.type == "response.output_item.added":
                        # Phase 5.9.5.1: Early capture of function name and tool call metadata for better correlation
                        if hasattr(event, 'item') and hasattr(event.item, 'type') and event.item.type == "function_call":
                            function_name = event.item.name  # Fixed: name is directly on ResponseFunctionToolCall
                            tool_call_id = event.item.id
                            
                            # Store function name for later delta accumulation (prevents frontend 400 errors)
                            accumulated_tool_calls[tool_call_id] = {
                                "id": tool_call_id,
                                "type": "function",
                                "function": {"name": str(function_name), "arguments": ""}  # Ensure string type
                            }
                            logger.debug(f"[TOOL] Tool call item added - ID: {tool_call_id}, Function: {function_name}")
                        
                    elif event.type == "response.output_text.delta":
                        # Handle streaming text content -> emit token event
                        if hasattr(event, 'delta') and event.delta:
                            current_content += event.delta
                            final_content_parts.append(event.delta)
                            token_count_initial += 1
                            logger.debug(f"TOKEN-DEBUG(initial): run_id={run_id} seq={seq} len={len(event.delta)}")
                            
                            # Emit our standardized token event
                            token_payload = {
                                "type": "token",
                                "run_id": run_id,
                                "seq": seq,
                                "data": {"delta": event.delta},
                                "timestamp": int(time.time() * 1000)
                            }
                            yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                            seq += 1
                            
                    elif event.type == "response.output_text.done":
                        # Phase 5.9.5.3: Text output completed - useful for responses without tool calls
                        logger.debug(f"Text output completed for response {response_id}")
                        # Continue processing, don't break - might have more events
                            
                    elif event.type == "response.function_call_arguments.delta":
                        # Function call arguments streaming - accumulate deltas
                        tool_call_id = event.item_id  # Use item_id from Responses API
                        
                        # Initialize tool call if not exists
                        if tool_call_id not in accumulated_tool_calls:
                            # Need to get function name from event (assuming it's available)
                            function_name = getattr(event, 'function_name', 'unknown_function')
                            # Phase 5.9.5.4: Ensure function name is always a string (prevents frontend 400s)
                            function_name = str(function_name) if function_name else 'unknown_function'
                            logger.debug(f"[TOOL] Tool call arguments started - ID: {tool_call_id}, Tool: {function_name}")
                            
                            accumulated_tool_calls[tool_call_id] = {
                                "id": tool_call_id,
                                "type": "function", 
                                "function": {
                                    "name": function_name,  # Already ensured to be string above
                                    "arguments": ""
                                }
                            }
                            
                            # Track in ID mapping for correlation
                            self.tool_call_id_map[tool_call_id] = {
                                "openai_id": tool_call_id,
                                "run_id": run_id,
                                "conversation_id": conversation_id,
                                "started_at": int(time.time() * 1000),
                                "status": "streaming"
                            }
                        
                        # Accumulate arguments delta
                        if event.delta:
                            accumulated_tool_calls[tool_call_id]["function"]["arguments"] += event.delta
                            
                    elif event.type == "response.function_call_arguments.done":
                        # Tool call ready for execution
                        tool_call_id = event.item_id  # Use item_id from Responses API
                        if tool_call_id in accumulated_tool_calls:
                            tool_call = accumulated_tool_calls[tool_call_id]
                            function_name = tool_call["function"]["name"]
                            
                            # Parse function arguments
                            try:
                                raw_args = tool_call["function"]["arguments"]
                                logger.debug(f"Raw tool arguments for {function_name}: {raw_args!r}")
                                if isinstance(raw_args, str) and raw_args.strip():
                                    function_args = json.loads(raw_args)
                                else:
                                    function_args = {}
                                    logger.warning(f"Empty arguments for {function_name}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse tool arguments for {function_name}: {e}")
                                function_args = {"error": f"Parse error: {str(e)}"}

                            # Phase 5.9.5.4: Validate function_name is string BEFORE using it
                            validated_function_name = str(function_name) if function_name else 'unknown_function'

                            # Auto-inject portfolio context when missing
                            if validated_function_name in {"get_portfolio_complete", "get_portfolio_snapshot", "get_portfolio_overview", "get_positions_details", "get_analytics_overview", "get_factor_exposures", "get_sector_exposure", "get_daily_movers"}:
                                if portfolio_context:
                                    primary_pid = portfolio_context.get("portfolio_id")
                                    fallback_pids = portfolio_context.get("portfolio_ids") or []
                                    candidate_pids = []
                                    if primary_pid:
                                        candidate_pids.append(primary_pid)
                                    if fallback_pids:
                                        candidate_pids.extend([pid for pid in fallback_pids if pid not in candidate_pids])

                                    if len(candidate_pids) == 1:
                                        chosen = candidate_pids[0]
                                        if not function_args.get("portfolio_id") or function_args.get("portfolio_id") == "default":
                                            function_args["portfolio_id"] = chosen
                                            logger.info(f"[TOOL] Injected portfolio_id={chosen} for tool {validated_function_name}")
                                    elif len(candidate_pids) > 1:
                                        # Multi-portfolio: pass the list if caller didn't specify
                                        if not function_args.get("portfolio_ids"):
                                            function_args["portfolio_ids"] = candidate_pids
                                        if function_args.get("portfolio_id") == "default":
                                            del function_args["portfolio_id"]

                            # Emit tool_call event
                            tool_call_payload = {
                                "type": "tool_call",
                                "run_id": run_id,
                                "seq": seq,
                                "data": {
                                    "tool_call_id": tool_call_id,
                                    "tool_name": validated_function_name,  # Ensure string type for frontend
                                    "tool_args": function_args
                                },
                                "timestamp": int(time.time() * 1000)
                            }
                            yield f"event: tool_call\ndata: {json.dumps(tool_call_payload)}\n\n"
                            seq += 1
                            
                            # Execute tool
                            logger.info(f"[TOOL] Executing tool call - ID: {tool_call_id}, Tool: {function_name}")
                            start_time = time.time()
                            
                            try:
                                from app.agent.tools.tool_registry import tool_registry
                                
                                # Build context for tool execution
                                tool_context = {
                                    "conversation_id": conversation_id,
                                    "portfolio_context": portfolio_context,
                                    "request_id": f"{conversation_id}_{tool_call_id}"
                                }
                                
                                # Add authentication context if available
                                if auth_context:
                                    tool_context.update(auth_context)
                                
                                result = await tool_registry.dispatch_tool_call(function_name, function_args, tool_context)
                                duration_ms = int((time.time() - start_time) * 1000)
                                
                                logger.info(f"[OK] Tool call completed - ID: {tool_call_id}, Tool: {function_name}, Duration: {duration_ms}ms")
                                
                                # Emit tool_result event
                                tool_result_payload = {
                                    "type": "tool_result", 
                                    "run_id": run_id,
                                    "seq": seq,
                                    "data": {
                                        "tool_call_id": tool_call_id,
                                        "tool_name": function_name,
                                        "tool_result": result,
                                        "duration_ms": duration_ms
                                    },
                                    "timestamp": int(time.time() * 1000)
                                }
                                yield f"event: tool_result\ndata: {json.dumps(tool_result_payload)}\n\n"
                                seq += 1
                                
                                # Store tool result for conversation continuation
                                accumulated_tool_calls[tool_call_id]["result"] = result
                                
                            except Exception as e:
                                duration_ms = int((time.time() - start_time) * 1000)
                                logger.error(f"[ERROR] Tool call failed - ID: {tool_call_id}, Tool: {function_name}, Error: {e}")
                                
                                # Emit error result
                                error_result = {
                                    "error": str(e),
                                    "tool_call_id": tool_call_id,
                                    "tool_name": function_name
                                }
                                
                                tool_error_payload = {
                                    "type": "tool_result",
                                    "run_id": run_id, 
                                    "seq": seq,
                                    "data": {
                                        "tool_call_id": tool_call_id,
                                        "tool_name": function_name,
                                        "tool_result": error_result,
                                        "duration_ms": duration_ms
                                    },
                                    "timestamp": int(time.time() * 1000)
                                }
                                yield f"event: tool_result\ndata: {json.dumps(tool_error_payload)}\n\n"
                                seq += 1
                                
                                # Store error result for conversation continuation
                                accumulated_tool_calls[tool_call_id]["result"] = error_result
                                    
                    elif event.type == "response.completed":
                        # Response completed
                        logger.info(f"Response completed: {response_id}")
                        break
                        
                    elif event.type == "response.failed":
                        # Phase 5.9.5.2: Handle API failures gracefully instead of silent failures
                        error_message = str(getattr(event, 'error', 'Unknown API failure'))
                        logger.error(f"OpenAI API failure for response {response_id}: {error_message}")
                        
                        error_payload = {
                            "type": "error",
                            "run_id": run_id,
                            "seq": seq,
                            "data": {
                                "error": error_message,
                                "error_type": "api_failure",
                                "message": error_message,
                                "retryable": True
                            },
                            "timestamp": int(time.time() * 1000)
                        }
                        yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
                        break
                        
                    elif event.type == "response.incomplete":
                        # Phase 5.9.5.2: Handle timeout/incomplete responses
                        logger.error(f"OpenAI response incomplete/timed out for response {response_id}")
                        
                        error_payload = {
                            "type": "error",
                            "run_id": run_id,
                            "seq": seq,
                            "data": {
                                "error": "Response timed out or was incomplete",
                                "error_type": "incomplete_response",
                                "message": "Response timed out or was incomplete",
                                "retryable": True
                            },
                            "timestamp": int(time.time() * 1000)
                        }
                        yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
                        break

                    elif event.type in ("response.in_progress", "response.output_item.done"):
                        # Expected housekeeping events - log at debug level
                        logger.debug(f"[STREAM] Housekeeping event: {event.type}")
                        continue

                    else:
                        # Truly unknown event type - log for investigation but don't fail
                        logger.debug(f"[STREAM] Unhandled event type: {event.type}")
                        continue

                except Exception as event_error:
                    logger.error(f"Error processing Responses API event: {event_error} - event: {event}")
                    continue
            
            # After stream completes, if tools were called, continue with recursive tool loop
            # This loop handles sequential tool calls (e.g., list_portfolios -> get_portfolio_complete)
            max_tool_iterations = 5  # Safety limit to prevent infinite loops
            tool_iteration = 0

            while accumulated_tool_calls and tool_iteration < max_tool_iterations:
                tool_iteration += 1
                logger.info(f"🔄 Tool loop iteration {tool_iteration}: {len(accumulated_tool_calls)} tool results to process")

                # Build tool results summary (without re-sending system prompt)
                tool_summary_parts = []
                portfolio_tools_list = ["get_portfolio_complete", "get_positions_details", "get_portfolio_data_quality"]

                for tool_call in accumulated_tool_calls.values():
                    tool_name = tool_call["function"]["name"]
                    tool_result = tool_call.get("result", {})

                    # Determine truncation limit
                    if settings.TOOL_RESPONSE_TRUNCATE_ENABLED:
                        if tool_name in portfolio_tools_list:
                            max_chars = settings.TOOL_RESPONSE_PORTFOLIO_MAX_CHARS
                        else:
                            max_chars = settings.TOOL_RESPONSE_MAX_CHARS
                    else:
                        max_chars = None

                    # Format tool result
                    if isinstance(tool_result, dict) and "data" in tool_result:
                        full_json = json.dumps(tool_result["data"], indent=2)
                    else:
                        full_json = json.dumps(tool_result, indent=2)

                    data_summary = full_json[:max_chars] if max_chars else full_json

                    if max_chars and len(full_json) > max_chars:
                        logger.info(f"Tool response truncated: {tool_name} - {len(full_json)} chars -> {max_chars} chars")

                    tool_summary_parts.append(f"Tool '{tool_name}' returned:\n{data_summary}")

                tool_summary = "\n\n".join(tool_summary_parts)

                # Build MINIMAL continuation input - NO system prompt re-send!
                # Only include: original user message + tool results as assistant context
                continuation_input = [
                    {
                        "role": "user",
                        "content": message_text  # Original user query
                    },
                    {
                        "role": "assistant",
                        "content": f"I've gathered the following data from tools:\n\n{tool_summary}"
                    },
                    {
                        "role": "user",
                        "content": "Based on this data, please provide a comprehensive analysis and answer."
                    }
                ]

                # Clear accumulated tool calls for this iteration
                accumulated_tool_calls = {}
                cont_tool_calls = {}  # Track new tool calls in continuation

                try:
                    logger.info(f"[CONTINUATION] Starting call {tool_iteration} with {len(continuation_input)} messages (no system prompt)")
                    logger.debug(f"[CONTINUATION] Tool summary: {len(tool_summary)} chars")

                    # Build continuation params (reasoning only for supported models)
                    cont_params = {
                        "model": model_to_use,
                        "input": continuation_input,
                        "tools": tools if tools else None,
                        "stream": True,
                        "text": {"format": {"type": "text"}, "verbosity": text_verbosity},
                    }
                    if supports_reasoning:
                        cont_params["reasoning"] = {"effort": reasoning_effort}

                    continuation_stream = await self.client.responses.create(**cont_params)

                    cont_event_count = 0
                    cont_has_text_output = False

                    async for cont_event in continuation_stream:
                        cont_event_count += 1

                        # Heartbeat
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_heartbeat > heartbeat_interval:
                            heartbeat_payload = {
                                "type": "heartbeat",
                                "run_id": run_id,
                                "seq": 0,
                                "data": {},
                                "timestamp": int(time.time() * 1000)
                            }
                            yield f"event: heartbeat\ndata: {json.dumps(heartbeat_payload)}\n\n"
                            last_heartbeat = current_time

                        try:
                            # Handle text output
                            if cont_event.type == "response.output_text.delta":
                                if hasattr(cont_event, 'delta') and cont_event.delta:
                                    current_content += cont_event.delta
                                    final_content_parts.append(cont_event.delta)
                                    token_count_continuation += 1
                                    cont_has_text_output = True

                                    token_payload = {
                                        "type": "token",
                                        "run_id": run_id,
                                        "seq": seq,
                                        "data": {"delta": cont_event.delta},
                                        "timestamp": int(time.time() * 1000)
                                    }
                                    yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                                    seq += 1

                            elif cont_event.type == "response.output_text.done":
                                if hasattr(cont_event, 'text') and cont_event.text and not final_content_parts:
                                    final_content_parts.append(cont_event.text)
                                    current_content = cont_event.text
                                    cont_has_text_output = True
                                logger.debug(f"[CONTINUATION] Text output done")

                            # Handle tool calls in continuation (recursive support)
                            elif cont_event.type == "response.output_item.added":
                                if hasattr(cont_event, 'item') and hasattr(cont_event.item, 'type') and cont_event.item.type == "function_call":
                                    function_name = cont_event.item.name
                                    tool_call_id = cont_event.item.id
                                    cont_tool_calls[tool_call_id] = {
                                        "id": tool_call_id,
                                        "type": "function",
                                        "function": {"name": str(function_name), "arguments": ""}
                                    }
                                    logger.debug(f"[CONTINUATION] New tool call: {function_name}")

                            elif cont_event.type == "response.function_call_arguments.delta":
                                tool_call_id = cont_event.item_id
                                if tool_call_id in cont_tool_calls and cont_event.delta:
                                    cont_tool_calls[tool_call_id]["function"]["arguments"] += cont_event.delta

                            elif cont_event.type == "response.function_call_arguments.done":
                                tool_call_id = cont_event.item_id
                                if tool_call_id in cont_tool_calls:
                                    tc = cont_tool_calls[tool_call_id]
                                    fn_name = tc["function"]["name"]
                                    try:
                                        fn_args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"].strip() else {}
                                    except json.JSONDecodeError:
                                        fn_args = {}

                                    logger.info(f"[CONTINUATION] Executing tool: {fn_name}")

                                    # Execute the tool
                                    async for sse_chunk in self._execute_tool_call(
                                        tool_call_id, fn_name, fn_args,
                                        conversation_id, portfolio_context, auth_context,
                                        run_id, seq
                                    ):
                                        if sse_chunk.startswith("event:"):
                                            yield sse_chunk
                                            seq += 1
                                        else:
                                            # This is the result JSON
                                            try:
                                                result_data = json.loads(sse_chunk)
                                                if "_result" in result_data:
                                                    cont_tool_calls[tool_call_id]["result"] = result_data["_result"]
                                            except json.JSONDecodeError:
                                                pass

                            elif cont_event.type == "response.completed":
                                logger.info(f"[CONTINUATION] Completed after {cont_event_count} events")
                                break

                            elif cont_event.type == "response.failed":
                                error_msg = str(getattr(cont_event, 'error', 'Unknown failure'))
                                logger.error(f"[CONTINUATION] Failed: {error_msg}")
                                error_payload = {
                                    "type": "error",
                                    "run_id": run_id,
                                    "seq": 0,
                                    "data": {"error": error_msg, "error_type": "continuation_failed", "retryable": True},
                                    "timestamp": int(time.time() * 1000)
                                }
                                yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
                                break

                            elif cont_event.type == "response.incomplete":
                                logger.error("[CONTINUATION] Incomplete/timed out")
                                break

                            elif cont_event.type in ("response.created", "response.in_progress", "response.output_item.done"):
                                logger.debug(f"[CONTINUATION] Housekeeping: {cont_event.type}")

                            else:
                                logger.debug(f"[CONTINUATION] Event: {cont_event.type}")

                        except Exception as evt_err:
                            logger.error(f"[CONTINUATION] Event error: {evt_err}")
                            continue

                    # If continuation called more tools, loop again
                    if cont_tool_calls and any("result" in tc for tc in cont_tool_calls.values()):
                        accumulated_tool_calls = cont_tool_calls
                        logger.info(f"[CONTINUATION] {len(accumulated_tool_calls)} more tool calls to process")
                    else:
                        # No more tool calls, exit loop
                        accumulated_tool_calls = {}

                    logger.info(f"[CONTINUATION] Iteration {tool_iteration} done: {token_count_continuation} tokens, text={cont_has_text_output}")

                except Exception as continuation_error:
                    logger.error(f"[CONTINUATION] Error: {continuation_error}")
                    error_payload = {
                        "type": "error",
                        "run_id": run_id,
                        "seq": 0,
                        "data": {"error": str(continuation_error), "error_type": "continuation_exception", "retryable": True},
                        "timestamp": int(time.time() * 1000)
                    }
                    yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
                    break  # Exit loop on error

            if tool_iteration >= max_tool_iterations:
                logger.warning(f"[CONTINUATION] Hit max iterations ({max_tool_iterations}), forcing completion")
            
            # Send final done event
            final_text = "".join(final_content_parts)
            done_payload = {
                "type": "done",
                "run_id": run_id,
                "seq": seq,
                "data": {
                    "final_text": final_text,
                    "tool_calls_count": len(accumulated_tool_calls),
                    "total_tokens": 0,  # TODO: Track token usage from Responses API
                    "token_counts": {
                        "initial": token_count_initial,
                        "continuation": token_count_continuation
                    }
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            
            # Log tool call summary if any tools were called
            if accumulated_tool_calls:
                self.log_tool_call_summary(conversation_id)
                
        except Exception as e:
            logger.error(f"Error in stream_responses: {e}")
            
            # Determine error characteristics
            error_type = "internal_error"
            retryable = True
            retry_after = 5
            
            if "rate_limit" in str(e).lower():
                error_type = "rate_limit_exceeded"
                retry_after = 60
            elif "insufficient_quota" in str(e).lower():
                error_type = "quota_exceeded"
                retryable = False
            elif "invalid_api_key" in str(e).lower():
                error_type = "authentication_error"
                retryable = False
            
            # Emit standardized error event
            error_payload = {
                "type": "error",
                "run_id": run_id,
                "seq": 0,  # Errors don't increment sequence
                "data": {
                    "error": str(e),
                    "error_type": error_type,
                    "retryable": retryable,
                    "retry_after": retry_after
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"

    def get_tool_call_mappings(self, conversation_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get tool call ID mappings for debugging and correlation.
        
        Args:
            conversation_id: Filter by specific conversation (optional)
            
        Returns:
            Dictionary of tool call ID mappings
        """
        if conversation_id:
            return {
                tool_id: mapping 
                for tool_id, mapping in self.tool_call_id_map.items()
                if mapping.get("conversation_id") == conversation_id
            }
        return self.tool_call_id_map.copy()
    
    def log_tool_call_summary(self, conversation_id: str):
        """Log a summary of all tool calls for a conversation"""
        mappings = self.get_tool_call_mappings(conversation_id)
        if mappings:
            logger.info(f"[DATA] Tool Call Summary for conversation {conversation_id}:")
            for tool_id, mapping in mappings.items():
                status = mapping.get("status", "unknown")
                tool_name = mapping.get("tool_name", "unknown")
                duration = mapping.get("duration_ms", "N/A")
                logger.info(f"  - {tool_id[:8]}... | {tool_name} | Status: {status} | Duration: {duration}ms")
        else:
            logger.info(f"[DATA] No tool calls recorded for conversation {conversation_id}")

    async def generate_insight(
        self,
        portfolio_id: Optional[str] = None,
        portfolio_ids: Optional[List[str]] = None,
        insight_type: str = "daily_summary",
        focus_area: Optional[str] = None,
        auth_context: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Generate a structured portfolio insight using OpenAI with tool calling.

        This method uses the new generalized LLM architecture to:
        1. Load the daily insight prompt
        2. Call tools to get real-time portfolio data (movers, news, analytics)
        3. Return a structured insight object

        Args:
            portfolio_id: Single portfolio UUID to analyze (optional if portfolio_ids provided)
            portfolio_ids: List of portfolio UUIDs to analyze (for multi-portfolio accounts)
            insight_type: Type of insight (daily_summary, volatility_analysis, etc.)
            focus_area: Optional specific focus area
            auth_context: Authentication context for tool calls
            db: Optional database session for RAG

        Returns:
            Dict with structured insight (title, summary, key_findings, recommendations, etc.)
        """
        from pathlib import Path

        start_time = time.time()
        run_id = str(uuid.uuid4())
        tool_calls_count = 0

        # Handle multi-portfolio: prefer list, fall back to single
        if portfolio_ids and len(portfolio_ids) > 0:
            portfolio_id_list = portfolio_ids
            is_multi_portfolio = len(portfolio_ids) > 1
        elif portfolio_id:
            portfolio_id_list = [portfolio_id]
            is_multi_portfolio = False
        else:
            return {
                "title": "Error - No Portfolio",
                "summary": "No portfolio ID provided",
                "error": "Either portfolio_id or portfolio_ids must be provided"
            }

        logger.info(f"[Insight] Starting insight generation: type={insight_type}, portfolios={portfolio_id_list}, multi={is_multi_portfolio}")

        try:
            # Load the appropriate insight prompt based on insight_type
            prompts_dir = Path(__file__).parent.parent / "prompts"

            # Morning briefing uses a special prompt with weekly data and web search emphasis
            if insight_type == "morning_briefing":
                insight_prompt_path = prompts_dir / "morning_briefing_prompt.md"
                include_web_search = True  # Always enable web search for morning briefing
            else:
                insight_prompt_path = prompts_dir / "daily_insight_prompt.md"
                include_web_search = False  # Web search optional for other insight types

            if insight_prompt_path.exists():
                with open(insight_prompt_path, 'r', encoding='utf-8') as f:
                    system_prompt = f.read()
            else:
                # Fallback prompt
                system_prompt = """You are generating a daily portfolio insight.
                Use tools to get portfolio data (get_daily_movers, get_portfolio_complete, get_market_news).
                Return a structured insight with: Title, Today's Snapshot, What Happened Today, News Driving Moves, Watch List, Action Items."""

            # Add focus area if provided
            if focus_area:
                system_prompt += f"\n\n## FOCUS AREA\nPay special attention to: {focus_area}"

            # Build portfolio context for user message
            portfolio_ids_str = ", ".join(portfolio_id_list)
            num_portfolios = len(portfolio_id_list)

            # Build the user message with explicit data fetching sequence
            if is_multi_portfolio:
                user_message = f"""Generate a {insight_type.replace('_', ' ')} for this user's {num_portfolios} portfolios.

Portfolio IDs: {portfolio_ids_str}

**IMPORTANT: Follow this exact sequence to gather data:**

STEP 1 - Get positions for EACH portfolio:
Call get_portfolio_complete with portfolio_ids parameter to get all holdings across portfolios.
This returns the positions you need BEFORE you can analyze movers.

STEP 2 - Get daily movers for EACH portfolio:
For each portfolio_id, call get_daily_movers to see biggest gainers/losers today.

STEP 3 - Get market news:
Call get_market_news with the top symbols from your positions to understand WHY things moved.
If news API unavailable, use your knowledge of recent market events.

STEP 4 - Synthesize:
Combine data from all {num_portfolios} portfolios into a unified daily insight.
Show aggregate stats (total value, total daily P&L) plus per-portfolio breakdown.

Follow the format in the system prompt for your final response."""
            else:
                # Single portfolio - simpler message
                single_portfolio_id = portfolio_id_list[0]
                user_message = f"""Generate a {insight_type.replace('_', ' ')} for portfolio {single_portfolio_id}.

**IMPORTANT: Follow this exact sequence to gather data:**

STEP 1 - Get portfolio positions:
Call get_portfolio_complete with portfolio_id="{single_portfolio_id}" to get all holdings.
This returns the positions you need BEFORE you can analyze movers.

STEP 2 - Get daily movers:
Call get_daily_movers with portfolio_id="{single_portfolio_id}" to see biggest gainers/losers today.
(This tool calls get_portfolio_complete internally, so you can skip Step 1 if preferred)

STEP 3 - Get market news:
Call get_market_news with portfolio_id="{single_portfolio_id}" to understand WHY things moved.
If news API unavailable, use your knowledge of recent market events.

STEP 4 - Synthesize:
Combine the data into a daily insight following the format in the system prompt."""

            # Build messages for the API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            # Get tool definitions (include web search for morning briefing)
            tools = self._get_tool_definitions_responses(include_web_search=include_web_search)

            # Use Responses API (non-streaming) with tool execution loop
            max_iterations = 5
            accumulated_tool_results = []
            final_response_text = None
            previous_response_id = None  # Track response ID for continuation

            for iteration in range(max_iterations):
                logger.info(f"[Insight] API call iteration {iteration + 1}/{max_iterations}")

                # Create the response (use previous_response_id for continuation after tool calls)
                if previous_response_id:
                    response = await self.client.responses.create(
                        model=self.model,
                        input=messages,
                        tools=tools,
                        previous_response_id=previous_response_id
                    )
                else:
                    response = await self.client.responses.create(
                        model=self.model,
                        input=messages,
                        tools=tools
                    )

                # Store response ID for potential continuation
                previous_response_id = response.id

                # Check the response output
                if not response.output:
                    logger.warning("[Insight] Empty response output")
                    break

                # Process output items
                has_tool_calls = False
                text_content = []

                for item in response.output:
                    if item.type == "message":
                        # Extract text content
                        for content in item.content:
                            if hasattr(content, 'text'):
                                text_content.append(content.text)

                    elif item.type == "function_call":
                        has_tool_calls = True
                        tool_calls_count += 1

                        function_name = item.name
                        call_id = item.call_id

                        # Parse arguments
                        try:
                            function_args = json.loads(item.arguments) if item.arguments else {}
                        except json.JSONDecodeError:
                            function_args = {}

                        # Auto-inject portfolio context if needed
                        portfolio_aware_tools = ["get_daily_movers", "get_portfolio_complete", "get_market_news",
                                                 "get_analytics_overview", "get_factor_exposures"]
                        if function_name in portfolio_aware_tools:
                            # For get_portfolio_complete, prefer portfolio_ids list for multi-portfolio
                            if function_name == "get_portfolio_complete" and is_multi_portfolio:
                                if not function_args.get("portfolio_ids"):
                                    function_args["portfolio_ids"] = portfolio_id_list
                            # For single-portfolio tools, inject first portfolio_id
                            elif not function_args.get("portfolio_id"):
                                function_args["portfolio_id"] = portfolio_id_list[0]

                        logger.info(f"[Insight] Executing tool: {function_name} with args: {list(function_args.keys())}")

                        # Execute tool
                        try:
                            from app.agent.tools.tool_registry import tool_registry

                            tool_context = {
                                "portfolio_id": portfolio_id_list[0],  # Primary portfolio
                                "portfolio_ids": portfolio_id_list,    # All portfolios
                            }
                            if auth_context:
                                tool_context.update(auth_context)

                            result = await tool_registry.dispatch_tool_call(
                                function_name,
                                function_args,
                                tool_context
                            )

                            accumulated_tool_results.append({
                                "call_id": call_id,
                                "tool_name": function_name,
                                "result": result
                            })

                            logger.info(f"[Insight] Tool {function_name} completed successfully")

                        except Exception as e:
                            logger.error(f"[Insight] Tool {function_name} failed: {e}")
                            accumulated_tool_results.append({
                                "call_id": call_id,
                                "tool_name": function_name,
                                "result": {"error": str(e)}
                            })

                # If we got text content and no tool calls, we're done
                if text_content and not has_tool_calls:
                    final_response_text = "\n".join(text_content)
                    break

                # If we had tool calls, continue the conversation with tool results
                if has_tool_calls and accumulated_tool_results:
                    # Format tool outputs for continuation
                    tool_outputs = []
                    for tr in accumulated_tool_results:
                        tool_outputs.append({
                            "type": "function_call_output",
                            "call_id": tr["call_id"],
                            "output": json.dumps(tr["result"]) if isinstance(tr["result"], dict) else str(tr["result"])
                        })

                    # Create continuation with tool outputs
                    messages = tool_outputs

                    # Clear accumulated results for next iteration
                    accumulated_tool_results = []
                    continue

                # No tool calls and no text - something went wrong
                if not text_content and not has_tool_calls:
                    logger.warning("[Insight] No content or tool calls in response")
                    break

            # Parse the final response into structured format
            if not final_response_text:
                final_response_text = "Unable to generate insight. Please try again."

            # Parse sections from markdown response
            insight = self._parse_insight_response(final_response_text, insight_type)

            # Add performance metrics
            generation_time_ms = (time.time() - start_time) * 1000
            insight["performance"] = {
                "generation_time_ms": round(generation_time_ms),
                "tool_calls_count": tool_calls_count,
                "model": self.model,
                "run_id": run_id
            }

            logger.info(f"[Insight] Generation complete: {generation_time_ms:.0f}ms, {tool_calls_count} tool calls")

            return insight

        except Exception as e:
            logger.error(f"[Insight] Error generating insight: {e}")
            return {
                "title": f"{insight_type.replace('_', ' ').title()} - Error",
                "summary": f"Failed to generate insight: {str(e)}",
                "key_findings": [],
                "recommendations": [],
                "data_limitations": str(e),
                "full_analysis": "",
                "severity": "INFO",
                "performance": {
                    "generation_time_ms": round((time.time() - start_time) * 1000),
                    "tool_calls_count": 0,
                    "error": str(e)
                }
            }

    def _parse_insight_response(self, response_text: str, insight_type: str) -> Dict[str, Any]:
        """Parse the LLM's markdown response into structured insight format."""
        result = {
            "title": None,
            "summary": "",
            "key_findings": [],
            "recommendations": [],
            "data_limitations": "",
            "full_analysis": response_text,
            "severity": "INFO",
            "todays_snapshot": None,
            "what_happened": "",
            "news_driving_moves": [],
            "watch_list": [],
            "action_items": []
        }

        lines = response_text.split('\n')
        current_section = None
        section_content = []

        for line in lines:
            line_stripped = line.strip()

            # Detect section headers
            if 'Title' in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'title'
                section_content = []
            elif "Today's Snapshot" in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'snapshot'
                section_content = []
            elif 'What Happened Today' in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'what_happened'
                section_content = []
            elif 'News Driving Moves' in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'news'
                section_content = []
            elif 'Watch List' in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'watch_list'
                section_content = []
            elif 'Action Items' in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'action_items'
                section_content = []
            elif 'Key Findings' in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'key_findings'
                section_content = []
            elif 'Recommendations' in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'recommendations'
                section_content = []
            elif 'Summary' in line_stripped and line_stripped.startswith('#'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'summary'
                section_content = []
            elif line_stripped.startswith('###') or line_stripped.startswith('##'):
                if current_section and section_content:
                    self._assign_section_content(result, current_section, section_content)
                current_section = 'other'
                section_content = []
            else:
                if current_section:
                    section_content.append(line)

        if current_section and section_content:
            self._assign_section_content(result, current_section, section_content)

        if not result["title"]:
            result["title"] = f"{insight_type.replace('_', ' ').title()} Analysis"

        if not result["summary"] and result["what_happened"]:
            wh = result["what_happened"]
            result["summary"] = wh[:300] + "..." if len(wh) > 300 else wh

        return result

    def _assign_section_content(self, result: Dict[str, Any], section: str, content: List[str]):
        """Assign parsed content to the appropriate result field."""
        text = "\n".join(content).strip()

        if section == 'title':
            for line in content:
                if line.strip():
                    result["title"] = line.strip().lstrip('#').strip()
                    break
        elif section == 'summary':
            result["summary"] = text
        elif section == 'snapshot':
            result["todays_snapshot"] = text
        elif section == 'what_happened':
            result["what_happened"] = text
        elif section == 'news':
            result["news_driving_moves"] = [
                line.lstrip('-*• ').strip()
                for line in content
                if line.strip().startswith(('-', '*', '•'))
            ]
        elif section == 'watch_list':
            result["watch_list"] = [
                line.lstrip('-*• ').strip()
                for line in content
                if line.strip().startswith(('-', '*', '•'))
            ]
        elif section == 'action_items':
            result["action_items"] = [
                line.lstrip('-*• ').strip()
                for line in content
                if line.strip().startswith(('-', '*', '•'))
            ]
        elif section == 'key_findings':
            result["key_findings"] = [
                line.lstrip('-*• ').strip()
                for line in content
                if line.strip().startswith(('-', '*', '•'))
            ]
        elif section == 'recommendations':
            result["recommendations"] = [
                line.lstrip('-*• ').strip()
                for line in content
                if line.strip().startswith(('-', '*', '•'))
            ]


# Singleton instance
openai_service = OpenAIService()
