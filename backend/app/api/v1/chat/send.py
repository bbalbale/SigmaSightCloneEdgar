"""
SSE streaming endpoint for chat messages
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import asyncio
import json
import time
from typing import AsyncGenerator, List, Dict, Any
from uuid import uuid4
from datetime import datetime
import random

from app.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.agent.models.conversations import Conversation, ConversationMessage
from app.agent.schemas.chat import MessageSend
from app.agent.schemas.sse import (
    SSEStartEvent,
    SSEMessageEvent,
    SSEDoneEvent,
    SSEErrorEvent,
    SSEHeartbeatEvent
)
from app.agent.services.openai_service import openai_service
from app.core.datetime_utils import utc_now
from app.core.logging import get_logger
from app.config import settings
from app.api.v1.data import get_portfolio_complete as get_portfolio_complete_endpoint
from uuid import UUID

logger = get_logger(__name__)

router = APIRouter()


async def load_message_history(
    conversation_id: str,
    db: AsyncSession,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Load recent message history for a conversation"""
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    # Convert to dict format and reverse to chronological order
    history = []
    for msg in reversed(messages):
        msg_dict = {
            "role": msg.role,
            "content": msg.content
        }
        # Phase 9.9.2: Do not include tool_calls in history to prevent contamination
        # Tool calls are handled in fresh context by openai_service filtering
        history.append(msg_dict)
    
    return history


