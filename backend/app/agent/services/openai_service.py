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
        
    def _get_tool_definitions(self) -> List[ChatCompletionToolParam]:
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
            # Handle tool calls if they exist in history
            if msg.get("tool_calls"):
                messages.append({
                    "role": "assistant",
                    "content": msg.get("content", ""),
                    "tool_calls": msg["tool_calls"]
                })
                # Add tool responses
                for tool_call in msg["tool_calls"]:
                    if tool_response := msg.get(f"tool_response_{tool_call['id']}"):
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(tool_response)
                        })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    async def stream_chat_completion(
        self,
        conversation_id: str,
        conversation_mode: str,
        message_text: str,
        message_history: List[Dict[str, Any]] = None,
        portfolio_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion with tool calling support
        
        Yields SSE formatted events with standardized contract (type, run_id, seq fields)
        """
        run_id = str(uuid.uuid4())
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
            
            # Call OpenAI with streaming
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                stream=True,
                max_completion_tokens=settings.CHAT_MAX_TOKENS
            )
            
            # Track state for streaming
            current_content = ""
            current_tool_calls = []
            tool_call_chunks = {}
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = settings.SSE_HEARTBEAT_INTERVAL_MS / 1000.0
            
            async for chunk in stream:
                # Debug: Log chunk details
                logger.info(f"OpenAI chunk received: {chunk}")
                
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
                
                delta = chunk.choices[0].delta if chunk.choices else None
                logger.info(f"Delta extracted: {delta}")
                if not delta:
                    continue
                
                # Handle content streaming with standardized token events
                if delta.content:
                    current_content += delta.content
                    final_content_parts.append(delta.content)
                    
                    # Emit standardized token event
                    token_payload = {
                        "type": "token",
                        "run_id": run_id,
                        "seq": seq,
                        "data": {"delta": delta.content},
                        "timestamp": int(time.time() * 1000)
                    }
                    yield f"event: token\ndata: {json.dumps(token_payload)}\n\n"
                    seq += 1
                
                # Handle tool calls with JSON parsing guards
                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        tool_call_id = tool_call_delta.id
                        
                        if tool_call_id not in tool_call_chunks:
                            tool_call_chunks[tool_call_id] = {
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": tool_call_delta.function.name if tool_call_delta.function else "",
                                    "arguments": ""
                                }
                            }
                        
                        # Accumulate function arguments
                        if tool_call_delta.function and tool_call_delta.function.arguments:
                            tool_call_chunks[tool_call_id]["function"]["arguments"] += tool_call_delta.function.arguments
                
                # Check for finish reason
                if chunk.choices and chunk.choices[0].finish_reason == "tool_calls":
                    # Execute tool calls
                    for tool_call_id, tool_call in tool_call_chunks.items():
                        function_name = tool_call["function"]["name"]
                        
                        # Parse function arguments with error guard
                        try:
                            raw_args = tool_call["function"]["arguments"]
                            if isinstance(raw_args, str) and raw_args.strip():
                                function_args = json.loads(raw_args)
                            else:
                                function_args = {}
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse tool arguments: {e}. Raw: {raw_args}")
                            function_args = {"__parse_error__": str(e), "raw": raw_args}
                        except Exception as e:
                            logger.warning(f"Unexpected error parsing tool arguments: {e}")
                            function_args = {"__parse_error__": str(e)}
                        
                        # Emit standardized tool_call event
                        tool_call_payload = {
                            "type": "tool_call",
                            "run_id": run_id,
                            "seq": seq,
                            "data": {
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
                                result = await tool_registry.dispatch(function_name, **function_args)
                                duration_ms = int((time.time() - tool_start_time) * 1000)
                                
                                # Emit standardized tool_result event
                                tool_result_payload = {
                                    "type": "tool_result",
                                    "run_id": run_id,
                                    "seq": seq,
                                    "data": {
                                        "tool_name": function_name,
                                        "tool_result": result
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
                                        "tool_name": function_name,
                                        "tool_result": {"error": str(e)}
                                    },
                                    "timestamp": int(time.time() * 1000)
                                }
                                yield f"event: tool_result\ndata: {json.dumps(error_result_payload)}\n\n"
                                seq += 1
                    
                    # Continue conversation with tool results
                    if tool_call_chunks:
                        # Add assistant message with tool calls to history
                        messages.append({
                            "role": "assistant",
                            "content": current_content or None,
                            "tool_calls": list(tool_call_chunks.values())
                        })
                        
                        # Make another API call with tool results
                        continuation_stream = await self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            stream=True,
                            max_completion_tokens=settings.CHAT_MAX_TOKENS
                        )
                        
                        # Stream the continuation with standardized token events
                        async for cont_chunk in continuation_stream:
                            cont_delta = cont_chunk.choices[0].delta if cont_chunk.choices else None
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


# Singleton instance
openai_service = OpenAIService()