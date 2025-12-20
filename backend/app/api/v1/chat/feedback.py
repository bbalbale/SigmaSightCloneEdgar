"""
Feedback endpoint for AI message ratings.

Allows users to provide thumbs up/down feedback on AI-generated messages.
This data is used for offline analysis and knowledge base improvement.

Phase 3 Enhancement (December 2025):
- Added background learning processing on feedback submission
- Positive feedback stores response as RAG example
- Negative feedback with edits extracts preference rules

Dual-DB Architecture Note (December 2025):
- ConversationMessage/Conversation live in Core DB (get_db)
- AIFeedback lives in AI DB (get_ai_db)
- The main endpoints currently use get_db for both, which works because
  ai_feedback table was also created in Core DB during initial migration.
- TODO: Refactor to use separate sessions for clean dual-DB separation.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.agent.models.conversations import Conversation, ConversationMessage
from app.models.ai_learning import AIFeedback
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _run_learning_background(feedback_id: UUID) -> None:
    """
    Background task to process feedback and trigger learning.

    This runs asynchronously after the feedback is saved, so it doesn't
    block the response to the user.

    NOTE: AIFeedback lives in the AI database (dual-DB architecture).
    """
    try:
        # Import here to avoid circular imports
        from app.agent.services.learning_service import learning_service
        from app.database import get_ai_session  # AI feedback in AI database

        async with get_ai_session() as db:
            # Get the feedback record
            result = await db.execute(
                select(AIFeedback).where(AIFeedback.id == feedback_id)
            )
            feedback = result.scalar_one_or_none()

            if feedback:
                learning_result = await learning_service.process_feedback(feedback)
                logger.info(
                    f"[Feedback-Learning] Processed feedback {feedback_id}: "
                    f"actions={learning_result.get('actions_taken', [])}"
                )
            else:
                logger.warning(f"[Feedback-Learning] Feedback {feedback_id} not found")

    except Exception as e:
        logger.error(f"[Feedback-Learning] Background learning failed for {feedback_id}: {e}")

router = APIRouter()


class FeedbackCreate(BaseModel):
    """Schema for creating feedback on a message."""
    rating: str = Field(..., description="Rating: 'up' or 'down'", pattern="^(up|down)$")
    edited_text: Optional[str] = Field(None, description="Optional corrected response text")
    comment: Optional[str] = Field(None, description="Optional comment explaining the rating")


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""
    id: UUID
    message_id: UUID
    rating: str
    edited_text: Optional[str] = None
    comment: Optional[str] = None


@router.post("/messages/{message_id}/feedback", response_model=FeedbackResponse)
async def create_message_feedback(
    message_id: UUID,
    feedback: FeedbackCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> FeedbackResponse:
    """
    Submit feedback (rating) on an AI-generated message.

    Args:
        message_id: The UUID of the message to rate
        feedback: Feedback data (rating, optional edited_text, optional comment)
        db: Database session
        current_user: Authenticated user

    Returns:
        The created feedback record

    Raises:
        404: Message not found
        403: Not authorized (message belongs to different user)
        400: Message is not from assistant (can only rate AI responses)
    """
    # Find the message
    result = await db.execute(
        select(ConversationMessage).where(ConversationMessage.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    # Verify user owns the conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == message.conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to provide feedback on this message"
        )

    # Only allow feedback on assistant messages
    if message.role != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback can only be provided on assistant messages"
        )

    # Check if feedback already exists for this message
    result = await db.execute(
        select(AIFeedback).where(AIFeedback.message_id == message_id)
    )
    existing_feedback = result.scalar_one_or_none()

    if existing_feedback:
        # Update existing feedback
        existing_feedback.rating = feedback.rating
        existing_feedback.edited_text = feedback.edited_text
        existing_feedback.comment = feedback.comment
        await db.commit()
        await db.refresh(existing_feedback)

        logger.info(
            f"Updated feedback for message {message_id}: rating={feedback.rating}"
        )

        # Trigger background learning process
        asyncio.create_task(_run_learning_background(existing_feedback.id))

        return FeedbackResponse(
            id=existing_feedback.id,
            message_id=existing_feedback.message_id,
            rating=existing_feedback.rating,
            edited_text=existing_feedback.edited_text,
            comment=existing_feedback.comment,
        )

    # Create new feedback
    new_feedback = AIFeedback(
        message_id=message_id,
        rating=feedback.rating,
        edited_text=feedback.edited_text,
        comment=feedback.comment,
    )
    db.add(new_feedback)
    await db.commit()
    await db.refresh(new_feedback)

    logger.info(
        f"Created feedback for message {message_id}: rating={feedback.rating}"
    )

    # Trigger background learning process
    asyncio.create_task(_run_learning_background(new_feedback.id))

    return FeedbackResponse(
        id=new_feedback.id,
        message_id=new_feedback.message_id,
        rating=new_feedback.rating,
        edited_text=new_feedback.edited_text,
        comment=new_feedback.comment,
    )


@router.get("/messages/{message_id}/feedback", response_model=Optional[FeedbackResponse])
async def get_message_feedback(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Optional[FeedbackResponse]:
    """
    Get feedback for a specific message (if any).

    Args:
        message_id: The UUID of the message
        db: Database session
        current_user: Authenticated user

    Returns:
        The feedback record if it exists, None otherwise

    Raises:
        404: Message not found
        403: Not authorized
    """
    # Find the message
    result = await db.execute(
        select(ConversationMessage).where(ConversationMessage.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    # Verify user owns the conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == message.conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view feedback for this message"
        )

    # Get feedback
    result = await db.execute(
        select(AIFeedback).where(AIFeedback.message_id == message_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        return None

    return FeedbackResponse(
        id=feedback.id,
        message_id=feedback.message_id,
        rating=feedback.rating,
        edited_text=feedback.edited_text,
        comment=feedback.comment,
    )


@router.delete("/messages/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message_feedback(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Delete feedback for a specific message.

    Args:
        message_id: The UUID of the message
        db: Database session
        current_user: Authenticated user

    Raises:
        404: Message or feedback not found
        403: Not authorized
    """
    # Find the message
    result = await db.execute(
        select(ConversationMessage).where(ConversationMessage.id == message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    # Verify user owns the conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == message.conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    if conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete feedback for this message"
        )

    # Find and delete feedback
    result = await db.execute(
        select(AIFeedback).where(AIFeedback.message_id == message_id)
    )
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found for this message"
        )

    await db.delete(feedback)
    await db.commit()

    logger.info(f"Deleted feedback for message {message_id}")
