"""
Feedback Learning Batch Job - Phase 3.4 of PRD4

Scheduled job that runs pattern analysis on accumulated feedback
across all users and creates memory rules for detected patterns.

This job complements real-time learning by:
1. Detecting patterns that only emerge over multiple feedback instances
2. Running more computationally expensive analyses during off-peak hours
3. Ensuring no feedback is missed even if real-time processing fails

Created: December 18, 2025
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import get_async_session, get_ai_session
from app.models.ai_models import AIFeedback
from app.agent.models.conversations import Conversation, ConversationMessage
from app.agent.services.learning_service import learning_service
from app.agent.services.feedback_analyzer import feedback_analyzer

logger = get_logger(__name__)


async def get_users_with_recent_feedback(
    days: int = 7,
    min_feedback_count: int = 3
) -> List[UUID]:
    """
    Get list of users who have provided feedback recently.

    Args:
        days: Number of days to look back
        min_feedback_count: Minimum feedback count to include user

    Returns:
        List of user UUIDs with recent feedback
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get all feedback message IDs from AI database
    async with get_ai_session() as ai_db:
        feedback_result = await ai_db.execute(
            select(AIFeedback.message_id)
            .where(AIFeedback.created_at >= cutoff)
        )
        message_ids = [f for f in feedback_result.scalars().all()]

    if not message_ids:
        return []

    # Get conversations and users from Core database
    async with get_async_session() as core_db:
        msg_result = await core_db.execute(
            select(ConversationMessage.conversation_id)
            .where(ConversationMessage.id.in_(message_ids))
        )
        conversation_ids = list(set(msg_result.scalars().all()))

        if not conversation_ids:
            return []

        # Get user IDs with feedback counts
        conv_result = await core_db.execute(
            select(
                Conversation.user_id,
                func.count(Conversation.id).label('conv_count')
            )
            .where(Conversation.id.in_(conversation_ids))
            .group_by(Conversation.user_id)
            .having(func.count(Conversation.id) >= min_feedback_count)
        )

        users = [row[0] for row in conv_result.all()]

    logger.info(
        f"Found {len(users)} users with {min_feedback_count}+ feedback "
        f"records in the last {days} days"
    )

    return users


async def run_feedback_learning_batch(
    min_confidence: float = 0.7,
    days_lookback: int = 30,
    min_feedback_per_user: int = 3
) -> Dict[str, Any]:
    """
    Run the batch feedback learning job.

    This job:
    1. Identifies users with recent feedback
    2. Runs pattern analysis on each user's feedback
    3. Creates memory rules for detected patterns
    4. Returns summary statistics

    Args:
        min_confidence: Minimum confidence for rule creation (0.7 = 70%)
        days_lookback: How many days of feedback to analyze
        min_feedback_per_user: Minimum feedback records per user to analyze

    Returns:
        Summary dictionary with job results
    """
    logger.info(
        f"[FeedbackLearningJob] Starting batch job "
        f"(confidence={min_confidence}, days={days_lookback})"
    )

    start_time = datetime.utcnow()

    result = {
        'job_type': 'feedback_learning_batch',
        'started_at': start_time.isoformat(),
        'users_processed': 0,
        'total_patterns_found': 0,
        'total_rules_created': 0,
        'user_results': [],
        'errors': []
    }

    try:
        # Get users with recent feedback
        users = await get_users_with_recent_feedback(
            days=days_lookback,
            min_feedback_count=min_feedback_per_user
        )

        if not users:
            logger.info("[FeedbackLearningJob] No users with sufficient feedback found")
            result['status'] = 'completed'
            result['message'] = 'No users with sufficient feedback to analyze'
            return result

        # Process each user
        for user_id in users:
            try:
                user_result = await learning_service.run_batch_pattern_analysis(
                    user_id=user_id,
                    min_confidence=min_confidence
                )

                result['users_processed'] += 1
                result['total_patterns_found'] += user_result.get('patterns_found', 0)
                result['total_rules_created'] += user_result.get('rules_created', 0)

                if user_result.get('rules_created', 0) > 0:
                    result['user_results'].append(user_result)

            except Exception as e:
                logger.error(
                    f"[FeedbackLearningJob] Error processing user {user_id}: {e}"
                )
                result['errors'].append({
                    'user_id': str(user_id),
                    'error': str(e)
                })

        result['status'] = 'completed'
        result['duration_seconds'] = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"[FeedbackLearningJob] Completed: processed {result['users_processed']} users, "
            f"found {result['total_patterns_found']} patterns, "
            f"created {result['total_rules_created']} rules"
        )

    except Exception as e:
        logger.error(f"[FeedbackLearningJob] Job failed: {e}")
        result['status'] = 'failed'
        result['error'] = str(e)

    result['completed_at'] = datetime.utcnow().isoformat()
    return result


