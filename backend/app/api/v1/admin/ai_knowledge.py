"""
Admin API endpoints for AI Knowledge Base management.

Provides admin access to:
- View RAG knowledge base documents (ai_kb_documents)
- View AI memories across all users (ai_memories)
- View all AI feedback (ai_feedback)

All data comes from the AI Database (metro on Railway).

Created: December 22, 2025
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel

from app.core.admin_dependencies import get_current_admin, require_super_admin, CurrentAdmin
from app.core.logging import get_logger
from app.database import get_db, get_ai_db
from app.models.ai_models import AIKBDocument, AIMemory, AIFeedback
from app.agent.models.conversations import Conversation, ConversationMessage

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/ai/knowledge", tags=["Admin - AI Knowledge Base"])


# ========== Response Models ==========

class KBDocumentResponse(BaseModel):
    """Knowledge base document response."""
    id: str
    scope: str
    title: str
    content: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class AIMemoryResponse(BaseModel):
    """AI memory response."""
    id: str
    user_id: Optional[str]
    tenant_id: Optional[str]
    scope: str
    content: str
    tags: Dict[str, Any]
    created_at: str


class AIFeedbackResponse(BaseModel):
    """AI feedback response."""
    id: str
    message_id: str
    rating: str
    edited_text: Optional[str]
    comment: Optional[str]
    created_at: str
    # Additional context from Core DB
    original_message: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


# ========== Knowledge Base Endpoints ==========

@router.get("/documents")
async def list_kb_documents(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db),
    scope: Optional[str] = Query(None, description="Filter by scope (e.g., 'global', 'page:portfolio')"),
    search: Optional[str] = Query(None, description="Search in title/content"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    List all knowledge base documents.

    Returns RAG documents used for retrieval-augmented generation.
    These are injected into the AI context based on user queries.
    """
    query = select(AIKBDocument)

    if scope:
        query = query.where(AIKBDocument.scope == scope)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (AIKBDocument.title.ilike(search_pattern)) |
            (AIKBDocument.content.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count(AIKBDocument.id))
    if scope:
        count_query = count_query.where(AIKBDocument.scope == scope)
    count_result = await ai_db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(AIKBDocument.updated_at)).offset(offset).limit(limit)
    result = await ai_db.execute(query)
    documents = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "documents": [
            {
                "id": str(doc.id),
                "scope": doc.scope,
                "title": doc.title,
                "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                "content_length": len(doc.content),
                "metadata": doc.doc_metadata or {},
                "has_embedding": hasattr(doc, 'embedding') and doc.embedding is not None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
            }
            for doc in documents
        ]
    }


@router.get("/documents/{doc_id}")
async def get_kb_document(
    doc_id: str,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db)
) -> Dict[str, Any]:
    """
    Get a specific knowledge base document with full content.
    """
    try:
        doc_uuid = UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    result = await ai_db.execute(
        select(AIKBDocument).where(AIKBDocument.id == doc_uuid)
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(doc.id),
        "scope": doc.scope,
        "title": doc.title,
        "content": doc.content,
        "metadata": doc.doc_metadata or {},
        "has_embedding": hasattr(doc, 'embedding') and doc.embedding is not None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
    }


@router.get("/documents/stats")
async def get_kb_stats(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db)
) -> Dict[str, Any]:
    """
    Get knowledge base statistics.
    """
    # Total count
    total_result = await ai_db.execute(select(func.count(AIKBDocument.id)))
    total = total_result.scalar() or 0

    # Count by scope
    scope_query = select(
        AIKBDocument.scope,
        func.count(AIKBDocument.id).label('count')
    ).group_by(AIKBDocument.scope)
    scope_result = await ai_db.execute(scope_query)
    scopes = {row[0]: row[1] for row in scope_result.fetchall()}

    return {
        "total_documents": total,
        "by_scope": scopes,
        "generated_at": datetime.utcnow().isoformat()
    }


# ========== AI Memories Endpoints ==========

