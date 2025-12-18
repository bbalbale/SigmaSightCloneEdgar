"""
Memory Service for AI Learning Engine

Provides CRUD operations for the ai_memories table.
Memories store user preferences, corrections, and context that persists across conversations.

Memory Scopes:
- "user": General user preferences (e.g., "prefers concise answers")
- "portfolio": Portfolio-specific context (e.g., "AAPL is core holding")
- "global": System-wide facts (rarely used)

Usage:
    from app.agent.services.memory_service import (
        save_memory,
        get_user_memories,
        delete_memory,
        format_memories_for_prompt,
    )
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.logging import get_logger

logger = get_logger(__name__)

# Memory scope constants
SCOPE_USER = "user"
SCOPE_PORTFOLIO = "portfolio"
SCOPE_GLOBAL = "global"

# Limits
MAX_MEMORIES_PER_USER = 50
MAX_MEMORY_LENGTH = 500


async def save_memory(
    db: AsyncSession,
    *,
    user_id: UUID,
    content: str,
    scope: str = SCOPE_USER,
    tags: Optional[Dict[str, Any]] = None,
    portfolio_id: Optional[UUID] = None,
) -> str:
    """
    Save a memory for a user.

    Args:
        db: Async database session
        user_id: The user's UUID
        content: The memory content (max 500 chars)
        scope: Memory scope ("user", "portfolio", "global")
        tags: Optional metadata tags (e.g., {"category": "preference"})
        portfolio_id: Optional portfolio UUID for portfolio-scoped memories

    Returns:
        The memory ID (UUID string)
    """
    # Validate and truncate content
    content = content.strip()
    if len(content) > MAX_MEMORY_LENGTH:
        content = content[:MAX_MEMORY_LENGTH]
        logger.warning(f"[Memory] Truncated memory content to {MAX_MEMORY_LENGTH} chars")

    if not content:
        raise ValueError("Memory content cannot be empty")

    tags = tags or {}

    # Add portfolio_id to tags if provided
    if portfolio_id:
        tags["portfolio_id"] = str(portfolio_id)

    # Check if user already has too many memories
    count_stmt = text("""
        SELECT COUNT(*) FROM ai_memories WHERE user_id = CAST(:user_id AS uuid)
    """)
    count_result = await db.execute(count_stmt, {"user_id": str(user_id)})
    current_count = count_result.scalar() or 0

    if current_count >= MAX_MEMORIES_PER_USER:
        # Delete oldest memory to make room
        delete_oldest_stmt = text("""
            DELETE FROM ai_memories
            WHERE id = (
                SELECT id FROM ai_memories
                WHERE user_id = CAST(:user_id AS uuid)
                ORDER BY created_at ASC
                LIMIT 1
            )
        """)
        await db.execute(delete_oldest_stmt, {"user_id": str(user_id)})
        logger.info(f"[Memory] Deleted oldest memory for user {user_id} (limit reached)")

    # Insert new memory
    stmt = text("""
        INSERT INTO ai_memories (user_id, scope, content, tags)
        VALUES (CAST(:user_id AS uuid), :scope, :content, CAST(:tags AS jsonb))
        RETURNING id
    """)

    result = await db.execute(stmt, {
        "user_id": str(user_id),
        "scope": scope,
        "content": content,
        "tags": json.dumps(tags),
    })

    row = result.fetchone()
    await db.commit()

    memory_id = str(row[0])
    logger.info(f"[Memory] Saved memory id={memory_id} user={user_id} scope={scope}")

    return memory_id


async def get_user_memories(
    db: AsyncSession,
    user_id: UUID,
    *,
    scope: Optional[str] = None,
    portfolio_id: Optional[UUID] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Retrieve memories for a user.

    Args:
        db: Async database session
        user_id: The user's UUID
        scope: Optional scope filter ("user", "portfolio", "global")
        portfolio_id: Optional portfolio UUID filter
        limit: Maximum number of memories to return

    Returns:
        List of memory dicts with id, scope, content, tags, created_at
    """
    if scope and portfolio_id:
        stmt = text("""
            SELECT id, scope, content, tags, created_at
            FROM ai_memories
            WHERE user_id = CAST(:user_id AS uuid)
              AND scope = :scope
              AND tags->>'portfolio_id' = :portfolio_id
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        params = {
            "user_id": str(user_id),
            "scope": scope,
            "portfolio_id": str(portfolio_id),
            "limit": limit,
        }
    elif scope:
        stmt = text("""
            SELECT id, scope, content, tags, created_at
            FROM ai_memories
            WHERE user_id = CAST(:user_id AS uuid)
              AND scope = :scope
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        params = {"user_id": str(user_id), "scope": scope, "limit": limit}
    elif portfolio_id:
        stmt = text("""
            SELECT id, scope, content, tags, created_at
            FROM ai_memories
            WHERE user_id = CAST(:user_id AS uuid)
              AND tags->>'portfolio_id' = :portfolio_id
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        params = {"user_id": str(user_id), "portfolio_id": str(portfolio_id), "limit": limit}
    else:
        stmt = text("""
            SELECT id, scope, content, tags, created_at
            FROM ai_memories
            WHERE user_id = CAST(:user_id AS uuid)
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        params = {"user_id": str(user_id), "limit": limit}

    result = await db.execute(stmt, params)
    rows = result.mappings().all()

    memories = []
    for row in rows:
        memories.append({
            "id": str(row["id"]),
            "scope": row["scope"],
            "content": row["content"],
            "tags": row["tags"] or {},
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })

    logger.debug(f"[Memory] Retrieved {len(memories)} memories for user {user_id}")
    return memories


async def delete_memory(
    db: AsyncSession,
    memory_id: str,
    user_id: UUID,
) -> bool:
    """
    Delete a specific memory (user must own it).

    Args:
        db: Async database session
        memory_id: The memory UUID to delete
        user_id: The user's UUID (for ownership check)

    Returns:
        True if deleted, False if not found or not owned by user
    """
    stmt = text("""
        DELETE FROM ai_memories
        WHERE id = CAST(:memory_id AS uuid)
          AND user_id = CAST(:user_id AS uuid)
        RETURNING id
    """)

    result = await db.execute(stmt, {
        "memory_id": memory_id,
        "user_id": str(user_id),
    })
    row = result.fetchone()
    await db.commit()

    if row:
        logger.info(f"[Memory] Deleted memory id={memory_id}")
        return True
    else:
        logger.warning(f"[Memory] Memory not found or not owned: id={memory_id}")
        return False


async def delete_all_user_memories(
    db: AsyncSession,
    user_id: UUID,
) -> int:
    """
    Delete all memories for a user.

    Args:
        db: Async database session
        user_id: The user's UUID

    Returns:
        Number of memories deleted
    """
    stmt = text("""
        DELETE FROM ai_memories
        WHERE user_id = CAST(:user_id AS uuid)
    """)

    result = await db.execute(stmt, {"user_id": str(user_id)})
    await db.commit()

    deleted_count = result.rowcount
    logger.info(f"[Memory] Deleted {deleted_count} memories for user {user_id}")

    return deleted_count


async def count_user_memories(
    db: AsyncSession,
    user_id: UUID,
) -> int:
    """
    Count memories for a user.

    Args:
        db: Async database session
        user_id: The user's UUID

    Returns:
        Number of memories
    """
    stmt = text("""
        SELECT COUNT(*) FROM ai_memories
        WHERE user_id = CAST(:user_id AS uuid)
    """)

    result = await db.execute(stmt, {"user_id": str(user_id)})
    return result.scalar() or 0


def format_memories_for_prompt(memories: List[Dict[str, Any]], max_chars: int = 1000) -> str:
    """
    Format memories for injection into the system prompt.

    Args:
        memories: List of memory dicts from get_user_memories
        max_chars: Maximum total characters

    Returns:
        Formatted string for prompt injection
    """
    if not memories:
        return ""

    parts = []
    total_chars = 0

    for memory in memories:
        content = memory["content"]
        scope = memory["scope"]

        # Format based on scope
        if scope == SCOPE_PORTFOLIO:
            portfolio_id = memory.get("tags", {}).get("portfolio_id", "")
            line = f"- [Portfolio] {content}"
        else:
            line = f"- {content}"

        if total_chars + len(line) > max_chars:
            break

        parts.append(line)
        total_chars += len(line) + 1  # +1 for newline

    return "\n".join(parts)


# Memory extraction prompt template
MEMORY_EXTRACTION_PROMPT = """Based on this conversation, identify any important facts I should remember about the user for future conversations.

Focus on:
- Communication preferences (e.g., "prefers concise answers", "likes bullet points")
- Investment interests (e.g., "interested in tech sector", "focused on dividends")
- Risk profile indicators (e.g., "conservative investor", "comfortable with volatility")
- Corrections they made (e.g., "AAPL is their largest holding")
- Explicit requests to remember something

Rules:
- Only extract genuinely useful, lasting information
- Skip transient questions or one-time requests
- Keep each memory under 100 characters
- Return NONE if nothing worth remembering

Return as a JSON array of strings, or the word NONE:
["memory 1", "memory 2"] or NONE

Conversation:
{conversation}

Memories to save:"""


async def check_for_duplicate_memory(
    db: AsyncSession,
    user_id: UUID,
    content: str,
    similarity_threshold: float = 0.9,
) -> bool:
    """
    Check if a similar memory already exists for this user.
    Uses simple string matching (could be enhanced with embeddings later).

    Args:
        db: Async database session
        user_id: The user's UUID
        content: The proposed memory content
        similarity_threshold: Not used in simple implementation

    Returns:
        True if a similar memory exists, False otherwise
    """
    # Simple approach: check for exact or near-exact matches
    content_lower = content.lower().strip()

    memories = await get_user_memories(db, user_id, limit=50)

    for memory in memories:
        existing_lower = memory["content"].lower().strip()

        # Exact match
        if existing_lower == content_lower:
            return True

        # High overlap (one contains the other)
        if content_lower in existing_lower or existing_lower in content_lower:
            return True

    return False


async def extract_memories_from_conversation(
    db: AsyncSession,
    user_id: UUID,
    conversation_text: str,
    portfolio_id: Optional[UUID] = None,
) -> List[str]:
    """
    Extract memories from a conversation using LLM analysis.

    This function analyzes conversation text to identify information worth
    remembering about the user for future conversations.

    Args:
        db: Async database session
        user_id: The user's UUID
        conversation_text: The full conversation text to analyze
        portfolio_id: Optional portfolio UUID for portfolio-scoped memories

    Returns:
        List of memory strings that were saved (empty if none extracted)
    """
    from openai import AsyncOpenAI
    from app.config import settings

    # Skip if conversation is too short
    if len(conversation_text) < 100:
        logger.debug("[Memory] Conversation too short for extraction")
        return []

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Format the extraction prompt
        prompt = MEMORY_EXTRACTION_PROMPT.format(conversation=conversation_text)

        # Call OpenAI to extract memories (use fast model)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3,
        )

        response_text = response.choices[0].message.content.strip()
        logger.debug(f"[Memory] Extraction response: {response_text}")

        # Check for NONE response
        if response_text.upper() == "NONE" or not response_text:
            logger.debug("[Memory] No memories to extract")
            return []

        # Parse JSON array response
        try:
            import json
            memories = json.loads(response_text)
            if not isinstance(memories, list):
                logger.warning(f"[Memory] Expected list, got {type(memories)}")
                return []
        except json.JSONDecodeError as e:
            logger.warning(f"[Memory] Failed to parse extraction response: {e}")
            return []

        # Save each memory (with duplicate checking)
        saved_memories = []
        for memory_content in memories:
            if not isinstance(memory_content, str) or not memory_content.strip():
                continue

            memory_content = memory_content.strip()

            # Check for duplicates
            if await check_for_duplicate_memory(db, user_id, memory_content):
                logger.debug(f"[Memory] Skipping duplicate: {memory_content[:50]}...")
                continue

            # Determine scope
            scope = SCOPE_PORTFOLIO if portfolio_id else SCOPE_USER

            # Save the memory
            try:
                await save_memory(
                    db,
                    user_id=user_id,
                    content=memory_content,
                    scope=scope,
                    portfolio_id=portfolio_id,
                    tags={"source": "auto_extraction"},
                )
                saved_memories.append(memory_content)
                logger.info(f"[Memory] Auto-saved: {memory_content[:50]}...")
            except Exception as e:
                logger.warning(f"[Memory] Failed to save memory: {e}")

        return saved_memories

    except Exception as e:
        logger.error(f"[Memory] Extraction failed: {e}")
        return []
