"""
AI Models - Separate Base for AI Database

These models use a separate declarative base (AiBase) to prevent
metadata collisions with core models. They will be managed by
migrations_ai/ and stored in the AI database (sigmasight-ai).

Tables:
- ai_kb_documents: RAG knowledge base with pgvector embeddings
- ai_memories: Persistent rules and preferences
- ai_feedback: User feedback on AI responses (logical link to Core messages)
"""
from sqlalchemy import Column, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

# Separate Base for AI models - prevents metadata collisions with Core
AiBase = declarative_base()

# Try to import Vector type from pgvector, fallback to None if not available
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None


class AIKBDocument(AiBase):
    """
    Knowledge base documents for RAG (Retrieval Augmented Generation).

    Stores domain knowledge, tool documentation, curated Q&A, and
    best-practice answers that the agent retrieves via semantic search.
    """
    __tablename__ = "ai_kb_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # Scope for filtering (e.g., 'global', 'page:portfolio', 'tenant:xyz')
    scope = Column(String(100), nullable=False, index=True)

    # Document content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)

    # Additional metadata (tags, source, version, etc.)
    doc_metadata = Column('metadata', JSONB, nullable=False, server_default='{}')

    # Vector embedding - 1536 dimensions for OpenAI embeddings
    # Note: If pgvector not installed, this column will be added via raw SQL
    if Vector is not None:
        embedding = Column(Vector(1536))

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_ai_kb_documents_scope', 'scope'),
        Index('ix_ai_kb_documents_created', 'created_at'),
        # HNSW index for vector similarity search is added via migration
    )


class AIMemory(AiBase):
    """
    Persistent memories and rules for the AI agent.

    Stores user preferences, tenant-level policies, and global rules
    that are injected into the system prompt at runtime.

    Note: user_id and tenant_id are logical references only (no FK).
    The actual User records live in the Core database.
    """
    __tablename__ = "ai_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # Logical references to Core database (NO foreign keys - cross-database)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Scope type: 'user', 'tenant', 'global'
    scope = Column(String(20), nullable=False, index=True)

    # The actual rule or preference content
    content = Column(Text, nullable=False)

    # Tags for filtering
    tags = Column(JSONB, nullable=False, server_default='{}')

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index('ix_ai_memories_scope', 'scope'),
        Index('ix_ai_memories_user_id', 'user_id'),
        Index('ix_ai_memories_tenant_id', 'tenant_id'),
    )


class AIFeedback(AiBase):
    """
    User feedback on AI-generated messages.

    Note: message_id is a logical reference to agent_messages in Core DB.
    No foreign key constraint - this is intentional for cross-database separation.
    """
    __tablename__ = "ai_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # Logical reference to message in Core DB (NO foreign key - cross-database)
    message_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Rating: 'up' or 'down'
    rating = Column(String(10), nullable=False, index=True)

    # Optional: user-corrected response text
    edited_text = Column(Text, nullable=True)

    # Optional: user comment explaining the rating
    comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index('ix_ai_feedback_message_id', 'message_id'),
        Index('ix_ai_feedback_rating', 'rating'),
    )
