"""
Admin API endpoints for feedback analysis and learning management.

Phase 3.5 of PRD4 - Provides admin visibility into:
- Feedback statistics and trends
- Detected patterns and learning rules
- Negative feedback review queue
- Manual learning job triggers

Created: December 18, 2025
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.dependencies import get_db
from app.core.admin_dependencies import get_current_admin, CurrentAdmin
from app.core.logging import get_logger
from app.database import get_db as get_core_db, get_ai_db
from app.models.ai_models import AIFeedback, AIMemory
from app.agent.models.conversations import Conversation, ConversationMessage
from app.agent.services.feedback_analyzer import feedback_analyzer
from app.agent.services.learning_service import learning_service
from app.batch.feedback_learning_job import (
    run_feedback_learning_batch,
    reprocess_unlearned_feedback,
    get_feedback_learning_stats
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/feedback", tags=["Admin - Feedback Learning"])


# Response Models
class FeedbackSummaryResponse(BaseModel):
    """Summary statistics for feedback."""
    total_feedback: int
    positive: int
    negative: int
    positive_ratio: float
    with_edits: int
    with_comments: int
    period_days: int
    generated_at: str


class PatternResponse(BaseModel):
    """A detected learning pattern."""
    type: str
    content: str
    confidence: float
    source: str
    category: str
    evidence_count: int


class NegativeFeedbackItem(BaseModel):
    """A negative feedback item for review."""
    feedback_id: str
    message_id: str
    user_id: Optional[str]
    rating: str
    original_text: Optional[str]
    edited_text: Optional[str]
    comment: Optional[str]
    created_at: str


class LearnedPreferenceResponse(BaseModel):
    """A learned user preference."""
    memory_id: str
    user_id: str
    content: str
    category: Optional[str]
    source: Optional[str]
    confidence: Optional[float]
    created_at: str


class LearningJobResponse(BaseModel):
    """Response from a learning job trigger."""
    job_type: str
    status: str
    users_processed: Optional[int] = None
    total_patterns_found: Optional[int] = None
    total_rules_created: Optional[int] = None
    duration_seconds: Optional[float] = None
    message: Optional[str] = None


@router.get("/summary", response_model=FeedbackSummaryResponse)
async def get_feedback_summary(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    days: int = Query(30, ge=1, le=365, description="Look-back period in days"),
    user_id: Optional[str] = Query(None, description="Filter by specific user ID")
) -> FeedbackSummaryResponse:
    """
    Get aggregate feedback statistics.

    Returns summary of feedback volume, positive/negative ratio, and edit counts.
    Can be filtered by user or time period.
    """
    user_uuid = UUID(user_id) if user_id else None

    summary = await feedback_analyzer.get_feedback_summary(
        user_id=user_uuid,
        days=days
    )

    return FeedbackSummaryResponse(**summary)


@router.get("/patterns")
async def get_detected_patterns(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    user_id: str = Query(..., description="User ID to analyze"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold")
) -> Dict[str, Any]:
    """
    Get detected learning patterns for a specific user.

    Analyzes the user's feedback history and returns detected patterns
    like length preferences, topic preferences, and style preferences.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    patterns = await feedback_analyzer.analyze_feedback_patterns(
        user_id=user_uuid,
        min_confidence=min_confidence
    )

    return {
        'user_id': user_id,
        'patterns_found': len(patterns),
        'patterns': [
            {
                'type': p.type,
                'content': p.content,
                'confidence': p.confidence,
                'source': p.source,
                'category': p.category,
                'evidence_count': p.evidence_count
            }
            for p in patterns
        ],
        'analyzed_at': datetime.utcnow().isoformat()
    }


