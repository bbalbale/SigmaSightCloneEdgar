"""
RAG Service for AI Learning Engine

Provides semantic search over the ai_kb_documents table using pgvector embeddings.
Used by the agent to retrieve relevant knowledge base documents before answering questions.

Features:
- Embed text using OpenAI text-embedding-3-small
- Insert/update KB documents with embeddings
- Retrieve relevant docs by vector similarity (cosine distance)
- Scope-based filtering (global, page-specific, portfolio-specific)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
import os
import json
from datetime import datetime

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)

# OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Singleton OpenAI client for embeddings
_embedding_client: Optional[AsyncOpenAI] = None


def get_embedding_client() -> AsyncOpenAI:
    """Get or create singleton OpenAI client for embeddings"""
    global _embedding_client
    if _embedding_client is None:
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set for RAG embeddings")
        _embedding_client = AsyncOpenAI(api_key=api_key)
    return _embedding_client


async def embed_text(text_value: str) -> List[float]:
    """
    Generate embedding vector for text using OpenAI.

    Args:
        text_value: The text to embed

    Returns:
        List of floats representing the embedding vector (1536 dimensions)
    """
    client = get_embedding_client()

    try:
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text_value,
        )
        embedding = response.data[0].embedding
        logger.debug(f"[RAG] Generated embedding for text ({len(text_value)} chars)")
        return embedding
    except Exception as e:
        logger.error(f"[RAG] Failed to generate embedding: {e}")
        raise


async def upsert_kb_document(
    db: AsyncSession,
    *,
    scope: str,
    title: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    doc_id: Optional[str] = None,
) -> str:
    """
    Insert or update a knowledge base document with its embedding.

    Args:
        db: Async database session
        scope: Scope for filtering (e.g., 'global', 'page:portfolio', 'tenant:xyz')
        title: Document title
        content: Document content (will be embedded)
        metadata: Optional metadata dict (tags, source, version, etc.)
        doc_id: Optional document ID for updates (if None, creates new)

    Returns:
        The document ID (UUID string)
    """
    metadata = metadata or {}

    # Generate embedding for the content
    embedding = await embed_text(content)
    embedding_str = f"[{','.join(str(x) for x in embedding)}]"

    if doc_id:
        # Update existing document
        # Note: Use CAST() instead of :: syntax for asyncpg compatibility
        stmt = text(
            """
            UPDATE ai_kb_documents
            SET scope = :scope,
                title = :title,
                content = :content,
                metadata = CAST(:metadata AS jsonb),
                embedding = CAST(:embedding AS vector),
                updated_at = now()
            WHERE id = CAST(:doc_id AS uuid)
            RETURNING id
            """
        )
        params = {
            "doc_id": doc_id,
            "scope": scope,
            "title": title,
            "content": content,
            "metadata": json.dumps(metadata),
            "embedding": embedding_str,
        }
    else:
        # Insert new document
        # Note: Use CAST() instead of :: syntax for asyncpg compatibility
        stmt = text(
            """
            INSERT INTO ai_kb_documents (scope, title, content, metadata, embedding)
            VALUES (:scope, :title, :content, CAST(:metadata AS jsonb), CAST(:embedding AS vector))
            RETURNING id
            """
        )
        params = {
            "scope": scope,
            "title": title,
            "content": content,
            "metadata": json.dumps(metadata),
            "embedding": embedding_str,
        }

    result = await db.execute(stmt, params)
    row = result.fetchone()
    await db.commit()

    new_id = str(row[0])
    action = "Updated" if doc_id else "Inserted"
    logger.info(f"[RAG] {action} KB doc id={new_id} scope={scope!r} title={title!r}")

    return new_id


async def retrieve_relevant_docs(
    db: AsyncSession,
    *,
    query: str,
    scopes: Optional[Sequence[str]] = None,
    limit: int = 5,
    similarity_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Retrieve the most relevant KB documents for a query using vector similarity.

    Args:
        db: Async database session
        query: The query text to search for
        scopes: Optional list of scopes to filter by (e.g., ['global', 'page:portfolio'])
        limit: Maximum number of documents to return (default 5)
        similarity_threshold: Minimum similarity score (0.0 = no threshold)

    Returns:
        List of document dicts with id, scope, title, content, metadata, similarity
    """
    # Generate embedding for the query
    embedding = await embed_text(query)
    embedding_str = f"[{','.join(str(x) for x in embedding)}]"

    if scopes:
        # Filter by scopes using ANY
        # Note: Use CAST() instead of :: syntax for asyncpg compatibility
        stmt = text(
            """
            SELECT
                id,
                scope,
                title,
                content,
                metadata,
                1 - (embedding <=> CAST(:embedding AS vector)) as similarity
            FROM ai_kb_documents
            WHERE scope = ANY(:scopes)
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )
        params = {
            "scopes": list(scopes),
            "embedding": embedding_str,
            "limit": limit,
        }
    else:
        # No scope filter - search all documents
        # Note: Use CAST() instead of :: syntax for asyncpg compatibility
        stmt = text(
            """
            SELECT
                id,
                scope,
                title,
                content,
                metadata,
                1 - (embedding <=> CAST(:embedding AS vector)) as similarity
            FROM ai_kb_documents
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )
        params = {
            "embedding": embedding_str,
            "limit": limit,
        }

    result = await db.execute(stmt, params)
    rows = result.mappings().all()

    docs: List[Dict[str, Any]] = []
    for row in rows:
        similarity = float(row["similarity"]) if row["similarity"] else 0.0

        # Skip documents below similarity threshold
        if similarity_threshold > 0 and similarity < similarity_threshold:
            continue

        docs.append({
            "id": str(row["id"]),
            "scope": row["scope"],
            "title": row["title"],
            "content": row["content"],
            "metadata": row["metadata"],
            "similarity": round(similarity, 4),
        })

    logger.info(f"[RAG] Retrieved {len(docs)} docs for query={query[:50]!r}... scopes={scopes}")
    return docs


