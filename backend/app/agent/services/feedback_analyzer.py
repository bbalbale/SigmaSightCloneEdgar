"""
Feedback Analyzer Service - Phase 3.1 of PRD4

Analyzes user feedback patterns to extract learning rules that improve
future AI responses. Supports both rule-based learning and LLM-based
rule extraction from edited responses.

Created: December 18, 2025
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.database import get_async_session
from app.models.ai_learning import AIFeedback
from app.agent.models.conversations import ConversationMessage, Conversation

logger = get_logger(__name__)


@dataclass
class LearningRule:
    """Represents a discovered learning rule from feedback analysis."""
    type: str  # 'preference', 'style', 'topic', 'format'
    content: str  # The actual rule/preference text
    confidence: float  # 0.0 to 1.0
    source: str  # 'pattern_analysis' or 'llm_extraction'
    category: str  # 'learned_preference', 'communication_style', etc.
    evidence_count: int = 1  # Number of feedback instances supporting this


class FeedbackAnalyzer:
    """
    Analyzes user feedback to extract learning rules.

    Supports two approaches:
    1. Pattern-based analysis: Statistical patterns in feedback
    2. LLM-based extraction: Extract rules from edited responses
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Fast model for extraction

    async def get_recent_feedback(
        self,
        user_id: UUID,
        limit: int = 100,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get recent feedback for a user with associated message content.

        Args:
            user_id: The user's UUID
            limit: Maximum feedback records to fetch
            days: Look back period in days

        Returns:
            List of feedback records with message content
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        async with get_async_session() as db:
            # Get feedback records
            result = await db.execute(
                select(AIFeedback)
                .where(AIFeedback.created_at >= cutoff)
                .order_by(AIFeedback.created_at.desc())
                .limit(limit)
            )
            feedbacks = result.scalars().all()

            # Enrich with message content
            enriched = []
            for feedback in feedbacks:
                # Get the associated message
                msg_result = await db.execute(
                    select(ConversationMessage)
                    .where(ConversationMessage.id == feedback.message_id)
                )
                message = msg_result.scalar_one_or_none()

                if message:
                    # Get the conversation to check user ownership
                    conv_result = await db.execute(
                        select(Conversation)
                        .where(Conversation.id == message.conversation_id)
                    )
                    conversation = conv_result.scalar_one_or_none()

                    # Only include feedback from this user
                    if conversation and conversation.user_id == user_id:
                        enriched.append({
                            'feedback_id': feedback.id,
                            'message_id': feedback.message_id,
                            'rating': feedback.rating,
                            'edited_text': feedback.edited_text,
                            'comment': feedback.comment,
                            'original_text': message.content,
                            'created_at': feedback.created_at
                        })

            return enriched

    async def analyze_feedback_patterns(
        self,
        user_id: UUID,
        min_confidence: float = 0.6
    ) -> List[LearningRule]:
        """
        Analyze user's feedback history for patterns.

        Looks for:
        - Response length preferences (too long/too short edits)
        - Topic preferences (which topics get positive feedback)
        - Style preferences (formal/casual, technical/simple)

        Args:
            user_id: The user's UUID
            min_confidence: Minimum confidence threshold for rules

        Returns:
            List of discovered LearningRule objects
        """
        feedbacks = await self.get_recent_feedback(user_id)

        if len(feedbacks) < 3:
            logger.info(f"Not enough feedback for pattern analysis: {len(feedbacks)} records")
            return []

        patterns = []

        # Pattern 1: Response length preferences
        length_rule = self._detect_length_preference(feedbacks)
        if length_rule and length_rule.confidence >= min_confidence:
            patterns.append(length_rule)

        # Pattern 2: Style preferences (from edited responses)
        style_rules = await self._detect_style_preferences(feedbacks)
        patterns.extend([r for r in style_rules if r.confidence >= min_confidence])

        # Pattern 3: Topic preferences (from positive/negative patterns)
        topic_rules = self._detect_topic_preferences(feedbacks)
        patterns.extend([r for r in topic_rules if r.confidence >= min_confidence])

        logger.info(
            f"Analyzed {len(feedbacks)} feedback records for user {user_id}, "
            f"found {len(patterns)} patterns"
        )

        return patterns

    def _detect_length_preference(
        self,
        feedbacks: List[Dict[str, Any]]
    ) -> Optional[LearningRule]:
        """
        Detect if user prefers shorter or longer responses.

        Analyzes edited responses to see if user consistently
        shortens or lengthens AI output.
        """
        edits_with_text = [
            f for f in feedbacks
            if f.get('edited_text') and f.get('original_text')
        ]

        if len(edits_with_text) < 3:
            return None

        length_changes = []
        for edit in edits_with_text:
            original_len = len(edit['original_text'])
            edited_len = len(edit['edited_text'])
            if original_len > 0:
                change = (edited_len - original_len) / original_len
                length_changes.append(change)

        if not length_changes:
            return None

        avg_change = sum(length_changes) / len(length_changes)
        consistency = sum(1 for c in length_changes if c * avg_change > 0) / len(length_changes)

        if abs(avg_change) > 0.2 and consistency > 0.6:
            if avg_change < -0.2:
                return LearningRule(
                    type='preference',
                    content='User prefers concise, shorter responses. Aim for brevity.',
                    confidence=min(consistency, 0.9),
                    source='pattern_analysis',
                    category='communication_style',
                    evidence_count=len(edits_with_text)
                )
            elif avg_change > 0.2:
                return LearningRule(
                    type='preference',
                    content='User prefers detailed, comprehensive responses with more explanation.',
                    confidence=min(consistency, 0.9),
                    source='pattern_analysis',
                    category='communication_style',
                    evidence_count=len(edits_with_text)
                )

        return None

    def _detect_topic_preferences(
        self,
        feedbacks: List[Dict[str, Any]]
    ) -> List[LearningRule]:
        """
        Detect topic preferences based on positive/negative feedback patterns.

        Identifies topics that consistently receive good or bad ratings.
        """
        # Define topic keywords
        topic_keywords = {
            'risk_analysis': ['risk', 'volatility', 'beta', 'drawdown', 'var'],
            'performance': ['return', 'performance', 'gain', 'loss', 'p&l'],
            'market_context': ['market', 'sector', 'index', 'benchmark'],
            'technical': ['technical', 'chart', 'pattern', 'indicator'],
            'fundamental': ['earnings', 'revenue', 'valuation', 'pe ratio'],
            'options': ['option', 'strike', 'expiration', 'greeks', 'delta'],
            'news': ['news', 'headline', 'announcement', 'event']
        }

        topic_ratings = {topic: {'positive': 0, 'negative': 0} for topic in topic_keywords}

        for feedback in feedbacks:
            content = (feedback.get('original_text') or '').lower()
            rating = feedback.get('rating')

            for topic, keywords in topic_keywords.items():
                if any(kw in content for kw in keywords):
                    if rating == 'up':
                        topic_ratings[topic]['positive'] += 1
                    elif rating == 'down':
                        topic_ratings[topic]['negative'] += 1

        rules = []
        for topic, counts in topic_ratings.items():
            total = counts['positive'] + counts['negative']
            if total >= 3:
                ratio = counts['positive'] / total if total > 0 else 0.5

                if ratio >= 0.8:
                    rules.append(LearningRule(
                        type='topic',
                        content=f'User appreciates detailed {topic.replace("_", " ")} analysis.',
                        confidence=min(ratio, 0.85),
                        source='pattern_analysis',
                        category='topic_preference',
                        evidence_count=total
                    ))
                elif ratio <= 0.2:
                    rules.append(LearningRule(
                        type='topic',
                        content=f'User prefers less emphasis on {topic.replace("_", " ")}.',
                        confidence=min(1 - ratio, 0.85),
                        source='pattern_analysis',
                        category='topic_preference',
                        evidence_count=total
                    ))

        return rules

    async def _detect_style_preferences(
        self,
        feedbacks: List[Dict[str, Any]]
    ) -> List[LearningRule]:
        """
        Detect style preferences using LLM analysis of edited responses.

        Batch analyzes multiple edits to find common style changes.
        """
        edits = [
            f for f in feedbacks
            if f.get('edited_text') and f.get('original_text')
            and len(f['original_text']) > 50 and len(f['edited_text']) > 50
        ]

        if len(edits) < 2:
            return []

        # Sample up to 5 edits for analysis
        sample = edits[:5]

        edit_descriptions = "\n\n".join([
            f"Edit {i+1}:\nOriginal: {e['original_text'][:500]}...\nEdited: {e['edited_text'][:500]}..."
            for i, e in enumerate(sample)
        ])

        prompt = f"""Analyze these user edits to AI responses and identify consistent style preferences.

{edit_descriptions}

Based on these edits, identify 1-3 clear style preferences the user has shown. For each preference:
1. Be specific and actionable
2. Focus on patterns that appear in multiple edits

Respond in JSON format:
{{
  "preferences": [
    {{
      "rule": "User prefers [specific preference]",
      "confidence": 0.0-1.0,
      "evidence": "Brief explanation of what edits show this"
    }}
  ]
}}

Only include preferences with clear evidence. If no clear patterns, return empty preferences array."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            rules = []
            for pref in result.get('preferences', []):
                if pref.get('rule') and pref.get('confidence', 0) >= 0.5:
                    rules.append(LearningRule(
                        type='style',
                        content=pref['rule'],
                        confidence=float(pref['confidence']),
                        source='llm_extraction',
                        category='communication_style',
                        evidence_count=len(sample)
                    ))

            return rules

        except Exception as e:
            logger.error(f"Style preference detection failed: {e}")
            return []

    async def extract_rule_from_edit(
        self,
        original: str,
        edited: str,
        comment: Optional[str] = None
    ) -> Optional[LearningRule]:
        """
        Use LLM to understand what a specific edit teaches us about user preferences.

        Args:
            original: The original AI response text
            edited: The user's edited version
            comment: Optional user comment explaining the edit

        Returns:
            A LearningRule if a clear preference is identified
        """
        if not original or not edited:
            return None

        # Truncate for efficiency
        original_truncated = original[:1500]
        edited_truncated = edited[:1500]

        comment_text = f"\nUser's comment: {comment}" if comment else ""

        prompt = f"""Analyze this user edit to an AI response and identify what preference it reveals.

Original response:
{original_truncated}

User edited to:
{edited_truncated}
{comment_text}

What specific preference does this edit reveal? Consider:
- Was content shortened or expanded?
- Was technical jargon simplified or added?
- Was tone changed (formal/casual)?
- Was structure/formatting changed?
- Were specific topics removed or added?

Respond in JSON format:
{{
  "preference": "User prefers [specific, actionable preference]",
  "confidence": 0.0-1.0,
  "category": "communication_style|format|content|tone"
}}

If no clear preference is identifiable, set preference to null."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            if result.get('preference') and result.get('confidence', 0) >= 0.6:
                return LearningRule(
                    type='preference',
                    content=result['preference'],
                    confidence=float(result['confidence']),
                    source='llm_extraction',
                    category=result.get('category', 'learned_preference'),
                    evidence_count=1
                )

            return None

        except Exception as e:
            logger.error(f"Rule extraction failed: {e}")
            return None

    async def get_feedback_summary(
        self,
        user_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get aggregate feedback statistics.

        Args:
            user_id: Optional filter by user (None = all users)
            days: Look back period

        Returns:
            Summary statistics dictionary
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        async with get_async_session() as db:
            base_query = select(AIFeedback).where(AIFeedback.created_at >= cutoff)

            # If user_id specified, filter by user's messages
            if user_id:
                # Get user's conversation IDs
                conv_result = await db.execute(
                    select(Conversation.id).where(Conversation.user_id == user_id)
                )
                conv_ids = [c for c in conv_result.scalars().all()]

                if conv_ids:
                    msg_result = await db.execute(
                        select(ConversationMessage.id)
                        .where(ConversationMessage.conversation_id.in_(conv_ids))
                    )
                    msg_ids = [m for m in msg_result.scalars().all()]
                    base_query = base_query.where(AIFeedback.message_id.in_(msg_ids))

            # Get all feedback
            result = await db.execute(base_query)
            feedbacks = result.scalars().all()

            # Calculate statistics
            total = len(feedbacks)
            positive = sum(1 for f in feedbacks if f.rating == 'up')
            negative = sum(1 for f in feedbacks if f.rating == 'down')
            with_edits = sum(1 for f in feedbacks if f.edited_text)
            with_comments = sum(1 for f in feedbacks if f.comment)

            return {
                'total_feedback': total,
                'positive': positive,
                'negative': negative,
                'positive_ratio': positive / total if total > 0 else 0,
                'with_edits': with_edits,
                'with_comments': with_comments,
                'period_days': days,
                'generated_at': datetime.utcnow().isoformat()
            }


# Module-level instance
feedback_analyzer = FeedbackAnalyzer()
