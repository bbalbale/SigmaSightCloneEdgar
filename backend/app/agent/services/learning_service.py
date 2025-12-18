"""
Learning Service - Phase 3.2 of PRD4

Orchestrates the feedback learning loop by:
1. Processing positive feedback → storing as RAG examples
2. Processing negative feedback with edits → extracting preference rules → creating memories
3. Applying learned preferences to prompts

Created: December 18, 2025
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database import get_async_session
from app.models.ai_learning import AIFeedback, AIMemory
from app.agent.models.conversations import ConversationMessage, Conversation
from app.agent.services.feedback_analyzer import feedback_analyzer, LearningRule
from app.agent.services.rag_service import (
    upsert_kb_document,
    retrieve_relevant_docs,
    format_rag_docs_for_prompt
)
from app.agent.services.memory_service import (
    save_memory,
    get_user_memories,
    check_for_duplicate_memory,
    format_memories_for_prompt
)

logger = get_logger(__name__)

# Scope identifier for positive examples stored in KB
POSITIVE_EXAMPLE_SCOPE = "feedback:positive_example"


class LearningService:
    """
    Orchestrates the feedback learning loop.

    Processes user feedback to:
    - Store highly-rated responses as RAG examples for few-shot prompting
    - Extract preference rules from edited responses and store as memories
    - Apply learned preferences and examples to future prompts
    """

    async def process_feedback(self, feedback: AIFeedback) -> Dict[str, Any]:
        """
        Process a feedback record and trigger appropriate learning actions.

        Args:
            feedback: The AIFeedback record to process

        Returns:
            Dictionary with processing results
        """
        logger.info(f"[Learning] Processing feedback {feedback.id} (rating={feedback.rating})")

        result = {
            'feedback_id': str(feedback.id),
            'rating': feedback.rating,
            'actions_taken': [],
            'rules_created': 0,
            'examples_stored': 0
        }

        try:
            if feedback.rating == 'up':
                stored = await self._process_positive_feedback(feedback)
                if stored:
                    result['examples_stored'] = 1
                    result['actions_taken'].append('stored_positive_example')

            elif feedback.rating == 'down':
                rules = await self._process_negative_feedback(feedback)
                result['rules_created'] = len(rules)
                if rules:
                    result['actions_taken'].append(f'created_{len(rules)}_rules')

            logger.info(f"[Learning] Completed processing feedback {feedback.id}: {result}")

        except Exception as e:
            logger.error(f"[Learning] Error processing feedback {feedback.id}: {e}")
            result['error'] = str(e)

        return result

    async def _process_positive_feedback(self, feedback: AIFeedback) -> bool:
        """
        Store a positively-rated response as a RAG example.

        The response will be retrievable for few-shot prompting when
        similar queries are asked in the future.

        Returns:
            True if example was stored successfully
        """
        async with get_async_session() as db:
            # Get the message content
            msg_result = await db.execute(
                select(ConversationMessage)
                .where(ConversationMessage.id == feedback.message_id)
            )
            message = msg_result.scalar_one_or_none()

            if not message or not message.content:
                logger.warning(f"[Learning] No message content for feedback {feedback.id}")
                return False

            # Get the conversation to find user query
            conv_result = await db.execute(
                select(Conversation)
                .where(Conversation.id == message.conversation_id)
            )
            conversation = conv_result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"[Learning] No conversation for message {message.id}")
                return False

            # Get the user's preceding message (the query)
            query_result = await db.execute(
                select(ConversationMessage)
                .where(
                    ConversationMessage.conversation_id == message.conversation_id,
                    ConversationMessage.role == 'user',
                    ConversationMessage.id < message.id
                )
                .order_by(ConversationMessage.id.desc())
                .limit(1)
            )
            user_message = query_result.scalar_one_or_none()

            user_query = user_message.content if user_message else "Unknown query"

            # Create KB document with the positive example
            # Content combines query and response for better semantic matching
            doc_content = f"""User Query: {user_query}

