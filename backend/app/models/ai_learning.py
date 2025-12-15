"""
AI Learning Models - Knowledge Base, Memories, and Feedback

Supports the learning engine for SigmaSight's AI copilot:
- ai_kb_documents: RAG knowledge base with pgvector embeddings
- ai_memories: Persistent rules and preferences (user/tenant/global)
- ai_feedback: User feedback on AI responses for improvement
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base

# Note: Vector type requires pgvector extension and pgvector-python package
# We use raw SQL in the migration for the vector column
# The embedding column will be accessed via raw SQL queries in rag_service.py


class AIKBDocument(Base):
    """
    Knowledge base documents for RAG (Retrieval Augmented Generation).

    Stores domain knowledge, tool documentation, curated Q&A, and
    best-practice answers that the agent retrieves via semantic search.
    """
    __tablename__ = "ai_kb_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Scope for filtering (e.g., 'global', 'page:portfolio', 'tenant:xyz')
    scope = Column(String(100), nullable=False, index=True)

    # Document content
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)

    # Additional metadata (tags, source, version, etc.)
    # Note: Named 'doc_metadata' because 'metadata' is reserved in SQLAlchemy
    doc_metadata = Column('metadata', JSONB, nullable=False, server_default='{}')

    # Note: embedding column (vector(1536)) is added via migration
    # SQLAlchemy doesn't natively support pgvector, so we use raw SQL

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_ai_kb_documents_scope', 'scope'),
        # Vector index is added via migration using raw SQL
    )

    def __repr__(self):
        return f"<AIKBDocument {self.id} scope={self.scope} title={self.title[:50]}>"


class AIMemory(Base):
    """
    Persistent memories and rules for the AI agent.

    Stores user preferences, tenant-level policies, and global rules
    that are injected into the system prompt at runtime.

    Examples:
    - Global: "Do not provide tax advice; suggest consulting a professional."
    - Tenant: "Default benchmark for this client is 60/40."
    - User: "Prefers brief, data-focused responses."
    """
    __tablename__ = "ai_memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Scope ownership
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Future: tenant support

    # Scope type: 'user', 'tenant', 'global'
    scope = Column(String(20), nullable=False, index=True)

    # The actual rule or preference content
    content = Column(Text, nullable=False)

    # Tags for filtering (e.g., {"page": "portfolio", "feature": "volatility"})
    tags = Column(JSONB, nullable=False, server_default='{}')

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('ix_ai_memories_scope', 'scope'),
        Index('ix_ai_memories_user_id', 'user_id'),
        Index('ix_ai_memories_tenant_id', 'tenant_id'),
    )

    def __repr__(self):
        return f"<AIMemory {self.id} scope={self.scope} content={self.content[:50]}>"


class AIFeedback(Base):
    """
    User feedback on AI-generated messages.

    Captures thumbs up/down ratings and optional edited responses
    for offline analysis and knowledge base improvement.
    """
    __tablename__ = "ai_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Reference to the message being rated
    # Note: References agent_messages table (not a formal FK to avoid circular deps)
    message_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Rating: 'up' or 'down'
    rating = Column(String(10), nullable=False)

    # Optional: user-corrected response text
    edited_text = Column(Text, nullable=True)

    # Optional: user comment explaining the rating
    comment = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index('ix_ai_feedback_message_id', 'message_id'),
        Index('ix_ai_feedback_rating', 'rating'),
    )

    def __repr__(self):
        return f"<AIFeedback {self.id} message={self.message_id} rating={self.rating}>"