@router.get("/negative")
async def get_negative_feedback(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    core_db: AsyncSession = Depends(get_core_db),
    ai_db: AsyncSession = Depends(get_ai_db),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    days: int = Query(30, ge=1, le=365, description="Look-back period in days"),
    with_edits_only: bool = Query(False, description="Only show feedback with edits")
) -> Dict[str, Any]:
    """
    Get negative feedback for manual review.

    Returns list of negative feedback items with original and edited text
    for human review and analysis.

    Note: Uses dual-DB architecture (AIFeedback in AI DB, messages in Core DB)
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Query AIFeedback from AI database
    query = select(AIFeedback).where(
        AIFeedback.rating == 'down',
        AIFeedback.created_at >= cutoff
    )

    if with_edits_only:
        query = query.where(AIFeedback.edited_text.isnot(None))

    query = query.order_by(AIFeedback.created_at.desc()).limit(limit)

    result = await ai_db.execute(query)
    feedbacks = result.scalars().all()

    items = []
    for fb in feedbacks:
        # Get associated message from Core database
        msg_result = await core_db.execute(
            select(ConversationMessage).where(ConversationMessage.id == fb.message_id)
        )
        message = msg_result.scalar_one_or_none()

        # Get user_id from conversation (Core database)
        user_id = None
        if message:
            conv_result = await core_db.execute(
                select(Conversation).where(Conversation.id == message.conversation_id)
            )
            conv = conv_result.scalar_one_or_none()
            if conv:
                user_id = str(conv.user_id)

        items.append({
            'feedback_id': str(fb.id),
            'message_id': str(fb.message_id),
            'user_id': user_id,
            'rating': fb.rating,
            'original_text': message.content if message else None,
            'edited_text': fb.edited_text,
            'comment': fb.comment,
            'created_at': fb.created_at.isoformat()
        })

    return {
        'total': len(items),
        'period_days': days,
        'with_edits_only': with_edits_only,
        'items': items
    }


@router.get("/learned-preferences")
async def get_learned_preferences(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    ai_db: AsyncSession = Depends(get_ai_db),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return")
) -> Dict[str, Any]:
    """
    Get learned preferences that have been created from feedback.

    Shows all memory rules that were created by the feedback learning system.

    Note: Uses AI database (ai_memories table)
    """
    query = select(AIMemory).where(AIMemory.scope == 'user')

    if user_id:
        try:
            user_uuid = UUID(user_id)
            query = query.where(AIMemory.user_id == user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")

    query = query.order_by(AIMemory.created_at.desc()).limit(limit)

    result = await ai_db.execute(query)
    memories = result.scalars().all()

    # Filter to only learned preferences
    learned = []
    for m in memories:
        tags = m.tags or {}
        if tags.get('source') in ['feedback_learning', 'pattern_analysis']:
            learned.append({
                'memory_id': str(m.id),
                'user_id': str(m.user_id),
                'content': m.content,
                'category': tags.get('category'),
                'source': tags.get('source'),
                'confidence': tags.get('confidence'),
                'created_at': m.created_at.isoformat()
            })

    return {
        'total': len(learned),
        'preferences': learned
    }


@router.get("/stats")
async def get_learning_stats(
    admin_user: CurrentAdmin = Depends(get_current_admin)
) -> Dict[str, Any]:
    """
    Get comprehensive feedback learning statistics.

    Returns overall statistics about the feedback learning system.
    """
    return await get_feedback_learning_stats()


@router.post("/run-learning")
async def trigger_learning_job(
    background_tasks: BackgroundTasks,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence for rules"),
    days: int = Query(30, ge=1, le=365, description="Days of feedback to analyze")
) -> Dict[str, Any]:
    """
    Manually trigger the feedback learning batch job.

    Analyzes accumulated feedback across all users and creates memory rules
    for detected patterns. Safe to run multiple times.
    """
    logger.info(f"Admin {admin_user.email} triggered feedback learning job")

    result = await run_feedback_learning_batch(
        min_confidence=min_confidence,
        days_lookback=days,
        min_feedback_per_user=3
    )

    return result


@router.post("/reprocess")
async def reprocess_feedback(
    admin_user: CurrentAdmin = Depends(get_current_admin),
    days: int = Query(7, ge=1, le=30, description="Days of feedback to reprocess")
) -> Dict[str, Any]:
    """
    Reprocess feedback that may have been missed.

    Catches any feedback where real-time learning failed.
    Safe to run multiple times as duplicates are checked.
    """
    logger.info(f"Admin {admin_user.email} triggered feedback reprocessing for {days} days")

    result = await reprocess_unlearned_feedback(days=days)

    return result


@router.post("/analyze-user/{user_id}")
async def analyze_user_feedback(
    user_id: str,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Minimum confidence for rules"),
    create_rules: bool = Query(False, description="Actually create memory rules")
) -> Dict[str, Any]:
    """
    Analyze a specific user's feedback and optionally create rules.

    Use create_rules=false (default) to preview what would be learned.
    Use create_rules=true to actually create memory rules.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    logger.info(
        f"Admin {admin_user.email} analyzing feedback for user {user_id} "
        f"(create_rules={create_rules})"
    )

    if create_rules:
        # Actually create rules
        result = await learning_service.run_batch_pattern_analysis(
            user_id=user_uuid,
            min_confidence=min_confidence
        )
        return result
    else:
        # Preview only - just analyze
        patterns = await feedback_analyzer.analyze_feedback_patterns(
            user_id=user_uuid,
            min_confidence=min_confidence
        )

        return {
            'user_id': user_id,
            'preview_mode': True,
            'patterns_found': len(patterns),
            'patterns': [
                {
                    'type': p.type,
                    'content': p.content,
                    'confidence': p.confidence,
                    'source': p.source,
                    'category': p.category,
                    'evidence_count': p.evidence_count
                }
                for p in patterns
            ],
            'note': 'Use create_rules=true to actually create these as memory rules'
        }