async def reprocess_unlearned_feedback(days: int = 7) -> Dict[str, Any]:
    """
    Reprocess feedback that may not have been learned from.

    This catches any feedback where the real-time learning failed
    or was missed. Safe to run multiple times as learning_service
    checks for duplicates.

    Args:
        days: Number of days to look back

    Returns:
        Summary of reprocessing results
    """
    logger.info(f"[FeedbackLearningJob] Reprocessing feedback from last {days} days")

    cutoff = datetime.utcnow() - timedelta(days=days)

    result = {
        'job_type': 'feedback_reprocessing',
        'started_at': datetime.utcnow().isoformat(),
        'feedback_processed': 0,
        'actions_taken': 0,
        'errors': []
    }

    try:
        # Get recent feedback from AI database
        async with get_ai_session() as ai_db:
            feedback_result = await ai_db.execute(
                select(AIFeedback)
                .where(AIFeedback.created_at >= cutoff)
                .order_by(AIFeedback.created_at.desc())
            )
            feedbacks = feedback_result.scalars().all()

        for feedback in feedbacks:
            try:
                learning_result = await learning_service.process_feedback(feedback)
                result['feedback_processed'] += 1

                if learning_result.get('actions_taken'):
                    result['actions_taken'] += len(learning_result['actions_taken'])

            except Exception as e:
                result['errors'].append({
                    'feedback_id': str(feedback.id),
                    'error': str(e)
                })

        result['status'] = 'completed'

    except Exception as e:
        logger.error(f"[FeedbackLearningJob] Reprocessing failed: {e}")
        result['status'] = 'failed'
        result['error'] = str(e)

    result['completed_at'] = datetime.utcnow().isoformat()
    return result


async def get_feedback_learning_stats() -> Dict[str, Any]:
    """
    Get statistics about feedback learning status.

    Returns:
        Statistics dictionary
    """
    # Query AI database for feedback statistics
    async with get_ai_session() as ai_db:
        # Total feedback count
        total_result = await ai_db.execute(
            select(func.count(AIFeedback.id))
        )
        total_feedback = total_result.scalar() or 0

        # Positive/negative counts
        positive_result = await ai_db.execute(
            select(func.count(AIFeedback.id))
            .where(AIFeedback.rating == 'up')
        )
        positive_count = positive_result.scalar() or 0

        negative_result = await ai_db.execute(
            select(func.count(AIFeedback.id))
            .where(AIFeedback.rating == 'down')
        )
        negative_count = negative_result.scalar() or 0

        # Feedback with edits
        edits_result = await ai_db.execute(
            select(func.count(AIFeedback.id))
            .where(AIFeedback.edited_text.isnot(None))
        )
        with_edits = edits_result.scalar() or 0

        # Recent feedback (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_result = await ai_db.execute(
            select(func.count(AIFeedback.id))
            .where(AIFeedback.created_at >= week_ago)
        )
        recent_feedback = recent_result.scalar() or 0

        return {
            'total_feedback': total_feedback,
            'positive_feedback': positive_count,
            'negative_feedback': negative_count,
            'positive_ratio': positive_count / total_feedback if total_feedback > 0 else 0,
            'feedback_with_edits': with_edits,
            'recent_feedback_7d': recent_feedback,
            'generated_at': datetime.utcnow().isoformat()
        }
