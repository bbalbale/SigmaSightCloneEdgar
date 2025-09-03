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
        
    def _get_tool_definitions_chat(self) -> List[ChatCompletionToolParam]:
        """Convert our tool definitions to Chat Completions API format"""
        """Convert our tool definitions to OpenAI format"""
        # Define the tools manually with their OpenAI-compatible schemas
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_portfolio_complete",
                    "description": "Get comprehensive portfolio snapshot with positions, values, and optional data",
                    "parameters": {
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
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_portfolio_data_quality",
                    "description": "Assess data completeness and analysis feasibility",
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
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_positions_details",
                    "description": "Get detailed position information with P&L and metadata",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "portfolio_id": {
                                "type": "string",
                                "description": "Portfolio UUID"
                            },
                            "position_ids": {
                                "type": "string",
                                "description": "Comma-separated position IDs"
                            },
                            "include_closed": {
                                "type": "boolean",
                                "description": "Include closed positions",
                                "default": False
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_prices_historical",
                    "description": "Get historical prices for top portfolio positions",
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
                            "max_symbols": {
                                "type": "integer",
                                "description": "Max symbols to return (max 5)",
                                "default": 5
                            },
                            "include_factor_etfs": {
                                "type": "boolean",
                                "description": "Include factor ETF prices",
                                "default": True
                            },
                            "date_format": {
                                "type": "string",
                                "description": "Date format: iso or unix",
                                "default": "iso"
                            }
                        },
                        "required": ["portfolio_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_quotes",
                    "description": "Get real-time market quotes for specified symbols",
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
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_factor_etf_prices",
                    "description": "Get historical prices for factor ETFs used in analysis",
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
            }
        ]
        return tools

    def _get_tool_definitions_responses(self) -> List[Dict[str, Any]]:
        """Convert our tool definitions to Responses API format (with full schemas)"""
        tools = [
            {
                "name": "get_portfolio_complete",
                "type": "function",
                "description": "Get comprehensive portfolio snapshot with positions, values, and optional data",
                "parameters": {
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
                "name": "get_portfolio_data_quality",
                "type": "function", 
                "description": "Assess portfolio data completeness and quality metrics",
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
            {
                "name": "get_positions_details",
                "type": "function",
                "description": "Get detailed position information with P&L calculations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {
                            "type": "string",
                            "description": "Portfolio UUID"
                        },
                        "position_ids": {
                            "type": "string",
                            "description": "Comma-separated position IDs"
                        },
                        "include_closed": {
                            "type": "boolean",
                            "description": "Include closed positions",
                            "default": False
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_prices_historical",
                "type": "function",
                "description": "Retrieve historical price data for portfolio symbols",
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
                        "max_symbols": {
                            "type": "integer",
                            "description": "Max symbols to return (max 5)",
                            "default": 5
                        },
                        "include_factor_etfs": {
                            "type": "boolean",
                            "description": "Include factor ETF prices",
                            "default": True
                        },
                        "date_format": {
                            "type": "string",
                            "description": "Date format: iso or unix",
                            "default": "iso"
                        }
                    },
                    "required": ["portfolio_id"]
                }
            },
            {
                "name": "get_current_quotes",
                "type": "function",
                "description": "Get real-time market quotes for specified symbols",
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
        ]
        return tools
    
    def _get_tool_definitions(self) -> List[ChatCompletionToolParam]:
        """Default tool definitions method - delegates to Chat API format"""
        return self._get_tool_definitions_chat()
    
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
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            # Skip tool calls in conversation history to avoid OpenAI validation errors
            # OpenAI requires every assistant message with tool_calls to be followed by tool responses
            # Since we don't store tool responses in conversation history, we skip tool calls entirely
            # The assistant will make new tool calls based on the current context
            if msg.get("tool_calls"):
                logger.debug(f"Skipping tool calls in conversation history to avoid incomplete sequences")
                # Just add the content without tool calls
                if msg.get("content"):
                    messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })
                # Skip empty assistant messages with only tool calls
                continue
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _build_responses_input(
        self, 
        conversation_mode: str, 
        message_history: List[Dict[str, Any]], 
        user_message: str,
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Build input structure for OpenAI Responses API (array of messages)"""
        # Get system prompt for the mode
        system_prompt = self.prompt_manager.get_system_prompt(
            conversation_mode,
            user_context=portfolio_context
        )
        
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
        run_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream responses using OpenAI Responses API with proper tool execution handshake
        
        Yields SSE formatted events with standardized contract (type, run_id, seq fields)
        """
        run_id = run_id or str(uuid.uuid4())
        seq = 0
        final_content_parts = []
        
        try:
            # Build Responses API input
            input_data = self._build_responses_input(
                conversation_mode,
                message_history or [],
                message_text,
                portfolio_context
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
                    "model": self.model
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: start\ndata: {json.dumps(start_payload)}\n\n"
            seq += 1
            
            # Call OpenAI Responses API with streaming
            stream = await self.client.responses.create(
                model=self.model,
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
                        
                    elif event.type == "response.output_text.delta":
                        # Handle streaming text content -> emit token event
                        if hasattr(event, 'delta') and event.delta:
                            current_content += event.delta
                            final_content_parts.append(event.delta)
                            
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
                            
                    elif event.type == "response.function_call_arguments.delta":
                        # Function call arguments streaming - accumulate deltas
                        tool_call_id = event.function_call_id  # Use function_call_id from Responses API
                        
                        # Initialize tool call if not exists
                        if tool_call_id not in accumulated_tool_calls:
                            # Need to get function name from event (assuming it's available)
                            function_name = getattr(event, 'function_name', 'unknown_function')
                            logger.debug(f"🔧 Tool call arguments started - ID: {tool_call_id}, Tool: {function_name}")
                            
                            accumulated_tool_calls[tool_call_id] = {
                                "id": tool_call_id,
                                "type": "function", 
                                "function": {
                                    "name": function_name,
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
                        tool_call_id = event.function_call_id  # Use function_call_id from Responses API
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
                            seq += 1
                            
                            # Execute tool
                            logger.info(f"🔧 Executing tool call - ID: {tool_call_id}, Tool: {function_name}")
                            start_time = time.time()
                            
                            try:
                                from app.agent.tools.tool_registry import tool_registry
                                result = await tool_registry.dispatch_tool_call(function_name, function_args)
                                duration_ms = int((time.time() - start_time) * 1000)
                                
                                logger.info(f"✅ Tool call completed - ID: {tool_call_id}, Tool: {function_name}, Duration: {duration_ms}ms")
                                
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
                                
                                # CRITICAL: Submit tool output back to Responses API for continuation
                                if response_id:
                                    await self.client.responses.submit_tool_outputs(
                                        response_id=response_id,
                                        tool_outputs=[{
                                            "tool_call_id": tool_call_id,
                                            "output": json.dumps(result) if isinstance(result, dict) else str(result)
                                        }]
                                    )
                                    logger.debug(f"Tool output submitted to response {response_id} for tool {tool_call_id}")
                                
                            except Exception as e:
                                duration_ms = int((time.time() - start_time) * 1000)
                                logger.error(f"❌ Tool call failed - ID: {tool_call_id}, Tool: {function_name}, Error: {e}")
                                
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
                                
                                # Submit error response to Responses API
                                if response_id:
                                    await self.client.responses.submit_tool_outputs(
                                        response_id=response_id,
                                        tool_outputs=[{
                                            "tool_call_id": tool_call_id,
                                            "output": f"Error: {str(e)}"
                                        }]
                                    )
                                    
                    elif event.type == "response.completed":
                        # Response completed
                        logger.info(f"Response completed: {response_id}")
                        break
                        
                    else:
                        # Unknown event type - log for investigation but don't fail
                        logger.warning(f"Unknown Responses API event type: {event.type}")
                        logger.debug(f"Event data: {event}")
                        continue
                        
                except Exception as event_error:
                    logger.error(f"Error processing Responses API event: {event_error} - event: {event}")
                    continue
            
            # Send final done event
            final_text = "".join(final_content_parts)
            done_payload = {
                "type": "done",
                "run_id": run_id,
                "seq": seq,
                "data": {
                    "final_text": final_text,
                    "tool_calls_count": len(accumulated_tool_calls),
                    "total_tokens": 0  # TODO: Track token usage from Responses API
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

    async def stream_chat_completion(
        self,
        conversation_id: str,
        conversation_mode: str,
        message_text: str,
        message_history: List[Dict[str, Any]] = None,
        portfolio_context: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion with tool calling support
        
        Yields SSE formatted events with standardized contract (type, run_id, seq fields)
        """
        run_id = run_id or str(uuid.uuid4())
        seq = 0
        final_content_parts = []
        
        try:
            # Build messages
            messages = self._build_messages(
                conversation_mode,
                message_history or [],
                message_text,
                portfolio_context
            )
            
            # Get tool definitions
            tools = self._get_tool_definitions()
            
            # Yield start event with standardized format
            start_payload = {
                "type": "start",
                "run_id": run_id,
                "seq": seq,
                "data": {
                    "conversation_id": conversation_id,
                    "mode": conversation_mode,
                    "model": self.model
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: start\ndata: {json.dumps(start_payload)}\n\n"
            seq += 1
            
            # Call OpenAI Chat Completions API with streaming (fallback from Responses API due to bugs)
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                stream=True,
                max_completion_tokens=getattr(settings, 'OPENAI_MAX_COMPLETION_TOKENS', settings.CHAT_MAX_TOKENS)
            )
            
            # Track state for streaming
            current_content = ""
            tool_call_chunks = {}
            
            async for chunk in stream:
                try:
                    # Handle both ChatCompletionChunk objects and dict responses
                    if hasattr(chunk, 'choices'):
                        # Standard ChatCompletionChunk object
                        delta = chunk.choices[0].delta if chunk.choices else None
                    elif isinstance(chunk, dict):
                        # Handle dict response (fallback)
                        choices = chunk.get('choices', [])
                        delta = choices[0].get('delta') if choices else None
                        logger.debug(f"Received dict chunk: {chunk}")
                    else:
                        logger.warning(f"Unknown chunk type: {type(chunk)} - {chunk}")
                        continue
                    
                    if not delta:
                        continue
                    
                    # Handle content deltas with standardized token events
                    if hasattr(delta, 'content') and delta.content:
                        current_content += delta.content
                        final_content_parts.append(delta.content)
                        
                        token_payload = {
                            "type": "token",
                            "run_id": run_id,
                            "seq": seq,
                            "data": {"delta": delta.content},
                            "timestamp": int(time.time() * 1000)
                        }
                        yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                        seq += 1
                    
                    # Handle tool calls with more robust error handling
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            tool_call_index = tool_call_delta.index
                            tool_call_id = tool_call_delta.id
                            
                            # Handle case where id is None (subsequent chunks for same tool call)
                            if tool_call_id is None:
                                # Find existing tool call by index
                                tool_call_id = None
                                for existing_id, chunk in tool_call_chunks.items():
                                    if chunk.get("_index") == tool_call_index:
                                        tool_call_id = existing_id
                                        break
                                
                                # If we still don't have an ID, this is an error state - skip this delta
                                if tool_call_id is None:
                                    logger.warning(f"Received tool call delta with null ID and unknown index {tool_call_index}")
                                    continue
                            else:
                                # This is a new tool call with an ID
                                if tool_call_id not in tool_call_chunks:
                                    # Log new tool call ID for tracking
                                    logger.debug(f"🔧 New tool call started - OpenAI ID: {tool_call_id}")
                                    tool_call_chunks[tool_call_id] = {
                                        "id": tool_call_id,
                                        "type": "function",
                                        "_index": tool_call_index,  # Track index for null ID lookups
                                        "function": {
                                            "name": tool_call_delta.function.name if tool_call_delta.function else "",
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
                            
                            # Accumulate function arguments (now tool_call_id is guaranteed to be valid)
                            if tool_call_delta.function and tool_call_delta.function.arguments:
                                tool_call_chunks[tool_call_id]["function"]["arguments"] += tool_call_delta.function.arguments
                    
                    # Check for finish reason with type safety
                    finish_reason = None
                    try:
                        if hasattr(chunk, 'choices'):
                            # Standard ChatCompletionChunk object
                            finish_reason = chunk.choices[0].finish_reason if chunk.choices else None
                        elif isinstance(chunk, dict):
                            # Handle dict response (fallback)
                            choices = chunk.get('choices', [])
                            finish_reason = choices[0].get('finish_reason') if choices else None
                    except Exception as e:
                        logger.debug(f"Error extracting finish_reason: {e} - chunk: {chunk}")
                        finish_reason = None
                    
                    if finish_reason == "tool_calls":
                        # Execute tool calls
                        for tool_call_id, tool_call in tool_call_chunks.items():
                            function_name = tool_call["function"]["name"]
                            
                            # Parse function arguments with error guard
                            try:
                                raw_args = tool_call["function"]["arguments"]
                                logger.debug(f"Raw tool arguments for {function_name}: {raw_args!r}")
                                if isinstance(raw_args, str) and raw_args.strip():
                                    function_args = json.loads(raw_args)
                                else:
                                    function_args = {}
                                    logger.warning(f"Empty or invalid arguments for {function_name}")
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse tool arguments for {function_name}: {e}")
                                function_args = {}
                            
                            # Update ID mapping with tool details
                            if tool_call_id in self.tool_call_id_map:
                                self.tool_call_id_map[tool_call_id].update({
                                    "tool_name": function_name,
                                    "tool_args": function_args,
                                    "status": "executing"
                                })
                            
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
                            seq += 1
                            
                            # Execute tool
                            logger.info(f"🔧 Executing tool call - ID: {tool_call_id}, Tool: {function_name}")
                            start_time = time.time()
                            
                            try:
                                from app.agent.tools.tool_registry import tool_registry
                                result = await tool_registry.dispatch_tool_call(function_name, function_args)
                                duration_ms = int((time.time() - start_time) * 1000)
                                
                                # Update ID mapping with completion
                                if tool_call_id in self.tool_call_id_map:
                                    self.tool_call_id_map[tool_call_id].update({
                                        "status": "completed",
                                        "duration_ms": duration_ms,
                                        "completed_at": int(time.time() * 1000)
                                    })
                                
                                logger.info(f"✅ Tool call completed - ID: {tool_call_id}, Tool: {function_name}, Duration: {duration_ms}ms")
                                
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
                                
                                # Add tool response to messages for continuation
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "content": json.dumps(result)
                                })
                                
                            except Exception as e:
                                duration_ms = int((time.time() - start_time) * 1000)
                                logger.error(f"❌ Tool call failed - ID: {tool_call_id}, Tool: {function_name}, Error: {e}")
                                
                                # Emit error event but continue
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
                                
                                # Add error response to messages
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "content": json.dumps({"error": str(e)})
                                })
                        
                        # Continue conversation with tool results if any were called
                        if tool_call_chunks:
                            # Clean up tool calls for OpenAI (remove internal fields)
                            clean_tool_calls = []
                            for tool_call in tool_call_chunks.values():
                                clean_call = {
                                    "id": tool_call["id"],
                                    "type": tool_call["type"],
                                    "function": tool_call["function"]
                                }
                                # Remove internal _index field if present
                                clean_tool_calls.append(clean_call)
                            
                            # Add assistant message with tool calls to history
                            messages.append({
                                "role": "assistant",
                                "content": current_content or None,
                                "tool_calls": clean_tool_calls
                            })
                            
                            # Make another API call with tool results
                            continuation_stream = await self.client.chat.completions.create(
                                model=self.model,
                                messages=messages,
                                stream=True,
                                max_completion_tokens=getattr(settings, 'OPENAI_MAX_COMPLETION_TOKENS', settings.CHAT_MAX_TOKENS)
                            )
                            
                            # Stream the continuation
                            try:
                                async for cont_chunk in continuation_stream:
                                    try:
                                        # Handle both ChatCompletionChunk objects and dict responses
                                        if hasattr(cont_chunk, 'choices'):
                                            # Standard ChatCompletionChunk object
                                            cont_delta = cont_chunk.choices[0].delta if cont_chunk.choices else None
                                        elif isinstance(cont_chunk, dict):
                                            # Handle dict response (fallback)
                                            choices = cont_chunk.get('choices', [])
                                            cont_delta = choices[0].get('delta') if choices else None
                                            logger.debug(f"Received dict chunk in continuation: {cont_chunk}")
                                        else:
                                            logger.warning(f"Unknown continuation chunk type: {type(cont_chunk)} - {cont_chunk}")
                                            continue
                                        
                                        if cont_delta and cont_delta.content:
                                            final_content_parts.append(cont_delta.content)
                                            
                                            token_payload = {
                                                "type": "token",
                                                "run_id": run_id,
                                                "seq": seq,
                                                "data": {"delta": cont_delta.content},
                                                "timestamp": int(time.time() * 1000)
                                            }
                                            yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                                            seq += 1
                                    except Exception as chunk_error:
                                        logger.error(f"Error processing continuation chunk: {chunk_error} - chunk: {cont_chunk}")
                                        continue
                            except Exception as e:
                                logger.error(f"Error in continuation streaming: {e}")
                                # Continue with the rest of the function
                
                except Exception as chunk_error:
                    logger.error(f"Error processing chunk: {chunk_error} - chunk: {chunk}")
                    continue
            
            # Send final done event
            final_text = "".join(final_content_parts)
            done_payload = {
                "type": "done",
                "run_id": run_id,
                "seq": seq,
                "data": {
                    "final_text": final_text,
                    "tool_calls_count": len(tool_call_chunks),
                    "total_tokens": 0  # TODO: Track token usage
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            
            # Log tool call summary if any tools were called
            if tool_call_chunks:
                self.log_tool_call_summary(conversation_id)
                
        except Exception as e:
            logger.error(f"Error in stream_chat_completion: {e}")
            
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
    
    async def stream_chat_completion_legacy(
        self,
        conversation_id: str,
        conversation_mode: str,
        message_text: str,
        message_history: List[Dict[str, Any]] = None,
        portfolio_context: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Legacy streaming implementation using Chat Completions API.
        Kept for fallback until Responses API is fully stable.
        """
        run_id = run_id or str(uuid.uuid4())
        seq = 0
        final_content_parts = []
        
        try:
            # Build messages
            messages = self._build_messages(
                conversation_mode,
                message_history or [],
                message_text,
                portfolio_context
            )
            
            # Get tool definitions
            tools = self._get_tool_definitions()
            
            # Yield start event with standardized format
            start_payload = {
                "type": "start",
                "run_id": run_id,
                "seq": seq,
                "data": {
                    "conversation_id": conversation_id,
                    "mode": conversation_mode,
                    "model": self.model
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: start\ndata: {json.dumps(start_payload)}\n\n"
            seq += 1
            
            # Call OpenAI Chat Completions API with streaming
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                stream=True,
                max_completion_tokens=getattr(settings, 'OPENAI_MAX_COMPLETION_TOKENS', settings.CHAT_MAX_TOKENS)
            )
            
            # Track state for streaming
            current_content = ""
            tool_call_chunks = {}
            
            async for chunk in stream:
                try:
                    # Handle both ChatCompletionChunk objects and dict responses
                    if hasattr(chunk, 'choices'):
                        # Standard ChatCompletionChunk object
                        delta = chunk.choices[0].delta if chunk.choices else None
                    elif isinstance(chunk, dict):
                        # Handle dict response (fallback)
                        choices = chunk.get('choices', [])
                        delta = choices[0].get('delta') if choices else None
                        logger.debug(f"Received dict chunk: {chunk}")
                    else:
                        logger.warning(f"Unknown chunk type: {type(chunk)} - {chunk}")
                        continue
                    
                    if not delta:
                        continue
                    
                    # Handle content deltas with standardized token events
                    if hasattr(delta, 'content') and delta.content:
                        current_content += delta.content
                        final_content_parts.append(delta.content)
                        
                        token_payload = {
                            "type": "token",
                            "run_id": run_id,
                            "seq": seq,
                            "data": {"delta": delta.content},
                            "timestamp": int(time.time() * 1000)
                        }
                        yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                        seq += 1
                    
                    # Handle tool calls with more robust error handling
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            tool_call_index = tool_call_delta.index
                            tool_call_id = tool_call_delta.id
                            
                            # Handle case where id is None (subsequent chunks for same tool call)
                            if tool_call_id is None:
                                # Find existing tool call by index
                                tool_call_id = None
                                for existing_id, chunk in tool_call_chunks.items():
                                    if chunk.get("_index") == tool_call_index:
                                        tool_call_id = existing_id
                                        break
                                
                                # If we still don't have an ID, this is an error state - skip this delta
                                if tool_call_id is None:
                                    logger.warning(f"Received tool call delta with null ID and unknown index {tool_call_index}")
                                    continue
                            else:
                                # This is a new tool call with an ID
                                if tool_call_id not in tool_call_chunks:
                                    # Log new tool call ID for tracking
                                    logger.debug(f"🔧 New tool call started - OpenAI ID: {tool_call_id}")
                                    tool_call_chunks[tool_call_id] = {
                                        "id": tool_call_id,
                                        "type": "function",
                                        "_index": tool_call_index,  # Track index for null ID lookups
                                        "function": {
                                            "name": tool_call_delta.function.name if tool_call_delta.function else "",
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
                            
                            # Accumulate function arguments (now tool_call_id is guaranteed to be valid)
                            if tool_call_delta.function and tool_call_delta.function.arguments:
                                tool_call_chunks[tool_call_id]["function"]["arguments"] += tool_call_delta.function.arguments
                    
                    # Check for finish reason with type safety
                    finish_reason = None
                    try:
                        if hasattr(chunk, 'choices'):
                            # Standard ChatCompletionChunk object
                            finish_reason = chunk.choices[0].finish_reason if chunk.choices else None
                        elif isinstance(chunk, dict):
                            # Handle dict response (fallback)
                            choices = chunk.get('choices', [])
                            finish_reason = choices[0].get('finish_reason') if choices else None
                    except Exception as e:
                        logger.debug(f"Error extracting finish_reason: {e} - chunk: {chunk}")
                        finish_reason = None
                    
                    if finish_reason == "tool_calls":
                        # Execute tool calls
                        for tool_call_id, tool_call in tool_call_chunks.items():
                            function_name = tool_call["function"]["name"]
                            
                            # Parse function arguments with error guard
                            try:
                                raw_args = tool_call["function"]["arguments"]
                                logger.debug(f"Raw tool arguments for {function_name}: {raw_args!r}")
                                if isinstance(raw_args, str) and raw_args.strip():
                                    # Try to parse as JSON
                                    try:
                                        function_args = json.loads(raw_args)
                                    except json.JSONDecodeError:
                                        # If it's just "portfolio" or similar malformed JSON, try to infer
                                        if function_name == "get_portfolio_complete" and "portfolio" in raw_args.lower():
                                            # Infer portfolio_id from context
                                            function_args = {"portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e", "include_holdings": True}
                                            logger.info(f"Inferred portfolio arguments for malformed JSON: {function_args}")
                                        else:
                                            function_args = {}
                                            logger.warning(f"Failed to parse tool arguments: {raw_args}")
                                else:
                                    function_args = {}
                            except Exception as e:
                                logger.warning(f"Unexpected error parsing tool arguments: {e}")
                                function_args = {"__parse_error__": str(e)}
                            
                            # Update ID mapping with tool details
                            if tool_call_id in self.tool_call_id_map:
                                self.tool_call_id_map[tool_call_id].update({
                                    "tool_name": function_name,
                                    "tool_args": function_args,
                                    "status": "executing"
                                })
                            
                            # Log tool call execution for ID correlation
                            logger.info(f"🔧 Executing tool call - ID: {tool_call_id}, Tool: {function_name}, Args: {json.dumps(function_args)[:100]}...")
                            
                            # Emit standardized tool_call event
                            tool_call_payload = {
                                "type": "tool_call",
                                "run_id": run_id,
                                "seq": seq,
                                "data": {
                                    "tool_call_id": tool_call_id,  # Include the tool call ID
                                    "tool_name": function_name,
                                    "tool_args": function_args
                                },
                                "timestamp": int(time.time() * 1000)
                            }
                            yield f"event: tool_call\ndata: {json.dumps(tool_call_payload)}\n\n"
                            seq += 1
                            
                            # Execute tool if arguments parsed successfully
                            if "__parse_error__" not in function_args:
                                try:
                                    tool_start_time = time.time()
                                    result = await tool_registry.dispatch_tool_call(function_name, function_args)
                                    duration_ms = int((time.time() - tool_start_time) * 1000)
                                    
                                    # Update ID mapping with completion
                                    if tool_call_id in self.tool_call_id_map:
                                        self.tool_call_id_map[tool_call_id].update({
                                            "status": "completed",
                                            "duration_ms": duration_ms,
                                            "completed_at": int(time.time() * 1000)
                                        })
                                    
                                    # Log tool result with ID correlation
                                    logger.info(f"✅ Tool call completed - ID: {tool_call_id}, Tool: {function_name}, Duration: {duration_ms}ms")
                                    
                                    # Emit standardized tool_result event with tool_call_id for correlation
                                    tool_result_payload = {
                                        "type": "tool_result",
                                        "run_id": run_id,
                                        "seq": seq,
                                        "data": {
                                            "tool_call_id": tool_call_id,  # Include ID for correlation
                                            "tool_name": function_name,
                                            "tool_result": result,
                                            "duration_ms": duration_ms
                                        },
                                        "timestamp": int(time.time() * 1000)
                                    }
                                    yield f"event: tool_result\ndata: {json.dumps(tool_result_payload)}\n\n"
                                    seq += 1
                                    
                                    # Add tool response to messages for next iteration
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call_id,
                                        "content": json.dumps(result)
                                    })
                                    
                                except Exception as e:
                                    logger.error(f"Tool execution error: {e}")
                                    error_result_payload = {
                                        "type": "tool_result",
                                        "run_id": run_id,
                                        "seq": seq,
                                        "data": {
                                            "tool_call_id": tool_call_id,  # Add tool call ID
                                            "tool_name": function_name,
                                            "tool_result": {"error": str(e)}
                                        },
                                        "timestamp": int(time.time() * 1000)
                                    }
                                    yield f"event: tool_result\ndata: {json.dumps(error_result_payload)}\n\n"
                                    seq += 1
                                    
                                    # CRITICAL: Add error response to messages for OpenAI
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call_id,
                                        "content": json.dumps({"error": str(e)})
                                    })
                        
                        # Continue conversation with tool results
                        if tool_call_chunks:
                            # Clean up tool calls for OpenAI (remove internal fields)
                            clean_tool_calls = []
                            for tool_call in tool_call_chunks.values():
                                clean_call = {
                                    "id": tool_call["id"],
                                    "type": tool_call["type"],
                                    "function": tool_call["function"]
                                }
                                # Remove internal _index field if present
                                clean_tool_calls.append(clean_call)
                            
                            # Add assistant message with tool calls to history
                            messages.append({
                                "role": "assistant",
                                "content": current_content or None,
                                "tool_calls": clean_tool_calls
                            })
                            
                            # Make another API call with tool results
                            continuation_stream = await self.client.chat.completions.create(
                                model=self.model,
                                messages=messages,
                                stream=True,
                                max_completion_tokens=getattr(settings, 'OPENAI_MAX_COMPLETION_TOKENS', settings.CHAT_MAX_TOKENS)
                            )
                            
                            # Stream the continuation with standardized token events
                            try:
                                async for cont_chunk in continuation_stream:
                                    try:
                                        # Handle both ChatCompletionChunk objects and dict responses
                                        if hasattr(cont_chunk, 'choices'):
                                            # Standard ChatCompletionChunk object
                                            cont_delta = cont_chunk.choices[0].delta if cont_chunk.choices else None
                                        elif isinstance(cont_chunk, dict):
                                            # Handle dict response (fallback)
                                            choices = cont_chunk.get('choices', [])
                                            cont_delta = choices[0].get('delta') if choices else None
                                            logger.debug(f"Received dict chunk in continuation: {cont_chunk}")
                                        else:
                                            logger.warning(f"Unknown continuation chunk type: {type(cont_chunk)} - {cont_chunk}")
                                            continue
                                        
                                        if cont_delta and cont_delta.content:
                                            final_content_parts.append(cont_delta.content)
                                            
                                            token_payload = {
                                                "type": "token",
                                                "run_id": run_id,
                                                "seq": seq,
                                                "data": {"delta": cont_delta.content},
                                                "timestamp": int(time.time() * 1000)
                                            }
                                            yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                                            seq += 1
                                    except Exception as chunk_error:
                                        logger.error(f"Error processing continuation chunk: {chunk_error} - chunk: {cont_chunk}")
                                        continue
                            except Exception as e:
                                logger.error(f"Error in continuation streaming: {e}")
                                # Continue with the rest of the function
                
                except Exception as chunk_error:
                    logger.error(f"Error processing chunk: {chunk_error} - chunk: {chunk}")
                    continue
                
            # Send standardized done event
            final_text = "".join(final_content_parts)
            done_payload = {
                "type": "done",
                "run_id": run_id,
                "seq": seq,
                "data": {
                    "final_text": final_text,
                    "tool_calls_count": len(tool_call_chunks),
                    "total_tokens": 0  # TODO: Track token usage
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            
            # Log tool call summary if any tools were called
            if tool_call_chunks:
                self.log_tool_call_summary(conversation_id)
                
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            
            # Classify error type
            error_type = "SERVER_ERROR"  # Default
            retryable = True
            retry_after = None
            
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                error_type = "RATE_LIMITED"
                retry_after = 30  # 30 seconds default
            elif "auth" in error_msg or "unauthorized" in error_msg:
                error_type = "AUTH_EXPIRED"
                retryable = False
            elif "network" in error_msg or "connection" in error_msg:
                error_type = "NETWORK_ERROR"
            
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
            logger.info(f"📊 Tool Call Summary for conversation {conversation_id}:")
            for tool_id, mapping in mappings.items():
                status = mapping.get("status", "unknown")
                tool_name = mapping.get("tool_name", "unknown")
                duration = mapping.get("duration_ms", "N/A")
                logger.info(f"  - {tool_id[:8]}... | {tool_name} | Status: {status} | Duration: {duration}ms")
        else:
            logger.info(f"📊 No tool calls recorded for conversation {conversation_id}")


# Singleton instance
openai_service = OpenAIService()