Well-Received Response:
{message.content}"""

            # Metadata for filtering and analysis
            metadata = {
                'type': 'positive_example',
                'user_id': str(conversation.user_id),
                'message_id': str(message.id),
                'feedback_id': str(feedback.id),
                'created_from_feedback': True,
                'feedback_date': datetime.utcnow().isoformat()
            }

            # Generate title from query
            title = f"Positive Example: {user_query[:100]}"

            try:
                doc_id = await upsert_kb_document(
                    db,
                    scope=POSITIVE_EXAMPLE_SCOPE,
                    title=title,
                    content=doc_content,
                    metadata=metadata
                )
                logger.info(
                    f"[Learning] Stored positive example as KB doc {doc_id} "
                    f"for user {conversation.user_id}"
                )
                return True

            except Exception as e:
                logger.error(f"[Learning] Failed to store positive example: {e}")
                return False

    async def _process_negative_feedback(
        self,
        feedback: AIFeedback
    ) -> List[LearningRule]:
        """
        Extract learning rules from negative feedback.

        If the user provided an edited response, we analyze the edit
        to understand their preferences.

        Returns:
            List of learning rules that were created as memories
        """
        rules_created = []

        # Only process if there's edited text (we can learn from it)
        if not feedback.edited_text:
            logger.debug(f"[Learning] No edited text in feedback {feedback.id}, skipping")
            return []

        async with get_async_session() as db:
            # Get the original message
            msg_result = await db.execute(
                select(ConversationMessage)
                .where(ConversationMessage.id == feedback.message_id)
            )
            message = msg_result.scalar_one_or_none()

            if not message or not message.content:
                return []

            # Get the conversation to find user_id
            conv_result = await db.execute(
                select(Conversation)
                .where(Conversation.id == message.conversation_id)
            )
            conversation = conv_result.scalar_one_or_none()

            if not conversation:
                return []

            # Extract rule from the edit using LLM
            rule = await feedback_analyzer.extract_rule_from_edit(
                original=message.content,
                edited=feedback.edited_text,
                comment=feedback.comment
            )

            if rule:
                # Check for duplicate before saving
                is_duplicate = await check_for_duplicate_memory(
                    user_id=conversation.user_id,
                    proposed_content=rule.content
                )

                if not is_duplicate:
                    # Save as user memory
                    memory_id = await save_memory(
                        user_id=conversation.user_id,
                        content=rule.content,
                        scope='user',
                        tags={
                            'category': rule.category,
                            'source': 'feedback_learning',
                            'confidence': rule.confidence,
                            'feedback_id': str(feedback.id)
                        }
                    )

                    if memory_id:
                        rules_created.append(rule)
                        logger.info(
                            f"[Learning] Created memory {memory_id} from feedback {feedback.id}: "
                            f"'{rule.content[:50]}...'"
                        )
                else:
                    logger.debug(
                        f"[Learning] Duplicate rule detected, not saving: {rule.content[:50]}..."
                    )

        return rules_created

    async def apply_learnings_to_prompt(
        self,
        user_id: UUID,
        query: str,
        base_prompt: str,
        max_examples: int = 3,
        include_examples: bool = True
    ) -> str:
        """
        Enhance a prompt with learned preferences and relevant examples.

        Args:
            user_id: The user's UUID
            query: The current user query (for finding relevant examples)
            base_prompt: The base prompt to enhance
            max_examples: Maximum number of examples to include
            include_examples: Whether to include RAG examples (can be disabled)

        Returns:
            Enhanced prompt with learnings applied
        """
        enhanced_parts = [base_prompt]

        # 1. Get learned preferences from memories
        memories = await get_user_memories(user_id, scope='user')

        # Filter for learned preferences
        learned_prefs = [
            m for m in memories
            if m.get('tags', {}).get('source') == 'feedback_learning'
        ]

        if learned_prefs:
            prefs_text = "\n".join([
                f"- {m['content']}"
                for m in learned_prefs[:10]  # Limit to 10 preferences
            ])

            enhanced_parts.append(f"""
## Learned User Preferences
Based on previous feedback, the user has these preferences:
{prefs_text}

Apply these preferences naturally in your response.""")

        # 2. Get relevant positive examples if enabled
        if include_examples:
            async with get_async_session() as db:
                examples = await retrieve_relevant_docs(
                    db,
                    query=query,
                    scopes=[POSITIVE_EXAMPLE_SCOPE],
                    limit=max_examples,
                    similarity_threshold=0.5  # Only include relevant examples
                )

                # Filter to only this user's examples
                user_examples = [
                    e for e in examples
                    if e.get('metadata', {}).get('user_id') == str(user_id)
                ]

                if user_examples:
                    examples_text = format_rag_docs_for_prompt(user_examples, max_chars=4000)
                    enhanced_parts.append(f"""
