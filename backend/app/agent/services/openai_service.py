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
        
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Default tool definitions method - delegates to Responses API format"""
        return self._get_tool_definitions_responses()
    
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
                            logger.debug(f"🔧 Tool call item added - ID: {tool_call_id}, Function: {function_name}")
                        
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
                            logger.debug(f"🔧 Tool call arguments started - ID: {tool_call_id}, Tool: {function_name}")
                            
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
                        
                    elif event.type == "response.failed":
                        # Phase 5.9.5.2: Handle API failures gracefully instead of silent failures
                        error_message = str(getattr(event, 'error', 'Unknown API failure'))
                        logger.error(f"OpenAI API failure for response {response_id}: {error_message}")
                        
                        error_payload = {
                            "type": "error",
                            "run_id": run_id,
                            "seq": seq,
                            "data": {
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