"""
Conversation management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import uuid4, UUID
from typing import List, Optional

from app.database import get_db
from app.core.dependencies import get_current_user, CurrentUser
from app.agent.models.conversations import Conversation, ConversationMessage
from app.models.users import User, Portfolio
from app.agent.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    ModeChangeRequest,
    ModeChangeResponse
)
from app.core.datetime_utils import utc_now
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
) -> ConversationResponse:
    """
    Create a new conversation for the current user.
    
    Args:
        request: ConversationCreate schema with mode selection
        db: Database session
        current_user: Authenticated user
        
    Returns:
        ConversationResponse with conversation_id and metadata
    """
    try:
        # Resolve portfolio ID - use provided or auto-resolve user's portfolio
        portfolio_id = None
        if request.portfolio_id:
            # Use explicitly provided portfolio ID
            portfolio_id = request.portfolio_id
            logger.info(f"Using explicit portfolio {portfolio_id} for user {current_user.id}")
        else:
            # Auto-resolve user's portfolio ID
            result = await db.execute(
                select(Portfolio.id)
                .where(Portfolio.user_id == current_user.id)
            )
            portfolio = result.scalar_one_or_none()
            if portfolio:
                portfolio_id = str(portfolio)
                logger.info(f"Auto-resolved portfolio {portfolio_id} for user {current_user.id}")
            else:
                # No portfolio found - this should not happen for authenticated users
                logger.error(f"No portfolio found for authenticated user {current_user.id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No portfolio found for user"
                )
        
        # Create metadata with portfolio context (always populated)
        meta_data = {
            "portfolio_id": portfolio_id
        }
            
        conversation = Conversation(
            id=uuid4(),  # Our canonical ID
            user_id=current_user.id,
            mode=request.mode,
            provider="openai",
            created_at=utc_now(),
            updated_at=utc_now(),
            meta_data=meta_data  # Store portfolio_id and other metadata
        )
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        # 🔍 TRACE-1 Conversation Created (Phase 9.12.1 investigation)
        logger.info(f"🔍 TRACE-1 Conversation Created: {conversation.id} | meta_data: {conversation.meta_data}")
        logger.info(f"Created conversation {conversation.id} for user {current_user.id}")
        
        return ConversationResponse(
            id=conversation.id,
            mode=conversation.mode,
            created_at=conversation.created_at,
            provider=conversation.provider,
            provider_thread_id=conversation.provider_thread_id
        )
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
) -> ConversationResponse:
    """
    Get a specific conversation by ID.
    
    Args:
        conversation_id: Conversation UUID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        ConversationResponse with conversation details
    """
    try:
        result = await db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return ConversationResponse(
            id=conversation.id,
            mode=conversation.mode,
            created_at=conversation.created_at,
            provider=conversation.provider,
            provider_thread_id=conversation.provider_thread_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get conversation"
        )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
) -> List[ConversationResponse]:
    """
    List conversations for the current user.
    
    Args:
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of ConversationResponse objects
    """
    try:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == current_user.id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        conversations = result.scalars().all()
        
        return [
            ConversationResponse(
                id=conv.id,
                mode=conv.mode,
                created_at=conv.created_at,
                provider=conv.provider,
                provider_thread_id=conv.provider_thread_id
            )
            for conv in conversations
        ]
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list conversations"
        )


@router.put("/conversations/{conversation_id}/mode", response_model=ModeChangeResponse)
async def change_conversation_mode(
    conversation_id: UUID,
    request: ModeChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
) -> ModeChangeResponse:
    """
    Change the mode of an existing conversation.
    
    Args:
        conversation_id: Conversation UUID
        request: ModeChangeRequest with new mode
        db: Database session
        current_user: Authenticated user
        
    Returns:
        ModeChangeResponse with mode change details
    """
    try:
        result = await db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        previous_mode = conversation.mode
        conversation.mode = request.mode
        conversation.updated_at = utc_now()
        
        await db.commit()
        
        logger.info(f"Changed mode for conversation {conversation_id} from {previous_mode} to {request.mode}")
        
        return ModeChangeResponse(
            id=conversation.id,
            previous_mode=previous_mode,
            new_mode=request.mode,
            changed_at=conversation.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing conversation mode: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change conversation mode"
        )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user)
) -> None:
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: Conversation UUID
        db: Database session
        current_user: Authenticated user
    """
    try:
        result = await db.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == current_user.id
                )
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Delete conversation (messages will cascade delete)
        await db.delete(conversation)
        await db.commit()
        
        logger.info(f"Deleted conversation {conversation_id} for user {current_user.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )