"""
Chat-related schemas for Agent
"""
from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import Field
from app.agent.schemas.base import AgentBaseSchema


class ConversationCreate(AgentBaseSchema):
    """Request schema for creating a conversation"""
    mode: str = Field(default="green", pattern="^(green|blue|indigo|violet)$")
    portfolio_id: Optional[str] = Field(None, description="Portfolio ID to associate with conversation")
    portfolio_ids: Optional[list[str]] = Field(None, description="Multiple portfolio IDs for aggregate context")
    page_hint: Optional[str] = Field(None, description="Page/feature hint for routing tools & RAG")
    route: Optional[str] = Field(None, description="Route path for additional context")


class ConversationResponse(AgentBaseSchema):
    """Response schema for conversation creation"""
    id: UUID
    mode: str
    created_at: datetime
    provider: str = "openai"
    provider_thread_id: Optional[str] = None


class UIContext(AgentBaseSchema):
    """UI context passed from the frontend for routing, RAG, and prompting"""

    page_hint: Optional[str] = Field(None, description="Page/feature hint (e.g., portfolio, ai-chat)")
    route: Optional[str] = Field(None, description="Route path for finer scoping (optional)")
    portfolio_id: Optional[str] = Field(None, description="Portfolio context override")
    portfolio_ids: Optional[list[str]] = Field(None, description="Multiple portfolio IDs for aggregate context")
    selection: Optional[dict] = Field(None, description="Current selection (symbol, tag, etc.)")


class MessageSend(AgentBaseSchema):
    """Request schema for sending a message"""
    conversation_id: UUID
    text: str = Field(..., min_length=1, max_length=4000)
    ui_context: Optional[UIContext] = Field(None, description="UI context for this turn")


class MessageResponse(AgentBaseSchema):
    """Response schema for message (used in non-streaming contexts)"""
    message_id: UUID
    role: str
    content: str
    created_at: datetime
    tool_calls: Optional[list] = None


class MessageCreateRequest(AgentBaseSchema):
    """Request to pre-create messages (backend-first ID generation)"""
    conversation_id: UUID
    text: str = Field(..., min_length=1, max_length=4000)


class MessageCreatedResponse(AgentBaseSchema):
    """Response containing created user and assistant message IDs"""
    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID


class MessageUpdateRequest(AgentBaseSchema):
    """Incremental message update payload"""
    content: Optional[str] = None
    tool_calls: Optional[list] = None
    first_token_ms: Optional[int] = None
    latency_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    provider_message_id: Optional[str] = None
    error: Optional[dict] = None


class ModeChangeRequest(AgentBaseSchema):
    """Request schema for changing conversation mode"""
    mode: str = Field(..., pattern="^(green|blue|indigo|violet)$")


class ModeChangeResponse(AgentBaseSchema):
    """Response schema for mode change"""
    id: UUID
    previous_mode: str
    new_mode: str
    changed_at: datetime