async def delete_kb_document(
    db: AsyncSession,
    doc_id: str,
) -> bool:
    """
    Delete a knowledge base document by ID.

    Args:
        db: Async database session
        doc_id: The document UUID to delete

    Returns:
        True if document was deleted, False if not found
    """
    # Note: Use CAST() instead of :: syntax for asyncpg compatibility
    stmt = text(
        """
        DELETE FROM ai_kb_documents
        WHERE id = CAST(:doc_id AS uuid)
        RETURNING id
        """
    )

    result = await db.execute(stmt, {"doc_id": doc_id})
    row = result.fetchone()
    await db.commit()

    if row:
        logger.info(f"[RAG] Deleted KB doc id={doc_id}")
        return True
    else:
        logger.warning(f"[RAG] KB doc not found for deletion id={doc_id}")
        return False


async def count_kb_documents(
    db: AsyncSession,
    scope: Optional[str] = None,
) -> int:
    """
    Count knowledge base documents, optionally filtered by scope.

    Args:
        db: Async database session
        scope: Optional scope to filter by

    Returns:
        Number of documents
    """
    if scope:
        stmt = text(
            """
            SELECT COUNT(*) FROM ai_kb_documents
            WHERE scope = :scope
            """
        )
        result = await db.execute(stmt, {"scope": scope})
    else:
        stmt = text("SELECT COUNT(*) FROM ai_kb_documents")
        result = await db.execute(stmt)

    count = result.scalar()
    return count or 0


async def get_kb_document_by_id(
    db: AsyncSession,
    doc_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get a single KB document by ID.

    Args:
        db: Async database session
        doc_id: The document UUID

    Returns:
        Document dict or None if not found
    """
    # Note: Use CAST() instead of :: syntax for asyncpg compatibility
    stmt = text(
        """
        SELECT id, scope, title, content, metadata, created_at, updated_at
        FROM ai_kb_documents
        WHERE id = CAST(:doc_id AS uuid)
        """
    )

    result = await db.execute(stmt, {"doc_id": doc_id})
    row = result.mappings().fetchone()

    if not row:
        return None

    return {
        "id": str(row["id"]),
        "scope": row["scope"],
        "title": row["title"],
        "content": row["content"],
        "metadata": row["metadata"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


async def list_kb_documents(
    db: AsyncSession,
    scope: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    List KB documents with pagination, optionally filtered by scope.

    Args:
        db: Async database session
        scope: Optional scope to filter by
        limit: Maximum number of documents to return
        offset: Number of documents to skip

    Returns:
        List of document dicts (without embeddings)
    """
    if scope:
        stmt = text(
            """
            SELECT id, scope, title, content, metadata, created_at, updated_at
            FROM ai_kb_documents
            WHERE scope = :scope
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        result = await db.execute(stmt, {"scope": scope, "limit": limit, "offset": offset})
    else:
        stmt = text(
            """
            SELECT id, scope, title, content, metadata, created_at, updated_at
            FROM ai_kb_documents
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        result = await db.execute(stmt, {"limit": limit, "offset": offset})

    rows = result.mappings().all()

    docs = []
    for row in rows:
        docs.append({
            "id": str(row["id"]),
            "scope": row["scope"],
            "title": row["title"],
            "content": row["content"],
            "metadata": row["metadata"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        })

    return docs


# Helper function to format RAG docs for injection into prompts
def format_rag_docs_for_prompt(docs: List[Dict[str, Any]], max_chars: int = 8000) -> str:
    """
    Format retrieved RAG documents for injection into the system prompt.

    Args:
        docs: List of document dicts from retrieve_relevant_docs
        max_chars: Maximum total characters for the formatted output

    Returns:
        Formatted string for prompt injection
    """
    if not docs:
        return ""

    parts = []
    total_chars = 0

    for i, doc in enumerate(docs, 1):
        # Format each document
        doc_text = f"[{i}] {doc['title']}\n{doc['content']}"

        # Check if we'd exceed max_chars
        if total_chars + len(doc_text) > max_chars:
            # Truncate this doc to fit
            remaining = max_chars - total_chars
            if remaining > 100:  # Only include if we have meaningful space
                doc_text = doc_text[:remaining] + "..."
                parts.append(doc_text)
            break

        parts.append(doc_text)
        total_chars += len(doc_text) + 2  # +2 for newlines

    return "\n\n".join(parts)