## Examples of Well-Received Responses
Here are examples of responses this user found helpful for similar queries:

{examples_text}

Use these as guidance for tone, structure, and detail level.""")

        return "\n\n".join(enhanced_parts)

    async def get_relevant_examples(
        self,
        user_id: UUID,
        query: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant positive examples for a query.

        Args:
            user_id: The user's UUID
            query: The query to find examples for
            limit: Maximum number of examples

        Returns:
            List of relevant example documents
        """
        async with get_async_session() as db:
            examples = await retrieve_relevant_docs(
                db,
                query=query,
                scopes=[POSITIVE_EXAMPLE_SCOPE],
                limit=limit * 2,  # Fetch extra to filter by user
                similarity_threshold=0.5
            )

            # Filter to user's examples only
            user_examples = [
                e for e in examples
                if e.get('metadata', {}).get('user_id') == str(user_id)
            ][:limit]

            return user_examples

    async def run_batch_pattern_analysis(
        self,
        user_id: UUID,
        min_confidence: float = 0.7
    ) -> Dict[str, Any]:
        """
        Run batch pattern analysis for a user and create memories.

        This is typically called by a scheduled job to analyze
        accumulated feedback and create new preference rules.

        Args:
            user_id: The user's UUID
            min_confidence: Minimum confidence for rule creation

        Returns:
            Summary of patterns found and rules created
        """
        logger.info(f"[Learning] Running batch pattern analysis for user {user_id}")

        result = {
            'user_id': str(user_id),
            'patterns_found': 0,
            'rules_created': 0,
            'details': []
        }

        try:
            # Run pattern analysis
            patterns = await feedback_analyzer.analyze_feedback_patterns(
                user_id,
                min_confidence=min_confidence
            )

            result['patterns_found'] = len(patterns)

            # Create memories for high-confidence patterns
            for pattern in patterns:
                is_duplicate = await check_for_duplicate_memory(
                    user_id=user_id,
                    proposed_content=pattern.content
                )

                if not is_duplicate:
                    memory_id = await save_memory(
                        user_id=user_id,
                        content=pattern.content,
                        scope='user',
                        tags={
                            'category': pattern.category,
                            'source': 'pattern_analysis',
                            'confidence': pattern.confidence,
                            'evidence_count': pattern.evidence_count
                        }
                    )

                    if memory_id:
                        result['rules_created'] += 1
                        result['details'].append({
                            'rule': pattern.content,
                            'confidence': pattern.confidence,
                            'memory_id': str(memory_id)
                        })

            logger.info(
                f"[Learning] Batch analysis complete for user {user_id}: "
                f"{result['rules_created']} rules created from {result['patterns_found']} patterns"
            )

        except Exception as e:
            logger.error(f"[Learning] Batch analysis failed for user {user_id}: {e}")
            result['error'] = str(e)

        return result

    async def get_learning_summary(
        self,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of learning activity.

        Args:
            user_id: Optional filter by user

        Returns:
            Summary statistics
        """
        # Get feedback summary
        feedback_summary = await feedback_analyzer.get_feedback_summary(user_id)

        # Get learned preferences count
        async with get_async_session() as db:
            if user_id:
                # Count user's learned preferences
                result = await db.execute(
                    select(AIMemory)
                    .where(AIMemory.user_id == user_id)
                )
                memories = result.scalars().all()

                learned_count = sum(
                    1 for m in memories
                    if m.tags and m.tags.get('source') in ['feedback_learning', 'pattern_analysis']
                )
            else:
                learned_count = 0

            # Count positive examples in KB
            # (Would need to query ai_kb_documents, but we'll estimate from feedback)
            positive_examples = feedback_summary['positive']

        return {
            'feedback': feedback_summary,
            'learned_preferences': learned_count,
            'positive_examples_stored': positive_examples,
            'generated_at': datetime.utcnow().isoformat()
        }


# Module-level instance
learning_service = LearningService()
