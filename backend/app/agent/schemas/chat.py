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


class ConversationResponse(AgentBaseSchema):
    """Response schema for conversation creation"""
    id: UUID
    mode: str
    created_at: datetime
    provider: str = "openai"
    provider_thread_id: Optional[str] = None


class MessageSend(AgentBaseSchema):
    """Request schema for sending a message"""
    conversation_id: UUID
    text: str = Field(..., min_length=1, max_length=4000)


class MessageResponse(AgentBaseSchema):
    """Response schema for message (used in non-streaming contexts)"""
    message_id: UUID
    role: str
    content: str
    created_at: datetime
    tool_calls: Optional[list] = None


class ModeChangeRequest(AgentBaseSchema):
    """Request schema for changing conversation mode"""
    mode: str = Field(..., pattern="^(green|blue|indigo|violet)$")


class ModeChangeResponse(AgentBaseSchema):
    """Response schema for mode change"""
    id: UUID
    previous_mode: str
    new_mode: str
    changed_at: datetime