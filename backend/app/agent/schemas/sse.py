"""
Server-Sent Events (SSE) schemas for Agent streaming
"""
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field
from app.agent.schemas.base import AgentBaseSchema


class SSEEvent(AgentBaseSchema):
    """Base SSE event structure"""
    event: str = Field(..., description="Event type: start|message|tool_call|tool_result|error|done")
    data: Dict[str, Any] = Field(default_factory=dict)


class SSEStartEvent(AgentBaseSchema):
    """SSE start event data"""
    conversation_id: str
    mode: str
    model: str = "gpt-5"


class SSEMessageEvent(AgentBaseSchema):
    """SSE message event data (text delta)"""
    delta: str = Field(..., description="Text chunk")
    role: str = "assistant"


class SSEToolCallEvent(AgentBaseSchema):
    """SSE tool call event data"""
    tool_name: str
    tool_id: str
    arguments: Dict[str, Any]


class SSEToolResultEvent(AgentBaseSchema):
    """SSE tool result event data"""
    tool_name: str
    tool_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class SSEErrorEvent(AgentBaseSchema):
    """SSE error event data with standardized error types"""
    message: str
    error_type: Optional[Literal[
        "AUTH_EXPIRED",
        "RATE_LIMITED", 
        "NETWORK_ERROR",
        "SERVER_ERROR",
        "FATAL_ERROR"
    ]] = None
    code: Optional[str] = None
    retryable: bool = True
    retry_after: Optional[int] = None  # For RATE_LIMITED errors (seconds)
    details: Optional[Dict[str, Any]] = None


class SSEToolStartedEvent(AgentBaseSchema):
    """SSE tool started event data"""
    tool_name: str
    arguments: Dict[str, Any]


class SSEToolFinishedEvent(AgentBaseSchema):
    """SSE tool finished event data"""
    tool_name: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None


class SSEHeartbeatEvent(AgentBaseSchema):
    """SSE heartbeat event for keeping connection alive"""
    timestamp: str


class SSEDoneEvent(AgentBaseSchema):
    """SSE completion event data"""
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    tool_calls_count: int = 0