@router.get("/memories")
async def list_ai_memories(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db),
    scope: Optional[str] = Query(None, description="Filter by scope (user, tenant, global)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    search: Optional[str] = Query(None, description="Search in content"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    List all AI memories (learned preferences and rules).

    Returns user preferences, tenant policies, and global rules
    that are injected into the AI system prompt.
    """
    query = select(AIMemory)

    if scope:
        query = query.where(AIMemory.scope == scope)

    if user_id:
        try:
            user_uuid = UUID(user_id)
            query = query.where(AIMemory.user_id == user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")

    if search:
        query = query.where(AIMemory.content.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count(AIMemory.id))
    if scope:
        count_query = count_query.where(AIMemory.scope == scope)
    if user_id:
        count_query = count_query.where(AIMemory.user_id == UUID(user_id))
    count_result = await ai_db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(AIMemory.created_at)).offset(offset).limit(limit)
    result = await ai_db.execute(query)
    memories = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "memories": [
            {
                "id": str(m.id),
                "user_id": str(m.user_id) if m.user_id else None,
                "tenant_id": str(m.tenant_id) if m.tenant_id else None,
                "scope": m.scope,
                "content": m.content,
                "tags": m.tags or {},
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in memories
        ]
    }


@router.get("/memories/stats")
async def get_memories_stats(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db)
) -> Dict[str, Any]:
    """
    Get AI memories statistics.
    """
    # Total count
    total_result = await ai_db.execute(select(func.count(AIMemory.id)))
    total = total_result.scalar() or 0

    # Count by scope
    scope_query = select(
        AIMemory.scope,
        func.count(AIMemory.id).label('count')
    ).group_by(AIMemory.scope)
    scope_result = await ai_db.execute(scope_query)
    scopes = {row[0]: row[1] for row in scope_result.fetchall()}

    # Count unique users with memories
    users_query = select(func.count(func.distinct(AIMemory.user_id))).where(AIMemory.user_id.isnot(None))
    users_result = await ai_db.execute(users_query)
    unique_users = users_result.scalar() or 0

    return {
        "total_memories": total,
        "by_scope": scopes,
        "unique_users_with_memories": unique_users,
        "generated_at": datetime.utcnow().isoformat()
    }


# ========== AI Feedback Endpoints ==========

@router.get("/feedback")
async def list_ai_feedback(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    core_db: AsyncSession = Depends(get_db),
    ai_db: AsyncSession = Depends(get_ai_db),
    rating: Optional[str] = Query(None, description="Filter by rating (up, down)"),
    days: int = Query(30, ge=1, le=365, description="Look-back period in days"),
    with_context: bool = Query(False, description="Include original message context"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    List all AI feedback.

    Returns user ratings and corrections on AI responses.
    Optionally includes the original message context from Core DB.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = select(AIFeedback).where(AIFeedback.created_at >= cutoff)

    if rating:
        query = query.where(AIFeedback.rating == rating)

    # Get total count
    count_query = select(func.count(AIFeedback.id)).where(AIFeedback.created_at >= cutoff)
    if rating:
        count_query = count_query.where(AIFeedback.rating == rating)
    count_result = await ai_db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(AIFeedback.created_at)).offset(offset).limit(limit)
    result = await ai_db.execute(query)
    feedbacks = result.scalars().all()

    items = []
    for fb in feedbacks:
        item = {
            "id": str(fb.id),
            "message_id": str(fb.message_id),
            "rating": fb.rating,
            "edited_text": fb.edited_text,
            "comment": fb.comment,
            "created_at": fb.created_at.isoformat() if fb.created_at else None
        }

        # Optionally fetch context from Core DB
        if with_context:
            msg_result = await core_db.execute(
                select(ConversationMessage).where(ConversationMessage.id == fb.message_id)
            )
            message = msg_result.scalar_one_or_none()

            if message:
                item["original_message"] = message.content
                item["conversation_id"] = str(message.conversation_id)

                # Get user from conversation
                conv_result = await core_db.execute(
                    select(Conversation).where(Conversation.id == message.conversation_id)
                )
                conv = conv_result.scalar_one_or_none()
                if conv:
                    item["user_id"] = str(conv.user_id)

        items.append(item)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "period_days": days,
        "feedback": items
    }


@router.get("/feedback/stats")
async def get_feedback_stats(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db),
    days: int = Query(30, ge=1, le=365, description="Look-back period in days")
) -> Dict[str, Any]:
    """
    Get AI feedback statistics.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Total count
    total_result = await ai_db.execute(
        select(func.count(AIFeedback.id)).where(AIFeedback.created_at >= cutoff)
    )
    total = total_result.scalar() or 0

    # Count by rating
    rating_query = select(
        AIFeedback.rating,
        func.count(AIFeedback.id).label('count')
    ).where(AIFeedback.created_at >= cutoff).group_by(AIFeedback.rating)
    rating_result = await ai_db.execute(rating_query)
    ratings = {row[0]: row[1] for row in rating_result.fetchall()}

    # Count with edits
    edits_result = await ai_db.execute(
        select(func.count(AIFeedback.id)).where(
            AIFeedback.created_at >= cutoff,
            AIFeedback.edited_text.isnot(None)
        )
    )
    with_edits = edits_result.scalar() or 0

    # Count with comments
    comments_result = await ai_db.execute(
        select(func.count(AIFeedback.id)).where(
            AIFeedback.created_at >= cutoff,
            AIFeedback.comment.isnot(None)
        )
    )
    with_comments = comments_result.scalar() or 0

    positive = ratings.get('up', 0)
    negative = ratings.get('down', 0)
    positive_ratio = positive / total if total > 0 else 0

    return {
        "period_days": days,
        "total_feedback": total,
        "positive": positive,
        "negative": negative,
        "positive_ratio": round(positive_ratio, 3),
        "with_edits": with_edits,
        "with_comments": with_comments,
        "generated_at": datetime.utcnow().isoformat()
    }