async def sse_generator(
    message_text: str,
    conversation: Conversation,
    db: AsyncSession,
    current_user: CurrentUser,
    request: Request = None
) -> AsyncGenerator[str, None]:
    """
    Generate Server-Sent Events for the chat response using OpenAI.
    """
    response_start_time = datetime.now()
    run_id = f"run_{uuid4().hex[:12]}"
    # Initialize timing and timeline early for use by all events
    start_time = time.time()
    event_timeline: List[Dict[str, Any]] = []
    
    try:
        # Handle mode switching
        if message_text.startswith("/mode "):
            new_mode = message_text[6:].strip()
            if new_mode in ["green", "blue", "indigo", "violet"]:
                conversation.mode = new_mode
                conversation.updated_at = utc_now()
                await db.commit()
                
                # Send start event
                start_event = SSEStartEvent(
                    conversation_id=str(conversation.id),
                    mode=new_mode,
                    model=settings.MODEL_DEFAULT
                )
                yield f"event: start\ndata: {json.dumps(start_event.model_dump())}\n\n"
                
                # Send mode change message
                mode_change_msg = SSEMessageEvent(
                    delta=f"Mode changed to {new_mode}",
                    role="system"
                )
                yield f"event: message\ndata: {json.dumps(mode_change_msg.model_dump())}\n\n"
                
                # Send standardized done event envelope
                done_payload = {
                    "type": "done",
                    "run_id": run_id,
                    "seq": 0,
                    "data": {
                        "final_text": f"Mode changed to {new_mode}",
                        "tool_calls_count": 0
                    },
                    "timestamp": int(time.time() * 1000)
                }
                yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
                return
        
        # Load message history
        message_history = await load_message_history(conversation.id, db)
        
        # Get portfolio context if available (stored in metadata)
        portfolio_context = None
        portfolio_id = conversation.meta_data.get("portfolio_id") if conversation.meta_data else None
        if portfolio_id:
            # Fetch portfolio data to include in context using the existing API endpoint
            try:
                # Convert to UUID if needed
                portfolio_uuid = UUID(portfolio_id) if isinstance(portfolio_id, str) else portfolio_id

                # Call the endpoint function directly (it handles all the database queries)
                portfolio_snapshot = await get_portfolio_complete_endpoint(
                    portfolio_id=portfolio_uuid,
                    include_holdings=True,
                    include_position_tags=False,  # Don't need tags for AI context
                    include_timeseries=False,
                    include_attrib=False,
                    as_of_date=None,
                    current_user=current_user,
                    db=db
                )

                portfolio_context = {
                    "portfolio_id": str(portfolio_id),
                    "portfolio_name": portfolio_snapshot.get("portfolio_name"),
                    "total_value": portfolio_snapshot.get("total_market_value"),
                    "position_count": len(portfolio_snapshot.get("holdings", [])),
                    "holdings": portfolio_snapshot.get("holdings", [])[:50]  # Limit to top 50 positions
                }
                logger.info(f"Using portfolio context with {len(portfolio_snapshot.get('holdings', []))} positions for conversation: portfolio_id={portfolio_id}")
            except Exception as e:
                logger.warning(f"Failed to fetch portfolio data for context: {e}, using portfolio_id only")
                portfolio_context = {
                    "portfolio_id": str(portfolio_id)
                }
                logger.info(f"Using portfolio context (ID only) for conversation: portfolio_id={portfolio_id}")
        
        # [TRACE] TRACE-2 Send Context (Phase 9.12.1 investigation)
        logger.info(f"[TRACE] TRACE-2 Send Context: conversation={conversation.id} | portfolio_context={portfolio_context}")
        
        # Create BOTH messages upfront with backend-generated IDs
        user_message = ConversationMessage(
            id=uuid4(),
            conversation_id=conversation.id,
            role="user",
            content=message_text,
            created_at=utc_now()
        )
        db.add(user_message)
        
        # Create assistant message placeholder that will be updated during streaming
        assistant_message = ConversationMessage(
            id=uuid4(),
            conversation_id=conversation.id,
            role="assistant",
            content="",  # Will be updated during streaming
            created_at=utc_now()
        )
        db.add(assistant_message)
        
        # Use transaction to ensure both messages created or neither
        try:
            await db.commit()
            await db.refresh(user_message)
            await db.refresh(assistant_message)
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create messages: {e}")
            error_payload = {
                "type": "error",
                "run_id": run_id,
                "seq": 0,
                "data": {
                    "error": "Failed to create messages",
                    "error_type": "SERVER_ERROR",
                    "retryable": False
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
            return
        
        # Extract authentication token from request (Bearer header or cookie)
        auth_context = None
        auth_token = None
        
        if request:
            # Try Bearer token first (preferred)
            authorization_header = request.headers.get("authorization")
            if authorization_header and authorization_header.startswith("Bearer "):
                auth_token = authorization_header[7:]  # Remove "Bearer " prefix
            # Fallback to auth cookie (used by chat interface)
            elif "auth_token" in request.cookies:
                auth_token = request.cookies["auth_token"]
        
        # If we have any valid token, pass it to tools for authentication
        if auth_token:
            auth_context = {
                "auth_token": auth_token,
                "user_id": str(current_user.id)
            }
        
        # EMIT message_created event with both IDs
        message_created_event = {
            "user_message_id": str(user_message.id),
            "assistant_message_id": str(assistant_message.id),
            "conversation_id": str(conversation.id),
            "run_id": run_id
        }
        yield f"event: message_created\ndata: {json.dumps(message_created_event)}\n\n"
        # Record timeline: message_created
        event_timeline.append({
            "type": "message_created",
            "t_ms": int((time.time() - start_time) * 1000)
        })
        
        # Stream OpenAI response with retry/backoff and optional fallback model
        assistant_content = ""
        tool_calls_made = []
        first_token_time = None
        openai_response_id = None
        tokens_received_total = 0
        upstream_token_counts = None
        last_tool_result_ts = None
        post_tool_first_token_gaps_ms: list[int] = []
        upstream_final_text = None
        start_event_forwarded = False
        tokens_forwarded_any = False

        max_retries = getattr(settings, "SSE_MAX_STREAM_RETRIES", 2)
        backoff_base_ms = getattr(settings, "SSE_RETRY_BACKOFF_BASE_MS", 500)
        backoff_multiplier = getattr(settings, "SSE_RETRY_BACKOFF_MULTIPLIER", 2.0)
        backoff_max_ms = getattr(settings, "SSE_RETRY_BACKOFF_MAX_MS", 5000)
        backoff_jitter_ms = getattr(settings, "SSE_RETRY_JITTER_MS", 250)
        use_model_fallback = getattr(settings, "SSE_USE_MODEL_FALLBACK", True)

        attempts = 0
        success = False
        last_error_obj: Dict[str, Any] | None = None
        final_model_used = settings.MODEL_DEFAULT
        fallback_model = settings.MODEL_FALLBACK
        fallback_used_flag = False

        while attempts <= max_retries:
            model_for_attempt = final_model_used
            if attempts > 0 and use_model_fallback and fallback_model and not tokens_forwarded_any:
                # Switch to fallback after first failure (no tokens yet)
                event_timeline.append({
                    "type": "fallback_switch",
                    "t_ms": int((time.time() - start_time) * 1000)
                })
                model_for_attempt = fallback_model
                fallback_used_flag = True
                info_payload = {
                    "type": "info",
                    "run_id": run_id,
                    "seq": 0,
                    "data": {
                        "info_type": "model_switch",
                        "from": final_model_used,
                        "to": model_for_attempt,
                        "attempt": attempts + 1
                    },
                    "timestamp": int(time.time() * 1000)
                }
                yield f"event: info\ndata: {json.dumps(info_payload)}\n\n"

            # Reset per-attempt state
            assistant_content = ""
            first_token_time = None
            openai_response_id = None
            upstream_token_counts = None
            last_tool_result_ts = None
            post_tool_first_token_gaps_ms = []
            upstream_final_text = None

            attempt_had_error = False
            attempt_error_retryable = False
            attempt_error_message = None

            # Start streaming for this attempt
            event_timeline.append({
                "type": "attempt_start",
                "t_ms": int((time.time() - start_time) * 1000),
            })

            async for sse_event in openai_service.stream_responses(
                conversation_id=str(conversation.id),
                conversation_mode=conversation.mode,
                message_text=message_text,
                message_history=message_history,
                portfolio_context=portfolio_context,
                auth_context=auth_context,
                run_id=run_id,
                model_override=model_for_attempt
            ):
                # Intercept service 'done' for metrics only
                if "event: done" in sse_event:
                    try:
                        data_line = sse_event.split("\ndata: ")[1].split("\n")[0]
                        data_obj = json.loads(data_line)
                        upstream_token_counts = data_obj.get("data", {}).get("token_counts")
                        upstream_final_text = data_obj.get("data", {}).get("final_text")
                    except Exception as e:
                        logger.warning(f"Failed to parse upstream done event for token_counts: {e}")
                    # Don't forward upstream done, but break the stream loop
                    break

                # On subsequent attempts, suppress duplicate start events
                if "event: start" in sse_event:
                    # Timeline: start event
                    event_timeline.append({
                        "type": "start",
                        "t_ms": int((time.time() - start_time) * 1000)
                    })
                    if not start_event_forwarded:
                        start_event_forwarded = True
                        yield sse_event
                    continue

                # Detect upstream error to decide on retry strategy
                if "event: error" in sse_event:
                    event_timeline.append({
                        "type": "error",
                        "t_ms": int((time.time() - start_time) * 1000)
                    })
                    try:
                        data_line = sse_event.split("\ndata: ")[1].split("\n")[0]
                        data_obj = json.loads(data_line)
                        err_data = data_obj.get("data", {})
                        attempt_had_error = True
                        attempt_error_retryable = bool(err_data.get("retryable", True))
                        attempt_error_message = err_data.get("error") or err_data.get("message") or "Unknown error"
                        last_error_obj = err_data
                    except Exception:
                        attempt_had_error = True
                        attempt_error_retryable = True
                        attempt_error_message = "Unknown error"
                    # Do not forward upstream error; we'll handle retry and only emit final error if exhausted
                    break

                # Forward the SSE event for non-done/non-error
                yield sse_event

                # Parse for metrics and content accumulation
                if "event: response_id" in sse_event:
                    event_timeline.append({
                        "type": "response_id",
                        "t_ms": int((time.time() - start_time) * 1000)
                    })
                    try:
                        data_line = sse_event.split("\ndata: ")[1].split("\n")[0]
                        data = json.loads(data_line)
                        openai_response_id = data.get("data", {}).get("response_id")
                        if openai_response_id:
                            logger.info(
                                f"[LINK] OpenAI Response Started - "
                                f"Response ID: {openai_response_id} | "
                                f"Conversation: {conversation.id} | "
                                f"User: {current_user.id} | "
                                f"Mode: {conversation.mode} | "
                                f"Run ID: {run_id} | "
                                f"Message Length: {len(message_text)} chars"
                            )
                    except Exception as e:
                        logger.error(f"Failed to parse response_id SSE event: {e}")
                elif "event: token" in sse_event:
                    try:
                        data_line = sse_event.split("\ndata: ")[1].split("\n")[0]
                        event_obj = json.loads(data_line)
                        delta = event_obj.get("data", {}).get("delta")
                        if delta:
                            assistant_content += delta
                            if not first_token_time:
                                first_token_time = time.time()
                                event_timeline.append({
                                    "type": "token_first",
                                    "t_ms": int((time.time() - start_time) * 1000)
                                })
                            tokens_received_total += 1
                            tokens_forwarded_any = True
                            if last_tool_result_ts is not None:
                                gap_ms = int((time.time() - last_tool_result_ts) * 1000)
                                post_tool_first_token_gaps_ms.append(gap_ms)
                                last_tool_result_ts = None
                    except Exception:
                        pass
                elif "event: message" in sse_event:
                    try:
                        data_line = sse_event.split("\ndata: ")[1].split("\n")[0]
                        data = json.loads(data_line)
                        if data.get("delta"):
                            assistant_content += data["delta"]
                            if not first_token_time:
                                first_token_time = time.time()
                                event_timeline.append({
                                    "type": "token_first",
                                    "t_ms": int((time.time() - start_time) * 1000)
                                })
                            tokens_received_total += 1
                            tokens_forwarded_any = True
                    except Exception:
                        pass
                elif "event: tool_call" in sse_event:
                    event_timeline.append({
                        "type": "tool_call",
                        "t_ms": int((time.time() - start_time) * 1000)
                    })
                    try:
                        data_line = sse_event.split("\ndata: ")[1].split("\n")[0]
                        event_obj = json.loads(data_line)
                        inner = event_obj.get("data", {})
                        tool_call_id = inner.get("tool_call_id", f"call_{uuid4().hex[:24]}")
                        tool_name = inner.get("tool_name")
                        if not tool_name or not isinstance(tool_name, str):
                            logger.warning(f"Invalid tool_name in SSE event: {tool_name} (type: {type(tool_name)})")
                            tool_name = "unknown_tool"
                        tool_calls_made.append({
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(inner.get("tool_args", {}))
                            }
                        })
                    except Exception as e:
                        logger.error(f"Failed to parse tool_call SSE event: {e}")
                elif "event: tool_result" in sse_event:
                    try:
                        last_tool_result_ts = time.time()
                        event_timeline.append({
                            "type": "tool_result",
                            "t_ms": int((time.time() - start_time) * 1000)
                        })
                    except Exception:
                        last_tool_result_ts = time.time()

            # After attempt stream ends, decide to retry or finalize
            if attempt_had_error and attempt_error_retryable and not tokens_forwarded_any and attempts < max_retries:
                # Schedule retry with exponential backoff
                delay_ms = min(int(backoff_base_ms * (backoff_multiplier ** attempts)) + random.randint(0, backoff_jitter_ms), backoff_max_ms)
                event_timeline.append({
                    "type": "retry_scheduled",
                    "t_ms": int((time.time() - start_time) * 1000),
                    "delay_ms": delay_ms
                })
                info_payload = {
                    "type": "info",
                    "run_id": run_id,
                    "seq": 0,
                    "data": {
                        "info_type": "retry_scheduled",
                        "attempt": attempts + 1,
                        "max_attempts": max_retries + 1,
                        "retry_in_ms": delay_ms,
                        "retryable": True
                    },
                    "timestamp": int(time.time() * 1000)
                }
                yield f"event: info\ndata: {json.dumps(info_payload)}\n\n"
                await asyncio.sleep(delay_ms / 1000.0)
                attempts += 1
                continue

            # No retry or success path
            final_model_used = model_for_attempt
            success = not attempt_had_error
            break

        # Update assistant message with final content and metrics
        assistant_message.content = assistant_content
        assistant_message.tool_calls = None
        if openai_response_id:
            assistant_message.provider_message_id = openai_response_id
            logger.info(f"[LINK] Stored OpenAI Response ID: {openai_response_id} for message {assistant_message.id} in conversation {conversation.id}")
        if first_token_time:
            assistant_message.first_token_ms = int((first_token_time - start_time) * 1000)
        assistant_message.latency_ms = int((time.time() - start_time) * 1000)
        await db.commit()

        latency_ms = int((datetime.now() - response_start_time).total_seconds() * 1000)

        if success:
            final_text_out = assistant_content or upstream_final_text or ""
            fallback_used = (bool(upstream_final_text) and not assistant_content) or fallback_used_flag
            event_timeline.append({
                "type": "done_emit",
                "t_ms": int((time.time() - start_time) * 1000)
            })
            done_payload = {
                "type": "done",
                "run_id": run_id,
                "seq": 0,
                "data": {
                    "final_text": final_text_out,
                    "tool_calls_count": len(tool_calls_made),
                    "latency_ms": latency_ms,
                    "token_counts": upstream_token_counts or {"initial": tokens_received_total, "continuation": 0},
                    "post_tool_first_token_gaps_ms": post_tool_first_token_gaps_ms,
                    "event_timeline": event_timeline,
                    "fallback_used": fallback_used,
                    "model_used": final_model_used,
                    "retry_stats": {
                        "attempts": attempts + 1,
                        "max_retries": max_retries,
                        "used_fallback_model": fallback_used_flag
                    }
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            try:
                logger.info(f"Event timeline (ms since start): {event_timeline}")
                if fallback_used:
                    logger.warning("Used upstream final_text or model fallback due to issues in primary attempt")
            except Exception:
                pass
            return  # Properly close the generator after done event
        else:
            # All attempts failed or non-retryable error
            error_payload = {
                "type": "error",
                "run_id": run_id,
                "seq": 0,
                "data": {
                    "error": last_error_obj.get("error") if last_error_obj else "Streaming failed",
                    "error_type": (last_error_obj.get("error_type") if last_error_obj else "STREAM_FAILED"),
                    "retryable": False,
                    "attempts": attempts + 1
                },
                "timestamp": int(time.time() * 1000)
            }
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
            return  # Properly close the generator after error event
        
    except Exception as e:
        logger.error(f"SSE generator error: {e}")
        error_payload = {
            "type": "error",
            "run_id": run_id,
            "seq": 0,
            "data": {
                "error": str(e),
                "error_type": "SERVER_ERROR",
                "retryable": True
            },
            "timestamp": int(time.time() * 1000)
        }
        yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
        return  # Properly close the generator after exception error event


@router.post("/send")
async def send_message(
    http_request: Request,  # FastAPI Request object for headers
    message_data: MessageSend,  # Renamed to avoid confusion
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
) -> StreamingResponse:
    """
    Send a message to a conversation and stream the response via SSE.
    
    Args:
        http_request: FastAPI Request object for accessing headers
        message_data: MessageSend schema with conversation_id and text
        db: Database session
        current_user: Authenticated user
        
    Returns:
        StreamingResponse with Server-Sent Events
    """
    try:
        # Load conversation
        result = await db.execute(
            select(Conversation)
            .where(
                Conversation.id == message_data.conversation_id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Verify user owns the conversation
        if conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )
        
        # Create SSE generator
        generator = sse_generator(
            message_data.text,
            conversation,
            db,
            current_user,
            http_request
        )
        
        # Return streaming response
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": http_request.headers.get('origin', 'http://localhost:3005'),
                "Access-Control-Allow-Credentials": "true",  # Enable credentials for SSE
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )