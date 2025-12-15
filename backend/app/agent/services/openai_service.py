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

logger = get_logger(__name__)


class OpenAIService:
    """Service for handling OpenAI API interactions"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.prompt_manager = PromptManager()
        self.model = settings.MODEL_DEFAULT
        self.fallback_model = settings.MODEL_FALLBACK
        # Track tool call IDs for correlation between OpenAI and our system
        self.tool_call_id_map: Dict[str, Dict[str, Any]] = {}
        # RAG configuration (from settings)
        self.rag_enabled = settings.RAG_ENABLED
        self.rag_doc_limit = settings.RAG_DOC_LIMIT
        self.rag_max_chars = settings.RAG_MAX_CHARS

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

            # Add page-specific scope if available
            if portfolio_context and portfolio_context.get("page_hint"):
                scopes.append(f"page:{portfolio_context['page_hint']}")

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
        
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Default tool definitions method - delegates to Responses API format"""
        return self._get_tool_definitions_responses()
    
    def _get_tool_definitions_responses(self) -> List[Dict[str, Any]]:
        """Convert our tool definitions to Responses API format (with full schemas)"""
        tools = [
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
            }
        ]
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
    ) -> List[Dict[str, Any]]:
        """Build input structure for OpenAI Responses API (array of messages)"""
        # Get system prompt for the mode
        system_prompt = self.prompt_manager.get_system_prompt(
            conversation_mode,
            user_context=portfolio_context
        )

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
        model_to_use = model_override or self.model

        try:
            # Retrieve RAG context before building input
            rag_context = await self._get_rag_context(
                db=db,
                query=message_text,
                portfolio_context=portfolio_context,
            )

            # Build Responses API input with RAG context
            input_data = self._build_responses_input(
                conversation_mode,
                message_history or [],
                message_text,
                portfolio_context,
                rag_context=rag_context,
            )
            
            # Get tool definitions for Responses API
            tools = self._get_tool_definitions_responses()
            
            # Yield start event with standardized format
            start_payload = {
                "type": "start",
                "run_id": run_id,
                "seq": seq,
                "data": {
                    "conversation_id": conversation_id,
                    "mode": conversation_mode,
                    "model": model_to_use
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: start\ndata: {json.dumps(start_payload)}\n\n"
            seq += 1
            
            # Call OpenAI Responses API with streaming
            stream = await self.client.responses.create(
                model=model_to_use,
                input=input_data,  # Use input structure instead of messages
                tools=tools if tools else None,
                stream=True
                # Note: max_completion_tokens is not supported by Responses API
            )
            
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
                            
                            # Emit tool_call event 
                            # Phase 5.9.5.4: Final validation that tool_name is string (prevents frontend 400s)
                            validated_function_name = str(function_name) if function_name else 'unknown_function'
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
                        
                    else:
                        # Unknown event type - log for investigation but don't fail
                        logger.warning(f"Unknown Responses API event type: {event.type}")
                        logger.debug(f"Event data: {event}")
                        continue
                        
                except Exception as event_error:
                    logger.error(f"Error processing Responses API event: {event_error} - event: {event}")
                    continue
            
            # After stream completes, if tools were called, continue conversation with tool results
            if accumulated_tool_calls:
                logger.info(f"🔄 Continuing conversation with {len(accumulated_tool_calls)} tool results")
                
                # Build continuation input with tool results
                continuation_input = input_data.copy()
                
                # Add user message asking OpenAI to analyze the tool results
                tool_summary_parts = []
                for tool_call in accumulated_tool_calls.values():
                    tool_name = tool_call["function"]["name"]
                    tool_result = tool_call.get("result", {})
                    
                    # Determine truncation limit based on tool type
                    # Portfolio tools get larger limits for complete data visibility
                    portfolio_tools = ["get_portfolio_complete", "get_positions_details", "get_portfolio_data_quality"]
                    
                    if settings.TOOL_RESPONSE_TRUNCATE_ENABLED:
                        if tool_name in portfolio_tools:
                            max_chars = settings.TOOL_RESPONSE_PORTFOLIO_MAX_CHARS
                        else:
                            max_chars = settings.TOOL_RESPONSE_MAX_CHARS
                    else:
                        # Truncation disabled - pass full response
                        max_chars = None
                    
                    # Create a summary of what the tool returned
                    if isinstance(tool_result, dict) and "data" in tool_result:
                        full_json = json.dumps(tool_result["data"], indent=2)
                        data_summary = full_json[:max_chars] if max_chars else full_json
                    else:
                        full_json = json.dumps(tool_result, indent=2)
                        data_summary = full_json[:max_chars] if max_chars else full_json
                    
                    # Log truncation info for debugging
                    if max_chars and len(data_summary) == max_chars:
                        logger.info(f"Tool response truncated: {tool_name} - {len(full_json)} chars -> {max_chars} chars")
                    
                    tool_summary_parts.append(f"Tool '{tool_name}' returned:\n{data_summary}")
                
                tool_summary = "\n\n".join(tool_summary_parts)
                
                # For Responses API, we add a follow-up user message with tool results
                continuation_message = {
                    "role": "user",
                    "content": f"Based on the tool results below, please provide a comprehensive analysis and answer to my original question:\n\n{tool_summary}"
                }
                continuation_input.append(continuation_message)
                
                # Make continuation call to get final response
                try:
                    continuation_stream = await self.client.responses.create(
                        model=model_to_use,
                        input=continuation_input,
                        tools=tools if tools else None,
                        stream=True
                    )
                    
                    # Process continuation stream events
                    async for cont_event in continuation_stream:
                        try:
                            # Continuation heartbeats to keep connection warm during long reasoning gaps
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

                            if cont_event.type == "response.output_text.delta":
                                if hasattr(cont_event, 'delta') and cont_event.delta:
                                    current_content += cont_event.delta
                                    final_content_parts.append(cont_event.delta)
                                    token_count_continuation += 1
                                    logger.debug(f"TOKEN-DEBUG(continuation): run_id={run_id} seq={seq} len={len(cont_event.delta)}")
                                    
                                    # Emit token event for continuation
                                    token_payload = {
                                        "type": "token",
                                        "run_id": run_id,
                                        "seq": seq,
                                        "data": {"delta": cont_event.delta},
                                        "timestamp": int(time.time() * 1000)
                                    }
                                    yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                                    seq += 1
                            elif cont_event.type == "response.completed":
                                logger.info(f"Continuation response completed")
                                break
                            elif cont_event.type == "response.failed":
                                # Propagate continuation failure as SSE error so frontend can handle gracefully
                                error_msg = str(getattr(cont_event, 'error', 'Unknown continuation failure'))
                                logger.error(f"OpenAI continuation failed: {error_msg}")
                                error_payload = {
                                    "type": "error",
                                    "run_id": run_id,
                                    "seq": 0,
                                    "data": {
                                        "error": error_msg,
                                        "error_type": "continuation_failed",
                                        "retryable": True
                                    },
                                    "timestamp": int(time.time() * 1000)
                                }
                                yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
                                break
                            elif cont_event.type == "response.incomplete":
                                # Timeout/incomplete continuation
                                logger.error("OpenAI continuation incomplete/timed out")
                                error_payload = {
                                    "type": "error",
                                    "run_id": run_id,
                                    "seq": 0,
                                    "data": {
                                        "error": "Continuation timed out or was incomplete",
                                        "error_type": "continuation_incomplete",
                                        "retryable": True
                                    },
                                    "timestamp": int(time.time() * 1000)
                                }
                                yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
                                break
                        except Exception as cont_event_error:
                            logger.error(f"Error processing continuation event: {cont_event_error}")
                            continue
                            
                except Exception as continuation_error:
                    logger.error(f"Error in conversation continuation: {continuation_error}")
                    # Emit error SSE so frontend can show a meaningful message instead of a silent gap
                    error_payload = {
                        "type": "error",
                        "run_id": run_id,
                        "seq": 0,
                        "data": {
                            "error": str(continuation_error),
                            "error_type": "continuation_exception",
                            "retryable": True
                        },
                        "timestamp": int(time.time() * 1000)
                    }
                    yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
                    # Continue to send done event afterward
            
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


# Singleton instance
openai_service = OpenAIService()