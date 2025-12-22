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

    def __repr__(self):
        title_preview = self.title[:50] if self.title else ""
        return f"<AIKBDocument {self.id} scope={self.scope} title={title_preview}>"


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

    def __repr__(self):
        content_preview = self.content[:50] if self.content else ""
        return f"<AIMemory {self.id} scope={self.scope} content={content_preview}>"


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

    def __repr__(self):
        return f"<AIFeedback {self.id} message={self.message_id} rating={self.rating}>"


class AIAdminAnnotation(AiBase):
    """
    Admin annotations on AI responses for tuning and quality improvement.

    Allows admins to review AI responses and add corrections, suggestions,
    or flags that can be exported for fine-tuning or RAG updates.

    Note: message_id and admin_user_id are logical references to Core DB.
    No foreign key constraints - this is intentional for cross-database separation.

    Created: December 22, 2025 (Phase 2 Admin Dashboard)
    """
    __tablename__ = "ai_admin_annotations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    # Logical reference to message in Core DB (NO foreign key - cross-database)
    message_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Logical reference to admin_users in Core DB (NO foreign key - cross-database)
    admin_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Annotation type: 'correction', 'improvement', 'flag', 'approved'
    annotation_type = Column(String(50), nullable=False, index=True)

    # Admin's comment explaining the issue or improvement
    content = Column(Text, nullable=False)

    # Optional: what the AI should have said instead
    suggested_response = Column(Text, nullable=True)

    # Severity level: 'minor', 'moderate', 'critical'
    severity = Column(String(20), nullable=True, index=True)

    # Categorization tags: ['tone', 'accuracy', 'completeness', 'safety', etc.]
    tags = Column(JSONB, nullable=False, server_default='[]')

    # Processing status: 'pending', 'reviewed', 'applied'
    status = Column(String(20), nullable=False, default='pending', index=True)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('ix_ai_admin_annotations_message_id', 'message_id'),
        Index('ix_ai_admin_annotations_status', 'status'),
        Index('ix_ai_admin_annotations_type', 'annotation_type'),
        Index('ix_ai_admin_annotations_severity', 'severity'),
    )

    def __repr__(self):
        content_preview = self.content[:50] if self.content else ""
        return f"<AIAdminAnnotation {self.id} type={self.annotation_type} status={self.status} content={content_preview}>"
