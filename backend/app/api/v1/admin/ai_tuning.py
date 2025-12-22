"""
Admin API endpoints for AI Tuning.

Provides admin access to:
- Browse AI conversations and messages (Core DB)
- Create and manage admin annotations (AI DB)
- Export annotations for training data

Implements dual-database pattern:
- Reads from Core DB (conversations, messages)
- Writes to AI DB (annotations)

Created: December 22, 2025 (Phase 2 Admin Dashboard)
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel, Field

from app.core.admin_dependencies import get_current_admin, require_super_admin, CurrentAdmin
from app.core.logging import get_logger
from app.database import get_db, get_ai_db
from app.models.ai_models import AIAdminAnnotation
from app.agent.models.conversations import Conversation, ConversationMessage

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/ai/tuning", tags=["Admin - AI Tuning"])


# ========== Enums ==========

class AnnotationType(str, Enum):
    CORRECTION = "correction"
    IMPROVEMENT = "improvement"
    FLAG = "flag"
    APPROVED = "approved"


class SeverityLevel(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"


class AnnotationStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    APPLIED = "applied"


# ========== Request/Response Models ==========

class AnnotationCreate(BaseModel):
    """Request model for creating an annotation."""
    message_id: str = Field(..., description="ID of the message to annotate")
    annotation_type: AnnotationType = Field(..., description="Type of annotation")
    content: str = Field(..., min_length=1, max_length=5000, description="Admin's comment")
    suggested_response: Optional[str] = Field(None, max_length=10000, description="What AI should have said")
    severity: Optional[SeverityLevel] = Field(None, description="Severity level")
    tags: List[str] = Field(default=[], description="Categorization tags")


class AnnotationUpdate(BaseModel):
    """Request model for updating an annotation."""
    annotation_type: Optional[AnnotationType] = None
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    suggested_response: Optional[str] = Field(None, max_length=10000)
    severity: Optional[SeverityLevel] = None
    tags: Optional[List[str]] = None
    status: Optional[AnnotationStatus] = None


class AnnotationResponse(BaseModel):
    """Response model for an annotation."""
    id: str
    message_id: str
    admin_user_id: str
    admin_email: Optional[str] = None
    annotation_type: str
    content: str
    suggested_response: Optional[str]
    severity: Optional[str]
    tags: List[str]
    status: str
    created_at: str
    updated_at: str


class ConversationSummary(BaseModel):
    """Summary of a conversation for listing."""
    id: str
    user_id: str
    user_email: Optional[str] = None
    title: Optional[str]
    message_count: int
    created_at: str
    updated_at: str


class MessageDetail(BaseModel):
    """Detailed message with context."""
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    annotations_count: int = 0


# ========== Conversation Browsing Endpoints (Core DB) ==========

@router.get("/conversations")
async def list_conversations(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    core_db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    days: int = Query(30, ge=1, le=365, description="Look-back period in days"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    List all AI conversations for admin review.

    Returns conversations sorted by most recent activity.
    Use this to find conversations that may need annotation.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Build query
    query = select(Conversation).where(Conversation.created_at >= cutoff)

    if user_id:
        try:
            user_uuid = UUID(user_id)
            query = query.where(Conversation.user_id == user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")

    # Get total count
    count_query = select(func.count(Conversation.id)).where(Conversation.created_at >= cutoff)
    if user_id:
        count_query = count_query.where(Conversation.user_id == UUID(user_id))
    count_result = await core_db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit)
    result = await core_db.execute(query)
    conversations = result.scalars().all()

    # Get message counts for each conversation
    items = []
    for conv in conversations:
        msg_count_result = await core_db.execute(
            select(func.count(ConversationMessage.id)).where(
                ConversationMessage.conversation_id == conv.id
            )
        )
        msg_count = msg_count_result.scalar() or 0

        items.append({
            "id": str(conv.id),
            "user_id": str(conv.user_id),
            "title": conv.title if hasattr(conv, 'title') else None,
            "message_count": msg_count,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "period_days": days,
        "conversations": items
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    core_db: AsyncSession = Depends(get_db),
    ai_db: AsyncSession = Depends(get_ai_db)
) -> Dict[str, Any]:
    """
    Get a conversation with all its messages.

    Includes annotation counts for each message.
    """
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    # Get conversation
    conv_result = await core_db.execute(
        select(Conversation).where(Conversation.id == conv_uuid)
    )
    conv = conv_result.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    msg_result = await core_db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conv_uuid)
        .order_by(ConversationMessage.created_at)
    )
    messages = msg_result.scalars().all()

    # Get annotation counts per message from AI DB
    message_ids = [msg.id for msg in messages]
    annotation_counts = {}

    if message_ids:
        for msg_id in message_ids:
            count_result = await ai_db.execute(
                select(func.count(AIAdminAnnotation.id)).where(
                    AIAdminAnnotation.message_id == msg_id
                )
            )
            annotation_counts[str(msg_id)] = count_result.scalar() or 0

    return {
        "id": str(conv.id),
        "user_id": str(conv.user_id),
        "title": conv.title if hasattr(conv, 'title') else None,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "annotations_count": annotation_counts.get(str(msg.id), 0)
            }
            for msg in messages
        ]
    }


@router.get("/messages/{message_id}")
async def get_message_with_context(
    message_id: str,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    core_db: AsyncSession = Depends(get_db),
    ai_db: AsyncSession = Depends(get_ai_db),
    context_messages: int = Query(5, ge=0, le=20, description="Number of context messages before/after")
) -> Dict[str, Any]:
    """
    Get a single message with surrounding context.

    Includes any existing annotations on this message.
    """
    try:
        msg_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")

    # Get the message
    msg_result = await core_db.execute(
        select(ConversationMessage).where(ConversationMessage.id == msg_uuid)
    )
    message = msg_result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Get conversation messages for context
    context_result = await core_db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == message.conversation_id)
        .order_by(ConversationMessage.created_at)
    )
    all_messages = context_result.scalars().all()

    # Find message index and extract context
    msg_index = next((i for i, m in enumerate(all_messages) if m.id == msg_uuid), -1)
    start_idx = max(0, msg_index - context_messages)
    end_idx = min(len(all_messages), msg_index + context_messages + 1)
    context = all_messages[start_idx:end_idx]

    # Get annotations for this message from AI DB
    annotations_result = await ai_db.execute(
        select(AIAdminAnnotation)
        .where(AIAdminAnnotation.message_id == msg_uuid)
        .order_by(desc(AIAdminAnnotation.created_at))
    )
    annotations = annotations_result.scalars().all()

    return {
        "message": {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat() if message.created_at else None
        },
        "context": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "is_target": m.id == msg_uuid,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in context
        ],
        "annotations": [
            {
                "id": str(ann.id),
                "admin_user_id": str(ann.admin_user_id),
                "annotation_type": ann.annotation_type,
                "content": ann.content,
                "suggested_response": ann.suggested_response,
                "severity": ann.severity,
                "tags": ann.tags or [],
                "status": ann.status,
                "created_at": ann.created_at.isoformat() if ann.created_at else None
            }
            for ann in annotations
        ]
    }


# ========== Annotation CRUD Endpoints (AI DB) ==========

@router.post("/annotations")
async def create_annotation(
    annotation: AnnotationCreate,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    core_db: AsyncSession = Depends(get_db),
    ai_db: AsyncSession = Depends(get_ai_db)
) -> Dict[str, Any]:
    """
    Create an annotation on an AI message.

    Admins use this to flag issues, suggest corrections, or approve responses.
    """
    try:
        message_uuid = UUID(annotation.message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")

    # Verify message exists in Core DB
    msg_result = await core_db.execute(
        select(ConversationMessage).where(ConversationMessage.id == message_uuid)
    )
    message = msg_result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Only allow annotating assistant messages
    if message.role != "assistant":
        raise HTTPException(
            status_code=400,
            detail="Can only annotate assistant messages"
        )

    # Create annotation in AI DB
    new_annotation = AIAdminAnnotation(
        message_id=message_uuid,
        admin_user_id=admin_user.id,  # Already a UUID from CurrentAdmin
        annotation_type=annotation.annotation_type.value,
        content=annotation.content,
        suggested_response=annotation.suggested_response,
        severity=annotation.severity.value if annotation.severity else None,
        tags=annotation.tags,
        status="pending"
    )

    ai_db.add(new_annotation)
    await ai_db.commit()
    await ai_db.refresh(new_annotation)

    logger.info(
        f"Admin {admin_user.email} created annotation {new_annotation.id} "
        f"on message {message_uuid}"
    )

    return {
        "id": str(new_annotation.id),
        "message_id": str(new_annotation.message_id),
        "admin_user_id": str(new_annotation.admin_user_id),
        "annotation_type": new_annotation.annotation_type,
        "content": new_annotation.content,
        "suggested_response": new_annotation.suggested_response,
        "severity": new_annotation.severity,
        "tags": new_annotation.tags or [],
        "status": new_annotation.status,
        "created_at": new_annotation.created_at.isoformat() if new_annotation.created_at else None
    }


@router.get("/annotations")
async def list_annotations(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db),
    status: Optional[AnnotationStatus] = Query(None, description="Filter by status"),
    annotation_type: Optional[AnnotationType] = Query(None, description="Filter by type"),
    severity: Optional[SeverityLevel] = Query(None, description="Filter by severity"),
    days: int = Query(30, ge=1, le=365, description="Look-back period"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    List admin annotations with filtering.

    Use to review pending annotations or find patterns.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Build query with filters
    query = select(AIAdminAnnotation).where(AIAdminAnnotation.created_at >= cutoff)

    if status:
        query = query.where(AIAdminAnnotation.status == status.value)
    if annotation_type:
        query = query.where(AIAdminAnnotation.annotation_type == annotation_type.value)
    if severity:
        query = query.where(AIAdminAnnotation.severity == severity.value)

    # Get total count
    count_query = select(func.count(AIAdminAnnotation.id)).where(
        AIAdminAnnotation.created_at >= cutoff
    )
    if status:
        count_query = count_query.where(AIAdminAnnotation.status == status.value)
    if annotation_type:
        count_query = count_query.where(AIAdminAnnotation.annotation_type == annotation_type.value)
    if severity:
        count_query = count_query.where(AIAdminAnnotation.severity == severity.value)

    count_result = await ai_db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(AIAdminAnnotation.created_at)).offset(offset).limit(limit)
    result = await ai_db.execute(query)
    annotations = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "period_days": days,
        "annotations": [
            {
                "id": str(ann.id),
                "message_id": str(ann.message_id),
                "admin_user_id": str(ann.admin_user_id),
                "annotation_type": ann.annotation_type,
                "content": ann.content,
                "suggested_response": ann.suggested_response,
                "severity": ann.severity,
                "tags": ann.tags or [],
                "status": ann.status,
                "created_at": ann.created_at.isoformat() if ann.created_at else None,
                "updated_at": ann.updated_at.isoformat() if ann.updated_at else None
            }
            for ann in annotations
        ]
    }


@router.get("/annotations/{annotation_id}")
async def get_annotation(
    annotation_id: str,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db)
) -> Dict[str, Any]:
    """Get a specific annotation."""
    try:
        ann_uuid = UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid annotation ID format")

    result = await ai_db.execute(
        select(AIAdminAnnotation).where(AIAdminAnnotation.id == ann_uuid)
    )
    annotation = result.scalar_one_or_none()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    return {
        "id": str(annotation.id),
        "message_id": str(annotation.message_id),
        "admin_user_id": str(annotation.admin_user_id),
        "annotation_type": annotation.annotation_type,
        "content": annotation.content,
        "suggested_response": annotation.suggested_response,
        "severity": annotation.severity,
        "tags": annotation.tags or [],
        "status": annotation.status,
        "created_at": annotation.created_at.isoformat() if annotation.created_at else None,
        "updated_at": annotation.updated_at.isoformat() if annotation.updated_at else None
    }


@router.put("/annotations/{annotation_id}")
async def update_annotation(
    annotation_id: str,
    update: AnnotationUpdate,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db)
) -> Dict[str, Any]:
    """Update an annotation."""
    try:
        ann_uuid = UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid annotation ID format")

    result = await ai_db.execute(
        select(AIAdminAnnotation).where(AIAdminAnnotation.id == ann_uuid)
    )
    annotation = result.scalar_one_or_none()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Update fields
    if update.annotation_type is not None:
        annotation.annotation_type = update.annotation_type.value
    if update.content is not None:
        annotation.content = update.content
    if update.suggested_response is not None:
        annotation.suggested_response = update.suggested_response
    if update.severity is not None:
        annotation.severity = update.severity.value
    if update.tags is not None:
        annotation.tags = update.tags
    if update.status is not None:
        annotation.status = update.status.value

    await ai_db.commit()
    await ai_db.refresh(annotation)

    logger.info(f"Admin {admin_user.email} updated annotation {annotation_id}")

    return {
        "id": str(annotation.id),
        "message_id": str(annotation.message_id),
        "admin_user_id": str(annotation.admin_user_id),
        "annotation_type": annotation.annotation_type,
        "content": annotation.content,
        "suggested_response": annotation.suggested_response,
        "severity": annotation.severity,
        "tags": annotation.tags or [],
        "status": annotation.status,
        "created_at": annotation.created_at.isoformat() if annotation.created_at else None,
        "updated_at": annotation.updated_at.isoformat() if annotation.updated_at else None
    }


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db)
) -> Dict[str, str]:
    """Delete an annotation."""
    try:
        ann_uuid = UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid annotation ID format")

    result = await ai_db.execute(
        select(AIAdminAnnotation).where(AIAdminAnnotation.id == ann_uuid)
    )
    annotation = result.scalar_one_or_none()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    await ai_db.delete(annotation)
    await ai_db.commit()

    logger.info(f"Admin {admin_user.email} deleted annotation {annotation_id}")

    return {"message": "Annotation deleted successfully"}


# ========== Analytics & Export Endpoints ==========

@router.get("/summary")
async def get_tuning_summary(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db),
    days: int = Query(30, ge=1, le=365, description="Look-back period")
) -> Dict[str, Any]:
    """
    Get summary statistics for AI tuning annotations.

    Shows breakdown by type, severity, and status.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Total count
    total_result = await ai_db.execute(
        select(func.count(AIAdminAnnotation.id)).where(
            AIAdminAnnotation.created_at >= cutoff
        )
    )
    total = total_result.scalar() or 0

    # By type
    type_query = select(
        AIAdminAnnotation.annotation_type,
        func.count(AIAdminAnnotation.id).label('count')
    ).where(AIAdminAnnotation.created_at >= cutoff).group_by(AIAdminAnnotation.annotation_type)
    type_result = await ai_db.execute(type_query)
    by_type = {row[0]: row[1] for row in type_result.fetchall()}

    # By severity
    severity_query = select(
        AIAdminAnnotation.severity,
        func.count(AIAdminAnnotation.id).label('count')
    ).where(
        AIAdminAnnotation.created_at >= cutoff,
        AIAdminAnnotation.severity.isnot(None)
    ).group_by(AIAdminAnnotation.severity)
    severity_result = await ai_db.execute(severity_query)
    by_severity = {row[0]: row[1] for row in severity_result.fetchall()}

    # By status
    status_query = select(
        AIAdminAnnotation.status,
        func.count(AIAdminAnnotation.id).label('count')
    ).where(AIAdminAnnotation.created_at >= cutoff).group_by(AIAdminAnnotation.status)
    status_result = await ai_db.execute(status_query)
    by_status = {row[0]: row[1] for row in status_result.fetchall()}

    # Count with suggested responses
    suggested_result = await ai_db.execute(
        select(func.count(AIAdminAnnotation.id)).where(
            AIAdminAnnotation.created_at >= cutoff,
            AIAdminAnnotation.suggested_response.isnot(None)
        )
    )
    with_suggestions = suggested_result.scalar() or 0

    return {
        "period_days": days,
        "total_annotations": total,
        "by_type": by_type,
        "by_severity": by_severity,
        "by_status": by_status,
        "with_suggestions": with_suggestions,
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/export")
async def export_annotations(
    admin_user: CurrentAdmin = Depends(require_super_admin),
    core_db: AsyncSession = Depends(get_db),
    ai_db: AsyncSession = Depends(get_ai_db),
    status: Optional[AnnotationStatus] = Query(None, description="Filter by status"),
    annotation_type: Optional[AnnotationType] = Query(None, description="Filter by type"),
    days: int = Query(90, ge=1, le=365, description="Look-back period"),
    format: str = Query("json", description="Export format: json or jsonl")
) -> Dict[str, Any]:
    """
    Export annotations for training data.

    Returns annotations with original message content.
    Requires super_admin role.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Build query
    query = select(AIAdminAnnotation).where(AIAdminAnnotation.created_at >= cutoff)

    if status:
        query = query.where(AIAdminAnnotation.status == status.value)
    if annotation_type:
        query = query.where(AIAdminAnnotation.annotation_type == annotation_type.value)

    query = query.order_by(AIAdminAnnotation.created_at)

    result = await ai_db.execute(query)
    annotations = result.scalars().all()

    # Fetch message content for each annotation
    export_data = []
    for ann in annotations:
        # Get original message from Core DB
        msg_result = await core_db.execute(
            select(ConversationMessage).where(ConversationMessage.id == ann.message_id)
        )
        message = msg_result.scalar_one_or_none()

        export_item = {
            "annotation_id": str(ann.id),
            "annotation_type": ann.annotation_type,
            "severity": ann.severity,
            "admin_comment": ann.content,
            "suggested_response": ann.suggested_response,
            "tags": ann.tags or [],
            "status": ann.status,
            "created_at": ann.created_at.isoformat() if ann.created_at else None,
            "original_message": {
                "id": str(message.id) if message else None,
                "role": message.role if message else None,
                "content": message.content if message else None
            } if message else None
        }

        export_data.append(export_item)

    return {
        "export_format": format,
        "period_days": days,
        "total_records": len(export_data),
        "filters": {
            "status": status.value if status else None,
            "annotation_type": annotation_type.value if annotation_type else None
        },
        "exported_at": datetime.utcnow().isoformat(),
        "data": export_data
    }
