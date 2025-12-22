"""
AI Metrics Recording Service

Records AI request metrics for admin dashboard analytics (Phase 4).
Uses fire-and-forget pattern to avoid impacting chat response latency.

Created: December 22, 2025 (Phase 4 Admin Dashboard)
"""
import asyncio
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from app.database import get_async_session
from app.models.admin import AIRequestMetrics
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIMetricsService:
    """Service for recording AI request metrics."""

    @classmethod
    def record_metrics(
        cls,
        conversation_id: UUID,
        message_id: UUID,
        user_id: Optional[UUID],
        model: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        first_token_ms: Optional[int] = None,
        total_latency_ms: Optional[int] = None,
        tool_calls_count: int = 0,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """
        Fire-and-forget metrics recording.

        Does not block the calling code. Failures are logged but don't
        affect the user experience.

        Args:
            conversation_id: UUID of the conversation
            message_id: UUID of the assistant message
            user_id: UUID of the user (optional)
            model: Model name used (e.g., "gpt-4o")
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
            total_tokens: Total tokens (input + output)
            first_token_ms: Time to first token in milliseconds
            total_latency_ms: Total response time in milliseconds
            tool_calls_count: Number of tool calls made
            tool_calls: List of tool call details
            error_type: Type of error if request failed
            error_message: Error message if request failed
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    cls._record_metrics_async(
                        conversation_id=conversation_id,
                        message_id=message_id,
                        user_id=user_id,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                        first_token_ms=first_token_ms,
                        total_latency_ms=total_latency_ms,
                        tool_calls_count=tool_calls_count,
                        tool_calls=tool_calls,
                        error_type=error_type,
                        error_message=error_message,
                    )
                )
            else:
                # Fallback: run synchronously if no event loop
                asyncio.run(
                    cls._record_metrics_async(
                        conversation_id=conversation_id,
                        message_id=message_id,
                        user_id=user_id,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=total_tokens,
                        first_token_ms=first_token_ms,
                        total_latency_ms=total_latency_ms,
                        tool_calls_count=tool_calls_count,
                        tool_calls=tool_calls,
                        error_type=error_type,
                        error_message=error_message,
                    )
                )
        except Exception as e:
            logger.warning(f"[AIMetrics] Failed to schedule metrics recording: {e}")

    @classmethod
    async def _record_metrics_async(
        cls,
        conversation_id: UUID,
        message_id: UUID,
        user_id: Optional[UUID],
        model: str,
        input_tokens: Optional[int],
        output_tokens: Optional[int],
        total_tokens: Optional[int],
        first_token_ms: Optional[int],
        total_latency_ms: Optional[int],
        tool_calls_count: int,
        tool_calls: Optional[List[Dict[str, Any]]],
        error_type: Optional[str],
        error_message: Optional[str],
    ):
        """
        Async implementation of metrics recording.

        Uses Core database session (ai_request_metrics is in Core DB).
        """
        try:
            async with get_async_session() as db:
                # Prepare tool_calls for JSONB storage
                tool_calls_json = None
                if tool_calls:
                    # Extract tool names and simplify structure for storage
                    tool_calls_json = {
                        "tools": [
                            {
                                "name": tc.get("function", {}).get("name", "unknown"),
                                "id": tc.get("id"),
                            }
                            for tc in tool_calls
                        ]
                    }

                metrics = AIRequestMetrics(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    user_id=user_id,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    first_token_ms=first_token_ms,
                    total_latency_ms=total_latency_ms,
                    tool_calls_count=tool_calls_count,
                    tool_calls=tool_calls_json,
                    error_type=error_type,
                    error_message=error_message,
                )

                db.add(metrics)
                await db.commit()

                logger.debug(
                    f"[AIMetrics] Recorded metrics for message {message_id}: "
                    f"model={model}, input={input_tokens}, output={output_tokens}, "
                    f"latency={total_latency_ms}ms, tools={tool_calls_count}"
                )

        except Exception as e:
            logger.warning(f"[AIMetrics] Failed to record metrics: {e}")


# Convenience function for direct import
def record_ai_metrics(
    conversation_id: UUID,
    message_id: UUID,
    user_id: Optional[UUID],
    model: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    first_token_ms: Optional[int] = None,
    total_latency_ms: Optional[int] = None,
    tool_calls_count: int = 0,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """
    Fire-and-forget AI metrics recording.

    Example usage:
        record_ai_metrics(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            user_id=current_user.id,
            model="gpt-4o",
            input_tokens=150,
            output_tokens=200,
            total_tokens=350,
            first_token_ms=450,
            total_latency_ms=3500,
            tool_calls_count=2,
            tool_calls=[...],
        )
    """
    AIMetricsService.record_metrics(
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=user_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        first_token_ms=first_token_ms,
        total_latency_ms=total_latency_ms,
        tool_calls_count=tool_calls_count,
        tool_calls=tool_calls,
        error_type=error_type,
        error_message=error_message,
    )
